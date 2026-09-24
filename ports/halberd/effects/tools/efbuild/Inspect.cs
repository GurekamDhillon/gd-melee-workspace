using HSDRaw; using HSDRaw.Common; using HSDRaw.Common.Animation; using HSDRaw.Melee.Ef;
static class Inspect {
  static string T(HSD_AOBJ a){ if(a==null) return "-"; var s=$"aobj[f={a.Flags} end={a.EndFrame}]"; if(a.FObjDesc!=null) foreach(var f in a.FObjDesc.List) s+=$" {f.JointTrackType}/{(int)f.TrackType}"; return s; }
  public static void Run(string path, int maxModels){
    var f=new HSDRawFile(path);
    foreach(var r in f.Roots){ Console.WriteLine("root "+r.Name+" "+r.Data?.GetType().Name);
      if(r.Name=="effBehaviorTable"){ var s=r.Data._s; int mn=s.GetInt32(0); var mt=s.GetReference<HSDAccessor>(4); int pn=s.GetInt32(8); var pt=s.GetReference<HSDAccessor>(0xC);
        Console.WriteLine($"  bhv models {mn}: "+(mt==null?"":string.Join(",",mt._s.GetData().Take(mn)))+$"  ptcl {pn}: "+(pt==null?"":string.Join(",",pt._s.GetData().Take(pn)))); }
      if(r.Name.EndsWith("DataTable")){ var t=new SBM_EffectTable(); t._s=r.Data._s;
        var pg=t.Particles; var tg=t.TextureGraphics; Console.WriteLine($"  ptcl gens {(pg==null?0:pg.GeneratorCount)} texg {(tg==null?0:tg._s.GetInt32(0))}");
        var ms=t.Models; Console.WriteLine("  models "+ms.Length);
        for(int i=0;i<Math.Min(ms.Length,maxModels);i++){ var m=ms[i]; Console.WriteLine($"  [{i}] frames {m.FrameCount} joint {(m.RootJoint!=null)} anim {(m.JointAnim!=null)} mat {(m.MaterialAnim!=null)} shape {(m.ShapeAnim!=null)}");
          if(m.RootJoint==null) continue; int ji=0;
          foreach(var j in m.RootJoint.TreeList){ Console.WriteLine($"     j{ji++} flags {j.Flags} S({j.SX:0.##},{j.SY:0.##},{j.SZ:0.##}) R({j.RX:0.##},{j.RY:0.##},{j.RZ:0.##}) T({j.TX:0.##},{j.TY:0.##},{j.TZ:0.##})");
            if(j.Dobj!=null) foreach(var d in j.Dobj.List){ var mo=d.Mobj; Console.WriteLine($"        mobj {mo.RenderFlags} diff {mo.Material?.DiffuseColor} amb {mo.Material?.AmbientColor} a {mo.Material?.Alpha}  pe {(mo.PEDesc==null?"-":mo.PEDesc.Flags+" "+mo.PEDesc.BlendMode+" "+mo.PEDesc.SrcFactor+" "+mo.PEDesc.DstFactor+" z"+mo.PEDesc.DepthFunction+" a"+mo.PEDesc.AlphaComp0+mo.PEDesc.AlphaRef0)}");
              if(mo.Textures!=null) foreach(var tx in mo.Textures.List) Console.WriteLine($"          tobj {tx.Flags} {tx.ImageData?.Format} {tx.ImageData?.Width}x{tx.ImageData?.Height} wrap {tx.WrapS}/{tx.WrapT} rep {tx.RepeatS}/{tx.RepeatT} blend {tx.Blending} coord {tx.GXTexGenSrc} S({tx.SX},{tx.SY}) T({tx.TX},{tx.TY}) tev {(tx.TEV==null?"-":"yes")}");
              if(d.Pobj!=null) foreach(var p in d.Pobj.List) Console.WriteLine($"          pobj flags {p.Flags} attrs {p.AttributesTypes}");
            } }
          if(m.JointAnim!=null){ int k=0; foreach(var aj in m.JointAnim.TreeList) Console.WriteLine($"     aj{k++} "+T(aj.AOBJ)); }
          if(m.MaterialAnim!=null){ int k=0; foreach(var mj in m.MaterialAnim.TreeList){ if(mj.MaterialAnimation!=null) foreach(var ma in mj.MaterialAnimation.List){ Console.WriteLine($"     mj{k} mat "+T(ma.AnimationObject)); if(ma.TextureAnimation!=null) foreach(var ta in ma.TextureAnimation.List) Console.WriteLine($"        tex {ta.GXTexMapID} "+T(ta.AnimationObject)+" imgs "+ta.ImageCount); } k++; } }
        } } } }
}
