#include "diagnostics.h"
#include "graphics.h"
#include <QCoreApplication>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMap>
#include <QStandardPaths>
#include <QProcess>
#include <QRegularExpression>
#include <QSet>
#include <QSysInfo>
#include <QtEndian>
#include <algorithm>
#include <cstring>
#ifdef Q_OS_UNIX
#include <csignal>
#include <spawn.h>
#include <sys/statvfs.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <cerrno>
#include <fcntl.h>
#include <unistd.h>
extern char **environ;
#endif

namespace launcher {
// ---- ELF ---------------------------------------------------------------------------------
QString ElfInfo::machineName() const {
    switch (machine) {
    case 3: return "i386 (32-bit x86)"; case 62: return "x86-64"; case 40: return "ARM"; case 183: return "AArch64";
    case 243: return "RISC-V"; case 0: return "none"; default: return "machine " + QString::number(machine);
    }
}
namespace {
struct Cursor {
    QIODevice &d; bool le;
    bool read(qint64 off, QByteArray &out, int n) const { if (off < 0 || !d.seek(off)) return false; out = d.read(n); return out.size() == n; }
    quint64 num(const QByteArray &b, int off, int n) const {
        const uchar *p = reinterpret_cast<const uchar *>(b.constData()) + off;
        switch (n) {
        case 2: return le ? qFromLittleEndian<quint16>(p) : qFromBigEndian<quint16>(p);
        case 4: return le ? qFromLittleEndian<quint32>(p) : qFromBigEndian<quint32>(p);
        default: return le ? qFromLittleEndian<quint64>(p) : qFromBigEndian<quint64>(p);
        }
    }
};
struct Load { quint64 vaddr, offset, filesz; };
bool cString(QIODevice &d, qint64 off, QString &out) {
    if (off < 0 || !d.seek(off)) return false;
    auto chunk = d.read(4096); auto end = chunk.indexOf('\0');
    if (end < 0) return false;
    out = QString::fromUtf8(chunk.left(end)); return true;
}
}
ElfInfo readElf(QIODevice &d, bool headerOnly) {
    ElfInfo e;
    if (!d.seek(0)) { e.error = "cannot read file"; return e; }
    auto id = d.read(16);
    if (id.size() < 4 || memcmp(id.constData(), "\x7f" "ELF", 4) != 0) { e.error = id.size() < 4 ? "file is too short to be an ELF binary" : "not an ELF file (bad magic)"; return e; }
    e.isElf = true;
    if (id.size() < 16) { e.error = "truncated ELF identification"; return e; }
    const int cls = uchar(id[4]), data = uchar(id[5]);
    if ((cls != 1 && cls != 2) || (data != 1 && data != 2)) { e.error = "unknown ELF class or byte order"; return e; }
    e.bits = cls == 1 ? 32 : 64; e.littleEndian = data == 1;
    Cursor c{d, e.littleEndian}; const bool is64 = e.bits == 64;
    QByteArray h;
    if (!c.read(0, h, is64 ? 64 : 52)) { e.error = "truncated ELF header"; return e; }
    e.type = c.num(h, 16, 2); e.machine = c.num(h, 18, 2);
    if (headerOnly) { e.valid = true; return e; }
    const quint64 phoff = is64 ? c.num(h, 32, 8) : c.num(h, 28, 4);
    const int phentsize = c.num(h, is64 ? 54 : 42, 2), phnum = c.num(h, is64 ? 56 : 44, 2);
    if (phnum == 0) { e.valid = true; return e; }
    if (phentsize < (is64 ? 56 : 32) || phnum > 512) { e.error = "implausible program header table"; return e; }
    QVector<Load> loads; quint64 dynOff = 0, dynSize = 0; bool haveDyn = false;
    for (int i = 0; i < phnum; ++i) {
        QByteArray p;
        if (!c.read(qint64(phoff) + qint64(i) * phentsize, p, is64 ? 56 : 32)) { e.error = "truncated: program headers run past the end of the file"; return e; }
        const quint32 type = c.num(p, 0, 4);
        const quint64 off = is64 ? c.num(p, 8, 8) : c.num(p, 4, 4), vaddr = is64 ? c.num(p, 16, 8) : c.num(p, 8, 4), filesz = is64 ? c.num(p, 32, 8) : c.num(p, 16, 4);
        if (type == 3) {   // PT_INTERP
            if (!cString(d, qint64(off), e.interpreter)) { e.error = "truncated: PT_INTERP string is unreadable"; return e; }
        } else if (type == 1) loads.append({vaddr, off, filesz});
        else if (type == 2) { haveDyn = true; dynOff = off; dynSize = filesz; }
    }
    if (!haveDyn) { e.valid = true; return e; }   // static executable
    e.dynamic = true;
    quint64 strtab = 0; QVector<quint64> needed, rpath, runpath; quint64 soname = 0; bool haveSoname = false;
    const int entry = is64 ? 16 : 8;
    for (quint64 i = 0; i < std::min<quint64>(dynSize / entry, 4096); ++i) {
        QByteArray p;
        if (!c.read(qint64(dynOff + i * entry), p, entry)) { e.error = "truncated: dynamic section runs past the end of the file"; return e; }
        const quint64 tag = c.num(p, 0, is64 ? 8 : 4), val = c.num(p, is64 ? 8 : 4, is64 ? 8 : 4);
        if (tag == 0) break;
        if (tag == 1) needed.append(val); else if (tag == 5) strtab = val; else if (tag == 14) { soname = val; haveSoname = true; }
        else if (tag == 15) rpath.append(val); else if (tag == 29) runpath.append(val);
    }
    if (needed.isEmpty() && rpath.isEmpty() && runpath.isEmpty() && !haveSoname) { e.valid = true; return e; }
    qint64 base = -1;
    for (const auto &l : loads) if (strtab >= l.vaddr && strtab < l.vaddr + l.filesz) { base = qint64(strtab - l.vaddr + l.offset); break; }
    if (base < 0) { e.error = "dynamic string table is not mapped by any segment"; return e; }
    auto str = [&](quint64 off, QString &out) { return cString(d, base + qint64(off), out); };
    for (auto v : needed) { QString s; if (!str(v, s)) { e.error = "truncated: dynamic string table is unreadable"; return e; } e.needed << s; }
    for (auto v : rpath) { QString s; if (str(v, s)) e.rpath << s.split(':', Qt::SkipEmptyParts); }
    for (auto v : runpath) { QString s; if (str(v, s)) e.runpath << s.split(':', Qt::SkipEmptyParts); }
    if (haveSoname) str(soname, e.soname);
    e.valid = true; return e;
}
ElfInfo readElf(const QString &path, bool headerOnly) {
    QFile f(path); ElfInfo e;
    if (!f.open(QIODevice::ReadOnly)) { e.error = f.errorString(); return e; }
    return readElf(f, headerOnly);
}
// Returns the first 32-bit (or whatever class `like` has) library called `name`, with notes on rejects.
static LibraryHit findLibrary(const QString &name, const QStringList &dirs, const ElfInfo &like) {
    LibraryHit hit; hit.name = name; QStringList rejected;
    QStringList candidates;
    if (name.contains('/')) candidates << name; else for (const auto &d : dirs) candidates << d + "/" + name;
    for (const auto &path : candidates) {
        if (!QFileInfo::exists(path)) continue;
        auto e = readElf(path, true);
        if (!e.valid) { rejected << path + " (not a readable ELF file)"; continue; }
        if (e.bits != like.bits || e.machine != like.machine) { rejected << path + " (" + QString::number(e.bits) + "-bit " + e.machineName() + ")"; continue; }
        hit.found = true; hit.path = QDir::cleanPath(path); break;
    }
    if (!hit.found && !rejected.isEmpty()) hit.note = "present only as: " + rejected.join("; ");
    return hit;
}
QVector<LibraryHit> resolveNeeded(const ElfInfo &exe, const QString &origin, const QStringList &ld, const QStringList &defaults) {
    auto expand = [&](QStringList list) { for (auto &s : list) { s.replace("$ORIGIN", origin); s.replace("${ORIGIN}", origin); } return list; };
    QStringList dirs;
    if (exe.runpath.isEmpty()) dirs << expand(exe.rpath);
    dirs << ld;
    dirs << expand(exe.runpath);
    dirs << defaults;
    QVector<LibraryHit> out;
    for (const auto &n : exe.needed) out << findLibrary(n, dirs, exe);
    return out;
}
static void readLdConf(const QString &root, const QString &file, QStringList &out, int depth) {
    if (depth > 4) return;
    QFile f(root + file); if (!f.open(QIODevice::ReadOnly)) return;
    for (auto line : QString::fromUtf8(f.read(65536)).split('\n')) {
        line = line.section('#', 0, 0).trimmed();
        if (line.isEmpty()) continue;
        if (line.startsWith("include ")) {
            auto pattern = line.mid(8).trimmed();
            if (!pattern.startsWith('/')) pattern = "/etc/" + pattern;
            QFileInfo info(root + pattern);
            for (const auto &g : QDir(info.absolutePath()).entryList({info.fileName()}, QDir::Files, QDir::Name)) readLdConf(root, info.dir().path().mid(root.size()) + "/" + g, out, depth + 1);
        } else if (line.startsWith('/')) out << root + line;
    }
}
QStringList systemLibraryDirs(const QString &root) {
    QStringList dirs{"/lib32", "/usr/lib32", "/lib/i386-linux-gnu", "/usr/lib/i386-linux-gnu", "/lib/i686-linux-gnu", "/usr/lib/i686-linux-gnu", "/lib", "/usr/lib"};
    for (auto &d : dirs) d = root + d;
    readLdConf(root, "/etc/ld.so.conf", dirs, 0);
    QStringList unique; for (const auto &d : dirs) if (!unique.contains(d)) unique << d;
    return unique;
}
// ---- small facts ---------------------------------------------------------------------------
MountInfo mountFor(const QString &path, const QString &mountinfo) {
    MountInfo best;
    for (const auto &line : mountinfo.split('\n', Qt::SkipEmptyParts)) {
        const auto parts = line.split(' ');
        const int dash = parts.indexOf("-");
        if (parts.size() < 7 || dash < 6 || dash + 1 >= parts.size()) continue;
        QString mp = parts[4];
        static const QRegularExpression octal("\\\\([0-7]{3})");
        for (auto m = octal.match(mp); m.hasMatch(); m = octal.match(mp)) mp.replace(m.capturedStart(), 4, QChar(m.captured(1).toInt(nullptr, 8)));
        const bool inside = mp == "/" || path == mp || path.startsWith(mp + "/");
        if (inside && (!best.found || mp.size() >= best.mountPoint.size())) {
            best.found = true; best.mountPoint = mp; best.fsType = parts[dash + 1]; best.options = parts[5]; best.noexec = parts[5].split(',').contains("noexec");
        }
    }
    return best;
}
QString signalName(int s) {
    static const QMap<int, QString> names = {{1, "SIGHUP"}, {2, "SIGINT"}, {3, "SIGQUIT"}, {4, "SIGILL"}, {5, "SIGTRAP"}, {6, "SIGABRT"}, {7, "SIGBUS"}, {8, "SIGFPE"}, {9, "SIGKILL"}, {10, "SIGUSR1"}, {11, "SIGSEGV"}, {12, "SIGUSR2"}, {13, "SIGPIPE"}, {14, "SIGALRM"}, {15, "SIGTERM"}, {24, "SIGXCPU"}, {31, "SIGSYS"}};
    return names.value(s, "signal " + QString::number(s));
}
QString permissionString(QFileDevice::Permissions p) {
    QString s; const struct { QFileDevice::Permission bit; char c; } table[] = {{QFileDevice::ReadOwner, 'r'}, {QFileDevice::WriteOwner, 'w'}, {QFileDevice::ExeOwner, 'x'}, {QFileDevice::ReadGroup, 'r'}, {QFileDevice::WriteGroup, 'w'}, {QFileDevice::ExeGroup, 'x'}, {QFileDevice::ReadOther, 'r'}, {QFileDevice::WriteOther, 'w'}, {QFileDevice::ExeOther, 'x'}};
    for (const auto &t : table) s += p.testFlag(t.bit) ? t.c : '-';
    return s;
}
// ---- verdict ---------------------------------------------------------------------------------
QString Verdict::line() const { return detail.isEmpty() ? code : code + " " + detail; }
QString missingLibraryInOutput(const QString &text) {
    static const QRegularExpression re("error while loading shared libraries: ([^:\\s]+): cannot open shared object file");
    auto m = re.match(text); return m.hasMatch() ? m.captured(1) : QString();
}
QString libraryVersionInOutput(const QString &text) {
    static const QRegularExpression re("([^\\s:]+): version `([^']+)' not found");
    auto m = re.match(text); return m.hasMatch() ? m.captured(2) + " (needed by " + m.captured(1) + ")" : QString();
}
bool graphicsFailureInOutput(const QString &text) {
    for (const char *m : {"No supported adapters", "Failed to create adapter", "Failed to initialize SDL renderer", "Failed to create renderer", "default EGL display", "VK_ERROR_INCOMPATIBLE_DRIVER", "VK_ERROR_INITIALIZATION_FAILED", "vkCreateInstance", "Could not initialize Vulkan", "No Vulkan"})
        if (text.contains(m)) return true;
    return false;
}
QString packageHint(const QString &osr, const QString &library, const QSet<quint32> &gpus) {
    QString id, like;
    for (const auto &line : osr.split('\n')) {
        auto v = line.section('=', 1).trimmed(); v.remove('"'); v.remove('\'');
        if (line.startsWith("ID=")) id = v; else if (line.startsWith("ID_LIKE=")) like = v;
    }
    const auto family = " " + id + " " + like + " ";
    auto has = [&](const char *name) { return family.contains(QString(" ") + name + " "); };
    const bool arch = has("arch") || has("cachyos") || has("manjaro") || has("endeavouros"), debian = has("debian") || has("ubuntu"), fedora = has("fedora") || has("rhel");
    if (!library.isEmpty()) {
        static const QMap<QString, QString> arch32 = {{"libvulkan.so.1", "lib32-vulkan-icd-loader"}, {"libc.so.6", "lib32-glibc"}, {"libm.so.6", "lib32-glibc"}, {"libstdc++.so.6", "lib32-gcc-libs"}, {"libgcc_s.so.1", "lib32-gcc-libs"}, {"libz.so.1", "lib32-zlib"}, {"libasound.so.2", "lib32-alsa-lib"}, {"libudev.so.1", "lib32-systemd"}, {"libX11.so.6", "lib32-libx11"}, {"libwayland-client.so.0", "lib32-wayland"}, {"libxkbcommon.so.0", "lib32-libxkbcommon"}, {"libpulse.so.0", "lib32-libpulse"}, {"libGL.so.1", "lib32-mesa"}, {"libEGL.so.1", "lib32-mesa"}};
        if (arch && arch32.contains(library)) return "Arch family: the 32-bit package for " + library + " is probably " + arch32[library] + " (guess from a short table; verify with `pacman -F " + library + "`), and [multilib] must be enabled in /etc/pacman.conf.";
        return QString("Install your distribution's 32-bit (") + (debian ? ":i386" : fedora ? ".i686" : arch ? "lib32-" : "i386/i686/lib32") + ") package that provides " + library + ". This is a guess; the package name is not known to the launcher.";
    }
    if (arch) {
        QString gpu = gpus.contains(0x1002) ? "lib32-vulkan-radeon" : gpus.contains(0x8086) ? "lib32-vulkan-intel" : gpus.contains(0x10de) ? "lib32-nvidia-utils (must match the installed NVIDIA driver)" : "lib32-vulkan-radeon, lib32-vulkan-intel or lib32-nvidia-utils for your GPU";
        return "Arch family (CachyOS, Manjaro, EndeavourOS): enable [multilib] in /etc/pacman.conf, then install lib32-glibc lib32-mesa lib32-vulkan-icd-loader and " + gpu + ". The GPU-specific name is a guess from the GPU vendor.";
    }
    if (debian) return "Debian/Ubuntu: `sudo dpkg --add-architecture i386`, then install libc6:i386 libvulkan1:i386 and mesa-vulkan-drivers:i386 (NVIDIA: the matching libnvidia-gl-<version>:i386). A guess from the distribution family.";
    if (fedora) return "Fedora family: install glibc.i686 vulkan-loader.i686 mesa-vulkan-drivers.i686 (NVIDIA: the matching i686 driver libraries). A guess from the distribution family.";
    return "Install your distribution's 32-bit glibc, Vulkan loader and GPU Vulkan driver (Mesa for AMD/Intel, the matching NVIDIA 32-bit libraries for NVIDIA). A generic guess; the distribution is not recognised.";
}
Verdict deriveVerdict(const VerdictInput &in) {
    Verdict v; QStringList checked;
    auto done = [&](const QString &code, const QString &detail, const QString &message) { v.code = code; v.detail = detail; v.message = message; v.checked = checked.join(", "); return v; };
    checked << "binary present";
    if (!in.binaryExists) return done("BINARY_MISSING", {}, "The game program file is missing. The download may be incomplete or extracted somewhere the launcher cannot see.");
    checked << "ELF header";
    if (!in.elfValid && in.elfBits == 0) return done("BAD_BINARY", {}, "The game program file is not a readable Linux executable (damaged or truncated download?).");
    if (in.elfBits != 0 && (in.elfBits != 32 || in.machine != 3)) return done("WRONG_ARCHITECTURE", QString::number(in.elfBits) + "-bit machine " + QString::number(in.machine), "The game program is not a 32-bit x86 executable, which this release requires.");
    checked << "execute permission";
    if (!in.executable) return done("NOT_EXECUTABLE", {}, "The game program has no execute permission for your user. Unzipping on some file systems drops it; run `chmod +x` on the game's bin/melee file or extract the archive with tar.");
    checked << "mount options";
    if (in.noexecMount) return done("NOEXEC_MOUNT", {}, "The game folder is on a file system mounted noexec, so programs there cannot run. Move the game to your home folder or another executable location.");
    checked << "32-bit loader";
    if (!in.interpreter.isEmpty() && !in.interpreterExists) return done("NO_32BIT_LOADER", in.interpreter, "This computer has no 32-bit program loader (" + in.interpreter + "), so the 32-bit game cannot even begin. The 32-bit glibc package is missing.");
    // The launcher refuses a missing or non-executable game itself; the binary checks above name the cause, so they win.
    if (!in.prepareError.isEmpty()) return done("LAUNCHER_FAILED", {}, "The launcher stopped before starting the game: " + in.prepareError);
    const bool ranFine = in.launched && in.finished && !in.crashed && in.exitCode == 0;
    if (ranFine) return done("STARTED_OK", {}, "The game started and exited normally.");
    if (in.launched && !in.finished && !in.startFailed) return done("RUNNING", {}, "The game is still running.");
    const bool failed = in.launched;
    const auto output = in.childOutput + "\n" + in.gameLog;
    checked << "loader messages";
    auto lib = missingLibraryInOutput(output);
    if (lib.isEmpty() && !in.lddMissing.isEmpty()) lib = in.lddMissing.first();
    if (lib.isEmpty() && !in.missingLibs.isEmpty() && !(failed && !in.startFailed && !in.crashed && in.exitCode == 0)) lib = in.missingLibs.first();
    if (!lib.isEmpty()) return done("MISSING_LIBRARY", lib, "The 32-bit library " + lib + " is missing, so the game cannot load.");
    auto ver = libraryVersionInOutput(output);
    if (!ver.isEmpty()) return done("LIBRARY_TOO_OLD", ver, "A system library is older than the game needs: " + ver + ".");
    checked << "graphics messages";
    const bool gfx = graphicsFailureInOutput(output);
    if (in.vulkanKnown && !in.vulkan32Present && (gfx || !failed || in.exitCode != 0 || in.crashed || in.startFailed))
        return done("NO_32BIT_VULKAN_DRIVER", {}, "No working 32-bit Vulkan driver was found. The game needs one for your graphics card, even though the launcher itself is 64-bit.");
    if (failed && gfx) return done("GRAPHICS_INIT_FAILED", {}, "The game started but could not set up graphics (32-bit Vulkan or the display connection).");
    if (!failed) {
        if (in.vulkanKnown) checked << "32-bit Vulkan";
        return done("UNKNOWN", {}, "No problem was found by the static checks; start the game to learn more.");
    }
    if (in.startFailed) return done("START_FAILED", in.startError, "The system refused to start the game program: " + in.startError);
    if (in.crashed) return done("KILLED_BY_SIGNAL", in.signal.isEmpty() ? "UNKNOWN_SIGNAL" : in.signal, "The game was killed by " + (in.signal.isEmpty() ? QString("a signal (Qt did not report which; see the game log)") : in.signal) + ".");
    if (in.exitCode != 0) return done("EXITED_EARLY", "code=" + QString::number(in.exitCode), "The game exited with code " + QString::number(in.exitCode) + " after " + QString::number(in.elapsedMs / 1000.0, 'f', 1) + " s. The game log below usually says why.");
    return done("UNKNOWN", {}, "The game stopped for a reason the launcher could not classify.");
}
// ---- redaction and formatting --------------------------------------------------------------------
Redactor Redactor::forThisMachine(const QStringList &discs) {
    Redactor r; r.home = QDir::homePath(); r.discPaths = discs;
    for (const auto &key : {"USER", "LOGNAME", "USERNAME"}) { auto v = qEnvironmentVariable(key); if (v.size() >= 3 && !r.words.contains(v)) r.words << v; }
    auto host = QSysInfo::machineHostName(); if (host.size() >= 3 && host != "localhost") r.words << host;
    return r;
}
QString Redactor::apply(QString text) const {
    for (const auto &disc : discPaths) {
        if (disc.isEmpty()) continue;
        const auto name = QFileInfo(disc).fileName();
        for (const auto &spelling : {disc, QDir::toNativeSeparators(disc), QFileInfo(disc).absoluteFilePath()}) text.replace(spelling, name);
    }
    // A path that starts at a word boundary and ends in a disc extension keeps only its file name, spaces included.
    static const QRegularExpression discLike(R"re((?<![\w/~.-])(?:~|[A-Za-z]:|/)(?:[^\s"']|[ ](?![/~]|[A-Za-z]:)){0,240}?[/\\]([^/\\\r\n"']+\.(?:iso|gcm|ciso|gcz|rvz|wia)))re", QRegularExpression::CaseInsensitiveOption);
    text.replace(discLike, "\\1");
    if (home.size() > 1) { text.replace(home, "~"); text.replace(QDir::toNativeSeparators(home), "~"); }
    static const QRegularExpression homes("(?:/mnt/[a-z])?/(?:home|Users)/[^/\\s\"']+|[A-Za-z]:\\\\Users\\\\[^\\\\\\s\"']+"), media("/(?:run/)?media/[^/\\s\"']+/?");
    text.replace(homes, "~"); text.replace(media, "/media/<user>/");
    static const QRegularExpression ip("\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b");
    text.replace(ip, "<ip>");
    static const QRegularExpression mac("\\b[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\\b");
    text.replace(mac, "<mac>");
    for (const auto &w : words) text.replace(QRegularExpression("(?<![\\w.-])" + QRegularExpression::escape(w) + "(?![\\w.-])"), "<name>");
    return text;
}
QString envValueForReport(const QString &name, const QString &value) {
    static const QRegularExpression secret("TOKEN|KEY|SECRET|PASS|AUTH|CRED|COOKIE|SESSION_ID|PRELOAD", QRegularExpression::CaseInsensitiveOption);
    if (name == "LD_PRELOAD") return value.isEmpty() ? "(empty)" : "(set, value hidden)";
    if (name.contains("SESSION_TYPE") || name == "XDG_SESSION_DESKTOP") return value;
    return secret.match(name).hasMatch() ? "(set, value hidden)" : value;
}
QString shortList(const QString &text, int head, int tail) {
    auto lines = text.split('\n'); while (!lines.isEmpty() && lines.last().isEmpty()) lines.removeLast();
    if (lines.size() <= head + tail) return lines.join('\n');
    return lines.mid(0, head).join('\n') + "\n... " + QString::number(lines.size() - head - tail) + " lines omitted ...\n" + lines.mid(lines.size() - tail).join('\n');
}
// ---- exec probe -------------------------------------------------------------------------------------
QString execProbe(const QString &program, const QStringList &environment) {
#ifdef Q_OS_UNIX
    // posix_spawn reports the errno of a failed execve directly. If it unexpectedly succeeds the
    // child is our own and is killed at once, by pid, before it can do anything.
    QByteArray path = QFile::encodeName(program); QVector<QByteArray> env; for (const auto &e : environment) env << e.toLocal8Bit();
    QVector<char *> envp; for (auto &e : env) envp << e.data(); envp << nullptr;
    char *argv[] = {path.data(), nullptr};
    posix_spawn_file_actions_t actions; posix_spawn_file_actions_init(&actions);
    for (int fd = 0; fd < 3; ++fd) posix_spawn_file_actions_addopen(&actions, fd, "/dev/null", fd == 0 ? O_RDONLY : O_WRONLY, 0);
    pid_t pid = 0; const int err = posix_spawn(&pid, path.constData(), &actions, nullptr, argv, envp.data());
    posix_spawn_file_actions_destroy(&actions);
    if (err != 0) {
        static const QMap<int, QString> names = {{ENOENT, "ENOENT"}, {EACCES, "EACCES"}, {ENOEXEC, "ENOEXEC"}, {ENOMEM, "ENOMEM"}, {ETXTBSY, "ETXTBSY"}, {ELIBBAD, "ELIBBAD"}, {E2BIG, "E2BIG"}, {ENOTDIR, "ENOTDIR"}, {ELOOP, "ELOOP"}, {EPERM, "EPERM"}};
        return names.value(err, "errno " + QString::number(err)) + ": " + QString::fromLocal8Bit(strerror(err));
    }
    kill(pid, SIGKILL); int status = 0; waitpid(pid, &status, 0);
    return "exec succeeded (the probe process was killed at once)";
#else
    Q_UNUSED(program) Q_UNUSED(environment)
    return "not available on this platform";
#endif
}
// ---- collector ----------------------------------------------------------------------------------------
QString diagnosticsDir(const QString &userDir) { return userDir + "/diagnostics"; }
QString gameProgramPath(const QString &app) {
#ifdef Q_OS_WIN
    return app + "/melee-pc.exe";
#else
    auto p = app + "/bin/melee"; return QFile::exists(p) ? p : app + "/melee";
#endif
}
QStringList environmentDiff(const QProcessEnvironment &before, const QProcessEnvironment &after) {
    QStringList out;
    for (const auto &k : after.keys()) {
        if (!before.contains(k)) out << "+ " + k + "=" + envValueForReport(k, after.value(k));
        else if (before.value(k) != after.value(k)) out << "~ " + k + "=" + envValueForReport(k, after.value(k)) + "  (was " + envValueForReport(k, before.value(k)) + ")";
    }
    for (const auto &k : before.keys()) if (!after.contains(k)) out << "- " + k;
    out.sort(); return out;
}
void rotateReports(const QString &dir, int keep) {
    auto files = QDir(dir).entryList({"launch-diagnostics-*.txt"}, QDir::Files, QDir::Name);
    for (int i = 0; i < files.size() - keep; ++i) QFile::remove(dir + "/" + files[i]);
}
namespace {
QString readHead(const QString &path, qint64 n) { if (path.isEmpty()) return {}; QFile f(path); return f.open(QIODevice::ReadOnly) ? QString::fromUtf8(f.read(n)) : QString(); }
QString readTail(const QString &path, qint64 n) {
    if (path.isEmpty()) return {};
    QFile f(path); if (!f.open(QIODevice::ReadOnly)) return {};
    if (f.size() > n) f.seek(f.size() - n);
    return QString::fromUtf8(f.readAll());
}
QMap<QString, QString> parseOsRelease(const QString &text) {
    QMap<QString, QString> m;
    for (const auto &line : text.split('\n')) { int eq = line.indexOf('='); if (eq <= 0) continue; auto v = line.mid(eq + 1).trimmed(); if (v.size() >= 2 && (v[0] == '"' || v[0] == '\'')) v = v.mid(1, v.size() - 2); m[line.left(eq)] = v; }
    return m;
}
struct Run { bool started = false, timedOut = false; int code = -1; QString out; };
Run runTool(const QString &program, const QStringList &args, const QProcessEnvironment &env, int ms) {
    Run r; QProcess p; p.setProcessChannelMode(QProcess::MergedChannels); p.setProcessEnvironment(env);
    p.start(program, args);
    if (!p.waitForStarted(2000)) return r;
    r.started = true;
    if (!p.waitForFinished(ms)) { r.timedOut = true; p.kill(); p.waitForFinished(1000); }
    r.code = p.exitCode(); r.out = QString::fromUtf8(p.readAll().left(256 * 1024)); return r;
}
QString section(const QString &title) { return QString(QChar(10)) + "== " + title + " ==" + QChar(10); }
QString vendorName(quint32 v) { return v == 0x1002 ? "AMD" : v == 0x8086 ? "Intel" : v == 0x10de ? "NVIDIA" : v == 0x1414 ? "Microsoft" : "unknown"; }
}
DiagResult buildDiagnostics(const DiagContext &c) {
    QString o; auto line = [&](const QString &s = {}) { o += s + "\n"; };
    auto heading = [&](const QString &t) { o += "\n== " + t + " ==\n"; };
    auto env = QProcessEnvironment::systemEnvironment();
    const auto &spec = c.spec;
    const auto program = c.haveSpec ? spec.program : gameProgramPath(c.appDir);
    const auto osText = readHead("/etc/os-release", 16384);
    const auto osr = parseOsRelease(osText);
    VerdictInput vin; vin.prepareError = c.prepareError;
    // The kernel release looks like an IPv4 address to the redaction pass (6.6.87.2), so it is put back afterwards.
    QString kernelText; const QString kernelMarker = QString(QChar(1)) + "KERNEL" + QChar(1);
    // ---- Launcher
    line("== Launcher ==");
    QString version; { QFile f(c.appDir + "/version.txt"); if (f.open(QIODevice::ReadOnly)) version = QString::fromUtf8(f.readLine()).trimmed(); }
    line("Game version: " + (version.isEmpty() ? "(no version.txt)" : version));
    line(QString("Build: ") +
#ifdef QT_DEBUG
         "debug"
#else
         "release"
#endif
         + ", Qt " + qVersion() + " (built with " + QT_VERSION_STR + "), platform plugin: " + (c.platform.isEmpty() ? "(none)" : c.platform));
    line("Launcher program: " + c.launcherExe);
    line("Working directory: " + QDir::currentPath());
    line("Game folder: " + c.appDir);
    line("User data folder: " + c.userDir);
    line("Run folder: " + (c.runDir.isEmpty() ? QString("(none, no game was started)") : c.runDir));
    {
        QStringList how;
        if (env.contains("GAMESCOPE_WAYLAND_DISPLAY") || env.contains("GAMESCOPE_WAYLAND")) how << "gamescope session";
        if (env.value("SteamDeck") == "1" || env.contains("SteamOS")) how << "SteamOS / handheld session";
        if (env.contains("SteamGameId") || env.contains("SteamAppId") || env.contains("STEAM_COMPAT_DATA_PATH")) how << "Steam";
        if (env.contains("GIO_LAUNCHED_DESKTOP_FILE") || env.contains("DESKTOP_STARTUP_ID") || env.contains("XDG_ACTIVATION_TOKEN")) how << "desktop entry";
        if (env.contains("INVOCATION_ID") && how.isEmpty()) how << "systemd unit";
#ifdef Q_OS_UNIX
        if (isatty(0) || isatty(1) || isatty(2)) how << "terminal";
#endif
        line("Started from (guess from the environment): " + (how.isEmpty() ? QString("unknown") : how.join(", ")));
    }
    // ---- System
    line(QString(QChar(10)) + section("System").trimmed() + "\n");
    o.chop(1);
    line("Operating system: " + QSysInfo::prettyProductName());
    if (!osr.isEmpty()) line(QString("os-release: ID=%1 NAME=\"%2\" VERSION_ID=%3 ID_LIKE=%4 VARIANT_ID=%5").arg(osr.value("ID"), osr.value("NAME"), osr.value("VERSION_ID"), osr.value("ID_LIKE"), osr.value("VARIANT_ID")));
#ifdef Q_OS_UNIX
    { struct utsname u; if (uname(&u) == 0) { kernelText = QString("%1 %2 %3, machine %4").arg(u.sysname, u.release, u.version, u.machine); line("Kernel: " + kernelMarker); } }
#else
    kernelText = QSysInfo::kernelType() + " " + QSysInfo::kernelVersion(); line("Kernel: " + kernelMarker);
#endif
    line("CPU architecture: " + QSysInfo::currentCpuArchitecture() + " (launcher built for " + QSysInfo::buildCpuArchitecture() + ")");
    vin.hostX86_64 = QSysInfo::currentCpuArchitecture() == "x86_64";
    line("Session: XDG_SESSION_TYPE=" + env.value("XDG_SESSION_TYPE", "(unset)") + " WAYLAND_DISPLAY=" + (env.contains("WAYLAND_DISPLAY") ? env.value("WAYLAND_DISPLAY") : "(unset)") + " DISPLAY=" + env.value("DISPLAY", "(unset)") + " XDG_CURRENT_DESKTOP=" + env.value("XDG_CURRENT_DESKTOP", "(unset)"));
    {
        QStringList seen; const auto keys = env.keys();
        static const QRegularExpression interesting("^(SDL_.*|VK_.*|MESA_.*|DRI_PRIME|__NV_.*|__VK_.*|__GLX_.*|LD_LIBRARY_PATH|LD_PRELOAD|MELEE_.*|GAMESCOPE.*|STEAM.*|SteamDeck|SteamGameId|SteamAppId|QT_QPA_PLATFORM|DESKTOP_SESSION|XDG_SESSION_DESKTOP|XDG_RUNTIME_DIR|WAYLAND_.*|ENABLE_.*|PROTON.*|DXVK.*|MANGOHUD.*)$");
        for (const auto &k : keys) if (interesting.match(k).hasMatch() && k != "XDG_RUNTIME_DIR") seen << k + "=" + envValueForReport(k, env.value(k));
        seen.sort();
        line("Environment the game or SDL reads (names matching a short allowlist; not the full environment):");
        for (const auto &s : seen) line("  " + s);
        if (seen.isEmpty()) line("  (none of them set)");
    }
    // ---- Game binary
    line(QString(QChar(10)) + section("Game binary").trimmed() + "\n"); o.chop(1);
    QFileInfo bin(program); vin.binaryExists = bin.exists();
    line("Path: " + QDir::cleanPath(bin.absoluteFilePath()) + (bin.isSymLink() ? "  (symlink to " + bin.symLinkTarget() + ")" : ""));
    line(QString("Exists: ") + (bin.exists() ? "yes" : "NO") + (bin.isDir() ? " (it is a directory)" : ""));
    ElfInfo elf; QStringList lddMissing; QString lddText; QVector<LibraryHit> libs; QStringList ldPath;
    if (bin.exists() && bin.isFile()) {
        line("Size: " + QString::number(bin.size()) + " bytes");
        const auto perms = bin.permissions();
        line("Permissions: " + permissionString(perms) + "  execute bit set for anyone: " + ((perms & (QFileDevice::ExeOwner | QFileDevice::ExeGroup | QFileDevice::ExeOther)) ? "yes" : "NO") + ", executable by this user: " + (bin.isExecutable() ? "yes" : "NO"));
        vin.executable = bin.isExecutable();
#ifdef Q_OS_UNIX
        { struct statvfs sv; if (statvfs(QFile::encodeName(bin.absoluteFilePath()).constData(), &sv) == 0) vin.noexecMount = (sv.f_flag & ST_NOEXEC) != 0; }
        auto mount = mountFor(bin.canonicalFilePath(), readHead("/proc/self/mountinfo", 1 << 20));
        line(QString("File system: ") + (mount.found ? mount.fsType + " mounted at " + mount.mountPoint + ", options " + mount.options : "(mount table unreadable)") + "; noexec: " + (vin.noexecMount ? "YES" : "no"));
#endif
        elf = readElf(bin.absoluteFilePath());
        vin.elfValid = elf.valid; vin.elfBits = elf.bits; vin.machine = elf.machine;
        if (!elf.isElf) line("ELF: " + elf.error);
        else {
            line(QString("ELF: class %1-bit, %2-endian, machine %3, type %4%5").arg(elf.bits).arg(elf.littleEndian ? "little" : "big", elf.machineName()).arg(elf.type == 2 ? "executable" : elf.type == 3 ? "PIE/shared" : QString::number(elf.type)).arg(elf.valid ? QString() : "  (incomplete: " + elf.error + ")"));
            line("Interpreter (PT_INTERP): " + (elf.interpreter.isEmpty() ? (elf.dynamic ? "(none recorded)" : "(static executable)") : elf.interpreter));
            if (!elf.interpreter.isEmpty()) {
                vin.interpreter = elf.interpreter; vin.interpreterExists = QFileInfo::exists(elf.interpreter);
                line("Interpreter exists: " + QString(vin.interpreterExists ? "yes" : "NO  (an existing binary that reports \"No such file or directory\" means this 32-bit loader is not installed)"));
            }
            if (!elf.runpath.isEmpty() || !elf.rpath.isEmpty()) line("RPATH/RUNPATH: " + (elf.rpath + elf.runpath).join(":"));
        }
    }
    // ---- Shared libraries
    line(QString(QChar(10)) + section("Shared libraries").trimmed() + "\n"); o.chop(1);
    ldPath = (c.haveSpec ? spec.environment.value("LD_LIBRARY_PATH") : c.appDir + "/lib").split(':', Qt::SkipEmptyParts);
    const auto sysDirs = systemLibraryDirs();
    if (elf.valid && elf.dynamic) {
        line("Search order: RPATH, LD_LIBRARY_PATH for the game (" + ldPath.join(":") + "), RUNPATH, 32-bit system folders. Only 32-bit files count.");
        libs = resolveNeeded(elf, bin.absolutePath(), ldPath, sysDirs);
        for (const auto &l : libs) {
            line("  " + l.name + ": " + (l.found ? "FOUND (" + l.path + ")" : "MISSING" + (l.note.isEmpty() ? QString() : "  [" + l.note + "]")));
            if (!l.found) vin.missingLibs << l.name;
        }
        if (libs.isEmpty()) line("  (no DT_NEEDED entries)");
    } else line(elf.valid ? "  Static executable: no shared libraries." : "  Not available: the binary could not be parsed.");
#ifdef Q_OS_UNIX
    if (elf.valid && elf.dynamic) {
        if (!QStandardPaths::findExecutable("ldd").isEmpty()) {
            auto pe = c.haveSpec ? spec.environment : env; pe.insert("LD_LIBRARY_PATH", ldPath.join(':'));
            pe.remove("LD_PRELOAD");
            auto r = runTool("ldd", {bin.absoluteFilePath()}, pe, 5000);
            lddText = r.out;
            line("ldd (with the game's library path), exit " + QString::number(r.code) + (r.timedOut ? ", TIMED OUT" : "") + ":");
            for (const auto &l : r.out.split('\n', Qt::SkipEmptyParts)) { line("  " + l.trimmed()); static const QRegularExpression nf("^\\s*(\\S+) => not found"); auto m = nf.match(l); if (m.hasMatch()) lddMissing << m.captured(1); }
        } else line("ldd: not installed (the launcher's own check above does not need it)");
    }
    vin.lddMissing = lddMissing;
    {
        line("Bundled libraries in " + c.appDir + "/lib:");
        auto names = QDir(c.appDir + "/lib").entryList({"*.so*"}, QDir::Files, QDir::Name);
        if (names.isEmpty()) line("  (none)");
        int bad = 0;
        for (const auto &n : names) {
            auto path = c.appDir + "/lib/" + n; auto e = readElf(path);
            QString status = !e.valid ? "unreadable ELF (" + e.error + ")" : QString::number(e.bits) + "-bit " + e.machineName();
            if (e.valid && e.dynamic) {
                auto hits = resolveNeeded(e, c.appDir + "/lib", ldPath, sysDirs); QStringList miss; for (const auto &h : hits) if (!h.found) miss << h.name;
                if (!miss.isEmpty()) status += "; MISSING: " + miss.join(", ");
            }
            if (!e.valid || e.bits != 32 || status.contains("MISSING")) { ++bad; line("  " + n + ": " + status); }
        }
        if (!names.isEmpty()) line("  " + QString::number(names.size()) + " files; " + (bad ? QString::number(bad) + " with a problem (listed above)" : "all are 32-bit and their own dependencies resolve"));
    }
#endif
    // ---- Graphics
    line(QString(QChar(10)) + section("Graphics").trimmed() + "\n"); o.chop(1);
    QSet<quint32> vendors;
#ifdef Q_OS_LINUX
    {
        for (const auto &card : QDir("/sys/class/drm").entryList({"card?"}, QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name)) {
            const auto dev = "/sys/class/drm/" + card + "/device";
            bool ok = false; quint32 vid = readHead(dev + "/vendor", 16).trimmed().toUInt(&ok, 16);
            if (!ok) continue; vendors.insert(vid);
            line("GPU " + card + ": vendor " + vendorName(vid) + " (0x" + QString::number(vid, 16) + "), device 0x" + readHead(dev + "/device", 16).trimmed().mid(2) + ", kernel driver " + (QFileInfo(dev + "/driver").isSymLink() ? QFileInfo(QFileInfo(dev + "/driver").symLinkTarget()).fileName() : "(none)"));
        }
        if (vendors.isEmpty()) line("GPU: none visible in /sys/class/drm");
        if (!QStandardPaths::findExecutable("lspci").isEmpty()) {
            if (c.full) {
                auto r = runTool("lspci", {"-nn"}, env, 3000);
                for (auto l : r.out.split('\n')) if (l.contains("VGA") || l.contains("3D controller") || l.contains("Display controller")) line("lspci: " + l.section(' ', 1));
            } else line("lspci: skipped in the quick report");
        } else line("lspci: not installed");
        // Vulkan ICDs
        QStringList manifests, dirs;
        const auto override_ = env.value("VK_DRIVER_FILES", env.value("VK_ICD_FILENAMES"));
        if (!override_.isEmpty()) { line("ICD list overridden by VK_DRIVER_FILES / VK_ICD_FILENAMES; only these are used."); for (const auto &f : override_.split(':', Qt::SkipEmptyParts)) manifests << f; }
        else {
            for (auto d : env.value("XDG_CONFIG_DIRS", "/etc/xdg").split(':', Qt::SkipEmptyParts)) dirs << d + "/vulkan/icd.d";
            dirs << "/etc/vulkan/icd.d" << (env.value("XDG_DATA_HOME", QDir::homePath() + "/.local/share") + "/vulkan/icd.d");
            for (auto d : env.value("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(':', Qt::SkipEmptyParts)) dirs << d + "/vulkan/icd.d";
            dirs << "/usr/share/vulkan/icd.d";
            QSet<QString> seen; for (const auto &d : dirs) if (!seen.contains(d)) for (const auto &f : QDir(d).entryList({"*.json"}, QDir::Files, QDir::Name)) manifests << d + "/" + f;
        }
        ElfInfo want; want.bits = 32; want.machine = 3; bool any32 = false;
        manifests.removeDuplicates();
        line("Vulkan ICD manifests:");
        for (const auto &m : manifests) {
            QFile f(m); if (!f.open(QIODevice::ReadOnly)) { line("  " + m + ": unreadable"); continue; }
            auto lib = QJsonDocument::fromJson(f.read(1 << 20)).object()["ICD"].toObject()["library_path"].toString();
            QString where;
            if (lib.isEmpty()) where = "no library_path";
            else {
                if (lib.startsWith("./") || lib.startsWith("../")) lib = QFileInfo(m).absolutePath() + "/" + lib;
                auto hit = findLibrary(lib, sysDirs + ldPath, want);
                if (hit.found) any32 = true;
                where = "library_path " + lib + " -> 32-bit build " + (hit.found ? "FOUND (" + hit.path + ")" : "MISSING" + (hit.note.isEmpty() ? QString() : " [" + hit.note + "]"));
            }
            line("  " + m + ": " + where);
        }
        if (manifests.isEmpty()) line("  (none found)");
        auto loader = findLibrary("libvulkan.so.1", sysDirs, want);
        line("32-bit Vulkan loader libvulkan.so.1: " + (loader.found ? "FOUND (" + loader.path + ")" : "MISSING" + (loader.note.isEmpty() ? QString() : " [" + loader.note + "]")));
        // The launcher's own 32-bit helper is the decisive check: it creates a Vulkan device as the game would.
        QByteArray probeJson; bool probeRan = false;
        auto pre = c.runDir.isEmpty() ? QString() : readHead(c.runDir + "/graphics-preflight.log", 1 << 20);
        if (!pre.isEmpty()) { int a = pre.indexOf("Probe stdout:\n"), b = pre.indexOf("\nProbe stderr:"); if (a >= 0 && b > a) { probeJson = pre.mid(a + 14, b - a - 14).toUtf8(); probeRan = true; } line("Launcher's 32-bit graphics check before this launch (graphics-preflight.log):"); for (const auto &l : shortList(pre.left(pre.indexOf("\nSelected GPU:") > 0 ? pre.indexOf("\nSelected GPU:") : pre.size()), 12, 4).split('\n')) line("  " + l); }
        else if (c.full && QFile::exists(c.appDir + "/bin/melee-graphics-probe")) {
            auto pe = c.haveSpec ? spec.environment : env; pe.remove("LD_PRELOAD"); pe.insert("LD_LIBRARY_PATH", ldPath.join(':'));
            auto r = runTool(c.appDir + "/bin/melee-graphics-probe", {}, pe, 12000);
            line("32-bit graphics helper (bin/melee-graphics-probe), exit " + QString::number(r.code) + (r.timedOut ? ", TIMED OUT" : "") + (r.started ? "" : ", could not start") + ":");
            for (const auto &l : shortList(r.out, 14, 4).split('\n')) line("  " + l);
            if (r.started && !r.timedOut) { probeJson = r.out.toUtf8(); probeRan = true; }
        }
        if (probeRan) {
            auto report = parseGraphicsReport(probeJson, 0);
            if (report.valid) { vin.vulkanKnown = true; vin.vulkan32Present = report.ready(); line("32-bit Vulkan device creation: " + QString(report.ready() ? "PASSED" : "FAILED") + " - " + report.summary().replace('\n', " | ")); }
        }
        if (!vin.vulkanKnown) { vin.vulkanKnown = true; vin.vulkan32Present = any32 && loader.found; line("32-bit Vulkan (inferred from ICD manifests and loader only): " + QString(vin.vulkan32Present ? "a 32-bit driver library exists" : "NO 32-bit driver library found")); }
        if (c.full && !QStandardPaths::findExecutable("vulkaninfo").isEmpty()) {
            auto r = runTool("vulkaninfo", {"--summary"}, env, 5000);
            line("vulkaninfo --summary (this is the 64-bit loader: it does NOT prove the 32-bit driver works), exit " + QString::number(r.code) + (r.timedOut ? ", TIMED OUT" : "") + ":");
            for (const auto &l : r.out.split('\n')) { auto t = l.trimmed(); if (t.startsWith("GPU") || t.startsWith("deviceName") || t.startsWith("driverName") || t.startsWith("driverInfo") || t.startsWith("apiVersion") || t.startsWith("deviceType") || t.startsWith("driverVersion") || t.startsWith("vendorID")) line("  " + t); }
        } else if (c.full) line("vulkaninfo: not installed");
        line("HINT: " + packageHint(osText, {}, vendors));
    }
#else
    line("Linux graphics checks do not apply on this platform.");
#endif
    // ---- Spawn
    line(QString(QChar(10)) + section("Spawn").trimmed() + "\n"); o.chop(1);
    const auto &sp = c.spawn;
    if (!c.prepareError.isEmpty()) line("The launcher failed before spawning: " + c.prepareError);
    else if (!sp.attempted) line("No game was started (diagnostics only).");
    else {
        QString args; for (const auto &a : sp.arguments) args += " " + (a.contains(' ') ? "\"" + a + "\"" : a);
        QStringList shown = sp.arguments; for (int i = 0; i + 1 < shown.size(); ++i) if (shown[i] == "--iso") shown[i + 1] = QFileInfo(shown[i + 1]).fileName();
        args.clear(); for (const auto &a : shown) args += " " + (a.contains(' ') ? "\"" + a + "\"" : a);
        line("Command: " + sp.program + args + "   (disc image shown by file name only)");
        line("Working directory: " + sp.workingDirectory);
        auto diff = c.haveSpec ? environmentDiff(env, spec.environment) : QStringList();
        line("Environment changes the launcher applied (+ added, ~ changed, - removed):");
        for (const auto &d : diff) line("  " + d);
        if (diff.isEmpty()) line("  (none)");
        line(QString("Start: ") + (sp.started ? "started" : "FAILED") + (sp.processError >= 0 ? ", QProcess error " + QString::number(sp.processError) + (sp.processError == 0 ? " (FailedToStart)" : "") : "") + (sp.errorString.isEmpty() ? QString() : ", " + sp.errorString));
        if (!sp.execProbe.isEmpty()) line("Direct exec probe: " + sp.execProbe);
        vin.launched = true; vin.startFailed = !sp.started; vin.startError = sp.execProbe.isEmpty() ? sp.errorString : sp.execProbe;
        vin.finished = sp.finished; vin.crashed = sp.crashed; vin.exitCode = sp.exitCode; vin.signal = sp.signal; vin.elapsedMs = sp.elapsedMs;
        if (sp.finished) line(QString("Result: ") + (sp.crashed ? "killed by " + (sp.signal.isEmpty() ? QString("a signal (not reported by Qt)") : sp.signal) : "exited with code " + QString::number(sp.exitCode)) + " after " + QString::number(sp.elapsedMs / 1000.0, 'f', 2) + " s");
        else if (sp.started) line("Result: still running when this report was written");
        // stdout and stderr share launcher-process.log (QProcess merged channels)
        const auto out = readHead(sp.stdoutFile, 64 * 1024) + (QFileInfo(sp.stdoutFile).size() > 128 * 1024 ? "\n" : "") + (QFileInfo(sp.stdoutFile).size() > 64 * 1024 ? readTail(sp.stdoutFile, 64 * 1024) : QString());
        vin.childOutput = out;
        line("Child stdout+stderr (launcher-process.log, first 25 and last 25 lines):");
        const auto text = QFileInfo(sp.stdoutFile).size() <= 128 * 1024 ? readHead(sp.stdoutFile, 128 * 1024) : readHead(sp.stdoutFile, 32 * 1024) + "\n" + readTail(sp.stdoutFile, 32 * 1024);
        if (text.trimmed().isEmpty()) line("  (empty: the game printed nothing)"); else for (const auto &l : shortList(text, 25, 25).split('\n')) line("  " + l);
    }
    // ---- After exit
    line(QString(QChar(10)) + section("After exit").trimmed() + "\n"); o.chop(1);
    if (!c.runDir.isEmpty()) {
        auto log = readTail(c.runDir + "/melee-pc.log", 48 * 1024);
        vin.gameLog = log;
        line("Game log (melee-pc.log, last 40 lines):");
        if (log.isEmpty()) line("  (no game log; the game never got far enough to write one)"); else for (const auto &l : shortList(log, 0, 40).split('\n')) line("  " + l);
        auto crash = latestCrash(c.runDir);
        if (!crash.isEmpty()) { line("Newest crash report (" + QFileInfo(crash).fileName() + ", first 60 lines):"); for (const auto &l : shortList(readHead(crash, 32 * 1024), 60, 0).split('\n')) line("  " + l); }
        else line("Crash report: none");
    } else line("No run folder for this report.");
    // ---- Verdict
    DiagResult result; result.verdict = deriveVerdict(vin);
    if (!c.finished && c.spawn.attempted && !c.spawn.finished && c.spawn.started) result.verdict.hint = "";
    const auto &v = result.verdict;
    QString hint = v.code == "MISSING_LIBRARY" ? packageHint(osText, v.detail, vendors) : (v.code == "NO_32BIT_LOADER" || v.code == "NO_32BIT_VULKAN_DRIVER" || v.code == "GRAPHICS_INIT_FAILED" || v.code == "LIBRARY_TOO_OLD") ? packageHint(osText, {}, vendors) : QString();
    if (v.code == "NOT_EXECUTABLE") hint = "Run: chmod +x \"" + program + "\" (and bin/melee-graphics-probe if present).";
    if (v.code == "NOEXEC_MOUNT") hint = "Move the whole game folder to your home directory (a noexec mount cannot run programs).";
    result.verdict.hint = hint;
    QString head;
    head += "GD's Melee launch diagnostics\n";
    head += "Written: " + QDateTime::currentDateTime().toString(Qt::ISODate) + "\n";
    head += "\nWHAT THIS FILE CONTAINS: your launcher and game versions, Linux distribution, kernel, session type, graphics card model, the game's file and library checks, the exact command that started the game (the disc image is shown by file name only), the environment variables the launcher changed, and the last lines of the game's logs. Your home folder is shown as ~; your user name, computer name and IP addresses are removed; the full environment and your disc image's location are NOT included. Read it before sharing.\n";
    head += "\nVERDICT: " + v.line() + "\n" + v.message + "\n";
    if (!v.hint.isEmpty()) head += "HINT: " + v.hint + "\n";
    head += "Checked: " + v.checked + "\n\n";
    result.text = Redactor::forThisMachine(c.discPaths).apply(head + o); result.text.replace(kernelMarker, kernelText);
    return result;
}
DiagResult writeDiagnostics(const DiagContext &c) {
    auto result = buildDiagnostics(c);
    const auto dir = diagnosticsDir(c.userDir); QDir().mkpath(dir);
    const auto bytes = result.text.toUtf8();
    const auto stamp = c.stamp.isEmpty() ? QDateTime::currentDateTime().toString("yyyyMMdd-HHmmss") : c.stamp;
    result.latestPath = dir + "/launch-diagnostics.txt"; result.path = dir + "/launch-diagnostics-" + stamp + ".txt";
    try {
        writeAtomic(result.latestPath, bytes); writeAtomic(result.path, bytes);
        if (!c.runDir.isEmpty() && QDir(c.runDir).exists()) writeAtomic(c.runDir + "/launch-diagnostics.txt", bytes);
    } catch (const std::exception &) {}   // a report that cannot be saved must never block the launch
    rotateReports(dir);
    return result;
}
}
