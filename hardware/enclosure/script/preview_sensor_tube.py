# Renders shaded previews of sensor_tube.FCStd to PNG without the FreeCAD GUI.
#   freecad -c hardware/enclosure/script/preview_sensor_tube.py
# FreeCAD tessellates the solids and dumps them as JSON, then preview_render.py
# (system Python with Pillow) draws the triangles. Printed parts are coloured, reference bodies grey.
import json
import os
import subprocess
import FreeCAD as App

HERE = os.path.dirname(os.path.abspath(__file__))
ENCLOSURE = os.path.dirname(HERE)  # the model and the PNGs live one directory up
doc = App.openDocument(os.path.join(ENCLOSURE, "sensor_tube.FCStd"))
doc.recompute()
COLORS = {"FilterAdapter": (230, 150, 60), "SensorTube": (70, 140, 220)}

meshes = []
for o in doc.Objects:
    if o.Name in COLORS:
        color = COLORS[o.Name]
    elif o.Name.startswith("REF_"):
        color = (170, 170, 170)
    else:
        continue
    verts, tris = o.Shape.tessellate(0.5)
    meshes.append({"name": o.Name, "color": color,
                   "verts": [(v.x, v.y, v.z) for v in verts], "tris": [list(t) for t in tris]})
dump = os.path.join(HERE, "_preview.json")
with open(dump, "w") as f:
    json.dump(meshes, f)
subprocess.run(["python3", "-I", os.path.join(HERE, "preview_render.py"), dump, ENCLOSURE], check=True)
os.remove(dump)
