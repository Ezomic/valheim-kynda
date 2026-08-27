using System;
using System.Collections.Generic;
using SoftReferenceableAssets;
using UnityEngine;

namespace Kynda
{
    /// <summary>
    /// Loads a vanilla asset by name, straight out of the game's own bundles, whether or
    /// not anything in the world has ever used it.
    ///
    /// This exists because of the magenta Tun. The camp donors - fi_village_wood above all
    /// - are only reachable through Valheim's soft-reference system: the material lives in
    /// a bundle that nothing opens until a player walks near a vendor camp, and on a fresh
    /// server world that is never. The first answer was to summon the whole Vendor
    /// location and wait for its material to appear among the loaded ones. It works, and
    /// it is still here as the fallback, but it asks for the wrong thing: an entire
    /// village prefab resident in memory to borrow one 441KB material, with the carrier
    /// location hand-named in config, so a game update that moved the material would break
    /// the skin silently.
    ///
    /// Asking for the material itself is a supported operation, with one catch. The
    /// loader reads StreamingAssets\SoftRef\manifest at startup - 471 entries, locations
    /// and dungeon rooms and scenes, which is why the Vendor prefab was addressable - and
    /// reads manifest_extended, the other 16,814 entries covering materials, textures and
    /// meshes, ONLY if <see cref="Runtime.MakeAllAssetsLoadable"/> was called first.
    /// Nothing in the game ever calls it. So on an unmodified runtime a material has no
    /// loadable id at all; one line in Awake is the whole difference.
    ///
    /// Nothing is ever released, and that is a correctness requirement rather than
    /// laziness. When an asset's reference count reaches zero the loader unloads its
    /// bundle with unloadAllLoadedObjects TRUE, which destroys the Material and its
    /// textures even while pieces standing in the world are drawing with them - and
    /// vanilla's own zone streaming load/release-cycles these same bundles as players
    /// come and go. A held reference is what stops a Tun going magenta mid-session.
    /// </summary>
    internal static class SoftAssets
    {
        /// <summary>
        /// Ask the loader to read the extended manifest, which is the one materials are
        /// listed in. Call from the plugin's Awake and nowhere else.
        ///
        /// It only sets a flag - no manifest is read and no bundle is opened here - but it
        /// has to happen before anything in the process touches a soft reference, because
        /// the flag is read once, in the loader's constructor, and the loader is built
        /// lazily on first use. Called too late it logs an error and does nothing, and
        /// then <see cref="LoadMaterial"/> simply finds no id and the location fallback
        /// carries the skin as it did before.
        /// </summary>
        public static void MakeEverythingLoadable()
        {
            try
            {
                Runtime.MakeAllAssetsLoadable();
            }
            catch (Exception e)
            {
                KyndaPlugin.Log.LogWarning(
                    "Could not enable the extended asset manifest: " + e.Message
                    + ". Location-only materials will fall back to summoning their carrier.");
            }
        }

        /// <summary>Path suffix to id, built once. Rebuilding it is a 17,000 entry copy.</summary>
        private static Dictionary<string, AssetID> _paths;
        private static bool _pathsFailed;

        private static readonly Dictionary<string, Material> _loaded =
            new Dictionary<string, Material>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// A vanilla material by asset name - "fi_village_wood" - loaded on demand, or
        /// null if this build of the game does not list one under that name.
        ///
        /// Deliberately not called from Awake: the lookup blocks until the loader has
        /// finished parsing its manifests on a background thread, which is invisible from
        /// an Update-driven retry and a stall on the boot path. Kynda's callers are all
        /// on the retry, so this is free.
        /// </summary>
        public static Material LoadMaterial(string name)
        {
            if (string.IsNullOrEmpty(name)) return null;

            Material already;
            if (_loaded.TryGetValue(name, out already) && already != null) return already;

            try
            {
                AssetID id;
                if (!TryFindId(name, ".mat", out id)) return null;

                // The id came out of the loader's own table, so the reference is known to
                // it. That matters more than it looks: Load and Asset both index a private
                // dictionary directly and throw KeyNotFoundException on an id it has never
                // heard of - the same unguarded lookup that made the first summoner die
                // silently on a location with an empty soft reference.
                var reference = new SoftReference<Material>(id);

                // Synchronous on purpose. It is one 441KB bundle plus its dependency
                // closure, memory-mapped rather than read, and having the material in hand
                // on the next line means the caller skins immediately instead of watching
                // for it to appear. Never released - see the class comment.
                var result = reference.Load();
                if (result != LoadResult.Succeeded)
                {
                    KyndaPlugin.Log.LogWarning("The asset '" + name + "' is listed but "
                        + "would not load (" + result + ").");
                    return null;
                }

                var material = reference.Asset;
                if (material == null) return null;

                _loaded[name] = material;
                KyndaPlugin.Log.LogInfo("Loaded the material '" + name
                    + "' straight from its bundle, no location needed.");
                return material;
            }
            catch (Exception e)
            {
                KyndaPlugin.Log.LogWarning("Could not load '" + name
                    + "' through the asset loader: " + e.Message);
                return null;
            }
        }

        /// <summary>
        /// The id of the one asset whose manifest path ends in /name.extension.
        ///
        /// Matching on the path suffix rather than storing the hex id is what makes this
        /// survive a game update. The id is the Unity asset GUID and the path is where the
        /// asset sits in Iron Gate's project - either can change in principle, but a
        /// rename shows up here as "listed under no such name", logged, and the fallback
        /// takes over, where a stale hardcoded GUID would resolve to nothing with no way
        /// to say why.
        /// </summary>
        private static bool TryFindId(string name, string extension, out AssetID id)
        {
            id = default(AssetID);

            if (_paths == null && !_pathsFailed)
            {
                try
                {
                    _paths = Runtime.GetAllAssetPathsInBundleMappedToAssetID();
                    KyndaPlugin.Log.LogInfo("Asset manifest: " + _paths.Count
                        + " assets addressable by name.");
                }
                catch (Exception e)
                {
                    _pathsFailed = true;
                    KyndaPlugin.Log.LogWarning(
                        "Could not read the asset manifest: " + e.Message);
                }
            }
            if (_paths == null) return false;

            var suffix = "/" + name + extension;

            foreach (var entry in _paths)
            {
                if (entry.Key == null) continue;
                if (!entry.Key.EndsWith(suffix, StringComparison.OrdinalIgnoreCase)) continue;
                if (!entry.Value.IsValid) continue;   // a few extended entries are all-zero

                id = entry.Value;
                return true;
            }

            return false;
        }
    }
}
