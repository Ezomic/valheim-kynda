# Stoker

Fewer trips to the smelter. Same amount of metal out of it.

Built against the installed game (0.221.12, Unity 6000.0.61, BepInEx 5.4.23.3, Harmony 2.9).

## The balance line

This replaces an auto-fuel mod, and it deliberately is not one. Auto-feeding does not make
Valheim more convenient so much as delete a system from it. You never think about coal
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
| Two upgrade pieces that raise capacity | **work in game**; models remade, not yet seen in game |

Both features have been used in a real session. The art was the reason this was 0.3 and not
1.0: the trough and the woodrack read acceptably at 128px and less well at eye height. Both
have been remade, and the remade pair has not been looked at in game yet.

## Batching

**Hold Shift** and press at a smelter, and three ore go in instead of one. Same for coal,
and for logs on a campfire, hearth or torch.

The modifier is held rather than toggled because a plain press has to stay exactly vanilla.
A mod that batches unconditionally has taken the single add away rather than added a batch,
and topping a nearly-full smelter with one last ore is a thing you actually want to do. Set
`BatchModifier` to `None` to make batching the default and give up the one-at-a-time press.

Because a held modifier is invisible, the station's hover text says so: a smelter you can
batch shows a `[Shift] x3` line under the usual use prompt, in the game's own key-prompt
style.

It covers every `Smelter`-based station (smelter, charcoal kiln, blast furnace, windmill,
spinning wheel, eitr refinery) because they are all the same component, so modded ones come
along for free. Fireplaces are a separate class and are handled alongside.

Batching stops early at the station's capacity or when you run out, so it can never put in
more than pressing repeatedly would have.

## The two upgrades

Two pieces, not one, because a charcoal kiln eats wood and a smelter eats ore and coal. A
single generic bin looked like it belonged to neither: it was a box that said "storage" and
nothing else.

| Piece | Cost | Serves |
| --- | --- | --- |
| **Tun**, two open casks, one of ore and one of coal | 20 fine wood, 15 iron nails | Smelter, blast furnace |
| **Woodrack**, rounds stacked in courses under a lean-to roof | 25 fine wood, 20 deer hide, 25 bronze nails | Charcoal kiln, windmill, spinning wheel |

Build one from the hammer's Crafting tab within 4m of the station it serves. Look at one and
it tells you which station it is feeding and what that station's capacity now is, or says
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
single rule gives both: a flat amount misses one end, and doubling gave the kiln its 50 but
left the smelter at 20.

The trough's coal figure is twice its ore figure because a smelter burns two coal for every
ore it melts. Matching them would leave the coal gone with a third of the ore still waiting,
which is the upgrade only half working.

**Which piece serves which station is decided on the station's own numbers, not a list of
names.** A station with a fuel slot takes the trough; one without takes the woodrack. That is
the same component-level matching the capacity component uses, so a modded station lands on
the right side without anyone naming it. It also means the windmill and spinning wheel accept
a woodrack, which is thematically odd and mechanically correct, since they are single-input
stations, which is exactly what the rack is for.

Bronze gates the trough behind the smelter it upgrades, so it cannot exist before there is
anything to smelt. The woodrack deliberately is **not** gated that way: a charcoal kiln is a
Black Forest build, and an upgrade you cannot build alongside its station is one you never
build at all.

A piece whose materials you have never held is absent from the hammer menu rather than
greyed out, which is vanilla behaviour: on a character that has never picked up bronze the
Tun is simply missing while the Woodrack is there. `TestMode` drops both to one wood.

Capacity only. Never throughput. That is the line above.

## Design notes

How batching rides the game's own add, why the trough still answers to its old prefab name,
how the surfaces and the link effect are borrowed, and the manual pass before a release:
[DESIGN.md](DESIGN.md).

## Stoker does not use Core

Stoker installs and runs entirely on its own, with no reference to
[Core](https://github.com/Ezomic/valheim-core) at all. It was a soft dependency until the
mod came out of the server pack; with nothing to register against, a compile-time
reference and a runtime check that only ever answers "not installed" were moving parts
earning nothing.

What that gives up is the **version gate**, a handshake that compares mod versions and
build ids on connect and refuses a client that does not match. It matters here more than
for most mods, because these upgrades are registered prefabs: a client that cannot
resolve a prefab name **discards the ZDO rather than erroring**, so a mismatch does not
fail loudly, it deletes every Tun and Woodrack already standing in that world.

Solo, none of that applies. If Stoker is ever shipped to other people again, the
reference and the `Suite.Register` call go back together, never one without the other.

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
| `OreCapacity` / `FuelCapacity` | per piece | Extra items each upgrade adds; see the Tun / Woodrack sections |
| `ShowLink` | `true` | Draw the game's station-link effect to the station when you look at an upgrade |
| `LinkHeight` | `0.8` | How far up the upgrade the link starts, in metres |

### Tun / Woodrack

The config section is still `[Trough]`. Renaming a section resets every saved setting
under it, which is a worse trade than a stale header. The prefab name is still
`stoker_hopper` for a harder reason: ZDOs key on its hash, so changing it destroys
every one already standing.

Each piece has its own section with the same four keys.

| Key | Tun | Woodrack |
| --- | --- | --- |
| `Name` | `Tun` | `Woodrack` |
| `Cost` | `FineWood:20,IronNails:15` | `FineWood:25,DeerHide:20,BronzeNails:25` |
| `Model` | `stoker_trough_casks.obj` | `stoker_rack_courses.obj` |
| `Scale` | `1.5` | `1.5` |
| `OreCapacity` | `20` | `25` |
| `FuelCapacity` | `40` | *(none, its stations have no fuel slot)* |

`Model` carries its own collision and icon: the `.col` sidecar and the `_icon.png` are
matched by filename, so dropping in a new model brings its shape and its picture with it.
`assets\variants\` holds every rejected design, the twin-barrel trough and the first lean-to
among them, so trying one is a config line and a relaunch, not a rebuild. The csproj does not
copy that folder, so a shelved shape is buildable without being deployed; move a file up into
`assets\` to put it back in play. A variant with no rendered icon falls back to the donor's,
with a warning.

### Diagnostics

| Key | Default | What it does |
| --- | --- | --- |
| `TestMode` | `false` | Both upgrades cost one wood, so they can be checked without bronze |
| `Verbose` | `false` | Log each batched add |
| `PrefabSearch` | *(empty)* | Words to search loaded prefab names for, when hunting a material donor |

`SmelterItemsPerAdd` or `FireplaceItemsPerAdd` set to `1` restores vanilla behaviour for
either.

`PrefabSearch` defaults off because it indexes every loaded object carrying a mesh, close to
two thousand, and then writes a few hundred names into a log shared with every other mod.
Genuinely useful while hunting for a prefab to borrow a material from, pure cost afterwards.

**A value already in the `.cfg` beats a new default in code.** BepInEx writes every entry to
disk on first run, so changing a default here does nothing on a machine that has already run
the plugin. Edit the `.cfg` too.

## Building

```bash
dotnet build
```

Deploys to the repo-local `testprofile\`, or build into the shared play profile with
`own-profile\build-all.ps1`.

## Author

Stoker is an original mod by **Robbin Thijssen** (Thijssen Software).
Copyright (c) 2026 Robbin Thijssen. MIT licensed. See `LICENSE`.
