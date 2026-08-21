"""
Tyrvi: resin-soaked pinewood, the fuel that replaces resin in torches.

    blender --background --python tools/tyrvi_designs.py

Three silhouettes, because two that share an outline are one design. An item is judged in
two places and they disagree about what matters - a 128px icon in a grid, where the
outline is nearly all of it, and lying on the ground at your feet, where the surface is.
So each variant gets both, and the ground shot is taken from standing height rather than
from the hero angle an icon wants.

Modelled face-up, lying in the XY plane with thickness in Z. An item's placement format
carries only yaw, so anything modelled standing ends up staring at the sky.

Groups are wood, wood_end and resin. The first two are the trade the woodrack already
makes - side grain on the sides, the donor's painted end disc on the sawn ends - and
resin is its own group because it is what the thing is *for*, and a fuel you cannot tell
from a stick is a stick.
"""

import bpy
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from upgrade_variants import (                                    # noqa: E402
    PREVIEWS, SHELF, TINTS,
    bounds, box, clear_scene, collide, finish, icon_scene, jitter, log, material,
    part, render, rnd, tint, write_col,
)

# Amber, and darker than resin looks in the hand. Valheim's Resin item is a translucent
# blob lit from inside; this is resin soaked into timber, which is a stain rather than a
# bead - so the colour wanted is that of the wet patch, not of the drop.
TINTS["resin"] = (0.55, 0.28, 0.06, 1.0)
TINTS["soak"] = (0.26, 0.14, 0.06, 1.0)

# A hand-sized splint. Vanilla's Wood item is about 0.45m along its longest axis and its
# Resin blob about 0.12, so 0.30 sits between the two things this is made of, which is
# where a crafted intermediate belongs.
LENGTH = 0.30


def splinter(length, radius, location, sides=5, rot=0.0):
    """
    One split of pinewood, lying along X.

    Odd-sided and never round: a split billet is flat facets struck off a log, and a
    seven-sided cylinder reads as a dowel. Three to five reads as split rather than
    turned.

    **No roll, and that is not a preference.** log()'s roll argument is wrong for
    axis="x" and right for axis="y", which is why every model built before this one got
    away with it. Blender's default euler order is XYZ, meaning R = Rz.Ry.Rx, so the X
    term is applied first. For axis="y" the helper puts the axis tip on X and the roll on
    Y, so the roll happens after the cylinder is already lying down and spins it about its
    own length - correct. For axis="x" it puts the roll on X and the tip on Y, so the roll
    happens to a cylinder still standing on Z: it tips the axis towards Y, and the
    following Ry(90) turns that into a heading in the XY plane. With roll running to 360
    the splints pointed in every direction on the ground - the bundle measured 0.295m
    across when its splints span 0.09.

    Not fixed in log() on purpose. Every committed .obj in this repo was built through it
    with a seeded jitter stream, so changing the rotation maths there rewrites the
    woodrack and the tun as a side effect of adding an item. The variety roll was buying
    is bought here by the side count and the taper instead.
    """
    return log(radius * (0.88 + rnd() * 0.24), length * (0.96 + rnd() * 0.08),
               location, "wood", axis="x", sides=sides, rot=rot,
               wobble=0.6, taper=0.80 + rnd() * 0.16, roll=0.0)


def bead(size, location, mat="resin"):
    """
    A run of resin.

    An ico sphere rather than a box, because this is the one part of the model that was
    not split, sawn or snapped - a hard edge on it reads as a chip of amber sitting on
    the wood rather than as something that ran down it.
    """
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.5, location=location)
    obj = bpy.context.active_object
    obj.scale = (size[0], size[1], size[2])
    obj.rotation_euler = (0.0, 0.0, math.radians(rnd() * 90.0))
    return part(obj, mat, bevel=0.003, projection="cube")


# --------------------------------------------------------------------------- variants

def tyrvi_splint():
    """
    A single long splinter, one end soaked dark and beaded with resin.

    The plainest of the three, and the one whose outline survives 128 pixels best: a long
    diagonal reads as itself at any size where a bundle becomes a smudge. The risk is
    that it is also the outline of a plain stick, which is why the soaked head is its own
    material rather than a darker end of the same one.
    """
    splinter(LENGTH * 0.78, 0.031, (-0.035, 0.0, 0.031), sides=5)

    # The soaked head is another splinter of the same stick, not a block stuck to the end
    # of it. As a box it was wider than the timber it sat on and read as a wedge someone
    # had wedged there - the give-away being that it had its own outline. Same cross
    # section, overlapping by a third of its length, and the join disappears.
    splinter(LENGTH * 0.42, 0.034, (0.088, 0.002, 0.032), sides=5, rot=1.5)

    # Two beads, not three, and each about twice the size. At 3cm they were orange
    # crumbs lying near the wood rather than resin on it - a bead has to be big enough to
    # touch both the timber and its own shadow.
    bead((0.055, 0.044, 0.030), (0.055, -0.012, 0.052))
    bead((0.040, 0.034, 0.024), (0.128, 0.014, 0.048))
    collide((0.0, 0.0, 0.03), (LENGTH * 1.1, 0.10, 0.06))


def tyrvi_bundle():
    """
    Five splints bound with cord - a faggot of fatwood rather than one piece.

    Reads as a made thing at a glance, which the other two have to earn with their
    surface, and it is the only one that says "several" without a stack count. It is also
    the one most likely to turn into a brown smudge at icon size.
    """
    for i in range(5):
        y = -0.036 + i * 0.018
        splinter(LENGTH * (0.92 + rnd() * 0.14), 0.014,
                 (jitter(0.012), y, 0.016 + (i % 2) * 0.013),
                 sides=(3, 5, 4, 5, 3)[i], rot=jitter(3.5))

    # Two cord wraps, one thin cylinder each rather than a ring of blocks: the splints
    # sit inside it so only its outer wall is ever seen, and the difference is a couple
    # of hundred triangles for a shape nobody can tell apart.
    for x in (-0.075, 0.080):
        log(0.044, 0.016, (x, 0.0, 0.022), "soak", axis="x", sides=11, wobble=0.3)

    for i in range(3):
        bead((0.024, 0.020, 0.014), (0.115 + i * 0.018, -0.020 + i * 0.020, 0.036))
    collide((0.0, 0.0, 0.022), (LENGTH * 1.1, 0.11, 0.05))


def tyrvi_billet():
    """
    A short fat chunk split off a stump, resin pooling in the hollow of the split face.

    The opposite bet from the splint: mass rather than line. A chunk this size reads as
    fuel where a stick reads as kindling, and the pooled resin has somewhere to sit
    instead of being beads stuck to a surface. It pays for that with the clean diagonal
    at icon size.
    """
    splinter(LENGTH * 0.62, 0.055, (0.0, 0.0, 0.050), sides=5)
    splinter(LENGTH * 0.52, 0.030, (0.014, 0.048, 0.038), sides=4, rot=-3.0)

    # Pooled along the split face rather than beaded on it: fewer, larger, and sunk into
    # the timber so the rim of the split cuts across them.
    for i in range(4):
        bead((0.042 - i * 0.004, 0.040, 0.016),
             (-0.052 + i * 0.036, jitter(0.014), 0.078))

    box((0.030, 0.088, 0.070), (-LENGTH * 0.30, 0.004, 0.048), "soak")
    collide((0.0, 0.0, 0.05), (LENGTH * 0.8, 0.13, 0.10))


VARIANTS = [
    ("tyrvi_splint", tyrvi_splint, "TYRVI - Single splinter"),
    ("tyrvi_bundle", tyrvi_bundle, "TYRVI - Bound faggot"),
    ("tyrvi_billet", tyrvi_billet, "TYRVI - Split chunk"),
]

# 20cm, not a metre. A metre cube beside a 30cm splint fills the frame and says nothing
# about the splint - the point of a reference is that it is comparable to the subject.
REF = 0.20


def ground_scene():
    """Standing height, looking down at it where it would actually be lying."""
    bpy.context.scene.render.film_transparent = False

    bpy.ops.mesh.primitive_plane_add(size=20.0, location=(0.0, 0.0, 0.0))
    bpy.context.active_object.data.materials.append(material("ground"))

    bpy.ops.mesh.primitive_cube_add(size=REF, location=(-0.26, 0.10, REF / 2.0))
    bpy.context.active_object.data.materials.append(material("ref"))

    bpy.ops.object.light_add(type="SUN", location=(-1.2, -1.6, 2.0))
    key = bpy.context.active_object
    key.data.energy = 1.4
    key.data.angle = math.radians(3.0)
    key.rotation_euler = (math.radians(48.0), 0.0, math.radians(-34.0))

    bpy.ops.object.light_add(type="SUN", location=(1.4, -1.2, 0.9))
    fill = bpy.context.active_object
    fill.data.energy = 0.35
    fill.rotation_euler = (math.radians(96.0), 0.0, math.radians(42.0))

    world = bpy.data.worlds.new("w")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.48, 0.44, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.28

    # 1.7m up and 0.75m back, which is where your eyes are when the thing is at your
    # feet. 50mm rather than the 35 the buildable pieces use: there is no 4m station to
    # fit in beside it, and a wide lens on a small object at close range bends it.
    # Eye height stays 1.7m, because that is the question - what it looks like at your
    # feet. What changes is the lens: at 50mm a 30cm item is a fifth of the frame and the
    # render says nothing about it. 85mm from the same place is the same view, read.
    bpy.ops.object.camera_add(location=(-0.02, -0.62, 1.70))
    cam = bpy.context.active_object
    cam.data.lens = 85.0
    cam.rotation_euler = (math.radians(20.0), 0.0, math.radians(0.0))
    bpy.context.scene.camera = cam


def tint_stage():
    for name, colour in (("ground", (0.19, 0.21, 0.16, 1.0)),
                         ("ref", (0.55, 0.55, 0.58, 1.0))):
        mat = material(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = colour
            bsdf.inputs["Roughness"].default_value = 0.9


def main():
    os.makedirs(PREVIEWS, exist_ok=True)
    os.makedirs(SHELF, exist_ok=True)

    for name, builder, label in VARIANTS:
        clear_scene()
        builder()
        obj = finish(name)
        tris = len(obj.data.polygons)
        dims = tuple(obj.dimensions)

        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.wm.obj_export(filepath=os.path.join(SHELF, name + ".obj"),
                              export_selected_objects=True, export_materials=True,
                              forward_axis="Z", up_axis="Y")
        write_col(os.path.join(SHELF, name + ".col"))

        tint()
        centre, extent = bounds(obj)
        icon_scene(centre, extent)
        render(os.path.join(SHELF, name + "_icon.png"), (128, 128))

        clear_scene()
        builder()
        obj = finish(name)
        tint()
        tint_stage()
        ground_scene()
        render(os.path.join(PREVIEWS, name + "_ground.png"), (720, 560))

        print("TYRVI %-16s tris=%-5d  %.3f x %.3f x %.3fm  %s"
              % (name, tris, dims[0], dims[1], dims[2], label))

    print("TYRVI_DONE")


main()
