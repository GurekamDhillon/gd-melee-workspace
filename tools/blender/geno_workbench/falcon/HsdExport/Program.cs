// Headless driver for HSDRaw + HSDRawViewer's exporters (no GUI).
//   hsdexport <model.dat> <out.glb|.smd|.dae> [--no-textures]
//   hsdexport --anim <model.dat> <anims.dat> <plan.json> <out_dir> <ClipName|all>...   (one SMD per clip)
using System;
using System.IO;
using System.Text.Json;
using System.Linq;
using HSDRaw;
using HSDRaw.Common;
using HSDRaw.Common.Animation;
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
        Console.WriteLine("anim " + name + " frames=" + mgr.FrameCount);
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
}
