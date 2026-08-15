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
        private ParticleSystem[] _effects;

        /// <summary>Said once per session rather than once per placed piece.</summary>
        private static bool _reported;

        private void Awake()
        {
            _piece = GetComponent<Piece>();
            All.Add(this);

            // Nothing in this mod creates a particle system. Any that are here came across
            // with the donor clone and survived the model swap, because that destroys
            // MeshRenderer objects and a particle system's renderer is a
            // ParticleSystemRenderer - which is not one. Rather than leave them spraying in
            // whatever direction the donor wanted, they are pointed at the station this
            // piece is feeding, and stopped when it is feeding nothing.
            _effects = GetComponentsInChildren<ParticleSystem>(true);

            if (!_reported)
            {
                _reported = true;
                StokerPlugin.Log.LogInfo(_effects.Length == 0
                    ? "No inherited particle systems on an upgrade - anything you can see "
                      + "moving near one is the world's, not ours."
                    : "Inherited particle systems on an upgrade: " + Names(_effects));
            }

            // The station cannot move, so this only has to catch it being built, destroyed
            // or falling down. Offset from the capacity poll so the two do not share a frame.
            if (_effects.Length > 0) InvokeRepeating("AimEffects", 1.5f, 3f);
        }

        private static string Names(ParticleSystem[] systems)
        {
            var names = new List<string>();
            foreach (var system in systems)
                if (system != null) names.Add(system.name);

            return string.Join(", ", names.ToArray());
        }

        private void OnDestroy()
        {
            All.Remove(this);
        }

        /// <summary>
        /// Turns the emitters to face the station this piece feeds.
        ///
        /// LookRotation puts local +Z on the target, which is the axis Unity's cone shape
        /// emits along - so a system left at its defaults travels towards the station. One
        /// that emits along a different axis, or simulates in world space with a fixed
        /// velocity, will not turn; the log names them so that is diagnosable rather than
        /// mysterious.
        /// </summary>
        private void AimEffects()
        {
            if (!StokerConfig.AimEffects.Value) return;

            var station = SmelterCapacity.Nearest(transform.position, m_servesFuelled);

            foreach (var effect in _effects)
            {
                if (effect == null) continue;

                if (station == null)
                {
                    // Feeding nothing, so showing nothing. An upgrade that is not attached
                    // to anything looks identical to one that is, otherwise.
                    if (effect.isPlaying) effect.Stop(true, ParticleSystemStopBehavior.StopEmitting);
                    continue;
                }

                var direction = station.transform.position - effect.transform.position;
                if (direction.sqrMagnitude > 0.0001f)
                    effect.transform.rotation = Quaternion.LookRotation(direction.normalized);

                if (!effect.isPlaying) effect.Play();
            }
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

        public string GetHoverName()
        {
            return _piece != null ? _piece.m_name : "";
        }

        public string GetHoverText()
        {
            var name = GetHoverName();
            var station = SmelterCapacity.NearestUsing(transform.position, m_servesFuelled);

            return Localization.instance.Localize(
                station == null
                    ? name + "\n<color=grey>not beside anything it can feed</color>"
                    : name + "\n<color=orange>" + station + "</color>");
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
            Description = "Ore on one side, coal on the other. A smelter or furnace "
                          + "beside it holds more of both.",
            ServesFuelled = true,
        };

        public static readonly UpgradeDef Woodrack = new UpgradeDef
        {
            PrefabName = "stoker_woodrack",
            Description = "Split logs, stacked and under cover. A charcoal kiln beside "
                          + "it holds more wood.",
            ServesFuelled = false,
        };

        public static readonly UpgradeDef[] All = { Trough, Woodrack };

        private static GameObject _holder;
        private static bool _addedToHammer;

        public static bool Ready
        {
            get
            {
                if (ZNetScene.instance == null) return false;

                foreach (var def in All)
                    if (ZNetScene.instance.GetPrefab(def.PrefabName) == null) return false;

                return true;
            }
        }

        /// <summary>Idempotent, and safe to call every frame until it takes.</summary>
        public static bool Register()
        {
            if (!StokerConfig.Enabled.Value) return true;
            if (Ready && _addedToHammer) return true;

            if (ZNetScene.instance == null || ObjectDB.instance == null) return false;

            foreach (var def in All)
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

            var piece = clone.GetComponent<Piece>();
            if (piece != null)
            {
                piece.m_name = def.Name.Value;
                piece.m_description = def.Description;
                piece.m_resources = Requirements(StokerConfig.CostNow(def));

                // Inherited from the donor, which is a chest and so files under Furniture.
                // These upgrade a smelter, so they belong on the same hammer tab as one.
                piece.m_category = Piece.PieceCategory.Crafting;

                var icon = LoadIcon(def);
                if (icon != null) piece.m_icon = icon;
            }

            UpgradeModel.Apply(clone, def.Model.Value);

            var scale = Mathf.Max(0.05f, def.Scale.Value);
            clone.transform.localScale = new Vector3(scale, scale, scale);

            var bin = clone.GetComponent<UpgradeBin>() ?? clone.AddComponent<UpgradeBin>();
            bin.m_servesFuelled = def.ServesFuelled;

            StokerPlugin.Log.LogInfo("Built " + def.PrefabName + " from " + source.name + ".");
            return clone;
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
            var model = def.Model.Value;
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

            foreach (var def in All)
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

        private static void AddToHammer()
        {
            if (_addedToHammer) return;

            var hammer = ObjectDB.instance.GetItemPrefab("Hammer");
            var drop = hammer != null ? hammer.GetComponent<ItemDrop>() : null;
            if (drop == null || drop.m_itemData == null || drop.m_itemData.m_shared == null) return;

            var table = drop.m_itemData.m_shared.m_buildPieces;
            if (table == null || table.m_pieces == null) return;

            foreach (var def in All)
            {
                if (def.Prefab == null) return;
                if (!table.m_pieces.Contains(def.Prefab)) table.m_pieces.Add(def.Prefab);
            }

            _addedToHammer = true;
            StokerPlugin.Log.LogInfo("Both upgrades added to the hammer.");
        }
    }
}
