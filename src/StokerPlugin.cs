using System.Runtime.CompilerServices;
using BepInEx;
using BepInEx.Bootstrap;
using BepInEx.Logging;
using Ezomic.Core;
using HarmonyLib;

namespace Stoker
{
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    // Soft, not hard. Stoker installs and runs on its own; a hard dependency
    // that is absent does not degrade, the plugin simply never loads. Soft still buys
    // the load-order guarantee when Core is present, which is what registering needs.
    [BepInDependency(CoreGuid, BepInDependency.DependencyFlags.SoftDependency)]
    // No BepInProcess. It is a whitelist, and a dedicated server runs valheim_server.exe.
    // The upgrades are registered prefabs, and ZNetScene discards any ZDO whose prefab name
    // does not resolve - so a server without this mod destroys every one already standing.
    public class StokerPlugin : BaseUnityPlugin
    {
        public const string PluginGuid = "ezomic.valheim.stoker";
        public const string PluginName = "Stoker";
        public const string PluginVersion = "0.4.0";
        public const string PluginAuthor = "Robbin Thijssen";

        /// <summary>Core's plugin GUID. Optional - see TryRegisterWithCore.</summary>
        private const string CoreGuid = "ezomic.valheim.core";

        internal static ManualLogSource Log;

        private Harmony _harmony;

        private void Awake()
        {
            Log = Logger;
            StokerConfig.Bind(Config);
            TryRegisterWithCore();

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

        /// <summary>
        /// Joins Core's version gate when Core is installed, and does nothing when it is not.
        ///
        /// Stoker is worth installing on its own, and a hard dependency that is absent does
        /// not degrade gracefully - the plugin never loads at all. So the reference is
        /// compile-time only and the call is made behind a check.
        ///
        /// What is given up standing alone is the gate, not the mod.
        /// This registers prefabs into ZNetScene, and a client that cannot resolve one discards
        /// the ZDO rather than erroring - destroying what is already standing. Without Core
        /// nothing refuses that client.
        /// </summary>
        private void TryRegisterWithCore()
        {
            if (!Chainloader.PluginInfos.ContainsKey(CoreGuid))
            {
                Log.LogInfo("Core not installed - running standalone, without the version gate.");
                return;
            }

            RegisterWithCore();
        }

        /// <summary>
        /// Kept separate and never inlined on purpose. The JIT resolves the assemblies a method
        /// needs when it first compiles that method, so a Suite call sitting directly in Awake
        /// would drag Ezomic.Core in before the check above could prevent it - and the
        /// missing-assembly exception would land during plugin load, which is the failure this
        /// whole arrangement exists to avoid. Isolating it means the type is only ever resolved
        /// on a machine that has Core.
        /// </summary>
        [MethodImpl(MethodImplOptions.NoInlining)]
        private void RegisterWithCore()
        {
            // Everyone, not HostOnly. Both ends have to agree about this mod, and the
            // disagreement is silent when they do not: a client that cannot resolve a prefab
            // hash discards the ZDO rather than erroring - destroying what is already standing
            // in the world - and item data that differs desyncs inventories.
            Suite.Register(PluginGuid, PluginName, PluginVersion, Config);
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
