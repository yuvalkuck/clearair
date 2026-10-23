#!/usr/bin/env python3
"""Turn a KiCad PCB into a 3D-printable carrier plate for PrusaSlicer.

The plate has the board outline, a hole at every pad and via, and a groove
along every track: tracks on F.Cu are cut into the top face, tracks on B.Cu
into the bottom face. Lay wires in the grooves and push pins or headers
through the holes. The result is an STL or 3MF file that PrusaSlicer opens.

The plate is seen from the top, as in KiCad: print it top face up.

It needs:
  - KiCad's Python (for the pcbnew module), e.g. with the KiCad 10 AppImage:
      ~/bin/kicad-10.0.5-x86_64.AppImage python3.11 make_carrier.py ...
  - FreeCAD 1.0 or newer, run without a window to build the solid.
  - A routed board for grooves. Use --route to route it first with
    route_board.py (Freerouting, see README), or route it yourself.

Examples:

    K="$HOME/bin/kicad-10.0.5-x86_64.AppImage python3.11"
    $K make_carrier.py board.kicad_pcb --route -o carrier.stl
    $K make_carrier.py routed.kicad_pcb -o carrier.3mf --thickness 4 --groove-width 1.5
    $K make_carrier.py board.kicad_pcb --no-grooves -o plate.stl

The board file is never changed. With --route, the routed copy is written
next to the output (carrier.routed.kicad_pcb) so you can look at it.
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

try:
    import pcbnew
except ImportError:
    sys.exit(
        "error: cannot import pcbnew. Run this script with KiCad's Python, e.g.\n"
        "  ~/bin/kicad-10.0.5-x86_64.AppImage python3.11 " + sys.argv[0] + " --help"
    )

HERE = os.path.dirname(os.path.abspath(__file__))

# Runs inside FreeCAD. Reads the JSON written by collect(), builds the solid
# and writes the mesh. KiCad's Y axis points down, so Y is flipped here.
FREECAD_SCRIPT = r'''
import json, math, os, sys
import FreeCAD, Part, MeshPart
from FreeCAD import Vector

data = json.load(open(os.environ["CARRIER_JSON"]))
T = data["thickness"]
W = data["groove_width"]
D = data["groove_depth"]

def flip(p):
    return Vector(p[0], -p[1], 0)

def prism(points, z0, height):
    pts = [flip(p) for p in points]
    if (pts[0] - pts[-1]).Length > 1e-6:
        pts.append(pts[0])
    face = Part.Face(Part.makePolygon(pts))
    return face.extrude(Vector(0, 0, height)).translate(Vector(0, 0, z0))

def stadium(a, b, width, z0, height):
    """Slot of the given width from a to b, round ends, vertical walls."""
    a, b = flip(a), flip(b)
    r = width / 2
    length = (b - a).Length
    if length < 1e-3:
        return [Part.makeCylinder(r, height, Vector(a.x, a.y, z0))]
    # One outline (two lines, two half circles), not a box plus two
    # cylinders: touching faces of separate solids mesh with open edges.
    u = (b - a) * (1.0 / length)
    n = Vector(-u.y, u.x, 0)
    p1, p2, p3, p4 = a + n * r, b + n * r, b - n * r, a - n * r
    edges = [Part.LineSegment(p1, p2).toShape(),
             Part.Arc(p2, b + u * r, p3).toShape(),
             Part.LineSegment(p3, p4).toShape(),
             Part.Arc(p4, a - u * r, p1).toShape()]
    face = Part.Face(Part.Wire(edges))
    return [face.extrude(Vector(0, 0, height)).translate(Vector(0, 0, z0))]

plate = prism(data["outline"], 0, T)
tools = [prism(c, -1, T + 2) for c in data["cutouts"]]

for h in data["holes"]:
    d = h["d"] + data["hole_clearance"]
    if h["slot"] is None:
        tools.append(Part.makeCylinder(d / 2, T + 2, flip(h["at"]) + Vector(0, 0, -1)))
    else:
        tools += stadium(h["slot"][0], h["slot"][1], d, -1, T + 2)

for s in data["tracks"]:
    if s["side"] == "top":
        tools += stadium(s["a"], s["b"], W, T - D, D + 1)
    else:
        tools += stadium(s["a"], s["b"], W, -1, D + 1)

print("carrier: %d holes, %d groove segments, %d cut tools" % (len(data["holes"]), len(data["tracks"]), len(tools)))
# Fuse the tools into one solid first: plate.cut(list) silently skips most
# of many overlapping tools. removeSplitter() merges the split faces.
solid = plate.cut(tools[0].multiFuse(tools[1:])) if tools else plate
solid = solid.removeSplitter()

# Netgen gives a closed mesh even where a groove passes very close to a
# hole. The standard mesher leaves open edges there, but is faster.
mesh = None
if data["mesher"] == "netgen":
    try:
        mesh = MeshPart.meshFromShape(Shape=solid, Fineness=2, SecondOrder=0, Optimize=0, AllowQuad=0)
    except Exception as exc:
        print("carrier: netgen failed (%s), using the standard mesher" % exc)
if mesh is None:
    mesh = MeshPart.meshFromShape(Shape=solid, LinearDeflection=data["deflection"], AngularDeflection=0.3)
mesh.write(data["output"])
print("carrier: volume %.0f of %.0f mm3 plate, %d facets, closed mesh: %s, valid solid: %s"
      % (solid.Volume, plate.Volume, mesh.CountFacets, mesh.isSolid(), solid.isValid()))
'''


def xy(v):
    return [pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)]


def chain_points(chain):
    return [xy(chain.CPoint(i)) for i in range(chain.PointCount())]


def collect(board, args):
    """Read outline, holes and tracks from the board into plain lists (mm)."""
    outlines = pcbnew.SHAPE_POLY_SET()
    if not board.GetBoardPolygonOutlines(outlines, False) or outlines.OutlineCount() == 0:
        sys.exit("error: the board has no closed Edge.Cuts outline (place_parts.py --outline draws one)")
    if outlines.OutlineCount() > 1:
        print(f"warning: the board has {outlines.OutlineCount()} outlines; only the first one is used")
    outline = chain_points(outlines.Outline(0))
    cutouts = [chain_points(outlines.Hole(0, i)) for i in range(outlines.HoleCount(0))]

    holes = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            size = pad.GetDrillSize()
            if size.x <= 0 or size.y <= 0:
                continue  # SMD pad, no hole
            at = xy(pad.GetPosition())
            if size.x == size.y:
                holes.append({"at": at, "d": pcbnew.ToMM(size.x), "slot": None})
                continue
            # Oval hole: a slot along its long side, turned with the pad.
            d = pcbnew.ToMM(min(size.x, size.y))
            half = (pcbnew.ToMM(max(size.x, size.y)) - d) / 2
            angle = math.radians(pad.GetOrientation().AsDegrees())
            if size.y > size.x:
                angle += math.pi / 2
            dx, dy = half * math.cos(angle), -half * math.sin(angle)
            holes.append({"at": at, "d": d, "slot": [[at[0] - dx, at[1] - dy], [at[0] + dx, at[1] + dy]]})

    tracks = []
    sides = {}
    for layer in args.layers:
        layer_id = board.GetLayerID(layer)
        if layer_id < 0:
            sys.exit(f"error: unknown layer {layer}")
        sides[layer_id] = "top" if layer.startswith("F.") else "bottom"
    for t in board.GetTracks():
        cls = t.GetClass()
        if cls == "PCB_VIA":
            holes.append({"at": xy(t.GetPosition()), "d": pcbnew.ToMM(t.GetDrillValue()), "slot": None})
            continue
        side = sides.get(t.GetLayer())
        if side is None:
            continue
        if cls == "PCB_ARC":
            # Two straight pieces through the arc midpoint are close enough for a groove.
            pts = [xy(t.GetStart()), xy(t.GetMid()), xy(t.GetEnd())]
            tracks += [{"a": pts[0], "b": pts[1], "side": side}, {"a": pts[1], "b": pts[2], "side": side}]
        else:
            tracks.append({"a": xy(t.GetStart()), "b": xy(t.GetEnd()), "side": side})

    if args.no_grooves:
        tracks = []
    return {"outline": outline, "cutouts": cutouts, "holes": holes, "tracks": tracks}


def find_freecad(explicit):
    """Return the command that runs a FreeCAD script without a window."""
    if explicit:
        return explicit.split()
    for name in ("freecadcmd", "FreeCADCmd"):
        path = shutil.which(name)
        if path:
            return [path]
    appimage = os.path.expanduser("~/bin/freecad")
    if os.path.exists(appimage):
        return [appimage, "freecadcmd"]  # the FreeCAD AppImage starts its CLI this way
    sys.exit("error: FreeCAD not found. Install it, or give --freecad 'PATH/FreeCAD.AppImage freecadcmd'")


def route(board_path, out_path, args):
    cmd = [sys.executable, os.path.join(HERE, "route_board.py"), board_path, "-o", out_path,
           "--clear", "--passes", str(args.passes)]
    print("routing with route_board.py ...", flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit("error: routing failed (see route_board.py output above)")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("board", help="input .kicad_pcb file")
    parser.add_argument("-o", "--output", required=True, help="output mesh, .stl or .3mf")
    parser.add_argument("--route", action="store_true", help="route the board first with route_board.py (old tracks are replaced)")
    parser.add_argument("--passes", type=int, default=30, help="autorouter passes with --route (default: 30)")
    parser.add_argument("--thickness", type=float, default=3.0, help="plate thickness in mm (default: 3.0)")
    parser.add_argument("--groove-width", type=float, default=1.2, help="groove width in mm (default: 1.2, fits 24 AWG)")
    parser.add_argument("--groove-depth", type=float, default=1.2, help="groove depth in mm (default: 1.2)")
    parser.add_argument("--hole-clearance", type=float, default=0.3,
                        help="added to every drill diameter, because printed holes shrink (default: 0.3)")
    parser.add_argument("--layers", default="F.Cu,B.Cu", help="copper layers that become grooves (default: F.Cu,B.Cu)")
    parser.add_argument("--no-grooves", action="store_true", help="plate and holes only")
    parser.add_argument("--mesher", choices=("netgen", "standard"), default="netgen",
                        help="netgen: closed mesh, slower (default); standard: faster, may leave open edges")
    parser.add_argument("--deflection", type=float, default=0.02,
                        help="standard mesher accuracy in mm, smaller = finer (default: 0.02)")
    parser.add_argument("--freecad", help="command that runs a FreeCAD script without a window "
                                          "(default: freecadcmd on PATH, else '~/bin/freecad freecadcmd')")
    parser.add_argument("--keep", metavar="DIR", help="keep the JSON, FreeCAD script and log in DIR")
    args = parser.parse_args()
    args.layers = [s.strip() for s in args.layers.split(",") if s.strip()]

    ext = os.path.splitext(args.output)[1].lower()
    if ext not in (".stl", ".3mf"):
        parser.error("output must end in .stl or .3mf")
    if args.groove_depth >= args.thickness:
        parser.error("--groove-depth must be less than --thickness")
    if not args.no_grooves and "F.Cu" in args.layers and "B.Cu" in args.layers and 2 * args.groove_depth >= args.thickness:
        print("warning: top and bottom grooves together are as deep as the plate; where they cross, the plate is cut through")

    output = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output), exist_ok=True)
    board_path = args.board
    if args.route:
        board_path = os.path.splitext(output)[0] + ".routed.kicad_pcb"
        route(args.board, board_path, args)

    board = pcbnew.LoadBoard(board_path)
    data = collect(board, args)
    if not data["tracks"] and not args.no_grooves:
        print("warning: the board has no tracks on " + ",".join(args.layers) + ", so there are no grooves (use --route)")
    data.update({
        "thickness": args.thickness, "groove_width": args.groove_width, "groove_depth": args.groove_depth,
        "hole_clearance": args.hole_clearance, "deflection": args.deflection, "mesher": args.mesher, "output": output,
    })

    workdir = args.keep or tempfile.mkdtemp(prefix="make_carrier_")
    os.makedirs(workdir, exist_ok=True)
    json_path = os.path.join(workdir, "carrier.json")
    script_path = os.path.join(workdir, "carrier_freecad.py")
    log_path = os.path.join(workdir, "freecad.log")
    with open(json_path, "w") as fh:
        json.dump(data, fh)
    with open(script_path, "w") as fh:
        fh.write(FREECAD_SCRIPT)

    if os.path.exists(output):
        os.remove(output)
    cmd = find_freecad(args.freecad) + [script_path]
    print(f"building in FreeCAD: {len(data['holes'])} holes, {len(data['tracks'])} groove segments (log: {log_path})",
          flush=True)
    with open(log_path, "w") as log:
        subprocess.run(cmd, env=dict(os.environ, CARRIER_JSON=json_path), stdout=log, stderr=subprocess.STDOUT)
    with open(log_path, errors="replace") as log:
        lines = log.read().replace("\r", "\n").splitlines()
    for line in lines:
        if line.startswith("carrier:"):
            print(line)
    if not os.path.exists(output):
        errors = [l for l in lines if "Error" in l or "Traceback" in l or "error" in l][-8:]
        sys.exit("error: FreeCAD did not write the mesh:\n  " + "\n  ".join(errors or lines[-8:]))

    xs = [p[0] for p in data["outline"]]
    ys = [p[1] for p in data["outline"]]
    print(f"plate: {max(xs) - min(xs):.1f} x {max(ys) - min(ys):.1f} x {args.thickness} mm")
    print(f"written: {output}")
    if not args.keep:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
