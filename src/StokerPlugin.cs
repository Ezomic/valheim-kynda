using BepInEx;
using BepInEx.Logging;
using HarmonyLib;

namespace Stoker
{
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    [BepInProcess("valheim.exe")]
    public class StokerPlugin : BaseUnityPlugin
    {
        public const string PluginGuid = "ezomic.valheim.stoker";
        public const string PluginName = "Stoker";
        public const string PluginVersion = "0.1.0";
        public const string PluginAuthor = "Robbin Thijssen";

        internal static ManualLogSource Log;

        private Harmony _harmony;

        private void Awake()
        {
            Log = Logger;
            StokerConfig.Bind(Config);

            BatchAdd.Verify();

            _harmony = new Harmony(PluginGuid);
            _harmony.PatchAll(typeof(BatchAdd));
            _harmony.PatchAll(typeof(ScenePatches));

            Log.LogInfo(PluginName + " " + PluginVersion + " by " + PluginAuthor + " - ready.");

            if (StokerConfig.TestMode.Value)
                Log.LogWarning("TEST MODE: the hopper costs one wood. "
                               + "Turn TestMode off in the config before playing for real.");
        }

        private void OnDestroy()
        {
            if (_harmony != null) _harmony.UnpatchSelf();
        }

        /// <summary>
        /// A safety net, not the main path. The hopper normally registers on ZNetScene and
        /// ObjectDB waking; this covers whichever of them ran before the other was ready,
        /// since the build cost needs ObjectDB and the prefab needs ZNetScene.
        /// </summary>
        private void Update()
        {
            if (ZNetScene.instance == null || ObjectDB.instance == null) return;
            HopperPrefab.Register();
        }
    }
}
