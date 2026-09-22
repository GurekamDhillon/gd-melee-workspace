using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using HSDRaw;
using HSDRaw.Common;
using HSDRaw.GX;
using HSDRaw.Melee.Gr;
using HSDRawViewer.Converters;
using HSDRawViewer.GUI.Plugins.Melee;
using IONET;
using IONET.Core;
using OpenTK.Mathematics;

class Program
{
    static int Main(string[] args)
    {
        if (args.Length == 0)
        {
            Usage();
            return 1;
        }

        try
        {
            switch (args[0])
            {
                case "rt":
                    return RoundTrip(args[1], args[2]);
                case "meshim":
                    return MeshImport(args[1], args[2]);
                case "load":
                    return LoadProbe(args[1]);
                case "objim":
                    return ObjImport(args[1], args[2]);
                case "build":
                {
                    var flags = args.Length > 5 ? args.Skip(5).ToArray() : new string[0];
                    return Build(args[1], args[2],
                        args.Length > 3 ? args[3] : null,
                        args.Length > 4 ? int.Parse(args[4]) : -1,
                        flags.Contains("clear"),
                        flags.Contains("floor"),
                        flags.Contains("material"));
                }
                case "coll":
                    return CollDump(args[1]);
                default:
                    Usage();
                    return 1;
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine("EXCEPTION " + ex);
            return 99;
        }
    }

    static void Usage()
    {
        Console.WriteLine("usage:");
        Console.WriteLine("  stagec rt     <in.dat>   <out.dat>");
        Console.WriteLine("  stagec meshim <in.gltf>  <out.dat>");
    }

    private static (int joints, int dobjs, int pobjs, int dlBytes, int verts) Stats(HSD_JOBJ root)
    {
        int joints = 0, dobjs = 0, pobjs = 0, dl = 0, verts = 0;
        if (root == null)
            return (0, 0, 0, 0, 0);

        foreach (var j in root.TreeList)
        {
            joints++;
            for (var d = j.Dobj; d != null; d = d.Next)
            {
                dobjs++;
                for (var p = d.Pobj; p != null; p = p.Next)
                {
                    pobjs++;
                    dl += p.DisplayListSize;
                    try
                    {
                        var gx = p.ToDisplayList();
                        if (gx != null && gx.Vertices != null)
                            verts += gx.Vertices.Count;
                    }
                    catch
                    {
                        // decode failure is itself a finding; counted as 0 verts
                    }
                }
            }
        }
        return (joints, dobjs, pobjs, dl, verts);
    }

    static void Dump(string tag, HSD_JOBJ root)
    {
        var s = Stats(root);
        Console.WriteLine($"  [{tag}] joints={s.joints} dobjs={s.dobjs} pobjs={s.pobjs} dlBytes={s.dlBytes} verts={s.verts}");
    }

    static int RoundTrip(string src, string dst)
    {
        Console.WriteLine("=== SPIKE 1: DAT round-trip (read -> Save -> reload) ===");

        var f1 = new HSDRawFile(src);
        Console.WriteLine($"source: {src} ({new FileInfo(src).Length} bytes) roots={f1.Roots.Count}");

        f1.Save(dst, true, true, false);
        Console.WriteLine($"saved : {dst} ({new FileInfo(dst).Length} bytes)");

        var f2 = new HSDRawFile(dst);
        Console.WriteLine($"reload roots={f2.Roots.Count}");

        var n1 = f1.Roots.Select(r => r.Name ?? "").OrderBy(x => x).ToArray();
        var n2 = f2.Roots.Select(r => r.Name ?? "").OrderBy(x => x).ToArray();
        bool sameSymbols = n1.SequenceEqual(n2);
        Console.WriteLine($"symbols identical: {sameSymbols}");
        if (!sameSymbols)
        {
            foreach (var x in n1.Except(n2)) Console.WriteLine("  only in src: " + x);
            foreach (var x in n2.Except(n1)) Console.WriteLine("  only in dst: " + x);
        }

        var mh1 = f1.Roots.FirstOrDefault(r => (r.Name ?? "").StartsWith("map_head"))?.Data as SBM_Map_Head;
        var mh2 = f2.Roots.FirstOrDefault(r => (r.Name ?? "").StartsWith("map_head"))?.Data as SBM_Map_Head;
        if (mh1 == null || mh2 == null)
        {
            Console.WriteLine("RESULT: FAIL - map_head missing");
            return 5;
        }

        var g1 = mh1.ModelGroups.Array;
        var g2 = mh2.ModelGroups.Array;
        Console.WriteLine($"model groups: src={g1.Length} dst={g2.Length}");
        for (int i = 0; i < Math.Min(g1.Length, g2.Length); i++)
        {
            Dump("src g" + i, g1[i].RootNode);
            Dump("dst g" + i, g2[i].RootNode);
        }

        Console.WriteLine(sameSymbols ? "RESULT: PASS" : "RESULT: FAIL");
        return sameSymbols ? 0 : 5;
    }

    static int MeshImport(string gltf, string dst)
    {
        Console.WriteLine("=== SPIKE 2: mesh -> JOBJ -> DAT (tests GX display-list ENCODE) ===");

        var jobj = ModelImporter.ImportModelFromFile(gltf);
        if (jobj == null)
        {
            Console.WriteLine("RESULT: FAIL - ImportModelFromFile returned null");
            return 6;
        }
        Dump("imported", jobj);

        var f = new HSDRawFile();
        f.Roots.Add(new HSDRootNode { Name = "root", Data = jobj });
        f.Save(dst, true, true, false);
        Console.WriteLine($"saved {dst} ({new FileInfo(dst).Length} bytes)");

        var f2 = new HSDRawFile(dst);
        var r2 = f2.Roots[0].Data as HSD_JOBJ;
        Dump("reloaded", r2);

        var a = Stats(jobj);
        var b = Stats(r2);
        bool ok = a.verts > 0 && b.verts > 0 && a.dlBytes == b.dlBytes;
        Console.WriteLine($"dl preserved: {a.dlBytes == b.dlBytes}, verts src={a.verts} reloaded={b.verts}");
        Console.WriteLine(ok ? "RESULT: PASS" : "RESULT: FAIL");
        return ok ? 0 : 7;
    }

    static int LoadProbe(string f)
    {
        Console.WriteLine("=== SPIKE 2a: IOManager.LoadScene probe (headless, no dialogs) ===");
        var scene = IOManager.LoadScene(f, new ImportSettings() { Triangulate = true });
        if (scene == null)
        {
            Console.WriteLine("RESULT: FAIL - LoadScene returned null");
            return 8;
        }
        Console.WriteLine($"models={scene.Models.Count}");
        var m = scene.Models[0];
        Console.WriteLine($"  name={m.Name} meshes={m.Meshes.Count} rootBones={m.Skeleton.RootBones.Count}");
        Console.WriteLine("RESULT: PASS");
        return 0;
    }

    static int ObjImport(string obj, string dst)
    {
        Console.WriteLine("=== SPIKE 2b: OBJ -> HSD JOBJ -> DAT (headless, dialogs bypassed) ===");

        var scene = IOManager.LoadScene(obj, new ImportSettings() { Triangulate = true });
        if (scene == null)
        {
            Console.WriteLine("RESULT: FAIL - LoadScene returned null");
            return 8;
        }

        var model = scene.Models[0];
        var settings = new ModelImportSettings();
        var imp = new ModelImporter(
            Path.GetDirectoryName(obj),
            scene,
            model,
            settings,
            Enumerable.Empty<MeshImportSettings>(),
            Enumerable.Empty<MaterialImportSettings>(),
            null);

        var bw = new BackgroundWorker();
        bw.WorkerReportsProgress = true;
        imp.Work(bw);

        var jobj = imp.NewModel;
        if (jobj == null)
        {
            Console.WriteLine("RESULT: FAIL - imp.NewModel is null");
            return 9;
        }

        Dump("imported", jobj);

        var file = new HSDRawFile();
        file.Roots.Add(new HSDRootNode { Name = "stage_joint", Data = jobj });
        file.Save(dst, true, true, false);
        Console.WriteLine($"saved {dst} ({new FileInfo(dst).Length} bytes)");

        var f2 = new HSDRawFile(dst);
        Dump("reloaded", f2.Roots[0].Data as HSD_JOBJ);

        Console.WriteLine("RESULT: PASS");
        return 0;
    }

    static int Build(string baseDat, string outDat, string meshObj, int groupIndex, bool clearOthers,
                     bool collFloor, bool borrowMaterial)
    {
        Console.WriteLine("=== BUILD: base.dat [+ mesh.obj @ group N] -> out.dat ===");

        var file = new HSDRawFile(baseDat);
        var mh = file.Roots.FirstOrDefault(r => (r.Name ?? "").StartsWith("map_head"))?.Data as SBM_Map_Head;
        if (mh == null)
        {
            Console.WriteLine("RESULT: FAIL - map_head not found in base");
            return 2;
        }

        var groups = mh.ModelGroups.Array;
        Console.WriteLine($"base model groups: {groups.Length}");
        for (int i = 0; i < groups.Length; i++)
            Dump("base g" + i, groups[i].RootNode);

        if (meshObj != null)
        {
            if (groupIndex < 0 || groupIndex >= groups.Length)
            {
                Console.WriteLine($"RESULT: FAIL - group index {groupIndex} out of range");
                return 3;
            }

            Console.WriteLine($"importing {meshObj} -> replacing group {groupIndex}");
            var scene = IOManager.LoadScene(meshObj, new ImportSettings() { Triangulate = true });
            if (scene == null)
            {
                Console.WriteLine("RESULT: FAIL - LoadScene returned null");
                return 8;
            }

            var imp = new ModelImporter(
                Path.GetDirectoryName(meshObj),
                scene,
                scene.Models[0],
                new ModelImportSettings(),
                Enumerable.Empty<MeshImportSettings>(),
                Enumerable.Empty<MaterialImportSettings>(),
                null);

            var bw = new BackgroundWorker();
            bw.WorkerReportsProgress = true;
            imp.Work(bw);

            var nj = imp.NewModel;
            if (nj == null)
            {
                Console.WriteLine("RESULT: FAIL - mesh import produced no model");
                return 9;
            }
            Dump("new mesh", nj);

            var srcPobj = nj.Dobj != null ? nj.Dobj.Pobj : null;
            if (srcPobj == null)
            {
                Console.WriteLine("RESULT: FAIL - imported mesh has no PObj");
                return 10;
            }

            var root = groups[groupIndex].RootNode;
            var donorJoint = (HSD_JOBJ)null;
            var donorDobj = (HSD_DOBJ)null;
            var donorPobj = (HSD_POBJ)null;
            if (root != null)
            {
                foreach (var j in root.TreeList)
                {
                    for (var d = j.Dobj; d != null; d = d.Next)
                    {
                        if (d.Pobj != null)
                        {
                            donorJoint = j;
                            donorDobj = d;
                            donorPobj = d.Pobj;
                            break;
                        }
                    }
                    if (donorDobj != null)
                        break;
                }
            }

            if (donorPobj == null)
            {
                Console.WriteLine("RESULT: FAIL - no donor DObj/PObj in group " + groupIndex);
                return 11;
            }

            Console.WriteLine($"donor dlist {donorPobj.DisplayListSize} bytes -> incoming mesh dlist {srcPobj.DisplayListSize} bytes");
            donorPobj.DisplayListBuffer = srcPobj.DisplayListBuffer;
            Console.WriteLine($"donor dlist is now {donorPobj.DisplayListSize} bytes");

            foreach (var grp in groups)
            {
                var r = grp.RootNode;
                if (r == null)
                    continue;
                foreach (var j in r.TreeList)
                {
                    j.Dobj = null;
                    j.TX = 0f;
                    j.TY = 0f;
                    j.TZ = 0f;
                    j.RX = 0f;
                    j.RY = 0f;
                    j.RZ = 0f;
                    j.SX = 1f;
                    j.SY = 1f;
                    j.SZ = 1f;
                }
            }

            donorDobj.Next = null;
            donorPobj.Next = null;
            donorJoint.TY = -10f;
            donorJoint.Dobj = donorDobj;
            Console.WriteLine("kept the donor DObj and cleared all other geometry");

            if (borrowMaterial && donorDobj.Mobj == null)
            {
                var fallback = FindMobj(groups);
                if (fallback != null)
                {
                    donorDobj.Mobj = fallback;
                    Console.WriteLine("donor had no material; assigned the stage's first MObj");
                }
            }

            Dump("grafted g" + groupIndex, groups[groupIndex].RootNode);

            if (collFloor)
            {
                var coll = file.Roots.FirstOrDefault(r => (r.Name ?? "").EndsWith("coll_data"))?.Data as SBM_Coll_Data;
                if (coll == null)
                {
                    Console.WriteLine("RESULT: FAIL - coll_data not found");
                    return 6;
                }
                BuildFloorCollision(coll, 20f, 1500f);
                Console.WriteLine("replaced collision with a single floor (y=20, x +-1500)");
            }
        }

        file.Save(outDat, true, true, false);
        Console.WriteLine($"saved {outDat} ({new FileInfo(outDat).Length} bytes)");

        var f2 = new HSDRawFile(outDat);
        var mh2 = f2.Roots.FirstOrDefault(r => (r.Name ?? "").StartsWith("map_head"))?.Data as SBM_Map_Head;
        if (mh2 == null)
        {
            Console.WriteLine("RESULT: FAIL - emitted dat has no map_head");
            return 4;
        }
        var g2 = mh2.ModelGroups.Array;
        Console.WriteLine($"emitted model groups: {g2.Length}");
        for (int i = 0; i < g2.Length; i++)
            Dump("out g" + i, g2[i].RootNode);

        Console.WriteLine("RESULT: PASS");
        return 0;
    }

    static HSD_MOBJ FindMobj(SBM_Map_GOBJ[] groups)
    {
        foreach (var grp in groups)
        {
            var r = grp.RootNode;
            if (r == null)
                continue;
            foreach (var j in r.TreeList)
            {
                for (var d = j.Dobj; d != null; d = d.Next)
                {
                    if (d.Mobj != null)
                        return d.Mobj;
                }
            }
        }
        return null;
    }

    static void BuildFloorCollision(SBM_Coll_Data coll, float y, float halfX)
    {
        var v0 = new CollVertex(-halfX, y);
        var v1 = new CollVertex(halfX, y);

        var group = new CollLineGroup();
        group.Range = new Vector4(-halfX, y - 200f, halfX, y + 200f);

        var line = new CollLine();
        line.v1 = v0;
        line.v2 = v1;
        line.Group = group;
        line.CollisionFlag = CollPhysics.Top;
        line.Flag = CollProperty.None;
        line.Material = CollMaterial.Basic;
        line.DynamicCollision = false;

        CollDataBuilder.GenerateCollData(new[] { line }, new[] { group }, coll);
    }

    static int CollDump(string dat)
    {
        var file = new HSDRawFile(dat);
        var coll = file.Roots.FirstOrDefault(r => (r.Name ?? "").EndsWith("coll_data"))?.Data as SBM_Coll_Data;
        if (coll == null)
        {
            Console.WriteLine("no coll_data");
            return 2;
        }

        var verts = coll.Vertices;
        var links = coll.Links;
        var groups = coll.LineGroups;
        Console.WriteLine($"vertices={verts?.Length} links={links?.Length} groups={groups?.Length}");
        Console.WriteLine($"top(off={coll.TopLinksOffset},n={coll.TopLinksCount}) bottom(off={coll.BottomLinksOffset},n={coll.BottomLinksCount}) right(off={coll.RightLinksOffset},n={coll.RightLinksCount}) left(off={coll.LeftLinksOffset},n={coll.LeftLinksCount}) dyn(off={coll.DynamicLinksOffset},n={coll.DynamicLinksCount})");

        if (groups != null)
        {
            for (int i = 0; i < groups.Length; i++)
            {
                var g = groups[i];
                Console.WriteLine($"  g{i}: AABB x[{g.XMin},{g.XMax}] y[{g.YMin},{g.YMax}] top({g.TopLineIndex},{g.TopLineCount}) bot({g.BottomLineIndex},{g.BottomLineCount}) r({g.RightLineIndex},{g.RightLineCount}) l({g.LeftLineIndex},{g.LeftLineCount}) verts({g.VertexStart},{g.VertexCount})");
            }
        }

        if (links != null && verts != null)
        {
            int shown = 0;
            for (int i = 0; i < links.Length && shown < 16; i++)
            {
                var l = links[i];
                if (l.CollisionFlag != CollPhysics.Top)
                    continue;
                float x1 = verts[l.VertexIndex1].X, y1 = verts[l.VertexIndex1].Y;
                float x2 = verts[l.VertexIndex2].X, y2 = verts[l.VertexIndex2].Y;
                Console.WriteLine($"  topLine{i}: ({x1},{y1})->({x2},{y2}) len={Math.Abs(x2 - x1)} mat={l.Material}");
                shown++;
            }
        }
        return 0;
    }
}
