// fighterbuild build <mesh.json> <template costume .dat> <out.dat> <joint symbol> [matanim symbol] [report.json] [--tex-format auto]
// fighterbuild verify <out.dat> <mesh.json>
//
// A Melee costume file on a ported fighter's OWN joint tree, from the neutral mesh JSON that
// ports/ir/tools/export_ultimate_mesh.py writes. The generic counterpart of Halberd's mkbuild
// (ports/halberd/model/tools/mkbuild), whose joint and skinning code this follows; the Brawl
// material layers and Meta Knight's eye texanims are left out.
//  - joints: rest SRT and inverse binds from the JSON, CLASSICAL_SCALING on every joint (so
//    HSD_JObjMakeMatrix composes parent * T * R * S, as the animation converter assumes)
//  - one DObj per mesh object, envelope-skinned POBJs; single-weight vertices are stored
//    joint-local (HSD draws them with the joint matrix only)
//  - material: the template costume's first textured MObj cloned (lighting, TEV), its TObj given
//    the mesh's colour texture; XLU + alpha blend where the source blends
//  - textures: RGBA from the JSON, encoded here (legacy CMPR/RGBA8 by default)
// Winding: FIGHTERBUILD_FLIP=1 reverses it (mkbuild needed that for BrawlLib); Ultimate's is
// unverified until the model is seen in game.
using System.Text.Json;
using System.Numerics;
using System.Globalization;
using HSDRaw;
using HSDRaw.Common;
using HSDRaw.Common.Animation;
using HSDRaw.GX;
using HSDRaw.Tools;

static class P
{
    static int Main(string[] a)
    {
        if (a.Length >= 3 && a[0] == "verify")
            return Verify.Run(a[1], a[2]);
        if (a.Length >= 2 && a[0] == "dumpmobj")
        {   // material summary of a model file (numbers only), to compare an authored material with a known-good one
            var f = new HSDRawFile(a[1]);
            var jr = f.Roots.First(r => r.Data is HSD_JOBJ).Data as HSD_JOBJ;
            foreach (var d in jr.TreeList.Where(j => j.Dobj != null).SelectMany(j => j.Dobj.List))
            {
                var m = d.Mobj; var t = m.Textures;
                Console.WriteLine($"render 0x{(int)m.RenderFlags:X8} mat amb {m.Material?.AMB_R},{m.Material?.AMB_G},{m.Material?.AMB_B} dif {m.Material?.DIF_R} spc {m.Material?.SPC_R} alpha {m.Material?.Alpha} shine {m.Material?.Shininess} pe {(m.PEDesc != null)}");
                if (t != null) Console.WriteLine($"  tobj flags 0x{(int)t.Flags:X8} map {t.TexMapID} src {t.GXTexGenSrc} wrap {t.WrapS}/{t.WrapT} rep {t.RepeatS},{t.RepeatT} sc {t.SX},{t.SY},{t.SZ} blend {t.Blending} mag {t.MagFilter} img {t.ImageData?.Width}x{t.ImageData?.Height} {t.ImageData?.Format} lod {(t.LOD != null)} tev {(t.TEV != null)}");
                if (t?.TEV != null) { var v = t.TEV; Console.WriteLine($"  tev active {v.active} cop {v.color_op} aop {v.alpha_op} cb {v.color_bias} ab {v.alpha_bias} cs {v.color_scale} as {v.alpha_scale} clamp {v.color_clamp}/{v.alpha_clamp} cabcd {v.color_a_in},{v.color_b_in},{v.color_c_in},{v.color_d_in} aabcd {v.alpha_a_in},{v.alpha_b_in},{v.alpha_c_in},{v.alpha_d_in}"); }
            }
            return 0;
        }
        if (a.Length >= 3 && a[0] == "compare")
            return TriangleEquality.Run(a[1], a[2]);
        if (a.Length >= 5 && a[0] == "build")
        {
            var positional = new List<string> { a[0] };
            int pcPalette = 0;
            bool autoTextures = false;
            for (int i = 1; i < a.Length; i++)
            {
                if (a[i] == "--pc-palette")
                {
                    if (pcPalette != 0 || ++i == a.Length || a[i] != "64")
                        throw new ArgumentException("--pc-palette requires 64");
                    pcPalette = 64;
                }
                else if (a[i] == "--tex-format")
                {
                    if (autoTextures || ++i == a.Length || a[i] != "auto")
                        throw new ArgumentException("--tex-format requires auto");
                    autoTextures = true;
                }
                else positional.Add(a[i]);
            }
            if (positional.Count < 5 || positional.Count > 7)
                throw new ArgumentException("invalid fighterbuild build arguments");
            return Build(positional[1], positional[2], positional[3], positional[4],
                positional.Count > 5 ? positional[5] : null,
                positional.Count > 6 ? positional[6] : null, pcPalette, autoTextures);
        }
        Console.Error.WriteLine("usage: fighterbuild build <mesh.json> <template.dat> <out.dat> <joint symbol> [matanim symbol] [report.json] [--pc-palette 64] [--tex-format auto]");
        Console.Error.WriteLine("       fighterbuild compare <strips.dat> <triangles.dat>");
        return 2;
    }

    static float[] F(JsonElement e) => e.EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();

    static GXWrapMode Wrap(string s) => s switch { "ClampToEdge" => GXWrapMode.CLAMP, "MirroredRepeat" => GXWrapMode.MIRROR, _ => GXWrapMode.REPEAT };

    static GXTexFmt AutoTextureFormat(byte[] rgba)
    {
        int pixels = rgba.Length / 4, intermediate = 0;
        bool nearOpaque = true, binary = true;
        for (int i = 3; i < rgba.Length; i += 4)
        {
            byte alpha = rgba[i];
            if (alpha < 250) nearOpaque = false;
            if (alpha != 0 && alpha != 255) binary = false;
            if (alpha > 0 && alpha < 255) intermediate++;
        }
        if (nearOpaque || binary) return GXTexFmt.CMP;
        return 2 * intermediate >= pixels ? GXTexFmt.RGBA8 : GXTexFmt.RGB5A3;
    }

    // An original lit, textured material: diffuse x texture, one TOBJ (UV coords, modulate, linear filter).
    static HSD_MOBJ AuthoredMobj()
    {
        var tobj = new HSD_TOBJ();
        tobj.TexMapID = GXTexMapID.GX_TEXMAP0; tobj.GXTexGenSrc = GXTexGenSrc.GX_TG_TEX0;
        tobj.CoordType = COORD_TYPE.UV; tobj.DiffuseLightmap = true; tobj.ColorOperation = COLORMAP.REPLACE;   // the texture IS the diffuse lightmap, as retail costumes (flags 0x50010)
        tobj.AlphaOperation = ALPHAMAP.NONE;
        tobj.WrapS = GXWrapMode.CLAMP; tobj.WrapT = GXWrapMode.CLAMP; tobj.MagFilter = GXTexFilter.GX_LINEAR;
        tobj.Blending = 1f;
        byte amb = byte.Parse(Environment.GetEnvironmentVariable("FIGHTERBUILD_AMB") ?? "179");   // retail costume materials: 179
        var mat = new HSD_Material { AMB_R = amb, AMB_G = amb, AMB_B = amb, AMB_A = 255, DIF_R = amb, DIF_G = amb, DIF_B = amb, DIF_A = 255,
                                     SPC_R = 255, SPC_G = 255, SPC_B = 255, SPC_A = 255, Alpha = 1f, Shininess = 50f };
        return new HSD_MOBJ { RenderFlags = RENDER_MODE.DIFFUSE | RENDER_MODE.TEX0, Material = mat, Textures = tobj };
    }

    static int Build(string meshPath, string templatePath, string outPath, string jointSym, string matAnimSym, string reportPath, int pcPaletteCapacity, bool autoTextures)
    {
        var mesh = JsonDocument.Parse(File.ReadAllText(meshPath)).RootElement;
        // template "-" = AUTHORED: no disc file is read; the material is built from scratch (AuthoredMobj)
        HSD_MOBJ tMobj;
        if (templatePath == "-") tMobj = AuthoredMobj();
        else
        {
            var tf = new HSDRawFile(templatePath);
            var tRoot = tf.Roots.First(r => r.Name.EndsWith("_Share_joint")).Data as HSD_JOBJ;
            tMobj = tRoot.TreeList.Where(j => j.Dobj != null).SelectMany(j => j.Dobj.List)
                         .Select(d => d.Mobj).First(m => m != null && m.Textures != null);
        }
        var report = new Dictionary<string, object>();

        // ---- joints -------------------------------------------------------------------------------
        var jl = mesh.GetProperty("joints").EnumerateArray().ToList();
        var jobjs = new List<HSD_JOBJ>();
        foreach (var j in jl)
        {
            var s = F(j.GetProperty("scale")); var r = F(j.GetProperty("rot")); var t = F(j.GetProperty("trans"));
            var ib = F(j.GetProperty("ibm"));
            jobjs.Add(new HSD_JOBJ
            {
                SX = s[0], SY = s[1], SZ = s[2], RX = r[0], RY = r[1], RZ = r[2], TX = t[0], TY = t[1], TZ = t[2],
                Flags = JOBJ_FLAG.CLASSICAL_SCALING
                        | (j.TryGetProperty("billboard", out var bb) && bb.GetBoolean() ? JOBJ_FLAG.BILLBOARD : 0),   // optional (effect meshes)
                InverseWorldTransform = new HSD_Matrix4x3
                {
                    M11 = ib[0], M12 = ib[1], M13 = ib[2], M14 = ib[3],
                    M21 = ib[4], M22 = ib[5], M23 = ib[6], M24 = ib[7],
                    M31 = ib[8], M32 = ib[9], M33 = ib[10], M34 = ib[11],
                },
            });
        }
        for (int i = 0; i < jl.Count; i++)
        {
            int p = jl[i].GetProperty("parent").GetInt32();
            if (p >= 0) jobjs[p].AddChild(jobjs[i]);
        }
        var root = jobjs[0];
        root.InverseWorldTransform = null;     // no vertex is weighted to TopN (vanilla roots carry none)

        // ---- textures -------------------------------------------------------------------------------
        var images = new Dictionary<string, HSD_Image>();
        var texRep = new List<object>();
        foreach (var t in mesh.GetProperty("textures").EnumerateArray())
        {
            int w = t.GetProperty("w").GetInt32(), h = t.GetProperty("h").GetInt32();
            var rgba = Convert.FromBase64String(t.GetProperty("rgba").GetString());
            var bgra = new byte[rgba.Length];
            for (int i = 0; i < w * h; i++)
            { bgra[i * 4] = rgba[i * 4 + 2]; bgra[i * 4 + 1] = rgba[i * 4 + 1]; bgra[i * 4 + 2] = rgba[i * 4]; bgra[i * 4 + 3] = rgba[i * 4 + 3]; }
            var fmt = autoTextures ? AutoTextureFormat(rgba) : t.GetProperty("fmt").GetString() switch
            {
                "CMPR" => GXTexFmt.CMP,
                "RGB5A3" => GXTexFmt.RGB5A3,
                _ => GXTexFmt.RGBA8,
            };
            var data = GXImageConverter.EncodeImage(bgra, w, h, fmt, GXTlutFmt.IA8, out _);
            images[t.GetProperty("name").GetString()] = new HSD_Image { ImageData = data, Width = (short)w, Height = (short)h, Format = fmt };
            texRep.Add(new { name = t.GetProperty("name").GetString(), w, h, fmt = fmt.ToString(), bytes = data.Length });
        }

        // ---- DObjs ----------------------------------------------------------------------------------
        bool strips = Environment.GetEnvironmentVariable("FIGHTERBUILD_STRIPS") == "1";
        if (pcPaletteCapacity == 64 && strips)
            throw new InvalidOperationException("--pc-palette 64 requires triangle lists; unset FIGHTERBUILD_STRIPS");
        var gen = new POBJ_Generator { UseTriangleStrips = strips, BatchTriangleLists = !strips,
                                       PcPaletteCapacity = pcPaletteCapacity };
        var ibm = jobjs.Select(j => j.InverseWorldTransform).ToList();
        bool flip = Environment.GetEnvironmentVariable("FIGHTERBUILD_FLIP") == "1";
        var dlist = new List<HSD_DOBJ>(); var per = new List<object>();
        int beforePobjs = 0, beforePrimitives = 0, beforeVertices = 0;
        int afterPobjs = 0, afterPrimitives = 0, afterVertices = 0;
        foreach (var d in mesh.GetProperty("dobjs").EnumerateArray())
        {
            var texs = d.GetProperty("textures").EnumerateArray().Select(x => x.GetString()).ToList();
            bool hasTex = texs.Count > 0 && images.ContainsKey(texs[0]);
            var attrs = new List<GXAttribName> { GXAttribName.GX_VA_PNMTXIDX, GXAttribName.GX_VA_POS, GXAttribName.GX_VA_NRM };
            // optional, additive (effect meshes: trail_magic_models.py): per-vertex colour "c" [r,g,b,a] 0..1 and an
            // unlit material ("lit": false) whose colour and alpha come from the vertex x texture
            bool vcol = d.TryGetProperty("vcolor", out var vc) && vc.GetBoolean();
            bool unlit = d.TryGetProperty("lit", out var lt) && lt.ValueKind == JsonValueKind.False;
            if (vcol) attrs.Add(GXAttribName.GX_VA_CLR0);
            if (hasTex) attrs.Add(GXAttribName.GX_VA_TEX0);
            // layer 2 (export_ultimate_mesh 'layers': an eye's iris over its white), on TEX1
            JsonElement? layer = null;
            if (hasTex && d.TryGetProperty("layers", out var ls) && ls.GetArrayLength() > 0 && images.ContainsKey(ls[0].GetProperty("texture").GetString()))
            { layer = ls[0]; attrs.Add(GXAttribName.GX_VA_TEX1); }
            var verts = new List<GX_Vertex>(); var bones = new List<HSD_JOBJ[]>(); var wts = new List<float[]>();
            int single = 0;
            foreach (var tri in d.GetProperty("tris").EnumerateArray())
                foreach (var v in flip ? tri.EnumerateArray().Reverse() : tri.EnumerateArray())
                {
                    var p = F(v.GetProperty("p")); var nr = F(v.GetProperty("n"));
                    var wl = v.GetProperty("w").EnumerateArray().Select(x => (x[0].GetInt32(), (float)x[1].GetDouble())).ToArray();
                    if (wl.Length == 1)
                    {
                        var m = ibm[wl[0].Item1];
                        p = new[] { m.M11 * p[0] + m.M12 * p[1] + m.M13 * p[2] + m.M14,
                                    m.M21 * p[0] + m.M22 * p[1] + m.M23 * p[2] + m.M24,
                                    m.M31 * p[0] + m.M32 * p[1] + m.M33 * p[2] + m.M34 };
                        var qn = new[] { m.M11 * nr[0] + m.M12 * nr[1] + m.M13 * nr[2],
                                         m.M21 * nr[0] + m.M22 * nr[1] + m.M23 * nr[2],
                                         m.M31 * nr[0] + m.M32 * nr[1] + m.M33 * nr[2] };
                        float l = MathF.Sqrt(qn[0] * qn[0] + qn[1] * qn[1] + qn[2] * qn[2]);
                        nr = l > 0 ? qn.Select(x => x / l).ToArray() : qn;
                        single++;
                    }
                    var gv = new GX_Vertex { POS = new GXVector3(p[0], p[1], p[2]), NRM = new GXVector3(nr[0], nr[1], nr[2]) };
                    if (vcol) { var c = F(v.GetProperty("c")); gv.CLR0 = new GXColor4(c[0], c[1], c[2], c[3]); }
                    if (hasTex) { var uv = F(v.GetProperty("uv")); gv.TEX0 = new GXVector2(uv[0], uv[1]); }
                    if (layer != null) { var uv2 = F(v.GetProperty("uv2")); gv.TEX1 = new GXVector2(uv2[0], uv2[1]); }
                    verts.Add(gv);
                    bones.Add(wl.Select(x => jobjs[x.Item1]).ToArray());
                    wts.Add(wl.Select(x => x.Item2).ToArray());
                }
            string cull = d.GetProperty("cull").GetString();
            gen.CullMode = cull == "Cull_None" ? GenCullMode.None : cull == "Cull_Outside" ? GenCullMode.Back : GenCullMode.Front;
            var otherGen = new POBJ_Generator { UseTriangleStrips = pcPaletteCapacity == 64 ? false : !strips,
                                                BatchTriangleLists = pcPaletteCapacity == 64 || strips,
                                                CullMode = gen.CullMode };
            var names = attrs.ToArray();
            var otherPobj = otherGen.CreatePOBJsFromTriangleList(new List<GX_Vertex>(verts), names, bones, wts);
            var pobj = gen.CreatePOBJsFromTriangleList(new List<GX_Vertex>(verts), names, bones, wts);
            var before = pcPaletteCapacity == 64 ? otherGen.GetCounts(otherPobj)
                : strips ? gen.GetCounts(pobj) : otherGen.GetCounts(otherPobj);
            var after = pcPaletteCapacity == 64 ? gen.GetCounts(pobj)
                : strips ? otherGen.GetCounts(otherPobj) : gen.GetCounts(pobj);
            beforePobjs += before.POBJs; beforePrimitives += before.Primitives; beforeVertices += before.Vertices;
            afterPobjs += after.POBJs; afterPrimitives += after.Primitives; afterVertices += after.Vertices;

            var mobj = new HSD_MOBJ { _s = tMobj._s.DeepClone() };
            var tobj = mobj.Textures; tobj.Next = null;
            var rf = mobj.RenderFlags & ~(RENDER_MODE.CONSTANT | RENDER_MODE.VERTEX | RENDER_MODE.DIFFUSE | RENDER_MODE.SPECULAR
                                          | RENDER_MODE.TEX0 | RENDER_MODE.TEX1 | RENDER_MODE.TEX2 | RENDER_MODE.TEX3);
            rf |= unlit ? 0 : RENDER_MODE.DIFFUSE;
            if (vcol) rf = (rf & ~RENDER_MODE.ALPHA_BOTH) | RENDER_MODE.VERTEX | RENDER_MODE.ALPHA_VTX;
            if (hasTex)
            {
                var wrap = d.GetProperty("wrap")[0];
                tobj.ImageData = images[texs[0]]; tobj.TlutData = null;
                tobj.WrapS = Wrap(wrap[0].GetString()); tobj.WrapT = Wrap(wrap[1].GetString());
                tobj.RepeatS = 1; tobj.RepeatT = 1;
                tobj.TexMapID = GXTexMapID.GX_TEXMAP0; tobj.GXTexGenSrc = GXTexGenSrc.GX_TG_TEX0;
                rf |= RENDER_MODE.TEX0;
                if (layer != null)
                {
                    var l = layer.Value; var lw = l.GetProperty("wrap");
                    var t1 = new HSD_TOBJ { _s = tobj._s.DeepClone() };
                    t1.Next = null;
                    t1.ImageData = images[l.GetProperty("texture").GetString()]; t1.TlutData = null;
                    t1.WrapS = Wrap(lw[0].GetString()); t1.WrapT = Wrap(lw[1].GetString());
                    t1.RepeatS = 1; t1.RepeatT = 1;
                    t1.TexMapID = GXTexMapID.GX_TEXMAP1; t1.GXTexGenSrc = GXTexGenSrc.GX_TG_TEX1;
                    t1.ColorOperation = l.GetProperty("blend").GetString() == "add" ? COLORMAP.ADD : COLORMAP.BLEND;
                    t1.AlphaOperation = ALPHAMAP.NONE;
                    tobj.Next = t1;
                    rf |= RENDER_MODE.TEX1;
                }
            }
            else mobj.Textures = null;
            mobj.RenderFlags = rf;
            bool xlu = d.GetProperty("xlu").GetBoolean();
            if (xlu)
            {
                mobj.RenderFlags |= RENDER_MODE.XLU | RENDER_MODE.ALPHA_MAT;
                if (hasTex) tobj.AlphaOperation = ALPHAMAP.MODULATE;
                mobj.PEDesc = new HSD_PEDesc
                {
                    Flags = PIXEL_PROCESS_ENABLE.COLOR_UPDATE | PIXEL_PROCESS_ENABLE.ALPHA_UPDATE | PIXEL_PROCESS_ENABLE.COMPARE | PIXEL_PROCESS_ENABLE.ZUPDATE,
                    BlendMode = GXBlendMode.GX_BLEND, SrcFactor = GXBlendFactor.GX_BL_SRCALPHA,
                    DstFactor = d.TryGetProperty("blend", out var bl) && bl.GetString() == "add" ? GXBlendFactor.GX_BL_ONE : GXBlendFactor.GX_BL_INVSRCALPHA,
                    BlendOp = GXLogicOp.GX_LO_SET, DepthFunction = GXCompareType.LEqual,
                    AlphaComp0 = GXCompareType.GEqual, AlphaOp = GXAlphaOp.And, AlphaComp1 = GXCompareType.GEqual,
                };
            }
            if (pcPaletteCapacity == 64 && mobj.Textures != null)
                foreach (var tex in mobj.Textures.List)
                    if (tex.CoordType == COORD_TYPE.REFLECTION || tex.CoordType == COORD_TYPE.HILIGHT ||
                        tex.GXTexGenSrc == GXTexGenSrc.GX_TG_NRM || tex.GXTexGenSrc == GXTexGenSrc.GX_TG_BINRM ||
                        tex.GXTexGenSrc == GXTexGenSrc.GX_TG_TANGENT)
                        throw new InvalidOperationException($"DOBJ {dlist.Count}: PC palette v1 does not support normal-projection texgens");
            dlist.Add(new HSD_DOBJ { Mobj = mobj, Pobj = pobj });
            per.Add(new
            {
                dobj = dlist.Count - 1, obj = d.GetProperty("object").GetString(), sub = d.GetProperty("subindex").GetInt32(),
                group = d.GetProperty("group").ValueKind == JsonValueKind.String ? d.GetProperty("group").GetString() : null,
                texture = hasTex ? texs[0] : null, layer2 = layer?.GetProperty("texture").GetString(), xlu, cull, verts = verts.Count, tris = verts.Count / 3,
                single_bound_verts = single, pobjs = strips ? before.POBJs : after.POBJs,
                before = new { pobjs = before.POBJs, primitives = before.Primitives, vertices = before.Vertices },
                after = new { pobjs = after.POBJs, primitives = after.Primitives, vertices = after.Vertices },
            });
        }
        if (dlist.Count > 124)
            throw new Exception($"{dlist.Count} DObjs: the fighter DObj list holds 124 (ftParts_80074194)");
        for (int i = 0; i < dlist.Count - 1; i++) dlist[i].Next = dlist[i + 1];
        root.Dobj = dlist[0];
        gen.SaveChanges();
        report["totals"] = new {
            before = new { pobjs = beforePobjs, primitives = beforePrimitives, vertices = beforeVertices },
            after = new { pobjs = afterPobjs, primitives = afterPrimitives, vertices = afterVertices },
        };
        root.UpdateFlags();
        foreach (var j in root.TreeList) j.Flags |= JOBJ_FLAG.CLASSICAL_SCALING;

        var f = new HSDRawFile();
        f.Roots.Add(new HSDRootNode { Name = jointSym, Data = root });
        // An empty material-animation tree (same shape as the joints, one empty MatAnim per DObj on the
        // root, as mkbuild's): m-ex's costume row always names a matanim symbol, and the costume loader
        // (ftData_80085820) looks it up whenever the name is set.
        if (matAnimSym != null)
        {
            HSD_MatAnimJoint Chain(HSD_JOBJ jo)
            {
                HSD_MatAnimJoint head = null, prev = null;
                for (var c = jo; c != null; c = c.Next)
                {
                    var n = new HSD_MatAnimJoint();
                    if (c.Child != null) n.Child = Chain(c.Child);
                    if (prev == null) head = n; else prev.Next = n;
                    prev = n;
                }
                return head;
            }
            var mroot = new HSD_MatAnimJoint();
            HSD_MatAnim first = null, last = null;
            for (int i = 0; i < dlist.Count; i++) { var ma = new HSD_MatAnim(); if (last == null) first = ma; else last.Next = ma; last = ma; }
            mroot.MaterialAnimation = first;
            if (root.Child != null) mroot.Child = Chain(root.Child);
            f.Roots.Add(new HSDRootNode { Name = matAnimSym, Data = mroot });
            report["matanim_symbol"] = matAnimSym;
        }
        f.Save(outPath);
        report["joint_symbol"] = jointSym;
        report["joints"] = root.TreeList.Count;
        report["dobjs"] = per;
        report["textures"] = texRep;
        report["bytes"] = new FileInfo(outPath).Length;
        if (reportPath != null)
            File.WriteAllText(reportPath, JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine($"{outPath}: {root.TreeList.Count} joints, {dlist.Count} DObjs, {texRep.Count} textures, {report["bytes"]} bytes");
        return 0;
    }
}

// Compare the serialized DATs, including strip winding and envelope weights.
// A vertex key contains its rest-skinned position, stored normal/UV/colour,
// and the joints and weights that animate it. Cyclic triangle rotations match;
// reversed winding does not.
static class TriangleEquality
{
    static Matrix4x4 Local(HSD_JOBJ j) =>
        Matrix4x4.CreateScale(j.SX, j.SY, j.SZ) * Matrix4x4.CreateRotationX(j.RX)
        * Matrix4x4.CreateRotationY(j.RY) * Matrix4x4.CreateRotationZ(j.RZ)
        * Matrix4x4.CreateTranslation(j.TX, j.TY, j.TZ);

    static Matrix4x4 FromIbm(HSD_Matrix4x3 m) => new(
        m.M11, m.M21, m.M31, 0, m.M12, m.M22, m.M32, 0,
        m.M13, m.M23, m.M33, 0, m.M14, m.M24, m.M34, 1);

    static string Triangle(string a, string b, string c)
    {
        var ab = a + "|" + b + "|" + c;
        var bc = b + "|" + c + "|" + a;
        var ca = c + "|" + a + "|" + b;
        return new[] { ab, bc, ca }.Min(StringComparer.Ordinal);
    }

    static Dictionary<string, int> ReadTriangles(string path, bool expectLists, out int count)
    {
        var f = new HSDRawFile(path);
        var root = (HSD_JOBJ)f.Roots[0].Data;
        var joints = root.TreeList;
        var jointIds = joints.Select((j, i) => (j, i)).ToDictionary(x => x.j._s, x => x.i);
        var world = new Dictionary<HSD_JOBJ, Matrix4x4>();
        void Walk(HSD_JOBJ j, Matrix4x4 parent)
        {
            for (var c = j; c != null; c = c.Next)
            {
                var w = Local(c) * parent;
                world[c] = w;
                if (c.Child != null) Walk(c.Child, w);
            }
        }
        Walk(root, Matrix4x4.Identity);

        var triangles = new Dictionary<string, int>(StringComparer.Ordinal);
        int total = 0;
        int dobjIndex = 0;
        foreach (var dobj in root.Dobj.List)
        {
            foreach (var pobj in dobj.Pobj.List)
            {
                var dl = pobj.ToDisplayList();
                var envelopes = pobj.EnvelopeWeights;
                if (expectLists && (dl.Primitives.Count != 1
                    || dl.Primitives[0].PrimitiveType != GXPrimitiveType.Triangles
                    || dl.Primitives[0].Count > 32766 || envelopes.Length > 10))
                    throw new InvalidDataException("triangle POBJ exceeds its primitive or envelope limit");
                string Vertex(GX_Vertex v)
                {
                    var env = envelopes[v.PNMTXIDX / 3];
                    var pos = new Vector3(v.POS.X, v.POS.Y, v.POS.Z);
                    var skinned = Vector3.Zero;
                    var influences = new List<(int Joint, int Weight)>();
                    for (int i = 0; i < env.EnvelopeCount; i++)
                    {
                        var joint = env.JOBJs[i];
                        influences.Add((jointIds[joint._s], BitConverter.SingleToInt32Bits(env.Weights[i])));
                        var transform = env.EnvelopeCount == 1 ? world[joint]
                            : FromIbm(joint.InverseWorldTransform) * world[joint];
                        skinned += (env.EnvelopeCount == 1 ? 1 : env.Weights[i])
                            * Vector3.Transform(pos, transform);
                    }
                    static string F(float x) => MathF.Round(x, 4).ToString("F4", CultureInfo.InvariantCulture);
                    static int B(float x) => BitConverter.SingleToInt32Bits(x);
                    return string.Join(";", dobjIndex, F(skinned.X), F(skinned.Y), F(skinned.Z),
                        B(v.POS.X), B(v.POS.Y), B(v.POS.Z),
                        B(v.NRM.X), B(v.NRM.Y), B(v.NRM.Z),
                        B(v.TEX0.X), B(v.TEX0.Y), B(v.TEX1.X), B(v.TEX1.Y),
                        B(v.CLR0.R), B(v.CLR0.G), B(v.CLR0.B), B(v.CLR0.A),
                        string.Join(",", influences.OrderBy(x => x.Joint).Select(x => $"{x.Joint}:{x.Weight}")));
                }
                int offset = 0;
                foreach (var primitive in dl.Primitives)
                {
                    var keys = dl.Vertices.Skip(offset).Take(primitive.Count).Select(Vertex).ToArray();
                    offset += primitive.Count;
                    void Add(int a, int b, int c)
                    {
                        var key = Triangle(keys[a], keys[b], keys[c]);
                        triangles.TryGetValue(key, out int old);
                        triangles[key] = old + 1;
                        total++;
                    }
                    if (primitive.PrimitiveType == GXPrimitiveType.Triangles)
                    {
                        if (keys.Length % 3 != 0) throw new InvalidDataException("incomplete triangle list");
                        for (int i = 0; i < keys.Length; i += 3) Add(i, i + 1, i + 2);
                    }
                    else if (primitive.PrimitiveType == GXPrimitiveType.TriangleStrip)
                    {
                        for (int i = 2; i < keys.Length; i++)
                            if (i % 2 == 0) Add(i - 2, i - 1, i);
                            else Add(i - 1, i - 2, i);
                    }
                    else throw new InvalidDataException($"unexpected primitive {primitive.PrimitiveType}");
                }
            }
            dobjIndex++;
        }
        count = total;
        return triangles;
    }

    public static int Run(string stripsPath, string trianglesPath)
    {
        var before = ReadTriangles(stripsPath, false, out int beforeCount);
        var after = ReadTriangles(trianglesPath, true, out int afterCount);
        int differences = 0;
        foreach (var (key, count) in before)
        {
            after.TryGetValue(key, out int other);
            differences += Math.Abs(count - other);
            after.Remove(key);
        }
        differences += after.Values.Sum();
        Console.WriteLine($"triangle multiset: strips {beforeCount}, triangles {afterCount}, differences {differences}");
        return differences == 0 ? 0 : 2;
    }
}
