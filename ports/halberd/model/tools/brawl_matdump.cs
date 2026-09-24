// brawl_matdump: reflective dump of Brawl MDL0 materials/shaders and SRT0/PAT0/CLR0/VIS0 animations (BrawlLib, x86).
//   brawl_matdump.exe <pac> tree            node tree (type + name), to find resources
//   brawl_matdump.exe <pac> node <name>     all public scalar properties of every node with that name (and its children)
//   brawl_matdump.exe <pac> anims <outdir>  SRT0/PAT0 per-frame values for every animation, as JSON (one file per type)
using System; using System.Collections.Generic; using System.Linq; using System.Reflection; using System.Text; using System.IO;
using BrawlLib.SSBB.ResourceNodes; using BrawlLib.Modeling; using BrawlLib.Internal;
unsafe class D {
  static object GetF(object o, string name) { var f = o.GetType().GetField(name, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance); return f == null ? null : f.GetValue(o); }
  static void Walk(ResourceNode n, List<ResourceNode> acc, Func<ResourceNode,bool> f){ if (f(n)) acc.Add(n); List<ResourceNode> ch=null; try{ch=n.Children;}catch{} if(ch==null)return; foreach(var c in ch) Walk(c,acc,f);}
  static void Tree(ResourceNode n, int d){ Console.WriteLine(new string(' ',d*2)+n.GetType().Name+" "+n.Name); List<ResourceNode> ch=null; try{ch=n.Children;}catch{} if(ch==null)return; foreach(var c in ch) Tree(c,d+1);}
  static void Props(ResourceNode n, int d){
    Console.WriteLine(new string(' ',d*2)+"== "+n.GetType().Name+" "+n.Name);
    foreach (var p in n.GetType().GetProperties(BindingFlags.Public|BindingFlags.Instance)) {
      if (p.GetIndexParameters().Length>0) continue;
      var t=p.PropertyType; if (!(t.IsPrimitive||t.IsEnum||t==typeof(string)||t.IsValueType)) continue;
      if (p.DeclaringType==typeof(ResourceNode)) continue;
      object v; try{ v=p.GetValue(n,null);}catch{ continue; }
      Console.WriteLine(new string(' ',d*2)+"  "+p.Name+" = "+v);
    }
    List<ResourceNode> ch=null; try{ch=n.Children;}catch{} if(ch==null)return; foreach(var c in ch) Props(c,d+1);
  }
  static int Main(string[] a){
    var root=NodeFactory.FromFile(null,a[0]);
    if (a[1]=="tree") { Tree(root,0); return 0; }
    if (a[1]=="node") { var l=new List<ResourceNode>(); Walk(root,l,n=>n.Name==a[2]); foreach(var n in l) Props(n,0); return 0; }
    if (a[1]=="uvs") {   // uvs <objectName> <out.json>: every UV set per triangle-list facepoint, model_export.cs order
      var l=new List<ResourceNode>(); Walk(root,l,n=>n is MDL0ObjectNode && n.Name==a[2]);
      var o=(MDL0ObjectNode)l[0]; var pm=o._manager; var ci=System.Globalization.CultureInfo.InvariantCulture;
      var tri=GetF(pm,"_triangles"); uint[] idx=tri==null?new uint[0]:(uint[])GetF(tri,"_indices");
      var sb=new StringBuilder("{\"object\":\""+o.Name+"\",\"sets\":[");
      bool f0=true; for(int u=4;u<12;u++){ if(pm._faceData[u]==null) continue; if(!f0) sb.Append(","); f0=false; sb.Append(u-4); }
      sb.Append("],\"fp\":[");
      for (int t=0;t<idx.Length;t++){ int fp=(int)idx[t]; if(t>0) sb.Append(","); sb.Append("["); bool ff=true;
        for(int u=4;u<12;u++){ if(pm._faceData[u]==null) continue; var uv=((Vector2*)pm._faceData[u].Address)[fp]; if(!ff) sb.Append(","); ff=false; sb.Append(uv._x.ToString("R",ci)+","+uv._y.ToString("R",ci)); }
        sb.Append("]"); }
      sb.Append("]}"); File.WriteAllText(a[3], sb.ToString()); Console.WriteLine("uvs "+idx.Length); return 0; }
    if (a[1]=="srt0") {   // JSON: every SRT0 -> {name: {frames, loop, textures: {TextureN: {baked: [[sx,sy,rot,tx,ty] per frame], keys: [[array, frame, value, tangent]]}}}}
      var l=new List<ResourceNode>(); Walk(root,l,n=>n is SRT0Node); var sb=new StringBuilder("{");
      var ci=System.Globalization.CultureInfo.InvariantCulture; bool first=true;
      foreach (SRT0Node n in l) {
        if(!first) sb.Append(","); first=false;
        sb.Append("\n\""+n.Name+"\":{\"frames\":"+n.FrameCount+",\"loop\":"+(n.Loop?"true":"false")+",\"materials\":{");
        bool fe=true;
        foreach (SRT0EntryNode e in n.Children) {
          if(!fe) sb.Append(","); fe=false; sb.Append("\""+e.Name+"\":{"); bool ft=true;
          foreach (SRT0TextureNode t in e.Children) {
            if(!ft) sb.Append(","); ft=false;
            sb.Append("\""+t.Name+"\":{\"index\":"+t.TextureIndex+",\"baked\":[");
            for (int f=0; f<n.FrameCount; f++) { if(f>0) sb.Append(","); sb.Append("["); for(int k=0;k<5;k++){ if(k>0) sb.Append(","); sb.Append(t.GetFrameValue(k,f).ToString("R",ci)); } sb.Append("]"); }
            sb.Append("],\"keys\":["); bool fk=true;
            for (int k=0;k<5;k++) for (int f=0; f<=n.FrameCount; f++) { var kf=t.GetKeyframe(k,f); if(kf==null) continue; if(!fk) sb.Append(","); fk=false; sb.Append("["+k+","+f+","+kf._value.ToString("R",ci)+","+kf._tangent.ToString("R",ci)+"]"); }
            sb.Append("]}");
          }
          sb.Append("}");
        }
        sb.Append("}}");
      }
      sb.Append("}"); File.WriteAllText(a[2], sb.ToString()); Console.WriteLine("srt0 "+l.Count); return 0; }
    if (a[1]=="methods") { var t=typeof(ResourceNode).Assembly.GetType(a[2]); foreach (var m in t.GetMethods()) Console.WriteLine(m.ReturnType.Name+" "+m.Name+"("+string.Join(",",m.GetParameters().Select(x=>x.ParameterType.Name+" "+x.Name))+")"); foreach (var pp in t.GetProperties()) Console.WriteLine("prop "+pp.PropertyType.Name+" "+pp.Name); return 0; }
    return 1;
  }
}
