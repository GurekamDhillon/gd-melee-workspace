using System.Numerics;
using System.Text.Json;
using HSDRaw;
using HSDRaw.Common;
using HSDRaw.Common.Animation;
using HSDRaw.GX;
using HSDRaw.Tools;

// mkbuild eyecheck <PlBmXx.dat> <eye_states.json> [report.json]
// The eyes, read back from the BUILT file (HSDRaw), no game: for every eye TObj (CI8 metaknight_eye) of every DObj, the
// PObj triangles are skinned to the rest pose (as Verify) and sampled on a barycentric grid through that TObj's own
// vertex UV set and texture matrix (tobj.c: uv' = repeat/scale * (uv - translate)); a sample with texel alpha > 0 draws
// eye. Per layer: opaque samples, their world centroid and side. Checks: two eye layers, each draws on one side of the
// head only, the two centroids mirror across x = 0; the matanim tracks evaluated at every integer frame (FOBJ_Player)
// equal eye_states.json's state for that frame; and per state the opaque coverage of both eyes (blinks go to ~0).
static class EyeCheck
{
    static Matrix4x4 Local(HSD_JOBJ j) =>
        Matrix4x4.CreateScale(j.SX, j.SY, j.SZ) * Matrix4x4.CreateRotationX(j.RX) * Matrix4x4.CreateRotationY(j.RY) * Matrix4x4.CreateRotationZ(j.RZ) * Matrix4x4.CreateTranslation(j.TX, j.TY, j.TZ);
    static Matrix4x4 FromIbm(HSD_Matrix4x3 m) => new Matrix4x4(m.M11, m.M21, m.M31, 0, m.M12, m.M22, m.M32, 0, m.M13, m.M23, m.M33, 0, m.M14, m.M24, m.M34, 1);

    public static int Run(string dat, string statesPath, string reportPath)
    {
        var f = new HSDRawFile(dat);
        var root = f.Roots.First(r => r.Name.EndsWith("_Share_joint")).Data as HSD_JOBJ;
        var mat = new HSD_MatAnimJoint { _s = f.Roots.First(r => r.Name.EndsWith("matanim_joint")).Data._s };
        var states = JsonDocument.Parse(File.ReadAllText(statesPath)).RootElement.GetProperty("states").EnumerateArray()
                     .Select(s => s.EnumerateArray().Select(x => (float)x.GetDouble()).ToArray()).ToList();
        var world = new Dictionary<HSD_JOBJ, Matrix4x4>();
        void Walk(HSD_JOBJ j, Matrix4x4 parent) { for (var c = j; c != null; c = c.Next) { var w = Local(c) * parent; world[c] = w; if (c.Child != null) Walk(c.Child, w); } }
        Walk(root, Matrix4x4.Identity);
        var rep = new Dictionary<string, object>(); bool ok = true; var notes = new List<string>();
        var dobjs = root.Dobj.List; int gT = 0;
        var layers = new List<(int dobj, int tobj, int global, GXTexMapID id, List<(Vector3[] p, Vector2[] uv)> tris, byte[] img, int w, int h)>();
        for (int di = 0; di < dobjs.Count; di++)
        {
            var tl = dobjs[di].Mobj.Textures.List;
            for (int ti = 0; ti < tl.Count; ti++, gT++)
            {
                var t = tl[ti];
                if (t.ImageData == null || t.ImageData.Format != GXTexFmt.CI8 || t.ImageData.Width != 256) continue;
                int src = (int)t.GXTexGenSrc - (int)GXTexGenSrc.GX_TG_TEX0;
                var tris = new List<(Vector3[] p, Vector2[] uv)>();
                foreach (var p in dobjs[di].Pobj.List)
                {
                    var dl = p.ToDisplayList(); var envs = p.EnvelopeWeights;
                    var tv = new List<GX_Vertex>(); int off = 0;
                    foreach (var prim in dl.Primitives)
                    {
                        var pv = dl.Vertices.GetRange(off, prim.Count); off += prim.Count;
                        if (prim.PrimitiveType == GXPrimitiveType.Triangles) tv.AddRange(pv);
                        else if (prim.PrimitiveType == GXPrimitiveType.TriangleStrip)
                            for (int k = 2; k < pv.Count; k++) { if (k % 2 == 0) { tv.Add(pv[k - 2]); tv.Add(pv[k - 1]); } else { tv.Add(pv[k - 1]); tv.Add(pv[k - 2]); } tv.Add(pv[k]); }
                        else throw new Exception("primitive " + prim.PrimitiveType);
                    }
                    for (int k = 0; k + 2 < tv.Count; k += 3)
                    {
                        var P = new Vector3[3]; var U = new Vector2[3];
                        for (int m = 0; m < 3; m++)
                        {
                            var v = tv[k + m]; var pos = new Vector3(v.POS.X, v.POS.Y, v.POS.Z);
                            var e = envs[v.PNMTXIDX / 3]; Vector3 o;
                            if (e.EnvelopeCount == 1) o = Vector3.Transform(pos, world[e.JOBJs[0]]);
                            else { o = Vector3.Zero; for (int q = 0; q < e.EnvelopeCount; q++) o += e.Weights[q] * Vector3.Transform(pos, FromIbm(e.JOBJs[q].InverseWorldTransform) * world[e.JOBJs[q]]); }
                            P[m] = o;
                            var uv = src == 0 ? v.TEX0 : src == 1 ? v.TEX1 : v.TEX2;
                            U[m] = new Vector2(uv.X, uv.Y);
                        }
                        tris.Add((P, U));
                    }
                }
                var img = GXImageConverter.DecodeTPL(t.ImageData.Format, t.ImageData.Width, t.ImageData.Height, t.ImageData.ImageData,
                                                     t.TlutData.Format, t.TlutData.ColorCount, t.TlutData.TlutData.Concat(new byte[Math.Max(0, t.TlutData.ColorCount * 2 - t.TlutData.TlutData.Length)]).ToArray());
                layers.Add((di, ti, gT, t.TexMapID, tris, img, t.ImageData.Width, t.ImageData.Height));
            }
        }
        // matanim tracks of each eye layer (root node's MatAnim list, one per DObj)
        var mas = mat.MaterialAnimation.List;
        (int n, float sx, float sy, float tx, float ty, Vector3 c) Cover(int li, float SX, float SY, float TX, float TY)
        {
            var L = layers[li]; int n = 0; var c = Vector3.Zero;
            foreach (var (P, U) in L.tris)
                for (int a = 0; a <= 12; a++) for (int b = 0; a + b <= 12; b++)
                    {
                        float wa = a / 12f, wb = b / 12f, wc = 1 - wa - wb;
                        var uv = U[0] * wa + U[1] * wb + U[2] * wc;
                        float u = (uv.X - TX) / SX, v = (uv.Y - TY) / SY;
                        int x = (int)MathF.Floor(Math.Clamp(u, 0f, 0.99999f) * L.w), y = (int)MathF.Floor(Math.Clamp(v, 0f, 0.99999f) * L.h);   // GX CLAMP
                        if (L.img[(y * L.w + x) * 4 + 3] > 0) { n++; c += P[0] * wa + P[1] * wb + P[2] * wc; }
                    }
            return (n, SX, SY, TX, TY, n > 0 ? c / n : Vector3.Zero);
        }
        var lrep = new List<object>();
        for (int li = 0; li < layers.Count; li++)
        {
            var L = layers[li];
            var r0 = Cover(li, 1, 1, 0, 0);
            var ta = mas[L.dobj].TextureAnimation?.List.FirstOrDefault(x => x.GXTexMapID == L.id);
            double trackErr = -1; int col = -1;
            if (ta != null && ta.AnimationObject?.FObjDesc != null)
            {
                var tracks = ta.AnimationObject.FObjDesc.List.ToDictionary(x => (TexTrackType)x.TrackType, x => new FOBJ_Player(x.TrackType, x.GetDecodedKeys()));
                // which state column block this layer plays (0 = Texture0, 4 = Texture1): the one its frame-1.. values match
                double best = 1e9;
                foreach (var cc in new[] { 0, 4 })
                {
                    double e = 0;
                    for (int s = 0; s < states.Count; s++)
                    {
                        e = Math.Max(e, Math.Abs(tracks[TexTrackType.HSD_A_T_SCAU].GetValue(s) - states[s][cc + 0]));
                        e = Math.Max(e, Math.Abs(tracks[TexTrackType.HSD_A_T_SCAV].GetValue(s) - states[s][cc + 1]));
                        e = Math.Max(e, Math.Abs(tracks[TexTrackType.HSD_A_T_TRAU].GetValue(s) - states[s][cc + 2]));
                        e = Math.Max(e, Math.Abs(tracks[TexTrackType.HSD_A_T_TRAV].GetValue(s) - states[s][cc + 3]));
                    }
                    if (e < best) { best = e; col = cc; }
                }
                trackErr = best;
            }
            int zero = 0, minN = int.MaxValue, maxN = 0;
            if (col >= 0)
                for (int s = 0; s < states.Count; s++)
                {
                    var r = Cover(li, states[s][col], states[s][col + 1], states[s][col + 2], states[s][col + 3]);
                    if (r.n == 0) zero++; minN = Math.Min(minN, r.n); maxN = Math.Max(maxN, r.n);
                }
            lrep.Add(new { dobj = L.dobj, tobj_in_dobj = L.tobj, tobj_global = L.global, map = L.id.ToString(), tris = L.tris.Count,
                           opaque_samples_rest = r0.n, centroid_rest = new[] { r0.c.X, r0.c.Y, r0.c.Z }, side = r0.c.X > 0 ? "+x" : "-x",
                           texanim = ta != null, state_block = col == 0 ? "Texture0" : col == 4 ? "Texture1" : "-", track_max_err = trackErr,
                           states_with_no_eye_visible = zero, opaque_samples_min = minN == int.MaxValue ? 0 : minN, opaque_samples_max = maxN });
            Console.WriteLine($"eye layer dobj {L.dobj} tobj {L.tobj} (global {L.global}, {L.id}) tris {L.tris.Count}: rest opaque {r0.n} at ({r0.c.X:F3},{r0.c.Y:F3},{r0.c.Z:F3}); " +
                              $"texanim {(ta != null)} block {(col == 0 ? "Texture0" : col == 4 ? "Texture1" : "-")} track err {trackErr:E2}; states with no eye {zero}/{states.Count}, opaque {minN}..{maxN}");
        }
        rep["layers"] = lrep;
        if (layers.Count != 2) { ok = false; notes.Add("expected 2 eye layers, got " + layers.Count); }
        else
        {
            var a = Cover(0, 1, 1, 0, 0); var b = Cover(1, 1, 1, 0, 0);
            var mir = new Vector3(-b.c.X, b.c.Y, b.c.Z);
            float merr = (a.c - mir).Length();
            rep["mirror_error"] = merr; rep["eye_distance"] = (a.c - b.c).Length();
            Console.WriteLine($"both eyes: {a.n} + {b.n} opaque samples, centroids ({a.c.X:F3},{a.c.Y:F3},{a.c.Z:F3}) / ({b.c.X:F3},{b.c.Y:F3},{b.c.Z:F3}), mirror err {merr:F4}, apart {(a.c - b.c).Length():F3}");
            if (a.n == 0 || b.n == 0) { ok = false; notes.Add("an eye layer draws nothing at rest"); }
            if (Math.Sign(a.c.X) == Math.Sign(b.c.X)) { ok = false; notes.Add("both eye layers on the same side"); }
            if (merr > 0.1) { ok = false; notes.Add("eye centroids do not mirror across x = 0"); }
            foreach (dynamic l in lrep) if (l.track_max_err < 0 || l.track_max_err > 1e-3) { ok = false; notes.Add("texanim track error on " + l.map); }
        }
        rep["ok"] = ok; rep["notes"] = notes;
        if (reportPath != null) File.WriteAllText(reportPath, JsonSerializer.Serialize(rep, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine(ok ? "EYES OK" : "EYES FAIL: " + string.Join("; ", notes));
        return ok ? 0 : 2;
    }
}
