using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;

namespace Kynda
{
    /// <summary>
    /// Lends each material group a real material off a vanilla prefab.
    ///
    /// Nothing here paints anything. The meshes are ours and the surfaces are the game's,
    /// which is what keeps a hand-built model looking like it belongs - texel density,
    /// palette and weathering all come along because they are the game's own. It also
    /// sidesteps swapping _MainTex on a borrowed material, which keeps the donor's normal
    /// map and leaves the surface lit for a shape it no longer has.
    ///
    /// Brought back from Vaettir, which got it from Stow, which got it from here. What
    /// Kynda kept was the borrowing; what it lost along the way was the atlas measuring
    /// below - so its pieces have been sampling whole texture sheets rather than the one
    /// tile they were supposed to.
    /// </summary>
    internal static class Skins
    {
        /// <summary>
        /// Prefabs to lift each group's material from, best first, ordered by measurement
        /// rather than by guess.
        ///
        /// ore and coal earn their place from the trough, whose two bays are the entire
        /// point of it - one heaped with ore, one with coal. Falling back to wood, which
        /// is what an unlisted group used to do, made them two identical tubs of nothing.
        /// Ripping the build set showed
        /// vanilla splits into two texel-density families: structural blocks - beam, pole,
        /// door, floor - run 165 to 224 texels/m and use nearly their whole sheet, while
        /// props, piles and furniture run 24 to 54 off a tight rect. These pieces are
        /// props, so the second family is the one to borrow from.
        ///
        /// wood_wall used to lead this list and does not exist. A name that does not
        /// resolve is skipped in silence, so the wood group had been quietly falling
        /// through to wood_beam - a structural block whose material covers 96% of its
        /// sheet, and the single worst donor available at 119 texels/m against a target
        /// of about 30.
        /// </summary>
        private static readonly Dictionary<string, string[]> Donors =
            new Dictionary<string, string[]>(StringComparer.OrdinalIgnoreCase)
            {
                // 29 texels/m, one material, 468 triangles. wood_wall_log second because
                // it is round bark-on timber at 54 - the right surface for split billets
                // when the piece is mostly logs.
                { "wood",  new[] { "piece_chest_wood", "wood_wall_log", "darkwood_beam" } },

                // The structure a pile sits IN, as opposed to the pile. Split out because
                // one group meant the rack's posts and lean-to wore woodpile texture - a
                // stack of split billets painted across a squared post, which reads as a
                // frame made of firewood. Vanilla does this the same way: a prop is one
                // material, but furniture is two, and a rack is furniture holding a prop.
                { "frame", new[] { "wood_beam", "wood_wall_log", "wood_pole" } },
                { "iron",  new[] { "piece_artisanstation", "forge", "piece_cauldron" } },
                { "stone", new[] { "stone_wall_2x1", "piece_stonecutter", "smelter" } },
                { "coal",  new[] { "coal_pile", "Coal", "charcoal_kiln" } },
                { "ore",   new[] { "CopperOre", "TinOre", "IronOre" } },
            };

        private static readonly Dictionary<string, Material> Cache =
            new Dictionary<string, Material>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// Where in its texture each borrowed material actually lives.
        ///
        /// Valheim's piece textures are atlases: a material does not use the whole image,
        /// it uses a strip of one. UVs running 0..1 therefore sample the entire sheet and
        /// pick up whatever the neighbouring tiles happen to be.
        /// </summary>
        private static readonly Dictionary<string, Rect> Atlas =
            new Dictionary<string, Rect>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// The donor texture's width in pixels, which is half of what decides how coarse
        /// our surface ends up. Vanilla's are tiny - 64 and 128 mostly, 256 at the largest
        /// - so the same slice of sheet means very different things on different donors.
        /// </summary>
        private static readonly Dictionary<string, int> TexPx =
            new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// Dropped on both ObjectDB.Awake and CopyOtherDB - a local world arrives through
        /// the first, a server handing over its item list through the second. Held across
        /// either, these are references to prefabs that have been torn down.
        /// </summary>
        public static void Invalidate()
        {
            Cache.Clear();
            Atlas.Clear();
            TexPx.Clear();
            PropIndex.Forget();
        }

        /// <summary>
        /// The suffix a model puts on a group to mean "the flat sawn end of this, not the
        /// length of it".
        ///
        /// Vanilla never models end grain, it paints it: every timber donor keeps two or
        /// three hand-drawn log-end discs in a corner of its sheet, away from the side
        /// grain, and UVs its cap faces onto one. Ours had no way to ask for that - a
        /// group got one rectangle and every face went into it - so our sawn ends were
        /// sampling bark, and a stack of logs read as extruded tube however carefully it
        /// was modelled. This is the group that gets aimed at the disc instead.
        /// </summary>
        private const string EndSuffix = "_end";

        /// <summary>
        /// The pseudo-group a piece uses to say "this donor covers all of me".
        ///
        /// Not a real group name, and deliberately one no model could produce - a material
        /// called * would have to come out of Blender, and it cannot.
        /// </summary>
        public const string Everything = "*";

        /// <summary>
        /// Groups a whole-piece donor does not cover.
        ///
        /// These are not what the piece is made of, they are what is sitting in it, and
        /// vanilla treats them the same way: a smelter is one material, smeltermat, and
        /// then its ore heap is a separate renderer wearing a separate material called
        /// blackhole. The charcoal kiln does the same. So a heap of copper keeping its own
        /// surface is not the mistake that four palettes on one cask was - it is the one
        /// place vanilla itself reaches for a second material.
        /// </summary>
        private static readonly HashSet<string> Contents =
            new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "ore", "coal" };

        /// <summary>
        /// The donor this group should come off: the one named for the group, else the
        /// one named for the whole piece, else nothing and the general list is used.
        /// </summary>
        private static string Named(string group, IDictionary<string, string> overrides)
        {
            if (overrides == null) return null;

            string donor;

            // The exact group before its family, or an end group can never have its own
            // entry: Base("wood_end") is "wood", so wood_end= pairs were parsed into the
            // map and then never read. With a prefab donor that never mattered - the cap
            // rect is measured off the renderer - but an @material donor has no renderer,
            // so the caps' rect has to arrive as its own pair or not at all.
            if (overrides.TryGetValue(group, out donor) && !string.IsNullOrEmpty(donor))
                return donor;

            var family = Base(group);

            if (overrides.TryGetValue(family, out donor) && !string.IsNullOrEmpty(donor))
                return donor;

            if (Contents.Contains(family)) return null;

            return overrides.TryGetValue(Everything, out donor) && !string.IsNullOrEmpty(donor)
                ? donor
                : null;
        }

        private static bool IsEnd(string group)
        {
            return group != null && group.Length > EndSuffix.Length
                   && group.EndsWith(EndSuffix, StringComparison.OrdinalIgnoreCase);
        }

        /// <summary>
        /// The material group an end group belongs to. A sawn end is the same timber as
        /// the log, off the same donor and the same material - only the corner of the
        /// sheet differs, so everything except the rectangle is looked up under this.
        /// </summary>
        private static string Base(string group)
        {
            return IsEnd(group) ? group.Substring(0, group.Length - EndSuffix.Length) : group;
        }

        /// <summary>
        /// The cache key. A group on its own is not enough once two pieces can ask for
        /// different donors for the same group - the woodrack wants round bark off
        /// wood_wall_log and the trough wants sawn planking off piece_chest_wood, and
        /// keying on "wood" alone would hand whichever asked second the other's material,
        /// its atlas rect and its texture size.
        ///
        /// The end suffix stays in the key. Same material, same donor, different
        /// rectangle - so they cannot share an entry.
        /// </summary>
        private static string Key(string group, IDictionary<string, string> overrides)
        {
            var donor = Named(group, overrides);
            return string.IsNullOrEmpty(donor) ? group : group + "|" + donor;
        }

        /// <summary>
        /// A loaded material by name, for the @material donor form.
        ///
        /// Resources.FindObjectsOfTypeAll because the material belongs to something that
        /// may not be in any scene - a location prefab held in memory rather than placed.
        /// Exact name first, then a case-insensitive match, because Unity appends nothing
        /// to a material the way it does "(Clone)" to an instantiated object but the
        /// capitalisation in an asset name is not something to rely on.
        /// </summary>
        private static Material FindMaterial(string name)
        {
            if (string.IsNullOrEmpty(name)) return null;

            Material loose = null;

            foreach (var candidate in Resources.FindObjectsOfTypeAll<Material>())
            {
                if (candidate == null || candidate.shader == null) continue;
                if (candidate.name == name) return candidate;

                if (loose != null) continue;

                if (string.Equals(candidate.name, name, StringComparison.OrdinalIgnoreCase))
                {
                    loose = candidate;
                    continue;
                }

                // Prefix, because Unity hands back "name (Instance)" for a material that
                // has been instanced, and a rip reports the asset name without it. That
                // difference is invisible in a report and fatal to an exact match, which
                // is why fi_village_containers resolved and fi_village_wood did not.
                if (candidate.name.StartsWith(name, StringComparison.OrdinalIgnoreCase))
                    loose = candidate;
            }

            if (loose == null)
            {
                var near = new List<string>();
                foreach (var candidate in Resources.FindObjectsOfTypeAll<Material>())
                {
                    if (candidate == null || candidate.name == null) continue;
                    if (candidate.name.IndexOf(name.Split('_')[0],
                                               StringComparison.OrdinalIgnoreCase) < 0) continue;
                    if (!near.Contains(candidate.name)) near.Add(candidate.name);
                    if (near.Count >= 12) break;
                }

                KyndaPlugin.Log.LogWarning("No loaded material called '" + name + "'. It only "
                    + "exists once something using it has loaded. Loaded names sharing its "
                    + "prefix: " + (near.Count == 0 ? "none" : string.Join(", ", near.ToArray())));

                // And do something about it: the camp donors live in location assets
                // that Valheim soft-ref streams - nothing loads them until somebody
                // WALKS to a vendor camp, which on a fresh server world is never. On
                // live that was a magenta Tun and a broken icon for every player. So
                // a missing material summons its carrier location through the softref
                // loader; the LateSkin watch applies the donor when the load lands.
                SummonDonorCarriers();
            }

            return loose;
        }

        private static float _nextSummon;

        private static void SummonDonorCarriers()
        {
            try
            {
                SummonDonorCarriersInner();
            }
            catch (Exception e)
            {
                // The LateSkin tick swallows exceptions, which made the first version
                // of this look simply absent: warnings fired, summoner never spoke.
                // Whatever throws in here, it says so exactly once.
                if (_summonFault == null)
                {
                    _summonFault = e.ToString();
                    KyndaPlugin.Log.LogError("Carrier summon failed: " + _summonFault);
                }
            }
        }

        private static string _summonFault;

        private static void SummonDonorCarriersInner()
        {
            if (UnityEngine.Time.time < _nextSummon) return;

            // The gate arms only after a REAL attempt: the first misses fire during
            // registration, before ZoneSystem exists, and arming on those burned the
            // whole window doing nothing - the summon then looked dead for 30s.
            var zone = ZoneSystem.instance;
            if (zone == null || zone.m_locations == null) return;
            _nextSummon = UnityEngine.Time.time + 30f;

            var hints = (KyndaConfig.DonorCarrierLocations.Value ?? "")
                .Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries);
            if (hints.Length == 0) return;

            var scanned = 0;
            var matched = 0;
            foreach (var location in zone.m_locations)
            {
                if (location == null) continue;
                scanned++;

                // m_prefabName, the plain string - NOT m_prefab.Name. A location can
                // carry an EMPTY soft-reference (an all-zero AssetID), and even the
                // Name getter walks the loader's dictionary and throws on it. That
                // exception, swallowed by the caller's tick, made the first summoner
                // look simply absent.
                var prefabName = location.m_prefabName;
                if (string.IsNullOrEmpty(prefabName)) continue;

                foreach (var hint in hints)
                {
                    if (prefabName.IndexOf(hint.Trim(),
                            StringComparison.OrdinalIgnoreCase) < 0) continue;

                    matched++;
                    try
                    {
                        if (location.m_prefab.IsValid && !location.m_prefab.IsLoaded
                            && !location.m_prefab.IsLoading)
                        {
                            location.m_prefab.LoadAsync();
                            KyndaPlugin.Log.LogInfo("Summoned location asset '"
                                + prefabName + "' for its donor materials.");
                        }
                    }
                    catch (Exception)
                    {
                        // An unresolvable reference on one location must not stop
                        // the sweep from reaching the one that resolves.
                    }
                    break;
                }
            }
            KyndaPlugin.Log.LogInfo("Carrier summon pass: " + scanned + " locations, "
                + matched + " matched.");
        }

        /// <summary>
        /// One model whose skin could not fully resolve at build time, waiting for the
        /// material to stream in.
        /// </summary>
        private sealed class LateSkin
        {
            public MeshRenderer Renderer;
            public Mesh Mesh;
            public Vector2[] OriginalUv;
            public string[] Groups;
            public IDictionary<string, string> Overrides;
        }

        /// <summary>Groups whose rect is sampled upside-down. See the ~ marker.</summary>
        private static readonly HashSet<string> FlipV =
            new HashSet<string>(StringComparer.Ordinal);

        private static readonly List<LateSkin> _late = new List<LateSkin>();
        private static float _nextLate;

        /// <summary>
        /// Skin a renderer now, and finish the job later if an @material is not loaded yet.
        ///
        /// An @donor names a material rather than a prefab, and a material only exists in
        /// memory once something wearing it has streamed in - but prefabs are built and
        /// skinned the moment ZNetScene exists, which is before any zone loads. So asking
        /// once at build time is asking at the one moment the answer is guaranteed to be
        /// no, however carefully the player positions themselves. This watches instead.
        ///
        /// The original UVs are snapshotted because Remap is not idempotent: it places UVs
        /// relative to what they are, so a late pass has to restore the mesh first and
        /// remap everything from scratch, or the groups that resolved on time get placed
        /// twice.
        /// </summary>
        public static Material[] SkinAndWatch(MeshRenderer renderer, Mesh mesh,
            string[] groups, IDictionary<string, string> overrides)
        {
            var skins = Skin(groups, overrides);

            for (var i = 0; i < groups.Length; i++)
            {
                if (skins[i] != null || !Key(groups[i], overrides).Contains("@")) continue;

                _late.Add(new LateSkin
                {
                    Renderer = renderer,
                    Mesh = mesh,
                    OriginalUv = mesh != null ? mesh.uv : null,
                    Groups = groups,
                    Overrides = overrides,
                });

                KyndaPlugin.Log.LogInfo("A skin donor is not loaded yet - it will be "
                    + "applied when its location streams in.");
                break;
            }

            return skins;
        }

        /// <summary>
        /// Retry the late skins. Call from the plugin's Update.
        ///
        /// Throttled hard, because the lookup behind a miss walks every loaded material.
        /// Five seconds is far below how often the answer can change - a location streams
        /// in over seconds - and the list is empty in any session that never uses an
        /// @donor, which is a count check and nothing else.
        /// </summary>
        public static void Tick()
        {
            if (_late.Count == 0) return;
            if (Time.realtimeSinceStartup < _nextLate) return;
            _nextLate = Time.realtimeSinceStartup + 5f;

            for (var i = _late.Count - 1; i >= 0; i--)
            {
                var entry = _late[i];

                // The world that wanted it is gone; a new world builds new prefabs and
                // registers its own watch.
                if (entry.Renderer == null || entry.Mesh == null) { _late.RemoveAt(i); continue; }

                var skins = Skin(entry.Groups, entry.Overrides);

                var missing = false;
                for (var j = 0; j < entry.Groups.Length; j++)
                    if (skins[j] == null && Key(entry.Groups[j], entry.Overrides).Contains("@"))
                        missing = true;
                if (missing) continue;

                // Restore, then remap from scratch - see the class comment.
                if (entry.OriginalUv != null) entry.Mesh.uv = entry.OriginalUv;
                entry.Renderer.sharedMaterials = skins;
                Remap(entry.Mesh, entry.Groups, entry.Overrides);

                // Pieces already standing share the Mesh asset, so their UVs just moved
                // with the remap - leaving their old materials on would scramble them.
                // Every scene renderer drawing this mesh gets the new set. FindObjectsOfType
                // is scene-only and this runs once, on the frame the donor finally loads.
                foreach (var live in UnityEngine.Object.FindObjectsOfType<MeshRenderer>())
                {
                    if (live == null || live == entry.Renderer) continue;
                    var filter = live.GetComponent<MeshFilter>();
                    if (filter == null || filter.sharedMesh != entry.Mesh) continue;
                    live.sharedMaterials = skins;
                }

                _late.RemoveAt(i);
                KyndaPlugin.Log.LogInfo("A late skin donor arrived and was applied, "
                    + "standing pieces included.");
            }
        }

        public static Material[] Skin(string[] groups, IDictionary<string, string> overrides)
        {
            var skins = new Material[groups.Length];
            for (var i = 0; i < groups.Length; i++) skins[i] = For(groups[i], overrides);
            return skins;
        }

        public static Material For(string group, IDictionary<string, string> overrides)
        {
            var key = Key(group, overrides);

            Material cached;
            if (Cache.TryGetValue(key, out cached)) return cached;

            var family = Base(group);
            var only = Named(group, overrides);

            string[] donors;
            if (!string.IsNullOrEmpty(only))
            {
                // Named explicitly, so it is the only candidate. Falling back to the
                // general list would silently hand back the material this piece asked
                // not to have, and the log would say it had been honoured.
                donors = new[] { only };
            }
            else if (!Donors.TryGetValue(family, out donors))
            {
                donors = Donors["wood"];
            }

            foreach (var name in donors)
            {
                var wanted = name.Trim();

                // A donor written @material names a MATERIAL rather than a prefab, and it
                // exists because the best surfaces in the game are unreachable any other
                // way. Haldor's camp dresses every barrel, keg and crate in
                // fi_village_wood - measured, fifteen containers ripped, fourteen of them
                // one material - but those props are children inside a location prefab,
                // so ZNetScene has never heard of them and PropIndex only walks roots.
                // The prefab lookup cannot get there; the material is loaded all the same.
                //
                // Caveat, and it is real: a material only exists in memory once something
                // using it has loaded. Ask for one before its location has ever streamed
                // in and it is not found, which is a warning and a fallback rather than a
                // failure.
                if (wanted.StartsWith("@"))
                {
                    // An @donor may carry a measured rect: @name:x/y/w/h, slashes because
                    // the donor list splits on commas. With no renderer to measure, the
                    // rect has to come from somewhere, and "the whole sheet" was tried
                    // and answered: fi_village_wood is an atlas, so the caps showed the
                    // entire catalogue - barrels, crates and the painted fruit at once.
                    // The rect vanilla itself uses is in any ripped prop wearing the
                    // sheet; the barrel's is measured in the config comment beside it.
                    var spec = wanted.Substring(1);
                    var rect = new Rect(0f, 0f, 1f, 1f);

                    // @name:keep - take the material and touch nothing else. For a mesh
                    // carrying vanilla's own UVs (the camp-barrel Tun is a rip, and its
                    // UVs are the ones this sheet was painted for) any remap is strictly
                    // worse than none, so no Atlas entry is stored and Remap skips the
                    // group entirely.
                    if (spec.EndsWith(":keep", StringComparison.OrdinalIgnoreCase))
                    {
                        var keepName = spec.Substring(0, spec.Length - 5);
                        var kept = FindMaterial(keepName);
                        if (kept == null) continue;

                        var keptTex = kept.GetTexture("_MainTex");
                        if (keptTex == null) continue;

                        Cache[key] = kept;
                        Atlas.Remove(key);
                        FlipV.Remove(key);
                        TexPx[key] = Mathf.Max(1, keptTex.width);

                        KyndaPlugin.Log.LogInfo("'" + key + "' skinned with the material "
                            + kept.name + " found by name, vanilla UVs kept, "
                            + keptTex.width + "px.");
                        return kept;
                    }

                    var colon = spec.IndexOf(':');
                    var flip = false;
                    if (colon > 0)
                    {
                        var parts = spec.Substring(colon + 1).Split('/');

                        // A ~ before the height flips V inside the rect. The stave strip
                        // is painted one way up and a cylinder unwrap runs whichever way
                        // the model was built - fi_village_wood's hoop band landed on the
                        // TOP of the casks, which is this exact mismatch and nothing else.
                        if (parts.Length == 4 && parts[3].StartsWith("~"))
                        {
                            flip = true;
                            parts[3] = parts[3].Substring(1);
                        }

                        float x, y, w, h;
                        if (parts.Length == 4
                            && float.TryParse(parts[0], NumberStyles.Float, CultureInfo.InvariantCulture, out x)
                            && float.TryParse(parts[1], NumberStyles.Float, CultureInfo.InvariantCulture, out y)
                            && float.TryParse(parts[2], NumberStyles.Float, CultureInfo.InvariantCulture, out w)
                            && float.TryParse(parts[3], NumberStyles.Float, CultureInfo.InvariantCulture, out h)
                            && w > 0f && h > 0f)
                        {
                            rect = new Rect(x, y, w, h);
                        }
                        else
                        {
                            KyndaPlugin.Log.LogWarning("Could not read the rect in '"
                                + wanted + "' - expected @name:x/y/w/h. Using the whole "
                                + "sheet, which will look like every tile at once.");
                        }
                        spec = spec.Substring(0, colon);
                    }

                    var byName = FindMaterial(spec);
                    if (byName == null) continue;

                    var tex = byName.GetTexture("_MainTex");
                    if (tex == null) continue;

                    Cache[key] = byName;
                    Atlas[key] = rect;
                    TexPx[key] = Mathf.Max(1, tex.width);
                    if (flip) FlipV.Add(key); else FlipV.Remove(key);

                    KyndaPlugin.Log.LogInfo("'" + key + "' skinned with the material "
                        + byName.name + " found by name (shader " + byName.shader.name
                        + "), rect " + rect + (flip ? ", V flipped" : "") + ", "
                        + tex.width + "px.");
                    return byName;
                }

                // Via PropIndex rather than ZNetScene directly: many dressing prefabs
                // carry no ZNetView and so are invisible to ZNetScene however loaded.
                var donor = PropIndex.Find(wanted);
                if (donor == null) continue;

                var renderer = MainRenderer(donor);
                if (renderer != null)
                {
                    var material = renderer.sharedMaterial;
                    var sheet = material.GetTexture("_MainTex");

                    Rect side, cap;
                    Regions(renderer, out side, out cap);

                    Rect patch;
                    if (IsEnd(group)) patch = cap;
                    else if (IsMetal(family)) patch = MetalRegion(sheet, name, side);
                    else patch = side;

                    Cache[key] = material;
                    Atlas[key] = patch;
                    TexPx[key] = Mathf.Max(1, sheet.width);

                    // The renderer is named because which one was measured is the thing
                    // that went wrong last time and the thing a wrong rect points at.
                    KyndaPlugin.Log.LogInfo(string.Format(
                        "'{0}' skinned with {1} from {2}/{3} (shader {4}), atlas {5}, {6}px.",
                        key, material.name, name, renderer.name, material.shader.name,
                        Atlas[key], TexPx[key]));
                    DumpShader(material);
                    return material;
                }
            }

            KyndaPlugin.Log.LogWarning("No material found for group '" + key + "'.");

            // A missing @material is NOT cached as a failure. Those name a material that
            // only exists once something using it has streamed in, so "not found" means
            // "not yet" rather than "never" - and caching the null meant the answer was
            // fixed at world load, before the location it lives in had ever been near.
            // Prefab donors are cached as before: a prefab that ZNetScene does not have at
            // load is not going to appear later, and re-searching every frame for one is
            // the cost this cache exists to avoid.
            if (!key.Contains("@")) Cache[key] = null;

            return null;
        }

        private static readonly HashSet<string> _dumped =
            new HashSet<string>(StringComparer.Ordinal);

        /// <summary>
        /// Every property on a borrowed material's shader, with its type and whether it is
        /// currently set.
        ///
        /// The names are not guessable and getting one wrong is silent - a texture written
        /// to a property the shader does not have simply does nothing, which looks exactly
        /// like the texture failing to load. _BumpMap is the Standard shader's name, and
        /// Valheim's pieces are on Custom/Piece, so the normal slot here is called something
        /// else. This is what any attempt to supply our own maps has to be written against.
        ///
        /// Once per shader rather than once per material: the property list belongs to the
        /// shader, and a piece borrowing four materials off Custom/Piece would print it four
        /// times for nothing.
        /// </summary>
        private static void DumpShader(Material material)
        {
            if (!KyndaConfig.DumpShader.Value) return;
            if (material == null || material.shader == null) return;
            if (!_dumped.Add(material.shader.name)) return;

            var shader = material.shader;
            var count = shader.GetPropertyCount();
            KyndaPlugin.Log.LogInfo(
                "SHADER " + shader.name + ": " + count + " properties.");

            for (var i = 0; i < count; i++)
            {
                var name = shader.GetPropertyName(i);
                var type = shader.GetPropertyType(i);

                var set = "";
                if (type == UnityEngine.Rendering.ShaderPropertyType.Texture)
                {
                    var tex = material.GetTexture(name);
                    set = tex == null
                        ? "  (unset)"
                        : "  = " + tex.name + " " + tex.width + "x" + tex.height;
                }
                else if (type == UnityEngine.Rendering.ShaderPropertyType.Color)
                {
                    set = "  = " + material.GetColor(name);
                }
                else if (type == UnityEngine.Rendering.ShaderPropertyType.Float
                         || type == UnityEngine.Rendering.ShaderPropertyType.Range)
                {
                    set = "  = " + material.GetFloat(name);
                }

                KyndaPlugin.Log.LogInfo("    " + name + " (" + type + ")" + set);
            }
        }

        /// <summary>
        /// The submesh's vertices split into connected parts - one per log, plank or hoop.
        ///
        /// Connectivity is through shared vertex indices, which is exactly right for our
        /// models: every part is built and unwrapped as its own object and only joined at
        /// the end, so no two parts ever share a vertex. The seams a UV projection creates
        /// split a part further, and that is fine - the pieces of one log all want the same
        /// treatment anyway, and they get it because they are the same size.
        /// </summary>
        private static List<List<int>> Islands(int[] indices, Vector2[] uv)
        {
            // Union-find over the vertices this submesh touches. Flat arrays over a
            // dictionary because this runs once per group at registration and the vertex
            // count is in the thousands.
            var parent = new Dictionary<int, int>();

            for (var i = 0; i < indices.Length; i++)
            {
                var v = indices[i];
                if (v >= 0 && v < uv.Length && !parent.ContainsKey(v)) parent[v] = v;
            }

            for (var i = 0; i + 2 < indices.Length; i += 3)
            {
                var a = indices[i];
                var b = indices[i + 1];
                var c = indices[i + 2];
                if (!parent.ContainsKey(a) || !parent.ContainsKey(b) || !parent.ContainsKey(c))
                    continue;

                Join(parent, a, b);
                Join(parent, a, c);
            }

            // Snapshot the keys. Find compresses paths as it goes, and .NET Framework's
            // Dictionary bumps its version even when a value is overwritten rather than
            // added - so walking parent.Keys directly throws part way through.
            var keys = new List<int>(parent.Keys);

            var groups = new Dictionary<int, List<int>>();
            foreach (var v in keys)
            {
                var root = Find(parent, v);

                List<int> island;
                if (!groups.TryGetValue(root, out island))
                {
                    island = new List<int>();
                    groups[root] = island;
                }
                island.Add(v);
            }

            return new List<List<int>>(groups.Values);
        }

        private static int Find(Dictionary<int, int> parent, int v)
        {
            while (parent[v] != v)
            {
                parent[v] = parent[parent[v]];
                v = parent[v];
            }
            return v;
        }

        private static void Join(Dictionary<int, int> parent, int a, int b)
        {
            var ra = Find(parent, a);
            var rb = Find(parent, b);
            if (ra != rb) parent[ra] = rb;
        }

        /// <summary>
        /// The bounding rectangle of the largest group of triangles whose own rectangles
        /// touch each other - which is the shape of one painted feature on the sheet.
        ///
        /// Merging by overlap is what separates a field from a detail. A painted area is
        /// covered by many triangles that necessarily abut, so they collapse into one
        /// rectangle the size of the area; something painted off on its own - a log-end
        /// disc, a knot, a strip of banding - has nothing adjoining it and stays separate.
        /// No threshold to tune and no assumption about where a donor keeps things.
        ///
        /// Repeated until nothing more merges, because merging is transitive: three strips
        /// side by side only become one field if the pass that joins the first two then
        /// gets a chance to see the third.
        /// </summary>
        private static Rect Cluster(List<Rect> rects)
        {
            var none = new Rect(0f, 0f, 0f, 0f);
            if (rects == null || rects.Count == 0) return none;

            var merged = new List<Rect>(rects);

            // Touching, not merely overlapping. Two strips of one painted field share an
            // edge exactly, and floating point means "exactly" is not something to wait
            // for - a hair under half a texel on the smallest sheet vanilla ships.
            const float touch = 1f / 128f;

            bool changed;
            var guard = 0;
            do
            {
                changed = false;
                guard++;

                for (var i = 0; i < merged.Count && !changed; i++)
                {
                    for (var j = i + 1; j < merged.Count; j++)
                    {
                        var a = merged[i];
                        var b = merged[j];

                        if (a.xMin > b.xMax + touch || b.xMin > a.xMax + touch) continue;
                        if (a.yMin > b.yMax + touch || b.yMin > a.yMax + touch) continue;

                        var x0 = Mathf.Min(a.xMin, b.xMin);
                        var y0 = Mathf.Min(a.yMin, b.yMin);
                        merged[i] = new Rect(x0, y0,
                            Mathf.Max(a.xMax, b.xMax) - x0,
                            Mathf.Max(a.yMax, b.yMax) - y0);
                        merged.RemoveAt(j);
                        changed = true;
                        break;
                    }
                }
            }
            while (changed && guard < 4096);

            var best = none;
            foreach (var rect in merged)
            {
                if (rect.width * rect.height > best.width * best.height) best = rect;
            }

            return best;
        }

        /// <summary>
        /// The renderer that is actually the object: the one carrying the most readable
        /// geometry.
        ///
        /// This used to take the first renderer with an albedo, which is wrong on almost
        /// every vanilla prefab. They carry a Worn and a Broken copy of the visual, a
        /// scatter of destruction chunks, and sometimes a lower LOD - and which of those
        /// GetComponentsInChildren hands back first is an accident of the hierarchy. On
        /// wood_wall_log the winner had UVs covering a slice 0.151 wide where the wall's
        /// own bark field is 0.424, so the woodrack was fitted to a third of the texture
        /// it should have had and came out at 15 texels per metre.
        ///
        /// Readability is part of the test rather than a separate check. A chunk whose
        /// mesh was built with Read/Write off cannot be measured at all, and picking one
        /// silently falls back to treating the whole sheet as the material's - the worst
        /// answer available, and indistinguishable in the log from a good one.
        /// </summary>
        private static MeshRenderer MainRenderer(GameObject donor)
        {
            MeshRenderer best = null;
            var most = 0;

            foreach (var renderer in donor.GetComponentsInChildren<MeshRenderer>(true))
            {
                var material = renderer.sharedMaterial;
                if (material == null || material.shader == null) continue;

                // A material with no albedo renders flat and grey, which looks like a bug
                // rather than a choice.
                if (!material.HasProperty("_MainTex")
                    || material.GetTexture("_MainTex") == null) continue;

                var filter = renderer.GetComponent<MeshFilter>();
                var mesh = filter != null ? filter.sharedMesh : null;
                if (mesh == null) continue;

                int count;
                try
                {
                    if (!mesh.isReadable) continue;
                    count = mesh.triangles.Length;
                }
                catch { continue; }

                if (count <= most) continue;

                most = count;
                best = renderer;
            }

            return best;
        }

        private static bool IsMetal(string family)
        {
            return string.Equals(family, "iron", StringComparison.OrdinalIgnoreCase);
        }

        /// <summary>
        /// Where the grey is on a donor's sheet.
        ///
        /// Vanilla puts a piece's metal on the same texture as its wood rather than on a
        /// second material. piece_chest_barrel is the clearest case: 64 pixels split down
        /// the middle, brown timber on the left and grey steel on the right, and its
        /// modelled hoops are UV'd onto the right half. One material, two substances.
        ///
        /// So the metal is found the way a person would find it - by looking for the part
        /// of the picture with no colour in it. Saturation separates the two cleanly and
        /// nothing else does: brightness does not, because weathered timber and dark iron
        /// overlap, and position does not, because no two sheets agree on a layout.
        ///
        /// Read through a RenderTexture, which is what makes this possible at all. Valheim
        /// ships its textures compressed and non-readable, so GetPixels throws on almost
        /// all of them, but anything can be blitted to a render target and read back from
        /// there. Same route the devkit's ripper takes, and the reason it never fails on a
        /// texture the way it does on a mesh.
        /// </summary>
        private static Rect MetalRegion(Texture sheet, string donor, Rect fallback)
        {
            if (sheet == null) return fallback;

            // 64 is plenty. Vanilla's sheets are 64 to 256 and this is looking for a
            // half-of-the-image sized block, not for detail.
            var w = Mathf.Clamp(sheet.width, 8, 64);
            var h = Mathf.Clamp(sheet.height, 8, 64);

            Color[] pixels;
            RenderTexture rt = null;
            var previous = RenderTexture.active;
            Texture2D readable = null;

            try
            {
                rt = RenderTexture.GetTemporary(w, h, 0, RenderTextureFormat.ARGB32,
                                                RenderTextureReadWrite.sRGB);
                Graphics.Blit(sheet, rt);
                RenderTexture.active = rt;

                readable = new Texture2D(w, h, TextureFormat.ARGB32, false);
                readable.ReadPixels(new Rect(0f, 0f, w, h), 0, 0);
                readable.Apply();
                pixels = readable.GetPixels();
            }
            catch (Exception e)
            {
                KyndaPlugin.Log.LogWarning(
                    "Could not read " + donor + "'s sheet to find its metal: " + e.Message);
                return fallback;
            }
            finally
            {
                RenderTexture.active = previous;
                if (rt != null) RenderTexture.ReleaseTemporary(rt);
                if (readable != null) UnityEngine.Object.Destroy(readable);
            }

            if (pixels == null || pixels.Length < w * h) return fallback;

            // Columns first, then rows inside the winning columns. Averaging rows across
            // the whole sheet would mix the brown half back in and flatten the signal -
            // on a left/right split every row looks equally middling.
            var columns = new float[w];
            var overall = 0f;
            for (var x = 0; x < w; x++)
            {
                var sum = 0f;
                for (var y = 0; y < h; y++) sum += Saturation(pixels[y * w + x]);
                columns[x] = sum / h;
                overall += columns[x];
            }
            overall /= w;

            int x0, x1;
            if (!Run(columns, overall, out x0, out x1)) return Grey(donor, fallback);

            var rows = new float[h];
            for (var y = 0; y < h; y++)
            {
                var sum = 0f;
                for (var x = x0; x <= x1; x++) sum += Saturation(pixels[y * w + x]);
                rows[y] = sum / (x1 - x0 + 1);
            }

            int y0, y1;
            if (!Run(rows, overall, out y0, out y1)) { y0 = 0; y1 = h - 1; }

            // Pulled in by a pixel on every side. A rect flush against the boundary
            // samples the neighbouring half wherever the GPU filters across the seam,
            // which on a 64 pixel sheet is a visible brown fringe along every hoop.
            var rect = new Rect((x0 + 1f) / w, (y0 + 1f) / h,
                                Mathf.Max(1f, x1 - x0 - 1f) / w,
                                Mathf.Max(1f, y1 - y0 - 1f) / h);

            KyndaPlugin.Log.LogInfo(string.Format(
                "{0}'s metal is the {1}x{2} px block at {3:0.000},{4:0.000} - saturation "
                + "{5:0.00} against {6:0.00} across the sheet.",
                donor, x1 - x0 + 1, y1 - y0 + 1, rect.x, rect.y,
                Mean(columns, x0, x1), overall));

            return rect;
        }

        /// <summary>
        /// The longest unbroken run of slices carrying markedly less colour than the sheet
        /// as a whole, or false when there is no such thing.
        ///
        /// Two tests, and both are needed. Half the mean catches the split on a sheet that
        /// really is part metal; the absolute ceiling stops a donor with no metal at all
        /// from confidently handing back whichever quarter of its timber happens to be
        /// least saturated. A sheet of nothing but wood has to be able to say no.
        /// </summary>
        private static bool Run(float[] slices, float overall, out int from, out int to)
        {
            from = 0;
            to = -1;

            var ceiling = Mathf.Min(overall * 0.5f, 0.18f);

            var bestFrom = 0;
            var bestTo = -1;
            var runFrom = -1;

            for (var i = 0; i < slices.Length; i++)
            {
                if (slices[i] <= ceiling)
                {
                    if (runFrom < 0) runFrom = i;
                    if (i - runFrom > bestTo - bestFrom) { bestFrom = runFrom; bestTo = i; }
                }
                else runFrom = -1;
            }

            // Two slices is noise, not a region.
            if (bestTo - bestFrom < 2) return false;

            from = bestFrom;
            to = bestTo;
            return true;
        }

        private static float Saturation(Color c)
        {
            var max = Mathf.Max(c.r, Mathf.Max(c.g, c.b));
            var min = Mathf.Min(c.r, Mathf.Min(c.g, c.b));
            return max <= 0.0001f ? 0f : (max - min) / max;
        }

        private static float Mean(float[] slices, int from, int to)
        {
            var sum = 0f;
            for (var i = from; i <= to; i++) sum += slices[i];
            return sum / Mathf.Max(1, to - from + 1);
        }

        private static Rect Grey(string donor, Rect fallback)
        {
            KyndaPlugin.Log.LogInfo(
                donor + " has no unsaturated block - it is all one substance, so metal "
                + "parts will wear the same surface as the rest of it.");
            return fallback;
        }

        /// <summary>
        /// The two slices of texture a donor uses: the field its broad faces sit on, and
        /// the patch its end faces sit on.
        ///
        /// Neither is the whole mesh's extent and neither is one triangle. Both of those
        /// were tried and both are wrong in opposite directions.
        ///
        /// Min/max across every vertex gives a rectangle spanning every tile the donor
        /// touches - on stone_wall_2x1 that was 71% of the sheet - and squeezing our
        /// coordinates into that still walks across tile boundaries.
        ///
        /// The largest single triangle, which is what this did until the game showed
        /// otherwise, is far too small. wood_wall_log's bark is painted as a row of
        /// adjacent vertical strips, one per log in the wall, and the biggest triangle in
        /// it is a single strip 10 pixels wide. Everything in the group then had to fit
        /// inside those 10 pixels, which put the woodrack at 7 texels per metre against a
        /// target of 35 - each texel blown up to 14cm, so the roof planks read as a
        /// checkerboard of enormous squares. The barrels went the same way at 6.
        ///
        /// So: cluster the triangles by whether their rectangles touch, and take the
        /// biggest cluster. Adjacent strips of one painted field merge into that field;
        /// a disc in the corner of the sheet stays its own cluster because nothing
        /// touches it. That is the shape of a painted feature, which is what we actually
        /// want to aim at.
        ///
        /// The cap is found by area, not by name or by hardcoded rectangle. Triangles are
        /// bucketed by which axis their normal points along, and the axis carrying the
        /// least total surface is the ends: a log, a plank and a barrel are all long in
        /// two directions and short in the third, so the faces looking down the short one
        /// are the cut ones. Measured against the rips this picks the painted disc exactly
        /// on every timber donor there is - wood_wall_log 9% of its surface, wood_stack
        /// 9%, barrell 24% - and each time the winning rectangle lands on the corner of
        /// the sheet where the discs are drawn.
        ///
        /// The alternative was a table of rectangles per donor, which would have been just
        /// as accurate today and silently wrong the first time a donor was swapped in
        /// config for one nobody had measured.
        /// </summary>
        private static void Regions(Renderer renderer, out Rect side, out Rect cap)
        {
            var whole = new Rect(0f, 0f, 1f, 1f);
            side = whole;
            cap = whole;

            var filter = renderer != null ? renderer.GetComponent<MeshFilter>() : null;
            var mesh = filter != null ? filter.sharedMesh : null;
            if (mesh == null) return;

            Vector3[] verts;
            Vector2[] uv;
            int[] tris;
            try
            {
                // Imported meshes are frequently upload-only; reading them then throws.
                if (!mesh.isReadable) return;
                verts = mesh.vertices;
                uv = mesh.uv;
                tris = mesh.triangles;
            }
            catch { return; }

            if (uv == null || uv.Length == 0 || tris == null || tris.Length < 3) return;
            if (verts == null || verts.Length == 0) return;

            // Per dominant normal axis: how much surface it carries, and every triangle's
            // rect on it, kept for clustering rather than reduced to a single winner.
            var surface = new float[3];
            var rects = new[] { new List<Rect>(), new List<Rect>(), new List<Rect>() };

            for (var i = 0; i + 2 < tris.Length; i += 3)
            {
                var a = tris[i];
                var b = tris[i + 1];
                var c = tris[i + 2];
                if (a >= uv.Length || b >= uv.Length || c >= uv.Length) continue;
                if (a >= verts.Length || b >= verts.Length || c >= verts.Length) continue;

                // Geometric, not the shading normal. A smooth-shaded cylinder's stored
                // normals lean around the curve, but the face itself still points squarely
                // out of the side - and it is the face we are classifying.
                var cross = Vector3.Cross(verts[b] - verts[a], verts[c] - verts[a]);
                var length = cross.magnitude;
                if (length <= 1e-9f) continue;

                var n = cross / length;
                var axis = Mathf.Abs(n.x) >= Mathf.Abs(n.y) && Mathf.Abs(n.x) >= Mathf.Abs(n.z)
                    ? 0
                    : (Mathf.Abs(n.y) >= Mathf.Abs(n.z) ? 1 : 2);

                surface[axis] += length * 0.5f;

                var minX = Mathf.Min(uv[a].x, Mathf.Min(uv[b].x, uv[c].x));
                var maxX = Mathf.Max(uv[a].x, Mathf.Max(uv[b].x, uv[c].x));
                var minY = Mathf.Min(uv[a].y, Mathf.Min(uv[b].y, uv[c].y));
                var maxY = Mathf.Max(uv[a].y, Mathf.Max(uv[b].y, uv[c].y));

                var width = maxX - minX;
                var height = maxY - minY;

                // A face that itself tiles past the sheet edge tells us nothing useful.
                if (width <= 0.005f || height <= 0.005f) continue;
                if (width > 1f || height > 1f) continue;

                rects[axis].Add(new Rect(minX, minY, width, height));
            }

            var total = surface[0] + surface[1] + surface[2];
            if (total <= 0f) return;

            var least = 0;
            for (var i = 1; i < 3; i++)
            {
                if (surface[i] < surface[least]) least = i;
            }

            var fields = new[] { Cluster(rects[0]), Cluster(rects[1]), Cluster(rects[2]) };

            // The side field is the biggest cluster on any axis, not the biggest cluster
            // on whichever axis carries the most surface.
            //
            // Tying it to the surface leader was the wrong hook and cost two rounds. It
            // assumes the broad painted field belongs to the facing with the most area,
            // and on wood_wall_log it does not: measured off the rip, a bark field of
            // 0.424 sits on one axis while another holds 0.547 of the same sheet, and
            // which of them the runtime calls "most" turns on the mesh's local
            // orientation rather than on anything about the texture. The rack kept being
            // fitted into a 0.151 slice for that reason alone.
            //
            // Clustering every triangle regardless of facing was the other candidate and
            // is worse: right here, but it merges every painted region on barrell into
            // one rectangle covering 98% of its sheet.
            var field = fields[0];
            foreach (var candidate in fields)
            {
                if (candidate.width * candidate.height > field.width * field.height)
                    field = candidate;
            }
            if (field.width > 0f) side = field;

            // All three printed, because a wrong rect is otherwise impossible to tell
            // from a wrong axis, and that ambiguity is what made this take three passes.
            KyndaPlugin.Log.LogInfo(string.Format(
                "{0}: surface {1:0}/{2:0}/{3:0}% by axis, fields {4:0.000}x{5:0.000} / "
                + "{6:0.000}x{7:0.000} / {8:0.000}x{9:0.000}.",
                renderer.name,
                surface[0] / total * 100f, surface[1] / total * 100f, surface[2] / total * 100f,
                fields[0].width, fields[0].height,
                fields[1].width, fields[1].height,
                fields[2].width, fields[2].height));

            // A donor whose thinnest axis still carries a third of its surface is not a
            // timber - it is a box, and its "ends" are just more of the same wall. Aiming
            // sawn ends at a rectangle picked off a cube would be a confident guess at
            // nothing, so it falls back to the side field, which is at least the surface
            // the piece is made of.
            var share = surface[least] / total;
            var disc = fields[least];
            if (share <= 0.30f && disc.width > 0f && disc != side)
            {
                cap = disc;
            }
            else
            {
                cap = side;
                KyndaPlugin.Log.LogInfo(string.Format(
                    "{0} has no separate end patch - its thinnest axis is {1:0}% of its "
                    + "surface. Sawn ends will use the side grain.",
                    renderer.name, share * 100f));
            }
        }

        /// <summary>
        /// Places each submesh's UVs inside its material's slice of the atlas, at a texel
        /// density chosen rather than inherited.
        ///
        /// This used to stretch the group's UVs to fill the rect, which made density an
        /// accident of two things nobody picked: how big the donor's slice happened to be
        /// and how big our model happened to be. Measured in game that gave 119 texels per
        /// metre on wood, 70 on iron and 11 on stone - an eleven-fold spread inside one
        /// piece, against a vanilla range of 24 to 54.
        ///
        /// Our exported UVs are already in metres, because the Blender pass cube-projects
        /// at a cube size of 1. So the wanted scale is simply target-texels divided by the
        /// donor's texture width, and the only complication is that the result has to fit
        /// the rect.
        ///
        /// Clamped, never wrapped. Repeat() here was the bug Stow paid for: it wraps per
        /// vertex, so a face crossing 1.0 got vertices at 0.9 and 0.2 and the GPU
        /// interpolated backwards across the whole tile between them - smeared diagonal
        /// banding that made a square model look crooked. That is also why a group too
        /// large for its rect is scaled down to fit rather than tiled: coarser than asked
        /// for, but continuous.
        /// </summary>
        public static void Remap(Mesh mesh, string[] groups, IDictionary<string, string> overrides)
        {
            if (mesh == null || groups == null) return;

            var uv = mesh.uv;
            if (uv == null || uv.Length == 0) return;

            var count = Mathf.Min(groups.Length, mesh.subMeshCount);
            var target = Mathf.Max(1f, KyndaConfig.TexelsPerMetre.Value);

            // A vertex on the seam between two groups appears in both submeshes, and
            // mapping it twice would place it relative to an already-placed position.
            var done = new bool[uv.Length];

            for (var i = 0; i < count; i++)
            {
                var key = Key(groups[i], overrides);

                Rect rect;
                int px;
                if (!Atlas.TryGetValue(key, out rect)) continue;
                if (!TexPx.TryGetValue(key, out px) || px <= 0) continue;

                var indices = mesh.GetTriangles(i);
                if (indices.Length == 0) continue;

                // An end group is not density-fitted, because a sawn end is not a tiling
                // surface - it is one painted disc that has to land on one cut face,
                // whole and once. The model already gave every cap its own copy of the
                // unit square, so the whole job here is to put that square on the disc.
                //
                // Density does still come out right, incidentally: a 24cm log end drawn
                // across an 18x12 texel disc is 75 texels/m, coarse enough to sit in the
                // same family as everything around it.
                if (IsEnd(groups[i]))
                {
                    foreach (var index in indices)
                    {
                        if (index < 0 || index >= uv.Length || done[index]) continue;
                        done[index] = true;

                        var ty = Mathf.Clamp01(uv[index].y);
                        if (FlipV.Contains(key)) ty = 1f - ty;

                        uv[index] = new Vector2(
                            rect.x + Mathf.Clamp01(uv[index].x) * rect.width,
                            rect.y + ty * rect.height);
                    }

                    KyndaPlugin.Log.LogInfo(string.Format(
                        "'{0}' aimed at the end-grain patch at {1:0.000},{2:0.000} "
                        + "{3:0.000}x{4:0.000} ({5} texels across).",
                        key, rect.x, rect.y, rect.width, rect.height,
                        Mathf.RoundToInt(rect.width * px)));
                    continue;
                }

                // Per island, not per group - and that distinction is worth as much as the
                // rect being the right size.
                //
                // A group's extent is the bounding box of every part in it laid side by
                // side, which is nothing any single part needs. The trough's six hoops
                // measured 2.72m across as a group; one hoop is 1.9m round, and the other
                // 0.8m was just the next hoop sitting beside it in UV space. Fitting the
                // group meant fitting a surface that does not exist, and it cost the hoops
                // 7 texels per metre - one or two pixels of grey stretched round a barrel,
                // which is why they came out as thin white wires.
                //
                // Islands are free to overlap each other inside the rect. That is what
                // tiling means, and it is safe done this way: a part is placed whole, so no
                // face ever straddles the rect boundary. Wrapping per vertex is the thing
                // that cannot be done - Stow paid for that one, with faces whose corners
                // landed at 0.9 and 0.2 and a GPU interpolating backwards across the tile.
                var islands = Islands(indices, uv);

                var coarsest = float.MaxValue;
                var finest = 0f;

                foreach (var island in islands)
                {
                    var min = new Vector2(float.MaxValue, float.MaxValue);
                    var max = new Vector2(float.MinValue, float.MinValue);
                    foreach (var index in island)
                    {
                        min = Vector2.Min(min, uv[index]);
                        max = Vector2.Max(max, uv[index]);
                    }

                    var span = max - min;
                    if (span.x <= 0f || span.y <= 0f) continue;

                    // Wanted, then reduced until it fits. Uniform on both axes so the
                    // texture is not stretched in one direction, which reads as smeared
                    // grain.
                    var scale = target / px;
                    scale = Mathf.Min(scale, rect.width / span.x);
                    scale = Mathf.Min(scale, rect.height / span.y);

                    coarsest = Mathf.Min(coarsest, scale * px);
                    finest = Mathf.Max(finest, scale * px);

                    // Centred in the rect, so a part that does fit samples the middle of
                    // the patch rather than its edge, where the neighbour bleeds across.
                    var centre = (min + max) * 0.5f;
                    var offset = new Vector2(rect.x + rect.width * 0.5f,
                                             rect.y + rect.height * 0.5f) - centre * scale;

                    foreach (var index in island)
                    {
                        if (done[index]) continue;
                        done[index] = true;

                        uv[index] = new Vector2(
                            Mathf.Clamp(uv[index].x * scale + offset.x, rect.xMin, rect.xMax),
                            FlipV.Contains(key)
                                ? rect.yMax - (Mathf.Clamp(uv[index].y * scale + offset.y,
                                                           rect.yMin, rect.yMax) - rect.yMin)
                                : Mathf.Clamp(uv[index].y * scale + offset.y,
                                              rect.yMin, rect.yMax));
                    }
                }

                if (finest <= 0f) continue;

                KyndaPlugin.Log.LogInfo(string.Format(
                    "'{0}' laid out at {1:0}-{2:0} texels/m (wanted {3:0}) across {4} "
                    + "parts, in a {5:0.000}x{6:0.000} rect.",
                    key, coarsest, finest, target, islands.Count, rect.width, rect.height));
            }

            mesh.uv = uv;
        }
    }
}
