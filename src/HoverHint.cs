using HarmonyLib;
using UnityEngine;

namespace Stoker
{
    /// <summary>
    /// Tells the player the batch modifier exists.
    ///
    /// Batching is deliberately held rather than toggled, so a plain press stays exactly
    /// vanilla - which also means a player who never guesses at the modifier never sees the
    /// feature at all. Nothing in the game hints at a key the game does not have. So the
    /// hint goes where every other interaction hint goes: the hover text of the thing you
    /// are about to press.
    ///
    /// This lives in its own class rather than in BatchAdd because two of the three targets
    /// are private methods matched by name. Harmony resolves a patch target when PatchAll
    /// runs and throws if it cannot, taking every patch in that class down with it - so a
    /// future version renaming OnHoverAddOre would cost the mod its batching as well as its
    /// hint. Patched separately, and guarded at the call site, a missing hover method costs
    /// only the hint.
    /// </summary>
    internal static class HoverHint
    {
        // ------------------------------------------------------------------ smelter

        [HarmonyPostfix]
        [HarmonyPatch(typeof(Smelter), "OnHoverAddFuel")]
        private static void SmelterFuelHover(Smelter __instance, ref string __result)
        {
            if (__instance.m_maxFuel <= 0) return;
            __result += BatchAdd.BatchHint(StokerConfig.SmelterItemsPerAdd.Value);
        }

        [HarmonyPostfix]
        [HarmonyPatch(typeof(Smelter), "OnHoverAddOre")]
        private static void SmelterOreHover(Smelter __instance, ref string __result)
        {
            if (__instance.m_maxOre <= 0) return;
            __result += BatchAdd.BatchHint(StokerConfig.SmelterItemsPerAdd.Value);
        }

        // ------------------------------------------------------------------ fireplace

        [HarmonyPostfix]
        [HarmonyPatch(typeof(Fireplace), nameof(Fireplace.GetHoverText))]
        private static void FireplaceHover(Fireplace __instance, ref string __result)
        {
            // GetHoverText returns an empty string for an invalid view or an infinite fire,
            // and the no-refill branch is the turn-it-off prompt, which batching never
            // touches. Appending to either would advertise a modifier that does nothing.
            if (string.IsNullOrEmpty(__result)) return;
            if (!__instance.m_canRefill || __instance.m_infiniteFuel) return;

            __result += BatchAdd.BatchHint(StokerConfig.FireplaceItemsPerAdd.Value);
        }

        /// <summary>
        /// Applied on its own so a missing hover method cannot take batching with it. The
        /// hover methods on Smelter are private and matched by name, which is exactly the
        /// kind of thing a game update renames without anyone noticing.
        /// </summary>
        public static void Apply(Harmony harmony)
        {
            try
            {
                harmony.PatchAll(typeof(HoverHint));
            }
            catch (System.Exception e)
            {
                StokerPlugin.Log.LogWarning(
                    "Could not add the batch hint to hover text - batching still works, it "
                    + "just will not announce itself: " + e.Message);
            }
        }
    }
}
