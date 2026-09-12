# Kynda

Load a smelter, kiln or fire several items at a time instead of one per press, and build two
pieces that make a smelter or a charcoal kiln hold more.

Kynda never changes throughput. `m_secPerProduct` and `m_fuelPerProduct` are untouched, so
twenty iron takes the same time and burns the same coal whether it went in as one load or
seven. What changes is how often you walk back to the station.

Built against Valheim 1.0.7, Unity 6000.0.75, BepInEx 5.4.23.5, Harmony 2.9.

## Features

- Hold a modifier key (Shift by default) while adding ore, coal or wood and three go in
  instead of one.
- Works on every station with a `Smelter` component: smelter, charcoal kiln, blast furnace,
  windmill, spinning wheel, eitr refinery, and any modded station built on the same class.
- Works on fireplaces that can be refilled: campfire, hearth, bonfire, standing torches.
- The station's hover text shows the modifier, so the feature is discoverable without
  reading this file.
- Two buildable upgrades, the Tun and the Woodrack, that raise the capacity of a smelter or
  a charcoal kiln standing next to them.
- Everything is configurable: the key, the batch size, the upgrade costs, which stations
  they serve, and how much capacity they add.

## Batching

Hold the modifier and press Use on the station.

| Station | What goes in | Default per press |
| --- | --- | --- |
| Smelter, blast furnace, eitr refinery | ore on the ore switch, coal on the wood switch | 3 |
| Charcoal kiln, windmill, spinning wheel | wood or its own input | 3 |
| Campfire, hearth, bonfire, torch | logs | 3 |

Some details worth knowing:

- The modifier is held rather than toggled, so a plain press stays vanilla and you can still
  top up a nearly full smelter with one last ore. Set `BatchModifier` to `None` if you would
  rather batch every time.
- Batching runs after the game's own add has succeeded, so vanilla decides whether the first
  item is allowed at all. Wrong item, empty hands, full station: nothing happens, same as
  before.
- Holding Use on a fireplace to refill it repeats on the game's own timer and is not
  batched. A single press is.
- Pressing Use on a fireplace that is lit and can be turned off is a toggle, not a refill,
  so it never takes logs.
- Set `SmelterItemsPerAdd` or `FireplaceItemsPerAdd` to `1` to restore vanilla for either
  half.

## The upgrades

Two buildable pieces, on the hammer's Crafting tab, marked with the upgrade star. Both need
a Forge in range to build, because both are held together with nails.

| Piece | Cost | Serves | Capacity |
| --- | --- | --- | --- |
| Tun | 20 Fine wood, 15 Iron nails | Smelter | 10 ore becomes 30, 20 coal becomes 60 |
| Woodrack | 25 Fine wood, 20 Deer hide, 25 Bronze nails | Charcoal kiln | 25 wood becomes 50 |

Build one within 4 metres of the station it serves and the station's capacity goes up. The
coal figure is twice the ore figure because a smelter burns two coal per ore; matching them
would run the fuel out with a third of the ore still queued.

One per station. A second Tun beside the same smelter adds nothing, and says so in its hover
text rather than sitting there looking broken. Raise `MaxPerStation` if you want them to
stack.

Look at an upgrade and it draws the game's own station-link effect to the station it is
feeding, the same run of motes a chopping block draws to its workbench. That is how you tell
which piece belongs to which station in a row of eight. An upgrade that is not next to
anything it can serve says so in its hover text.

Each piece serves exactly one station prefab by default: `smelter` for the Tun,
`charcoal_kiln` for the Woodrack. Blast furnaces, eitr refineries, windmills and spinning
wheels are left alone. Both lists are config, so adding a modded station is a line in the
`.cfg` rather than a rebuild.

The models are plain `.obj` files read from beside the DLL at runtime, with a `.col` sidecar
for collision and an `_icon.png` for the hammer icon, matched by filename. Rejected designs
live in `assets\variants\` and are not deployed; copy one up into `assets\` and point
`Model` at it to try it.

**The upgrades register prefabs, and that is permanent.** Valheim keys a placed piece on its
prefab name hash and discards any saved object whose name no longer resolves. Loading a world
without Kynda, or joining a server that does not run it, deletes every Tun and Woodrack
standing there without an error. See Multiplayer below for what prevents that.

Turning `Enabled` off is safe: since 1.1.0 it only hides the pieces from the hammer and
leaves the prefabs registered, so anything already built keeps working.

## Installation

Requires [BepInEx 5.4.2350](https://thunderstore.io/c/valheim/p/denikson/BepInExPack_Valheim/).
BepInEx 5 only; this will not load under BepInEx 6.

**Mod manager:** install [Kynda](https://thunderstore.io/c/valheim/p/Ezomic/Kynda/) from
Thunderstore.

**Manual:** drop the contents of `plugins/Kynda` into
`<Valheim>\BepInEx\plugins\Kynda\`. The `.obj`, `.col` and `.png` files have to sit beside
`Kynda.dll` or the upgrades fall back to the donor prefab's look and icon.

[Longhouse Core](https://thunderstore.io/c/valheim/p/Ezomic/Longhouse_Core/) is optional but
recommended on any server. Kynda works without it.

## Configuration

`BepInEx\config\ezomic.valheim.kynda.cfg`, written on first run.

BepInEx writes every entry to disk the first time the plugin runs, and the saved value beats
a new default in code. If a setting appears to do nothing after an update, check the `.cfg`.

### [Batching]

| Key | Default | Effect |
| --- | --- | --- |
| `BatchModifier` | `LeftShift` | Hold while interacting to batch. `None` makes batching unconditional. Read through Unity's legacy input, so use a keyboard key |
| `SmelterItemsPerAdd` | `3` | Ore or coal per press at any Smelter-based station. `1` restores vanilla |
| `FireplaceItemsPerAdd` | `3` | Logs per press at a fireplace. `1` restores vanilla |

### [Upgrades]

| Key | Default | Effect |
| --- | --- | --- |
| `Enabled` | `true` | Whether the two upgrades appear on the hammer. Off hides them from the next world load; it does not delete what is built |
| `Donor` | `piece_chest_barrel` | Prefab cloned for its machinery (ZNetView, Piece, WearNTear, placement rules). Its look, collision and icon are all replaced, so this is not a visual choice. Falls back to `piece_chest_wood`. Needs a restart |
| `Station` | `forge` | Crafting station you must stand near to build them. Empty or an unknown name leaves the donor's, which is the workbench |
| `Range` | `4` | How close an upgrade must be to the station it feeds, in metres |
| `MaxPerStation` | `1` | How many upgrades of one kind count for a single station |
| `TexelsPerMetre` | `28` | How coarse the borrowed texture is drawn. Vanilla props and piles run 24 to 54; higher eventually reads as flat colour |
| `ShowLink` | `true` | Draw the station-link effect when you look at an upgrade |
| `LinkHeight` | `0.8` | How far up the upgrade the link starts, in metres |

### [Trough] (the Tun)

The section header is still `[Trough]`. Renaming a config section resets every saved value
under it, so it stays as it is.

| Key | Default | Effect |
| --- | --- | --- |
| `Name` | `Tun` | Name on the hammer and in hover text |
| `Stations` | `smelter` | Station prefabs this upgrades, comma separated |
| `Cost` | `FineWood:20,IronNails:15` | Build cost as `Item:Amount` pairs |
| `Model` | `kynda_tun_camp.obj` | OBJ loaded from beside the DLL, with its `.col` and `_icon.png` matched by name |
| `Scale` | `1.0` | Overall size. Scales collision with it |
| `SkinDonors` | `@fi_village_wood:keep,coal=@coal_pile:keep,ore=@copper_ore:0.02/0.30/0.46/0.22` | Which vanilla prefab or material each mesh group borrows its surface from. A bare name covers the whole piece; `group=prefab` overrides one group |
| `OreCapacity` | `20` | Extra ore a served station holds per Tun |
| `FuelCapacity` | `40` | Extra coal a served station holds per Tun |

### [Woodrack]

| Key | Default | Effect |
| --- | --- | --- |
| `Name` | `Woodrack` | Name on the hammer and in hover text |
| `Stations` | `charcoal_kiln` | Station prefabs this upgrades, comma separated |
| `Cost` | `FineWood:25,DeerHide:20,BronzeNails:25` | Build cost as `Item:Amount` pairs |
| `Model` | `kynda_rack_camp.obj` | OBJ loaded from beside the DLL |
| `Scale` | `1.0` | Overall size |
| `SkinDonors` | `@wood_item:keep,frame=@woodwall:keep,roof=@straw_roof:keep,roofalpha=@straw_roof_alpha:keep` | As above |
| `OreCapacity` | `25` | Extra wood a served station holds per Woodrack |

There is no `FuelCapacity` here. The Woodrack only serves stations with no fuel slot, so it
would be a setting that could never do anything.

### [Diagnostics]

| Key | Default | Effect |
| --- | --- | --- |
| `TestMode` | `false` | Both upgrades cost one wood, so they can be built without bronze or iron. Logged loudly at startup |
| `Verbose` | `false` | Log each batched add |
| `VariantMode` | `false` | Put every model in `assets\` on the hammer as its own piece at one wood each, named `var: ...`, to compare them side by side. **Destructive when turned off**: each variant is a registered prefab, and anything built from one vanishes when its name stops existing |
| `SkinTrials` | *(empty)* | Comma-separated donor prefabs. Puts one copy of each upgrade on the hammer per donor, named `skin: ...`. Same destructive warning as `VariantMode` |
| `DumpShader` | `false` | List every property of each borrowed material's shader, with its type |
| `PrefabSearch` | *(empty)* | Comma-separated words. Every loaded prefab whose name contains one is listed in the log. Scans everything loaded, so empty it again when you are done |
| `DonorCarrierLocations` | `Vendor,Hildir` | Fallback only. Location prefabs to stream in if a donor material cannot be loaded directly by name. Blank turns the fallback off |

## Multiplayer

Install Kynda on the server and on every client. The version has to match.

With [Longhouse Core](https://thunderstore.io/c/valheim/p/Ezomic/Longhouse_Core/) installed,
Kynda registers at `Requirement.Everyone`: Core checks each client's Kynda version and build
id on connect and the server rejects a client that does not match. Core also applies the
host's Kynda config to connected clients in memory, without writing to the client's own
config file, so a server's capacity figures and batch sizes are the ones in play.
`BatchModifier` is exempt from that, because a key binding is personal.

Without Core, Kynda still works and logs a warning at startup. Nothing then stops a client
that lacks the mod from connecting, and that client will discard every Tun and Woodrack in
the world it loads. Run it ungated on a world you control, not on one you share with people.

## Compatibility

- Batching hooks `Smelter.OnAddOre`, `Smelter.OnAddFuel`, `Fireplace.UseItem` and
  `Fireplace.Interact` as postfixes, and the capacity component is attached to every prefab
  carrying a `Smelter`. Another mod that adds a Smelter-based station is picked up
  automatically.
- Another mod that changes a station's `m_maxOre` or `m_maxFuel` on the prefab will conflict.
  Kynda captures the base values in `Awake` and recomputes from them every three seconds.
- Kynda does not touch smelting speed, fuel cost or conversion recipes, so it composes with
  mods that do.

## Known limitations

- **Repeated presses can overshoot a station's queue.** The capacity check reads the queue
  size from the station's network object, which updates after the add rather than during it.
  One batched press stops at capacity correctly. Pressing again before the station has caught
  up can push the queue past its maximum, and the game does not clamp the ore queue on its
  own side. Reported on smelters and blast furnaces. Not fixed yet.
- Uninstalling Kynda from a world that has Tuns or Woodracks in it deletes them permanently.
  Break them down first if you want the materials back.

## Troubleshooting

**No `[Shift] x3` line on a station's hover text.** Check `BepInEx\LogOutput.log` for a line
from Kynda saying which reflected game members are missing. If a game update renames a
private method Kynda uses, batching is switched off at startup and says so rather than
throwing later.

**The upgrades are not on the hammer.** Valheim hides a piece whose materials you have never
picked up, rather than greying it out. On a character that has never held bronze the Woodrack
is simply absent. `TestMode` drops both to one wood if you want to check they registered.

**An upgrade is next to its station and nothing changed.** Check the range (4 metres by
default), that the station is one named in that piece's `Stations` list, and that there is
not already a closer upgrade of the same kind counting for it. The hover text says which of
those it is.

**The Tun is magenta or wearing the wrong texture.** It borrows materials the game streams in
on demand. They are loaded by name, and there is a fallback that summons the carrier location.
Both are logged. A dedicated server skips skinning entirely because it draws nothing.

**A config change did nothing.** BepInEx already wrote that key to the `.cfg`, and the saved
value wins. Edit the file.

## Bug reports

Report in the [Discord](https://discord.gg/hJzAVaZ5wb) or on the
[issue tracker](https://github.com/Ezomic/valheim-kynda/issues). Please include:

- `BepInEx\LogOutput.log`
- Whether you were on a server or in single player, and whether Longhouse Core was installed
- Your `ezomic.valheim.kynda.cfg`
- For anything involving a station or a piece, its prefab name
- `AppData\LocalLow\IronGate\Valheim\Player.log` if a vanilla mechanic broke. Gameplay
  exceptions land there, not in the BepInEx log

## Discord

[discord.gg/hJzAVaZ5wb](https://discord.gg/hJzAVaZ5wb) for mod information, updates, support,
bug reports and compatibility questions.

There's also a small EU server running the pack if you want somewhere to play. Details are in
the Discord.

## Design notes

Why the upgrades are buildable pieces rather than a level on the smelter, how batching rides
the game's own add, why the Tun still answers to the `[Trough]` config section, and how the
surfaces and the link effect are borrowed: [DESIGN.md](DESIGN.md).

## Building

```bash
dotnet build
```

Targets net462. Game assemblies are referenced by `HintPath` from the Steam install; no NuGet
packages. Output deploys to the repo-local `testprofile\` by default, or pass
`-p:ProfileDir=` to deploy elsewhere.

## Part of Longhouse

Kynda 1.1.0 is included in the [Longhouse](https://thunderstore.io/c/valheim/p/Ezomic/Longhouse/)
modpack. It behaves exactly the same installed on its own.

## Licence

Kynda is an original mod by Robbin Thijssen (Thijssen Software).
Copyright (c) 2026 Robbin Thijssen. MIT licensed, see [LICENSE](LICENSE).
