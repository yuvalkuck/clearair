#!/usr/bin/env python3
"""Perfboard build instructions from clearair.kicad_pcb (plain text, no KiCad needed).

Run from the board folder:  python3 ../tools/perfboard_wire_list.py [BOARD.kicad_pcb [OUT.md]] [--link-max-mm 300]
                            [--max-wires-per-hole 3] [--wire-stock 24,30]
Writes perfboard_wiring.md: 1) sockets and headers, 2) the other parts, 3) every
wire pin to pin with its AWG (star: every pin of a net goes to the net's hub
pin), 4) a check list per part.
"""
import re, math, sys

import argparse, glob, json, os
ap = argparse.ArgumentParser(description='Perfboard build instructions from a KiCad board.')
ap.add_argument('pcb', nargs='?', default=(glob.glob('*.kicad_pcb') or ['board.kicad_pcb'])[0])
ap.add_argument('out', nargs='?', default='perfboard_wiring.md')
ap.add_argument('--link-max-mm', type=int, default=300, help='longest wire between two boards')
ap.add_argument('--max-wires-per-hole', type=int, default=3, help='wire ends that fit on one solder pad')
ap.add_argument('--wire-stock', default='24,30', help='AWG numbers of the wire you have, comma separated')
ARGS = ap.parse_args()
PCB, OUT = ARGS.pcb, ARGS.out
STOCK = sorted(int(x) for x in ARGS.wire_stock.split(','))         # thick (low number) first
CFG = dict(transistor_pins={}, header_footprints=['PinHeader', 'PinSocket'], link_max_mm=ARGS.link_max_mm,
           max_wires_per_hole=ARGS.max_wires_per_hole, optional={})

# Part data lives in the schematic next to the board: the DNP flag and the pin names and electrical types of the symbols.
SCH = os.path.splitext(PCB)[0] + '.kicad_sch'
PIN_TYPES = {}                     # ref -> {pin number: electrical type}, from the symbols
if os.path.exists(SCH):
    st = open(SCH).read()
    libpins = {}                   # lib_id -> {pad: pin name}
    for lid in set(re.findall(r'\n\t\t\(lib_id "([^"]+)"', st)):
        i = st.index(f'(symbol "{lid}"'); j = st.find('\n\t\t(symbol "', i + 10); j = j if j > 0 else st.index('\n\t)', i)
        libpins[lid] = {n: nm for nm, n in re.findall(r'\(pin \w+ \w+.*?\(name "([^"]*)".*?\(number "([^"]*)"', st[i:j], re.S)}
        libpins[lid + ' types'] = {n: ty for ty, n in re.findall(r'\(pin (\w+) \w+.*?\(number "([^"]*)"', st[i:j], re.S)}
    for blk in st.split('\n\t(symbol\n')[1:]:
        props = dict(re.findall(r'\(property "([^"]+)" "([^"]*)"', blk))
        ref, lid = props.get('Reference'), re.search(r'\(lib_id "([^"]+)"', blk)[1]
        PIN_TYPES[ref] = libpins.get(lid + ' types', {})
        if re.search(r'\n\t\t\(dnp yes\)', blk): CFG['optional'][ref] = 'DNP'      # KiCad's Do Not Populate: hardware for a later stage, wires to it can be left out
        if lid in libpins and ref[0] == 'Q': CFG['transistor_pins'].setdefault(props['Value'], {}).update(libpins[lid])
KIND = {'R': 'resistor', 'J': 'header', 'Q': 'transistor', 'A': 'MCU board', 'SW': 'push button',
        'BZ': 'buzzer', 'PS': 'power input', 'M': 'fan header', 'U': 'module'}
t = open(PCB).read()
rects = sorted(tuple(map(float, m)) for m in re.findall(
    r'\(gr_rect\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)(?:(?!gr_rect).)*?"Edge.Cuts"', t, re.S))
parts = {}
for f in re.split(r'\n\t\(footprint ', t)[1:]:
    m = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', f)
    x0, y0, a = float(m[1]), float(m[2]), math.radians(float(m[3] or 0))
    ref = re.search(r'"Reference"\s+"([^"]*)"', f)[1]
    val = re.search(r'"Value"\s+"([^"]*)"', f)[1]
    pl = []
    for blk in re.split(r'\n\t\t\(pad ', f)[1:]:
        h = re.match(r'"([^"]*)" thru_hole', blk)
        if not h: continue
        at = re.search(r'\(at ([-\d.]+) ([-\d.]+)', blk)
        px, py = float(at[1]), float(at[2])
        n = re.search(r'\(net "([^"]*)"', blk)
        fn = re.search(r'\(pinfunction "([^"]*)"', blk)
        ty = re.search(r'\(pintype "([^"+]*)', blk)
        net = n[1] if n and not n[1].startswith('unconnected') else None
        pl.append(dict(num=h[1], net=net, fn=fn[1] if fn else '', type=ty[1] if ty else 'passive',
                       x=x0 + px * math.cos(a) + py * math.sin(a), y=y0 - px * math.sin(a) + py * math.cos(a)))
    parts[ref] = dict(ref=ref, val=val, pads=pl, rot=a, fp=f.split('\n')[0].strip().strip('"'))
    if re.search(r'\(attr [^)]*\bboard_only\b', f) and pl and len({q['net'] for q in pl}) == 1 and pl[0]['net']:
        parts[ref]['bus'] = pl[0]['net']             # a board-only footprint whose pads share one net: a bus strip (bare wire along its holes)

MCU = max((r for r in parts if not parts[r].get('bus')), key=lambda r: len(parts[r]['pads']))      # the biggest part, normally the MCU module
FEMALE = [MCU]                     # the module plugs into sockets
def prefix(r): return re.match(r'[A-Za-z]+', r)[0]
def kind(r): return KIND.get(prefix(r), 'part')

boards = []
for i, (l, tp, r, b) in enumerate(rects):
    W, H = round((r - l) / 2.54) + 1, round((b - tp) / 2.54) + 1
    boards.append(dict(i=i, l=l, tp=tp, r=r, b=b, W=W, H=H, rot=H > W))   # taller than wide: shown rotated
def board_of(p):
    for bd in boards:
        if bd['l'] - 1 <= p['x'] <= bd['r'] + 1 and bd['tp'] - 1 <= p['y'] <= bd['b'] + 1: return bd
for ref, pt in parts.items():
    for p in pt['pads']:
        bd = board_of(p); p['ref'] = ref; p['bd'] = bd
        if not bd: continue
        c, rw = (p['x'] - bd['l']) / 2.54, (p['y'] - bd['tp']) / 2.54
        p['off'] = max(abs(c - round(c)), abs(rw - round(rw))) * 2.54
        c, rw = round(c) + 1, round(rw) + 1
        if bd['rot']: c, rw = bd['H'] + 1 - rw, c        # portrait board shown rotated 90 deg clockwise
        p['hole'] = (c, rw)
def ncols(bd): return bd['H'] if bd['rot'] else bd['W']
def nrows(bd): return bd['W'] if bd['rot'] else bd['H']
def cnum(s):
    n = 0
    for ch in s: n = n * 26 + ord(ch) - 64
    return n
def cname(c):
    """Column letter: 1 = A ... 24 = X, 27 = AA."""
    s = ''
    while c: c, m = divmod(c - 1, 26); s = chr(65 + m) + s
    return s
def hname(bd, c, r): return f"{cname(ncols(bd) + 1 - c)}{nrows(bd) + 1 - r}"   # A18 is the top right corner of the component side
def hn(p): return hname(p['bd'], *p['hole'])      # the board's own hole name, the same from both sides
def lab(p):
    same = [q for q in parts[p['ref']]['pads'] if q['num'] == p['num']]
    return f"{p['ref']}.{p['num']}" + (f"@{hn(p)}" if len(same) > 1 else '')
def where(p): return f"B{p['bd']['i']+1}:{hn(p)}"

def netname(n): return n[1:] if n and n.startswith('/') else n   # a net label on the root sheet: KiCad puts the sheet path "/" before its name
LINK_MAX_MM = CFG['link_max_mm']  # longest wire between two boards
# Net classes from the KiCad project (Schematic Setup > Net Classes): the track width sets the current and so the AWG, the schematic color the wire color.
PRO = os.path.splitext(PCB)[0] + '.kicad_pro'
NS = json.load(open(PRO)).get('net_settings', {}) if os.path.exists(PRO) else {}
CLASSES = {c['name']: c for c in NS.get('classes', [])}
PATTERNS = [(q['pattern'], q['netclass']) for q in NS.get('netclass_patterns') or []]
def net_class(net):
    import fnmatch
    return CLASSES.get(next((c for pat, c in PATTERNS if fnmatch.fnmatchcase(net, pat)), 'Default'), {})
PALETTE = {'red': (220, 0, 0), 'black': (0, 0, 0), 'white': (255, 255, 255), 'yellow': (200, 160, 0), 'green': (0, 140, 0),
           'blue': (0, 0, 220), 'orange': (255, 128, 0), 'grey': (128, 128, 128), 'purple': (128, 0, 160), 'brown': (120, 60, 0)}
def class_color(net):
    m = re.match(r'rgba\((\d+), (\d+), (\d+), ([\d.]+)\)', net_class(net).get('schematic_color', ''))
    if not m or float(m[4]) == 0: return ''
    rgb = tuple(int(x) for x in m.groups()[:3])
    return min(PALETTE, key=lambda k: sum((u - v) ** 2 for u, v in zip(PALETTE[k], rgb)))
AMPACITY = {20: 11, 22: 7, 24: 3.5, 26: 2.2, 28: 1.4, 30: 0.86, 32: 0.53}      # A, chassis wiring (single wire in free air)
def track_amps(mm):
    """IPC-2221 current of a PCB track: outer layer, 1 oz (35 um) copper, 10 C rise; as in KiCad's PCB Calculator."""
    return 0.048 * 10 ** 0.44 * (mm / 0.0254 * 1.378) ** 0.725
def awg_of(mm):
    """Thinnest wire in stock that carries the current of a track of this width (the thickest one if none does)."""
    amps = track_amps(mm)
    n = next((n for n in reversed(STOCK) if AMPACITY.get(n, 0) >= amps), None)
    if n is None:
        n = STOCK[0]
        if mm not in WARNED: WARNED.add(mm); print(f"warning: no wire in stock carries {amps:.1f} A (track {mm} mm), using AWG{n}", file=sys.stderr)
    return f"AWG{n}"
WARNED = set()
def awgn(aw): return int(aw[3:])
THICK = f"AWG{STOCK[0]}"           # the bare wire of the bus strips
def wire_kind(net, a, b, link=False):
    """(kind, AWG) of the wire between pads a and b of one net, from the track width of its net class."""
    if a['ref'] == MCU and b['ref'] == MCU: return 'same module, no wire', '--'
    nc = net_class(net)
    return nc.get('name', 'Default').lower(), awg_of(nc.get('track_width', 0.2))

allpads = [p for pt in parts.values() if not pt.get('bus') for p in pt['pads'] if p['bd']]
nets = {}
for p in allpads:
    if p['net']: nets.setdefault(p['net'], []).append(p)
def nets_of(n): return nets.get(n, [])
def hub_of(ps):
    for p in ps:
        if p['ref'] == MCU: return p
    for pref in ('J', 'PS', 'M', 'BZ', 'SW', 'Q', 'R'):
        for p in ps:
            if prefix(p['ref']) == pref: return p
    return ps[0]
hub = {}                       # (net, board) -> hub pad
for n, ps in nets.items():
    for bd in boards:
        loc = [p for p in ps if p['bd'] is bd]
        if loc: hub[(n, bd['i'])] = hub_of(loc)


def net_rank(n):
    """Voltage rails first (highest voltage on top), then ground, then signals by name."""
    name = netname(n)
    v = re.fullmatch(r'\+?(\d+)V(\d*)', name)
    if v: return (0, -float(f"{v[1]}.{v[2] or 0}"), '')
    if re.fullmatch(r'(GND|AGND|DGND|VSS)', name, re.I): return (1, 0, '')
    return (2, 0, name)

# Bus strips: board-only footprints in the PCB, one per rail and board, whose pads share the rail's net. A bare wire runs along
# their holes on the back. Every pin of that rail on the board gets its own short wire to one hole of the strip.
BUS = {}                       # (net, board) -> dict(ref, row, pads, assign {id(pad): bus pad}, link bus pad or None)
for ref, pt in sorted(parts.items(), key=lambda kv: int(re.sub(r'\D', '', kv[0]) or 0)):
    if not pt.get('bus') or not pt['pads'][0]['bd']: continue
    n, bd = pt['bus'], pt['pads'][0]['bd']
    bpads = sorted(pt['pads'], key=lambda p: int(p['num']))
    loc = [p for p in nets_of(n) if p['bd'] is bd]
    vref = [p for p in loc if p['ref'] == MCU and p['fn'].startswith('VREF')]      # VREF pins are not fed from the supply pins inside the module: own wire, and never the supply path
    mcu = [p for p in loc if p['ref'] == MCU and p not in vref]
    items = sorted([p for p in loc if p['ref'] != MCU] + vref, key=lambda p: p['hole'])
    if mcu:
        mid = sum(q['hole'][0] for q in bpads) / len(bpads)
        items.append(min(mcu, key=lambda p: abs(p['hole'][0] - mid))); items.sort(key=lambda p: p['hole'])
    linked = len({q['bd']['i'] for q in nets_of(n)}) > 1
    free = list(bpads[:len(bpads) - linked] if linked else bpads)
    assign = {}
    if len(free) == len(items): assign = {id(p): free[i] for i, p in enumerate(items)}
    else:                                                        # not one hole per pin: nearest free hole of the strip
        for p in items:
            q = min(free or bpads, key=lambda q: math.hypot(q['hole'][0] - p['hole'][0], q['hole'][1] - p['hole'][1]))
            assign[id(p)] = q
            if q in free: free.remove(q)
    BUS[(n, bd['i'])] = dict(ref=ref, row=bpads[0]['hole'][1], pads=bpads, assign=assign, link=bpads[-1] if linked else None)
    pt['val'] = f"{netname(n)} bus"

def top(p): return p['hole']
def runs(ps):
    """Split pads (sorted by number) into straight runs of neighbouring holes."""
    out, cur = [], []
    for p in sorted(ps, key=lambda p: (len(p['num']), p['num'], p['hole'])):
        if cur:
            (c0, r0), (c1, r1) = cur[-1]['hole'], p['hole']
            d = (c1 - c0, r1 - r0)
            ok = (abs(d[0]) + abs(d[1]) == 1) and (len(cur) < 2 or d == (cur[-1]['hole'][0] - cur[-2]['hole'][0], cur[-1]['hole'][1] - cur[-2]['hole'][1]))
            if ok: cur.append(p); continue
            out.append(cur); cur = []
        cur.append(p)
    if cur: out.append(cur)
    return out
def direction(run):
    if len(run) < 2: return ''
    (c0, r0), (c1, r1) = run[0]['hole'], run[1]['hole']
    return {(1, 0): 'to the right', (-1, 0): 'to the left', (0, 1): 'downwards', (0, -1): 'upwards'}[(c1 - c0, r1 - r0)]
def is_socket(pt):
    """Connector-like parts: pin headers and sockets, and the MCU module."""
    return pt['ref'] in FEMALE or any(k in pt['fp'] for k in CFG['header_footprints'])
def part_sort(r): return (prefix(r), int(re.sub(r'\D', '', r) or 0))
def refs_on(bd, pred):
    return [r for r in sorted(parts, key=part_sort) if pred(parts[r], r) and any(p['bd'] is bd for p in parts[r]['pads'] if 'hole' in p)]
INTRO = ("Hole name = column letter + row number, like `E7`. Columns are letters along the long side (A, B, C ...), rows are numbers along the short side, as printed on the perfboard. "
         "Look at the component side (**top**) with the long side horizontal: the corner A + last row is at the **top right**, column A is at the right and row 1 at the bottom. "
         "The name of a hole is the same from both sides: from the **back** (solder side, where all wires go) the board is turned over left to right, so A is at the left. "
         + "".join(f"Board {bd['i']+1} is shown rotated 90° clockwise, so it lies landscape (in KiCad it is portrait). " for bd in boards if bd['rot'])
         + "\n" + "".join(f"\nBoard {bd['i']+1}: {ncols(bd)} columns (A to {cname(ncols(bd))}) x {nrows(bd)} rows." for bd in boards) + "\n")
o = ["# Perfboard build instructions\n\nGenerated by `hardware/tools/perfboard_wire_list.py` from `clearair.kicad_pcb`. Regenerate after you move parts.\n\n" + INTRO]
bad = [p for p in allpads if p['off'] > 0.35]
if bad: o.append("\n> **Layout not on the grid yet:** " + ", ".join(sorted({p['ref'] for p in bad}, key=part_sort)) + " have pins more than 0.35 mm off the 2.54 mm grid, so the holes below are rounded. Fix it in KiCad and regenerate.\n")
o.append("\n## 1. Place the parts (top side)\n\n**Male** = pin header: everything that connects with a wire or a plug from off the board (sensors, fans, buzzer, RTC, dimmer, supply). **Female** = socket: a board that plugs into the perfboard (the MCU module).\n")
PINS = CFG['transistor_pins']       # {value: {pad: letter}}, from the symbols
def flat_side(pt, bd):
    """Which way the flat face of a TO-92 points, in the top view of the board."""
    dx, dy = math.sin(pt['rot']), math.cos(pt['rot'])          # footprint flat side is +y
    if bd['rot']: dx, dy = -dy, dx                              # a portrait board is shown rotated
    if abs(dx) > abs(dy): return 'right' if dx > 0 else 'left'
    return 'down' if dy > 0 else 'up'
def short_type(r, pt, n):
    if pt.get('bus'): return f"bus strip {netname(pt['bus'])}: one bare wire ({THICK}) along the holes on the back, soldered in every hole"
    if r in FEMALE:
        lines = len({p['hole'][1] for p in parts[r]['pads'] if 'hole' in p})
        return f"{lines} x 1x{n // max(lines, 1)} female socket"
    if is_socket(pt): return f"1x{n:02d} male header {re.sub(r' wire header.*', '', pt['val'])}"
    return {'R': 'resistor', 'Q': 'transistor', 'SW': 'push button', 'BZ': 'buzzer'}.get(prefix(r), kind(r)) + f" {pt['val']}"
for bd in boards:
    o.append(f"\n### Board {bd['i']+1}\n\n| Part | Type | Holes |\n|---|---|---|\n")
    for r in refs_on(bd, lambda pt, rr: True):
        pt = parts[r]; ps = sorted([p for p in pt['pads'] if p['bd'] is bd], key=lambda p: (len(p['num']), p['num'], p['hole']))
        h = hn
        if pt.get('bus'): where_ = f"{h(ps[0])} to {h(ps[-1])}"
        elif prefix(r) == 'Q':
            where_ = ' '.join(f"{h(p)}={PINS.get(pt['val'], {}).get(p['num'], p['num'])}" for p in ps)
        elif prefix(r) == 'BZ':
            where_ = ' '.join(f"{h(p)}={'+' if p['fn'].startswith('+') else '-'}" for p in ps)
        elif r in FEMALE:
            where_ = '; '.join(f"{hname(bd, min(q['hole'][0] for q in ps if q['hole'][1] == rw), rw)} to {hname(bd, max(q['hole'][0] for q in ps if q['hole'][1] == rw), rw)}" for rw in sorted({q['hole'][1] for q in ps}))
        elif is_socket(pt):
            where_ = '; '.join(f"{h(run[0])} to {h(run[-1])}" if len(run) > 1 else h(run[0]) for run in runs(ps))
        elif len(ps) == 3: where_ = f"{h(ps[0])} to {h(ps[-1])}"
        elif len(ps) > 3: where_ = '; '.join(f"{h(run[0])} to {h(run[-1])}" if len(run) > 1 else h(run[0]) for run in runs(ps))
        else: where_ = ', '.join(h(p) for p in ps)
        typ = short_type(r, pt, len(ps)) + (f", flat side {flat_side(pt, bd)}" if prefix(r) == 'Q' else '')
        o.append(f"| {r} | {typ}" + (f" (optional: {CFG['optional'][r]})" if r in CFG['optional'] else "") + f" | {where_} |\n")
o.append("\n## 2. Solder the wires (back side, pin to pin)\n\nSolder on the **back** side. **Bus strips** (`BUSn`, the first of the thick AWG24 rows in each table): lay them before the wires that go to them. Lay one bare wire from the first to the last hole of a strip (on either side of the board) and solder it in every hole; each pin of that voltage or ground then gets its own short wire to one hole of the strip (the `BUSn.k` pin). Nets without a strip: every pin of a net is wired to the nearest pin of the same net that is already connected, so no hole gets more than 3 wire ends (the MCU module's own pins of a net count as one connection). A wire carries the current of everything behind it, so it is thick if any wire behind it is thick. Max length is only set where it matters: wires between the boards (`B1 ↔ B2`) are limited to 300 mm. The other wires have no limit. Three tables: board 1, board 2, and the wires between the boards. Each is sorted by AWG number from high to low (thin AWG30 before thick AWG24), then by net: voltage rails first (highest voltage on top), then ground, then signals; then by wire color. Work from the top down.\n")
order = {'power': 0, 'ground': 1, 'signal': 2}
wires = []
CAP = CFG['max_wires_per_hole']    # wire ends in one hole: more do not fit on the solder pad
def kind_order(kd): return order.get(kd.split()[0].rstrip(','), 2)
def hole_dist(a, b): return math.hypot(a['hole'][0] - b['hole'][0], a['hole'][1] - b['hole'][1])
for n in sorted(nets):
    for bd in boards:
        loc = [p for p in nets[n] if p['bd'] is bd]
        if len(loc) < 2: continue
        if (n, bd['i']) in BUS:
            for p in sorted(loc, key=lambda p: p['hole']):
                if id(p) in BUS[(n, bd['i'])]['assign']:
                    bp = BUS[(n, bd['i'])]['assign'][id(p)]; kd, aw = wire_kind(n, p, bp)
                    wires.append((kind_order(kd), n, bd['i'], p, bp, kd, aw, ''))
            continue
        h = hub[(n, bd['i'])]
        roots = [p for p in loc if p['ref'] == MCU] or [h]     # the pins of the MCU module are joined inside it: each is a root
        deg = {id(p): 0 for p in loc}
        if (n, 1 - bd['i']) in hub and len(boards) == 2: deg[id(h)] += 1      # the wire to the other board ends here
        linked = list(roots)
        todo = sorted((p for p in loc if p not in roots), key=lambda p: (part_sort(p['ref']), p['num']))
        edges = []                                              # (child, parent)
        while todo:                                             # nearest free pad first: short wires, few ends per hole
            best = min(((hole_dist(q, c), qi, ci) for qi, q in enumerate(todo) for ci, c in enumerate(linked) if deg[id(c)] < CAP), default=None)
            if best is None: sys.exit(f"error: net {n} on board {bd['i']+1}: no hole left, raise max_wires_per_hole")
            _, qi, ci = best
            q, c = todo.pop(qi), linked[ci]
            kd, aw = wire_kind(n, q, c)
            if aw != '--': deg[id(c)] += 1; deg[id(q)] += 1; edges.append([q, c, kd, aw])
            linked.append(q)
        parent = {id(e[0]): e for e in edges}
        for e in edges:                                         # a wire carries the current of everything behind it: as thick as the thickest wire behind it
            up = parent.get(id(e[1]))
            while up is not None and awgn(e[3]) < awgn(up[3]):
                up[3] = e[3]; up = parent.get(id(up[1]))
        for q, c, kd, aw in edges:
            wires.append((kind_order(kd), n, bd['i'], q, c, kd, aw, ''))
for n in sorted(nets):
    if (n, 0) in hub and (n, 1) in hub:
        a = BUS[(n, 0)]['link'] if (n, 0) in BUS else hub[(n, 0)]
        b = BUS[(n, 1)]['link'] if (n, 1) in BUS else hub[(n, 1)]
        kd, aw = wire_kind(n, a, b, link=True)
        wires.append((order.get(kd.split()[0].rstrip(','), 2), n, 2, a, b, kd, aw, str(LINK_MAX_MM)))
def color_of(w): return ('white' if tie_of(w) else class_color(w[1])).capitalize()
def tie_of(w):                                                  # a logic pin (input, bidirectional ...) on a voltage rail is strapped high, not powered
    return net_rank(w[1])[0] == 0 and any(PIN_TYPES.get(p['ref'], {}).get(p['num'], p.get('type', 'passive')) not in ('passive', 'power_in', 'power_out', 'unspecified', 'free') for p in (w[3], w[4]))
def optional_of(w):                                             # a wire to a pin header (J...) that is not optional is built with that header
    if any(prefix(p['ref']) == 'J' and p['ref'] not in CFG['optional'] for p in (w[3], w[4])): return ''
    return next((CFG['optional'][p['ref']] for p in (w[3], w[4]) if p['ref'] in CFG['optional']), '')
wires.sort(key=lambda w: (w[2] == 2, w[2], -awgn(w[6]), net_rank(w[1]), color_of(w), part_sort(w[3]['ref'])))   # board (links last), thin wire (higher AWG number) first, then net, then color
HAS_NOTE = any(optional_of(w) for w in wires)               # the Note column is only there when a wire has a note
def wire_table(title, bi_want):
    link = bi_want == 2
    o.append(f"\n### {title}\n\n| # | AWG | Color | Net | From hole | To hole | From pin | To pin |" + (" Max length (mm) |" if link else "") + (" Note |" if HAS_NOTE else "") + "\n|---|---|---|---|---|---|---|---|" + ("---|" if link else "") + ("---|" if HAS_NOTE else "") + "\n")
    def bus_rows():                                             # the bare wire of each bus strip: it is a part of the board, listed with the thick wires
        if link: return
        for ref in sorted((r for r in parts if parts[r].get('bus') and parts[r]['pads'][0]['bd']['i'] == bi_want), key=lambda r: (net_rank(parts[r]['bus']), part_sort(r))):
            ps_ = parts[ref]['pads']
            o.append(f"| {ref} | {THICK} bare | Bare | {netname(parts[ref]['bus'])} | {hn(ps_[0])} | {hn(ps_[-1])} | {ref}.{ps_[0]['num']} | {ref}.{ps_[-1]['num']} |" + (" |" if HAS_NOTE else "") + "\n")
    done = link
    for i, w in enumerate(wires, 1):
        _, n, bi, a, b, kd, aw, ln = w
        if bi != bi_want: continue
        if awgn(aw) <= awgn(THICK) and not done: bus_rows(); done = True
        fh, th = (where(a), where(b)) if link else (hn(a), hn(b))
        o.append(f"| #{i:02d} | {aw} | {color_of(w)} | {netname(n)} | {fh} | {th} | {lab(a)} | {lab(b)} |" + (f" {ln} |" if link else "") + ((f" optional: {optional_of(w)} |" if optional_of(w) else " |") if HAS_NOTE else "") + "\n")
    if not done: bus_rows()
wid = {}
for i, (_, n, bi, a, b, kd, aw, ln) in enumerate(wires, 1):
    wid.setdefault(id(a), []).append(i); wid.setdefault(id(b), []).append(i)
for bd in boards: wire_table(f"Wires on board {bd['i']+1}", bd['i'])
wire_table("Wires between the boards (B1 ↔ B2)", 2)
o.append("\n## 3. Check list per part\n\nOne table per part: every pin with its hole and the wire numbers that touch it. `--` means no wire.\n")
def pin_name(pt, p):
    if prefix(pt['ref']) == 'Q' and p['num'] in PINS.get(pt['val'], {}): return PINS[pt['val']][p['num']]
    return '' if re.fullmatch(r'Pin_\d+(_\d+)?', p['fn']) else p['fn']
for r in sorted(parts, key=part_sort):
    ps = [p for p in parts[r]['pads'] if p['bd']]
    if not ps: continue
    o.append(f"\n**{r}** {parts[r]['val']}" + (f" (optional: {CFG['optional'][r]})" if r in CFG['optional'] else "") + "\n\n| Pin | Name | Net | Hole | Wires |\n|---|---|---|---|---|\n")
    for p in sorted(ps, key=lambda p: (len(p['num']), p['num'], p['hole'])):
        o.append(f"| {p['num']} | {pin_name(parts[r], p)} | {netname(p['net']) or ''} | {where(p)} | {', '.join(f'#{w:02d}' for w in wid.get(id(p), [])) or '--'} |\n")
open(OUT, 'w').write(''.join(o))
print('wrote', OUT, len(nets), 'nets,', len(wires), 'wires')
