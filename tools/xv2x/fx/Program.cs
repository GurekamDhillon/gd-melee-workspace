// Xv2Fx: local dumper for Xenoverse 2 effect / model / texture containers.
// Uses the LazyBone152 Xv2CoreLib (MIT) loaders. Read-only on inputs.
//
//   emb  <file.emb> <outDir>   extract embedded entries (raw bytes) + outDir/index.json
//   emo  <file.emo> <out.json> model dump: parts, meshes, vertex arrays, submeshes, skeleton
//   emp  <file.emp> <out.json> particle container (EMP_NEW loader, the XV2 binary path)
//   ecf  <file.ecf> <out.json> ECF colour container
//   etr  <file.etr> <out.json> ETR trail container
//   ema  <file.ema> <out.json> EMA animation container
//   emm  <file.emm> <out.json> EMM material container
//
// Generic dumps serialise the loaded object graph by reflection (public fields and
// properties, nothing dropped). Enums are written as {"name": "...", "value": N}.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Xv2Fx
{
    internal sealed class EnumNameValueConverterFactory : JsonConverterFactory
    {
        public override bool CanConvert(Type typeToConvert) =>
            typeToConvert.IsEnum || typeof(System.Windows.DependencyObject).IsAssignableFrom(typeToConvert);

        public override JsonConverter CreateConverter(Type typeToConvert, JsonSerializerOptions options)
        {
            if (typeToConvert.IsEnum)
                return (JsonConverter)Activator.CreateInstance(typeof(EnumNameValueConverter<>).MakeGenericType(typeToConvert));
            return (JsonConverter)Activator.CreateInstance(typeof(WpfObjectConverter<>).MakeGenericType(typeToConvert));
        }
    }

    // WPF objects (Transform, Brush, ImageSource...) are rendering state, not file data, and
    // their getters build fresh chains (Transform.Inverse.Inverse...) without end. They are
    // written as a marker with their CLR type name instead of being walked.
    internal sealed class WpfObjectConverter<T> : JsonConverter<T> where T : class
    {
        public override T Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            throw new NotSupportedException("Xv2Fx dumps are write-only.");
        }

        public override void Write(Utf8JsonWriter writer, T value, JsonSerializerOptions options)
        {
            if (value == null)
            {
                writer.WriteNullValue();
                return;
            }
            writer.WriteStartObject();
            writer.WriteString("wpfType", value.GetType().FullName);
            writer.WriteString("note", "WPF rendering object; not walked member-by-member");
            writer.WriteEndObject();
        }
    }

    internal sealed class EnumNameValueConverter<T> : JsonConverter<T> where T : struct, Enum
    {
        public override T Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            throw new NotSupportedException("Xv2Fx dumps are write-only.");
        }

        public override void Write(Utf8JsonWriter writer, T value, JsonSerializerOptions options)
        {
            writer.WriteStartObject();
            writer.WriteString("name", value.ToString());
            writer.WriteNumber("value", Convert.ToDecimal(value, CultureInfo.InvariantCulture));
            writer.WriteEndObject();
        }
    }

    internal static class Program
    {
        private static readonly JsonSerializerOptions DumpOptions = MakeOptions();

        private static JsonSerializerOptions MakeOptions()
        {
            var o = new JsonSerializerOptions
            {
                IncludeFields = true,
                WriteIndented = true,
                ReferenceHandler = ReferenceHandler.IgnoreCycles,
                MaxDepth = 512,
                NumberHandling = JsonNumberHandling.AllowNamedFloatingPointLiterals,
                DefaultIgnoreCondition = JsonIgnoreCondition.Never,
                Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
            };
            o.Converters.Add(new EnumNameValueConverterFactory());
            return o;
        }

        private static int Main(string[] args)
        {
            try
            {
                if (args.Length < 2) return Usage();
                string cmd = args[0].ToLowerInvariant();
                string input = args[1];
                string output = args.Length > 2 ? args[2] : null;
                if (output == null) return Usage();

                switch (cmd)
                {
                    case "emb":
                        return ExtractEmb(input, output);
                    case "emo":
                        return DumpEmo(input, output);
                    case "emp":
                        return WriteJson(Xv2CoreLib.EMP_NEW.EMP_File.Load(File.ReadAllBytes(input), true), input, output);
                    case "ecf":
                        return WriteJson(Xv2CoreLib.ECF.ECF_File.Load(File.ReadAllBytes(input)), input, output);
                    case "etr":
                        return WriteJson(Xv2CoreLib.ETR.ETR_File.Load(File.ReadAllBytes(input)), input, output);
                    case "ema":
                        return WriteJson(Xv2CoreLib.EMA.EMA_File.Load(File.ReadAllBytes(input)), input, output);
                    case "emm":
                        return WriteJson(Xv2CoreLib.EMM.EMM_File.LoadEmm(File.ReadAllBytes(input)), input, output);
                    default:
                        return Usage();
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("ERROR: " + ex);
                return 1;
            }
        }

        private static int Usage()
        {
            Console.Error.WriteLine("usage: Xv2Fx <emb|emo|emp|ecf|etr|ema|emm> <input> <output>");
            return 2;
        }

        private static int WriteJson(object root, string input, string output)
        {
            if (root == null) throw new InvalidDataException("loader returned null for " + input);
            string json = JsonSerializer.Serialize(root, root.GetType(), DumpOptions);
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output)));
            File.WriteAllText(output, json, new UTF8Encoding(false));
            Console.WriteLine("wrote " + output + " (" + new FileInfo(output).Length + " bytes, root " + root.GetType().FullName + ")");
            return 0;
        }

        // ---------------------------------------------------------------- EMB

        private sealed class EmbIndexRow
        {
            public int index { get; set; }
            public int id { get; set; }
            public string name { get; set; }
            public string file { get; set; }
            public long size { get; set; }
        }

        private static int ExtractEmb(string input, string outDir)
        {
            var emb = Xv2CoreLib.EMB_CLASS.EMB_File.Load(File.ReadAllBytes(input));
            Directory.CreateDirectory(outDir);
            var rows = new List<EmbIndexRow>();
            var used = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            for (int i = 0; i < emb.Entry.Count; i++)
            {
                var e = emb.Entry[i];
                string stored = e.Name ?? string.Empty;
                string baseName = Path.GetFileName(stored);
                if (string.IsNullOrWhiteSpace(baseName) || baseName.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0)
                    baseName = "entry_" + i.ToString("D4") + ".bin";
                string fileName = baseName;
                if (!used.Add(fileName))
                {
                    fileName = i.ToString("D4") + "_" + baseName;
                    used.Add(fileName);
                }
                byte[] data = e.Data ?? Array.Empty<byte>();
                File.WriteAllBytes(Path.Combine(outDir, fileName), data);
                rows.Add(new EmbIndexRow { index = i, id = e.ID, name = stored, file = fileName, size = data.Length });
                Console.WriteLine("  [" + i + "] " + (stored.Length == 0 ? "(no name)" : stored) + "  " + data.Length + " bytes -> " + fileName);
            }

            File.WriteAllText(Path.Combine(outDir, "index.json"),
                JsonSerializer.Serialize(rows, new JsonSerializerOptions { WriteIndented = true, Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping }),
                new UTF8Encoding(false));
            Console.WriteLine("emb: " + rows.Count + " entries, version " + emb.Version + ", -> " + outDir);
            return 0;
        }

        // ---------------------------------------------------------------- EMO

        private static int DumpEmo(string input, string output)
        {
            var emo = Xv2CoreLib.EMO.EMO_File.Load(File.ReadAllBytes(input));

            float[] mn = null, mx = null;
            int meshCount = 0, vertCount = 0, submeshCount = 0, triCount = 0, badFaces = 0;

            var parts = new List<object>();
            for (int p = 0; p < emo.Parts.Count; p++)
            {
                var part = emo.Parts[p];
                var emgs = new List<object>();
                for (int g = 0; g < part.EmgFiles.Count; g++)
                {
                    var emg = part.EmgFiles[g];
                    var meshes = new List<object>();
                    for (int m = 0; m < emg.EmgMeshes.Count; m++)
                    {
                        var mesh = emg.EmgMeshes[m];
                        meshCount++;
                        var verts = mesh.Vertices ?? new List<Xv2CoreLib.EMD.EMD_Vertex>();
                        vertCount += verts.Count;
                        foreach (var v in verts)
                            Grow(ref mn, ref mx, v.PositionX, v.PositionY, v.PositionZ);

                        var groups = new List<object>();
                        foreach (var grp in mesh.SubmeshGroups)
                        {
                            var subs = new List<object>();
                            foreach (var sm in grp.Submeshes)
                            {
                                submeshCount++;
                                short[] faces = sm.Faces ?? Array.Empty<short>();
                                int tris = faces.Length / 3;
                                triCount += tris;
                                var triList = new List<int[]>();
                                for (int t = 0; t < tris; t++)
                                {
                                    int a = faces[3 * t], b = faces[3 * t + 1], c = faces[3 * t + 2];
                                    if (a < 0 || b < 0 || c < 0 || a >= verts.Count || b >= verts.Count || c >= verts.Count) badFaces++;
                                    triList.Add(new[] { a, b, c });
                                }
                                subs.Add(new
                                {
                                    barycenter = new[] { sm.BarycenterX, sm.BarycenterY, sm.BarycenterZ, sm.BarycenterW },
                                    textureListIndex = sm.TextureListIndex,
                                    materialName = sm.MaterialName,
                                    boneIndices = sm.Bones,
                                    faceCount = faces.Length,
                                    faces = faces,
                                    triangleCount = tris,
                                    trailingFaces = faces.Length % 3,
                                    triangles = triList,
                                });
                            }
                            groups.Add(new
                            {
                                materialName = grp.MaterialName,
                                textureSamplerDefs = grp.TextureSamplerDefs,
                                submeshes = subs,
                            });
                        }

                        meshes.Add(new
                        {
                            index = m,
                            i08 = mesh.I_08,
                            vertexFlags = mesh.VertexFlags,
                            strips = mesh.Strips,
                            aabb = mesh.AABB,
                            vertexCount = verts.Count,
                            vertices = new
                            {
                                position = verts.Select(v => new[] { v.PositionX, v.PositionY, v.PositionZ }).ToList(),
                                normal = verts.Select(v => new[] { v.NormalX, v.NormalY, v.NormalZ }).ToList(),
                                tangent = verts.Select(v => new[] { v.TangentX, v.TangentY, v.TangentZ }).ToList(),
                                uv = verts.Select(v => new[] { v.TextureU, v.TextureV }).ToList(),
                                uv2 = verts.Select(v => new[] { v.Texture2U, v.Texture2V }).ToList(),
                                color = verts.Select(v => new[] { v.ColorR, v.ColorG, v.ColorB, v.ColorA }).ToList(),
                                blendIndexes = verts.Select(v => v.BlendIndexes).ToList(),
                                blendWeights = verts.Select(v => v.BlendWeights).ToList(),
                            },
                            submeshGroups = groups,
                        });
                    }
                    emgs.Add(new { index = g, linkedBoneIdx = emg.LinkedBoneIdx, meshes = meshes });
                }
                parts.Add(new { index = p, name = part.Name, emgFiles = emgs });
            }

            var bones = new List<object>();
            if (emo.Skeleton != null)
            {
                foreach (var b in emo.Skeleton.Bones)
                {
                    var rm = b.RelativeMatrix;
                    float[] mat = rm == null ? null : new[]
                    {
                        rm.M11, rm.M12, rm.M13, rm.M14,
                        rm.M21, rm.M22, rm.M23, rm.M24,
                        rm.M31, rm.M32, rm.M33, rm.M34,
                        rm.M41, rm.M42, rm.M43, rm.M44,
                    };
                    bones.Add(new
                    {
                        index = b.Index,
                        name = b.Name,
                        parentIndex = b.ParentIndex,
                        childIndex = b.ChildIndex,
                        siblingIndex = b.SiblingIndex,
                        emoPartIndex = b.EmoPartIndex,
                        relativeMatrixRowMajor = mat,
                    });
                }
            }

            var result = new
            {
                file = Path.GetFileName(input),
                signature = "#EMO",
                version = emo.Version,
                i24 = emo.I_24,
                materialsCount = emo.MaterialsCount,
                totals = new { parts = emo.Parts.Count, meshes = meshCount, vertices = vertCount, submeshes = submeshCount, triangles = triCount, faceIndicesOutOfRange = badFaces },
                bbox = mn == null ? null : new { min = mn, max = mx },
                boneHierarchy = bones,
                skeleton = emo.Skeleton,
                parts = parts,
            };

            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output)));
            File.WriteAllText(output, JsonSerializer.Serialize(result, DumpOptions), new UTF8Encoding(false));
            Console.WriteLine("emo: parts=" + emo.Parts.Count + " meshes=" + meshCount + " verts=" + vertCount + " submeshes=" + submeshCount + " tris=" + triCount + " -> " + output);
            return 0;
        }

        private static void Grow(ref float[] mn, ref float[] mx, float x, float y, float z)
        {
            if (mn == null)
            {
                mn = new[] { x, y, z };
                mx = new[] { x, y, z };
                return;
            }
            float[] v = { x, y, z };
            for (int i = 0; i < 3; i++)
            {
                if (v[i] < mn[i]) mn[i] = v[i];
                if (v[i] > mx[i]) mx[i] = v[i];
            }
        }
    }
}
