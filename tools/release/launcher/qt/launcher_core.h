#pragma once
#include <QJsonObject>
#include <QProcessEnvironment>
#include <QStringList>
#include <QVector>

namespace launcher {
struct DiscInfo {
    enum Verdict { Bad, Warn, Good } verdict = Bad;
    QString gameId, title, kind, message;
    int revision = -1, fileCount = 0;
    qint64 size = 0;
};
DiscInfo probeDisc(const QString &path);
struct Disc { QString id, name, kind, path; };
struct Settings {
    QVector<Disc> discs;
    QJsonObject options;
    QString defaultId;
    static Settings load(const QString &userDir);
    void save(const QString &userDir) const;
    QString option(const QString &key, const QString &fallback = {}) const;
    bool flag(const QString &key, bool fallback = false) const;
    QString newId(const QString &name) const;
    int defaultIndex() const;
};
bool safeId(const QString &id);
QString pickUserDir(const QString &appDir, const QString &overrideDir = {});
QString modsDir(const QString &appDir, const QString &userDir);
struct Mod {
    QString id, name, version, description;
    QStringList requires, conflicts;
    bool enabled = false;
};
QVector<Mod> installedMods(const QString &dir);
void setModEnabled(const QString &dir, const QString &id, bool enabled);
void removeMod(const QString &dir, const QString &id);
struct LaunchSpec {
    QString program, workingDirectory, logFile;
    QStringList arguments;
    QProcessEnvironment environment;
};
LaunchSpec prepareLaunch(const QString &appDir, const QString &userDir,
                         const Settings &settings, const Disc &disc);
// The 32-bit game's environment on Linux. The launcher keeps its own Qt hygiene (its x86-64 Qt folder and
// plugin paths never reach the game; neither does a stray LD_PRELOAD, which is nearly always a 64-bit
// overlay), but it no longer discards the player's own library path: the game's lib/ comes first, then
// whatever LD_LIBRARY_PATH the launcher was started with, minus the launcher's own launcher/lib that the
// GD-Melee wrapper adds. A player who needs a preload for the game sets MELEE_GAME_LD_PRELOAD.
QString gameLibraryPath(const QString &appDir, const QString &inheritedPath);
void applyGameLibraryEnvironment(QProcessEnvironment &env, const QString &appDir);
QString latestCrash(const QString &runDir);
void writeAtomic(const QString &path, const QByteArray &data);
QString readText(const QString &path, qint64 limit = 1024 * 1024);
}
