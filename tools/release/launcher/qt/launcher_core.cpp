#include "launcher_core.h"
#include "graphics.h"
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonParseError>
#include <QRegularExpression>
#include <QSaveFile>
#include <QSet>
#include <QStandardPaths>
#include <QTemporaryFile>
#include <QUuid>
#include <QtEndian>
#include <algorithm>
#include <functional>
#include <stdexcept>
#ifdef Q_OS_WIN
#include <windows.h>
#endif

namespace launcher {
static void fail(const QString &s) { throw std::runtime_error(s.toUtf8().constData()); }
static void ensureDir(const QString &s) { if (!QDir().mkpath(s)) fail("Cannot create folder: " + s); }
QString readText(const QString &path, qint64 limit) {
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly)) fail(path + ": " + f.errorString());
    if (f.size() > limit) fail("File is too large: " + path);
    return QString::fromUtf8(f.readAll());
}
void writeAtomic(const QString &path, const QByteArray &data) {
    ensureDir(QFileInfo(path).absolutePath());
    QSaveFile f(path);
    if (!f.open(QIODevice::WriteOnly) || f.write(data) != data.size() || !f.commit())
        fail(path + ": " + f.errorString());
}
static quint32 be32(const QByteArray &b, int offset) { return qFromBigEndian<quint32>(b.constData() + offset); }
static QString cstr(const QByteArray &b, int offset, int length) {
    auto s = b.mid(offset, length); int end = s.indexOf('\0');
    if (end >= 0) s.truncate(end);
    return QString::fromLatin1(s).trimmed();
}
DiscInfo probeDisc(const QString &path) {
    DiscInfo d;
    QFile f(path);
    auto bad = [&](const QString &s) { d.verdict = DiscInfo::Bad; d.message = s; return d; };
    if (!f.open(QIODevice::ReadOnly)) return bad(f.errorString());
    d.size = f.size(); auto h = f.read(0x440);
    if (h.startsWith("RVZ") || h.startsWith("WIA") || h.startsWith("CISO"))
        return bad("Compressed disc image. Convert it to ISO in Dolphin first.");
    if (h.size() != 0x440) return bad("The file is too small to be a GameCube disc image.");
    if (be32(h, 0x1c) != 0xc2339f3d)
        return bad(be32(h, 0x18) == 0x5d1c9ea3 ? "This is a Wii disc image." : "This is not a GameCube disc image.");
    d.gameId = QString::fromLatin1(h.left(6)); d.revision = quint8(h[7]);
    d.title = cstr(h, 0x20, 0x3e0);
    if (d.gameId != "GALE01" && d.gameId != "GTME01")
        return bad("Use Melee NTSC-U (USA), game ID GALE01, revision 1.02.");
    if (d.revision != 2) return bad("This revision is unsupported. Use Melee NTSC-U 1.02.");
    quint32 off = be32(h, 0x424), size = be32(h, 0x428);
    auto damaged = [&] { return bad("The disc file table is damaged or truncated. Dump the disc again."); };
    if (size < 12 || size > 16 * 1024 * 1024 || quint64(off) + size > quint64(d.size) || !f.seek(off)) return damaged();
    auto fst = f.read(size);
    if (fst.size() != size) return damaged();
    quint32 count = be32(fst, 8);
    if (!count || quint64(count) * 12 > size || quint8(fst[0]) != 1) return damaged();
    QSet<QString> names;
    for (quint32 i = 1; i < count; ++i) {
        quint32 word = be32(fst, i * 12), p = count * 12 + (word & 0xffffff);
        if (p >= size) return damaged();
        auto end = fst.indexOf('\0', p);
        if (end < 0) return damaged();
        if ((word >> 24) > 1) return damaged();
        if (word >> 24) {
            if (be32(fst, i * 12 + 8) <= i || be32(fst, i * 12 + 8) > count) return damaged();
        } else if (quint64(be32(fst, i * 12 + 4)) + be32(fst, i * 12 + 8) > quint64(d.size)) return damaged();
        names.insert(QString::fromLatin1(fst.mid(p, end - p)).toLower());
    }
    d.fileCount = int(count); d.verdict = DiscInfo::Good;
    if (names.contains("mxdt.dat")) {
        bool ace = false;
        for (const auto &m : {"altslippicss.dat", "efkxdata.dat", "efmkdata.dat", "efzxdata.dat"}) ace |= names.contains(m);
        if (ace) d.kind = "ACE (m-ex mod)";
        else if (d.title.contains("Akaneia", Qt::CaseInsensitive)) d.kind = "Akaneia (m-ex mod)";
        else { d.kind = "m-ex mod: " + d.title; d.verdict = DiscInfo::Warn; }
    } else if (d.title == "Super Smash Bros Melee" && count == 1212) d.kind = "Melee 1.02 (vanilla)";
    else {
        d.verdict = DiscInfo::Warn;
        d.kind = d.gameId == "GTME01" ? "Training Mode (TM-CE)" : "Melee 1.02 mod: " + d.title;
    }
    if (d.verdict == DiscInfo::Warn) d.message = "Modified disc. Features that patch the original game's code may not work. Tested packs: vanilla, ACE and Akaneia.";
    if (h.mid(0x200, 4) == "NKIT") { d.verdict = DiscInfo::Warn; d.message += " NKit image: restore to full ISO if loading fails."; }
    return d;
}
bool safeId(const QString &id) {
    static const QRegularExpression re("^[a-z0-9][a-z0-9._-]{0,63}$");
    return re.match(id).hasMatch();
}
QString Settings::option(const QString &key, const QString &fallback) const { return options.value(key).toString(fallback); }
bool Settings::flag(const QString &key, bool fallback) const { return option(key, fallback ? "1" : "0") == "1"; }
int Settings::defaultIndex() const {
    for (int i = 0; i < discs.size(); ++i) if (discs[i].id == defaultId) return i;
    return discs.isEmpty() ? -1 : 0;
}
Settings Settings::load(const QString &dir) {
    Settings s;
    QString jsonPath = dir + "/launcher.json", legacyPath = dir + "/launcher.cfg";
    if (QFile::exists(jsonPath)) {
        QJsonParseError error;
        auto doc = QJsonDocument::fromJson(readText(jsonPath).toUtf8(), &error);
        if (error.error != QJsonParseError::NoError || !doc.isObject() || doc["format"].toInt() != 1)
            fail("Invalid launcher settings: " + jsonPath);
        auto obj = doc.object(); s.options = obj["options"].toObject(); s.defaultId = obj["default"].toString();
        for (const auto &v : obj["discs"].toArray()) {
            auto d = v.toObject(); s.discs.append({d["id"].toString(), d["name"].toString(), d["kind"].toString(), d["path"].toString()});
        }
    } else if (QFile::exists(legacyPath)) {
        for (auto line : readText(legacyPath).split('\n')) {
            line = line.trimmed(); if (line.startsWith('#')) continue;
            int eq = line.indexOf('='); if (eq < 0) continue;
            auto k = line.left(eq).trimmed(), v = line.mid(eq + 1).trimmed();
            if (k == "default") s.defaultId = v;
            else if (k == "disc") {
                auto p = v.split('|');
                if (p.size() < 4) fail("Invalid disc record in " + legacyPath);
                s.discs.append({p[0], p[1], p[2], p.mid(3).join('|')});
            } else s.options[k] = v;
        }
    }
    QSet<QString> ids;
    for (const auto &d : s.discs) {
        if (!safeId(d.id) || ids.contains(d.id) || d.path.isEmpty()) fail("Invalid or duplicate disc ID in launcher settings.");
        ids.insert(d.id);
    }
    return s;
}
void Settings::save(const QString &dir) const {
    QJsonArray list;
    for (const auto &d : discs) list.append(QJsonObject{{"id", d.id}, {"name", d.name}, {"kind", d.kind}, {"path", d.path}});
    writeAtomic(dir + "/launcher.json", QJsonDocument(QJsonObject{{"format", 1}, {"default", defaultId}, {"options", options}, {"discs", list}}).toJson());
}
QString Settings::newId(const QString &name) const {
    auto stem = name.toLower().replace(QRegularExpression("[^a-z0-9]+"), "-").left(24);
    stem.remove(QRegularExpression("^-+|-+$")); if (stem.isEmpty()) stem = "disc";
    auto candidate = stem;
    for (int n = 2; std::any_of(discs.begin(), discs.end(), [&](const Disc &d) { return d.id == candidate; }); ++n) candidate = stem + "-" + QString::number(n);
    return candidate;
}
static bool writable(const QString &path) {
    if (!QDir().mkpath(path)) return false;
    QTemporaryFile probe(path + "/.launcher-write-XXXXXX"); return probe.open();
}
QString pickUserDir(const QString &appDir, const QString &overrideDir) {
    if (!overrideDir.isEmpty()) {
        auto path = QFileInfo(overrideDir).absoluteFilePath();
        if (!writable(path)) fail("Cannot write user data: " + path);
        return path;
    }
    const auto portable = appDir + "/userdata";
#ifdef Q_OS_WIN
    if (writable(portable)) return portable;
    const auto fallback = QStandardPaths::writableLocation(QStandardPaths::GenericDataLocation) + "/GDMelee";
#else
    if (QDir(portable).exists() && writable(portable)) return portable;
    const auto fallback = QStandardPaths::writableLocation(QStandardPaths::GenericDataLocation) + "/melee-linux";
#endif
    if (!writable(fallback)) fail("Cannot write user data: " + fallback);
    return fallback;
}
QString modsDir(const QString &appDir, const QString &userDir) {
    return QDir(appDir + "/mods").exists() ? appDir + "/mods" : userDir + "/mods";
}
static QStringList strings(const QJsonValue &v) {
    QStringList out; for (const auto &s : v.toArray()) out << s.toString(); return out;
}
QVector<Mod> installedMods(const QString &dir) {
    QSet<QString> enabled;
    const bool all = !QFile::exists(dir + "/enabled.txt");
    if (!all) for (auto line : readText(dir + "/enabled.txt").split('\n')) {
        line.remove(QChar(0xfeff));
        line = line.section('#', 0, 0).trimmed().toLower();
        if (!line.isEmpty()) enabled.insert(line);
    }
    QVector<Mod> result;
    for (const auto &f : QDir(dir).entryInfoList(QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name)) {
        auto id = f.fileName(); if (!safeId(id) || id == "targettest" || f.isSymLink()) continue;
        QJsonObject obj;
        if (QFile::exists(f.filePath() + "/mod.json")) {
            QJsonParseError error;
            auto doc = QJsonDocument::fromJson(readText(f.filePath() + "/mod.json").toUtf8(), &error);
            if (error.error != QJsonParseError::NoError || !doc.isObject()) fail("Invalid mod.json in " + f.filePath());
            obj = doc.object();
        }
        result.append({id, obj["name"].toString(id), obj["version"].toString(), obj["description"].toString(), strings(obj["requires"]), strings(obj["conflicts"]), all || enabled.contains(id)});
    }
    return result;
}
static QSet<QString> cyclicMods(const QVector<Mod> &mods, const QSet<QString> &selected) {
    QMap<QString, QStringList> requirements;
    for (const auto &m : mods) if (selected.contains(m.id)) requirements[m.id] = m.requires;
    QMap<QString, int> state;
    QStringList stack;
    QSet<QString> cycles;
    std::function<void(const QString &)> visit = [&](const QString &id) {
        if (!selected.contains(id) || state.value(id) == 2) return;
        if (state.value(id) == 1) {
            for (int i = stack.indexOf(id); i < stack.size(); ++i) cycles.insert(stack[i]);
            return;
        }
        state[id] = 1; stack.append(id);
        for (const auto &r : requirements.value(id)) visit(r);
        stack.removeLast(); state[id] = 2;
    };
    for (auto i = requirements.begin(); i != requirements.end(); ++i) visit(i.key());
    return cycles;
}
void setModEnabled(const QString &dir, const QString &id, bool on) {
    auto mods = installedMods(dir); QSet<QString> selected; bool found = false;
    for (const auto &m : mods) { if (m.enabled) selected.insert(m.id); found |= m.id == id; }
    if (!found) fail("Unknown mod: " + id);
    const auto cycles = cyclicMods(mods, selected);
    if (!on && cycles.contains(id)) {
        // No member of a requirement cycle can mount. Let the user recover
        // an invalid default/all-enabled selection without hand-editing it.
        selected.subtract(cycles);
        bool changed;
        do {
            changed = false;
            for (const auto &m : mods) if (selected.contains(m.id)) {
                for (const auto &r : m.requires) if (!selected.contains(r)) {
                    selected.remove(m.id); changed = true; break;
                }
            }
        } while (changed);
    }
    if (on) selected.insert(id); else selected.remove(id);
    auto remainingCycles = cyclicMods(mods, selected).values(); remainingCycles.sort();
    if (!remainingCycles.isEmpty()) fail("Mod requirement cycle: " + remainingCycles.join(", "));
    for (const auto &m : mods) if (selected.contains(m.id)) {
        for (const auto &r : m.requires) if (!selected.contains(r)) fail(m.id + " requires enabled mod " + r);
        for (const auto &c : m.conflicts) if (selected.contains(c)) fail(m.id + " conflicts with " + c);
    }
    auto sorted = selected.values(); sorted.sort();
    writeAtomic(dir + "/enabled.txt", ("# Enabled mods for the next launch\n" + sorted.join('\n') + "\n").toUtf8());
}
void removeMod(const QString &dir, const QString &id) {
    if (!safeId(id)) fail("Invalid mod ID");
    const auto path = dir + "/" + id;
    if (QFileInfo(path).isSymLink()) fail("Refusing to remove a linked mod folder.");
    setModEnabled(dir, id, false);
    // Move to a local trash folder so a mistaken removal is recoverable.
    const auto trash = dir + "/.removed"; ensureDir(trash);
    if (!QDir().rename(path, trash + "/" + id + "-" + QUuid::createUuid().toString(QUuid::WithoutBraces))) fail("Cannot move mod to .removed: " + path);
}
static QString gamePath(QString path) {
#ifdef Q_OS_WIN
    if (path.toLatin1() != path.toUtf8()) {
        wchar_t buf[32768]; auto n = GetShortPathNameW(reinterpret_cast<LPCWSTR>(path.utf16()), buf, 32768);
        if (n && n < 32768) path = QString::fromWCharArray(buf, n);
    }
#endif
    return QDir::toNativeSeparators(path);
}
QString gameLibraryPath(const QString &appDir, const QString &inheritedPath) {
    QStringList out{appDir + "/lib"};
    const auto launcherLib = QDir::cleanPath(appDir + "/launcher/lib");
    for (const auto &entry : inheritedPath.split(':', Qt::SkipEmptyParts)) {
        const auto clean = QDir::cleanPath(entry);
        if (clean == launcherLib || clean.startsWith(launcherLib + "/") || out.contains(clean)) continue;
        out << clean;
    }
    return out.join(':');
}
void applyGameLibraryEnvironment(QProcessEnvironment &env, const QString &appDir) {
    const auto inherited = env.value("LD_LIBRARY_PATH");
    const auto preload = env.value("MELEE_GAME_LD_PRELOAD");
    env.remove("QT_PLUGIN_PATH"); env.remove("QT_QPA_PLATFORM_PLUGIN_PATH"); env.remove("LD_PRELOAD");
    env.remove("MELEE_GAME_LD_PRELOAD");
    if (!preload.isEmpty()) env.insert("LD_PRELOAD", preload);
    env.insert("LD_LIBRARY_PATH", gameLibraryPath(appDir, inherited));
}
LaunchSpec prepareLaunch(const QString &app, const QString &user, const Settings &s, const Disc &disc) {
    if (!safeId(disc.id)) fail("Invalid disc ID");
    auto check = probeDisc(disc.path); if (check.verdict == DiscInfo::Bad) fail(check.message);
    LaunchSpec spec;
#ifdef Q_OS_WIN
    spec.program = app + "/melee-pc.exe";
#else
    spec.program = app + "/bin/melee";
    if (!QFile::exists(spec.program)) spec.program = app + "/melee";
#endif
    if (!QFileInfo(spec.program).isExecutable()) fail("Game executable is missing or not executable: " + spec.program);
    auto ui = app + "/assets/ui"; if (!QDir(ui).exists()) ui = app + "/ui";
    if (!QFile::exists(ui + "/manifest.json")) fail("Game UI assets are missing: " + ui);
    spec.workingDirectory = user + "/runs/" + QUuid::createUuid().toString(QUuid::WithoutBraces);
    auto card = user + "/saves/" + disc.id;
    ensureDir(card); ensureDir(spec.workingDirectory);
    ensureDir(user + "/scripts"); ensureDir(user + "/scripts-data"); ensureDir(user + "/config");
    ensureDir(modsDir(app, user));
    auto env = QProcessEnvironment::systemEnvironment();
    // Launcher state controls each boot. Do not inherit a developer's previous scene or network session.
    for (const auto &key : env.keys()) if (key.startsWith("MELEE_NET") || key.startsWith("MELEE_SLIPPI") || key.startsWith("MELEE_SCENE") || key == "MELEE_SCRIPT" || key == "MELEE_TRAINING") env.remove(key);
    for (const auto &key : {"MELEE_INPUT", "MELEE_KEYBOARD_PORT", "MELEE_CONSOLE_PORT"}) env.remove(key);
    auto setPath = [&](const QString &key, const QString &value) { env.insert(key, gamePath(value)); };
    setPath("MELEE_CARD_PATH", card); setPath("MELEE_SETTINGS_CFG", user + "/config/settings.cfg");
    setPath("MELEE_MODS_DIR", modsDir(app, user)); setPath("MELEE_SCRIPTS_DIR", QDir(app + "/scripts").exists() ? app + "/scripts" : user + "/scripts");
    setPath("MELEE_SCRIPT_DATA_DIR", user + "/scripts-data"); setPath("MELEE_CACHE_DIR", spec.workingDirectory + "/cache");
    ensureDir(spec.workingDirectory + "/cache");
    setPath("MELEE_MENUTEX_DIR", ui); setPath("MELEE_FONT_DIR", app + "/assets/fonts");
    env.insert("MELEE_VOLUME", QString::number(std::clamp(s.option("volume", "50").toInt(), 0, 100)));
    for (const auto &pair : {qMakePair("unlock_all", "MELEE_UNLOCK_ALL"), qMakePair("skip_intro", "MELEE_SKIP_INTRO")}) {
        if (s.flag(pair.first, true)) env.insert(pair.second, "1"); else env.remove(pair.second);
    }
    QStringList log;
    if (s.flag("log_all")) log << "all"; else log = s.option("log_categories").split(',', Qt::SkipEmptyParts);
    int render = s.option("log_render", "0").toInt();
    if (render < 0) log << "-render"; else if (render > 0) log << "render";
    if (!s.flag("log_scene", true)) log << "-scene";
    if (log.isEmpty()) env.remove("MELEE_LOG"); else env.insert("MELEE_LOG", log.join(','));
    for (const auto &pair : {qMakePair("heap", "MELEE_HEAP_TRACE"), qMakePair("dvd", "MELEE_DVD_TRACE")}) {
        if (s.flag("log_all") || log.contains(pair.first)) env.insert(pair.second, "1"); else env.remove(pair.second);
    }
    for (const auto &pair : {qMakePair("pad_diag", "MELEE_PAD_DIAG"), qMakePair("pad_release_on_blur", "MELEE_PAD_RELEASE_ON_BLUR")}) {
        int v = s.option(pair.first, "-1").toInt(); if (v >= 0) env.insert(pair.second, QString::number(v)); else env.remove(pair.second);
    }
    static const QMap<QString, QString> traces = {{"gr", "MELEE_GR_TRACE"}, {"mexcalls", "MELEE_MEX_TRACE_CALLS"}, {"card", "MELEE_CARD_DIAG"}, {"profile", "MELEE_PROFILE"}, {"fps", "MELEE_SHOW_FPS"}, {"aurora", "MELEE_AURORA_VERBOSE"}, {"osreport", "MELEE_PC_TRACE_OSREPORT"}};
    auto selected = s.option("traces").split(',');
    for (auto i = traces.begin(); i != traces.end(); ++i) { if (selected.contains(i.key())) env.insert(i.value(), "1"); else env.remove(i.value()); }
#ifndef Q_OS_WIN
    // The 64-bit Qt runtime must never enter the 32-bit game's library search path.
    applyGameLibraryEnvironment(env, app);
    env = graphicsEnvironment(env, s.option("graphics_device", "auto"));
#endif
    spec.environment = env; spec.arguments = {"--iso", gamePath(QFileInfo(disc.path).absoluteFilePath())};
    spec.logFile = spec.workingDirectory + "/launcher-process.log";
    return spec;
}
QString latestCrash(const QString &runDir) {
    auto files = QDir(runDir + "/crashlogs").entryInfoList({"crash-*.log"}, QDir::Files, QDir::Time);
    for (const auto &f : files) if (!f.fileName().endsWith("-full.log")) {
        QFile report(f.filePath()); if (!report.open(QIODevice::ReadOnly)) continue;
        auto head = report.read(2048);
        if (head.startsWith("==== GD's Melee crash report ====") && !head.contains("during shutdown: yes")) return f.filePath();
    }
    return {};
}
}
