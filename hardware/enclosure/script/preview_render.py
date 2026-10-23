# Draws the meshes written by preview_sensor_tube.py into preview_<view>.png (needs Pillow).
import json
import math
import os
import sys
from PIL import Image, ImageDraw

src = sys.argv[1]
out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(src))
meshes = json.load(open(src))

# name: (direction from the part towards the camera, up vector). Air flows along +X.
VIEWS = {
    "inlet_iso": ((-1.0, -1.0, 0.8), (0, 0, 1)),
    "outlet_iso": ((1.0, 1.0, 0.8), (0, 0, 1)),
    "side": ((0, -1, 0), (0, 0, 1)),
    "top": ((0, 0, 1), (0, 1, 0)),
}
W, H, PAD = 1400, 700, 30


def norm(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


for name, (direction, up) in VIEWS.items():
    d = norm(direction)
    right = norm(cross(up, d))
    upv = cross(d, right)
    light = norm((d[0] + 0.4 * right[0] + 0.6 * upv[0], d[1] + 0.4 * right[1] + 0.6 * upv[1], d[2] + 0.4 * right[2] + 0.6 * upv[2]))
    tris = []
    for m in meshes:
        pts = m["verts"]
        for a, b, c in m["tris"]:
            pa, pb, pc = pts[a], pts[b], pts[c]
            n = norm(cross([pb[i] - pa[i] for i in range(3)], [pc[i] - pa[i] for i in range(3)])) if True else None
            shade = 0.35 + 0.65 * abs(dot(n, light))
            depth = (dot(pa, d) + dot(pb, d) + dot(pc, d)) / 3
            tris.append((depth, [(dot(p, right), dot(p, upv)) for p in (pa, pb, pc)], m["color"], shade, m["name"].startswith("REF_")))
    xs = [p[0] for t in tris for p in t[1]]
    ys = [p[1] for t in tris for p in t[1]]
    scale = min((W - 2 * PAD) / (max(xs) - min(xs)), (H - 2 * PAD) / (max(ys) - min(ys)))
    img = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(img)
    tris.sort(key=lambda t: t[0])  # far to near
    for depth, poly, color, shade, is_ref in tris:
        pts = [(PAD + (p[0] - min(xs)) * scale, H - PAD - (p[1] - min(ys)) * scale) for p in poly]
        fill = tuple(int(c * shade) for c in color)
        dr.polygon(pts, fill=fill, outline=fill)
    dr.text((10, 8), "%s  (orange adapter, blue tube, grey = reference parts)  %.2f px/mm" % (name, scale), fill=(200, 0, 0))
    img.save(os.path.join(out_dir, "preview_%s.png" % name))
    print("wrote preview_%s.png" % name)
