using System.Collections.Generic;
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

        // --------------------------------------------------------------- pending adds

        /// <summary>
        /// How long a prediction is trusted, in seconds.
        ///
        /// Long enough to cover a round trip to a dedicated server and back, short enough that
        /// it cannot outlive a smelt. One ore takes tens of seconds to process, so the queue
        /// cannot legitimately fall inside this window, which is the only way a stale
        /// prediction could hold back an add that should have been allowed.
        /// </summary>
        private const float PredictionSeconds = 3f;

        private struct Prediction
        {
            public float Level;
            public float Time;
        }

        private static readonly Dictionary<ZDOID, Prediction> Pending =
            new Dictionary<ZDOID, Prediction>();

        private static float _lastPrune;

        /// <summary>
        /// What the station's level will be once everything already sent has landed.
        ///
        /// This is the fix for a blast furnace ending up with more ore in it than its capacity
        /// allows. Vanilla's only capacity check is in OnAddOre, on the client, against
        /// GetQueueSize() - and RPC_AddOre on the owner has no check at all, it just writes
        /// item&lt;n&gt; and increments the count. So whatever the client believes is the only
        /// thing standing between a station and an overfilled ZDO, and an overfilled one stays
        /// that way.
        ///
        /// What the client believes was wrong across presses. Each postfix read GetQueueSize()
        /// fresh, and on a dedicated server that value is a round trip behind: the ZDO does not
        /// reflect an add until the owner has written it and replicated it back. Press three
        /// times quickly and all three batches count from the same stale number, so a furnace
        /// two ore short of full accepts three batches of three.
        ///
        /// Tracking the level per station rather than per press closes that. The ZDO's own
        /// answer wins the moment it catches up, so this only ever matters while something is
        /// genuinely in flight, and a prediction that is somehow too low costs nothing - the
        /// authoritative value is always the floor.
        /// </summary>
        private static float Predicted(ZDOID id, float authoritative)
        {
            Prune();

            Prediction p;
            if (Pending.TryGetValue(id, out p)
                && Time.time - p.Time < PredictionSeconds
                && p.Level > authoritative)
                return p.Level;

            return authoritative;
        }

        private static void Remember(ZDOID id, float level)
        {
            Pending[id] = new Prediction { Level = level, Time = Time.time };
        }

        /// <summary>
        /// Drops expired entries so a long session does not accumulate one per station ever
        /// touched. Rate-limited because it walks the dictionary, and nothing here is urgent.
        /// </summary>
        private static void Prune()
        {
            if (Time.time - _lastPrune < PredictionSeconds) return;
            _lastPrune = Time.time;

            if (Pending.Count == 0) return;

            var dead = new List<ZDOID>();
            foreach (var entry in Pending)
                if (Time.time - entry.Value.Time >= PredictionSeconds) dead.Add(entry.Key);

            foreach (var id in dead) Pending.Remove(id);
        }

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
            if (key != KeyCode.None && !Held(key)) return 0;

            return Mathf.Max(0, perAdd - 1);
        }

        /// <summary>
        /// True while the modifier is held.
        ///
        /// ZInput rather than UnityEngine.Input, and this is the whole of why Shift+use did
        /// nothing while the config file held exactly the right key. Valheim runs on the new
        /// Input System: ZInput.GetKey routes a KeyCode to Keyboard.current, Mouse.current or
        /// Gamepad.current itself, and the legacy Input class does not see all of them here.
        /// The symptom is the unhelpful kind - the key is bound, it is correct, and nothing
        /// happens - so it is worth naming in a comment rather than only in a changelog.
        ///
        /// logWarning: false, or ZInput grumbles about every KeyCode it cannot map, and a key
        /// nobody bound is a configuration choice rather than a fault.
        ///
        /// The text-field refusal matches Vaettir's Keys.Held. A held modifier hardly matters
        /// while chat has focus, since you cannot reach a smelter anyway, but two key readers
        /// in one suite with different manners is how one of them ends up wrong later.
        /// </summary>
        private static bool Held(KeyCode key)
        {
            if (key == KeyCode.None) return false;
            if (!ZInput.GetKey(key, false)) return false;

            if (Chat.instance != null && Chat.instance.HasFocus()) return false;
            return !Console.IsVisible() && !TextInput.IsVisible();
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

            // +1 for the add the game just made, which the ZDO has not caught up with, and
            // counted from the prediction rather than the ZDO so a second press inside the
            // round trip does not start over from a stale number.
            var id = nview.GetZDO().m_uid;
            var expected = Predicted(id, (float)SmelterGetFuel.Invoke(__instance, null)) + 1f;
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

            Remember(id, expected);
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

            var id = nview.GetZDO().m_uid;
            var expected =
                Mathf.CeilToInt(Predicted(id, (int)SmelterGetQueueSize.Invoke(__instance, null))) + 1;
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

                // Two arguments, not one. Smelter registers this as Register<string, bool> and
                // vanilla's own OnAddOre sends (name, item.m_cheated); sending the name alone
                // leaves the receiver reading a bool off the end of the package. Match the
                // game's call exactly - a signature is not something to send an approximation
                // of, and it changed under us when the cheated flag was added.
                nview.InvokeRPC("RPC_AddOre", item.m_dropPrefab.name, item.m_cheated);
                expected++;
                added++;
            }

            Remember(id, expected);
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
            var id = nview.GetZDO().m_uid;
            var expected = Predicted(id, nview.GetZDO().GetFloat(ZDOVars.s_fuel)) + 1f;
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

            Remember(id, expected);
            Report(fireplace.m_name, "logs", added);
        }

        private static void Report(string station, string what, int added)
        {
            if (!KyndaConfig.Verbose.Value || added == 0) return;
            KyndaPlugin.Log.LogInfo(station + ": batched " + added + " extra " + what + ".");
        }
    }
}
