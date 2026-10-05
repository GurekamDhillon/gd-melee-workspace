#pragma once
// Launch diagnostics: one paste-able text file that says why "the game will not start".
// Pure helpers (ELF reader, library resolution, verdict, redaction, rotation) are separate
// from the collector so tests can feed them synthetic facts.
#include "launcher_core.h"
#include <QFileDevice>
#include <QIODevice>
#include <QVector>
namespace launcher {
struct ElfInfo {
    bool isElf = false, valid = false;   // isElf: magic seen; valid: every table we need parsed
    QString error;                        // why valid is false
    int bits = 0; bool littleEndian = true; quint16 type = 0, machine = 0;
    bool dynamic = false;
    QString interpreter, soname;
    QStringList needed, rpath, runpath;
    QString machineName() const;
};
ElfInfo readElf(QIODevice &device, bool headerOnly = false);
ElfInfo readElf(const QString &path, bool headerOnly = false);

struct LibraryHit { QString name, path, note; bool found = false; };
// Resolves DT_NEEDED the way ld.so orders its search (RPATH, LD_LIBRARY_PATH, RUNPATH, defaults),
// but only accepts a file of the same ELF class and machine: Arch keeps its 64-bit libraries in
// /usr/lib, so a name-only match there would hide the missing lib32 package.
QVector<LibraryHit> resolveNeeded(const ElfInfo &exe, const QString &origin, const QStringList &ldLibraryPath, const QStringList &defaultDirs);
QStringList systemLibraryDirs(const QString &root = {});   // 32-bit candidates plus /etc/ld.so.conf entries

struct MountInfo { QString mountPoint, options, fsType; bool noexec = false, found = false; };
MountInfo mountFor(const QString &path, const QString &mountinfo);

QString signalName(int signal);
QString permissionString(QFileDevice::Permissions p);

// Facts in, one verdict out.
struct VerdictInput {
    QString prepareError;
    bool binaryExists = true, executable = true, noexecMount = false;
    bool elfValid = true; int elfBits = 32; quint16 machine = 3; bool hostX86_64 = true;
    QString interpreter; bool interpreterExists = true;
    QStringList missingLibs, lddMissing;
    bool vulkanKnown = false, vulkan32Present = true;
    bool launched = false, startFailed = false; QString startError;
    bool finished = false, crashed = false; int exitCode = 0; QString signal; qint64 elapsedMs = 0;
    QString childOutput, gameLog;
};
struct Verdict {
    QString code, detail, message, hint, checked;
    QString line() const;   // "MISSING_LIBRARY libvulkan.so.1"
    bool ok() const { return code == "STARTED_OK"; }
};
Verdict deriveVerdict(const VerdictInput &in);
QString missingLibraryInOutput(const QString &text);   // ld.so: "error while loading shared libraries: X"
QString libraryVersionInOutput(const QString &text);   // ld.so: "version `GLIBC_2.38' not found"
bool graphicsFailureInOutput(const QString &text);
QString packageHint(const QString &osRelease, const QString &library = {}, const QSet<quint32> &gpuVendors = {});

struct Redactor {
    QString home;
    QStringList discPaths, words;   // words: user and host names, replaced wherever they stand alone
    QString apply(QString text) const;
    static Redactor forThisMachine(const QStringList &discPaths);
};
QString envValueForReport(const QString &name, const QString &value);   // value, or "(set)" for anything that could hold a secret
QString shortList(const QString &text, int head, int tail);             // first/last lines with a gap marker

struct SpawnRecord {
    bool attempted = false, started = false, finished = false, crashed = false;
    QString program, workingDirectory, errorString, execProbe, stdoutFile;
    QStringList arguments;
    int processError = -1, exitCode = 0;
    QString signal;
    qint64 elapsedMs = -1;
};
QString execProbe(const QString &program, const QStringList &environment);   // posix_spawn errno text; Unix only
struct DiagContext {
    QString appDir, userDir, runDir, platform, launcherExe, stamp, graphicsDevice;
    LaunchSpec spec; bool haveSpec = false;
    QString prepareError;
    QStringList discPaths;
    SpawnRecord spawn;
    bool finished = false, full = false;   // full: also run lspci/vulkaninfo (slow)
};
struct DiagResult { QString text, path, latestPath; Verdict verdict; };
DiagResult buildDiagnostics(const DiagContext &ctx);
// Writes <userDir>/diagnostics/launch-diagnostics.txt, a timestamped copy (last 10 kept) and,
// when there is one, <runDir>/launch-diagnostics.txt.
DiagResult writeDiagnostics(const DiagContext &ctx);
void rotateReports(const QString &dir, int keep = 10);
QString diagnosticsDir(const QString &userDir);
QString gameProgramPath(const QString &appDir);
QStringList environmentDiff(const QProcessEnvironment &before, const QProcessEnvironment &after);
}
