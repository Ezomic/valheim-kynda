"""
The funnel: the blast furnace's upgrade, finished for the game (LHM-99).

    blender --background --python tools/funnel_model.py

Concept art (Z-Image) went through TRELLIS.2 for a shape reference, but a mesh made that way
comes out soft, with the chute floating beside the bowl. This builds the piece from
primitives to the measurements of that model instead, and paints its own surfaces:

  assets\\kynda_furnace_funnel.obj             four material groups: stone, wood, iron, coal
  assets\\kynda_furnace_funnel.col             collision boxes
  assets\\kynda_furnace_funnel_<group>.png     one tileable texture per group
  assets\\kynda_furnace_funnel_icon.png        the hammer icon, 128px

A stone bowl of stacked blocks on three braced timber legs, an iron chute bolted under it,
a basket of coal beside it. The palette is the blast furnace's own: pale warm stone,
green-bronze metal, orange timber.

The textures are generated here rather than baked from the TRELLIS model. A bake aligned the
smooth model to this block relief only roughly and put the band green on the stone.
"""

import bpy
import bmesh
import math
import os
import random

import numpy as np
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
NAME = "kynda_furnace_funnel"
HEIGHT = 1.9
TRI_CAP = 3500

SIDES = 8
LEG_ANGLES = [140, 20, -80]
CHUTE_ANGLE = 80
BASKET_ANGLE = 200
R_RIM, R_BASE, Z_TOP, Z_BASE = 0.43, 0.25, 0.50, -0.12
LEG_TOP = (0.235, -0.07)
LEG_BOT = (0.385, -0.5)
CORE = 0.04


def pol(r, deg, z):
    a = math.radians(deg)
    return Vector((r * math.cos(a), r * math.sin(a), z))


def ring(r, z, rot=22.5):
    return [pol(r, rot + i * 360 / SIDES, z) for i in range(SIDES)]


def loft(bm, rings, flip=False):
    vs = [[bm.verts.new(p) for p in rg] for rg in rings]
    for k in range(len(vs) - 1):
        for i in range(SIDES):
            j = (i + 1) % SIDES
            f = [vs[k][i], vs[k][j], vs[k + 1][j], vs[k + 1][i]]
            bm.faces.new(f[::-1] if flip else f)


def beam(bm, p0, p1, w, h, up=Vector((0, 0, 1))):
    d = (p1 - p0).normalized()
    s = d.cross(up)
    if s.length < 1e-4:
        s = d.cross(Vector((1, 0, 0)))
    s.normalize()
    u = s.cross(d).normalized()
    e0, e1 = [[bm.verts.new(p + s * sw * w + u * uh * h)
               for sw, uh in ((1, 1), (-1, 1), (-1, -1), (1, -1))] for p in (p0, p1)]
    bm.faces.new(e0[::-1])
    bm.faces.new(e1)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([e0[i], e0[j], e1[j], e1[i]])


def finish(bm, name):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def wall_r(z):
    if z < Z_BASE + 0.02:
        return R_BASE
    return R_BASE + (R_RIM - R_BASE) * ((z - (Z_BASE + 0.02)) / (Z_TOP - Z_BASE - 0.02))


def build_stone():
    bm = bmesh.new()
    loft(bm, [ring(R_BASE * 0.55 - CORE, Z_BASE - 0.02), ring(R_BASE - CORE, Z_BASE + 0.02),
              ring((R_BASE + R_RIM) / 2 - 0.01 - CORE, 0.20), ring(R_RIM - CORE, Z_TOP)])
    loft(bm, [ring(R_RIM, Z_TOP), ring(R_RIM - 0.075, Z_TOP)])
    loft(bm, [ring(R_RIM - 0.075, Z_TOP), ring(R_RIM - 0.11, 0.30), ring(0.17, 0.12)], flip=True)
    bm.faces.new([bm.verts.new(p) for p in ring(0.17, 0.12)])
    bm.faces.new([bm.verts.new(p) for p in ring(R_BASE * 0.55 - CORE, Z_BASE - 0.02)][::-1])

    rng = random.Random(11)
    courses, cols, gap = 6, 16, 0.006
    zs = [Z_BASE + 0.02 + (Z_TOP - Z_BASE - 0.02) * k / courses for k in range(courses + 1)]
    for c in range(courses):
        off = 11.25 if c % 2 else 0.0
        z0, z1 = zs[c] + gap, zs[c + 1] - gap
        for i in range(cols):
            a0 = off + i * 360 / cols + 1.2
            a1 = off + (i + 1) * 360 / cols - 1.2
            jit = rng.uniform(0.0, 0.016)
            corners = ((a0, z0), (a1, z0), (a1, z1), (a0, z1))
            front = [bm.verts.new(pol(wall_r(z) + jit, a, z)) for a, z in corners]
            back = [bm.verts.new(pol(wall_r(z) - CORE + 0.01, a, z)) for a, z in corners]
            bm.faces.new(front[::-1])
            for k in range(4):
                j = (k + 1) % 4
                bm.faces.new([front[k], front[j], back[j], back[k]])
    return finish(bm, "stone")


def build_iron():
    bm = bmesh.new()
    for z, half in ((0.465, 0.030), (0.225, 0.028), (0.0, 0.026)):
        frac = (z - Z_BASE) / (Z_TOP - Z_BASE)
        r = R_BASE + (R_RIM - R_BASE) * frac + 0.024
        loft(bm, [ring(r, z - half), ring(r + 0.012, z - half),
                  ring(r + 0.012, z + half), ring(r, z + half)])

    for a in LEG_ANGLES:
        top, bot = pol(LEG_TOP[0], a, LEG_TOP[1]), pol(LEG_BOT[0], a, LEG_BOT[1])
        along = (bot - top).normalized()
        for t in (0.30, 0.68):
            c = top + (bot - top) * t
            beam(bm, c - along * 0.028, c + along * 0.028, 0.052, 0.052)

    brace_z = -0.30
    brace_r = LEG_TOP[0] + (LEG_BOT[0] - LEG_TOP[0]) * ((LEG_TOP[1] - brace_z) / (LEG_TOP[1] - LEG_BOT[1]))
    for i in range(3):
        a0, a1 = LEG_ANGLES[i], LEG_ANGLES[(i + 1) % 3]
        if a1 < a0:
            a1 += 360
        beam(bm, pol(brace_r, a0, brace_z), pol(brace_r, a1, brace_z), 0.018, 0.018)

    p0, p1 = pol(0.07, CHUTE_ANGLE, -0.115), pol(0.37, CHUTE_ANGLE, -0.40)
    d = (p1 - p0).normalized()
    side = d.cross(Vector((0, 0, 1))).normalized()
    up = side.cross(d).normalized()
    width = 0.075
    beam(bm, p0, p1, width, 0.014)
    for sign in (1, -1):
        edge = side * (width - 0.005) * sign
        beam(bm, p0 + edge + up * 0.03, p1 + edge + up * 0.03, 0.011, 0.034)
    beam(bm, p0 + d * 0.04 + up * 0.06, pol(0.20, CHUTE_ANGLE, -0.04), 0.014, 0.014)
    return finish(bm, "iron")


def basket_centre():
    return pol(0.43, BASKET_ANGLE, -0.5)


def build_wood():
    bm = bmesh.new()
    for a in LEG_ANGLES:
        beam(bm, pol(LEG_TOP[0], a, LEG_TOP[1]), pol(LEG_BOT[0], a, LEG_BOT[1]), 0.044, 0.044)
    c = basket_centre()
    rings = [[c + Vector((r * math.cos(math.radians(22.5 + i * 45)),
                          r * math.sin(math.radians(22.5 + i * 45)), z)) for i in range(SIDES)]
             for r, z in ((0.075, 0.0), (0.095, 0.085))]
    vs = [[bm.verts.new(p) for p in rg] for rg in rings]
    for i in range(SIDES):
        j = (i + 1) % SIDES
        bm.faces.new([vs[0][i], vs[0][j], vs[1][j], vs[1][i]])
    bm.faces.new(vs[0][::-1])
    return finish(bm, "wood")


def build_coal():
    bm = bmesh.new()
    rng = random.Random(5)
    c = basket_centre()

    def lump(at, size):
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=size, matrix=Matrix.Translation(at))

    for _ in range(5):
        lump(c + Vector((rng.uniform(-0.04, 0.04), rng.uniform(-0.04, 0.04),
                         0.095 + rng.uniform(0, 0.03))), rng.uniform(0.032, 0.045))
    for _ in range(8):
        lump(Vector((rng.uniform(-0.11, 0.11), rng.uniform(-0.11, 0.11),
                     0.145 + rng.uniform(0, 0.04))), rng.uniform(0.05, 0.075))
    return finish(bm, "coal")


def periodic_noise(size, alpha, seed):
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(size)[:, None] ** 2 + np.fft.fftfreq(size)[None, :] ** 2
    f[0, 0] = 1
    spectrum = (rng.normal(size=(size, size)) + 1j * rng.normal(size=(size, size))) / f ** (alpha / 2)
    spectrum[0, 0] = 0
    field = np.fft.ifft2(spectrum).real
    return (field - field.min()) / (field.max() - field.min())


def paint(group):
    if group == "stone":
        n = 512
        blotch, grit = periodic_noise(n, 2.2, 1), periodic_noise(n, 0.8, 2)
        fleck = (periodic_noise(n, 1.4, 9) > 0.80) * 1.0
        return (np.array([186, 176, 158]) * (0.86 + 0.28 * blotch[..., None])
                + (grit[..., None] - 0.5) * 26 - fleck[..., None] * 28)
    n = 256
    if group == "wood":
        streak = np.tile(periodic_noise(n, 1.2, 5)[:1, :], (n, 1)) * 0.5 + periodic_noise(n, 2.0, 6) * 0.5
        col = (np.array([182, 104, 46]) * (0.78 + 0.4 * streak[..., None])
               + (periodic_noise(n, 1.0, 4)[..., None] - 0.5) * 18)
        col[:, ::64, :] *= 0.7
        return col
    if group == "iron":
        wear = (periodic_noise(n, 1.2, 8) > 0.78) * 1.0
        return (np.array([78, 104, 72]) * (0.8 + 0.4 * periodic_noise(n, 2.0, 7)[..., None])
                + wear[..., None] * np.array([40, 34, 12]))
    n = 128
    return np.array([30, 30, 34]) * (0.7 + 0.9 * periodic_noise(n, 1.0, 10)[..., None])


def write_texture(group):
    pixels = np.clip(paint(group), 0, 255) / 255.0
    h, w = pixels.shape[:2]
    rgba = np.concatenate([pixels, np.ones((h, w, 1))], axis=2)
    path = os.path.join(ASSETS, "%s_%s.png" % (NAME, group))
    image = bpy.data.images.new("%s_%s" % (NAME, group), w, h, alpha=False)
    image.colorspace_settings.name = "Non-Color"
    image.pixels = rgba.ravel().tolist()
    image.filepath_raw = path
    image.file_format = "PNG"
    image.save()
    return image


def assemble():
    parts = [build_stone(), build_iron(), build_wood(), build_coal()]
    groups = ["stone", "iron", "wood", "coal"]
    for obj, group in zip(parts, groups):
        material = bpy.data.materials.new(group)
        material.use_nodes = True
        node = material.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = write_texture(group)
        material.node_tree.links.new(node.outputs["Color"],
                                     material.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
        obj.data.materials.append(material)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = NAME

    bpy.ops.object.mode_set(mode="EDIT")
    for i in range(len(obj.material_slots)):
        bpy.ops.mesh.select_all(action="DESELECT")
        obj.active_material_index = i
        bpy.ops.object.material_slot_select()
        bpy.ops.uv.cube_project(cube_size=0.45)
    bpy.ops.object.mode_set(mode="OBJECT")

    k = HEIGHT / obj.dimensions.z
    lowest = min(v.co.z for v in obj.data.vertices)
    obj.scale = (k, k, k)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location.z -= lowest * k
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    return obj, k, lowest


def colliders(k, lowest):
    def z(raw):
        return (raw - lowest) * k
    boxes = []
    bowl_lo, bowl_hi = z(Z_BASE), z(Z_TOP)
    boxes.append(((0.0, 0.0, (bowl_lo + bowl_hi) / 2), (1.50, 1.50, bowl_hi - bowl_lo)))
    leg_hi = z(LEG_TOP[1])
    mid_r = (LEG_TOP[0] + LEG_BOT[0]) / 2 * k
    for a in LEG_ANGLES:
        c = pol(mid_r, a, leg_hi / 2)
        boxes.append(((c.x, c.y, c.z), (0.30, 0.30, leg_hi)))
    return boxes


def write_col(path, boxes):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# box  centre x y z  size x y z  qx qy qz qw\n")
        for (cx, cy, cz), (sx, sy, sz) in boxes:
            fh.write("box %.3f %.3f %.3f %.3f %.3f %.3f 0.0000 0.0000 0.0000 1.0000\n"
                     % (-cx, cz, cy, sx, sz, sy))


def check_col(obj_path, col_path):
    verts = []
    with open(obj_path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("v "):
                verts.append(tuple(float(n) for n in line.split()[1:4]))
    failed = False
    with open(col_path, encoding="utf-8") as fh:
        index = 0
        for line in fh:
            if not line.startswith("box"):
                continue
            n = [float(t) for t in line.split()[1:]]
            centre, size = n[0:3], n[3:6]
            hits = sum(1 for v in verts
                       if -0.05 <= max(abs(v[i] - centre[i]) - size[i] / 2.0 for i in range(3)) <= 0.05)
            print("COL_CHECK box %d  %d vertices on its surface" % (index, hits))
            failed = failed or hits < 8
            index += 1
    if failed:
        raise SystemExit("FUNNEL_FAIL a collision box does not match the mesh")


def shoot_icon(obj, path):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "TEXTURE"
    scene.display.render_aa = "8"
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = 128
    camera = bpy.data.objects.new("icon_cam", bpy.data.cameras.new("icon_cam"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(obj.dimensions) * 1.15
    centre = Vector((0, 0, obj.dimensions.z / 2))
    az, el = math.radians(35), math.radians(20)
    view = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    camera.location = centre + view * 20
    camera.rotation_euler = (-view).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj, k, lowest = assemble()
    tris = len(obj.data.polygons)
    size = tuple(round(v, 2) for v in obj.dimensions)
    print("FUNNEL_OK faces=%d size=%s groups=%s" % (tris, size, [m.name for m in obj.data.materials]))
    if tris > TRI_CAP:
        raise SystemExit("FUNNEL_FAIL over the %d triangle cap" % TRI_CAP)

    obj_path = os.path.join(ASSETS, NAME + ".obj")
    col_path = os.path.join(ASSETS, NAME + ".col")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.wm.obj_export(filepath=obj_path, export_selected_objects=True, export_materials=True,
                          forward_axis="Z", up_axis="Y", path_mode="STRIP")
    write_col(col_path, colliders(k, lowest))
    check_col(obj_path, col_path)
    shoot_icon(obj, os.path.join(ASSETS, NAME + "_icon.png"))


main()
