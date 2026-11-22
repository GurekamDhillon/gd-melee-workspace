using System.Text.Json;
using HSDRaw;
using HSDRaw.Common;
using HSDRaw.GX;
using HSDRaw.Tools;

// costumebuild: write a Melee costume file that keeps a retail costume's joint tree untouched and replaces
// only DObj meshes / textures, per a skin.json made by ports/skin/skin.py.
//
//   costumebuild build   <retail.dat> <skin.json> <out.dat> [report.json]
//   costumebuild inspect <costume.dat> <out.json>          joints (depth-first), DObjs (global order), skinned verts
//   costumebuild synth   <out.dat>                         a small made-up costume for the synthetic tests
//
// Rules: the JObj structs (flags, SRT, inverse binds, order, hierarchy) are never written to; DObj count and global
// order stay as retail (the part/visibility tables index DObjs by that order). A replaced DObj keeps its retail MObj
// (render flags, TEV, the TObj chain the matanim addresses); only TObj images change. A "blank" DObj gets one
// zero-area triangle so its slot still exists.
static class P
{
    static int Main(string[] a)
    {
        try
        {
            switch (a[0])
            {
                case "build": return Build(a[1], a[2], a[3], a.Length > 4 ? a[4] : null);
                case "inspect": return Inspect(a[1], a[2]);
                case "synth": return Synth(a[1]);
                case "tobjs": return Tobjs(a[1]);
            }
            Console.Error.WriteLine("usage: costumebuild build|inspect|synth ...");
            return 2;
        }
        catch (Exception e) { Console.Error.WriteLine(e); return 1; }
    }

    public static List<HSD_JOBJ> Joints(HSD_JOBJ root)
    {
        var l = new List<HSD_JOBJ>();
        void W(HSD_JOBJ j) { for (; j != null; j = j.Next) { l.Add(j); if (j.Child != null && !j.Flags.HasFlag(JOBJ_FLAG.INSTANCE)) W(j.Child); } }
        W(root);
        return l;
    }

    public static List<(HSD_DOBJ d, int joint)> Dobjs(List<HSD_JOBJ> js)
    {
        var l = new List<(HSD_DOBJ, int)>();
        for (int i = 0; i < js.Count; i++)
            if (js[i].Dobj != null && !js[i].Flags.HasFlag(JOBJ_FLAG.SPLINE) && !js[i].Flags.HasFlag(JOBJ_FLAG.PTCL))
                foreach (var d in js[i].Dobj.List) l.Add((d, i));
        return l;
    }

    static float[] F(JsonElement e) => e.EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();

    static GXTexFmt Fmt(string s) => Enum.Parse<GXTexFmt>(s == "CMPR" ? "CMP" : s);
    static GXTlutFmt Tlut(string s) => s switch { "RGB5A3" => GXTlutFmt.RGB5A3, "RGB565" => GXTlutFmt.RGB565, _ => GXTlutFmt.IA8 };

    // Native GX texture from a skin.json texture record. CI4/CI8 keep their palette (TLUT) as-is; anything larger than
    // max is box-downscaled and re-encoded (CMPR when fully opaque, RGB5A3 otherwise; CI8 kept CI8).
    static (HSD_Image, HSD_Tlut, object) Tex(JsonElement t, int max)
    {
        var fmt = Fmt(t.GetProperty("fmt").GetString());
        int w = t.GetProperty("w").GetInt32(), h = t.GetProperty("h").GetInt32();
        var raw = Convert.FromBase64String(t.GetProperty("data").GetString());
        byte[] pal = null; GXTlutFmt pf = GXTlutFmt.RGB5A3; int pc = fmt == GXTexFmt.CI4 ? 16 : 256;
        if (t.TryGetProperty("palette", out var pe) && pe.ValueKind == JsonValueKind.String)
        {
            pal = Convert.FromBase64String(pe.GetString());
            pf = Tlut(t.GetProperty("palette_fmt").GetString());
            pal = pal.Take(pc * 2).Concat(new byte[Math.Max(0, pc * 2 - pal.Length)]).ToArray();
        }
        bool ci = fmt == GXTexFmt.CI4 || fmt == GXTexFmt.CI8;
        if (ci && pal == null) throw new Exception("palette texture without a palette: " + t.GetProperty("name").GetString());
        int need = GXImageConverter.GetImageSize(fmt, w, h);
        if (raw.Length < need) throw new Exception($"texture {t.GetProperty("name").GetString()}: {raw.Length} bytes < {need}");
        raw = raw.Take(need).ToArray();
        string note = "kept";
        if (w > max || h > max)
        {
            var bgra = ci ? GXImageConverter.DecodeTPL(fmt, w, h, raw, pf, pc, pal) : GXImageConverter.DecodeTPL(fmt, w, h, raw);
            int f = 1; while (w / f > max || h / f > max) f *= 2;
            int nw = w / f, nh = h / f; var o = new byte[nw * nh * 4]; bool opaque = true;
            for (int y = 0; y < nh; y++) for (int x = 0; x < nw; x++) for (int c = 0; c < 4; c++)
                    {
                        int s = 0; for (int dy = 0; dy < f; dy++) for (int dx = 0; dx < f; dx++) s += bgra[((y * f + dy) * w + x * f + dx) * 4 + c];
                        o[(y * nw + x) * 4 + c] = (byte)(s / (f * f)); if (c == 3 && o[(y * nw + x) * 4 + 3] != 255) opaque = false;
                    }
            var nf = ci ? GXTexFmt.CI8 : opaque ? GXTexFmt.CMP : GXTexFmt.RGB5A3;
            raw = GXImageConverter.EncodeImage(o, nw, nh, nf, GXTlutFmt.RGB5A3, out var npal);
            if (ci) { pal = npal.Concat(new byte[Math.Max(0, 512 - npal.Length)]).Take(512).ToArray(); pf = GXTlutFmt.RGB5A3; pc = 256; }
            note = $"downscaled {w}x{h}->{nw}x{nh} {nf}"; fmt = nf; w = nw; h = nh;
        }
        var img = new HSD_Image { ImageData = raw, Width = (short)w, Height = (short)h, Format = fmt };
        var tl = ci ? new HSD_Tlut { TlutData = pal, Format = pf, GXTlut = 0, ColorCount = (short)pc } : null;
        return (img, tl, new { name = t.GetProperty("name").GetString(), fmt = fmt.ToString(), w, h, bytes = raw.Length + (pal?.Length ?? 0), note });
    }

    static int Build(string retail, string skinPath, string outPath, string reportPath)
    {
        var skin = JsonDocument.Parse(File.ReadAllText(skinPath)).RootElement;
        var f = new HSDRawFile(retail);
        var root = f.Roots.First(r => r.Name.EndsWith("_Share_joint")).Data as HSD_JOBJ;
        var js = Joints(root); var ds = Dobjs(js);
        int maxTex = skin.TryGetProperty("max_texture", out var mt) ? mt.GetInt32() : 256;
        if (skin.GetProperty("retail_joints").GetInt32() != js.Count) throw new Exception($"skin.json made for {skin.GetProperty("retail_joints").GetInt32()} joints, retail has {js.Count}");
        if (skin.GetProperty("retail_dobjs").GetInt32() != ds.Count) throw new Exception($"skin.json made for {skin.GetProperty("retail_dobjs").GetInt32()} DObjs, retail has {ds.Count}");

        var texs = new Dictionary<string, (HSD_Image, HSD_Tlut)>(); var texRep = new List<object>();
        foreach (var t in skin.GetProperty("textures").EnumerateArray())
        {
            var (im, tl, r) = Tex(t, maxTex); texs[t.GetProperty("name").GetString()] = (im, tl); texRep.Add(r);
        }
        var gen = new POBJ_Generator { UseTriangleStrips = true };
        var rep = new List<object>(); int tris = 0; HSD_Image blankImg = null;
        foreach (var e in skin.GetProperty("dobjs").EnumerateArray())
        {
            int di = e.GetProperty("dobj").GetInt32(); var (d, ji) = ds[di];
            string mode = e.GetProperty("mode").GetString();
            if (mode == "keep") { rep.Add(new { dobj = di, mode }); continue; }
            var verts = new List<GX_Vertex>(); var bones = new List<HSD_JOBJ[]>(); var wts = new List<float[]>();
            int nuv = 1;
            if (mode == "blank")
            {
                for (int k = 0; k < 3; k++) { verts.Add(new GX_Vertex { POS = new GXVector3(0, 0, 0), NRM = new GXVector3(0, 1, 0), TEX0 = new GXVector2(0, 0) }); bones.Add(new[] { js[ji] }); wts.Add(new[] { 1f }); }
                // a blank slot is never drawn: its retail images are dead weight in the file (the eye matanim brings its own)
                blankImg ??= new HSD_Image { ImageData = new byte[32], Width = 8, Height = 8, Format = GXTexFmt.CMP };
                for (var t = d.Mobj?.Textures; t != null; t = t.Next) { t.ImageData = blankImg; t.TlutData = null; }
            }
            else
            {
                foreach (var tri in e.GetProperty("tris").EnumerateArray())
                    // winding: SKIN_REVERSE=1 restores the old reversal (it turned real Brawl meshes inside out: cull back
                    // then removed the near faces, so arms, legs, torso and face showed their insides)
                    foreach (var v in (Environment.GetEnvironmentVariable("SKIN_REVERSE") == "1" ? tri.EnumerateArray().Reverse() : tri.EnumerateArray()))
                    {
                        var p = F(v.GetProperty("p")); var n = F(v.GetProperty("n"));
                        var uvs = v.GetProperty("uvs").EnumerateArray().Select(F).ToList(); nuv = Math.Max(1, uvs.Count);
                        var gv = new GX_Vertex { POS = new GXVector3(p[0], p[1], p[2]), NRM = new GXVector3(n[0], n[1], n[2]) };
                        if (uvs.Count > 0) gv.TEX0 = new GXVector2(uvs[0][0], uvs[0][1]);
                        if (uvs.Count > 1) gv.TEX1 = new GXVector2(uvs[1][0], uvs[1][1]);
                        verts.Add(gv);
                        var w = v.GetProperty("w").EnumerateArray().ToList();
                        bones.Add(w.Select(x => js[x[0].GetInt32()]).ToArray()); wts.Add(w.Select(x => (float)x[1].GetDouble()).ToArray());
                    }
                tris += verts.Count / 3;
            }
            var attrs = new List<GXAttribName> { GXAttribName.GX_VA_PNMTXIDX, GXAttribName.GX_VA_POS, GXAttribName.GX_VA_NRM, GXAttribName.GX_VA_TEX0 };
            if (nuv > 1) attrs.Add(GXAttribName.GX_VA_TEX1);
            string cull = e.TryGetProperty("cull", out var cu) ? cu.GetString() : "back";
            gen.CullMode = cull == "none" ? GenCullMode.None : cull == "front" ? GenCullMode.Front : GenCullMode.Back;
            d.Pobj = gen.CreatePOBJsFromTriangleList(verts, attrs.ToArray(), bones, wts);

            // textures into the retail TObj chain (null = keep retail's image)
            var tob = new List<HSD_TOBJ>(); for (var t = d.Mobj?.Textures; t != null; t = t.Next) tob.Add(t);
            if (e.TryGetProperty("textures", out var tl))
            {
                int k = 0;
                foreach (var tn in tl.EnumerateArray())
                {
                    if (k >= tob.Count) throw new Exception($"DObj {di}: {tl.GetArrayLength()} textures, retail MObj has {tob.Count} TObjs");
                    if (tn.ValueKind == JsonValueKind.String)
                    {
                        var (im, tlut) = texs[tn.GetString()];
                        tob[k].ImageData = im; tob[k].TlutData = tlut;
                        // the retail TObj's UV transform and CLAMP wrap were made for retail's UVs, not the source's
                        tob[k].SX = tob[k].SY = tob[k].SZ = 1; tob[k].RX = tob[k].RY = tob[k].RZ = 0; tob[k].TX = tob[k].TY = tob[k].TZ = 0;
                        tob[k].RepeatS = tob[k].RepeatT = 1;
                        if (e.TryGetProperty("wraps", out var wr) && wr.GetArrayLength() > k && wr[k].ValueKind == JsonValueKind.Array)
                        {
                            GXWrapMode W(string m) => m == "clamp" ? GXWrapMode.CLAMP : m == "mirror" ? GXWrapMode.MIRROR : GXWrapMode.REPEAT;
                            tob[k].WrapS = W(wr[k][0].GetString()); tob[k].WrapT = W(wr[k][1].GetString());
                        }
                    }
                    k++;
                }
            }
            if (e.TryGetProperty("alpha_test", out var at) && at.GetBoolean() && d.Mobj != null)
            {
                // alpha-compare cutout (Brawl's alpha test): pass when alpha > 128, depth written, no blending
                d.Mobj.PEDesc = new HSD_PEDesc
                {
                    Flags = PIXEL_PROCESS_ENABLE.COLOR_UPDATE | PIXEL_PROCESS_ENABLE.ALPHA_UPDATE | PIXEL_PROCESS_ENABLE.ZUPDATE | PIXEL_PROCESS_ENABLE.COMPARE,
                    AlphaRef0 = 128, AlphaRef1 = 128, BlendMode = GXBlendMode.GX_NONE, SrcFactor = GXBlendFactor.GX_BL_ONE, DstFactor = GXBlendFactor.GX_BL_ZERO,
                    BlendOp = GXLogicOp.GX_LO_COPY, DepthFunction = GXCompareType.LEqual, AlphaComp0 = GXCompareType.Greater, AlphaOp = GXAlphaOp.And, AlphaComp1 = GXCompareType.Always,
                };
                d.Mobj.RenderFlags |= RENDER_MODE.XLU;
            }
            rep.Add(new { dobj = di, mode, joint = ji, tris = mode == "blank" ? 0 : verts.Count / 3 });
        }
        gen.SaveChanges();
        f.Save(outPath);
        var size = new FileInfo(outPath).Length;
        var report = new { retail_bytes = new FileInfo(retail).Length, out_bytes = size, joints = js.Count, dobjs = ds.Count, tris_new = tris, textures = texRep, per_dobj = rep };
        var json = JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true });
        if (reportPath != null) File.WriteAllText(reportPath, json); else Console.WriteLine(json);
        return 0;
    }

    // per DObj: each TObj's texture transform, wrap, repeat, coord source and flags (what a swapped image inherits)
    static int Tobjs(string path)
    {
        var f = new HSDRawFile(path);
        var root = f.Roots.First(r => r.Name.EndsWith("_Share_joint")).Data as HSD_JOBJ;
        var ds = Dobjs(Joints(root)); int i = 0;
        foreach (var (d, j) in ds)
        {
            int k = 0;
            for (var t = d.Mobj?.Textures; t != null; t = t.Next, k++)
                Console.WriteLine($"dobj {i} tobj {k} S=({t.SX},{t.SY},{t.SZ}) R=({t.RX},{t.RY},{t.RZ}) T=({t.TX},{t.TY},{t.TZ}) wrap={t.WrapS}/{t.WrapT} rep={t.RepeatS}/{t.RepeatT} src={t.GXTexGenSrc} flags={t.Flags} img={t.ImageData?.Width}x{t.ImageData?.Height} {t.ImageData?.Format} mobjflags={d.Mobj.RenderFlags} dif={d.Mobj.Material?.DiffuseColor} amb={d.Mobj.Material?.AmbientColor} spc={d.Mobj.Material?.SpecularColor} tev={(t.TEV != null ? $"{t.TEV.color_op} {t.TEV.color_a_in}/{t.TEV.color_b_in}/{t.TEV.color_c_in}/{t.TEV.color_d_in} k={t.TEV.constant} t0={t.TEV.tev0} t1={t.TEV.tev1}" : "none")} blend={t.Blending} aop={t.AlphaOperation} cop={t.ColorOperation}");
            i++;
        }
        return 0;
    }

    static int Inspect(string path, string outPath)
    {
        var f = new HSDRawFile(path);
        var root = f.Roots.First(r => r.Name.EndsWith("_Share_joint")).Data as HSD_JOBJ;
        var js = Joints(root); var ds = Dobjs(js);
        var jo = js.Select((j, i) => new { i, flags = (uint)j.Flags, s = new[] { j.SX, j.SY, j.SZ }, r = new[] { j.RX, j.RY, j.RZ }, t = new[] { j.TX, j.TY, j.TZ } }).ToList();
        int tris = 0; var dl = new List<object>(); var texs = new List<object>();
        foreach (var (d, ji) in ds)
        {
            var vs = new List<object>(); int tri = 0;
            for (var p = d.Pobj; p != null; p = p.Next)
            {
                var list = p.ToDisplayList();
                var env = p.EnvelopeWeights;
                foreach (var prim in list.Primitives)
                {
                    int n = prim.Count;
                    tri += prim.PrimitiveType == GXPrimitiveType.Triangles ? n / 3 : prim.PrimitiveType == GXPrimitiveType.TriangleStrip ? Math.Max(0, n - 2) : 0;
                }
                foreach (var v in GX_VertexAccessor.GetDecodedVertices(list, p))
                {
                    object w;
                    if (env != null) { var en = env[v.PNMTXIDX / 3]; w = Enumerable.Range(0, en.EnvelopeCount).Select(k => new object[] { js.IndexOf(en.JOBJs[k]), en.Weights[k] }).ToArray(); }
                    else if (p.SingleBoundJOBJ != null) w = new[] { new object[] { js.IndexOf(p.SingleBoundJOBJ), 1f } };
                    else w = new[] { new object[] { ji, 1f } };
                    vs.Add(new { p = new[] { v.POS.X, v.POS.Y, v.POS.Z }, w });
                }
            }
            tris += tri;
            for (var t = d.Mobj?.Textures; t != null; t = t.Next) if (t.ImageData != null) texs.Add(new { fmt = t.ImageData.Format.ToString(), w = (int)t.ImageData.Width, h = (int)t.ImageData.Height });
            dl.Add(new { joint = ji, tris = tri, alpha_test = d.Mobj?.PEDesc != null && d.Mobj.PEDesc.AlphaComp0 == GXCompareType.Greater, verts = vs });
        }
        File.WriteAllText(outPath, JsonSerializer.Serialize(new { publics = f.Roots.Select(r => r.Name).ToArray(), joints = jo, dobjs = dl, tris, textures = texs, bytes = new FileInfo(path).Length }));
        return 0;
    }

    // A made-up 6-joint costume (root, hip, spine, arm.L, arm.R, head) with 3 DObjs, one textured MObj, one IBM per
    // skinned joint. Original test data: no game file is read.
    static int Synth(string outPath)
    {
        var J = new HSD_JOBJ[6];
        float[][] t = { new[] { 0f, 0, 0 }, new[] { 0f, 1, 0 }, new[] { 0f, 1, 0 }, new[] { 0.5f, 0.5f, 0 }, new[] { -0.5f, 0.5f, 0 }, new[] { 0f, 0.7f, 0 } };
        int[] par = { -1, 0, 1, 2, 2, 2 };
        var world = new System.Numerics.Matrix4x4[6];
        for (int i = 0; i < 6; i++)
        {
            J[i] = new HSD_JOBJ { SX = 1, SY = 1, SZ = 1, TX = t[i][0], TY = t[i][1], TZ = t[i][2], RZ = i == 3 ? -0.3f : 0, Flags = JOBJ_FLAG.CLASSICAL_SCALING };
            var local = System.Numerics.Matrix4x4.CreateRotationZ(J[i].RZ) * System.Numerics.Matrix4x4.CreateTranslation(t[i][0], t[i][1], t[i][2]);
            world[i] = par[i] < 0 ? local : local * world[par[i]];
            if (i > 0)
            {
                System.Numerics.Matrix4x4.Invert(world[i], out var inv);
                J[i].InverseWorldTransform = new HSD_Matrix4x3 { M11 = inv.M11, M12 = inv.M21, M13 = inv.M31, M14 = inv.M41, M21 = inv.M12, M22 = inv.M22, M23 = inv.M32, M24 = inv.M42, M31 = inv.M13, M32 = inv.M23, M33 = inv.M33, M34 = inv.M43 };
                J[i].Flags |= JOBJ_FLAG.SKELETON;
                J[par[i]].AddChild(J[i]);
            }
        }
        J[0].Flags |= JOBJ_FLAG.SKELETON_ROOT | JOBJ_FLAG.ENVELOPE_MODEL;
        var gen = new POBJ_Generator();
        var bgra = new byte[8 * 8 * 4]; for (int i = 0; i < bgra.Length; i++) bgra[i] = (byte)(i * 7);
        HSD_DOBJ Box(int joint, float y)
        {
            var vs = new List<GX_Vertex>(); var b = new List<HSD_JOBJ[]>(); var w = new List<float[]>();
            foreach (var (x, z) in new[] { (0f, 0f), (0.1f, 0f), (0f, 0.1f) }) { vs.Add(new GX_Vertex { POS = new GXVector3(x, y, z), NRM = new GXVector3(0, 0, 1), TEX0 = new GXVector2(x, z) }); b.Add(new[] { J[joint] }); w.Add(new[] { 1f }); }
            var img = GXImageConverter.EncodeImage(bgra, 8, 8, GXTexFmt.RGB5A3, GXTlutFmt.RGB5A3, out _);
            var m = new HSD_MOBJ { RenderFlags = RENDER_MODE.DIFFUSE | RENDER_MODE.TEX0, Material = new HSD_Material { DiffuseColor = System.Drawing.Color.White, AmbientColor = System.Drawing.Color.Gray, SpecularColor = System.Drawing.Color.White, Alpha = 1, Shininess = 50 },
                Textures = new HSD_TOBJ { ImageData = new HSD_Image { ImageData = img, Width = 8, Height = 8, Format = GXTexFmt.RGB5A3 }, Flags = TOBJ_FLAGS.COORD_UV | TOBJ_FLAGS.LIGHTMAP_DIFFUSE | TOBJ_FLAGS.COLORMAP_MODULATE, GXTexGenSrc = GXTexGenSrc.GX_TG_TEX0, TexMapID = GXTexMapID.GX_TEXMAP0, WrapS = GXWrapMode.REPEAT, WrapT = GXWrapMode.REPEAT, RepeatS = 1, RepeatT = 1, SX = 1, SY = 1, SZ = 1, MagFilter = GXTexFilter.GX_LINEAR } };
            return new HSD_DOBJ { Mobj = m, Pobj = gen.CreatePOBJsFromTriangleList(vs, new[] { GXAttribName.GX_VA_PNMTXIDX, GXAttribName.GX_VA_POS, GXAttribName.GX_VA_NRM, GXAttribName.GX_VA_TEX0 }, b, w) };
        }
        var d0 = Box(1, 1); d0.Next = Box(2, 2); d0.Next.Next = Box(5, 3);       // body, hand-swap stand-in, head
        J[0].Dobj = d0;
        gen.SaveChanges();
        var f = new HSDRawFile(); f.Roots.Add(new HSDRootNode { Name = "PlySynth5K_Share_joint", Data = J[0] });
        f.Save(outPath);
        return 0;
    }
}
