# KiCad PCB tools

Five scripts for any KiCad 10 board:

- [`place_parts.py`](#place_partspy-group-placement): places footprints in
  groups, keeps the parts you moved by hand.
- [`route_board.py`](#route_boardpy-autorouting-with-freerouting): autoroutes
  the board as it is with Freerouting.
- [`make_carrier.py`](#make_carrierpy-printable-carrier-for-prusaslicer):
  turns the board into a printable plate (holes for pins, grooves for
  wires) for PrusaSlicer.
- [`wire_list.py`](#wire_listpy-perfboard-build-instructions): writes the
  build instructions for a hand-wired perfboard (where each part goes, which
  pin connects to which pin, with the wire gauge).
- [`verify_perfboard.py`](#verify_perfboardpy-check-the-perfboard-instructions):
  checks that build instructions match the board and the schematic, before
  you solder.

## The whole sequence (best practice)

From schematic to printed carrier. Do the steps in this order. Run every
command from the repository root, with these variables set once per shell:

```sh
K="$HOME/bin/kicad-10.0.5-x86_64.AppImage python3.11"   # KiCad's Python
A="$HOME/bin/kicad-10.0.5-x86_64.AppImage"              # for kicad-cli
T=hardware/tools
B=hardware/WeAct-G474CE-Long/clearair.kicad_pcb
```

**Rule for every step that writes the board: save and close KiCad first.**
If KiCad has the board open (there is a `~clearair.kicad_pcb.lck` file next
to it), it overwrites the script's result on its next save.

1. **Once per machine:** install the [external tools](#external-tools), then
   get Freerouting:

   ```sh
   $K $T/route_board.py --download
   ```

2. **Schematic changed?** In KiCad's PCB editor run **Tools → Update PCB
   from Schematic** (F8), save, close KiCad. New parts land off the board;
   step 3 places them.

3. **Place new parts.** Only for a new board or new parts: `--auto` makes a
   first layout from the netlist, then you move parts in KiCad.

   ```sh
   $K $T/place_parts.py $B --auto --in-place        # new board only
   ```

4. **Adjust by hand in KiCad.** Set the grid to 2.54 mm first (**View → Grid
   Settings**), so pins stay on the 0.1" grid. Move parts, save, close
   KiCad.

5. **Snap to the grid.** The board is the source of truth, no layout file.
   Every part moves so its pin 1 is on the grid (up to 1.27 mm):

   ```sh
   $K $T/place_parts.py $B --snap --in-place
   ```

6. **Check:** no overlaps, pins on the grid. Only footprints that can never
   be on the grid should remain (see [Grid and header pins](#grid-and-header-pins)).

   ```sh
   $K $T/place_parts.py $B --check
   ```

7. **No 3D printer? Build a perfboard instead.** Skip the carrier below and step 8, and
   write the build instructions (`perfboard_wiring.md` next to the board):

   ```sh
   cd hardware/WeAct-G474CE-Long && python3 ../tools/wire_list.py
   ```

   See [wire_list.py](#wire_listpy-perfboard-build-instructions). Then check
   the result before you solder (needs only `python3`):

   ```sh
   python3 ../tools/verify_perfboard.py clearair.kicad_pcb --kicad-cli "$A kicad-cli"
   ```

   See [verify_perfboard.py](#verify_perfboardpy-check-the-perfboard-instructions).

   **Build the printable carrier (needs a 3D printer).** This routes a copy of the board (your
   board file is not changed) and cuts the grooves:

   ```sh
   $K $T/make_carrier.py $B --route -o hardware/WeAct-G474CE-Long/carrier/clearair_carrier.stl
   ```

   It writes `clearair_carrier.stl` and deletes the routed copy. Add
   `--keep-routed` to keep it as `clearair_carrier.routed.kicad_pcb`, then
   open it in KiCad to see the wire paths; any connection it reports as
   unrouted has no groove.

8. **Print.** In PrusaSlicer: **File → Import → Import STL/3MF/STEP/OBJ…**
   (Ctrl+I), pick the STL, keep it flat (top face up), slice, print. See
   [Printing](#printing).

9. **Commit** the board and the carrier files, so you can
   go back to any step.

Repeat from step 2 when the schematic changes, from step 4 when you only
move parts.

## External tools

| Tool | Needed by | Version tested | Install |
|---|---|---|---|
| KiCad (its Python with `pcbnew`, and `kicad-cli`) | all three | 10.0.5 AppImage | [kicad.org/download](https://www.kicad.org/download/); this project uses `~/bin/kicad-10.0.5-x86_64.AppImage` |
| FreeCAD 1.0 or newer | `make_carrier.py` | 1.1.3 AppImage | [freecad.org/downloads](https://www.freecad.org/downloads.php); the script finds `freecadcmd` on PATH or `~/bin/freecad` (AppImage) |
| PrusaSlicer | printing | 2.7.4 AppImage | [prusa3d.com/prusaslicer](https://www.prusa3d.com/page/prusaslicer_424/) |
| Java (JRE) 17 or newer | `route_board.py`, `make_carrier.py --route` | OpenJDK 21 | `sudo apt install openjdk-21-jre` |
| Freerouting **1.9.0** jar | `route_board.py`, `make_carrier.py --route` | 1.9.0 | `route_board.py --download` (saves `~/.local/share/freerouting/freerouting-1.9.0.jar`) |
| ImageMagick (`magick` or `convert`) | `route_board.py --render x.png` | 7.1.1 | `sudo apt install imagemagick`. Not needed for `--render x.svg` |
| `xvfb-run` | `route_board.py` with no display (SSH, CI) | not tested | `sudo apt install xvfb` |

`kicad-cli` is also used for DRC (see [Checking the result](#checking-the-result)).
With the AppImage it is `~/bin/kicad-10.0.5-x86_64.AppImage kicad-cli`.

Freerouting 2.x does not work with `route_board.py`: 2.0 to 2.1 ignore the
pass limit from the command line and never stop, and 2.2 and newer need
Java 25.

# place_parts.py: group placement

KiCad has no auto-placement. `place_parts.py` moves the footprints of a
`.kicad_pcb` file into groups packed in rows, so no two courtyards overlap.
It can also draw a rectangular board outline on `Edge.Cuts`. It works on
any KiCad board, not only ClearAir.

It does not route tracks (use [`route_board.py`](#route_boardpy-autorouting-with-freerouting)
for that). It does not keep mains away from logic or put connectors at the
board edge by itself. Use a layout file for that (see
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
  ],
  "fixed": {                // optional, parts moved by hand, written by --capture
    "U6": [75.5, 21.0, -90] // anchor x, y in mm relative to origin, rotation
  }
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
- A part under `fixed` still takes its place in its group, so the parts
  after it do not shift. Then it moves to its `fixed` spot, with pin 1
  snapped to `grid`. Delete its `fixed` entry to give it back to the group.

## Keeping your manual changes (`--capture`)

This is only for boards you place with a layout file. If the board is the source of truth, you do not need it: move parts in KiCad and run `--snap` ([step 5](#the-whole-sequence-best-practice)).

After `place_parts.py` runs, you will move some parts by hand in KiCad.
Running the layout again would put them back. To keep them, save the
board, close KiCad, and run:

```sh
$K $P $B -l my_layout.json --capture
```

```
capture: U6 fixed at (75.5, 21.0) @-90.0 (relative to origin)
capture: M2 fixed at (59.17, 55.96) @0.0 (relative to origin)
...
layout: my_layout.json (10 fixed part(s))
```

`--capture` compares every part with where its group would put it. Each
part that differs, or that is in no group, goes under `fixed` with its
current spot, moved so pin 1 is on `grid` (see [Grid and header pins](#grid-and-header-pins)).
A part you moved back to its group spot is removed from `fixed`. The board
is not changed, only the layout file. Running the layout again then gives
your board, with every hand-placed part on the grid.

Use `--save-layout FILE` with `--capture` to write a new file and keep the
old layout.

To move a hand-placed part with its group again, delete its line from
`fixed`.

`route_board.py` needs nothing like this: it routes the board file as it
is saved and does not move parts.

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

6. Fine-tune by hand in KiCad. Save, close KiCad, and record your moves
   with `--capture` (see [Keeping your manual changes](#keeping-your-manual-changes---capture)).
7. Route with `route_board.py`.

## All options

| Option | Default | What it does |
|---|---|---|
| `board` | | Input `.kicad_pcb` file |
| `-a`, `--auto` | | Build the groups from the netlist |
| `-l`, `--layout FILE` | | Use groups from a JSON layout file |
| `--list` | | List footprints (size, position, pads, nets) and exit |
| `--check` | | Report courtyard overlaps and numbered pins off `--grid`, then exit (exit code 1 if any) |
| `--only GROUP` | all | Place only this group; repeat for more |
| `-o`, `--output FILE` | | Write the result to a new file |
| `-i`, `--in-place` | | Overwrite the input board, keep `BOARD.kicad_pcb.bak` |
| `-n`, `--dry-run` | | Print the moves, write nothing |
| `--save-layout FILE` | | Write the layout used to JSON (works with `-n`) |
| `--capture` | | With `-l`: save parts moved by hand under `fixed` in the layout file; the board is not changed |
| `--outline MARGIN_MM` | | Draw an `Edge.Cuts` rectangle around all parts |
| `--replace-outline` | | Delete existing `Edge.Cuts` items before `--outline` |
| `--origin X Y` | `50 50` | Auto: board top-left in mm |
| `--snap` | | Move every part so pin 1 is on `--grid`, keeping the board as it is, no layout file |
| `--grid MM` | `2.54` | Auto and `--check`: snap pitch, 0 = off |
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

## Grid and header pins

Pins that take 2.54 mm (0.1") headers or perfboard holes must sit on a
2.54 mm grid. With `"grid": 2.54` the script snaps **pin 1** of each part
to the grid, not the footprint anchor: some footprints (the WeAct board,
the RTC module) put the anchor between pins, which would leave every pin
1.27 mm off. All other pins land on the grid too when the footprint's pin
pitch is a multiple of 2.54.

The grid starts at page 0,0 (KiCad's default grid origin), not at the
layout `origin`.

Some footprints can never be fully on the grid:

| Footprint | Why | Fix |
|---|---|---|
| `TO-92_Inline` (Q1–Q3) | 1.27 mm pin pitch, middle pin is between grid points | Use `Package_TO_SOT_THT:TO-92_Inline_Wide` (2.54 mm pitch, legs bent out) in the schematic |
| `SW_PUSH_6mm` (SW1, SW2) | Pins 6.5 × 4.5 mm apart | Leave it if no header goes there, or pick a button footprint with 2.54 mm pitch |
| Unnumbered pads (mounting holes of PS1, U5, U6) | Not pins | Nothing; `--check` ignores them |

Parts you move by hand get snapped by `--snap`. If you move them in KiCad on
a finer grid, `--snap` puts each one with pin 1 on the nearest 2.54 grid
point, so a part can move up to 1.27 mm from where you left it. To avoid
that, set KiCad's grid to 2.54 mm (**View → Grid Settings**, or the grid box
in the top toolbar) before you move parts.

With a layout file, use `--capture` and then run the layout once
(`-l ... --in-place`) so the board matches the file.

Check a board:

```sh
$K $P $B --check
```

```
overlaps: 0
off grid: Q1 pin(s) 2
off grid: SW1 pin(s) 1 2
footprints with numbered pins off the 2.54 mm grid: 2
```

It lists courtyard overlaps and numbered pins off `--grid` (default 2.54),
and exits with 1 if it finds any. It changes nothing.

## Checking the result

Use `--check` (above) for overlaps and the pin grid. For the rest, run
KiCad's DRC:

```sh
A=~/bin/kicad-10.0.5-x86_64.AppImage
$A kicad-cli pcb drc /tmp/placed.kicad_pcb -o /tmp/drc.rpt
grep -E '^\[' /tmp/drc.rpt | sed 's/\].*/]/' | sort | uniq -c
```

On an unrouted board, `unconnected_items` is expected. `courtyards_overlap`
means two parts collide: move a group. `silk_overlap` is cosmetic.
`lib_footprint_issues` ("does not include the footprint library") appears
when the board is checked outside its project folder, so KiCad does not
find the project's `fp-lib-table`; run DRC on the board inside the project.

To look at the board without opening KiCad, render it:

```sh
$A kicad-cli pcb export svg $B -l F.Cu,B.Cu,F.Silkscreen,F.Courtyard,Edge.Cuts \
   --mode-single --fit-page-to-board -o /tmp/board.svg
magick -density 200 -background white /tmp/board.svg -flatten /tmp/board.png
```

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
| `Debug: Adding duplicate image handler for 'PNG file'` (and more) | Comes from KiCad's wxWidgets when a board is saved. Harmless |
| Positions a little off the numbers in the layout | Pin 1 snaps to `grid`, so a part can move up to half a grid step |
| Is the board open in KiCad? | KiCad leaves `~BOARD.kicad_pcb.lck` next to the board while it is open. No lock file = safe to write |

## Undo

- `--in-place` copies the board to `BOARD.kicad_pcb.bak` before it writes.
  Each run overwrites the `.bak`, so it holds only the version just before
  the last run. Restore it with `cp BOARD.kicad_pcb.bak BOARD.kicad_pcb`.
- The board is in git, so `git checkout -- BOARD.kicad_pcb` brings back the
  last committed version.
- `--capture` rewrites the layout file without a backup. Commit the layout
  file to git so you can go back.

# route_board.py: autorouting with Freerouting

## Ratsnest and tracks

After placement, KiCad draws thin straight lines from pad to pad. That is
the **ratsnest**: it only shows which pads must be connected. It runs at
any angle, follows the parts when they move, and is not a wire. A board
has wires only after **routing**, which draws tracks (copper, or the paths
you will wire by hand on a carrier).

There are three ways to route:

1. **By hand in KiCad.** Open the board, press `X` (Route Single Track),
   click a pad and follow its ratsnest line to the target pad. The router
   keeps tracks at 45/90°. Press `V` while routing to change copper layer
   (F.Cu/B.Cu); that places a via.
2. **Freerouting from inside KiCad.** Install the Freerouting plugin from
   **Tools → Plugin and Content Manager**, then click its button in the PCB
   editor. Or by hand: **File → Export → Specctra DSN**, run
   `java -jar freerouting-1.9.0.jar -de board.dsn -do board.ses -mp 30 -da`,
   then **File → Import → Specctra Session**.
3. **`route_board.py`** does option 2 for you, without opening KiCad.

`route_board.py` routes a placed board. It exports the board as a Specctra
DSN file, runs the [Freerouting](https://github.com/freerouting/freerouting)
autorouter, imports the routed session (SES) back into the board and saves
it. Tracks come out at 45/90°. It works on any `.kicad_pcb` file.

## Requirements

- KiCad's Python, as for `place_parts.py`.
- Java 17 or newer (`java -version`).
- Freerouting **1.9.0**. Get it once:

  ```sh
  $K hardware/tools/route_board.py --download
  ```

  This saves `~/.local/share/freerouting/freerouting-1.9.0.jar`. Use
  `--jar` or `FREEROUTING_JAR` for another location. Newer releases do not
  work here: 2.x ignores the pass limit from the command line and never
  stops, and 2.2+ needs Java 25.
- A display. Freerouting 1.9.0 opens a small progress window while it
  routes. Without a display (SSH, CI), install `xvfb-run`; the script uses
  it on its own.

## Use

```sh
R=hardware/tools/route_board.py

# Route into a new file and render a picture to look at.
$K $R $B -o /tmp/routed.kicad_pcb --render /tmp/routed.png

# Throw away the old tracks and route again, in place (keeps a .bak copy).
$K $R $B --clear --in-place
```

Output:

```
routing: up to 30 passes, timeout 600 s (log: /tmp/route_board_.../freerouting.log)
result: 271 track segments, 3 vias, 1677 mm of track, 3 unrouted connections
written: /tmp/routed.kicad_pcb
render: /tmp/routed.png
```

Without `--clear`, existing tracks go to Freerouting too and it routes
around them.

## Options

| Option | Default | What it does |
|---|---|---|
| `board` | | Input `.kicad_pcb` file |
| `-o`, `--output FILE` | | Write the routed board to a new file |
| `-i`, `--in-place` | | Overwrite the input board, keep `BOARD.kicad_pcb.bak` |
| `--clear` | | Delete existing tracks and vias before routing |
| `--passes N` | `30` | Maximum autorouter passes |
| `--threads N` | Freerouting | Optimizer threads |
| `--timeout S` | `600` | Stop Freerouting after S seconds |
| `--render FILE` | | Render copper, silkscreen and outline to `.png` (needs ImageMagick) or `.svg` |
| `--keep DIR` | temp dir | Keep the DSN, SES and log files in DIR |
| `--jar FILE` | `~/.local/share/freerouting/freerouting-1.9.0.jar` | Freerouting jar (or `$FREEROUTING_JAR`) |
| `--java PROG` | `java` on PATH | Java program |
| `--kicad-cli PROG` | next to KiCad's Python | `kicad-cli` used by `--render` |
| `--download` | | Download Freerouting 1.9.0 to `--jar` |

The script passes `-da` to Freerouting, which turns off its usage
analytics.

## After routing

1. Run DRC (see [Checking the result](#checking-the-result)).
   `unconnected_items` now lists the connections the router could not
   make. Route those by hand with `X` in KiCad.
2. Track width and clearance come from the board's net classes
   (**File → Board Setup → Net Classes**). Set them before routing, for
   example wider power tracks.
3. An autorouted board works but is not tidy (see below).

## Will the tracks be easy to follow?

Freerouting always makes 45/90° tracks, so the angles are never the
problem. Whether a track is easy to follow by eye depends on the placement:

- **Short links inside a group** (a header and its divider resistors) are
  a few mm long and easy to follow.
- **Long links to the MCU** are hard. When a group does not sit near the
  MCU pins it uses, its tracks run 50–60 mm across the board on diagonals
  and bundle in the narrow channels between parts. Following one track
  inside a bundle is the hard part.

To make them easier:

- Put each group next to the side of the MCU where its pins are, in pin
  order (edit `at` and `refs` in the layout), so most tracks run short
  and straight.
- Leave wider channels: a larger group gap (for example `"gap": 5.08`
  between groups) gives the tracks room to spread out.

Crossings are not a problem in themselves: on two layers the router passes
under with a via; on a hand-wired carrier, wires cross freely.

## Tracks as grooves (3D-printed carrier)

For a printed carrier with grooves for the wires, use the routed tracks
(not the ratsnest) as the groove paths. Export them as DXF, in mm, and
import the DXF into FreeCAD to cut the grooves:

```sh
A=~/bin/kicad-10.0.5-x86_64.AppImage
$A kicad-cli pcb export dxf /tmp/routed.kicad_pcb -l F.Cu,Edge.Cuts \
   --mode-single --ou mm -o /tmp/top_tracks.dxf
$A kicad-cli pcb export dxf /tmp/routed.kicad_pcb -l B.Cu,Edge.Cuts \
   --mode-single --ou mm -o /tmp/bottom_tracks.dxf
```

Each copper layer goes to its own file, so top and bottom grooves stay
apart. The DXF also holds the pads. There is no script for the groove
geometry yet.

## ClearAir routing status

Routing the ClearAir board (parts placed with the layout tools, 2 layers, default
net class) gives:

```
result: 271 track segments, 3 vias, 1677 mm of track, 3 unrouted connections
```

The 3 unrouted connections:

- **2 come from the A1 footprint** (`WeAct_STM32G474CoreBoard_Long` in the
  `libraries` footprint library, `~/kicad/libraries`). Its pad 24 (NRST)
  and pad 52 (+3V3) are at the same spot. DRC reports this as
  `shorting_items`, `solder_mask_bridge` and `holes_co_located`, and the
  router cannot connect either pad. Moving A1 does not help: fix the
  footprint.
- **1 is the long PA9 link** from A1 to R20. Route it by hand with `X`.

## Troubleshooting

| Message or symptom | Cause and fix |
|---|---|
| `Freerouting jar not found` | Run with `--download`, or give `--jar` |
| `Freerouting needs a display` | No `DISPLAY`. Use a desktop session or install `xvfb-run` |
| `UnsupportedClassVersionError` in the log | The jar needs a newer Java. Use Freerouting 1.9.0 |
| `Freerouting did not finish in 600 s` | Raise `--timeout` or lower `--passes` |
| `Freerouting failed:` plus log lines | Read the full log: run again with `--keep DIR` |
| Same few connections always unrouted | Often a footprint problem, e.g. two pads of different nets in the same place. Check DRC `shorting_items` |
| Result gone after opening KiCad | The board was open in KiCad. Close it before `--in-place`, restore from `.bak` |
| A window opens while it runs | Freerouting 1.9.0 shows its progress window. It closes when routing is done |
| `New version available: v2.5.0` in the log | Freerouting checks for updates. Ignore it; 2.x does not work with this script |
| Freerouting 2.x runs forever, never writes the SES | 2.0 to 2.1 ignore the pass limit. Use 1.9.0 |

# make_carrier.py: printable carrier for PrusaSlicer

`make_carrier.py` turns a board into a 3D-printable plate:

- the board outline (from `Edge.Cuts`),
- a hole at every through-hole pad and via, for pins and headers,
- a groove along every track: tracks on `F.Cu` are cut into the top face,
  tracks on `B.Cu` into the bottom face. Lay the wires in the grooves.

It writes an STL or 3MF file. The board file is never changed.

How it works: KiCad's Python reads the outline, holes and tracks, then
FreeCAD (no window) builds the solid, cuts everything in one boolean cut
and meshes it with FreeCAD's standard mesher, which gives a closed mesh.

## Requirements

- KiCad's Python, as for the other scripts.
- FreeCAD 1.0 or newer (see [External tools](#external-tools)).
- For grooves, a routed board. `--route` routes a copy with
  `route_board.py` first, so it also needs Java and Freerouting.

## Use

```sh
C=hardware/tools/make_carrier.py

# Route a copy and build the carrier (the usual way).
$K $C $B --route -o hardware/WeAct-G474CE-Long/carrier/clearair_carrier.stl

# Board already routed (by hand or with route_board.py): no --route.
$K $C /tmp/routed.kicad_pcb -o /tmp/carrier.stl

# Plate with holes only, no grooves.
$K $C $B --no-grooves -o /tmp/plate.stl
```

Output for ClearAir:

```
routing with route_board.py ...
result: 281 track segments, 5 vias, 1789 mm of track, 2 unrouted connections
written: /tmp/make_carrier_.../routed.kicad_pcb
building in FreeCAD: 158 holes, 281 groove segments (log: /tmp/make_carrier_.../freecad.log)
carrier: volume 17342 of 20244 mm3 plate, 193382 facets, closed mesh: True, valid solid: True
plate: 92.3 x 73.1 x 3.0 mm
written: .../carrier/clearair_carrier.stl
```

It takes about 45 s (routing 15 s, FreeCAD 30 s). `closed mesh: True` means
PrusaSlicer will load it without repairs.

With `--route`, the routed copy is deleted after the build. Add
`--keep-routed` to write it next to the output as `NAME.routed.kicad_pcb`,
then open it in KiCad to see where each groove goes. Your board file is
never changed.

## Options

| Option | Default | What it does |
|---|---|---|
| `board` | | Input `.kicad_pcb` file |
| `-o`, `--output FILE` | required | Output mesh, `.stl` or `.3mf` |
| `--route` | | Route a copy with `route_board.py` first (replaces its tracks) |
| `--keep-routed` | | With `--route`, keep the routed copy as `NAME.routed.kicad_pcb` next to the output |
| `--passes N` | `30` | Autorouter passes with `--route` |
| `--thickness MM` | `3.0` | Plate thickness |
| `--groove-width MM` | `1.2` | Groove width (fits insulated 24 AWG wire) |
| `--groove-depth MM` | `1.2` | Groove depth, on each face |
| `--hole-clearance MM` | `0.3` | Added to every drill diameter, because printed holes come out small |
| `--layers LIST` | `F.Cu,B.Cu` | Copper layers that become grooves |
| `--no-grooves` | | Plate and holes only |
| `--mesher` | `standard` | `standard`: fast, closed mesh. `netgen`: slower; on a dense board it can put stray triangles outside the plate (the script checks and falls back to `standard`) |
| `--deflection MM` | `0.02` | Accuracy of the `standard` mesher |
| `--freecad CMD` | auto | Command that runs a FreeCAD script without a window, e.g. `'~/bin/freecad freecadcmd'` |
| `--keep DIR` | temp dir | Keep the JSON, FreeCAD script and log in DIR |

## Choosing the sizes

| Size | Rule |
|---|---|
| Groove width | Wire outer diameter + 0.2 mm. 24 AWG solid with PVC is about 1.0 mm, so 1.2 mm. 22 AWG: about 1.4 mm |
| Groove depth | At least the wire diameter, so the wire sits below the surface |
| Thickness | More than 2 × groove depth when both faces have grooves. Where a top and a bottom groove cross, the plate is only `thickness − 2 × depth` thick (0.6 mm with the defaults). The script warns when it would cut through |
| Hole clearance | Header pins are 0.64 mm square (0.9 mm across the corners) and the footprints drill 1.0 mm, so 1.3 mm holes. Print a test piece and change it if pins are loose or do not go in |

Where a groove passes very close to a hole, the wall between them can be
thinner than one extrusion line; the slicer drops it, and the groove opens
into the hole. That is harmless for wiring.

## Printing

- **Orientation:** flat, top face up, as it comes in. Do not flip it: the
  pins and the KiCad view match the top face.
- **Bottom grooves** face the bed. They print as short bridges (1.2 mm
  wide), so no supports are needed. Turn supports off.
- **Layer height:** 0.2 mm gives cleaner grooves than 0.3 mm.
- **Material:** PLA or PETG. Use PETG near the AC side (mains, TRIAC, PSU):
  it softens at a higher temperature.
- **Holes too tight:** raise `--hole-clearance` (for example 0.4) and build
  again, or set **Print Settings → Advanced → XY Size Compensation** in
  PrusaSlicer to a small negative value (affects the whole part).
- **3MF instead of STL:** `-o carrier.3mf` gives a smaller file; PrusaSlicer
  opens both.

PrusaSlicer's default profile (0.3 mm layers) slices the ClearAir carrier
in about 1 h 45 min.

## ClearAir carrier

`hardware/WeAct-G474CE-Long/carrier/` holds the current printable file
`clearair_carrier.stl` (92.3 × 73.1 × 3.0 mm, closed mesh). The routed copy
it was built from is not kept; build with `--keep-routed` to see it. Two connections have no groove: the A1 footprint
puts pad 24 (NRST) and pad 52 (+3V3) at the same spot, so the router cannot
connect them (see [ClearAir routing status](#clearair-routing-status)).
Wire those two by hand.

Build it again after every placement change (step 7 of
[the whole sequence](#the-whole-sequence-best-practice)).

## Troubleshooting

| Message or symptom | Cause and fix |
|---|---|
| `FreeCAD not found` | Install FreeCAD, put `freecadcmd` on PATH, or give `--freecad` |
| `the board has no closed Edge.Cuts outline` | Draw one: `place_parts.py ... --outline 2.54` |
| `the board has no tracks ... so there are no grooves` | Add `--route`, or route the board first |
| `FreeCAD did not write the mesh:` plus lines | Read the full log: run again with `--keep DIR`, see `DIR/freecad.log` |
| `closed mesh: False` | Use the default `--mesher standard`. PrusaSlicer repairs small mesh errors on load anyway |
| `netgen failed ...` or `netgen mesh reaches outside the plate, using the standard mesher` | Only with `--mesher netgen`. The script switched to the standard mesher; nothing to do |
| Plate mirrored | It is not: the plate is the top view. Print it top face up |
| `routing failed` | See the `route_board.py` messages above it and [its troubleshooting](#troubleshooting-1) |

---

# wire_list.py: perfboard build instructions

Reads the board file and writes `perfboard_wiring.md`: everything you need to
build the circuit on 2.54 mm perfboard by hand. It uses plain Python and
needs no KiCad. It does not change the board.

## Use

Run it from the board folder (after you place the parts, step 4 above):

```sh
cd hardware/WeAct-G474CE-Long
python3 ../tools/wire_list.py                       # clearair.kicad_pcb -> perfboard_wiring.md
python3 ../tools/wire_list.py BOARD.kicad_pcb OUT.md
```

Run it again after you move parts. The file is generated, so do not edit it
by hand.

## Boards

It builds one perfboard per `Edge.Cuts` rectangle (sorted left to right), so
draw each board's **hole area** as one rectangle: for a 24 x 18 hole board
that is 58.42 x 43.18 mm. A part belongs to the board that holds its pins.
A portrait board (taller than wide) is shown rotated 90° clockwise so every
board lies landscape.

## What is in the file

1. **Parts (top side).** One table per board: part, type (for example
   `1x06 male header`, `resistor 4k7`, `transistor 2N7000`) and the holes to
   place it at, as column letter + row number (`E7`). Male headers are for everything that
   connects from off the board with a wire or plug; the MCU module (`A1`)
   plugs into female sockets.
2. **Wires (back side).** Three tables (board 1, board 2, wires between the boards), each sorted by AWG (thick first), then net (voltage rails first, then ground, then signals). One row per wire: number, board, net, from pin and hole,
   to pin and hole, **AWG** and max length. Every pin of a net is wired to the nearest pin of the same net that is
   already connected, so no hole gets more than 3 wire ends (`max_wires_per_hole`).
   Voltage and ground nets with at least `bus_min_pads` (4) connections, counting
   the board link, get a bus strip instead: a free row of holes (between the
   socket rows of the MCU module, but not in the rows right next to the sockets,
   if the board has one; short strips share a row with one hole of gap, and strips
   in neighbouring rows do not run over the same columns; else next to the parts
   with `Role` = `bus`) joined by one bare wire, with one short wire from each
   pin to its own hole of the strip.
   The pins of the MCU module are joined inside it, so each is a start point.
   A wire is thick when any wire behind it is thick. One wire per net joins the two boards.
3. **Check list per part.** One table per part: every pin with its name, net, hole and the wire numbers that touch it.

A hole is its column letter plus its row number, like `E7`. Columns are
letters along the long side (A to X for 24 columns), rows are numbers along
the short side. Looking at the component side with the long side
horizontal, the corner A + last row is at the top right: column A is at the
right and row 1 at the bottom. A hole has the same name from both sides:
from the solder side the board is turned over left to right, so A is then
at the left. Wires are numbered `#01`, `#02`, ... so they cannot be
mistaken for holes like `W15`.

## Part data in the schematic

The script reads the `.kicad_sch` next to the board file. No config file is
needed: the part data are hidden fields on the schematic symbols. Without a
schematic it takes the part with the most pins as the MCU module and uses
AWG24 / AWG30 for the wires.

| Field | Meaning |
| :--- | :--- |
| `Role` | Space-separated words. `mcu`: start of every net, no wire between its own pins. `female`: a socket the module plugs into. `header`: male header without a `PinHeader` footprint. `post`: loose male pins (supply). `bus`: bus strips are placed next to this part (boards without an MCU module). `sensor`: power and ground wires get the thick wire. `heavy`: same, for fan, buzzer and supply parts |
| `Optional` | Free text, for example `RTC, planned`: hardware for a later stage. Every wire that ends on this part is marked `optional: <text>` in the Note column, sorted after the required wires of its table, and the part is marked optional in the part tables. The wires are still listed, so you can leave them out |
| `Bus area` | On a part with `Role` = `bus`: the strips of its board stay inside this rectangle, given as two corner hole names, for example `A14:Q18` |
| `Net <pin>` | Readable name for the net KiCad names after that pin, for example `Net PA0` = `MQ131 out` names `Net-(A1-PA0)` |

Transistor pin letters come from the symbol's pin names. The two gauges are
defaults in the script (`AWG24`, `AWG30`), and the
longest wire between two boards is `link_max_mm` (300), and the most wire ends in one hole is `max_wires_per_hole` (3).

An optional `wire_list.json` next to the board (or its path as the third
argument) still overrides any of these keys: `mcu`, `female`, `headers`,
`posts`, `sensors`, `high_current_prefixes`, `transistor_pins`, `net_names`,
`link_max_mm`, `max_wires_per_hole`, `bus_min_pads` (0 = no strips), `bus_near`, `awg_thick`, `awg_thin`. ClearAir does not use one.

## Wire gauge

Power and ground wires are thick (`awg_thick`) when they feed the supply, the
MCU module, a high-current part or a `sensors` part, and for the ground wire
between boards. Everything else is thin (`awg_thin`). The rules are in
`wire_kind()` in the script.

## Check the layout first

If a pin is more than 0.35 mm off the 2.54 mm grid, the file starts with a
warning listing the parts, and the holes are rounded. Fix the layout (see
[Grid and header pins](#grid-and-header-pins)) and run it again.

# verify_perfboard.py: check the perfboard instructions

Run it after `wire_list.py` and before you solder. It reads the board, the
schematic and `perfboard_wiring.md`, and recomputes every hole from the pad
positions itself, so it catches mistakes in the instructions. It uses only
the Python standard library.

```sh
cd hardware/WeAct-G474CE-Long
python3 ../tools/verify_perfboard.py clearair.kicad_pcb --kicad-cli "$HOME/bin/kicad-10.0.5-x86_64.AppImage kicad-cli"
```

| Check | What fails it |
| :--- | :--- |
| 1. Pads | a pad outside every board or inside two, or off the 2.54 mm grid |
| 2. Holes | two pads in one hole |
| 3. Check list | a hole in section 3 that differs from the pad position (solder side mirrored left-right, portrait board turned 90° clockwise) |
| 4. Top view | a hole in section 1 that is not on that part, or a bus strip that is not one row of free holes |
| 5. Nets | a net that differs between the board and the schematic (skipped without a schematic or `kicad-cli`) |
| 6. Wires | a net the wires do not join, wires that join two nets, or a bus wire that is not on its strip |
| 7. Wire ends | more than 3 wire ends in one hole (`--max-per-hole`) |

| Argument | Meaning | Default |
| :--- | :--- | :--- |
| `BOARD` | the `.kicad_pcb`, with one `Edge.Cuts` rectangle per perfboard | required |
| `WIRING` | file written by `wire_list.py` | `perfboard_wiring.md` next to the board |
| `--sch FILE` | schematic for check 5 | the `.kicad_sch` next to the board |
| `--kicad-cli CMD` | command that runs `kicad-cli` | `kicad-cli` on `PATH` |
| `--mcu REF` | part whose pins of one net are joined inside the module and need no wire | part with `Role` = `mcu`, else the part with most pads |

Exit code 0 when all checks pass, 1 when any fails. It does not know your
real parts: measure the module, the headers and the board before you
solder.

