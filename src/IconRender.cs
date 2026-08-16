using System;
using UnityEngine;

namespace Stoker
{
    /// <summary>
    /// Photographs the finished prefab and uses that as its build-menu icon.
    ///
    /// The icons used to be rendered in Blender alongside the previews, and they gave the
    /// pieces away as modded more plainly than the models ever did. Vanilla's icons show
    /// the real object: charcoal_kiln's turf and stone, piece_chest_wood's grain and iron
    /// banding, lit warm and filling the frame. Ours were one flat tone of brown, because
    /// the Blender pass only knows the placeholder tints in the build script - a piece's
    /// actual surface is a vanilla material borrowed at runtime, and no offline render can
    /// have seen it.
    ///
    /// So the icon could never have matched the piece, however well it was lit. It is not
    /// a lighting problem, it is a "the thing does not exist yet" problem, and the fix is
    /// to take the picture at the point where it does.
    ///
    /// This is also the same principle the rest of the mod runs on. The model is ours, the
    /// surface is the game's, and anything derived from both has to be made where both are
    /// present.
    /// </summary>
    internal static class IconRender
    {
        /// <summary>
        /// Rendered at 4x and handed over at 4x. The menu slot is small and the sprite is
        /// always being minified, which is free anti-aliasing - where rendering at the
        /// final size gives stair-stepped edges against the transparent background, and
        /// those read as a sprite pasted in rather than an object photographed.
        /// </summary>
        private const int Size = 512;

        /// <summary>
        /// A layer nothing else draws on, so the icon camera sees the subject and only the
        /// subject. 31 is the last one Unity offers and vanilla leaves it alone; sharing a
        /// layer with the world would put whatever happens to be standing nearby in the
        /// picture.
        /// </summary>
        private const int Layer = 31;

        public static Sprite Shoot(GameObject prefab, string name)
        {
            GameObject subject = null;
            GameObject rig = null;
            RenderTexture target = null;
            var previous = RenderTexture.active;

            try
            {
                // A copy, not the prefab. Moving the prefab itself to a corner of the world
                // to photograph it would leave every instance placed afterwards carrying
                // that position and layer.
                //
                // Init stays suppressed for the same reason it does when the prefab is
                // built: a live ZNetView would try to register this throwaway with the
                // network the moment it woke up.
                var wasDisabled = ZNetView.m_forceDisableInit;
                ZNetView.m_forceDisableInit = true;
                try { subject = UnityEngine.Object.Instantiate(prefab); }
                finally { ZNetView.m_forceDisableInit = wasDisabled; }

                subject.name = name + "_icon_subject";

                // Far from anything, and well under the terrain's reach so no landscape
                // wanders into frame.
                subject.transform.position = new Vector3(0f, -8000f, 0f);
                subject.transform.rotation = Quaternion.identity;
                SetLayer(subject, Layer);

                var bounds = Framing(subject);
                if (bounds.size == Vector3.zero) return null;

                rig = new GameObject(name + "_icon_rig");
                rig.transform.position = bounds.center;

                // Three quarters on, and from a little above - the angle every vanilla
                // piece icon is shot from. Straight on hides the top and reads as a
                // cardboard cut-out; directly above stops being recognisable as the thing
                // you are about to place.
                rig.transform.rotation = Quaternion.Euler(22f, 32f, 0f);

                var camera = rig.AddComponent<Camera>();
                camera.orthographic = true;
                camera.clearFlags = CameraClearFlags.SolidColor;

                // Transparent black, not transparent white. A white background bleeds pale
                // fringes into every edge when the sprite is filtered down.
                camera.backgroundColor = new Color(0f, 0f, 0f, 0f);
                camera.cullingMask = 1 << Layer;
                camera.enabled = false;

                // The subject's longest diagonal from this angle, with a little air. The
                // diagonal rather than the height because the camera is turned - framing on
                // height alone clips the corners of anything wider than it is tall.
                var reach = bounds.extents.magnitude;
                camera.orthographicSize = reach * 1.06f;
                camera.nearClipPlane = 0.01f;
                camera.farClipPlane = reach * 8f;
                camera.transform.position = bounds.center - camera.transform.forward * reach * 4f;

                Light(rig.transform, reach);

                target = RenderTexture.GetTemporary(Size, Size, 24, RenderTextureFormat.ARGB32,
                                                    RenderTextureReadWrite.sRGB);
                camera.targetTexture = target;
                camera.Render();

                RenderTexture.active = target;

                var texture = new Texture2D(Size, Size, TextureFormat.RGBA32, false)
                {
                    filterMode = FilterMode.Bilinear,
                    wrapMode = TextureWrapMode.Clamp,
                    name = name + "_icon",
                    hideFlags = HideFlags.HideAndDontSave
                };
                texture.ReadPixels(new Rect(0f, 0f, Size, Size), 0, 0);
                texture.Apply();

                StokerPlugin.Log.LogInfo(string.Format(
                    "Icon for {0} rendered from the prefab at {1}px, subject {2:0.00}x"
                    + "{3:0.00}x{4:0.00}m.",
                    name, Size, bounds.size.x, bounds.size.y, bounds.size.z));

                return Sprite.Create(texture, new Rect(0f, 0f, Size, Size),
                                     new Vector2(0.5f, 0.5f));
            }
            catch (Exception e)
            {
                StokerPlugin.Log.LogWarning(
                    "Could not photograph " + name + " for its icon: " + e.Message
                    + " - falling back to the png beside the dll.");
                return null;
            }
            finally
            {
                RenderTexture.active = previous;
                if (target != null) RenderTexture.ReleaseTemporary(target);

                // DestroyImmediate, not Destroy. Registration happens inside a single
                // frame and a deferred destroy would leave the subject standing in the
                // scene for the rest of it - eight thousand metres down, but real, and
                // carrying a Piece.
                if (rig != null) UnityEngine.Object.DestroyImmediate(rig);
                if (subject != null) UnityEngine.Object.DestroyImmediate(subject);
            }
        }

        /// <summary>
        /// What the camera should frame: the renderers, not the transform hierarchy.
        ///
        /// A piece's bounds are not its geometry. Both of these now carry more than half a
        /// metre of buried timber so they do not float on uneven ground, and a collider
        /// that reaches down with it - frame on any of that and the icon is mostly empty
        /// space with the object squashed into the top of it.
        /// </summary>
        private static Bounds Framing(GameObject subject)
        {
            var bounds = new Bounds();
            var started = false;

            foreach (var renderer in subject.GetComponentsInChildren<Renderer>(false))
            {
                if (renderer == null || !renderer.enabled) continue;
                if (renderer is ParticleSystemRenderer) continue;

                if (!started) { bounds = renderer.bounds; started = true; }
                else bounds.Encapsulate(renderer.bounds);
            }

            return started ? bounds : new Bounds(subject.transform.position, Vector3.zero);
        }

        /// <summary>
        /// A warm key from over the camera's shoulder and a cool fill opposite it.
        ///
        /// Matched against the ripped vanilla icons rather than picked. Theirs are lit hard
        /// enough to blow small highlights on the top faces while keeping the shadowed
        /// sides readable rather than black, which is what gives a 64 pixel picture enough
        /// contrast to be identifiable at a glance. An evenly lit model at this size turns
        /// into a single silhouette of one colour - which is exactly what the Blender icons
        /// did, on top of having no texture to show.
        ///
        /// Parented to the rig so the lighting travels with the angle, and range-limited so
        /// it cannot reach anything else even though nothing else is on this layer.
        /// </summary>
        private static void Light(Transform rig, float reach)
        {
            var key = new GameObject("key").transform;
            key.SetParent(rig, false);
            key.localRotation = Quaternion.Euler(28f, -22f, 0f);

            var keyLight = key.gameObject.AddComponent<Light>();
            keyLight.type = LightType.Directional;
            keyLight.color = new Color(1f, 0.96f, 0.88f);
            keyLight.intensity = 1.35f;
            keyLight.cullingMask = 1 << Layer;

            var fill = new GameObject("fill").transform;
            fill.SetParent(rig, false);
            fill.localRotation = Quaternion.Euler(-14f, 158f, 0f);

            var fillLight = fill.gameObject.AddComponent<Light>();
            fillLight.type = LightType.Directional;
            fillLight.color = new Color(0.72f, 0.78f, 0.92f);
            fillLight.intensity = 0.55f;
            fillLight.cullingMask = 1 << Layer;
        }

        private static void SetLayer(GameObject root, int layer)
        {
            root.layer = layer;
            foreach (Transform child in root.transform) SetLayer(child.gameObject, layer);
        }
    }
}
