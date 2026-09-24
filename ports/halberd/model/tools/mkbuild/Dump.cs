using HSDRaw; using HSDRaw.Common; using HSDRaw.Common.Animation; using HSDRaw.GX;
// mkbuild mdump <dat> : every DObj's material (render flags, colours, PE) and TObjs (map id, coord source/type,
// colour/alpha op, lightmap, wrap, repeat, scale, blending, image), then the matanim's per-DObj texture anims.
static class Dump
{
    public static int Run(string path)
    {
        var f = new HSDRawFile(path);
        foreach (var r in f.Roots)
        {
            if (r.Data is HSD_JOBJ root)
            {
                Console.WriteLine("root " + r.Name + " joints " + root.TreeList.Count);
                int ji = 0, di = 0;
                foreach (var j in root.TreeList)
                {
                    if (j.Dobj != null)
                        foreach (var d in j.Dobj.List)
                        {
                            var m = d.Mobj;
                            Console.WriteLine($" dobj {di} joint {ji} flags {m?.RenderFlags} pobjs {d.Pobj?.List.Count}");
                            if (m?.Material != null) Console.WriteLine($"   mat amb {m.Material.AmbientColor} dif {m.Material.DiffuseColor} spc {m.Material.SpecularColor} alpha {m.Material.Alpha} shin {m.Material.Shininess}");
                            if (m?.PEDesc != null) Console.WriteLine($"   pe {m.PEDesc.Flags} {m.PEDesc.BlendMode} {m.PEDesc.SrcFactor} {m.PEDesc.DstFactor}");
                            int ti = 0;
                            if (m?.Textures != null) foreach (var t in m.Textures.List)
                            {
                                Console.WriteLine($"   tobj {ti++} map {t.TexMapID} src {t.GXTexGenSrc} flags {t.Flags} wrap {t.WrapS}/{t.WrapT} rep {t.RepeatS}/{t.RepeatT} S ({t.SX},{t.SY}) T ({t.TX},{t.TY}) R ({t.RX},{t.RY},{t.RZ}) blend {t.Blending} img {t.ImageData?.Format} {t.ImageData?.Width}x{t.ImageData?.Height} tlut {(t.TlutData != null)} tev {(t.TEV != null)}");
                                if (t.TEV != null) { var v = t.TEV; Console.WriteLine($"     c_op {v.color_op} a_op {v.alpha_op} cA {v.color_a_in} cB {v.color_b_in} cC {v.color_c_in} cD {v.color_d_in} aA {v.alpha_a_in} aB {v.alpha_b_in} aC {v.alpha_c_in} aD {v.alpha_d_in}"); }
                            }
                            di++;
                        }
                    ji++;
                }
            }
            else if (r.Name.EndsWith("matanim_joint"))
            {
                var mj = new HSD_MatAnimJoint { _s = r.Data._s };
                int ji = 0;
                foreach (var n in mj.TreeList)
                {
                    int di = 0;
                    if (n.MaterialAnimation != null)
                        foreach (var ma in n.MaterialAnimation.List)
                        {
                            if (ma.TextureAnimation != null)
                                foreach (var ta in ma.TextureAnimation.List)
                                {
                                    var ao = ta.AnimationObject;
                                    Console.WriteLine($" matanim joint {ji} dobj {di} map {ta.GXTexMapID} end {ao?.EndFrame} flags {ao?.Flags} images {ta.ImageCount} tluts {ta.TlutCount} tracks [{string.Join(",", ao?.FObjDesc?.List.Select(x => x.JointTrackType.ToString() + "/" + ((TexTrackType)x.TrackType).ToString()) ?? new string[0])}]");
                                }
                            if (ma.AnimationObject != null) Console.WriteLine($" matanim joint {ji} dobj {di} MOBJ anim end {ma.AnimationObject.EndFrame}");
                            di++;
                        }
                    ji++;
                }
            }
            else Console.WriteLine("root " + r.Name + " " + r.Data.GetType().Name);
        }
        return 0;
    }
}
