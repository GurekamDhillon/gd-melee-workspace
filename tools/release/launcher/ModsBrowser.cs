// ModsBrowser.cs - the launcher's Mods tab: the installed mods (mods/<id>/mod.json + enabled.txt, the
// layout in docs/mods-packaging.md) and a browser for mods listed by the sources in
// mods/sources.txt (docs/mods-browser.md, schema tools/mods_browser/gdmelee-mods.schema.json).
//
// SAFETY, because every byte here comes from strangers:
//   - downloads are HTTPS only (plain http and file:// are accepted for localhost testing only);
//   - every download is checked against the sha256 and size its index declares BEFORE it is opened;
//   - zips are unpacked by hand, entry by entry: absolute paths, drive letters, "..", ':' (NTFS
//     streams), reserved device names, control characters and symlink entries are refused, every
//     target is re-checked to be inside the mod's folder, and the total size is capped;
//   - a mod is unpacked into a staging folder and only moved into mods/<id> once it is complete;
//   - nothing downloaded is ever executed by the launcher. Script mods run sandboxed in the game.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace GDMelee
{
    class ModInfo
    {
        public string Id = "", Name = "", Version = "", Kind = "misc", Pack = "", Description = "";
        public string Url = "", Sha256 = "", Homepage = "", Authors = "", Source = "";
        public long Size;
        public int ApiVersion;
        public List<string> Requires = new List<string>(), Conflicts = new List<string>();
        public bool Enabled;      // installed: in the enabled set for the next boot
        public string Folder = ""; // installed: its folder

        public string RequiresText { get { return Requires.Count > 0 ? string.Join(", ", Requires.ToArray()) : "-"; } }
        public string ConflictsText { get { return Conflicts.Count > 0 ? string.Join(", ", Conflicts.ToArray()) : "-"; } }
    }

    static class ModJson
    {
        static string Str(Dictionary<string, object> d, string k)
        {
            object v;
            return d.TryGetValue(k, out v) && v != null ? Convert.ToString(v, System.Globalization.CultureInfo.InvariantCulture) : "";
        }

        static List<string> List(Dictionary<string, object> d, string k)
        {
            List<string> r = new List<string>();
            object v;
            System.Collections.IEnumerable items = null;
            if (d.TryGetValue(k, out v)) items = v as System.Collections.IEnumerable;
            if (items == null || v is string) return r;
            foreach (object o in items)
            {
                if (o != null) r.Add(o.ToString());
            }
            return r;
        }

        public static ModInfo FromDict(Dictionary<string, object> d)
        {
            ModInfo m = new ModInfo();
            m.Id = Str(d, "id");
            m.Name = Str(d, "name");
            m.Version = Str(d, "version");
            string kind = Str(d, "kind");
            if (kind.Length > 0) m.Kind = kind;
            m.Pack = Str(d, "pack");
            m.Description = Str(d, "description");
            m.Url = Str(d, "url");
            m.Sha256 = Str(d, "sha256").ToLowerInvariant();
            m.Homepage = Str(d, "homepage");
            m.Authors = Str(d, "authors");
            long size;
            if (long.TryParse(Str(d, "size"), out size)) m.Size = size;
            int api;
            if (int.TryParse(Str(d, "api_version"), out api)) m.ApiVersion = api;
            m.Requires = List(d, "requires");
            m.Conflicts = List(d, "conflicts");
            if (m.Name.Length == 0) m.Name = m.Id;
            return m;
        }

        public static Dictionary<string, object> Parse(string text)
        {
            JavaScriptSerializer js = new JavaScriptSerializer();
            js.MaxJsonLength = 4 * 1024 * 1024;
            return js.DeserializeObject(text) as Dictionary<string, object>;
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Installed mods and the enabled set (mods/enabled.txt: one id per line, '#' comments;
    // ABSENT = every mod enabled - delta's gw_mods.c reads it at boot)
    // ---------------------------------------------------------------------------------------------
    static class ModStore
    {
        public static readonly Regex IdRe = new Regex("^[a-z0-9][a-z0-9._-]{0,63}$");
        public static string Dir { get { return Game.ModsDir; } }
        static string EnabledFile { get { return Path.Combine(Dir, "enabled.txt"); } }

        public static List<ModInfo> Installed()
        {
            List<ModInfo> r = new List<ModInfo>();
            if (!Directory.Exists(Dir)) return r;
            HashSet<string> enabled = EnabledSet();
            foreach (string d in Directory.GetDirectories(Dir))
            {
                string id = Path.GetFileName(d);
                if (id.StartsWith(".") || id.Equals("targettest", StringComparison.OrdinalIgnoreCase)) continue;
                ModInfo m = new ModInfo();
                string mj = Path.Combine(d, "mod.json");
                if (File.Exists(mj))
                {
                    try
                    {
                        Dictionary<string, object> j = ModJson.Parse(File.ReadAllText(mj));
                        if (j != null) m = ModJson.FromDict(j);
                    }
                    catch { m.Description = L.T("(mod.json is not valid JSON)"); }
                }
                m.Id = id; // the folder name is the id
                if (m.Name.Length == 0) m.Name = id;
                m.Folder = d;
                m.Enabled = enabled == null || enabled.Contains(id.ToLowerInvariant());
                r.Add(m);
            }
            r.Sort(delegate(ModInfo a, ModInfo b) { return string.CompareOrdinal(a.Id, b.Id); });
            return r;
        }

        /// <summary>The enabled ids (lower case), or null when enabled.txt is absent (= all).</summary>
        public static HashSet<string> EnabledSet()
        {
            if (!File.Exists(EnabledFile)) return null;
            HashSet<string> s = new HashSet<string>();
            foreach (string raw in File.ReadAllLines(EnabledFile))
            {
                string line = raw.Trim();
                if (line.Length == 0 || line.StartsWith("#")) continue;
                s.Add(line.ToLowerInvariant());
            }
            return s;
        }

        static void WriteEnabled(IEnumerable<string> ids)
        {
            List<string> list = new List<string>(ids);
            list.Sort(StringComparer.Ordinal);
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("# the mods that mount at the next boot, one id per line (written by the GD's Melee launcher)");
            foreach (string id in list) sb.AppendLine(id);
            Directory.CreateDirectory(Dir);
            File.WriteAllText(EnabledFile, sb.ToString(), new UTF8Encoding(false));
        }

        public static void SetEnabled(string id, bool on)
        {
            HashSet<string> s = EnabledSet();
            if (s == null)
            {
                if (on) return; // absent = all enabled already
                s = new HashSet<string>();
                foreach (ModInfo m in Installed()) s.Add(m.Id.ToLowerInvariant());
            }
            if (on) s.Add(id.ToLowerInvariant());
            else s.Remove(id.ToLowerInvariant());
            WriteEnabled(s);
        }

        public static void Remove(string id)
        {
            if (!IdRe.IsMatch(id)) throw new ArgumentException(L.F("bad mod id {0}", id));
            string d = Path.Combine(Dir, id);
            if (Directory.Exists(d)) Directory.Delete(d, true);
            HashSet<string> s = EnabledSet();
            if (s != null && s.Remove(id.ToLowerInvariant())) WriteEnabled(s);
        }

        public static ModInfo Find(List<ModInfo> list, string id)
        {
            foreach (ModInfo m in list) if (string.Equals(m.Id, id, StringComparison.OrdinalIgnoreCase)) return m;
            return null;
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Downloads
    // ---------------------------------------------------------------------------------------------
    static class Net
    {
        static Net()
        {
            // TLS 1.2 (GitHub requires it; .NET 4.x does not always default to it)
            ServicePointManager.SecurityProtocol |= (SecurityProtocolType)3072;
        }

        public static bool IsLocal(Uri u)
        {
            return u.IsFile || u.IsLoopback;
        }

        public static void CheckScheme(Uri u)
        {
            if (u.Scheme == Uri.UriSchemeHttps) return;
            if ((u.Scheme == Uri.UriSchemeHttp || u.IsFile) && IsLocal(u)) return; // testing
            throw new Exception(L.F("refusing {0}:// (only https downloads are allowed): {1}", u.Scheme, u));
        }

        static Stream Open(Uri u, out Uri final, out long length)
        {
            CheckScheme(u);
            if (u.IsFile)
            {
                final = u;
                FileStream fs = File.OpenRead(u.LocalPath);
                length = fs.Length;
                return fs;
            }
            HttpWebRequest req = (HttpWebRequest)WebRequest.Create(u);
            req.UserAgent = "GDMelee-launcher";
            req.Timeout = 30000;
            req.ReadWriteTimeout = 60000;
            req.AllowAutoRedirect = true;
            req.MaximumAutomaticRedirections = 5;
            HttpWebResponse resp = (HttpWebResponse)req.GetResponse();
            final = resp.ResponseUri;
            CheckScheme(final); // a redirect may not downgrade to http
            length = resp.ContentLength;
            return resp.GetResponseStream();
        }

        public static string GetText(Uri u, int maxBytes)
        {
            Uri final;
            long len;
            using (Stream s = Open(u, out final, out len))
            using (MemoryStream ms = new MemoryStream())
            {
                byte[] buf = new byte[65536];
                int n;
                while ((n = s.Read(buf, 0, buf.Length)) > 0)
                {
                    ms.Write(buf, 0, n);
                    if (ms.Length > maxBytes) throw new Exception(L.F("the index is larger than {0} bytes", maxBytes));
                }
                return Encoding.UTF8.GetString(ms.ToArray());
            }
        }

        /// <summary>Download to a file, hashing as it streams; returns the sha256 (lower-case hex).</summary>
        public static string Download(Uri u, string path, long maxBytes, Action<long, long> progress)
        {
            Uri final;
            long len, total = 0;
            using (SHA256 sha = SHA256.Create())
            using (Stream s = Open(u, out final, out len))
            using (FileStream f = File.Create(path))
            {
                if (len > maxBytes) throw new Exception(L.F("the download is larger than declared ({0} bytes)", len));
                byte[] buf = new byte[1 << 16];
                int n;
                while ((n = s.Read(buf, 0, buf.Length)) > 0)
                {
                    total += n;
                    if (total > maxBytes) throw new Exception(L.T("the download is larger than declared"));
                    sha.TransformBlock(buf, 0, n, null, 0);
                    f.Write(buf, 0, n);
                    if (progress != null) progress(total, len > 0 ? len : maxBytes);
                }
                sha.TransformFinalBlock(buf, 0, 0);
                StringBuilder sb = new StringBuilder();
                foreach (byte b in sha.Hash) sb.Append(b.ToString("x2"));
                return sb.ToString();
            }
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Safe unzip
    // ---------------------------------------------------------------------------------------------
    static class SafeZip
    {
        public const long MaxTotal = 3L * 1024 * 1024 * 1024; // 3 GB unpacked
        static readonly Regex Reserved = new Regex(@"^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?$", RegexOptions.IgnoreCase);

        /// <summary>Why an entry name is refused, or null when it is safe. Exposed for the tests.</summary>
        public static string Check(string name)
        {
            if (name.Length == 0) return L.T("empty name");
            foreach (char c in name) if (c < 32 || c == ':' || c == '*' || c == '?' || c == '"' || c == '<' || c == '>' || c == '|')
                return L.T("a character that is not allowed in a file name");
            string n = name.Replace('\\', '/');
            if (n.StartsWith("/")) return L.T("an absolute path");
            foreach (string seg in n.Split('/'))
            {
                if (seg == "..") return L.T("a '..' step out of the folder");
                if (seg == ".") return L.T("a '.' segment");
                if (seg.Length > 0 && (seg.EndsWith(".") || seg.EndsWith(" "))) return L.T("a name ending in '.' or ' '");
                if (Reserved.IsMatch(seg)) return L.F("a reserved device name ({0})", seg);
            }
            return null;
        }

        static bool IsSymlink(ZipArchiveEntry e)
        {
            // ExternalAttributes (.NET 4.7.2+) carries the unix mode in its high 16 bits
            System.Reflection.PropertyInfo p = typeof(ZipArchiveEntry).GetProperty("ExternalAttributes");
            if (p == null) return false;
            int attr = (int)p.GetValue(e, null);
            return ((attr >> 16) & 0xF000) == 0xA000;
        }

        /// <summary>Unpack zip into dest (which must not exist). If every entry sits under one top
        /// folder and there is no mod.json at the root, that folder is stripped.</summary>
        public static void Extract(string zipPath, string dest)
        {
            using (ZipArchive z = ZipFile.OpenRead(zipPath))
            {
                long total = 0;
                string strip = null;
                bool rootMod = false;
                HashSet<string> tops = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                foreach (ZipArchiveEntry e in z.Entries)
                {
                    string why = Check(e.FullName);
                    if (why != null) throw new Exception(L.F("unsafe entry \"{0}\" in the zip: {1}", e.FullName, why));
                    if (IsSymlink(e)) throw new Exception(L.F("the zip contains a symbolic link ({0})", e.FullName));
                    total += e.Length;
                    if (e.Length < 0 || total > MaxTotal) throw new Exception(L.T("the zip unpacks to more than 3 GB"));
                    string n = e.FullName.Replace('\\', '/');
                    if (n.Equals("mod.json", StringComparison.OrdinalIgnoreCase)) rootMod = true;
                    int slash = n.IndexOf('/');
                    tops.Add(slash >= 0 ? n.Substring(0, slash) : n);
                }
                if (!rootMod && tops.Count == 1)
                {
                    foreach (string t in tops) strip = t + "/";
                }
                string root = Path.GetFullPath(dest).TrimEnd('\\') + "\\";
                Directory.CreateDirectory(root);
                foreach (ZipArchiveEntry e in z.Entries)
                {
                    string n = e.FullName.Replace('\\', '/');
                    if (strip != null)
                    {
                        if (!n.StartsWith(strip, StringComparison.OrdinalIgnoreCase)) continue;
                        n = n.Substring(strip.Length);
                    }
                    if (n.Length == 0) continue;
                    string target = Path.GetFullPath(Path.Combine(root, n.Replace('/', '\\')));
                    if (!target.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                        throw new Exception(L.F("zip entry escapes the mod folder: {0}", e.FullName));
                    if (n.EndsWith("/"))
                    {
                        Directory.CreateDirectory(target);
                        continue;
                    }
                    Directory.CreateDirectory(Path.GetDirectoryName(target));
                    using (Stream s = e.Open())
                    using (FileStream f = new FileStream(target, FileMode.CreateNew))
                    {
                        s.CopyTo(f);
                    }
                }
            }
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Sources: mods/sources.txt -> index URLs -> available mods
    // ---------------------------------------------------------------------------------------------
    static class ModSources
    {
        public const string IndexName = "gdmelee-mods.json";
        public static string File_ { get { return Path.Combine(ModStore.Dir, "sources.txt"); } }

        public const string Example =
            "# GD's Melee mod sources - where the Mods tab looks for mods to install.\r\n" +
            "# One source per line; '#' starts a comment. No source is listed by default: GD's Melee does\r\n" +
            "# not vouch for anyone's mods. Add the ones you trust.\r\n" +
            "#\r\n" +
            "#   owner/repo                     a GitHub repo: its gdmelee-mods.json (at the repo root, or\r\n" +
            "#                                  as an asset of its latest release)\r\n" +
            "#   owner/repo@v1.2                the same at a tag or branch\r\n" +
            "#   https://github.com/owner/repo  the same, as a URL\r\n" +
            "#   https://example.org/my-index.json   any index file served over https\r\n" +
            "#\r\n" +
            "# The index format is docs/mods-browser.md in the GD's Melee workspace repository.\r\n";

        public static List<string> Read()
        {
            List<string> r = new List<string>();
            if (!File.Exists(File_)) return r;
            foreach (string raw in File.ReadAllLines(File_))
            {
                string line = raw;
                int hash = line.IndexOf('#');
                if (hash >= 0) line = line.Substring(0, hash);
                line = line.Trim();
                if (line.Length > 0) r.Add(line);
            }
            return r;
        }

        public static void EnsureExample()
        {
            Directory.CreateDirectory(ModStore.Dir);
            if (!File.Exists(File_)) File.WriteAllText(File_, Example, new UTF8Encoding(false));
        }

        static readonly Regex Gh = new Regex(@"^(?:https?://github\.com/)?([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:/tree/([^@\s]+))?/?(?:@(\S+))?$");

        /// <summary>The index URLs to try for a sources.txt entry, in order.</summary>
        public static List<Uri> Candidates(string entry)
        {
            List<Uri> r = new List<Uri>();
            Match m = Gh.Match(entry);
            bool isUrl = entry.Contains("://");
            if (m.Success && (!isUrl || entry.StartsWith("https://github.com/", StringComparison.OrdinalIgnoreCase) ||
                              entry.StartsWith("http://github.com/", StringComparison.OrdinalIgnoreCase)))
            {
                string owner = m.Groups[1].Value, repo = m.Groups[2].Value;
                string reff = m.Groups[4].Success ? m.Groups[4].Value : (m.Groups[3].Success ? m.Groups[3].Value : null);
                r.Add(new Uri("https://raw.githubusercontent.com/" + owner + "/" + repo + "/" + (reff ?? "HEAD") + "/" + IndexName));
                r.Add(new Uri("https://github.com/" + owner + "/" + repo + "/releases/" +
                              (reff != null ? "download/" + reff : "latest/download") + "/" + IndexName));
                return r;
            }
            Uri u;
            if (Uri.TryCreate(entry, UriKind.Absolute, out u)) r.Add(u);
            return r;
        }

        /// <summary>Fetch and parse one source. Download URLs are resolved against the index URL.</summary>
        public static List<ModInfo> Fetch(string entry, out string error)
        {
            List<ModInfo> r = new List<ModInfo>();
            error = null;
            List<Uri> cands = Candidates(entry);
            if (cands.Count == 0)
            {
                error = L.T("not a GitHub repo or a URL");
                return r;
            }
            foreach (Uri u in cands)
            {
                string text;
                try { text = Net.GetText(u, 1 << 20); }
                catch (Exception e) { error = e.Message; continue; }
                Dictionary<string, object> j;
                try { j = ModJson.Parse(text); }
                catch (Exception e) { error = L.F("the index is not valid JSON ({0})", e.Message); return r; }
                object mods;
                if (j == null || !j.TryGetValue("mods", out mods) || !(mods is object[]))
                {
                    error = L.T("the index has no \"mods\" list");
                    return r;
                }
                foreach (object o in (object[])mods)
                {
                    Dictionary<string, object> d = o as Dictionary<string, object>;
                    if (d == null) continue;
                    ModInfo m = ModJson.FromDict(d);
                    m.Source = entry;
                    Uri dl;
                    if (!ModStore.IdRe.IsMatch(m.Id) || m.Id == "targettest")
                    {
                        error = L.F("skipped a mod with a bad id \"{0}\" (lower-case letters, digits, . _ -)", m.Id);
                        continue;
                    }
                    if (m.Sha256.Length != 64 || !Regex.IsMatch(m.Sha256, "^[0-9a-f]{64}$") || m.Size <= 0 ||
                        !Uri.TryCreate(u, m.Url, out dl))
                    {
                        error = L.F("skipped {0}: it needs url, sha256 and size", m.Id);
                        continue;
                    }
                    m.Url = dl.ToString();
                    r.Add(m);
                }
                error = r.Count == 0 && error == null ? L.T("the index lists no mods") : error;
                return r;
            }
            return r;
        }
    }

    // ---------------------------------------------------------------------------------------------
    // Installing
    // ---------------------------------------------------------------------------------------------
    static class ModInstaller
    {
        public const int ScriptApi = 1; // the scripting API this build's game provides

        /// <summary>Download, verify and install one mod into mods/&lt;id&gt; (replacing an older one).
        /// Throws with a message a player can read.</summary>
        public static void Install(ModInfo m, Action<long, long> progress)
        {
            if (!ModStore.IdRe.IsMatch(m.Id)) throw new Exception(L.F("bad mod id {0}", m.Id));
            if (m.Kind == "script" && m.ApiVersion > ScriptApi)
                throw new Exception(L.F("{0} needs scripting API {1}; this game has {2}. Update GD's Melee first.", m.Name, m.ApiVersion, ScriptApi));
            Directory.CreateDirectory(ModStore.Dir);
            string tmp = Path.Combine(ModStore.Dir, ".download-" + m.Id + ".zip");
            string stage = Path.Combine(ModStore.Dir, ".staging-" + m.Id);
            string final = Path.Combine(ModStore.Dir, m.Id);
            string old = Path.Combine(ModStore.Dir, ".old-" + m.Id);
            try
            {
                if (Directory.Exists(stage)) Directory.Delete(stage, true);
                string sha = Net.Download(new Uri(m.Url), tmp, m.Size, progress);
                long got = new FileInfo(tmp).Length;
                if (got != m.Size) throw new Exception(L.F("the download is {0} bytes; the index says {1}", got, m.Size));
                if (sha != m.Sha256) throw new Exception(L.T("the download's sha256 does not match the index - not installed"));
                SafeZip.Extract(tmp, stage);
                string mj = Path.Combine(stage, "mod.json");
                if (!File.Exists(mj)) throw new Exception(L.T("the zip has no mod.json at its top level"));
                Dictionary<string, object> j = ModJson.Parse(File.ReadAllText(mj));
                ModInfo inside = j != null ? ModJson.FromDict(j) : null;
                if (inside != null && inside.Id.Length > 0 && !inside.Id.Equals(m.Id, StringComparison.OrdinalIgnoreCase))
                    throw new Exception(L.F("the zip's mod.json says id \"{0}\", the index says \"{1}\"", inside.Id, m.Id));
                if (Directory.Exists(old)) Directory.Delete(old, true);
                if (Directory.Exists(final)) Directory.Move(final, old);
                Directory.Move(stage, final);
                if (Directory.Exists(old)) Directory.Delete(old, true);
                // enabled.txt: absent = everything is enabled; present = append the new id
                if (ModStore.EnabledSet() != null) ModStore.SetEnabled(m.Id, true);
            }
            finally
            {
                try { if (File.Exists(tmp)) File.Delete(tmp); } catch { }
                try { if (Directory.Exists(stage)) Directory.Delete(stage, true); } catch { }
            }
        }
    }

    // ---------------------------------------------------------------------------------------------
    // The Mods tab
    // ---------------------------------------------------------------------------------------------
    class ModsTab
    {
        readonly MainForm form;
        readonly Settings s;
        ListView installed, available;
        Label detail, sourceState;
        Button removeBtn, installBtn, refreshBtn;
        ProgressBar bar;
        List<ModInfo> inst = new List<ModInfo>(), avail = new List<ModInfo>();
        bool busy, filling;

        public ModsTab(TabPage page, MainForm form, Settings s)
        {
            this.form = form;
            this.s = s;
            page.Padding = new Padding(10);

            installed = MakeList(true);
            installed.Columns.Add(L.T("Installed mod"), 190);
            installed.Columns.Add(L.T("Version"), 70);
            installed.Columns.Add(L.T("Kind"), 60);
            installed.Columns.Add(L.T("Needs"), 160);
            installed.ItemChecked += delegate(object o, ItemCheckedEventArgs e) { OnChecked(e.Item); };
            installed.SelectedIndexChanged += delegate { ShowDetail(Sel(installed)); UpdateButtons(); };

            available = MakeList(false);
            available.Columns.Add(L.T("Available mod"), 190);
            available.Columns.Add(L.T("Version"), 70);
            available.Columns.Add(L.T("Kind"), 60);
            available.Columns.Add(L.T("Status"), 110);
            available.Columns.Add(L.T("Source"), 150);
            available.SelectedIndexChanged += delegate { ShowDetail(Sel(available)); UpdateButtons(); };
            available.DoubleClick += delegate { InstallSelected(); };

            removeBtn = UI.Btn(L.T("Remove"), delegate { RemoveSelected(); });
            Button folder = UI.Btn(L.T("Open mods folder"), delegate { Directory.CreateDirectory(ModStore.Dir); Process.Start("explorer.exe", "\"" + ModStore.Dir + "\""); });
            refreshBtn = UI.Btn(L.T("Refresh sources"), delegate { Refresh(); });
            installBtn = UI.Btn(L.T("Install"), delegate { InstallSelected(); });
            Button sources = UI.Btn(L.T("Edit sources..."), delegate
            {
                ModSources.EnsureExample();
                Process.Start("notepad.exe", "\"" + ModSources.File_ + "\"");
            });
            sourceState = new Label { AutoSize = true, ForeColor = Color.DimGray, Margin = new Padding(8, 7, 0, 0) };
            bar = new ProgressBar { Width = 140, Height = 16, Visible = false, Margin = new Padding(8, 6, 0, 0) };

            detail = new Label { Dock = DockStyle.Fill, ForeColor = Color.DimGray, AutoEllipsis = true };

            // the scripts corner: the console socket for tools, and the scripts folder
            CheckBox socket = new CheckBox { Text = L.T("Console socket for tools (127.0.0.1:51700)"), Checked = s.ConsoleSocket, AutoSize = true, Margin = new Padding(0, 4, 12, 0) };
            socket.CheckedChanged += delegate { s.ConsoleSocket = socket.Checked; try { s.Save(); } catch { } };
            Button scripts = UI.Btn(L.T("Open scripts folder"), delegate
            {
                string p = Path.Combine(Settings.AppDir, "scripts");
                Directory.CreateDirectory(p);
                Process.Start("explorer.exe", "\"" + p + "\"");
            });

            TableLayoutPanel t = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 6 };
            t.RowStyles.Add(new RowStyle(SizeType.Percent, 45));
            t.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            t.RowStyles.Add(new RowStyle(SizeType.Percent, 55));
            t.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            t.RowStyles.Add(new RowStyle(SizeType.Absolute, 40));
            t.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            t.Controls.Add(installed, 0, 0);
            t.Controls.Add(UI.Row(removeBtn, folder), 0, 1);
            t.Controls.Add(available, 0, 2);
            t.Controls.Add(UI.Row(refreshBtn, installBtn, sources, bar, sourceState), 0, 3);
            t.Controls.Add(detail, 0, 4);
            t.Controls.Add(UI.Row(socket, scripts), 0, 5);
            page.Controls.Add(t);

            ReloadInstalled();
            sourceState.Text = ModSources.Read().Count == 0
                ? L.T("No sources yet: \"Edit sources...\" to add the ones you trust.")
                : L.F("{0} source(s). \"Refresh sources\" to see their mods.", ModSources.Read().Count);
            UpdateButtons();
        }

        static ListView MakeList(bool checks)
        {
            ListView l = new ListView();
            l.View = View.Details;
            l.FullRowSelect = true;
            l.HideSelection = false;
            l.MultiSelect = false;
            l.CheckBoxes = checks;
            l.Dock = DockStyle.Fill;
            return l;
        }

        static ModInfo Sel(ListView l)
        {
            return l.SelectedItems.Count > 0 ? l.SelectedItems[0].Tag as ModInfo : null;
        }

        void UpdateButtons()
        {
            removeBtn.Enabled = !busy && Sel(installed) != null;
            ModInfo a = Sel(available);
            installBtn.Enabled = !busy && a != null;
            refreshBtn.Enabled = !busy;
            if (a != null)
            {
                ModInfo have = ModStore.Find(inst, a.Id);
                installBtn.Text = have == null ? L.T("Install") : (have.Version == a.Version ? L.T("Reinstall") : L.T("Update"));
            }
        }

        void ShowDetail(ModInfo m)
        {
            if (m == null) { detail.Text = ""; return; }
            detail.Text = m.Name + (m.Version.Length > 0 ? " " + m.Version : "") + (m.Pack.Length > 0 ? L.F("  (pack {0})", m.Pack) : "") +
                          (m.Authors.Length > 0 ? L.F("  by {0}", m.Authors) : "") + "\r\n" +
                          (m.Description.Length > 0 ? m.Description + "\r\n" : "") +
                          L.F("Needs: {0}    Conflicts with: {1}", m.RequiresText, m.ConflictsText) +
                          (m.Size > 0 ? string.Format("    {0:0.0} MB", m.Size / 1048576.0) : "");
        }

        public void ReloadInstalled()
        {
            filling = true;
            inst = ModStore.Installed();
            installed.BeginUpdate();
            installed.Items.Clear();
            foreach (ModInfo m in inst)
            {
                ListViewItem it = new ListViewItem(m.Name == m.Id ? m.Id : m.Name + "  [" + m.Id + "]");
                it.SubItems.Add(m.Version);
                it.SubItems.Add(m.Kind);
                List<string> missing = new List<string>();
                foreach (string r in m.Requires) if (ModStore.Find(inst, r) == null) missing.Add(r);
                it.SubItems.Add(missing.Count > 0 ? L.F("MISSING {0}", string.Join(", ", missing.ToArray())) : m.RequiresText);
                if (missing.Count > 0) it.ForeColor = Color.Firebrick;
                it.Checked = m.Enabled;
                it.Tag = m;
                installed.Items.Add(it);
            }
            installed.EndUpdate();
            filling = false;
            FillAvailable();
        }

        void FillAvailable()
        {
            available.BeginUpdate();
            available.Items.Clear();
            foreach (ModInfo m in avail)
            {
                ModInfo have = ModStore.Find(inst, m.Id);
                ListViewItem it = new ListViewItem(m.Name);
                it.SubItems.Add(m.Version);
                it.SubItems.Add(m.Kind);
                it.SubItems.Add(have == null ? "" : (have.Version == m.Version ? L.T("installed") : L.F("update {0} > {1}", have.Version, m.Version)));
                it.SubItems.Add(m.Source);
                it.Tag = m;
                available.Items.Add(it);
            }
            available.EndUpdate();
            UpdateButtons();
        }

        void OnChecked(ListViewItem item)
        {
            if (filling) return;
            ModInfo m = item.Tag as ModInfo;
            if (m == null || m.Enabled == item.Checked) return; // (the ListView re-sends checks when shown)
            try
            {
                ModStore.SetEnabled(m.Id, item.Checked);
                m.Enabled = item.Checked;
                form.Status(item.Checked ? L.F("Enabled {0} for the next start of the game.", m.Id) : L.F("Disabled {0} for the next start of the game.", m.Id));
            }
            catch (Exception e) { MessageBox.Show(form, e.Message, L.T("Mods")); }
        }

        void RemoveSelected()
        {
            ModInfo m = Sel(installed);
            if (m == null) return;
            List<string> dependents = new List<string>();
            foreach (ModInfo o in inst) if (o.Requires.Contains(m.Id)) dependents.Add(o.Id);
            string q = L.F("Remove {0}? Its folder is deleted.", m.Id) +
                       (dependents.Count > 0 ? L.F("\r\n\r\nThese installed mods need it: {0}", string.Join(", ", dependents.ToArray())) : "");
            if (MessageBox.Show(form, q, L.T("Remove mod"), MessageBoxButtons.OKCancel, MessageBoxIcon.Question) != DialogResult.OK) return;
            try { ModStore.Remove(m.Id); form.Status(L.F("Removed {0}.", m.Id)); }
            catch (Exception e) { MessageBox.Show(form, L.F("Could not remove {0}:\r\n{1}", m.Id, e.Message), L.T("Mods")); }
            ReloadInstalled();
        }

        public async void Refresh()
        {
            List<string> srcs = ModSources.Read();
            if (srcs.Count == 0)
            {
                sourceState.Text = L.T("No sources in mods\\sources.txt - \"Edit sources...\" to add some.");
                return;
            }
            busy = true;
            UpdateButtons();
            sourceState.Text = L.F("Reading {0} source(s)...", srcs.Count);
            List<string> errors = new List<string>();
            List<ModInfo> found = await Task.Run(() =>
            {
                List<ModInfo> all = new List<ModInfo>();
                foreach (string src in srcs)
                {
                    string err;
                    List<ModInfo> got = ModSources.Fetch(src, out err);
                    if (err != null) lock (errors) errors.Add(src + ": " + err);
                    foreach (ModInfo m in got) if (ModStore.Find(all, m.Id) == null) all.Add(m); // the first source wins an id
                }
                return all;
            });
            avail = found;
            busy = false;
            sourceState.Text = L.F("{0} mod(s) from {1} source(s)", found.Count, srcs.Count) + (errors.Count > 0 ? L.F(" - {0} problem(s)", errors.Count) : "");
            FillAvailable();
            if (errors.Count > 0) MessageBox.Show(form, string.Join("\r\n", errors.ToArray()), L.T("Mod sources"), MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }

        async void InstallSelected()
        {
            ModInfo m = Sel(available);
            if (m == null || busy) return;
            // requirements first (from the same lists), and a word about conflicts
            List<ModInfo> plan = new List<ModInfo>();
            List<string> unknown = new List<string>();
            CollectPlan(m, plan, unknown, 0);
            List<string> clash = new List<string>();
            foreach (ModInfo p in plan)
                foreach (ModInfo o in inst)
                    if (o.Enabled && (p.Conflicts.Contains(o.Id) || o.Conflicts.Contains(p.Id))) clash.Add(L.F("{0} (conflicts with {1})", o.Id, p.Id));
            StringBuilder q = new StringBuilder();
            q.AppendLine(L.F("Install {0} {1}?", m.Name, m.Version));
            q.AppendLine(L.F("From: {0}", m.Source));
            if (plan.Count > 1)
            {
                q.AppendLine();
                q.AppendLine(L.T("It needs, and these are installed too:"));
                foreach (ModInfo p in plan) if (p != m) q.AppendLine("  " + p.Id + " " + p.Version);
            }
            if (unknown.Count > 0)
            {
                q.AppendLine();
                q.AppendLine(L.F("It needs mods none of your sources offer: {0}. It will not load without them.", string.Join(", ", unknown.ToArray())));
            }
            if (clash.Count > 0)
            {
                q.AppendLine();
                q.AppendLine(L.F("These enabled mods conflict and will be disabled: {0}", string.Join(", ", clash.ToArray())));
            }
            q.AppendLine();
            q.AppendLine(L.T("Mods are other people's work: install the ones you trust. Downloads are checked against the source's sha256; nothing downloaded is run by the launcher."));
            if (MessageBox.Show(form, q.ToString(), L.T("Install mod"), MessageBoxButtons.OKCancel, MessageBoxIcon.Question) != DialogResult.OK) return;

            busy = true;
            bar.Visible = true;
            UpdateButtons();
            string error = null;
            foreach (ModInfo p in plan)
            {
                ModInfo cur = p;
                sourceState.Text = L.F("Downloading {0}...", cur.Id);
                try
                {
                    await Task.Run(() => ModInstaller.Install(cur, (done, total) =>
                    {
                        int pct = total > 0 ? (int)Math.Min(100, done * 100 / total) : 0;
                        form.BeginInvoke(new MethodInvoker(delegate { bar.Value = pct; }));
                    }));
                }
                catch (Exception e) { error = cur.Id + ": " + e.Message; break; }
            }
            if (error == null)
                foreach (ModInfo o in inst)
                    foreach (ModInfo p in plan)
                        if (o.Enabled && (p.Conflicts.Contains(o.Id) || o.Conflicts.Contains(p.Id))) ModStore.SetEnabled(o.Id, false);
            busy = false;
            bar.Visible = false;
            ReloadInstalled();
            if (error != null)
            {
                sourceState.Text = L.T("Install failed.");
                MessageBox.Show(form, L.F("Not installed - {0}", error), L.T("Install mod"), MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            else
            {
                sourceState.Text = L.F("Installed {0}. It loads at the next start of the game.", m.Id);
                form.Status(sourceState.Text);
            }
        }

        void CollectPlan(ModInfo m, List<ModInfo> plan, List<string> unknown, int depth)
        {
            if (depth > 8 || plan.Contains(m)) return;
            foreach (string r in m.Requires)
            {
                ModInfo have = ModStore.Find(inst, r);
                if (have != null) continue;
                ModInfo a = ModStore.Find(avail, r);
                if (a == null) { if (!unknown.Contains(r)) unknown.Add(r); continue; }
                CollectPlan(a, plan, unknown, depth + 1);
            }
            if (!plan.Contains(m)) plan.Add(m);
        }
    }
}

namespace GDMelee
{
    // Scriptable installs, for power users and the tests:
    //   "GD Melee.exe" --install-mod <id> [<id>...]   fetch mods\sources.txt, install with requirements
    //   "GD Melee.exe" --list-mods                     installed + available, into the log
    // The result goes to userdata\mods.log (the launcher has no console); exit code 0 = all installed.
    static class ModsCli
    {
        public static int Run(string[] ids, bool listOnly)
        {
            StringBuilder log = new StringBuilder();
            int rc = 0;
            List<ModInfo> avail = new List<ModInfo>();
            foreach (string src in ModSources.Read())
            {
                string err;
                foreach (ModInfo m in ModSources.Fetch(src, out err)) if (ModStore.Find(avail, m.Id) == null) avail.Add(m);
                if (err != null) log.AppendLine("source " + src + ": " + err);
            }
            if (listOnly)
            {
                foreach (ModInfo m in ModStore.Installed())
                    log.AppendLine("installed " + m.Id + " " + m.Version + " " + m.Kind + (m.Enabled ? " enabled" : " disabled"));
                foreach (ModInfo m in avail) log.AppendLine("available " + m.Id + " " + m.Version + " " + m.Kind + " " + m.Url);
            }
            foreach (string id in ids)
            {
                List<ModInfo> plan = new List<ModInfo>();
                if (!Plan(id, avail, plan, log, 0)) { rc = 1; continue; }
                foreach (ModInfo m in plan)
                {
                    try
                    {
                        ModInstaller.Install(m, null);
                        log.AppendLine("installed " + m.Id + " " + m.Version);
                    }
                    catch (Exception e)
                    {
                        log.AppendLine("FAILED " + m.Id + ": " + e.Message);
                        rc = 1;
                        break;
                    }
                }
            }
            try
            {
                Directory.CreateDirectory(Settings.UserDir);
                File.WriteAllText(Path.Combine(Settings.UserDir, "mods.log"), log.ToString());
            }
            catch { }
            return rc;
        }

        static bool Plan(string id, List<ModInfo> avail, List<ModInfo> plan, StringBuilder log, int depth)
        {
            ModInfo m = ModStore.Find(avail, id);
            if (m == null) { log.AppendLine("FAILED " + id + ": no source offers it"); return false; }
            if (depth > 8) return false;
            foreach (string r in m.Requires)
                if (ModStore.Find(ModStore.Installed(), r) == null && ModStore.Find(plan, r) == null && !Plan(r, avail, plan, log, depth + 1))
                    return false;
            if (!plan.Contains(m)) plan.Add(m);
            return true;
        }
    }
}
