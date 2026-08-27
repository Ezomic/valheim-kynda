using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;

namespace Kynda
{
    /// <summary>
    /// Loads a Wavefront OBJ into a Mesh at runtime. OBJ is plain text and needs no asset
    /// bundle, which is what lets the mod ship a hand-modelled altar while staying a single
    /// DLL plus a text file.
    ///
    /// Handles what Blender's exporter emits: v / vt / vn and triangulated f with the
    /// v/vt/vn index form. Anything else is ignored rather than fought with.
    /// </summary>
    /// <summary>
    /// A loaded model and the names of its material groups, one per submesh. The groups
    /// are what let a bench be timber where it is timber and iron where it is iron: each
    /// gets its own material, and so its own texture.
    /// </summary>
    internal sealed class ModelData
    {
        public Mesh Mesh;
        public string[] Groups;
    }

    internal static class ObjMesh
    {
        public static ModelData Load(string path)
        {
            if (!File.Exists(path))
            {
                KyndaPlugin.Log.LogWarning("No model at " + path);
                return null;
            }

            try { return Parse(File.ReadAllLines(path), Path.GetFileNameWithoutExtension(path)); }
            catch (Exception e)
            {
                KyndaPlugin.Log.LogError("Could not read " + path + ": " + e.Message);
                return null;
            }
        }

        private static ModelData Parse(string[] lines, string name)
        {
            var positions = new List<Vector3>();
            var uvs = new List<Vector2>();
            var normals = new List<Vector3>();
            var shades = new List<Color>();

            // Faces are bucketed by the usemtl in force when they were met. Order matters
            // and Dictionary does not keep it, so the names are tracked alongside.
            var groupNames = new List<string>();
            var groupTris = new List<List<int>>();
            var groupIndex = new Dictionary<string, int>();

            // OBJ indexes position, uv and normal separately; Unity needs one flat vertex
            // per unique combination, so they are interned as they are met.
            var lookup = new Dictionary<string, int>();
            var outPositions = new List<Vector3>();
            var outUvs = new List<Vector2>();
            var outNormals = new List<Vector3>();
            var outShades = new List<Color>();

            var culture = CultureInfo.InvariantCulture;

            // Everything before the first usemtl belongs to a nameless group, which is
            // what a single-material model consists of entirely.
            var triangles = Bucket("", groupNames, groupTris, groupIndex);

            foreach (var raw in lines)
            {
                var line = raw.Trim();
                if (line.Length == 0 || line[0] == '#') continue;

                var parts = line.Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
                if (parts.Length < 2) continue;

                switch (parts[0])
                {
                    case "v":
                        if (parts.Length >= 4)
                        {
                            positions.Add(new Vector3(
                                float.Parse(parts[1], culture),
                                float.Parse(parts[2], culture),
                                float.Parse(parts[3], culture)));

                            // Baked occlusion rides along as optional r g b after the position.
                            if (parts.Length >= 7)
                            {
                                shades.Add(new Color(
                                    float.Parse(parts[4], culture),
                                    float.Parse(parts[5], culture),
                                    float.Parse(parts[6], culture), 1f));
                            }
                        }
                        break;

                    case "vt":
                        if (parts.Length >= 3)
                            uvs.Add(new Vector2(
                                float.Parse(parts[1], culture),
                                float.Parse(parts[2], culture)));
                        break;

                    case "vn":
                        if (parts.Length >= 4)
                            normals.Add(new Vector3(
                                float.Parse(parts[1], culture),
                                float.Parse(parts[2], culture),
                                float.Parse(parts[3], culture)));
                        break;

                    case "usemtl":
                        triangles = Bucket(parts[1].Trim(), groupNames, groupTris, groupIndex);
                        break;

                    case "f":
                        AddFace(parts, positions, uvs, normals, shades,
                            lookup, outPositions, outUvs, outNormals, outShades, triangles);
                        break;
                }
            }

            // Drop groups that never received a face, which is what the nameless bucket
            // becomes as soon as the model does name its materials.
            for (int i = groupTris.Count - 1; i >= 0; i--)
            {
                if (groupTris[i].Count != 0) continue;
                groupTris.RemoveAt(i);
                groupNames.RemoveAt(i);
            }

            if (outPositions.Count == 0 || groupTris.Count == 0)
            {
                KyndaPlugin.Log.LogError("Model " + name + " has no geometry.");
                return null;
            }

            var mesh = new Mesh { name = name };

            // 32 bit indices. Unity defaults a mesh to 16 bit, which tops out at 65535
            // vertices - and this model is over 70000 once the OBJ is split into one
            // vertex per position/uv/normal combination. Past the ceiling the indices
            // wrap round and each triangle is stitched between unrelated corners of the
            // model, which draws as huge thin sheets across the piece. The mesh data is
            // correct either way, which is why it survived every check made against the
            // file and every change of material.
            if (outPositions.Count > 65535)
            {
                mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
                KyndaPlugin.Log.LogInfo(name + " needs 32 bit indices ("
                                          + outPositions.Count + " verts).");
            }

            mesh.SetVertices(outPositions);
            if (outUvs.Count == outPositions.Count) mesh.SetUVs(0, outUvs);

            mesh.subMeshCount = groupTris.Count;
            for (int i = 0; i < groupTris.Count; i++) mesh.SetTriangles(groupTris[i], i);

            // Exported normals carry the smoothing across the bevelled edges, which is what
            // rounds the corners into the light. Safe to trust now the winding is correct;
            // recalculating would flatten every chamfer back into a hard edge.
            if (outNormals.Count == outPositions.Count) mesh.SetNormals(outNormals);
            else mesh.RecalculateNormals();

            // Baked occlusion travels in the vertex colours - but only if the shader
            // actually treats vertex colour as a tint.
            //
            // That was an assumption, never checked. Valheim's piece shaders are its own,
            // and a vertex colour channel in a game shader just as often drives blending,
            // wetness or wear masks. Feeding those a greyscale occlusion bake would not
            // darken creases, it would tell the shader whole faces are something they are
            // not - which is a candidate for the black facets on the altar. So it is a
            // setting now, and off means plain white.
            // Always plain white here. These models carry no baked occlusion, and the
            // warning above is the reason it never will: Valheim's piece shaders use the
            // vertex colour channel for their own purposes, so handing them a shading bake
            // does not darken creases, it lies to the shader about the surface.
            var white = new Color[outPositions.Count];
            for (int i = 0; i < white.Length; i++) white[i] = Color.white;
            mesh.colors = white;

            mesh.RecalculateBounds();
            mesh.RecalculateTangents();

            var total = 0;
            for (int i = 0; i < groupTris.Count; i++) total += groupTris[i].Count;

            KyndaPlugin.Log.LogInfo(string.Format("Loaded {0}: {1} verts, {2} tris, parts [{3}]",
                name, outPositions.Count, total / 3, string.Join(", ", groupNames.ToArray())));

            return new ModelData { Mesh = mesh, Groups = groupNames.ToArray() };
        }

        /// <summary>Finds or opens the triangle list for one material name.</summary>
        private static List<int> Bucket(string material, List<string> names,
            List<List<int>> buckets, Dictionary<string, int> index)
        {
            int slot;
            if (index.TryGetValue(material, out slot)) return buckets[slot];

            index[material] = buckets.Count;
            names.Add(material);
            buckets.Add(new List<int>());
            return buckets[buckets.Count - 1];
        }

        private static void AddFace(string[] parts,
            List<Vector3> positions, List<Vector2> uvs, List<Vector3> normals, List<Color> shades,
            Dictionary<string, int> lookup,
            List<Vector3> outPositions, List<Vector2> outUvs, List<Vector3> outNormals,
            List<Color> outShades, List<int> triangles)
        {
            var corners = new List<int>(parts.Length - 1);

            for (int i = 1; i < parts.Length; i++)
            {
                var key = parts[i];

                int index;
                if (!lookup.TryGetValue(key, out index))
                {
                    var fields = key.Split('/');

                    var vi = Index(fields, 0, positions.Count);
                    if (vi < 0) continue;

                    outPositions.Add(positions[vi]);
                    outShades.Add(vi < shades.Count ? shades[vi] : Color.white);

                    var ti = Index(fields, 1, uvs.Count);
                    outUvs.Add(ti >= 0 ? uvs[ti] : Vector2.zero);

                    var ni = Index(fields, 2, normals.Count);
                    outNormals.Add(ni >= 0 ? normals[ni] : Vector3.up);

                    index = outPositions.Count - 1;
                    lookup[key] = index;
                }
                corners.Add(index);
            }

            // Fan triangulation covers triangles and the odd quad alike. Winding is kept as
            // exported: reversing it turned every face inside out, so the outside of the
            // model was culled away and you saw straight through to the far inner walls.
            for (int i = 2; i < corners.Count; i++)
            {
                triangles.Add(corners[0]);
                triangles.Add(corners[i - 1]);
                triangles.Add(corners[i]);
            }
        }

        /// <summary>OBJ indices are 1-based, and negative means "counting back from here".</summary>
        private static int Index(string[] fields, int slot, int count)
        {
            if (slot >= fields.Length) return -1;

            var text = fields[slot];
            if (string.IsNullOrEmpty(text)) return -1;

            int value;
            if (!int.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out value)) return -1;

            if (value > 0) value -= 1;
            else if (value < 0) value = count + value;

            return value >= 0 && value < count ? value : -1;
        }
    }
}
