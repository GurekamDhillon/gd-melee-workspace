using System; using System.Collections.Generic; using BrawlLib.SSBB.ResourceNodes;
class T { static void W(ResourceNode n,int d){ Console.WriteLine(new string(' ',d*2)+n.GetType().Name+" '"+n.Name+"'"); List<ResourceNode> ch=null; try{ch=n.Children;}catch{} if(ch==null)return; foreach(var c in ch) W(c,d+1);} 
 static int Main(string[] a){ var r=NodeFactory.FromFile(null,a[0]); W(r,0); return 0; } }
