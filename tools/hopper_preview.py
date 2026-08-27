"""
Renders the hopper the way you will actually meet it: standing next to it.

Deliberately not a hero shot. A three-quarter view from 1.7m at three metres is what
a player sees, and a model that only reads from a flattering angle is a model that
does not read. A 1m reference cube stands beside it for scale.

    blender --background --python tools/hopper_preview.py
"""

import bpy
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBJ = os.path.join(ROOT, "assets", "kynda_hopper.obj")
OUT = os.path.join(ROOT, "assets", "previews", "hopper_eyeheight.png")

TINTS = {
    "wood": (0.28, 0.18, 0.10, 1.0),
    "iron": (0.20, 0.20, 0.22, 1.0),
    "stone": (0.42, 0.41, 0.38, 1.0),
}


def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def tint_materials():
    for mat in bpy.data.materials:
        key = mat.name.split(".")[0].lower()
        if key not in TINTS:
            continue
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = TINTS[key]
            bsdf.inputs["Roughness"].default_value = 0.85


def scale_cube():
    """One cubic metre, so the eye has something honest to measure against."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(1.5, 0.0, 0.5))
    cube = bpy.context.active_object
    cube.name = "one_metre"
    mat = bpy.data.materials.new("ref")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.5, 0.5, 0.55, 1)
    cube.data.materials.append(mat)


def ground():
    bpy.ops.mesh.primitive_plane_add(size=20.0, location=(0, 0, 0))
    plane = bpy.context.active_object
    mat = bpy.data.materials.new("ground")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.18, 0.20, 0.15, 1)
    plane.data.materials.append(mat)


def camera_and_light():
    # Eye height, three metres back, angled off the front-left so the chute is visible.
    #
    # Aimed with a Track To constraint rather than hand-computed Euler angles. The
    # first attempt did the trigonometry by hand, got the axis convention wrong, and
    # rendered a photograph of the ground - and a blank render looks identical to a
    # failed import, which is a confusing way to lose ten minutes.
    bpy.ops.object.camera_add(location=(-2.3, -2.3, 1.7))
    cam = bpy.context.active_object
    cam.data.lens = 40

    target = bpy.data.objects.new("aim", None)
    bpy.context.collection.objects.link(target)
    target.location = (0.0, 0.0, 0.65)

    track = cam.constraints.new(type="TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    bpy.context.scene.camera = cam

    bpy.ops.object.light_add(type="SUN", location=(3, -4, 6))
    sun = bpy.context.active_object
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))

    world = bpy.data.worlds.new("w")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.42, 0.52, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.6


def main():
    clear()
    bpy.ops.wm.obj_import(filepath=OBJ, forward_axis="Z", up_axis="Y")
    tint_materials()
    scale_cube()
    ground()
    camera_and_light()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 675
    scene.render.filepath = OUT

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print("PREVIEW_OK", OUT)


main()
