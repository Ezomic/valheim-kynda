# Stoker design notes

Why it works the way it does, and how it is built. None of this is needed to play; for that
see the [README](README.md).

## Why the upgrades are pieces, not a level on the smelter

Modelled on vanilla's `StationExtension`, the way a chopping block upgrades a workbench,
because that is the game's own idiom for "upgrade by building something next to it".
`StationExtension` itself is hardwired to `CraftingStation` and a smelter is not one, so it
keeps its own registry, but the shape is the same, down to the link effect being poked from
`GetHoverText` and torn down on a timer.

Two things make this better than an upgrade level on the smelter's ZDO. Persistence comes
free, because the upgrade *is* a placed piece, and you can see at a glance which smelters
are upgraded. And it costs floor space as well as materials, so upgrading a row of eight is
a decision about your base rather than a switch you flip once.

## Why the models were picked twice

Two of the three causes turned out to be in the *preview*, not the models. The renders were
taken at the raw model size while the runtime applies `Scale 1.5`, so every design was picked
from a picture two thirds the size of the real thing; and the lights were hot enough to put a
0.30 albedo at 0.72 in sRGB, so everything arrived at one flat value and no silhouette could
be judged. The stage now renders at the scale the game draws, under lights that keep timber
looking like timber, with a block of the smelter's measured mass standing beside the piece,
because that is the only context these are ever seen in.

## Why a piece can be missing from the hammer menu

> **A piece whose materials you have never held does not appear in the hammer menu at all**,
> not greyed out, absent. `PieceTable.UpdateAvailable` lists a piece only if it is a known
> recipe, and `RequirementMode.IsKnown` requires every item in its cost to be in
> `m_knownMaterial`. So on a character that has never picked up Bronze, the Tun is simply
> missing while the Woodrack is there. That is vanilla behaviour and not a registration
> failure. Check the log for `Both upgrades added to the hammer` before hunting for a bug.
> `TestMode` drops both to one wood, which makes them visible immediately.

## Implementation notes

**Batching is a postfix on the game's own add.** `Smelter.OnAddFuel` / `OnAddOre` and
`Fireplace.UseItem` / `Interact` each validate, remove one item, and fire an RPC. The
postfix only runs when that succeeded, then repeats the last two steps. All the rules,
right item, station not full, player has one, stay in vanilla's hands.

**The add is an RPC, and the ZDO does not reflect it in the same frame.** Re-reading the
fuel level inside the loop returns a stale value and cheerfully overfills. The expected
level is tracked locally instead, starting one above what the ZDO reports because the
original add is still in flight.

**`Fireplace.Interact` does two jobs and returns `true` for both.** When a fire can be
turned off and has fuel, the press was a toggle and never touched your logs, so batching
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
methods matched by name, and Harmony resolves patch targets when `PatchAll` runs, and one that
cannot be found throws and takes every patch in that class with it. Kept in its own class,
a future rename costs the hint and leaves the feature working.

**No `BepInProcess`.** It is a whitelist, and a dedicated server runs `valheim_server.exe`.
The upgrades are registered prefabs, and `ZNetScene` discards any ZDO whose prefab name does
not resolve, so a server without this mod would silently destroy every one already standing.

**The trough's prefab is still named `stoker_hopper`.** It inherited the name from the single
generic bin it replaced. Prefab names are permanent: `ZNetScene` keys on
`name.GetStableHashCode()` and saved ZDOs store that hash, so renaming it would have
destroyed every bin already placed in a world, silently. Only its display name, model and
icon changed.

**Surfaces are borrowed, and their UVs are fitted to the atlas.** Each material group in the
OBJ (wood, iron, stone, ore, coal) takes a real material off a vanilla prefab, so texel
density, palette and weathering come along because they are the game's own. Valheim's piece
textures are atlases though: a material uses a strip of a sheet, so UVs running 0..1 sample
the whole thing and pick up the neighbouring tiles. `Skins` measures the donor's rect from
its **largest single triangle**, not min/max across the mesh, which for `stone_wall_2x1`
spans 71% of the sheet, and remaps clamped, never wrapped.

**The link effect is the game's, and the scale is the part that matters.**
`StationExtension.StartConnectionEffect` rotates the effect so its local +Z faces the station
and then sets `localScale` to `(1, 1, distance)`, and the stretch along Z is what turns a
stationary puff into something that spans the gap. Ours does the same, with the prefab
borrowed off whatever carries a `StationExtension` rather than off a named one, so it does
not depend on the forge and workbench extensions keeping their prefab names.

**Anything the donor emitted is stripped.** The model swap destroys `MeshRenderer` objects,
and a particle system's renderer is a `ParticleSystemRenderer`, so a donor's effect would
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

## What to check

Batching:

1. **Shift**-press at a smelter puts in 3 coal, and 3 ore. A plain press puts in 1.
2. The smelter's hover text shows a `[LeftShift] x3` line.
3. Shift-pressing at a nearly-full smelter tops it to exactly full and no further.
4. With 2 coal left, a press uses both and stops, with no phantom consumption.
5. **Toggling a hearth off does not consume logs**, with or without Shift.
6. Holding to refill a campfire behaves as it always did.
7. A charcoal kiln batches wood.
8. Check the log at startup for a missing-members error.

The upgrades:

9. **Both appear on the hammer's Crafting tab, each with its own icon**: a stack of rounds
   under a roof, and two casks. A closed barrel with a lid means neither the
   in-game shot nor the `_icon.png` was found and it is wearing the donor's; the log says
   which file it wanted.
9b. **The logs read as firewood, not as rubble.** Every round should be a round. Anything
   with a three- or four-sided end means the model came from `billet()` rather than
   `round_log()`, and at 2m that reads as a cage full of rocks.
10. Build a trough by a smelter: it should read **ore 20, fuel 40**, doubled from 10 and 20.
11. Build a woodrack by a charcoal kiln: it should read **ore 50**, doubled from 25, and
    **still no fuel slot**. A kiln has no fuel at all, and handing it one would have it
    refuse to work until fed coal it cannot take.
12. **A woodrack beside a smelter should do nothing**, and say so on hover, and a trough
    beside a kiln likewise. Each piece only counts for the kind of station it serves.
13. Tear one down and confirm the capacity drops back within about three seconds.
14. Confirm neither is a chest; they should have no inventory to open.
15. Look closely at the timber: the borrowed materials should read as one clean tile, not as
    a smear of several. Banding or fragments of a neighbouring texture means the atlas remap
    picked the wrong rect for that group.
16. **Look at an upgrade and the link should run to its station** and stop about a second
    later. Check the log for `Link effect borrowed from ...` naming which extension it came
    off; a warning there means no `StationExtension` was loaded to borrow from.
17. A `Stripped inherited particle system` line means the donor was emitting something of
    its own, which is now gone. No such line means it never was.
