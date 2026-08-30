extends Node

const BRIDGE_VERSION := "game_studio_godot_bridge.v1"
const PROTOCOL_VERSION := "godot_bridge_protocol.v1"
const MAX_MESSAGE_BYTES := 1048576
const ALLOWED_GENERIC_COMMANDS := {
	"snapshot": true,
	"input_action": true,
	"key_event": true,
	"mouse_button": true,
	"mouse_motion": true,
	"project_command": true,
	"checkpoint": true,
	"capture_structure": true,
	"capture_png": true,
	"movie_marker": true,
	"shutdown": true,
}

var _enabled := false
var _authenticated := false
var _token := ""
var _port := 0
var _output_dir := ""
var _profile_path := ""
var _scenario_path := ""
var _live_seed = null
var _live_initial_checkpoint = null
var _profile: Dictionary = {}
var _scenario: Dictionary = {}
var _server: TCPServer
var _peer: StreamPeerTCP
var _expected_size := -1
var _command_queue: Array[Dictionary] = []
var _sequence := 0
var _scenario_index := 0
var _scenario_wait_until_frame := -1
var _condition_started_frame := -1
var _scenario_failed := false
var _scenario_finished := false
var _start_frame := 0


func _enter_tree() -> void:
	var args := OS.get_cmdline_user_args()
	if not args.has("--studio-adapter-enabled"):
		return
	# Exported release templates report false.  Editor and debug exports report
	# true; no CLI argument may override this gate.
	if not OS.is_debug_build():
		push_error("Game Studio Godot Bridge refused activation in a release build")
		return
	var parsed := _parse_arguments(args)
	if not parsed.get("ok", false):
		push_error(str(parsed.get("error", "invalid bridge arguments")))
		return
	_token = parsed["token"]
	_port = parsed["port"]
	_output_dir = parsed["output_dir"]
	_profile_path = parsed["profile"]
	_scenario_path = parsed["scenario"]
	_live_seed = parsed["seed"]
	_live_initial_checkpoint = parsed["initial_checkpoint"]
	if not _token.is_valid_hex_number(false) or _token.length() != 64:
		push_error("Game Studio Godot Bridge requires a 256-bit hexadecimal session token")
		return
	if _port < 1 or _port > 65535:
		push_error("Game Studio Godot Bridge requires a valid loopback TCP port")
		return
	if not _load_contracts():
		return
	DirAccess.make_dir_recursive_absolute(_output_dir)
	_enabled = true
	set_process(true)


func _ready() -> void:
	if not _enabled:
		set_process(false)
		return
	_server = TCPServer.new()
	var listen_error := _server.listen(_port, "127.0.0.1")
	if listen_error != OK:
		_trace("ERROR", {"code": "LISTEN_FAILED", "error": error_string(listen_error)})
		_write_result("BLOCKED", "loopback bridge could not listen")
		set_process(false)
		return
	_trace("BRIDGE_READY", {
		"bridge_version": BRIDGE_VERSION,
		"protocol_version": PROTOCOL_VERSION,
		"port": _port,
		"scenario_preloaded": not _scenario.is_empty(),
	})
	_start_frame = Engine.get_process_frames()
	if not _scenario.is_empty():
		seed(int(_scenario["seed"]))
		var initial_checkpoint = _scenario.get("initial_checkpoint")
		if initial_checkpoint != null:
			_command_queue.append({
				"message_id": "scenario-initial-checkpoint",
				"payload": {"command": "checkpoint", "checkpoint": initial_checkpoint, "arguments": {}},
				"network": false,
			})
	else:
		if _live_seed != null:
			seed(int(_live_seed))
		if _live_initial_checkpoint != null:
			_command_queue.append({
				"message_id": "live-initial-checkpoint",
				"payload": {"command": "checkpoint", "checkpoint": _live_initial_checkpoint, "arguments": {}},
				"network": false,
			})


func _process(_delta: float) -> void:
	if not _enabled:
		return
	_poll_network()
	_execute_queued_commands()
	if not _scenario.is_empty() and not _scenario_finished:
		_run_scenario_frame()


func _exit_tree() -> void:
	# Release transport objects while the engine's StringName subsystem is still
	# alive; leaving them to final process teardown produces spurious core errors
	# on some Godot 4.6 patch builds.
	set_process(false)
	_command_queue.clear()
	if _peer != null:
		_peer.disconnect_from_host()
		_peer = null
	if _server != null:
		_server.stop()
		_server = null


func _parse_arguments(args: PackedStringArray) -> Dictionary:
	var result := {"ok": true, "token": "", "port": 0, "output_dir": "", "profile": "", "scenario": "", "seed": null, "initial_checkpoint": null}
	for value in args:
		if value.begins_with("--studio-token="):
			result["token"] = value.trim_prefix("--studio-token=")
		elif value.begins_with("--studio-port="):
			result["port"] = int(value.trim_prefix("--studio-port="))
		elif value.begins_with("--studio-output-dir="):
			result["output_dir"] = value.trim_prefix("--studio-output-dir=")
		elif value.begins_with("--studio-profile="):
			result["profile"] = value.trim_prefix("--studio-profile=")
		elif value.begins_with("--studio-scenario="):
			result["scenario"] = value.trim_prefix("--studio-scenario=")
		elif value.begins_with("--studio-seed="):
			result["seed"] = int(value.trim_prefix("--studio-seed="))
		elif value.begins_with("--studio-initial-checkpoint="):
			result["initial_checkpoint"] = value.trim_prefix("--studio-initial-checkpoint=")
	if result["token"] == "" or result["port"] == 0 or result["output_dir"] == "" or result["profile"] == "":
		return {"ok": false, "error": "missing required bridge activation argument"}
	return result


func _load_contracts() -> bool:
	var profile_text := FileAccess.get_file_as_string(_profile_path)
	if profile_text == "":
		push_error("Game Studio Godot Bridge profile is missing or empty")
		return false
	var profile_value = JSON.parse_string(profile_text)
	if not profile_value is Dictionary or profile_value.get("schema_version") != "godot_bridge_profile.v1":
		push_error("Game Studio Godot Bridge profile is invalid")
		return false
	_profile = profile_value
	_profile["allowed_keycodes"] = Array(_profile.get("allowed_keycodes", [])).map(func(value): return int(value))
	_profile["allowed_mouse_buttons"] = Array(_profile.get("allowed_mouse_buttons", [])).map(func(value): return int(value))
	if _scenario_path != "":
		var scenario_text := FileAccess.get_file_as_string(_scenario_path)
		var scenario_value = JSON.parse_string(scenario_text)
		if not scenario_value is Dictionary or scenario_value.get("schema_version") != "godot_scenario.v1":
			push_error("Game Studio Godot Bridge scenario is invalid")
			return false
		_scenario = scenario_value
	return true


func _poll_network() -> void:
	if _server == null:
		return
	if _server.is_connection_available():
		var candidate := _server.take_connection()
		candidate.big_endian = false
		if _peer != null and _peer.get_status() == StreamPeerTCP.STATUS_CONNECTED:
			candidate.disconnect_from_host()
		else:
			_peer = candidate
			_authenticated = false
			_expected_size = -1
			_send_message("hello", "bridge-hello", {
				"bridge_version": BRIDGE_VERSION,
				"capabilities": _capabilities(),
				"single_client": true,
				"loopback_only": true,
			})
	if _peer == null:
		return
	_peer.poll()
	if _peer.get_status() != StreamPeerTCP.STATUS_CONNECTED:
		if _authenticated:
			_trace("DISCONNECT", {})
		_peer = null
		_authenticated = false
		_expected_size = -1
		return
	while true:
		if _expected_size < 0:
			if _peer.get_available_bytes() < 4:
				return
			_expected_size = _peer.get_32()
			if _expected_size < 2 or _expected_size > MAX_MESSAGE_BYTES:
				_send_error("invalid-length", "message length rejected")
				_peer.disconnect_from_host()
				return
		if _peer.get_available_bytes() < _expected_size:
			return
		var packet := _peer.get_data(_expected_size)
		_expected_size = -1
		if packet[0] != OK:
			_peer.disconnect_from_host()
			return
		var message_value = JSON.parse_string(packet[1].get_string_from_utf8())
		if not message_value is Dictionary:
			_send_error("invalid-json", "message must be JSON object")
			continue
		_handle_message(message_value)


func _handle_message(message: Dictionary) -> void:
	var raw_message_id = message.get("message_id")
	var message_id := str(raw_message_id) if raw_message_id != null else "invalid-message"
	if not _exact_keys(message, ["protocol_version", "type", "message_id", "payload"], []):
		_send_error(message_id, "message fields violate strict protocol contract")
		return
	if not raw_message_id is String or message_id.is_empty() or message_id.length() > 128:
		_send_error("invalid-message", "message_id violates strict protocol contract")
		return
	if message.get("protocol_version") != PROTOCOL_VERSION:
		_send_error(message_id, "protocol version mismatch")
		return
	if not _authenticated:
		if message.get("type") != "handshake":
			_send_error(message_id, "handshake required")
			return
		var payload = message.get("payload", {})
		if (
			not payload is Dictionary
			or not _exact_keys(payload, ["token", "requested_capabilities"], [])
			or not _is_string_array(payload.get("requested_capabilities"))
			or payload.get("token", "") != _token
		):
			_send_message("handshake_ack", message_id, {"accepted": false})
			_peer.disconnect_from_host()
			return
		_authenticated = true
		_send_message("handshake_ack", message_id, {"accepted": true, "capabilities": _capabilities()})
		return
	if message.get("type") != "command":
		_send_error(message_id, "only command messages are accepted after handshake")
		return
	var command = message.get("payload", {})
	if not command is Dictionary or not _valid_command_contract(command):
		_send_error(message_id, "command is not declared by the bridge protocol")
		return
	_command_queue.append({"message_id": message_id, "payload": command, "network": true})


func _valid_command_contract(command: Dictionary) -> bool:
	var kind := str(command.get("command", ""))
	if not ALLOWED_GENERIC_COMMANDS.has(kind):
		return false
	match kind:
		"snapshot":
			return (
				_exact_keys(command, ["command", "snapshot_id", "kind"], ["observation"])
				and _is_nonempty_string(command["snapshot_id"])
				and command["kind"] in ["OBSERVABLE", "MECHANICAL"]
				and (not command.has("observation") or _is_nonempty_string(command["observation"]))
			)
		"input_action":
			var strength = command.get("strength", 1.0)
			return (
				_exact_keys(command, ["command", "action", "pressed"], ["strength"])
				and _is_nonempty_string(command["action"])
				and command["pressed"] is bool
				and _is_number(strength) and float(strength) >= 0.0 and float(strength) <= 1.0
			)
		"key_event":
			return (
				_exact_keys(command, ["command", "keycode", "pressed"], ["echo", "unicode"])
				and _is_nonnegative_integer(command["keycode"])
				and command["pressed"] is bool
				and (not command.has("echo") or command["echo"] is bool)
				and (not command.has("unicode") or _is_nonnegative_integer(command["unicode"]))
			)
		"mouse_button":
			return (
				_exact_keys(command, ["command", "button_index", "pressed", "position"], [])
				and _is_nonnegative_integer(command["button_index"])
				and command["pressed"] is bool
				and _is_vec2(command["position"])
			)
		"mouse_motion":
			return (
				_exact_keys(command, ["command", "position", "relative"], ["button_mask"])
				and _is_vec2(command["position"])
				and _is_vec2(command["relative"])
				and (not command.has("button_mask") or _is_nonnegative_integer(command["button_mask"]))
			)
		"project_command":
			return (
				_exact_keys(command, ["command", "name"], ["arguments"])
				and _is_nonempty_string(command["name"])
				and (not command.has("arguments") or command["arguments"] is Dictionary)
			)
		"checkpoint":
			return (
				_exact_keys(command, ["command", "checkpoint"], ["arguments"])
				and _is_nonempty_string(command["checkpoint"])
				and (not command.has("arguments") or command["arguments"] is Dictionary)
			)
		"capture_structure", "capture_png":
			return _exact_keys(command, ["command", "capture_id"], []) and _is_nonempty_string(command["capture_id"])
		"movie_marker":
			return _exact_keys(command, ["command", "marker"], []) and _is_nonempty_string(command["marker"])
		"shutdown":
			return _exact_keys(command, ["command"], ["exit_code"]) and (not command.has("exit_code") or _is_integer(command["exit_code"]))
	return false


func _exact_keys(value: Dictionary, required: Array, optional: Array) -> bool:
	for key in required:
		if not value.has(key):
			return false
	for key in value.keys():
		if not required.has(key) and not optional.has(key):
			return false
	return true


func _is_nonempty_string(value) -> bool:
	return value is String and not value.is_empty()


func _is_integer(value) -> bool:
	return typeof(value) == TYPE_INT or (typeof(value) == TYPE_FLOAT and float(value) == floorf(float(value)))


func _is_nonnegative_integer(value) -> bool:
	return _is_integer(value) and int(value) >= 0


func _is_number(value) -> bool:
	return typeof(value) == TYPE_INT or typeof(value) == TYPE_FLOAT


func _is_vec2(value) -> bool:
	return value is Array and value.size() == 2 and _is_number(value[0]) and _is_number(value[1])


func _is_string_array(value) -> bool:
	if not value is Array:
		return false
	var seen := {}
	for item in value:
		if not _is_nonempty_string(item) or seen.has(item):
			return false
		seen[item] = true
	return true


func _execute_queued_commands() -> void:
	var queued := _command_queue
	_command_queue = []
	for item in queued:
		var result := _execute_command(item["payload"])
		_trace("COMMAND_ACK", _command_result_trace(item["payload"], result))
		if item["network"] and _peer != null and _authenticated:
			if result.get("ok", false):
				_send_message("command_ack", item["message_id"], result)
			else:
				_send_error(item["message_id"], str(result.get("error", "command failed")))


func _execute_command(command: Dictionary) -> Dictionary:
	var kind := str(command.get("command", ""))
	_trace("COMMAND", command.duplicate(true))
	match kind:
		"input_action":
			return _input_action(command)
		"key_event":
			return _key_event(command)
		"mouse_button":
			return _mouse_button(command)
		"mouse_motion":
			return _mouse_motion(command)
		"project_command":
			return _project_command(command)
		"checkpoint":
			return _checkpoint(command)
		"snapshot":
			return _snapshot(command)
		"capture_structure":
			return _capture_structure(str(command.get("capture_id", "structure")))
		"capture_png":
			return _capture_png(str(command.get("capture_id", "capture")))
		"movie_marker":
			_trace("MOVIE_MARKER", {"marker": str(command.get("marker", ""))})
			return {"ok": true}
		"shutdown":
			_write_result("PASS", "live session requested shutdown")
			get_tree().quit(int(command.get("exit_code", 0)))
			return {"ok": true}
	return {"ok": false, "error": "command is not implemented"}


func _input_action(command: Dictionary) -> Dictionary:
	var action := str(command.get("action", ""))
	if not _profile.get("allowed_input_actions", []).has(action):
		return {"ok": false, "error": "input action is not allowlisted"}
	var pressed := bool(command.get("pressed", false))
	var strength := float(command.get("strength", 1.0))
	if pressed:
		Input.action_press(action, clampf(strength, 0.0, 1.0))
	else:
		Input.action_release(action)
	_trace("INJECTED_INPUT", {"kind": "ACTION", "action": action, "pressed": pressed, "strength": strength})
	return {"ok": true, "applied_frame": Engine.get_process_frames()}


func _key_event(command: Dictionary) -> Dictionary:
	var keycode := int(command.get("keycode", -1))
	if not _profile.get("allowed_keycodes", []).has(keycode):
		return {"ok": false, "error": "keycode is not allowlisted"}
	var event := InputEventKey.new()
	event.keycode = keycode
	event.pressed = bool(command.get("pressed", false))
	event.echo = bool(command.get("echo", false))
	event.unicode = int(command.get("unicode", 0))
	Input.parse_input_event(event)
	_trace("INJECTED_INPUT", {"kind": "KEY", "keycode": keycode, "pressed": event.pressed})
	return {"ok": true, "applied_frame": Engine.get_process_frames()}


func _mouse_button(command: Dictionary) -> Dictionary:
	var button_index := int(command.get("button_index", -1))
	if not _profile.get("allowed_mouse_buttons", []).has(button_index):
		return {"ok": false, "error": "mouse button is not allowlisted"}
	var position = command.get("position", [0, 0])
	var event := InputEventMouseButton.new()
	event.button_index = button_index
	event.pressed = bool(command.get("pressed", false))
	event.position = Vector2(float(position[0]), float(position[1]))
	Input.parse_input_event(event)
	_trace("INJECTED_INPUT", {"kind": "MOUSE_BUTTON", "button_index": button_index, "pressed": event.pressed, "position": position})
	return {"ok": true, "applied_frame": Engine.get_process_frames()}


func _mouse_motion(command: Dictionary) -> Dictionary:
	var position = command.get("position", [0, 0])
	var relative = command.get("relative", [0, 0])
	var event := InputEventMouseMotion.new()
	event.position = Vector2(float(position[0]), float(position[1]))
	event.relative = Vector2(float(relative[0]), float(relative[1]))
	event.button_mask = int(command.get("button_mask", 0))
	Input.parse_input_event(event)
	_trace("INJECTED_INPUT", {"kind": "MOUSE_MOTION", "position": position, "relative": relative, "button_mask": event.button_mask})
	return {"ok": true, "applied_frame": Engine.get_process_frames()}


func _provider() -> Node:
	var provider_name := str(_profile.get("provider_autoload", ""))
	if provider_name == "":
		return null
	return get_tree().root.get_node_or_null(NodePath("/root/" + provider_name))


func _project_command(command: Dictionary) -> Dictionary:
	var name := str(command.get("name", command.get("project_command", "")))
	if not _profile.get("project_commands", []).has(name):
		return {"ok": false, "error": "project command is not allowlisted"}
	var provider := _provider()
	if provider == null or not provider.has_method("studio_bridge_command"):
		return {"ok": false, "error": "project observation provider is unavailable"}
	var value = provider.studio_bridge_command(name, command.get("arguments", {}))
	if value is Dictionary and value.get("ok", true) == false:
		return {"ok": false, "error": str(value.get("error", "project command failed"))}
	return {"ok": true, "value": value}


func _checkpoint(command: Dictionary) -> Dictionary:
	var name := str(command.get("checkpoint", ""))
	if not _profile.get("checkpoints", []).has(name):
		return {"ok": false, "error": "checkpoint is not allowlisted"}
	var provider := _provider()
	if provider == null or not provider.has_method("studio_bridge_checkpoint"):
		return {"ok": false, "error": "project checkpoint provider is unavailable"}
	var value = provider.studio_bridge_checkpoint(name, command.get("arguments", {}))
	if value is Dictionary and value.get("ok", true) == false:
		return {"ok": false, "error": str(value.get("error", "project checkpoint failed"))}
	return {"ok": true, "value": value}


func _observation(name: String) -> Dictionary:
	match name:
		"bridge.frame":
			return {"ok": true, "value": Engine.get_process_frames()}
		"bridge.scene":
			var scene := get_tree().current_scene
			return {"ok": true, "value": scene.scene_file_path if scene != null else ""}
		"bridge.viewport":
			var rect := get_viewport().get_visible_rect()
			return {"ok": true, "value": {"width": int(rect.size.x), "height": int(rect.size.y)}}
		"bridge.input_map":
			return {"ok": true, "value": Array(InputMap.get_actions()).map(func(value): return str(value))}
	if not _profile.get("observations", []).has(name):
		return {"ok": false, "error": "observation is not allowlisted"}
	var provider := _provider()
	if provider == null or not provider.has_method("studio_bridge_observe"):
		return {"ok": false, "error": "project observation provider is unavailable"}
	return {"ok": true, "value": provider.studio_bridge_observe(name)}


func _snapshot(command: Dictionary) -> Dictionary:
	var kind := str(command.get("kind", "OBSERVABLE"))
	var snapshot_id := str(command.get("snapshot_id", "snapshot"))
	var result: Dictionary
	if kind == "MECHANICAL":
		var provider := _provider()
		if provider == null or not provider.has_method("studio_bridge_mechanical_snapshot"):
			return {"ok": false, "error": "project mechanical snapshot provider is unavailable"}
		result = {"ok": true, "value": provider.studio_bridge_mechanical_snapshot()}
	else:
		result = _observation(str(command.get("observation", "bridge.frame")))
	if result.get("ok", false):
		_trace("SNAPSHOT", {"snapshot_id": snapshot_id, "kind": kind, "value": result["value"]})
	return result


func record_project_resolved_action(action: String, payload: Dictionary = {}) -> void:
	# Project code owns this fact.  The bridge never infers a resolved gameplay
	# action from its own injected event.
	_trace("PROJECT_RESOLVED_ACTION", {"action": action, "payload": payload})


func _capture_structure(capture_id: String) -> Dictionary:
	if not _safe_id(capture_id):
		return {"ok": false, "error": "capture_id is unsafe"}
	var nodes: Array = []
	for spec in _profile.get("structural_nodes", []):
		var node := get_tree().root.get_node_or_null(NodePath(spec["node_path"]))
		var facts := {"id": spec["id"], "node_path": spec["node_path"], "exists": node != null}
		if node != null:
			for fact in spec["facts"]:
				facts[fact] = _structural_fact(node, fact)
		nodes.append(facts)
	var report := {"schema_version": "godot_structural_capture.v1", "frame": Engine.get_process_frames(), "nodes": nodes}
	var file_name := "structure_%s.json" % capture_id
	_write_json_file(_output_dir.path_join(file_name), report)
	_trace("STRUCTURE", {"capture_id": capture_id, "file": file_name})
	return {"ok": true, "file": file_name, "value": report}


func _structural_fact(node: Node, fact: String):
	match fact:
		"class": return node.get_class()
		"visible": return node.is_visible_in_tree() if node is CanvasItem else false
		"focus": return node.has_focus() if node is Control else false
		"position": return _vector(node.position) if node is Node2D or node is Control else null
		"global_position": return _vector(node.global_position) if node is Node2D or node is Control else null
		"size": return _vector(node.size) if node is Control else null
		"theme": return node.theme.resource_path if node is Control and node.theme != null else ""
		"styleboxes": return _stylebox_facts(node) if node is Control else {}
		"text": return str(node.get("text")) if node is Label or node is RichTextLabel or node is Button or node is LineEdit else ""
		"disabled": return bool(node.disabled) if node is BaseButton else false
	return null


func _stylebox_facts(control: Control) -> Dictionary:
	var output := {}
	for property in control.get_property_list():
		var name := str(property.get("name", ""))
		if not name.begins_with("theme_override_styles/"):
			continue
		var style = control.get(name)
		if style is StyleBox:
			output[name] = {"class": style.get_class(), "resource_path": style.resource_path}
	return output


func _capture_png(capture_id: String) -> Dictionary:
	if not _safe_id(capture_id):
		return {"ok": false, "error": "capture_id is unsafe"}
	var image := get_viewport().get_texture().get_image()
	if image == null or image.is_empty():
		return {"ok": false, "error": "viewport image is unavailable"}
	var file_name := "capture_%s.png" % capture_id
	var error := image.save_png(_output_dir.path_join(file_name))
	if error != OK:
		return {"ok": false, "error": error_string(error)}
	_trace("CAPTURE", {"capture_id": capture_id, "file": file_name, "width": image.get_width(), "height": image.get_height()})
	return {"ok": true, "file": file_name}


func _run_scenario_frame() -> void:
	var max_frames := int(_scenario.get("max_frames", 1))
	if Engine.get_process_frames() - _start_frame > max_frames:
		_scenario_failed = true
		_trace("ERROR", {"code": "SCENARIO_MAX_FRAMES"})
		_finish_scenario(1)
		return
	if _scenario_index >= _scenario.get("steps", []).size():
		return
	if _scenario_wait_until_frame >= 0:
		if Engine.get_process_frames() < _scenario_wait_until_frame:
			return
		_scenario_wait_until_frame = -1
		_scenario_index += 1
		return
	var step: Dictionary = _scenario["steps"][_scenario_index]
	var step_type := str(step["type"])
	if step_type == "wait_frames":
		_scenario_wait_until_frame = Engine.get_process_frames() + int(step["frames"])
		return
	if step_type == "wait_until":
		if _condition_started_frame < 0:
			_condition_started_frame = Engine.get_process_frames()
		var condition_result := _evaluate_condition(step["condition"])
		if condition_result.get("matched", false):
			_condition_started_frame = -1
			_scenario_index += 1
		elif Engine.get_process_frames() - _condition_started_frame >= int(step["deadline_frames"]):
			_scenario_failed = true
			_trace("ASSERTION", {"assertion_id": "wait_until:%d" % _scenario_index, "status": "FAIL", "actual": condition_result.get("actual"), "expected": step["condition"].get("expected"), "detail": "deadline exceeded"})
			_finish_scenario(1)
		return
	if step_type == "assert":
		var assertion := _evaluate_condition(step)
		var assertion_status := "PASS" if assertion.get("matched", false) else "FAIL"
		if assertion_status == "FAIL":
			_scenario_failed = true
		_trace("ASSERTION", {"assertion_id": step["assertion_id"], "status": assertion_status, "actual": assertion.get("actual"), "expected": step.get("expected"), "detail": "strict runtime assertion"})
		_scenario_index += 1
		return
	if step_type == "finish":
		_finish_scenario(int(step.get("exit_code", 0)))
		return
	var command := step.duplicate(true)
	command["command"] = step_type
	if step_type == "project_command":
		command["name"] = step["command"]
		command["command"] = "project_command"
	var result := _execute_command(command)
	_trace("COMMAND_ACK", _command_result_trace(command, result))
	if not result.get("ok", false):
		_scenario_failed = true
		_trace("ERROR", {"code": "SCENARIO_STEP_FAILED", "step_index": _scenario_index, "error": result.get("error", "unknown")})
		_finish_scenario(1)
		return
	_scenario_index += 1


func _evaluate_condition(condition: Dictionary) -> Dictionary:
	var observation := _observation(str(condition.get("actual", "")))
	if not observation.get("ok", false):
		return {"matched": false, "actual": null, "error": observation.get("error")}
	var actual = observation["value"]
	var expected = condition.get("expected")
	var operator := str(condition.get("operator", "eq"))
	var matched := false
	match operator:
		"eq": matched = actual == expected
		"ne": matched = actual != expected
		"gt": matched = actual > expected
		"gte": matched = actual >= expected
		"lt": matched = actual < expected
		"lte": matched = actual <= expected
		"contains": matched = expected in actual
		"exists": matched = actual != null
	return {"matched": matched, "actual": actual}


func _finish_scenario(exit_code: int) -> void:
	if _scenario_finished:
		return
	_scenario_finished = true
	var status := "FAIL" if _scenario_failed else "PASS"
	_trace("FINISH", {"status": status, "exit_code": exit_code})
	_write_result(status, "scenario finished")
	call_deferred("_quit_after_flush", exit_code if status == "PASS" else 1)


func _quit_after_flush(exit_code: int) -> void:
	get_tree().quit(exit_code)


func _write_result(status: String, detail: String) -> void:
	_write_json_file(_output_dir.path_join("bridge_result.json"), {
		"schema_version": "godot_bridge_result.v1",
		"status": status,
		"detail": detail,
		"frame": Engine.get_process_frames(),
		"scenario_id": _scenario.get("scenario_id", null),
		"seed": _scenario.get("seed", _live_seed),
		"initial_checkpoint": _scenario.get("initial_checkpoint", _live_initial_checkpoint),
		"acceptance_authority": "EVIDENCE_ONLY",
		"gameplay_verdict": "NOT_ISSUED",
	})


func _trace(kind: String, payload: Dictionary) -> void:
	if _output_dir == "":
		return
	var record := {
		"schema_version": "godot_session_trace_record.v1",
		"sequence": _sequence,
		"frame": Engine.get_process_frames(),
		"kind": kind,
		"payload": payload,
	}
	_sequence += 1
	var file := FileAccess.open(_output_dir.path_join("session_trace.jsonl"), FileAccess.READ_WRITE)
	if file == null:
		file = FileAccess.open(_output_dir.path_join("session_trace.jsonl"), FileAccess.WRITE)
	if file != null:
		file.seek_end()
		file.store_line(JSON.stringify(record))
		file.flush()


func _write_json_file(path: String, value) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(value, "  ", false) + "\n")
		file.flush()


func _send_message(type: String, message_id: String, payload: Dictionary) -> void:
	if _peer == null:
		return
	var message := {"protocol_version": PROTOCOL_VERSION, "type": type, "message_id": message_id, "payload": payload}
	var bytes := JSON.stringify(message).to_utf8_buffer()
	if bytes.size() > MAX_MESSAGE_BYTES:
		return
	_peer.put_32(bytes.size())
	_peer.put_data(bytes)


func _send_error(message_id: String, detail: String) -> void:
	_send_message("error", message_id, {"error": detail})


func _command_result_trace(command: Dictionary, result: Dictionary) -> Dictionary:
	var payload := {"command": str(command.get("command", "")), "ok": bool(result.get("ok", false))}
	for field in ["value", "applied_frame", "file", "error"]:
		if result.has(field):
			payload[field] = result[field]
	return payload


func _capabilities() -> Array:
	return [
		"FRAME_BOUND_EXECUTION", "ACTION_INPUT", "KEY_INPUT", "MOUSE_INPUT",
		"STRUCTURAL_CAPTURE", "PNG_CAPTURE", "OBSERVATION", "CHECKPOINT",
		"PROJECT_COMMAND", "LIVE_SESSION",
	]


func _safe_id(value: String) -> bool:
	if value == "":
		return false
	for character in value:
		if not (character.is_valid_identifier() or character == "-" or character == "."):
			return false
	return true


func _vector(value: Vector2) -> Array:
	return [value.x, value.y]
