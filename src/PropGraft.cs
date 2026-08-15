using System;
using System.Collections.Generic;
using UnityEngine;

namespace Stoker
{
    /// <summary>
    /// Borrows the *look* of a vanilla prop and puts it on our piece.
    ///
    /// Seven hand-built models in and none of them looked like the game. Assembling
    /// boxes and cones procedurally gets you something recognisable and never something
    /// good, whereas the game already ships crates, sacks, baskets and barrels that a
    /// human modelled. Grafting one of those on is not a shortcut past the art problem,
    /// it is the answer to it: the texel density, the palette and the silhouette
    /// language all match, because they are the game's.
    ///
    /// Only the renderers come across. The piece keeps its own ZNetView, Piece and
    /// WearNTear - the machinery that makes it buildable and networked.
    /// </summary>
    internal static class PropGraft
    {
        /// <summary>
        /// Props worth trying, from the asset manifest. Not all of these are guaranteed
        /// to be loaded - the ones prefixed fi_vil_ are Ashlands village dressing and may
        /// only exist while such a location is streamed in - so the list is reported at
        /// startup rather than assumed.
        /// </summary>
        public static readonly string[] Candidates =
        {
            // Verified loaded in-game, not taken from the asset manifest. The first list
            // was manifest-derived and only 2 of 16 actually resolved: the manifest
            // catalogues what exists on disk, most of which lives in bundles that only
            // stream in with the location using them.
            "wood_stack",            // split logs, stacked - the kiln's own input
            "wood_fine_stack",
            "blackwood_stack",
            "wood_core_stack",
            "wood_yggdrasil_stack",
            "coal_pile",             // heaped charcoal - the smelter's fuel
            "stone_pile",
            "blackmarble_pile",
            "grausten_pile",
            "treasure_pile",
            "CargoCrate",
            "dvergrprops_crate",
            "dvergrprops_crate_long",
            "dvergrprops_crate_ashlands",
            "dvergrprops_barrel",
            "barrell",
            "bone_stack",
            "Cart",
        };


        private static Dictionary<string, GameObject> _index;

        /// <summary>
        /// Replaces the piece's visuals with the named prop's. Returns false if the prop
        /// cannot be found, so the caller can fall back to the hand-built model rather
        /// than shipping an invisible piece.
        /// </summary>
        public static bool Apply(GameObject prefab, string propName, float scale)
        {
            if (string.IsNullOrEmpty(propName)) return false;

            var prop = Find(propName);
            if (prop == null)
            {
                StokerPlugin.Log.LogWarning(
                    "Visual prop '" + propName + "' not found - falling back to the built model. "
                    + "Set LogVisualCandidates to see what is actually loadable.");
                return false;
            }

            // Null-checked: destroying a renderer's GameObject takes its children with it, and
            // GetComponentsInChildren lists parents first, so a nested renderer is already
            // destroyed when the loop reaches it and asking it for its gameObject throws. The
            // second loop is doubly exposed, since the first may already have taken the branch
            // a skinned renderer sat on.
            foreach (var renderer in prefab.GetComponentsInChildren<MeshRenderer>(true))
            {
                if (renderer == null) continue;
                UnityEngine.Object.DestroyImmediate(renderer.gameObject);
            }

            foreach (var skinned in prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (skinned == null) continue;
                UnityEngine.Object.DestroyImmediate(skinned.gameObject);
            }

            var previous = ZNetView.m_forceDisableInit;
            ZNetView.m_forceDisableInit = true;

            GameObject visual;
            try { visual = UnityEngine.Object.Instantiate(prop, prefab.transform); }
            finally { ZNetView.m_forceDisableInit = previous; }

            visual.name = "grafted_visual";
            visual.transform.localPosition = Vector3.zero;
            visual.transform.localRotation = Quaternion.identity;
            visual.transform.localScale = Vector3.one * Mathf.Max(0.05f, scale);

            Quieten(visual);

            StokerPlugin.Log.LogInfo("Hopper wearing '" + propName + "' at scale " + scale + ".");
            return true;
        }

        /// <summary>
        /// Strips everything that is not a picture.
        ///
        /// Particle systems are removed by name here rather than trusted to go with the
        /// scripts: the game's own Strip takes MonoBehaviours, colliders and ZNetView but
        /// leaves ParticleSystems running, which is how decorative props end up still
        /// emitting the sparkle that says "pick me up".
        /// </summary>
        private static void Quieten(GameObject visual)
        {
            foreach (var behaviour in visual.GetComponentsInChildren<MonoBehaviour>(true))
                UnityEngine.Object.DestroyImmediate(behaviour);

            foreach (var view in visual.GetComponentsInChildren<ZNetView>(true))
                UnityEngine.Object.DestroyImmediate(view);

            foreach (var collider in visual.GetComponentsInChildren<Collider>(true))
                UnityEngine.Object.DestroyImmediate(collider);

            foreach (var body in visual.GetComponentsInChildren<Rigidbody>(true))
                UnityEngine.Object.DestroyImmediate(body);

            foreach (var particles in visual.GetComponentsInChildren<ParticleSystem>(true))
                UnityEngine.Object.DestroyImmediate(particles);

            foreach (var light in visual.GetComponentsInChildren<Light>(true))
                UnityEngine.Object.DestroyImmediate(light);
        }

        /// <summary>
        /// ZNetScene only knows prefabs that carry a ZNetView, and most dressing props do
        /// not - they live as children inside location prefabs. So the scene is asked
        /// first, and everything Unity currently has loaded is searched second.
        /// </summary>
        public static GameObject Find(string name)
        {
            if (ZNetScene.instance != null)
            {
                var registered = ZNetScene.instance.GetPrefab(name);
                if (registered != null) return registered;
            }

            if (_index == null) BuildIndex();

            GameObject found;
            return _index.TryGetValue(name, out found) ? found : null;
        }

        private static void BuildIndex()
        {
            _index = new Dictionary<string, GameObject>(StringComparer.OrdinalIgnoreCase);

            // Expensive, so it happens once. Prefabs are preferred over scene instances:
            // an instance carries whatever state the world has put on it.
            foreach (var candidate in Resources.FindObjectsOfTypeAll<GameObject>())
            {
                if (candidate == null || candidate.transform.parent != null) continue;
                if (candidate.GetComponentInChildren<MeshRenderer>(true) == null) continue;

                var inScene = candidate.scene.IsValid();
                GameObject existing;

                if (!_index.TryGetValue(candidate.name, out existing) || (!inScene && existing.scene.IsValid()))
                    _index[candidate.name] = candidate;
            }

            StokerPlugin.Log.LogInfo("Prop index built: " + _index.Count + " candidates with meshes.");
        }

        /// <summary>
        /// Lists everything loaded whose name contains one of the given words.
        ///
        /// The hand-written candidate list came off the asset manifest, which catalogues
        /// every asset that exists rather than every asset that is loaded - and only two
        /// of sixteen turned out to be reachable. The index knows what is genuinely there,
        /// so asking it beats guessing at names.
        /// </summary>
        public static void Search(string keywords)
        {
            if (string.IsNullOrEmpty(keywords)) return;
            if (_index == null) BuildIndex();

            foreach (var raw in keywords.Split(','))
            {
                var word = raw.Trim();
                if (word.Length == 0) continue;

                var hits = new List<string>();
                foreach (var pair in _index)
                {
                    if (pair.Key.IndexOf(word, StringComparison.OrdinalIgnoreCase) < 0) continue;

                    // Broken and destruction variants are the same prop in pieces.
                    var lower = pair.Key.ToLowerInvariant();
                    if (lower.Contains("destruction") || lower.Contains("broken")
                        || lower.Contains("lod") || lower.Contains("vfx")
                        || lower.Contains("sfx")) continue;

                    hits.Add(pair.Key);
                }

                hits.Sort();
                StokerPlugin.Log.LogInfo(
                    "Props matching '" + word + "' (" + hits.Count + "): "
                    + string.Join(", ", hits.GetRange(0, Math.Min(40, hits.Count)).ToArray()));
            }
        }

        /// <summary>Says which of the candidates are actually available right now.</summary>
        public static void ReportCandidates()
        {
            var found = new List<string>();
            var missing = new List<string>();

            foreach (var name in Candidates)
                (Find(name) != null ? found : missing).Add(name);

            StokerPlugin.Log.LogInfo("Visual props available: " + string.Join(", ", found.ToArray()));

            if (missing.Count > 0)
                StokerPlugin.Log.LogInfo("Visual props not loaded: " + string.Join(", ", missing.ToArray()));
        }
    }
}
