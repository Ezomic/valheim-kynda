using System.Reflection;
using HarmonyLib;
using UnityEngine;

namespace Kynda
{
    /// <summary>
    /// Adds several items per press instead of one.
    ///
    /// Everything here is a postfix that runs only when the game's own add succeeded, so
    /// the first item goes in through vanilla's validation - right item, station not full,
    /// player actually has one - and this just repeats the last two steps of it. That keeps
    /// the rules in one place: if the game would refuse the first item, nothing happens.
    ///
    /// The one trap worth knowing: the add is an RPC, and the ZDO does not reflect it in
    /// the same frame. Re-reading the fuel level inside the loop would give a stale value
    /// and happily overfill. So the expected level is tracked locally instead, starting one
    /// above what the ZDO says because the original add is already in flight.
    /// </summary>
    internal static class BatchAdd
    {
        // Cached because these are called on every interaction with a smelter.
        private static readonly MethodInfo SmelterGetFuel =
            AccessTools.Method(typeof(Smelter), "GetFuel");

        private static readonly MethodInfo SmelterGetQueueSize =
            AccessTools.Method(typeof(Smelter), "GetQueueSize");

        private static readonly MethodInfo SmelterFindCookable =
            AccessTools.Method(typeof(Smelter), "FindCookableItem");

        private static readonly FieldInfo SmelterNView =
            AccessTools.Field(typeof(Smelter), "m_nview");

        private static readonly FieldInfo FireplaceNView =
            AccessTools.Field(typeof(Fireplace), "m_nview");

        /// <summary>
        /// Everything above is looked up by name, and AccessTools answers a name it cannot
        /// find with null rather than an error. Left alone that surfaces much later as a
        /// NullReferenceException the first time someone stokes a fire, with nothing to
        /// connect it back to a game update having renamed a private method. So it is
        /// checked once, at startup, and said out loud.
        /// </summary>
        public static bool Verify()
        {
            var missing = new System.Collections.Generic.List<string>();

            if (SmelterGetFuel == null) missing.Add("Smelter.GetFuel");
            if (SmelterGetQueueSize == null) missing.Add("Smelter.GetQueueSize");
            if (SmelterFindCookable == null) missing.Add("Smelter.FindCookableItem");
            if (SmelterNView == null) missing.Add("Smelter.m_nview");
            if (FireplaceNView == null) missing.Add("Fireplace.m_nview");

            if (missing.Count == 0) return true;

            KyndaPlugin.Log.LogError(
                "Game members this mod reflects on are missing - batching is disabled: "
                + string.Join(", ", missing.ToArray()));
            return false;
        }

        private static bool Ready => SmelterGetFuel != null && SmelterGetQueueSize != null
                                     && SmelterFindCookable != null && SmelterNView != null
                                     && FireplaceNView != null;

        /// <summary>
        /// How many extra items this press should add - zero unless the modifier is held.
        ///
        /// The gate is here rather than at each call site so a plain press is vanilla in
        /// exactly one place. Set BatchModifier to None and the check falls away, which
        /// makes batching unconditional for anyone who wants it that way.
        /// </summary>
        private static int Extra(int perAdd)
        {
            var key = KyndaConfig.BatchModifier.Value;
            if (key != KeyCode.None && !Input.GetKey(key)) return 0;

            return Mathf.Max(0, perAdd - 1);
        }

        /// <summary>
        /// The hint appended to a station's hover text, or nothing when batching is off.
        ///
        /// Formatted as the game formats its own key prompts - a yellow bold key in square
        /// brackets on its own line - rather than as a parenthetical, so it reads as one
        /// more thing the station can do instead of as a mod announcing itself. With no
        /// modifier bound there is no key to name, so it states the multiplier instead.
        /// </summary>
        internal static string BatchHint(int perAdd)
        {
            if (perAdd <= 1) return "";

            var key = KyndaConfig.BatchModifier.Value;

            return key == KeyCode.None
                ? "\n<color=grey>x" + perAdd + " per press</color>"
                : "\n[<color=yellow><b>" + key + "</b></color>] x" + perAdd;
        }

        // ------------------------------------------------------------------ smelter fuel

        [HarmonyPostfix]
        [HarmonyPatch(typeof(Smelter), "OnAddFuel")]
        private static void BatchFuel(Smelter __instance, bool __result, Humanoid user)
        {
            if (!__result || user == null || !Ready) return;

            var extra = Extra(KyndaConfig.SmelterItemsPerAdd.Value);
            if (extra <= 0) return;

            var nview = SmelterNView.GetValue(__instance) as ZNetView;
            if (nview == null || !nview.IsValid()) return;

            var inventory = user.GetInventory();
            if (inventory == null || __instance.m_fuelItem == null) return;

            var fuelName = __instance.m_fuelItem.m_itemData.m_shared.m_name;

            // +1 for the add the game just made, which the ZDO has not caught up with.
            var expected = (float)SmelterGetFuel.Invoke(__instance, null) + 1f;
            var added = 0;

            for (var i = 0; i < extra; i++)
            {
                // Vanilla's own guard, so batching cannot exceed what pressing repeatedly would.
                if (expected > __instance.m_maxFuel - 1) break;
                if (!inventory.HaveItem(fuelName)) break;

                inventory.RemoveItem(fuelName, 1);
                nview.InvokeRPC("RPC_AddFuel");
                expected += 1f;
                added++;
            }

            Report(__instance.m_name, "fuel", added);
        }

        // ------------------------------------------------------------------ smelter ore

        [HarmonyPostfix]
        [HarmonyPatch(typeof(Smelter), "OnAddOre")]
        private static void BatchOre(Smelter __instance, bool __result, Humanoid user)
        {
            if (!__result || user == null || !Ready) return;

            var extra = Extra(KyndaConfig.SmelterItemsPerAdd.Value);
            if (extra <= 0) return;

            var nview = SmelterNView.GetValue(__instance) as ZNetView;
            if (nview == null || !nview.IsValid()) return;

            var inventory = user.GetInventory();
            if (inventory == null) return;

            var expected = (int)SmelterGetQueueSize.Invoke(__instance, null) + 1;
            var added = 0;

            for (var i = 0; i < extra; i++)
            {
                if (expected >= __instance.m_maxOre) break;

                // Re-found every pass rather than reusing the original argument: that
                // argument is null when the player pressed with an empty hand and the game
                // chose the item itself, and the chosen stack can run out mid-batch.
                var item = SmelterFindCookable.Invoke(__instance, new object[] { inventory })
                    as ItemDrop.ItemData;

                if (item == null || item.m_dropPrefab == null) break;

                inventory.RemoveItem(item, 1);
                nview.InvokeRPC("RPC_AddOre", item.m_dropPrefab.name);
                expected++;
                added++;
            }

            Report(__instance.m_name, "ore", added);
        }

        // ------------------------------------------------------------------ fireplace

        [HarmonyPostfix]
        [HarmonyPatch(typeof(Fireplace), nameof(Fireplace.UseItem))]
        private static void BatchFireplaceUseItem(Fireplace __instance, bool __result,
            Humanoid user, ItemDrop.ItemData item)
        {
            if (!__result || user == null || item == null || __instance.m_fuelItem == null) return;
            if (item.m_shared.m_name != __instance.m_fuelItem.m_itemData.m_shared.m_name) return;

            TopUpFire(__instance, user);
        }

        [HarmonyPostfix]
        [HarmonyPatch(typeof(Fireplace), nameof(Fireplace.Interact))]
        private static void BatchFireplaceInteract(Fireplace __instance, bool __result,
            Humanoid user, bool hold, bool alt)
        {
            // Holding to refill already repeats on its own timer; batching that too would
            // empty an inventory into a campfire faster than anyone means to.
            if (!__result || hold || user == null || !Ready) return;

            // Interact does two different jobs and returns true for both. When the fire can
            // be turned off and has fuel, the press was a toggle and never touched the
            // player's logs - batching there would put three on the fire for a press that
            // was only meant to snuff it out.
            var nview = FireplaceNView.GetValue(__instance) as ZNetView;
            if (nview == null || !nview.IsValid()) return;

            if (__instance.m_canTurnOff && !alt && nview.GetZDO().GetFloat(ZDOVars.s_fuel) > 0f)
                return;

            TopUpFire(__instance, user);
        }

        private static void TopUpFire(Fireplace fireplace, Humanoid user)
        {
            var extra = Extra(KyndaConfig.FireplaceItemsPerAdd.Value);
            if (extra <= 0 || !Ready || fireplace.m_infiniteFuel || !fireplace.m_canRefill) return;

            var nview = FireplaceNView.GetValue(fireplace) as ZNetView;
            if (nview == null || !nview.IsValid()) return;

            var inventory = user.GetInventory();
            if (inventory == null || fireplace.m_fuelItem == null) return;

            var fuelName = fireplace.m_fuelItem.m_itemData.m_shared.m_name;
            var expected = nview.GetZDO().GetFloat(ZDOVars.s_fuel) + 1f;
            var added = 0;

            for (var i = 0; i < extra; i++)
            {
                // The fireplace clamps fuel in its own RPC, so going over would not break
                // anything - it would just silently eat the logs. Hence checking first.
                if (Mathf.CeilToInt(expected) >= fireplace.m_maxFuel) break;
                if (!inventory.HaveItem(fuelName)) break;

                inventory.RemoveItem(fuelName, 1);
                nview.InvokeRPC("RPC_AddFuel");
                expected += 1f;
                added++;
            }

            Report(fireplace.m_name, "logs", added);
        }

        private static void Report(string station, string what, int added)
        {
            if (!KyndaConfig.Verbose.Value || added == 0) return;
            KyndaPlugin.Log.LogInfo(station + ": batched " + added + " extra " + what + ".");
        }
    }
}
