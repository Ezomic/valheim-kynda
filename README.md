# Stoker

Fewer trips to the smelter. Same amount of metal out of it.

Built against the installed game (0.221.12, Unity 6000.0.61, BepInEx 5.4.23.3, Harmony 2.9).

## The balance line

This replaces an auto-fuel mod, and it deliberately is not one. Auto-feeding does not make
Valheim more convenient so much as delete a system from it — you never think about coal
again, and the mid-game logistics problem quietly stops existing.

So the whole mod sits on one line:

> **It changes how often you walk to a smelter. It never changes what comes out of one.**

`m_secPerProduct` and `m_fuelPerProduct` are never touched. Three ore in one press costs
exactly three ore. Twenty iron takes the same time and burns the same coal whether it went
in as one load or three. You buy fewer trips, not more metal.

## Status: v0.2 — batching and the hopper

| Feature | State |
| --- | --- |
| **Add several items per press** | **built, untested** |
| **Hopper piece that raises capacity** | **built, untested** |

### Batching

Press once at a smelter and three ore go in instead of one. Same for coal, and for logs on
a campfire, hearth or torch.

It covers every `Smelter`-based station — smelter, charcoal kiln, blast furnace, windmill,
spinning wheel, eitr refinery — because they are all the same component, so modded ones
come along for free. Fireplaces are a separate class and are handled alongside.

Batching stops early at the station's capacity or when you run out, so it can never put in
more than pressing repeatedly would have.

### The Hopper

Build a **Hopper** from the hammer (20 wood, 5 bronze) within 4m of a smelter, kiln or
furnace and that station holds 10 more ore and 10 more fuel. A second hopper adds another
10. Two is the limit by default.

Bronze gates it behind the smelter it upgrades, so it cannot exist before there is anything
to smelt. Look at a hopper and it tells you which station it is feeding and what that
station's capacity now is.

Modelled on vanilla's `StationExtension` — the way a chopping block upgrades a workbench —
because that is the game's own idiom for "upgrade by building something next to it".
`StationExtension` itself is hardwired to `CraftingStation` and a smelter is not one, so it
keeps its own registry, but the shape is the same.

Two things make this better than an upgrade level on the smelter's ZDO. Persistence comes
free, because the upgrade *is* a placed piece — and you can see at a glance which smelters
are upgraded. And it costs floor space as well as materials, so upgrading a row of eight is
a decision about your base rather than a switch you flip once.

Capacity only. Never throughput — that is the line above.

## Design notes

**Batching is a postfix on the game's own add.** `Smelter.OnAddFuel` / `OnAddOre` and
`Fireplace.UseItem` / `Interact` each validate, remove one item, and fire an RPC. The
postfix only runs when that succeeded, then repeats the last two steps. All the rules —
right item, station not full, player has one — stay in vanilla's hands.

**The add is an RPC, and the ZDO does not reflect it in the same frame.** Re-reading the
fuel level inside the loop returns a stale value and cheerfully overfills. The expected
level is tracked locally instead, starting one above what the ZDO reports because the
original add is still in flight.

**`Fireplace.Interact` does two jobs and returns `true` for both.** When a fire can be
turned off and has fuel, the press was a toggle and never touched your logs — batching
there would put three on the fire for a press meant to snuff it out. The postfix replicates
that branch condition and bows out.

**Ore is re-found every pass** rather than reusing the original argument. That argument is
null when you press with an empty hand and the game picks the item itself, and the chosen
stack can run out mid-batch.

**Reflection targets are checked at startup.** Five private members are looked up by name,
and `AccessTools` answers a name it cannot find with `null`. Unchecked, a renamed method in
some future game version surfaces as a `NullReferenceException` the first time you stoke a
fire, with nothing tying it back to the update. Instead it is verified once in `Awake`,
logged as an error naming the missing members, and batching disables itself.

## Config

`BepInEx\config\robbin.valheim.stoker.cfg`

| Key | Default | What it does |
| --- | --- | --- |
| `SmelterItemsPerAdd` | `3` | Ore or coal per press at any Smelter-based station |
| `FireplaceItemsPerAdd` | `3` | Logs per press at a fire |
| `HopperEnabled` | `true` | Add the buildable hopper |
| `HopperName` | `Hopper` | Name on the hammer and on hover |
| `HopperCost` | `Wood:20,Bronze:5` | Build cost as `Item:Amount` pairs |
| `HopperDonor` | `piece_chest_barrel` | Prefab whose model and icon it borrows |
| `HopperRange` | `4` | How close it must be to the station it feeds |
| `MaxHoppers` | `2` | Most that count for one station |
| `CapacityPerHopper` | `10` | Extra ore and fuel capacity each |
| `Verbose` | `false` | Log each batched add |

`1` restores vanilla behaviour for either. A value already in the `.cfg` beats a new default
in code.

## Building

```bash
dotnet build
```

Deploys to the repo-local `testprofile\`, or build into the shared play profile with
`valheim-own-profile\build-all.ps1`.

## What to check

1. One press at a smelter puts in 3 coal, and 3 ore.
2. Pressing at a nearly-full smelter tops it to exactly full and no further.
3. With 2 coal left, a press uses both and stops — no phantom consumption.
4. **Toggling a hearth off does not consume logs.**
5. Holding to refill a campfire behaves as it always did.
6. A charcoal kiln batches wood.
7. Check the log at startup for a missing-members error.
8. **The Hopper appears on the hammer** with a barrel icon — check the log for a
   `Hopper donor ... does not exist` warning if it does not.
9. Build one by a smelter: capacity should go 10 → 20 for both ore and fuel.
10. **A charcoal kiln should gain ore capacity but no fuel slot.** A kiln has no fuel at
    all, and handing it one would have it refuse to work until fed coal it cannot take.
11. Tear the hopper down and confirm the capacity drops back.
12. Confirm a hopper is not a chest — it should have no inventory to open.

## Author

Stoker is an original mod by **Robbin Thijssen** (Thijssen Software).
Copyright (c) 2026 Robbin Thijssen. See `LICENSE`.
