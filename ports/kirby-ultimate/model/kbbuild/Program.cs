using System.Text.Json;
using HSDRaw;
using HSDRaw.Common;
using HSDRaw.Common.Animation;
using HSDRaw.GX;
using HSDRaw.Tools;

// Replace only Kirby's body/arm/foot geometry in the stock costume archive.
// Its 46-joint tree, public symbols, materials, and material animations remain.
if (args.Length < 3 || args.Length > 6)
{
    Console.Error.WriteLine("usage: kbbuild <stock PlKb costume.dat> <retargeted mesh.json> <out costume.dat> [body-atlas.bgra] [skin.bgra] [face texture dir]");
    return 2;
}
var file = new HSDRawFile(args[0]);
var rootSymbol = file.Roots.Single(r => r.Name.EndsWith("_Share_joint")).Name;
var matanimSymbol = file.Roots.Single(r => r.Name.EndsWith("_Share_matanim_joint")).Name;
var root = file.Roots.First(r => r.Name == rootSymbol).Data as HSD_JOBJ
           ?? throw new Exception("stock Kirby joint root absent");
var joints = root.TreeList;
var dobjs = root.Dobj.List;
if (joints.Count != 46 || dobjs.Count < 20) throw new Exception("unexpected stock Kirby costume layout");
var description = JsonDocument.Parse(File.ReadAllText(args[1])).RootElement.GetProperty("dobjs");
var generator = new POBJ_Generator { UseTriangleStrips = true };
// Ultimate winding is outward-facing. Stock Kirby's PObj culls the opposite
// face; retaining that flag would expose the eye shell's untextured rear.
var windingMode = Environment.GetEnvironmentVariable("KB_FLIP") ?? "source";
var invertNormals = Environment.GetEnvironmentVariable("KB_INVERT_NORMALS") == "1";
var unlit = Environment.GetEnvironmentVariable("KB_UNLIT") == "1";
var cullMode = Environment.GetEnvironmentVariable("KB_CULL") ?? "back";
var eyeCullMode = Environment.GetEnvironmentVariable("KB_EYE_CULL") ?? cullMode;
var eyeYawDegrees = float.Parse(Environment.GetEnvironmentVariable("KB_EYE_YAW_DEG") ?? "0",
                                System.Globalization.CultureInfo.InvariantCulture);
var eyeYaw = eyeYawDegrees * MathF.PI / 180;
var eyeCos = MathF.Cos(eyeYaw);
var eyeSin = MathF.Sin(eyeYaw);
var attrs = new[] { GXAttribName.GX_VA_PNMTXIDX, GXAttribName.GX_VA_POS,
                    GXAttribName.GX_VA_NRM, GXAttribName.GX_VA_TEX0 };
var ibm = joints.Select(j => j.InverseWorldTransform).ToArray();
HSD_Image bodyAtlas = null;
if (args.Length >= 4)
{
    var raw = File.ReadAllBytes(args[3]);
    if (raw.Length != 128 * 128 * 4) throw new Exception("expected 128x128 BGRA atlas");
    bodyAtlas = new HSD_Image {
        ImageData = GXImageConverter.EncodeImage(raw, 128, 128, GXTexFmt.RGB5A3, GXTlutFmt.RGB5A3, out _),
        Width = 128, Height = 128, Format = GXTexFmt.RGB5A3,
    };
}
HSD_Image skinImage = null;
if (args.Length >= 5)
{
    var raw = File.ReadAllBytes(args[4]);
    if (raw.Length != 16 * 16 * 4) throw new Exception("expected 16x16 BGRA skin texture");
    skinImage = new HSD_Image {
        ImageData = GXImageConverter.EncodeImage(raw, 16, 16, GXTexFmt.RGB5A3, GXTlutFmt.RGB5A3, out _),
        Width = 16, Height = 16, Format = GXTexFmt.RGB5A3,
    };
}
var counts = new Dictionary<string, int>();
foreach (var key in description.EnumerateObject())
{
    int di = int.Parse(key.Name);
    if (di is not (0 or 1 or 3 or 4 or 6 or 7 or 18 or 19)) throw new Exception("unsupported DObj " + di);
    var flipWinding = windingMode == "reverse" || (windingMode == "mixed" && di is not (0 or 3));
    var vertices = new List<GX_Vertex>();
    var bones = new List<HSD_JOBJ[]>();
    var weights = new List<float[]>();
    foreach (var tri in key.Value.GetProperty("tris").EnumerateArray())
    foreach (var v in (flipWinding ? tri.EnumerateArray().Reverse() : tri.EnumerateArray()))
    {
        var p = v.GetProperty("p").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
        var n = v.GetProperty("n").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
        if (di is 0 or 3 && eyeYawDegrees != 0)
        {
            // Move the eye shell around the spherical body's Y axis while
            // retaining its distance from the surface. This tests whether
            // Melee's side camera needs a modest profile presentation angle.
            (p[0], p[2]) = (eyeCos * p[0] + eyeSin * p[2],
                            -eyeSin * p[0] + eyeCos * p[2]);
            (n[0], n[2]) = (eyeCos * n[0] + eyeSin * n[2],
                            -eyeSin * n[0] + eyeCos * n[2]);
        }
        if (invertNormals) for (int c = 0; c < 3; c++) n[c] = -n[c];
        var uv = v.GetProperty("uv").EnumerateArray().Select(x => (float)x.GetDouble()).ToArray();
        var influences = v.GetProperty("w").EnumerateArray()
            .Select(x => (joint: x[0].GetInt32(), weight: (float)x[1].GetDouble())).ToArray();
        if (influences.Length == 0 || influences.Length > 4) throw new Exception("bad skinning weights");
        if (influences.Length == 1)
        {
            // A single-weight HSD envelope consumes joint-local coordinates.
            var m = ibm[influences[0].joint] ?? throw new Exception("missing inverse bind");
            var q = new float[] {
                m.M11 * p[0] + m.M12 * p[1] + m.M13 * p[2] + m.M14,
                m.M21 * p[0] + m.M22 * p[1] + m.M23 * p[2] + m.M24,
                m.M31 * p[0] + m.M32 * p[1] + m.M33 * p[2] + m.M34 };
            var r = new float[] {
                m.M11 * n[0] + m.M12 * n[1] + m.M13 * n[2],
                m.M21 * n[0] + m.M22 * n[1] + m.M23 * n[2],
                m.M31 * n[0] + m.M32 * n[1] + m.M33 * n[2] };
            float length = MathF.Sqrt(r.Sum(x => x * x));
            if (length > 0) for (int c = 0; c < 3; c++) r[c] /= length;
            p = q; n = r;
        }
        vertices.Add(new GX_Vertex {
            POS = new GXVector3(p[0], p[1], p[2]),
            NRM = new GXVector3(n[0], n[1], n[2]),
            TEX0 = new GXVector2(uv[0], uv[1]),
        });
        bones.Add(influences.Select(x => joints[x.joint]).ToArray());
        weights.Add(influences.Select(x => x.weight).ToArray());
    }
    var flags = dobjs[di].Pobj?.Flags ?? 0;
    var selectedCullMode = di is 0 or 3 ? eyeCullMode : cullMode;
    generator.CullMode = selectedCullMode == "back" ? GenCullMode.Back
        : selectedCullMode == "front" ? GenCullMode.Front
        : selectedCullMode == "none" ? GenCullMode.None
        : (flags & POBJ_FLAG.CULLFRONT) != 0 && (flags & POBJ_FLAG.CULLBACK) != 0
        ? GenCullMode.FrontAndBack
        : (flags & POBJ_FLAG.CULLFRONT) != 0 ? GenCullMode.Front
        : (flags & POBJ_FLAG.CULLBACK) != 0 ? GenCullMode.Back : GenCullMode.None;
    dobjs[di].Pobj = generator.CreatePOBJsFromTriangleList(vertices, attrs, bones, weights);
    if (di is 0 or 1 or 3 or 4)
    {
        // Kirby's arm MObj uses his tiny solid-pink skin texture. The stock
        // body DObjs sample face/eye atlases that do not match Ultimate UVs.
        dobjs[di].Mobj = new HSD_MOBJ { _s = dobjs[6].Mobj._s.DeepClone() };
        if (bodyAtlas != null)
        {
            var texture = dobjs[di].Mobj.Textures;
            texture.ImageData = bodyAtlas;
            texture.TlutData = null;
            texture.WrapS = GXWrapMode.CLAMP;
            texture.WrapT = GXWrapMode.CLAMP;
        }
    }
    if (di is 6 or 18 && bodyAtlas != null)
    {
        var texture = dobjs[di].Mobj.Textures;
        texture.ImageData = bodyAtlas;
        texture.TlutData = null;
        texture.WrapS = GXWrapMode.CLAMP;
        texture.WrapT = GXWrapMode.CLAMP;
    }
    if (di is 7 or 19 && skinImage != null)
    {
        var texture = dobjs[di].Mobj.Textures;
        texture.ImageData = skinImage;
        texture.TlutData = null;
        texture.WrapS = GXWrapMode.CLAMP;
        texture.WrapT = GXWrapMode.CLAMP;
    }
    if (unlit)
    {
        var material = dobjs[di].Mobj;
        material.RenderFlags = (material.RenderFlags & ~(RENDER_MODE.DIFFUSE | RENDER_MODE.SPECULAR | RENDER_MODE.VERTEX))
                             | RENDER_MODE.CONSTANT;
        material.Material.DiffuseColor = System.Drawing.Color.White;
        material.Material.AmbientColor = System.Drawing.Color.White;
    }
    counts[key.Name] = vertices.Count / 3;
}
// These stock face/body patches would duplicate the whole Ultimate body.
foreach (int di in new[] { 2, 5 }) dobjs[di].Pobj = null;
// Kirby switches to DObjs 8..17 at distance. Match the established Brawl
// Kirby low-from-high mapping so LAB and normal play display this costume.
var lowFromHigh = new Dictionary<int, int> {
    [8] = 1, [9] = 2, [10] = 0,
    [11] = 4, [12] = 5, [13] = 3,
    [14] = 6, [15] = 7, [16] = 18, [17] = 19,
};
foreach (var (low, high) in lowFromHigh)
{
    dobjs[low].Pobj = dobjs[high].Pobj;
    if (dobjs[high].Pobj != null)
        dobjs[low].Mobj = new HSD_MOBJ { _s = dobjs[high].Mobj._s.DeepClone() };
}
// Keep the stock texture animation nodes: fighter spawn expects an AObj on
// Kirby's costume TObj indices even when an eye DObj has no geometry.
if (args.Length == 6)
{
    var faceImages = new Dictionary<string, HSD_Image>();
    foreach (var name in new[] { "w", "d", "c", "f" })
    {
        var raw = File.ReadAllBytes(Path.Combine(args[5], $"face-{name}.bgra"));
        if (raw.Length != 128 * 128 * 4) throw new Exception($"bad {name} face atlas size");
        faceImages[name] = new HSD_Image {
            ImageData = GXImageConverter.EncodeImage(raw, 128, 128, GXTexFmt.RGB5A3, GXTlutFmt.RGB5A3, out _),
            Width = 128, Height = 128, Format = GXTexFmt.RGB5A3,
        };
    }
    var matanim = file.Roots.First(r => r.Name == matanimSymbol).Data as HSD_MatAnimJoint
        ?? throw new Exception("stock Kirby material animation root absent");
    var animations = matanim.MaterialAnimation.List;
    foreach (int di in new[] { 3, 5 })
    {
        var ta = animations[di].TextureAnimation
            ?? throw new Exception($"stock eye texture animation absent on DObj {di}");
        var buffers = new HSDArrayAccessor<HSD_TexBuffer>();
        foreach (var name in new[] { "w", "d", "c", "f" })
            buffers.Add(new HSD_TexBuffer { Data = faceImages[name] });
        ta.ImageBuffers = buffers;
        ta.TlutBuffers = null;
        var aobj = ta.AnimationObject ?? throw new Exception("stock eye texture AObj absent");
        var tracks = aobj.FObjDesc.List.Where(track => (int)track.JointTrackType != 10).ToList();
        for (int i = 0; i < tracks.Count; i++) tracks[i].Next = i + 1 < tracks.Count ? tracks[i + 1] : null;
        aobj.FObjDesc = tracks.Count > 0 ? tracks[0] : null;
    }
}
generator.SaveChanges();
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(args[2]))!);
file.Save(args[2]);
var reread = new HSDRawFile(args[2]);
var rereadRoot = reread.Roots.First(r => r.Name == rootSymbol).Data as HSD_JOBJ;
if (rereadRoot == null || rereadRoot.TreeList.Count != 46 || rereadRoot.Dobj.List.Count != dobjs.Count)
    throw new Exception("costume reload failed");
if (!reread.Roots.Any(r => r.Name == matanimSymbol))
    throw new Exception("stock material animation public absent");
var checkedMatanim = reread.Roots.First(r => r.Name == matanimSymbol).Data as HSD_MatAnimJoint;
foreach (int di in new[] { 3, 5 })
{
    var eye = checkedMatanim?.MaterialAnimation?.List[di]?.TextureAnimation;
    if (eye?.AnimationObject == null || eye.ImageCount != 4)
        throw new Exception($"eye DObj {di} lost its four-frame texture animation");
}
Console.WriteLine(JsonSerializer.Serialize(new {
    file = args[2], bytes = new FileInfo(args[2]).Length,
    joints = rereadRoot.TreeList.Count, dobjs = rereadRoot.Dobj.List.Count,
    triangles = counts,
}));
return 0;
