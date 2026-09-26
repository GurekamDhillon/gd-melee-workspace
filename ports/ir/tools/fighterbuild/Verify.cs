using System.Numerics;
using System.Text.Json;
using HSDRaw;
using HSDRaw.Common;
using HSDRaw.GX;

// fighterbuild verify <out.dat> <mesh.json>   (from ports/halberd/model/tools/mkbuild/Verify.cs)
// Reload the built file with HSDRaw, rebuild rest world matrices from the stored joint SRT (HSD classical: T*Rz*Ry*Rx*S),
// skin every PObj vertex the way HSD does (single-weight envelope: joint world * v; multi: sum w * world * IBM * v)
// and compare each DObj's skinned bounding box / centroid with the source mesh (world bind space).
static class Verify
{
    static Matrix4x4 Local(HSD_JOBJ j) =>
        Matrix4x4.CreateScale(j.SX, j.SY, j.SZ) * Matrix4x4.CreateRotationX(j.RX) * Matrix4x4.CreateRotationY(j.RY) * Matrix4x4.CreateRotationZ(j.RZ) * Matrix4x4.CreateTranslation(j.TX, j.TY, j.TZ);
    static Matrix4x4 FromIbm(HSD_Matrix4x3 m) => new Matrix4x4(m.M11, m.M21, m.M31, 0, m.M12, m.M22, m.M32, 0, m.M13, m.M23, m.M33, 0, m.M14, m.M24, m.M34, 1);

    public static int Run(string dat, string meshPath)
    {
        var f = new HSDRawFile(dat);
        var root = f.Roots[0].Data as HSD_JOBJ;
        var list = root.TreeList;
        var world = new Dictionary<HSD_JOBJ, Matrix4x4>();
        void Walk(HSD_JOBJ j, Matrix4x4 parent) { for (var c = j; c != null; c = c.Next) { var w = Local(c) * parent; world[c] = w; if (c.Child != null) Walk(c.Child, w); } }
        Walk(root, Matrix4x4.Identity);
        double ibmErr = 0;
        foreach (var j in list) if (j.InverseWorldTransform != null) { Matrix4x4.Invert(world[j], out var inv); var s = FromIbm(j.InverseWorldTransform); for (int r = 0; r < 4; r++) for (int c = 0; c < 4; c++) ibmErr = Math.Max(ibmErr, Math.Abs(inv[r, c] - s[r, c])); }
        var mesh = JsonDocument.Parse(File.ReadAllText(meshPath)).RootElement.GetProperty("dobjs").EnumerateArray().ToList();
        int di = 0; double worst = 0; int nv = 0;
        foreach (var d in root.Dobj.List)
        {
            var mn = new Vector3(1e9f); var mx = new Vector3(-1e9f); var sum = Vector3.Zero; int n = 0;
            foreach (var p in d.Pobj.List)
            {
                var dl = p.ToDisplayList();
                var envs = p.EnvelopeWeights;
                foreach (var v in dl.Vertices)
                {
                    var pos = new Vector3(v.POS.X, v.POS.Y, v.POS.Z); Vector3 o;
                    var e = envs[v.PNMTXIDX / 3];
                    if (e.EnvelopeCount == 1) o = Vector3.Transform(pos, world[e.JOBJs[0]]);
                    else { o = Vector3.Zero; for (int k = 0; k < e.EnvelopeCount; k++) o += e.Weights[k] * Vector3.Transform(pos, FromIbm(e.JOBJs[k].InverseWorldTransform) * world[e.JOBJs[k]]); }
                    mn = Vector3.Min(mn, o); mx = Vector3.Max(mx, o); sum += o; n++;
                }
            }
            var src = mesh[di].GetProperty("tris").EnumerateArray().SelectMany(t => t.EnumerateArray()).Select(v => { var a = v.GetProperty("p").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray(); return new Vector3(a[0], a[1], a[2]); }).ToList();
            var smn = src.Aggregate(new Vector3(1e9f), Vector3.Min); var smx = src.Aggregate(new Vector3(-1e9f), Vector3.Max);
            var sc = src.Aggregate(Vector3.Zero, (a, b) => a + b) / src.Count; var c = sum / n;
            double err = Math.Max((mn - smn).Length(), (mx - smx).Length());   // centroids differ: the PObjs hold deduplicated vertices
            worst = Math.Max(worst, err); nv += n;
            Console.WriteLine($"dobj {di,2} verts {n,5} (src {src.Count,5}) centroid ({c.X:F2},{c.Y:F2},{c.Z:F2}) bbox err {err:F4} flags {d.Pobj.Flags}");
            di++;
        }
        Console.WriteLine($"joints {list.Count} ibm_vs_fk_max_err {ibmErr:E2} dobjs {di} verts {nv} worst_bbox_err {worst:F4}");
        return worst < 0.05 && ibmErr < 1e-3 ? 0 : 2;
    }
}
