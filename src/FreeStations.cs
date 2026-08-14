using System.Collections.Generic;
using UnityEngine;

namespace Stoker
{
    /// <summary>
    /// Makes the vanilla burning stations free to Build while TestMode is on.
    ///
    /// Checking that a hopper sits right beside a smelter means having a smelter, and a
    /// smelter means Stone and surtling cores from a burial chamber. That is a fine cost
    /// to pay when playing and a silly one to pay to look at a model, so the whole row -
    /// smelter, kiln, blast furnace, windmill, spinning wheel, eitr refinery - is free
    /// while testing.
    ///
    /// matched on components rather than a name list, exactly like the Capacity
    /// component: anything that is both a piece and a smelter is a burning station,
    /// including modded ones.
    /// </summary>
    internal static class FreeStations
    {
        /// <summary>
        /// the real costs, kept so Turning TestMode off puts them back without a restart
        /// of the whole game. Captured before anything is cleared and never overwritten,
        /// or the "original" would end up being the empty list we ourselves wrote.
        /// </summary>
        private static readonly Dictionary<string, Piece.Requirement[]> original =
            new Dictionary<string, Piece.Requirement[]>();

        public static void Apply()
        {
            var scene = ZNetScene.instance;
            if (scene == null) return;

            var free = StokerConfig.TestMode.Value;
            var touched = 0;

            foreach (var prefab in scene.m_prefabs)
            {
                if (prefab == null) continue;

                var piece = prefab.GetComponent<Piece>();
                if (piece == null || prefab.GetComponent<Smelter>() == null) continue;

                if (!original.ContainsKey(prefab.name))
                    original[prefab.name] = piece.m_resources;

                var wanted = free ? new Piece.Requirement[0] : original[prefab.name];
                if (piece.m_resources == wanted) continue;

                piece.m_resources = wanted;
                touched++;
            }

            if (touched == 0) return;

            StokerPlugin.Log.LogWarning(free
                ? "TEST MODE: " + touched + " burning station(s) are free to Build."
                : "Restored the real Build cost of " + touched + " burning station(s).");
        }
    }
}
