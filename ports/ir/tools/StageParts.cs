// HSDLib-backed, read-only stage inspector. DAT bytes arrive on stdin; only
// the caller-selected _build/tmp/stage-parts/<stage> directory is written.
using System.Globalization;
using System.Numerics;
using System.Text;
using System.Text.Json;
using HSDRaw;
using HSDRaw.Common;
using HSDRaw.GX;
using HSDRaw.Melee.Gr;

return StageParts.Entry(args);

static class StageParts
{
    static readonly CultureInfo CI = CultureInfo.InvariantCulture;
    static readonly Dictionary<HSDStruct, string> MaterialIds = new();
    static readonly Dictionary<HSDStruct, string> TextureIds = new();
    static readonly Dictionary<HSDStruct, string> ImageIds = new();
    static string Id(Dictionary<HSDStruct, string> ids, HSDStruct node, string prefix)
    {
        if (!ids.TryGetValue(node, out var id))
            ids[node] = id = $"{prefix}{ids.Count:D3}";
        return id;
    }
    static string F(float x) => x.ToString("G9", CI);
    static string Safe(string? x) => string.Concat((x ?? "unnamed").Select(c =>
        char.IsLetterOrDigit(c) || c == '_' || c == '-' ? c : '_'));

    static Matrix4x4 Local(HSD_JOBJ j)
    {
        // HSD viewer's Euler convention is row-vector Rx * Ry * Rz.
        return Matrix4x4.CreateScale(j.SX, j.SY, j.SZ)
             * Matrix4x4.CreateRotationX(j.RX)
             * Matrix4x4.CreateRotationY(j.RY)
             * Matrix4x4.CreateRotationZ(j.RZ)
             * Matrix4x4.CreateTranslation(j.TX, j.TY, j.TZ);
    }

    static IEnumerable<(int a, int b, int c)> Triangles(GXPrimitiveType type, int n)
    {
        if (type == GXPrimitiveType.Triangles)
            for (int i = 0; i + 2 < n; i += 3) yield return (i, i + 1, i + 2);
        else if (type == GXPrimitiveType.TriangleStrip)
            for (int i = 0; i + 2 < n; i++)
                yield return i % 2 == 0 ? (i, i + 1, i + 2) : (i + 1, i, i + 2);
        else if (type == GXPrimitiveType.TriangleFan)
            for (int i = 1; i + 1 < n; i++) yield return (0, i, i + 1);
        else if (type == GXPrimitiveType.Quads)
            for (int i = 0; i + 3 < n; i += 4)
            {
                yield return (i, i + 1, i + 2);
                yield return (i, i + 2, i + 3);
            }
    }

    static bool ValidTriangle(GX_Vertex a, GX_Vertex b, GX_Vertex c)
    {
        var x = new Vector3(a.POS.X, a.POS.Y, a.POS.Z);
        var y = new Vector3(b.POS.X, b.POS.Y, b.POS.Z);
        var z = new Vector3(c.POS.X, c.POS.Y, c.POS.Z);
        return Vector3.Cross(y - x, z - x).LengthSquared() > 1e-12f;
    }

    static int ExportPrimitive(StreamWriter writer, GX_DisplayList dl, GX_PrimitiveGroup prim,
                               int offset, int baseIndex, Matrix4x4 world)
    {
        int count = prim.Count;
        for (int i = 0; i < count; i++)
        {
            var v = dl.Vertices[offset + i];
            var pos = Vector3.Transform(new Vector3(v.POS.X, v.POS.Y, v.POS.Z), world);
            writer.WriteLine($"v {F(pos.X)} {F(pos.Y)} {F(pos.Z)}");
        }
        for (int i = 0; i < count; i++)
        {
            var uv = dl.Vertices[offset + i].TEX0;
            writer.WriteLine($"vt {F(uv.X)} {F(1 - uv.Y)}");
        }
        int triangles = 0;
        foreach (var (a, b, c) in Triangles(prim.PrimitiveType, count))
        {
            if (!ValidTriangle(dl.Vertices[offset + a], dl.Vertices[offset + b], dl.Vertices[offset + c]))
                continue;
            int ia = baseIndex + a, ib = baseIndex + b, ic = baseIndex + c;
            writer.WriteLine($"f {ia}/{ia} {ib}/{ib} {ic}/{ic}");
            triangles++;
        }
        return triangles;
    }

    static DobjInfo InspectDobj(HSD_DOBJ dobj, int groupId, int jointId, int dobjId,
                                string jointName, Matrix4x4 world, string outDir)
    {
        var info = new DobjInfo { Index = dobjId, Name = dobj.ClassName };
        var mat = dobj.Mobj;
        if (mat != null)
        {
            info.MaterialId = Id(MaterialIds, mat._s, "M");
            info.RenderFlags = (uint)mat.RenderFlags;
            var tex = mat.Textures;
            for (int ti = 0; tex != null && ti < 64; ti++, tex = tex.Next)
            {
                var image = tex.ImageData;
                info.Textures.Add(new TextureInfo { Id = Id(TextureIds, tex._s, "T"),
                    ImageId = image == null ? null : Id(ImageIds, image._s, "I"),
                    TexMapId = (int)tex.TexMapID, Width = image?.Width ?? 0,
                    Height = image?.Height ?? 0, Format = image?.Format.ToString() });
            }
        }
        var polys = new List<(HSD_POBJ pobj, GX_DisplayList dl)>();
        var pobj = dobj.Pobj;
        for (int pi = 0; pobj != null && pi < 4096; pi++, pobj = pobj.Next)
        {
            var dl = pobj.ToDisplayList();
            var p = new PobjInfo { Index = pi, Flags = (int)pobj.Flags,
                MaterialId = info.MaterialId,
                TextureIds = info.Textures.Select(t => t.Id).ToList(),
                PrimitiveCount = dl.Primitives.Count,
                VertexCount = dl.Vertices.Count,
                HasEnvelope = pobj.Flags.HasFlag(POBJ_FLAG.ENVELOPE),
                HasShapeAnimation = pobj.Flags.HasFlag(POBJ_FLAG.SHAPEANIM),
                HasSingleBind = pobj.SingleBoundJOBJ != null };
            int off = 0;
            foreach (var prim in dl.Primitives)
            {
                foreach (var (a, b, c) in Triangles(prim.PrimitiveType, prim.Count))
                    if (ValidTriangle(dl.Vertices[off + a], dl.Vertices[off + b], dl.Vertices[off + c]))
                        p.Triangles++;
                off += prim.Count;
            }
            info.Pobjs.Add(p);
            info.Triangles += p.Triangles;
            polys.Add((pobj, dl));
        }
        if (info.Triangles == 0) return info;

        var filename = $"g{groupId:D2}_j{jointId:D3}_d{dobjId:D2}_{Safe(jointName)}.obj";
        info.Obj = filename;
        using var writer = new StreamWriter(Path.Combine(outDir, filename), false, new UTF8Encoding(false));
        writer.WriteLine($"# Stage group {groupId}, joint {jointId} ({jointName}), DObj {dobjId}");
        writer.WriteLine("# Static rest pose. Texture images and animation are not embedded.");
        writer.WriteLine($"o {Safe(jointName)}_d{dobjId}");
        int nextIndex = 1;
        for (int pi = 0; pi < polys.Count; pi++)
        {
            var (poly, dl) = polys[pi];
            writer.WriteLine($"g pobj_{pi}");
            writer.WriteLine($"# material_id {info.MaterialId}; textures {string.Join(',', info.Textures.Select(t => t.Id))}");
            if (poly.Flags.HasFlag(POBJ_FLAG.ENVELOPE) || poly.Flags.HasFlag(POBJ_FLAG.SHAPEANIM) ||
                poly.SingleBoundJOBJ != null)
                writer.WriteLine("# WARNING: skinned, morph, or single-bound geometry uses owning JObj rest transform only");
            int off = 0;
            foreach (var prim in dl.Primitives)
            {
                ExportPrimitive(writer, dl, prim, off, nextIndex, world);
                off += prim.Count;
                nextIndex += prim.Count;
            }
        }
        return info;
    }

    static void Walk(HSD_JOBJ? node, int parent, int depth, Matrix4x4 parentWorld,
                     GroupInfo group, string outDir)
    {
        for (var j = node; j != null; j = j.Next)
        {
            int index = group.Joints.Count;
            var world = Local(j) * parentWorld;
            string name = string.IsNullOrWhiteSpace(j.ClassName) ? $"JOBJ_{index}" : j.ClassName;
            var ji = new JointInfo { Index = index, Parent = parent, Depth = depth,
                Name = name, Flags = (uint)j.Flags,
                Translation = new[] { j.TX, j.TY, j.TZ },
                RotationRadians = new[] { j.RX, j.RY, j.RZ },
                Scale = new[] { j.SX, j.SY, j.SZ },
                WorldTranslation = new[] { world.M41, world.M42, world.M43 } };
            group.Joints.Add(ji);
            int di = 0;
            for (var d = j.Dobj; d != null && di < 4096; d = d.Next, di++)
                ji.Dobjs.Add(InspectDobj(d, group.Index, index, di, name, world, outDir));
            if (j.Child != null) Walk(j.Child, index, depth + 1, world, group, outDir);
        }
    }

    static List<CollisionGroupInfo> Collisions(SBM_Coll_Data? coll)
    {
        var result = new List<CollisionGroupInfo>();
        if (coll?.LineGroups == null) return result;
        for (int i = 0; i < coll.LineGroups.Length; i++)
        {
            var g = coll.LineGroups[i];
            result.Add(new CollisionGroupInfo { Index = i,
                Floor = new[] { (int)g.TopLineIndex, (int)g.TopLineCount },
                Ceiling = new[] { (int)g.BottomLineIndex, (int)g.BottomLineCount },
                RightWall = new[] { (int)g.RightLineIndex, (int)g.RightLineCount },
                LeftWall = new[] { (int)g.LeftLineIndex, (int)g.LeftLineCount },
                Dynamic = new[] { (int)g.DynamicLineIndex, (int)g.DynamicLineCount },
                VertexSpan = new[] { (int)g.VertexStart, (int)g.VertexCount },
                Bounds = new[] { g.XMin, g.YMin, g.XMax, g.YMax } });
        }
        return result;
    }

    static List<CollisionLineInfo> CollisionLines(SBM_Coll_Data? coll,
                                                   List<CollisionGroupInfo> groups)
    {
        var result = new List<CollisionLineInfo>();
        var lines = coll?.Links ?? Array.Empty<SBM_CollLine>();
        var vertices = coll?.Vertices ?? Array.Empty<SBM_CollVertex>();
        for (int i = 0; i < lines.Length; i++)
        {
            var l = lines[i];
            var a = l.VertexIndex1 >= 0 && l.VertexIndex1 < vertices.Length ? vertices[l.VertexIndex1] : null;
            var b = l.VertexIndex2 >= 0 && l.VertexIndex2 < vertices.Length ? vertices[l.VertexIndex2] : null;
            var item = new CollisionLineInfo { Index = i,
                VertexIndices = new[] { (int)l.VertexIndex1, (int)l.VertexIndex2 },
                A = a == null ? null : new[] { a.X, a.Y },
                B = b == null ? null : new[] { b.X, b.Y },
                PhysicsFlags = (int)l.CollisionFlag, PropertyFlags = (int)l.Flag,
                Material = (int)l.Material,
                Adjacency = new[] { (int)l.NextLine, (int)l.PreviousLine,
                                    (int)l.NextLineAltGroup, (int)l.PreviousLineAltGroup } };
            foreach (var group in groups)
            {
                if (InRange(i, group.Floor)) item.Groups.Add($"{group.Index}:floor");
                if (InRange(i, group.Ceiling)) item.Groups.Add($"{group.Index}:ceiling");
                if (InRange(i, group.RightWall)) item.Groups.Add($"{group.Index}:right_wall");
                if (InRange(i, group.LeftWall)) item.Groups.Add($"{group.Index}:left_wall");
                if (InRange(i, group.Dynamic)) item.Groups.Add($"{group.Index}:dynamic");
            }
            result.Add(item);
        }
        return result;
    }

    static bool InRange(int i, int[] range) => range.Length == 2 && i >= range[0] && i < range[0] + range[1];

    static void AddLinks(GroupInfo group, HSDRaw.HSDArrayAccessor<SBM_Map_GOBJ_CollisionLink>? links,
                         int list, List<CollisionGroupInfo> collisions)
    {
        if (links == null) return;
        foreach (var link in links.Array)
        {
            var item = new CollisionLinkInfo { List = list, CollisionGroup = link.CollisionIndex,
                UnknownIndex = link.UnknownIndex, JobjIndex = link.JOBJIndex };
            group.CollisionLinks.Add(item);
            if (link.JOBJIndex >= 0 && link.JOBJIndex < group.Joints.Count)
                group.Joints[link.JOBJIndex].CollisionGroups.Add(link.CollisionIndex);
            if (link.CollisionIndex >= 0 && link.CollisionIndex < collisions.Count)
                collisions[link.CollisionIndex].Links.Add(new CollisionOwner {
                    Group = group.Index, JobjIndex = link.JOBJIndex, List = list });
        }
    }

    static int Run(string[] args)
    {
        if (args.Length != 2 || !System.Text.RegularExpressions.Regex.IsMatch(args[0], @"^Gr[A-Za-z0-9]+$"))
            throw new ArgumentException("usage: StageParts <GrName> <output-dir>");
        string stage = args[0], outDir = args[1];
        Directory.CreateDirectory(outDir);
        using var stream = new MemoryStream();
        Console.OpenStandardInput().CopyTo(stream);
        var file = new HSDRawFile(stream.ToArray());
        var map = file["map_head"]?.Data as SBM_Map_Head
            ?? throw new InvalidDataException("map_head not found or not parsed by HSDLib");
        var coll = file["coll_data"]?.Data as SBM_Coll_Data;
        var report = new StageReport { Stage = stage,
            PublicSymbols = file.Roots.Select(r => r.Name).ToList(),
            CollisionGroups = Collisions(coll),
            CollisionVertexCount = coll?.Vertices?.Length ?? 0,
            CollisionLineCount = coll?.Links?.Length ?? 0 };
        report.CollisionLines = CollisionLines(coll, report.CollisionGroups);
        var groups = map.ModelGroups?.Array ?? Array.Empty<SBM_Map_GOBJ>();
        for (int gi = 0; gi < groups.Length; gi++)
        {
            var group = new GroupInfo { Index = gi, HasRoot = groups[gi].RootNode != null,
                HasJointAnimation = groups[gi].JointAnimations != null,
                HasMaterialAnimation = groups[gi].MaterialAnimations != null,
                HasShapeAnimation = groups[gi].ShapeAnimations != null };
            report.Groups.Add(group);
            Walk(groups[gi].RootNode, -1, 0, Matrix4x4.Identity, group, outDir);
            AddLinks(group, groups[gi].CollisionLinks, 1, report.CollisionGroups);
            AddLinks(group, groups[gi].CollisionLinks2, 2, report.CollisionGroups);
        }
        report.JointCount = report.Groups.Sum(g => g.Joints.Count);
        report.DobjCount = report.Groups.Sum(g => g.Joints.Sum(j => j.Dobjs.Count));
        report.PobjCount = report.Groups.Sum(g => g.Joints.Sum(j => j.Dobjs.Sum(d => d.Pobjs.Count)));
        report.SeparableMeshCount = report.Groups.Sum(g => g.Joints.Sum(j => j.Dobjs.Count(d => d.Triangles > 0)));
        report.TriangleCount = report.Groups.Sum(g => g.Joints.Sum(j => j.Dobjs.Sum(d => d.Triangles)));
        string json = JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase });
        File.WriteAllText(Path.Combine(outDir, "hierarchy.json"), json + "\n", new UTF8Encoding(false));
        Console.WriteLine($"{stage}: groups={groups.Length} joints={report.JointCount} meshes={report.SeparableMeshCount} POBJs={report.PobjCount} triangles={report.TriangleCount} collision_groups={report.CollisionGroups.Count}");
        return 0;
    }

    public static int Entry(string[] args)
    {
        try { return Run(args); }
        catch (Exception ex) { Console.Error.WriteLine(ex); return 1; }
    }
}

sealed class StageReport
{
    public string Stage { get; set; } = "";
    public List<string> PublicSymbols { get; set; } = new();
    public List<GroupInfo> Groups { get; set; } = new();
    public List<CollisionGroupInfo> CollisionGroups { get; set; } = new();
    public List<CollisionLineInfo> CollisionLines { get; set; } = new();
    public int JointCount { get; set; }
    public int DobjCount { get; set; }
    public int PobjCount { get; set; }
    public int SeparableMeshCount { get; set; }
    public int TriangleCount { get; set; }
    public int CollisionVertexCount { get; set; }
    public int CollisionLineCount { get; set; }
}
sealed class GroupInfo
{
    public int Index { get; set; }
    public bool HasRoot { get; set; }
    public bool HasJointAnimation { get; set; }
    public bool HasMaterialAnimation { get; set; }
    public bool HasShapeAnimation { get; set; }
    public List<JointInfo> Joints { get; set; } = new();
    public List<CollisionLinkInfo> CollisionLinks { get; set; } = new();
}
sealed class JointInfo
{
    public int Index { get; set; }
    public int Parent { get; set; }
    public int Depth { get; set; }
    public string Name { get; set; } = "";
    public uint Flags { get; set; }
    public float[] Translation { get; set; } = Array.Empty<float>();
    public float[] RotationRadians { get; set; } = Array.Empty<float>();
    public float[] Scale { get; set; } = Array.Empty<float>();
    public float[] WorldTranslation { get; set; } = Array.Empty<float>();
    public List<int> CollisionGroups { get; set; } = new();
    public List<DobjInfo> Dobjs { get; set; } = new();
}
sealed class DobjInfo
{
    public int Index { get; set; }
    public string? Name { get; set; }
    public string? MaterialId { get; set; }
    public uint RenderFlags { get; set; }
    public List<TextureInfo> Textures { get; set; } = new();
    public List<PobjInfo> Pobjs { get; set; } = new();
    public int Triangles { get; set; }
    public string? Obj { get; set; }
}
sealed class PobjInfo
{
    public int Index { get; set; }
    public int Flags { get; set; }
    public string? MaterialId { get; set; }
    public List<string> TextureIds { get; set; } = new();
    public int PrimitiveCount { get; set; }
    public int VertexCount { get; set; }
    public int Triangles { get; set; }
    public bool HasEnvelope { get; set; }
    public bool HasShapeAnimation { get; set; }
    public bool HasSingleBind { get; set; }
}
sealed class TextureInfo
{
    public string Id { get; set; } = "";
    public string? ImageId { get; set; }
    public int TexMapId { get; set; }
    public int Width { get; set; }
    public int Height { get; set; }
    public string? Format { get; set; }
}
sealed class CollisionGroupInfo
{
    public int Index { get; set; }
    public int[] Floor { get; set; } = Array.Empty<int>();
    public int[] Ceiling { get; set; } = Array.Empty<int>();
    public int[] RightWall { get; set; } = Array.Empty<int>();
    public int[] LeftWall { get; set; } = Array.Empty<int>();
    public int[] Dynamic { get; set; } = Array.Empty<int>();
    public int[] VertexSpan { get; set; } = Array.Empty<int>();
    public float[] Bounds { get; set; } = Array.Empty<float>();
    public List<CollisionOwner> Links { get; set; } = new();
}
sealed class CollisionLinkInfo
{
    public int List { get; set; }
    public int CollisionGroup { get; set; }
    public int UnknownIndex { get; set; }
    public int JobjIndex { get; set; }
}
sealed class CollisionOwner
{
    public int Group { get; set; }
    public int JobjIndex { get; set; }
    public int List { get; set; }
}
sealed class CollisionLineInfo
{
    public int Index { get; set; }
    public int[] VertexIndices { get; set; } = Array.Empty<int>();
    public float[]? A { get; set; }
    public float[]? B { get; set; }
    public int PhysicsFlags { get; set; }
    public int PropertyFlags { get; set; }
    public int Material { get; set; }
    public int[] Adjacency { get; set; } = Array.Empty<int>();
    public List<string> Groups { get; set; } = new();
}
