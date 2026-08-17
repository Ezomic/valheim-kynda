"""
Third pass at the two upgrade models, and first a corrected way of looking at them.

    blender --background --python tools/upgrade_remodel.py

Both shipped pieces read acceptably as a 128px icon and less well at eye height, which
is the complaint this pass exists to answer. Before changing any geometry, two things
about the rig that produced every render we have picked from so far:

**The renders are not at the size the game draws.** Both pieces carry Scale 1.5 in
config - measured deliberately, because the modelled cask was 0.57m across against a
vanilla barrell's 0.84 - and the preview has always rendered the raw model beside a 1m
reference cube. So every judgement so far was made about a piece two thirds the size of
the one standing in the world. A rack that looks fussy at 1.35m is a different problem
from a rack that looks fussy at 2.03m: the first wants fewer parts, the second wants
bigger ones, and we could not tell which we had.

**The lights are hot enough to flatten it.** vhbuild's own note says the tell is dark
brown rendering as pale beige, and that is exactly what these do: `wood` is authored at
0.30, 0.19, 0.10 and comes out sand-coloured. The arithmetic is not close - a sun at
3.0 plus a fill at 1.0 plus a world at 0.7 puts a 0.30 albedo at roughly 0.47 linear,
which is 0.72 in sRGB. Everything therefore renders at nearly one value, and value is
most of what tells you whether a silhouette is reading. Key 1.4 lands the same surface
near 0.45 and leaves the shadowed faces somewhere to go.

**And nothing was ever in frame with it.** These are upgrades: they are only ever seen
touching a smelter or a charcoal kiln, and a shape that reads on its own in an empty
field can still vanish against 4 metres of stonework. The grey block is the smelter's
measured size, so the question the render answers is the one that matters - can you
tell there is something there, from where you stand.

Candidates are written to assets/variants/, never assets/, so re-running this cannot
quietly put a rejected design back in the build menu.
"""

import bpy
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Helpers only - upgrade_variants guards its own main(), so importing it builds nothing.
# The state it owns (COLLIDERS, PARTS, the jitter seed) stays in its namespace and every
# helper here goes through it, so nothing below may rebind those names.
from upgrade_variants import (                                    # noqa: E402
    ASSETS, PREVIEWS, SHELF, TINTS,
    band, bounds, box, clear_scene, collide, cone, contents, finish, heap, icon_scene,
    jitter, log, material, part, render, ring_count, rnd, strap, tint, write_col,
    rack_lean, trough_barrels,
)

# What the runtime applies to each piece, from StokerConfig. Rendering without it is
# what made every previous preview a picture of something smaller than the piece.
SCALE = {"trough": 1.5, "rack": 1.5}

# The smelter, from the rip: 3.03 wide, 2.58 deep, 4.24 tall. The charcoal kiln is a
# similar mass, so one block stands in for both rather than inventing a second figure.
STATION = (3.03, 2.58, 4.24)

# Key, fill and sky. Low enough that a 0.30 albedo stays a dark timber rather than
# turning to sand - see the note above.
KEY, FILL, SKY = 1.4, 0.35, 0.28


def scale_for(name):
    return SCALE["rack"] if "rack" in name else SCALE["trough"]


def staged_scene(size, close=False):
    """
    Eye height, three and a half metres back, with the station it upgrades beside it.

    Not a hero orbit and not an empty field. `size` is the scale the runtime will apply,
    and it is applied to the model here rather than to the camera, so the reference cube
    and the station block stay honest metres.
    """
    # icon_scene turns film_transparent on and nothing turns it off, so a staged render
    # taken after an icon in the same run came out with a white void for a sky - which
    # reads as a blown exposure and sends you to the lights. Cleared here rather than
    # there, because this is the pass that needs it off.
    bpy.context.scene.render.film_transparent = False

    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.scale = (size, size, size)

    bpy.ops.mesh.primitive_plane_add(size=60.0, location=(0.0, 0.0, 0.0))
    ground = bpy.context.active_object
    ground.data.materials.append(material("ground"))

    # A metre cube, close enough to the piece to be compared against it without
    # overlapping. Everything here is now up to 2m wide, so it moves further out.
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-2.35, 0.2, 0.5))
    bpy.context.active_object.data.materials.append(material("ref"))

    # The station, set back and to one side. Grey and featureless on purpose: the
    # question is whether the upgrade separates from that much mass, not whether our
    # stand-in looks like a smelter. It runs out of frame, which is correct - it is
    # context rather than subject, and framing it whole would shrink the piece.
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(
        STATION[0] / 2.0 + 1.45, 1.05, STATION[2] / 2.0))
    station = bpy.context.active_object
    station.scale = STATION
    station.data.materials.append(material("station"))

    bpy.ops.object.light_add(type="SUN", location=(-3.0, -4.0, 5.0))
    key = bpy.context.active_object
    key.data.energy = KEY
    key.data.angle = math.radians(3.0)
    key.rotation_euler = (math.radians(52.0), 0.0, math.radians(-36.0))

    bpy.ops.object.light_add(type="SUN", location=(3.0, -3.0, 2.0))
    fill = bpy.context.active_object
    fill.data.energy = FILL
    fill.rotation_euler = (math.radians(96.0), 0.0, math.radians(42.0))

    world = bpy.data.worlds.new("w")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.48, 0.44, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = SKY

    # Further back than the old rig's 3.2m, because the subject is now half again as
    # large and has a 4m block standing next to it. Still 1.7m off the ground and still
    # tilted down rather than level - a level camera at this distance cuts the legs off.
    #
    # 35mm rather than 42. Not a wider look for its own sake: at 42 a 2.2m piece with a
    # metre cube one side and a smelter the other does not fit at any distance you would
    # actually stand at, and backing off far enough to fit it stops being eye height and
    # starts being a survey photograph.
    # close is for comparing a detail rather than a silhouette - still standing height,
    # just at the distance you are at when you actually put ore in the thing. A detail
    # pass needs its own frame: at 5.4m a hoop is four pixels and every treatment of it
    # looks identical, which is how a part nobody can see gets argued about.
    if close:
        bpy.ops.object.camera_add(location=(0.05, -4.0, 1.62))
        cam = bpy.context.active_object
        cam.data.lens = 42.0
        cam.rotation_euler = (math.radians(84.0), 0.0, math.radians(0.0))
    else:
        bpy.ops.object.camera_add(location=(0.25, -5.4, 1.7))
        cam = bpy.context.active_object
        cam.data.lens = 35.0
        cam.rotation_euler = (math.radians(83.0), 0.0, math.radians(0.0))
    bpy.context.scene.camera = cam


def tint_stage():
    """The two stand-ins, kept out of TINTS so they cannot be mistaken for a material
    group a model is allowed to use."""
    for name, colour in (("ground", (0.19, 0.21, 0.16, 1.0)),
                         ("ref", (0.55, 0.55, 0.58, 1.0)),
                         ("station", (0.38, 0.38, 0.40, 1.0))):
        mat = material(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = colour
            bsdf.inputs["Roughness"].default_value = 0.9


# --------------------------------------------------------------------------- candidates
#
# Executions, not concepts. Both silhouettes were already picked out of a field of
# twelve, and re-running that contest would be answering a question that has been
# answered. What the staged baseline shows is that neither piece fails at the level of
# "is a lean-to the right idea" - they fail at the level of what the parts are doing.
#
# The rack's diagnosis is one line: billet() plays a lottery with the cross-section.
# Three, four, five, six and seven sides, a full turn of roll and a taper that flips end
# for end - all aimed at "no two logs alike", and at 2 metres the result is a frame
# packed with pentagonal rubble. Vanilla varies a woodpile's diameter and never its
# cross-section: every piece in wood_stack is a round, which is exactly why you read it
# as wood from thirty metres. So the candidates below all use rounds.
#
# The trough's diagnosis is the deck. The sled is a pale slab across the front, wider
# than the casks and at the height where a barrel is widest, so it cuts both casks off
# at their belly and the piece reads bottom-heavy and boxy. Every candidate here puts
# the casks on the ground.

# Copper, tin and iron ore are what the runtime skins this group with, and not one of
# them is timber-coloured. The inherited 0.34, 0.24, 0.16 is within a hair of `wood`,
# which meant the ore side of the trough has never been legible in a preview whatever
# the model did - the heap and the cask it sits in were the same value.
TINTS["ore"] = (0.31, 0.29, 0.25, 1.0)


def round_log(radius, length, location, axis="y", rot=0.0):
    """
    One round of firewood: bark on, sawn both ends, seven sides.

    This is billet() with the lottery taken out. The variety that survives is the
    variety a real stack has - diameter, taper, and which facet happens to face you -
    and the variety that goes is the part that was doing the damage: a stack whose
    pieces are three-sided, four-sided and seven-sided reads as broken rock, because
    a triangular end is not a shape wood is ever cut into.
    """
    r = radius * (0.90 + rnd() * 0.20)
    taper = 0.82 + rnd() * 0.14
    if rnd() < 0.5:
        r, taper = r * taper, 1.0 / taper
    return log(r, length * (0.97 + rnd() * 0.06), location, "wood", axis=axis, sides=7,
               rot=rot + jitter(5.0), wobble=0.5, taper=taper, roll=rnd() * 360.0)


def cask(x, radius, top, turn, fill, stave=0.115, hoops=3):
    """
    An open cask standing on the ground, hooped and full to just under the rim.

    Lifted from trough_barrels unchanged except for where it stands - the cask itself
    was never the problem. Hoop placement is a fraction of height rather than a fixed
    figure so a short tub and a tall barrel both get their top hoop under the rim.
    """
    staves = ring_count(radius, stave)
    for i in range(staves):
        a = (i / float(staves)) * math.tau + math.radians(turn)
        box((stave, stave, top * 0.99),
            (x + math.cos(a) * radius, math.sin(a) * radius, top * 0.5),
            "wood", rot=(0.0, 0.0, math.degrees(a)), wobble=0.5)

    outer = radius + stave / 2.0
    heights = ((0.12, 0.55, 0.93) if hoops == 3 else (0.16, 0.90))
    for f in heights:
        band(outer + (0.022 if f < 0.9 else -0.010), 0.075, top * f,
             sides=11, centre=(x, 0.0))

    contents((x, 0.0, top * 0.94), radius - stave * 0.25, fill,
             rise=0.15 * max(0.8, radius / 0.29))


def stack(rows, per_row, radius, length, spread, base_z, pitch, y=0.0):
    """
    Courses of rounds, ends to the front.

    Alternating counts and a half-shift are what make it read as stacked rather than
    poured: a course of four beds into the hollows of the course of three below it,
    which is what firewood actually does and what the old scatter never showed.
    """
    for row in range(rows):
        count = per_row if row % 2 == 0 else per_row + 1
        z = base_z + row * pitch
        for i in range(count):
            f = 0.0 if count == 1 else i / float(count - 1) - 0.5
            round_log(radius, length, (f * spread, y + (row % 2) * 0.035 - 0.018, z))


# ------------------------------------------------------------------------ the racks

def rack_courses():
    """
    The lean-to, with the rubble replaced by firewood and the back closed.

    Three changes, and the third is the one that is easy to miss. Rounds instead of the
    cross-section lottery; a roof with a slope you can see from standing height and a
    fascia thick enough to cast a line; and a back board, because the staged render
    shows daylight and grey smelter straight through the middle of the stack. A pile
    you can see through is not a pile - it is a rack with some wood leaning in it.
    """
    for x in (-0.58, 0.58):
        box((0.16, 0.22, 1.10), (x, 0.0, 0.55), "wood")
        # Buried deep on purpose - vanilla's own woodpiles sit 58cm into the ground,
        # because terrain is never flat and a 2m footprint always has a corner over a dip.
        box((0.20, 0.26, 0.56), (x, 0.0, -0.16), "wood")

    box((1.24, 0.07, 0.96), (0.0, 0.30, 0.54), "wood")            # back board
    box((1.28, 0.70, 0.13), (0.0, 0.0, 0.07), "wood")             # sill

    stack(4, 3, 0.125, 0.58, 0.62, 0.27, 0.215, y=-0.02)

    # The slope sign was wrong, and had been since the first lean-to. A rotation of -17
    # about x lifts the *front* edge, so the roof rose towards the viewer - which is why
    # it read as a table with a raised lip rather than as a roof, and why nothing done to
    # its thickness ever helped. A lean-to sheds forwards; +17 is that.
    #
    # The fascia also has to clear the stack. At y -0.44 against a stack front face at
    # -0.31 it stood in front of the top course and hid it, so the rack looked half
    # empty and the roof looked like a second shelf.
    box((1.48, 0.90, 0.10), (0.0, -0.04, 1.14), "wood", rot=(17.0, 0.0, 0.0))
    box((1.52, 0.14, 0.17), (0.0, -0.46, 1.00), "wood", rot=(17.0, 0.0, 0.0))
    collide((0.0, 0.0, 0.62), (1.34, 0.82, 1.24))


def rack_open():
    """
    No roof at all: four stakes, a rail, and a stack standing proud above it.

    The roof is the part of the lean-to that has never worked - it is a flat plate
    seen edge-on from every angle you play at, and it is also the reason the piece is
    2.6m tall next to a kiln. Vanilla's woodpiles have no roof either. Wider and lower
    than the others, so this is the one that reads as something laid down beside the
    kiln rather than built over it.
    """
    for x in (-0.76, 0.76):
        for y in (-0.26, 0.26):
            box((0.12, 0.14, 0.92), (x, y, 0.44), "wood")
        box((0.15, 0.20, 0.50), (x, 0.0, -0.14), "wood")          # sole plate

    box((1.66, 0.72, 0.13), (0.0, 0.0, 0.07), "wood")             # sill
    box((1.58, 0.07, 0.84), (0.0, 0.30, 0.46), "wood")            # back board

    stack(3, 5, 0.135, 0.60, 1.16, 0.29, 0.235)

    # Back rail only. With one at the front as well the four stakes and two rails closed
    # a rectangle around the stack and the whole thing read as a crate someone had filled
    # - the ends of the wood were behind a frame instead of being the front of the piece.
    box((1.62, 0.09, 0.10), (0.0, 0.26, 0.86), "wood")
    collide((0.0, 0.0, 0.48), (1.70, 0.72, 0.96))


def rack_gable():
    """
    A gable roof on four posts - the one candidate with a silhouette a smelter yard
    does not already have.

    A ridge reads at any distance and from any angle, where a single slope reads from
    one. It costs height, which is the argument against it: this is the tallest of the
    three and a charcoal kiln is not a tall station.
    """
    for x in (-0.56, 0.56):
        for y in (-0.28, 0.28):
            box((0.14, 0.14, 1.02), (x, y, 0.51), "wood")
        box((0.18, 0.22, 0.52), (x, 0.0, -0.14), "wood")

    box((1.16, 0.07, 0.90), (0.0, 0.30, 0.50), "wood")            # back board
    box((1.22, 0.72, 0.13), (0.0, 0.0, 0.07), "wood")             # sill

    stack(4, 3, 0.120, 0.56, 0.58, 0.27, 0.205, y=-0.02)

    # Two slopes meeting on a ridge beam, and a gable end board at each side so the
    # triangle is closed. An open gable is a roof with a hole in it, and the hole is
    # the first thing the eye finds.
    # 36 degrees, not 28. At eye height you see a roof close to edge-on, so a shallow
    # pitch is a flat plate with a crease in it - the whole reason to pay for a ridge is
    # that it breaks the outline, and it only does that if the slopes are steep enough
    # to be seen as two surfaces.
    for sign in (-1.0, 1.0):
        box((1.36, 0.60, 0.09), (0.0, sign * 0.21, 1.15), "wood",
            rot=(-36.0 * sign, 0.0, 0.0))
    box((1.40, 0.12, 0.12), (0.0, 0.0, 1.33), "wood")             # ridge
    for x in (-0.60, 0.60):
        box((0.09, 0.56, 0.34), (x, 0.0, 1.13), "wood")           # gable end
    collide((0.0, 0.0, 0.66), (1.28, 0.76, 1.32))


# ----------------------------------------------------------------------- the troughs

def trough_grounded():
    """
    The twin casks with the sled taken out from under them.

    Nothing about the casks changes. The deck goes, the runners drop to a kerb the
    casks stand between, and the two are pulled further apart in size - 0.30 against
    0.23 in radius rather than 0.285 against 0.265, which is the difference between
    two casks and the same cask twice.
    """
    cask(-0.34, 0.300, 0.90, 0.0, "ore")
    cask(0.44, 0.230, 0.66, 24.0, "coal")

    # A kerb rather than a deck: four low timbers *outside* the casks, buried to their
    # tops, so the piece is bedded into the ground instead of standing on a pallet. The
    # first attempt sat them at y +-0.36 against a 0.30 cask, which put the front timber
    # under the belly of both and read as exactly the deck it was replacing.
    for y in (-0.44, 0.44):
        box((1.52, 0.14, 0.40), (0.02, y, -0.13), "wood")
    for x in (-0.80, 0.86):
        box((0.14, 0.90, 0.38), (x, 0.0, -0.14), "wood")
    collide((0.02, 0.0, 0.46), (1.80, 0.96, 0.92))


def trough_framed():
    """
    The same two casks held in a timber frame with a top rail.

    A cask is a cylinder, and two cylinders side by side have no outline of their own -
    which is most of why the shipped piece reads as "some barrels" rather than as one
    object. The frame is what makes it a thing: a rectangle around a pair of rounds,
    the way a bottle rack is not a bottle.
    """
    cask(-0.34, 0.300, 0.88, 0.0, "ore")
    cask(0.44, 0.230, 0.66, 24.0, "coal")

    for x in (-0.74, 0.82):
        for y in (-0.40, 0.40):
            box((0.12, 0.12, 1.02), (x, y, 0.48), "wood")
        box((0.16, 0.22, 0.52), (x, 0.0, -0.14), "wood")

    # Top rails all round, and a low rail at the back only. The front one used to run
    # across at 0.30 - straight through the belly of both casks - which cut each one in
    # two and left four objects where there are two.
    for y in (-0.40, 0.40):
        box((1.72, 0.10, 0.11), (0.04, y, 0.95), "wood")
    box((1.72, 0.09, 0.09), (0.04, 0.40, 0.22), "wood")
    for x in (-0.74, 0.82):
        box((0.09, 0.84, 0.09), (x, 0.0, 0.95), "wood")
    collide((0.04, 0.0, 0.50), (1.84, 0.92, 1.00))


def trough_tub():
    """
    A tall cask of ore beside a low wide tub of coal.

    The asymmetry is the whole idea. Two barrels of similar size is a pair, and a pair
    reads as a set piece someone dropped in; a barrel and a tub reads as a working
    arrangement, and it gives the piece a stepped outline that neither of the others
    has. It is also the only candidate where you can see into both containers from
    standing height, which is what makes the ore side and the coal side legible at all.
    """
    cask(-0.36, 0.285, 1.00, 0.0, "ore")
    cask(0.48, 0.360, 0.42, 18.0, "coal", stave=0.125, hoops=2)

    # One back board and one sole plate under both, not one under each. Two separate
    # plates read as two pieces of furniture that happen to be adjacent - the shared
    # base is the only thing making a barrel and a tub into a single object.
    box((1.76, 0.11, 0.60), (0.06, 0.42, 0.30), "wood")
    box((1.84, 0.92, 0.38), (0.06, 0.0, -0.14), "wood")
    collide((0.06, 0.0, 0.52), (1.86, 0.94, 1.04))


CANDIDATES = [
    ("stoker_rack_courses",    rack_courses,    "WOODRACK - Lean-to, coursed"),
    ("stoker_rack_open",       rack_open,       "WOODRACK - Open stack, no roof"),
    ("stoker_rack_gable",      rack_gable,      "WOODRACK - Gable shed"),
    ("stoker_trough_grounded", trough_grounded, "TROUGH - Casks on a kerb"),
    ("stoker_trough_framed",   trough_framed,   "TROUGH - Casks in a frame"),
    ("stoker_trough_tub",      trough_tub,      "TROUGH - Cask and tub"),
]


# ------------------------------------------------------------------- the cask itself
#
# The arrangement is settled - two casks on a kerb, no frame - and the cask is what
# reads as modded. Three reasons, and none of them is the arrangement:
#
# It is not a cask shape. A real one bulges at the belly; ours is a straight tube, and
# the note in trough_barrels says so explicitly - the bulge was dropped on the grounds
# that at 28 texels/m it is under a pixel of shading. That was about *shading*, and the
# thing it costs is *silhouette*, which is not under a pixel of anything. A straight
# hooped cylinder is a bucket, or a planter.
#
# The staves are modelled as square posts. Twenty 11.5cm boxes round a 30cm radius give
# a corrugated outline no vanilla barrel has - piece_chest_barrel is a turned cylinder
# with the staves painted on, which is the same trade as end grain: vanilla paints the
# detail it does not model, and modelling it is most of what makes a prop look fan-made.
#
# It is oversized. Vanilla's barrell measures 0.84 across and 1.10 tall. Ours is 0.90 x
# 1.35 in the world, so it stands a head above the thing it is imitating - and something
# that is nearly a familiar object but bigger is exactly the uncanny note being reported.
# The figures below are vanilla's, worked back through Scale 1.5: radius 0.28 modelled
# is 0.84 across in the world, height 0.74 is 1.11 tall.

ORE, COAL = (-0.31, 0.280, 0.74), (0.37, 0.225, 0.56)


def hoops(x, radii, thickness=0.042):
    """
    Thin, and barely proud of the wood.

    The shipped hoop is 7.5cm tall standing 2.2cm off an 11-sided ring against a body
    of a different side count, and at arm's length it is a grey donut rather than a
    band of iron - it was the loudest thing on the piece. Same side count as the body,
    so the facets line up instead of the hoop's vertices poking through the staves.
    """
    for z, r in radii:
        band(r + 0.008, thickness, z, sides=15, centre=(x, 0.0))


def cask_smooth(x, radius, top, fill):
    """
    A turned barrel: bulged body, no modelled staves, three thin hoops.

    This is how vanilla builds one, and it is also cheaper - two cones of fifteen sides
    against twenty beveled boxes. The stave lines come from the donor's texture, which
    is the whole reason we skin off piece_chest_barrel in the first place.
    """
    waist = radius * 0.87
    cone(waist, radius, top * 0.52, top * 0.26, "wood", sides=15, centre=(x, 0.0))
    cone(radius, radius * 0.93, top * 0.50, top * 0.75, "wood", sides=15, centre=(x, 0.0))
    hoops(x, ((top * 0.10, waist * 1.04), (top * 0.50, radius),
              (top * 0.95, radius * 0.94)))
    # Twelve small lumps rather than six large ones. At 7.2cm on a 24cm mouth each lump
    # was nearly a third of the opening, so it presented a flat top the size of a paving
    # slab and every ore donor read as slate however it was textured. The coal has always
    # read correctly off the same geometry purely because it is near-black and the facets
    # disappear into the mass - so this is the change that lets a mid-value ore work at all.
    contents((x, 0.0, top * 0.93), radius * 0.86, fill, rise=0.13,
             count=12, lump=0.045)


def cask_staved(x, radius, top, fill, stave=0.10):
    """
    Modelled staves kept, but coopered rather than extruded: two courses, the lower
    leaning out and the upper leaning in, so the barrel is widest at its belly.

    Six degrees each way is enough - a barrel bulges by about a tenth of its girth, not
    by a third. The tilt is about local Y after the spin, which lands radially.
    """
    staves = ring_count(radius * 0.94, stave)
    for i in range(staves):
        a = (i / float(staves)) * math.tau
        cx, cy = x + math.cos(a) * radius * 0.94, math.sin(a) * radius * 0.94
        d = math.degrees(a)
        box((stave, stave, top * 0.58), (cx, cy, top * 0.27), "wood",
            rot=(0.0, -6.0, d), wobble=0.4)
        box((stave, stave, top * 0.58), (cx, cy, top * 0.73), "wood",
            rot=(0.0, 6.0, d), wobble=0.4)
    hoops(x, ((top * 0.10, radius * 0.93), (top * 0.50, radius * 1.02),
              (top * 0.95, radius * 0.94)))
    # Twelve small lumps rather than six large ones. At 7.2cm on a 24cm mouth each lump
    # was nearly a third of the opening, so it presented a flat top the size of a paving
    # slab and every ore donor read as slate however it was textured. The coal has always
    # read correctly off the same geometry purely because it is near-black and the facets
    # disappear into the mass - so this is the change that lets a mid-value ore work at all.
    contents((x, 0.0, top * 0.93), radius * 0.86, fill, rise=0.13,
             count=12, lump=0.045)


def cask_cut(x, radius, top, fill):
    """
    A barrel sawn off just above its belly, so the mouth is the widest part of it.

    The one treatment that explains itself. Every other version is a cask that happens
    to have no lid, and an open barrel full of ore is not a thing a cooper makes - it is
    a thing somebody did to a barrel. Cutting it at the belly is what you would actually
    do, it puts the widest hoop at the rim holding the staves in, and it gives the pair a
    squatter outline that is further from vanilla's closed barrel rather than nearer it.
    """
    body = top * 1.28                      # the height it would have been before the cut
    waist = radius * 0.87
    cone(waist, radius, body * 0.46, body * 0.23, "wood", sides=15, centre=(x, 0.0))
    cone(radius, radius * 0.99, body * 0.14, body * 0.53, "wood", sides=15,
         centre=(x, 0.0))
    hoops(x, ((body * 0.09, waist * 1.04), (body * 0.34, radius * 0.97)))
    hoops(x, ((body * 0.57, radius * 1.00),), thickness=0.058)   # the rim hoop
    contents((x, 0.0, body * 0.57), radius * 0.92, fill, rise=0.12,
             count=6, lump=0.072)


def cask_tub(x, radius, top, fill):
    """
    Not a barrel at all: a coopered tub, straight-tapered wider at the top.

    Worth seeing because it sidesteps the comparison entirely. Nothing about it invites
    you to measure it against vanilla's barrell, so it cannot look like a slightly wrong
    one. The risk is the opposite failure - a tapered tub with two hoops is close to a
    flowerpot, and there is no Viking read to fall back on.
    """
    cone(radius * 0.78, radius * 1.06, top, top * 0.5, "wood", sides=15, centre=(x, 0.0))
    hoops(x, ((top * 0.12, radius * 0.84), (top * 0.90, radius * 1.04)))
    contents((x, 0.0, top * 0.90), radius * 0.96, fill, rise=0.13,
             count=6, lump=0.072)


def kerb(half=0.70, length=1.30):
    """
    The base from trough_grounded, drawn in to the casks it holds.

    It was sized before the casks were cut to vanilla's figures, so it went on standing
    2.7m wide around a pair that now spans 1.27 - nearly a metre of empty kerb, which is
    what turns a bed into a platform. Buried to its top either way: terrain is never
    flat and the alternative is a corner in the air.
    """
    for y in (-0.42, 0.42):
        box((length, 0.14, 0.40), (0.02, y, -0.13), "wood")
    for x in (-half, half):
        box((0.14, 0.86, 0.38), (x, 0.0, -0.14), "wood")
    collide((0.0, 0.0, 0.42), (2.0 * half + 0.16, 0.92, 0.84))


def pair(shape):
    def build():
        shape(ORE[0], ORE[1], ORE[2], "ore")
        shape(COAL[0], COAL[1], COAL[2], "coal")
        kerb()
    return build


CASKS = [
    ("stoker_cask_smooth", pair(cask_smooth), "CASK - Turned, bulged, painted staves"),
    ("stoker_cask_staved", pair(cask_staved), "CASK - Coopered staves, two courses"),
    ("stoker_cask_cut",    pair(cask_cut),    "CASK - Barrel sawn off at the belly"),
    ("stoker_cask_tub",    pair(cask_tub),    "CASK - Tapered tub"),
]


# ------------------------------------------------------------------------- the picks
#
# Chosen on 2026-08-17: the coursed lean-to for the kiln, and a pair of turned casks for
# the smelter. These two write to assets/ rather than assets/variants/, which is the
# only difference between a candidate and a model that ships.
#
# The .obj filename is not the prefab name and carries no ZDO risk - the prefab keeps
# calling itself Trough and Woodrack, and only the Model config entry moves. The old
# shapes go to the shelf rather than being deleted, the same as every other rejected one.


def trough_casks():
    """
    Two turned casks, ore and coal, standing on the ground and nothing else.

    The kerb is gone. It was there to tie the pair into one object and to bed them into
    the terrain, and it did neither well enough to earn a third of the piece's footprint:
    four low timbers round a pair of barrels read as the pallet the deck had just been
    taken away for being. Two casks standing together are legible as two casks standing
    together, which is all this needs to be.
    """
    cask_smooth(ORE[0], ORE[1], ORE[2], "ore")
    cask_smooth(COAL[0], COAL[1], COAL[2], "coal")

    # A collider each, now that the kerb is not supplying one. Axis-aligned boxes round
    # a cylinder is what the .col format offers and it is close enough - the corners
    # stand about 4cm proud of a 42cm radius, which nobody walks into and notices.
    for x, radius, top in (ORE, COAL):
        collide((x, 0.0, top * 0.5), (radius * 2.0, radius * 2.0, top))


PICKS = [
    ("stoker_rack_courses", rack_courses,  "WOODRACK - Lean-to, coursed"),
    ("stoker_trough_casks", trough_casks,  "TROUGH - Turned casks"),
]


# --------------------------------------------------------------------------- export

def main(items, close=False, promote=False):
    os.makedirs(PREVIEWS, exist_ok=True)
    os.makedirs(SHELF, exist_ok=True)

    for name, builder, label in items:
        clear_scene()
        builder()
        obj = finish(name)
        tris = len(obj.data.polygons)
        size = scale_for(name)

        # The shelf unless promoted. The baseline pair is re-rendered rather than
        # re-exported: rewriting a shipped .obj from a script whose whole job is to
        # change it is how a rejected shape gets into the build menu.
        #
        # And never on the close pass. That is the same model shot from a second camera,
        # and exporting it again wrote a promoted piece to the shelf as well as to
        # assets - two copies of one model, one of them in the folder that means rejected.
        if name not in [b[0] for b in BASELINE] and not close:
            dest = ASSETS if promote else SHELF
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.wm.obj_export(filepath=os.path.join(dest, name + ".obj"),
                                  export_selected_objects=True, export_materials=True,
                                  forward_axis="Z", up_axis="Y")
            write_col(os.path.join(dest, name + ".col"))

        # The icon here is only the fallback. IconRender photographs the finished prefab
        # in game, where the borrowed vanilla materials actually exist, and this is what
        # it falls back to if that fails - without one the piece wears the donor's icon,
        # which is a picture of a barrel. So it has to exist and does not have to be good.
        if promote:
            tint()
            centre, extent = bounds(obj)
            icon_scene(centre, extent)
            render(os.path.join(ASSETS, name + "_icon.png"), (128, 128))

            clear_scene()
            builder()
            obj = finish(name)

        tint()
        tint_stage()
        staged_scene(size, close=close)
        render(os.path.join(PREVIEWS, name + ("_close" if close else "_staged") + ".png"),
               (760, 620))

        # dimensions is read after staged_scene has applied the runtime scale, so these
        # are already the metres the game draws - multiplying by size again double-counts.
        # Said out loud every run rather than checked once. These get placed in rows -
        # eight upgraded smelters is sixteen copies in view - so the count is multiplied
        # by the base rather than paid once, and a model creeps over one detail at a time.
        flag = "  OVER BUDGET" if promote and tris > 3500 else ""
        print("STAGED %-26s tris=%-6d  %.2f x %.2f x %.2fm in game (scale %.1f)  %s%s"
              % (name, tris, obj.dimensions[0], obj.dimensions[1], obj.dimensions[2],
                 size, label, flag))

    print("REMODEL_DONE")


# The two that ship, re-rendered through the corrected rig before anything is changed.
# A baseline taken with the same lights and the same scale as the candidates is the
# only way a comparison means anything.
BASELINE = [
    ("stoker_rack_lean", rack_lean, "SHIPPED - Woodrack, lean-to"),
    ("stoker_trough_barrels", trough_barrels, "SHIPPED - Trough, twin casks"),
]


if __name__ == "__main__":
    # Which round to shoot. Edited rather than made a flag, because `blender --background
    # --python` swallows anything after the script name and passing it through argv means
    # a `--` separator nobody remembers.
    main(PICKS, promote=True)
    main(PICKS, close=True)
