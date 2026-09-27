using System.Numerics;
using System.Text.Json;
using HSDRaw.Common;
using HSDRaw.GX;

// Checks the serialized PC palette format and compares decoded triangles with JSON.
static class PaletteVerify
{
    public const string ClassName = "geno_pal_pobj_v1";
    public record Result(int POBJs, int Triangles, int TriangleDifferences, int WeightDifferences);

    static Matrix4x4 FromIbm(HSD_Matrix4x3 m) => new(
        m.M11, m.M21, m.M31, 0, m.M12, m.M22, m.M32, 0,
        m.M13, m.M23, m.M33, 0, m.M14, m.M24, m.M34, 1);

    static Vector3 JsonPosition(JsonElement e)
    {
        var a = e.EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
        return new Vector3(a[0], a[1], a[2]);
    }

    static string Weights(IEnumerable<(int Joint, float Weight)> weights) =>
        string.Join(",", weights.OrderBy(x => x.Joint)
            .Select(x => $"{x.Joint}:{BitConverter.SingleToInt32Bits(x.Weight):X8}"));

    sealed class SourceTriangle
    {
        public Vector3[] Points;
        public string[] Weights;
        public bool GeometryMatched;
        public bool WeightedMatched;
    }

    static (int, int, int) Cell(Vector3 p) =>
        ((int)MathF.Floor(p.X * 1000), (int)MathF.Floor(p.Y * 1000), (int)MathF.Floor(p.Z * 1000));

    static Vector3 Centroid(Vector3 a, Vector3 b, Vector3 c) => (a + b + c) / 3;

    static bool MatchTriangle(Dictionary<(int, int, int), List<SourceTriangle>> cells,
        Vector3[] points, string[] weights, bool weighted)
    {
        var (x, y, z) = Cell(Centroid(points[0], points[1], points[2]));
        SourceTriangle best = null;
        float bestDistance = float.MaxValue;
        for (int dx = -1; dx <= 1; dx++)
            for (int dy = -1; dy <= 1; dy++)
                for (int dz = -1; dz <= 1; dz++)
                    if (cells.TryGetValue((x + dx, y + dy, z + dz), out var bucket))
                        foreach (var candidate in bucket)
                        {
                            if (weighted ? candidate.WeightedMatched : candidate.GeometryMatched) continue;
                            for (int rotation = 0; rotation < 3; rotation++)
                            {
                                float distance = 0;
                                bool fits = true;
                                for (int i = 0; i < 3; i++)
                                {
                                    int j = (i + rotation) % 3;
                                    float d = Vector3.DistanceSquared(points[i], candidate.Points[j]);
                                    if (d > 1e-6f || (weighted && weights[i] != candidate.Weights[j]))
                                    {
                                        fits = false;
                                        break;
                                    }
                                    distance += d;
                                }
                                if (fits && distance < bestDistance)
                                {
                                    best = candidate;
                                    bestDistance = distance;
                                }
                            }
                        }
        if (best == null) return false;
        if (weighted) best.WeightedMatched = true; else best.GeometryMatched = true;
        return true;
    }

    public static Result Compare(HSD_DOBJ dobj, JsonElement source,
        Dictionary<HSD_JOBJ, Matrix4x4> world, IReadOnlyList<HSD_JOBJ> joints, int dobjIndex)
    {
        var jointIds = joints.Select((j, i) => (j, i)).ToDictionary(x => x.j._s, x => x.i);
        var triangleCells = new Dictionary<(int, int, int), List<SourceTriangle>>();
        var sourceTriangles = new List<SourceTriangle>();
        bool flip = Environment.GetEnvironmentVariable("FIGHTERBUILD_FLIP") == "1";
        foreach (var triangle in source.GetProperty("tris").EnumerateArray())
        {
            var vertices = (flip ? triangle.EnumerateArray().Reverse() : triangle.EnumerateArray()).ToArray();
            var sourceTriangle = new SourceTriangle
            {
                Points = vertices.Select(v => JsonPosition(v.GetProperty("p"))).ToArray(),
                Weights = vertices.Select(v => Weights(v.GetProperty("w").EnumerateArray()
                    .Select(item => (item[0].GetInt32(), (float)item[1].GetDouble())))).ToArray()
            };
            sourceTriangles.Add(sourceTriangle);
            var triangleCell = Cell(Centroid(sourceTriangle.Points[0], sourceTriangle.Points[1], sourceTriangle.Points[2]));
            if (!triangleCells.TryGetValue(triangleCell, out var triangleBucket))
                triangleCells.Add(triangleCell, triangleBucket = new List<SourceTriangle>());
            triangleBucket.Add(sourceTriangle);
        }
        int pobjs = 0, triangles = 0, geometryUnmatched = 0, weightedUnmatched = 0;
        foreach (var pobj in dobj.Pobj.List)
        {
            if (pobj._s.GetString(0x00) != ClassName)
                throw new InvalidDataException($"DOBJ {dobjIndex}: mixed PC palette and ordinary POBJs");
            pobjs++;
            var flags = pobj.Flags;
            if (flags != (POBJ_FLAG.ENVELOPE | (flags & (POBJ_FLAG.CULLBACK | POBJ_FLAG.CULLFRONT))))
                throw new InvalidDataException($"DOBJ {dobjIndex}: invalid PC palette POBJ flags {flags}");
            var envelopes = pobj.EnvelopeWeights;
            if (envelopes == null || envelopes.Length < 1 || envelopes.Length > 64)
                throw new InvalidDataException($"DOBJ {dobjIndex}: PC palette envelope count outside 1..64");
            foreach (var envelope in envelopes)
            {
                if (envelope == null || envelope.EnvelopeCount < 1 ||
                    envelope.Weights.Any(w => float.IsNaN(w) || float.IsInfinity(w) || w < 0) ||
                    Math.Abs(envelope.Weights.Sum(w => (double)w) - 1.0) > 1e-5 ||
                    (envelope.EnvelopeCount == 1 && envelope.Weights[0] != 1.0f))
                    throw new InvalidDataException($"DOBJ {dobjIndex}: invalid PC palette weights");
            }
            var dl = pobj.ToDisplayList();
            var attrs = dl.Attributes.Where(a => a.AttributeName != GXAttribName.GX_VA_NULL).ToArray();
            if (attrs.Length < 3 || attrs[0].AttributeName != GXAttribName.GX_VA_PNMTXIDX ||
                attrs[0].AttributeType != GXAttribType.GX_DIRECT || attrs[0].CompCount != GXCompCnt.PosXYZ ||
                attrs[0].CompType != GXCompType.UInt8 || attrs[1].AttributeName != GXAttribName.GX_VA_POS ||
                attrs[2].AttributeName != GXAttribName.GX_VA_NRM ||
                attrs.Any(a => a.AttributeName >= GXAttribName.GX_VA_TEX0MTXIDX && a.AttributeName <= GXAttribName.GX_VA_TEX7MTXIDX))
                throw new InvalidDataException($"DOBJ {dobjIndex}: invalid PC palette vertex descriptor");

            var points = new Vector3[dl.Vertices.Count];
            var weights = new string[dl.Vertices.Count];
            for (int i = 0; i < dl.Vertices.Count; i++)
            {
                var v = dl.Vertices[i];
                int slot = v.PNMTXIDX; // DIRECT u8: deliberately no GX /3 scaling.
                if (slot >= envelopes.Length)
                    throw new InvalidDataException($"DOBJ {dobjIndex}: slot {slot} >= {envelopes.Length}");
                var envelope = envelopes[slot];
                var stored = new Vector3(v.POS.X, v.POS.Y, v.POS.Z);
                Vector3 skinned;
                if (envelope.EnvelopeCount == 1)
                    skinned = Vector3.Transform(stored, world[envelope.JOBJs[0]]);
                else
                {
                    skinned = Vector3.Zero;
                    for (int k = 0; k < envelope.EnvelopeCount; k++)
                    {
                        var joint = envelope.JOBJs[k];
                        skinned += envelope.Weights[k] * Vector3.Transform(stored,
                            FromIbm(joint.InverseWorldTransform) * world[joint]);
                    }
                }
                var weight = Weights(Enumerable.Range(0, envelope.EnvelopeCount)
                    .Select(k => (jointIds[envelope.JOBJs[k]._s], envelope.Weights[k])));
                points[i] = skinned;
                weights[i] = weight;
            }

            int offset = 0;
            foreach (var primitive in dl.Primitives)
            {
                if (primitive.Count > 32766 || (primitive.PrimitiveType != GXPrimitiveType.Triangles &&
                    primitive.PrimitiveType != GXPrimitiveType.TriangleStrip))
                    throw new InvalidDataException($"DOBJ {dobjIndex}: invalid PC palette primitive");
                void AddAt(int a, int b, int c)
                {
                    var trianglePoints = new[] { points[offset + a], points[offset + b], points[offset + c] };
                    var triangleWeights = new[] { weights[offset + a], weights[offset + b], weights[offset + c] };
                    if (!MatchTriangle(triangleCells, trianglePoints, triangleWeights, false)) geometryUnmatched++;
                    if (!MatchTriangle(triangleCells, trianglePoints, triangleWeights, true)) weightedUnmatched++;
                    triangles++;
                }
                if (primitive.PrimitiveType == GXPrimitiveType.Triangles)
                {
                    if (primitive.Count % 3 != 0)
                        throw new InvalidDataException($"DOBJ {dobjIndex}: incomplete triangle list");
                    for (int i = 0; i < primitive.Count; i += 3) AddAt(i, i + 1, i + 2);
                }
                else
                    for (int i = 2; i < primitive.Count; i++)
                        if (i % 2 == 0) AddAt(i - 2, i - 1, i); else AddAt(i - 1, i - 2, i);
                offset += primitive.Count;
            }
        }

        return new Result(pobjs, triangles,
            geometryUnmatched + sourceTriangles.Count(t => !t.GeometryMatched),
            weightedUnmatched + sourceTriangles.Count(t => !t.WeightedMatched));
    }
}
