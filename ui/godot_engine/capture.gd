extends RefCounted
## Await from an isolated game-owned runner, never from the shipped main scene.
## This exports raw rendering observations, NOT a semantic or comprehension PASS.
## Optional metadata: ui_element_id, ui_fact_ids, ui_overlay_group.
## Custom drawing requires a game-owned exporter extension; never invent samples.


static func sample(root: Node, image_path: String, frame_id: int, time_ms: float,
		overlays_complete: bool = false) -> Dictionary:
	await RenderingServer.frame_post_draw
	var image: Image = root.get_viewport().get_texture().get_image()
	if image == null or image.is_empty():
		push_error("UI capture has no rendered frame (headless dummy rendering is not evidence)")
		return {}
	var error: Error = image.save_png(ProjectSettings.globalize_path("res://" + image_path))
	if error != OK:
		push_error("Could not save UI capture: " + str(error))
		return {}
	var elements: Array[Dictionary] = []
	if not _collect(root, root, elements):
		push_error("UI observation export failed; do not seal a partial inventory")
		return {}
	return {"frame_id": frame_id, "time_ms": time_ms, "image_path": image_path,
		"elements": elements, "overlays_complete": overlays_complete}


static func _collect(node: Node, root: Node, output: Array[Dictionary]) -> bool:
	if node is Control or node is Line2D:
		var item: CanvasItem = node as CanvasItem
		var points: Array = []
		var rectangle: Rect2
		var transform: Transform2D = item.get_global_transform_with_canvas()
		if node is Control:
			var control: Control = node as Control
			var corners: Array[Vector2] = [Vector2.ZERO, Vector2(control.size.x, 0), control.size, Vector2(0, control.size.y)]
			rectangle = Rect2(transform * corners[0], Vector2.ZERO)
			for corner in corners:
				rectangle = rectangle.expand(transform * corner)
		else:
			var line: Line2D = node as Line2D
			for point in line.points:
				var absolute: Vector2 = transform * point
				points.append([absolute.x, absolute.y])
				if points.size() == 1:
					rectangle = Rect2(absolute, Vector2.ZERO)
				else:
					rectangle = rectangle.expand(absolute)
		var effective: Color = item.self_modulate
		var ancestor: CanvasItem = item
		while ancestor != null:
			effective *= ancestor.modulate
			ancestor = ancestor.get_parent() as CanvasItem
		var draw_color: Variant = null
		if node is ColorRect:
			draw_color = (node as ColorRect).color * effective
		elif node is Line2D:
			draw_color = (node as Line2D).default_color * effective
		elif node is Label:
			draw_color = (node as Label).get_theme_color("font_color") * effective
		var color_array: Variant = null
		if draw_color is Color:
			color_array = [draw_color.r, draw_color.g, draw_color.b, draw_color.a]
		var enabled: bool = not (node as BaseButton).disabled if node is BaseButton else true
		output.append({"element_id": str(node.get_meta("ui_element_id", str(root.get_path_to(node)))),
			"bounds": [rectangle.position.x, rectangle.position.y, rectangle.size.x, rectangle.size.y],
			"visible": item.is_visible_in_tree() and effective.a > 0, "enabled": enabled,
			"fact_ids": Array(node.get_meta("ui_fact_ids", [])), "color": color_array,
			"points": points, "overlay_group": node.get_meta("ui_overlay_group", null)})
	for child in node.get_children():
		if not _collect(child, root, output):
			return false
	return true
