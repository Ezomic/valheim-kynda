"""
Hammer icons for the two station upgrades.

    blender --background --python tools/upgrade_icons.py

Reads the shipped .obj back in and renders assets/<name>_icon.png at 128px. Reading
the mesh rather than rebuilding it matters: the icon is a promise about what you are
about to place, so it has to come from the exact geometry the game will load, not
from a builder function that has since drifted from it.

Two departures from the item-icon pass in vaettir/tools/item_designs.py, both because
these are pieces rather than items:

Three-quarter, not front-on. An item is a silhouette and reads dead-on. A trough
seen from the front is a rectangle with legs - both bays, which are the entire point
of the thing, are on top and invisible. Vanilla's own piece icons are all slightly
above and slightly to the side for exactly this reason.

Still orthographic, though. Perspective on something a metre across just makes the
near end fatter than the far one, and an icon is a symbol rather than a photograph.
"""

import bpy
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

# Same tints as upgrade_models.py. Flat colour bands, no gradients - the runtime
# skins the real piece with borrowed vanilla materials, so these only ever have to
# read as "wood", "iron", "stone", "ore" and "coal" at 128 pixels.
TINTS = {
    "wood":  (0.30, 0.19, 0.10, 1.0),
    "iron":  (0.19, 0.19, 0.21, 1.0),
    "stone": (0.42, 0.41, 0.38, 1.0),
    "coal":  (0.06, 0.06, 0.07, 1.0),
    "ore":   (0.34, 0.24, 0.16, 1.0),
}

MODELS = ["stoker_kiln_woodrack", "stoker_trough_raised"]


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.objects,
                  bpy.data.lights, bpy.data.cameras, bpy.data.worlds):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def load(name):
    """
    The exact inverse of the export in upgrade_models.py.

    Blender is Z-up and Unity is Y-up, so the export writes forward_axis="Z",
    up_axis="Y". Importing with the same two settings is what makes it a round trip
    rather than a model lying on its side.
    """
    path = os.path.join(ASSETS, name + ".obj")
    bpy.ops.wm.obj_import(filepath=path, forward_axis="Z", up_axis="Y")

    objects = [o for o in bpy.context.selected_objects if o.type == "MESH"]
    if not objects:
        raise RuntimeError("no mesh in " + path)

    return objects


def tint(objects):
    for obj in objects:
        for slot in obj.material_slots:
            if slot.material is None:
                continue

            # The .mtl names each group; anything unexpected goes grey rather than
            # pink, so a new group shows up as a dull patch instead of screaming.
            base = TINTS.get(slot.material.name.lower(), (0.5, 0.5, 0.5, 1.0))

            slot.material.use_nodes = True
            bsdf = slot.material.node_tree.nodes.get("Principled BSDF")
            if bsdf is None:
                continue

            bsdf.inputs["Base Color"].default_value = base
            bsdf.inputs["Roughness"].default_value = 0.82
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = 0.2


def bounds(objects):
    """World-space min/max across every object, so the framing fits the whole piece."""
    lo = [1e9, 1e9, 1e9]
    hi = [-1e9, -1e9, -1e9]

    for obj in objects:
        for corner in obj.bound_box:
            world = obj.matrix_world @ __import__("mathutils").Vector(corner)
            for i in range(3):
                lo[i] = min(lo[i], world[i])
                hi[i] = max(hi[i], world[i])

    centre = [(lo[i] + hi[i]) / 2.0 for i in range(3)]
    size = max(hi[i] - lo[i] for i in range(3))
    return centre, size


def stage(objects):
    scene = bpy.context.scene
    scene.render.film_transparent = True

    centre, size = bounds(objects)

    target = bpy.data.objects.new("target", None)
    scene.collection.objects.link(target)
    target.location = centre

    # 35 degrees around, 26 up. Enough to open both bays of the trough and to show
    # that the woodrack has depth, without tipping so far that it reads as a plan view.
    around = math.radians(35.0)
    up = math.radians(26.0)
    distance = size * 3.0

    bpy.ops.object.camera_add(location=(
        centre[0] + distance * math.cos(up) * math.sin(-around),
        centre[1] - distance * math.cos(up) * math.cos(around),
        centre[2] + distance * math.sin(up)))

    cam = bpy.context.active_object
    cam.data.type = "ORTHO"
    # 1.12 rather than a tight fit: a piece that touches all four edges looks cramped
    # in a slot that already has a border drawn round it.
    cam.data.ortho_scale = size * 1.12
    scene.camera = cam

    track = cam.constraints.new(type="TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    # Suns, not area lights. An area light at close range blows every channel to
    # white - the tell is dark brown rendering as pale beige - and a sun has no
    # falloff to get wrong at any object size.
    bpy.ops.object.light_add(type="SUN", location=(centre[0] - 2.0, centre[1] - 2.4, centre[2] + 2.2))
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


def render(path):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 128
    scene.render.resolution_y = 128
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = path

    # Blender 4.x defaults to AgX, which rolls bright values towards white and
    # would take the flat colour bands with it.
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"

    bpy.ops.render.render(write_still=True)


def main():
    for name in MODELS:
        clear_scene()
        objects = load(name)
        tint(objects)
        stage(objects)

        out = os.path.join(ASSETS, name + "_icon.png")
        render(out)
        print("ICON_OK %s tris=%d" % (name, sum(len(o.data.polygons) for o in objects)))

    print("ICONS_DONE")


main()
