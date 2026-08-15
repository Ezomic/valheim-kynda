"""
Second pass at both upgrade models. Richer, not bigger.

    blender --background --python tools/upgrade_variants.py

The first set read as plain next to real Valheim pieces, and the cause was not the
silhouettes - it was that upgrade_models.py never beveled. finish() there joins and
triangulates and nothing else, so every edge in both shipped models is a perfect
90 degrees. Vanilla has no perfect edges anywhere; a bevel per object before joining
is the single biggest thing separating "assembled from primitives" from "made".

So everything here goes through build(), which bevels each part *before* the join and
jitters it a few degrees and a few millimetres. Beveling after the join would work on
the intersections between overlapping parts and produce spikes, which is why it has
to happen per object.

The other three changes, all from the same diagnosis:

  - Members overlap far more, and there are fewer of them. A heap of small parts
    reads as noise at four metres; the eye wants a few large forms with real joins.
  - Every timber gets end-grain: a slightly proud, slightly rotated cap, because a
    sawn end catching light differently from the length is most of what says "cut
    from a tree" rather than "extruded".
  - Iron is strapping over timber rather than a frame around it. Vanilla's metal sits
    on top of wood and is bolted through it.

Writes assets/<name>.obj + .col, assets/<name>_icon.png and assets/previews/<name>.png.
"""

import bpy
import bmesh
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
PREVIEWS = os.path.join(ASSETS, "previews")

COLLIDERS = []
PARTS = []

# These get placed in rows beside a row of smelters, so the count is a real cost.
TRI_BUDGET = 15000

TINTS = {
    "wood":  (0.30, 0.19, 0.10, 1.0),
    "iron":  (0.19, 0.19, 0.21, 1.0),
    "stone": (0.42, 0.41, 0.38, 1.0),
    "coal":  (0.06, 0.06, 0.07, 1.0),
    "ore":   (0.34, 0.24, 0.16, 1.0),
}

# One stream for the whole file so a change anywhere reshuffles nothing downstream
# of it by accident - the .obj is committed, and unseeded jitter churns it every run.
_seed = [20260815]


def rnd():
    _seed[0] = (_seed[0] * 1103515245 + 12345) & 0x7FFFFFFF
    return (_seed[0] % 10000) / 10000.0


def jitter(amount=1.0):
    """A few degrees and a few millimetres. Perfect alignment is most of why a model
    reads as machined, and the fix is small enough to be invisible as an intent."""
    return (rnd() - 0.5) * amount


# --------------------------------------------------------------------------- helpers

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.objects,
                  bpy.data.lights, bpy.data.cameras, bpy.data.worlds):
        for item in list(block):
            if item.users == 0:
                block.remove(item)
    del COLLIDERS[:]
    del PARTS[:]
    _seed[0] = 20260815


def material(name):
    mat = bpy.data.materials.get(name)
    return mat if mat else bpy.data.materials.new(name)


def collide(centre, size):
    COLLIDERS.append((centre, size))


def part(obj, mat, bevel=0.012):
    obj.data.materials.append(material(mat))

    # Per object, before the join. The width is small because these are 10-20cm
    # timbers - a 12mm chamfer on a 10cm post is the width of a plane's pass, which
    # is what it is imitating.
    #
    # One segment, not two. The second segment doubles the geometry a bevel adds and
    # buys almost nothing at this width: a 12mm chamfer is four pixels at the distance
    # these are seen from, and what matters is that the edge catches light at all
    # rather than how smoothly it turns. That change alone took the barrels from 27k
    # triangles to comfortably inside budget.
    modifier = obj.modifiers.new(name="bevel", type="BEVEL")
    modifier.width = bevel
    modifier.segments = 1
    modifier.limit_method = "ANGLE"
    modifier.angle_limit = math.radians(40.0)

    PARTS.append(obj)
    return obj


def box(size, location, mat, rot=(0.0, 0.0, 0.0), wobble=1.0, bevel=0.012):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(
        location[0] + jitter(0.004) * wobble,
        location[1] + jitter(0.004) * wobble,
        location[2] + jitter(0.004) * wobble))
    obj = bpy.context.active_object
    # size, not size/2 - primitive_cube_add(size=1.0) is already a unit cube.
    obj.scale = size
    obj.rotation_euler = (math.radians(rot[0] + jitter(1.6) * wobble),
                          math.radians(rot[1] + jitter(1.6) * wobble),
                          math.radians(rot[2] + jitter(1.6) * wobble))
    return part(obj, mat, bevel)


def log(radius, length, location, mat="wood", axis="x", sides=7, rot=0.0, wobble=1.0):
    """
    Odd-sided on purpose. An even-sided cylinder presents a flat face to the camera
    and reads as a box; seven never does, at any rotation.
    """
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=length, vertices=sides,
                                        location=(location[0] + jitter(0.005) * wobble,
                                                  location[1] + jitter(0.005) * wobble,
                                                  location[2] + jitter(0.005) * wobble))
    obj = bpy.context.active_object
    rot_e = [0.0, 0.0, math.radians(rot + jitter(6.0) * wobble)]
    if axis == "x":
        rot_e[1] = math.radians(90 + jitter(1.4) * wobble)
    elif axis == "y":
        rot_e[0] = math.radians(90 + jitter(1.4) * wobble)
    obj.rotation_euler = rot_e
    return part(obj, mat, bevel=0.008)


def endgrain(radius, location, axis="x", mat="wood"):
    """
    A sawn end, sat slightly proud of the log it caps.

    Cheap and worth it: a flat disc catching light differently from the curved length
    is most of what says a timber was cut rather than extruded, and it is what makes
    a stack of logs read as a stack from across a clearing.
    """
    return log(radius * 1.04, 0.035, location, mat, axis=axis, sides=7, wobble=0.4)


def strap(length, location, mat="iron", axis="x", thickness=0.028, width=0.10, rot=0.0):
    """Iron over timber, not a frame around it - vanilla bolts its metal on top."""
    size = ((length, width, thickness) if axis == "x"
            else (width, length, thickness) if axis == "y"
            else (width, thickness, length))
    return box(size, location, mat, rot=(0.0, 0.0, rot), wobble=0.6, bevel=0.006)


def cone(bottom, top, height, z, mat, sides=9, centre=(0.0, 0.0)):
    """Odd-sided, so it never presents a flat face and reads as round from anywhere."""
    bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=bottom, radius2=top,
                                    depth=height, location=(centre[0], centre[1], z))
    obj = bpy.context.active_object
    obj.rotation_euler = (0.0, 0.0, math.radians(jitter(8.0)))
    return part(obj, mat, bevel=0.010)


def band(radius, height, z, mat="iron", sides=14, centre=(0.0, 0.0)):
    """
    A hoop, as one thin cylinder rather than a ring of blocks.

    The staves sit inside it, so only its outer wall is ever seen and a solid cylinder
    reads exactly as an iron band would. Built as blocks it was twenty-one beveled
    boxes per hoop and three hoops a barrel - about 1,400 triangles each where this is
    sixty, for a shape nobody can tell apart.
    """
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=height, vertices=sides,
                                        location=(centre[0], centre[1], z))
    obj = bpy.context.active_object
    obj.rotation_euler = (0.0, 0.0, math.radians(jitter(6.0)))
    return part(obj, mat, bevel=0.006)


def ring_count(radius, part_width, overlap=1.18):
    """
    How many parts a ring of this radius needs before they touch.

    Picked counts are how the first round two ended up as a colonnade and a cage:
    eleven 17cm logs around a 50cm radius cover 1.87m of a 3.14m circumference, so
    almost half of it is daylight. Overlap is not a nicety here - a ring of separate
    uprights reads as a fence around nothing, never as a stack of anything.
    """
    return max(5, int(math.ceil(2.0 * math.pi * radius * overlap / part_width)))


def bay(centre, inner, depth, mat, fill, wall=0.09, count=9, lump=0.15):
    """
    An open container: four thin walls and a floor, with the heap sunk inside so the
    rim cuts across it.

    Built as a frame rather than as a box with a lid on top, which is what the first
    pass did - a full-area plate across an opening reads as closed however much you
    pile on it, and the pile then reads as rubbish left on a crate rather than as the
    contents. The heap's top sits just under the rim for the same reason: material
    proud of the walls looks dropped on, material below them looks held.
    """
    cx, cy, cz = centre
    ix, iy = inner
    ox, oy = ix + wall * 2.0, iy + wall * 2.0

    box((ox, wall, depth), (cx, cy - (iy + wall) / 2.0, cz), mat)
    box((ox, wall, depth), (cx, cy + (iy + wall) / 2.0, cz), mat)
    box((wall, iy, depth), (cx - (ix + wall) / 2.0, cy, cz), mat)
    box((wall, iy, depth), (cx + (ix + wall) / 2.0, cy, cz), mat)
    box((ox, oy, 0.08), (cx, cy, cz - depth / 2.0 + 0.04), mat)

    heap((cx, cy, cz + depth / 2.0 - lump * 0.55), min(ix, iy) * 0.62,
         count, lump, fill)


def heap(centre, spread, count, size, mat, dome=0.55):
    """
    A mound, not a scatter. Lumps overlap their neighbours and sit lower towards the
    edges, so the silhouette is one shape - small lumps spread at a constant height
    read as confetti sitting on the model, and the tell is air around each one.
    """
    for _ in range(count):
        fx = rnd() - 0.5
        fy = rnd() - 0.5
        w = rnd()
        radial = min(1.0, (fx * fx + fy * fy) ** 0.5 * 2.0)
        s = size * (0.85 + w * 0.45)
        box((s, s, s * 0.7),
            (centre[0] + fx * spread,
             centre[1] + fy * spread,
             centre[2] - radial * size * dome + w * size * 0.12),
            mat, rot=(w * 14, w * 9, rnd() * 90), bevel=0.006)


# --------------------------------------------------------------------------- woodracks

def rack_lean():
    """
    A lean-to against nothing: two heavy posts, a sloped plank roof, logs stacked deep
    underneath. The roof slope is the whole silhouette - a flat lid reads as a crate.
    """
    for x in (-0.52, 0.52):
        box((0.13, 0.15, 1.16), (x, 0.0, 0.58), "wood")
        box((0.16, 0.18, 0.10), (x, 0.0, 0.03), "stone")          # footing pad

    # Roof: two overlapping planks, sloped, oversailing the posts at the low edge.
    box((1.34, 0.62, 0.07), (0.0, -0.14, 1.16), "wood", rot=(-13.0, 0.0, 0.0))
    box((1.34, 0.52, 0.06), (0.0, 0.30, 1.24), "wood", rot=(-13.0, 0.0, 0.0))
    strap(1.30, (0.0, 0.06, 1.21), axis="x")

    # Logs along Y, so the sawn ends face the front. Along X they were seen purely
    # side-on and read as smooth pipes: the end grain is the whole reason a woodpile
    # is legible at distance, and it has to be pointing at the viewer to do any work.
    # The preview camera stands on -y, so that is where the ends go.
    for row, z in enumerate((0.24, 0.50, 0.76)):
        offset = (row % 2) * 0.07 - 0.035
        for i in range(4):
            x = -0.33 + i * 0.22
            log(0.12, 0.62, (x, offset, z), axis="y")
            endgrain(0.12, (x, offset - 0.32, z), axis="y")

    box((0.98, 0.60, 0.10), (0.0, 0.02, 0.06), "wood")            # sill the pile sits on
    collide((0.0, 0.0, 0.62), (1.30, 0.68, 1.24))


def rack_crib():
    """
    A log crib - courses laid at right angles to each other, the way seasoning wood is
    actually stacked. No frame at all, so the silhouette is pure stacked timber.
    """
    for course in range(5):
        z = 0.13 + course * 0.215
        across = course % 2 == 0
        for i in range(4):
            offset = -0.33 + i * 0.22
            if across:
                log(0.105, 0.92, (0.0, offset, z), axis="x")
                endgrain(0.105, (-0.47, offset, z), axis="x")
            else:
                log(0.105, 0.92, (offset, 0.0, z), axis="y")
                endgrain(0.105, (offset, -0.47, z), axis="y")

    # Two stakes leaning in against the stack, which is what stops a real crib walking.
    box((0.09, 0.09, 1.24), (-0.53, 0.30, 0.60), "wood", rot=(0.0, 7.0, 0.0))
    box((0.09, 0.09, 1.24), (0.53, -0.30, 0.60), "wood", rot=(0.0, -7.0, 0.0))
    collide((0.0, 0.0, 0.58), (1.10, 1.10, 1.16))


def rack_barrow():
    """
    A two-wheeled barrow tipped back on its handles, loaded with split wood. Reads as
    a thing someone put down rather than a structure, which no other variant does.
    """
    box((1.05, 0.66, 0.10), (0.0, 0.0, 0.52), "wood", rot=(0.0, -16.0, 0.0))   # bed
    box((1.05, 0.09, 0.30), (0.0, -0.30, 0.66), "wood", rot=(0.0, -16.0, 0.0))
    box((1.05, 0.09, 0.30), (0.0, 0.30, 0.66), "wood", rot=(0.0, -16.0, 0.0))
    box((0.09, 0.62, 0.26), (-0.50, 0.0, 0.60), "wood", rot=(0.0, -16.0, 0.0))

    for y in (-0.34, 0.34):                                        # handles
        box((0.62, 0.07, 0.07), (0.62, y, 0.90), "wood", rot=(0.0, -16.0, 0.0))
    # Wood, and smaller. At 0.26 in iron the wheel was the largest single form on the
    # piece and the only grey one, so the eye read "wheel" before "woodpile".
    for y in (-0.34, 0.34):
        log(0.19, 0.08, (-0.30, y, 0.19), "wood", axis="y", sides=9, wobble=0.3)
    strap(0.74, (-0.30, 0.0, 0.24), axis="x", width=0.10)

    # Ends to the front, same reason as the lean-to.
    for row, z in enumerate((0.64, 0.82)):
        for i in range(3):
            x = -0.26 + i * 0.26
            log(0.105, 0.56, (x, 0.02 + row * 0.05, z), axis="y")
            endgrain(0.105, (x, -0.27 + row * 0.05, z), axis="y")
    collide((0.0, 0.0, 0.50), (1.34, 0.80, 1.00))


# --------------------------------------------------------------------------- troughs

def trough_bench():
    """
    A heavy bench with two sunk bays, ore in one and coal in the other, iron strapped
    over the corners. The legs are boxed rather than sticks - four thin posts read as
    a table, and a table is not a thing you shovel out of.
    """
    for x in (-0.46, 0.46):
        box((0.20, 0.60, 0.52), (x, 0.0, 0.26), "wood")            # slab legs
        box((0.26, 0.66, 0.07), (x, 0.0, 0.035), "stone")

    box((1.30, 0.76, 0.16), (0.0, 0.0, 0.58), "wood")              # the slab they sit in

    bay((-0.31, 0.0, 0.80), (0.40, 0.54), 0.30, "wood", "ore")
    bay((0.31, 0.0, 0.80), (0.40, 0.54), 0.30, "wood", "coal")

    for x in (-0.63, 0.63):
        strap(0.78, (x, 0.0, 0.60), axis="y", width=0.11)
    strap(1.24, (0.0, -0.39, 0.62), axis="x", width=0.09)
    collide((0.0, 0.0, 0.48), (1.34, 0.80, 0.96))


def trough_hod():
    """
    A stone hod on a timber cradle: the ore side is a stone box matching the smelter,
    the coal side an iron-bound tub. Two materials rather than one is what stops it
    reading as a planter.
    """
    # Stone on the ore side to echo the smelter, timber on the coal side. Both open -
    # the first attempt capped them and they read as two crates with litter on top.
    bay((-0.31, 0.0, 0.52), (0.46, 0.56), 0.46, "stone", "ore", wall=0.11, lump=0.15)
    bay((0.34, 0.0, 0.46), (0.38, 0.48), 0.36, "wood", "coal", lump=0.13, count=8)

    for z in (0.34, 0.58):
        strap(0.60, (0.34, 0.0, z), axis="y", width=0.09, thickness=0.030)

    box((1.34, 0.80, 0.16), (0.0, 0.0, 0.14), "wood")              # cradle
    for x in (-0.54, 0.54):
        box((0.14, 0.74, 0.22), (x, 0.0, 0.11), "wood")
    collide((0.0, 0.0, 0.44), (1.38, 0.82, 0.88))


def trough_scuttle():
    """
    A tipping scuttle in a timber frame - one deep hopper, angled, with a lip to shovel
    from. One large form instead of two small ones, which is the variant that tests
    whether the divided-bay idea was ever necessary.
    """
    # One deep open hopper standing on stone, rather than a closed tub slung in a
    # gantry. The gantry was the mistake: it left the body floating with daylight all
    # round it, and a piece that does not touch the ground reads as unfinished.
    bay((0.0, 0.0, 0.66), (0.74, 0.62), 0.54, "wood", "coal",
        wall=0.10, count=12, lump=0.16)

    box((0.44, 0.66, 0.09), (0.58, 0.0, 0.80), "iron", rot=(0.0, 22.0, 0.0))   # lip

    for z in (0.50, 0.80):
        strap(0.86, (0.0, 0.0, z), axis="y", width=0.12, thickness=0.032)

    box((1.06, 0.86, 0.24), (0.0, 0.0, 0.14), "stone")             # plinth
    for x in (-0.40, 0.40):                                        # corner posts
        box((0.13, 0.13, 0.44), (x, -0.36, 0.42), "wood")
        box((0.13, 0.13, 0.44), (x, 0.36, 0.42), "wood")
    collide((0.0, 0.0, 0.48), (1.10, 0.90, 0.96))


# --------------------------------------------------------------------------- round two
#
# The first six are all rectangular masses roughly a metre across, which means that
# from twenty metres they are one shape with different detail on it. These six each
# take a silhouette none of those had - triangular, round, ground-hugging, tall -
# because silhouette is the only thing that survives distance, and two designs sharing
# an outline are one design.


def rack_aframe():
    """
    Two leaning faces of logs meeting at a ridge. Triangular from every side, which
    nothing else here is, and it needs no frame - the lean is what holds it.
    """
    for side in (-1, 1):
        for row in range(5):
            t = row / 4.0
            x = side * (0.46 - t * 0.34)
            z = 0.16 + t * 0.86
            for i in range(3):
                y = -0.26 + i * 0.26
                log(0.105, 0.58, (x, y, z), axis="y", rot=side * -16.0)
                endgrain(0.105, (x, y - 0.29, z), axis="y")

    box((0.16, 0.72, 0.12), (0.0, 0.0, 1.06), "wood")              # ridge cap
    for y in (-0.34, 0.34):                                        # ground rails
        box((1.12, 0.12, 0.11), (0.0, y, 0.055), "wood")
    collide((0.0, 0.0, 0.54), (1.10, 0.80, 1.08))


def rack_rick():
    """
    A round rick - logs stacked on end in a ring, drawn in towards the top and hooded
    with turf. Circular in plan, domed in profile, and the only piece here with no
    straight vertical edge anywhere.
    """
    for ring, (radius, z, height, r) in enumerate((
            (0.48, 0.32, 0.64, 0.095), (0.38, 0.78, 0.38, 0.090), (0.22, 1.02, 0.24, 0.085))):
        count = ring_count(radius, r * 2.0)
        for i in range(count):
            a = (i / float(count)) * math.tau + ring * 0.4
            log(r, height, (math.cos(a) * radius, math.sin(a) * radius, z),
                axis="z", rot=math.degrees(a))
            endgrain(r, (math.cos(a) * radius, math.sin(a) * radius, z + height / 2.0),
                     axis="z")

    # A turf cone that oversails the top ring. Two stacked slabs read as a chimney
    # block sitting on the stack rather than as something covering it, and the whole
    # point of a rick's hood is that it sheds rain over the edge.
    cone(0.40, 0.13, 0.30, 1.20, "stone")
    box((1.18, 1.18, 0.12), (0.0, 0.0, 0.06), "stone", rot=(0.0, 0.0, 12.0))   # base pad
    collide((0.0, 0.0, 0.60), (1.14, 1.14, 1.20))


def rack_upright():
    """
    Logs stood on end in a low timber corral, the way a woodshed is actually filled
    when the wood is going to be split again. Reads as a mass of vertical lines rather
    than horizontal ones, which is the opposite of every other rack here.
    """
    # Packed on a grid tighter than the log diameter, not scattered on a circle. The
    # first attempt put fourteen posts on two rings and left daylight between all of
    # them, which reads as a few stakes standing in a box rather than as a corral with
    # wood in it. A container has to look full or it looks abandoned.
    radius, step = 0.085, 0.148
    for ix in range(6):
        for iy in range(5):
            x = -0.37 + ix * step
            y = -0.30 + iy * step
            h = 0.80 + ((ix * 5 + iy) % 5) * 0.075
            log(radius, h, (x, y, h / 2.0 + 0.09), axis="z",
                rot=(ix * 37 + iy * 61) % 90)
            endgrain(radius, (x, y, h + 0.09), axis="z")

    # A corral of four low boards, overlapping at the corners rather than mitred.
    for y in (-0.42, 0.42):
        box((1.06, 0.09, 0.46), (0.0, y, 0.25), "wood")
    for x in (-0.50, 0.50):
        box((0.09, 0.94, 0.46), (x, 0.0, 0.25), "wood")
    for x in (-0.50, 0.50):
        for y in (-0.42, 0.42):
            box((0.14, 0.14, 0.62), (x, y, 0.31), "wood")          # corner posts
    collide((0.0, 0.0, 0.50), (1.14, 1.00, 1.00))


def trough_barrels():
    """
    Two open-topped barrels on a sled. Round where every other trough is square, and
    the staves give it vertical banding that catches light at any angle.
    """
    stave = 0.085

    # The two are not clones. A pair of identical barrels reads as one asset placed
    # twice, which is the tell that gives away a kit - so they differ in height, in
    # girth and in how far they are turned, by about as much as two real casks would.
    for x, radius, top, turn, fill in ((-0.33, 0.285, 0.86, 0.0, "ore"),
                                       (0.36, 0.265, 0.78, 24.0, "coal")):
        staves = ring_count(radius, stave)
        for i in range(staves):
            a = (i / float(staves)) * math.tau + math.radians(turn)
            # Staves bulge: a barrel is widest at its belly, and a straight-sided one
            # is a bucket. Two courses with the upper set pulled in does it cheaply.
            box((stave, stave, top * 0.62),
                (x + math.cos(a) * radius, math.sin(a) * radius, top * 0.34),
                "wood", rot=(0.0, 0.0, math.degrees(a)), wobble=0.5)
            box((stave * 0.94, stave * 0.94, top * 0.42),
                (x + math.cos(a) * (radius - 0.022), math.sin(a) * (radius - 0.022),
                 top * 0.78),
                "wood", rot=(0.0, 0.0, math.degrees(a)), wobble=0.5)

        # Three hoops, not two, and the top one sits right under the rim where a
        # cooper puts it.
        # Clear of the staves, not level with them. A stave box centred at `radius` has
        # its outer face at radius + half its width, so a band any tighter than that is
        # buried inside the barrel and renders as nothing at all - which is exactly what
        # happened at radius + 0.035 against a 0.085 stave.
        outer = radius + stave / 2.0
        for z, r in ((top * 0.16, outer + 0.022), (top * 0.60, outer + 0.022),
                     (top * 0.94, outer - 0.010)):
            band(r, 0.075, z, centre=(x, 0.0))

        box((radius * 2.0, radius * 2.0, 0.09), (x, 0.0, 0.24), "wood")   # floor
        # Heaped proud of the rim rather than sunk out of sight. These are open casks
        # and what is in them is how you tell the ore side from the coal side.
        heap((x, 0.0, top + 0.02), radius * 0.78, 12, 0.155, fill, dome=0.42)

    # A sled with real cross members and iron at the corners, rather than one plank.
    box((1.40, 0.80, 0.13), (0.0, 0.0, 0.175), "wood")
    for y in (-0.31, 0.31):
        box((1.48, 0.14, 0.14), (0.0, y, 0.07), "wood")
    for x in (-0.60, 0.60):
        box((0.14, 0.74, 0.12), (x, 0.0, 0.175), "wood")
        strap(0.78, (x, 0.0, 0.245), axis="y", width=0.10)
    collide((0.0, 0.0, 0.50), (1.46, 0.84, 1.00))


def trough_pit():
    """
    A stone-kerbed pit, barely above the ground. Almost no vertical silhouette at all,
    which makes it the one option that does not block sightlines in a packed base -
    and the one most likely to disappear next to a smelter.
    """
    # Laid as individual blocks rather than four long boxes. A continuous kerb reads
    # as a moulded trough - a bathtub - where overlapping stones of slightly different
    # length read as something someone set by hand, which is what the piece is.
    def kerb(along, fixed, axis, count, span):
        for i in range(count):
            t = -span / 2.0 + span * (i + 0.5) / count
            length = span / count * 1.22
            width = 0.21 + (i % 3) * 0.02
            height = 0.30 + (i % 2) * 0.035
            pos = (t, fixed, height / 2.0) if axis == "x" else (fixed, t, height / 2.0)
            size = (length, width, height) if axis == "x" else (width, length, height)
            box(size, pos, "stone", rot=(0.0, 0.0, jitter(4.0)))

    kerb(None, -0.50, "x", 5, 1.66)
    kerb(None, 0.50, "x", 5, 1.66)
    kerb(None, -0.74, "y", 3, 1.02)
    kerb(None, 0.74, "y", 3, 1.02)

    box((1.34, 0.86, 0.10), (0.0, 0.0, 0.05), "stone")             # floor

    # Deeper heaps. At 10 lumps they sat below the kerb and the pit read as empty
    # from standing height, which is the one thing a full pit must not do.
    box((0.12, 0.90, 0.30), (0.0, 0.0, 0.18), "wood")              # divider plank
    heap((-0.35, 0.0, 0.30), 0.32, 14, 0.15, "ore", dome=0.40)
    heap((0.35, 0.0, 0.30), 0.32, 14, 0.15, "coal", dome=0.40)

    for x in (-0.74, 0.74):                                        # timber capping
        box((0.27, 1.14, 0.09), (x, 0.0, 0.345), "wood")
    for x in (-0.74, 0.74):                                        # corner posts
        for y in (-0.50, 0.50):
            box((0.15, 0.15, 0.52), (x, y, 0.26), "wood")
    collide((0.0, 0.0, 0.26), (1.74, 1.20, 0.52))


def trough_tower():
    """
    A tall standing bin fed from the top and drawn from a chute at the bottom. The only
    piece taller than it is wide, so it breaks a skyline where the rest sit under it.
    """
    bay((0.0, 0.0, 1.08), (0.56, 0.52), 0.42, "wood", "coal", wall=0.09, count=9)

    box((0.74, 0.70, 0.70), (0.0, 0.0, 0.62), "wood")              # body
    box((0.66, 0.34, 0.30), (0.0, -0.42, 0.34), "wood", rot=(28.0, 0.0, 0.0))  # chute
    box((0.58, 0.20, 0.06), (0.0, -0.56, 0.22), "iron", rot=(28.0, 0.0, 0.0))

    for z in (0.44, 0.78):
        strap(0.78, (0.0, 0.0, z), axis="y", width=0.11, thickness=0.030)
    for x in (-0.34, 0.34):                                        # feet
        box((0.15, 0.62, 0.28), (x, 0.05, 0.14), "wood")
    box((0.92, 0.86, 0.10), (0.0, 0.0, 0.05), "stone")
    collide((0.0, 0.0, 0.66), (0.82, 0.78, 1.32))


# --------------------------------------------------------------------------- export

VARIANTS = [
    ("stoker_rack_lean",      rack_lean,      "WOODRACK - Lean-to"),
    ("stoker_rack_crib",      rack_crib,      "WOODRACK - Log crib"),
    ("stoker_rack_barrow",    rack_barrow,    "WOODRACK - Barrow"),
    ("stoker_trough_bench",   trough_bench,   "TROUGH - Bench"),
    ("stoker_trough_hod",     trough_hod,     "TROUGH - Stone hod"),
    ("stoker_trough_scuttle", trough_scuttle, "TROUGH - Scuttle"),

    ("stoker_rack_aframe",    rack_aframe,    "WOODRACK - A-frame"),
    ("stoker_rack_rick",      rack_rick,      "WOODRACK - Round rick"),
    ("stoker_rack_upright",   rack_upright,   "WOODRACK - Upright corral"),
    ("stoker_trough_barrels", trough_barrels, "TROUGH - Twin barrels"),
    ("stoker_trough_pit",     trough_pit,     "TROUGH - Kerbed pit"),
    ("stoker_trough_tower",   trough_tower,   "TROUGH - Standing bin"),
]


def finish(name):
    # Apply every bevel before joining. After the join the modifier would work on the
    # intersections between overlapping parts, which produces spikes rather than edges.
    for obj in PARTS:
        bpy.context.view_layer.objects.active = obj
        for modifier in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=modifier.name)

    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
    bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = name

    # join() adopts the first object's transform and rewrites every other vertex into
    # its local space, so the transform has to be applied before anything is measured.
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=1.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")

    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(mesh)
    bm.free()
    return obj


def write_col(path):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# box  centre x y z  size x y z  qx qy qz qw\n")
        for (cx, cy, cz), (sx, sy, sz) in COLLIDERS:
            # The sidecar is read in Unity space, so it swaps y and z itself.
            fh.write("box %.3f %.3f %.3f %.3f %.3f %.3f 0 0 0 1\n"
                     % (cx, cz, cy, sx, sz, sy))


def tint():
    for mat in bpy.data.materials:
        key = mat.name.split(".")[0].lower()
        if key not in TINTS:
            continue
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = TINTS[key]
            bsdf.inputs["Roughness"].default_value = 0.85


def export(obj, name):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    # Blender is Z-up, Unity is Y-up.
    bpy.ops.wm.obj_export(filepath=os.path.join(ASSETS, name + ".obj"),
                          export_selected_objects=True, export_materials=True,
                          forward_axis="Z", up_axis="Y")
    write_col(os.path.join(ASSETS, name + ".col"))


def world_scene():
    """Eye height, a metre reference cube, and a plain ground - never a hero orbit."""
    bpy.ops.mesh.primitive_plane_add(size=40.0, location=(0.0, 0.0, 0.0))
    bpy.context.active_object.data.materials.append(material("ground"))

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-1.5, 0.4, 0.5))
    bpy.context.active_object.data.materials.append(material("ref"))

    bpy.ops.object.light_add(type="SUN", location=(-3.0, -4.0, 5.0))
    key = bpy.context.active_object
    key.data.energy = 3.0
    key.rotation_euler = (math.radians(52.0), 0.0, math.radians(-36.0))

    bpy.ops.object.light_add(type="SUN", location=(3.0, -3.0, 2.0))
    fill = bpy.context.active_object
    fill.data.energy = 1.0
    fill.rotation_euler = (math.radians(96.0), 0.0, math.radians(42.0))

    world = bpy.data.worlds.new("w")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.48, 0.44, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.7

    # Eye height, but tilted down 12 degrees rather than level. A rotation of 86 looks
    # 4 degrees *up*, which at 3m with a 42mm lens starts the frame 0.34m off the
    # ground and cuts the legs off every one of these. 78 puts the whole piece in shot
    # with headroom, and is still the angle you would actually see it from.
    bpy.ops.object.camera_add(location=(0.6, -3.2, 1.7))
    cam = bpy.context.active_object
    cam.data.lens = 42.0
    cam.rotation_euler = (math.radians(78.0), 0.0, math.radians(11.0))
    bpy.context.scene.camera = cam


def icon_scene(centre, size):
    scene = bpy.context.scene
    scene.render.film_transparent = True

    target = bpy.data.objects.new("target", None)
    scene.collection.objects.link(target)
    target.location = centre

    around, up = math.radians(35.0), math.radians(26.0)
    distance = size * 3.0
    bpy.ops.object.camera_add(location=(
        centre[0] + distance * math.cos(up) * math.sin(-around),
        centre[1] - distance * math.cos(up) * math.cos(around),
        centre[2] + distance * math.sin(up)))
    cam = bpy.context.active_object
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = size * 1.12
    scene.camera = cam

    track = cam.constraints.new(type="TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    bpy.ops.object.light_add(type="SUN", location=(centre[0] - 2, centre[1] - 2.4, centre[2] + 2.2))
    key = bpy.context.active_object
    key.data.energy = 3.1
    key.rotation_euler = (math.radians(54.0), 0.0, math.radians(-38.0))

    bpy.ops.object.light_add(type="SUN", location=(centre[0] + 2.2, centre[1] - 1.8, centre[2] - 0.6))
    fill = bpy.context.active_object
    fill.data.energy = 1.0
    fill.rotation_euler = (math.radians(102.0), 0.0, math.radians(40.0))

    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.0


def render(path, size):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = path
    # Blender 4.x defaults to AgX, which rolls the flat colour bands towards white.
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    bpy.ops.render.render(write_still=True)


def bounds(obj):
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for corner in obj.bound_box:
        for i in range(3):
            lo[i] = min(lo[i], corner[i])
            hi[i] = max(hi[i], corner[i])
    centre = [(lo[i] + hi[i]) / 2.0 for i in range(3)]
    return centre, max(hi[i] - lo[i] for i in range(3))


def main():
    os.makedirs(PREVIEWS, exist_ok=True)
    over = []

    for name, builder, label in VARIANTS:
        clear_scene()
        builder()
        obj = finish(name)
        export(obj, name)
        tris = len(obj.data.polygons)
        boxes = len(COLLIDERS)

        centre, size = bounds(obj)
        icon_scene(centre, size)
        render(os.path.join(ASSETS, name + "_icon.png"), (128, 128))

        clear_scene()
        builder()
        obj = finish(name)
        tint()
        world_scene()
        render(os.path.join(PREVIEWS, name + ".png"), (620, 560))

        # Said out loud on every build rather than checked once by hand. A model creeps
        # over budget one detail at a time and the cost is invisible in the render -
        # these are placed in rows of eight, so the count is a real number and not a
        # tidiness concern.
        flag = "  OVER BUDGET" if tris > TRI_BUDGET else ""
        print("VARIANT_OK %-24s tris=%-6d colliders=%d  %s%s"
              % (name, tris, boxes, label, flag))
        if flag:
            over.append((name, tris))

    if over:
        print("BUDGET_FAIL " + ", ".join("%s=%d" % (n, t) for n, t in over))
    print("VARIANTS_DONE")


main()
