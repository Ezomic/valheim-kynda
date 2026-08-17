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
        public static ConfigEntry<string> Station;
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

            // The donor is a chest, so both upgrades inherited the workbench. They are
            // nailed together now, and nails are forge work - so the bench you need to
            // build one is in step with what it is made of.
            Station = config.Bind("Upgrades", "Station", "forge",
                "Prefab name of the crafting station you must stand near to build these. "
                + "The forge, because both upgrades are held together with nails and a "
                + "workbench could never have made them. Empty or an unknown name leaves "
                + "the donor's, which is the workbench.");

            Range = config.Bind("Upgrades", "Range", 4f,
                "How close an upgrade must be to the station it feeds.");

            // One. An upgrade is a one-time improvement to a station, not a currency you
            // spend until capacity stops mattering.
            //
            // At two, the figures the whole design is built on stopped meaning anything:
            // the kiln's 25 becomes 50 becomes 75, and "a charcoal kiln landing on a round
            // 50" - the reason the woodrack adds 25 where the trough adds 20 - was only
            // true if you happened to build exactly one. A second bin now changes nothing
            // and says so when you look at it, because a silent no-op reads as a bug.
            MaxPerStation = config.Bind("Upgrades", "MaxPerStation", 1,
                "How many upgrades of one kind count for a single station. One, because "
                + "these are a one-time improvement rather than something to stack - the "
                + "capacity figures are chosen to land on a round number exactly once. "
                + "Raising it stacks them again; a bin that is not counting says so when "
                + "you look at it.");

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

            // The nails carry the gate now, so the loose bronze that used to do it is gone
            // rather than stacked on top - iron nails already require a smelter to have
            // made iron, which is the same statement bronze was making and a biome later.
            // Fine wood over ordinary wood on both, so the two upgrades are joinery rather
            // than something knocked together from felled trunks.
            UpgradePrefabs.Trough.Cost = config.Bind("Trough", "Cost",
                "FineWood:20,IronNails:15",
                "Build cost, as Item:Amount pairs. The iron nails put it a biome beyond the "
                + "smelter it upgrades, so it is an improvement you return to make rather "
                + "than part of the original build.");

            // stoker_trough_casks, not stoker_trough_barrels. Same two casks on the same
            // kerb; what changed is the cask itself, which read as modded for three
            // measurable reasons - it was a straight tube where a cask bulges, its staves
            // were modelled as twenty square posts where vanilla paints them, and at
            // 0.90 x 1.35 it stood a head over the 0.84 x 1.10 barrell it was imitating.
            // The prefab is still called Trough, so nothing standing in a world notices.
            UpgradePrefabs.Trough.Model = config.Bind("Trough", "Model",
                "stoker_trough_casks.obj",
                "The OBJ loaded from beside the DLL. Its .col sidecar supplies the "
                + "collision and its _icon.png the hammer icon, both matched by name - so "
                + "dropping in a new model brings its own shape and picture with it.");

            // 1.5, because the modelled size was measurably too small. A vanilla barrell
            // is 0.84m across and 1.10m tall; ours were 0.57 and 0.86. At 1.5 each cask is
            // 0.86 x 1.29, which is a real barrel sat beside a real smelter - and the
            // smelter is 3.03 x 4.24 x 2.58, so there is no danger of crowding it.
            UpgradePrefabs.Trough.Scale = config.Bind("Trough", "Scale", 1.5f,
                "Overall size of the trough. Scales the collision with it, since the boxes "
                + "are children of the piece.");

            // One donor for the whole cask, and piece_chest_barrel because it is one: a
            // barrel of the same size, built the same way, whose 64px sheet carries brown
            // timber on the left and grey steel on the right. The staves take the timber,
            // the hoops take the steel, and both come off one material - which is what
            // every vanilla piece does and what this one was not doing. Before this the
            // wood came from piece_chest_wood and the hoops from piece_artisanstation, so
            // one small cask wore two objects' palettes that were never painted together.
            UpgradePrefabs.Trough.SkinDonors = config.Bind("Trough", "SkinDonors",
                "piece_chest_barrel",
                "Which vanilla prefab this piece borrows its surface from. A bare prefab "
                + "name covers the whole piece, which is the usual case and matches how "
                + "vanilla builds a piece - one texture carrying every substance it is "
                + "made of. group=prefab pairs override a single group. Empty uses the "
                + "general list. Ore and coal keep their own surfaces either way: they "
                + "are what is in the piece rather than what it is made of, and vanilla "
                + "gives a smelter's ore heap its own material too.");

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

            // This used to argue against any bronze at all, on the grounds that a charcoal
            // kiln is a Black Forest build and an upgrade you cannot raise alongside its
            // station is one you never build. The bronze nails overrule that on purpose:
            // both upgrades now sit a tier behind the station they serve, which makes them
            // a second visit rather than part of the first. Recorded rather than quietly
            // deleted, because the old reasoning was sound and was replaced by a choice.
            //
            // Hide in place of the stone it used to want. A rack keeps cut wood off the
            // ground and out of the rain, so a hide reads as what it is for in a way a
            // footing of stone never did.
            UpgradePrefabs.Woodrack.Cost = config.Bind("Woodrack", "Cost",
                "FineWood:25,DeerHide:20,BronzeNails:25",
                "Build cost, as Item:Amount pairs. The bronze nails put it a tier behind "
                + "the charcoal kiln it serves, so it is something you come back and add "
                + "rather than raise alongside the kiln itself.");

            // stoker_rack_courses, not stoker_rack_lean. The lean-to's logs were built by
            // a helper that picked a cross section at random - three, four, five, six or
            // seven sides - so at 2 metres the rack read as a frame packed with rubble.
            // Vanilla varies a woodpile's diameter and never its cross section. The roof
            // also sloped the wrong way: -17 degrees about x lifts the front edge, which
            // is why it read as a table.
            UpgradePrefabs.Woodrack.Model = config.Bind("Woodrack", "Model",
                "stoker_rack_courses.obj",
                "The OBJ loaded from beside the DLL, with its .col and _icon.png matched "
                + "by name.");

            // Same reasoning. wood_stack, vanilla's own woodpile, is 2.31 x 1.30 x 2.46;
            // ours was 1.35 x 1.36 x 1.02, well under half its footprint. At 1.5 it is
            // 2.03 x 2.04 x 1.53 - taller and shallower than vanilla's, which suits a
            // roofed rack rather than a free heap.
            UpgradePrefabs.Woodrack.Scale = config.Bind("Woodrack", "Scale", 1.5f,
                "Overall size of the woodrack. Scales the collision with it, since the "
                + "boxes are children of the piece.");

            // 25 rather than the trough's 20, because a charcoal kiln starts at 25 and this
            // is aimed at landing on a round 50. The two upgrades need different figures for
            // the same reason a percentage would not do: the stations are different sizes,
            // and what matters is the number you end on.
            // Round bark rather than sawn planking. This piece is a stack of logs, and
            // piece_chest_wood's slice of atlas carries the chest's dark iron banding -
            // which landed on the sawn ends and rendered them almost black. wood_wall_log
            // is uniformly timber, and its rect is 0.424 against 0.231, so the wood group
            // reaches the full target density here instead of clamping at 20.
            // Bare, so it covers the piece rather than only its wood group - though the
            // rack has nothing but wood now, which is the point. wood_wall_log is round
            // bark-on timber with real sawn-end discs painted in the corner of its sheet,
            // and a woodrack is a stack of logs.
            UpgradePrefabs.Woodrack.SkinDonors = config.Bind("Woodrack", "SkinDonors",
                "wood_wall_log",
                "Which vanilla prefab this piece borrows its surface from. A bare prefab "
                + "name covers the whole piece; group=prefab pairs override a single "
                + "group. Empty uses the general list.");

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
