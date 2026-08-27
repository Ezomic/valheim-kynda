using System.Runtime.CompilerServices;
using BepInEx;
using BepInEx.Bootstrap;
using BepInEx.Logging;
using Ezomic.Core;
using HarmonyLib;

namespace Kynda
{
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    // Soft, not hard. A hard dependency that is absent does not degrade - the plugin never
    // loads at all - and every mod here has to be installable on its own. Soft still buys
    // the load-order guarantee when Core is present, which is all the gate needs.
    //
    // Back as of 1.0.0, together with the upgrades, and the pairing is the point: they are
    // registered prefabs, and ZNetScene discards any ZDO whose prefab name does not resolve
    // rather than erroring. A server without this mod does not fail to show a Tun, it
    // deletes every Tun already standing. The gate is what refuses that connection instead.
    //
    // No BepInProcess. It is a whitelist, and a dedicated server runs valheim_server.exe.
    [BepInDependency(CoreGuid, BepInDependency.DependencyFlags.SoftDependency)]
    public class KyndaPlugin : BaseUnityPlugin
    {
        public const string PluginGuid = "ezomic.valheim.kynda";
        public const string PluginName = "Kynda";
        public const string PluginVersion = "1.0.1";
        public const string PluginAuthor = "Robbin Thijssen";

        /// <summary>Core's plugin GUID. Optional - see TryRegisterWithCore.</summary>
        private const string CoreGuid = "ezomic.valheim.core";

        /// <summary>Whether Core answered at load.</summary>
        internal static bool CorePresent;

        internal static ManualLogSource Log;

        private Harmony _harmony;

        private void Awake()
        {
            Log = Logger;
            KyndaConfig.Bind(Config);

            // Before anything else touches a soft reference. The asset loader is built
            // lazily on first use and reads this flag once, in its constructor, so the
            // window for asking it to list materials as well as locations is here in
            // Awake and nowhere later. It reads nothing and loads nothing by itself.
            SoftAssets.MakeEverythingLoadable();

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

            if (KyndaConfig.TestMode.Value)
                Log.LogWarning("TEST MODE: both upgrades cost one wood. "
                               + "Turn TestMode off in the config before playing for real.");
        }

        /// <summary>
        /// Joins Core's version gate when Core is installed, and does nothing when it is not.
        ///
        /// What standing alone costs here is not enforcement of a rule, it is somebody's
        /// buildings. The upgrades are registered prefabs; ZNetScene discards any ZDO whose
        /// prefab name will not resolve, and it does it silently. So a client without this
        /// mod joining a world that has it does not error and does not merely fail to see a
        /// Tun - it deletes every Tun and Woodrack standing in that world.
        ///
        /// Ungated, nothing refuses that client. That was acceptable exactly while this was a
        /// single-player mod being reworked, and it stopped being acceptable the moment it
        /// went back into the pack.
        /// </summary>
        private void TryRegisterWithCore()
        {
            CorePresent = Chainloader.PluginInfos.ContainsKey(CoreGuid);

            if (!CorePresent)
            {
                Log.LogWarning("Core is not installed, so there is no version gate. The "
                               + "upgrades still work, but a world loaded without this mod "
                               + "discards every one already built - and nothing will stop "
                               + "that happening.");
                return;
            }

            RegisterWithCore();
        }

        /// <summary>
        /// Kept separate and never inlined. The JIT resolves the assemblies a method needs
        /// when it first compiles that method, so a Suite call sitting directly in Awake
        /// would drag Ezomic.Core in before the check above could prevent it, and the
        /// missing-assembly exception would land during plugin load.
        /// </summary>
        [MethodImpl(MethodImplOptions.NoInlining)]
        private void RegisterWithCore()
        {
            // Everyone, not HostOnly, and not a matter of taste: this registers prefabs.
            Suite.Register(PluginGuid, PluginName, PluginVersion, Config, Requirement.Everyone);
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

            // Skins that named a material the world had not streamed in yet. Empty-list
            // cheap in any session that never uses an @donor.
            Skins.Tick();

            // And once those land, the hammer icons become photographs of the skinned
            // pieces rather than the flat placeholder renders.
            UpgradePrefabs.RefreshIcons();
        }
    }
}
