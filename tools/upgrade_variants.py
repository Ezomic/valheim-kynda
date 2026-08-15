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
    modifier = obj.modifiers.new(name="bevel", type="BEVEL")
    modifier.width = bevel
    modifier.segments = 2
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


# --------------------------------------------------------------------------- export

VARIANTS = [
    ("stoker_rack_lean",      rack_lean,      "WOODRACK - Lean-to"),
    ("stoker_rack_crib",      rack_crib,      "WOODRACK - Log crib"),
    ("stoker_rack_barrow",    rack_barrow,    "WOODRACK - Barrow"),
    ("stoker_trough_bench",   trough_bench,   "TROUGH - Bench"),
    ("stoker_trough_hod",     trough_hod,     "TROUGH - Stone hod"),
    ("stoker_trough_scuttle", trough_scuttle, "TROUGH - Scuttle"),
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

        print("VARIANT_OK %-24s tris=%-6d colliders=%d  %s" % (name, tris, boxes, label))

    print("VARIANTS_DONE")


main()
