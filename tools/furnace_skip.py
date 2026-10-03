"""
The skip hoist: the furnace upgrade model, finished for the game (LHM-47).

    blender --background --python tools/furnace_skip.py
    blender --background --python tools/furnace_skip.py -- furnace_out=<dir>

furnace_designs.py drew four candidates and stopped. This takes the skip one (a long low
diagonal: a stone bank carrying iron rails, an ore skip on them, a stone buttress at the
high end with a winch drum behind it) and turns it into what the mod loads:

  assets\\kynda_furnace_skip.obj        two material groups, "iron" and "stone"
  assets\\kynda_furnace_skip.col        collision boxes, some of them tilted with the bank
  assets\\kynda_furnace_skip_icon.png   the hammer icon, 128px, same camera as the other two

The groups are called iron and stone, not "blackmetal" as the design script had them,
because Skins already has a donor list and a metal-patch search for exactly those two names.
Whatever the black metal ends up wearing in game is a config line (SkinDonors), not this
file's business.

What changed from the design, and why each one matters in game rather than in a render:

  - The skip's walls were offset in world axes and only rotated about their own centres, so
    the whole box was sheared by the slope: its ends sat 0.1m off the floor. Every part of
    it is placed in the skip's own frame now and then carried up the slope.
  - The ore sat 6cm above the floor with nothing under it. It rises to the pouring lip now,
    heaped past the low front wall, which is the half of the picture that says "ore".
  - The skip floated 2cm over the rails. It rides on four wheels that overlap both.
  - There was a winch and nothing it was winding. A cable now runs from the drum to a lug
    on the skip. That one bar is what makes the hoist read as a hoist.

Every part is a closed primitive, so there is nothing single-sided to look into (LHM-24).
The open edge count is printed anyway, on positions rather than indices, and the script
fails loudly over the triangle cap or on any open edge.
"""

import bpy
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import upgrade_variants as uv   # helpers only; it guards its own main()
import furnace_designs as fd    # staging and the open-edge count; it guards its own main()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
NAME = "kynda_furnace_skip"

# Black metal reads near black next to stone, which is the whole point of the pair. The
# design script's flat values, only darker on the iron so the icon keeps the contrast at 128px.
uv.TINTS["iron"] = (0.085, 0.085, 0.095, 1.0)
uv.TINTS["stone"] = (0.50, 0.45, 0.38, 1.0)

RUN, RISE = 3.0, 0.72
PITCH = math.degrees(math.atan2(RISE, RUN))
CP, SP = math.cos(math.radians(PITCH)), math.sin(math.radians(PITCH))
SLOPE = math.hypot(RUN, RISE)

# Rail centreline height at x, and the skip's base point on it.
LINE0 = 0.465 + RISE / 2.0
CX = -0.35

COLLIDERS = []   # (centre, size, rot_y_degrees) in Blender space


def line_z(x):
    return LINE0 + x * RISE / RUN


def on_slope(lx, ly, lz):
    """A point given in the skip's own frame (along the rails, across, up off them)."""
    return (CX + lx * CP - lz * SP, ly, line_z(CX) + lx * SP + lz * CP)


def metal(size, loc, rot=(0.0, 0.0, 0.0), bevel=0.010):
    return uv.box(size, loc, "iron", rot=rot, bevel=bevel)


def tilted(size, local, bevel=0.010):
    return metal(size, on_slope(*local), rot=(0.0, -PITCH, 0.0), bevel=bevel)


def collide(centre, size, rot_y=0.0):
    COLLIDERS.append((centre, size, rot_y))


def build():
    # Two rails climbing toward +x, on one stone bank rather than a row of posts. The
    # rails overlap the bank by a couple of centimetres, as a bolted rail does.
    for y in (-0.34, 0.34):
        metal((SLOPE, 0.11, 0.13), (0.0, y, LINE0), rot=(0.0, -PITCH, 0.0))

    fd.rock((SLOPE + 0.30, 1.06, 0.62), (0.0, 0.0, LINE0 - 0.35),
            rot=(0.0, -PITCH, 0.0), bevel=0.03)
    fd.rock((1.00, 1.16, 0.34), (-1.45, 0.0, 0.17))
    collide((0.0, 0.0, LINE0 - 0.35), (SLOPE + 0.30, 1.06, 0.62), -PITCH)
    collide((-1.45, 0.0, 0.17), (1.00, 1.16, 0.34))

    # Cross ties, sunk into the bank so none of them sits on it with a gap under.
    for x in (-1.05, -0.45, 0.15, 0.75):
        metal((0.12, 0.92, 0.09), (x, 0.0, line_z(x) - 0.02), rot=(0.0, -PITCH, 0.0))

    # The buttress the skip tips against, full height like a stop. The bank's high end is
    # inside it.
    fd.courses(1.34, 1.74, -0.60, 0.60, 0.0, (0.55, 0.50, 0.46))
    collide((1.54, 0.0, 0.755), (0.40, 1.20, 1.51))

    # The skip, in its own frame: floor, two side walls, a high back wall and a low front
    # wall to pour over. Walls plus a floor, so it is a vessel and not a tray.
    floor = 0.065 + 0.12 + 0.05
    tilted((1.00, 0.86, 0.10), (0.0, 0.0, floor))
    tilted((1.00, 0.09, 0.50), (0.0, -0.43, floor + 0.25))
    tilted((1.00, 0.09, 0.50), (0.0, 0.43, floor + 0.25))
    tilted((0.09, 0.86, 0.50), (-0.48, 0.0, floor + 0.23))
    tilted((0.09, 0.86, 0.34), (0.48, 0.0, floor + 0.17))

    # Ore, from just inside the floor up past the low front wall: the heap is what says
    # the skip is loaded, and it is stone so the pair stays two materials.
    ore_bottom = floor + 0.03
    uv.box((0.90, 0.78, 0.50), on_slope(0.0, 0.0, ore_bottom + 0.25), "stone",
           rot=(0.0, -PITCH, 0.0), bevel=0.03)
    uv.box((0.50, 0.46, 0.16), on_slope(0.12, 0.0, ore_bottom + 0.55), "stone",
           rot=(0.0, -PITCH + 6.0, 4.0), bevel=0.03)
    collide(on_slope(0.0, 0.0, floor + 0.28), (1.06, 0.96, 0.60), -PITCH)

    # Four wheels, axle across, each overlapping both the rail under it and the floor over
    # it. Placed along the slope, not along x, or half of them float.
    for along in (-0.30, 0.30):
        for y in (-0.34, 0.34):
            wx = CX + along * CP
            wheel = uv.cone(0.13, 0.13, 0.09, line_z(wx) + 0.065 + 0.07, "iron",
                            sides=7, centre=(wx, y))
            wheel.rotation_euler = (math.radians(90.0), 0.0, 0.0)

    # The lug the cable hooks into, on the skip's low front wall.
    tilted((0.10, 0.14, 0.14), (0.53, 0.0, floor + 0.20))

    # The winch behind the buttress: two posts, a crossbar and a drum across them.
    for y in (-0.56, 0.56):
        metal((0.14, 0.14, 1.30), (1.52, y, 1.10))
    metal((0.14, 1.40, 0.12), (1.52, 0.0, 1.78))
    drum = uv.cone(0.17, 0.17, 1.30, 1.88, "iron", sides=9, centre=(1.52, 0.0))
    drum.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    collide((1.52, 0.0, 1.80), (0.45, 1.40, 0.62))

    # The cable, drum to lug. One bar, tilted to meet both ends exactly, so no gap and no
    # overshoot; it clears the buttress by a good hand at the closest point.
    start = (1.45, 0.0, 1.80)
    end = on_slope(0.53, 0.0, floor + 0.20)
    dx, dz = start[0] - end[0], start[2] - end[2]
    length = math.hypot(dx, dz)
    angle = math.degrees(math.atan2(dz, dx))
    metal((length, 0.05, 0.05),
          ((start[0] + end[0]) / 2.0, 0.0, (start[2] + end[2]) / 2.0),
          rot=(0.0, -angle, 0.0), bevel=0.006)


def quaternion_for(rot_y):
    """
    The sidecar's rotation for a box turned about Blender's Y by rot_y degrees.

    Blender to the game is (x, y, z) -> (-x, z, y): the OBJ exporter with forward Z and up Y
    negates x, ObjMesh reads the numbers as they are, and the sidecar has to follow the mesh
    rather than Blender. That map is a proper rotation, so a turn about Blender's Y is a turn
    of the same angle about the game's Z. Checked numerically against the exported mesh by
    check_col, not trusted.
    """
    half = math.radians(rot_y) / 2.0
    return (0.0, 0.0, math.sin(half), math.cos(half))


def write_col(path):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# box  centre x y z  size x y z  qx qy qz qw\n")
        for (cx, cy, cz), (sx, sy, sz), rot in COLLIDERS:
            qx, qy, qz, qw = quaternion_for(rot)
            fh.write("box %.3f %.3f %.3f %.3f %.3f %.3f %.4f %.4f %.4f %.4f\n"
                     % (-cx, cz, cy, sx, sz, sy, qx, qy, qz, qw))


def _rotate(q, v):
    qx, qy, qz, qw = q
    x, y, z = v
    cx, cy, cz = qy * z - qz * y, qz * x - qx * z, qx * y - qy * x
    dx, dy, dz = qy * cz - qz * cy, qz * cx - qx * cz, qx * cy - qy * cx
    return (x + 2 * (qw * cx + dx), y + 2 * (qw * cy + dy), z + 2 * (qw * cz + dz))


def check_col(obj_path, col_path):
    """
    Reads the shipped .obj and .col back as the game will and counts, for every box, the
    mesh vertices lying on its surface (within 5cm, either side). A box that is turned the
    wrong way or mirrored matches far fewer, and nothing else in this script would say so:
    the build passes, the model looks right, and the collision is a ramp tilted the wrong
    way. Part corners are bevelled and jittered by a degree, so "on the surface" is a
    tolerance, and the bar is 8 (one corner's worth) rather than every vertex.
    """
    verts = []
    with open(obj_path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("v "):
                verts.append(tuple(float(n) for n in line.split()[1:4]))

    def surface_hits(centre, size, q):
        inverse = (-q[0], -q[1], -q[2], q[3])
        hits = 0
        for v in verts:
            local = _rotate(inverse, (v[0] - centre[0], v[1] - centre[1], v[2] - centre[2]))
            depth = [abs(local[i]) - size[i] / 2.0 for i in range(3)]
            if -0.05 <= max(depth) <= 0.05:
                hits += 1
        return hits

    failed = False
    with open(col_path, encoding="utf-8") as fh:
        index = 0
        for line in fh:
            if not line.startswith("box"):
                continue
            n = [float(t) for t in line.split()[1:]]
            centre, size, q = n[0:3], n[3:6], n[6:10]
            hits = surface_hits(centre, size, q)
            note = ""
            if abs(q[2]) > 1e-6:
                # A tilted box must beat the same box tilted the other way.
                other = surface_hits(centre, size, (q[0], q[1], -q[2], q[3]))
                note = "  (tilted the other way: %d)" % other
                if hits <= other:
                    failed = True
            if hits < 8:
                failed = True
            print("COL_CHECK box %d  %d vertices on its surface%s" % (index, hits, note))
            index += 1
    if failed:
        raise SystemExit("SKIP_FAIL a collision box does not match the mesh")


def make():
    uv.clear_scene()
    del COLLIDERS[:]
    build()
    return uv.finish(NAME)


def main():
    outdir = fd.arg("furnace_out", os.path.join(ASSETS, "previews"))
    os.makedirs(outdir, exist_ok=True)

    obj = make()
    tris = len(obj.data.polygons)
    open_n = fd.open_edges(obj)
    lo = [min(v.co[i] for v in obj.data.vertices) for i in range(3)]
    hi = [max(v.co[i] for v in obj.data.vertices) for i in range(3)]
    size = tuple(hi[i] - lo[i] for i in range(3))
    groups = [m.name for m in obj.data.materials]

    print("SKIP_OK tris=%d open_edges=%d boxes=%d groups=%s size=%.2f x %.2f x %.2f m"
          % (tris, open_n, len(COLLIDERS), groups, size[0], size[1], size[2]))
    if tris > fd.TRI_CAP:
        raise SystemExit("SKIP_FAIL over the %d triangle cap" % fd.TRI_CAP)
    if open_n:
        raise SystemExit("SKIP_FAIL %d open edges: something here can be looked through" % open_n)

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.obj_export(filepath=os.path.join(ASSETS, NAME + ".obj"),
                          export_selected_objects=True, export_materials=True,
                          forward_axis="Z", up_axis="Y")
    write_col(os.path.join(ASSETS, NAME + ".col"))
    check_col(os.path.join(ASSETS, NAME + ".obj"), os.path.join(ASSETS, NAME + ".col"))

    # The hammer icon, from the same geometry the game loads, tinted before it is shot or
    # it comes out as a pale blob next to vanilla's coloured ones.
    uv.tint()
    centre, span = uv.bounds(obj)
    uv.icon_scene(centre, span)
    uv.render(os.path.join(ASSETS, NAME + "_icon.png"), (128, 128))
    bpy.context.scene.render.film_transparent = False

    # The two reviews: eye height beside the furnace's measured mass, then the whole pair.
    # Rebuilt from scratch, because the icon pass left a camera and a transparent sky.
    make()
    uv.tint()
    fd.stage(None, 42.0, (0.6, -fd.EYE_BACK, 1.7), (0.6, 0.0, 1.25), size)
    uv.render(os.path.join(outdir, "furnace_skip_eye.png"), (760, 600))
    for o in list(bpy.context.scene.objects):
        if o.type == "CAMERA":
            o.data.lens = 24.0
            o.location = (1.0, -7.0, 1.7)
            fd.aim(o, (1.0, 0.0, 1.9))
    uv.render(os.path.join(outdir, "furnace_skip_wide.png"), (760, 600))
    print("SKIP_DONE")


main()
