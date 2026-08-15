using BepInEx;
using BepInEx.Logging;
using HarmonyLib;

namespace Stoker
{
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    // No BepInProcess. It is a whitelist, and a dedicated server runs valheim_server.exe.
    // The upgrades are registered prefabs, and ZNetScene discards any ZDO whose prefab name
    // does not resolve - so a server without this mod destroys every one already standing.
    public class StokerPlugin : BaseUnityPlugin
    {
        public const string PluginGuid = "ezomic.valheim.stoker";
        public const string PluginName = "Stoker";
        public const string PluginVersion = "0.3.0";
        public const string PluginAuthor = "Robbin Thijssen";

        internal static ManualLogSource Log;

        private Harmony _harmony;

        private void Awake()
        {
            Log = Logger;
            StokerConfig.Bind(Config);

            _harmony = new Harmony(PluginGuid);
            _harmony.PatchAll(typeof(ScenePatches));

            // Verify says out loud which reflected members have gone missing; the postfixes
            // themselves each re-check, so a false answer costs batching and nothing else.
            // The hint is only worth advertising when the thing it advertises works.
            if (BatchAdd.Verify())
            {
                _harmony.PatchAll(typeof(BatchAdd));
                HoverHint.Apply(_harmony);
            }

            Log.LogInfo(PluginName + " " + PluginVersion + " by " + PluginAuthor + " - ready.");

            if (StokerConfig.TestMode.Value)
                Log.LogWarning("TEST MODE: both upgrades cost one wood. "
                               + "Turn TestMode off in the config before playing for real.");
        }

        private void OnDestroy()
        {
            if (_harmony != null) _harmony.UnpatchSelf();
        }

        /// <summary>
        /// A safety net, not the main path. The upgrades normally register on ZNetScene and
        /// ObjectDB waking; this covers whichever of them ran before the other was ready,
        /// since the build costs need ObjectDB and the prefabs need ZNetScene.
        /// </summary>
        private void Update()
        {
            if (ZNetScene.instance == null || ObjectDB.instance == null) return;
            UpgradePrefabs.Register();
        }
    }
}
