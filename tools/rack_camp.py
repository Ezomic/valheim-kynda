"""
The Woodrack: vanilla's logs cut to billets, split and stacked ends-out.

    blender --background --python tools/rack_camp.py

Round one used the wood_stack pile verbatim - a replica of a buildable piece, rejected.
Round two restacked its full logs - and a charcoal kiln does not take full logs. Kilns
burn BILLETS: wood cut short and split to dry, which is also what Valheim's own kiln
eats (the Wood item is a short round). So this cuts the pile's logs into ~55cm billets,
halves a share of them bark-up, and stacks them in courses with their ends facing
front - the firewood wall every woodshed shows the road.

The paint survives all of it. The billets are windows cut from vanilla's own painted
logs, so their bark is vanilla's bark; a billet that includes an original log end keeps
its hand-painted disc outright, and the faces my cuts create are capped, grouped
wood_end, and aimed at that same painted disc by the machinery the old rack already
had. Split faces point down, where nobody looks.

Ends-front also settles which way the piece faces: the wall of discs is the front.

Axes: the rip stays in Unity's frame - X across, Y UP, Z deep - as established.
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
RIP = "E:/Repositories/valheim/own-profile/BepInEx/rips/log__1_/log__1_.obj"
WALL_RIP = "E:/Repositories/valheim/own-profile/BepInEx/rips/woodwall/woodwall.obj"
ROOF_RIP = "E:/Repositories/valheim/own-profile/BepInEx/rips/wood_roof/wood_roof.obj"

NAME = "kynda_rack_camp"


def material(name):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    return mat


def load_log():
    """The item log, as ripped. One mesh, closed, ends painted."""
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=RIP, forward_axis="Z", up_axis="Y")
    fresh = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    log = fresh[0]
    for extra in fresh[1:]:
        bpy.data.objects.remove(extra, do_unlink=True)
    log.data.materials.clear()
    log.data.materials.append(material("wood"))
    for poly in log.data.polygons:
        poly.material_index = 0
    return log


def load_rip_parts(path, groups):
    """Vanilla parts, verbatim: import a rip and keep the named New/high pieces,
    each assigned to a skin group. `groups` is a list of (name-prefix, group)
    pairs, first match wins. Returns the kept objects, in this script's y-up
    working frame with all transforms baked - the importer stores its axis
    conversion in the object matrix over raw file coordinates, so bake first,
    then rotate -90 about x (a rotation, not a swap: winding survives)."""
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis="Z", up_axis="Y")
    fresh = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]

    bpy.ops.object.select_all(action="DESELECT")
    for o in fresh:
        o.select_set(True)
    bpy.context.view_layer.objects.active = fresh[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    kept = []
    for o in fresh:
        grp = None
        for prefix, g in groups:
            if o.name.startswith(prefix):
                grp = g
                break
        if grp is None:
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        for v in o.data.vertices:
            v.co.y, v.co.z = v.co.z, -v.co.y
        o.data.materials.clear()
        o.data.materials.append(material(grp))
        for poly in o.data.polygons:
            poly.material_index = 0
        kept.append(o)
    return kept


def shear_top(objs, y_cut):
    """The wall-top shear, on placed vanilla parts: every vertex above the cut
    rises with depth by the roof pitch. Per vertex, so plank tops at different
    depths form the slope with no steps, and a rail simply tilts."""
    for o in objs:
        for v in o.data.vertices:
            if v.co.y > y_cut:
                v.co.y += SLOPE * (v.co.z - SLOPE_Z0)


def span(obj):
    lo = [min((obj.matrix_world @ Vector(c))[i] for c in obj.bound_box) for i in range(3)]
    hi = [max((obj.matrix_world @ Vector(c))[i] for c in obj.bound_box) for i in range(3)]
    return lo, hi


def bisect(obj, axis, at, keep_positive, fill):
    """One plane cut. Kerf paid for the semantics: "outer" is the side the plane
    normal points at, so keeping the positive side means clearing INNER."""
    normal = [(1,0,0),(0,1,0),(0,0,1)][axis]
    co = [0.0, 0.0, 0.0]; co[axis] = at
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.bisect(plane_co=co, plane_no=normal,
                        clear_inner=keep_positive, clear_outer=not keep_positive,
                        use_fill=fill)
    bpy.ops.object.mode_set(mode="OBJECT")


def billet(log, index, length=0.56):
    """
    A billet cut from a full log: orient the long axis to Z, take a window of it, cap
    the cuts. The window slides along the log per index, so different billets carry
    different stretches of bark and some keep an original painted end.
    """
    lo, hi = span(log)
    dims = [hi[i] - lo[i] for i in range(3)]
    longest = dims.index(max(dims))
    if longest == 0:
        log.rotation_euler.y = math.radians(90.0)
    elif longest == 1:
        log.rotation_euler.x = math.radians(90.0)
    bpy.ops.object.select_all(action="DESELECT")
    log.select_set(True)
    bpy.context.view_layer.objects.active = log
    bpy.ops.object.transform_apply(rotation=True)

    lo, hi = span(log)
    full = hi[2] - lo[2]
    slide = ((index * 29) % 7) / 7.0
    a = lo[2] + slide * max(full - length, 0.0)
    b = min(a + length, hi[2])

    # An end cut only where the window does not already end at the log's own painted
    # end - cutting flush would shave the disc off for nothing. fill=False: the filled
    # cap came out as a 16-gon, and a billet whose file was PROVABLY correct - winding
    # computed outward from the shipped OBJ - still rendered with one end missing in
    # game. Whatever the game side dislikes about that polygon, the cure is to stop
    # shipping exotic geometry: the caps below are hand-built triangle fans, the most
    # boring mesh there is.
    cut_planes = []
    if a > lo[2] + 0.01:
        bisect(log, 2, a, True, False)
        cut_planes.append((a, -1.0))
    if b < hi[2] - 0.01:
        bisect(log, 2, b, False, False)
        cut_planes.append((b, 1.0))

    # Cap each open cut with an explicit fan: boundary verts at the cut plane,
    # ordered by angle, a centre vertex, triangles wound so the face points out of
    # the billet. Nothing here is inferred - the winding is written by hand.
    import bmesh
    for plane_z, outward in cut_planes:
        bm = bmesh.new()
        bm.from_mesh(log.data)
        bm.verts.ensure_lookup_table()
        rim = [v for v in bm.verts if abs(v.co.z - plane_z) < 0.005]
        if len(rim) >= 3:
            uv_layer = bm.loops.layers.uv.active
            cx0 = sum(v.co.x for v in rim) / len(rim)
            cy0 = sum(v.co.y for v in rim) / len(rim)
            d = max(max(abs(v.co.x - cx0), abs(v.co.y - cy0)) for v in rim) * 2.0 + 1e-5
            centre = bm.verts.new((cx0, cy0, plane_z))
            rim.sort(key=lambda v: math.atan2(v.co.y - cy0, v.co.x - cx0))
            for i in range(len(rim)):
                v1, v2 = rim[i], rim[(i + 1) % len(rim)]
                order = (centre, v2, v1) if outward > 0 else (centre, v1, v2)
                try:
                    face = bm.faces.new(order)
                except ValueError:
                    continue
                # The disc UVs are baked HERE, onto wood_pile's painted end-grain patch
                # at (0.600, 0.636) 0.161 square - the same patch the log's own painted
                # ends use. That removes the wood_end group entirely: one submesh, one
                # material, and nowhere left for a submesh to silently not render,
                # which is what every cap did through three winding theories.
                for loop in face.loops:
                    v = loop.vert.co
                    loop[uv_layer].uv.x = 0.600 + 0.161 * (0.5 + (v.x - cx0) / d)
                    loop[uv_layer].uv.y = 0.636 + 0.161 * (0.5 + (v.y - cy0) / d)
            bm.to_mesh(log.data)
        bm.free()

    # No wood_end classification. The log's own painted ends already carry vanilla's
    # disc UVs and :keep leaves them alone; the authored fans baked theirs above. The
    # previous version reassigned every end face into a wood_end submesh - and that
    # submesh, whatever the reason, never reached the screen.
    return log


def place(obj, x, y, z):
    lo, hi = span(obj)
    obj.location.x += x - (lo[0]+hi[0])/2
    obj.location.y += y - (lo[1]+hi[1])/2
    obj.location.z += z - (lo[2]+hi[2])/2


SLOPE = 0.509           # vanilla's own pitch, measured off wood_roof's understraw
                        # plane (2:1, but measured rather than recited)
SLOPE_Z0 = -0.62        # the front wall line; shear is zero here, full at the back


# The painted panels, measured off the rips (tools note: largest-face UV rects).
# Vanilla does not tile these sheets - it paints a FACE and stretches it over the
# geometry it was made for, so a cube projection tiled across them samples patch
# borders and neighbours: that was the "texture in the wrong place". Each rect here
# is (u0, u1, v0, v1, metres-per-u-span, metres-per-v-span): the log wall paints a
# 1m-tall, 2m-long course; the darkwood beam a 0.2m-wide, 1m-long side.
PANELS = {
    # woodwall is full-bleed planks; only the sill still goes through frame_box
    "frame": (0.0, 1.0, 0.0, 1.0, 2.0, 2.0),
}


def frame_box(size, location, rot_x=0.0, yaw=0.0, mat="frame", shear=None,
              panel_off=(0.0, 0.0), cut_y=None):
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

    # An interior cut, not a stack: two boxes meeting put two beveled edges at the
    # course line and the groove caught light as a split no texture could hide (a
    # ledger pole hid it and was rejected). One box bisected keeps the surface a
    # single continuous plane - no bevel at the cut, identical normals both sides -
    # so the only seam left is the painted band's own tiling edge, which is the
    # seam vanilla's stacked walls show.
    if cut_y is not None:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.bisect(plane_co=(0.0, cut_y, 0.0), plane_no=(0.0, 1.0, 0.0),
                            clear_inner=False, clear_outer=False, use_fill=False)
        bpy.ops.object.mode_set(mode="OBJECT")

    # The slope, as a SHEAR rather than a rotation: wall tops and the whole roof
    # move by the same formula, so the contact is flush by construction.
    if shear:
        mesh = obj.data
        y_cut = (location[1] + size[1] * 0.2) if shear == "top" else -1e9
        for v in mesh.vertices:
            wy = v.co.y * size[1] + location[1]
            wz = v.co.z * size[2] + location[2]
            if wy > y_cut:
                v.co.y += (SLOPE * (wz - SLOPE_Z0)) / size[1]

    # Panel mapping, not projection: every face lands once inside its material's
    # painted rect, centred, at the density vanilla painted it at - compressed only
    # when the face outgrows the panel. A wall face therefore looks like a vanilla
    # wall panel, which is the whole fix: tiling these atlas sheets sampled across
    # patch borders and read as "texture in the wrong place".
    u0, u1, v0, v1, pu, pv = PANELS[mat]
    mesh = obj.data
    layer = mesh.uv_layers.active.data
    for poly in mesh.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        # Which world axes feed u (across the panel) and v (along it), per face
        # orientation. Walls: u is height, v runs along the wall. Roof boards lie
        # flat: u is across the board, v down the slope.
        if mat == "roof":
            au, av = ((1, 2), (0, 2), (1, 0))[ax]
        else:
            au, av = ((1, 2), (2, 0), (1, 0))[ax] if ax != 2 else (1, 0)
        pts = []
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            w = (co.x * size[0] + location[0],
                 co.y * size[1] + location[1],
                 co.z * size[2] + location[2])
            pts.append((li, w[au], w[av]))
        lou = min(t[1] for t in pts); hiu = max(t[1] for t in pts)
        lov = min(t[2] for t in pts); hiv = max(t[2] for t in pts)
        mu, mv = (lou + hiu) / 2.0, (lov + hiv) / 2.0
        fu = min(1.0, pu / max(hiu - lou, 1e-5)) / pu
        fv = min(1.0, pv / max(hiv - lov, 1e-5)) / pv
        # Tall wall faces span the FULL band, never a centred window of it. The band
        # is painted to tile at its edges - vanilla stacks these walls - so a centred
        # 86% window cut every course mid-log and each wall read as split in two.
        # 16% fatter logs are invisible; broken tiling edges are not.
        if mat == "frame" and ax != 1:
            fu = 1.0 / max(hiu - lou, 1e-5)
        # panel_off slides the sampled window inside the rect, in rect fractions,
        # so stacked parts of one material do not all read the same centred patch.
        for li, wu, wv in pts:
            layer[li].uv.x = (u0 + u1) / 2.0 + (wu - mu) * fu * (u1 - u0)                 + panel_off[0] * (u1 - u0)
            layer[li].uv.y = (v0 + v1) / 2.0 + (wv - mv) * fv * (v1 - v0)                 + panel_off[1] * (v1 - v0)

    obj.data.materials.clear()
    obj.data.materials.append(material(mat))
    for poly in obj.data.polygons:
        poly.material_index = 0
    return obj


def main():
    uv.clear_scene()
    # The wall of end discs, at last, and with nothing invented: each billet is a
    # copy of the item log squashed to a kiln length, its painted ends intact. The
    # long axis rides along Z so the sawn faces look out of the rack - the design the
    # split-wood request always wanted, reached the moment a closed painted source
    # existed to squash.
    # Full length, no squash - squashing compressed the bark and the log's wavy
    # silhouette until every billet read as a coin. The item log lies crosswise at
    # its native 2.07m, painted ends showing at the sides, and the rack is courses
    # of them: three deep, four high. Nothing is cut, scaled or authored.
    master = load_log()

    parts = []
    slots = []
    for layer_i, ly in enumerate((0.22, 0.56, 0.90, 1.24)):
        # Row depth is budgeted against the ROLLED envelope, not the resting one: a
        # rolled log swings its rectangular cross-section's corners to a 0.27 radius,
        # and the old rear row at 0.42 put corner bits through the back plate.
        for row, lz in enumerate((-0.30, 0.0, 0.30)):
            slots.append((ly, lz + (0.03 if layer_i % 2 else 0.0)))

    for index, (ly, lz) in enumerate(slots):
        b = master.copy()
        b.data = master.data.copy()
        bpy.context.collection.objects.link(b)

        wob = 0.93 + ((index * 17) % 11) / 100.0
        b.scale = (1.0, wob, wob)              # radial variety only; length untouched

        # Twelve copies of one log read as twelve copies unless the copy is disguised,
        # and the two disguises that cost nothing are the ones a real woodpile has:
        # every log ROLLED about its own length by a big pseudo-random angle - the
        # wavy silhouette lands differently each time - and every second log turned
        # end for end, so even the painted ends swap sides. Golden-angle stepping
        # keeps neighbouring rolls far apart; seeded, as ever, or the committed .obj
        # churns per rebuild.
        b.rotation_euler.x = math.radians((index * 137) % 360)
        if index % 2:
            b.rotation_euler.z = math.radians(180.0)
        bpy.ops.object.select_all(action="DESELECT")
        b.select_set(True)
        bpy.context.view_layer.objects.active = b
        bpy.ops.object.transform_apply(rotation=True, scale=True)

        place(b, 0.0, ly, lz)
        parts.append(b)

    bpy.data.objects.remove(master, do_unlink=True)

    # One coherent shed, five boxes that actually meet, and none of them jittered.
    # The earlier frame was posts, plates, rails and a sloped roof, each placed by
    # eye and wobbled like the logs - so nothing sat flush and the piece read as a
    # scaffold of loose boards. Structure is square by definition; wonkiness belongs
    # to the firewood. The walls share faces at the corners, the roof sits ON the
    # walls with an even overhang, and the sill ties the sides at the front.
    wall_h = 1.72

    # ---- the shell, from vanilla's own pieces. Every hand-built stand-in for
    # these - painted slabs, sheared boxes, stacked courses - was rejected in turn;
    # the woodwall and wood_roof rips carry the real geometry with the UVs their
    # paint was authored for, which is the Tun lesson applied to the whole shack.

    # The wood wall: four vertical planks and two rails, whole parts, no cuts.
    unit = load_rip_parts(WALL_RIP, [("New/high/plank", "frame")])
    lo, hi = None, None
    uplanks = [o for o in unit if max(v.co.y for v in o.data.vertices)
               - min(v.co.y for v in o.data.vertices) > 1.0]
    urails = [o for o in unit if o not in uplanks]

    # Normalise the unit so its battens sit on local +z - the face every wall
    # turns outward. The rip carries whatever yaw the piece was BUILT at, so this
    # is measured off the rails' proud side, never assumed. 180 about y: a
    # rotation, so the winding survives.
    p_z = sum(v.co.z for o in uplanks for v in o.data.vertices) / max(
        sum(len(o.data.vertices) for o in uplanks), 1)
    r_z = sum(v.co.z for o in urails for v in o.data.vertices) / max(
        sum(len(o.data.vertices) for o in urails), 1)
    if r_z < p_z:
        for o in unit:
            for v in o.data.vertices:
                v.co.x, v.co.z = -v.co.x, -v.co.z

    # The unit's own frame: ground it and centre its depth before any copy, or
    # every wall inherits whatever offsets the rip happened to stand at.
    u_ymin = min(v.co.y for o in unit for v in o.data.vertices)
    u_zmid = (min(v.co.z for o in unit for v in o.data.vertices)
              + max(v.co.z for o in unit for v in o.data.vertices)) / 2.0

    # Depth at 40%: the piece is 0.43m thick, built to be a house wall. Full
    # depth here put the firewood through its inner face and its outer face past
    # the roof; slimmed it reads as board-on-frame and everything clears.
    SZ = 0.4

    def wall_copy(src, sx, cx0, tx, tz, yaw):
        c = src.copy()
        c.data = src.data.copy()
        bpy.context.collection.objects.link(c)
        for v in c.data.vertices:
            x = (v.co.x - cx0) * sx
            y = (v.co.y - u_ymin) * 0.86
            z = (v.co.z - u_zmid) * SZ
            if yaw:
                # proper 90-degree rotations, mirror-free: +z faces outward on
                # both sides. (x,z)->(z,x) was tried and is a REFLECTION - it
                # turned one wall inside-out.
                x, z = z * yaw, -x * yaw
            v.co.x, v.co.y, v.co.z = x + tx, y, z + tz
        parts.append(c)
        return c

    wall_objs = []
    # Back wall: the full unit, widened to the shed, inner face clear of the logs.
    for src in unit:
        wall_objs.append(wall_copy(src, 1.135, 0.0, 0.0, 0.68, 0))
    # Side walls: three planks re-ranked to the shed's depth, plus both rails.
    for sx_wall in (-1.10, 1.10):
        yaw = -1 if sx_wall < 0 else 1
        for k, zc in enumerate((-0.413, 0.0, 0.413)):
            src = uplanks[k % len(uplanks)]
            cx = sum(v.co.x for v in src.data.vertices) / len(src.data.vertices)
            wall_objs.append(wall_copy(src, 0.827, cx, sx_wall, zc, yaw))
        for src in urails:
            cx = sum(v.co.x for v in src.data.vertices) / len(src.data.vertices)
            wall_objs.append(wall_copy(src, 0.62, cx, sx_wall, 0.0, yaw))
    for o in unit:
        bpy.data.objects.remove(o, do_unlink=True)

    # Slope the wall tops to the roof pitch, per vertex, after placement.
    shear_top(wall_objs, 1.15)

    # The real thatched roof 26: planks, crossbeam, understraw and the ragged
    # straw sheets, complete - so it is closed from below and behind, and the
    # alpha edge at the eave is vanilla's own. Uniform in depth and height (62%),
    # so the pitch survives; width stretched separately to the shed.
    roof_parts = load_rip_parts(ROOF_RIP, [
        ("New/high/understraw", "roof"),
        ("New/high/straw", "roofalpha"),
        ("New/high/plank", "frame"),
        ("New/high/crossbeam", "frame"),
    ])
    under = next(o for o in roof_parts if o.data.materials[0].name == "roof")
    us = under.data.vertices
    n = len(us)
    mz = sum(v.co.z for v in us) / n
    my = sum(v.co.y for v in us) / n
    b = sum((v.co.z - mz) * (v.co.y - my) for v in us) / max(
        sum((v.co.z - mz) ** 2 for v in us), 1e-9)
    if b < 0:
        for o in roof_parts:
            for v in o.data.vertices:
                v.co.x, v.co.z = -v.co.x, -v.co.z
    x_mid = (min(v.co.x for o in roof_parts for v in o.data.vertices)
             + max(v.co.x for o in roof_parts for v in o.data.vertices)) / 2.0
    for o in roof_parts:
        for v in o.data.vertices:
            v.co.x = (v.co.x - x_mid) * 1.149
            v.co.y *= 0.62
            v.co.z *= 0.62
    # Seat: back edge just past the back wall, underside plane through the wall
    # tops at the front line. The plane is re-fitted after scaling.
    mz = sum(v.co.z for v in us) / n
    my = sum(v.co.y for v in us) / n
    b2 = sum((v.co.z - mz) * (v.co.y - my) for v in us) / max(
        sum((v.co.z - mz) ** 2 for v in us), 1e-9)
    a2 = my - b2 * mz
    z_hi = max(v.co.z for o in roof_parts for v in o.data.vertices)
    dz = 0.80 - z_hi
    dy = 1.68 - (a2 + b2 * (-0.62 - dz))
    for o in roof_parts:
        for v in o.data.vertices:
            v.co.z += dz
            v.co.y += dy
        parts.append(o)

    # The understraw stops short of the back wall - vanilla's underside sheet is
    # shorter than its straw courses - and the shortfall read as a gap over the
    # backplate. Stretch its uphill edge to the roof's back edge, raising y with z
    # at the roof pitch so the sheet stays in its plane and lands flush on the
    # wall-top line instead of kinking.
    uz = [v.co.z for v in under.data.vertices]
    z_lo_u, z_hi_u = min(uz), max(uz)
    k = (0.79 - z_lo_u) / max(z_hi_u - z_lo_u, 1e-5)
    for v in under.data.vertices:
        stretched = z_lo_u + (v.co.z - z_lo_u) * k
        v.co.y += SLOPE * (stretched - v.co.z)
        v.co.z = stretched

    parts.append(frame_box((2.27, 0.14, 0.10), (0.0, 0.07, -0.57)))

    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    rack = bpy.context.active_object
    rack.name = NAME

    # The calibrated stand-up, measured off two artefacts rather than theorised: the
    # known-good Tun's FILE carries height in Y, and this script's collider (written in
    # blender coordinates) showed height in blender-Y while the exported file had it in
    # Z - so the exporter swaps Y and Z on the way out. Rotating the finished piece
    # +90 about X moves the stack's height into blender-Z, which the exporter then
    # writes as the file's Y. Up, in game.
    rack.rotation_euler.x = math.radians(90.0)
    bpy.ops.object.transform_apply(rotation=True)
    _lo = min((rack.matrix_world @ Vector(c)).z for c in rack.bound_box)
    rack.location.z += -_lo
    bpy.ops.object.transform_apply(location=True)

    rack.data.calc_loop_triangles()
    tris = len(rack.data.loop_triangles)

    # Two boxes, written in UNITY space (y up, z = NEGATED working z - the export
    # chain flips it; the shed front sits at unity +0.62). The body box wraps walls
    # and firewood. The roof box is ROTATED to lie along the pitch: one axis-aligned
    # box over a sloped roof holds your feet at its highest corner, which read as
    # "it looks like I can jump on it but I can't". Rotation about x by +27 degrees
    # (atan of the 0.509 pitch), quaternion (sin 13.5, 0, 0, cos 13.5); the parser
    # gives each rotated box its own child transform.
    with open(os.path.join(ASSETS, NAME + ".col"), "w") as col:
        col.write("# box  centre x y z  size x y z  qx qy qz qw\n")
        col.write("box 0 0.86 -0.07 2.47 1.72 1.39 0 0 0 1\n")
        col.write("box 0 2.09 0.115 2.55 0.30 2.05 0.2334 0 0 0.9724\n")

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

    spans = [0.0] * 3
    lo_v = [1e9] * 3
    for line in open(os.path.join(ASSETS, NAME + ".obj")):
        if line.startswith("v "):
            v = [float(x) for x in line.split()[1:4]]
            for i in range(3):
                lo_v[i] = min(lo_v[i], v[i])
                spans[i] = max(spans[i], v[i])
    spans = [spans[i] - lo_v[i] for i in range(3)]
    worst = 0
    for line in open(os.path.join(ASSETS, NAME + ".obj")):
        if line.startswith("f "):
            worst = max(worst, len(line.split()) - 1)
    assert worst <= 4, "an ngon reached the export (%d corners) - see the cap story" % worst
    assert spans[1] > spans[2] and abs(lo_v[1]) < 0.05, (
        "exported file is not Y-up-grounded: spans %s min-y %.2f" % (spans, lo_v[1]))

    print("  %s: %d tris, file y-up OK (%.2f x %.2f x %.2f)"
          % (NAME, tris, spans[0], spans[1], spans[2]))


main()
