extends SceneTree


func _init() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 4:
		printerr("image_metrics.gd requires baseline, actual, diff, and report paths")
		quit(2)
		return
	var baseline := Image.load_from_file(args[0])
	var actual := Image.load_from_file(args[1])
	if baseline == null or baseline.is_empty() or actual == null or actual.is_empty():
		_write_report(args[3], {"status": "FAIL", "error": "image load failed"})
		quit(2)
		return
	if baseline.get_width() != actual.get_width() or baseline.get_height() != actual.get_height():
		_write_report(args[3], {
			"status": "FAIL",
			"error": "image dimensions differ",
			"baseline_size": [baseline.get_width(), baseline.get_height()],
			"actual_size": [actual.get_width(), actual.get_height()],
		})
		quit(1)
		return
	baseline.convert(Image.FORMAT_RGBA8)
	actual.convert(Image.FORMAT_RGBA8)
	var metrics := baseline.compute_image_metrics(actual, false)
	var width := baseline.get_width()
	var height := baseline.get_height()
	var diff := Image.create_empty(width, height, false, Image.FORMAT_RGBA8)
	var changed := 0
	var min_x := width
	var min_y := height
	var max_x := -1
	var max_y := -1
	for y in range(height):
		for x in range(width):
			var before := baseline.get_pixel(x, y)
			var after := actual.get_pixel(x, y)
			var delta := Color(absf(before.r - after.r), absf(before.g - after.g), absf(before.b - after.b), absf(before.a - after.a))
			diff.set_pixel(x, y, Color(delta.r, delta.g, delta.b, 1.0))
			if delta.r > 0.0 or delta.g > 0.0 or delta.b > 0.0 or delta.a > 0.0:
				changed += 1
				min_x = mini(min_x, x)
				min_y = mini(min_y, y)
				max_x = maxi(max_x, x)
				max_y = maxi(max_y, y)
	var save_error := diff.save_png(args[2])
	if save_error != OK:
		_write_report(args[3], {"status": "FAIL", "error": error_string(save_error)})
		quit(2)
		return
	metrics["rmse"] = metrics["root_mean_squared"]
	metrics["psnr"] = metrics["peak_snr"]
	metrics["changed_pixel_ratio"] = float(changed) / float(width * height)
	var bbox = null if changed == 0 else [min_x, min_y, max_x, max_y]
	_write_report(args[3], {
		"status": "PASS",
		"metrics": metrics,
		"changed_pixel_count": changed,
		"changed_bbox": bbox,
		"width": width,
		"height": height,
	})
	quit(0)


func _write_report(path: String, payload: Dictionary) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(payload, "  ", false) + "\n")
		file.flush()
