"""
The Tun assembled from Haldor's own barrels: the big one filled with coal, the small
one with ore.

    blender --background --python tools/tun_camp.py

This replaces two hand-built rounds, and the reasoning is worth the file it sits in.

The hand-built casks were fought over four sessions - donor, density, rect, flip - and
every fight was the same fight: fitting a foreign projection to a sheet painted for a
different body. fi_village_wood's stave strip is not a tiling texture, it is a painted
FACE, stretched over vanilla's barrel like a label (measured: ~58 texels/m vertically,
~21 horizontally - they stretch and do not care). The only geometry that sheet fits
perfectly is the geometry it was painted for, and we have that geometry: the rips carry
vanilla's own UVs. So the model IS the camp barrels, UVs untouched, and the whole
projection problem stops existing.

The contents are vanilla's pattern too, which the camp proved against this mod's own
earlier doctrine: fruit, fish and sweetpot barrels are 140-triangle vessels with a
painted fill surface. Coal in the big one and ore in the small one is that exact
pattern wearing the smelter's inputs. The fill faces are split into their own groups -
"coal" and "ore" - so the runtime skins them from coal_pile and CopperOre, the donors
the Skins table already carries.

Face classification: a content face points up and samples OUTSIDE the wood tiles.
The wood tiles are measured off the ripped empty barrel - stave strip u .331-.519
v .500-.668, cap disc u .734-.856 v .492-.615 - so rim timber that also points up
stays wood by its UVs, not by a height guess.
"""

import bpy
import os
import sys
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import upgrade_variants as uv   # helpers only; it guards its own main()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
PREVIEWS = os.path.join(ASSETS, "previews")
RIPS = r"E:\Repositories\valheim\own-profile\BepInEx\rips"

NAME = "stoker_tun_camp"

# The wood tiles on fi_village_wood, measured from the ripped empty barrel. An upward
# face sampling inside either is rim timber; outside is painted contents.
WOOD_TILES = ((0.331, 0.519, 0.500, 0.668),   # stave strip
              (0.734, 0.856, 0.492, 0.615))   # cap disc


def load_barrel(rip):
    path = os.path.join(RIPS, rip, rip + ".obj")
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis="Z", up_axis="Y")
    fresh = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]

    if len(fresh) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for o in fresh: o.select_set(True)
        bpy.context.view_layer.objects.active = fresh[0]
        bpy.ops.object.join()

    # No axis conversion and no flip: the import keeps the rip's own frame, so the
    # data sits in Blender exactly as Unity had it - X across, Y UP, Z deep - and the
    # winding already produces normals matching the file's. Probed, not assumed: the
    # fish fill reads (0, 1, 0) in Blender, straight up in Unity terms. Every test in
    # this file therefore runs on Y, and a flip here would export the mesh inside-out.
    return bpy.context.view_layer.objects.active if len(fresh) > 1 else fresh[0]


def material(name):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    return mat


def in_wood_tile(u, v):
    for (u0, u1, v0, v1) in WOOD_TILES:
        if u0 - 0.01 <= u <= u1 + 0.01 and v0 - 0.01 <= v <= v1 + 0.01:
            return True
    return False


def classify(obj, content_mat):
    """Wood everywhere, except upward faces sampling outside the wood tiles."""
    mesh = obj.data
    mesh.materials.clear()
    mesh.materials.append(material("wood"))       # slot 0
    mesh.materials.append(content_mat)            # slot 1

    layer = mesh.uv_layers.active.data
    moved = 0
    for poly in mesh.polygons:
        poly.material_index = 0
        # 0.2, not 0.5: the fish barrel's fill is painted on a sloped surface and its
        # faces missed a steeper test entirely - zero content faces found. Leaning on
        # the UV test to say what is wood makes a loose angle safe: a stave face at any
        # tilt still samples the stave strip and stays wood.
        if poly.normal.y <= 0.2:
            continue
        cu = cv = 0.0
        for li in poly.loop_indices:
            cu += layer[li].uv.x
            cv += layer[li].uv.y
        cu /= poly.loop_total
        cv /= poly.loop_total
        if not in_wood_tile(cu, cv):
            poly.material_index = 1
            moved += 1
    print("  %s: %d content face(s) -> %s" % (obj.name, moved, content_mat.name))

    # One top projection across every fill face. Vanilla's fill UVs point at the fruit
    # and fish paintings, which are exactly what the contents must stop being - and
    # remapped per island in game they came out as patchwork: coal in eleven scattered
    # patches inside a dark barrel read as a black pit. Projected from above as one
    # sheet, the coal texture reads as a coal pile and the ore as an ore heap. The
    # donors keep these UVs verbatim (:keep), so what is written here is what renders.
    fills = [poly for poly in mesh.polygons if poly.material_index == 1]
    if fills:
        xs, zs = [], []
        for poly in fills:
            for vi in poly.vertices:
                xs.append(mesh.vertices[vi].co.x)
                zs.append(mesh.vertices[vi].co.z)
        x0, z0 = min(xs), min(zs)
        sx = max(max(xs) - x0, 1e-5)
        sz = max(max(zs) - z0, 1e-5)
        for poly in fills:
            for li in poly.loop_indices:
                vi = mesh.loops[li].vertex_index
                layer[li].uv.x = 0.05 + 0.90 * (mesh.vertices[vi].co.x - x0) / sx
                layer[li].uv.y = 0.05 + 0.90 * (mesh.vertices[vi].co.z - z0) / sz


def ground_at(obj, x):
    lo = min((obj.matrix_world @ Vector(c)).y for c in obj.bound_box)
    cx = sum((obj.matrix_world @ Vector(c)).x for c in obj.bound_box) / 8.0
    obj.location.x += x - cx
    obj.location.y += -lo


def main():
    os.makedirs(PREVIEWS, exist_ok=True)
    uv.clear_scene()

    big = load_barrel("fi_vil_container_barrel_big_fruit")
    classify(big, material("coal"))
    ground_at(big, -0.33)

    small = load_barrel("fi_vil_container_barrel_small_fish")
    classify(small, material("ore"))
    ground_at(small, 0.52)
    # No yaw. A few degrees "so the pair reads as stood together" was tried and read in
    # game as a piece placed crooked - the camp's own barrels stand straight, and that
    # is the reference this whole model exists to match.

    bpy.ops.object.select_all(action="DESELECT")
    big.select_set(True)
    small.select_set(True)
    bpy.context.view_layer.objects.active = big
    bpy.ops.object.join()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    tun = bpy.context.active_object
    tun.name = NAME

    tris = sum(1 for _ in tun.data.polygons)  # quads counted below via calc
    tun.data.calc_loop_triangles()
    tris = len(tun.data.loop_triangles)

    # One box over the pair, written in UNITY space: the game is Y-up, so Blender's z
    # becomes the middle number, exactly as every other .col here does it.
    los = [1e9] * 3; his = [-1e9] * 3
    for c in tun.bound_box:
        w = tun.matrix_world @ Vector(c)
        for i in range(3):
            los[i] = min(los[i], w[i]); his[i] = max(his[i], w[i])
    cx, cy, cz = [(los[i] + his[i]) / 2 for i in range(3)]
    sx, sy, sz = [his[i] - los[i] for i in range(3)]
    with open(os.path.join(ASSETS, NAME + ".col"), "w") as col:
        col.write("# box  centre x y z  size x y z  qx qy qz qw\n")
        col.write("box %.3f %.3f %.3f %.3f %.3f %.3f 0 0 0 1\n"
                  % (cx, cy, cz, sx, sy, sz))

    bpy.ops.object.select_all(action="DESELECT")
    tun.select_set(True)
    bpy.ops.wm.obj_export(filepath=os.path.join(ASSETS, NAME + ".obj"),
                          export_selected_objects=True, export_materials=True,
                          forward_axis="Z", up_axis="Y")

    # Preview and icon with the shared flat tints - shape and grouping only; the real
    # look is vanilla's own paint and only the game can show it.
    uv.tint()
    centre, size = uv.bounds(tun)
    uv.icon_scene(centre, size)
    uv.render(os.path.join(ASSETS, NAME + "_icon.png"), (128, 128))
    bpy.context.scene.render.film_transparent = False

    print("  %s: %d tris, groups [wood, coal, ore]" % (NAME, tris))


main()
