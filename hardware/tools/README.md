# place_parts.py: group placement for KiCad PCBs

KiCad has no auto-placement. `place_parts.py` moves the footprints of a
`.kicad_pcb` file into groups packed in rows, so no two courtyards overlap.
It can also draw a rectangular board outline on `Edge.Cuts`. It works on
any KiCad board, not only ClearAir.

It does not route tracks. It does not keep mains away from logic or put
connectors at the board edge by itself. Use a layout file for that (see
[Workflow](#recommended-workflow)).

## Requirements

- KiCad 10 (tested with 10.0.5). Other versions with the `pcbnew` Python
  API should work but are not tested.
- The board must already contain the footprints. In the PCB editor, run
  **Tools → Update PCB from Schematic** (F8) first. The script only moves
  footprints that are on the board.
- Close the board in KiCad before you write it in place. If the board is
  still open, KiCad overwrites the result on its next save.

## Running it

The script imports `pcbnew`, so it must run with the Python that ships with
KiCad. A normal `python3` gives:

```
error: cannot import pcbnew. Run this script with KiCad's Python, ...
```

Only the AppImage line is tested. The Windows and macOS lines are the usual
install paths; check yours.

| KiCad install | Python to use |
|---|---|
| Linux AppImage (this project) | `~/bin/kicad-10.0.5-x86_64.AppImage python3.11` |
| Linux distribution package | `python3` (if `python3 -c "import pcbnew"` works) |
| Windows | `"C:\Program Files\KiCad\10.0\bin\python.exe"` |
| macOS | `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3` |

The examples below use a shell variable for the AppImage. Run them from the
repository root:

```sh
K="$HOME/bin/kicad-10.0.5-x86_64.AppImage python3.11"
P=hardware/tools/place_parts.py
B=hardware/WeAct-G474CE-Long/clearair.kicad_pcb
```

`$K $P --help` prints every option and the layout file format.

## Quick start

```sh
# 1. See what is on the board: size, position, pad count and nets per part.
$K $P $B --list

# 2. Preview an automatic placement. Nothing is written.
$K $P $B --auto -n

# 3. Write it to a new file and open that file in KiCad to look at it.
$K $P $B --auto --outline 2.54 -o /tmp/placed.kicad_pcb

# 4. When you like the result, write it into the board (keeps a .bak copy).
$K $P $B --auto --outline 2.54 --in-place
```

## Two modes

### `--auto`: groups from the netlist

The script builds the groups by itself:

1. **Signal nets only.** Nets whose names match `--power-nets` (GND, VCC,
   VDD, VSS, VBAT, VIN, VBUS, `+5V`, `3V3`, `unconnected-...`) are ignored.
   Nets that touch more than `--max-net-parts` parts (default 8), such as
   buses, are also ignored.
2. **Hubs.** Parts with at least `--hub-pads` pads (default 16), for example
   an MCU board, go in a top row of their own. Without this, the MCU links
   every part into one big group.
3. **Groups.** Parts that share a signal net go in the same group. Inside a
   group the biggest part comes first, then always the part with the most
   nets shared with the parts already placed, so connected parts sit next
   to each other.
4. **Rotation.** Long 2 or 3 pin parts (axial resistors, diodes; width more
   than twice the height) are turned 90° so rows stay short. Other parts
   keep their rotation. `--no-rotate` turns this off.
5. **Single parts** with no signal links share one `misc` group.
6. **Packing.** Groups are packed into rows, tallest first, up to a target
   width. The width is `--width` if given, otherwise it comes from the total
   part area and `--aspect` (default 1.6). A group wider than the board is
   split into several rows.

Group names in auto mode are the reference of the first part in the group
(`U6`, `J5`, ...), plus `hubs` and `misc`.

### `--layout FILE`: groups you write

You choose every group, its position and the order of its parts. Use this
when the auto result is close but not right, or when placement must follow
rules the netlist cannot show (mains on one side, connectors at the edge).

## Layout file format

```jsonc
{
  "origin": [100, 60],      // board top-left in mm, page coordinates
  "grid": 2.54,             // snap pin 1 of each part to this pitch, 0 = off
  "gap": 1.27,              // default space between parts in a group, mm
  "groups": [
    {
      "name": "power",      // used in messages and with --only
      "at": [27.94, 22.86], // group top-left in mm, relative to origin
      "flow": "right",      // "right" = one row, "down" = one column
      "gap": 2.54,          // optional, overrides the default gap
      "rotation": 90,       // optional, rotation for every part in the group
      "refs": ["PS1@0", "U5@0", "R14", "R15"]
    }
  ]
}
```

(JSON has no comments. Remove the `//` parts in a real file.)

Rules:

- `"R14@90"` sets the rotation of one part. It wins over the group
  `rotation`.
- A part with no `@` gets the group `rotation`, or 0 when the group has
  none. This sets the rotation, it does not keep the old one.
- Rotation is in degrees, counter-clockwise, as in KiCad.
- Groups do not push each other. If two groups overlap, move their `at`.
  Check with `--outline` and DRC (see [Checking the result](#checking-the-result)).
- A part listed in no group stays where it is. The script prints a warning
  with the list.
- A reference that is not on the board is skipped with a warning.

## Samples

### Minimal layout: two rows

```json
{
  "origin": [50, 50],
  "grid": 2.54,
  "gap": 1.27,
  "groups": [
    { "name": "mcu",  "at": [0, 0],     "flow": "right", "refs": ["U1", "Y1", "C1", "C2"] },
    { "name": "pull", "at": [0, 15.24], "flow": "right", "rotation": 90, "refs": ["R1", "R2", "R3"] }
  ]
}
```

### Column of connectors along the left edge

```json
{ "name": "edge", "at": [0, 0], "flow": "down", "gap": 2.54, "refs": ["J1", "J2", "J3", "J4"] }
```

### ClearAir

`hardware/WeAct-G474CE-Long/placement.json` is a layout written for this
board, not generated by `--auto`: MCU and RTC on top, buttons and power (PSU, dimmer, zero-cross
divider) below, then the gas, I2C and fan groups, then the level shifters
and the buzzer driver.

```sh
$K $P $B -l hardware/WeAct-G474CE-Long/placement.json --outline 2.54 --in-place
```

Result: 35 parts, no overlaps, outline 117.6 × 71.5 mm.

## Recommended workflow

1. Let `--auto` do the first pass and save its groups:

   ```sh
   $K $P $B --auto --save-layout my_layout.json -n
   ```

2. Edit `my_layout.json`: rename groups, move them with `at`, reorder
   `refs`, change rotations, move mains parts away from logic.
3. Try it on a copy and open the copy in KiCad:

   ```sh
   $K $P $B -l my_layout.json --outline 2.54 -o /tmp/try.kicad_pcb
   ```

4. Repeat 2 and 3. To move one group only, add `--only NAME` (repeat it
   for more groups). The other parts stay where they are.
5. Close the board in KiCad and write it:

   ```sh
   $K $P $B -l my_layout.json --outline 2.54 --replace-outline --in-place
   ```

6. Fine-tune by hand in KiCad, then route.

## All options

| Option | Default | What it does |
|---|---|---|
| `board` | | Input `.kicad_pcb` file |
| `-a`, `--auto` | | Build the groups from the netlist |
| `-l`, `--layout FILE` | | Use groups from a JSON layout file |
| `--list` | | List footprints (size, position, pads, nets) and exit |
| `--only GROUP` | all | Place only this group; repeat for more |
| `-o`, `--output FILE` | | Write the result to a new file |
| `-i`, `--in-place` | | Overwrite the input board, keep `BOARD.kicad_pcb.bak` |
| `-n`, `--dry-run` | | Print the moves, write nothing |
| `--save-layout FILE` | | Write the layout used to JSON (works with `-n`) |
| `--outline MARGIN_MM` | | Draw an `Edge.Cuts` rectangle around all parts |
| `--replace-outline` | | Delete existing `Edge.Cuts` items before `--outline` |
| `--origin X Y` | `50 50` | Auto: board top-left in mm |
| `--grid MM` | `2.54` | Auto: snap pitch, 0 = off |
| `--gap MM` | `1.27` | Auto: space between parts |
| `--group-gap MM` | `2.54` | Auto: space between groups |
| `--width MM` | from area | Auto: target board width |
| `--aspect R` | `1.6` | Auto: width/height ratio when `--width` is not given |
| `--hub-pads N` | `16` | Auto: parts with at least N pads go in the hub row |
| `--max-net-parts N` | `8` | Auto: ignore nets touching more than N parts |
| `--power-nets REGEX` | GND, VCC, ... | Auto: net names ignored for grouping |
| `--no-rotate` | | Auto: keep every part's rotation |

You must give one of `-o`, `--in-place` or `-n`. The one exception is
`--save-layout` without `--outline`: alone, it saves the layout and acts as
a dry run.

## Tuning `--auto`

| Problem | Try |
|---|---|
| Board too tall and narrow | `--width 120` or a larger `--aspect` |
| Everything ends up in one big group | Lower `--hub-pads`, or `--max-net-parts 4` |
| Power parts pulled into one group | Add your rail names: `--power-nets '(?i)^(gnd\|vcc\|\+12v\|vmot)$'` |
| An MCU module is not in the hub row | Lower `--hub-pads` below its pad count (see `--list`) |
| Parts too close for hand soldering | `--gap 2.54 --group-gap 5.08` |
| SMD board, no 0.1" grid | `--grid 0` or `--grid 0.5` |

A custom `--power-nets` replaces the default, so include GND and the other
rails in it too. KiCad may prefix net names with a sheet path such as
`/Power/+5V`; match that if your names have it.

## Checking the result

The script itself checks nothing after it writes. Check with KiCad's DRC:

```sh
A=~/bin/kicad-10.0.5-x86_64.AppImage
$A kicad-cli pcb drc /tmp/placed.kicad_pcb -o /tmp/drc.rpt
grep -E '^\[' /tmp/drc.rpt | sed 's/\].*/]/' | sort | uniq -c
```

On an unrouted board, `unconnected_items` is expected. `courtyards_overlap`
means two parts collide: move a group. `silk_overlap` is cosmetic.

## Troubleshooting

| Message or symptom | Cause and fix |
|---|---|
| `cannot import pcbnew` | Wrong Python. Use KiCad's Python (see [Running it](#running-it)) |
| Result gone after opening KiCad | The board was open in KiCad and KiCad saved over it. Close it first, restore from `.bak` |
| `reference X is used by more than one footprint` | Duplicate references. Those parts are not moved. Annotate the schematic again and update the PCB |
| `X is not on the board, skipped` | Layout lists a reference that the board does not have. Update the PCB from the schematic, or fix the layout |
| `not in any group, left where they were` | Parts missing from the layout. Add them to a group |
| `board already has N Edge.Cuts item(s)` | An outline exists. Add `--replace-outline` to delete it and draw a new one |
| Parts overlap after `-l` | Two groups overlap. Change their `at`. Footprints with no courtyard use their body box, which may be smaller than the real part |
| `swig/python detected a memory leak ...` at exit | Comes from KiCad's Python bindings. Harmless |
| Positions a little off the numbers in the layout | Pin 1 snaps to `grid`, so a part can move up to half a grid step |

## Undo

- `--in-place` keeps the previous board as `BOARD.kicad_pcb.bak`. Restore it
  with `cp BOARD.kicad_pcb.bak BOARD.kicad_pcb`.
- The board is in git, so `git checkout -- BOARD.kicad_pcb` also works if
  you have not committed.
