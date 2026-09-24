using HSDRaw;
using HSDRaw.Common.Animation;

// mkbuild roundtrip <file.dat>   HSDRaw load -> save -> reload; every root's struct graph compared (data bytes and
//                                reference layout). Exit 0 = identical graphs.
// mkbuild ajcheck <PlXxAJ.dat> <joints>  every 0x20-aligned sub-archive: HSDRaw parse, one public *_figatree root,
//                                HSD_FigaTree with <joints> nodes; each sub-archive also round-tripped.
static class Roundtrip
{
    static int nodes, diffs;
    static void Cmp(HSDStruct a, HSDStruct b, HashSet<HSDStruct> seen, List<string> log, string path)
    {
        if (a == null || b == null) { if (a != b) { diffs++; log.Add("null mismatch " + path); } return; }
        if (!seen.Add(a)) return; nodes++;
        var da = a.GetData(); var db = b.GetData(); int n = Math.Min(da.Length, db.Length);
        bool eq = da.AsSpan(0, n).SequenceEqual(db.AsSpan(0, n)) && da.Skip(n).All(x => x == 0) && db.Skip(n).All(x => x == 0);
        if (!eq) { diffs++; if (log.Count < 20) log.Add($"data diff at {path} len {da.Length}/{db.Length}"); }
        var ka = a.References.Keys.OrderBy(x => x).ToList(); var kb = b.References.Keys.OrderBy(x => x).ToList();
        if (!ka.SequenceEqual(kb)) { diffs++; if (log.Count < 20) log.Add($"ref keys diff at {path}"); return; }
        foreach (var k in ka) Cmp(a.References[k], b.References[k], seen, log, path + "/" + k.ToString("X"));
    }
    public static (int nodes, int diffs, List<string> log, int size) One(byte[] raw)
    {
        var f = new HSDRawFile(raw);
        var ms = new MemoryStream(); f.Save(ms); var outb = ms.ToArray();
        var g = new HSDRawFile(outb);
        nodes = 0; diffs = 0; var log = new List<string>();
        if (f.Roots.Count != g.Roots.Count) { diffs++; log.Add("root count"); }
        for (int i = 0; i < Math.Min(f.Roots.Count, g.Roots.Count); i++)
        {
            if (f.Roots[i].Name != g.Roots[i].Name) { diffs++; log.Add("root name " + f.Roots[i].Name); }
            Cmp(f.Roots[i].Data._s, g.Roots[i].Data._s, new(), log, f.Roots[i].Name);
        }
        return (nodes, diffs, log, outb.Length);
    }
    public static int Run(string path)
    {
        var (n, d, log, size) = One(File.ReadAllBytes(path));
        Console.WriteLine($"{Path.GetFileName(path)}: roots {new HSDRawFile(path).Roots.Count} graph nodes {n} diffs {d} resaved {size} B");
        foreach (var l in log) Console.WriteLine("  " + l);
        return d == 0 ? 0 : 2;
    }
    public static int Aj(string path, int joints)
    {
        var raw = File.ReadAllBytes(path); int off = 0, subs = 0, bad = 0, rtBad = 0; long maxSize = 0;
        while (off + 0x20 <= raw.Length)
        {
            int fs = (raw[off] << 24) | (raw[off + 1] << 16) | (raw[off + 2] << 8) | raw[off + 3];
            if (fs <= 0 || off + fs > raw.Length) break;
            var sub = raw.AsSpan(off, fs).ToArray(); subs++; maxSize = Math.Max(maxSize, fs);
            try
            {
                var f = new HSDRawFile(sub);
                var r = f.Roots.Single();
                var ft = new HSD_FigaTree { _s = r.Data._s };
                int nn = ft.NodeCount;
                if (!r.Name.EndsWith("_figatree") || nn != joints) { bad++; if (bad < 5) Console.WriteLine($"  bad {r.Name} nodes {nn}"); }
                if (One(sub).diffs != 0) rtBad++;
            }
            catch (Exception e) { bad++; if (bad < 5) Console.WriteLine($"  parse error at 0x{off:X}: {e.Message}"); }
            off = (off + fs + 0x1F) & ~0x1F;
        }
        Console.WriteLine($"{Path.GetFileName(path)}: sub-archives {subs} bad {bad} roundtrip_diffs {rtBad} max {maxSize} B (end 0x{off:X} of 0x{raw.Length:X})");
        return bad == 0 && rtBad == 0 && off == raw.Length ? 0 : 2;
    }
}
