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
        /// The hopper is attempted here too, though it usually takes on the ObjectDB hook
        /// instead: its build cost needs item prefabs, and which of the two wakes first is
        /// not something to rely on.
        /// </summary>
        [HarmonyPostfix]
        [HarmonyPatch(typeof(ZNetScene), "Awake")]
        private static void OnSceneAwake()
        {
            var touched = SmelterCapacity.AttachToPrefabs();
            if (touched > 0)
                StokerPlugin.Log.LogInfo("Capacity component added to " + touched + " station prefab(s).");

            HopperPrefab.Register();

            if (StokerConfig.LogVisualCandidates.Value) PropGraft.ReportCandidates();
            PropGraft.Search(StokerConfig.VisualSearch.Value);
        }

        [HarmonyPostfix]
        [HarmonyPatch(typeof(ObjectDB), "Awake")]
        private static void OnObjectDbAwake()
        {
            HopperPrefab.Register();
        }

        [HarmonyPostfix]
        [HarmonyPatch(typeof(ObjectDB), nameof(ObjectDB.CopyOtherDB))]
        private static void OnObjectDbCopy()
        {
            HopperPrefab.Register();
        }
    }
}
