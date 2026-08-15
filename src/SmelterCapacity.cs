using System.Collections.Generic;
using UnityEngine;

namespace Stoker
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
        /// A station with a fuel slot takes the trough; one without takes the woodrack.
        /// Decided on the station's own numbers rather than a list of prefab names, so a
        /// modded station lands on the right side without anyone naming it.
        /// </summary>
        private bool Fuelled { get { return _baseFuel > 0; } }

        /// <summary>
        /// A flat amount, taken from whichever upgrade serves this kind of station.
        ///
        /// Per piece rather than one figure for the mod, and not a proportion either. The
        /// numbers wanted are a charcoal kiln landing on 50 from 25 and a smelter landing on
        /// 30 from 10 - that is +25 and +20, and no single rule gives both. Doubling gave
        /// the kiln its 50 and left the smelter at 20.
        /// </summary>
        private void Recompute()
        {
            if (_smelter == null) return;

            var level = StokerConfig.Enabled.Value
                ? Mathf.Min(UpgradeBin.CountNear(transform.position, Fuelled),
                            Mathf.Max(0, StokerConfig.MaxPerStation.Value))
                : 0;

            var def = UpgradePrefabs.For(Fuelled);

            var oreBonus = level * Mathf.Max(0, def.OreCapacity.Value);
            var fuelBonus = def.FuelCapacity != null
                ? level * Mathf.Max(0, def.FuelCapacity.Value)
                : 0;

            // Only raise a cap the station already has. A charcoal kiln has no fuel slot at
            // all - giving it one would have it refuse to work until fed coal it cannot take.
            if (_baseOre > 0) _smelter.m_maxOre = _baseOre + oreBonus;
            if (_baseFuel > 0) _smelter.m_maxFuel = _baseFuel + fuelBonus;
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

        /// <summary>The nearest station of the matching kind, or null.</summary>
        public static SmelterCapacity Nearest(Vector3 point, bool fuelled)
        {
            var range = StokerConfig.Range.Value;

            SmelterCapacity best = null;
            var bestDistance = float.MaxValue;

            foreach (var capacity in All)
            {
                if (capacity == null || capacity._smelter == null) continue;
                if (capacity.Fuelled != fuelled) continue;

                var distance = Vector3.Distance(capacity.transform.position, point);
                if (distance > range || distance >= bestDistance) continue;

                best = capacity;
                bestDistance = distance;
            }

            return best;
        }

        /// <summary>
        /// The station an upgrade at this point is helping, for its hover text. Only
        /// stations of the matching kind count, so a woodrack beside a smelter correctly
        /// reports that it is feeding nothing rather than claiming the smelter.
        /// </summary>
        public static string NearestUsing(Vector3 point, bool fuelled)
        {
            var best = Nearest(point, fuelled);
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
