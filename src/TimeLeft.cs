using System.Reflection;
using HarmonyLib;
using UnityEngine;

namespace Kynda
{
    /// <summary>
    /// The one hover line saying how long what is loaded will last.
    ///
    /// Every number comes from the station: the queue and bake timer a Smelter keeps in its
    /// ZDO, the fuel level both station kinds keep, and the m_secPerProduct, m_fuelPerProduct
    /// and m_secPerFuel the prefab carries. Kynda never changes any of them, so nothing here
    /// is an estimate of Kynda's own throughput. A station whose speed is not a constant
    /// (a windmill's depends on the wind) gets no line rather than a wrong one, and so does
    /// one that is not running for want of fuel, since a countdown that is not counting is
    /// a lie.
    /// </summary>
    internal static class TimeLeft
    {
        private static readonly FieldInfo SmelterNView =
            AccessTools.Field(typeof(Smelter), "m_nview");

        private static readonly FieldInfo FireplaceNView =
            AccessTools.Field(typeof(Fireplace), "m_nview");

        public static string Line(float seconds)
        {
            if (!KyndaConfig.ShowTimeLeft.Value || seconds <= 0f) return "";
            return "\n<color=grey>" + Format(seconds) + " left</color>";
        }

        public static float QueueSeconds(Smelter smelter)
        {
            var zdo = Zdo(SmelterNView, smelter);
            if (zdo == null || smelter.m_secPerProduct <= 0f || smelter.m_windmill) return 0f;

            var queued = zdo.GetInt(ZDOVars.s_queued);
            if (queued <= 0) return 0f;
            if (smelter.m_maxFuel > 0 && zdo.GetFloat(ZDOVars.s_fuel) <= 0f) return 0f;

            return queued * smelter.m_secPerProduct - zdo.GetFloat(ZDOVars.s_bakeTimer);
        }

        public static float FuelSeconds(Smelter smelter)
        {
            var zdo = Zdo(SmelterNView, smelter);
            if (zdo == null || smelter.m_secPerProduct <= 0f || smelter.m_fuelPerProduct <= 0
                || smelter.m_windmill) return 0f;

            return zdo.GetFloat(ZDOVars.s_fuel) * smelter.m_secPerProduct / smelter.m_fuelPerProduct;
        }

        public static float FireplaceSeconds(Fireplace fireplace)
        {
            var zdo = Zdo(FireplaceNView, fireplace);
            if (zdo == null || fireplace.m_secPerFuel <= 0f) return 0f;

            return zdo.GetFloat(ZDOVars.s_fuel) * fireplace.m_secPerFuel;
        }

        private static ZDO Zdo(FieldInfo field, object owner)
        {
            if (field == null) return null;
            var nview = field.GetValue(owner) as ZNetView;
            return nview != null && nview.IsValid() ? nview.GetZDO() : null;
        }

        private static string Format(float seconds)
        {
            var total = Mathf.CeilToInt(seconds);
            var hours = total / 3600;
            var minutes = total % 3600 / 60;
            var secs = total % 60;

            if (hours > 0) return hours + "h " + minutes + "m";
            if (minutes > 0) return minutes + "m " + secs + "s";
            return secs + "s";
        }
    }
}
