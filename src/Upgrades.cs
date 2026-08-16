// No `using System` here: this file leans on UnityEngine.Object throughout, and
// importing System makes every bare `Object` ambiguous with System.Object.
using System.Collections.Generic;
using System.IO;
using BepInEx.Configuration;
using HarmonyLib;
using UnityEngine;

namespace Stoker
{
    /// <summary>
    /// One of the two things you build beside a station to make it hold more.
    ///
    /// Two pieces rather than one, because a charcoal kiln eats wood and a smelter eats
    /// ore and coal. A single generic bin looked like it belonged to neither - it was a
    /// box that said "storage" and nothing else. The woodrack is a rack of split logs and
    /// the trough has two bays, one heaped with ore and one with coal, so each piece says
    /// what its station is fed just by standing there.
    ///
    /// Which one serves which station is decided on the station's own numbers rather than
    /// a list of prefab names: a station with a fuel slot takes the trough, one without
    /// takes the woodrack. That is the same component-level matching the capacity
    /// component uses, so a modded station lands on the right side without being named.
    /// </summary>
    internal sealed class UpgradeDef
    {
        /// <summary>
        /// Permanent. ZNetScene keys on name.GetStableHashCode() and saved ZDOs store that
        /// hash, so renaming one of these destroys every copy already standing in a world.
        /// The trough is still called stoker_hopper for exactly that reason - it inherited
        /// the name from the single generic bin it replaced, and changing it now would take
        /// out anything built while that bin existed.
        /// </summary>
        public string PrefabName;

        public ConfigEntry<string> Name;
        public ConfigEntry<string> Cost;
        public ConfigEntry<string> Model;
        public ConfigEntry<float> Scale;

        /// <summary>
        /// Set instead of the config entries above on a comparison variant, which exists
        /// for one session and does not deserve six settings in the file.
        /// </summary>
        public string LiteralName;
        public string LiteralModel;

        /// <summary>
        /// Which vanilla prefab this piece borrows each material group from, when the
        /// general list is not what it wants. The woodrack is stacked round timber and
        /// wants bark off wood_wall_log; the trough is sawn staves and planking and wants
        /// piece_chest_wood. One list for both meant one of them always wore the other's
        /// surface.
        /// </summary>
        public ConfigEntry<string> SkinDonors;

        /// <summary>
        /// group -&gt; prefab, or null when this piece takes the general list.
        ///
        /// An entry with no group - a bare prefab name - covers the whole piece, and that
        /// is now the normal way to write one. Every vanilla piece is a single material on
        /// a single submesh: barrell, wood_stack, piece_chest_wood, wood_wall_log, the
        /// smelter, the charcoal kiln, all of them. They manage it by painting everything
        /// the object is made of onto one sheet - piece_chest_barrel's is 64 pixels split
        /// down the middle, wood on the left and grey metal on the right, with the modelled
        /// hoops mapped onto the metal half.
        ///
        /// Naming a donor per group was how this piece ended up wearing four different
        /// objects' palettes at once, none of which were painted to sit together. One
        /// donor, and the groups reach different patches of its sheet instead.
        /// </summary>
        public IDictionary<string, string> Skins
        {
            get
            {
                if (SkinDonors == null || string.IsNullOrEmpty(SkinDonors.Value)) return null;

                var map = new Dictionary<string, string>(
                    System.StringComparer.OrdinalIgnoreCase);
                foreach (var entry in SkinDonors.Value.Split(','))
                {
                    var parts = entry.Split('=');

                    if (parts.Length == 1)
                    {
                        var whole = parts[0].Trim();
                        // Fully qualified: this class has a Skins property of its own, and
                        // it would otherwise shadow the static class being reached for.
                        if (whole.Length > 0) map[Stoker.Skins.Everything] = whole;
                        continue;
                    }

                    if (parts.Length != 2) continue;

                    var group = parts[0].Trim();
                    var donor = parts[1].Trim();
                    if (group.Length > 0 && donor.Length > 0) map[group] = donor;
                }

                return map.Count > 0 ? map : null;
            }
        }

        public string NameValue { get { return Name != null ? Name.Value : LiteralName; } }
        public string ModelValue { get { return Model != null ? Model.Value : LiteralModel; } }
        public float ScaleValue { get { return Scale != null ? Scale.Value : 1f; } }

        /// <summary>
        /// How much each of these adds, in items, to the station it serves.
        ///
        /// Per piece rather than one figure for the mod, because the two cannot share one.
        /// A charcoal kiln holds 25 and wants to land on 50; a smelter holds 10 and wants to
        /// land on 30. That is +25 and +20, and no single rule - flat or proportional -
        /// produces both. Multiplying gave the kiln its 50 and left the smelter at 20.
        /// </summary>
        public ConfigEntry<int> OreCapacity;

        /// <summary>
        /// Null on an upgrade that only ever serves stations with no fuel slot, where it
        /// would be a config entry that can never do anything.
        /// </summary>
        public ConfigEntry<int> FuelCapacity;

        public string Description;

        /// <summary>True for the trough, false for the woodrack.</summary>
        public bool ServesFuelled;

        public GameObject Prefab;
    }

    /// <summary>
    /// The component on a placed upgrade. It carries which kind it is, so a woodrack
    /// standing near a smelter does not quietly count towards it.
    /// </summary>
    internal class UpgradeBin : MonoBehaviour, Hoverable
    {
        private static readonly List<UpgradeBin> All = new List<UpgradeBin>();

        /// <summary>
        /// Public and a plain field on purpose: Unity copies serialised fields from the
        /// prefab into every instance, so setting it once while building the prefab is
        /// what makes a placed copy remember what it is.
        /// </summary>
        public bool m_servesFuelled;

        private Piece _piece;
        private GameObject _connection;

        /// <summary>False on a placement ghost, which is a copy of the prefab with no ZDO.</summary>
        private bool _placed;

        private void Awake()
        {
            _piece = GetComponent<Piece>();

            // Vanilla's StationExtension.Awake gates its whole registration on exactly this
            // check, and the reason is the placement ghost: the translucent copy following
            // your cursor is a real instance of the prefab with every component awake on it,
            // and the only thing separating it from a placed piece is that it has no ZDO.
            //
            // Without the guard it registers as a real upgrade - so it draws its own link
            // from wherever the cursor happens to be, and counts towards the capacity of
            // whatever station it is currently floating near, before you have built anything.
            var nview = GetComponent<ZNetView>();
            _placed = nview != null && nview.GetZDO() != null;
            if (!_placed) return;

            All.Add(this);
        }

        private void OnDestroy()
        {
            StopConnectionEffect();
            if (_placed) All.Remove(this);
        }

        // ------------------------------------------------------------------ the link

        /// <summary>
        /// The run of motes from this piece to the station it feeds - the same thing a
        /// chopping block draws to its workbench.
        ///
        /// Lifted from StationExtension.StartConnectionEffect rather than invented, because
        /// the game already has one answer to "show which station this is attached to" and
        /// a second one that looked slightly different would just read as wrong. The two
        /// details that matter are both non-obvious: the effect is rotated so its local +Z
        /// faces the station, and then *scaled* along Z by the distance, which is what turns
        /// a stationary puff into something that spans the gap.
        ///
        /// Poked from GetHoverText, exactly as vanilla does for a non-continuous extension.
        /// Looking at the piece is the moment you want the answer, and a base with eight
        /// smelters in it would be a light show if every upgrade emitted all the time.
        /// </summary>
        private void PokeEffect(float timeout = 1f)
        {
            if (!_placed || !StokerConfig.ShowLink.Value) return;

            var station = SmelterCapacity.Nearest(transform.position, m_servesFuelled);
            if (station == null) return;

            var from = transform.position + Vector3.up * StokerConfig.LinkHeight.Value;
            var to = station.ConnectionPoint;

            if (_connection == null)
            {
                var prefab = ConnectionPrefab();
                if (prefab == null) return;

                _connection = Instantiate(prefab, from, Quaternion.identity);
            }

            var span = to - from;
            if (span.sqrMagnitude < 0.0001f) return;

            // Costs nothing and rules one thing out: a prefab held inactive instantiates
            // inactive, and an inactive effect is indistinguishable from a broken one.
            if (!_connection.activeSelf) _connection.SetActive(true);

            _connection.transform.position = from;
            _connection.transform.rotation = Quaternion.LookRotation(span.normalized);
            _connection.transform.localScale = new Vector3(1f, 1f, span.magnitude);

            Describe(from, to, span);

            CancelInvoke("StopConnectionEffect");
            Invoke("StopConnectionEffect", timeout);
        }

        /// <summary>
        /// Says what the link actually is, for the first few pokes of a session.
        ///
        /// Here because the effect was being created without being visible, and every
        /// explanation for that - wrong distance, wrong end point, an inactive instance, a
        /// prefab with no renderer on it - is a number that can simply be read rather than
        /// guessed at.
        /// </summary>
        private static int _pokesDescribed;

        private void Describe(Vector3 from, Vector3 to, Vector3 span)
        {
            if (_pokesDescribed >= 3 || _connection == null) return;
            _pokesDescribed++;

            StokerPlugin.Log.LogInfo(string.Format(
                "Link poke {0}: {1} -> {2}, {3:0.00}m, active {4}/{5}, {6} particle "
                + "system(s), {7} renderer(s).",
                _pokesDescribed, from, to, span.magnitude,
                _connection.activeSelf, _connection.activeInHierarchy,
                _connection.GetComponentsInChildren<ParticleSystem>(true).Length,
                _connection.GetComponentsInChildren<Renderer>(true).Length));
        }

        private void StopConnectionEffect()
        {
            if (_connection == null) return;

            Destroy(_connection);
            _connection = null;
        }

        /// <summary>
        /// The vanilla connection effect, borrowed off whichever station extension the game
        /// has loaded.
        ///
        /// Found by component rather than by name - anything carrying a StationExtension
        /// with a connection prefab will do, so this does not depend on the forge and
        /// workbench extensions keeping their current prefab names. Cached because it is a
        /// scan, and cleared with the rest of the borrowed art when the item list changes.
        /// </summary>
        private static GameObject _connectionPrefab;
        private static bool _connectionSearched;

        private static GameObject ConnectionPrefab()
        {
            if (_connectionSearched) return _connectionPrefab;
            _connectionSearched = true;

            var scene = ZNetScene.instance;
            if (scene == null) return null;

            foreach (var prefab in scene.m_prefabs)
            {
                if (prefab == null) continue;

                var extension = prefab.GetComponent<StationExtension>();
                if (extension == null || extension.m_connectionPrefab == null) continue;

                _connectionPrefab = extension.m_connectionPrefab;
                StokerPlugin.Log.LogInfo(
                    "Link effect borrowed from " + prefab.name + " ("
                    + _connectionPrefab.name + ").");
                return _connectionPrefab;
            }

            StokerPlugin.Log.LogWarning(
                "No StationExtension with a connection effect is loaded - upgrades will not "
                + "draw a link to their station.");
            return null;
        }

        public static void ForgetConnectionPrefab()
        {
            _connectionPrefab = null;
            _connectionSearched = false;
        }

        /// <summary>How many upgrades of the matching kind are close enough to count.</summary>
        public static int CountNear(Vector3 point, bool fuelled)
        {
            var range = StokerConfig.Range.Value;
            var count = 0;

            foreach (var bin in All)
            {
                if (bin == null || bin.m_servesFuelled != fuelled) continue;
                if (Vector3.Distance(bin.transform.position, point) <= range) count++;
            }

            return count;
        }

        /// <summary>
        /// How many upgrades of this kind stand closer to the same station than this one.
        ///
        /// Which is how a bin knows whether it is doing anything. The upgrade is one-time
        /// now, so the second one built beside a station changes nothing at all - and
        /// without being told, that is indistinguishable from a broken mod. Nearest wins,
        /// because it is stable: distance does not change when a piece is destroyed and
        /// rebuilt, where "whichever registered first" would hand the credit around.
        /// </summary>
        private int CloserToStation(Vector3 station)
        {
            var mine = Vector3.Distance(transform.position, station);
            var range = StokerConfig.Range.Value;
            var ahead = 0;

            foreach (var bin in All)
            {
                if (bin == null || bin == this || bin.m_servesFuelled != m_servesFuelled)
                    continue;

                var theirs = Vector3.Distance(bin.transform.position, station);
                if (theirs > range) continue;

                // Ties broken on the instance id, so two bins the same distance out do not
                // both call themselves redundant and leave the station apparently unserved.
                if (theirs < mine || (theirs == mine && bin.GetInstanceID() < GetInstanceID()))
                    ahead++;
            }

            return ahead;
        }

        public string GetHoverName()
        {
            return _piece != null ? _piece.m_name : "";
        }

        public string GetHoverText()
        {
            // Vanilla pokes the link effect from here too, for any extension that is not
            // continuously connected. Looking at the piece is the moment you are asking
            // which station it belongs to - and the effect answers that on its own, by
            // drawing a run of motes to the station, which is how a chopping block says
            // the same thing without a word of text.
            PokeEffect();

            var name = GetHoverName();

            // Just the name once it is working. The station and its new capacity used to
            // be appended - "Charcoal Kiln (ore 50)" - which is build-time information
            // sitting permanently on a finished object. Vanilla's extensions do not
            // narrate themselves either: a chopping block reads "Chopping block" and
            // nothing more, and you learn what it is attached to from the motes.
            //
            // The unattached case keeps its line, because that one is not information
            // about the piece, it is the piece telling you it is doing nothing.
            var station = SmelterCapacity.Nearest(transform.position, m_servesFuelled);

            if (station == null)
            {
                return Localization.instance.Localize(
                    name + "\n<color=grey>not beside anything it can feed</color>");
            }

            // The one case that does need saying. An upgrade is one-time, so a second one
            // beside the same station does nothing whatsoever - and silence there is
            // indistinguishable from the mod being broken, which is the reading a player
            // will reach for first.
            var ahead = CloserToStation(station.transform.position);
            if (ahead >= Mathf.Max(1, StokerConfig.MaxPerStation.Value))
            {
                return Localization.instance.Localize(
                    name + "\n<color=grey>already upgraded - this one adds nothing</color>");
            }

            return Localization.instance.Localize(name);
        }
    }

    /// <summary>
    /// Builds both upgrade prefabs at runtime by cloning a vanilla piece, so the mod stays
    /// a single DLL with no asset bundle. Only the donor's machinery is kept - ZNetView,
    /// Piece, WearNTear, placement rules - while the look, the collision and the icon are
    /// all replaced with our own.
    /// </summary>
    internal static class UpgradePrefabs
    {
        public static readonly UpgradeDef Trough = new UpgradeDef
        {
            PrefabName = "stoker_hopper",
            // Says what it upgrades before it says anything else. The build menu shows
            // this under the name, and the star in the corner only tells you that the
            // piece is an upgrade - never of what.
            Description = "Smelter improvement. Ore on one side, coal on the other. A "
                          + "smelter or furnace beside it holds more of both.",
            ServesFuelled = true,
        };

        public static readonly UpgradeDef Woodrack = new UpgradeDef
        {
            PrefabName = "stoker_woodrack",
            Description = "Kiln improvement. Split logs, stacked and under cover. A "
                          + "charcoal kiln beside it holds more wood.",
            ServesFuelled = false,
        };

        public static readonly UpgradeDef[] All = { Trough, Woodrack };

        /// <summary>The upgrade that serves stations of this kind.</summary>
        public static UpgradeDef For(bool fuelled)
        {
            return fuelled ? Trough : Woodrack;
        }

        // ------------------------------------------------------------------ variants

        private static List<UpgradeDef> _variants;

        /// <summary>
        /// One buildable piece per model file, so every candidate can stand in a row and be
        /// compared in the game's own light at the same time of day.
        ///
        /// A config line and a relaunch per look is the alternative, and it compares a model
        /// against a memory of the last one rather than against the model itself. This is
        /// the same reason the design renders are a contact sheet and not one image at a
        /// time.
        ///
        /// Every one of these is a registered prefab, so anything built from them is a real
        /// ZDO keyed on a name that stops existing the moment VariantMode goes off - and
        /// ZNetScene discards a ZDO whose prefab name will not resolve, silently. Build them
        /// somewhere you do not mind losing.
        /// </summary>
        private static List<UpgradeDef> Variants()
        {
            if (_variants != null) return _variants;

            _variants = new List<UpgradeDef>();
            if (!StokerConfig.VariantMode.Value) return _variants;

            var dir = Path.GetDirectoryName(typeof(UpgradePrefabs).Assembly.Location);

            foreach (var path in Directory.GetFiles(dir, "stoker_*.obj"))
            {
                var stem = Path.GetFileNameWithoutExtension(path);
                var lower = stem.ToLowerInvariant();

                var isTrough = lower.Contains("trough");
                if (!isTrough && !lower.Contains("rack")) continue;

                _variants.Add(new UpgradeDef
                {
                    // Prefixed so a variant can never collide with a real piece's name, and
                    // so the throwaway ones are obvious in a ZDO dump.
                    PrefabName = "stoker_var_" + stem,
                    LiteralName = Pretty(stem),
                    LiteralModel = stem + ".obj",
                    Description = "Comparison variant. Not a real piece - turn VariantMode "
                                  + "off and it stops existing.",
                    ServesFuelled = isTrough,
                    OreCapacity = isTrough ? Trough.OreCapacity : Woodrack.OreCapacity,
                    FuelCapacity = isTrough ? Trough.FuelCapacity : null,
                });
            }

            if (_variants.Count > 0)
                StokerPlugin.Log.LogWarning(
                    "VARIANT MODE: " + _variants.Count + " comparison piece(s) on the hammer "
                    + "at one wood each. Anything built from them is destroyed when "
                    + "VariantMode goes off.");

            return _variants;
        }

        /// <summary>stoker_trough_bench -> "var: trough bench", which sorts together.</summary>
        private static string Pretty(string stem)
        {
            return "var: " + stem.Replace("stoker_", "").Replace("_", " ");
        }

        private static IEnumerable<UpgradeDef> Active()
        {
            foreach (var def in All) yield return def;
            foreach (var def in Variants()) yield return def;
        }

        private static GameObject _holder;

        public static bool Ready
        {
            get
            {
                if (ZNetScene.instance == null) return false;

                foreach (var def in Active())
                    if (ZNetScene.instance.GetPrefab(def.PrefabName) == null) return false;

                return true;
            }
        }

        /// <summary>Idempotent, and safe to call every frame until it takes.</summary>
        public static bool Register()
        {
            if (!StokerConfig.Enabled.Value) return true;

            if (ZNetScene.instance == null || ObjectDB.instance == null) return false;
            if (Ready && InHammer()) return true;

            foreach (var def in Active())
            {
                if (def.Prefab == null) def.Prefab = Build(def);
                if (def.Prefab == null) return false;
            }

            AddToScene();
            AddToHammer();
            return Ready;
        }

        private static GameObject Donor()
        {
            var scene = ZNetScene.instance;

            // Configured first, then a fallback, because a name that does not resolve is
            // skipped silently by the game and the piece would just never appear.
            foreach (var name in new[] { StokerConfig.Donor.Value, "piece_chest_wood" })
            {
                if (string.IsNullOrEmpty(name)) continue;

                var found = scene.GetPrefab(name);
                if (found != null) return found;

                StokerPlugin.Log.LogWarning("Upgrade donor '" + name + "' does not exist.");
            }

            return null;
        }

        private static GameObject Build(UpgradeDef def)
        {
            var source = Donor();
            if (source == null) return null;

            if (_holder == null)
            {
                _holder = new GameObject("StokerUpgradeHolder");
                _holder.SetActive(false);
                Object.DontDestroyOnLoad(_holder);
            }

            // Always clone inside an inactive holder with init suppressed, or the clone
            // tries to network-register itself while it is still half-built.
            var previous = ZNetView.m_forceDisableInit;
            ZNetView.m_forceDisableInit = true;

            GameObject clone;
            try { clone = Object.Instantiate(source, _holder.transform); }
            finally { ZNetView.m_forceDisableInit = previous; }

            clone.name = def.PrefabName;

            // It is a bin, not storage. Leaving the Container on would give it an inventory
            // the station never reads, which is exactly the confusion to avoid.
            //
            // DestroyImmediate, not Destroy: ordinary Destroy is deferred to the end of the
            // frame, and this prefab is registered and can be built from within that frame -
            // which would hand out an upgrade that really is a chest.
            foreach (var container in clone.GetComponentsInChildren<Container>(true))
                Object.DestroyImmediate(container);

            // The model swap destroys MeshRenderer objects, and a particle system's renderer
            // is a ParticleSystemRenderer - not one of those - so anything the donor emitted
            // would otherwise survive onto a piece that no longer looks anything like it.
            // The link effect below is the one deliberate effect these pieces have.
            foreach (var particles in clone.GetComponentsInChildren<ParticleSystem>(true))
            {
                if (particles == null) continue;

                StokerPlugin.Log.LogInfo("Stripped inherited particle system '"
                                         + particles.name + "' from " + def.PrefabName + ".");
                Object.DestroyImmediate(particles);
            }

            var piece = clone.GetComponent<Piece>();
            if (piece != null)
            {
                piece.m_name = def.NameValue;
                piece.m_description = def.Description;
                piece.m_resources = Requirements(StokerConfig.CostNow(def));

                // Inherited from the donor, which is a chest and so files under Furniture.
                // These upgrade a smelter, so they belong on the same hammer tab as one.
                piece.m_category = Piece.PieceCategory.Crafting;

                // The star in the corner of the build menu icon. It is not part of the icon
                // art - Hud builds each slot from a prefab carrying an "upgrade" child and
                // does m_upgrade.SetActive(piece.m_isUpgrade) - so it is a flag rather than
                // something to draw, and these are exactly what it means by an upgrade.
                piece.m_isUpgrade = true;

                // The forge, not the workbench the donor came with.
                //
                // A chest is workbench work and these are not: both upgrades are nailed
                // together now, and nails are a forge product. It also puts the station
                // requirement in step with the cost - there is no point asking for iron
                // nails at a bench that could never have made them.
                //
                // Left alone rather than nulled if the forge cannot be found. A piece with
                // no station requirement at all is buildable anywhere, which is a quieter
                // and worse failure than one asking for the wrong bench.
                var station = StationNamed(StokerConfig.Station.Value);
                if (station != null) piece.m_craftingStation = station;
            }

            UpgradeModel.Apply(clone, def.ModelValue, def.Skins);

            var scale = Mathf.Max(0.05f, def.ScaleValue);
            clone.transform.localScale = new Vector3(scale, scale, scale);

            var bin = clone.GetComponent<UpgradeBin>() ?? clone.AddComponent<UpgradeBin>();
            bin.m_servesFuelled = def.ServesFuelled;

            // After the model, the materials and the scale, because the icon is a
            // photograph of the finished piece and none of that has happened yet where it
            // used to sit. Taken there it would have shown the donor's barrel wearing the
            // donor's chest textures at the donor's size - a picture of the thing this
            // piece was cloned from rather than of the piece.
            if (piece != null)
            {
                var shot = IconRender.Shoot(clone, def.PrefabName) ?? LoadIcon(def);
                if (shot != null) piece.m_icon = shot;
            }

            StokerPlugin.Log.LogInfo("Built " + def.PrefabName + " from " + source.name + ".");
            return clone;
        }

        /// <summary>
        /// The CraftingStation component off a named prefab.
        ///
        /// Via PropIndex rather than ZNetScene, for the same reason the materials go that
        /// way: plenty of prefabs are reachable without carrying a ZNetView.
        /// </summary>
        private static CraftingStation StationNamed(string name)
        {
            if (string.IsNullOrEmpty(name)) return null;

            var prefab = PropIndex.Find(name);
            if (prefab == null)
            {
                StokerPlugin.Log.LogWarning(
                    "No prefab called '" + name + "' for the crafting station requirement - "
                    + "the upgrades keep the donor's, which is the workbench.");
                return null;
            }

            var station = prefab.GetComponent<CraftingStation>()
                          ?? prefab.GetComponentInChildren<CraftingStation>(true);

            if (station == null)
            {
                StokerPlugin.Log.LogWarning(
                    "'" + name + "' exists but is not a crafting station - the upgrades keep "
                    + "the donor's.");
            }

            return station;
        }

        // ------------------------------------------------------------------ the icon

        /// <summary>
        /// The icon, read off disk beside the DLL.
        ///
        /// Without this the piece keeps the donor's icon, which is a picture of a barrel -
        /// and the thing you place is not a barrel. An icon that shows the wrong object is
        /// worse than a plain one, because the hammer menu is where you choose.
        /// </summary>
        private static Sprite LoadIcon(UpgradeDef def)
        {
            var dir = Path.GetDirectoryName(typeof(UpgradePrefabs).Assembly.Location);
            var model = def.ModelValue;
            if (string.IsNullOrEmpty(model)) return null;

            var path = Path.Combine(dir, Path.GetFileNameWithoutExtension(model) + "_icon.png");

            if (!File.Exists(path))
            {
                StokerPlugin.Log.LogWarning(
                    "No icon beside the dll for " + def.PrefabName + " - it will wear the "
                    + "donor's, which is a picture of something else. Expected "
                    + Path.GetFileName(path) + ".");
                return null;
            }

            try
            {
                // Bilinear, not point. Everything else in these mods wants point filtering,
                // but a 128px source drawn into a smaller slot is always being minified,
                // and point-sampling a minified image shimmers as the menu scrolls.
                var texture = new Texture2D(2, 2, TextureFormat.RGBA32, false)
                {
                    filterMode = FilterMode.Bilinear,
                    wrapMode = TextureWrapMode.Clamp
                };

                if (!LoadPng(texture, File.ReadAllBytes(path))) return null;

                texture.name = def.PrefabName + "_icon";
                texture.hideFlags = HideFlags.HideAndDontSave;

                StokerPlugin.Log.LogInfo(string.Format("Icon for {0}: {1} ({2}x{3}).",
                    def.PrefabName, Path.GetFileName(path), texture.width, texture.height));

                return Sprite.Create(texture,
                                     new Rect(0f, 0f, texture.width, texture.height),
                                     new Vector2(0.5f, 0.5f));
            }
            catch (System.Exception e)
            {
                StokerPlugin.Log.LogError("Could not read " + path + ": " + e.Message);
                return null;
            }
        }

        /// <summary>
        /// Texture2D.LoadImage, by reflection.
        ///
        /// It lives in UnityEngine.ImageConversionModule, which targets netstandard 2.1
        /// while this builds against net462 - referencing it outright fails the build with
        /// CS1705. The method is there at runtime regardless, so reaching it this way costs
        /// one lookup and removes the whole problem.
        /// </summary>
        private static bool LoadPng(Texture2D texture, byte[] data)
        {
            var type = AccessTools.TypeByName("UnityEngine.ImageConversion");
            if (type == null)
            {
                StokerPlugin.Log.LogWarning(
                    "UnityEngine.ImageConversion is missing - cannot read icons.");
                return false;
            }

            var method = AccessTools.Method(type, "LoadImage",
                                            new[] { typeof(Texture2D), typeof(byte[]) })
                         ?? AccessTools.Method(type, "LoadImage",
                                               new[] { typeof(Texture2D), typeof(byte[]),
                                                       typeof(bool) });

            if (method == null)
            {
                StokerPlugin.Log.LogWarning(
                    "No LoadImage overload found on UnityEngine.ImageConversion.");
                return false;
            }

            var args = method.GetParameters().Length == 3
                ? new object[] { texture, data, false }
                : new object[] { texture, data };

            return (bool)method.Invoke(null, args);
        }

        // ------------------------------------------------------------------ registering

        private static Piece.Requirement[] Requirements(string spec)
        {
            var list = new List<Piece.Requirement>();

            foreach (var entry in (spec ?? "").Split(','))
            {
                var parts = entry.Split(':');
                if (parts.Length != 2) continue;

                var itemName = parts[0].Trim();
                if (itemName.Length == 0) continue;

                int amount;
                if (!int.TryParse(parts[1].Trim(), out amount) || amount <= 0) continue;

                var prefab = ObjectDB.instance.GetItemPrefab(itemName);
                var drop = prefab != null ? prefab.GetComponent<ItemDrop>() : null;
                if (drop == null)
                {
                    StokerPlugin.Log.LogWarning("Cost mentions unknown item '" + itemName + "'.");
                    continue;
                }

                list.Add(new Piece.Requirement
                {
                    m_resItem = drop,
                    m_amount = amount,
                    m_recover = true
                });
            }

            return list.ToArray();
        }

        private static void AddToScene()
        {
            var scene = ZNetScene.instance;

            foreach (var def in Active())
            {
                if (def.Prefab == null || scene.GetPrefab(def.PrefabName) != null) continue;

                if (!scene.m_prefabs.Contains(def.Prefab)) scene.m_prefabs.Add(def.Prefab);

                try
                {
                    // ZNetScene needs both the list and the private dictionary. The
                    // dictionary is built in Awake and never rebuilt, so adding to the
                    // list alone does nothing at all.
                    var named = (Dictionary<int, GameObject>)
                        AccessTools.Field(typeof(ZNetScene), "m_namedPrefabs").GetValue(scene);
                    named[def.PrefabName.GetStableHashCode()] = def.Prefab;
                }
                catch (System.Exception e)
                {
                    StokerPlugin.Log.LogError(
                        "Could not register " + def.PrefabName + ": " + e.Message);
                }
            }
        }

        /// <summary>
        /// Whether every active upgrade is already in the hammer's current piece table.
        ///
        /// Asked of the table rather than remembered in a static bool. ObjectDB is rebuilt
        /// per world, so the Hammer from the last one is a different object with a
        /// different list - and a flag that says "already done" then keeps the upgrades out
        /// of the build menu for the whole of the second world of a session. Stow lost a
        /// built piece to the same mistake in its harsher form, where the stale flag guarded
        /// the ZNetScene registration and every ZDO of the prefab was discarded.
        /// </summary>
        private static bool InHammer()
        {
            var table = HammerPieces();
            if (table == null) return false;

            foreach (var def in Active())
            {
                if (def.Prefab == null) return false;
                if (!table.m_pieces.Contains(def.Prefab)) return false;
            }

            return true;
        }

        private static PieceTable HammerPieces()
        {
            if (ObjectDB.instance == null) return null;

            var hammer = ObjectDB.instance.GetItemPrefab("Hammer");
            var drop = hammer != null ? hammer.GetComponent<ItemDrop>() : null;
            if (drop == null || drop.m_itemData == null || drop.m_itemData.m_shared == null)
                return null;

            var table = drop.m_itemData.m_shared.m_buildPieces;
            return table != null && table.m_pieces != null ? table : null;
        }

        private static void AddToHammer()
        {
            var table = HammerPieces();
            if (table == null) return;

            var added = 0;
            foreach (var def in Active())
            {
                if (def.Prefab == null) return;
                if (table.m_pieces.Contains(def.Prefab)) continue;

                table.m_pieces.Add(def.Prefab);
                added++;
            }

            // Logged on the add, not on the call: this is retried every frame and an
            // already-satisfied retry would write a line per frame.
            if (added > 0)
                StokerPlugin.Log.LogInfo(added + " upgrade(s) added to the hammer.");
        }
    }
}
