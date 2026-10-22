# Enclosure scripts

These scripts were written by Claude (Anthropic's AI) as the starting point for the FreeCAD design of the enclosure. Claude wrote them from human instructions: the user gave the requirements and measurements, and Claude turned them into FreeCAD Python.

- `build_sensor_tube.py` builds `../sensor_tube.FCStd`, the baseline model. Run it with `freecad -c hardware/enclosure/script/build_sensor_tube.py </dev/null`. Close stdin with `</dev/null`: on a script error FreeCAD otherwise waits at its console and the run hangs silently. The script overwrites the `.FCStd`, so use it only to regenerate the baseline and do further design work in the `.FCStd`.
- `preview_sensor_tube.py` and `preview_render.py` render PNG previews of the model without the FreeCAD GUI.

## Known limits

- The model was checked headless only (valid solids, no overlaps, screw holes present). It has not been reviewed in the FreeCAD GUI or test printed.
- The fan mount is a flat plate with no sleeve, so the tube and the adapter cone are glued by a butt joint over a 2 mm wall. The glue area is small and may be weak.
- `preview_sensor_tube.py` does not draw the three `FanMount` parts, so the previews show no plates.
- `plate_size` and `x_plate_a` still say "adapter flange" in their notes, and `mq_boss_d` is unused.
