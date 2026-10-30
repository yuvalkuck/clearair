#!/usr/bin/env python3
"""Check a perfboard wiring file against the KiCad board and schematic it came from.

    python3 perfboard_verify.py BOARD.kicad_pcb [WIRING.md] [--sch FILE] [--kicad-cli CMD] [--mcu REF] [--max-per-hole N]

BOARD.kicad_pcb  the board with one Edge.Cuts rectangle per perfboard
WIRING.md        written by perfboard_wire_list.py (default: perfboard_wiring.md next to the board)
--sch FILE       schematic to compare the nets with (default: the .kicad_sch next to the board)
--kicad-cli CMD  command that runs kicad-cli, for the schematic netlist (default: kicad-cli on PATH).
                 Without kicad-cli the net comparison is skipped.
--mcu REF        part whose pins of one net are joined inside the module, so they need no wire
                 (default: the part with the most pads)

It uses only the Python standard library, so plain python3 is enough. It does not run KiCad's Python.
Checks, each independent of the numbers in perfboard_wire_list.py:
  1. every through-hole pad is inside exactly one board, on its 2.54 mm grid
  2. no two pads share a hole
  3. the back-side holes in the check list (section 3) match the pad positions,
     named column letter + row, A18 at the top right of the component side, a portrait board turned 90 deg clockwise
  4. the top-view holes (section 1) match the check list
  5. the board nets equal the schematic nets
  6. the wire table joins every net and never joins two nets
  7. no hole has more than --max-per-hole wire ends (default 3)

Exit code 0 when all checks pass, 1 when any fails.
"""
import argparse, collections, math, os, re, shlex, subprocess, sys, tempfile

GRID = 2.54


def cname(c):
    """Column letter: 1 = A ... 24 = X, 27 = AA."""
    s = ''
    while c:
        c, m = divmod(c - 1, 26)
        s = chr(65 + m) + s
    return s


def cnum(s):
    n = 0
    for ch in s:
        n = n * 26 + ord(ch) - 64
    return n


def load_board(path):
    text = open(path).read()
    rects = [tuple(map(float, m)) for m in re.findall(
        r'\(gr_rect\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)(?:(?!gr_rect).)*?"Edge.Cuts"', text, re.S)]
    pads = collections.defaultdict(list)       # ref -> [(number, x, y)]
    nets = collections.defaultdict(set)        # net name -> {"REF.number"}
    for fp in re.split(r'\n\t\(footprint ', text)[1:]:
        m = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', fp)
        x0, y0, a = float(m[1]), float(m[2]), math.radians(float(m[3] or 0))
        ref = re.search(r'"Reference"\s+"([^"]*)"', fp)[1]
        if re.search(r'\(attr [^)]*\bboard_only\b', fp):
            continue                           # board-only footprints (bus strips) are not parts: the wire tables list their holes
        for blk in re.split(r'\n\t\t\(pad ', fp)[1:]:
            h = re.match(r'"([^"]*)" thru_hole', blk)
            if not h:
                continue
            at = re.search(r'\(at ([-\d.]+) ([-\d.]+)', blk)
            px, py = float(at[1]), float(at[2])
            pads[ref].append((h[1], x0 + px * math.cos(a) + py * math.sin(a), y0 - px * math.sin(a) + py * math.cos(a)))
            n = re.search(r'\(net "([^"]*)"', blk)
            if n:
                nets[n[1]].add(f'{ref}.{h[1]}')
    return rects, pads, nets


def schematic_nets(sch, kicad_cli):
    """Return the set of frozenset({"REF.pin"}) per net, or None if kicad-cli is missing."""
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, 'n.net')
        try:
            subprocess.run(shlex.split(kicad_cli) + ['sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', out, sch],
                           capture_output=True, check=True)
        except (OSError, subprocess.CalledProcessError):
            return None
        text = open(out).read()
    nets = set()
    for blk in re.split(r'\n\t\t\(net\n', text[text.index('\t(nets'):])[1:]:
        nets.add(frozenset(f'{r}.{p}' for r, p in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk)))
    return nets


def mcu_ref(sch, pads):
    return max(pads, key=lambda r: len(pads[r]))      # the MCU module: the part with the most pads


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('board')
    ap.add_argument('wiring', nargs='?')
    ap.add_argument('--sch')
    ap.add_argument('--kicad-cli', default='kicad-cli')
    ap.add_argument('--mcu')
    ap.add_argument('--max-per-hole', type=int, default=3)
    args = ap.parse_args()
    base = os.path.splitext(args.board)[0]
    wiring = args.wiring or os.path.join(os.path.dirname(os.path.abspath(args.board)), 'perfboard_wiring.md')
    sch = args.sch or base + '.kicad_sch'
    md = open(wiring).read()

    errors = []
    def bad(*what):
        errors.append(' '.join(map(str, what)))
        print('  ERROR', *what)

    rects, pads, nets = load_board(args.board)
    dims = [(round((r[2] - r[0]) / GRID) + 1, round((r[3] - r[1]) / GRID) + 1) for r in rects]
    print('boards (columns x rows in the PCB):', dims)
    if not rects:
        bad('no Edge.Cuts rectangle: nothing to check')
        sys.exit(1)

    # 1 + 2: pads inside one board, on the grid, one pad per hole
    holes = collections.defaultdict(list)
    placed = collections.defaultdict(list)     # ref -> [(number, board index, x, y)]
    for ref, ps in pads.items():
        for num, x, y in ps:
            inside = [i for i, r in enumerate(rects) if r[0] - .01 <= x <= r[2] + .01 and r[1] - .01 <= y <= r[3] + .01]
            if len(inside) != 1:
                bad('pad in', len(inside), 'boards:', f'{ref}.{num}')
                continue
            l, tp = rects[inside[0]][:2]
            if abs((x - l) / GRID - round((x - l) / GRID)) > .01 or abs((y - tp) / GRID - round((y - tp) / GRID)) > .01:
                bad('pad off the grid:', f'{ref}.{num}')
            placed[ref].append((num, inside[0], x, y))
            holes[(inside[0], round(x / .1), round(y / .1))].append(f'{ref}.{num}')
    for pads_in_hole in holes.values():
        if len(pads_in_hole) > 1:
            bad('pads share a hole:', pads_in_hole)
    print(f'1-2. {sum(map(len, placed.values()))} pads on {len(placed)} parts: in a board, on the grid, one per hole')

    # 3: check list (section 3) against the pad positions
    expected = collections.defaultdict(collections.Counter)
    for ref, ps in placed.items():
        for num, b, x, y in ps:
            l, tp = rects[b][:2]
            W, H = dims[b]
            c, r = round((x - l) / GRID) + 1, round((y - tp) / GRID) + 1
            if H > W:
                c, r = H + 1 - r, c                       # portrait board shown turned 90 deg clockwise
            nc, nr = (H, W) if H > W else (W, H)
            expected[ref][(num, b + 1, nc + 1 - c, nr + 1 - r)] += 1   # A18 is top right of the component side; same name from both sides
    listed = {}
    sec3 = md[md.index('## 3.'):]
    for ref, body in re.findall(r'^\*\*(\w+)\*\*[^\n]*\n\n\| Pin[^\n]*\n\|[-|]*\n((?:\|[^\n]*\n)+)', sec3, re.M):
        listed[ref] = collections.Counter((row[0], int(row[3][1]), cnum(re.match(r'B\d:([A-Z]+)', row[3])[1]), int(re.match(r'B\d:[A-Z]+(\d+)', row[3])[1]))
                                          for row in ([x.strip() for x in line.strip().strip('|').split('|')] for line in body.splitlines()))
        if not ref.startswith('BUS') and listed[ref] != expected[ref]:
            bad('check-list holes differ from the board:', ref, sorted(set(listed[ref]) ^ set(expected[ref])))
    listed = {r: v for r, v in listed.items() if not r.startswith('BUS')}
    if set(listed) != set(placed):
        bad('parts missing from the check list or the board:', sorted(set(listed) ^ set(placed)))
    print('3.   check list matches the pad positions')

    # 4: top view (section 1) against the back holes
    holes_of = collections.defaultdict(set)
    for ref, c in expected.items():
        for num, b, col, row in c:
            holes_of[(ref, b)].add((col, row))
    cur = None
    buses = {}                                   # BUSn -> (board, row, first column, last column)
    for line in md[md.index('## 1.'):md.index('## 2.')].splitlines():
        m = re.match(r'### Board (\d)', line)
        if m:
            cur = int(m[1]); continue
        m = re.match(r'\| (\w+) \| .*? \| (.*) \|$', line)
        if not m or m[1] == 'Part' or cur is None:
            continue
        if m[1].startswith('BUS'):
            a = re.fullmatch(r'([A-Z]+)(\d+) to ([A-Z]+)(\d+)', m[2].strip())
            if not a or a[2] != a[4]:
                bad('bus is not one row of holes:', m[1], m[2]); continue
            c1, c2 = sorted((cnum(a[1]), cnum(a[3])))
            buses[m[1]] = (cur, int(a[2]), c1, c2)
            continue
        pts = {(cnum(a), int(b)) for a, b in re.findall(r'(?<![\w#.:])([A-Z]{1,2})(\d+)(?![\w.])', re.sub(r'=\S+', '', m[2]))}
        if not pts <= holes_of[(m[1], cur)]:
            bad('top-view hole not on the part:', m[1], sorted(pts - holes_of[(m[1], cur)]))
        if ' to ' not in m[2] and ',' in m[2] and pts != holes_of[(m[1], cur)]:
            bad('top-view holes differ from the part:', m[1])
    all_holes = {(b, c, r) for c0 in expected.values() for (_, b, c, r) in c0}
    for ref, (b, r, c1, c2) in buses.items():
        nc, nr = (dims[b - 1][1], dims[b - 1][0]) if dims[b - 1][1] > dims[b - 1][0] else dims[b - 1]
        if not (1 <= c1 and c2 <= nc and 1 <= r <= nr):
            bad('bus outside the board:', ref)
        for c in range(c1, c2 + 1):
            if (b, c, r) in all_holes:
                bad('bus hole is used by a part:', ref, f'{cname(c)}{r}')
    print(f'4.   top view matches the check list ({len(buses)} bus strips on free holes)')

    # 5: board nets against the schematic
    pcb_nets = {frozenset(v) for v in nets.values() if len(v) > 1}
    sch_nets = schematic_nets(sch, args.kicad_cli) if os.path.exists(sch) else None
    if sch_nets is None:
        print('5.   skipped: no schematic or no kicad-cli')
    else:
        on_board = {f'{r}.{n}' for r, ps in pads.items() for n, *_ in ps}
        sch_set = {k for k in (frozenset(n for n in net if n in on_board) for net in sch_nets) if len(k) > 1}
        for k in sch_set ^ pcb_nets:
            bad('net differs between schematic and board:', sorted(k))
        print(f'5.   {len(sch_set)} schematic nets, {len(pcb_nets)} board nets')

    # 6: wires join every net and never two nets
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    rows = []                                    # (board of the table or None, cells)
    seen_bus_rows = set()
    section = None
    for line in md[md.index('## 2.'):md.index('## 3.')].splitlines():
        m = re.match(r'### Wires on board (\d)', line)
        if m:
            section = int(m[1]); continue
        if line.startswith('### Wires between'):
            section = None; continue
        if re.match(r'\| #\d+ \|', line):
            rows.append((section, [x.strip() for x in line.strip('|').split('|')]))
    for line in md[md.index('## 2.'):md.index('## 3.')].splitlines():     # the bare wire of a strip runs from its first to its last hole
        m = re.match(r'\| (BUS\d+) \| [^|]*\| [^|]*\| [^|]*\| ([A-Z]+\d+) \| ([A-Z]+\d+) \|', line)
        if m:
            seen_bus_rows.add(m[1])
            bb = buses.get(m[1])
            ends = sorted((cnum(re.match(r'[A-Z]+', h)[0]), int(re.search(r'\d+$', h)[0])) for h in (m[2], m[3]))
            if not bb or ends != [(bb[2], bb[1]), (bb[3], bb[1])]:
                bad('bus wire row does not match its strip:', m[1])
    for ref in buses:
        if ref not in seen_bus_rows:
            bad('bus strip has no bare-wire row in the wire tables:', ref)
    for section, c in rows:
        parent[find(re.sub(r'@.*', '', c[6]))] = find(re.sub(r'@.*', '', c[7]))
        for hole, pin in ((c[4], c[6]), (c[5], c[7])):
            if pin.startswith('BUS'):
                parent[find(pin)] = find(pin.split('.')[0])          # all holes of one strip are one conductor
                b, cell = (int(hole[1]), hole[3:]) if ':' in hole else (section, hole)
                col, row = cnum(re.match(r'[A-Z]+', cell)[0]), int(re.search(r'\d+$', cell)[0])
                bb = buses.get(pin.split('.')[0])
                if not bb or bb[0] != b or bb[1] != row or not bb[2] <= col <= bb[3]:
                    bad('bus wire not on its strip:', pin, hole)
    mcu = args.mcu or mcu_ref(sch, pads)
    for net in pcb_nets:
        own = sorted(n for n in net if n.startswith(mcu + '.'))
        for n in own[1:]:
            parent[find(n)] = find(own[0])           # the module joins its own pins of one net
    for net in pcb_nets:
        if len({find(n) for n in net}) > 1:
            bad('net not fully wired:', sorted(net))
    which = {n: name for name, v in nets.items() for n in v}
    groups = collections.defaultdict(set)
    for n in list(parent):
        groups[find(n)].add(which.get(n))
    for g in groups.values():
        g.discard(None)                          # bus holes are not pads
        if len(g) > 1:
            bad('wires join different nets:', g)
    print(f'6.   {len(rows)} wires join every net (MCU {mcu}), no shorts')

    # 7: wire ends per hole
    ends = collections.Counter()
    for section, c in rows:
        for h in c[4:6]:
            ends[h if ':' in h else f'B{section}:{h}'] += 1
    for h, n in sorted(ends.items()):
        if n > args.max_per_hole:
            bad(f'{n} wire ends in hole {h} (max {args.max_per_hole})')
    print(f'7.   at most {max(ends.values())} wire ends in one hole (max {args.max_per_hole})')

    print('PROBLEMS:', len(errors))
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
