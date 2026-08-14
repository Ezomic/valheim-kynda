using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;

namespace Stoker
{
    /// <summary>
    /// Puts the hand-modelled hopper onto the cloned prefab, in place of the donor's own
    /// look.
    ///
    /// Nothing here paints anything. Each material group in the OBJ - wood, iron, stone -
    /// is skinned with a real material lifted off a vanilla prefab, so the piece is made of
    /// the game's own wood and the game's own iron rather than an approximation of them.
    /// That also sidesteps the trap of swapping _MainTex on a borrowed material, which
    /// keeps the donor's normal map and leaves the surface lit for a shape it no longer has.
    /// </summary>
    internal static class HopperModel
    {
        /// <summary>Fallback only; the file is named in config so it can be swapped live.</summary>
        private const string ModelFile = "stoker_hopper.obj";
        private const string ColliderFile = "stoker_hopper.col";

        /// <summary>Prefabs to lift each group's material from, best first.</summary>
        private static readonly Dictionary<string, string[]> Donors =
            new Dictionary<string, string[]>(StringComparer.OrdinalIgnoreCase)
            {
                { "wood",  new[] { "wood_wall", "wood_beam", "piece_chest_wood" } },
                { "iron",  new[] { "piece_artisanstation", "forge", "piece_cauldron" } },
                { "stone", new[] { "stone_wall_2x1", "piece_stonecutter", "smelter" } },
            };

        private static readonly Dictionary<string, Material> Cache =
            new Dictionary<string, Material>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// Swaps the donor's visuals for ours. Returns false if the model is missing, in
        /// which case the caller keeps the donor's look rather than shipping an invisible
        /// piece.
        /// </summary>
        public static bool Apply(GameObject prefab)
        {
            var dir = Path.GetDirectoryName(typeof(HopperModel).Assembly.Location);
            var wanted = StokerConfig.HopperModelFile.Value;
            if (string.IsNullOrWhiteSpace(wanted)) wanted = ModelFile;

            var model = ObjMesh.Load(Path.Combine(dir, wanted));

            if (model == null || model.Mesh == null)
            {
                StokerPlugin.Log.LogWarning(
                    "No hopper model beside the dll - falling back to the donor's own look.");
                return false;
            }

            // The donor's renderers go, but its ZNetView, Piece and WearNTear stay: those
            // are the machinery that makes it a buildable, damageable, networked object,
            // and rebuilding them by hand is exactly the work cloning avoids.
            foreach (var renderer in prefab.GetComponentsInChildren<MeshRenderer>(true))
                UnityEngine.Object.DestroyImmediate(renderer.gameObject);

            var visual = new GameObject("hopper_visual");
            visual.transform.SetParent(prefab.transform, false);

            var filter = visual.AddComponent<MeshFilter>();
            filter.sharedMesh = model.Mesh;

            var meshRenderer = visual.AddComponent<MeshRenderer>();
            meshRenderer.sharedMaterials = Skins(model.Groups);

            ReplaceColliders(prefab, Path.Combine(dir, ColliderFile));

            StokerPlugin.Log.LogInfo(string.Format(
                "Hopper model loaded: {0} verts, {1} tris, groups [{2}].",
                model.Mesh.vertexCount, model.Mesh.triangles.Length / 3,
                string.Join(", ", model.Groups)));

            return true;
        }

        private static Material[] Skins(string[] groups)
        {
            var skins = new Material[groups.Length];

            for (var i = 0; i < groups.Length; i++)
            {
                skins[i] = Borrow(groups[i]);
                if (skins[i] == null)
                    StokerPlugin.Log.LogWarning(
                        "No material found for hopper group '" + groups[i] + "'.");
            }

            return skins;
        }

        private static Material Borrow(string group)
        {
            Material cached;
            if (Cache.TryGetValue(group, out cached)) return cached;

            string[] donors;
            if (!Donors.TryGetValue(group, out donors)) donors = Donors["wood"];

            foreach (var name in donors)
            {
                var donor = ZNetScene.instance.GetPrefab(name);
                if (donor == null) continue;

                foreach (var renderer in donor.GetComponentsInChildren<MeshRenderer>(true))
                {
                    var material = renderer.sharedMaterial;
                    if (material == null || material.shader == null) continue;

                    // A material with no albedo renders flat and grey, which looks like a
                    // bug rather than a choice.
                    if (!material.HasProperty("_MainTex") || material.GetTexture("_MainTex") == null)
                        continue;

                    Cache[group] = material;
                    StokerPlugin.Log.LogInfo(string.Format(
                        "Hopper '{0}' skinned with {1} from {2} (shader {3}).",
                        group, material.name, name, material.shader.name));
                    return material;
                }
            }

            Cache[group] = null;
            return null;
        }

        /// <summary>
        /// Boxes from the sidecar, replacing whatever shape the donor had. A barrel's
        /// capsule around a square bin leaves you bumping into air at the corners.
        /// </summary>
        private static void ReplaceColliders(GameObject prefab, string path)
        {
            if (!File.Exists(path))
            {
                StokerPlugin.Log.LogWarning(
                    "No collider file beside the dll - keeping the donor's collision.");
                return;
            }

            var boxes = new List<string[]>();
            foreach (var line in File.ReadAllLines(path))
            {
                var trimmed = line.Trim();
                if (trimmed.Length == 0 || trimmed.StartsWith("#")) continue;

                var parts = trimmed.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
                if (parts.Length >= 7 && parts[0] == "box") boxes.Add(parts);
            }

            if (boxes.Count == 0) return;

            foreach (var collider in prefab.GetComponentsInChildren<Collider>(true))
                UnityEngine.Object.DestroyImmediate(collider);

            var culture = CultureInfo.InvariantCulture;
            var host = new GameObject("hopper_collision");
            host.transform.SetParent(prefab.transform, false);

            foreach (var parts in boxes)
            {
                var box = host.AddComponent<BoxCollider>();
                box.center = new Vector3(
                    float.Parse(parts[1], culture),
                    float.Parse(parts[2], culture),
                    float.Parse(parts[3], culture));
                box.size = new Vector3(
                    float.Parse(parts[4], culture),
                    float.Parse(parts[5], culture),
                    float.Parse(parts[6], culture));
            }

            StokerPlugin.Log.LogInfo("Hopper collision: " + boxes.Count + " boxes.");
        }
    }
}
