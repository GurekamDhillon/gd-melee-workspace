using System.Numerics;
using System.Text.Json;
using HSDRaw;
using HSDRaw.Common;
using HSDRaw.Common.Animation;
using HSDRaw.GX;
using HSDRaw.Melee.Ef;
using HSDRaw.Tools;

// efbuild build <ef_metaknight.json> <spec.json> <out.dat>
// Meta Knight's Brawl effect models (ef_metaknight.pac MDL0 + VIS0/CHR0/SRT0/CLR0, exported by efexport.exe) as a Melee
// effect bank (EfXxData.dat: effXxDataTable = SBM_EffectTable {ptcl, texg, EffectModel[]} + m-ex's effBehaviorTable).
//  - one JObj per Brawl bone (bind SRT), every Brawl object is a rigid DObj on its single-bind bone (vertices
//    bone-local, no envelope), Brawl's cull-none kept (no cull flags)
//  - material: unlit (RENDER_CONSTANT = material colour, or RENDER_VERTEX when Brawl's light channel takes the vertex
//    colour), TEX0 modulate, XLU, PE blend = Brawl's (SrcAlpha/One additive or SrcAlpha/InvSrcAlpha), no z update
//  - Brawl's two-colour TEV (rgb = lerp(Color1, Color0, texture)) is baked into an RGBA8 texture
//  - VIS0 -> HSD_A_J_NODE, CHR0 -> joint SRT tracks, SRT0 translation -> TexAnim TRAU/TRAV, CLR0 material alpha ->
//    HSD_A_M_ALPHA; all baked per frame (linear keys; visibility constant keys)
//  - particles (spec "ptcl"): generators written from the spec's op lists (HSDRaw ParticleEncoding), texture groups
//    from RGBA images in the spec
static class Build
{
    static float[] Fa(JsonElement e) => e.EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
    const float D2R = MathF.PI / 180f;

    static Matrix4x4 Local(float[] s, float[] r, float[] t)
    {
        // NW4R / HSD: M = T * Rz * Ry * Rx * S (column vectors) -> System.Numerics row-vector order S*Rx*Ry*Rz*T
        return Matrix4x4.CreateScale(s[0], s[1], s[2]) * Matrix4x4.CreateRotationX(r[0] * D2R) * Matrix4x4.CreateRotationY(r[1] * D2R)
             * Matrix4x4.CreateRotationZ(r[2] * D2R) * Matrix4x4.CreateTranslation(t[0], t[1], t[2]);
    }

    static (byte r, byte g, byte b, byte a) Col(string s)
    {
        // "R:255 G:255 B:255 A:255"
        var d = s.Split(' ').Select(p => p.Split(':')).ToDictionary(p => p[0], p => byte.Parse(p[1]));
        return (d["R"], d["G"], d["B"], d["A"]);
    }

    static GXBlendFactor BF(string s) => s switch
    {
        "Zero" => GXBlendFactor.GX_BL_ZERO, "One" => GXBlendFactor.GX_BL_ONE,
        "SourceAlpha" => GXBlendFactor.GX_BL_SRCALPHA, "InverseSourceAlpha" => GXBlendFactor.GX_BL_INVSRCALPHA,
        "SourceColor" => GXBlendFactor.GX_BL_SRCCLR, "InverseSourceColor" => GXBlendFactor.GX_BL_INVSRCCLR,
        "DestinationAlpha" => GXBlendFactor.GX_BL_DSTALPHA, "InverseDestinationAlpha" => GXBlendFactor.GX_BL_INVDSTALPHA,
        _ => GXBlendFactor.GX_BL_ONE
    };
    static GXWrapMode Wrap(string s) => s == "Clamp" ? GXWrapMode.CLAMP : s == "Mirror" ? GXWrapMode.MIRROR : GXWrapMode.REPEAT;

    // ---------------------------------------------------------------------------------------------- images
    class Img { public int W, H; public byte[] Rgba; public string Fmt; }
    static Dictionary<string, Img> images = new();
    static Dictionary<string, HSD_Image> encoded = new();
    public static Dictionary<string, object> Report = new();

    static HSD_Image Encode(string key, Img im)
    {
        if (encoded.TryGetValue(key, out var e)) return e;
        bool gray = true, opaque = true;
        for (int i = 0; i < im.W * im.H; i++)
        {
            byte r = im.Rgba[i * 4], g = im.Rgba[i * 4 + 1], b = im.Rgba[i * 4 + 2], a = im.Rgba[i * 4 + 3];
            if (r != g || g != b) gray = false;
            if (a != 255) opaque = false;
        }
        var fmt = gray ? (opaque ? GXTexFmt.I8 : GXTexFmt.IA8) : (im.Fmt == "CMPR" ? GXTexFmt.CMP : GXTexFmt.RGBA8);
        var bgra = new byte[im.Rgba.Length];
        for (int i = 0; i < im.W * im.H; i++)
        { bgra[i * 4] = im.Rgba[i * 4 + 2]; bgra[i * 4 + 1] = im.Rgba[i * 4 + 1]; bgra[i * 4 + 2] = im.Rgba[i * 4]; bgra[i * 4 + 3] = im.Rgba[i * 4 + 3]; }
        var data = GXImageConverter.EncodeImage(bgra, im.W, im.H, fmt, GXTlutFmt.IA8, out _);
        var h = new HSD_Image { ImageData = data, Width = (short)im.W, Height = (short)im.H, Format = fmt };
        encoded[key] = h;
        return h;
    }

    // Brawl two-colour TEV: rgb = lerp(C1, C0, tex.rgb) (a = C1, b = C0, c = texture), alpha from the texture
    static Img Bake2(Img src, (byte r, byte g, byte b, byte a) c0, (byte r, byte g, byte b, byte a) c1)
    {
        var o = new Img { W = src.W, H = src.H, Rgba = new byte[src.Rgba.Length] };
        for (int i = 0; i < src.W * src.H; i++)
        {
            float tr = src.Rgba[i * 4] / 255f, tg = src.Rgba[i * 4 + 1] / 255f, tb = src.Rgba[i * 4 + 2] / 255f;
            o.Rgba[i * 4] = (byte)Math.Clamp(MathF.Round(c1.r * (1 - tr) + c0.r * tr), 0, 255);
            o.Rgba[i * 4 + 1] = (byte)Math.Clamp(MathF.Round(c1.g * (1 - tg) + c0.g * tg), 0, 255);
            o.Rgba[i * 4 + 2] = (byte)Math.Clamp(MathF.Round(c1.b * (1 - tb) + c0.b * tb), 0, 255);
            o.Rgba[i * 4 + 3] = src.Rgba[i * 4 + 3];
        }
        return o;
    }

    // ---------------------------------------------------------------------------------------------- tracks
    static HSD_FOBJDesc Track(byte type, IList<float> vals, bool constant = false)
    {
        var keys = new List<FOBJKey>();
        for (int f = 0; f < vals.Count; f++)
        {
            if (constant)
            {
                if (f > 0 && vals[f] == vals[f - 1]) continue;
                keys.Add(new FOBJKey { Frame = f, Value = vals[f], InterpolationType = GXInterpolationType.HSD_A_OP_CON });
            }
            else
            {
                // drop keys a straight line through their neighbours reproduces
                if (f > 0 && f < vals.Count - 1 && MathF.Abs(vals[f] - (vals[f - 1] + vals[f + 1]) * 0.5f) < 1e-5f) continue;
                keys.Add(new FOBJKey { Frame = f, Value = vals[f], InterpolationType = GXInterpolationType.HSD_A_OP_LIN });
            }
        }
        var d = new HSD_FOBJDesc();
        d.SetKeys(keys, type);
        return d;
    }
    static bool Varies(IList<float> v) { for (int i = 1; i < v.Count; i++) if (MathF.Abs(v[i] - v[0]) > 1e-5f) return true; return false; }
    static HSD_AOBJ Aobj(List<HSD_FOBJDesc> tracks, float end, bool loop)
    {
        if (tracks.Count == 0) return null;
        for (int i = 0; i < tracks.Count - 1; i++) tracks[i].Next = tracks[i + 1];
        return new HSD_AOBJ { Flags = loop ? AOBJ_Flags.ANIM_LOOP : 0, EndFrame = end, FObjDesc = tracks[0] };
    }

    // ---------------------------------------------------------------------------------------------- model
    static SBM_EffectModel Model(JsonElement m, JsonElement spec)
    {
        string mname = m.GetProperty("name").GetString();
        var rep = new Dictionary<string, object>();
        Report[mname] = rep;
        // bones
        var bl = m.GetProperty("bones").EnumerateArray().ToList();
        var jobjs = new List<HSD_JOBJ>(); var byName = new Dictionary<string, int>();
        var world = new List<Matrix4x4>();
        float maxBindErr = 0;
        for (int i = 0; i < bl.Count; i++)
        {
            var b = bl[i];
            var s = Fa(b.GetProperty("s")); var r = Fa(b.GetProperty("r")); var t = Fa(b.GetProperty("t"));
            var jo = new HSD_JOBJ { SX = s[0], SY = s[1], SZ = s[2], RX = r[0] * D2R, RY = r[1] * D2R, RZ = r[2] * D2R, TX = t[0], TY = t[1], TZ = t[2], Flags = JOBJ_FLAG.CLASSICAL_SCALING };
            byName[b.GetProperty("name").GetString()] = i;
            var loc = Local(s, r, t);
            string par = b.GetProperty("parent").ValueKind == JsonValueKind.Null ? null : b.GetProperty("parent").GetString();
            var w = par == null ? loc : loc * world[byName[par]];
            world.Add(w);
            if (par != null) jobjs[byName[par]].AddChild(jo);
            jobjs.Add(jo);
            // exported BrawlLib bind matrix (column-major, translation at 12..14) vs our FK
            var bm = Fa(b.GetProperty("bind"));
            maxBindErr = MathF.Max(maxBindErr, MathF.Abs(bm[12] - w.M41) + MathF.Abs(bm[13] - w.M42) + MathF.Abs(bm[14] - w.M43));
        }
        rep["bind_error"] = maxBindErr;
        var inv = world.Select(w => { Matrix4x4.Invert(w, out var iw); return iw; }).ToList();

        // images of this model's textures (by name) come from the file-level table
        var mats = m.GetProperty("materials").EnumerateArray().ToDictionary(x => x.GetProperty("name").GetString(), x => x);

        // animations
        JsonElement? vis = m.GetProperty("vis0").GetArrayLength() > 0 ? m.GetProperty("vis0")[0] : null;
        JsonElement? chr = m.GetProperty("chr0").GetArrayLength() > 0 ? m.GetProperty("chr0")[0] : null;
        JsonElement? srt = m.GetProperty("srt0").GetArrayLength() > 0 ? m.GetProperty("srt0")[0] : null;
        JsonElement? clr = m.GetProperty("clr0").GetArrayLength() > 0 ? m.GetProperty("clr0")[0] : null;
        int frames = 0; bool loop = false;
        foreach (var a in new[] { vis, chr, srt, clr }) if (a != null) { frames = Math.Max(frames, a.Value.GetProperty("frames").GetInt32()); loop |= a.Value.GetProperty("loop").GetBoolean(); }
        if (spec.TryGetProperty("loop", out var lo)) loop = lo.GetBoolean();

        // DObjs, per bone, in object order
        var perJoint = jobjs.Select(_ => new List<(HSD_DOBJ d, string mat)>()).ToList();
        var gen = new POBJ_Generator { UseTriangleStrips = true };
        var objs = new List<object>();
        foreach (var o in m.GetProperty("objects").EnumerateArray())
        {
            string matName = o.GetProperty("material").GetString();
            var mat = mats[matName];
            var props = mat.GetProperty("props");
            var has = o.GetProperty("has").EnumerateArray().Select(x => x.GetInt32()).ToArray();
            var tris = o.GetProperty("tris").EnumerateArray().ToList();
            // single-bind bone
            string sb = o.GetProperty("singlebind").ValueKind == JsonValueKind.String ? o.GetProperty("singlebind").GetString() : null;
            if (sb == null && tris.Count > 0) sb = tris[0][14][0][0].GetString();
            int bi = byName[sb];
            bool vtxColor = props.GetProperty("C1ColorMaterialSource").GetString() == "Vertex" && has[2] == 1;
            bool vtxAlpha = props.GetProperty("C1AlphaMaterialSource").GetString() == "Vertex" && has[2] == 1;
            var verts = new List<GX_Vertex>();
            foreach (var tv in tris)
            {
                var v = tv.EnumerateArray().ToList();
                var p = Vector3.Transform(new Vector3((float)v[0].GetDouble(), (float)v[1].GetDouble(), (float)v[2].GetDouble()), inv[bi]);
                var n = Vector3.Normalize(Vector3.TransformNormal(new Vector3((float)v[3].GetDouble(), (float)v[4].GetDouble(), (float)v[5].GetDouble()), inv[bi]));
                verts.Add(new GX_Vertex
                {
                    POS = new GXVector3(p.X, p.Y, p.Z), NRM = new GXVector3(n.X, n.Y, n.Z),
                    TEX0 = new GXVector2((float)v[6].GetDouble(), (float)v[7].GetDouble()),
                    CLR0 = new GXColor4(v[10].GetInt32() / 255f, v[11].GetInt32() / 255f, v[12].GetInt32() / 255f, v[13].GetInt32() / 255f),
                });
            }
            var attrs = new List<GXAttribName> { GXAttribName.GX_VA_POS, GXAttribName.GX_VA_NRM };
            if (vtxColor || vtxAlpha) attrs.Add(GXAttribName.GX_VA_CLR0);
            attrs.Add(GXAttribName.GX_VA_TEX0);
            gen.CullMode = GenCullMode.None;
            var pobj = gen.CreatePOBJsFromTriangleList(verts, attrs.ToArray(), null, null);

            // material
            var c1 = Col(props.GetProperty("C1MaterialColor").GetString());
            var col0 = Col(props.GetProperty("Color0").GetString()); var col1 = Col(props.GetProperty("Color1").GetString());
            var st = mat.GetProperty("stages")[0];
            bool twoTone = st.GetProperty("ColorSelectionA").GetString() == "Color1" && st.GetProperty("ColorSelectionB").GetString() == "Color0"
                           && st.GetProperty("ColorSelectionC").GetString() == "TextureColor";
            var tref = mat.GetProperty("refs")[0];
            string tex = tref.GetProperty("Texture").GetString();
            var srcImg = images[tex];
            string key = tex;
            if (twoTone) { key = tex + "|" + col0 + "|" + col1; if (!images.ContainsKey(key)) images[key] = Bake2(srcImg, col0, col1); }
            var img = Encode(key, images[key]);
            var rf = RENDER_MODE.TEX0 | RENDER_MODE.XLU;
            rf |= vtxColor ? RENDER_MODE.VERTEX : RENDER_MODE.CONSTANT;
            rf |= vtxAlpha ? RENDER_MODE.ALPHA_VTX : RENDER_MODE.ALPHA_MAT;
            if (vtxAlpha && clr != null) rf = (rf & ~RENDER_MODE.ALPHA_VTX) | RENDER_MODE.ALPHA_BOTH;
            if (vtxColor && twoTone) { }  // two-tone keeps the vertex colour modulation (Brawl: raster = vertex, but stage ignores raster colour)
            var tobj = new HSD_TOBJ
            {
                TexMapID = GXTexMapID.GX_TEXMAP0, GXTexGenSrc = GXTexGenSrc.GX_TG_TEX0,
                SX = 1, SY = 1, SZ = 1, RepeatS = 1, RepeatT = 1,
                WrapS = Wrap(tref.GetProperty("UWrapMode").GetString()), WrapT = Wrap(tref.GetProperty("VWrapMode").GetString()),
                Flags = TOBJ_FLAGS.COORD_UV | TOBJ_FLAGS.LIGHTMAP_DIFFUSE | TOBJ_FLAGS.COLORMAP_MODULATE | TOBJ_FLAGS.ALPHAMAP_MODULATE,
                Blending = 1, MagFilter = GXTexFilter.GX_LINEAR, ImageData = img,
            };
            if (tobj.WrapT == GXWrapMode.MIRROR) tobj.TY = -1;   // HSD adds one repeat to a mirrored T (tobj.c MakeTextureMtx): cancel it
            if (twoTone)
            {   // the TEV stage ignores the raster colour: draw it as material white (vertex alpha still applies)
                rf = (rf & ~RENDER_MODE.VERTEX) | RENDER_MODE.CONSTANT;
            }
            var mobj = new HSD_MOBJ
            {
                RenderFlags = rf,
                Material = new HSD_Material
                {
                    AmbientColor = System.Drawing.Color.FromArgb(255, 255, 255, 255),
                    DiffuseColor = twoTone ? System.Drawing.Color.FromArgb(255, 255, 255, 255) : System.Drawing.Color.FromArgb(255, c1.r, c1.g, c1.b),
                    SpecularColor = System.Drawing.Color.FromArgb(255, 255, 255, 255),
                    Alpha = c1.a / 255f, Shininess = 50,
                },
                Textures = tobj,
                PEDesc = new HSD_PEDesc
                {
                    Flags = PIXEL_PROCESS_ENABLE.COLOR_UPDATE | PIXEL_PROCESS_ENABLE.COMPARE | PIXEL_PROCESS_ENABLE.BEFORE_TEX,
                    AlphaRef0 = 0, AlphaRef1 = 0, DestinationAlpha = 0,
                    BlendMode = GXBlendMode.GX_BLEND,
                    SrcFactor = BF(props.GetProperty("SrcFactor").GetString()), DstFactor = BF(props.GetProperty("DstFactor").GetString()),
                    BlendOp = GXLogicOp.GX_LO_SET, DepthFunction = GXCompareType.LEqual,
                    AlphaComp0 = GXCompareType.Always, AlphaOp = GXAlphaOp.And, AlphaComp1 = GXCompareType.Always,
                },
            };
            if (props.GetProperty("EnableDepthUpdate").GetBoolean()) mobj.PEDesc.Flags |= PIXEL_PROCESS_ENABLE.ZUPDATE;
            var dobj = new HSD_DOBJ { Mobj = mobj, Pobj = pobj };
            perJoint[bi].Add((dobj, matName));
            objs.Add(new { obj = o.GetProperty("name").GetString(), material = matName, bone = sb, tris = verts.Count / 3, twoTone, vtxColor, vtxAlpha,
                           tex = tex, fmt = img.Format.ToString(), blend = props.GetProperty("SrcFactor").GetString() + "/" + props.GetProperty("DstFactor").GetString() });
        }
        for (int i = 0; i < jobjs.Count; i++)
        {
            var l = perJoint[i];
            for (int k = 0; k < l.Count - 1; k++) l[k].d.Next = l[k + 1].d;
            if (l.Count > 0) jobjs[i].Dobj = l[0].d;
        }
        gen.SaveChanges();
        var root = jobjs[0];
        root.UpdateFlags();
        foreach (var j in root.TreeList) j.Flags |= JOBJ_FLAG.CLASSICAL_SCALING;
        rep["objects"] = objs;

        // ---- joint animation
        HSD_AnimJoint animRoot = null; bool anyJ = false;
        var ajs = new List<HSD_AnimJoint>();
        for (int i = 0; i < bl.Count; i++)
        {
            string bn = bl[i].GetProperty("name").GetString();
            var tracks = new List<HSD_FOBJDesc>();
            if (vis != null && vis.Value.GetProperty("bones").TryGetProperty(bn, out var vs))
            {
                var bits = vs.GetString().Select(c => c == '1' ? 1f : 0f).ToList();
                if (bits.Any(x => x == 0f))
                {
                    tracks.Add(Track((byte)JointTrackType.HSD_A_J_NODE, bits, constant: true));
                    if (bits[0] == 0f) jobjs[i].Flags |= JOBJ_FLAG.HIDDEN;
                }
            }
            if (chr != null && chr.Value.GetProperty("bones").TryGetProperty(bn, out var cs))
            {
                var fr = cs.EnumerateArray().Select(Fa).ToList();
                var types = new[] { JointTrackType.HSD_A_J_SCAX, JointTrackType.HSD_A_J_SCAY, JointTrackType.HSD_A_J_SCAZ,
                                    JointTrackType.HSD_A_J_ROTX, JointTrackType.HSD_A_J_ROTY, JointTrackType.HSD_A_J_ROTZ,
                                    JointTrackType.HSD_A_J_TRAX, JointTrackType.HSD_A_J_TRAY, JointTrackType.HSD_A_J_TRAZ };
                for (int k = 0; k < 9; k++)
                {
                    var vals = fr.Select(x => k >= 3 && k < 6 ? x[k] * D2R : x[k]).ToList();
                    float bind = k < 3 ? new[] { jobjs[i].SX, jobjs[i].SY, jobjs[i].SZ }[k] : k < 6 ? new[] { jobjs[i].RX, jobjs[i].RY, jobjs[i].RZ }[k - 3] : new[] { jobjs[i].TX, jobjs[i].TY, jobjs[i].TZ }[k - 6];
                    if (Varies(vals) || MathF.Abs(vals[0] - bind) > 1e-4f) tracks.Add(Track((byte)types[k], vals));
                }
            }
            var aj = new HSD_AnimJoint { AOBJ = Aobj(tracks, frames, loop) };
            if (tracks.Count > 0) anyJ = true;
            ajs.Add(aj);
        }
        // AnimJoint tree mirrors the JObj tree
        for (int i = 0; i < bl.Count; i++)
        {
            var b = bl[i];
            string par = b.GetProperty("parent").ValueKind == JsonValueKind.Null ? null : b.GetProperty("parent").GetString();
            if (par != null) ajs[byName[par]].AddChild(ajs[i]);
        }
        animRoot = anyJ ? ajs[0] : null;

        // ---- material animation (per joint, one MatAnim per DObj in order)
        bool anyM = false;
        var mjs = new List<HSD_MatAnimJoint>();
        for (int i = 0; i < bl.Count; i++)
        {
            var mj = new HSD_MatAnimJoint();
            HSD_MatAnim first = null, prev = null;
            foreach (var (d, matName) in perJoint[i])
            {
                var ma = new HSD_MatAnim();
                var mt = new List<HSD_FOBJDesc>();
                if (clr != null && clr.Value.GetProperty("mats").TryGetProperty(matName, out var cm))
                    foreach (var tg in cm.EnumerateObject())
                    {
                        if (tg.Name != "LightChannel0MaterialColor") continue;
                        var cols = tg.Value.GetProperty("colors").EnumerateArray().Select(x => x.EnumerateArray().Select(y => y.GetInt32()).ToArray()).ToList();
                        var al = cols.Select(x => x[3] / 255f).ToList();
                        if (Varies(al)) mt.Add(Track((byte)MatTrackType.HSD_A_M_ALPHA, al));
                    }
                ma.AnimationObject = Aobj(mt, frames, loop);
                if (srt != null && srt.Value.GetProperty("mats").TryGetProperty(matName, out var sm) && sm.TryGetProperty("0", out var s0))
                {
                    var fr = s0.EnumerateArray().Select(Fa).ToList();   // [su, sv, rot, tu, tv]
                    var tt = new List<HSD_FOBJDesc>();
                    float tv0 = 0;
                    foreach (var (dd, mn) in perJoint[i]) if (mn == matName && dd.Mobj.Textures.WrapT == GXWrapMode.MIRROR) tv0 = -1;
                    var tu = fr.Select(x => x[3]).ToList(); var tv = fr.Select(x => -x[4] + tv0).ToList();
                    var su = fr.Select(x => x[0]).ToList(); var sv = fr.Select(x => x[1]).ToList();
                    if (Varies(tu) || tu[0] != 0) tt.Add(Track((byte)TexTrackType.HSD_A_T_TRAU, tu));
                    if (Varies(tv) || tv[0] != 0) tt.Add(Track((byte)TexTrackType.HSD_A_T_TRAV, tv));
                    if (Varies(su) || su[0] != 1) tt.Add(Track((byte)TexTrackType.HSD_A_T_SCAU, su));
                    if (Varies(sv) || sv[0] != 1) tt.Add(Track((byte)TexTrackType.HSD_A_T_SCAV, sv));
                    if (fr.Any(x => x[2] != 0)) rep["srt_rotation_ignored"] = true;
                    if (tt.Count > 0) ma.TextureAnimation = new HSD_TexAnim { GXTexMapID = GXTexMapID.GX_TEXMAP0, AnimationObject = Aobj(tt, frames, loop) };
                }
                if (ma.AnimationObject != null || ma.TextureAnimation != null) anyM = true;
                if (prev == null) first = ma; else prev.Next = ma;
                prev = ma;
            }
            mj.MaterialAnimation = first;
            mjs.Add(mj);
        }
        for (int i = 0; i < bl.Count; i++)
        {
            var b = bl[i];
            string par = b.GetProperty("parent").ValueKind == JsonValueKind.Null ? null : b.GetProperty("parent").GetString();
            if (par != null) mjs[byName[par]].AddChild(mjs[i]);
        }

        float life = spec.TryGetProperty("lifetime", out var lf) && lf.ValueKind == JsonValueKind.Number ? (float)lf.GetDouble() : (loop ? 0 : frames);
        rep["frames"] = frames; rep["loop"] = loop; rep["lifetime"] = life; rep["joint_anim"] = anyJ; rep["mat_anim"] = anyM;
        return new SBM_EffectModel { FrameCount = life, RootJoint = root, JointAnim = animRoot, MaterialAnim = anyM ? mjs[0] : null };
    }

    // ---------------------------------------------------------------------------------------------- particles
    static (HSD_ParticleGroup, HSD_TEXGraphicBank) Particles(JsonElement p)
    {
        var gens = new List<HSD_ParticleGenerator>();
        foreach (var g in p.GetProperty("generators").EnumerateArray())
        {
            var gg = new HSD_ParticleGenerator();
            gg.New();
            var hdr = g.GetProperty("header");
            gg.TypeShape = (ParticleType)hdr.GetProperty("type").GetInt32();
            gg.Flags = (GeneratorFlags)hdr.GetProperty("gflags").GetInt32();
            gg.TexGroup = (short)hdr.GetProperty("texg").GetInt32();
            gg.GenLife = (short)hdr.GetProperty("genlife").GetInt32();
            gg.Life = (short)hdr.GetProperty("life").GetInt32();
            gg.Kind = (ParticleKind)(uint)hdr.GetProperty("kind").GetInt64();
            gg.Gravity = (float)hdr.GetProperty("gravity").GetDouble();
            gg.Friction = (float)hdr.GetProperty("friction").GetDouble();
            var vel = Fa(hdr.GetProperty("vel")); gg.VX = vel[0]; gg.VY = vel[1]; gg.VZ = vel[2];
            gg.Radius = (float)hdr.GetProperty("radius").GetDouble();
            gg.Angle = (float)hdr.GetProperty("angle").GetDouble();
            gg.Random = (float)hdr.GetProperty("random").GetDouble();
            gg.Size = (float)hdr.GetProperty("size").GetDouble();
            var prm = Fa(hdr.GetProperty("param")); gg.Param1 = prm[0]; gg.Param2 = prm[1]; gg.Param3 = prm[2];
            var ops = new List<Tuple<byte, object[]>>();
            foreach (var op in g.GetProperty("ops").EnumerateArray())
            {
                var code = (byte)op[0].GetInt32();
                var args = new List<object>();
                var types = op[1].GetString();
                for (int i = 0; i < types.Length; i++)
                {
                    var a = op[2 + i];
                    switch (types[i])
                    {
                        case 'b': args.Add((byte)a.GetInt32()); break;
                        case 's': case 'e': args.Add((short)a.GetInt32()); break;
                        case 'f': args.Add((float)a.GetDouble()); break;
                        case 'o': args.Add(a.GetBoolean()); break;
                    }
                }
                ops.Add(Tuple.Create(code, args.ToArray()));
            }
            gg.TrackData = ParticleEncoding.EncodeParticleCodes(ops);
            gens.Add(gg);
        }
        var group = new HSD_ParticleGroup();
        group.Generators = gens.ToArray();
        group.Unknown1 = 0x0042; group.Unknown2 = 0x0000;
        group.EffectIDStart = p.TryGetProperty("id_start", out var ids) ? ids.GetInt32() : 0;

        var bank = new HSD_TEXGraphicBank();
        var tgs = new List<HSD_TexGraphic>();
        foreach (var t in p.GetProperty("texgroups").EnumerateArray())
        {
            var tg = new HSD_TexGraphic();
            var fmt = Enum.Parse<GXTexFmt>(t.GetProperty("fmt").GetString());
            int w = t.GetProperty("w").GetInt32(), h = t.GetProperty("h").GetInt32();
            var tobjs = new List<HSD_TOBJ>();
            foreach (var fr in t.GetProperty("frames").EnumerateArray())
            {
                var rgba = Convert.FromBase64String(fr.GetString());
                var bgra = new byte[rgba.Length];
                for (int i = 0; i < w * h; i++) { bgra[i * 4] = rgba[i * 4 + 2]; bgra[i * 4 + 1] = rgba[i * 4 + 1]; bgra[i * 4 + 2] = rgba[i * 4]; bgra[i * 4 + 3] = rgba[i * 4 + 3]; }
                var data = GXImageConverter.EncodeImage(bgra, w, h, fmt, GXTlutFmt.IA8, out _);
                tobjs.Add(new HSD_TOBJ { ImageData = new HSD_Image { ImageData = data, Width = (short)w, Height = (short)h, Format = fmt } });
            }
            tg._s = new HSDStruct(0x18);
            tg.SetFromTOBJs(tobjs.ToArray());
            tgs.Add(tg);
        }
        bank._s = new HSDStruct(4);
        bank.ParticleImages = tgs.ToArray();
        return (group, bank);
    }

    public static int Run(string efPath, string specPath, string outPath)
    {
        var ef = JsonDocument.Parse(File.ReadAllText(efPath)).RootElement;
        var spec = JsonDocument.Parse(File.ReadAllText(specPath)).RootElement;
        foreach (var t in ef.GetProperty("textures").EnumerateArray().Concat(ef.GetProperty("reft").EnumerateArray()))
        {
            if (t.GetProperty("w").GetInt32() == 0) continue;
            string n = t.GetProperty("name").GetString();
            if (images.ContainsKey(n)) continue;
            var im = new Img { W = t.GetProperty("w").GetInt32(), H = t.GetProperty("h").GetInt32(), Rgba = Convert.FromBase64String(t.GetProperty("rgba").GetString()), Fmt = t.TryGetProperty("fmt", out var ff) ? ff.GetString() : null };
            // GX intensity formats sample alpha = intensity; BrawlLib's bitmap gives them alpha 255
            if (im.Fmt == "I4" || im.Fmt == "I8") for (int i = 0; i < im.W * im.H; i++) im.Rgba[i * 4 + 3] = im.Rgba[i * 4];
            images[n] = im;
        }
        var models = ef.GetProperty("models").EnumerateArray().ToList();
        var outModels = new List<SBM_EffectModel>(); var mtypes = new List<byte>();
        foreach (var s in spec.GetProperty("models").EnumerateArray())
        {
            if (s.ValueKind == JsonValueKind.Null) { outModels.Add(new SBM_EffectModel()); mtypes.Add(6); continue; }
            int src = s.GetProperty("src").GetInt32();
            outModels.Add(Model(models[src], s));
            mtypes.Add((byte)s.GetProperty("behavior").GetInt32());
        }
        var table = new SBM_EffectTable();
        table._s = new HSDStruct(0x08);
        table.Models = outModels.ToArray();
        var ptypes = new List<byte>();
        if (spec.TryGetProperty("ptcl", out var p) && p.ValueKind == JsonValueKind.Object)
        {
            var (grp, bank) = Particles(p);
            table.Particles = grp; table.TextureGraphics = bank;
            foreach (var g in p.GetProperty("generators").EnumerateArray()) ptypes.Add((byte)g.GetProperty("behavior").GetInt32());
        }
        // m-ex effBehaviorTable {s32 mdl_num; u8* mdl_type; s32 ptcl_num; u8* ptcl_type}
        var bhv = new HSDAccessor(); bhv._s = new HSDStruct(0x10);
        bhv._s.SetInt32(0x00, mtypes.Count);
        var mt = new HSDAccessor(); mt._s = new HSDStruct(mtypes.ToArray()); mt._s.Resize((mtypes.Count + 3) / 4 * 4);
        bhv._s.SetReference(0x04, mt);
        bhv._s.SetInt32(0x08, ptypes.Count);
        if (ptypes.Count > 0) { var pt = new HSDAccessor(); pt._s = new HSDStruct(ptypes.ToArray()); pt._s.Resize((ptypes.Count + 3) / 4 * 4); bhv._s.SetReference(0x0C, pt); }
        var f = new HSDRawFile();
        f.Roots.Add(new HSDRootNode { Name = spec.GetProperty("symbol").GetString(), Data = table });
        f.Roots.Add(new HSDRootNode { Name = "effBehaviorTable", Data = bhv });
        f.Save(outPath);
        Report["_file"] = new { bytes = new FileInfo(outPath).Length, models = outModels.Count, generators = ptypes.Count };
        File.WriteAllText(outPath + ".report.json", JsonSerializer.Serialize(Report, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine("wrote " + outPath + " " + new FileInfo(outPath).Length + " models " + outModels.Count + " generators " + ptypes.Count);
        return 0;
    }
}
