#!/usr/bin/env python3
"""Place the footprints of any KiCad PCB in groups, without overlaps.

KiCad has no auto-placement. This script packs footprints into rows, one
group at a time, using each footprint's courtyard (or its bounding box when
it has no courtyard). It can also draw a rectangular board outline on
Edge.Cuts around the result. It works on any .kicad_pcb file.

Two ways to choose the groups:

  --auto          Build the groups from the board's netlist. Parts that share
                  a signal net go in the same group (power nets such as GND,
                  +5V, VCC are ignored). Big parts with many pads ("hubs", for
                  example an MCU board) go in a top row of their own, so they
                  do not pull every other part into one group. Groups are then
                  packed into rows. Add --save-layout to write the result as a
                  JSON layout you can edit and re-run with --layout.

  --layout FILE   Use groups from a JSON layout file (format below).

The script needs the pcbnew Python module, so run it with the Python that
ships inside KiCad. With the KiCad 10 AppImage:

    K="$HOME/bin/kicad-10.0.5-x86_64.AppImage python3.11"
    $K place_parts.py --list board.kicad_pcb
    $K place_parts.py board.kicad_pcb --auto -n
    $K place_parts.py board.kicad_pcb --auto --save-layout layout.json -n
    $K place_parts.py board.kicad_pcb --layout layout.json --outline 2.54 --in-place

With an installed KiCad (not the AppImage), use the system python3 if it
can import pcbnew.

Close the board in KiCad before you write it in place, or KiCad overwrites
the result on its next save.

Layout file format (JSON):

    {
      "origin": [100, 100],        board top-left in mm (page coordinates)
      "grid": 2.54,                snap footprint anchors to this pitch (0 = off)
      "gap": 1.27,                 default space between parts in mm
      "groups": [
        {
          "name": "mcu",           label used in messages and --only
          "at": [0, 0],            group top-left, mm relative to origin
          "flow": "right",         "right" packs a row, "down" packs a column
          "gap": 2.54,             optional, overrides the default gap
          "rotation": 90,          optional, degrees for every part in the group
          "refs": ["A1", "R1"]     references in packing order
        }
      ]
    }

Use "R1@90" in "refs" to give one part its own rotation. A part without a
rotation gets the group rotation (0 when the group has none).
"""

import argparse
import json
import math
import re
import shutil
import sys

try:
    import pcbnew
except ImportError:
    sys.exit(
        "error: cannot import pcbnew. Run this script with KiCad's Python, e.g.\n"
        "  ~/bin/kicad-10.0.5-x86_64.AppImage python3.11 " + sys.argv[0] + " --help"
    )

DEFAULT_POWER_NETS = r"(?i)^(/)?(gnd\w*|\w*gnd|agnd|dgnd|pgnd|v(cc|dd|ss|ee|bat|in|bus)\w*|[+-]\S*|\d+v\d*|unconnected-.*)$"


def mm(value):
    return pcbnew.FromMM(value)


def to_mm(value):
    return pcbnew.ToMM(value)


def footprint_box(fp):
    """Return the courtyard box of a footprint, or its body box without text."""
    if hasattr(fp, "BuildCourtyardCaches"):
        fp.BuildCourtyardCaches()
    for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
        poly = fp.GetCourtyard(layer)
        if not poly.IsEmpty():
            return poly.BBox()
    return fp.GetBoundingBox(False)


def box_size_at(fp, rotation):
    """Return (width, height) in mm of the footprint box at a given rotation."""
    old = fp.GetOrientationDegrees()
    fp.SetOrientationDegrees(rotation)
    box = footprint_box(fp)
    fp.SetOrientationDegrees(old)
    return to_mm(box.GetWidth()), to_mm(box.GetHeight())


def snap(value, grid):
    if grid <= 0:
        return value
    step = mm(grid)
    return int(round(value / step)) * step


def snap_up_mm(value, grid):
    if grid <= 0:
        return value
    return math.ceil(value / grid - 1e-9) * grid


def parse_ref(entry, group_rotation):
    if "@" in entry:
        ref, rot = entry.split("@", 1)
        return ref, float(rot)
    return entry, group_rotation


def place_group(group, footprints, origin, grid, default_gap, dry_run):
    """Pack one group. Return the set of references it placed."""
    name = group.get("name", "?")
    flow = group.get("flow", "right")
    if flow not in ("right", "down"):
        sys.exit(f"error: group '{name}': flow must be 'right' or 'down', not '{flow}'")
    gap = mm(group.get("gap", default_gap))
    group_rotation = float(group.get("rotation", 0))
    cursor_x = origin[0] + mm(group["at"][0])
    cursor_y = origin[1] + mm(group["at"][1])
    placed = set()

    for entry in group["refs"]:
        ref, rotation = parse_ref(entry, group_rotation)
        fp = footprints.get(ref)
        if fp is None:
            print(f"warning: group '{name}': {ref} is not on the board, skipped")
            continue
        if ref in placed:
            print(f"warning: group '{name}': {ref} listed twice, skipped")
            continue

        old_pos = fp.GetPosition()
        old_rot = fp.GetOrientationDegrees()
        fp.SetOrientationDegrees(rotation)
        box = footprint_box(fp)
        # Offset from the box top-left corner to the footprint anchor.
        dx = fp.GetPosition().x - box.GetX()
        dy = fp.GetPosition().y - box.GetY()
        new_pos = pcbnew.VECTOR2I(snap(cursor_x + dx, grid), snap(cursor_y + dy, grid))
        fp.SetPosition(new_pos)

        print(
            f"{name:>12}  {ref:<6} ({to_mm(old_pos.x):8.2f}, {to_mm(old_pos.y):8.2f}) @{old_rot:6.1f}"
            f"  ->  ({to_mm(new_pos.x):8.2f}, {to_mm(new_pos.y):8.2f}) @{rotation:6.1f}"
        )

        box = footprint_box(fp)
        if flow == "right":
            cursor_x = box.GetRight() + gap
        else:
            cursor_y = box.GetBottom() + gap
        placed.add(ref)

        if dry_run:
            fp.SetOrientationDegrees(old_rot)
            fp.SetPosition(old_pos)
    return placed


def signal_nets(footprints, power_re, max_net_parts):
    """Map each signal net name to the set of references that touch it."""
    nets = {}
    for ref, fp in footprints.items():
        for pad in fp.Pads():
            name = pad.GetNetname()
            if name and not power_re.match(name):
                nets.setdefault(name, set()).add(ref)
    return {n: refs for n, refs in nets.items() if 1 < len(refs) <= max_net_parts}


def cluster_parts(footprints, hubs, nets):
    """Group non-hub parts that share signal nets. Return a list of ref lists."""
    parent = {ref: ref for ref in footprints if ref not in hubs}

    def find(ref):
        while parent[ref] != ref:
            parent[ref] = parent[parent[ref]]
            ref = parent[ref]
        return ref

    weight = {}
    for refs in nets.values():
        members = sorted(r for r in refs if r not in hubs)
        for a in members:
            for b in members:
                if a < b:
                    weight[(a, b)] = weight.get((a, b), 0) + 1
                    parent[find(a)] = find(b)

    clusters = {}
    for ref in parent:
        clusters.setdefault(find(ref), []).append(ref)

    def neighbours(ref):
        out = {}
        for (a, b), w in weight.items():
            if a == ref:
                out[b] = w
            elif b == ref:
                out[a] = w
        return out

    def area(ref):
        box = footprint_box(footprints[ref])
        return box.GetWidth() * box.GetHeight()

    ordered = []
    for members in clusters.values():
        # Start with the biggest part, then always add the remaining part with
        # the most nets shared with the parts already placed, so connected
        # parts end up next to each other in the row.
        remaining = set(members)
        start = max(remaining, key=lambda r: (area(r), r))
        order = [start]
        remaining.discard(start)
        score = dict.fromkeys(remaining, 0)
        for n, w in neighbours(start).items():
            if n in score:
                score[n] += w
        while remaining:
            nxt = max(remaining, key=lambda r: (score[r], area(r), r))
            order.append(nxt)
            remaining.discard(nxt)
            del score[nxt]
            for n, w in neighbours(nxt).items():
                if n in score:
                    score[n] += w
        ordered.append(order)
    return ordered


def auto_layout(footprints, args):
    """Build a layout dict (same format as a JSON layout file) from the netlist."""
    power_re = re.compile(args.power_nets)
    nets = signal_nets(footprints, power_re, args.max_net_parts)
    hubs = sorted(
        (ref for ref, fp in footprints.items() if len(fp.Pads()) >= args.hub_pads),
        key=lambda r: -len(footprints[r].Pads()),
    )
    clusters = cluster_parts(footprints, set(hubs), nets)

    def rotation_for(ref):
        fp = footprints[ref]
        rot = fp.GetOrientationDegrees()
        if args.no_rotate:
            return rot
        w, h = box_size_at(fp, rot)
        # Stand long thin two- or three-pin parts (axial resistors, diodes) up
        # so rows stay short. Modules and connectors keep their rotation.
        if w > 2 * h and len(fp.Pads()) <= 3:
            rot = (rot + 90) % 360
        return rot

    def block(refs, gap):
        parts = []
        width = 0.0
        height = 0.0
        for ref in refs:
            rot = rotation_for(ref)
            w, h = box_size_at(footprints[ref], rot)
            parts.append(f"{ref}@{rot:g}")
            width += w + args.grid  # allow for anchor snapping
            height = max(height, h + args.grid)
        width += gap * (len(refs) - 1)
        return {"refs": parts, "w": width, "h": height}

    blocks = []
    if hubs:
        blocks.append(dict(block(hubs, args.group_gap), name="hubs", gap=args.group_gap))
    for refs in sorted(clusters, key=lambda c: (-len(c), c[0])):
        name = refs[0] if len(refs) > 1 else "single"
        blocks.append(dict(block(refs, args.gap), name=name, gap=args.gap))

    # Pack lone parts into shared rows instead of one group each.
    singles = [b for b in blocks if b["name"] == "single"]
    blocks = [b for b in blocks if b["name"] != "single"]
    if singles:
        refs = [r.split("@")[0] for b in singles for r in b["refs"]]
        blocks.append(dict(block(refs, args.gap), name="misc", gap=args.gap))

    total_area = sum(b["w"] * b["h"] for b in blocks)
    width = args.width or max(
        max((b["w"] for b in blocks if b["name"] == "hubs"), default=0),
        math.sqrt(total_area * args.aspect),
    )

    # Split any block wider than the board into several groups, one per row.
    split = []
    for b in blocks:
        if b["w"] <= width or len(b["refs"]) == 1:
            split.append(b)
            continue
        chunk = []
        for entry in b["refs"]:
            trial = block([r.split("@")[0] for r in chunk + [entry]], b["gap"])
            if chunk and trial["w"] > width:
                part = block([r.split("@")[0] for r in chunk], b["gap"])
                split.append(dict(part, name=f"{b['name']}.{len(split)}", gap=b["gap"]))
                chunk = []
            chunk.append(entry)
        part = block([r.split("@")[0] for r in chunk], b["gap"])
        split.append(dict(part, name=f"{b['name']}.{len(split)}", gap=b["gap"]))

    # Shelf packing: hubs first, then taller groups first.
    hub_blocks = [b for b in split if b["name"].startswith("hubs")]
    rest = sorted((b for b in split if not b["name"].startswith("hubs")), key=lambda b: (-b["h"], -b["w"]))
    groups = []
    x = y = row_h = 0.0
    for b in hub_blocks + rest:
        if x > 0 and x + b["w"] > width:
            x = 0.0
            y = snap_up_mm(y + row_h + args.group_gap, args.grid)
            row_h = 0.0
        groups.append({"name": b["name"], "at": [round(x, 3), round(y, 3)], "flow": "right", "gap": b["gap"], "refs": b["refs"]})
        x = snap_up_mm(x + b["w"] + args.group_gap, args.grid)
        row_h = max(row_h, b["h"])
        if b["name"].startswith("hubs"):
            # Keep the hub row on its own so the rest starts below it.
            x = width + 1

    return {"origin": args.origin, "grid": args.grid, "gap": args.gap, "groups": groups}


def board_extent(footprints):
    box = None
    for fp in footprints:
        fb = footprint_box(fp)
        if box is None:
            box = pcbnew.BOX2I(fb.GetPosition(), fb.GetSize())
        else:
            box.Merge(fb)
    return box


def draw_outline(board, footprints, margin, replace):
    edges = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    if edges and not replace:
        print(
            f"warning: board already has {len(edges)} Edge.Cuts item(s); outline not drawn "
            "(use --replace-outline to delete them and draw a new one)"
        )
        return
    for item in edges:
        board.Remove(item)

    box = board_extent(footprints)
    box.Inflate(mm(margin))
    rect = pcbnew.PCB_SHAPE(board)
    rect.SetShape(pcbnew.SHAPE_T_RECT)
    rect.SetLayer(pcbnew.Edge_Cuts)
    rect.SetWidth(mm(0.1))
    rect.SetStart(box.GetPosition())
    rect.SetEnd(box.GetEnd())
    board.Add(rect)
    print(f"outline: {to_mm(box.GetWidth()):.2f} x {to_mm(box.GetHeight()):.2f} mm (margin {margin} mm)")


def list_footprints(board):
    print(f"{'ref':<6} {'w mm':>6} {'h mm':>6} {'rot':>6} {'x mm':>9} {'y mm':>9} {'pads':>4}  nets")
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        box = footprint_box(fp)
        pos = fp.GetPosition()
        nets = sorted(
            {p.GetNetname() for p in fp.Pads() if p.GetNetname() and not p.GetNetname().startswith("unconnected")}
        )
        print(
            f"{fp.GetReference():<6} {to_mm(box.GetWidth()):6.1f} {to_mm(box.GetHeight()):6.1f}"
            f" {fp.GetOrientationDegrees():6.1f} {to_mm(pos.x):9.2f} {to_mm(pos.y):9.2f} {len(fp.Pads()):4}"
            f"  {' '.join(nets)}"
        )


def main():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("board", help="input .kicad_pcb file")

    mode = parser.add_argument_group("what to place")
    mode.add_argument("-l", "--layout", help="JSON layout file (see format below)")
    mode.add_argument("-a", "--auto", action="store_true", help="build the groups from the netlist")
    mode.add_argument("--list", action="store_true", help="list footprints with size, position, pads and nets, then exit")
    mode.add_argument("--only", action="append", metavar="GROUP", help="place only this group (repeatable)")

    out = parser.add_argument_group("output")
    out.add_argument("-o", "--output", help="write the result to this .kicad_pcb file")
    out.add_argument("-i", "--in-place", action="store_true", help="overwrite the input board (a .bak copy is kept)")
    out.add_argument("-n", "--dry-run", action="store_true", help="print the moves, change nothing")
    out.add_argument("--save-layout", metavar="FILE", help="write the layout used (e.g. from --auto) to a JSON file")
    out.add_argument("--outline", type=float, metavar="MARGIN_MM", help="draw an Edge.Cuts rectangle around all parts")
    out.add_argument("--replace-outline", action="store_true", help="delete existing Edge.Cuts items before --outline")

    auto = parser.add_argument_group("--auto options")
    auto.add_argument("--origin", type=float, nargs=2, default=[50.0, 50.0], metavar=("X", "Y"),
                      help="board top-left in mm (default: 50 50)")
    auto.add_argument("--grid", type=float, default=2.54, help="snap pitch in mm, 0 = off (default: 2.54)")
    auto.add_argument("--gap", type=float, default=1.27, help="space between parts in mm (default: 1.27)")
    auto.add_argument("--group-gap", type=float, default=2.54, help="space between groups in mm (default: 2.54)")
    auto.add_argument("--width", type=float, help="target board width in mm (default: from total part area)")
    auto.add_argument("--aspect", type=float, default=1.6, help="width/height ratio when --width is not given (default: 1.6)")
    auto.add_argument("--hub-pads", type=int, default=16,
                      help="parts with at least this many pads go in the hub row (default: 16)")
    auto.add_argument("--max-net-parts", type=int, default=8,
                      help="ignore nets that touch more parts than this, e.g. buses (default: 8)")
    auto.add_argument("--power-nets", default=DEFAULT_POWER_NETS, metavar="REGEX",
                      help="regex of net names ignored for grouping (default matches GND, VCC, VDD, +5V, 3V3, ...)")
    auto.add_argument("--no-rotate", action="store_true", help="keep each part's rotation (default stands long 2-3 pin parts up)")
    args = parser.parse_args()

    board = pcbnew.LoadBoard(args.board)
    if args.list:
        list_footprints(board)
        return

    if args.layout and args.auto:
        parser.error("--layout and --auto cannot be used together")
    if not args.layout and not args.auto and args.outline is None:
        parser.error("give --auto, --layout and/or --outline (or --list)")
    if not args.dry_run and not args.output and not args.in_place and not (args.save_layout and not args.outline):
        parser.error("give -o OUTPUT, --in-place, or --dry-run")
    if args.output and args.in_place:
        parser.error("-o and --in-place cannot be used together")
    if args.save_layout and not args.output and not args.in_place:
        args.dry_run = True

    all_footprints = list(board.GetFootprints())
    footprints = {}
    duplicates = set()
    for fp in all_footprints:
        ref = fp.GetReference()
        if ref in footprints:
            duplicates.add(ref)
        footprints[ref] = fp
    for ref in sorted(duplicates):
        # A reference must name one part; parts that share one stay where they are.
        print(f"warning: reference {ref} is used by more than one footprint; those parts are not moved")
        del footprints[ref]
    layout = None
    if args.layout:
        with open(args.layout) as fh:
            layout = json.load(fh)
    elif args.auto:
        layout = auto_layout(footprints, args)

    if layout is not None:
        if args.save_layout:
            with open(args.save_layout, "w") as fh:
                json.dump(layout, fh, indent=2)
                fh.write("\n")
            print(f"layout: {args.save_layout}")
        origin = (mm(layout.get("origin", [0, 0])[0]), mm(layout.get("origin", [0, 0])[1]))
        grid = float(layout.get("grid", 0))
        default_gap = float(layout.get("gap", 1.27))
        placed = set()
        groups = layout["groups"]
        if args.only:
            unknown = set(args.only) - {g.get("name") for g in groups}
            if unknown:
                parser.error(f"unknown group(s): {', '.join(sorted(unknown))}")
            groups = [g for g in groups if g.get("name") in args.only]
        for group in groups:
            placed |= place_group(group, footprints, origin, grid, default_gap, args.dry_run)
        if not args.only:
            missing = sorted(set(footprints) - placed)
            if missing:
                print(f"warning: not in any group, left where they were: {' '.join(missing)}")

    if args.outline is not None:
        if args.dry_run:
            box = board_extent(all_footprints)
            box.Inflate(mm(args.outline))
            print(f"outline (dry run, current positions): {to_mm(box.GetWidth()):.2f} x {to_mm(box.GetHeight()):.2f} mm")
        else:
            draw_outline(board, all_footprints, args.outline, args.replace_outline)

    if args.dry_run:
        print("dry run: nothing written")
        return
    if not args.output and not args.in_place:
        return

    target = args.board if args.in_place else args.output
    if args.in_place:
        shutil.copy2(args.board, args.board + ".bak")
        print(f"backup: {args.board}.bak")
    board.Save(target)
    print(f"written: {target}")


if __name__ == "__main__":
    main()
