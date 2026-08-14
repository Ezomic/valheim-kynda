using System.Collections.Generic;
using UnityEngine;

namespace Stoker
{
    /// <summary>
    /// Raises a station's capacity for each hopper built beside it.
    ///
    /// Capacity only. M_secPerProduct and m_fuelPerProduct are never touched, so an upgraded
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
            // current values instead would add a hopper's worth of capacity every tick.
            _baseOre = _smelter.m_maxOre;
            _baseFuel = _smelter.m_maxFuel;

            All.Add(this);

            // Polled rather than pushed: a hopper can be built, destroyed or fall down at
            // any time, and a station that quietly kept capacity from a bin that burned down
            // would be a duplication bug rather than a cosmetic one.
            InvokeRepeating("Recompute", 1f, 3f);
        }

        private void OnDestroy()
        {
            All.Remove(this);
        }

        private void Recompute()
        {
            if (_smelter == null) return;

            var level = StokerConfig.HopperEnabled.Value
                ? Mathf.Min(Hopper.CountNear(transform.position), Mathf.Max(0, StokerConfig.MaxHoppers.Value))
                : 0;

            var bonus = level * Mathf.Max(0, StokerConfig.CapacityPerHopper.Value);

            // Only raise a cap the station already has. A charcoal kiln has no fuel slot at
            // all - giving it one would have it refuse to work until fed coal it cannot take.
            if (_baseOre > 0) _smelter.m_maxOre = _baseOre + bonus;
            if (_baseFuel > 0) _smelter.m_maxFuel = _baseFuel + bonus;
        }

        /// <summary>The station a hopper at this point is helping, for its hover text.</summary>
        public static string NearestUsing(Vector3 point)
        {
            var range = StokerConfig.HopperRange.Value;

            SmelterCapacity best = null;
            var bestDistance = float.MaxValue;

            foreach (var capacity in All)
            {
                if (capacity == null || capacity._smelter == null) continue;

                var distance = Vector3.Distance(capacity.transform.position, point);
                if (distance > range || distance >= bestDistance) continue;

                best = capacity;
                bestDistance = distance;
            }

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
