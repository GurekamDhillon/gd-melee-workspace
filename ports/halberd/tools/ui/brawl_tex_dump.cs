using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Text;
using BrawlLib.SSBB.ResourceNodes;

// brawl_tex_dump <outdir> <filter-regex or ""> <file> [file...]
//  every TEX0 in each file (.brres / .pac, nested archives walked) whose name matches -> outdir/<texname>.png
//  outdir/index.json : [{file, path, name, width, height, format, palette}]
class TexDump
{
    static string Esc(string s) { return s == null ? "null" : "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\""; }
    static void Walk(ResourceNode n, List<ResourceNode> acc)
    {
        if (n is TEX0Node) acc.Add(n);
        List<ResourceNode> ch = null;
        try { ch = n.Children; } catch { }
        if (ch == null) return;
        foreach (ResourceNode c in ch) Walk(c, acc);
    }
    static string PathOf(ResourceNode n) { var p = new List<string>(); for (; n != null; n = n.Parent) p.Insert(0, n.Name); return string.Join("/", p); }
    static int Main(string[] args)
    {
        string outdir = args[0]; Directory.CreateDirectory(outdir);
        var rx = new System.Text.RegularExpressions.Regex(args[1]);
        var sb = new StringBuilder("["); int k = 0;
        for (int i = 2; i < args.Length; i++)
        {
            ResourceNode root = NodeFactory.FromFile(null, args[i]);
            var acc = new List<ResourceNode>(); Walk(root, acc);
            foreach (ResourceNode n in acc)
            {
                TEX0Node t = (TEX0Node)n;
                if (!rx.IsMatch(t.Name)) continue;
                string fn = t.Name.Replace("/", "_") + ".png";
                string pal = "null";
                try { var p = t.GetPaletteNode(); if (p != null) pal = Esc(p.Name + ":" + p.Format + ":" + p.Colors); } catch { }
                using (Bitmap b = t.GetImage(0)) b.Save(Path.Combine(outdir, fn), ImageFormat.Png);
                if (k++ > 0) sb.Append(",");
                sb.Append("\n{\"file\":" + Esc(Path.GetFileName(args[i])) + ",\"path\":" + Esc(PathOf(t)) + ",\"name\":" + Esc(t.Name) +
                          ",\"png\":" + Esc(fn) + ",\"width\":" + t.Width + ",\"height\":" + t.Height + ",\"format\":" + Esc(t.Format.ToString()) + ",\"palette\":" + pal + "}");
            }
            root.Dispose();
        }
        sb.Append("\n]\n");
        File.WriteAllText(Path.Combine(outdir, "index.json"), sb.ToString());
        Console.WriteLine(k + " textures");
        return 0;
    }
}
