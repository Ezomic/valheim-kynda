"""
Four candidate models for the blast furnace upgrade (LHM-47). Design step only: nothing
here is wired into the mod, and nothing is written to assets\\.

    blender --background --python tools/furnace_designs.py
    blender --background --python tools/furnace_designs.py -- only=hopper,skip

The Tun is a picture of ore and coal and the Woodrack a picture of firewood; the site's
roadmap says the blast furnace gets a piece of its own because a blast furnace is black
metal and stone. So these use two materials and no more, "blackmetal" and "stone", which
is also the vanilla rule (one or two submeshes per prop, never three or four palettes).
Neither borrowed palette is wired up yet: the skin donors are the follow-up once one is
picked. The tint table below is only so the renders can tell the two apart.

The four are meant to disagree at the outline, not in detail:

  hopper   a tall iron funnel on legs over a stone plinth, with a chute reaching the
           furnace. The only one that stands taller than a person.
  skip     a stone-sleepered rail ramp climbing toward the furnace with a tipped ore
           skip and a winch frame. A long diagonal, low at the near end.
  bunker   a stepped stone bunker in two bays under a sloping iron hood. Wide and low,
           the only one with a roofline.
  crane    a round stone charging well with an iron mast and a swung boom carrying a
           bucket. Vertical plus an overhang, the only round footprint.

Every part is a closed primitive, so there is no single-sided geometry to look through
(LHM-24). The open edge count is printed per variant anyway, counted on positions rather
than vertex indices so a split-normal vertex cannot inflate it; a funnel is made of
slabs and a fill, not a capped frustum, because a capped cone is a lid.

Rendering follows the family's rule: eye height (1.7m), three metres back, 42mm, a one
metre reference cube, and a grey block of the blast furnace's MEASURED mass beside it.
An upgrade is only ever seen touching its station, and a piece judged alone is a picture
of something the wrong size standing next to nothing.

The furnace, off own-profile\\BepInEx\\rips\\blastfurnace (the baked New/high/BF mesh, cm
space, the root sits at y 50 in the rip and is subtracted): 3.74 wide, 3.83 deep and
5.43 tall, centred at x -0.19. Its ore and coal hatches face +z in game and its output
spout is at x -1.93 on the left. Here it stands to the piece's +x, 1m clear of the piece's
edge, which is inside Kynda's 4m range with room to spare. The block is a bounding box,
so the real furnace has a narrower waist than it shows.

Everything is modelled at the size it would stand in game, scale 1.0. Kynda's Tun is
rendered at 1.5 because it sits against a 3m smelter; whichever of these is picked can
be scaled by config like the others, but the first render should not assume it.

Writes PNGs to the scratch directory given by furnace_out= (default beside this file's
repo, under assets\\previews\\furnace_*; the session passes a scratchpad path instead).
"""

import bpy
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import upgrade_variants as uv   # helpers only; it guards its own main()
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRI_CAP = 10000

# Measured, not picked. See the module note.
FURNACE = (3.74, 3.83, 5.43)
GAP = 1.0
EYE_BACK = 5.6

uv.TINTS.update({
    "blackmetal": (0.075, 0.075, 0.085, 1.0),
    "stone":      (0.50, 0.45, 0.38, 1.0),
    "block":      (0.56, 0.58, 0.62, 1.0),
    "ground":     (0.24, 0.30, 0.22, 1.0),
    "ref":        (0.88, 0.88, 0.88, 1.0),
})


def arg(name, default=None):
    if "--" not in sys.argv:
        return default
    for a in sys.argv[sys.argv.index("--") + 1:]:
        if a.startswith(name + "="):
            return a[len(name) + 1:]
    return default


# --------------------------------------------------------------------------- parts

def iron(size, loc, rot=(0.0, 0.0, 0.0), bevel=0.010):
    return uv.box(size, loc, "blackmetal", rot=rot, bevel=bevel)


def rock(size, loc, rot=(0.0, 0.0, 0.0), bevel=0.020):
    return uv.box(size, loc, "stone", rot=rot, bevel=bevel)


def courses(x0, x1, y0, y1, z0, heights, jut=0.025):
    """Stacked rubble courses: a few big boxes, each a little out of line with the last."""
    z = z0
    for h in heights:
        rock((x1 - x0 + uv.jitter(jut) * 2, y1 - y0 + uv.jitter(jut) * 2, h),
             ((x0 + x1) / 2.0 + uv.jitter(jut), (y0 + y1) / 2.0 + uv.jitter(jut), z + h / 2.0))
        z += h
    return z


# --------------------------------------------------------------------------- A: hopper

def hopper():
    # Stone plinth, then four legs standing on it and running up under the funnel.
    rock((1.70, 1.70, 0.30), (0.0, 0.0, 0.15))
    rock((1.50, 1.50, 0.16), (0.0, 0.0, 0.38))
    for x in (-0.50, 0.50):
        for y in (-0.50, 0.50):
            iron((0.16, 0.16, 1.45), (x, y, 1.18))
    iron((1.16, 0.10, 0.10), (0.0, -0.50, 0.98))
    iron((1.16, 0.10, 0.10), (0.0, 0.50, 0.98))
    iron((0.10, 1.16, 0.10), (-0.50, 0.0, 0.98))
    iron((0.10, 1.16, 0.10), (0.50, 0.0, 0.98))

    # Funnel: four slabs leaning in, 1.7m across at the rim (z 2.50) and 0.45 at the
    # throat (z 1.30). Slabs rather than a frustum, so the mouth is a mouth. The cant is
    # atan(0.625 / 1.2); each slab is a little longer than the slope so the corners overlap.
    cant = 27.5
    for side in (-1, 1):
        iron((1.82, 0.09, 1.42), (0.0, side * 0.545, 1.90), rot=(side * -cant, 0.0, 0.0))
        iron((0.09, 1.82, 1.42), (side * 0.545, 0.0, 1.90), rot=(0.0, side * cant, 0.0))

    # Ore filling the funnel to a hand below the rim, in the other material so the
    # mouth reads as full rather than as a dark well.
    rock((1.50, 1.50, 0.20), (0.0, 0.0, 2.30), bevel=0.03)

    # A heavy frame rim, the thing that makes it a tool and not a bucket.
    iron((1.96, 0.15, 0.13), (0.0, -0.88, 2.52))
    iron((1.96, 0.15, 0.13), (0.0, 0.88, 2.52))
    iron((0.15, 1.61, 0.13), (-0.88, 0.0, 2.52))
    iron((0.15, 1.61, 0.13), (0.88, 0.0, 2.52))

    # Chute out of the throat toward the furnace (+x), dropping 0.3m over its length.
    iron((1.30, 0.34, 0.10), (0.90, 0.0, 1.10), rot=(0.0, 13.0, 0.0))
    iron((1.30, 0.07, 0.22), (0.90, -0.20, 1.18), rot=(0.0, 13.0, 0.0))
    iron((1.30, 0.07, 0.22), (0.90, 0.20, 1.18), rot=(0.0, 13.0, 0.0))


# --------------------------------------------------------------------------- B: skip

def skip():
    run, rise = 3.0, 0.72
    pitch = math.degrees(math.atan2(rise, run))
    slope = math.hypot(run, rise)

    # Two rails climbing toward +x, with stone sleepers and a buttress at the foot.
    for y in (-0.34, 0.34):
        iron((slope, 0.11, 0.13), (0.0, y, 0.465 + rise / 2.0), rot=(0.0, -pitch, 0.0))

    # One stone bank under the rails, parallel to them, rather than a row of posts.
    rock((slope + 0.30, 1.06, 0.62), (0.0, 0.0, 0.215 + rise / 2.0 - 0.10),
         rot=(0.0, -pitch, 0.0), bevel=0.03)
    rock((1.00, 1.16, 0.34), (-1.45, 0.0, 0.17))
    for x in (-1.05, -0.45, 0.15, 0.75):
        zt = 0.40 + rise * ((x + run / 2.0) / run) + 0.04
        iron((0.12, 0.92, 0.07), (x, 0.0, zt + 0.02), rot=(0.0, -pitch, 0.0))

    # Buttress at the high end: the skip tips against it. Full height, like a stop.
    courses(1.34, 1.74, -0.60, 0.60, 0.0, (0.55, 0.50, 0.46))

    # The skip: a box bucket on the rails, tipped back with the slope. Walls plus a floor
    # so it is a vessel, with stone filling it level with the lip.
    cx = -0.35
    cz = 0.40 + rise * (cx + run / 2.0) / run + 0.20
    iron((1.00, 0.86, 0.10), (cx, 0.0, cz), rot=(0.0, -pitch, 0.0))
    iron((1.00, 0.09, 0.50), (cx, -0.43, cz + 0.25), rot=(0.0, -pitch, 0.0))
    iron((1.00, 0.09, 0.50), (cx, 0.43, cz + 0.25), rot=(0.0, -pitch, 0.0))
    iron((0.09, 0.86, 0.50), (cx - 0.48, 0.0, cz + 0.23), rot=(0.0, -pitch, 0.0))
    iron((0.09, 0.86, 0.34), (cx + 0.48, 0.0, cz + 0.17), rot=(0.0, -pitch, 0.0))
    rock((0.90, 0.78, 0.22), (cx, 0.0, cz + 0.22), rot=(0.0, -pitch, 0.0), bevel=0.03)
    for s in (-0.34, 0.34):
        for t in (-0.30, 0.30):
            uv.cone(0.14, 0.14, 0.10, cz - 0.10, "blackmetal", sides=7,
                    centre=(cx + t, s * 1.2))

    # A winch frame behind the buttress: two posts and a drum across them.
    for y in (-0.62, 0.62):
        iron((0.14, 0.14, 1.30), (1.52, y * 0.9, 1.10))
    drum = uv.cone(0.17, 0.17, 1.30, 1.88, "blackmetal", sides=9, centre=(1.52, 0.0))
    drum.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    iron((0.14, 1.40, 0.12), (1.52, 0.0, 1.78))


# --------------------------------------------------------------------------- C: bunker

def bunker():
    # Two bays, the back wall one course taller than the front, as a stepped section.
    courses(-1.05, 1.05, -0.70, -0.50, 0.0, (0.40, 0.34, 0.30))        # front wall
    courses(-1.05, 1.05, 0.50, 0.70, 0.0, (0.46, 0.40, 0.38, 0.32, 0.26))  # back wall
    courses(-1.05, -0.85, -0.70, 0.70, 0.0, (0.46, 0.40, 0.36, 0.30))  # left wall
    courses(0.85, 1.05, -0.70, 0.70, 0.0, (0.46, 0.40, 0.36, 0.30))    # right wall
    courses(-0.10, 0.10, -0.70, 0.70, 0.0, (0.46, 0.40, 0.36, 0.30))   # divider
    rock((2.06, 1.38, 0.14), (0.0, 0.0, 0.07))

    # Fill in each bay, stone, one course below the front lip.
    rock((0.80, 1.12, 0.70), (-0.50, 0.0, 0.42), bevel=0.03)
    rock((0.80, 1.12, 0.70), (0.50, 0.0, 0.42), bevel=0.03)

    # The hood: a sloped iron plate over the back half, on two stout posts, falling
    # toward the front. Roofline is the point of this one.
    for x in (-0.92, 0.92):
        iron((0.15, 0.15, 1.12), (x, 0.60, 1.00))
    iron((2.30, 1.10, 0.10), (0.0, 0.36, 1.62), rot=(-15.0, 0.0, 0.0))
    iron((2.30, 0.12, 0.30), (0.0, -0.18, 1.52), rot=(-15.0, 0.0, 0.0))

    # Ore heaped past the lip so the skyline is not a straight line, and a short spout
    # out of the right wall toward the furnace.
    uv.cone(0.46, 0.14, 0.40, 0.88, "stone", sides=5, centre=(-0.50, -0.05))
    uv.cone(0.46, 0.14, 0.34, 0.85, "stone", sides=5, centre=(0.50, 0.05))
    iron((0.90, 0.46, 0.10), (1.45, 0.0, 0.46), rot=(0.0, 14.0, 0.0))
    iron((0.90, 0.07, 0.20), (1.45, -0.26, 0.54), rot=(0.0, 14.0, 0.0))
    iron((0.90, 0.07, 0.20), (1.45, 0.26, 0.54), rot=(0.0, 14.0, 0.0))

    # Strapping across the front bays, bolted over the stone.
    for x in (-0.50, 0.50):
        iron((0.12, 0.10, 0.96), (x, -0.76, 0.52))
    iron((2.10, 0.10, 0.12), (0.0, -0.78, 0.98))


# --------------------------------------------------------------------------- D: crane

def crane():
    # The well: a stone drum, an open ring of rim stones, and an iron band round the
    # waist. Odd sides so it reads round from anywhere. The rim is separate stones round
    # an opening, not a capped disc: a capped cone is a lid.
    uv.cone(0.92, 0.86, 0.90, 0.45, "stone", sides=11, centre=(0.0, 0.0))
    uv.band(0.93, 0.12, 0.30, mat="blackmetal", sides=11, centre=(0.0, 0.0))
    count = 11
    for i in range(count):
        a = 2.0 * math.pi * i / count
        rock((0.62, 0.26, 0.22), (math.cos(a) * 0.80, math.sin(a) * 0.80, 1.01),
             rot=(0.0, 0.0, math.degrees(a) + 90.0), bevel=0.02)
    # Dark fill a hand below the lip, so the opening reads as full of something.
    uv.cone(0.70, 0.70, 0.10, 0.92, "blackmetal", sides=11, centre=(0.0, 0.0))

    # The mast on its own footing beside the well, with a strut up to the boom and the
    # boom swung out over the opening.
    rock((0.62, 0.62, 0.40), (-1.30, 0.0, 0.20), bevel=0.03)
    iron((0.20, 0.20, 2.30), (-1.30, 0.0, 1.50))
    iron((2.10, 0.15, 0.15), (-0.28, 0.0, 2.55), rot=(0.0, 1.5, 0.0))
    iron((1.52, 0.12, 0.12), (-0.82, 0.0, 2.02), rot=(0.0, -44.0, 0.0))

    # Chain and bucket hanging off the boom tip.
    iron((0.06, 0.06, 0.62), (0.52, 0.0, 2.20))
    uv.cone(0.26, 0.34, 0.34, 1.72, "blackmetal", sides=9, centre=(0.52, 0.0))
    uv.band(0.36, 0.07, 1.86, mat="blackmetal", sides=9, centre=(0.52, 0.0))


DESIGNS = [
    ("hopper", hopper, "tall iron funnel on legs, stone plinth, chute to the furnace"),
    ("skip", skip, "rail ramp with a tipped ore skip, buttress and winch frame"),
    ("bunker", bunker, "stepped stone twin bays under a sloping iron hood"),
    ("crane", crane, "round stone well, iron mast and boom, hanging bucket"),
]


# --------------------------------------------------------------------------- checks

def open_edges(obj):
    """Edges that belong to exactly one face, counted on positions rather than indices."""
    mesh = obj.data
    pos = [tuple(round(c, 5) for c in v.co) for v in mesh.vertices]
    seen = {}
    for poly in mesh.polygons:
        ids = [pos[i] for i in poly.vertices]
        for i in range(len(ids)):
            a, b = ids[i], ids[(i + 1) % len(ids)]
            key = (min(a, b), max(a, b))
            seen[key] = seen.get(key, 0) + 1
    return sum(1 for n in seen.values() if n == 1)


# --------------------------------------------------------------------------- staging

def aim(cam, target):
    direction = Vector(target) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def stage(obj_pos_centre, lens, cam_loc, cam_target, size):
    scene = bpy.context.scene

    bpy.ops.mesh.primitive_plane_add(size=60.0, location=(0.0, 0.0, 0.0))
    bpy.context.active_object.data.materials.append(uv.material("ground"))

    # The one metre reference cube, near the piece and well inside the frame.
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-2.0, -0.9, 0.5))
    bpy.context.active_object.data.materials.append(uv.material("ref"))

    # The furnace's measured mass. Output spout side is -x in game, which here is the
    # side nearest the piece; the lie is small and the block is a bounding box anyway.
    fx = 1.10 + GAP + FURNACE[0] / 2.0
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(fx, 0.0, FURNACE[2] / 2.0))
    block = bpy.context.active_object
    block.scale = (FURNACE[0], FURNACE[1], FURNACE[2])
    block.data.materials.append(uv.material("block"))

    bpy.ops.object.light_add(type="SUN", location=(-3.0, -4.0, 5.0))
    key = bpy.context.active_object
    key.data.energy = 1.4
    key.rotation_euler = (math.radians(52.0), 0.0, math.radians(-36.0))

    bpy.ops.object.light_add(type="SUN", location=(3.0, -3.0, 2.0))
    fill = bpy.context.active_object
    fill.data.energy = 0.35
    fill.rotation_euler = (math.radians(96.0), 0.0, math.radians(42.0))

    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.48, 0.52, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.28

    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.active_object
    cam.data.lens = lens
    cam.data.sensor_fit = "HORIZONTAL"
    aim(cam, cam_target)
    scene.camera = cam


def build(label, maker, blurb, outdir):
    uv.clear_scene()
    maker()
    obj = uv.finish("kynda_furnace_" + label)
    tris = len(obj.data.polygons)
    open_n = open_edges(obj)
    lo = [min(v.co[i] for v in obj.data.vertices) for i in range(3)]
    hi = [max(v.co[i] for v in obj.data.vertices) for i in range(3)]
    size = tuple(hi[i] - lo[i] for i in range(3))
    flag = "  OVER CAP" if tris > TRI_CAP else ""
    print("FURNACE_OK %-8s tris=%-5d open_edges=%-3d size=%.2f x %.2f x %.2f m  %s%s"
          % (label, tris, open_n, size[0], size[1], size[2], blurb, flag))
    uv.tint()

    # Eye height, three metres back, 42mm, aimed at the piece's middle.
    # About three metres back means from the piece's front edge: these stand 2 to 3m
    # across, and 42mm covers only 2.6m at 3m, so the camera sits a little further out
    # (EYE_BACK) to keep the whole piece and a slice of the furnace in frame.
    stage(None, 42.0, (0.6, -EYE_BACK, 1.7), (0.6, 0.0, 1.25), size)
    uv.render(os.path.join(outdir, "furnace_%s_eye.png" % label), (760, 600))

    # The same piece from further out, with the whole furnace in frame, so the pair
    # can be judged as one skyline. Wider lens, still eye height.
    for o in list(bpy.context.scene.objects):
        if o.type == "CAMERA":
            o.data.lens = 24.0
            o.location = (1.0, -7.0, 1.7)
            aim(o, (1.0, 0.0, 1.9))
    uv.render(os.path.join(outdir, "furnace_%s_wide.png" % label), (760, 600))
    return tris, open_n


def main():
    outdir = arg("furnace_out", os.path.join(ROOT, "assets", "previews"))
    os.makedirs(outdir, exist_ok=True)
    picked = arg("only")
    for label, maker, blurb in DESIGNS:
        if picked and label not in picked.split(","):
            continue
        build(label, maker, blurb, outdir)
    print("FURNACE_DONE")


if __name__ == "__main__":
    main()
