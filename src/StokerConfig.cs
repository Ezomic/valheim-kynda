using BepInEx.Configuration;

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
        public static ConfigEntry<bool> Verbose;

        public static ConfigEntry<bool> HopperEnabled;
        public static ConfigEntry<string> HopperName;
        public static ConfigEntry<string> HopperCost;
        public static ConfigEntry<string> HopperDonor;
        public static ConfigEntry<float> HopperRange;
        public static ConfigEntry<int> MaxHoppers;
        public static ConfigEntry<int> CapacityPerHopper;

        public static void Bind(ConfigFile config)
        {
            HopperEnabled = config.Bind("Hopper", "HopperEnabled", true,
                "Add the buildable hopper that raises a nearby station's capacity.");

            HopperName = config.Bind("Hopper", "HopperName", "Hopper",
                "Name shown on the hammer and when you look at one.");

            HopperCost = config.Bind("Hopper", "HopperCost", "Wood:20,Bronze:5",
                "Build cost, as Item:Amount pairs. Bronze gates it behind the smelter it "
                + "upgrades, so it cannot be built before there is anything to smelt.");

            HopperDonor = config.Bind("Hopper", "HopperDonor", "piece_chest_barrel",
                "Prefab whose model and icon the hopper borrows. Falls back to "
                + "piece_chest_wood if this does not exist.");

            HopperRange = config.Bind("Hopper", "HopperRange", 4f,
                "How close a hopper must be to the station it feeds.");

            MaxHoppers = config.Bind("Hopper", "MaxHoppers", 2,
                "Most hoppers that will count for one station. Keeps the upgrade a decision "
                + "rather than something you stack until capacity stops mattering.");

            CapacityPerHopper = config.Bind("Hopper", "CapacityPerHopper", 10,
                "Extra ore and fuel capacity per hopper. Never affects speed or fuel "
                + "efficiency - only how long a station runs before it needs you.");

            SmelterItemsPerAdd = config.Bind("Batching", "SmelterItemsPerAdd", 3,
                "Ore or coal added per press at a smelter, kiln, blast furnace, windmill, "
                + "spinning wheel or eitr refinery. Stops early at the station's capacity "
                + "or when you run out. 1 restores vanilla.");

            FireplaceItemsPerAdd = config.Bind("Batching", "FireplaceItemsPerAdd", 3,
                "Logs added per press at a campfire, hearth or torch. 1 restores vanilla.");

            Verbose = config.Bind("Diagnostics", "Verbose", false,
                "Log each batched add and why it stopped.");
        }
    }
}
