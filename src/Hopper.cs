using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;

namespace Stoker
{
    /// <summary>
    /// A bin you build beside a smelter to make it hold more.
    ///
    /// Modelled on vanilla's StationExtension - the way a chopping block upgrades a
    /// workbench - because that is the game's own idiom for "upgrade by building something
    /// next to it". StationExtension itself is welded to CraftingStation and a smelter is
    /// not one, so this keeps its own registry, but the shape is the same.
    ///
    /// Being a real placed piece is what makes this better than an upgrade level on the
    /// smelter's ZDO. Persistence comes free, you can see at a glance which smelters are
    /// upgraded, and it costs floor space as well as materials - so upgrading a row of eight
    /// is a decision about your base rather than a switch you flip once.
    /// </summary>
    internal class Hopper : MonoBehaviour, Hoverable
    {
        private static readonly List<Hopper> All = new List<Hopper>();

        private Piece _piece;

        private void Awake()
        {
            _piece = GetComponent<Piece>();
            All.Add(this);
        }

        private void OnDestroy()
        {
            All.Remove(this);
        }

        /// <summary>How many hoppers are close enough to count for a station at this point.</summary>
        public static int CountNear(Vector3 point)
        {
            var range = StokerConfig.HopperRange.Value;
            var count = 0;

            foreach (var hopper in All)
            {
                if (hopper == null) continue;
                if (Vector3.Distance(hopper.transform.position, point) <= range) count++;
            }

            return count;
        }

        public string GetHoverName()
        {
            return _piece != null ? _piece.m_name : StokerConfig.HopperName.Value;
        }

        public string GetHoverText()
        {
            var name = GetHoverName();
            var station = SmelterCapacity.NearestUsing(transform.position);

            return Localization.instance.Localize(
                station == null
                    ? name + "\n<color=grey>not beside anything that burns</color>"
                    : name + "\n<color=orange>" + station + "</color>");
        }
    }

    /// <summary>
    /// Builds the hopper prefab at runtime by cloning a barrel, so the mod stays a single
    /// DLL with no asset bundle. The clone keeps the donor's icon, which is why a barrel is
    /// the donor: the picture on the hammer is already a picture of a bin.
    /// </summary>
    internal static class HopperPrefab
    {
        public const string Name = "stoker_hopper";

        private static GameObject _prefab;
        private static GameObject _holder;
        private static bool _addedToHammer;

        public static bool Ready =>
            ZNetScene.instance != null && ZNetScene.instance.GetPrefab(Name) != null;

        /// <summary>Idempotent, and safe to call every frame until it takes.</summary>
        public static bool Register()
        {
            if (!StokerConfig.HopperEnabled.Value) return true;
            if (Ready && _addedToHammer) return true;

            if (ZNetScene.instance == null || ObjectDB.instance == null) return false;

            if (_prefab == null)
            {
                _prefab = Build();
                if (_prefab == null) return false;
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
            foreach (var name in new[] { StokerConfig.HopperDonor.Value, "piece_chest_wood" })
            {
                if (string.IsNullOrEmpty(name)) continue;

                var found = scene.GetPrefab(name);
                if (found != null) return found;

                StokerPlugin.Log.LogWarning("Hopper donor '" + name + "' does not exist.");
            }

            return null;
        }

        private static GameObject Build()
        {
            var source = Donor();
            if (source == null) return null;

            if (_holder == null)
            {
                _holder = new GameObject("StokerHopperHolder");
                _holder.SetActive(false);
                Object.DontDestroyOnLoad(_holder);
            }

            var previous = ZNetView.m_forceDisableInit;
            ZNetView.m_forceDisableInit = true;

            GameObject clone;
            try { clone = Object.Instantiate(source, _holder.transform); }
            finally { ZNetView.m_forceDisableInit = previous; }

            clone.name = Name;

            // It is a bin, not storage. Leaving the Container on would give it an inventory
            // the smelter never reads, which is exactly the confusion to avoid.
            //
            // DestroyImmediate, not Destroy: ordinary Destroy is deferred to the end of the
            // frame, and this prefab is registered and can be built from within that frame -
            // which would hand out a hopper that really is a chest.
            foreach (var container in clone.GetComponentsInChildren<Container>(true))
                Object.DestroyImmediate(container);

            var piece = clone.GetComponent<Piece>();
            if (piece != null)
            {
                piece.m_name = StokerConfig.HopperName.Value;
                piece.m_description = "Beside a smelter, kiln or furnace, it holds more.";
                piece.m_resources = Requirements(StokerConfig.HopperCostNow());

                // Inherited from the donor, which is a chest and so files under Furniture.
                // This upgrades a smelter, so it belongs on the same hammer tab as the
                // smelter - Crafting - not next to the beds and banners.
                piece.m_category = Piece.PieceCategory.Crafting;
            }

            // Its own model, replacing the donor's entirely. If the OBJ is missing the
            // donor's look is kept and squashed instead, so a lost asset costs the piece
            // its shape rather than making it invisible.
            var modelled = HopperModel.Apply(clone);

            var scale = StokerConfig.HopperScale.Value;
            var squash = modelled ? 1f : Mathf.Max(0.05f, StokerConfig.HopperSquash.Value);
            clone.transform.localScale = new Vector3(scale, scale * squash, scale);

            if (clone.GetComponent<Hopper>() == null) clone.AddComponent<Hopper>();

            StokerPlugin.Log.LogInfo("Built " + Name + " from " + source.name + ".");
            return clone;
        }

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
                    StokerPlugin.Log.LogWarning("Hopper cost mentions unknown item '" + itemName + "'.");
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
            if (_prefab == null || scene.GetPrefab(Name) != null) return;

            if (!scene.m_prefabs.Contains(_prefab)) scene.m_prefabs.Add(_prefab);

            try
            {
                var named = (Dictionary<int, GameObject>)
                    AccessTools.Field(typeof(ZNetScene), "m_namedPrefabs").GetValue(scene);
                named[Name.GetStableHashCode()] = _prefab;
            }
            catch (System.Exception e)
            {
                StokerPlugin.Log.LogError("Could not register " + Name + ": " + e.Message);
            }
        }

        private static void AddToHammer()
        {
            if (_addedToHammer || _prefab == null) return;

            var hammer = ObjectDB.instance.GetItemPrefab("Hammer");
            var drop = hammer != null ? hammer.GetComponent<ItemDrop>() : null;
            if (drop == null || drop.m_itemData == null || drop.m_itemData.m_shared == null) return;

            var table = drop.m_itemData.m_shared.m_buildPieces;
            if (table == null || table.m_pieces == null) return;

            if (!table.m_pieces.Contains(_prefab)) table.m_pieces.Add(_prefab);
            _addedToHammer = true;

            StokerPlugin.Log.LogInfo("Hopper added to the hammer.");
        }
    }
}
