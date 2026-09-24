using System.Text.Json;
using HSDRaw;
using HSDRaw.Common;
using HSDRaw.Common.Animation;
using HSDRaw.GX;
using HSDRaw.Tools;
using HSDRaw.Tools.Textures;

// mkbuild build <mesh.json> <FitMetaknightNN.json> <out.dat> [template PlKbNr.dat] [report.json]
// A NEW Melee costume file for Meta Knight on his own joint tree (mesh.py / skeleton.py):
//  - joints: rest SRT from Brawl, CLASSICAL_SCALING (Brawl 'Standard' scaling), inverse binds = inverse(HSD FK)
//  - one DObj per Brawl object (mesh.py order), all on the root joint, envelope-skinned PObjs
//    (single-weight vertices are stored joint-local, as HSD draws them with the joint matrix only)
//  - winding reversed (BrawlLib triangle lists vs POBJ_Generator + HSD cull flags; the Kirby port's
//    grey-model bug) and CULLFRONT for Brawl 'Cull_Inside', no cull for 'Cull_None'
//  - materials: vanilla Kirby's skin MObj cloned per material, every Brawl layer (see the DObj section); CI8 eye
//    texture keeps its RGB5A3 palette; 'nuki' is XLU (alpha blend)
// Public symbols: PlyMetaknight5K_Share_joint, PlyMetaknight5K_Share_matanim_joint (the eye state texanims, see BuildMatAnim).
static class Build
{
    public const string JointSym = "PlyMetaknight5K_Share_joint";
    public const string MatAnimSym = "PlyMetaknight5K_Share_matanim_joint";

    static HSD_MatAnimJoint BuildMatAnim(HSD_JOBJ j, int ndobj, int eyeDobj, List<(GXTexMapID id, int col)> eyeMaps, List<float[]> states)
    {
        HSD_TexAnim EyeAnim(GXTexMapID id, int col)
        {
            // frame k = state k: SCAU, SCAV, TRAU, TRAV = states[k][col..col+3]; linear keys at every integer frame, so a
            // SetTexAnim frame reads exactly its state whichever side of a key the AObj evaluator lands on
            var ao = new HSD_AOBJ { Flags = 0, EndFrame = states.Count };
            HSD_FOBJDesc prev = null;
            foreach (var (tt, k) in new[] { (TexTrackType.HSD_A_T_SCAU, 0), (TexTrackType.HSD_A_T_SCAV, 1), (TexTrackType.HSD_A_T_TRAU, 2), (TexTrackType.HSD_A_T_TRAV, 3) })
            {
                var keys = new List<FOBJKey>();
                for (int s = 0; s < states.Count; s++) keys.Add(new FOBJKey { Frame = s, Value = states[s][col + k], InterpolationType = GXInterpolationType.HSD_A_OP_LIN });
                var fd = new HSD_FOBJDesc(); fd.SetKeys(keys, (byte)tt, 0.00002f);
                if (prev == null) ao.FObjDesc = fd; else prev.Next = fd;
                prev = fd;
            }
            return new HSD_TexAnim { GXTexMapID = id, AnimationObject = ao };
        }
        HSD_MatAnimJoint Node(HSD_JOBJ jo, bool isRoot)
        {
            var n = new HSD_MatAnimJoint();
            if (isRoot)
            {
                HSD_MatAnim first = null, prev = null;
                for (int i = 0; i < ndobj; i++)
                {
                    var ma = new HSD_MatAnim();
                    if (i == eyeDobj)
                    {
                        HSD_TexAnim tp = null;
                        foreach (var (id, col) in eyeMaps)
                        {
                            var ta = EyeAnim(id, col);
                            if (tp == null) ma.TextureAnimation = ta; else tp.Next = ta;
                            tp = ta;
                        }
                    }
                    if (prev == null) first = ma; else prev.Next = ma;
                    prev = ma;
                }
                n.MaterialAnimation = first;
            }
            if (jo.Child != null) n.Child = Chain(jo.Child);
            return n;
        }
        HSD_MatAnimJoint Chain(HSD_JOBJ jo)
        {
            HSD_MatAnimJoint head = null, prev = null;
            for (var c = jo; c != null; c = c.Next) { var n = Node(c, false); if (prev == null) head = n; else prev.Next = n; prev = n; }
            return head;
        }
        return Node(j, true);
    }

    // A Brawl sphere map with the material's TEV factor on it (per channel), re-encoded RGB565 for the Melee ADD layer.
    static HSD_Image PremultSphere(HSD_Image src, float[] k)
    {
        var bgra = GXImageConverter.DecodeTPL(src.Format, src.Width, src.Height, src.ImageData);
        for (int i = 0; i < bgra.Length; i += 4)
        {
            bgra[i + 0] = (byte)Math.Clamp((int)MathF.Round(bgra[i + 0] * k[2]), 0, 255);
            bgra[i + 1] = (byte)Math.Clamp((int)MathF.Round(bgra[i + 1] * k[1]), 0, 255);
            bgra[i + 2] = (byte)Math.Clamp((int)MathF.Round(bgra[i + 2] * k[0]), 0, 255);
            bgra[i + 3] = 255;
        }
        var enc = GXImageConverter.EncodeImage(bgra, src.Width, src.Height, GXTexFmt.RGB565, GXTlutFmt.RGB565, out _);
        return new HSD_Image { ImageData = enc, Width = src.Width, Height = src.Height, Format = GXTexFmt.RGB565 };
    }

    static int ImgBytes(GXTexFmt f, int w, int h)
    {
        int bw, bh, bpp;
        switch (f)
        {
            case GXTexFmt.I4: case GXTexFmt.CI4: case GXTexFmt.CMP: bw = 8; bh = 8; bpp = 4; break;
            case GXTexFmt.I8: case GXTexFmt.IA4: case GXTexFmt.CI8: bw = 8; bh = 4; bpp = 8; break;
            case GXTexFmt.RGBA8: bw = 4; bh = 4; bpp = 32; break;
            default: bw = 4; bh = 4; bpp = 16; break;
        }
        return ((w + bw - 1) / bw * bw) * ((h + bh - 1) / bh * bh) * bpp / 8;
    }

    static GXWrapMode Wrap(string s) => s == "Clamp" ? GXWrapMode.CLAMP : s == "Mirror" ? GXWrapMode.MIRROR : GXWrapMode.REPEAT;

    public static int Run(string meshPath, string brawlPath, string outPath, string templatePath = null, string reportPath = null)
    {
        var mesh = JsonDocument.Parse(File.ReadAllText(meshPath)).RootElement;
        var brawl = JsonDocument.Parse(File.ReadAllText(brawlPath)).RootElement;
        templatePath ??= Path.Combine(Path.GetDirectoryName(Path.GetFullPath(meshPath)), "vanilla", "PlKbNr.dat");
        var tf = new HSDRawFile(templatePath);
        var tRoot = tf.Roots.First(r => r.Name.EndsWith("_Share_joint")).Data as HSD_JOBJ;
        var tMobj = tRoot.Dobj.List[3].Mobj;          // Kirby skin: DIFFUSE|SPECULAR|TEX0, CI8+TLUT, TEV
        var report = new Dictionary<string, object>();

        // ---- joints ---------------------------------------------------------------------------------
        var jl = mesh.GetProperty("joints").EnumerateArray().ToList();
        var jobjs = new List<HSD_JOBJ>();
        foreach (var j in jl)
        {
            var s = j.GetProperty("scale").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
            var r = j.GetProperty("rot").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
            var t = j.GetProperty("trans").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
            var ib = j.GetProperty("ibm").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
            var jo = new HSD_JOBJ
            {
                SX = s[0], SY = s[1], SZ = s[2], RX = r[0], RY = r[1], RZ = r[2], TX = t[0], TY = t[1], TZ = t[2],
                Flags = JOBJ_FLAG.CLASSICAL_SCALING,
            };
            jo.InverseWorldTransform = new HSD_Matrix4x3
            {
                M11 = ib[0], M12 = ib[1], M13 = ib[2], M14 = ib[3],
                M21 = ib[4], M22 = ib[5], M23 = ib[6], M24 = ib[7],
                M31 = ib[8], M32 = ib[9], M33 = ib[10], M34 = ib[11],
            };
            jobjs.Add(jo);
        }
        for (int i = 0; i < jl.Count; i++)
        {
            int p = jl[i].GetProperty("parent").GetInt32();
            if (p >= 0) jobjs[p].AddChild(jobjs[i]);
        }
        var root = jobjs[0];
        root.InverseWorldTransform = null;                 // no vertex is weighted to TopN (vanilla roots carry no IBM either)

        // ---- textures (raw GX bytes carry over) -------------------------------------------------------
        var images = new Dictionary<string, (HSD_Image img, HSD_Tlut tlut)>();
        foreach (var t in brawl.GetProperty("textures").EnumerateArray())
        {
            var fmt = P.Fmt(t.GetProperty("fmt").GetString());
            int w = t.GetProperty("w").GetInt32(), h = t.GetProperty("h").GetInt32();
            var raw = Convert.FromBase64String(t.GetProperty("data").GetString());
            var img = new HSD_Image { ImageData = raw.Take(ImgBytes(fmt, w, h)).ToArray(), Width = (short)w, Height = (short)h, Format = fmt };
            HSD_Tlut tl = null;
            if (t.TryGetProperty("palette", out var pal))
            {
                var pd = Convert.FromBase64String(pal.GetString());
                var pf = t.GetProperty("palette_fmt").GetString() switch { "RGB5A3" => GXTlutFmt.RGB5A3, "RGB565" => GXTlutFmt.RGB565, _ => GXTlutFmt.IA8 };
                int n = fmt == GXTexFmt.CI4 ? 16 : 256;
                tl = new HSD_Tlut { TlutData = pd.Take(n * 2).Concat(new byte[Math.Max(0, n * 2 - pd.Length)]).ToArray(), Format = pf, GXTlut = 0, ColorCount = (short)n };
            }
            images[t.GetProperty("name").GetString()] = (img, tl);
        }

        // ---- DObjs --------------------------------------------------------------------------------------
        // Material layers follow the Brawl material (mesh.py 'textures' / 'coords' / 'maps', BRAWL_MAT 'lit' / 'spec' / 'env'):
        //  - TexCoord layers in Brawl's TEV order (the highest TexCoord first: medama = body on TexCoord2, then the eye on
        //    TexCoord1, then the eye on TexCoord0). The first is Kirby's skin TObj (REPLACE + its TEV); the next ones are
        //    COLORMAP_ALPHA_MASK layers (Yoshi's eye DObjs: CI8 eye over the skin, blended by the texture's alpha), each on
        //    its own vertex UV set (TEX0.. in that order). This is the eye fix: Brawl draws each eye from a different UV set
        //    (one per island, the other set lands on the texture's transparent border), the old build kept TexCoord0 only.
        //  - EnvCamera (sphere map) layers: COORD_REFLECTION TObjs (tobj.c: GX_TG_NRM through the reflection matrix, as the
        //    vanilla fighters' shine layers), COLORMAP_ADD into the diffuse term, the Brawl TEV factor baked into the texture.
        //  - lighting: Brawl C1ColorEnabled false -> RENDER_CONSTANT (unlit, white diffuse); specular only where Brawl's
        //    channel 1 is a specular channel ('mask', its colour); Kirby's lit ambient/diffuse otherwise.
        var gen = new POBJ_Generator { UseTriangleStrips = true };
        var ibm = jobjs.Select(j => j.InverseWorldTransform).ToList();
        bool flip = Environment.GetEnvironmentVariable("MK_FLIP") != "0";
        var dlist = new List<HSD_DOBJ>(); var per = new List<object>(); var firstTobj = new List<int>();
        int tobjIndex = 0; var eyeTobj = new Dictionary<string, int>(); int eyeDobj = -1;
        var envCache = new Dictionary<string, HSD_Image>();
        foreach (var d in mesh.GetProperty("dobjs").EnumerateArray())
        {
            var texs = d.GetProperty("textures").EnumerateArray().Select(x => x.GetString()).ToList();
            var coords = d.GetProperty("coords").EnumerateArray().Select(x => x.GetString()).ToList();
            var maps = d.GetProperty("maps").EnumerateArray().Select(x => x.GetString()).ToList();
            var wraps = d.GetProperty("wrap").EnumerateArray().Select(x => (x[0].GetString(), x[1].GetString())).ToList();
            var uvRefs = Enumerable.Range(0, texs.Count).Where(i => maps[i] == "TexCoord").Reverse().ToList();
            var envRefs = Enumerable.Range(0, texs.Count).Where(i => maps[i] == "EnvCamera").ToList();
            var uvSet = uvRefs.Select(i => int.Parse(coords[i].Replace("TexCoord", ""))).ToList();
            var attrs = new List<GXAttribName> { GXAttribName.GX_VA_PNMTXIDX, GXAttribName.GX_VA_POS, GXAttribName.GX_VA_NRM };
            for (int k = 0; k < uvSet.Count; k++) attrs.Add(GXAttribName.GX_VA_TEX0 + k);

            var verts = new List<GX_Vertex>(); var bones = new List<HSD_JOBJ[]>(); var wts = new List<float[]>();
            int single = 0;
            foreach (var tri in d.GetProperty("tris").EnumerateArray())
                foreach (var v in (flip ? tri.EnumerateArray().Reverse() : tri.EnumerateArray()))
                {
                    var p = v.GetProperty("p").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
                    var nr = v.GetProperty("n").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
                    var uvs = v.TryGetProperty("uvs", out var us)
                        ? us.EnumerateArray().Select(u => u.EnumerateArray().Select(x => (float)x.GetDouble()).ToArray()).ToList()
                        : new List<float[]> { v.GetProperty("uv").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray() };
                    var wl = v.GetProperty("w").EnumerateArray().Select(x => (x[0].GetInt32(), (float)x[1].GetDouble())).ToArray();
                    if (wl.Length == 1)
                    {
                        var m = ibm[wl[0].Item1];
                        var q = new float[] {
                            m.M11 * p[0] + m.M12 * p[1] + m.M13 * p[2] + m.M14,
                            m.M21 * p[0] + m.M22 * p[1] + m.M23 * p[2] + m.M24,
                            m.M31 * p[0] + m.M32 * p[1] + m.M33 * p[2] + m.M34 };
                        var qn = new float[] {
                            m.M11 * nr[0] + m.M12 * nr[1] + m.M13 * nr[2],
                            m.M21 * nr[0] + m.M22 * nr[1] + m.M23 * nr[2],
                            m.M31 * nr[0] + m.M32 * nr[1] + m.M33 * nr[2] };
                        float l = MathF.Sqrt(qn[0] * qn[0] + qn[1] * qn[1] + qn[2] * qn[2]); if (l > 0) { qn[0] /= l; qn[1] /= l; qn[2] /= l; }
                        p = q; nr = qn; single++;
                    }
                    var gv = new GX_Vertex { POS = new GXVector3(p[0], p[1], p[2]), NRM = new GXVector3(nr[0], nr[1], nr[2]) };
                    GXVector2 UV(int k) => new GXVector2(uvs[uvSet[k]][0], uvs[uvSet[k]][1]);
                    if (uvSet.Count > 0) gv.TEX0 = UV(0);
                    if (uvSet.Count > 1) gv.TEX1 = UV(1);
                    if (uvSet.Count > 2) gv.TEX2 = UV(2);
                    verts.Add(gv);
                    bones.Add(wl.Select(x => jobjs[x.Item1]).ToArray());
                    wts.Add(wl.Select(x => x.Item2).ToArray());
                }
            string cull = d.GetProperty("cull").GetString();
            gen.CullMode = cull == "Cull_None" ? GenCullMode.None : cull == "Cull_Outside" ? GenCullMode.Back : GenCullMode.Front;
            var pobj = gen.CreatePOBJsFromTriangleList(verts, attrs.ToArray(), bones, wts);

            // material
            var mobj = new HSD_MOBJ { _s = tMobj._s.DeepClone() };
            bool xlu = d.GetProperty("xlu").GetBoolean();
            bool lit = d.GetProperty("lit").GetBoolean();
            var spec = d.GetProperty("spec").ValueKind == JsonValueKind.Array ? d.GetProperty("spec").EnumerateArray().Select(x => x.GetInt32()).ToArray() : null;
            var env = d.GetProperty("env").ValueKind == JsonValueKind.Array ? d.GetProperty("env").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray() : null;
            var baseT = mobj.Textures; baseT.Next = null;
            var tl_ = new List<HSD_TOBJ>(); var layers = new List<object>();
            for (int k = 0; k < uvRefs.Count; k++)
            {
                int ri = uvRefs[k];
                var t = k == 0 ? baseT : new HSD_TOBJ { _s = baseT._s.DeepClone() };
                var (im, tl) = images[texs[ri]];
                t.ImageData = im;
                t.TlutData = im.Format == GXTexFmt.CI8 || im.Format == GXTexFmt.CI4 ? tl : null;
                t.WrapS = Wrap(wraps[ri].Item1); t.WrapT = Wrap(wraps[ri].Item2);
                t.RepeatS = 1; t.RepeatT = 1;
                t.TexMapID = GXTexMapID.GX_TEXMAP0 + tl_.Count; t.GXTexGenSrc = GXTexGenSrc.GX_TG_TEX0 + k;
                if (k > 0) { t.Flags = TOBJ_FLAGS.LIGHTMAP_DIFFUSE | TOBJ_FLAGS.COLORMAP_ALPHA_MASK; t.TEV = null; t.Blending = 1; }
                if (texs[ri] == "metaknight_eye") { eyeTobj[coords[ri]] = tobjIndex + tl_.Count; eyeDobj = d.GetProperty("index").GetInt32(); }
                tl_.Add(t);
                layers.Add(new { layer = tl_.Count - 1, texture = texs[ri], coord = coords[ri], vtx = "TEX" + k, op = k == 0 ? "REPLACE" : "ALPHA_MASK", fmt = im.Format.ToString() });
            }
            foreach (int ri in envRefs)
            {
                if (env == null) throw new Exception("sphere map without a BRAWL_MAT env factor: " + d.GetProperty("material").GetString());
                string key = texs[ri] + string.Join(",", env);
                if (!envCache.TryGetValue(key, out var eim)) envCache[key] = eim = PremultSphere(images[texs[ri]].img, env);
                var t = new HSD_TOBJ { _s = baseT._s.DeepClone() };
                t.TEV = null; t.TlutData = null; t.ImageData = eim;
                t.Flags = TOBJ_FLAGS.COORD_REFLECTION | TOBJ_FLAGS.LIGHTMAP_DIFFUSE | TOBJ_FLAGS.COLORMAP_ADD;
                t.WrapS = GXWrapMode.CLAMP; t.WrapT = GXWrapMode.CLAMP; t.RepeatS = 1; t.RepeatT = 1; t.Blending = 1;
                t.TexMapID = GXTexMapID.GX_TEXMAP0 + tl_.Count; t.GXTexGenSrc = GXTexGenSrc.GX_TG_TEX0 + tl_.Count;
                tl_.Add(t);
                layers.Add(new { layer = tl_.Count - 1, texture = texs[ri], coord = "REFLECTION (normals)", vtx = "-", op = "ADD x" + string.Join(",", env.Select(x => x.ToString("0.###"))), fmt = eim.Format.ToString() });
            }
            for (int i = 0; i < tl_.Count - 1; i++) tl_[i].Next = tl_[i + 1];
            var rf = mobj.RenderFlags & ~(RENDER_MODE.CONSTANT | RENDER_MODE.VERTEX | RENDER_MODE.DIFFUSE | RENDER_MODE.SPECULAR
                                          | RENDER_MODE.TEX0 | RENDER_MODE.TEX1 | RENDER_MODE.TEX2 | RENDER_MODE.TEX3);
            rf |= lit ? RENDER_MODE.DIFFUSE : RENDER_MODE.CONSTANT;
            if (lit && spec != null) rf |= RENDER_MODE.SPECULAR;
            for (int i = 0; i < tl_.Count; i++) rf |= (RENDER_MODE)((int)RENDER_MODE.TEX0 << i);
            mobj.RenderFlags = rf;
            if (!lit) { mobj.Material.DiffuseColor = System.Drawing.Color.FromArgb(255, 255, 255, 255); mobj.Material.AmbientColor = System.Drawing.Color.FromArgb(255, 255, 255, 255); }
            if (spec != null) mobj.Material.SpecularColor = System.Drawing.Color.FromArgb(255, spec[0], spec[1], spec[2]);
            if (xlu)
            {
                mobj.RenderFlags |= RENDER_MODE.XLU | RENDER_MODE.ALPHA_MAT;
                baseT.AlphaOperation = ALPHAMAP.MODULATE;
                mobj.PEDesc = new HSD_PEDesc
                {
                    Flags = PIXEL_PROCESS_ENABLE.COLOR_UPDATE | PIXEL_PROCESS_ENABLE.ALPHA_UPDATE | PIXEL_PROCESS_ENABLE.COMPARE | PIXEL_PROCESS_ENABLE.ZUPDATE,
                    AlphaRef0 = 0, AlphaRef1 = 0, DestinationAlpha = 0,
                    BlendMode = GXBlendMode.GX_BLEND, SrcFactor = GXBlendFactor.GX_BL_SRCALPHA, DstFactor = GXBlendFactor.GX_BL_INVSRCALPHA,
                    BlendOp = GXLogicOp.GX_LO_SET, DepthFunction = GXCompareType.LEqual,
                    AlphaComp0 = GXCompareType.GEqual, AlphaOp = GXAlphaOp.And, AlphaComp1 = GXCompareType.GEqual,
                };
            }
            var dobj = new HSD_DOBJ { Mobj = mobj, Pobj = pobj };
            dlist.Add(dobj); firstTobj.Add(tobjIndex);
            per.Add(new { dobj = d.GetProperty("index").GetInt32(), obj = d.GetProperty("object").GetString(), group = d.GetProperty("group").GetString(),
                          material = d.GetProperty("material").GetString(), texture = texs[uvRefs[0]], fmt = images[texs[uvRefs[0]]].img.Format.ToString(),
                          tlut = baseT.TlutData != null, render = mobj.RenderFlags.ToString(), first_tobj = tobjIndex, layers,
                          cull = cull, xlu, verts = verts.Count, tris = verts.Count / 3, single_bound_verts = single, pobjs = pobj.List.Count });
            tobjIndex += tl_.Count;
        }
        for (int i = 0; i < dlist.Count - 1; i++) dlist[i].Next = dlist[i + 1];
        root.Dobj = dlist[0];
        gen.SaveChanges();
        root.UpdateFlags();
        foreach (var j in root.TreeList) j.Flags |= JOBJ_FLAG.CLASSICAL_SCALING;
        report["dobjs"] = per;
        report["joints"] = root.TreeList.Count;
        report["root_flags"] = root.Flags.ToString();
        report["template_root_flags"] = tRoot.Flags.ToString();
        report["template_joint1_flags"] = tRoot.Child.Flags.ToString();
        report["joint1_flags"] = root.Child.Flags.ToString();

        // ---- matanim: the costume texture anims. ftData x8->x8 lists the two eye TObjs (global TObj indices, eye_tobjs):
        // the SetTexAnim script command sets both to a frame (= an eye state, anim/out/eye_states.json) and the engine
        // resets them to frame 0 (state 0 = identity, open eyes) at every motion change.
        var statesPath = Environment.GetEnvironmentVariable("MK_EYE_STATES")
                         ?? Path.Combine(Path.GetDirectoryName(Path.GetFullPath(meshPath)), "..", "..", "anim", "out", "eye_states.json");
        var states = JsonDocument.Parse(File.ReadAllText(statesPath)).RootElement.GetProperty("states").EnumerateArray()
                     .Select(s => s.EnumerateArray().Select(x => (float)x.GetDouble()).ToArray()).ToList();
        var eyeMaps = new List<(GXTexMapID id, int col)>();
        foreach (var (coord, col) in new[] { ("TexCoord0", 0), ("TexCoord1", 4) })
            eyeMaps.Add((GXTexMapID.GX_TEXMAP0 + (eyeTobj[coord] - firstTobj[eyeDobj]), col));
        var mroot = BuildMatAnim(root, dlist.Count, eyeDobj, eyeMaps, states);
        report["eye_dobj"] = eyeDobj;
        report["eye_tobjs"] = new[] { eyeTobj["TexCoord0"], eyeTobj["TexCoord1"] };
        report["eye_states"] = states.Count;
        report["matanim"] = $"tree {mroot.TreeList.Count} nodes; DObj {eyeDobj}: texanims on the eye TObjs ({string.Join(", ", eyeMaps.Select(m => m.id))}), SCAU/SCAV/TRAU/TRAV linear keys, frame k = eye state k ({states.Count} states)";
        var f = new HSDRawFile();
        f.Roots.Add(new HSDRootNode { Name = JointSym, Data = root });
        f.Roots.Add(new HSDRootNode { Name = MatAnimSym, Data = mroot });
        f.Save(outPath);
        if (reportPath != null) File.WriteAllText(reportPath, JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine("wrote " + outPath + " " + new FileInfo(outPath).Length + " joints " + root.TreeList.Count + " dobjs " + dlist.Count);
        return 0;
    }
}
