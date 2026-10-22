# Builds hardware/enclosure/sensor_tube.FCStd, the baseline model of the filter adapter, the sensor
# tube, one separate flat fan mount plate for both ends, a slot for each of the BME680 and MiCS-4514 boards (glued in, no
# carrier, at 90 and 180 deg from the MQ131) and a hole for the MQ131 sensor itself. Every dimension lives in
# the "Params" spreadsheet and the solids are bound to it by expressions, so edit the numbers in
# FreeCAD and the model follows.
#
#   freecad -c hardware/enclosure/script/build_sensor_tube.py
#
# Running it again overwrites the .FCStd, so keep it for regenerating the baseline only and
# do further design work in the .FCStd itself. Air flows along +X:
#   filter -> adapter -> front fan -> sensor tube (sensors) -> rear fan -> exhaust
# Printed parts: FilterAdapter, SensorTube and FanMount (three copies, FanMount_front and FanMount_rear are its mirrors).
import os
import FreeCAD as App
import Part
import Draft

# The model lives one directory up from this script.
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sensor_tube.FCStd")

# (alias, value, note). Values with a unit are lengths in mm, "=..." are formulas.
PARAMS = [
    ("# Measured by the user", None, None),
    ("filter_dia", "107 mm", "3M 2091 filter diameter"),
    ("filter_t", "15 mm", "3M 2091 thickness without the bayonet"),
    ("port_od", "22 mm", "mask bayonet port outer diameter"),
    ("port_id", "19 mm", "mask bayonet port inner diameter"),
    ("tooth_h", "3 mm", "bayonet tooth height (radial)"),
    ("tooth_w", "7 mm", "bayonet tooth width (tangential)"),
    ("# Assumptions, confirm on the real parts", None, None),
    ("port_len", "12 mm", "port tube length that enters the filter"),
    ("tooth_t", "2 mm", "bayonet tooth thickness along the flow"),
    ("tooth_x", "2 mm", "tooth distance from the port tip"),
    ("collar_t", "4 mm", "collar thickness at the port base"),
    ("collar_w", "6 mm", "collar width beyond the port outer diameter"),
    ("groove_w", "2.5 mm", "o-ring face groove width (size TBD)"),
    ("groove_d", "1.5 mm", "o-ring face groove depth (size TBD)"),
    ("wall", "2 mm", "printed wall, 5 perimeters at 0.4 mm"),
    ("fan_size", "80 mm", "8025 fan frame"),
    ("fan_t", "25 mm", "8025 fan thickness"),
    ("fan_hole_sp", "71.5 mm", "80 mm fan mounting hole spacing"),
    ("fan_hole_d", "4.3 mm", "fan mounting hole, M4 clearance"),
    ("fan_bore", "76 mm", "fan airflow opening"),
    ("adapter_len", "50 mm", "cone length from 22 mm port to the fan bore"),
    ("plate_size", "100 mm", "square mount plate (adapter flange and fan mounts)"),
    ("plate_t", "2 mm", "mount plate thickness"),
    ("tube_id", "85 mm", "sensor tube inner diameter"),
    ("tube_len", "100 mm", "sensor tube length between its two mount plates"),
    ("# BME680 and MiCS-4514 boards: pushed through a slot in the tube wall and glued. l along the flow, w radial (into the tube), t thick, x from the tube inlet, z offset along the wall (0 = centred on the slot line)", None, None),
    ("bme_l", "19 mm", "BME680 board length"),
    ("bme_w", "15.5 mm", "BME680 board width"),
    ("bme_t", "3 mm", "BME680 board thickness including parts"),
    ("bme_x", "11.7 mm", "BME680 distance from the tube inlet"),
    ("bme_z", "=-bme_t / 2", "BME680 offset along the wall, centred on its slot line"),
    ("mics_l", "23 mm", "MiCS-4514 board length"),
    ("mics_w", "15 mm", "MiCS-4514 board width"),
    ("mics_t", "3 mm", "MiCS-4514 board thickness including parts"),
    ("mics_x", "11.7 mm", "MiCS-4514 distance from the tube inlet"),
    ("mics_z", "=-mics_t / 2", "MiCS-4514 offset along the wall, centred on its slot line"),
    ("bme_ang", "90 deg", "BME680 slot angle around the tube axis from +Y toward +Z: 90 deg from the MQ131 (which is on -Y)"),
    ("mics_ang", "0 deg", "MiCS-4514 slot angle around the tube axis from +Y toward +Z: 180 deg from the MQ131"),
    ("slot_clear", "0.5 mm", "clearance around a board in its slot (room for glue)"),
    ("board_out", "3 mm", "how far a board sticks out past the outer wall (header end)"),
    ("# MQ131 sensor in a hole in the tube side (-Y), ledge outside, inserted from outside", None, None),
    ("mq_base_d", "14.2 mm", "MQ131 white base diameter (measured)"),
    ("mq_hole_clear", "0.4 mm", "clearance of the base in the hole"),
    ("mq_ledge_d", "=mq_base_d + 2 * 1.5 mm", "MQ131 ledge ring outer diameter (measured: base + 2 x 1.5 mm)"),
    ("mq_ledge_t", "1.5 mm", "MQ131 ledge thickness along the sensor (assumed)"),
    ("mq_base_h", "8 mm", "MQ131 white base height from the ledge to the can (assumed)"),
    ("mq_can_d", "17 mm", "MQ131 metal can diameter (assumed, must pass the hole if inserted from outside)"),
    ("mq_len", "22 mm", "MQ131 length from the ledge face to the can tip (assumed)"),
    ("mq_x", "65 mm", "MQ131 hole centre distance from the tube inlet"),
    ("mq_boss_h", "3 mm", "flat boss height above the tube outer surface, seat for the ledge"),
    ("mq_boss_d", "=mq_ledge_d + 2 * 3 mm", "flat boss diameter"),
    ("sps_l", "41 mm", "SPS30 length"),
    ("sps_gap", "8 mm", "SPS30 distance from the filter edge"),
    ("# Positions along the flow, derived", None, None),
    ("x_adapter", "=filter_t", "port base, collar face against the filter"),
    ("x_cone", "=x_adapter + collar_t", "cone start"),
    ("x_plate_a", "=x_cone + adapter_len", "adapter flange"),
    ("x_fan_f", "=x_plate_a + plate_t", "front fan start"),
    ("x_tf", "=x_fan_f + fan_t", "front fan mount plate"),
    ("x_t0", "=x_tf + plate_t", "tube inlet (start of the tube)"),
    ("x_tr", "=x_t0 + tube_len", "tube outlet, rear fan mount plate"),
    ("x_fan_r", "=x_tr + plate_t", "rear fan start"),
]

doc = App.newDocument("SensorTube")
sheet = doc.addObject("Spreadsheet::Sheet", "Params")
row = 1
for alias, value, note in PARAMS:
    sheet.set("A%d" % row, alias)
    if value is not None:
        sheet.set("B%d" % row, value)
        sheet.set("C%d" % row, note)
        sheet.setAlias("B%d" % row, alias)
    row += 1
doc.recompute()

V = App.Vector
ALONG_X = App.Rotation(V(0, 1, 0), 90)  # cylinder axis Z -> X
ALONG_Y = App.Rotation(V(1, 0, 0), -90)  # cylinder axis Z -> +Y
ALONG_NY = App.Rotation(V(1, 0, 0), 90)  # cylinder axis Z -> -Y


def _place(o, x, y, z):
    o.setExpression("Placement.Base.x", x)
    o.setExpression("Placement.Base.y", y)
    o.setExpression("Placement.Base.z", z)


def cylinder(name, radius, length, x, y="0 mm", z="0 mm"):
    o = doc.addObject("Part::Cylinder", name)
    o.setExpression("Radius", radius)
    o.setExpression("Height", length)
    o.Placement = App.Placement(V(0, 0, 0), ALONG_X)
    _place(o, x, y, z)
    return o


def cylinder_y(name, radius, length, x, y, z):
    o = doc.addObject("Part::Cylinder", name)
    o.setExpression("Radius", radius)
    o.setExpression("Height", length)
    o.Placement = App.Placement(V(0, 0, 0), ALONG_Y)
    _place(o, x, y, z)
    return o


def cylinder_ny(name, radius, length, x, y, z):
    o = doc.addObject("Part::Cylinder", name)
    o.setExpression("Radius", radius)
    o.setExpression("Height", length)
    o.Placement = App.Placement(V(0, 0, 0), ALONG_NY)
    _place(o, x, y, z)
    return o


def box(name, length, width, height, x, y, z, rotation=None, angle=None):
    """length along X, width along Y, height along Z. angle (a parameter name) turns the box
    around the tube axis (X); y and z are then the position before that turn."""
    o = doc.addObject("Part::Box", name)
    o.setExpression("Length", length)
    o.setExpression("Width", width)
    o.setExpression("Height", height)
    if angle is not None:
        o.Placement = App.Placement(V(0, 0, 0), App.Rotation(V(1, 0, 0), 1))  # axis X, angle set below
        for axis, value in (("x", "1"), ("y", "0"), ("z", "0")):
            o.setExpression("Placement.Rotation.Axis." + axis, value)
        o.setExpression("Placement.Rotation.Angle", angle)
        y, z = ("(%s) * cos(%s) - (%s) * sin(%s)" % (y, angle, z, angle),
                "(%s) * sin(%s) + (%s) * cos(%s)" % (y, angle, z, angle))
    elif rotation is not None:
        o.Placement = App.Placement(V(0, 0, 0), rotation)
    _place(o, x, y, z)
    return o


def cone(name, r1, r2, length, x):
    o = doc.addObject("Part::Cone", name)
    o.setExpression("Radius1", r1)
    o.setExpression("Radius2", r2)
    o.setExpression("Height", length)
    o.Placement = App.Placement(V(0, 0, 0), ALONG_X)
    o.setExpression("Placement.Base.x", x)
    return o


def fuse(name, shapes):
    o = doc.addObject("Part::MultiFuse", name)
    o.Shapes = shapes
    return o


def cut(name, base, tool):
    o = doc.addObject("Part::Cut", name)
    o.Base = base
    o.Tool = tool
    return o


def fan_holes(prefix, x):
    """Four axial fan screw holes through a mount plate at x: one hole, polar array of 4 around the X axis."""
    hole = cylinder(prefix, "Params.fan_hole_d / 2", "Params.plate_t + 2 mm", x + " - 1 mm",
                    "Params.fan_hole_sp / 2", "Params.fan_hole_sp / 2")
    holes = Draft.make_polar_array(hole, number=4, angle=360, center=V(0, 0, 0), use_link=False)
    holes.Axis = V(1, 0, 0)
    holes.Fuse = True
    return [holes]


def plate(name, x):
    return box(name, "Params.plate_t", "Params.plate_size", "Params.plate_size", x,
               "-Params.plate_size / 2", "-Params.plate_size / 2")


# ---- Filter adapter: bayonet port, o-ring face groove, cone 22 mm -> fan bore (the fan plate is a FanMount, glued on) ----
port = cylinder("A_port", "Params.port_od / 2", "Params.port_len", "Params.x_adapter - Params.port_len")
collar = cylinder("A_collar", "Params.port_od / 2 + Params.collar_w", "Params.collar_t", "Params.x_adapter")
outer_cone = cone("A_cone_out", "Params.port_id / 2 + Params.wall", "Params.fan_bore / 2 + Params.wall",
                  "Params.adapter_len", "Params.x_cone")
# One bayonet tooth on +Z, repeated 3 times around the port axis (X) with a Draft polar array.
r = "(Params.port_od / 2 - 0.5 mm)"
tooth = box("A_tooth", "Params.tooth_t", "Params.tooth_w", "Params.tooth_h + 0.5 mm",
            "Params.x_adapter - Params.port_len + Params.tooth_x", "-Params.tooth_w / 2", r)
teeth = Draft.make_polar_array(tooth, number=3, angle=360, center=V(0, 0, 0), use_link=False)
teeth.Axis = V(1, 0, 0)
teeth.Fuse = True
adapter_solid = fuse("A_solid", [port, collar, outer_cone, teeth])

bore = cylinder("A_bore", "Params.port_id / 2", "Params.port_len + Params.collar_t + 2 mm", "Params.x_adapter - Params.port_len - 1 mm")
inner_cone = cone("A_cone_in", "Params.port_id / 2", "Params.fan_bore / 2", "Params.adapter_len", "Params.x_cone")
# o-ring face groove in the collar face, around the port; the filter back face seals against it
groove_out = cylinder("A_groove_out", "Params.port_od / 2 + 1 mm + Params.groove_w", "Params.groove_d + 1 mm", "Params.x_adapter - 1 mm")
groove_in = cylinder("A_groove_in", "Params.port_od / 2 + 1 mm", "Params.groove_d + 1 mm", "Params.x_adapter - 1 mm")
groove = cut("A_groove", groove_out, groove_in)
adapter_tools = fuse("A_tools", [bore, inner_cone, groove])
adapter = cut("FilterAdapter", adapter_solid, adapter_tools)

# ---- BME680 and MiCS-4514: a slot through the tube side takes each board, which is glued in place ----
# No holder and no pad. Each board goes in edge first through its own slot, header end outside.
# The slots sit at different angles around the tube: the MQ131 hole is on -Y, the BME680 slot is 90 deg
# from it (top, +Z) and the MiCS-4514 slot 180 deg from it (+Y).
# Reference bodies, not printed.
OUTER = "(Params.tube_id / 2 + Params.wall)"  # outer wall radius
slots, sensor_refs = [], []
for p, label in (("bme", "BME"), ("mics", "MiCS")):
    def P(a, p=p):
        return "Params.%s_%s" % (p, a)

    slot_x = "(Params.x_t0 + " + P("x") + " - Params.slot_clear)"
    slot_len = "(" + P("l") + " + 2 * Params.slot_clear)"
    slot_z = "(" + P("z") + " - Params.slot_clear)"
    slot_h = "(" + P("t") + " + 2 * Params.slot_clear)"
    slots.append(box("T_slot_" + p, slot_len, OUTER + " + 1 mm", slot_h, slot_x, "0 mm", slot_z, angle=P("ang")))
    sensor_refs.append(box("REF_" + label, P("l"), P("w"), P("t"), "Params.x_t0 + " + P("x"),
                           OUTER + " + Params.board_out - " + P("w"), P("z"), angle=P("ang")))

# ---- Sensor tube: a plain tube, a slot per board, a hole for the MQ131 (fan mounts are separate) ----
tube_out = cylinder("T_tube_out", "Params.tube_id / 2 + Params.wall", "Params.tube_len", "Params.x_t0")
# MQ131: a hole slightly bigger than the base on the -Y side takes the sensor. The boss/ring that seats the
# ledge is left out on purpose, to be added by hand in the .FCStd.
MQ_X = "Params.x_t0 + Params.mq_x"
MQ_FACE = "(Params.tube_id / 2 + Params.wall + Params.mq_boss_h)"  # distance of the boss face from the axis
mq_hole = cylinder_ny("T_mq_hole", "(Params.mq_base_d + Params.mq_hole_clear) / 2", MQ_FACE + " + 2 mm", MQ_X, "0 mm", "0 mm")
tube_tools = [cylinder("T_bore", "Params.tube_id / 2", "Params.tube_len + 2 mm", "Params.x_t0 - 1 mm")]
sensor_tube = cut("SensorTube", tube_out, fuse("T_tools", tube_tools + slots + [mq_hole]))

# ---- Fan mount: ONE part, printed separately and glued onto each tube end ----
# A flat square plate with the fan opening and screw holes. The tube end is glued to its inner face.
# The rear mount is the front one mirrored about the middle of the tube, so editing FanMount changes
# both; print two copies.
fm_plate = plate("FM_plate", "Params.x_tf")
fm_tools = fuse("FM_tools", [cylinder("FM_bore", "Params.fan_bore / 2", "Params.plate_t + 2 mm", "Params.x_tf - 1 mm")]
                + fan_holes("FM_fan", "Params.x_tf"))
fan_mount = cut("FanMount", fm_plate, fm_tools)
fan_mount_rear = doc.addObject("Part::Mirroring", "FanMount_rear")
fan_mount_rear.Source = fan_mount
fan_mount_rear.Base = V(0, 0, 0)
fan_mount_rear.Normal = V(1, 0, 0)
fan_mount_rear.setExpression("Base.x", "(Params.x_t0 + Params.x_tr) / 2")
# The front fan's upstream plate is the same part: FanMount mirrored about the middle of the front fan, glued to the cone end.
fan_mount_front = doc.addObject("Part::Mirroring", "FanMount_front")
fan_mount_front.Source = fan_mount
fan_mount_front.Base = V(0, 0, 0)
fan_mount_front.Normal = V(1, 0, 0)
fan_mount_front.setExpression("Base.x", "(Params.x_fan_f + Params.x_tf) / 2")

# ---- Reference bodies, not printed: parts the enclosure is built around ----
refs = [
    cylinder("REF_filter_3M2091", "Params.filter_dia / 2", "Params.filter_t", "0 mm"),
    box("REF_fan_front", "Params.fan_t", "Params.fan_size", "Params.fan_size", "Params.x_fan_f",
        "-Params.fan_size / 2", "-Params.fan_size / 2"),
    box("REF_fan_rear", "Params.fan_t", "Params.fan_size", "Params.fan_size", "Params.x_fan_r",
        "-Params.fan_size / 2", "-Params.fan_size / 2"),
    box("REF_SPS30", "Params.sps_l", "12 mm", "Params.sps_l", "0 mm", "Params.filter_dia / 2 + Params.sps_gap",
        "-Params.sps_l / 2"),
] + sensor_refs + [
    cylinder_ny("REF_MQ131_ledge", "Params.mq_ledge_d / 2", "Params.mq_ledge_t", MQ_X, "-" + MQ_FACE, "0 mm"),
    cylinder_y("REF_MQ131_base", "Params.mq_base_d / 2", "Params.mq_base_h", MQ_X, "-" + MQ_FACE, "0 mm"),
    cylinder_y("REF_MQ131_can", "Params.mq_can_d / 2", "Params.mq_len - Params.mq_base_h", MQ_X,
               "-" + MQ_FACE + " + Params.mq_base_h", "0 mm"),
]
group = doc.addObject("App::DocumentObjectGroup", "Reference_NotPrinted")
group.Group = refs

doc.recompute()

# Built headless, so nothing hides the helper solids (cut tools, fuse inputs) the way the GUI does.
# Show only the printed parts and the reference bodies.
shown = {"FilterAdapter", "SensorTube", "FanMount", "FanMount_rear", "FanMount_front"} | {r.Name for r in refs}
for o in doc.Objects:
    if hasattr(o, "Shape") and o.TypeId.startswith("Part::"):
        o.Visibility = o.Name in shown
doc.saveAs(OUT)
print("saved", OUT)
