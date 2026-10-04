using System.Collections.Generic;
using UnityEngine;

namespace Kynda
{
    /// <summary>
    /// Raises a station's capacity for each matching upgrade built beside it.
    ///
    /// Capacity only. m_secPerProduct and m_fuelPerProduct are never touched, so an upgraded
    /// smelter takes exactly as long and burns exactly as much coal per bar as a bare one -
    /// it simply goes longer between visits. That is the line the whole mod sits on, and it
    /// is the reason this is a convenience rather than a power increase.
    /// </summary>
    internal class SmelterCapacity : MonoBehaviour
    {
        private static readonly List<SmelterCapacity> All = new List<SmelterCapacity>();

        private Smelter _smelter;
        private int _baseOre;
        private int _baseFuel;

        private void Awake()
        {
            _smelter = GetComponent<Smelter>();
            if (_smelter == null) { enabled = false; return; }

            // Captured before anything is applied, and never rewritten. Recomputing from the
            // current values instead would add an upgrade's worth of capacity every tick.
            _baseOre = _smelter.m_maxOre;
            _baseFuel = _smelter.m_maxFuel;

            All.Add(this);

            // Polled rather than pushed: an upgrade can be built, destroyed or fall down at
            // any time, and a station that quietly kept capacity from a bin that burned down
            // would be a duplication bug rather than a cosmetic one.
            InvokeRepeating("Recompute", 1f, 3f);
        }

        private void OnDestroy()
        {
            All.Remove(this);
        }

        /// <summary>
        /// Which kind of bin this station could take: one with a fuel slot, or one without.
        /// Read off the station's own numbers, so a modded station lands on the right side of
        /// the split without anyone naming it.
        ///
        /// This only narrows the field. Which piece actually serves the station is the one
        /// whose Stations list names it and that is built beside it - see Def. A smelter and a
        /// blast furnace are both fuelled, and it is the lists that tell the Tun from the
        /// furnace upgrade. The Tun names both, so a blast furnace takes whichever of the Tun
        /// and the Skip the player built.
        /// </summary>
        private bool Fuelled { get { return _baseFuel > 0; } }

        /// <summary>The piece that raises this station's capacity, or null when none does.</summary>
        private UpgradeDef Def
        {
            get { return UpgradePrefabs.ServingStation(
                Utils.GetPrefabName(gameObject), Fuelled, transform.position); }
        }

        /// <summary>
        /// A flat amount, taken from whichever upgrade serves this station.
        ///
        /// Per piece rather than one figure for the mod, and not a proportion either. The
        /// numbers wanted are a charcoal kiln landing on 50 from 25 and a smelter landing on
        /// 30 from 10 - that is +25 and +20, and no single rule gives both. Doubling gave
        /// the kiln its 50 and left the smelter at 20.
        /// </summary>
        private void Recompute()
        {
            if (_smelter == null) return;

            var def = Def;

            var level = KyndaConfig.Enabled.Value && def != null
                ? Mathf.Min(UpgradeBin.CountNear(transform.position, def.Kind),
                            Mathf.Max(0, KyndaConfig.MaxPerStation.Value))
                : 0;

            var oreBonus = def != null ? level * Mathf.Max(0, def.OreCapacity.Value) : 0;
            var fuelBonus = def != null && def.FuelCapacity != null
                ? level * Mathf.Max(0, def.FuelCapacity.Value)
                : 0;

            var ore = _smelter.m_maxOre;
            var fuel = _smelter.m_maxFuel;

            // Only raise a cap the station already has. A charcoal kiln has no fuel slot at
            // all - giving it one would have it refuse to work until fed coal it cannot take.
            if (_baseOre > 0) _smelter.m_maxOre = _baseOre + oreBonus;
            if (_baseFuel > 0) _smelter.m_maxFuel = _baseFuel + fuelBonus;

            if (KyndaConfig.Verbose.Value && (ore != _smelter.m_maxOre || fuel != _smelter.m_maxFuel))
                KyndaPlugin.Log.LogInfo(string.Format(
                    "{0} capacity ore {1} to {2}, fuel {3} to {4}, {5} upgrade(s) counting.",
                    Utils.GetPrefabName(gameObject), ore, _smelter.m_maxOre,
                    fuel, _smelter.m_maxFuel, level));
        }

        /// <summary>
        /// Where the link effect should end.
        ///
        /// Vanilla asks the CraftingStation for a GetConnectionEffectPoint, which a Smelter
        /// has no equivalent of. Half the collider's height is close enough and adapts to a
        /// kiln and a smelter without either being measured by hand; a link ending at the
        /// station's origin would sink into the ground.
        /// </summary>
        public Vector3 ConnectionPoint
        {
            get
            {
                var collider = GetComponentInChildren<Collider>();
                if (collider != null) return collider.bounds.center;

                return transform.position + Vector3.up;
            }
        }

        /// <summary>The nearest station that the piece of this kind actually serves, or null.</summary>
        public static SmelterCapacity Nearest(Vector3 point, int kind)
        {
            var range = KyndaConfig.Range.Value;
            var def = UpgradePrefabs.ByKind(kind);
            if (def == null) return null;

            SmelterCapacity best = null;
            var bestDistance = float.MaxValue;

            foreach (var capacity in All)
            {
                if (capacity == null || capacity._smelter == null) continue;

                // A bin standing next to a station it does not serve must not claim it, or
                // the hover text names a station whose capacity never moved - which is the
                // silent no-op this mod already went out of its way to avoid elsewhere. A
                // station named by two pieces is served by the one built beside it, and only that
                // one claims it.
                if (capacity.Def != def) continue;

                var distance = Vector3.Distance(capacity.transform.position, point);
                if (distance > range || distance >= bestDistance) continue;

                best = capacity;
                bestDistance = distance;
            }

            return best;
        }

        /// <summary>
        /// True when a station in range is named by this kind's Stations list but is served by
        /// another piece built beside it, so the hover can say so.
        /// </summary>
        public static bool NamesNearby(Vector3 point, int kind)
        {
            var range = KyndaConfig.Range.Value;
            var def = UpgradePrefabs.ByKind(kind);
            if (def == null) return false;

            foreach (var capacity in All)
            {
                if (capacity == null || capacity._smelter == null) continue;
                if (Vector3.Distance(capacity.transform.position, point) > range) continue;
                if (!UpgradePrefabs.Serves(def, Utils.GetPrefabName(capacity.gameObject),
                                           capacity.Fuelled)) continue;

                var serving = capacity.Def;
                if (serving != null && serving != def) return true;
            }

            return false;
        }

        /// <summary>
        /// The station an upgrade at this point is helping, for its hover text. Only
        /// stations of the matching kind count, so a woodrack beside a smelter correctly
        /// reports that it is feeding nothing rather than claiming the smelter.
        /// </summary>
        public static string NearestUsing(Vector3 point, int kind)
        {
            var best = Nearest(point, kind);
            if (best == null) return null;

            var smelter = best._smelter;
            var parts = new List<string>();
            if (smelter.m_maxOre > 0) parts.Add("ore " + smelter.m_maxOre);
            if (smelter.m_maxFuel > 0) parts.Add("fuel " + smelter.m_maxFuel);

            return smelter.m_name + " (" + string.Join(", ", parts.ToArray()) + ")";
        }

        /// <summary>
        /// Bolts the component onto every Smelter-based prefab. One component covers the
        /// smelter, kiln, blast furnace, windmill, spinning wheel and eitr refinery, because
        /// they are all the same class - and modded ones come along for free.
        /// </summary>
        public static int AttachToPrefabs()
        {
            var scene = ZNetScene.instance;
            if (scene == null) return 0;

            var touched = 0;

            foreach (var prefab in scene.m_prefabs)
            {
                if (prefab == null) continue;
                if (prefab.GetComponent<Smelter>() == null) continue;
                if (prefab.GetComponent<SmelterCapacity>() != null) continue;

                prefab.AddComponent<SmelterCapacity>();
                touched++;
            }

            return touched;
        }
    }
}
