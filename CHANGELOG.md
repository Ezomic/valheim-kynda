# Changelog

Notable changes to Stoker. Format follows [Keep a Changelog](https://keepachangelog.com),
and the mod uses [semantic versioning](https://semver.org).

## [0.3.0] — 2026-08-16

First published release. Earlier numbers were development only and never went out.

### The balance line

> **It changes how often you walk to a smelter. It never changes what comes out of one.**

`m_secPerProduct` and `m_fuelPerProduct` are never touched. Three ore in one press costs
exactly three ore, and twenty iron takes the same time and burns the same coal whether it
went in as one load or three. You buy fewer trips, not more metal. This replaces an auto-fuel
mod and deliberately is not one — auto-feeding deletes the mid-game logistics problem rather
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
- Covers **every `Smelter`-based station** — smelter, charcoal kiln, blast furnace, windmill,
  spinning wheel, eitr refinery — because they are all the same component, so modded ones are
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
