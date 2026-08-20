# Changelog

Notable changes to Stoker. Format follows [Keep a Changelog](https://keepachangelog.com),
and the mod uses [semantic versioning](https://semver.org).

## [1.0.0] - 2026-08-19

**1.0 is the batching.** The two upgrade pieces are off by default, and that default is the
only thing about them that changed.

Stoker is going back into the Longhouse pack, which is a different bar from running it here.
A pack member is handed to somebody who chose the pack, not the mod, so the question stops
being "does this work" and becomes "what can this cost a person who never opted into it".

Batching costs nothing. It installs no prefabs, it writes nothing to a world, and by its own
balance line three ore in one press is three presses of one ore - so removing the mod leaves a
world exactly as it would have been. The upgrades cannot say that. They are registered
prefabs, and ZNetScene **discards a ZDO whose prefab name no longer resolves**: a world that
later loads without them loses every Tun and Woodrack standing in it, silently. That is a fair
trade for somebody who read the setting and turned it on. It is a trap in a pack.

So they stay in the code, they stay working, and they stay off. `Upgrades.Enabled = true` is
the whole of turning them back on - and note that **a value already in your `.cfg` beats this
new default**, so an existing install keeps them until that line is edited.

### Changed

- `Upgrades.Enabled` now defaults to **false**, with the reason in the setting's own comment.
- The README leads with what 1.0 actually is, and the Core section now says why no version
  gate is needed at the shipped default: batching is not a rule two ends can disagree about.
  The gate becomes necessary exactly when the upgrades come on, which is a solo decision.
- The package description no longer advertises the upgrades.

### Unchanged

Everything else. The Shift-held batch at every `Smelter` station and at fires, the `[Shift] x3`
hover line, the capacity matching, the link effect and the diagnostics are all as they were in
0.3.0 - this release is a default and a page, not a rewrite.

## [Unreleased] - the upgrades, still in the code and off

### Both upgrade models remade

The art was the stated reason 0.3 was not 1.0. Two of the three causes were in the
**preview** rather than in the models, which is why previous passes kept not helping.

- **The renders were never at the size the game draws.** Both pieces carry `Scale 1.5`,
  and the preview rendered the raw model beside a 1m cube, so every design was picked
  from a picture two thirds the size of the real thing.
- **The lights were hot enough to flatten everything.** A sun at 3.0 plus a fill at 1.0
  plus a world at 0.7 puts a 0.30 albedo at 0.72 in sRGB, so timber rendered as sand and
  the whole model arrived at one value. Value is most of what says a silhouette works.
- **Nothing was ever in frame with it.** These are only ever seen touching a station, so
  the stage now carries a block of the smelter's measured mass.

With that corrected, both models were rebuilt:

- **Woodrack** is now `stoker_rack_courses`. The logs came from a helper that picked a
  cross-section at random (three, four, five, six or seven sides) which at 2 metres read
  as a frame packed with rubble. Vanilla varies a woodpile's diameter and never its cross
  section, so every piece is a round now. The back is closed, and the roof slopes forwards:
  it had been rotated `-17` about x since the first version, which lifts the *front* edge,
  and a roof rising towards the viewer is why it read as a table.
- **Trough** is now `stoker_trough_casks`. The deck it stood on was a slab across the front
  at exactly the height a cask is widest, cutting both off at the belly; the casks stand on
  the ground now, with nothing round them at all - a kerb was tried and read as the pallet
  the deck had just been taken away for being. The cask itself was straight-sided where a cask bulges,
  had its staves modelled as twenty square posts where vanilla paints them on a turned
  cylinder, and at 0.90 × 1.35m stood a head over the 0.84 × 1.10 `barrell` it imitates. It
  is now vanilla's size, turned and bulged, with hoops thin enough to read as iron bands.

Both are under budget: 1,472 and 2,024 triangles against a ceiling of 3,500. The rejected
designs are shelved in `assets\variants\`, including the shapes these replace, so a config
line brings any of them back.

**Not yet seen in game.** The models are built, exported and wired up; nobody has stood
next to one.

## [0.3.0] - 2026-08-16

First published release. Earlier numbers were development only and never went out.

### The balance line

> **It changes how often you walk to a smelter. It never changes what comes out of one.**

`m_secPerProduct` and `m_fuelPerProduct` are never touched. Three ore in one press costs
exactly three ore, and twenty iron takes the same time and burns the same coal whether it
went in as one load or three. You buy fewer trips, not more metal. This replaces an auto-fuel
mod and deliberately is not one, since auto-feeding deletes the mid-game logistics problem rather
than easing it.

### Batching

- **Hold Shift and press** at a smelter and three ore go in instead of one. Same for coal,
  and for logs on a campfire, hearth or torch.
- Held rather than toggled, because a plain press has to stay exactly vanilla. Topping a
  nearly-full smelter with one last ore is a thing you actually want to do, and a mod that
  batches unconditionally has taken the single add away rather than added a batch. Set
  `BatchModifier` to `None` if you disagree.
- A held modifier is invisible, so the station's hover text says so: a smelter you can batch
  shows a `[Shift] x3` line in the game's own key-prompt style.
- Covers **every `Smelter`-based station** (smelter, charcoal kiln, blast furnace, windmill,
  spinning wheel, eitr refinery) because they are all the same component, so modded ones are
  included for free.

### Upgrades

- **Two buildable upgrade pieces** that raise a station's capacity, each with its own model,
  icon and capacity figure.
- Capacity scales from the station's own rather than being a flat number, so an upgrade means
  the same thing on a kiln as on a blast furnace.
- They use the game's own station-link drawing, so the connection reads the way vanilla's
  does, and `m_isUpgrade` is set so the build menu draws the star.

### Known limits

- Both features have been used in a real session. **The art is what is unsettled**: the
  trough and the woodrack read acceptably at 128px and less well at eye height, and are being
  reworked. That is the reason this is 0.3 and not 1.0.
- Rejected models are shelved rather than shipped, so two pieces appear on the hammer rather
  than eighteen.
