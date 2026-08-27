"""
Five original smelter-store designs, built and rendered for comparison.

    blender --background --python tools/smelter_designs.py

Written after seven rejected attempts, and shaped by why they failed rather than by
new ideas alone:

  * every part must overlap its neighbour - a 5cm gap reads as a detached stick
  * few large parts beat many small ones - small parts read as rubble, not detail
  * heaps of little cubes look like confetti; use one mass, not twelve lumps
  * a capped cone is a lid, so an open top needs a rim built from separate boxes
  * primitive_cube_add(size=1.0) is already a unit cube - scale by size, not size/2

Each is a different proportion on purpose. If two designs share a silhouette then
there is really only one design, which is what made the first batch feel like no
choice at all.
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
    "stone": (0.44, 0.43, 0.40, 1.0),
    "coal": (0.07, 0.07, 0.08, 1.0),
    "ore": (0.36, 0.25, 0.16, 1.0),
    "turf": (0.22, 0.26, 0.15, 1.0),
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


def cyl(radius, length, location, mat, axis="z", sides=10, rot_z=0.0):
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


def frustum(bottom, top, height, z, mat, sides=4, rot_z=45.0, location=(0.0, 0.0)):
    bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=bottom, radius2=top,
                                    depth=height, location=(location[0], location[1], z),
                                    rotation=(0.0, 0.0, math.radians(rot_z)))
    obj = bpy.context.active_object
    obj.data.materials.append(material(mat))
    return obj


def mound(centre, radius, height, mat, sides=8):
    """
    One mass, not a scatter of cubes.

    Heaped contents were twelve small boxes before, and from three metres that reads
    as confetti resting on the model because each lump has air around it. A single
    squat cone is a pile.
    """
    frustum(radius, radius * 0.28, height, centre[2] + height / 2.0, mat,
            sides=sides, rot_z=22.5, location=(centre[0], centre[1]))


def rim(half_x, half_y, z, width=0.08, height=0.10, mat="iron"):
    """Four boxes, so the middle stays open. A capped cone would be a lid."""
    box((half_x * 2.0, width, height), (0.0, -half_y + width / 2.0, z), mat)
    box((half_x * 2.0, width, height), (0.0, half_y - width / 2.0, z), mat)
    box((width, half_y * 2.0 - width * 2.0, height), (-half_x + width / 2.0, 0.0, z), mat)
    box((width, half_y * 2.0 - width * 2.0, height), (half_x - width / 2.0, 0.0, z), mat)


# --------------------------------------------------------------------------- designs

def ore_trough():
    """Long, low and open. Sits beside the smelter without competing with it."""
    box((1.36, 0.66, 0.14), (0.0, 0.0, 0.07), "stone")
    box((1.28, 0.58, 0.40), (0.0, 0.0, 0.32), "stone")
    collide((0.0, 0.0, 0.26), (1.36, 0.66, 0.52))

    mound((-0.30, 0.0, 0.48), 0.30, 0.22, "coal")
    mound((0.32, 0.0, 0.48), 0.30, 0.22, "ore")

    box((0.09, 0.60, 0.30), (0.0, 0.0, 0.44), "iron")
    rim(0.66, 0.33, 0.54, width=0.09, height=0.10)


def ore_cairn():
    """
    A heap held back by two timber walls, like ore tipped against a revetment.

    The least built of the five - it is mostly material, with just enough structure
    to say someone put it there.
    """
    box((1.10, 0.14, 0.72), (0.0, -0.44, 0.36), "wood")
    box((0.14, 0.94, 0.72), (-0.48, 0.0, 0.36), "wood")
    collide((0.0, -0.10, 0.36), (1.10, 0.94, 0.72))

    for x, y, r, h, mat in ((-0.12, -0.10, 0.44, 0.52, "ore"),
                            (0.26, 0.16, 0.34, 0.40, "coal")):
        mound((x, y, 0.02), r, h, mat)

    box((0.10, 0.10, 0.86), (-0.48, -0.44, 0.43), "wood")
    box((1.24, 1.06, 0.10), (0.0, -0.02, 0.05), "stone")
    collide((0.0, -0.02, 0.05), (1.24, 1.06, 0.10))


def charcoal_clamp():
    """
    A turf-covered burning mound with a stone collar and an iron draw door.

    How charcoal was actually made, and the only dome in the set - nothing else in a
    Valheim base has that silhouette.
    """
    frustum(0.62, 0.50, 0.20, 0.16, "stone", sides=8, rot_z=22.5)
    collide((0.0, 0.0, 0.16), (1.24, 1.24, 0.20))

    frustum(0.54, 0.30, 0.44, 0.44, "turf", sides=8, rot_z=22.5)
    frustum(0.31, 0.10, 0.24, 0.74, "turf", sides=8, rot_z=22.5)
    collide((0.0, 0.0, 0.50), (1.08, 1.08, 0.70))

    box((0.30, 0.16, 0.28), (0.0, 0.50, 0.24), "iron")
    box((0.38, 0.10, 0.09), (0.0, 0.52, 0.40), "iron")

    for a in (55, 125, 235, 305):
        r = math.radians(a)
        box((0.10, 0.10, 0.26), (math.cos(r) * 0.54, math.sin(r) * 0.54, 0.15), "stone")


def ore_barrow():
    """
    A single-axle barrow, laden and tipped back on its legs.

    Diagonal where everything else is upright, and the only design with a wheel.
    """
    cyl(0.22, 0.08, (0.0, 0.42, 0.22), "iron", axis="x", sides=12)
    box((0.14, 0.14, 0.10), (0.0, 0.42, 0.22), "iron")

    for x in (-0.26, 0.26):
        box((0.09, 1.16, 0.09), (x, 0.02, 0.44), "wood", rot_x=-16.0)
        box((0.08, 0.08, 0.34), (x, -0.44, 0.19), "wood")

    box((0.62, 0.76, 0.36), (0.0, 0.10, 0.54), "wood", rot_x=-16.0)
    box((0.68, 0.10, 0.34), (0.0, -0.24, 0.60), "wood", rot_x=-16.0)
    collide((0.0, 0.04, 0.44), (0.70, 1.20, 0.80))

    mound((0.0, 0.14, 0.62), 0.28, 0.26, "ore")

    box((0.12, 0.12, 0.44), (0.0, -0.50, 0.66), "wood")


def twin_bins():
    """
    Two narrow bins shouldering each other, coal and ore kept apart.

    The only vertical design, and the only one where the two materials are separated
    by structure rather than by which side of a heap they landed on.
    """
    box((1.02, 0.56, 0.14), (0.0, 0.0, 0.07), "stone")
    collide((0.0, 0.0, 0.07), (1.02, 0.56, 0.14))

    for x, mat in ((-0.25, "coal"), (0.25, "ore")):
        box((0.44, 0.48, 0.92), (x, 0.0, 0.60), "wood")
        mound((x, 0.0, 1.04), 0.21, 0.18, mat)
        box((0.48, 0.52, 0.07), (x, 0.0, 0.78), "iron")
        box((0.48, 0.52, 0.07), (x, 0.0, 0.34), "iron")

    box((0.08, 0.52, 1.02), (0.0, 0.0, 0.63), "iron")
    collide((0.0, 0.0, 0.60), (1.02, 0.56, 0.92))

    for x in (-0.48, 0.48):
        box((0.08, 0.08, 1.00), (x, 0.0, 0.62), "wood")


# --------------------------------------------------------------------------- export

VARIANTS = [
    ("kynda_ore_trough", ore_trough, "1 - Ore trough (low, long, divided)"),
    ("kynda_ore_cairn", ore_cairn, "2 - Ore cairn (heap on a revetment)"),
    ("kynda_charcoal_clamp", charcoal_clamp, "3 - Charcoal clamp (turf dome)"),
    ("kynda_ore_barrow", ore_barrow, "4 - Ore barrow (wheeled, tipped)"),
    ("kynda_twin_bins", twin_bins, "5 - Twin bins (vertical, separated)"),
]


def finish(name):
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
    bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = name

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
            bsdf.inputs["Roughness"].default_value = 0.88


def stage_and_render(out_png):
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

    bpy.ops.object.camera_add(location=(-1.85, 2.55, 1.7))
    cam = bpy.context.active_object
    cam.data.lens = 42
    target = bpy.data.objects.new("aim", None)
    bpy.context.collection.objects.link(target)
    target.location = (0.0, 0.0, 0.5)
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
        print("DESIGN_OK %s verts=%d tris=%d" % (name, verts, tris))


main()
