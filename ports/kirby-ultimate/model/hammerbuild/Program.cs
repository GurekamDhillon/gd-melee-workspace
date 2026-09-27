using System.Text.Json;
using HSDRaw;
using HSDRaw.Common;
using HSDRaw.GX;
using HSDRaw.Melee.Pl;
using HSDRaw.Tools;

// Replace Kirby's hammer article geometry inside an existing PlKb.dat.
// Fighter status logic, article parameters, joints, animation, and hitboxes stay intact.
if (args.Length != 2 && args.Length != 5)
{
    Console.Error.WriteLine("usage: hammerbuild <input PlKb.dat> <output report.json> [hammer-mesh.json texture-dir output PlKb.dat]");
    return 2;
}
var file = new HSDRawFile(args[0]);
var fighter = file.Roots.Single(r => r.Name == "ftDataKirby").Data as SBM_FighterData
    ?? throw new Exception("ftDataKirby missing");
var articles = fighter.Articles?.Articles ?? throw new Exception("fighter articles missing");
if (articles.Length < 2 || articles[1]?.Model?.RootModelJoint == null)
    throw new Exception("Kirby hammer article 1 missing");
var hammer = articles[1];
var root = hammer.Model.RootModelJoint;
var jobs = root.TreeList;
var dobjs = root.Child?.Dobj?.List ?? throw new Exception("hammer mesh child missing");
var original = new {
    joints = jobs.Count,
    root_translation = new[] { root.TX, root.TY, root.TZ },
    child_translation = new[] { root.Child.TX, root.Child.TY, root.Child.TZ },
    root_flags = root.Flags.ToString(),
    child_flags = root.Child.Flags.ToString(),
    dobjs = dobjs.Select((d, i) => new {
        index = i,
        pobjs = d.Pobj?.List.Count ?? 0,
        pobj_flags = d.Pobj?.Flags.ToString(),
        bound_joint_flags = d.Pobj?.SingleBoundJOBJ?.Flags.ToString(),
        textures = d.Mobj?.Textures?.List.Count ?? 0,
        render_flags = d.Mobj?.RenderFlags.ToString(),
        ambient = d.Mobj?.Material == null ? null : new[] {
            (int)d.Mobj.Material.AMB_R, (int)d.Mobj.Material.AMB_G,
            (int)d.Mobj.Material.AMB_B, (int)d.Mobj.Material.AMB_A },
        diffuse = d.Mobj?.Material == null ? null : new[] {
            (int)d.Mobj.Material.DIF_R, (int)d.Mobj.Material.DIF_G,
            (int)d.Mobj.Material.DIF_B, (int)d.Mobj.Material.DIF_A },
        image_size = d.Mobj?.Textures?.ImageData == null ? null :
            new[] { (int)d.Mobj.Textures.ImageData.Width, (int)d.Mobj.Textures.ImageData.Height },
        bounds = d.Pobj == null ? null : d.Pobj.List
            .SelectMany(p => p.ToDisplayList().Vertices)
            .Aggregate(new[] { float.PositiveInfinity, float.PositiveInfinity, float.PositiveInfinity,
                               float.NegativeInfinity, float.NegativeInfinity, float.NegativeInfinity },
                (b, v) => {
                    b[0] = MathF.Min(b[0], v.POS.X); b[1] = MathF.Min(b[1], v.POS.Y);
                    b[2] = MathF.Min(b[2], v.POS.Z); b[3] = MathF.Max(b[3], v.POS.X);
                    b[4] = MathF.Max(b[4], v.POS.Y); b[5] = MathF.Max(b[5], v.POS.Z);
                    return b;
                }),
    }).ToArray(),
    bone_count = hammer.Model.BoneCount,
    bone_attach_id = hammer.Model.BoneAttachID,
    model_scale = hammer.Parameters?.ModelScale,
    states = hammer.ItemState?.Array.Select((state, i) => new {
        index = i,
        has_matanim = state.MatAnimJoint != null,
        matanim_nodes = state.MatAnimJoint?.TreeList.Count ?? 0,
    }).ToArray(),
};
if (args.Length == 2)
{
    Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[1]))!);
    File.WriteAllText(args[1], JsonSerializer.Serialize(original, new JsonSerializerOptions { WriteIndented = true }));
    Console.WriteLine(JsonSerializer.Serialize(original));
    return 0;
}
if (jobs.Count != 2 || dobjs.Count < 2)
    throw new Exception("unexpected stock hammer JObj/DObj layout");
var description = JsonDocument.Parse(File.ReadAllText(args[2])).RootElement;
var pieces = description.GetProperty("objects").EnumerateArray().ToArray();
int textureSize = description.GetProperty("texture_size").GetInt32();
bool woodOnly = Environment.GetEnvironmentVariable("KB_HAMMER_WOOD_ONLY") == "1";
if (pieces.Length != 2 || textureSize <= 0 || textureSize > 1024)
    throw new Exception("unexpected Ultimate hammer description");
var generator = new POBJ_Generator { UseTriangleStrips = true };
// The stock hammer is a rigid DObj with no PObj envelope. Its two joints do
// not form an HSD skeleton; an enveloped PObj trips displayfunc.c:262.
var attrs = new[] { GXAttribName.GX_VA_POS, GXAttribName.GX_VA_NRM,
                    GXAttribName.GX_VA_TEX0 };
var result = new List<object>();
for (int i = 0; i < (woodOnly ? 1 : pieces.Length); i++)
{
    var piece = pieces[i];
    var material = piece.GetProperty("material").GetString();
    if (material != (i == 0 ? "def" : "metal"))
        throw new Exception("hammer material order mismatch");
    var vertices = new List<GX_Vertex>();
    foreach (var triangle in piece.GetProperty("triangles").EnumerateArray())
    foreach (var vertex in triangle.EnumerateArray())
    {
        var p = vertex.GetProperty("p").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
        var n = vertex.GetProperty("n").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
        var uv = vertex.GetProperty("uv").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
        // Ultimate hammer winding and normals face outward. Keeping the stock
        // front-cull flag exposed the reverse shell and obscured the star art.
        vertices.Add(new GX_Vertex {
            POS = new GXVector3(p[0], p[1], p[2]),
            NRM = new GXVector3(n[0], n[1], n[2]),
            TEX0 = new GXVector2(uv[0], uv[1]),
        });
    }
    generator.CullMode = GenCullMode.Back;
    dobjs[i].Pobj = generator.CreatePOBJsFromTriangleList(vertices, attrs, null, null);
    var raw = File.ReadAllBytes(Path.Combine(args[3], material + ".bgra"));
    if (raw.Length != textureSize * textureSize * 4)
        throw new Exception("bad hammer BGRA texture size");
    var image = new HSD_Image {
        ImageData = GXImageConverter.EncodeImage(raw, textureSize, textureSize,
                                                  GXTexFmt.RGB5A3, GXTlutFmt.RGB5A3, out _),
        Width = (short)textureSize, Height = (short)textureSize, Format = GXTexFmt.RGB5A3,
    };
    // Deep clone: some stock DObjs may share material/texture references.
    dobjs[i].Mobj = new HSD_MOBJ { _s = dobjs[i].Mobj._s.DeepClone() };
    var texture = dobjs[i].Mobj.Textures ?? throw new Exception("hammer material texture missing");
    texture.ImageData = image;
    texture.TlutData = null;
    texture.WrapS = GXWrapMode.CLAMP;
    texture.WrapT = GXWrapMode.CLAMP;
    result.Add(new { material, triangles = vertices.Count / 3,
                     pobjs = dobjs[i].Pobj.List.Count });
}
for (int i = woodOnly ? 1 : pieces.Length; i < dobjs.Count; i++) dobjs[i].Pobj = null;
generator.SaveChanges();
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[4]))!);
file.Save(args[4]);
var reread = new HSDRawFile(args[4]);
var checkedFighter = reread.Roots.Single(r => r.Name == "ftDataKirby").Data as SBM_FighterData
    ?? throw new Exception("hammer output lost ftDataKirby");
var checkedHammer = checkedFighter.Articles.Articles[1];
var checkedRoot = checkedHammer.Model.RootModelJoint;
var checkedDobjs = checkedRoot.Child.Dobj.List;
if (checkedRoot.TreeList.Count != 2 || checkedDobjs.Count != dobjs.Count ||
    checkedDobjs[0].Pobj == null || (woodOnly ? checkedDobjs[1].Pobj != null : checkedDobjs[1].Pobj == null))
    throw new Exception("hammer article reload check failed");
foreach (var dobj in checkedDobjs.Take(woodOnly ? 1 : 2))
foreach (var pobj in dobj.Pobj.List)
    if (pobj.SingleBoundJOBJ != null || (pobj.Flags & POBJ_FLAG.ENVELOPE) != 0 ||
        pobj.ToGXAttributes().Any(a => a.AttributeName == GXAttribName.GX_VA_PNMTXIDX))
        throw new Exception("hammer PObj must remain rigid like the stock article");
for (int i = 0; i < (woodOnly ? 1 : 2); i++)
    File.WriteAllBytes(Path.Combine(args[3], (i == 0 ? "def" : "metal") + "-decoded.rgba"),
                       checkedDobjs[i].Mobj.Textures.GetDecodedImageData());
var report = new { input = args[0], output = args[4], bytes = new FileInfo(args[4]).Length,
                   original, wood_only = woodOnly, converted = result, joints = checkedRoot.TreeList.Count,
                   dobjs = checkedDobjs.Count };
File.WriteAllText(args[1], JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine(JsonSerializer.Serialize(report));
return 0;
