// efexport <ef_xxx.pac> <out.json> [common_ef.pac]
// Dumps a Brawl fighter effect archive for the Melee effect builder (build_efbm):
//   EFLS table, every effect MDL0 (bones with bind SRT, triangles in world bind space with the single-bind bone,
//   materials with blend / z / alpha test / TEV stage summary / texture refs), its CHR0 / VIS0 / SRT0 / CLR0 baked
//   per frame, TEX0 + REFT images decoded to RGBA (BrawlLib), and REFF emitter / particle parameters (reflection).
// Built with Windows' .NET Framework csc, x86, against BrawlLib.dll (32-bit).
using System;
using System.Collections;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using BrawlLib.Internal;
using BrawlLib.Imaging;
using BrawlLib.Modeling;
using BrawlLib.SSBB.ResourceNodes;
using BrawlLib.Wii.Animations;
using BrawlLib.Wii.Models;

class EfExport
{
    static CultureInfo IC = CultureInfo.InvariantCulture;
    static string F(float f) { if (float.IsNaN(f) || float.IsInfinity(f)) return "0"; return f.ToString("R", IC); }
    static string Esc(string s) { return s == null ? "null" : "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\""; }
    static unsafe string M(Matrix m) { var sb = new StringBuilder("["); float* p = (float*)&m; for (int i = 0; i < 16; i++) { if (i > 0) sb.Append(","); sb.Append(F(p[i])); } return sb.Append("]").ToString(); }
    static string V3(Vector3 v) { return "[" + F(v._x) + "," + F(v._y) + "," + F(v._z) + "]"; }
    static string V2(Vector2 v) { return "[" + F(v._x) + "," + F(v._y) + "]"; }
    static void Walk(ResourceNode n, List<ResourceNode> acc, Type t)
    {
        if (t.IsInstanceOfType(n)) acc.Add(n);
        List<ResourceNode> ch = null; try { ch = n.Children; } catch { }
        if (ch == null) return; foreach (var c in ch) Walk(c, acc, t);
    }
    static object GetF(object o, string name) { var f = o.GetType().GetField(name, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance); return f == null ? null : f.GetValue(o); }

    // every public instance property of a node (not ResourceNode's own), as a JSON object of strings/numbers
    static string Props(object o)
    {
        var sb = new StringBuilder("{"); bool first = true;
        foreach (var p in o.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance))
        {
            if (p.DeclaringType == typeof(ResourceNode) || p.GetIndexParameters().Length > 0) continue;
            object v; try { v = p.GetValue(o, null); } catch { continue; }
            if (v == null || v is ResourceNode || (v is ICollection && !(v is string))) continue;
            string s;
            if (v is float) s = F((float)v);
            else if (v is int || v is short || v is byte || v is uint || v is ushort || v is sbyte || v is long) s = Convert.ToString(v, IC);
            else if (v is bool) s = ((bool)v) ? "true" : "false";
            else s = Esc(v.ToString());
            if (!first) sb.Append(","); first = false;
            sb.Append(Esc(p.Name) + ":" + s);
        }
        return sb.Append("}").ToString();
    }

    static string ImageJson(string name, Bitmap bmp, string fmt)
    {
        int w = bmp.Width, h = bmp.Height;
        var data = new byte[w * h * 4];
        var bd = bmp.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        var row = new byte[w * 4];
        for (int y = 0; y < h; y++)
        {
            Marshal.Copy(bd.Scan0 + y * bd.Stride, row, 0, w * 4);
            for (int x = 0; x < w; x++)
            {   // BGRA -> RGBA
                data[(y * w + x) * 4 + 0] = row[x * 4 + 2]; data[(y * w + x) * 4 + 1] = row[x * 4 + 1];
                data[(y * w + x) * 4 + 2] = row[x * 4 + 0]; data[(y * w + x) * 4 + 3] = row[x * 4 + 3];
            }
        }
        bmp.UnlockBits(bd);
        return "{\"name\":" + Esc(name) + ",\"fmt\":" + Esc(fmt) + ",\"w\":" + w + ",\"h\":" + h + ",\"rgba\":\"" + Convert.ToBase64String(data) + "\"}";
    }

    static unsafe string Model(MDL0Node mdl, int brres)
    {
        var w = new StringBuilder();
        w.Append("{\"name\":" + Esc(mdl.Name) + ",\"brres\":" + brres + ",\n\"bones\":[");
        var bones = new List<ResourceNode>(); Walk(mdl, bones, typeof(MDL0BoneNode));
        for (int i = 0; i < bones.Count; i++)
        {
            var b = (MDL0BoneNode)bones[i];
            if (i > 0) w.Append(",");
            var bs = b.BindState;
            w.Append("\n{\"name\":" + Esc(b.Name) + ",\"parent\":" + ((b.Parent is MDL0BoneNode) ? Esc(b.Parent.Name) : "null") +
                ",\"s\":" + V3(bs._scale) + ",\"r\":" + V3(bs._rotate) + ",\"t\":" + V3(bs._translate) +
                ",\"billboard\":" + Esc(b.BillboardSetting.ToString()) + ",\"flags\":" + Esc(b.Flags.ToString()) +
                ",\"bind\":" + M(b.BindMatrix) + "}");
        }
        w.Append("],\n\"objects\":[");
        var objs = new List<ResourceNode>(); Walk(mdl, objs, typeof(MDL0ObjectNode));
        for (int oi = 0; oi < objs.Count; oi++)
        {
            var o = (MDL0ObjectNode)objs[oi];
            var pm = o._manager;
            string mat = null, vis = null, pass = null; int drawPriority = 0;
            foreach (DrawCall dc in o._drawCalls) { if (mat == null) { mat = dc.Material; vis = dc.VisibilityBone; pass = dc.DrawPass.ToString(); drawPriority = dc.DrawPriority; } }
            if (oi > 0) w.Append(",");
            string sb1 = null; try { sb1 = o.SingleBind; } catch { }
            w.Append("\n{\"name\":" + Esc(o.Name) + ",\"material\":" + Esc(mat) + ",\"visbone\":" + Esc(vis) + ",\"pass\":" + Esc(pass) +
                ",\"prio\":" + drawPriority + ",\"singlebind\":" + Esc(sb1) + ",\"has\":[");
            for (int k = 0; k < 12; k++) { if (k > 0) w.Append(","); w.Append(pm._faceData[k] != null ? "1" : "0"); }
            w.Append("],\"tris\":[");
            var tri = GetF(pm, "_triangles");
            uint[] idx = tri == null ? new uint[0] : (uint[])GetF(tri, "_indices");
            ushort* vmap = (ushort*)pm._indices.Address;
            for (int t = 0; t < idx.Length; t++)
            {
                int fp = (int)idx[t];
                var v = pm._vertices[vmap[fp]];
                IMatrixNode node = v.GetMatrixNode();
                Vector3 pos = v._position;
                Vector3 nrm = pm._faceData[1] != null ? ((Vector3*)pm._faceData[1].Address)[fp] : new Vector3(0, 1, 0);
                if (node is MDL0BoneNode)
                {
                    Matrix bm = ((MDL0BoneNode)node).BindMatrix;
                    pos = bm * pos;
                    Matrix r = bm.GetRotationMatrix();
                    nrm = r * nrm;
                }
                if (t > 0) w.Append(",");
                w.Append("[" + F(pos._x) + "," + F(pos._y) + "," + F(pos._z) + "," + F(nrm._x) + "," + F(nrm._y) + "," + F(nrm._z));
                for (int u = 4; u < 6; u++)
                {
                    if (pm._faceData[u] != null) { var uv = ((Vector2*)pm._faceData[u].Address)[fp]; w.Append("," + F(uv._x) + "," + F(uv._y)); }
                    else w.Append(",0,0");
                }
                if (pm._faceData[2] != null) { var c = ((RGBAPixel*)pm._faceData[2].Address)[fp]; w.Append("," + c.R + "," + c.G + "," + c.B + "," + c.A); }
                else w.Append(",255,255,255,255");
                w.Append(",[");
                if (node is MDL0BoneNode) w.Append("[" + Esc(((MDL0BoneNode)node).Name) + ",1]");
                else if (node != null)
                {
                    int k = 0;
                    foreach (BoneWeight bw in node.Weights) { if (k++ > 0) w.Append(","); w.Append("[" + Esc(((ResourceNode)bw.Bone).Name) + "," + F(bw.Weight) + "]"); }
                }
                w.Append("]]");
            }
            w.Append("]}");
        }
        w.Append("],\n\"materials\":[");
        var mats = new List<ResourceNode>(); Walk(mdl, mats, typeof(MDL0MaterialNode));
        for (int i = 0; i < mats.Count; i++)
        {
            var m = (MDL0MaterialNode)mats[i];
            if (i > 0) w.Append(",");
            w.Append("\n{\"name\":" + Esc(m.Name) + ",\"props\":" + Props(m) + ",\"stages\":[");
            int k = 0;
            var sh = m.ShaderNode;
            if (sh != null)
                foreach (var st in sh.Children) { if (k++ > 0) w.Append(","); w.Append(Props(st)); }
            w.Append("],\"refs\":[");
            k = 0;
            foreach (var c in m.Children)
            {
                var r = c as MDL0MaterialRefNode; if (r == null) continue;
                if (k++ > 0) w.Append(",");
                w.Append(Props(r));
            }
            w.Append("]}");
        }
        w.Append("]");
        return w.ToString();
    }

    static string Anims(ResourceNode brres, string mdlName)
    {
        var w = new StringBuilder();
        var chr = new List<ResourceNode>(); Walk(brres, chr, typeof(CHR0Node));
        var vis = new List<ResourceNode>(); Walk(brres, vis, typeof(VIS0Node));
        var srt = new List<ResourceNode>(); Walk(brres, srt, typeof(SRT0Node));
        var clr = new List<ResourceNode>(); Walk(brres, clr, typeof(CLR0Node));
        var pat = new List<ResourceNode>(); Walk(brres, pat, typeof(PAT0Node));
        var shp = new List<ResourceNode>(); Walk(brres, shp, typeof(SHP0Node));
        w.Append(",\n\"chr0\":[");
        for (int a = 0; a < chr.Count; a++)
        {
            var c = (CHR0Node)chr[a]; if (a > 0) w.Append(",");
            w.Append("{\"name\":" + Esc(c.Name) + ",\"frames\":" + c.FrameCount + ",\"loop\":" + (c.Loop ? "true" : "false") + ",\"bones\":{");
            int k = 0;
            foreach (var e0 in c.Children)
            {
                var e = e0 as CHR0EntryNode; if (e == null) continue;
                if (k++ > 0) w.Append(",");
                w.Append(Esc(e.Name) + ":[");
                for (int f = 0; f < c.FrameCount; f++)
                {
                    var fr = e.GetAnimFrame(f, false);
                    if (f > 0) w.Append(",");
                    w.Append("[" + F(fr.Scale._x) + "," + F(fr.Scale._y) + "," + F(fr.Scale._z) + "," + F(fr.Rotation._x) + "," + F(fr.Rotation._y) + "," + F(fr.Rotation._z) + "," +
                        F(fr.Translation._x) + "," + F(fr.Translation._y) + "," + F(fr.Translation._z) + "]");
                }
                w.Append("]");
            }
            w.Append("}}");
        }
        w.Append("],\n\"vis0\":[");
        for (int a = 0; a < vis.Count; a++)
        {
            var c = (VIS0Node)vis[a]; if (a > 0) w.Append(",");
            w.Append("{\"name\":" + Esc(c.Name) + ",\"frames\":" + c.FrameCount + ",\"loop\":" + (c.Loop ? "true" : "false") + ",\"bones\":{");
            int k = 0;
            foreach (var e0 in c.Children)
            {
                var e = e0 as VIS0EntryNode; if (e == null) continue;
                if (k++ > 0) w.Append(",");
                w.Append(Esc(e.Name) + ":\"");
                for (int f = 0; f < c.FrameCount; f++)
                {
                    bool on = e.Constant ? e.Enabled : e.GetEntry(f);
                    w.Append(on ? "1" : "0");
                }
                w.Append("\"");
            }
            w.Append("}}");
        }
        w.Append("],\n\"srt0\":[");
        for (int a = 0; a < srt.Count; a++)
        {
            var c = (SRT0Node)srt[a]; if (a > 0) w.Append(",");
            w.Append("{\"name\":" + Esc(c.Name) + ",\"frames\":" + c.FrameCount + ",\"loop\":" + (c.Loop ? "true" : "false") + ",\"mats\":{");
            int k = 0;
            foreach (var e0 in c.Children)
            {
                if (k++ > 0) w.Append(",");
                w.Append(Esc(e0.Name) + ":{");
                int kk = 0;
                foreach (var t0 in e0.Children)
                {
                    var t = t0 as SRT0TextureNode; if (t == null) continue;
                    if (kk++ > 0) w.Append(",");
                    w.Append("\"" + t.TextureIndex + (t.Indirect ? "i" : "") + "\":[");
                    for (int f = 0; f < c.FrameCount; f++)
                    {
                        var fr = t.GetAnimFrame(f);
                        if (f > 0) w.Append(",");
                        w.Append("[" + F(fr.Scale._x) + "," + F(fr.Scale._y) + "," + F(fr.Rotation) + "," + F(fr.Translation._x) + "," + F(fr.Translation._y) + "]");
                    }
                    w.Append("]");
                }
                w.Append("}");
            }
            w.Append("}}");
        }
        w.Append("],\n\"clr0\":[");
        for (int a = 0; a < clr.Count; a++)
        {
            var c = (CLR0Node)clr[a]; if (a > 0) w.Append(",");
            w.Append("{\"name\":" + Esc(c.Name) + ",\"frames\":" + c.FrameCount + ",\"loop\":" + (c.Loop ? "true" : "false") + ",\"mats\":{");
            int k = 0;
            foreach (var e0 in c.Children)
            {
                if (k++ > 0) w.Append(",");
                w.Append(Esc(e0.Name) + ":{");
                int kk = 0;
                foreach (var t0 in e0.Children)
                {
                    var t = t0 as CLR0MaterialEntryNode; if (t == null) continue;
                    if (kk++ > 0) w.Append(",");
                    w.Append(Esc(t.Target.ToString()) + ":{\"mask\":" + Esc(t.ColorMask.ToString()) + ",\"colors\":[");
                    for (int f = 0; f < c.FrameCount; f++)
                    {
                        ARGBPixel p = t.Constant ? t.SolidColor : t.GetColor(f, 0);
                        if (f > 0) w.Append(",");
                        w.Append("[" + p.R + "," + p.G + "," + p.B + "," + p.A + "]");
                    }
                    w.Append("]}");
                }
                w.Append("}");
            }
            w.Append("}}");
        }
        w.Append("],\"pat0\":" + pat.Count + ",\"shp0\":" + shp.Count + "}");
        return w.ToString();
    }

    static unsafe void Reff(ResourceNode root, StringBuilder w)
    {
        var ents = new List<ResourceNode>(); Walk(root, ents, typeof(REFFEntryNode));
        for (int i = 0; i < ents.Count; i++)
        {
            var e = ents[i]; if (i > 0) w.Append(",");
            w.Append("\n{\"name\":" + Esc(e.Name));
            foreach (var c in e.Children)
            {
                if (c.GetType().Name.StartsWith("REFFEmitter"))
                {
                    w.Append(",\"emitter\":" + Props(c) + ",\"tev\":[");
                    int k = 0; foreach (var s in c.Children) { if (k++ > 0) w.Append(","); w.Append(Props(s)); }
                    w.Append("]");
                }
                else if (c is REFFParticleNode) w.Append(",\"particle\":" + Props(c));
                else if (c is REFFAnimationListNode)
                {
                    w.Append(",\"anims\":[");
                    int k = 0;
                    foreach (var an in c.Children)
                    {
                        if (k++ > 0) w.Append(",");
                        // raw bytes of the curve, for the builder to decode keys
                        string raw = "";
                        try { var src = an.WorkingUncompressed; var b = new byte[src.Length]; Marshal.Copy((IntPtr)(void*)src.Address, b, 0, b.Length); raw = Convert.ToBase64String(b); } catch { }
                        w.Append("{\"props\":" + Props(an) + ",\"raw\":\"" + raw + "\"}");
                    }
                    w.Append("]");
                }
            }
            w.Append("}");
        }
    }

    static int Main(string[] args)
    {
        ResourceNode root = NodeFactory.FromFile(null, args[0]);
        var w = new StringBuilder("{\"file\":" + Esc(Path.GetFileName(args[0])) + ",\n\"efls\":[");
        var efls = new List<ResourceNode>(); Walk(root, efls, typeof(EFLSEntryNode));
        for (int i = 0; i < efls.Count; i++)
        {
            var e = (EFLSEntryNode)efls[i]; if (i > 0) w.Append(",");
            w.Append("{\"i\":" + i + ",\"name\":" + Esc(e.Name == "<null>" ? null : e.Name) + ",\"brres\":" + (e.UseBrres ? e.BrresId.ToString() : "null") + "}");
        }
        w.Append("],\n\"textures\":[");
        var texs = new List<ResourceNode>(); Walk(root, texs, typeof(TEX0Node));
        for (int i = 0; i < texs.Count; i++)
        {
            var t = (TEX0Node)texs[i]; if (i > 0) w.Append(",");
            w.Append("\n" + ImageJson(t.Name, t.GetImage(0), t.Format.ToString()));
        }
        w.Append("],\n\"reft\":[");
        var refts = new List<ResourceNode>(); Walk(root, refts, typeof(REFTEntryNode));
        if (args.Length > 2) { var r2 = NodeFactory.FromFile(null, args[2]); Walk(r2, refts, typeof(REFTEntryNode)); }
        for (int i = 0; i < refts.Count; i++)
        {
            var t = (REFTEntryNode)refts[i]; if (i > 0) w.Append(",");
            Bitmap b = null; try { b = t.GetImage(0); } catch { }
            if (b == null) { w.Append("{\"name\":" + Esc(t.Name) + ",\"w\":0}"); continue; }
            w.Append("\n" + ImageJson(t.Name, b, t.TextureFormat.ToString()));
        }
        w.Append("],\n\"models\":[");
        var brs = new List<ResourceNode>(); Walk(root, brs, typeof(BRRESNode));
        int n = 0, bi = -1;
        foreach (var br in brs)
        {
            var mdls = new List<ResourceNode>(); Walk(br, mdls, typeof(MDL0Node));
            if (br.Name.StartsWith("Model Data")) bi++;
            foreach (MDL0Node mdl in mdls)
            {
                if (n++ > 0) w.Append(",");
                w.Append("\n" + Model(mdl, bi) + Anims(br, mdl.Name));
            }
        }
        w.Append("],\n\"reff\":[");
        Reff(root, w);
        w.Append("]}\n");
        File.WriteAllText(args[1], w.ToString());
        Console.WriteLine("efls " + efls.Count + " textures " + texs.Count + " reft " + refts.Count + " models " + n);
        return 0;
    }
}
