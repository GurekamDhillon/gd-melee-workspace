using HSDRaw;
// hsdresave <in.dat> <out.dat>   HSDRaw load -> save: drops every byte no root reaches (orphaned key streams, images,
//                                 tables left behind by append-only editors). Prints the sizes.
class P
{
    static int Main(string[] a)
    {
        var raw = File.ReadAllBytes(a[0]);
        var f = new HSDRawFile(raw);
        f.Save(a[1]);
        Console.WriteLine($"{Path.GetFileName(a[0])}: {raw.Length} -> {new FileInfo(a[1]).Length} B, roots {f.Roots.Count}");
        return 0;
    }
}
