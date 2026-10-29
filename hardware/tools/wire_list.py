#!/usr/bin/env python3
"""Perfboard build instructions from clearair.kicad_pcb (plain text, no KiCad needed).

Run from the board folder:  python3 ../tools/wire_list.py [BOARD.kicad_pcb [OUT.md [CONFIG.json]]]
Writes perfboard_wiring.md: 1) sockets and headers, 2) the other parts, 3) every
wire pin to pin with its AWG (star: every pin of a net goes to the net's hub
pin), 4) a check list per part.
"""
import re, math, sys

import glob, json, os
PCB = sys.argv[1] if len(sys.argv) > 1 else (glob.glob('*.kicad_pcb') or ['board.kicad_pcb'])[0]
OUT = sys.argv[2] if len(sys.argv) > 2 else 'perfboard_wiring.md'
CFG_PATH = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.abspath(PCB)), 'wire_list.json')
CFG = dict(net_names={}, mcu=None, female=None, posts=[], sensors=[], high_current_prefixes=[], transistor_pins={},
           headers=[], header_footprints=['PinHeader'], link_max_mm=300, max_wires_per_hole=3, bus_min_pads=4, bus_near=[], bus_area={}, awg_thick='AWG24', awg_thin='AWG30')
if os.path.exists(CFG_PATH): CFG.update(json.load(open(CFG_PATH)))

# Part data lives in the schematic next to the board: field "Role" (words: mcu, female, header, post, sensor, heavy),
# fields "Net <pin>" (readable net name), and the pin names of the transistor symbols.
SCH = os.path.splitext(PCB)[0] + '.kicad_sch'
SCH_NETS = {}                      # (ref, pin) -> readable net name
if os.path.exists(SCH):
    st = open(SCH).read()
    libpins = {}                   # lib_id -> {pad: pin name}
    for lid in set(re.findall(r'\n\t\t\(lib_id "([^"]+)"', st)):
        i = st.index(f'(symbol "{lid}"'); j = st.find('\n\t\t(symbol "', i + 10); j = j if j > 0 else st.index('\n\t)', i)
        libpins[lid] = {n: nm for nm, n in re.findall(r'\(pin \w+ \w+.*?\(name "([^"]*)".*?\(number "([^"]*)"', st[i:j], re.S)}
    for blk in st.split('\n\t(symbol\n')[1:]:
        props = dict(re.findall(r'\(property "([^"]+)" "([^"]*)"', blk))
        ref, lid = props.get('Reference'), re.search(r'\(lib_id "([^"]+)"', blk)[1]
        words = props.get('Role', '').split()
        for w, key in (('mcu', 'mcu'), ('female', 'female'), ('header', 'headers'), ('post', 'posts'), ('sensor', 'sensors')):
            if w in words:
                if key == 'mcu': CFG['mcu'] = ref
                else: CFG[key] = list(CFG[key] or []) + [ref]
        if 'bus' in words: CFG['bus_near'] = list(CFG['bus_near']) + [ref]
        if props.get('Bus area'): CFG['bus_area'] = dict(CFG['bus_area'], **{ref: props['Bus area']})      # e.g. A14:Q18, hole names of two corners
        if 'heavy' in words: CFG['heavy'] = CFG.get('heavy', []) + [ref]
        if lid in libpins and ref[0] == 'Q': CFG['transistor_pins'].setdefault(props['Value'], {}).update(libpins[lid])
        for k, v in props.items():
            if k.startswith('Net '): SCH_NETS[(ref, k[4:])] = v
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
        net = n[1] if n and not n[1].startswith('unconnected') else None
        pl.append(dict(num=h[1], net=net, fn=fn[1] if fn else '',
                       x=x0 + px * math.cos(a) + py * math.sin(a), y=y0 - px * math.sin(a) + py * math.cos(a)))
    parts[ref] = dict(ref=ref, val=val, pads=pl, rot=a, fp=f.split('\n')[0].strip().strip('"'))

MCU = CFG['mcu'] or max(parts, key=lambda r: len(parts[r]['pads']))      # the biggest part, normally the MCU module
FEMALE = CFG['female'] if CFG['female'] is not None else [MCU]
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

NETNAME = dict(CFG['net_names'])  # readable names for unnamed nets
for (r_, pin_), nm_ in SCH_NETS.items(): NETNAME[f'Net-({r_}-{pin_})'] = nm_   # KiCad names an unnamed net after one of its pins
LINK_MAX_MM = CFG['link_max_mm']  # longest wire between two boards
SENSORS = CFG['sensors']          # refs with heaters or fans: thick wire on their power and ground
HEAVY = CFG['high_current_prefixes'] + sorted({prefix(r) for r in CFG.get('heavy', [])})   # ref prefixes that carry fan, buzzer or supply current (field Role = heavy)
THICK, THIN = CFG['awg_thick'], CFG['awg_thin']
def wire_kind(net, a, b, link=False):
    """(kind, AWG) of the wire between pads a and b of one net. Only AWG24 and AWG30 are stocked."""
    if a['ref'] == MCU and b['ref'] == MCU: return 'same module, no wire', '--'
    if link and net in ('+5V', '+12V'): return 'power, board link', THICK
    ends = {prefix(a['ref']), prefix(b['ref'])}
    sensor = bool({a['ref'], b['ref']} & set(SENSORS))      # SPS30, MQ131, MiCS: heaters and fans, 65 to 185 mA
    if net == '+12V': return 'power 12V', THICK
    if net == 'GND':
        if link: return 'ground, board link (all returns)', THICK
        if ends & set(HEAVY): return 'ground, high current', THICK
        return ('ground, sensor' if sensor else 'ground, signal return'), (THICK if sensor else THIN)
    if net == '+5V':
        if ends & set(HEAVY) | {prefix(MCU)}: return 'power 5V, supply', THICK
        return ('power 5V, sensor' if sensor else 'power 5V, pull-up'), (THICK if sensor else THIN)
    if net == '+3V3': return 'power 3V3', THIN
    return 'signal', THIN

allpads = [p for pt in parts.values() for p in pt['pads'] if p['bd']]
nets = {}
for p in allpads:
    if p['net']: nets.setdefault(p['net'], []).append(p)
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
    name = NETNAME.get(n, n)
    v = re.fullmatch(r'\+?(\d+)V(\d*)', name)
    if v: return (0, -float(f"{v[1]}.{v[2] or 0}"), '')
    if re.fullmatch(r'(GND|AGND|DGND|VSS)', name, re.I): return (1, 0, '')
    return (2, 0, name)

# Bus strips: a bare wire laid along a free row of holes on the back. Every pin of a rail (voltage or ground) gets its own short wire
# to a hole of the strip, so no hole gets many wires. Boards with an MCU module put them under it (between its two socket rows).
BUS = {}                       # (net, board) -> dict(ref, row, pads, assign {id(pad): bus pad}, link bus pad or None)
busnr = 0
if CFG['bus_min_pads']:
    used = {bd['i']: {p['hole'] for p in allpads if p['bd'] is bd and 'hole' in p} for bd in boards}
    spans = {bd['i']: [] for bd in boards}          # (row, first column, last column) of the strips
    for n in sorted(nets, key=net_rank):
        if net_rank(n)[0] > 1: continue
        for bd in boards:
            loc = [p for p in nets[n] if p['bd'] is bd]
            mcu = [p for p in loc if p['ref'] == MCU]
            others = [p for p in loc if p['ref'] != MCU]
            linked = len({q['bd']['i'] for q in nets[n]}) > 1
            k = len(others) + bool(mcu) + linked
            if k < CFG['bus_min_pads']: continue
            ncol, nrow = ncols(bd), nrows(bd)
            mrows = sorted({p['hole'][1] for p in allpads if p['bd'] is bd and p['ref'] == MCU})
            near = [p for p in allpads if p['bd'] is bd and p['ref'] in CFG['bus_near']] or loc      # strips go next to the parts with Role = bus
            mean_r = sum(p['hole'][1] for p in near) / len(near); mean_c = sum(p['hole'][0] for p in near) / len(near)
            area = [CFG['bus_area'][p['ref']] for p in near if p['ref'] in CFG['bus_area']]      # the strips of this board stay inside this rectangle
            if area:
                (la, ra), (lb, rb) = (re.fullmatch(r'([A-Z]+)(\d+)', s).groups() for s in area[0].split(':'))
                ca = sorted((ncol + 1 - cnum(la), ncol + 1 - cnum(lb))); ra_ = sorted((nrow + 1 - int(ra), nrow + 1 - int(rb)))
            else: ca, ra_ = (1, ncol), (1, nrow)
            between = [r for r in range(1, nrow + 1) if len(mrows) > 1 and mrows[0] < r < mrows[-1]]
            between = [r for r in between if r not in (mrows[0] + 1, mrows[-1] - 1)] or between      # not right next to the socket rows of the module
            between = sorted(between, key=lambda r: abs(r - mean_r))
            between = between[0::2] + between[1::2]                                                  # every other row first: bare wires 2 rows apart
            between = [r for r in between if ra_[0] <= r <= ra_[1]]
            rest = sorted((r for r in range(ra_[0], ra_[1] + 1) if r not in between), key=lambda r: abs(r - mean_r))
            def fits(r, w):                                                                          # no strip in the next row over the same columns
                return not any(abs(r2 - r) == 1 and not (w[-1] < a - 1 or w[0] > b + 1) for r2, a, b in spans[bd['i']])
            pick = None
            for strict in (True, False):
                for r in between + rest:
                    free = [c for c in range(ca[0], ca[1] + 1) if (c, r) not in used[bd['i']]]
                    runs_, cur_ = [], []
                    for c in free:
                        if cur_ and c != cur_[-1] + 1: runs_.append(cur_); cur_ = []
                        cur_.append(c)
                    if cur_: runs_.append(cur_)
                    wins = [run[s:s + k] for run in runs_ for s in range(len(run) - k + 1) if not strict or fits(r, run[s:s + k])]
                    if wins:
                        pick = (r, min(wins, key=lambda w: abs(sum(w) / k - mean_c))); break
                if pick: break
            if not pick: continue
            r, cols = pick
            busnr += 1; ref = f"BUS{busnr}"
            bpads = [dict(ref=ref, num=str(i), net=n, fn='', bd=bd, hole=(c, r), off=0, x=0, y=0) for i, c in enumerate(cols, 1)]
            items = sorted(others, key=lambda p: p['hole'])
            if mcu:
                mid = sum(cols) / k
                items.append(min(mcu, key=lambda p: abs(p['hole'][0] - mid))); items.sort(key=lambda p: p['hole'])
            assign = {id(p): bpads[i] for i, p in enumerate(items)}
            link = bpads[-1] if linked else None
            spans[bd['i']].append((r, cols[0], cols[-1])); used[bd['i']] |= {(c, r) for c in range(cols[0] - 1, cols[-1] + 2)}      # one hole of gap either side
            BUS[(n, bd['i'])] = dict(ref=ref, row=r, pads=bpads, assign=assign, link=link)
            parts[ref] = dict(ref=ref, val=f"{NETNAME.get(n, n)} bus", pads=bpads, rot=0, fp='bus', bus=n)


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
    """Connector-like parts: pin headers, the MCU module, supply posts and the refs listed under `headers`."""
    return pt['ref'] in FEMALE or pt['ref'] in CFG['posts'] or pt['ref'] in CFG['headers'] or any(k in pt['fp'] for k in CFG['header_footprints'])
def part_sort(r): return (prefix(r), int(re.sub(r'\D', '', r) or 0))
def refs_on(bd, pred):
    return [r for r in sorted(parts, key=part_sort) if pred(parts[r], r) and any(p['bd'] is bd for p in parts[r]['pads'] if 'hole' in p)]
INTRO = ("Hole name = column letter + row number, like `E7`. Columns are letters along the long side (A, B, C ...), rows are numbers along the short side, as printed on the perfboard. "
         "Look at the component side (**top**) with the long side horizontal: the corner A + last row is at the **top right**, column A is at the right and row 1 at the bottom. "
         "The name of a hole is the same from both sides: from the **back** (solder side, where all wires go) the board is turned over left to right, so A is at the left. "
         + "".join(f"Board {bd['i']+1} is shown rotated 90° clockwise, so it lies landscape (in KiCad it is portrait). " for bd in boards if bd['rot'])
         + "\n" + "".join(f"\nBoard {bd['i']+1}: {ncols(bd)} columns (A to {cname(ncols(bd))}) x {nrows(bd)} rows." for bd in boards) + "\n")
o = ["# Perfboard build instructions\n\nGenerated by `hardware/tools/wire_list.py` from `clearair.kicad_pcb`. Regenerate after you move parts.\n\n" + INTRO]
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
    if pt.get('bus'): return f"bus strip {NETNAME.get(pt['bus'], pt['bus'])}: one bare wire ({THICK}) along the holes on the back, soldered in every hole"
    if r in FEMALE:
        lines = len({p['hole'][1] for p in parts[r]['pads'] if 'hole' in p})
        return f"{lines} x 1x{n // max(lines, 1)} female socket"
    if r in CFG['posts']: return f"{n} male pins"
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
        else: where_ = ', '.join(h(p) for p in ps)
        typ = short_type(r, pt, len(ps)) + (f", flat side {flat_side(pt, bd)}" if prefix(r) == 'Q' else '')
        o.append(f"| {r} | {typ} | {where_} |\n")
o.append("\n## 2. Solder the wires (back side, pin to pin)\n\nSolder on the **back** side. **Bus strips** (`BUSn`, the first rows of each table): do them first. Lay one bare wire from the first to the last hole of a strip (on either side of the board) and solder it in every hole; each pin of that voltage or ground then gets its own short wire to one hole of the strip (the `BUSn.k` pin). Nets without a strip: every pin of a net is wired to the nearest pin of the same net that is already connected, so no hole gets more than 3 wire ends (the MCU module's own pins of a net count as one connection). A wire carries the current of everything behind it, so it is thick if any wire behind it is thick. Max length is only set where it matters: wires between the boards (`B1 ↔ B2`) are limited to 300 mm. The other wires have no limit. Three tables: board 1, board 2, and the wires between the boards. Each is sorted by thick wire (AWG24) before thin, then by net: voltage rails first (highest voltage on top), then ground, then signals. Work from the top down.\n")
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
        for e in edges:                                         # a wire carries the current of everything behind it: thick if any wire behind it is thick
            if e[3] == THICK:
                up = parent.get(id(e[1]))
                while up is not None:
                    up[3] = THICK; up = parent.get(id(up[1]))
        for q, c, kd, aw in edges:
            wires.append((kind_order(kd), n, bd['i'], q, c, kd, aw, ''))
for n in sorted(nets):
    if (n, 0) in hub and (n, 1) in hub:
        a = BUS[(n, 0)]['link'] if (n, 0) in BUS else hub[(n, 0)]
        b = BUS[(n, 1)]['link'] if (n, 1) in BUS else hub[(n, 1)]
        kd, aw = wire_kind(n, a, b, link=True)
        wires.append((order.get(kd.split()[0].rstrip(','), 2), n, 2, a, b, kd, aw, str(LINK_MAX_MM)))
wires.sort(key=lambda w: (w[2] == 2, w[2], w[6] != THICK, net_rank(w[1]), part_sort(w[3]['ref'])))   # board (links last), thick wire first, then net
def wire_table(title, bi_want):
    link = bi_want == 2
    o.append(f"\n### {title}\n\n| # | AWG | Net | From hole | To hole | From pin | To pin |" + (" Max length (mm) |" if link else "") + "\n|---|---|---|---|---|---|---|" + ("---|" if link else "") + "\n")
    if not link:                                                # the bare wire of each bus strip first: it is a part of the board
        for ref in sorted((r for r in parts if parts[r].get('bus') and parts[r]['pads'][0]['bd']['i'] == bi_want), key=lambda r: (net_rank(parts[r]['bus']), part_sort(r))):
            ps_ = parts[ref]['pads']
            o.append(f"| {ref} | {THICK} bare | {NETNAME.get(parts[ref]['bus'], parts[ref]['bus'])} | {hn(ps_[0])} | {hn(ps_[-1])} | {ref}.{ps_[0]['num']} | {ref}.{ps_[-1]['num']} |\n")
    for i, (_, n, bi, a, b, kd, aw, ln) in enumerate(wires, 1):
        if bi != bi_want: continue
        fh, th = (where(a), where(b)) if link else (hn(a), hn(b))
        o.append(f"| #{i:02d} | {aw} | {NETNAME.get(n, n)} | {fh} | {th} | {lab(a)} | {lab(b)} |" + (f" {ln} |" if link else "") + "\n")
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
    o.append(f"\n**{r}** {parts[r]['val']}\n\n| Pin | Name | Net | Hole | Wires |\n|---|---|---|---|---|\n")
    for p in sorted(ps, key=lambda p: (len(p['num']), p['num'], p['hole'])):
        o.append(f"| {p['num']} | {pin_name(parts[r], p)} | {NETNAME.get(p['net'], p['net']) or ''} | {where(p)} | {', '.join(f'#{w:02d}' for w in wid.get(id(p), [])) or '--'} |\n")
open(OUT, 'w').write(''.join(o))
print('wrote', OUT, len(nets), 'nets,', len(wires), 'wires')
