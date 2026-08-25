"""
Four Tuns, built to the rule the last one broke.

    blender --background --python tools/tun_designs.py

The shipped stoker_trough_casks was measured before this round and it explains itself:

    iron   696 faces  29.3%      <- hoops, modelled as separate bands
    ore    608 faces  25.6%      <- visible contents
    coal   608 faces  25.6%      <- visible contents
    wood   464 faces  19.5%      <- the actual object

Four material groups, and the timber is a fifth of the model. Every vanilla prop with a
rip here is ONE material on one submesh - piece_chest_barrel is barrelplayer_mat, barrell
is barrel_iron, and barrell's iron hoops are PAINTED INTO its wood texture rather than
modelled. So the old Tun spent half its triangles on contents vanilla hides and a third
on hoops vanilla paints, then wore four borrowed palettes that were never painted to sit
together. That is the "does not look like Valheim", and it is a rule rather than a taste.

So, for all four here:

  * ONE material group. No iron, no ore, no coal. A band is a shallow ring in the same
    timber, reading as a hoop through its own shadow, because the borrowed material
    brings vanilla's painted hoops with it.
  * No visible contents. A vanilla barrel does not show you what is in it.
  * Few large parts. The silhouette is the staves or the walls, not decoration.

The four are meant to disagree at the outline, not in detail:

  A  casks     two upright barrels, round and tall
  B  hopper    a tapered box on legs with a chute, the shape that feeds a furnace
  C  bin       a square open bin under a half lean-to, the only one with a roofline
  D  trough    a long low vessel on skids, wider than it is tall

Everything is rendered at Scale 1.5, which is what the runtime applies, beside a grey
block of the smelter's MEASURED mass - 3.03 x 4.24 x 2.58m off its rip. A bin judged
alone at raw scale is a picture of something two thirds the size standing next to
nothing, and that lie is what picked the last three rounds.
"""

import bpy
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import upgrade_variants as uv   # helpers only: the file guards its own main()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIEWS = os.path.join(ROOT, "assets", "previews")
VARIANTS = os.path.join(ROOT, "assets", "variants")

# What the runtime does to these, so the render is of the real thing.
SCALE = 1.5

# Off own-profile/BepInEx/rips/smelter. The neighbour is not decoration: an upgrade is
# only ever seen touching its station.
SMELTER = (3.03, 2.58, 4.24)


def timber(size, location, rot=(0.0, 0.0, 0.0), bevel=0.014):
    """A box in the one material this round allows."""
    return uv.box(size, location, "wood", rot=rot, bevel=bevel)


def stave_barrel(centre, radius, height, sides=9):
    """
    A cask at vanilla's density, which is far lower than the first cut of this assumed.

    Measured off Haldor's camp: fi_vil_container_barrel_small is 116 triangles for a
    0.64m barrel, barrel_big_fruit is 140, the keg is 142. The whole camp is built from
    meshes that size. The first version of this was 716 for the pair - five times a
    vanilla barrel - and it read smooth and round where the game is chunky and faceted.
    That density is a difference in how it looks, not just what it costs.

    So: nine sides, no modelled hoops, and no waist ring. The hoops come from the sheet,
    which is what fi_village_wood paints and what barrell paints too - the game makes a
    banded barrel with texture and a barrel of fish by moving the UVs, never by adding
    geometry.

    ends=True still splits the caps, because a timber sheet keeps its end discs in a
    corner and one rect over caps and staves gives the caps whatever is there.
    """
    cx, cy = centre
    body = uv.cone(radius * 0.86, radius, height * 0.5, height * 0.25, "wood",
                   sides=sides, centre=(cx, cy), ends=True)
    top = uv.cone(radius, radius * 0.86, height * 0.5, height * 0.75, "wood",
                  sides=sides, centre=(cx, cy), ends=True)

    return [body, top]


def casks():
    """A: two upright casks. Round and tall, the only curved outline of the four."""
    for side, radius in ((-0.42, 0.40), (0.44, 0.34)):
        stave_barrel((side, 0.0), radius, 1.05 if radius > 0.36 else 0.88)

    # One plank across the feet, so the pair reads as one object rather than as two
    # barrels that happen to stand together.
    timber((1.62, 0.34, 0.09), (0.02, 0.0, 0.045))
    uv.collide((0.0, 0.0, 0.55), (1.80, 0.95, 1.10))


def hopper():
    """B: a tapered box on legs with a chute. The shape that feeds a furnace."""
    # Narrow at the bottom, wide at the top, spanning z 0.52 to 1.32. Five sides rather
    # than four: a four-sided cone is a box stood on a smaller box, and the whole point
    # of this silhouette is that it tapers visibly.
    uv.cone(0.30, 0.56, 0.80, 0.92, "wood", sides=5, centre=(0.0, 0.0))

    # Legs, overlapping the body rather than touching it - a 5cm gap reads as a
    # detached stick at this scale. They span 0 to 0.58 against a body starting at 0.52.
    for x in (-0.26, 0.26):
        for y in (-0.24, 0.24):
            timber((0.15, 0.15, 0.58), (x, y, 0.29))

    # The chute, leaving the narrow end and angled forward. One part, not a funnel.
    timber((0.34, 0.44, 0.26), (0.0, -0.34, 0.50), rot=(math.radians(32.0), 0.0, 0.0))

    # A rim at the top edge, which is what stops it reading as a cut-off cone.
    uv.band(0.58, 0.10, 1.30, mat="wood", sides=5, centre=(0.0, 0.0))
    uv.collide((0.0, 0.0, 0.70), (1.20, 1.20, 1.40))


def bin_roofed():
    """C: a square bin with half a lean-to over it. The only one with a roofline."""
    for x, y, sx, sy in ((0.0, -0.46, 1.10, 0.14), (0.0, 0.46, 1.10, 0.14),
                         (-0.48, 0.0, 0.14, 1.06), (0.48, 0.0, 0.14, 1.06)):
        timber((sx, sy, 0.92), (x, y, 0.46))

    timber((1.14, 1.10, 0.12), (0.0, 0.0, 0.06))

    # Two posts and a sloping roof over the back half. The roof is what makes this
    # readable at four metres; without it this is a crate.
    for x in (-0.44, 0.44):
        timber((0.13, 0.13, 0.66), (x, 0.42, 1.24))

    timber((1.28, 0.78, 0.10), (0.0, 0.18, 1.62), rot=(math.radians(-17.0), 0.0, 0.0))
    uv.collide((0.0, 0.0, 0.60), (1.25, 1.20, 1.20))


def trough():
    """D: long, low and on skids. Wider than it is tall, which none of the others are."""
    timber((1.86, 0.86, 0.14), (0.0, 0.0, 0.22))

    for y, sy in ((-0.40, 0.13), (0.40, 0.13)):
        timber((1.86, sy, 0.52), (0.0, y, 0.53))
    for x in (-0.90, 0.90):
        timber((0.13, 0.86, 0.52), (x, 0.0, 0.53))

    # Skids, crossways, so the thing sits ON the ground rather than in it.
    for x in (-0.62, 0.62):
        timber((0.20, 1.04, 0.16), (x, 0.0, 0.08))

    # A capping rail down each long side. Two parts, and they are most of what stops a
    # box of planks reading as a packing crate.
    for y in (-0.40, 0.40):
        timber((1.94, 0.22, 0.10), (0.0, y, 0.82))

    uv.collide((0.0, 0.0, 0.45), (1.95, 1.05, 0.90))


def neighbour():
    """A grey block of the smelter's measured mass, and a 1m cube for scale."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(1.95, 0.9, SMELTER[2] / 2.0))
    block = bpy.context.active_object
    block.scale = SMELTER
    block.name = "smelter_mass"

    grey = bpy.data.materials.new("neighbour")
    grey.use_nodes = True
    grey.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.26, 0.25, 0.24, 1.0)
    block.data.materials.append(grey)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-2.1, 0.0, 0.5))
    cube = bpy.context.active_object
    cube.name = "one_metre"
    cube.data.materials.append(grey)


BUILDS = [
    ("stoker_tun_casks",  casks,       "A  casks - two upright barrels"),
    ("stoker_tun_hopper", hopper,      "B  hopper - tapered box on legs"),
    ("stoker_tun_bin",    bin_roofed,  "C  bin - square, half lean-to"),
    ("stoker_tun_trough", trough,      "D  trough - long and low on skids"),
]


def main():
    os.makedirs(PREVIEWS, exist_ok=True)
    os.makedirs(VARIANTS, exist_ok=True)

    for name, builder, label in BUILDS:
        uv.clear_scene()
        uv.COLLIDERS[:] = []
        builder()

        obj = uv.finish(name)
        uv.export(obj, name)
        tris = len(obj.data.polygons)

        # Scale AFTER the export, so the .obj is the raw model the runtime scales and
        # the picture is of the thing at the size it is actually drawn.
        obj.scale = (SCALE, SCALE, SCALE)
        bpy.ops.object.transform_apply(scale=True)

        uv.tint()
        neighbour()

        bpy.ops.object.light_add(type="SUN", location=(-2.4, -3.0, 4.0))
        sun = bpy.context.active_object
        sun.data.energy = 1.4
        sun.rotation_euler = (math.radians(52.0), 0.0, math.radians(-36.0))

        bpy.ops.object.light_add(type="SUN", location=(2.6, -2.2, 2.0))
        fill = bpy.context.active_object
        fill.data.energy = 0.35
        fill.rotation_euler = (math.radians(104.0), 0.0, math.radians(44.0))

        world = bpy.data.worlds.new("w")
        bpy.context.scene.world = world
        world.use_nodes = True
        world.node_tree.nodes["Background"].inputs[1].default_value = 0.28

        bpy.ops.mesh.primitive_plane_add(size=40.0, location=(0.0, 0.0, 0.0))
        ground = bpy.context.active_object
        ground.data.materials.append(bpy.data.materials["neighbour"])

        # Eye height, three metres back, 42mm. Never a hero orbit.
        target = bpy.data.objects.new("aim", None)
        bpy.context.scene.collection.objects.link(target)
        target.location = (0.1, 0.4, 1.1)

        # Far enough back to hold the piece, the smelter's mass and the metre cube in one
        # frame. Three metres put the camera inside the object and made a picture of a
        # barrel, which is the exact framing this round exists to stop making.
        bpy.ops.object.camera_add(location=(-1.4, -8.2, 1.7))
        cam = bpy.context.active_object
        cam.data.lens = 42
        bpy.context.scene.camera = cam
        track = cam.constraints.new(type="TRACK_TO")
        track.target = target
        track.track_axis = "TRACK_NEGATIVE_Z"
        track.up_axis = "UP_Y"

        bpy.context.scene.render.film_transparent = False
        uv.render(os.path.join(PREVIEWS, name + ".png"), (1000, 760))

        # The icon, beside the model rather than in assets/. A shape earns its place next
        # to the DLL by being moved up a folder, and its picture travels with it.
        uv.clear_scene()
        uv.COLLIDERS[:] = []
        builder()
        icon = uv.finish(name)
        uv.tint()
        centre, size = uv.bounds(icon)
        uv.icon_scene(centre, size)
        uv.render(os.path.join(VARIANTS, name + "_icon.png"), (128, 128))
        bpy.context.scene.render.film_transparent = False

        print("  %-22s %5d tris, %d collider(s)" % (label, tris, len(uv.COLLIDERS)))

    print("\nRenders in %s" % PREVIEWS)


main()
