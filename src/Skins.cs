using System;
using System.Collections.Generic;
using UnityEngine;

namespace Stoker
{
    /// <summary>
    /// Lends each material group a real material off a vanilla prefab.
    ///
    /// Nothing here paints anything. The meshes are ours and the surfaces are the game's,
    /// which is what keeps a hand-built model looking like it belongs - texel density,
    /// palette and weathering all come along because they are the game's own. It also
    /// sidesteps swapping _MainTex on a borrowed material, which keeps the donor's normal
    /// map and leaves the surface lit for a shape it no longer has.
    ///
    /// Brought back from Vaettir, which got it from Stow, which got it from here. What
    /// Stoker kept was the borrowing; what it lost along the way was the atlas measuring
    /// below - so its pieces have been sampling whole texture sheets rather than the one
    /// tile they were supposed to.
    /// </summary>
    internal static class Skins
    {
        /// <summary>
        /// Prefabs to lift each group's material from, best first, ordered by measurement
        /// rather than by guess.
        ///
        /// ore and coal earn their place from the trough, whose two bays are the entire
        /// point of it - one heaped with ore, one with coal. Falling back to wood, which
        /// is what an unlisted group used to do, made them two identical tubs of nothing.
        /// Ripping the build set showed
        /// vanilla splits into two texel-density families: structural blocks - beam, pole,
        /// door, floor - run 165 to 224 texels/m and use nearly their whole sheet, while
        /// props, piles and furniture run 24 to 54 off a tight rect. These pieces are
        /// props, so the second family is the one to borrow from.
        ///
        /// wood_wall used to lead this list and does not exist. A name that does not
        /// resolve is skipped in silence, so the wood group had been quietly falling
        /// through to wood_beam - a structural block whose material covers 96% of its
        /// sheet, and the single worst donor available at 119 texels/m against a target
        /// of about 30.
        /// </summary>
        private static readonly Dictionary<string, string[]> Donors =
            new Dictionary<string, string[]>(StringComparer.OrdinalIgnoreCase)
            {
                // 29 texels/m, one material, 468 triangles. wood_wall_log second because
                // it is round bark-on timber at 54 - the right surface for split billets
                // when the piece is mostly logs.
                { "wood",  new[] { "piece_chest_wood", "wood_wall_log", "darkwood_beam" } },
                { "iron",  new[] { "piece_artisanstation", "forge", "piece_cauldron" } },
                { "stone", new[] { "stone_wall_2x1", "piece_stonecutter", "smelter" } },
                { "coal",  new[] { "coal_pile", "Coal", "charcoal_kiln" } },
                { "ore",   new[] { "CopperOre", "TinOre", "IronOre" } },
            };

        private static readonly Dictionary<string, Material> Cache =
            new Dictionary<string, Material>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// Where in its texture each borrowed material actually lives.
        ///
        /// Valheim's piece textures are atlases: a material does not use the whole image,
        /// it uses a strip of one. UVs running 0..1 therefore sample the entire sheet and
        /// pick up whatever the neighbouring tiles happen to be.
        /// </summary>
        private static readonly Dictionary<string, Rect> Atlas =
            new Dictionary<string, Rect>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// The donor texture's width in pixels, which is half of what decides how coarse
        /// our surface ends up. Vanilla's are tiny - 64 and 128 mostly, 256 at the largest
        /// - so the same slice of sheet means very different things on different donors.
        /// </summary>
        private static readonly Dictionary<string, int> TexPx =
            new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// Dropped on both ObjectDB.Awake and CopyOtherDB - a local world arrives through
        /// the first, a server handing over its item list through the second. Held across
        /// either, these are references to prefabs that have been torn down.
        /// </summary>
        public static void Invalidate()
        {
            Cache.Clear();
            Atlas.Clear();
            TexPx.Clear();
            PropIndex.Forget();
        }

        /// <summary>
        /// The cache key. A group on its own is not enough once two pieces can ask for
        /// different donors for the same group - the woodrack wants round bark off
        /// wood_wall_log and the trough wants sawn planking off piece_chest_wood, and
        /// keying on "wood" alone would hand whichever asked second the other's material,
        /// its atlas rect and its texture size.
        /// </summary>
        private static string Key(string group, IDictionary<string, string> overrides)
        {
            string donor;
            if (overrides != null && overrides.TryGetValue(group, out donor)
                && !string.IsNullOrEmpty(donor))
                return group + "|" + donor;

            return group;
        }

        public static Material[] Skin(string[] groups, IDictionary<string, string> overrides)
        {
            var skins = new Material[groups.Length];
            for (var i = 0; i < groups.Length; i++) skins[i] = For(groups[i], overrides);
            return skins;
        }

        public static Material For(string group, IDictionary<string, string> overrides)
        {
            var key = Key(group, overrides);

            Material cached;
            if (Cache.TryGetValue(key, out cached)) return cached;

            string[] donors;
            string only;
            if (overrides != null && overrides.TryGetValue(group, out only)
                && !string.IsNullOrEmpty(only))
            {
                // Named explicitly, so it is the only candidate. Falling back to the
                // general list would silently hand back the material this piece asked
                // not to have, and the log would say it had been honoured.
                donors = new[] { only };
            }
            else if (!Donors.TryGetValue(group, out donors))
            {
                donors = Donors["wood"];
            }

            foreach (var name in donors)
            {
                // Via PropIndex rather than ZNetScene directly: many dressing prefabs
                // carry no ZNetView and so are invisible to ZNetScene however loaded.
                var donor = PropIndex.Find(name);
                if (donor == null) continue;

                foreach (var renderer in donor.GetComponentsInChildren<MeshRenderer>(true))
                {
                    var material = renderer.sharedMaterial;
                    if (material == null || material.shader == null) continue;

                    // A material with no albedo renders flat and grey, which looks like a
                    // bug rather than a choice.
                    if (!material.HasProperty("_MainTex")
                        || material.GetTexture("_MainTex") == null) continue;

                    Cache[key] = material;
                    Atlas[key] = UvRegion(renderer);
                    TexPx[key] = Mathf.Max(1, material.GetTexture("_MainTex").width);

                    StokerPlugin.Log.LogInfo(string.Format(
                        "'{0}' skinned with {1} from {2} (shader {3}), atlas {4}, {5}px.",
                        key, material.name, name, material.shader.name,
                        Atlas[key], TexPx[key]));
                    return material;
                }
            }

            StokerPlugin.Log.LogWarning("No material found for group '" + key + "'.");
            Cache[key] = null;
            return null;
        }

        /// <summary>
        /// The slice of texture one face of the donor uses.
        ///
        /// Deliberately one face, not the whole mesh. Measuring min/max across every vertex
        /// gives a rectangle spanning every tile the donor touches - for stone_wall_2x1
        /// that was 71% of the sheet - and squeezing our coordinates into that still walks
        /// across tile boundaries.
        ///
        /// The largest single triangle is used because area is a good proxy for "a plain
        /// wall face" rather than a trim detail, and a triangle cannot straddle two tiles
        /// without the donor itself looking wrong.
        /// </summary>
        private static Rect UvRegion(Renderer renderer)
        {
            var whole = new Rect(0f, 0f, 1f, 1f);

            var filter = renderer != null ? renderer.GetComponent<MeshFilter>() : null;
            var mesh = filter != null ? filter.sharedMesh : null;
            if (mesh == null) return whole;

            Vector2[] uv;
            int[] tris;
            try
            {
                // Imported meshes are frequently upload-only; reading them then throws.
                if (!mesh.isReadable) return whole;
                uv = mesh.uv;
                tris = mesh.triangles;
            }
            catch { return whole; }

            if (uv == null || uv.Length == 0 || tris == null || tris.Length < 3) return whole;

            var bestArea = 0f;
            var best = whole;

            for (var i = 0; i + 2 < tris.Length; i += 3)
            {
                var a = tris[i];
                var b = tris[i + 1];
                var c = tris[i + 2];
                if (a >= uv.Length || b >= uv.Length || c >= uv.Length) continue;

                var minX = Mathf.Min(uv[a].x, Mathf.Min(uv[b].x, uv[c].x));
                var maxX = Mathf.Max(uv[a].x, Mathf.Max(uv[b].x, uv[c].x));
                var minY = Mathf.Min(uv[a].y, Mathf.Min(uv[b].y, uv[c].y));
                var maxY = Mathf.Max(uv[a].y, Mathf.Max(uv[b].y, uv[c].y));

                var width = maxX - minX;
                var height = maxY - minY;

                // A face that itself tiles past the sheet edge tells us nothing useful.
                if (width <= 0.005f || height <= 0.005f) continue;
                if (width > 1f || height > 1f) continue;

                var area = width * height;
                if (area <= bestArea) continue;

                bestArea = area;
                best = new Rect(minX, minY, width, height);
            }

            return bestArea > 0f ? best : whole;
        }

        /// <summary>
        /// Places each submesh's UVs inside its material's slice of the atlas, at a texel
        /// density chosen rather than inherited.
        ///
        /// This used to stretch the group's UVs to fill the rect, which made density an
        /// accident of two things nobody picked: how big the donor's slice happened to be
        /// and how big our model happened to be. Measured in game that gave 119 texels per
        /// metre on wood, 70 on iron and 11 on stone - an eleven-fold spread inside one
        /// piece, against a vanilla range of 24 to 54.
        ///
        /// Our exported UVs are already in metres, because the Blender pass cube-projects
        /// at a cube size of 1. So the wanted scale is simply target-texels divided by the
        /// donor's texture width, and the only complication is that the result has to fit
        /// the rect.
        ///
        /// Clamped, never wrapped. Repeat() here was the bug Stow paid for: it wraps per
        /// vertex, so a face crossing 1.0 got vertices at 0.9 and 0.2 and the GPU
        /// interpolated backwards across the whole tile between them - smeared diagonal
        /// banding that made a square model look crooked. That is also why a group too
        /// large for its rect is scaled down to fit rather than tiled: coarser than asked
        /// for, but continuous.
        /// </summary>
        public static void Remap(Mesh mesh, string[] groups, IDictionary<string, string> overrides)
        {
            if (mesh == null || groups == null) return;

            var uv = mesh.uv;
            if (uv == null || uv.Length == 0) return;

            var count = Mathf.Min(groups.Length, mesh.subMeshCount);
            var target = Mathf.Max(1f, StokerConfig.TexelsPerMetre.Value);

            // A vertex on the seam between two groups appears in both submeshes, and
            // mapping it twice would place it relative to an already-placed position.
            var done = new bool[uv.Length];

            for (var i = 0; i < count; i++)
            {
                var key = Key(groups[i], overrides);

                Rect rect;
                int px;
                if (!Atlas.TryGetValue(key, out rect)) continue;
                if (!TexPx.TryGetValue(key, out px) || px <= 0) continue;

                var indices = mesh.GetTriangles(i);
                if (indices.Length == 0) continue;

                // The group's own extent, in metres. Per group rather than per mesh: a
                // handful of small stone footings and a metre of timber want different
                // scales to land on the same density, which is the whole point.
                var min = new Vector2(float.MaxValue, float.MaxValue);
                var max = new Vector2(float.MinValue, float.MinValue);
                foreach (var index in indices)
                {
                    if (index < 0 || index >= uv.Length) continue;
                    min = Vector2.Min(min, uv[index]);
                    max = Vector2.Max(max, uv[index]);
                }

                var span = max - min;
                if (span.x <= 0f || span.y <= 0f) continue;

                // Wanted, then reduced until it fits. Uniform on both axes so the texture
                // is not stretched in one direction, which reads as smeared grain.
                var scale = target / px;
                scale = Mathf.Min(scale, rect.width / span.x);
                scale = Mathf.Min(scale, rect.height / span.y);

                // Centred in the rect, so a group that does fit is sampling the middle of
                // the tile rather than pressed against its edge where the neighbour bleeds.
                var centre = (min + max) * 0.5f;
                var offset = new Vector2(rect.x + rect.width * 0.5f, rect.y + rect.height * 0.5f)
                             - centre * scale;

                foreach (var index in indices)
                {
                    if (index < 0 || index >= uv.Length || done[index]) continue;
                    done[index] = true;

                    uv[index] = new Vector2(
                        Mathf.Clamp(uv[index].x * scale + offset.x, rect.xMin, rect.xMax),
                        Mathf.Clamp(uv[index].y * scale + offset.y, rect.yMin, rect.yMax));
                }

                StokerPlugin.Log.LogInfo(string.Format(
                    "'{0}' laid out at {1:0} texels/m (wanted {2:0}), {3:0.00}x{4:0.00}m in "
                    + "a {5:0.000}x{6:0.000} rect.",
                    key, scale * px, target, span.x, span.y, rect.width, rect.height));
            }

            mesh.uv = uv;
        }
    }
}
