using BepInEx.Configuration;
using UnityEngine;

namespace Stoker
{
    /// <summary>
    /// The whole mod is built on one balance line: it changes how often you walk to a
    /// smelter, never how much metal comes out of it.
    ///
    /// Batching removes clicks, not resources - three ore in one press costs exactly the
    /// three ore. Capacity means a longer gap between trips, but m_secPerProduct and
    /// m_fuelPerProduct are never touched, so twenty iron takes the same time and the same
    /// coal whether it went in as one load or three. Nothing here is a throughput increase,
    /// which is what keeps it from turning into the automation mod it replaces.
    /// </summary>
    internal static class StokerConfig
    {
        public static ConfigEntry<int> SmelterItemsPerAdd;
        public static ConfigEntry<int> FireplaceItemsPerAdd;
        public static ConfigEntry<KeyCode> BatchModifier;
        public static ConfigEntry<bool> Verbose;

        public static ConfigEntry<bool> Enabled;
        public static ConfigEntry<string> Donor;
        public static ConfigEntry<float> Range;
        public static ConfigEntry<int> MaxPerStation;
        public static ConfigEntry<float> CapacityPerUpgrade;
        public static ConfigEntry<bool> AimEffects;

        public static ConfigEntry<string> PrefabSearch;
        public static ConfigEntry<bool> TestMode;

        /// <summary>
        /// The real costs are gated behind the stations they upgrade, which is a whole
        /// biome of progression before you can check that the thing even appears on the
        /// hammer. This makes that a switch rather than a config string to edit and
        /// remember to put back.
        /// </summary>
        private const string TestCost = "Wood:1";

        public static string CostNow(UpgradeDef def)
        {
            return TestMode.Value ? TestCost : def.Cost.Value;
        }

        public static void Bind(ConfigFile config)
        {
            TestMode = config.Bind("Diagnostics", "TestMode", false,
                "Makes both upgrades cost one wood, so they can be built and looked at "
                + "without bronze. Announced in the log on startup so it is hard to leave on.");

            Verbose = config.Bind("Diagnostics", "Verbose", false,
                "Log each batched add and why it stopped.");

            // Off by default. It indexes every loaded object carrying a mesh - close to two
            // thousand of them - and then writes a few hundred names into a log shared with
            // every other mod. Genuinely useful while hunting for a prefab to borrow a
            // material from, pure cost on every world load afterwards.
            PrefabSearch = config.Bind("Diagnostics", "PrefabSearch", "",
                "Comma-separated words. Every loaded prefab whose name contains one is "
                + "listed in the log, which is how to find a prefab worth borrowing a "
                + "material from. Empty turns it off. Scans everything loaded, so empty it "
                + "again when you are done.");

            // ------------------------------------------------------------------ upgrades

            Enabled = config.Bind("Upgrades", "Enabled", true,
                "Add the two buildable upgrades that raise a nearby station's capacity.");

            Donor = config.Bind("Upgrades", "Donor", "piece_chest_barrel",
                "Prefab cloned for its machinery - ZNetView, Piece, WearNTear, placement "
                + "rules. Its look, collision and icon are all replaced, so this is not a "
                + "visual choice. Falls back to piece_chest_wood. Needs a restart.");

            Range = config.Bind("Upgrades", "Range", 4f,
                "How close an upgrade must be to the station it feeds.");

            MaxPerStation = config.Bind("Upgrades", "MaxPerStation", 2,
                "Most upgrades of one kind that will count for one station. Keeps it a "
                + "decision rather than something you stack until capacity stops mattering.");

            // A multiple of the station's own capacity, not a flat amount. A flat figure
            // cannot be round for two stations of different sizes - +20 turned a charcoal
            // kiln's 25 into 45 and a smelter's 10 into 30 - and it needed separate ore and
            // fuel numbers kept in step by hand to preserve the 2:1 coal ratio that the
            // station's own base values already encode.
            CapacityPerUpgrade = config.Bind("Upgrades", "CapacityPerUpgrade", 1.0f,
                "How much capacity each upgrade adds, as a multiple of what the station "
                + "already holds. 1 doubles it - a charcoal kiln goes 25 to 50, a smelter "
                + "10 ore and 20 coal to 20 and 40 - and a second upgrade triples it. 0.5 "
                + "adds half. Ore and fuel scale together, so the ratio a station was built "
                + "with survives. Never affects speed or fuel efficiency, only how long a "
                + "station runs before it needs you.");

            AimEffects = config.Bind("Upgrades", "AimEffects", true,
                "Point any particle effect the piece inherited from its donor at the "
                + "station it feeds, and stop it when it feeds nothing. Off leaves the "
                + "donor's effect exactly as it came.");

            // ------------------------------------------------------------------ the trough

            UpgradePrefabs.Trough.Name = config.Bind("Trough", "Name", "Trough",
                "Name shown on the hammer and when you look at one.");

            UpgradePrefabs.Trough.Cost = config.Bind("Trough", "Cost", "Wood:20,Bronze:5",
                "Build cost, as Item:Amount pairs. Bronze gates it behind the smelter it "
                + "upgrades, so it cannot be built before there is anything to smelt.");

            UpgradePrefabs.Trough.Model = config.Bind("Trough", "Model",
                "stoker_trough_raised.obj",
                "The OBJ loaded from beside the DLL. Its .col sidecar supplies the "
                + "collision and its _icon.png the hammer icon, both matched by name - so "
                + "dropping in a new model brings its own shape and picture with it.");

            UpgradePrefabs.Trough.Scale = config.Bind("Trough", "Scale", 1f,
                "Overall size of the trough.");

            // ------------------------------------------------------------------ the rack

            UpgradePrefabs.Woodrack.Name = config.Bind("Woodrack", "Name", "Woodrack",
                "Name shown on the hammer and when you look at one.");

            // No bronze here. A charcoal kiln is a Black Forest build and the rack that
            // feeds it has to be reachable at the same time, or the upgrade arrives an age
            // after the station it exists for.
            UpgradePrefabs.Woodrack.Cost = config.Bind("Woodrack", "Cost", "Wood:25,Stone:10",
                "Build cost, as Item:Amount pairs. Deliberately not gated behind bronze - "
                + "a charcoal kiln is buildable long before that, and an upgrade you "
                + "cannot build alongside its station is one you never build at all.");

            UpgradePrefabs.Woodrack.Model = config.Bind("Woodrack", "Model",
                "stoker_kiln_woodrack.obj",
                "The OBJ loaded from beside the DLL, with its .col and _icon.png matched "
                + "by name.");

            UpgradePrefabs.Woodrack.Scale = config.Bind("Woodrack", "Scale", 1f,
                "Overall size of the woodrack.");

            // ------------------------------------------------------------------ batching

            // Held, not toggled: a plain press has to stay exactly vanilla, or the mod has
            // taken the single-add away rather than added a batch. Set to None to make
            // batching the default and lose the one-at-a-time press.
            BatchModifier = config.Bind("Batching", "BatchModifier", KeyCode.LeftShift,
                "Hold this while interacting to add a batch instead of one. Plain use stays "
                + "vanilla, so nothing is taken away - the batch is an option you reach for.");

            SmelterItemsPerAdd = config.Bind("Batching", "SmelterItemsPerAdd", 3,
                "Ore or coal added per press at a smelter, kiln, blast furnace, windmill, "
                + "spinning wheel or eitr refinery. Stops early at the station's capacity "
                + "or when you run out. 1 restores vanilla.");

            FireplaceItemsPerAdd = config.Bind("Batching", "FireplaceItemsPerAdd", 3,
                "Logs added per press at a campfire, hearth or torch. 1 restores vanilla.");
        }
    }
}
