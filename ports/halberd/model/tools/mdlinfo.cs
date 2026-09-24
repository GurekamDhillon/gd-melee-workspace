using System; using System.Collections.Generic; using BrawlLib.SSBB.ResourceNodes;
class I { static void Walk(ResourceNode n, List<ResourceNode> acc, Type t){ if (t.IsInstanceOfType(n)) acc.Add(n); List<ResourceNode> ch=null; try{ch=n.Children;}catch{} if(ch==null)return; foreach(var c in ch) Walk(c,acc,t);}
 static int Main(string[] a){ var root=NodeFactory.FromFile(null,a[0]); var m=new List<ResourceNode>(); Walk(root,m,typeof(MDL0Node));
 foreach(MDL0Node x in m){ Console.WriteLine(x.Name+" ver "+x.Version+" scaling "+x.ScalingRule+" texmtx "+x.TextureMatrixMode+" envmtx "+x.EnvelopeMatrixMode+" origPath "+x.OriginalPath);
   var bs=new List<ResourceNode>(); Walk(x,bs,typeof(MDL0BoneNode)); foreach(MDL0BoneNode b in bs) if(b.SegScaleCompApply||b.SegScaleCompParent) Console.WriteLine("  SSC "+b.Name+" "+b.SegScaleCompApply+" "+b.SegScaleCompParent); }
 var v=new List<ResourceNode>(); Walk(root,v,typeof(VIS0Node)); Console.WriteLine("vis0 "+v.Count);
 return 0;}}
