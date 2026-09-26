// fighterbuild build <mesh.json> <template costume .dat> <out.dat> <joint symbol> [report.json]
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
//  - textures: RGBA from the JSON, encoded here (CMPR if opaque, else RGBA8)
// Winding: FIGHTERBUILD_FLIP=1 reverses it (mkbuild needed that for BrawlLib); Ultimate's is
// unverified until the model is seen in game.
using System.Text.Json;
using HSDRaw;
using HSDRaw.Common;
using HSDRaw.GX;
using HSDRaw.Tools;

static class P
{
    static int Main(string[] a)
    {
        if (a.Length >= 3 && a[0] == "verify")
            return Verify.Run(a[1], a[2]);
        if (a.Length >= 5 && a[0] == "build")
            return Build(a[1], a[2], a[3], a[4], a.Length > 5 ? a[5] : null);
        Console.Error.WriteLine("usage: fighterbuild build <mesh.json> <template.dat> <out.dat> <joint symbol> [report.json]");
        return 2;
    }

    static float[] F(JsonElement e) => e.EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();

    static GXWrapMode Wrap(string s) => s switch { "ClampToEdge" => GXWrapMode.CLAMP, "MirroredRepeat" => GXWrapMode.MIRROR, _ => GXWrapMode.REPEAT };

    static int Build(string meshPath, string templatePath, string outPath, string jointSym, string reportPath)
    {
        var mesh = JsonDocument.Parse(File.ReadAllText(meshPath)).RootElement;
        var tf = new HSDRawFile(templatePath);
        var tRoot = tf.Roots.First(r => r.Name.EndsWith("_Share_joint")).Data as HSD_JOBJ;
        var tMobj = tRoot.TreeList.Where(j => j.Dobj != null).SelectMany(j => j.Dobj.List)
                         .Select(d => d.Mobj).First(m => m != null && m.Textures != null);
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
                Flags = JOBJ_FLAG.CLASSICAL_SCALING,
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
            var fmt = t.GetProperty("fmt").GetString() == "CMPR" ? GXTexFmt.CMP : GXTexFmt.RGBA8;
            var data = GXImageConverter.EncodeImage(bgra, w, h, fmt, GXTlutFmt.IA8, out _);
            images[t.GetProperty("name").GetString()] = new HSD_Image { ImageData = data, Width = (short)w, Height = (short)h, Format = fmt };
            texRep.Add(new { name = t.GetProperty("name").GetString(), w, h, fmt = fmt.ToString(), bytes = data.Length });
        }

        // ---- DObjs ----------------------------------------------------------------------------------
        var gen = new POBJ_Generator { UseTriangleStrips = true };
        var ibm = jobjs.Select(j => j.InverseWorldTransform).ToList();
        bool flip = Environment.GetEnvironmentVariable("FIGHTERBUILD_FLIP") == "1";
        var dlist = new List<HSD_DOBJ>(); var per = new List<object>();
        foreach (var d in mesh.GetProperty("dobjs").EnumerateArray())
        {
            var texs = d.GetProperty("textures").EnumerateArray().Select(x => x.GetString()).ToList();
            bool hasTex = texs.Count > 0 && images.ContainsKey(texs[0]);
            var attrs = new List<GXAttribName> { GXAttribName.GX_VA_PNMTXIDX, GXAttribName.GX_VA_POS, GXAttribName.GX_VA_NRM };
            if (hasTex) attrs.Add(GXAttribName.GX_VA_TEX0);
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
                    if (hasTex) { var uv = F(v.GetProperty("uv")); gv.TEX0 = new GXVector2(uv[0], uv[1]); }
                    verts.Add(gv);
                    bones.Add(wl.Select(x => jobjs[x.Item1]).ToArray());
                    wts.Add(wl.Select(x => x.Item2).ToArray());
                }
            string cull = d.GetProperty("cull").GetString();
            gen.CullMode = cull == "Cull_None" ? GenCullMode.None : cull == "Cull_Outside" ? GenCullMode.Back : GenCullMode.Front;
            var pobj = gen.CreatePOBJsFromTriangleList(verts, attrs.ToArray(), bones, wts);

            var mobj = new HSD_MOBJ { _s = tMobj._s.DeepClone() };
            var tobj = mobj.Textures; tobj.Next = null;
            var rf = mobj.RenderFlags & ~(RENDER_MODE.CONSTANT | RENDER_MODE.VERTEX | RENDER_MODE.DIFFUSE | RENDER_MODE.SPECULAR
                                          | RENDER_MODE.TEX0 | RENDER_MODE.TEX1 | RENDER_MODE.TEX2 | RENDER_MODE.TEX3);
            rf |= RENDER_MODE.DIFFUSE;
            if (hasTex)
            {
                var wrap = d.GetProperty("wrap")[0];
                tobj.ImageData = images[texs[0]]; tobj.TlutData = null;
                tobj.WrapS = Wrap(wrap[0].GetString()); tobj.WrapT = Wrap(wrap[1].GetString());
                tobj.RepeatS = 1; tobj.RepeatT = 1;
                tobj.TexMapID = GXTexMapID.GX_TEXMAP0; tobj.GXTexGenSrc = GXTexGenSrc.GX_TG_TEX0;
                rf |= RENDER_MODE.TEX0;
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
                    BlendMode = GXBlendMode.GX_BLEND, SrcFactor = GXBlendFactor.GX_BL_SRCALPHA, DstFactor = GXBlendFactor.GX_BL_INVSRCALPHA,
                    BlendOp = GXLogicOp.GX_LO_SET, DepthFunction = GXCompareType.LEqual,
                    AlphaComp0 = GXCompareType.GEqual, AlphaOp = GXAlphaOp.And, AlphaComp1 = GXCompareType.GEqual,
                };
            }
            dlist.Add(new HSD_DOBJ { Mobj = mobj, Pobj = pobj });
            per.Add(new
            {
                dobj = dlist.Count - 1, obj = d.GetProperty("object").GetString(), sub = d.GetProperty("subindex").GetInt32(),
                group = d.GetProperty("group").ValueKind == JsonValueKind.String ? d.GetProperty("group").GetString() : null,
                texture = hasTex ? texs[0] : null, xlu, cull, verts = verts.Count, tris = verts.Count / 3,
                single_bound_verts = single, pobjs = pobj.List.Count,
            });
        }
        if (dlist.Count > 124)
            throw new Exception($"{dlist.Count} DObjs: the fighter DObj list holds 124 (ftParts_80074194)");
        for (int i = 0; i < dlist.Count - 1; i++) dlist[i].Next = dlist[i + 1];
        root.Dobj = dlist[0];
        gen.SaveChanges();
        root.UpdateFlags();
        foreach (var j in root.TreeList) j.Flags |= JOBJ_FLAG.CLASSICAL_SCALING;

        var f = new HSDRawFile();
        f.Roots.Add(new HSDRootNode { Name = jointSym, Data = root });
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
