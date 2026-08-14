"""
Variations on the ore trough - the shape that survived the shortlist.

    blender --background --python tools/trough_variants.py

All four keep what made the trough work: low and long so it does not compete with
the smelter for height, open on top, and visibly divided so the two materials it
holds are both legible. What changes is what it is built from and how it stands,
which is where the character is.
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
    "wood": (0.31, 0.20, 0.11, 1.0),
    "iron": (0.19, 0.19, 0.21, 1.0),
    "stone": (0.44, 0.43, 0.40, 1.0),
    "coal": (0.07, 0.07, 0.08, 1.0),
    "ore": (0.37, 0.26, 0.16, 1.0),
}


# --------------------------------------------------------------------------- helpers

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.objects,
                  bpy.data.lights, bpy.data.cameras):
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
    obj.scale = (size[0], size[1], size[2])
    obj.rotation_euler = (math.radians(rot_x), math.radians(rot_y), math.radians(rot_z))
    obj.data.materials.append(material(mat))
    return obj


def frustum(bottom, top, height, z, mat, sides=4, rot_z=45.0, location=(0.0, 0.0)):
    bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=bottom, radius2=top,
                                    depth=height, location=(location[0], location[1], z),
                                    rotation=(0.0, 0.0, math.radians(rot_z)))
    obj = bpy.context.active_object
    obj.data.materials.append(material(mat))
    return obj


def mound(centre, radius, height, mat, sides=8):
    """One solid mass. Scattered lumps read as confetti resting on the model."""
    frustum(radius, radius * 0.26, height, centre[2] + height / 2.0, mat,
            sides=sides, rot_z=22.5, location=(centre[0], centre[1]))


def rim(half_x, half_y, z, width=0.08, height=0.10, mat="iron"):
    """Four boxes so the middle stays open - a capped cone would be a lid."""
    box((half_x * 2.0, width, height), (0.0, -half_y + width / 2.0, z), mat)
    box((half_x * 2.0, width, height), (0.0, half_y - width / 2.0, z), mat)
    box((width, half_y * 2.0 - width * 2.0, height), (-half_x + width / 2.0, 0.0, z), mat)
    box((width, half_y * 2.0 - width * 2.0, height), (half_x - width / 2.0, 0.0, z), mat)


# --------------------------------------------------------------------------- variants

def trough_stone():
    """The original: a masonry trough with an iron rim and divider."""
    box((1.36, 0.66, 0.14), (0.0, 0.0, 0.07), "stone")
    box((1.28, 0.58, 0.42), (0.0, 0.0, 0.33), "stone")
    collide((0.0, 0.0, 0.27), (1.36, 0.66, 0.54))

    mound((-0.31, 0.0, 0.50), 0.30, 0.22, "coal")
    mound((0.31, 0.0, 0.50), 0.30, 0.22, "ore")

    box((0.09, 0.60, 0.32), (0.0, 0.0, 0.46), "iron")
    rim(0.66, 0.33, 0.56, width=0.09, height=0.11)


def trough_timber():
    """
    Plank-built and iron-hooped: the same trough as a piece of carpentry.

    Warmer than the masonry version and closer to what a viking base is mostly made
    of, so it sits alongside a workbench as comfortably as a smelter.
    """
    box((1.30, 0.60, 0.44), (0.0, 0.0, 0.34), "wood")
    collide((0.0, 0.0, 0.34), (1.30, 0.60, 0.44))

    # Hoops around the body rather than a rim on top.
    for x in (-0.44, 0.0, 0.44):
        box((0.08, 0.66, 0.48), (x, 0.0, 0.34), "iron")

    mound((-0.32, 0.0, 0.52), 0.28, 0.20, "coal")
    mound((0.32, 0.0, 0.52), 0.28, 0.20, "ore")

    # Feet, so the timber is not sitting in the mud.
    for x in (-0.52, 0.52):
        box((0.14, 0.60, 0.14), (x, 0.0, 0.07), "wood")
    collide((0.0, 0.0, 0.07), (1.30, 0.60, 0.14))


def trough_raised():
    """
    Standing on stout legs, so you shovel out of it rather than bend into it.

    The only variant with air under it, which gives the silhouette a gap and stops it
    reading as another block on the ground.
    """
    for x in (-0.50, 0.50):
        for y in (-0.22, 0.22):
            box((0.12, 0.12, 0.44), (x, y, 0.22), "wood")
    for x in (-0.50, 0.50):
        box((0.14, 0.62, 0.10), (x, 0.0, 0.40), "wood")

    box((1.22, 0.56, 0.38), (0.0, 0.0, 0.63), "wood")
    collide((0.0, 0.0, 0.50), (1.24, 0.62, 0.82))

    mound((-0.30, 0.0, 0.80), 0.27, 0.19, "coal")
    mound((0.30, 0.0, 0.80), 0.27, 0.19, "ore")

    box((0.08, 0.58, 0.30), (0.0, 0.0, 0.76), "iron")
    rim(0.63, 0.30, 0.84, width=0.08, height=0.10)


def trough_long():
    """
    Longer, lower and three-bayed - a working bench rather than a box.

    Reads as infrastructure: something a smelter row was built around, rather than a
    single container set down beside one furnace.
    """
    box((1.76, 0.58, 0.12), (0.0, 0.0, 0.06), "stone")
    box((1.68, 0.50, 0.34), (0.0, 0.0, 0.27), "stone")
    collide((0.0, 0.0, 0.22), (1.76, 0.58, 0.44))

    mound((-0.56, 0.0, 0.42), 0.24, 0.17, "coal")
    mound((0.0, 0.0, 0.42), 0.24, 0.17, "ore")
    mound((0.56, 0.0, 0.42), 0.24, 0.17, "coal")

    for x in (-0.28, 0.28):
        box((0.07, 0.52, 0.26), (x, 0.0, 0.38), "iron")

    rim(0.86, 0.29, 0.46, width=0.08, height=0.09)

    # Timber ends, so it is not one long slab of grey.
    for x in (-0.86, 0.86):
        box((0.10, 0.56, 0.42), (x, 0.0, 0.31), "wood")


# --------------------------------------------------------------------------- export

VARIANTS = [
    ("stoker_trough_stone", trough_stone, "A - Stone trough (the original)"),
    ("stoker_trough_timber", trough_timber, "B - Timber trough (iron-hooped)"),
    ("stoker_trough_raised", trough_raised, "C - Raised trough (on legs)"),
    ("stoker_trough_long", trough_long, "D - Long trough (three bays)"),
]


def finish(name):
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
    bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = name

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    # scale_to_bounds, so every UV lands inside 0..1 across the whole model.
    #
    # World-scale UVs running past 1 forced the runtime to wrap them into the atlas
    # tile, and wrapping happens per vertex: a face spanning 0.9 to 1.2 ends up with
    # vertices at 0.9 and 0.2, so the GPU interpolates backwards across the entire
    # tile between them. That is where the smeared diagonal banding came from - and a
    # gradient across a flat face is what made a provably square model look crooked.
    bpy.ops.uv.cube_project(cube_size=1.0, correct_aspect=True, scale_to_bounds=True)
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
            bsdf.inputs["Roughness"].default_value = 0.88


def stage_and_render(out_png):
    bpy.ops.mesh.primitive_plane_add(size=20.0, location=(0, 0, 0))
    ground = bpy.context.active_object
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.19, 0.21, 0.16, 1)
    ground.data.materials.append(gm)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(1.6, 0.1, 0.5))
    cube = bpy.context.active_object
    cm = bpy.data.materials.new("ref")
    cm.use_nodes = True
    cm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.52, 0.52, 0.56, 1)
    cube.data.materials.append(cm)

    bpy.ops.object.camera_add(location=(-1.9, 2.6, 1.7))
    cam = bpy.context.active_object
    cam.data.lens = 40
    target = bpy.data.objects.new("aim", None)
    bpy.context.collection.objects.link(target)
    target.location = (0.0, 0.0, 0.45)
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
    scene.render.resolution_y = 500
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
        print("TROUGH_OK %s verts=%d tris=%d" % (name, verts, tris))


main()
