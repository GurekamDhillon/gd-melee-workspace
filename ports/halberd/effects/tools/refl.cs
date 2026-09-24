using System; using System.Reflection; 
class R{ static int Main(string[] a){ var asm=Assembly.LoadFrom("BrawlLib.dll"); foreach(var n in a){ var t=asm.GetType(n); if(t==null){Console.WriteLine("?? "+n);continue;} Console.WriteLine("== "+t.FullName+" : "+t.BaseType);
 foreach(var m in t.GetMethods(BindingFlags.Public|BindingFlags.Instance|BindingFlags.Static|BindingFlags.DeclaredOnly)) if(!m.IsSpecialName) { var ps=""; foreach(var p in m.GetParameters()) ps+=p.ParameterType.Name+" "+p.Name+","; Console.WriteLine("  M "+m.ReturnType.Name+" "+m.Name+"("+ps+")"); }
 foreach(var p in t.GetProperties(BindingFlags.Public|BindingFlags.Instance|BindingFlags.DeclaredOnly)) Console.WriteLine("  P "+p.PropertyType.Name+" "+p.Name);
 foreach(var f in t.GetFields(BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance|BindingFlags.DeclaredOnly)) Console.WriteLine("  F "+f.FieldType.Name+" "+f.Name);} return 0;}}
