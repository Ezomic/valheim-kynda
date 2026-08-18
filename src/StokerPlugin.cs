using BepInEx;
using BepInEx.Logging;
using HarmonyLib;

namespace Stoker
{
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    // No dependency on Core at all, soft or otherwise. Stoker has left the suite while its
    // upgrade models are being reworked - it is out of the pack and off the server, so there
    // is no shared set for a version gate to hold it to, and a soft dependency that only ever
    // resolves to "not installed" is a moving part earning nothing.
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

        // Core registration removed with the mod's departure from the pack and the server.
        //
        // What that gave up is worth writing down, because it comes back the moment Stoker
        // ships anywhere again. The gate is what stopped a client joining a host that did not
        // have this mod: the upgrades are registered prefabs, ZNetScene discards any ZDO whose
        // prefab name will not resolve, and it does it silently - so a mismatched client does
        // not error, it deletes every Tun and Woodrack already standing in that world.
        //
        // Standing alone, nothing refuses that client. Which is acceptable exactly while this
        // is a single-player mod being reworked, and not a moment longer.

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
