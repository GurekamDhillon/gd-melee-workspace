using System.Text.Json;
using HSDRaw;
using HSDRaw.Common;
using HSDRaw.GX;
using HSDRaw.Tools;

// Melee has five Stone visibility states at two LODs. Replace those states
// with five Ultimate shapes without changing the costume's joint/matanim
// topology. The sixth Ultimate shape is held until the visibility table grows.
if (args.Length != 5 && args.Length != 6)
{
    Console.Error.WriteLine("usage: stonebuild <input costume> <stone-mesh.json> <texture dir> <output costume> <report.json> [--append-sixth]");
    return 2;
}
bool appendSixth = args.Length == 6 && args[5] == "--append-sixth";
if (args.Length == 6 && !appendSixth) throw new Exception("unknown Stone option");
var file = new HSDRawFile(args[0]);
var jointRoot = file.Roots.Single(r => r.Name.EndsWith("_Share_joint"));
var matanimRoot = file.Roots.Single(r => r.Name.EndsWith("_Share_matanim_joint"));
var root = jointRoot.Data as HSD_JOBJ ?? throw new Exception("costume root JObj missing");
var joints = root.TreeList;
var dobjs = joints.SelectMany(j => j.Dobj?.List ?? new List<HSD_DOBJ>()).ToList();
if (joints.Count != 46 || dobjs.Count != 42 ||
    dobjs.Skip(20).Take(22).Any(d => !joints[6].Dobj.List.Contains(d)))
    throw new Exception("unexpected Kirby costume topology");

var source = JsonDocument.Parse(File.ReadAllText(args[1])).RootElement;
var shapes = source.GetProperty("shapes").EnumerateArray()
    .ToDictionary(e => e.GetProperty("name").GetString()!, e => e);
var states = new List<(string name, int[] high, int[] low)> {
    (name: "100t", high: new[] {20, 21, 22}, low: new[] {31, 32, 33}),
    (name: "tbox", high: new[] {23, 24}, low: new[] {34, 35}),
    (name: "dosun", high: new[] {25, 26}, low: new[] {36, 37}),
    (name: "kirby", high: new[] {27, 28, 29}, low: new[] {38, 39, 40}),
    (name: "ppon", high: new[] {30}, low: new[] {41}),
};
if (appendSixth)
{
    // Body JObj6 owns the final 22 DObjs. Appending after its tail assigns
    // global indices 42/43 without disturbing the five stock visibility sets.
    if (joints[6].Dobj.List.Count != 22)
        throw new Exception("Stone DObjs are not the final body DObjs");
    for (int i = 0; i < 2; i++)
    {
        var added = new HSD_DOBJ();
        joints[6].Dobj.Add(added);
        dobjs.Add(added);
    }
    states.Add(("hammer", new[] {42}, new[] {43}));
}
if (shapes.Count != 6 || states.Any(s => !shapes.ContainsKey(s.name)))
    throw new Exception("expected all six Ultimate Stone meshes");
var textureSize = source.GetProperty("texture_size").GetInt32();
var attrs = new[] { GXAttribName.GX_VA_POS, GXAttribName.GX_VA_NRM,
                    GXAttribName.GX_VA_TEX0 };
var generator = new POBJ_Generator { UseTriangleStrips = true,
                                      CullMode = GenCullMode.Back };
var reportStates = new List<object>();
foreach (var state in states)
{
    var shape = shapes[state.name];
    var vertices = new List<GX_Vertex>();
    foreach (var triangle in shape.GetProperty("triangles").EnumerateArray())
    foreach (var vertex in triangle.EnumerateArray())
    {
        var p = vertex.GetProperty("p").EnumerateArray().Select(e => (float)e.GetDouble()).ToArray();
        var n = vertex.GetProperty("n").EnumerateArray().Select(e => (float)e.GetDouble()).ToArray();
        var uv = vertex.GetProperty("uv").EnumerateArray().Select(e => (float)e.GetDouble()).ToArray();
        vertices.Add(new GX_Vertex {
            POS = new GXVector3(p[0], p[1], p[2]),
            NRM = new GXVector3(n[0], n[1], n[2]),
            TEX0 = new GXVector2(uv[0], uv[1]),
        });
    }
    var pobj = generator.CreatePOBJsFromTriangleList(vertices, attrs, null, null);
    if (pobj == null) throw new Exception($"no PObj for {state.name}");
    var textureRaw = File.ReadAllBytes(Path.Combine(args[2], state.name + ".bgra"));
    if (textureRaw.Length != textureSize * textureSize * 4)
        throw new Exception($"bad BGRA texture for {state.name}");
    var image = new HSD_Image {
        ImageData = GXImageConverter.EncodeImage(textureRaw, textureSize, textureSize,
                                                  GXTexFmt.RGB5A3, GXTlutFmt.RGB5A3, out _),
        Width = (short)textureSize, Height = (short)textureSize, Format = GXTexFmt.RGB5A3,
    };
    // Stock DObj23 is a simple opaque diffuse/texture material. Clone it so
    // the six different source atlases cannot alias each other or the body.
    var material = new HSD_MOBJ { _s = dobjs[23].Mobj._s.DeepClone() };
    var texture = material.Textures ?? throw new Exception("stock Stone texture missing");
    texture.ImageData = image;
    texture.TlutData = null;
    texture.WrapS = GXWrapMode.CLAMP;
    texture.WrapT = GXWrapMode.CLAMP;
    foreach (var set in new[] { state.high, state.low })
    {
        dobjs[set[0]].Pobj = pobj;
        dobjs[set[0]].Mobj = material;
        foreach (var index in set.Skip(1)) dobjs[index].Pobj = null;
    }
    reportStates.Add(new { name = state.name, triangles = vertices.Count / 3,
                           high = state.high, low = state.low,
                           pobjs = pobj.List.Count });
}
generator.SaveChanges();
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[3]))!);
file.Save(args[3]);
var checkedFile = new HSDRawFile(args[3]);
var checkedRoot = checkedFile.Roots.Single(r => r.Name == jointRoot.Name).Data as HSD_JOBJ
    ?? throw new Exception("output costume root missing");
var checkedDobjs = checkedRoot.TreeList.SelectMany(j => j.Dobj?.List ?? new List<HSD_DOBJ>()).ToList();
if (checkedRoot.TreeList.Count != 46 || checkedDobjs.Count != (appendSixth ? 44 : 42) ||
    checkedFile.Roots.All(r => r.Name != matanimRoot.Name) ||
    states.Any(s => checkedDobjs[s.high[0]].Pobj == null || checkedDobjs[s.low[0]].Pobj == null ||
                    s.high.Skip(1).Any(i => checkedDobjs[i].Pobj != null) ||
                    s.low.Skip(1).Any(i => checkedDobjs[i].Pobj != null)))
    throw new Exception("Stone costume failed structural reload");
var report = new { input = args[0], output = args[3], bytes = new FileInfo(args[3]).Length,
                   joints = checkedRoot.TreeList.Count, dobjs = checkedDobjs.Count,
                   states = reportStates, pending_sixth = appendSixth ? null : "hammer" };
File.WriteAllText(args[4], JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine(JsonSerializer.Serialize(report));
return 0;
