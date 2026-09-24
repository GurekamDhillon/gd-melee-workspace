using HSDRaw; using HSDRaw.Common; using HSDRaw.Melee.Ef; using HSDRaw.Tools;
static class PtclDump {
  public static void Run(string path, int max){
    var f=new HSDRawFile(path);
    foreach(var r in f.Roots){ if(!r.Name.EndsWith("DataTable")) continue; var t=new SBM_EffectTable(); t._s=r.Data._s;
      var pg=t.Particles; if(pg==null) continue; Console.WriteLine($"group ver {pg.Unknown1:X} start {pg.EffectIDStart} n {pg.GeneratorCount}");
      var tg=t.TextureGraphics; if(tg!=null){ int i=0; foreach(var x in tg.ParticleImages) Console.WriteLine($"  texg{i++} {x.ImageFormat} {x.Width}x{x.Height} x{x.ImageCount}"); }
      int gi=0; foreach(var g in pg.Generators){ if(gi>=max) break;
        Console.WriteLine($" gen{gi++} {g.TypeShape} flags {g.Flags} texg {g.TexGroup} genlife {g.GenLife} life {g.Life} kind {g.Kind} grav {g.Gravity} fric {g.Friction} v({g.VX},{g.VY},{g.VZ}) rad {g.Radius} ang {g.Angle} rnd {g.Random} size {g.Size} p({g.Param1},{g.Param2},{g.Param3})");
        try{ foreach(var op in ParticleEncoding.DecodeParticleOpCodes(g.TrackData)) Console.WriteLine($"     {op.Item1:X2} "+string.Join(",",op.Item2.Select(a=>Convert.ToString(a,System.Globalization.CultureInfo.InvariantCulture)))); } catch(Exception e){ Console.WriteLine("     decode err "+e.Message);} }
    } } }
