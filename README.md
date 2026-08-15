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

## Status: v0.2

| Feature | State |
| --- | --- |
| Add several items per press | built, runs in game, **not play-tested** |
| Hopper piece that raises capacity | built, registers and builds, **not play-tested** |

"Runs in game" means the mod loads, the hopper registers and lands on the hammer, and the
log is clean. Whether the numbers feel right over a real smelting session is untested.

### Batching

**Hold Shift** and press at a smelter, and three ore go in instead of one. Same for coal,
and for logs on a campfire, hearth or torch.

The modifier is held rather than toggled because a plain press has to stay exactly vanilla.
A mod that batches unconditionally has taken the single add away rather than added a batch —
and topping a nearly-full smelter with one last ore is a thing you actually want to do. Set
`BatchModifier` to `None` to make batching the default and give up the one-at-a-time press.

Because a held modifier is invisible, the station's hover text says so: a smelter you can
batch shows a `[Shift] x3` line under the usual use prompt, in the game's own key-prompt
style.

It covers every `Smelter`-based station — smelter, charcoal kiln, blast furnace, windmill,
spinning wheel, eitr refinery — because they are all the same component, so modded ones come
along for free. Fireplaces are a separate class and are handled alongside.

Batching stops early at the station's capacity or when you run out, so it can never put in
more than pressing repeatedly would have.

### The Hopper

Build a **Hopper** from the hammer's Crafting tab (20 wood, 5 bronze) within 4m of a smelter,
kiln or furnace and that station holds **20 more ore and 40 more fuel**. A second hopper adds
another lot. Two is the limit by default.

The two figures differ because a smelter burns two coal for every ore it melts. Matching them
would leave the coal side running out first, and the upgrade would only half work.

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
logged as an error naming the missing members, and the batching patches are never applied.

**The hover hint is patched separately from batching.** Two of its three targets are private
methods matched by name, and Harmony resolves patch targets when `PatchAll` runs — one that
cannot be found throws and takes every patch in that class with it. Kept in its own class,
a future rename costs the hint and leaves the feature working.

**No `BepInProcess`.** It is a whitelist, and a dedicated server runs `valheim_server.exe`.
The hopper is a registered prefab, and `ZNetScene` discards any ZDO whose prefab name does
not resolve — so a server without this mod would silently destroy every hopper already
standing.

## Config

`BepInEx\config\ezomic.valheim.stoker.cfg`

### Batching

| Key | Default | What it does |
| --- | --- | --- |
| `BatchModifier` | `LeftShift` | Hold to batch. `None` makes batching unconditional |
| `SmelterItemsPerAdd` | `3` | Ore or coal per press at any Smelter-based station |
| `FireplaceItemsPerAdd` | `3` | Logs per press at a fire |

### Hopper

| Key | Default | What it does |
| --- | --- | --- |
| `HopperEnabled` | `true` | Add the buildable hopper |
| `HopperName` | `Hopper` | Name on the hammer and on hover |
| `HopperCost` | `Wood:20,Bronze:5` | Build cost as `Item:Amount` pairs |
| `HopperDonor` | `piece_chest_barrel` | Prefab cloned for its Piece/WearNTear machinery and icon |
| `HopperRange` | `4` | How close it must be to the station it feeds |
| `MaxHoppers` | `2` | Most that count for one station |
| `OreCapacityPerHopper` | `20` | Extra ore capacity each |
| `FuelCapacityPerHopper` | `40` | Extra fuel capacity each — double, because coal burns 2:1 |
| `HopperModelFile` | `stoker_hopper.obj` | OBJ read from beside the DLL for the shape |
| `HopperScale` | `1` | Overall size |
| `HopperSquash` | `0.7` | Height multiplier, only applied when falling back to the donor's body |
| `HopperVisual` | *(empty)* | Vanilla prop to wear instead of the built model |
| `HopperVisualScale` | `1` | Size of that grafted prop |

### Diagnostics

| Key | Default | What it does |
| --- | --- | --- |
| `TestMode` | `false` | Hopper costs one wood, and every burning station is free to build |
| `Verbose` | `false` | Log each batched add |
| `LogVisualCandidates` | `false` | List which grafting candidates are loaded |
| `VisualSearch` | *(empty)* | Words to search loaded prop names for |

`SmelterItemsPerAdd` or `FireplaceItemsPerAdd` set to `1` restores vanilla behaviour for
either.

The two diagnostics at the bottom were the scaffolding for choosing a prop to graft, and
both default off: either one indexes every loaded object carrying a mesh — close to two
thousand — and the search then writes a few hundred names into a log shared with every other
mod. Turn them on while picking, off again afterwards.

**A value already in the `.cfg` beats a new default in code.** BepInEx writes every entry to
disk on first run, so changing a default here does nothing on a machine that has already run
the plugin — edit the `.cfg` too.

## Building

```bash
dotnet build
```

Deploys to the repo-local `testprofile\`, or build into the shared play profile with
`own-profile\build-all.ps1`.

## What to check

Batching:

1. **Shift**-press at a smelter puts in 3 coal, and 3 ore. A plain press puts in 1.
2. The smelter's hover text shows a `[LeftShift] x3` line.
3. Shift-pressing at a nearly-full smelter tops it to exactly full and no further.
4. With 2 coal left, a press uses both and stops — no phantom consumption.
5. **Toggling a hearth off does not consume logs**, with or without Shift.
6. Holding to refill a campfire behaves as it always did.
7. A charcoal kiln batches wood.
8. Check the log at startup for a missing-members error.

The hopper:

9. **It appears on the hammer's Crafting tab** — check the log for a
   `Hopper donor ... does not exist` warning if it does not.
10. Build one by a smelter: the ore cap should rise by exactly 20 and the fuel cap by 40
    over whatever that station started with. Read the before/after off the smelter's own
    hover text rather than assuming vanilla's figures.
11. **A charcoal kiln should gain ore capacity but no fuel slot.** A kiln has no fuel at
    all, and handing it one would have it refuse to work until fed coal it cannot take.
12. Tear the hopper down and confirm the capacity drops back within about three seconds.
13. Confirm a hopper is not a chest — it should have no inventory to open.
14. Turn `TestMode` on and confirm smelters are free to build; turn it off and confirm the
    real cost comes back without restarting the game.

## Author

Stoker is an original mod by **Robbin Thijssen** (Thijssen Software).
Copyright (c) 2026 Robbin Thijssen. MIT licensed — see `LICENSE`.
