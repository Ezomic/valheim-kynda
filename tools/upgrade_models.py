"""
Candidate models for the two station upgrades, built and rendered for comparison.

Two pieces, not one. A charcoal kiln eats wood and a smelter eats ore, so a single
generic bin was always going to look like it belonged to neither - which is what the
first hopper looked like. Each candidate below is shaped by what its station is fed.

    blender --background --python tools/upgrade_models.py

Writes assets/<name>.obj + .col and assets/previews/<name>.png for every variant.
Materials are group names only; the runtime skins each group with a real vanilla
material lifted off a game prefab.
"""

import bpy
import bmesh
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
PREVIEWS = os.path.join(ASSETS, "previews")

COLLIDERS = []

TINTS = {
    "wood": (0.30, 0.19, 0.10, 1.0),
    "iron": (0.19, 0.19, 0.21, 1.0),
    "stone": (0.42, 0.41, 0.38, 1.0),
    "coal": (0.06, 0.06, 0.07, 1.0),
    "ore": (0.34, 0.24, 0.16, 1.0),
}


# --------------------------------------------------------------------------- helpers

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.objects, bpy.data.lights,
                  bpy.data.cameras):
        for item in list(block):
            if item.users == 0:
                block.remove(item)
    del COLLIDERS[:]


def material(name):
    mat = bpy.data.materials.get(name)
    return mat if mat else bpy.data.materials.new(name)


def collide(centre, size):
    COLLIDERS.append((centre, size))


def box(size, location, mat, rot_x=0.0, rot_y=0.0, rot_z=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    # scale, not scale/2. primitive_cube_add(size=1.0) already makes a unit cube
    # spanning -0.5..0.5, so halving again produced every box at half its stated
    # size - while cones and cylinders, which take a radius, came out correct. Mixing
    # the two is why banding sat inside the bin, corner straps floated clear of the
    # crate they were meant to bind, and a footing swallowed a chute: every
    # box-against-cone relationship in the file was wrong by a factor of two.
    obj.scale = (size[0], size[1], size[2])
    obj.rotation_euler = (math.radians(rot_x), math.radians(rot_y), math.radians(rot_z))
    obj.data.materials.append(material(mat))
    return obj


def cyl(radius, length, location, mat, axis="z", sides=8, rot_z=0.0):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=length, vertices=sides,
                                        location=location)
    obj = bpy.context.active_object
    rot = [0.0, 0.0, math.radians(rot_z)]
    if axis == "x":
        rot[1] = math.radians(90)
    elif axis == "y":
        rot[0] = math.radians(90)
    obj.rotation_euler = rot
    obj.data.materials.append(material(mat))
    return obj


def frustum(bottom, top, height, z, mat, sides=4, rot_z=45.0):
    bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=bottom, radius2=top,
                                    depth=height, location=(0.0, 0.0, z),
                                    rotation=(0.0, 0.0, math.radians(rot_z)))
    obj = bpy.context.active_object
    obj.data.materials.append(material(mat))
    return obj


def heap(centre, spread, count, size, mat, seed=1):
    """
    A pile of lumps - ore or coal - mounded in an opening.

    Fewer and bigger than the first attempt, and domed rather than scattered at a
    constant height. Small lumps spread flat across a rim do not read as a pile from
    three metres away, they read as confetti sitting on top of the model; the give-away
    is that each one has clear air around it. Lumps here overlap their neighbours and
    sit lower towards the edges, so the silhouette is a single mound.
    """
    state = seed
    for i in range(count):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        fx = (state % 1000) / 1000.0 - 0.5
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        fy = (state % 1000) / 1000.0 - 0.5
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        wobble = (state % 1000) / 1000.0
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        yaw = (state % 90)

        # Domed: the further from the middle, the lower it sits.
        radial = min(1.0, (fx * fx + fy * fy) ** 0.5 * 2.0)
        s = size * (0.85 + wobble * 0.45)
        box((s, s, s * 0.7),
            (centre[0] + fx * spread,
             centre[1] + fy * spread,
             centre[2] - radial * size * 0.55 + wobble * size * 0.12),
            mat, rot_z=yaw, rot_x=yaw * 0.15)


def blob(size, location, mat, rot_z=0.0, squash=0.78):
    """A soft lump - a filled sack, where every other part here is a hard edge."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.5, location=location)
    obj = bpy.context.active_object
    obj.scale = (size[0], size[1], size[2] * squash)
    obj.rotation_euler = (0.0, 0.0, math.radians(rot_z))
    obj.data.materials.append(material(mat))
    return obj


# --------------------------------------------------------------------------- kiln A

def kiln_woodrack():
    """
    Split logs racked between two posts, under a plank hood.

    A kiln is fed wood, so the upgrade beside it is a woodpile. The stacked round
    ends read instantly at any distance, which a smooth bin never does.

    Called a rack rather than a rick: a rick is a free-standing stack with no frame,
    and this is held between posts. The word is also dated enough that it needed
    explaining, which is disqualifying for something you read off a hammer menu.
    """
    for x in (-0.46, 0.46):
        box((0.10, 0.12, 1.05), (x, 0.0, 0.525), "wood")
        box((0.10, 0.72, 0.09), (x, 0.0, 1.02), "wood")
    collide((0.0, 0.0, 0.52), (1.02, 0.72, 1.05))

    # Logs, stacked in courses with the ends facing out.
    for row, z in enumerate((0.20, 0.40, 0.60, 0.78)):
        count = 4 if row % 2 == 0 else 3
        span = 0.62
        for i in range(count):
            x = -span / 2.0 + span * (i / float(max(1, count - 1)))
            cyl(0.095, 0.66, (x, 0.0, z), "wood", axis="y", sides=8)

    # Plank hood, resting on the posts rather than hovering above them: it was at
    # 1.14 with the posts topping out at 1.05, and a 5cm gap reads as a floating board.
    box((1.16, 0.90, 0.07), (0.0, 0.0, 1.07), "wood", rot_x=6.0)
    box((0.09, 0.86, 0.05), (0.0, 0.0, 1.12), "iron", rot_x=6.0)

    box((1.06, 0.78, 0.10), (0.0, 0.0, 0.05), "stone")
    collide((0.0, 0.0, 0.05), (1.06, 0.78, 0.10))


# --------------------------------------------------------------------------- kiln B

def kiln_charbin():
    """
    A squat stone bin with an iron lid ajar and charcoal heaped at the mouth.

    Where the rick says "wood goes in", this says "charcoal comes out". Lower and
    wider than the smelter piece on purpose, so the two never read as a matched pair
    of the same object.
    """
    frustum(0.52, 0.46, 0.62, 0.44, "stone", sides=8, rot_z=22.5)
    collide((0.0, 0.0, 0.44), (1.00, 1.00, 0.62))

    # Iron hoops, top and bottom.
    frustum(0.50, 0.50, 0.05, 0.20, "iron", sides=8, rot_z=22.5)
    frustum(0.475, 0.475, 0.05, 0.68, "iron", sides=8, rot_z=22.5)

    # Charcoal at the mouth.
    heap((0.0, 0.0, 0.78), 0.46, 7, 0.18, "coal", seed=7)

    # Lid, tipped back off the rim so the bin reads as open.
    box((0.86, 0.86, 0.05), (0.0, -0.30, 0.94), "iron", rot_x=-52.0)
    box((0.10, 0.10, 0.14), (0.0, -0.46, 1.10), "iron")

    box((1.04, 1.04, 0.12), (0.0, 0.0, 0.06), "stone")
    collide((0.0, 0.0, 0.06), (1.04, 1.04, 0.12))


# --------------------------------------------------------------------------- smelter A

def smelter_orecrate():
    """
    An iron-bound crate, heaped with ore and standing on a low plinth.

    Square, hard-edged and heavy: it should look like it is holding something dense,
    which is the whole difference between this and a wood store.
    """
    box((0.86, 0.72, 0.68), (0.0, 0.0, 0.52), "wood")
    collide((0.0, 0.0, 0.52), (0.86, 0.72, 0.68))

    # Banding: two hoops and four corner straps.
    for z in (0.28, 0.74):
        box((0.90, 0.76, 0.07), (0.0, 0.0, z), "iron")
    for x in (-0.42, 0.42):
        for y in (-0.35, 0.35):
            box((0.07, 0.07, 0.70), (x, y, 0.52), "iron")

    # Ore heaped over the rim, spilling slightly.
    heap((0.0, 0.0, 0.90), 0.52, 7, 0.20, "ore", seed=3)

    # Plinth.
    box((1.00, 0.86, 0.16), (0.0, 0.0, 0.08), "stone")
    collide((0.0, 0.0, 0.08), (1.00, 0.86, 0.16))


# --------------------------------------------------------------------------- smelter B

def smelter_bunker():
    """
    A masonry bunker with a sloped face and an iron chute at the foot.

    Reads as part of the smelter's own structure rather than something set down next
    to it - stone first, iron second, no timber at all.
    """
    box((0.92, 0.62, 0.74), (0.0, -0.06, 0.49), "stone")
    collide((0.0, -0.06, 0.49), (0.92, 0.62, 0.74))

    # Sloped front face, so it sheds rather than stacks.
    box((0.92, 0.46, 0.10), (0.0, 0.26, 0.72), "stone", rot_x=34.0)

    # One iron chute at the foot. There were two plates plus six corner quoins here,
    # and at eye height that many small parts stops reading as masonry and starts
    # reading as rubble piled against a box.
    box((0.36, 0.46, 0.11), (0.0, 0.34, 0.24), "iron", rot_x=24.0)
    collide((0.0, 0.30, 0.26), (0.36, 0.24, 0.44))

    # Two courses only, marking the stone as laid rather than poured.
    for z in (0.30, 0.62):
        box((0.96, 0.66, 0.05), (0.0, -0.06, z), "stone")

    # Ore mounded in the open top.
    heap((0.0, -0.10, 0.88), 0.50, 7, 0.19, "ore", seed=11)

    box((1.06, 0.78, 0.12), (0.0, -0.06, 0.06), "stone")
    collide((0.0, -0.06, 0.06), (1.06, 0.78, 0.12))


# --------------------------------------------------------------------------- smelter C

def smelter_charbin():
    """
    One bin, split down the middle: coal on the left, ore on the right.

    A smelter is the only station here that needs two different things at once, and a
    single undivided heap hides that. The divider makes the piece say what the station
    wants - which is the same reason the kiln gets a rack of logs rather than a bin.

    Wider than it is deep, so it reads as a long trough beside the smelter rather than
    competing with it for height.
    """
    # Trough body.
    box((1.18, 0.62, 0.52), (0.0, 0.0, 0.42), "wood")
    collide((0.0, 0.0, 0.42), (1.18, 0.62, 0.52))

    # Iron rails along the top edges and a divider across the middle.
    for y in (-0.30, 0.30):
        box((1.24, 0.08, 0.09), (0.0, y, 0.69), "iron")
    box((0.07, 0.66, 0.62), (0.0, 0.0, 0.47), "iron")

    # Corner straps, now that they land on the body rather than beside it.
    for x in (-0.57, 0.57):
        box((0.07, 0.66, 0.56), (x, 0.0, 0.44), "iron")

    # Coal to the left, ore to the right. Two materials, one silhouette.
    heap((-0.30, 0.0, 0.70), 0.44, 6, 0.17, "coal", seed=5)
    heap((0.30, 0.0, 0.70), 0.44, 6, 0.17, "ore", seed=9)

    # Stone plinth.
    box((1.32, 0.76, 0.16), (0.0, 0.0, 0.08), "stone")
    collide((0.0, 0.0, 0.08), (1.32, 0.76, 0.16))


# --------------------------------------------------------------------------- smelter D

def smelter_orecart():
    """
    A tipper wagon, parked and tilted towards whatever it feeds.

    The three bins before this were all the same object with different cladding - a
    box with material heaped on top - so none of them looked like a choice. Wheels
    change the silhouette completely: nothing else in a Valheim base has them, and a
    cart reads as "this was hauled here" rather than "this was built here".
    """
    # Rails it sits on, half sunk in the ground.
    for x in (-0.30, 0.30):
        box((0.08, 1.10, 0.06), (x, 0.0, 0.05), "iron")
    for y in (-0.42, 0.0, 0.42):
        box((0.86, 0.09, 0.05), (0.0, y, 0.02), "wood")

    # Wheels.
    for x in (-0.34, 0.34):
        for y in (-0.30, 0.30):
            cyl(0.16, 0.07, (x, y, 0.18), "iron", axis="x", sides=10)
    box((0.74, 0.07, 0.07), (0.0, -0.30, 0.18), "iron")
    box((0.74, 0.07, 0.07), (0.0, 0.30, 0.18), "iron")

    # Body: tipped forward, so it is pouring rather than parked.
    box((0.70, 0.86, 0.44), (0.0, 0.02, 0.50), "wood", rot_x=-14.0)
    for z, y in ((0.36, 0.02), (0.64, -0.05)):
        box((0.76, 0.90, 0.06), (0.0, y, z), "iron", rot_x=-14.0)
    collide((0.0, 0.0, 0.42), (0.80, 1.00, 0.80))

    # Ore riding in it, spilling towards the low end.
    heap((0.0, 0.20, 0.66), 0.46, 7, 0.17, "ore", seed=13)
    heap((0.0, -0.22, 0.74), 0.34, 4, 0.15, "coal", seed=21)


# --------------------------------------------------------------------------- smelter E

def smelter_sacks():
    """
    Stacked sacks on a pallet, roped down.

    Every candidate so far has been made of flat planes. Sacks are the one shape in a
    viking base that sags, and that softness is what stops this reading as another
    crate - you can tell what it is from the silhouette alone, with no contents to see.
    """
    box((1.06, 0.78, 0.10), (0.0, 0.0, 0.05), "wood")
    for y in (-0.26, 0.26):
        box((1.02, 0.10, 0.07), (0.0, y, 0.13), "wood")
    collide((0.0, 0.0, 0.05), (1.06, 0.78, 0.14))

    # Bottom course: three sacks, bulging.
    for i, x in enumerate((-0.32, 0.0, 0.32)):
        blob((0.36, 0.52, 0.40), (x, 0.0, 0.34), "coal" if i != 1 else "ore",
             rot_z=12 * i)

    # Top course: two, nestled in the dips.
    for i, x in enumerate((-0.17, 0.17)):
        blob((0.34, 0.48, 0.36), (x, -0.02, 0.66), "ore" if i == 0 else "coal",
             rot_z=-20 + 40 * i)

    # Rope over the top, holding the stack.
    for x in (-0.20, 0.20):
        box((0.04, 0.72, 0.04), (x, 0.0, 0.80), "iron")
    collide((0.0, 0.0, 0.48), (1.00, 0.66, 0.72))


# --------------------------------------------------------------------------- smelter F

def smelter_skip():
    """
    An iron skip hung from a timber gantry, tipped towards the furnace.

    Tall and open where the others were low and closed. A hanging load has a shape
    nothing else in a base has, and the gantry gives it a vertical line that a smelter
    - which is all horizontal mass - does not compete with.
    """
    # Gantry: two A-frames and a beam.
    for y in (-0.34, 0.34):
        box((0.09, 0.09, 1.10), (-0.40, y, 0.58), "wood", rot_y=9.0)
        box((0.09, 0.09, 1.10), (0.40, y, 0.58), "wood", rot_y=-9.0)
    box((1.06, 0.10, 0.10), (0.0, -0.34, 1.14), "wood")
    box((1.06, 0.10, 0.10), (0.0, 0.34, 1.14), "wood")
    box((0.10, 0.86, 0.10), (0.0, 0.0, 1.14), "wood")
    collide((0.0, 0.0, 0.58), (0.98, 0.86, 1.16))

    # Chain.
    for y in (-0.13, 0.13):
        box((0.04, 0.04, 0.30), (0.0, y, 0.98), "iron")

    # The skip itself, tipped.
    frustum(0.24, 0.36, 0.46, 0.62, "iron", sides=6, rot_z=0.0)
    box((0.62, 0.10, 0.07), (0.0, 0.0, 0.84), "iron")
    collide((0.0, 0.0, 0.62), (0.66, 0.66, 0.50))

    # Ore in the skip and a little spilled on the stone below.
    heap((0.0, 0.0, 0.82), 0.30, 5, 0.15, "ore", seed=17)
    heap((0.0, 0.30, 0.14), 0.34, 4, 0.13, "coal", seed=23)

    box((1.14, 0.94, 0.10), (0.0, 0.0, 0.05), "stone")
    collide((0.0, 0.0, 0.05), (1.14, 0.94, 0.10))


# --------------------------------------------------------------------------- export

VARIANTS = [
    ("kynda_kiln_woodrack", kiln_woodrack, "KILN - Woodrack"),
    ("kynda_smelter_orecart", smelter_orecart, "SMELTER - Ore cart"),
    ("kynda_smelter_sacks", smelter_sacks, "SMELTER - Sack stack"),
    ("kynda_smelter_skip", smelter_skip, "SMELTER - Hanging skip"),
]


def finish(name):
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
    bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = name

    bpy.context.view_layer.objects.active = obj
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


def stage_and_render(out_png):
    """Eye height, three metres, with a 1m cube for scale. Never a hero angle."""
    bpy.ops.mesh.primitive_plane_add(size=20.0, location=(0, 0, 0))
    ground = bpy.context.active_object
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.19, 0.21, 0.16, 1)
    ground.data.materials.append(gm)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(1.45, 0.1, 0.5))
    cube = bpy.context.active_object
    cm = bpy.data.materials.new("ref")
    cm.use_nodes = True
    cm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.52, 0.52, 0.56, 1)
    cube.data.materials.append(cm)

    bpy.ops.object.camera_add(location=(-1.75, 2.45, 1.7))
    cam = bpy.context.active_object
    cam.data.lens = 42
    target = bpy.data.objects.new("aim", None)
    bpy.context.collection.objects.link(target)
    target.location = (0.0, 0.0, 0.55)
    track = cam.constraints.new(type="TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    bpy.context.scene.camera = cam

    bpy.ops.object.light_add(type="SUN", location=(3, 4, 6))
    bpy.context.active_object.data.energy = 3.2
    bpy.context.active_object.rotation_euler = (math.radians(52), 0, math.radians(200))

    world = bpy.data.worlds.new("w")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.36, 0.43, 0.53, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.65

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 520
    scene.render.filepath = out_png
    bpy.ops.render.render(write_still=True)


def main():
    os.makedirs(ASSETS, exist_ok=True)
    os.makedirs(PREVIEWS, exist_ok=True)

    for name, build, label in VARIANTS:
        clear_scene()
        build()
        obj = finish(name)
        verts, tris = len(obj.data.vertices), len(obj.data.polygons)

        bpy.ops.wm.obj_export(
            filepath=os.path.join(ASSETS, name + ".obj"),
            export_selected_objects=False, export_materials=True,
            export_normals=True, export_uv=True, export_triangulated_mesh=True,
            forward_axis="Z", up_axis="Y", path_mode="AUTO")
        write_col(os.path.join(ASSETS, name + ".col"))

        tint()
        stage_and_render(os.path.join(PREVIEWS, name + ".png"))
        print("VARIANT_OK %s verts=%d tris=%d" % (name, verts, tris))


main()
