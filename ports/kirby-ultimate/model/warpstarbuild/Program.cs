using System.Text.Json;
using HSDRaw;
using HSDRaw.Common;
using HSDRaw.Common.Animation;
using HSDRaw.GX;
using HSDRaw.Melee.Pl;
using HSDRaw.Tools;

// Standalone rigid Warp Star asset for Kirby's 120-frame Ultimate Entry.
// The native host owns spawn, Have/Rot animation, visibility, and despawn.
if (args.Length != 6)
{
    Console.Error.WriteLine("usage: warpstarbuild <template PlKb.dat> <warpstar-mesh.json> <texture-dir> <warpstar-poses.json> <output.dat> <report.json>");
    return 2;
}
const string JointSymbol = "PlyKirbyWarpStar_joint";
const string AnimSymbol = "PlyKirbyWarpStar_animjoint";
const float Scale = 5f / 4.6f;
var template = new HSDRawFile(args[0]);
var fighter = template.Roots.Single(r => r.Name == "ftDataKirby").Data as SBM_FighterData
    ?? throw new Exception("ftDataKirby missing from template");
var article = fighter.Articles?.Articles.ElementAtOrDefault(1)
    ?? throw new Exception("Kirby Hammer article material template missing");
var materialTemplate = article.Model?.RootModelJoint?.Child?.Dobj?.Mobj
    ?? throw new Exception("Hammer material template missing");
var description = JsonDocument.Parse(File.ReadAllText(args[1])).RootElement;
var objects = description.GetProperty("objects").EnumerateArray().ToArray();
int textureSize = description.GetProperty("texture_size").GetInt32();
if (objects.Length != 5 || textureSize <= 0 || textureSize > 1024)
    throw new Exception("unexpected Warp Star model description");
var placement = new HSD_JOBJ { SX = 1, SY = 1, SZ = 1,
                               Flags = JOBJ_FLAG.CLASSICAL_SCALING }; // host world placement
var root = new HSD_JOBJ { SX = 1, SY = 1, SZ = 1,
                          Flags = JOBJ_FLAG.CLASSICAL_SCALING }; // Have
var rot = new HSD_JOBJ { SX = 1, SY = 1, SZ = 1,
                         TY = -2.14035f * Scale, TZ = -1.5f * Scale,
                         Flags = JOBJ_FLAG.CLASSICAL_SCALING }; // Rot source rest
placement.AddChild(root);
root.AddChild(rot);
var dobjs = new List<HSD_DOBJ>();
var generator = new POBJ_Generator { UseTriangleStrips = true };
var attrs = new[] { GXAttribName.GX_VA_POS, GXAttribName.GX_VA_NRM,
                    GXAttribName.GX_VA_TEX0 };
var images = new Dictionary<string, HSD_Image>();
foreach (var material in new[] { "star", "glow" })
{
    var raw = File.ReadAllBytes(Path.Combine(args[2], material + ".bgra"));
    if (raw.Length != textureSize * textureSize * 4)
        throw new Exception("bad Warp Star texture byte count: " + material);
    images[material] = new HSD_Image {
        ImageData = GXImageConverter.EncodeImage(raw, textureSize, textureSize,
                                                  GXTexFmt.RGB5A3, GXTlutFmt.RGB5A3, out _),
        Width = (short)textureSize, Height = (short)textureSize, Format = GXTexFmt.RGB5A3,
    };
}
var itemReport = new List<object>();
foreach (var piece in objects)
{
    string name = piece.GetProperty("name").GetString();
    string material = piece.GetProperty("material").GetString();
    if (material != "star" && material != "glow")
        throw new Exception("unexpected Warp Star material: " + material);
    var vertices = new List<GX_Vertex>();
    foreach (var triangle in piece.GetProperty("triangles").EnumerateArray())
    foreach (var vertex in triangle.EnumerateArray())
    {
        var p = vertex.GetProperty("p").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
        var n = vertex.GetProperty("n").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
        var uv = vertex.GetProperty("uv").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
        vertices.Add(new GX_Vertex {
            POS = new GXVector3(Scale * p[0], Scale * p[1], Scale * p[2]),
            NRM = new GXVector3(n[0], n[1], n[2]),
            TEX0 = new GXVector2(uv[0], uv[1]),
        });
    }
    // Both sides of the source glow quads need to be visible during descent.
    generator.CullMode = material == "glow" ? GenCullMode.None : GenCullMode.Back;
    var pobj = generator.CreatePOBJsFromTriangleList(vertices, attrs, null, null);
    var mobj = new HSD_MOBJ { _s = materialTemplate._s.DeepClone() };
    var texture = mobj.Textures ?? throw new Exception("Hammer material texture missing");
    texture.Next = null;
    texture.ImageData = images[material];
    texture.TlutData = null;
    texture.WrapS = GXWrapMode.CLAMP;
    texture.WrapT = GXWrapMode.CLAMP;
    mobj.Material.DiffuseColor = System.Drawing.Color.White;
    mobj.Material.AmbientColor = System.Drawing.Color.White;
    if (material == "glow")
    {
        mobj.RenderFlags |= RENDER_MODE.XLU | RENDER_MODE.ALPHA_MAT | RENDER_MODE.CONSTANT;
        texture.AlphaOperation = ALPHAMAP.MODULATE;
        mobj.PEDesc = new HSD_PEDesc {
            Flags = PIXEL_PROCESS_ENABLE.COLOR_UPDATE | PIXEL_PROCESS_ENABLE.ALPHA_UPDATE
                    | PIXEL_PROCESS_ENABLE.COMPARE | PIXEL_PROCESS_ENABLE.ZUPDATE,
            AlphaRef0 = 0, AlphaRef1 = 0, DestinationAlpha = 0,
            BlendMode = GXBlendMode.GX_BLEND, SrcFactor = GXBlendFactor.GX_BL_SRCALPHA,
            DstFactor = GXBlendFactor.GX_BL_INVSRCALPHA, BlendOp = GXLogicOp.GX_LO_SET,
            DepthFunction = GXCompareType.LEqual,
            AlphaComp0 = GXCompareType.GEqual, AlphaOp = GXAlphaOp.And,
            AlphaComp1 = GXCompareType.GEqual,
        };
    }
    dobjs.Add(new HSD_DOBJ { Pobj = pobj, Mobj = mobj });
    itemReport.Add(new { name, material, triangles = vertices.Count / 3,
                         pobjs = pobj.List.Count });
}
for (int i = 0; i < dobjs.Count - 1; i++) dobjs[i].Next = dobjs[i + 1];
rot.Dobj = dobjs[0];
generator.SaveChanges();
placement.UpdateFlags();
var output = new HSDRawFile();
output.Roots.Add(new HSDRootNode { Name = JointSymbol, Data = placement });
var poses = JsonDocument.Parse(File.ReadAllText(args[3])).RootElement;
int frames = poses.GetProperty("frames").GetInt32();
if (frames != 120)
    throw new Exception("expected 120-frame Warp Star Entry animation");
var animPlacement = new HSD_AnimJoint();
var animHave = new HSD_AnimJoint();
var animRot = new HSD_AnimJoint();
animPlacement.AddChild(animHave);
animHave.AddChild(animRot);
var trackTypes = new[] {
    JointTrackType.HSD_A_J_SCAX, JointTrackType.HSD_A_J_SCAY,
    JointTrackType.HSD_A_J_SCAZ, JointTrackType.HSD_A_J_ROTX,
    JointTrackType.HSD_A_J_ROTY, JointTrackType.HSD_A_J_ROTZ,
    JointTrackType.HSD_A_J_TRAX, JointTrackType.HSD_A_J_TRAY,
    JointTrackType.HSD_A_J_TRAZ,
};
var animTracks = new List<object>();
foreach (var (name, node) in new[] { ("Have", animHave), ("Rot", animRot) })
{
    var samples = poses.GetProperty("joints").GetProperty(name).EnumerateArray().ToArray();
    if (samples.Length != frames + 1)
        throw new Exception("Warp Star pose count mismatch: " + name);
    var descs = new List<HSD_FOBJDesc>();
    for (int axis = 0; axis < trackTypes.Length; axis++)
    {
        string property = axis < 3 ? "scale" : axis < 6 ? "rotation" : "translation";
        int component = axis % 3;
        var values = samples.Select(sample =>
            (float)sample.GetProperty(property)[component].GetDouble()).ToArray();
        var keys = new List<FOBJKey>();
        for (int frame = 0; frame < values.Length; frame++)
        {
            if (frame > 0 && frame < frames &&
                MathF.Abs(values[frame] - (values[frame - 1] + values[frame + 1]) * .5f) < 1e-5f)
                continue;
            keys.Add(new FOBJKey { Frame = frame, Value = values[frame],
                                   InterpolationType = GXInterpolationType.HSD_A_OP_LIN });
        }
        var track = new HSD_FOBJDesc();
        track.SetKeys(keys, (byte)trackTypes[axis]);
        descs.Add(track);
        animTracks.Add(new { bone = name, type = trackTypes[axis].ToString(), keys = keys.Count });
    }
    for (int i = 0; i < descs.Count - 1; i++) descs[i].Next = descs[i + 1];
    node.AOBJ = new HSD_AOBJ { EndFrame = frames, FObjDesc = descs[0] };
}
output.Roots.Add(new HSDRootNode { Name = AnimSymbol, Data = animPlacement });
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[4]))!);
output.Save(args[4]);
var checkedFile = new HSDRawFile(args[4]);
var checkedRoot = checkedFile.Roots.Single(r => r.Name == JointSymbol).Data as HSD_JOBJ
    ?? throw new Exception("Warp Star joint symbol missing after round-trip");
if (checkedRoot.TreeList.Count != 3 || checkedRoot.Child?.Child?.Dobj?.List.Count != 5 ||
    checkedRoot.Child.Child.Dobj.List.Any(d => d.Pobj == null || d.Mobj?.Textures?.ImageData == null))
    throw new Exception("Warp Star model failed structural round-trip");
foreach (var dobj in checkedRoot.Child.Child.Dobj.List)
foreach (var pobj in dobj.Pobj.List)
    if (pobj.SingleBoundJOBJ != null || (pobj.Flags & POBJ_FLAG.ENVELOPE) != 0)
        throw new Exception("Warp Star PObj must be rigid");
var checkedAnim = checkedFile.Roots.Single(r => r.Name == AnimSymbol).Data as HSD_AnimJoint
    ?? throw new Exception("Warp Star AnimJoint symbol missing after round-trip");
if (checkedAnim.TreeList.Count != 3 || checkedAnim.Child?.AOBJ?.EndFrame != frames ||
    checkedAnim.Child.Child?.AOBJ?.EndFrame != frames)
    throw new Exception("Warp Star animation failed structural round-trip");
var report = new { input = args[1], output = args[4], bytes = new FileInfo(args[4]).Length,
                   symbol = JointSymbol, joints = checkedRoot.TreeList.Count,
                   anim_symbol = AnimSymbol, anim_joints = checkedAnim.TreeList.Count,
                   anim_frames = frames, anim_tracks = animTracks,
                   dobjs = checkedRoot.Child.Child.Dobj.List.Count, scale = Scale,
                   joints_dfs = new[] { "Placement", "Have", "Rot" },
                   rot_rest = new[] { checkedRoot.Child.Child.TX, checkedRoot.Child.Child.TY,
                                      checkedRoot.Child.Child.TZ },
                   objects = itemReport,
                   host_required = "set Placement to fighter spawn, apply independent Have/Rot HSD AnimJoint, remove at frame120" };
File.WriteAllText(args[5], JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine(JsonSerializer.Serialize(report));
return 0;
