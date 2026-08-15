using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;

namespace Stoker
{
    /// <summary>
    /// Puts a hand-modelled mesh onto a cloned prefab, in place of the donor's own look.
    ///
    /// The surfaces come from Skins, which lends each material group a real material off a
    /// vanilla prefab and then fits our UVs into that material's slice of its atlas.
    /// </summary>
    internal static class UpgradeModel
    {
        /// <summary>
        /// Swaps the donor's visuals for ours. Returns false if the model is missing, in
        /// which case the caller keeps the donor's look rather than shipping an invisible
        /// piece.
        /// </summary>
        public static bool Apply(GameObject prefab, string modelFile,
                                 IDictionary<string, string> skins)
        {
            var dir = Path.GetDirectoryName(typeof(UpgradeModel).Assembly.Location);
            if (string.IsNullOrWhiteSpace(modelFile)) return false;

            var model = ObjMesh.Load(Path.Combine(dir, modelFile));

            if (model == null || model.Mesh == null)
            {
                StokerPlugin.Log.LogWarning(
                    "No " + modelFile + " beside the dll - falling back to the donor's look.");
                return false;
            }

            // The donor's renderers go, but its ZNetView, Piece and WearNTear stay: those
            // are the machinery that makes it a buildable, damageable, networked object,
            // and rebuilding them by hand is exactly the work cloning avoids.
            // Null-checked: destroying a renderer's GameObject takes its children with it, and
            // GetComponentsInChildren lists parents first, so a nested renderer is already
            // destroyed when the loop reaches it and asking it for its gameObject throws.
            foreach (var renderer in prefab.GetComponentsInChildren<MeshRenderer>(true))
            {
                if (renderer == null) continue;
                UnityEngine.Object.DestroyImmediate(renderer.gameObject);
            }

            var visual = new GameObject("upgrade_visual");
            visual.transform.SetParent(prefab.transform, false);

            var filter = visual.AddComponent<MeshFilter>();
            filter.sharedMesh = model.Mesh;

            var meshRenderer = visual.AddComponent<MeshRenderer>();
            meshRenderer.sharedMaterials = Skins.Skin(model.Groups, skins);

            // Without this the mesh samples the whole texture sheet instead of the one
            // tile its material actually occupies, and picks up the neighbouring tiles.
            Skins.Remap(model.Mesh, model.Groups, skins);

            // The collision sidecar sits beside the model and shares its name, so a model
            // swap in config brings the right boxes with it rather than leaving the last
            // model's shape behind.
            ReplaceColliders(prefab, Path.Combine(dir,
                Path.GetFileNameWithoutExtension(modelFile) + ".col"));

            StokerPlugin.Log.LogInfo(string.Format(
                "{0}: {1} verts, {2} tris, groups [{3}].",
                modelFile, model.Mesh.vertexCount, model.Mesh.triangles.Length / 3,
                string.Join(", ", model.Groups)));

            return true;
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
                    "No " + Path.GetFileName(path) + " beside the dll - keeping the donor's "
                    + "collision.");
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
            var host = new GameObject("upgrade_collision");
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

            StokerPlugin.Log.LogInfo(
                Path.GetFileName(path) + ": " + boxes.Count + " collision boxes.");
        }
    }
}
