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

## Status: v0.3

| Feature | State |
| --- | --- |
| Add several items per press | **works in game** |
| Two upgrade pieces that raise capacity | **work in game**; models being revisited |

Both features have been used in a real session. What is unsettled is the art: the trough and
the woodrack read acceptably at 128px and less well at eye height, and are being reworked.

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

### The two upgrades

Two pieces, not one, because a charcoal kiln eats wood and a smelter eats ore and coal. A
single generic bin looked like it belonged to neither — it was a box that said "storage" and
nothing else.

| Piece | Cost | Serves |
| --- | --- | --- |
| **Trough** — two bays, one of ore and one of coal, on legs | 20 wood, 5 bronze | Smelter, blast furnace |
| **Woodrack** — split logs stacked under a roof | 25 wood, 10 stone | Charcoal kiln, windmill, spinning wheel |

Build one from the hammer's Crafting tab within 4m of the station it serves. Look at one and
it tells you which station it is feeding and what that station's capacity now is — or says
plainly that it is feeding nothing, which is what a woodrack parked next to a smelter will
tell you.

**Looking at one also draws the link**, the same run of motes a chopping block draws to its
workbench, so you can see at a glance which station an upgrade belongs to in a row of them.

Two is the limit per station by default.

| Station | Bare | One upgrade | Two |
| --- | --- | --- | --- |
| Charcoal kiln | 25 wood | **50** | 75 |
| Smelter | 10 ore, 20 coal | **30, 60** | 50, 100 |

**Each piece carries its own figure**, rather than the mod having one. The kiln holds 25 and
should land on 50; the smelter holds 10 and should land on 30. That is +25 and +20, and no
single rule gives both — a flat amount misses one end, and doubling gave the kiln its 50 but
left the smelter at 20.

The trough's coal figure is twice its ore figure because a smelter burns two coal for every
ore it melts. Matching them would leave the coal gone with a third of the ore still waiting,
which is the upgrade only half working.

**Which piece serves which station is decided on the station's own numbers, not a list of
names.** A station with a fuel slot takes the trough; one without takes the woodrack. That is
the same component-level matching the capacity component uses, so a modded station lands on
the right side without anyone naming it. It also means the windmill and spinning wheel accept
a woodrack, which is thematically odd and mechanically correct — they are single-input
stations, which is exactly what the rack is for.

Bronze gates the trough behind the smelter it upgrades, so it cannot exist before there is
anything to smelt. The woodrack deliberately is **not** gated that way: a charcoal kiln is a
Black Forest build, and an upgrade you cannot build alongside its station is one you never
build at all.

> **A piece whose materials you have never held does not appear in the hammer menu at all** —
> not greyed out, absent. `PieceTable.UpdateAvailable` lists a piece only if it is a known
> recipe, and `RequirementMode.IsKnown` requires every item in its cost to be in
> `m_knownMaterial`. So on a character that has never picked up Bronze, the Trough is simply
> missing while the Woodrack is there. That is vanilla behaviour and not a registration
> failure — check the log for `Both upgrades added to the hammer` before hunting for a bug.
> `TestMode` drops both to one wood, which makes them visible immediately.

Modelled on vanilla's `StationExtension` — the way a chopping block upgrades a workbench —
because that is the game's own idiom for "upgrade by building something next to it".
`StationExtension` itself is hardwired to `CraftingStation` and a smelter is not one, so it
keeps its own registry, but the shape is the same, down to the link effect being poked from
`GetHoverText` and torn down on a timer.

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
The upgrades are registered prefabs, and `ZNetScene` discards any ZDO whose prefab name does
not resolve — so a server without this mod would silently destroy every one already standing.

**The trough's prefab is still named `stoker_hopper`.** It inherited the name from the single
generic bin it replaced. Prefab names are permanent — `ZNetScene` keys on
`name.GetStableHashCode()` and saved ZDOs store that hash — so renaming it would have
destroyed every bin already placed in a world, silently. Only its display name, model and
icon changed.

**Surfaces are borrowed, and their UVs are fitted to the atlas.** Each material group in the
OBJ — wood, iron, stone, ore, coal — takes a real material off a vanilla prefab, so texel
density, palette and weathering come along because they are the game's own. Valheim's piece
textures are atlases though: a material uses a strip of a sheet, so UVs running 0..1 sample
the whole thing and pick up the neighbouring tiles. `Skins` measures the donor's rect from
its **largest single triangle** — not min/max across the mesh, which for `stone_wall_2x1`
spans 71% of the sheet — and remaps clamped, never wrapped.

**The link effect is the game's, and the scale is the part that matters.**
`StationExtension.StartConnectionEffect` rotates the effect so its local +Z faces the station
and then sets `localScale` to `(1, 1, distance)` — the stretch along Z is what turns a
stationary puff into something that spans the gap. Ours does the same, with the prefab
borrowed off whatever carries a `StationExtension` rather than off a named one, so it does
not depend on the forge and workbench extensions keeping their prefab names.

**Anything the donor emitted is stripped.** The model swap destroys `MeshRenderer` objects,
and a particle system's renderer is a `ParticleSystemRenderer` — so a donor's effect would
otherwise survive onto a piece that no longer looks remotely like it. The link is the one
deliberate effect these pieces have.

**The star on the build-menu icon is a flag, not art.** `Hud` builds each menu slot from a
prefab carrying an `"upgrade"` child and does `m_upgrade.SetActive(piece.m_isUpgrade)`, so
matching vanilla's station upgrades meant setting `Piece.m_isUpgrade`, not compositing a star
into the rendered PNG. Worth knowing before painting one on.

**Icons are rendered, not borrowed.** Without one, a piece keeps the donor's icon, and the
donor is a barrel. An icon showing the wrong object is worse than a plain one, because the
hammer menu is where you choose. `tools/upgrade_icons.py` reads the shipped `.obj` back in
and renders a 128px transparent PNG beside it; the runtime finds it by name and reaches
`Texture2D.LoadImage` by reflection, since `UnityEngine.ImageConversionModule` targets
netstandard 2.1 and this builds against net462.


## Core is optional

Stoker installs and runs on its own. [Core](https://github.com/Ezomic/valheim-core) is a
**soft** dependency: present, it is used; absent, nothing here is degraded. Installing
Stoker from Thunderstore no longer installs Core with it.

What Core adds is the **version gate** — a handshake that compares mod versions and build
ids on connect and refuses a client that does not match. Without it nothing refuses a client that lacks the mod, and this registers prefabs into `ZNetScene`: a client that cannot resolve one **discards the ZDO rather than erroring**, destroying what is already standing in the world.

Solo, none of that applies and Core is not needed at all.

## Config

`BepInEx\config\ezomic.valheim.stoker.cfg`

### Batching

| Key | Default | What it does |
| --- | --- | --- |
| `BatchModifier` | `LeftShift` | Hold to batch. `None` makes batching unconditional |
| `SmelterItemsPerAdd` | `3` | Ore or coal per press at any Smelter-based station |
| `FireplaceItemsPerAdd` | `3` | Logs per press at a fire |

### Upgrades

| Key | Default | What it does |
| --- | --- | --- |
| `Enabled` | `true` | Add both buildable upgrades |
| `Donor` | `piece_chest_barrel` | Prefab cloned for its machinery. Its look, collision and icon are all replaced, so this is not a visual choice |
| `Range` | `4` | How close an upgrade must be to the station it feeds |
| `MaxPerStation` | `2` | Most of one kind that count for one station |
| `OreCapacity` / `FuelCapacity` | per piece | Extra items each upgrade adds — see the Trough / Woodrack sections |
| `ShowLink` | `true` | Draw the game's station-link effect to the station when you look at an upgrade |
| `LinkHeight` | `0.8` | How far up the upgrade the link starts, in metres |

### Trough / Woodrack

Each piece has its own section with the same four keys.

| Key | Trough | Woodrack |
| --- | --- | --- |
| `Name` | `Trough` | `Woodrack` |
| `Cost` | `Wood:20,Bronze:5` | `Wood:25,Stone:10` |
| `Model` | `stoker_trough_raised.obj` | `stoker_kiln_woodrack.obj` |
| `Scale` | `1` | `1` |
| `OreCapacity` | `20` | `25` |
| `FuelCapacity` | `40` | *(none — its stations have no fuel slot)* |

`Model` carries its own collision and icon: the `.col` sidecar and the `_icon.png` are
matched by filename, so dropping in a new model brings its shape and its picture with it.
The `assets\` folder holds the rejected variants too — `stoker_trough_stone.obj`,
`stoker_smelter_orecart.obj` and the rest — so trying one is a config line and a relaunch,
not a rebuild. A variant with no rendered icon falls back to the donor's, with a warning.

### Diagnostics

| Key | Default | What it does |
| --- | --- | --- |
| `TestMode` | `false` | Both upgrades cost one wood, so they can be checked without bronze |
| `Verbose` | `false` | Log each batched add |
| `PrefabSearch` | *(empty)* | Words to search loaded prefab names for, when hunting a material donor |

`SmelterItemsPerAdd` or `FireplaceItemsPerAdd` set to `1` restores vanilla behaviour for
either.

`PrefabSearch` defaults off because it indexes every loaded object carrying a mesh — close to
two thousand — and then writes a few hundred names into a log shared with every other mod.
Genuinely useful while hunting for a prefab to borrow a material from, pure cost afterwards.

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

The upgrades:

9. **Both appear on the hammer's Crafting tab, each with its own icon** — a rack of logs and
   a two-bay trough, not two barrels. A barrel means the `_icon.png` was not found; the log
   says which file it wanted.
10. Build a trough by a smelter: it should read **ore 20, fuel 40** — doubled from 10 and 20.
11. Build a woodrack by a charcoal kiln: it should read **ore 50**, doubled from 25, and
    **still no fuel slot**. A kiln has no fuel at all, and handing it one would have it
    refuse to work until fed coal it cannot take.
12. **A woodrack beside a smelter should do nothing**, and say so on hover — and a trough
    beside a kiln likewise. Each piece only counts for the kind of station it serves.
13. Tear one down and confirm the capacity drops back within about three seconds.
14. Confirm neither is a chest — they should have no inventory to open.
15. Look closely at the timber: the borrowed materials should read as one clean tile, not as
    a smear of several. Banding or fragments of a neighbouring texture means the atlas remap
    picked the wrong rect for that group.
16. **Look at an upgrade and the link should run to its station** and stop about a second
    later. Check the log for `Link effect borrowed from ...` naming which extension it came
    off; a warning there means no `StationExtension` was loaded to borrow from.
17. A `Stripped inherited particle system` line means the donor was emitting something of
    its own, which is now gone. No such line means it never was.

## Author

Stoker is an original mod by **Robbin Thijssen** (Thijssen Software).
Copyright (c) 2026 Robbin Thijssen. MIT licensed — see `LICENSE`.
