#!/usr/bin/env python3
"""Perfboard build instructions from clearair.kicad_pcb (plain text, no KiCad needed).

Run from the board folder:  python3 ../tools/wire_list.py
Writes perfboard_wiring.md: 1) sockets and headers, 2) the other parts, 3) every
wire pin to pin with its AWG (star: every pin of a net goes to the net's hub
pin), 4) a check list per part.
"""
import re, math, sys

PCB = sys.argv[1] if len(sys.argv) > 1 else 'clearair.kicad_pcb'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'perfboard_wiring.md'
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
    parts[ref] = dict(val=val, pads=pl, rot=a, fp=f.split('\n')[0].strip().strip('"'))

def prefix(r): return re.match(r'[A-Za-z]+', r)[0]
def kind(r): return KIND.get(prefix(r), 'part')

boards = []
for i, (l, tp, r, b) in enumerate(rects):
    W, H = round((r - l) / 2.54) + 1, round((b - tp) / 2.54) + 1
    boards.append(dict(i=i, l=l, tp=tp, r=r, b=b, W=W, H=H))
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
        if bd['i'] == 1: c, rw = bd['H'] + 1 - rw, c        # board 2 shown rotated 90 deg clockwise
        p['hole'] = (c, rw)
def ncols(bd): return bd['W'] if bd['i'] == 0 else bd['H']
def back(p): return (ncols(p['bd']) + 1 - p['hole'][0], p['hole'][1])      # seen from the solder side: left-right mirrored
def lab(p):
    same = [q for q in parts[p['ref']]['pads'] if q['num'] == p['num']]
    return f"{p['ref']}.{p['num']}" + (f"@{back(p)[0]},{back(p)[1]}" if len(same) > 1 else '')
def where(p): return f"B{p['bd']['i']+1}({back(p)[0]},{back(p)[1]})"

NETNAME = {                      # readable names for the unnamed nets (README "Service -> Pin Assignments")
    'Net-(A1-PA0)': 'MQ131 out', 'Net-(J5-Pin_4)': 'MQ131 out',
    'Net-(A1-PA1)': 'MiCS CO', 'Net-(J6-Pin_3)': 'MiCS CO',
    'Net-(A1-PA7)': 'MiCS NO2', 'Net-(J6-Pin_4)': 'MiCS NO2',
    'Net-(A1-PA15)': 'I2C SCL', 'Net-(A1-PB7)': 'I2C SDA',
    'Net-(A1-PB0)': 'ZC in', 'Net-(U5-Z-C)': 'ZC out', 'Net-(A1-PB1)': 'TRIAC gate',
    'Net-(A1-PB14)': 'Cold-boot button', 'Net-(A1-NRST)': 'Reset button',
    'Net-(A1-PB15)': 'Buzzer drive', 'Net-(Q3-B)': 'Buzzer base', 'Net-(BZ1--)': 'Buzzer GND',
    'Net-(A1-PA8)': 'Front fan PWM', 'Net-(M2-Pin_4)': 'Front fan PWM',
    'Net-(A1-PA9)': 'Rear fan PWM', 'Net-(M3-Pin_4)': 'Rear fan PWM',
    'Net-(A1-PA5)': 'Front fan tach', 'Net-(A1-PB3)': 'Rear fan tach',
    'Net-(A1-PB10)': 'Display TX', 'Net-(Q1-D)': 'Display TX',
    'Net-(A1-PB11)': 'Display RX', 'Net-(Q2-D)': 'Display RX',
}
LINK_MAX_MM = 300                # longest wire between the two boards (keeps I2C clean)
SENSORS = ('J3', 'J5', 'J6')
HEAVY = ('PS', 'M', 'BZ')       # carry fan / buzzer / supply current
def wire_kind(net, a, b, link=False):
    """(kind, AWG) of the wire between pads a and b of one net. Only AWG24 and AWG30 are stocked."""
    if a['ref'] == 'A1' and b['ref'] == 'A1': return 'same module, no wire', '--'
    ends = {prefix(a['ref']), prefix(b['ref'])}
    sensor = bool({a['ref'], b['ref']} & set(SENSORS))      # SPS30, MQ131, MiCS: heaters and fans, 65 to 185 mA
    if net == '+12V': return 'power 12V', 'AWG24'
    if net == 'GND':
        if link: return 'ground, board link (all returns)', 'AWG24'
        if ends & set(HEAVY): return 'ground, high current', 'AWG24'
        return ('ground, sensor' if sensor else 'ground, signal return'), ('AWG24' if sensor else 'AWG30')
    if net == '+5V':
        if ends & set(HEAVY) | {'A'}: return 'power 5V, supply', 'AWG24'
        return ('power 5V, sensor' if sensor else 'power 5V, pull-up'), ('AWG24' if sensor else 'AWG30')
    if net == '+3V3': return 'power 3V3', 'AWG30'
    return 'signal', 'AWG30'

allpads = [p for pt in parts.values() for p in pt['pads'] if p['bd']]
nets = {}
for p in allpads:
    if p['net']: nets.setdefault(p['net'], []).append(p)
def hub_of(ps):
    for pref in ('A', 'J', 'PS', 'M', 'BZ', 'SW', 'Q', 'R'):
        for p in ps:
            if prefix(p['ref']) == pref: return p
    return ps[0]
hub = {}                       # (net, board) -> hub pad
for n, ps in nets.items():
    for bd in boards:
        loc = [p for p in ps if p['bd'] is bd]
        if loc: hub[(n, bd['i'])] = hub_of(loc)


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
SOCKET = ('PinHeader', 'WeAct', 'RobotDyn', 'PSU')
def is_socket(pt): return any(k in pt['fp'] for k in SOCKET)
def socket_name(ref, pt):
    n = len([p for p in pt['pads']])
    if ref == 'A1': return '2 x 1x24 female socket, 2.54 mm (the WeAct board plugs in; rows 6 holes apart)'
    if ref == 'PS1': return '4 solder posts or 4 pins of a header strip (the two supply modules wire to them)'
    if ref == 'U5': return '1x04 female socket, 2.54 mm (RobotDyn dimmer logic side)'
    return f'1x{n:02d} female socket, 2.54 mm' + (' (the module or fan plug goes in)' if prefix(ref) in 'JM' else '')
def part_sort(r): return (prefix(r), int(re.sub(r'\D', '', r) or 0))
def refs_on(bd, pred):
    return [r for r in sorted(parts, key=part_sort) if pred(parts[r], r) and any(p['bd'] is bd for p in parts[r]['pads'] if 'hole' in p)]
INTRO = ("Hole = `(column,row)`, row 1 at the top. **Top** = component side, column 1 at the left, where the parts go. "
         "**Back** = solder side, where all wires go: the board turned over left to right, so back column = 25 - top column. "
         "Board 2 is shown rotated 90° clockwise, so it lies landscape like board 1 (in KiCad it is portrait).\n")
o = ["# Perfboard build instructions\n\nGenerated by `hardware/tools/wire_list.py` from `clearair.kicad_pcb`. Regenerate after you move parts.\n\n" + INTRO]
bad = [p for p in allpads if p['off'] > 0.35]
if bad: o.append("\n> **Layout not on the grid yet:** " + ", ".join(sorted({p['ref'] for p in bad}, key=part_sort)) + " have pins more than 0.35 mm off the 2.54 mm grid, so the holes below are rounded. Fix it in KiCad and regenerate.\n")
o.append("\n## 1. Place the parts (top side)\n\n**Male** = pin header: everything that connects with a wire or a plug from off the board (sensors, fans, buzzer, RTC, dimmer, supply). **Female** = socket: the WeAct G4 board, which plugs into the perfboard.\n")
PINS = {'2N7000': {'1': 'S', '2': 'G', '3': 'D'}, '2N2222A': {'1': 'E', '2': 'B', '3': 'C'}}   # TO-92, from the symbols
def flat_side(pt, bd):
    """Which way the flat face of a TO-92 points, in the top view of the board."""
    dx, dy = math.sin(pt['rot']), math.cos(pt['rot'])          # footprint flat side is +y
    if bd['i'] == 1: dx, dy = -dy, dx                           # board 2 is shown rotated
    if abs(dx) > abs(dy): return 'right' if dx > 0 else 'left'
    return 'down' if dy > 0 else 'up'
def short_type(r, pt, n):
    if r == 'A1': return '2 x 1x24 female socket'
    if r == 'PS1': return '4 male pins'
    if is_socket(pt): return f'1x{n:02d} male header'
    return {'R': 'resistor', 'Q': 'transistor', 'SW': 'push button', 'BZ': 'buzzer'}.get(prefix(r), kind(r)) + f" {pt['val']}"
for bd in boards:
    o.append(f"\n### Board {bd['i']+1}\n\n| Part | Type | Holes (column,row) |\n|---|---|---|\n")
    for r in refs_on(bd, lambda pt, rr: True):
        pt = parts[r]; ps = sorted([p for p in pt['pads'] if p['bd'] is bd], key=lambda p: (len(p['num']), p['num'], p['hole']))
        h = lambda p: f"({p['hole'][0]},{p['hole'][1]})"
        if prefix(r) == 'Q':
            where_ = ' '.join(f"{h(p)}={PINS.get(pt['val'], {}).get(p['num'], p['num'])}" for p in ps)
        elif prefix(r) == 'BZ':
            where_ = ' '.join(f"{h(p)}={'+' if p['fn'].startswith('+') else '-'}" for p in ps)
        elif r == 'A1':
            where_ = '; '.join(f"({min(q['hole'][0] for q in ps if q['hole'][1] == rw)},{rw}) to ({max(q['hole'][0] for q in ps if q['hole'][1] == rw)},{rw})" for rw in sorted({q['hole'][1] for q in ps}))
        elif is_socket(pt):
            where_ = '; '.join(f"{h(run[0])} to {h(run[-1])}" if len(run) > 1 else h(run[0]) for run in runs(ps))
        elif len(ps) == 3: where_ = f"{h(ps[0])} to {h(ps[-1])}"
        else: where_ = ', '.join(h(p) for p in ps)
        typ = short_type(r, pt, len(ps)) + (f", flat side {flat_side(pt, bd)}" if prefix(r) == 'Q' else '')
        o.append(f"| {r} | {typ} | {where_} |\n")
o.append("\n## 2. Solder the wires (back side, pin to pin)\n\nAll holes are **back** holes. Star: every pin of a net gets one wire to the net's **hub** pin (the `To pin` column). Max length is only set where it matters: wires between the boards (`B1 ↔ B2`) are limited to 300 mm. The other wires have no limit. Do `power` first, then `ground`, then `signal`.\n")
order = {'power': 0, 'ground': 1, 'signal': 2}
wires = []
for n in sorted(nets):
    for bd in boards:
        loc = [p for p in nets[n] if p['bd'] is bd]
        if len(loc) < 2: continue
        h = hub[(n, bd['i'])]
        for p in sorted(loc, key=lambda p: (part_sort(p['ref']), p['num'])):
            if p is h: continue
            kd, aw = wire_kind(n, p, h)
            if aw == '--': continue
            (c0, r0), (c1, r1) = back(p), back(h)
            wires.append((order[kd.split()[0].rstrip(',')] if kd.split()[0].rstrip(',') in order else 2, n, bd['i'], p, h, kd, aw, ''))
for n in sorted(nets):
    if (n, 0) in hub and (n, 1) in hub:
        a, b = hub[(n, 0)], hub[(n, 1)]; kd, aw = wire_kind(n, a, b, link=True)
        wires.append((order.get(kd.split()[0].rstrip(','), 2), n, 2, a, b, kd, aw, str(LINK_MAX_MM)))
wires.sort(key=lambda w: (w[2] == 2, w[0], w[2], w[1], part_sort(w[3]['ref'])))
wid = {}
o.append("\n| # | Board | AWG | Net | From pin | To pin | From hole | To hole | Max length (mm) |\n|---|---|---|---|---|---|---|---|---|\n")
for i, (_, n, bi, a, b, kd, aw, ln) in enumerate(wires, 1):
    wid.setdefault(id(a), []).append(i); wid.setdefault(id(b), []).append(i)
    board = 'B1 ↔ B2' if bi == 2 else f"B{bi+1}"
    o.append(f"| W{i:02d} | {board} | {aw} | {NETNAME.get(n, n)} | {lab(a)} | {lab(b)} | {where(a)[2:] if bi!=2 else where(a)} | {where(b)[2:] if bi!=2 else where(b)} | {ln} |\n")
o.append("\n## 3. Check list per part\n\nEvery pin and the wire numbers that touch it. `--` means no wire.\n")
for r in sorted(parts, key=part_sort):
    ps = [p for p in parts[r]['pads'] if p['bd']]
    if not ps: continue
    o.append(f"\n**{r}** {parts[r]['val']}: " + '; '.join(f"{p['num']}{(' '+p['fn']) if p['fn'] else ''} {where(p)} " + (', '.join(f'W{w:02d}' for w in wid.get(id(p), [])) or '--') for p in sorted(ps, key=lambda p: (len(p['num']), p['num'], p['hole']))) + "\n")
open(OUT, 'w').write(''.join(o))
print('wrote', OUT, len(nets), 'nets,', len(wires), 'wires')
