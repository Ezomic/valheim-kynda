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

## Status: v1.0

| Feature | State |
| --- | --- |
| Add several items per press | **works in game** |
| Two upgrade pieces that raise capacity | work in game; **models not yet seen at eye height** |

Both halves ship. The batching has been used in a real session. The upgrades work and their
models were remade, but the remade pair has only been judged from renders, which is the one
thing still outstanding.

**The upgrades register prefabs, and that is permanent.** ZNetScene keys a piece on its name
hash and **discards a ZDO whose name no longer resolves**, so a world that later loads without
this mod loses every Tun and Woodrack standing in it, silently and without an error. That is
why Stoker registers with [Core](https://github.com/Ezomic/valheim-core)'s version gate: the
gate refuses a mismatched connection rather than letting it quietly eat what you built.

`Upgrades.Enabled = false` turns them off, for a world where you want the batching alone.

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

**One per station.** These are a one-time improvement rather than something to stack, and the
capacity figures are chosen to land on a round number exactly once. A second bin beside the
same station changes nothing and says so when you look at it, because a silent no-op reads as
a bug. `MaxPerStation` raises it if you disagree.

| Station | Bare | With its upgrade |
| --- | --- | --- |
| Charcoal kiln | 25 wood | **50** |
| Smelter | 10 ore, 20 coal | **30, 60** |

**Each piece carries its own figure**, rather than the mod having one. The kiln holds 25 and
should land on 50; the smelter holds 10 and should land on 30. That is +25 and +20, and no
single rule gives both: a flat amount misses one end, and doubling gave the kiln its 50 but
left the smelter at 20.

The trough's coal figure is twice its ore figure because a smelter burns two coal for every
ore it melts. Matching them would leave the coal gone with a third of the ore still waiting,
which is the upgrade only half working.

**The Tun upgrades a smelter. The Woodrack upgrades a charcoal kiln. Nothing else.**

Which *kind* of bin a station could take is still read off its own components - a fuel slot
means the Tun, no fuel slot means the Woodrack - but which stations actually get one is a
named list, because that is a decision about what the mod is for rather than a fact about how
a station works. A blast furnace and an eitr refinery are fuelled and would match on
components alone; they are late-game stations that do not need the help. A windmill and a
spinning wheel are single-input like the kiln; neither is what a rack of split logs is a
picture of.

Both lists are config, so a modded station that wants in, or a server that disagrees, is a
line in the `.cfg` rather than a rebuild. A bin standing beside a station it does not serve
tells you it is feeding nothing rather than pretending.

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

## Stoker uses Core, and why it has to

[Core](https://github.com/Ezomic/valheim-core) is a **soft** dependency: install Stoker on its
own and it works. What Core adds is the **version gate**, a handshake that compares mod
versions and build ids on connect and refuses a client that does not match.

Batching would not need one. Three ore in one press is three presses of one ore - same time,
same coal, same metal - so a player who has it and a player who does not are playing the same
game at different walking speeds, and there is nothing for a server to hold anyone to.

**The upgrades are a different matter, and they are why the gate is here.** They are
registered prefabs, and a client that cannot resolve a prefab name **discards the ZDO rather
than erroring**. A mismatch does not fail loudly and it does not merely hide a Tun: it deletes
every Tun and Woodrack standing in that world. The gate refuses that connection instead, which
is the only way the mod can protect what somebody built.

Without Core the upgrades still work and the mod says so in the log - it just cannot stop that
happening. Run it ungated on a world you control, not on one you share.

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
| `Enabled` | `true` | Add both buildable upgrades. They register prefabs, so a world that later loads without this mod discards every one already built |
| `Donor` | `piece_chest_barrel` | Prefab cloned for its machinery. Its look, collision and icon are all replaced, so this is not a visual choice |
| `Range` | `4` | How close an upgrade must be to the station it feeds |
| `MaxPerStation` | `1` | How many of one kind count for a single station. One, because these are a one-time improvement and the figures land on a round number exactly once |
| `Stations` | per piece | Which station prefabs each upgrade serves. `smelter` for the Tun, `charcoal_kiln` for the Woodrack |
| `OreCapacity` / `FuelCapacity` | per piece | Extra items each upgrade adds; see the Tun / Woodrack sections |
| `ShowLink` | `true` | Draw the game's station-link effect to the station when you look at an upgrade |
| `LinkHeight` | `0.8` | How far up the upgrade the link starts, in metres |

### Tun / Woodrack

The config section is still `[Trough]`. Renaming a section resets every saved setting
under it, which is a worse trade than a stale header. The prefab name is still
`stoker_tun` as of 1.0.0, renamed from `stoker_hopper` while nothing had shipped and
there was therefore nothing standing to lose. From the first release it is fixed for good:
ZDOs key on its hash, so changing it destroys
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
