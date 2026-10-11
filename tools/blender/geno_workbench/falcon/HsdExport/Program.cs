// Headless driver for HSDRaw + HSDRawViewer's exporters (no GUI).
//   hsdexport <model.dat> <out.glb|.smd|.dae> [--no-textures]
//   hsdexport --parts <fighterdata.dat> <model.dat> <out.json>   (model-part visibility tables + DObj layout)
//   hsdexport --anim <model.dat> <anims.dat> <plan.json> <out_dir> <ClipName|all>...   (one SMD per clip, plus <Clip>.scale.json when the clip animates scale)
using System;
using System.IO;
using System.Text.Json;
using System.Linq;
using HSDRaw;
using HSDRaw.Common;
using HSDRaw.Common.Animation;
using HSDRaw.Melee.Pl;
using System.Collections.Generic;
using System.Text;
using HSDRawViewer.Converters;
using HSDRawViewer.Converters.Animation;
using HSDRawViewer.Rendering;
using HSDRawViewer.Tools.Animation;
static class P {
  static HSD_JOBJ Root(string path) {
    var f = new HSDRawFile(path);
    foreach (var r in f.Roots) if (r.Data is HSD_JOBJ j) return j;
    throw new Exception("no JOBJ root in " + path);
  }
  [STAThread] static int Main(string[] a) {
    if (a.Length > 0 && a[0] == "--parts") return Parts(a[1], a[2], a[3]);
    if (a.Length > 0 && a[0] == "--anim") {
      // --anim <model.dat> <anims.dat> <plan.json> <out_dir> <ClipName|all>...
      // The anim file is a run of standalone figatree DATs; plan.json bank.clips gives each one's offset/bytes.
      var root = Root(a[1]);
      var all = File.ReadAllBytes(a[2]);
      var clips = JsonDocument.Parse(File.ReadAllText(a[3])).RootElement.GetProperty("bank").GetProperty("clips");
      Directory.CreateDirectory(a[4]);
      var names = a.Skip(5).ToList();
      if (names.Contains("all")) names = clips.EnumerateObject().Select(c => c.Name).ToList();
      int bad = 0;
      foreach (var name in names) {
        if (!clips.TryGetProperty(name, out var c)) { Console.Error.WriteLine("no clip " + name); bad++; continue; }
        int off = c.GetProperty("offset").GetInt32(), len = c.GetProperty("bytes").GetInt32();
        var slice = new byte[len]; Array.Copy(all, off, slice, 0, len);
        var f = new HSDRawFile(slice);
        var node = f.Roots.FirstOrDefault(r => r.Data is HSD_FigaTree);
        if (node == null) { Console.Error.WriteLine("no figatree in " + name); bad++; continue; }
        var mgr = new JointAnimManager((HSD_FigaTree)node.Data);
        SMDConv.ExportAnimationToSMD(Path.Combine(a[4], name + ".smd"), root, new JointMap(), mgr);
        // The SMD format has no scale channel, so SMDConv drops every HSD_A_J_SCA* track: Falcon's clips squash and
        // stretch their leg/arm joints (and the game applies it), so the Blender rig would play them unscaled and the
        // skinned meshes deform differently from the game. Sidecar: per joint, the scale at every frame 0..FrameCount
        // (the same sampling the SMD uses), an untracked axis keeping the joint's rest scale.
        string scaleJson = ScaleSidecar(root, mgr);
        string scalePath = Path.Combine(a[4], name + ".scale.json");
        if (scaleJson != null) File.WriteAllText(scalePath, scaleJson); else if (File.Exists(scalePath)) File.Delete(scalePath);
        Console.WriteLine("anim " + name + " frames=" + mgr.FrameCount + (scaleJson != null ? " scale=yes" : ""));
      }
      return bad == 0 ? 0 : 4;
    }
    var jobj = Root(a[0]);
    Console.WriteLine("joints " + jobj.TreeList.Count);
    var s = new ModelExportSettings();
    if (a.Contains("--no-textures")) s.ExportTextures = false;
    ModelExporter.ExportFile(a[1], jobj, s, new JointMap());
    Console.WriteLine("exported " + a[1]);
    return 0;
  }

  static string ScaleSidecar(HSD_JOBJ root, JointAnimManager mgr) {
    var jl = root.TreeList;
    var inv = System.Globalization.CultureInfo.InvariantCulture;
    var sb = new StringBuilder("{\"frames\":" + mgr.FrameCount + ",\"joints\":{");
    bool first = true;
    for (int i = 0; i < mgr.NodeCount && i < jl.Count; i++) {
      var tr = mgr.Nodes[i].Tracks;
      var sx = tr.FirstOrDefault(t => t.JointTrackType == JointTrackType.HSD_A_J_SCAX);
      var sy = tr.FirstOrDefault(t => t.JointTrackType == JointTrackType.HSD_A_J_SCAY);
      var sz = tr.FirstOrDefault(t => t.JointTrackType == JointTrackType.HSD_A_J_SCAZ);
      if (sx == null && sy == null && sz == null) continue;
      sb.Append((first ? "" : ",") + "\"" + i + "\":[");
      for (int f = 0; f <= mgr.FrameCount; f++) {
        float x = sx != null ? sx.GetValue(f) : jl[i].SX, y = sy != null ? sy.GetValue(f) : jl[i].SY, z = sz != null ? sz.GetValue(f) : jl[i].SZ;
        sb.Append((f == 0 ? "[" : ",[") + x.ToString("0.#######", inv) + "," + y.ToString("0.#######", inv) + "," + z.ToString("0.#######", inv) + "]");
      }
      sb.Append("]");
      first = false;
    }
    sb.Append("}}");
    return first ? null : sb.ToString();
  }

  // The fighter's model-part visibility tables (ftData.x8, read by ftParts_8007487C): per costume row, per LOD
  // table (high, low, metal, metal main), per model part, per state, the DObj indices that state shows. DObj
  // index = position in the model tree walked joint by joint, each joint's DObj list in order (fp->dobj_list).
  // names = what the glTF exporter calls that DObj: Joint_0_Object_<index> on the root, Joint_<j>_Object_<rank>_SINGLE elsewhere.
  static int Parts(string dataPath, string modelPath, string outPath) {
    var fd = new HSDRawFile(dataPath).Roots.Select(r => r.Data).OfType<SBM_FighterData>().First();
    var jl = Root(modelPath).TreeList;
    var sb = new StringBuilder("{\"dobjs\":[");
    int n = 0; bool first = true;
    for (int j = 0; j < jl.Count; j++) {
      if (jl[j].Dobj == null) continue;
      int rank = 0;
      foreach (var d in jl[j].Dobj.List) {
        string name = j == 0 ? "Joint_0_Object_" + n : "Joint_" + j + "_Object_" + rank + "_SINGLE";
        // The glTF export drops the material's alpha: the visor (DObj 22 on Falcon) is a 0.4-alpha XLU black glass.
        var mat = d.Mobj == null ? null : d.Mobj.Material;
        string alpha = mat != null && mat.Alpha < 0.999f ? ",\"alpha\":" + mat.Alpha.ToString("0.###", System.Globalization.CultureInfo.InvariantCulture) : "";
        // POBJ cull flags (the glTF export drops them): CULLFRONT is the engine's usual one-sided surface.
        bool cullFront = d.Pobj != null && d.Pobj.List.Any(pp => pp.Flags.HasFlag(HSDRaw.Common.POBJ_FLAG.CULLFRONT));
        string cull = cullFront ? ",\"cull\":\"front\"" : "";
        sb.Append((first ? "" : ",") + "{\"index\":" + n + ",\"joint\":" + j + ",\"rank\":" + rank + ",\"name\":\"" + name + "\"" + alpha + cull + "}");
        first = false; n++; rank++;
      }
    }
    var t = fd.ModelLookupTables;
    int parts = t.VisibilityLookupLength;
    sb.Append("],\"model_num\":" + parts + ",\"rows\":[");
    int rows = 0;
    for (int c = 0; c < 64; c++) {
      SBM_CostumeLookupTable e;
      try { e = t.CostumeVisibilityLookups[c]; } catch { break; }
      if (e == null || e.HighPoly == null || e.HighPoly._s == null) break;   // rows past the real ones read as null; the game then falls back to row 0
      rows++;
    }
    for (int c = 0; c < rows; c++) {
      var e = t.CostumeVisibilityLookups[c];
      sb.Append((c == 0 ? "" : ",") + "{\"costume\":" + c + ",\"lods\":{");
      var lods = new[] { ("high", e.HighPoly), ("low", e.LowPoly), ("metal", e.MetalPoly), ("metal_main", e.MetalMainModel) };
      for (int l = 0; l < lods.Length; l++) {
        sb.Append((l == 0 ? "" : ",") + "\"" + lods[l].Item1 + "\":");
        var tb = lods[l].Item2;
        if (tb == null || tb._s == null) { sb.Append("null"); continue; }
        sb.Append("[");
        for (int m = 0; m < parts; m++) {
          var lt = tb[m];
          sb.Append((m == 0 ? "[" : ",[") );
          for (int k = 0; k < lt.Count; k++)
            sb.Append((k == 0 ? "[" : ",[") + string.Join(",", lt.LookupEntries[k].Entries) + "]");
          sb.Append("]");
        }
        sb.Append("]");
      }
      sb.Append("}}");
    }
    sb.Append("]}");
    File.WriteAllText(outPath, sb.ToString());
    Console.WriteLine("parts dobjs=" + n + " model_num=" + parts + " rows=" + rows);
    return 0;
  }
}
