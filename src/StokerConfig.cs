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

        public static ConfigEntry<bool> HopperEnabled;
        public static ConfigEntry<string> HopperName;
        public static ConfigEntry<string> HopperCost;
        public static ConfigEntry<string> HopperDonor;
        public static ConfigEntry<float> HopperRange;
        public static ConfigEntry<int> MaxHoppers;
        public static ConfigEntry<int> OreCapacityPerHopper;
        public static ConfigEntry<int> FuelCapacityPerHopper;
        public static ConfigEntry<string> HopperModelFile;
        public static ConfigEntry<float> HopperScale;
        public static ConfigEntry<float> HopperSquash;
        public static ConfigEntry<string> HopperVisual;
        public static ConfigEntry<float> HopperVisualScale;
        public static ConfigEntry<bool> LogVisualCandidates;
        public static ConfigEntry<string> VisualSearch;
        public static ConfigEntry<bool> TestMode;

        /// <summary>
        /// The hopper's real cost is gated behind bronze, which is a whole biome of
        /// progression before you can check that the thing even appears on the hammer.
        /// This makes that a switch rather than a config string to edit and remember to
        /// put back.
        /// </summary>
        private const string TestCost = "Wood:1";

        public static string HopperCostNow()
        {
            return TestMode.Value ? TestCost : HopperCost.Value;
        }

        public static void Bind(ConfigFile config)
        {
            TestMode = config.Bind("Diagnostics", "TestMode", false,
                "Makes the hopper cost one wood, so it can be built and checked without "
                + "bronze. Announced in the log on startup so it is hard to leave on.");

            HopperEnabled = config.Bind("Hopper", "HopperEnabled", true,
                "Add the buildable hopper that raises a nearby station's capacity.");

            HopperName = config.Bind("Hopper", "HopperName", "Hopper",
                "Name shown on the hammer and when you look at one.");

            HopperCost = config.Bind("Hopper", "HopperCost", "Wood:20,Bronze:5",
                "Build cost, as Item:Amount pairs. Bronze gates it behind the smelter it "
                + "upgrades, so it cannot be built before there is anything to smelt.");

            HopperDonor = config.Bind("Hopper", "HopperDonor", "piece_chest_barrel",
                "Prefab whose model and icon the hopper borrows. Falls back to "
                + "piece_chest_wood if this does not exist. Other vanilla pieces worth "
                + "trying: piece_oven (stone, reads industrial), piece_cauldron (metal), "
                + "piece_pot1 (clay). Changing this needs a restart, not a rebuild.");

            HopperVisual = config.Bind("Hopper", "HopperVisual", "",
                "Name of a vanilla prop to wear instead of the built model. Empty uses "
                + "the hand-built mesh. Worth trying: CargoCrate, Crate_box, Barrels, "
                + "Baskets, Sacks, fi_vil_container_sack03_grain, "
                + "fi_vil_container_basket01_grain_lid, Cart. Needs a restart, not a "
                + "rebuild - so cycling through them is a relaunch each, not a build each.");

            HopperVisualScale = config.Bind("Hopper", "HopperVisualScale", 1f,
                "Size of the grafted prop. Props are modelled at their own scale, so "
                + "expect to tune this per prop rather than once.");

            // Both default off. They were the scaffolding for picking a prop to graft, and
            // they are not free: either one builds an index of every loaded GameObject
            // carrying a mesh - close to two thousand of them - and the search then writes
            // a few hundred prop names into a log shared with every other mod. Useful
            // exactly once, while choosing; pure cost on every world load after that.
            VisualSearch = config.Bind("Diagnostics", "VisualSearch", "",
                "Comma-separated words. Every loaded prop whose name contains one is listed "
                + "in the log, so a real name can be picked instead of guessed at. Empty "
                + "turns it off. Worth a line like "
                + "crate,sack,barrel,pile,stack while choosing a prop for HopperVisual, and "
                + "worth emptying again afterwards - it scans every loaded object.");

            LogVisualCandidates = config.Bind("Diagnostics", "LogVisualCandidates", false,
                "List which of the candidate props are actually loaded at startup. They "
                + "are not all guaranteed - some are location dressing that only exists "
                + "while such a location is streamed in. Builds the same index VisualSearch "
                + "does, so leave it off unless you are picking a prop.");

            HopperScale = config.Bind("Hopper", "HopperScale", 1f,
                "Overall size of the hopper.");

            HopperSquash = config.Bind("Hopper", "HopperSquash", 0.7f,
                "Height multiplier on top of HopperScale. Below 1 squats the donor down so "
                + "it reads as a bin rather than the barrel it was cloned from. 1 keeps the "
                + "donor's own proportions.");

            HopperRange = config.Bind("Hopper", "HopperRange", 4f,
                "How close a hopper must be to the station it feeds.");

            MaxHoppers = config.Bind("Hopper", "MaxHoppers", 2,
                "Most hoppers that will count for one station. Keeps the upgrade a decision "
                + "rather than something you stack until capacity stops mattering.");

            // Split rather than one number, because a smelter eats two coal for every ore.
            // A single figure either starves the fuel side or overfills the ore side, and
            // the whole point of the upgrade is that one filling lasts a sensible while.
            OreCapacityPerHopper = config.Bind("Hopper", "OreCapacityPerHopper", 20,
                "Extra ore capacity per hopper, added to whatever the station already holds. "
                + "Never affects speed or fuel efficiency - only how long a station runs "
                + "before it needs you.");

            FuelCapacityPerHopper = config.Bind("Hopper", "FuelCapacityPerHopper", 40,
                "Extra fuel capacity per hopper. Twice the ore figure by default, because a "
                + "smelter burns two coal for every ore it melts - matching them means the "
                + "coal side runs out first and the upgrade only half works.");

            HopperModelFile = config.Bind("Hopper", "HopperModelFile", "stoker_hopper.obj",
                "The OBJ loaded from the mod's assets folder for the hopper's shape. Named "
                + "here rather than compiled in so a new model can be dropped in and looked "
                + "at without a rebuild.");

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

            Verbose = config.Bind("Diagnostics", "Verbose", false,
                "Log each batched add and why it stopped.");
        }
    }
}
