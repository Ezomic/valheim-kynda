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
        public static ConfigEntry<float> TexelsPerMetre;
        public static ConfigEntry<bool> ShowLink;
        public static ConfigEntry<float> LinkHeight;

        public static ConfigEntry<string> PrefabSearch;
        public static ConfigEntry<bool> TestMode;
        public static ConfigEntry<bool> VariantMode;

        /// <summary>
        /// The real costs are gated behind the stations they upgrade, which is a whole
        /// biome of progression before you can check that the thing even appears on the
        /// hammer. This makes that a switch rather than a config string to edit and
        /// remember to put back.
        /// </summary>
        private const string TestCost = "Wood:1";

        public static string CostNow(UpgradeDef def)
        {
            return TestMode.Value || def.Cost == null ? TestCost : def.Cost.Value;
        }

        public static void Bind(ConfigFile config)
        {
            TestMode = config.Bind("Diagnostics", "TestMode", false,
                "Makes both upgrades cost one wood, so they can be built and looked at "
                + "without bronze. Announced in the log on startup so it is hard to leave on.");

            Verbose = config.Bind("Diagnostics", "Verbose", false,
                "Log each batched add and why it stopped.");

            // For judging models against each other in the game's own light rather than
            // against a memory of the last one. Every variant is a registered prefab, so
            // anything built from one is a real ZDO keyed on a name that stops resolving
            // the moment this goes off - and ZNetScene discards those silently. Hence the
            // warning in the log rather than only here.
            VariantMode = config.Bind("Diagnostics", "VariantMode", false,
                "Put every candidate model on the hammer as its own piece at one wood "
                + "each, named 'var: ...', so they can be built side by side and compared. "
                + "DESTRUCTIVE WHEN TURNED OFF: anything built from a variant vanishes with "
                + "it, because its prefab name stops existing. Build them somewhere you do "
                + "not mind losing.");

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

            // Measured off the game rather than picked. Ripping the build set showed
            // vanilla runs two families: structural blocks - beam, pole, door, floor - at
            // 165 to 224 texels/m using nearly their whole sheet, and props, piles and
            // furniture at 24 to 54 off a tight rect. wood_stack is 28, barrell 29,
            // piece_chest_wood 42, wood_wall_log 54. These pieces are props, so 35 sits in
            // the middle of the family they belong to.
            TexelsPerMetre = config.Bind("Upgrades", "TexelsPerMetre", 35f,
                "How coarse the borrowed texture is drawn, in texels per metre. Vanilla's "
                + "props and piles run 24 to 54; its structural pieces run far finer and "
                + "are the wrong thing to match. Higher is finer and eventually reads as "
                + "flat colour, because the grain becomes smaller than a pixel on screen. "
                + "A group too big for its donor's slice of the atlas is drawn coarser "
                + "than this rather than tiled - the log says when.");

            ShowLink = config.Bind("Upgrades", "ShowLink", true,
                "Draw the game's own station-link effect from an upgrade to the station it "
                + "feeds when you look at it - the same run of motes a chopping block draws "
                + "to its workbench. Off is silent.");

            LinkHeight = config.Bind("Upgrades", "LinkHeight", 0.8f,
                "How far up the upgrade the link starts, in metres. The default leaves it "
                + "around the top of both pieces; at 0 it comes out of the ground.");

            // ------------------------------------------------------------------ the trough

            UpgradePrefabs.Trough.Name = config.Bind("Trough", "Name", "Trough",
                "Name shown on the hammer and when you look at one.");

            UpgradePrefabs.Trough.Cost = config.Bind("Trough", "Cost", "Wood:20,Bronze:5",
                "Build cost, as Item:Amount pairs. Bronze gates it behind the smelter it "
                + "upgrades, so it cannot be built before there is anything to smelt.");

            UpgradePrefabs.Trough.Model = config.Bind("Trough", "Model",
                "stoker_trough_barrels.obj",
                "The OBJ loaded from beside the DLL. Its .col sidecar supplies the "
                + "collision and its _icon.png the hammer icon, both matched by name - so "
                + "dropping in a new model brings its own shape and picture with it.");

            UpgradePrefabs.Trough.Scale = config.Bind("Trough", "Scale", 1f,
                "Overall size of the trough.");

            // Empty means the general list, which leads with piece_chest_wood - sawn
            // planking, which is what a stave and a sled are.
            UpgradePrefabs.Trough.SkinDonors = config.Bind("Trough", "SkinDonors", "",
                "Which vanilla prefab each material group borrows its surface from, as "
                + "group=prefab pairs. Empty uses the general list. Only worth setting when "
                + "a piece wants a different surface from the other one.");

            UpgradePrefabs.Trough.OreCapacity = config.Bind("Trough", "OreCapacity", 20,
                "Extra ore a smelter or furnace holds per trough. Vanilla's 10 becomes 30.");

            // Twice the ore figure, because a smelter burns two coal for every ore it melts.
            // Matching them would leave the coal side empty with a third of the ore still in
            // the hopper, which is the upgrade only half working.
            UpgradePrefabs.Trough.FuelCapacity = config.Bind("Trough", "FuelCapacity", 40,
                "Extra coal a smelter or furnace holds per trough. Vanilla's 20 becomes 60. "
                + "Twice the ore figure on purpose - a smelter burns two coal per ore, so "
                + "matching them would run the fuel out before the ore.");

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
                "stoker_rack_lean.obj",
                "The OBJ loaded from beside the DLL, with its .col and _icon.png matched "
                + "by name.");

            UpgradePrefabs.Woodrack.Scale = config.Bind("Woodrack", "Scale", 1f,
                "Overall size of the woodrack.");

            // 25 rather than the trough's 20, because a charcoal kiln starts at 25 and this
            // is aimed at landing on a round 50. The two upgrades need different figures for
            // the same reason a percentage would not do: the stations are different sizes,
            // and what matters is the number you end on.
            // Round bark rather than sawn planking. This piece is a stack of logs, and
            // piece_chest_wood's slice of atlas carries the chest's dark iron banding -
            // which landed on the sawn ends and rendered them almost black. wood_wall_log
            // is uniformly timber, and its rect is 0.424 against 0.231, so the wood group
            // reaches the full target density here instead of clamping at 20.
            UpgradePrefabs.Woodrack.SkinDonors = config.Bind("Woodrack", "SkinDonors",
                "wood=wood_wall_log",
                "Which vanilla prefab each material group borrows its surface from, as "
                + "group=prefab pairs. Empty uses the general list.");

            UpgradePrefabs.Woodrack.OreCapacity = config.Bind("Woodrack", "OreCapacity", 25,
                "Extra wood a charcoal kiln holds per woodrack. Vanilla's 25 becomes 50.");

            // No fuel entry. This one only ever serves stations with no fuel slot, so it
            // would be a setting that could never do anything.

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
