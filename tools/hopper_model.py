"""
Builds the Hopper mesh and exports it as OBJ plus a box-collider sidecar.

Run headless:
    blender --background --python tools/hopper_model.py

The shape is a genuine hopper rather than a barrel with a new name: a square bin
that tapers inwards towards the bottom, iron-banded, standing on short legs with a
chute at the front pointing at whatever it feeds. Read from across a base it should
say "ore goes in the top, ore comes out the bottom" - which is exactly the thing a
barrel fails to say.

Materials are group names only. Nothing here paints anything: at runtime each group
is skinned with a real vanilla material borrowed off a game prefab, so the piece
matches the game's own art rather than approximating it.
"""

import bpy
import bmesh
import math
import os

# --------------------------------------------------------------------------- setup

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

GROUPS = ("wood", "iron", "stone")

COLLIDERS = []


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.objects):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def material(name):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    return mat


def collide(centre, size):
    """Remember a box for the .col sidecar. Rotation is always identity here."""
    COLLIDERS.append((centre, size))


# --------------------------------------------------------------------------- parts

def add_box(name, size, location, mat, rot_z=0.0, rot_x=0.0, collider=False):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    # scale, not scale/2. primitive_cube_add(size=1.0) already makes a unit cube
    # spanning -0.5..0.5, so halving again produced every box at half its stated
    # size - while cones and cylinders, which take a radius, came out correct. Mixing
    # the two is why banding sat inside the bin, corner straps floated clear of the
    # crate they were meant to bind, and a footing swallowed a chute: every
    # box-against-cone relationship in the file was wrong by a factor of two.
    obj.scale = (size[0], size[1], size[2])
    obj.rotation_euler = (math.radians(rot_x), 0.0, math.radians(rot_z))
    obj.data.materials.append(material(mat))
    if collider:
        collide(location, size)
    return obj


def add_cyl(name, radius, length, location, mat, axis="z", sides=12):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=length, vertices=sides,
                                        location=location)
    obj = bpy.context.active_object
    obj.name = name
    if axis == "x":
        obj.rotation_euler = (0.0, math.radians(90), 0.0)
    elif axis == "y":
        obj.rotation_euler = (math.radians(90), 0.0, 0.0)
    obj.data.materials.append(material(mat))
    return obj


def add_taper(name, bottom, top, height, z, mat, sides=4):
    """A four-sided frustum: the hopper's defining shape."""
    bpy.ops.mesh.primitive_cone_add(
        vertices=sides, radius1=bottom, radius2=top, depth=height,
        location=(0.0, 0.0, z), rotation=(0.0, 0.0, math.radians(45)))
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(material(mat))
    return obj


def band(name, radius, z, thickness=0.045):
    """An iron hoop round the bin."""
    bpy.ops.mesh.primitive_cone_add(
        vertices=4, radius1=radius, radius2=radius, depth=thickness,
        location=(0.0, 0.0, z), rotation=(0.0, 0.0, math.radians(45)))
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(material("iron"))
    return obj


# --------------------------------------------------------------------------- build

def rim_frame(name, half, z, width=0.09, height=0.10, mat="iron"):
    """
    A square rim built from four boxes.

    Not a band(): that makes a *capped* four-sided cylinder, which is a solid plate.
    Used anywhere on the body it is hidden inside the bin and only its edge shows,
    which is the intent - but put one on top and the cap becomes a lid, turning the
    whole thing into a closed crate. Four boxes leave the middle genuinely open.
    """
    inner = half - width / 2.0
    for y in (-inner, inner):
        add_box(name, (half * 2.0, width, height), (0.0, y, z), mat)
    for x in (-inner, inner):
        add_box(name, (width, half * 2.0 - width * 2.0, height), (x, 0.0, z), mat)


def build_hopper():
    """
    A bin standing on its own footing.

    Two rebuilds got here. The first slung the taper on four short legs, the second
    on a full corner frame, and at eye height both read the same way: loose sticks
    near a floating box, because a 0.10 post only grazes the bin's corner and the eye
    reads the gap, not the contact. Sitting the taper straight on the stone removes
    the join to get wrong. Fewer parts, all of them touching.
    """
    clear_scene()

    # Stone footing. Kept narrow on purpose: the first version was 0.94 across and
    # swallowed the chute whole, so the one part that says which way the hopper faces
    # was invisible from every angle.
    add_box("footing", (0.72, 0.72, 0.13), (0.0, 0.0, 0.065), "stone")
    collide((0.0, 0.0, 0.065), (0.72, 0.72, 0.13))

    # Throat: lifts the bin off the stone and leaves room underneath for the chute to
    # come out where it can be seen.
    add_taper("throat", bottom=0.16, top=0.25, height=0.30, z=0.28, mat="iron")

    # The bin: narrow at the throat, wide at the mouth. The taper is the whole idea,
    # so it runs the full height rather than being a detail on a box.
    add_taper("bin", bottom=0.25, top=0.60, height=0.90, z=0.88, mat="wood")
    collide((0.0, 0.0, 0.70), (0.86, 0.86, 1.20))

    # Iron banding. These are solid discs, which is fine here: the bin swallows the
    # middle and only the protruding edge shows, which is exactly what a hoop is.
    #
    # A four-sided cone turned 45 degrees is a square whose half-width is r/root-2,
    # not r. Sizing these by eye put the first set inside the bin where they showed
    # nothing, and the rim a full 18cm proud of the edge like a pair of wings. The
    # radii below are taken off the taper at the height each one sits at.
    band("band_low", 0.34, 0.60)     # bin here is 0.315
    band("band_mid", 0.50, 0.98)     # bin here is 0.468

    # The mouth sits just *above* the bin's own cap rather than below it. The cone is
    # capped, so anything tucked underneath is simply hidden and the top reads as a
    # solid lid - a crate, not a hopper. A dark plate on top leaves the wood as a thin
    # border round a dark square, which is what an opening looks like from eye height.
    band("mouth", 0.52, 1.340, thickness=0.02)

    # Rim as four boxes, sized to the bin's actual half-width (0.60 / root-2 = 0.424)
    # so it reads as an edge rather than a shelf.
    rim_frame("rim", half=0.45, z=1.325, width=0.075, height=0.085)

    # The chute: one angled box, buried in the throat at one end and overhanging the
    # footing at the other.
    #
    # It was three parts - spout, lip and brace - and the lip kept ending up as a
    # loose block on the ground beside the model, because positioning a separate piece
    # against a rotated one means redoing the rotation by hand every time the angle
    # changes. One box that starts inside the throat cannot come adrift from it.
    add_box("chute", (0.30, 0.52, 0.12), (0.0, 0.30, 0.26), "iron", rot_x=25.0)
    collide((0.0, 0.26, 0.30), (0.34, 0.26, 0.52))


# --------------------------------------------------------------------------- export

def join_all(name="hopper"):
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
    bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = name
    return obj


def unwrap(obj, texel=1.0):
    """
    World-scale UVs.

    The borrowed vanilla materials expect roughly one texture repeat per metre; a
    smart-projected unwrap at that scale keeps the grain the same size as it is on
    the game's own walls, rather than smeared or tiled to a blur.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=texel, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def triangulate(obj):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(mesh)
    bm.free()
    mesh.calc_normals_split() if hasattr(mesh, "calc_normals_split") else None


def write_colliders(path):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# box  centre x y z  size x y z  qx qy qz qw   "
                 "(metres, Y-up, Unity quat)\n")
        for (cx, cy, cz), (sx, sy, sz) in COLLIDERS:
            # Blender is Z-up, Unity is Y-up, so Y and Z swap.
            #
            # No sign flip on the new Z. That was the first guess and it was wrong:
            # the exporter is run with forward_axis="Z", which sends Blender +Y to
            # OBJ +Z unchanged. Measured off the exported file - the chute sits at
            # Blender y=+0.30 and lands at OBJ z=+0.51 - rather than reasoned about,
            # because a flipped collider puts the solid part behind the model where
            # nothing visible explains why you cannot walk through it.
            fh.write("box %.3f %.3f %.3f %.3f %.3f %.3f 0 0 0 1\n"
                     % (cx, cz, cy, sx, sz, sy))


def main():
    build_hopper()
    obj = join_all()
    unwrap(obj)
    triangulate(obj)

    os.makedirs(OUT_DIR, exist_ok=True)
    obj_path = os.path.join(OUT_DIR, "stoker_hopper.obj")

    bpy.ops.wm.obj_export(
        filepath=obj_path,
        export_selected_objects=False,
        export_materials=True,
        export_normals=True,
        export_uv=True,
        export_triangulated_mesh=True,
        # Blender Z-up to Unity Y-up. The runtime loader expects the file already
        # in the game's axes, the same way the altar models are exported.
        forward_axis="Z",
        up_axis="Y",
        path_mode="AUTO",
    )

    write_colliders(os.path.join(OUT_DIR, "stoker_hopper.col"))

    verts = len(obj.data.vertices)
    tris = len(obj.data.polygons)
    print("HOPPER_OK verts=%d tris=%d groups=%s boxes=%d"
          % (verts, tris, ",".join(sorted({m.name for m in obj.data.materials})),
             len(COLLIDERS)))


main()
