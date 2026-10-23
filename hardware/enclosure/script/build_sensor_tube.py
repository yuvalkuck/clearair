# Builds hardware/enclosure/sensor_tube.FCStd, the baseline model of the filter adapter, the sensor
# tube, three fan mount plates with a short sleeve (one design for the tube, a variant for the cone), a slot for each of the BME680 and MiCS-4514 boards (glued in, no
# carrier, at 90 deg from the MQ131 and opposite each other) and a ring boss and hole for the MQ131 sensor itself. Every dimension lives in
# the "Params" spreadsheet and the solids are bound to it by expressions, so edit the numbers in
# FreeCAD and the model follows.
#
#   freecad -c hardware/enclosure/script/build_sensor_tube.py
#
# Running it again overwrites the .FCStd, so keep it for regenerating the baseline only and
# do further design work in the .FCStd itself. Air flows along +X:
#   filter -> adapter -> front fan -> sensor tube (sensors) -> rear fan -> exhaust
# Printed parts: FilterAdapter, SensorTube, SPS30_Holder and FanMount (tube end; FanMount_rear is its mirror) and FanMount_front (cone end).
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
    ("sleeve_len", "4 mm", "fan mount sleeve length over the tube end (or the cone end, on the front mount)"),
    ("sleeve_wall", "2 mm", "fan mount sleeve wall"),
    ("sleeve_ch", "2 mm", "chamfer between the sleeve outside and the plate face"),
    ("mount_clear", "0.3 mm", "fan mount sleeve diametral clearance over the tube or cone end, room for glue"),
    ("boss_d", "9 mm", "raised seat around each fan screw hole, where the board goes"),
    ("boss_h", "3 mm", "raised seat height above the plate face"),
    ("boss_ch", "1.5 mm", "chamfer between the raised seat and the plate face"),
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
    ("mics_ang", "270 deg", "MiCS-4514 slot angle around the tube axis from +Y toward +Z: opposite the BME680 (-Z), 90 deg from the MQ131"),
    ("slot_clear", "0.5 mm", "clearance around a board in its slot (room for glue)"),
    ("slot_pad", "3 mm", "margin of the flat pad around a board slot, along the flow and across"),
    ("slot_pad_in", "3 mm", "how far a slot pad sticks inside the bore wall, at the slot centre"),
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
    ("mq_boss_h", "0 mm", "flat boss top above the tube outer radius (0 = flush with the tube top, a flat pad that follows the tube curve out to the sides)"),
    ("mq_boss_in", "3 mm", "how far the boss inner face sits inside the tube bore wall (at the hole centre)"),
    ("mq_boss_d", "=mq_ledge_d + 2 * 3 mm", "flat boss diameter"),
    ("sps_l", "41 mm", "SPS30 length"),
    ("sps_gap", "8 mm", "SPS30 distance from the filter edge"),
    ("# SPS30 holder: separate part that plugs into holes in the tube on top (+Z) beside the BME680. A flat inverted U (a bridge on two legs)\n# with a small lip at the foot of each leg to carry the sensor. Open at both ends across the flow so the sensor slides in\n# and its ports and cable stay free. Four pegs push into four blind holes in the tube top (no saddle).", None, None),
    ("sps_w", "41 mm", "SPS30 width, across the legs (along the flow)"),
    ("sps_t", "12 mm", "SPS30 thickness"),
    ("sps_fit", "0.6 mm", "clearance around the SPS30 inside the holder"),
    ("hold_wall", "2 mm", "holder bridge and leg thickness"),
    ("hold_len", "30 mm", "holder length across the flow (the sensor slides in this way)"),
    ("hold_lift", "2 mm", "sensor underside distance above the tube outer radius"),
    ("hold_lip_w", "3 mm", "lip width under the sensor, at the foot of each leg"),
    ("hold_lip_t", "1.5 mm", "lip thickness"),
    ("peg_d", "3 mm", "holder peg diameter, pushes into a blind hole in the tube"),
    ("peg_len", "3 mm", "holder peg length below the tube top line (the holes are cut from there)"),
    ("hold_clear", "0.2 mm", "diametral clearance between the holder underside and the tube"),
    ("peg_fit", "0.2 mm", "peg hole diametral clearance (room for glue)"),
    ("peg_dx", "35 mm", "peg spacing along the flow"),
    ("peg_dy", "20 mm", "peg spacing across the flow"),
    ("peg_pad_d", "9 mm", "round pad on the tube around each peg hole, sticking inside the bore"),
    ("# Positions along the flow, derived", None, None),
    ("x_adapter", "=filter_t", "port base, collar face against the filter"),
    ("x_cone", "=x_adapter + collar_t", "cone start"),
    ("x_plate_a", "=x_cone + adapter_len", "adapter flange"),
    ("x_fan_f", "=x_plate_a + plate_t", "front fan start"),
    ("x_tf", "=x_fan_f + fan_t", "front fan mount plate"),
    ("x_t0", "=x_tf + plate_t", "tube inlet (start of the tube)"),
    ("x_tr", "=x_t0 + tube_len", "tube outlet, rear fan mount plate"),
    ("x_fan_r", "=x_tr + plate_t", "rear fan start"),
    ("x_sps", "=x_t0 + bme_x + bme_l + slot_pad + 4 mm + hold_wall + (sps_w + sps_fit) / 2", "SPS30 holder centre: beside the BME680 slot pad along the flow, 4 mm gap"),
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
ALONG_NX = App.Rotation(V(0, 1, 0), -90)  # cylinder axis Z -> -X
ALONG_Y = App.Rotation(V(1, 0, 0), -90)  # cylinder axis Z -> +Y
ALONG_NY = App.Rotation(V(1, 0, 0), 90)  # cylinder axis Z -> -Y


def _place(o, x, y, z):
    o.setExpression("Placement.Base.x", x)
    o.setExpression("Placement.Base.y", y)
    o.setExpression("Placement.Base.z", z)


def cylinder(name, radius, length, x, y="0 mm", z="0 mm", rot=ALONG_X):
    o = doc.addObject("Part::Cylinder", name)
    o.setExpression("Radius", radius)
    o.setExpression("Height", length)
    o.Placement = App.Placement(V(0, 0, 0), rot)
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


def common(name, a, b):
    o = doc.addObject("Part::Common", name)
    o.Base = a
    o.Tool = b
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


def fan_holes(prefix, x, extra="0 mm"):
    """Four axial fan screw holes through a mount plate at x: one hole, polar array of 4 around the X axis.
    extra lengthens the hole past the plate, for a raised seat on the far face."""
    hole = cylinder(prefix, "Params.fan_hole_d / 2", "Params.plate_t + " + extra + " + 2 mm", x + " - 1 mm",
                    "Params.fan_hole_sp / 2", "Params.fan_hole_sp / 2")
    return [polar4(hole)]


def polar4(shape):
    """Four copies of shape around the X axis, fused."""
    arr = Draft.make_polar_array(shape, number=4, angle=360, center=V(0, 0, 0), use_link=False)
    arr.Axis = V(1, 0, 0)
    arr.Fuse = True
    return arr


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
# from it (top, +Z) and the MiCS-4514 slot is opposite the BME680 (bottom, -Z). Each slot has a pad like the MQ131 boss.
# Reference bodies, not printed.
OUTER = "(Params.tube_id / 2 + Params.wall)"  # outer wall radius
slots, pads, sensor_refs = [], [], []
for p, label in (("bme", "BME"), ("mics", "MiCS")):
    def P(a, p=p):
        return "Params.%s_%s" % (p, a)

    slot_x = "(Params.x_t0 + " + P("x") + " - Params.slot_clear)"
    slot_len = "(" + P("l") + " + 2 * Params.slot_clear)"
    slot_z = "(" + P("z") + " - Params.slot_clear)"
    slot_h = "(" + P("t") + " + 2 * Params.slot_clear)"
    slots.append(box("T_slot_" + p, slot_len, OUTER + " + 1 mm", slot_h, slot_x, "0 mm", slot_z, angle=P("ang")))
    # Pad around the slot: straight walls, flat top at the tube height, flat inner face past the bore wall.
    pad_in = "(Params.tube_id / 2 - Params.slot_pad_in)"
    pads.append(box("T_pad_" + p, slot_len + " + 2 * Params.slot_pad", OUTER + " + Params.mq_boss_h - " + pad_in,
                    slot_h + " + 2 * Params.slot_pad", slot_x + " - Params.slot_pad", pad_in,
                    slot_z + " - Params.slot_pad", angle=P("ang")))
    sensor_refs.append(box("REF_" + label, P("l"), P("w"), P("t"), "Params.x_t0 + " + P("x"),
                           OUTER + " + Params.board_out - " + P("w"), P("z"), angle=P("ang")))

# ---- Sensor tube: a plain tube, a slot per board, a ring boss and hole for the MQ131 (fan mounts are separate) ----
tube_out = cylinder("T_tube_out", "Params.tube_id / 2 + Params.wall", "Params.tube_len", "Params.x_t0")
# MQ131: a flat ring boss on the -Y side seats the ledge: straight walls from inside the tube out to a flat
# top at the tube height (mq_boss_h = 0), so it spreads sideways as a pad where the tube wall curves away.
# Inside, it protrudes mq_boss_in past the bore wall, with a flat face that also follows the curve sideways.
# A hole slightly bigger than the base takes the sensor.
MQ_X = "Params.x_t0 + Params.mq_x"
MQ_FACE = "(Params.tube_id / 2 + Params.wall + Params.mq_boss_h)"  # distance of the boss face from the axis
# The boss also sticks a little into the bore: flat inner face mq_boss_in inside the bore wall.
MQ_IN = "(Params.tube_id / 2 - Params.mq_boss_in)"  # distance of the boss inner face from the axis
mq_boss = cylinder_ny("T_mq_boss", "Params.mq_boss_d / 2", MQ_FACE + " - " + MQ_IN, MQ_X, "-" + MQ_IN, "0 mm")
mq_hole = cylinder_ny("T_mq_hole", "(Params.mq_base_d + Params.mq_hole_clear) / 2", MQ_FACE + " + 2 mm", MQ_X, "0 mm", "0 mm")
# Bore first, then the boss, so the bore does not cut away the part of the boss that sticks into it.
tube_hollow = cut("T_hollow", tube_out, cylinder("T_bore", "Params.tube_id / 2", "Params.tube_len + 2 mm", "Params.x_t0 - 1 mm"))
# SPS30 holder pegs: four round pads (thickening the wall inside, sticking into the bore like the other pads) with a
# blind hole each. Built on the +Z top of the tube, like the BME680 (bme_ang = 90 deg), around x_sps.
# The pads only thicken the wall inside: their outside is cut to the tube outer cylinder, so the holder lies on the curve.
peg_env = cylinder("T_peg_env", OUTER, "Params.tube_len", "Params.x_t0")
peg_pads, peg_holes = [], []
for i, (sx, sy) in enumerate([(1, 1), (1, -1), (-1, 1), (-1, -1)]):
    px, py = "Params.x_sps + %d * Params.peg_dx / 2" % sx, "%d * Params.peg_dy / 2" % sy
    top = "(" + OUTER + " + Params.mq_boss_h)"
    pad_in = "(Params.tube_id / 2 - Params.slot_pad_in)"
    pad = cylinder("T_peg_pad_%d" % i, "Params.peg_pad_d / 2", OUTER + " + 1 mm - " + pad_in, px, py, pad_in,
                   rot=App.Rotation())
    peg_pads.append(common("T_peg_padc_%d" % i, pad, peg_env))
    peg_holes.append(cylinder("T_peg_hole_%d" % i, "(Params.peg_d + Params.peg_fit) / 2", "Params.peg_len + 0.4 mm + 1 mm",
                              px, py, top + " - Params.peg_len - 0.4 mm", rot=App.Rotation()))
tube_solid = fuse("T_solid", [tube_hollow, mq_boss] + pads + peg_pads)
sensor_tube = cut("SensorTube", tube_solid, fuse("T_tools", slots + [mq_hole] + peg_holes))

# ---- Fan mounts: flat plate + sleeve + raised screw seats, printed separately and glued on ----
# The plate has the fan opening and four screw holes. On the face away from the fan it has a short sleeve that
# slips over the end of the tube (or the cone) and a round raised seat with a chamfer at each screw hole.
# FanMount is the tube end version; FanMount_rear is its mirror about the middle of the tube. FanMount_front
# is built the same way but faces the other way, and its sleeve bore is a cone that matches the adapter cone, so the mount slides onto the cone end from the right (+X) toward the left.
def fan_mount_part(name, x_plate, face, sgn, end_r, taper=None):
    """x_plate: plate start (x). face: x of the plate face with the sleeve. sgn: +1 if the sleeve grows
    toward +X, -1 toward -X. end_r: outer radius of the tube/cone end that the sleeve takes, at the plate.
    taper: if given, the radius the end loses per mm away from the plate (a cone); the sleeve bore then
    tapers the same way, so it fits the cone exactly."""
    rot = ALONG_X if sgn > 0 else ALONG_NX
    recess_r = "(" + end_r + " + Params.mount_clear / 2)"
    sleeve_r = recess_r + " + Params.sleeve_wall"
    plate_ = plate(name + "_plate", x_plate)
    sleeve = cylinder(name + "_sleeve", sleeve_r, "Params.sleeve_len", face, rot=rot)
    sleeve_ch = doc.addObject("Part::Cone", name + "_sleeve_ch")
    sleeve_ch.setExpression("Radius1", sleeve_r + " + Params.sleeve_ch")
    sleeve_ch.setExpression("Radius2", sleeve_r)
    sleeve_ch.setExpression("Height", "Params.sleeve_ch")
    sleeve_ch.Placement = App.Placement(V(0, 0, 0), rot)
    sleeve_ch.setExpression("Placement.Base.x", face)
    sy = sz = "Params.fan_hole_sp / 2"
    seat = cylinder(name + "_seat", "Params.boss_d / 2", "Params.boss_h", face, sy, sz, rot=rot)
    seat_ch = doc.addObject("Part::Cone", name + "_seat_ch")
    seat_ch.setExpression("Radius1", "Params.boss_d / 2 + Params.boss_ch")
    seat_ch.setExpression("Radius2", "Params.boss_d / 2")
    seat_ch.setExpression("Height", "Params.boss_ch")
    seat_ch.Placement = App.Placement(V(0, 0, 0), rot)
    _place(seat_ch, face, sy, sz)
    seat_one = fuse(name + "_seat_one", [seat, seat_ch])
    solid = fuse(name + "_solid", [plate_, sleeve, sleeve_ch, polar4(seat_one)])
    bore = cylinder(name + "_bore", "Params.fan_bore / 2", "Params.plate_t + 2 mm", x_plate + " - 1 mm")
    if taper is None:
        recess = cylinder(name + "_recess", recess_r, "Params.sleeve_len + 1 mm", face, rot=rot)
    else:
        recess = doc.addObject("Part::Cone", name + "_recess")
        recess.setExpression("Radius1", recess_r)
        recess.setExpression("Radius2", recess_r + " - " + taper + " * (Params.sleeve_len + 1 mm)")
        recess.setExpression("Height", "Params.sleeve_len + 1 mm")
        recess.Placement = App.Placement(V(0, 0, 0), rot)
        recess.setExpression("Placement.Base.x", face)
    hole_x = x_plate if sgn > 0 else x_plate + " - Params.boss_h"
    tools = fuse(name + "_tools", [bore, recess] + fan_holes(name + "_fan", hole_x, "Params.boss_h"))
    return cut(name, solid, tools)


TUBE_END_R = "(Params.tube_id / 2 + Params.wall)"
CONE_END_R = "(Params.fan_bore / 2 + Params.wall)"
fan_mount = fan_mount_part("FanMount", "Params.x_tf", "Params.x_t0", 1, TUBE_END_R)
fan_mount_rear = doc.addObject("Part::Mirroring", "FanMount_rear")
fan_mount_rear.Source = fan_mount
fan_mount_rear.Base = V(0, 0, 0)
fan_mount_rear.Normal = V(1, 0, 0)
fan_mount_rear.setExpression("Base.x", "(Params.x_t0 + Params.x_tr) / 2")
fan_mount_front = fan_mount_part("FanMount_front", "Params.x_plate_a", "Params.x_plate_a", -1, CONE_END_R,
                               taper="((Params.fan_bore / 2 - Params.port_id / 2) / Params.adapter_len)")

# ---- SPS30 holder: separate printed part on top of the tube (+Z), beside the BME680 along the flow ----
# A flat inverted U: a bridge on two legs over a floor, with a lip at the foot of each leg. The sensor slides in from
# either end across the flow, so its ports and cable stay free. Four pegs under the floor push into the blind holes in
# the tube top (T_peg_hole_*). The underside is cut to the tube outer cylinder, so it lies on the curve.
GAP = "(Params.sps_w + Params.sps_fit)"  # clear width between the legs
BASE = OUTER + " - 5 mm"  # the legs and floor start below the tube top, then the saddle cut rounds the underside
YS0 = OUTER + " + Params.hold_lift"  # underside of the sensor
YS1 = "(" + YS0 + " + Params.sps_t + Params.sps_fit)"  # top of the sensor
XC = "Params.x_sps"


def hbox(*args):
    """A box built on +Y, turned to the BME680 angle."""
    return box(*args, angle="Params.bme_ang")


hz = "-Params.hold_len / 2"
parts = [
    hbox("H_floor", GAP + " + 2 * Params.hold_wall", YS0 + " - (" + BASE + ")", "Params.hold_len",
         XC + " - " + GAP + " / 2 - Params.hold_wall", BASE, hz),
    hbox("H_bridge", GAP + " + 2 * Params.hold_wall", "Params.hold_wall", "Params.hold_len",
         XC + " - " + GAP + " / 2 - Params.hold_wall", YS1, hz),
    hbox("H_leg_a", "Params.hold_wall", YS1 + " + Params.hold_wall - (" + BASE + ")", "Params.hold_len",
         XC + " - " + GAP + " / 2 - Params.hold_wall", BASE, hz),
    hbox("H_leg_b", "Params.hold_wall", YS1 + " + Params.hold_wall - (" + BASE + ")", "Params.hold_len",
         XC + " + " + GAP + " / 2", BASE, hz),
    hbox("H_lip_a", "Params.hold_lip_w", "Params.hold_lip_t", "Params.hold_len", XC + " - " + GAP + " / 2",
         YS0 + " - Params.hold_lip_t", hz),
    hbox("H_lip_b", "Params.hold_lip_w", "Params.hold_lip_t", "Params.hold_len", XC + " + " + GAP + " / 2 - Params.hold_lip_w",
         YS0 + " - Params.hold_lip_t", hz),
]
# pegs go down (-Z at the top of the tube), same spots as the holes and pads in the tube
saddle = cylinder("H_saddle", OUTER + " + Params.hold_clear / 2", GAP + " + 2 * Params.hold_wall + 4 mm",
                  XC + " - " + GAP + " / 2 - Params.hold_wall - 2 mm")
pegs = []
for i, (sx, sy) in enumerate([(1, 1), (1, -1), (-1, 1), (-1, -1)]):
    pegs.append(cylinder("H_peg_%d" % i, "Params.peg_d / 2", "Params.peg_len + 1.5 mm",
                          "Params.x_sps + %d * Params.peg_dx / 2" % sx, "%d * Params.peg_dy / 2" % sy,
                          OUTER + " - Params.peg_len", rot=App.Rotation()))
# the pegs go on after the saddle cut: they reach below the tube outer cylinder, into the holes
sps_holder = fuse("SPS30_Holder", [cut("H_cut", fuse("H_body", parts), saddle)] + pegs)

# ---- Reference bodies, not printed: parts the enclosure is built around ----
refs = [
    cylinder("REF_filter_3M2091", "Params.filter_dia / 2", "Params.filter_t", "0 mm"),
    box("REF_fan_front", "Params.fan_t", "Params.fan_size", "Params.fan_size", "Params.x_fan_f",
        "-Params.fan_size / 2", "-Params.fan_size / 2"),
    box("REF_fan_rear", "Params.fan_t", "Params.fan_size", "Params.fan_size", "Params.x_fan_r",
        "-Params.fan_size / 2", "-Params.fan_size / 2"),
    box("REF_SPS30_in_holder", "Params.sps_w", "Params.sps_t", "Params.sps_w", XC + " - Params.sps_w / 2", YS0, "-Params.sps_w / 2",
        angle="Params.bme_ang"),
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
shown = {"FilterAdapter", "SensorTube", "FanMount", "FanMount_rear", "FanMount_front", "SPS30_Holder"} | {r.Name for r in refs}
for o in doc.Objects:
    if hasattr(o, "Shape") and o.TypeId.startswith("Part::"):
        o.Visibility = o.Name in shown
doc.saveAs(OUT)
print("saved", OUT)
