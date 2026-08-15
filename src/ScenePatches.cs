using HarmonyLib;

namespace Stoker
{
    internal static class ScenePatches
    {
        /// <summary>
        /// The capacity component goes onto the prefabs, so it has to land before anything
        /// is built from them. Every station in the world - including ones loaded back out
        /// of a save - is instantiated after this, so they all get it rather than only newly
        /// placed ones.
        ///
        /// The upgrades are attempted here too, though they usually take on the ObjectDB
        /// hook instead: their build costs need item prefabs, and which of the two wakes
        /// first is not something to rely on.
        /// </summary>
        [HarmonyPostfix]
        [HarmonyPatch(typeof(ZNetScene), "Awake")]
        private static void OnSceneAwake()
        {
            var touched = SmelterCapacity.AttachToPrefabs();
            if (touched > 0)
                StokerPlugin.Log.LogInfo("Capacity component added to " + touched + " station prefab(s).");

            UpgradePrefabs.Register();

            PropIndex.Search(StokerConfig.PrefabSearch.Value);
        }

        /// <summary>
        /// Borrowed materials are dropped on both of these. A local world arrives through
        /// Awake and a server handing over its item list through CopyOtherDB; a material
        /// held across either is a reference to a prefab that has been torn down.
        /// </summary>
        [HarmonyPostfix]
        [HarmonyPatch(typeof(ObjectDB), "Awake")]
        private static void OnObjectDbAwake()
        {
            Skins.Invalidate();
            UpgradeBin.ForgetConnectionPrefab();
            UpgradePrefabs.Register();
        }

        [HarmonyPostfix]
        [HarmonyPatch(typeof(ObjectDB), nameof(ObjectDB.CopyOtherDB))]
        private static void OnObjectDbCopy()
        {
            Skins.Invalidate();
            UpgradeBin.ForgetConnectionPrefab();
            UpgradePrefabs.Register();
        }
    }
}
