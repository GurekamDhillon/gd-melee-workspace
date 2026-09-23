// GD's Melee launcher - the program end users double-click.
//
// Asks for the user's own Melee disc image on first run, checks it (GALE01 revision 2, or a known
// m-ex mod disc such as ACE or Akaneia), remembers it, lets the user keep several discs
// ("modpacks") and pick which one to boot, edits the netplay server setting, and starts
// melee-pc.exe. No game data ships with it or is ever written by it.
//
// Built with the C# compiler that ships inside Windows (.NET Framework 4.x), so the language is
// C# 5: no string interpolation, no ?. operator. See tools/release/build_launcher.ps1 and
// tools/release/README.md.
//
// Command line (for shortcuts and scripts):
//   "GD Melee.exe"                       open the launcher
//   "GD Melee.exe" --play [disc name]    boot the default (or the named) disc without the window
//   "GD Melee.exe" --add-iso <path>      add a disc (and make it the default), then open the window
//   "GD Melee.exe" --forget-all          forget every saved disc (saves are kept), then open
//   "GD Melee.exe" --shots <dir>         render each tab to <dir>\launcher-<tab>.png and exit (docs)
//   "GD Melee.exe" --upload-crashes      what "Upload last 3 crash logs" does (only with the opt-in
//                                        on), result appended to userdata\crash-upload.txt

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

[assembly: AssemblyTitle("GD's Melee Launcher")]
[assembly: AssemblyProduct("GD's Melee")]
[assembly: AssemblyDescription("Launcher for GD's Melee. Bring your own Melee disc image.")]
[assembly: AssemblyVersion("1.0.0.0")]

namespace GDMelee
{
    // ---------------------------------------------------------------------------------------------
    // Disc detection
    // ---------------------------------------------------------------------------------------------

    enum DiscVerdict { Good, Warn, Bad }

    class DiscInfo
    {
        public DiscVerdict Verdict = DiscVerdict.Bad;
        public string GameId = "";
        public int Revision = -1;
        public string Title = "";
        public string Kind = "";      // what we call it in the list: "Melee 1.02 (vanilla)", "ACE (m-ex mod)"
        public string Message = "";   // why it is refused, or what to watch out for
        public bool Mex;
        public int FileCount;
        public long Size;

        public string Describe()
        {
            StringBuilder sb = new StringBuilder();
            if (GameId.Length > 0)
                sb.AppendFormat("Game ID: {0}   revision: {1}\r\nTitle: {2}\r\n", GameId,
                    Revision >= 0 ? "1.0" + Revision : "?", Title);
            if (FileCount > 0) sb.AppendFormat("Files on disc: {0}   size: {1:0.00} GB\r\n", FileCount, Size / 1073741824.0);
            if (Kind.Length > 0) sb.AppendFormat("Detected: {0}\r\n", Kind);
            if (Message.Length > 0) sb.Append("\r\n" + Message);
            return sb.ToString().TrimEnd();
        }
    }

    static class DiscProbe
    {
        // Files that exist only on the ACE build of Akaneia (both are m-ex discs with the same
        // header title, "Super Smash Bros. Melee: Akaneia").
        static readonly string[] AceMarkers = { "AltSlippiCSS.dat", "EfKxData.dat", "EfMkData.dat", "EfZxData.dat" };
        const int VanillaFstEntries = 1212;   // NTSC 1.02 (USA): root + 1211 files/directories

        static uint BE32(byte[] b, int o)
        {
            return ((uint)b[o] << 24) | ((uint)b[o + 1] << 16) | ((uint)b[o + 2] << 8) | b[o + 3];
        }

        static string CStr(byte[] b, int o, int max)
        {
            int n = 0;
            while (n < max && o + n < b.Length && b[o + n] != 0) n++;
            return Encoding.GetEncoding(932).GetString(b, o, n).Trim();   // Shift-JIS is a superset for titles
        }

        static byte[] ReadAt(FileStream fs, long off, int len)
        {
            if (off < 0 || off + len > fs.Length) return null;
            byte[] b = new byte[len];
            fs.Seek(off, SeekOrigin.Begin);
            int got = 0;
            while (got < len)
            {
                int r = fs.Read(b, got, len - got);
                if (r <= 0) return null;
                got += r;
            }
            return b;
        }

        public static DiscInfo Probe(string path)
        {
            DiscInfo d = new DiscInfo();
            try
            {
                using (FileStream fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                {
                    d.Size = fs.Length;
                    byte[] h = ReadAt(fs, 0, 0x440);
                    if (h == null) { d.Message = "The file is too small to be a GameCube disc image."; return d; }
                    string magic = Encoding.ASCII.GetString(h, 0, 4);
                    if (magic == "RVZ\u0001" || magic == "WIA\u0001")
                    {
                        d.Message = "This is a compressed Dolphin image (" + magic.Substring(0, 3) + "). GD's Melee reads plain disc images.\r\n" +
                                    "In Dolphin: right-click the game > Convert File... > Format: ISO, then pick the .iso.";
                        return d;
                    }
                    if (magic == "CISO")
                    {
                        d.Message = "This is a compressed CISO image. Convert it to a plain .iso first (Dolphin: Convert File... > ISO).";
                        return d;
                    }
                    if (BE32(h, 0x1C) != 0xC2339F3Du)
                    {
                        d.Message = BE32(h, 0x18) == 0x5D1C9EA3u
                            ? "This is a Wii disc image, not a GameCube one."
                            : "This is not a GameCube disc image (the disc header's magic number is missing).";
                        return d;
                    }
                    d.GameId = Encoding.ASCII.GetString(h, 0, 6);
                    d.Revision = h[7];
                    d.Title = CStr(h, 0x20, 0x3E0);
                    bool nkit = Encoding.ASCII.GetString(h, 0x200, 4) == "NKIT";

                    // Training Mode - Community Edition is Melee NTSC 1.02 under its own game ID.
                    bool tmce = d.GameId == "GTME01";
                    if (!d.GameId.StartsWith("GAL") && !tmce)
                    {
                        d.Message = "This disc is \"" + d.Title + "\" (" + d.GameId + "), not Super Smash Bros. Melee.";
                        return d;
                    }
                    if (d.GameId != "GALE01" && !tmce)
                    {
                        string region = d.GameId[3] == 'P' ? "PAL (Europe)" : d.GameId[3] == 'J' ? "Japanese" : "\"" + d.GameId + "\"";
                        d.Message = "This is the " + region + " version of Melee. GD's Melee needs the NTSC-U (USA) disc, game ID GALE01.";
                        return d;
                    }
                    if (d.Revision != 2)
                    {
                        d.Message = "This is Melee NTSC 1.0" + d.Revision + ". GD's Melee needs revision 1.02 (the last USA revision, and the one every mod builds on).";
                        return d;
                    }

                    HashSet<string> names = ReadFstNames(fs, BE32(h, 0x424), BE32(h, 0x428), out d.FileCount);
                    if (names == null)
                    {
                        d.Message = "The disc's file table is unreadable. The image may be truncated or damaged; dump it again.";
                        return d;
                    }
                    d.Mex = names.Contains("MxDt.dat");
                    d.Verdict = DiscVerdict.Good;
                    if (d.Mex)
                    {
                        bool ace = Path.GetFileName(path).IndexOf("ACE", StringComparison.Ordinal) >= 0;
                        foreach (string m in AceMarkers) if (names.Contains(m)) ace = true;
                        if (ace) d.Kind = "ACE (m-ex mod)";
                        else if (d.Title.IndexOf("Akaneia", StringComparison.OrdinalIgnoreCase) >= 0) d.Kind = "Akaneia (m-ex mod)";
                        else
                        {
                            d.Kind = "m-ex mod: " + d.Title;
                            d.Verdict = DiscVerdict.Warn;
                            d.Message = "This is an m-ex mod disc other than ACE or Akaneia. It may work, but only ACE and Akaneia are tested.";
                        }
                    }
                    else if (d.Title == "Super Smash Bros Melee")
                    {
                        if (d.FileCount == VanillaFstEntries) d.Kind = "Melee 1.02 (vanilla)";
                        else
                        {
                            d.Kind = "Melee 1.02 (modified)";
                            d.Verdict = DiscVerdict.Warn;
                            d.Message = "The disc is Melee 1.02 but its files differ from the retail disc. Mods that patch the game's code may not work.";
                        }
                    }
                    else if (tmce)
                    {
                        d.Kind = "Training Mode (TM-CE)";
                        d.Verdict = DiscVerdict.Warn;
                        d.Message = "This disc boots, but its special features (the training lab and its menus) aren't supported yet: it plays like vanilla Melee for now.";
                    }
                    else if (d.Title.IndexOf("20XX", StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        d.Kind = "20XX: " + d.Title;
                        d.Verdict = DiscVerdict.Warn;
                        d.Message = "This disc boots, but its special features (the 20XX menus and codes) aren't supported yet: it plays like vanilla Melee for now.";
                    }
                    else
                    {
                        d.Kind = "Melee 1.02 mod: " + d.Title;
                        d.Verdict = DiscVerdict.Warn;
                        d.Message = "This is a mod built on Melee 1.02. Most mods patch the game's code, which GD's Melee does not run; expect it to behave like vanilla or to fail. Tested: vanilla 1.02, ACE, Akaneia.";
                    }
                    if (nkit)
                    {
                        d.Verdict = DiscVerdict.Warn;
                        d.Message = (d.Message + "\r\nThis is an NKit image. If the game fails to start, restore it to a full ISO with NKit.").Trim();
                    }
                }
            }
            catch (Exception e)
            {
                d.Verdict = DiscVerdict.Bad;
                d.Message = "Could not read the file: " + e.Message;
            }
            return d;
        }

        static HashSet<string> ReadFstNames(FileStream fs, uint off, uint size, out int count)
        {
            count = 0;
            if (size < 12 || size > 16u * 1024 * 1024) return null;
            byte[] f = ReadAt(fs, off, (int)size);
            if (f == null) return null;
            uint n = BE32(f, 8);
            if (n == 0 || (long)n * 12 > size) return null;
            int strings = (int)n * 12;
            HashSet<string> names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            for (int i = 1; i < n; i++)
            {
                int no = (int)(BE32(f, i * 12) & 0xFFFFFF);
                int p = strings + no, e = p;
                if (p >= f.Length) return null;
                while (e < f.Length && f[e] != 0) e++;
                names.Add(Encoding.ASCII.GetString(f, p, e - p));
            }
            count = (int)n;
            return names;
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Settings: userdata\launcher.cfg next to the launcher (portable), or %LOCALAPPDATA%\GDMelee
    // when the launcher's folder is read-only (e.g. unzipped into Program Files).
    // ---------------------------------------------------------------------------------------------

    class Disc
    {
        public string Id = "";     // stable: names this disc's save folder, survives "Change ISO"
        public string Name = "";   // user-editable
        public string Path = "";
        public string Kind = "";
    }

    class Settings
    {
        public List<Disc> Discs = new List<Disc>();
        public string DefaultId = "";
        public bool SkipIntro = true;
        public bool UnlockAll = true;
        public bool KeyboardOnly = false;  // MELEE_INPUT=keyboard: controllers ignored (the game's default is keyboard + controllers)
        public int KeyboardPort = 0;         // MELEE_KEYBOARD_PORT 1-4, 0 = the game's default (1)
        public bool CloseOnPlay = false;
        public int Volume = 50;            // MELEE_VOLUME, 0-100
        public bool ConsoleSocket = false; // MELEE_CONSOLE_PORT=51700 (scripts console for tools)

        // Diagnostics tab (see class Diagnostics): what the game writes to melee-pc.log
        public int LogRender = 0;           // 0 one DIAG block per scene (the game's default), 1 every block, -1 none
        public bool LogScene = true;        // scene changes and menu cursors
        public bool LogAll = false;         // MELEE_LOG=all
        public string LogCategories = "";   // opt-in categories, comma-separated (Diagnostics.Categories)
        public int PadDiag = -1;            // MELEE_PAD_DIAG 0/1/2, -1 = the game's default
        public int PadReleaseOnBlur = -1;   // MELEE_PAD_RELEASE_ON_BLUR 0/1, -1 = the game's default
        public string Traces = "";          // extra switches, comma-separated (Diagnostics.TraceList)
        public bool CrashUpload = false;    // the Diagnostics tab's opt-in: enables "Upload last 3 crash logs"

        public static string AppDir = System.IO.Path.GetDirectoryName(Application.ExecutablePath);
        public static string UserDir = PickUserDir();
        static string File { get { return System.IO.Path.Combine(UserDir, "launcher.cfg"); } }

        public static bool Writable(string dir)
        {
            try
            {
                Directory.CreateDirectory(dir);
                string probe = System.IO.Path.Combine(dir, ".write-test");
                System.IO.File.WriteAllText(probe, "x");
                System.IO.File.Delete(probe);
                return true;
            }
            catch { return false; }
        }

        static string PickUserDir()
        {
            string portable = System.IO.Path.Combine(AppDir, "userdata");
            if (Writable(portable)) return portable;
            return System.IO.Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "GDMelee");
        }

        public Disc Find(string id)
        {
            foreach (Disc d in Discs) if (d.Id == id) return d;
            return null;
        }

        public Disc Default
        {
            get
            {
                Disc d = Find(DefaultId);
                return d != null ? d : (Discs.Count > 0 ? Discs[0] : null);
            }
        }

        public static Settings Load()
        {
            Settings s = new Settings();
            if (!System.IO.File.Exists(File)) return s;
            foreach (string raw in System.IO.File.ReadAllLines(File, Encoding.UTF8))
            {
                string line = raw.Trim();
                if (line.Length == 0 || line.StartsWith("#")) continue;
                int eq = line.IndexOf('=');
                if (eq < 0) continue;
                string k = line.Substring(0, eq).Trim(), v = line.Substring(eq + 1).Trim();
                switch (k)
                {
                    case "default": s.DefaultId = v; break;
                    case "skip_intro": s.SkipIntro = v == "1"; break;
                    case "unlock_all": s.UnlockAll = v == "1"; break;
                    case "keyboard_only": s.KeyboardOnly = v == "1"; break;
                    case "keyboard_port": { int r; if (int.TryParse(v, out r)) s.KeyboardPort = Math.Max(0, Math.Min(4, r)); } break;
                    case "close_on_play": s.CloseOnPlay = v == "1"; break;
                    case "volume": { int vol; if (int.TryParse(v, out vol)) s.Volume = Math.Max(0, Math.Min(100, vol)); } break;
                    case "console_socket": s.ConsoleSocket = v == "1"; break;
                    case "log_render": { int r; if (int.TryParse(v, out r)) s.LogRender = Math.Max(-1, Math.Min(1, r)); } break;
                    case "log_scene": s.LogScene = v != "0"; break;
                    case "log_all": s.LogAll = v == "1"; break;
                    case "log_categories": s.LogCategories = v; break;
                    case "pad_diag": { int r; if (int.TryParse(v, out r)) s.PadDiag = Math.Max(-1, Math.Min(2, r)); } break;
                    case "pad_release_on_blur": { int r; if (int.TryParse(v, out r)) s.PadReleaseOnBlur = Math.Max(-1, Math.Min(1, r)); } break;
                    case "traces": s.Traces = v; break;
                    case "crash_upload": s.CrashUpload = v == "1"; break;
                    case "disc":
                        // id|name|kind|path  ('|' cannot appear in a Windows path)
                        string[] p = v.Split(new[] { '|' }, 4);
                        if (p.Length == 4) s.Discs.Add(new Disc { Id = p[0], Name = p[1], Kind = p[2], Path = p[3] });
                        break;
                }
            }
            return s;
        }

        public void Save()
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("# GD's Melee launcher settings. Delete this file to start over (your saves are kept in saves\\).");
            sb.AppendLine("default=" + DefaultId);
            sb.AppendLine("skip_intro=" + (SkipIntro ? "1" : "0"));
            sb.AppendLine("unlock_all=" + (UnlockAll ? "1" : "0"));
            sb.AppendLine("keyboard_only=" + (KeyboardOnly ? "1" : "0"));
            sb.AppendLine("keyboard_port=" + KeyboardPort);
            sb.AppendLine("close_on_play=" + (CloseOnPlay ? "1" : "0"));
            sb.AppendLine("volume=" + Volume);
            sb.AppendLine("console_socket=" + (ConsoleSocket ? "1" : "0"));
            sb.AppendLine("log_render=" + LogRender);
            sb.AppendLine("log_scene=" + (LogScene ? "1" : "0"));
            sb.AppendLine("log_all=" + (LogAll ? "1" : "0"));
            sb.AppendLine("log_categories=" + LogCategories);
            sb.AppendLine("pad_diag=" + PadDiag);
            sb.AppendLine("pad_release_on_blur=" + PadReleaseOnBlur);
            sb.AppendLine("traces=" + Traces);
            sb.AppendLine("crash_upload=" + (CrashUpload ? "1" : "0"));
            foreach (Disc d in Discs)
                sb.AppendLine("disc=" + d.Id + "|" + d.Name.Replace("|", "/") + "|" + d.Kind.Replace("|", "/") + "|" + d.Path);
            Directory.CreateDirectory(UserDir);
            System.IO.File.WriteAllText(File, sb.ToString(), new UTF8Encoding(false));
        }

        public string NewId(string name)
        {
            StringBuilder sb = new StringBuilder();
            foreach (char c in name.ToLowerInvariant())
                if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')) sb.Append(c);
                else if (sb.Length > 0 && sb[sb.Length - 1] != '-') sb.Append('-');
            string stem = sb.ToString().Trim('-');
            if (stem.Length == 0) stem = "disc";
            if (stem.Length > 24) stem = stem.Substring(0, 24).Trim('-');
            string id = stem;
            for (int i = 2; Find(id) != null; i++) id = stem + "-" + i;
            return id;
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Starting the game
    // ---------------------------------------------------------------------------------------------

    static class Game
    {
        public static string Exe { get { return Path.Combine(Settings.AppDir, "melee-pc.exe"); } }
        public static string ServerFile { get { return Path.Combine(Settings.AppDir, "netplay_server.txt"); } }
        public static string ModsDir { get { return Path.Combine(Settings.AppDir, "mods"); } }

        // Where the game runs: its log, crash logs and shader cache go in the working directory.
        // The game's own folder when that is writable, else a folder in the user's profile.
        public static string RunDir
        {
            get { return Settings.Writable(Settings.AppDir) ? Settings.AppDir : Path.Combine(Settings.UserDir, "run"); }
        }

        public static string LogFile { get { return Path.Combine(RunDir, "melee-pc.log"); } }

        // True when the last session's log shows the user closed the window, so a non-zero exit
        // code came from shutting down rather than from a crash mid-game.
        public static bool ClosedByUser()
        {
            try
            {
                using (FileStream fs = new FileStream(LogFile, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                using (StreamReader r = new StreamReader(fs))
                {
                    string all = r.ReadToEnd();
                    int closed = all.LastIndexOf("melee-pc: window closed, shutting down", StringComparison.Ordinal);
                    int fatal = all.LastIndexOf("gw: FATAL", StringComparison.Ordinal);
                    return closed >= 0 && (fatal < 0 || fatal > closed);
                }
            }
            catch { return false; }
        }

        public static string Version()
        {
            string f = Path.Combine(Settings.AppDir, "version.txt");
            try
            {
                if (File.Exists(f))
                {
                    string first = File.ReadAllLines(f)[0].Trim();
                    if (first.Length > 0) return first;
                }
            }
            catch { }
            return "development build";
        }

        public static string[] MissingFiles()
        {
            List<string> miss = new List<string>();
            foreach (string f in new[] { "melee-pc.exe", "SDL3.dll", "webgpu_dawn.dll", "ui\\manifest.json" })
                if (!File.Exists(Path.Combine(Settings.AppDir, f))) miss.Add(f);
            return miss.ToArray();
        }

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        static extern uint GetShortPathNameW(string longPath, StringBuilder shortPath, uint size);

        // The game takes its paths as ANSI strings, so a path with characters outside the system
        // code page would arrive mangled. The 8.3 short name is plain ASCII when the volume has
        // short names; otherwise hand over the path and let the game report it.
        public static string AnsiSafe(string path)
        {
            bool ascii = true;
            foreach (char c in path) if (c > 127) { ascii = false; break; }
            if (ascii) return path;
            StringBuilder sb = new StringBuilder(1024);
            uint n = GetShortPathNameW(path, sb, (uint)sb.Capacity);
            return (n > 0 && n < sb.Capacity) ? sb.ToString() : path;
        }

        public static Process Start(Settings s, Disc disc)
        {
            string saves = Path.Combine(Path.Combine(Settings.UserDir, "saves"), disc.Id);
            Directory.CreateDirectory(saves);
            Directory.CreateDirectory(RunDir);

            ProcessStartInfo psi = new ProcessStartInfo(Exe);
            psi.Arguments = "--iso \"" + AnsiSafe(disc.Path) + "\"";
            psi.WorkingDirectory = RunDir;
            psi.UseShellExecute = false;
            psi.EnvironmentVariables["MELEE_CARD_PATH"] = AnsiSafe(saves);   // one memory card per disc
            if (RunDir != Settings.AppDir) psi.EnvironmentVariables["MELEE_CACHE_DIR"] = AnsiSafe(RunDir);
            // every character, stage and unlockable rule, without touching the save (gmmain_lib.c)
            if (s.UnlockAll) psi.EnvironmentVariables["MELEE_UNLOCK_ALL"] = "1";
            else psi.EnvironmentVariables.Remove("MELEE_UNLOCK_ALL");
            psi.EnvironmentVariables["MELEE_VOLUME"] = s.Volume.ToString(); // percent of full volume
            if (s.ConsoleSocket) psi.EnvironmentVariables["MELEE_CONSOLE_PORT"] = "51700"; /* 127.0.0.1 only */
            else psi.EnvironmentVariables.Remove("MELEE_CONSOLE_PORT");
            if (s.SkipIntro) psi.EnvironmentVariables["MELEE_SKIP_INTRO"] = "1";
            else psi.EnvironmentVariables.Remove("MELEE_SKIP_INTRO");
            // unset = keyboard and controllers together (the game's default since 0.1.2)
            if (s.KeyboardOnly) psi.EnvironmentVariables["MELEE_INPUT"] = "keyboard";
            else psi.EnvironmentVariables.Remove("MELEE_INPUT");
            if (s.KeyboardPort >= 1) psi.EnvironmentVariables["MELEE_KEYBOARD_PORT"] = s.KeyboardPort.ToString();
            else psi.EnvironmentVariables.Remove("MELEE_KEYBOARD_PORT");
            Mods.ApplyEnvironment(s, disc, psi);
            Diagnostics.ApplyEnvironment(s, psi);
            return Process.Start(psi);
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Diagnostics: the game's log categories and trace switches (melee pc/platform/gw_log.c), passed
    // as environment variables at launch. The game's own default keeps melee-pc.log short: scene
    // changes, loads, warnings, netplay and pad events; everything else is opt-in here.
    // ---------------------------------------------------------------------------------------------

    class Choice
    {
        public string Key, Label, Tip;
        public Choice(string key, string label, string tip) { Key = key; Label = label; Tip = tip; }
    }

    static class Diagnostics
    {
        // MELEE_LOG categories that are quiet unless turned on
        public static readonly Choice[] Categories = {
            new Choice("watchdog", "Watchdog samples", "Where the game thread is, sampled ten times a second (\"gw: at ...\"), and a stats line every 2 s. Helps with freezes and silent exits."),
            new Choice("mex", "m-ex internals", "Fighter and stage code from m-ex discs and mods: hooks installed, calls into their code, item and effect registration. For crashes with ACE/Akaneia fighters or stages."),
            new Choice("heap", "Memory (heap) trace", "Every allocation from the game's heaps (MELEE_HEAP_TRACE). For \"out of memory\" / ALLOC_FAIL crashes. Large."),
            new Choice("dvd", "Disc file trace", "Every file the game opens and where it came from, the disc or a mod (MELEE_DVD_TRACE). For missing or wrong files in mods."),
            new Choice("tex", "UI texture loads", "Every menu texture the game opens (gxtex)."),
            new Choice("frontend", "Menu layout files", "Sizes of the menu layout and animation files as they load."),
            new Choice("audio", "Sound bank loads", "Each sound bank as it is loaded (synth: bank ...)."),
            new Choice("snap", "Rollback snapshot internals", "Object pool bookkeeping inside rollback snapshots. For online desyncs, when asked."),
        };

        // switches that are not log categories: key -> environment variable = 1
        public static readonly Choice[] TraceList = {
            new Choice("rb", "Rollback log (MELEE_RB_LOG)", "Rollback and netplay frame decisions: rollbacks, input arrival, desync checks. For online problems."),
            new Choice("gr", "Stage code trace (MELEE_GR_TRACE)", "Every call into an m-ex stage's own code. Very large; for a stage that crashes."),
            new Choice("mexcalls", "m-ex engine call trace (MELEE_MEX_TRACE_CALLS)", "The first engine calls an m-ex fighter or stage makes, with arguments."),
            new Choice("card", "Memory card diagnostics (MELEE_CARD_DIAG)", "Saves and loads of the memory card files. For lost settings or saves."),
            new Choice("profile", "Frame timing profile (MELEE_PROFILE)", "Where each frame's time goes, every 600 frames. For stutter or low frame rate."),
            new Choice("fps", "Show the frame rate (MELEE_SHOW_FPS)", "An FPS counter on the game window."),
            new Choice("aurora", "Renderer log (MELEE_AURORA_VERBOSE)", "The graphics backend's own messages. For a black or broken screen."),
            new Choice("osreport", "Report format trace (MELEE_PC_TRACE_OSREPORT)", "Every game report's format string before it is printed. Doubles the log; for a crash inside logging."),
        };

        static readonly Dictionary<string, string> TraceEnv = new Dictionary<string, string> {
            { "rb", "MELEE_RB_LOG" }, { "gr", "MELEE_GR_TRACE" }, { "mexcalls", "MELEE_MEX_TRACE_CALLS" },
            { "card", "MELEE_CARD_DIAG" }, { "profile", "MELEE_PROFILE" }, { "fps", "MELEE_SHOW_FPS" },
            { "aurora", "MELEE_AURORA_VERBOSE" }, { "osreport", "MELEE_PC_TRACE_OSREPORT" },
        };

        public static bool Has(string list, string key)
        {
            foreach (string k in list.Split(',')) if (k.Trim() == key) return true;
            return false;
        }

        public static string Set(string list, string key, bool on)
        {
            List<string> keys = new List<string>();
            foreach (string k in list.Split(',')) if (k.Trim().Length > 0 && k.Trim() != key) keys.Add(k.Trim());
            if (on) keys.Add(key);
            return string.Join(",", keys.ToArray());
        }

        // The MELEE_LOG value for these settings, "" when it is the game's default.
        public static string LogSpec(Settings s)
        {
            List<string> t = new List<string>();
            if (s.LogAll) t.Add("all");
            foreach (Choice c in Categories) if (!s.LogAll && Has(s.LogCategories, c.Key)) t.Add(c.Key);
            if (s.LogRender > 0 && !s.LogAll) t.Add("render");
            if (s.LogRender < 0) t.Add("-render");
            if (!s.LogScene) t.Add("-scene");
            return string.Join(",", t.ToArray());
        }

        public static void ApplyEnvironment(Settings s, ProcessStartInfo psi)
        {
            string spec = LogSpec(s);
            if (spec.Length > 0) psi.EnvironmentVariables["MELEE_LOG"] = spec;
            else psi.EnvironmentVariables.Remove("MELEE_LOG");
            // the game maps these categories onto the old switches itself; set them too, so an
            // older build honours them
            bool heap = s.LogAll || Has(s.LogCategories, "heap"), dvd = s.LogAll || Has(s.LogCategories, "dvd");
            if (heap) psi.EnvironmentVariables["MELEE_HEAP_TRACE"] = "1"; else psi.EnvironmentVariables.Remove("MELEE_HEAP_TRACE");
            if (dvd) psi.EnvironmentVariables["MELEE_DVD_TRACE"] = "1"; else psi.EnvironmentVariables.Remove("MELEE_DVD_TRACE");
            if (!s.LogScene) psi.EnvironmentVariables["MELEE_SCENE_TRACE"] = "0"; else psi.EnvironmentVariables.Remove("MELEE_SCENE_TRACE");
            if (s.PadDiag >= 0) psi.EnvironmentVariables["MELEE_PAD_DIAG"] = s.PadDiag.ToString();
            else psi.EnvironmentVariables.Remove("MELEE_PAD_DIAG");
            if (s.PadReleaseOnBlur >= 0) psi.EnvironmentVariables["MELEE_PAD_RELEASE_ON_BLUR"] = s.PadReleaseOnBlur.ToString();
            else psi.EnvironmentVariables.Remove("MELEE_PAD_RELEASE_ON_BLUR");
            foreach (KeyValuePair<string, string> kv in TraceEnv)
            {
                if (Has(s.Traces, kv.Key)) psi.EnvironmentVariables[kv.Value] = "1";
                else psi.EnvironmentVariables.Remove(kv.Value);
            }
        }

        // One line for the status bar / About: what is switched on beyond the defaults.
        public static string Summary(Settings s)
        {
            List<string> on = new List<string>();
            string spec = LogSpec(s);
            if (spec.Length > 0) on.Add("MELEE_LOG=" + spec);
            if (s.PadDiag >= 0) on.Add("pad diagnostics " + s.PadDiag);
            if (s.PadReleaseOnBlur >= 0) on.Add("release adapter on focus loss " + (s.PadReleaseOnBlur == 1 ? "on" : "off"));
            foreach (Choice c in TraceList) if (Has(s.Traces, c.Key)) on.Add(c.Key);
            return on.Count == 0 ? "Diagnostics: the game's defaults." : "Diagnostics on: " + string.Join(", ", on.ToArray()) + ".";
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Crash reports: crashlogs\crash-<time>.log is the game's compact report (at most 64 KB, user
    // paths already replaced); crash-<time>-full.log beside it is the whole log and never leaves the
    // machine. NOTHING is uploaded automatically: only when the player has ticked the opt-in on the
    // Diagnostics tab AND clicks "Upload last 3 crash logs" are the three newest compact reports
    // POSTed to the matchmaking server named in netplay_server.txt (http://<host:port>/crash,
    // tools/release/crash_upload_server.py); each sent one gets a .sent file. A fault while the
    // game was already shutting down (the window was closed) is marked "during shutdown: yes" by
    // the game; those do not alarm the player and are not uploaded.
    // ---------------------------------------------------------------------------------------------

    static class Crashes
    {
        public static string Dir { get { return Path.Combine(Game.RunDir, "crashlogs"); } }
        public const int MaxUpload = 64 * 1024;

        public static List<FileInfo> Reports()
        {
            List<FileInfo> r = new List<FileInfo>();
            try
            {
                if (!Directory.Exists(Dir)) return r;
                foreach (FileInfo f in new DirectoryInfo(Dir).GetFiles("crash-*.log"))
                    if (!f.Name.EndsWith("-full.log", StringComparison.OrdinalIgnoreCase)) r.Add(f);
            }
            catch { }
            r.Sort(delegate(FileInfo a, FileInfo b) { return a.LastWriteTimeUtc.CompareTo(b.LastWriteTimeUtc); });
            return r;
        }

        public static FileInfo Latest()
        {
            List<FileInfo> r = Reports();
            return r.Count > 0 ? r[r.Count - 1] : null;
        }

        static string Head(FileInfo f)
        {
            try
            {
                using (StreamReader rd = new StreamReader(f.FullName))
                {
                    char[] b = new char[2048];
                    int n = rd.Read(b, 0, b.Length);
                    return new string(b, 0, Math.Max(0, n));
                }
            }
            catch { return ""; }
        }

        // An old-style report (the whole log, before 0.1.2) has no header; it is never uploaded.
        public static bool IsCompact(FileInfo f) { return Head(f).StartsWith("==== GD's Melee crash report ===="); }
        public static bool DuringShutdown(FileInfo f) { return Head(f).Contains("during shutdown: yes"); }
        public static bool Sent(FileInfo f) { return File.Exists(f.FullName + ".sent"); }

        // Reports the player should hear about / that may be uploaded: compact, not a teardown fault.
        public static List<FileInfo> Real(DateTime sinceUtc)
        {
            List<FileInfo> r = new List<FileInfo>();
            foreach (FileInfo f in Reports())
                if (f.LastWriteTimeUtc >= sinceUtc && IsCompact(f) && !DuringShutdown(f)) r.Add(f);
            return r;
        }

        // The newest n compact reports that may be uploaded (not teardown faults), newest first.
        public static List<FileInfo> Newest(int n)
        {
            List<FileInfo> all = Real(DateTime.MinValue), r = new List<FileInfo>();
            for (int i = all.Count - 1; i >= 0 && r.Count < n; i--)
                if (all[i].Length <= MaxUpload) r.Add(all[i]);
            return r;
        }

        public static string Server()
        {
            try
            {
                if (File.Exists(Game.ServerFile))
                {
                    foreach (string line in File.ReadAllLines(Game.ServerFile))
                        if (line.Trim().Length > 0 && !line.Trim().StartsWith("#")) return line.Trim();
                }
            }
            catch { }
            return "";
        }

        // Defence in depth: the game already replaced these, but the launcher checks again.
        public static string Scrub(string text)
        {
            string profile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            if (profile.Length > 3)
            {
                text = System.Text.RegularExpressions.Regex.Replace(text, System.Text.RegularExpressions.Regex.Escape(profile), "%USERPROFILE%",
                    System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                text = System.Text.RegularExpressions.Regex.Replace(text, System.Text.RegularExpressions.Regex.Escape(profile.Replace('\\', '/')), "%USERPROFILE%",
                    System.Text.RegularExpressions.RegexOptions.IgnoreCase);
            }
            string user = Environment.UserName;
            if (user.Length >= 3)
                text = System.Text.RegularExpressions.Regex.Replace(text, System.Text.RegularExpressions.Regex.Escape(user), "<user>",
                    System.Text.RegularExpressions.RegexOptions.IgnoreCase);
            return text;
        }

        // POSTs one report. Returns null on success (and writes the .sent marker), else why not.
        public static string Upload(FileInfo f)
        {
            string server = Server();
            if (server.Length == 0) return "no matchmaking server is set (netplay_server.txt)";
            try
            {
                byte[] body = new UTF8Encoding(false).GetBytes(Scrub(File.ReadAllText(f.FullName)));
                if (body.Length > MaxUpload) return "the report is over 64 KB";
                System.Net.HttpWebRequest rq = (System.Net.HttpWebRequest)System.Net.WebRequest.Create("http://" + server + "/crash");
                rq.Method = "POST";
                rq.ContentType = "text/plain; charset=utf-8";
                rq.Timeout = 10000;
                rq.ReadWriteTimeout = 10000;
                rq.UserAgent = "GDMeleeLauncher/" + Game.Version();
                rq.ContentLength = body.Length;
                using (Stream st = rq.GetRequestStream()) st.Write(body, 0, body.Length);
                using (System.Net.HttpWebResponse rs = (System.Net.HttpWebResponse)rq.GetResponse())
                using (StreamReader rd = new StreamReader(rs.GetResponseStream()))
                {
                    string answer = rd.ReadToEnd().Trim();
                    File.WriteAllText(f.FullName + ".sent", DateTime.Now.ToString("s") + " " + server + " " + answer + "\r\n");
                    return null;
                }
            }
            catch (System.Net.WebException e)
            {
                System.Net.HttpWebResponse rs = e.Response as System.Net.HttpWebResponse;
                if (rs != null && (int)rs.StatusCode == 400)
                    try { File.WriteAllText(f.FullName + ".sent", "refused by the server (400)\r\n"); } catch { }
                return rs != null ? "the server answered " + (int)rs.StatusCode : e.Message;
            }
            catch (Exception e) { return e.Message; }
        }

        // Uploads the newest three reports (the opt-in is the caller's check). Returns what happened.
        public static string UploadNewest(out bool ok)
        {
            List<FileInfo> files = Newest(3);
            int sent = 0;
            string err = null;
            ok = false;
            if (files.Count == 0) return "no crash reports to send (in " + Dir + ")";
            foreach (FileInfo f in files)
            {
                err = Upload(f);
                if (err != null) break;
                sent++;
            }
            ok = err == null;
            return err == null ? "sent " + sent + " crash report" + (sent == 1 ? "" : "s")
                               : "sent " + sent + " of " + files.Count + ", then failed: " + err;
        }
    }

    // ---------------------------------------------------------------------------------------------
    // MODS HOOK (charlie C2 / delta D1)
    //
    // Everything mod-related the launcher does goes through this class, so the mods browser can
    // replace it without touching the rest. Today: the game's own loader reads MELEE_MODS_DIR
    // (default: "mods" next to melee-pc.exe). Mods are always loaded, online included: the game
    // matches fighters and stages between the two players by content hash (delta's work), so
    // there is deliberately NO "mods off for online" switch (user decision, 2026-09-22).
    // To add the browser: fill BuildTab() (it gets the "Mods" tab page) and, once delta's
    // enabled-set file exists, write it here per disc before the game starts.
    // ---------------------------------------------------------------------------------------------

    static class Mods
    {
        public static void ApplyEnvironment(Settings s, Disc disc, ProcessStartInfo psi)
        {
            Directory.CreateDirectory(Game.ModsDir);
            psi.EnvironmentVariables["MELEE_MODS_DIR"] = Game.AnsiSafe(Game.ModsDir);
            psi.EnvironmentVariables.Remove("MELEE_MODS");
        }

        public static ModsTab BuildTab(TabPage page, MainForm form, Settings s)
        {
            return new ModsTab(page, form, s); // ModsBrowser.cs
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Small UI helpers
    // ---------------------------------------------------------------------------------------------

    static class UI
    {
        public static readonly Color Accent = Color.FromArgb(0xC8, 0x2E, 0x3C);
        public static readonly Color Header = Color.FromArgb(0x1B, 0x1D, 0x24);
        public static Font Body = new Font("Segoe UI", 9.75f);
        public static Font Bold = new Font("Segoe UI Semibold", 9.75f);

        public static Label Para(string text)
        {
            Label l = new Label();
            l.Text = text;
            l.AutoSize = true;
            l.MaximumSize = new Size(560, 0);
            l.Margin = new Padding(0, 0, 0, 10);
            return l;
        }

        public static Button Btn(string text, EventHandler click)
        {
            Button b = new Button();
            b.Text = text;
            b.AutoSize = true;
            b.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            b.Padding = new Padding(8, 2, 8, 2);
            b.Margin = new Padding(0, 0, 6, 6);
            b.UseVisualStyleBackColor = true;
            if (click != null) b.Click += click;
            return b;
        }

        public static FlowLayoutPanel Column(params Control[] cs)
        {
            FlowLayoutPanel f = new FlowLayoutPanel();
            f.FlowDirection = FlowDirection.TopDown;
            f.WrapContents = false;
            f.Dock = DockStyle.Fill;
            f.Padding = new Padding(14);
            f.AutoScroll = true;
            f.Controls.AddRange(cs);
            return f;
        }

        public static FlowLayoutPanel Row(params Control[] cs)
        {
            FlowLayoutPanel f = new FlowLayoutPanel();
            f.FlowDirection = FlowDirection.LeftToRight;
            f.AutoSize = true;
            f.WrapContents = true;
            f.Margin = new Padding(0);
            f.Controls.AddRange(cs);
            return f;
        }
    }

    // ---------------------------------------------------------------------------------------------
    // The window
    // ---------------------------------------------------------------------------------------------

    class MainForm : Form
    {
        Settings s;
        TabControl tabs;
        ListView list;
        Button playBtn, changeBtn, renameBtn, forgetBtn, defaultBtn;
        CheckBox unlockAll, skipIntro, keyboard, closeOnPlay;
        Label status, detail;
        TextBox serverBox;
        Label serverState;
        Process running;
        DateTime runningSince;
        bool firstRunPrompted;

        public MainForm(Settings settings)
        {
            s = settings;
            Text = "GD's Melee";
            Font = UI.Body;
            AutoScaleMode = AutoScaleMode.Dpi;
            StartPosition = FormStartPosition.CenterScreen;
            ClientSize = new Size(760, 600);
            MinimumSize = new Size(640, 480);
            try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }

            Panel head = new Panel();
            head.Dock = DockStyle.Top;
            head.Height = 64;
            head.BackColor = UI.Header;
            head.Paint += delegate(object o, PaintEventArgs e)
            {
                e.Graphics.TextRenderingHint = System.Drawing.Text.TextRenderingHint.ClearTypeGridFit;
                using (Font big = new Font("Segoe UI Semibold", 18f))
                using (Font small = new Font("Segoe UI", 9f))
                using (SolidBrush accent = new SolidBrush(UI.Accent))
                {
                    e.Graphics.FillRectangle(accent, 0, head.Height - 3, head.Width, 3);
                    e.Graphics.DrawString("GD's Melee", big, Brushes.White, 14, 12);
                    string v = Game.Version();
                    SizeF vs = e.Graphics.MeasureString(v, small);
                    e.Graphics.DrawString(v, small, Brushes.Gainsboro, head.Width - vs.Width - 14, 24);
                }
            };
            head.Resize += delegate { head.Invalidate(); };

            status = new Label();
            status.Dock = DockStyle.Bottom;
            status.Height = 26;
            status.Padding = new Padding(10, 0, 10, 0);
            status.TextAlign = ContentAlignment.MiddleLeft;
            status.BackColor = Color.FromArgb(0xF0, 0xF0, 0xF2);

            tabs = new TabControl();
            tabs.Dock = DockStyle.Fill;
            tabs.Padding = new Point(14, 5);
            tabs.TabPages.Add(BuildPlayTab());
            tabs.TabPages.Add(BuildOnlineTab());
            TabPage mods = new TabPage("Mods");
            modsTab = Mods.BuildTab(mods, this, s);
            tabs.TabPages.Add(mods);
            tabs.TabPages.Add(BuildDiagnosticsTab());
            tabs.TabPages.Add(BuildAboutTab());

            Controls.Add(tabs);
            Controls.Add(status);
            Controls.Add(head);

            RefreshList();
            SetStatus(Game.MissingFiles().Length > 0
                ? "Missing game files: " + string.Join(", ", Game.MissingFiles()) + ". Unzip the whole release again."
                : "Ready.");
            Shown += delegate
            {
                FirstRun();
                if (OpenModsOnShow)
                {
                    tabs.SelectedIndex = 2;
                    modsTab.Refresh();
                }
            };
            FormClosing += delegate { SaveOptions(); };
        }

        public TabControl Tabs { get { return tabs; } }
        ModsTab modsTab;
        public bool OpenModsOnShow; // --mods: open on the Mods tab and read the sources

        void SetStatus(string t) { status.Text = t; }
        public void Status(string t) { SetStatus(t); }

        // --- Play tab ------------------------------------------------------------------------------

        TabPage BuildPlayTab()
        {
            TabPage page = new TabPage("Play");
            page.Padding = new Padding(12);

            list = new ListView();
            list.View = View.Details;
            list.FullRowSelect = true;
            list.HideSelection = false;
            list.MultiSelect = false;
            list.Dock = DockStyle.Fill;
            list.Columns.Add("Disc", 190);
            list.Columns.Add("Detected", 160);
            list.Columns.Add("File", 300);
            list.SelectedIndexChanged += delegate { UpdateButtons(); };
            list.Resize += delegate { FitColumns(); };
            list.DoubleClick += delegate { Play(); };

            Button add = UI.Btn("&Add disc...", delegate { AddDisc(); });
            changeBtn = UI.Btn("&Change ISO...", delegate { ChangeIso(); });
            renameBtn = UI.Btn("&Rename...", delegate { Rename(); });
            defaultBtn = UI.Btn("Make &default", delegate { MakeDefault(); });
            forgetBtn = UI.Btn("&Forget", delegate { Forget(); });
            foreach (Button b in new[] { add, changeBtn, renameBtn, defaultBtn, forgetBtn })
            {
                b.AutoSize = false;
                b.Size = new Size(124, 30);
            }
            FlowLayoutPanel side = new FlowLayoutPanel();
            side.FlowDirection = FlowDirection.TopDown;
            side.Dock = DockStyle.Right;
            side.Width = 140;
            side.Padding = new Padding(10, 0, 0, 0);
            side.Controls.AddRange(new Control[] { add, changeBtn, renameBtn, defaultBtn, forgetBtn });

            detail = new Label();
            detail.Dock = DockStyle.Bottom;
            detail.Height = 40;
            detail.Padding = new Padding(0, 6, 0, 0);
            detail.ForeColor = Color.DimGray;
            detail.AutoEllipsis = true;

            unlockAll = new CheckBox { Text = "Unlock every character and stage (your save is not changed)", Checked = s.UnlockAll, AutoSize = true };
            skipIntro = new CheckBox { Text = "Skip the intro movie", Checked = s.SkipIntro, AutoSize = true };
            keyboard = new CheckBox { Text = "Keyboard only (ignore controllers and the adapter)", Checked = s.KeyboardOnly, AutoSize = true };
            closeOnPlay = new CheckBox { Text = "Close this launcher when the game starts", Checked = s.CloseOnPlay, AutoSize = true };
            foreach (CheckBox c in new[] { unlockAll, skipIntro, keyboard, closeOnPlay })
            {
                c.Margin = new Padding(0, 0, 18, 2);
                c.CheckedChanged += delegate { SaveOptions(); };
            }
            FlowLayoutPanel opts = new FlowLayoutPanel();
            opts.FlowDirection = FlowDirection.TopDown;
            opts.AutoSize = true;
            opts.Controls.AddRange(new Control[] { unlockAll, skipIntro, keyboard, closeOnPlay });
            Label volLabel = new Label { AutoSize = true, Margin = new Padding(0, 6, 6, 0), Text = "Game volume: " + s.Volume + "%" };
            TrackBar vol = new TrackBar { Minimum = 0, Maximum = 100, TickFrequency = 10, SmallChange = 5, LargeChange = 10,
                                          Value = s.Volume, Width = 180, Height = 30, AutoSize = false, Margin = new Padding(0) };
            vol.ValueChanged += delegate { s.Volume = vol.Value; volLabel.Text = "Game volume: " + vol.Value + "%"; };
            vol.MouseUp += delegate { SaveOptions(); };
            vol.KeyUp += delegate { SaveOptions(); };
            opts.Controls.Add(UI.Row(volLabel, vol));
            Label kpLabel = new Label { AutoSize = true, Margin = new Padding(0, 6, 6, 0), Text = "Keyboard plays as:" };
            ComboBox kp = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = 300, Margin = new Padding(0, 2, 0, 0) };
            kp.Items.AddRange(new object[] { "Port 1, shared with a controller (default)", "Port 2 (a separate player)", "Port 3", "Port 4" });
            kp.SelectedIndex = s.KeyboardPort <= 1 ? 0 : s.KeyboardPort - 1;
            kp.SelectedIndexChanged += delegate { s.KeyboardPort = kp.SelectedIndex == 0 ? 0 : kp.SelectedIndex + 1; TrySave(); };
            opts.Controls.Add(UI.Row(kpLabel, kp));

            playBtn = new Button();
            playBtn.Text = "PLAY";
            playBtn.Font = new Font("Segoe UI Semibold", 14f);
            playBtn.Size = new Size(140, 56);
            playBtn.BackColor = UI.Accent;
            playBtn.ForeColor = Color.White;
            playBtn.FlatStyle = FlatStyle.Flat;
            playBtn.FlatAppearance.BorderSize = 0;
            playBtn.Anchor = AnchorStyles.Right | AnchorStyles.Top;
            playBtn.Click += delegate { Play(); };

            TableLayoutPanel bottom = new TableLayoutPanel();
            bottom.Dock = DockStyle.Bottom;
            bottom.Height = 184;
            bottom.ColumnCount = 2;
            bottom.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            bottom.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            bottom.Padding = new Padding(0, 8, 0, 0);
            bottom.Controls.Add(opts, 0, 0);
            bottom.Controls.Add(playBtn, 1, 0);

            Panel top = new Panel();
            top.Dock = DockStyle.Fill;
            top.Controls.Add(list);
            top.Controls.Add(side);

            page.Controls.Add(top);
            page.Controls.Add(detail);
            page.Controls.Add(bottom);
            AcceptButton = playBtn;
            return page;
        }

        // The File column takes whatever width the other two leave, so there is no sideways scrollbar.
        void FitColumns()
        {
            if (list.Columns.Count < 3) return;
            int w = list.ClientSize.Width - list.Columns[0].Width - list.Columns[1].Width;
            list.Columns[2].Width = Math.Max(120, w);
        }

        Disc Selected
        {
            get
            {
                if (list.SelectedItems.Count == 0) return null;
                return list.SelectedItems[0].Tag as Disc;
            }
        }

        void RefreshList() { RefreshList(null); }

        void RefreshList(string selectId)
        {
            if (selectId == null && Selected != null) selectId = Selected.Id;
            if (selectId == null && s.Default != null) selectId = s.Default.Id;
            list.BeginUpdate();
            list.Items.Clear();
            Disc def = s.Default;
            foreach (Disc d in s.Discs)
            {
                bool present = File.Exists(d.Path);
                ListViewItem it = new ListViewItem((d == def ? "\u2605 " : "     ") + d.Name);
                it.SubItems.Add(present ? d.Kind : "FILE MISSING");
                it.SubItems.Add(d.Path);
                it.Tag = d;
                if (!present) it.ForeColor = Color.Firebrick;
                if (d == def) it.Font = UI.Bold;
                list.Items.Add(it);
                if (d.Id == selectId) it.Selected = true;
            }
            list.EndUpdate();
            if (list.SelectedItems.Count == 0 && list.Items.Count > 0) list.Items[0].Selected = true;
            UpdateButtons();
        }

        void UpdateButtons()
        {
            Disc d = Selected;
            bool has = d != null;
            changeBtn.Enabled = renameBtn.Enabled = forgetBtn.Enabled = has;
            defaultBtn.Enabled = has && d != s.Default;
            playBtn.Enabled = has && running == null;
            if (!has)
                detail.Text = s.Discs.Count == 0 ? "No disc yet. Click \"Add disc...\" and pick your Melee .iso." : "";
            else
                detail.Text = (File.Exists(d.Path) ? "" : "The file is gone. Use \"Change ISO...\" to point at its new place.\r\n") +
                              "Saves for this disc: " + Path.Combine(Path.Combine(Settings.UserDir, "saves"), d.Id);
        }

        void SaveOptions()
        {
            if (skipIntro == null) return;
            s.UnlockAll = unlockAll.Checked;
            s.SkipIntro = skipIntro.Checked;
            s.KeyboardOnly = keyboard.Checked;
            s.CloseOnPlay = closeOnPlay.Checked;
            TrySave();
        }

        void TrySave()
        {
            try { s.Save(); }
            catch (Exception e) { SetStatus("Could not save settings: " + e.Message); }
        }

        string PickIso(string title)
        {
            using (OpenFileDialog dlg = new OpenFileDialog())
            {
                dlg.Title = title;
                dlg.Filter = "GameCube disc images (*.iso;*.gcm)|*.iso;*.gcm|All files (*.*)|*.*";
                dlg.CheckFileExists = true;
                if (Selected != null && File.Exists(Selected.Path)) dlg.InitialDirectory = Path.GetDirectoryName(Selected.Path);
                return dlg.ShowDialog(this) == DialogResult.OK ? dlg.FileName : null;
            }
        }

        // Checks a picked file and tells the user what it is. Returns the probe, or null if refused.
        DiscInfo CheckIso(string path)
        {
            Cursor = Cursors.WaitCursor;
            DiscInfo info = DiscProbe.Probe(path);
            Cursor = Cursors.Default;
            if (info.Verdict == DiscVerdict.Bad)
            {
                MessageBox.Show(this, Path.GetFileName(path) + "\r\n\r\n" + info.Describe(), "This disc can't be used",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                return null;
            }
            if (info.Verdict == DiscVerdict.Warn)
            {
                DialogResult r = MessageBox.Show(this, Path.GetFileName(path) + "\r\n\r\n" + info.Describe() + "\r\n\r\nUse it anyway?",
                    "Check this disc", MessageBoxButtons.YesNo, MessageBoxIcon.Warning);
                return r == DialogResult.Yes ? info : null;
            }
            return info;
        }

        public Disc AddPath(string path, bool quiet)
        {
            path = Path.GetFullPath(path);
            foreach (Disc existing in s.Discs)
                if (string.Equals(existing.Path, path, StringComparison.OrdinalIgnoreCase))
                {
                    RefreshList(existing.Id);
                    if (!quiet) SetStatus("That disc is already in the list: " + existing.Name);
                    return existing;
                }
            DiscInfo info = quiet ? DiscProbe.Probe(path) : CheckIso(path);
            if (info == null || info.Verdict == DiscVerdict.Bad)
            {
                if (quiet && info != null) SetStatus("Not added: " + info.Message);
                return null;
            }
            Disc d = new Disc();
            d.Kind = info.Kind;
            d.Name = info.Kind.StartsWith("Melee 1.02 (vanilla)") ? "Melee" :
                     info.Kind.StartsWith("ACE") ? "ACE" :
                     info.Kind.StartsWith("Akaneia") ? "Akaneia" :
                     info.Kind.StartsWith("Training Mode") ? "TM-CE" :
                     info.Kind.StartsWith("20XX") ? "20XX" : Path.GetFileNameWithoutExtension(path);
            d.Id = s.NewId(d.Name);
            d.Path = path;
            s.Discs.Add(d);
            if (s.Find(s.DefaultId) == null) s.DefaultId = d.Id;
            TrySave();
            RefreshList(d.Id);
            SetStatus("Added " + d.Name + ": " + d.Kind + ".");
            return d;
        }

        void AddDisc()
        {
            string p = PickIso("Pick a Super Smash Bros. Melee disc image (NTSC 1.02, or an ACE/Akaneia build)");
            if (p != null) AddPath(p, false);
        }

        void FirstRun()
        {
            if (firstRunPrompted || s.Discs.Count > 0 || Game.MissingFiles().Length > 0) return;
            firstRunPrompted = true;
            MessageBox.Show(this,
                "Welcome to GD's Melee.\r\n\r\nGD's Melee contains no Nintendo game data. It runs from your own disc image of " +
                "Super Smash Bros. Melee: NTSC-U (USA) revision 1.02, as a plain .iso (or an ACE / Akaneia build made from it).\r\n\r\n" +
                "Pick the file next. It is remembered; you can add more discs, change or forget them later.",
                "GD's Melee - first run", MessageBoxButtons.OK, MessageBoxIcon.Information);
            AddDisc();
        }

        void ChangeIso()
        {
            Disc d = Selected;
            if (d == null) return;
            string p = PickIso("Pick the new disc image for \"" + d.Name + "\"");
            if (p == null) return;
            DiscInfo info = CheckIso(p);
            if (info == null) return;
            d.Path = Path.GetFullPath(p);
            d.Kind = info.Kind;
            TrySave();
            RefreshList(d.Id);
            SetStatus(d.Name + " now boots " + Path.GetFileName(p) + " (" + info.Kind + "). Its saves are unchanged.");
        }

        void Rename()
        {
            Disc d = Selected;
            if (d == null) return;
            string n = Prompt("Rename disc", "Name shown in the list:", d.Name);
            if (string.IsNullOrEmpty(n)) return;
            d.Name = n.Trim();
            TrySave();
            RefreshList(d.Id);
        }

        void MakeDefault()
        {
            Disc d = Selected;
            if (d == null) return;
            s.DefaultId = d.Id;
            TrySave();
            RefreshList(d.Id);
            SetStatus(d.Name + " is the default (\"--play\" and double-click boot it).");
        }

        void Forget()
        {
            Disc d = Selected;
            if (d == null) return;
            if (MessageBox.Show(this, "Forget \"" + d.Name + "\"?\r\n\r\nThe disc image itself is not touched, and its saves stay in\r\n" +
                    Path.Combine(Path.Combine(Settings.UserDir, "saves"), d.Id), "Forget disc",
                    MessageBoxButtons.OKCancel, MessageBoxIcon.Question) != DialogResult.OK) return;
            s.Discs.Remove(d);
            if (s.DefaultId == d.Id) s.DefaultId = s.Discs.Count > 0 ? s.Discs[0].Id : "";
            TrySave();
            RefreshList();
            SetStatus("Forgot " + d.Name + ".");
        }

        public void Play()
        {
            Disc d = Selected;
            if (d == null || running != null) return;
            string[] missing = Game.MissingFiles();
            if (missing.Length > 0)
            {
                MessageBox.Show(this, "These game files are missing next to the launcher:\r\n\r\n" + string.Join("\r\n", missing) +
                    "\r\n\r\nUnzip the whole release into one folder.", "GD's Melee", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }
            if (!File.Exists(d.Path))
            {
                if (MessageBox.Show(this, "The disc image for \"" + d.Name + "\" is no longer at\r\n" + d.Path + "\r\n\r\nFind it now?",
                        "Disc not found", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) == DialogResult.Yes) ChangeIso();
                return;
            }
            SaveOptions();
            try
            {
                running = Game.Start(s, d);
                runningSince = DateTime.Now;
                running.EnableRaisingEvents = true;
                running.Exited += delegate { BeginInvoke(new MethodInvoker(GameExited)); };
                SetStatus("Running " + d.Name + " (" + Path.GetFileName(d.Path) + ").");
                UpdateButtons();
                if (s.CloseOnPlay) Close();
                else WindowState = FormWindowState.Minimized;
            }
            catch (Exception e)
            {
                running = null;
                MessageBox.Show(this, "Could not start melee-pc.exe:\r\n" + e.Message, "GD's Melee", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        void GameExited()
        {
            int code = 0;
            try { code = running.ExitCode; } catch { }
            double secs = (DateTime.Now - runningSince).TotalSeconds;
            running = null;
            if (WindowState == FormWindowState.Minimized) WindowState = FormWindowState.Normal;
            Activate();
            UpdateButtons();
            // A crash is a NEW compact report from this session that the game did not mark "during
            // shutdown". Closing the window (exit 0, no report) is never one, and neither is a fault
            // while the game was already tearing down after the window was closed.
            List<FileInfo> fresh = Crashes.Real(runningSince.ToUniversalTime().AddSeconds(-2));
            if (fresh.Count > 0)
            {
                FileInfo f = fresh[fresh.Count - 1];
                SetStatus("The game crashed after " + (int)secs + " s. Report: " + f.FullName);
                if (MessageBox.Show(this, "The game stopped with an error" + (code != 0 ? " (exit code 0x" + code.ToString("X8") + ")" : "") + ".\r\n\r\n" +
                        "A short crash report was written to\r\n" + f.FullName + "\r\n(the whole log is beside it, ending in -full.log).\r\n\r\nOpen the report?",
                        "GD's Melee", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) == DialogResult.Yes)
                    Process.Start("notepad.exe", "\"" + f.FullName + "\"");
            }
            else if (code != 0 && Game.ClosedByUser())
            {
                // The window was closed and the game then faulted while tearing the renderer down
                // (a known Dawn shutdown crash). Nothing was lost; don't alarm the user.
                SetStatus("The game closed.");
            }
            else if (code != 0)
            {
                SetStatus("The game stopped with an error (code 0x" + code.ToString("X8") + ") after " + (int)secs + " s.");
                if (MessageBox.Show(this, "The game stopped with an error (exit code 0x" + code.ToString("X8") + ").\r\n\r\n" +
                        "Its log is " + Game.LogFile + " (crash logs are in the crashlogs folder beside it).\r\nOpen the log?",
                        "GD's Melee", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) == DialogResult.Yes) OpenLog();
            }
            else SetStatus("The game closed.");
        }

        void OpenLog()
        {
            if (File.Exists(Game.LogFile)) Process.Start("notepad.exe", "\"" + Game.LogFile + "\"");
            else MessageBox.Show(this, "No log yet: " + Game.LogFile, "GD's Melee");
        }

        static string Prompt(string title, string label, string value)
        {
            using (Form f = new Form())
            {
                f.Text = title;
                f.Font = UI.Body;
                f.FormBorderStyle = FormBorderStyle.FixedDialog;
                f.StartPosition = FormStartPosition.CenterParent;
                f.MinimizeBox = f.MaximizeBox = false;
                f.ClientSize = new Size(380, 110);
                Label l = new Label { Text = label, Left = 12, Top = 12, AutoSize = true };
                TextBox t = new TextBox { Text = value, Left = 12, Top = 36, Width = 356 };
                Button ok = new Button { Text = "OK", DialogResult = DialogResult.OK, Left = 212, Top = 70, Width = 75 };
                Button cancel = new Button { Text = "Cancel", DialogResult = DialogResult.Cancel, Left = 293, Top = 70, Width = 75 };
                f.Controls.AddRange(new Control[] { l, t, ok, cancel });
                f.AcceptButton = ok;
                f.CancelButton = cancel;
                return f.ShowDialog() == DialogResult.OK ? t.Text : null;
            }
        }

        // --- Online tab ----------------------------------------------------------------------------

        TabPage BuildOnlineTab()
        {
            TabPage page = new TabPage("Online");
            Label intro = UI.Para(
                "Online play is in the game: Main Menu > VS. Mode > Melee > Online Play. Both players need this same release " +
                "of GD's Melee. Mods are welcome online: any fighter or stage you both have can be picked (see the Mods tab).\r\n\r\n" +
                "Room codes (short codes instead of IP addresses) need a matchmaking server. Enter its address here as " +
                "host:port, or leave it empty to swap addresses by hand. The setting is stored in netplay_server.txt next to the game.");
            Label lbl = new Label { Text = "Matchmaking server (host:port):", AutoSize = true, Margin = new Padding(0, 4, 0, 4) };
            serverBox = new TextBox { Width = 320, Margin = new Padding(0, 0, 0, 6) };
            serverState = new Label { AutoSize = true, ForeColor = Color.DimGray, Margin = new Padding(0, 0, 0, 10) };
            Button save = UI.Btn("Save", delegate { SaveServer(serverBox.Text.Trim()); });
            Button clear = UI.Btn("Clear", delegate { serverBox.Text = ""; SaveServer(""); });
            Button howto = UI.Btn("How to play online", delegate
            {
                string f = Path.Combine(Settings.AppDir, "HOW TO PLAY ONLINE.txt");
                if (File.Exists(f)) Process.Start("notepad.exe", "\"" + f + "\"");
            });
            page.Controls.Add(UI.Column(intro, lbl, serverBox, UI.Row(save, clear, howto), serverState));
            LoadServer();
            return page;
        }

        void LoadServer()
        {
            string v = "";
            try { if (File.Exists(Game.ServerFile)) v = File.ReadAllText(Game.ServerFile).Trim(); } catch { }
            serverBox.Text = v;
            serverState.Text = v.Length > 0 ? "Room codes use " + v + "." : "No server set: players swap addresses (the Online Play screen shows yours).";
        }

        void SaveServer(string v)
        {
            if (v.Length > 0)
            {
                int colon = v.LastIndexOf(':');
                int port;
                if (colon <= 0 || !int.TryParse(v.Substring(colon + 1), out port) || port < 1 || port > 65535 || v.Contains(" "))
                {
                    MessageBox.Show(this, "Write it as host:port, for example play.example.net:51500", "Matchmaking server",
                        MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }
            }
            try
            {
                if (v.Length > 0) File.WriteAllText(Game.ServerFile, v + "\r\n", Encoding.ASCII);
                else if (File.Exists(Game.ServerFile)) File.Delete(Game.ServerFile);
                LoadServer();
                SetStatus("Server setting saved.");
            }
            catch (Exception e)
            {
                MessageBox.Show(this, "Could not write " + Game.ServerFile + ":\r\n" + e.Message +
                    "\r\n\r\nMove the game to a folder you can write to (not Program Files).", "Matchmaking server");
            }
        }

        // --- Diagnostics tab -----------------------------------------------------------------------

        ToolTip tips;
        CheckBox sendReports;
        Button uploadBtn;
        Label diagSummary;

        static Label Heading(string text)
        {
            return new Label { Text = text, Font = UI.Bold, AutoSize = true, Margin = new Padding(0, 10, 0, 4) };
        }

        CheckBox Toggle(string label, string tip, bool on, EventHandler changed)
        {
            CheckBox c = new CheckBox { Text = label, Checked = on, AutoSize = true, Margin = new Padding(12, 0, 18, 2) };
            tips.SetToolTip(c, tip);
            c.CheckedChanged += changed;
            return c;
        }

        ComboBox Pick(string tip, string[] items, int index, EventHandler changed)
        {
            ComboBox b = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = 300, Margin = new Padding(0, 0, 0, 4) };
            b.Items.AddRange(items);
            b.SelectedIndex = Math.Max(0, Math.Min(items.Length - 1, index));
            tips.SetToolTip(b, tip);
            b.SelectedIndexChanged += changed;
            return b;
        }

        void DiagChanged()
        {
            TrySave();
            if (diagSummary != null) diagSummary.Text = Diagnostics.Summary(s) + " Changes apply the next time the game starts.";
        }

        TabPage BuildDiagnosticsTab()
        {
            TabPage page = new TabPage("Diagnostics");
            tips = new ToolTip { AutoPopDelay = 20000, InitialDelay = 400 };
            List<Control> col = new List<Control>();
            col.Add(UI.Para("The game writes melee-pc.log in its folder. By default it keeps it short: scene changes, fighter, stage " +
                            "and mod loads, warnings and errors, online and controller events. If you are asked for more detail " +
                            "for a bug report, turn on what you were asked for here, play until it happens, then send the log. " +
                            "Hover over an option for what it adds."));

            col.Add(Heading("Game log"));
            col.Add(Toggle("Scene changes and menu cursors (on by default)", "Every screen change and the menu cursor positions. Turn off only if asked.",
                s.LogScene, delegate(object o, EventArgs e) { s.LogScene = ((CheckBox)o).Checked; DiagChanged(); }));
            foreach (Choice c in Diagnostics.Categories)
            {
                string key = c.Key;
                col.Add(Toggle(c.Label, c.Tip, Diagnostics.Has(s.LogCategories, key),
                    delegate(object o, EventArgs e) { s.LogCategories = Diagnostics.Set(s.LogCategories, key, ((CheckBox)o).Checked); DiagChanged(); }));
            }
            Label rl = new Label { Text = "Rendering diagnostics (DIAG blocks):", AutoSize = true, Margin = new Padding(12, 6, 0, 2) };
            col.Add(rl);
            ComboBox render = Pick("The renderer's DIAG block: matrices, EFB copies, a depth grid and the camera. The first one after each scene change is enough to tell why a screen is black.",
                new[] { "One block per scene (default)", "Every block (every half second)", "None" },
                s.LogRender == 0 ? 0 : s.LogRender > 0 ? 1 : 2,
                delegate(object o, EventArgs e) { int i = ((ComboBox)o).SelectedIndex; s.LogRender = i == 0 ? 0 : i == 1 ? 1 : -1; DiagChanged(); });
            render.Margin = new Padding(12, 0, 0, 4);
            col.Add(render);
            col.Add(Toggle("Everything (MELEE_LOG=all)", "Every line from every category above, no flood limit. The log gets large quickly.",
                s.LogAll, delegate(object o, EventArgs e) { s.LogAll = ((CheckBox)o).Checked; DiagChanged(); }));

            col.Add(Heading("Controllers"));
            Label pl = new Label { Text = "Controller diagnostics (MELEE_PAD_DIAG):", AutoSize = true, Margin = new Padding(12, 0, 0, 2) };
            col.Add(pl);
            ComboBox pad = Pick("What the game logs about controllers and the GameCube adapter. Level 1, the event log (plugged in, unplugged, device switches), is the game's default; level 2 adds the old verbose dump of every pad every 30 frames.",
                new[] { "Game default (1, events)", "0 - off", "1 - events: plug, unplug, device switches", "2 - verbose: every pad every 30 frames (large)" },
                s.PadDiag + 1,
                delegate(object o, EventArgs e) { s.PadDiag = ((ComboBox)o).SelectedIndex - 1; DiagChanged(); });
            pad.Margin = new Padding(12, 0, 0, 4);
            col.Add(pad);
            Label bl = new Label { Text = "Let go of the GameCube adapter when the game window loses focus (MELEE_PAD_RELEASE_ON_BLUR):", AutoSize = true, MaximumSize = new Size(560, 0), Margin = new Padding(12, 4, 0, 2) };
            col.Add(bl);
            ComboBox blur = Pick("On (the game's default): switching to another window hands the adapter to Dolphin or another copy of the game, and it is taken back when you return. Off: the game keeps it, as Dolphin does. During online play it is always kept.",
                new[] { "Game default (on)", "Off - keep the adapter", "On - release it" },
                s.PadReleaseOnBlur + 1,
                delegate(object o, EventArgs e) { s.PadReleaseOnBlur = ((ComboBox)o).SelectedIndex - 1; DiagChanged(); });
            blur.Margin = new Padding(12, 0, 0, 4);
            col.Add(blur);

            col.Add(Heading("Deeper traces (only when asked)"));
            foreach (Choice c in Diagnostics.TraceList)
            {
                string key = c.Key;
                col.Add(Toggle(c.Label, c.Tip, Diagnostics.Has(s.Traces, key),
                    delegate(object o, EventArgs e) { s.Traces = Diagnostics.Set(s.Traces, key, ((CheckBox)o).Checked); DiagChanged(); }));
            }

            col.Add(Heading("Crash reports"));
            uploadBtn = UI.Btn("Upload last 3 crash logs", delegate { UploadCrashes(); });
            sendReports = Toggle("Allow uploading crash reports", "Off by default. Nothing is ever sent on its own: only the button below sends anything.",
                s.CrashUpload, delegate(object o, EventArgs e) { s.CrashUpload = ((CheckBox)o).Checked; uploadBtn.Enabled = s.CrashUpload; DiagChanged(); });
            col.Add(sendReports);
            Label consent = UI.Para(
                "What is sent: the short crash reports the game writes to crashlogs (crash-<time>.log, at most 64 KB each) - the game " +
                "version, the disc's ID and title, the mods you use, your settings, the error with the code it happened in, and the last " +
                "lines of the log. Your Windows user name is removed from every path and your player name is left out; the full log " +
                "(-full.log) is never sent.\r\n" +
                "Where: the matchmaking server this game uses for online play (netplay_server.txt).\r\n" +
                "Why: so crashes can be found and fixed without you having to send files by hand.\r\n" +
                "Nothing is sent automatically. The button sends your three newest reports (not faults that happened while the game was " +
                "closing), once, when you click it.");
            consent.Margin = new Padding(12, 2, 0, 6);
            consent.ForeColor = Color.DimGray;
            col.Add(consent);
            uploadBtn.Enabled = s.CrashUpload;
            uploadBtn.Margin = new Padding(12, 0, 6, 10);
            col.Add(uploadBtn);
            col.Add(UI.Row(
                UI.Btn("Open log folder", delegate { OpenRunDir(); }),
                UI.Btn("Open game log", delegate { OpenLog(); }),
                UI.Btn("Open latest crash report", delegate { OpenLatestCrash(); }),
                UI.Btn("Copy latest crash report", delegate { CopyLatestCrash(); }),
                UI.Btn("Reset to defaults", delegate { ResetDiagnostics(); })));
            diagSummary = new Label { AutoSize = true, MaximumSize = new Size(560, 0), ForeColor = Color.DimGray, Margin = new Padding(0, 6, 0, 0) };
            col.Add(diagSummary);
            DiagChanged();
            page.Controls.Add(UI.Column(col.ToArray()));
            return page;
        }

        void ResetDiagnostics()
        {
            s.LogRender = 0; s.LogScene = true; s.LogAll = false; s.LogCategories = ""; s.PadDiag = -1; s.PadReleaseOnBlur = -1; s.Traces = "";
            TrySave();
            int i = tabs.TabPages.IndexOf(tabs.SelectedTab);
            TabPage old = tabs.TabPages[i];
            tabs.TabPages.RemoveAt(i);
            tabs.TabPages.Insert(i, BuildDiagnosticsTab());
            tabs.SelectedIndex = i;
            old.Dispose();
            SetStatus("Diagnostics are back to the game's defaults.");
        }

        void OpenRunDir()
        {
            Directory.CreateDirectory(Game.RunDir);
            Process.Start("explorer.exe", "\"" + Game.RunDir + "\"");
        }

        void OpenLatestCrash()
        {
            FileInfo f = Crashes.Latest();
            if (f != null) Process.Start("notepad.exe", "\"" + f.FullName + "\"");
            else MessageBox.Show(this, "No crash reports in " + Crashes.Dir + ".", "GD's Melee");
        }

        void CopyLatestCrash()
        {
            FileInfo f = Crashes.Latest();
            if (f == null) { MessageBox.Show(this, "No crash reports in " + Crashes.Dir + ".", "GD's Melee"); return; }
            try
            {
                Clipboard.SetText(Crashes.Scrub(File.ReadAllText(f.FullName)));
                SetStatus("Copied " + f.Name + " (" + (f.Length / 1024) + " KB) to the clipboard.");
            }
            catch (Exception e) { SetStatus("Could not copy the report: " + e.Message); }
        }

        // "Upload last 3 crash logs": the only way anything leaves the machine.
        void UploadCrashes()
        {
            if (!s.CrashUpload) return;
            string server = Crashes.Server();
            if (server.Length == 0)
            {
                MessageBox.Show(this, "No matchmaking server is set (Online tab), so there is nowhere to send the reports.", "Upload crash logs",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            uploadBtn.Enabled = false;
            Cursor = Cursors.WaitCursor;
            bool ok = false;
            string result;
            try { result = Crashes.UploadNewest(out ok); }
            finally { Cursor = Cursors.Default; uploadBtn.Enabled = s.CrashUpload; }
            SetStatus("Crash logs: " + result + ".");
            MessageBox.Show(this, char.ToUpper(result[0]) + result.Substring(1) + (ok ? " to " + server + ". Thank you." : "."), "Upload crash logs",
                MessageBoxButtons.OK, ok ? MessageBoxIcon.Information : MessageBoxIcon.Warning);
        }

        // --- About tab -----------------------------------------------------------------------------

        TabPage BuildAboutTab()
        {
            TabPage page = new TabPage("About");
            Label v = new Label { Text = "GD's Melee " + Game.Version(), Font = new Font("Segoe UI Semibold", 12f), AutoSize = true, Margin = new Padding(0, 0, 0, 8) };
            Label about = UI.Para(
                "A native PC port of Super Smash Bros. Melee, built from the community decompilation.\r\n\r\n" +
                "This download contains no Nintendo game data: no disc image, no game files, no textures, music or models. " +
                "Everything the game shows comes from the disc image you pick. Super Smash Bros. Melee is (c) Nintendo / HAL " +
                "Laboratory; this project is not affiliated with or endorsed by them.\r\n\r\n" +
                "Licences for the port and the libraries it uses are in the LICENSES folder.");
            Button folder = UI.Btn("Open game folder", delegate { Process.Start("explorer.exe", "\"" + Settings.AppDir + "\""); });
            Button saves = UI.Btn("Open saves folder", delegate
            {
                string p = Path.Combine(Settings.UserDir, "saves");
                Directory.CreateDirectory(p);
                Process.Start("explorer.exe", "\"" + p + "\"");
            });
            Button log = UI.Btn("Open game log", delegate { OpenLog(); });
            Button lic = UI.Btn("Licences", delegate
            {
                string p = Path.Combine(Settings.AppDir, "LICENSES");
                if (Directory.Exists(p)) Process.Start("explorer.exe", "\"" + p + "\"");
            });
            Button src = UI.Btn("Source code", delegate { Process.Start("https://github.com/GurekamDhillon/melee/tree/pc-port"); });
            Label paths = new Label { AutoSize = true, ForeColor = Color.DimGray, Margin = new Padding(0, 10, 0, 0),
                Text = "Game folder: " + Settings.AppDir + "\r\nSettings and saves: " + Settings.UserDir };
            page.Controls.Add(UI.Column(v, about, UI.Row(folder, saves, log, lic, src), paths));
            return page;
        }

        // --- documentation screenshots (--shots) ---------------------------------------------------

        public void Shots(string dir)
        {
            Directory.CreateDirectory(dir);
            Show();
            for (int i = 0; i < tabs.TabPages.Count; i++)
            {
                tabs.SelectedIndex = i;
                Application.DoEvents();
                Refresh();
                using (Bitmap bmp = new Bitmap(Width, Height))
                {
                    DrawToBitmap(bmp, new Rectangle(0, 0, Width, Height));
                    bmp.Save(Path.Combine(dir, "launcher-" + tabs.TabPages[i].Text.ToLowerInvariant() + ".png"), ImageFormat.Png);
                }
            }
        }
    }

    static class Program
    {
        [DllImport("user32.dll")]
        static extern bool SetProcessDPIAware();

        [STAThread]
        static int Main(string[] args)
        {
            try { SetProcessDPIAware(); } catch { }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Settings s = Settings.Load();

            string addIso = null, playName = null, shots = null;
            bool openMods = false;
            bool play = false;
            for (int i = 0; i < args.Length; i++)
            {
                string a = args[i];
                if (a == "--play") { play = true; if (i + 1 < args.Length && !args[i + 1].StartsWith("--")) playName = args[++i]; }
                else if (a == "--add-iso" && i + 1 < args.Length) addIso = args[++i];
                else if (a == "--forget-all") { s.Discs.Clear(); s.DefaultId = ""; try { s.Save(); } catch { } }
                else if (a == "--shots" && i + 1 < args.Length) shots = args[++i];
                else if (a == "--list-mods") return ModsCli.Run(new string[0], true);
                else if ((a == "--enable-mod" || a == "--disable-mod") && i + 1 < args.Length)
                {
                    ModStore.SetEnabled(args[++i], a == "--enable-mod");
                    return 0;
                }
                else if (a == "--mods") openMods = true;
                else if (a == "--upload-crashes")
                {
                    // the button's action from a command line (tools, tests): the newest three, only
                    // with the opt-in on; the result goes to userdata\crash-upload.txt (a windowed
                    // program has no console)
                    bool ok = false;
                    string result = s.CrashUpload ? Crashes.UploadNewest(out ok) : "not sent: uploading crash reports is off (Diagnostics tab)";
                    try { File.AppendAllText(Path.Combine(Settings.UserDir, "crash-upload.txt"), DateTime.Now.ToString("s") + " " + result + "\r\n"); } catch { }
                    return ok ? 0 : 1;
                }
                else if (a == "--install-mod" && i + 1 < args.Length)
                {
                    List<string> ids = new List<string>();
                    while (i + 1 < args.Length && !args[i + 1].StartsWith("--")) ids.Add(args[++i]);
                    return ModsCli.Run(ids.ToArray(), false);
                }
            }

            MainForm form = new MainForm(s);
            form.OpenModsOnShow = openMods;
            if (addIso != null)
            {
                Disc d = form.AddPath(addIso, true);
                if (d != null) { s.DefaultId = d.Id; try { s.Save(); } catch { } }
            }
            if (shots != null)
            {
                form.Shots(shots);
                return 0;
            }
            if (play)
            {
                Disc d = s.Default;
                if (playName != null)
                {
                    d = null;
                    foreach (Disc x in s.Discs) if (string.Equals(x.Name, playName, StringComparison.OrdinalIgnoreCase) || x.Id == playName) d = x;
                }
                if (d != null && File.Exists(d.Path) && Game.MissingFiles().Length == 0)
                {
                    try { Game.Start(s, d); return 0; }
                    catch (Exception e) { MessageBox.Show("Could not start melee-pc.exe:\r\n" + e.Message, "GD's Melee"); }
                }
                // otherwise fall through to the window so the user can fix it
            }
            Application.Run(form);
            return 0;
        }
    }
}
