# Changelog

Notable changes to Kynda. Format follows [Keep a Changelog](https://keepachangelog.com),
and the mod uses [semantic versioning](https://semver.org).

## [1.0.0] - 2026-08-25

Both halves ship: the batching, and the two upgrade pieces.

### The upgrades are in, and so is the gate

They were briefly cut for a pack release and then put back, and the two decisions belong
together rather than one at a time. A Tun and a Woodrack are **registered prefabs**, and
ZNetScene discards a ZDO whose prefab name will not resolve rather than erroring - so a world
that later loads without this mod does not fail to show what you built, it deletes it.

That is why Core is a dependency again, soft, with `Suite.Register` at `Requirement.Everyone`.
The reference and the registration go together and never one without the other: ungated, the
mod has no way to stop a mismatched client quietly eating somebody's buildings. Without Core
installed everything still works and the log says plainly what is unprotected.

### Each upgrade now serves exactly one station

**The Tun upgrades a smelter. The Woodrack upgrades a charcoal kiln.** Nothing else.

Which *kind* of bin a station could take is still read off its own components, a fuel slot or
not - that part is a fact about how a station works and it still means a modded station lands
on the right side of the split. But which stations actually get one is a named list now,
because that is a decision about what the mod is for. A blast furnace and an eitr refinery
would have matched on components and are late-game stations that need no help; a windmill and
a spinning wheel are single-input like the kiln and are not what a rack of split logs is a
picture of.

`Trough.Stations` and `Woodrack.Stations` are config, so a modded station that wants in is a
line rather than a rebuild. A bin beside a station it does not serve says it is feeding
nothing rather than pretending.

### The Tun's prefab is renamed

`kynda_hopper` becomes **`kynda_tun`**. The old name was inherited from the single generic
bin this piece replaced two designs ago, and a prefab name is permanent from the first one
built in any world - so the only free moment to fix one is before the mod has ever shipped.
That moment is now. After this release it cannot be touched again without deleting every Tun
standing in every world that has ever run it.

**If you have a Tun standing in a test world, it is gone.** Nothing was published, so this is
the whole exposure.

### One per station

`MaxPerStation` is 1. These are a one-time improvement rather than something to stack, and the
capacity figures are chosen to land on a round number exactly once - a kiln at 50 from 25, a
smelter at 30 from 10. A second bin changes nothing and says so when you look at it, because a
silent no-op reads as a bug. The README claimed 2 for a while; the code never did.

### The Tun is remodelled, and the rack's frame is its own surface

Two art fixes, and both came out of measuring rather than looking.

**The old Tun wore four palettes.** Measured by face count it was iron 29%, ore 26%, coal
26% and wood 19% - so a third of it was hoops, half was visible contents, and the timber
that should have been the object was a fifth of it. Every vanilla prop ripped here is one
material on one submesh, and `barrell`'s iron hoops are **painted into its wood texture**
rather than modelled. The replacement, `kynda_tun_casks`, is one group: two upright casks,
hoops as shallow rings in the same timber, no contents. 716 triangles against 2,376.

It was chosen from four built to the same rules - casks, a hopper, a bin under a lean-to,
and a long trough - staged at the 1.5 scale the runtime applies, beside a block of the
smelter's measured mass. The other three are in `assets/variants/` with their icons.

**The rack's frame no longer wears the woodpile.** It had two groups, log sides and sawn
ends, which meant the posts, sill, back board and lean-to roof were painted with split
billets - a frame apparently built out of firewood. It has three now: `wood` for the
courses, `wood_end` for the sawn discs, and `frame` for the structure, borrowing
`wood_beam`. One material is right for a prop and two for furniture, and a rack is
furniture holding a prop.

`SkinDonors` takes `group=prefab` pairs, so `wood_stack,frame=wood_beam` is the default and
either half can be retargeted without a rebuild.

### Batching, unchanged

Hold Shift, three ore or coal per press at any `Smelter` station, three logs at a fire. `1`
restores vanilla for either. The `[Shift] x3` hover line exists because a held modifier is
otherwise invisible.

## [1.0.0] - 2026-08-25 (the model rework, which also ships here)

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

- **Woodrack** is now `kynda_rack_courses`. The logs came from a helper that picked a
  cross-section at random (three, four, five, six or seven sides) which at 2 metres read
  as a frame packed with rubble. Vanilla varies a woodpile's diameter and never its cross
  section, so every piece is a round now. The back is closed, and the roof slopes forwards:
  it had been rotated `-17` about x since the first version, which lifts the *front* edge,
  and a roof rising towards the viewer is why it read as a table.
- **Trough** is now `kynda_trough_casks`. The deck it stood on was a slab across the front
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
