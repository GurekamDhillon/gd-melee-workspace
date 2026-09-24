// mkbuild: Meta Knight model / fighter-data builder (HSDRaw).
using HSDRaw; using HSDRaw.Common; using HSDRaw.Melee.Pl;
static partial class P
{
    static int Main(string[] a)
    {
        switch (a[0])
        {
            case "ftinfo": return FtInfo(a[1]);
            case "build": return Build.Run(a[1], a[2], a[3], a.Length > 4 ? a[4] : null, a.Length > 5 ? a[5] : null);
            case "info": return Info(a[1]);
            case "mdump": return Dump.Run(a[1]);
            case "eyecheck": return EyeCheck.Run(a[1], a[2], a.Length > 3 ? a[3] : null);
            case "verify": return Verify.Run(a[1], a[2]);
            case "roundtrip": return Roundtrip.Run(a[1]);
            case "ajcheck": return Roundtrip.Aj(a[1], int.Parse(a[2]));
        }
        return 1;
    }
    public static HSDRaw.GX.GXTexFmt Fmt(string s) => s switch
    {
        "I4" => HSDRaw.GX.GXTexFmt.I4, "I8" => HSDRaw.GX.GXTexFmt.I8, "IA4" => HSDRaw.GX.GXTexFmt.IA4, "IA8" => HSDRaw.GX.GXTexFmt.IA8,
        "RGB565" => HSDRaw.GX.GXTexFmt.RGB565, "RGB5A3" => HSDRaw.GX.GXTexFmt.RGB5A3, "RGBA8" => HSDRaw.GX.GXTexFmt.RGBA8, "CMPR" => HSDRaw.GX.GXTexFmt.CMP,
        "CI4" => HSDRaw.GX.GXTexFmt.CI4, "CI8" => HSDRaw.GX.GXTexFmt.CI8, _ => throw new Exception("fmt " + s)
    };
    static string Hx(HSDAccessor x) => x == null ? "null" : $"len {x._s.Length}";
    static int FtInfo(string path)
    {
        var f = new HSDRawFile(path);
        foreach (var r in f.Roots) Console.WriteLine("root " + r.Name + " " + r.Data.GetType().Name);
        var ft = f.Roots.First(r => r.Name.StartsWith("ftData")).Data;
        var fd = new SBM_FighterData(); fd._s = ft._s;
        var ml = fd.ModelLookupTables;
        Console.WriteLine($"x8 vislen {ml.VisibilityLookupLength} matlen {ml.MaterialLookupLength} parts {ml.ItemHoldBone} {ml.ShieldBone} {ml.TopOfHeadBone} {ml.LeftFootBone} {ml.RightFootBone}");
        int ci = 0;
        foreach (var c in ml.CostumeVisibilityLookups.Array)
        {
            foreach (var (nm, t) in new[] { ("hi", c.HighPoly), ("lo", c.LowPoly), ("metal", c.MetalPoly), ("metalmain", c.MetalMainModel) })
            {
                if (t == null) { Console.WriteLine($" c{ci} {nm} null"); continue; }
                foreach (var lt in t.Array)
                    Console.WriteLine($" c{ci} {nm} lookup: " + string.Join(" | ", lt.LookupEntries?.Array.Select(e => "[" + string.Join(",", e.Entries ?? new byte[0]) + "]") ?? new string[0]));
            }
            ci++;
        }
        if (ml.CostumeMaterialLookups != null) foreach (var m in ml.CostumeMaterialLookups.Array) Console.WriteLine(" matlookup " + (m.Entries == null ? "null" : string.Join(",", m.Entries.Array)));
        Console.WriteLine("x1C modelparts " + (fd.ModelPartAnimations == null ? "null" : string.Join("; ", fd.ModelPartAnimations.Array.Select(p => p == null ? "null" : $"start {p.StartingBone} n {p.Count} entries [{string.Join(",", p.Entries ?? new byte[0])}] anims {(p.Anims == null ? 0 : p.Anims.Length)}"))));
        Console.WriteLine("x20 shield " + (fd.ShieldPoseContainer?.ShieldPose == null ? "null" : "jobj " + fd.ShieldPoseContainer.ShieldPose.TreeList.Count));
        Console.WriteLine("x2C physics " + (fd.Physics == null ? "null" : $"dyn {fd.Physics.DynamicDescCount} bubbles {fd.Physics.DynamicHitBubbleCount}"));
        if (fd.Physics?.DynamicDesc != null) foreach (var d in fd.Physics.DynamicDesc.Array) Console.WriteLine($"   dyn bone {d.BoneIndex} n {d.Parameters?.Length}");
        if (fd.Physics?.Hitbubbles != null) foreach (var d in fd.Physics.Hitbubbles.Array) Console.WriteLine($"   bubble {d}");
        Console.WriteLine("x30 hurt:"); foreach (var h in fd.Hurtboxes.Hurtboxes) Console.WriteLine("   " + h + " type " + h.Type);
        Console.WriteLine($"x34 center bone {fd.CenterBubble?.BoneIndex} size {fd.CenterBubble?.Size}");
        Console.WriteLine("x38 coin " + (fd.CoinCollisionSpheres == null ? "null" : string.Join("; ", fd.CoinCollisionSpheres.Array.Select(c => $"b{c.BoneIndex} ({c.XOffset},{c.YOffset},{c.ZOffset}) r{c.Size}"))));
        var e = fd.EnvironmentCollision;
        Console.WriteLine($"x44 ecb {e.ECBBone1} {e.ECBBone2} {e.ECBBone3} {e.ECBBone4} {e.ECBBone5} {e.ECBBone6} mul {e.Multiplier} ledge {e.LedgeGrabWidth} {e.LedgeGrabYOffset} {e.LedgeGrabHeight}");
        var b = fd.FighterBoneTable;
        Console.WriteLine(b == null ? "x54 null" : $"x54 bones head {b.HeadBone} rarm {b.RightArm} lleg {b.LeftLeg} rleg {b.RightLeg} larm {b.LeftArm}");
        var ik = fd.FighterIK;
        Console.WriteLine(ik == null ? "x58 null" : $"x58 ik leg {ik.RLegJ},{ik.LLegJ} knee {ik.RKneeJ},{ik.LKneeJ} foot {ik.RFootJ},{ik.LFootJ} sh {ik.RShoulderJ},{ik.LShoulderJ} arm {ik.RArmJ},{ik.LArmJ}");
        Console.WriteLine("x5C metal " + (fd.MetalModel == null ? "null" : "jobj " + fd.MetalModel.TreeList.Count));
        Console.WriteLine("x10 dynbeh " + Hx(fd._s.GetReference<HSDAccessor>(0x10)) + " x18 " + Hx(fd._s.GetReference<HSDAccessor>(0x18)) + " x48 " + Hx(fd._s.GetReference<HSDAccessor>(0x48)) + " x50 " + Hx(fd._s.GetReference<HSDAccessor>(0x50)));
        return 0;
    }
    static int Info(string dat)
    {
        var f = new HSDRawFile(dat);
        foreach (var r in f.Roots) Console.WriteLine("root " + r.Name + " " + r.Data.GetType().Name);
        return 0;
    }
}
