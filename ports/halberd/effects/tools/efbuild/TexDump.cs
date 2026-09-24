using HSDRaw; using HSDRaw.Common; using HSDRaw.Melee.Ef; using HSDRaw.Tools;
static class TexDump {
  public static void Run(string path, int model, string outDir){
    var f=new HSDRawFile(path); Directory.CreateDirectory(outDir);
    foreach(var r in f.Roots){ if(!r.Name.EndsWith("DataTable")) continue; var t=new SBM_EffectTable(); t._s=r.Data._s;
      var m=t.Models[model]; int k=0;
      foreach(var j in m.RootJoint.TreeList) if(j.Dobj!=null) foreach(var d in j.Dobj.List){ var im=d.Mobj.Textures.ImageData;
        var rgba=GXImageConverter.DecodeTPL(im.Format, im.Width, im.Height, im.ImageData);
        // BGRA -> write raw ppm-ish: dump as .rgba with header text
        File.WriteAllBytes(Path.Combine(outDir, $"m{model}_{k}_{im.Format}_{im.Width}x{im.Height}.bgra"), rgba); k++; } } } }
