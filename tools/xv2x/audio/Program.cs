using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using CriPakTools;
using VGAudio.Containers.Hca;
using Xv2CoreLib.ACB;
using Xv2CoreLib.AFS2;

namespace Xv2Audio
{
    // Load order of the game's own CPK resolution (first hit wins), from Xv2CoreLib CPK_Reader.
    // CPKs not in this list are appended after these, in name order.
    internal static class Program
    {
        private static readonly string[] GameLoadOrder =
        {
            "data_d4_5_xv1.cpk", "data_d6_dlc.cpk", "data_d0_stv.cpk", "movie_d6_dlc.cpk", "movie_p4.cpk",
            "movie_p2.cpk", "movie.cpk", "movie0.cpk", "data2.cpk", "data1.cpk", "data0.cpk", "data.cpk"
        };

        private sealed class CpkEntry
        {
            public string CpkName;
            public string Path;          // path inside the CPK, forward slashes, original case
            public FileEntry Raw;
            public long Size;
        }

        private sealed class CpkSet
        {
            public List<CPK> Cpks = new List<CPK>();
            public List<string> Names = new List<string>();
            public List<string> CpkPaths = new List<string>();
        }

        private static int Main(string[] args)
        {
            try
            {
                if (args.Length >= 3 && args[0] == "list")
                    return CmdList(args[1], args[2]);
                if (args.Length >= 4 && args[0] == "get")
                    return CmdGet(args[1], args[2], args[3]);
                if (args.Length >= 3 && args[0] == "acb")
                    return CmdAcb(args[1], args[2]);

                Console.Error.WriteLine("usage:");
                Console.Error.WriteLine("  Xv2Audio list <gameDir> <substring>");
                Console.Error.WriteLine("  Xv2Audio get <gameDir> <pathInCpk> <outFile>");
                Console.Error.WriteLine("  Xv2Audio acb <acbFile> <outDir>");
                return 2;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("ERROR: " + ex.GetType().Name + ": " + ex.Message);
                Console.Error.WriteLine(ex.StackTrace);
                return 1;
            }
        }

        // ---------------------------------------------------------------- CPK access

        private static CpkSet OpenCpks(string gameDir)
        {
            string cpkDir = Path.Combine(gameDir, "cpk");
            if (!Directory.Exists(cpkDir))
                throw new DirectoryNotFoundException("No cpk folder under " + gameDir);

            var files = Directory.GetFiles(cpkDir, "*.cpk")
                .OrderBy(f => { int i = Array.IndexOf(GameLoadOrder, Path.GetFileName(f).ToLowerInvariant()); return i < 0 ? int.MaxValue : i; })
                .ThenBy(f => Path.GetFileName(f), StringComparer.OrdinalIgnoreCase)
                .ToArray();

            var set = new CpkSet();
            foreach (string f in files)
            {
                var cpk = new CPK(new Tools());
                try
                {
                    if (!cpk.ReadCPK(f))
                    {
                        Console.Error.WriteLine("WARN: could not read " + Path.GetFileName(f));
                        continue;
                    }
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine("WARN: " + Path.GetFileName(f) + ": " + ex.Message);
                    continue;
                }
                set.Cpks.Add(cpk);
                set.Names.Add(Path.GetFileName(f));
                set.CpkPaths.Add(f);
            }
            return set;
        }

        private static string EntryPath(FileEntry fe)
        {
            string dir = fe.DirName == null ? "" : fe.DirName.ToString();
            string name = fe.FileName == null ? "" : fe.FileName.ToString();
            if (name.Length == 0) return null;
            return dir.Length == 0 ? name : dir.Replace('\\', '/').TrimEnd('/') + "/" + name;
        }

        private static long EntrySize(FileEntry fe)
        {
            return fe.FileSize == null ? 0 : Convert.ToInt64(fe.FileSize);
        }

        private static IEnumerable<CpkEntry> AllEntries(CpkSet set)
        {
            for (int i = 0; i < set.Cpks.Count; i++)
            {
                foreach (FileEntry fe in set.Cpks[i].FileTable)
                {
                    string p = EntryPath(fe);
                    if (p == null) continue;
                    yield return new CpkEntry { CpkName = set.Names[i], Path = p, Raw = fe, Size = EntrySize(fe) };
                }
            }
        }

        private static byte[] ReadEntryBytes(string cpkPath, FileEntry fe)
        {
            long size = EntrySize(fe);
            byte[] chunk;
            using (var fs = File.OpenRead(cpkPath))
            {
                fs.Seek(Convert.ToInt64(fe.FileOffset), SeekOrigin.Begin);
                chunk = new byte[size];
                int read = 0;
                while (read < size)
                {
                    int n = fs.Read(chunk, read, (int)(size - read));
                    if (n <= 0) throw new EndOfStreamException("short read from " + cpkPath);
                    read += n;
                }
            }
            if (chunk.Length >= 8 && Encoding.ASCII.GetString(chunk, 0, 8) == "CRILAYLA")
                chunk = CPK.DecompressCRILAYLA(chunk);
            return chunk;
        }

        // ---------------------------------------------------------------- list

        private static int CmdList(string gameDir, string sub)
        {
            CpkSet set = OpenCpks(gameDir);
            string needle = sub.ToLowerInvariant();
            int count = 0;
            foreach (CpkEntry e in AllEntries(set))
            {
                if (e.Path.ToLowerInvariant().Contains(needle))
                {
                    Console.WriteLine(e.CpkName + "\t" + e.Path + "\t" + e.Size);
                    count++;
                }
            }
            Console.Error.WriteLine("matches: " + count);
            return 0;
        }

        // ---------------------------------------------------------------- get

        private static int CmdGet(string gameDir, string pathInCpk, string outFile)
        {
            CpkSet set = OpenCpks(gameDir);
            string want = pathInCpk.Replace('\\', '/').Trim('/').ToLowerInvariant();

            // Game resolution order: first CPK in load order wins. All copies are listed.
            var hits = new List<(int idx, FileEntry fe, string cpkPath, string name)>();
            for (int i = 0; i < set.Cpks.Count; i++)
            {
                if (set.Cpks[i].Files.TryGetValue(want, out FileEntry fe))
                    hits.Add((i, fe, set.CpkPaths[i], set.Names[i]));
            }
            if (hits.Count == 0)
            {
                Console.Error.WriteLine("NOT FOUND: " + pathInCpk);
                return 3;
            }
            foreach (var h in hits)
                Console.Error.WriteLine("copy in " + h.name + " (" + EntrySize(h.fe) + " bytes)");

            var chosen = hits[0];
            byte[] bytes = ReadEntryBytes(chosen.cpkPath, chosen.fe);
            string dir = Path.GetDirectoryName(Path.GetFullPath(outFile));
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
            File.WriteAllBytes(outFile, bytes);
            Console.WriteLine("from " + chosen.name + " -> " + Path.GetFullPath(outFile) + " (" + bytes.Length + " bytes)");
            return 0;
        }

        // ---------------------------------------------------------------- acb

        private static int CmdAcb(string acbFile, string outDir)
        {
            Directory.CreateDirectory(outDir);
            ACB_File acb = ACB_File.Load(Path.GetFullPath(acbFile), false);
            Console.Error.WriteLine("acb: " + Path.GetFileName(acbFile) + " cues=" + acb.Cues.Count +
                " waveforms=" + acb.Waveforms.Count + " awbEntries=" + acb.AudioTracks.Entries.Count +
                " externalAwbError=" + acb.ExternalAwbError);

            var cueRows = new List<Dictionary<string, object>>();
            var used = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            foreach (ACB_Cue cue in acb.Cues)
            {
                List<ACB_Waveform> wfs = (acb.GetWaveformsFromCue(cue) ?? new List<ACB_Waveform>())
                    .Where(w => w != null).ToList();

                string cueName = string.IsNullOrWhiteSpace(cue.Name) ? null : cue.Name;
                var wfRows = new List<Dictionary<string, object>>();
                double cueDuration = 0;

                for (int k = 0; k < wfs.Count; k++)
                {
                    ACB_Waveform wf = wfs[k];
                    string label = cueName ?? ("wf" + wf.Index);
                    string baseName = SafeName(cue.ID + "_" + label) + (wfs.Count > 1 ? "_w" + k : "");
                    string wavName = baseName + ".wav";
                    int n = 2;
                    while (!used.Add(wavName.ToLowerInvariant()))
                        wavName = baseName + "_" + (n++) + ".wav";

                    double dur = wf.SamplingRate > 0 ? (double)wf.NumSamples / wf.SamplingRate : 0;
                    cueDuration += dur;

                    var row = new Dictionary<string, object>
                    {
                        ["waveformIndex"] = wf.Index,
                        ["awbId"] = wf.AwbId,
                        ["encode"] = wf.EncodeType.ToString(),
                        ["streaming"] = wf.IsStreaming,
                        ["channels"] = wf.NumChannels,
                        ["sampleRate"] = wf.SamplingRate,
                        ["numSamples"] = wf.NumSamples,
                        ["durationSec"] = Math.Round(dur, 3),
                        ["wav"] = null as string,
                        ["error"] = null as string
                    };

                    try
                    {
                        AFS2_Entry entry = acb.AudioTracks.GetEntry(wf.AwbId);
                        if (entry == null || entry.bytes == null)
                            throw new InvalidDataException("no AWB entry for awbId " + wf.AwbId);
                        short[][] pcm; int rate; int ch;
                        DecodeHca(entry.bytes, out pcm, out rate, out ch);
                        WriteWav(Path.Combine(outDir, wavName), pcm, rate);
                        row["wav"] = wavName;
                        row["decodedChannels"] = ch;
                        row["decodedSampleRate"] = rate;
                    }
                    catch (Exception ex)
                    {
                        row["error"] = ex.GetType().Name + ": " + ex.Message;
                        Console.Error.WriteLine("WARN cue " + cue.ID + " wf" + wf.Index + ": " + ex.Message);
                    }
                    wfRows.Add(row);
                }

                cueRows.Add(new Dictionary<string, object>
                {
                    ["cueId"] = cue.ID,
                    ["name"] = cueName,
                    ["referenceType"] = cue.ReferenceType.ToString(),
                    ["durationSec"] = Math.Round(cueDuration, 3),
                    ["waveforms"] = wfRows
                });
            }

            var opts = new JsonSerializerOptions { WriteIndented = true };
            File.WriteAllText(Path.Combine(outDir, "cues.json"), JsonSerializer.Serialize(cueRows, opts));

            foreach (var c in cueRows)
            {
                var wfs = (List<Dictionary<string, object>>)c["waveforms"];
                string wavs = string.Join(",", wfs.Select(w => w["wav"] ?? ("ERR:" + w["error"])));
                Console.WriteLine(c["cueId"] + "\t" + (c["name"] ?? "(no name)") + "\t" + c["durationSec"] + "s\t" + wavs);
            }
            Console.Error.WriteLine("wrote " + Path.Combine(outDir, "cues.json") + " and " + cueRows.Count + " cue(s)");
            return 0;
        }

        private static void DecodeHca(byte[] hca, out short[][] channels, out int sampleRate, out int chCount)
        {
            var reader = new HcaReader();
            var fmt = reader.ReadFormat(hca);
            var pcm = fmt.ToPcm16();
            channels = pcm.Channels;
            sampleRate = pcm.SampleRate;
            chCount = pcm.ChannelCount;
        }

        private static void WriteWav(string path, short[][] ch, int rate)
        {
            int channels = ch.Length;
            int frames = channels == 0 ? 0 : ch.Min(c => c.Length);
            int dataBytes = frames * channels * 2;
            var buf = new byte[dataBytes];
            int o = 0;
            for (int f = 0; f < frames; f++)
                for (int c = 0; c < channels; c++)
                {
                    short s = ch[c][f];
                    buf[o++] = (byte)(s & 0xFF);
                    buf[o++] = (byte)((s >> 8) & 0xFF);
                }

            using (var fs = File.Create(path))
            using (var bw = new BinaryWriter(fs))
            {
                bw.Write(Encoding.ASCII.GetBytes("RIFF"));
                bw.Write(36 + dataBytes);
                bw.Write(Encoding.ASCII.GetBytes("WAVE"));
                bw.Write(Encoding.ASCII.GetBytes("fmt "));
                bw.Write(16);
                bw.Write((short)1);
                bw.Write((short)channels);
                bw.Write(rate);
                bw.Write(rate * channels * 2);
                bw.Write((short)(channels * 2));
                bw.Write((short)16);
                bw.Write(Encoding.ASCII.GetBytes("data"));
                bw.Write(dataBytes);
                bw.Write(buf);
            }
        }

        private static string SafeName(string s)
        {
            foreach (char c in Path.GetInvalidFileNameChars()) s = s.Replace(c, '_');
            return s;
        }
    }
}
