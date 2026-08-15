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
        /// Prefabs to lift each group's material from, best first.
        ///
        /// ore and coal earn their place from the trough, whose two bays are the entire
        /// point of it - one heaped with ore, one with coal. Falling back to wood, which
        /// is what an unlisted group used to do, made them two identical tubs of nothing.
        /// </summary>
        private static readonly Dictionary<string, string[]> Donors =
            new Dictionary<string, string[]>(StringComparer.OrdinalIgnoreCase)
            {
                { "wood",  new[] { "wood_wall", "wood_beam", "piece_chest_wood" } },
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
        /// Dropped on both ObjectDB.Awake and CopyOtherDB - a local world arrives through
        /// the first, a server handing over its item list through the second. Held across
        /// either, these are references to prefabs that have been torn down.
        /// </summary>
        public static void Invalidate()
        {
            Cache.Clear();
            Atlas.Clear();
            PropIndex.Forget();
        }

        public static Material[] Skin(string[] groups)
        {
            var skins = new Material[groups.Length];
            for (var i = 0; i < groups.Length; i++) skins[i] = For(groups[i]);
            return skins;
        }

        public static Material For(string group)
        {
            Material cached;
            if (Cache.TryGetValue(group, out cached)) return cached;

            string[] donors;
            if (!Donors.TryGetValue(group, out donors)) donors = Donors["wood"];

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

                    Cache[group] = material;
                    Atlas[group] = UvRegion(renderer);

                    StokerPlugin.Log.LogInfo(string.Format(
                        "'{0}' skinned with {1} from {2} (shader {3}), atlas {4}.",
                        group, material.name, name, material.shader.name, Atlas[group]));
                    return material;
                }
            }

            StokerPlugin.Log.LogWarning("No material found for group '" + group + "'.");
            Cache[group] = null;
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
        /// Squeezes each submesh's UVs into its material's slice of the atlas.
        ///
        /// Clamped, never wrapped. Repeat() here was the bug Stow paid for: it wraps per
        /// vertex, so a face crossing 1.0 got vertices at 0.9 and 0.2 and the GPU
        /// interpolated backwards across the whole tile between them - smeared diagonal
        /// banding that made a square model look crooked.
        /// </summary>
        public static void Remap(Mesh mesh, string[] groups)
        {
            if (mesh == null || groups == null) return;

            var uv = mesh.uv;
            if (uv == null || uv.Length == 0) return;

            var count = Mathf.Min(groups.Length, mesh.subMeshCount);

            // A vertex on the seam between two groups appears in both submeshes, and
            // mapping it twice would squeeze it into a rectangle inside a rectangle.
            var done = new bool[uv.Length];

            for (var i = 0; i < count; i++)
            {
                Rect rect;
                if (!Atlas.TryGetValue(groups[i], out rect)) continue;
                if (rect.width >= 0.999f && rect.height >= 0.999f) continue;

                foreach (var index in mesh.GetTriangles(i))
                {
                    if (index < 0 || index >= uv.Length || done[index]) continue;
                    done[index] = true;

                    uv[index] = new Vector2(
                        rect.x + Mathf.Clamp01(uv[index].x) * rect.width,
                        rect.y + Mathf.Clamp01(uv[index].y) * rect.height);
                }
            }

            mesh.uv = uv;
        }
    }
}
