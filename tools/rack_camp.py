"""
The Woodrack: vanilla's own logs, restacked as a rack.

    blender --background --python tools/rack_camp.py

Round one of this used the wood_stack pile verbatim, and the verdict was immediate and
fair: a complete replica of a piece you can already build is not an upgrade, it is the
decoration with a frame around it. But the pile separates into 36 loose logs - real
2-metre rounds wearing wood_pile, the sheet painted for exactly this geometry - and a
RACK is what you get when somebody stacks those logs properly: courses laid crosswise,
ends showing, under a roof. Same paint, same rounds, different object. Vanilla's heap
says "felled"; this says "kept".

Axes: the rip stays in Unity's frame - X across, Y UP, Z deep - as tun_camp.py
established. The logs' long axis is measured per log, not assumed.
"""

import bpy
import math
import os
import sys
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import upgrade_variants as uv   # clear_scene, tint, icon_scene, render, bounds

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
RIP = r"E:\Repositories\valheim\own-profile\BepInEx\rips\wood_stack\wood_stack.obj"

NAME = "stoker_rack_camp"


def material(name):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    return mat


def load_logs():
    """Import, keep the New state, and split it into its loose logs."""
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=RIP, forward_axis="Z", up_axis="Y")
    for o in [o for o in bpy.data.objects if o not in before and o.type == "MESH"]:
        if not o.name.startswith("New/"):
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.separate(type="LOOSE")
        bpy.ops.object.mode_set(mode="OBJECT")

    logs = [o for o in bpy.data.objects if o.type == "MESH"]
    for log in logs:
        log.data.materials.clear()
        log.data.materials.append(material("wood"))
        for poly in log.data.polygons:
            poly.material_index = 0
    return logs


def span(obj):
    lo = [min((obj.matrix_world @ Vector(c))[i] for c in obj.bound_box) for i in range(3)]
    hi = [max((obj.matrix_world @ Vector(c))[i] for c in obj.bound_box) for i in range(3)]
    return lo, hi


def lay(log, index, x, y, z):
    """
    One log into the stack: long axis along X, ends facing the sides, centred at the
    given spot, with a seeded wobble so the courses read as stacked by hands rather
    than by machine - and seeded rather than random, or the committed .obj churns on
    every rebuild.
    """
    lo, hi = span(log)
    dims = [hi[i] - lo[i] for i in range(3)]
    longest = dims.index(max(dims))

    # Rotate the long axis onto X. In this frame Y is up and Z is depth, so a log
    # standing in Y turns about Z, and one lying in Z turns about Y.
    if longest == 1:
        log.rotation_euler.z = math.radians(90.0)
    elif longest == 2:
        log.rotation_euler.y = math.radians(90.0)

    log.rotation_euler.x += math.radians(((index * 37) % 13 - 6) * 0.35)
    log.rotation_euler.y += math.radians(((index * 53) % 11 - 5) * 0.5)

    bpy.ops.object.select_all(action="DESELECT")
    log.select_set(True)
    bpy.context.view_layer.objects.active = log
    bpy.ops.object.transform_apply(rotation=True)

    lo, hi = span(log)
    log.location.x += x - (lo[0] + hi[0]) / 2
    log.location.y += y - (lo[1] + hi[1]) / 2
    log.location.z += z - (lo[2] + hi[2]) / 2


def frame_box(size, location, rot_x=0.0, yaw=0.0):
    """A squared timber, beveled once, in the frame group. Built in the Unity frame:
    size and location are (x, y-up, z-deep)."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.scale = size
    obj.rotation_euler = (math.radians(rot_x), math.radians(yaw), 0.0)

    mod = obj.modifiers.new(name="bevel", type="BEVEL")
    mod.width = 0.014
    mod.segments = 1
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(40.0)
    bpy.ops.object.modifier_apply(modifier="bevel")

    obj.data.materials.clear()
    obj.data.materials.append(material("frame"))
    for poly in obj.data.polygons:
        poly.material_index = 0
    return obj


def main():
    uv.clear_scene()
    logs = load_logs()

    # Three courses of three, one part-course on top, from whichever logs came out of
    # the pile first. Eleven logs at ~160 triangles is the pile's look at a third of
    # its count, and with the frame it lands near 2,100 - the family the smelter and
    # the kiln themselves live in.
    slots = []
    for layer, ly in enumerate((0.26, 0.71, 1.16)):
        for row, lz in enumerate((-0.52, 0.0, 0.52)):
            slots.append((0.02 * ((layer + row) % 2), ly, lz))
    slots += [(0.0, 1.58, -0.26), (0.05, 1.58, 0.30)]

    used = []
    for index, slot in enumerate(slots):
        if index >= len(logs): break
        lay(logs[index], index, *slot)
        used.append(logs[index])
    for spare in logs[len(slots):]:
        bpy.data.objects.remove(spare, do_unlink=True)

    parts = list(used)

    # The frame, hugging the restack: posts clear of the log ends, rails at the height
    # the eye needs the frame to claim the pile, and the lean-to shedding forward.
    px, pz = 1.22, 0.92
    post_h = 2.0
    for sx, sz, yaw in ((-px, -pz, 1.5), (px, -pz, -2.0), (-px, pz, -1.0), (px, pz, 2.5)):
        parts.append(frame_box((0.16, post_h, 0.16), (sx, post_h / 2, sz), yaw=yaw))
    for sz in (-pz, pz):
        parts.append(frame_box((2.58, 0.11, 0.13), (0.0, 1.32, sz)))
    parts.append(frame_box((2.72, 0.09, 2.24), (0.0, 2.06, 0.05), rot_x=17.0))
    parts.append(frame_box((2.78, 0.15, 0.14), (0.0, 1.74, -1.08), rot_x=17.0))

    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = used[0]
    bpy.ops.object.join()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    rack = bpy.context.active_object
    rack.name = NAME

    rack.data.calc_loop_triangles()
    tris = len(rack.data.loop_triangles)

    # One box, written as measured - the data never left Unity's frame.
    los = [1e9] * 3; his = [-1e9] * 3
    for c in rack.bound_box:
        w = rack.matrix_world @ Vector(c)
        for i in range(3):
            los[i] = min(los[i], w[i]); his[i] = max(his[i], w[i])
    with open(os.path.join(ASSETS, NAME + ".col"), "w") as col:
        col.write("# box  centre x y z  size x y z  qx qy qz qw\n")
        col.write("box %.3f %.3f %.3f %.3f %.3f %.3f 0 0 0 1\n" % (
            (los[0] + his[0]) / 2, (los[1] + his[1]) / 2, (los[2] + his[2]) / 2,
            his[0] - los[0], his[1] - los[1], his[2] - los[2]))

    bpy.ops.object.select_all(action="DESELECT")
    rack.select_set(True)
    bpy.ops.wm.obj_export(filepath=os.path.join(ASSETS, NAME + ".obj"),
                          export_selected_objects=True, export_materials=True,
                          forward_axis="Z", up_axis="Y")

    uv.tint()
    centre, size = uv.bounds(rack)
    uv.icon_scene(centre, size)
    uv.render(os.path.join(ASSETS, NAME + "_icon.png"), (128, 128))
    bpy.context.scene.render.film_transparent = False

    print("  %s: %d tris, groups [wood, frame]" % (NAME, tris))


main()
