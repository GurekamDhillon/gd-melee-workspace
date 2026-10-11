#include "game_exe.h"
#include "commands.h"
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QRegularExpression>
#include <algorithm>

namespace wb {
namespace {
#ifdef Q_OS_WIN
const char *kGameName = "melee-pc.exe";
#else
const char *kGameName = "melee-pc";
#endif
QString dotenvValue(const QString &root, const QString &key) {
    QFile file(QDir(root).filePath(".env"));
    if (!file.open(QIODevice::ReadOnly)) return {};
    const auto lines = QString::fromUtf8(file.readAll()).split('\n');
    for (QString line : lines) {
        line = line.trimmed();
        if (line.startsWith("export ")) line = line.mid(7).trimmed();
        if (line.startsWith('#') || !line.startsWith(key + "=")) continue;
        QString value = line.mid(key.size() + 1).trimmed();
        if (value.size() >= 2 && (value.startsWith('"') || value.startsWith('\'')) && value.endsWith(value[0])) value = value.mid(1, value.size() - 2);
        return value;
    }
    return {};
}
QString jsonToolPath(const QString &root, const QString &key) {
    QFile file(QDir(root).filePath("_build/tools.json"));
    if (!file.open(QIODevice::ReadOnly)) return {};
    const auto value = QJsonDocument::fromJson(file.readAll()).object().value("paths").toObject().value(key).toString();
    if (value.isEmpty()) return {};
    return QDir::cleanPath(QDir::isAbsolutePath(value) ? value : QDir(root).filePath(value));
}
}
QString workspaceRootOf(const QString &projectDir, const QProcessEnvironment &env) {
    const auto explicitRoot = env.value("GW_ROOT").trimmed();
    if (!explicitRoot.isEmpty() && QFileInfo(explicitRoot).isDir()) return QDir::cleanPath(explicitRoot);
    if (projectDir.isEmpty() || !QFileInfo(projectDir).isDir()) return {};
    QString gitRoot;
    for (QDir dir(QFileInfo(projectDir).absoluteFilePath()); ; ) {
        if (QFileInfo::exists(dir.filePath(".env"))) return dir.absolutePath();
        if (gitRoot.isEmpty() && QFileInfo::exists(dir.filePath(".git"))) gitRoot = dir.absolutePath();
        if (!dir.cdUp()) break;
    }
    return gitRoot;
}
GameExe resolveGameExe(const QString &setting, const QProcessEnvironment &env,
                       const QString &projectDir, const QString &appDir) {
    if (!setting.trimmed().isEmpty()) return {QDir::fromNativeSeparators(setting.trimmed()), t("Settings (Game exe)", "Ajustes (ejecutable del juego)"), {}};
    const auto fromEnv = env.value("GW_ENGINE_EXE").trimmed();
    if (!fromEnv.isEmpty()) return {QDir::fromNativeSeparators(fromEnv), "GW_ENGINE_EXE", {}};
    const auto root = workspaceRootOf(projectDir, env);
    QStringList tried;
    if (!projectDir.isEmpty()) {
        QFile file(QDir(projectDir).filePath("workbench.json"));
        if (file.open(QIODevice::ReadOnly)) {
            const auto engine = QJsonDocument::fromJson(file.readAll()).object().value("engine").toString().trimmed();
            if (!engine.isEmpty()) {
                QStringList options;
                if (QDir::isAbsolutePath(engine)) options << engine;
                else { options << QDir(projectDir).filePath(engine); if (!root.isEmpty()) options << QDir(root).filePath(engine); }
                for (const auto &option : options) {
                    const auto clean = QDir::cleanPath(option); tried << clean;
                    if (QFileInfo(clean).isFile()) return {clean, "workbench.json engine", {}};
                }
            }
        }
    }
    if (!root.isEmpty()) {
        const auto built = QDir(root).filePath(QString("_build/") + kGameName); tried << built;
        if (QFileInfo(built).isFile()) return {QDir::cleanPath(built), t("workspace _build", "_build del espacio de trabajo"), {}};
    }
    if (!appDir.isEmpty()) {
        const auto beside = QDir(appDir).filePath(kGameName); tried << beside;
        if (QFileInfo(beside).isFile()) return {QDir::cleanPath(beside), t("beside the launcher", "junto al lanzador"), {}};
    }
    return {{}, {}, t("Game executable not found. Set Game exe in Settings or GW_ENGINE_EXE. Looked in: %1",
                      "No se encontró el ejecutable del juego. Define Game exe en Ajustes o GW_ENGINE_EXE. Se buscó en: %1").arg(tried.join(", "))};
}
QString discoverBlender(const QString &projectDir, const QProcessEnvironment &env) {
    if (env.value("GW_BLENDER_DISCOVERY") == "0") return {}; // tests and locked-down setups
    const auto root = workspaceRootOf(projectDir, env);
    auto good = [](const QString &p) { return !p.isEmpty() && QFileInfo(p).isFile(); };
    if (!root.isEmpty()) {
        auto fromEnv = dotenvValue(root, "GW_BLENDER");
        if (!fromEnv.isEmpty()) { fromEnv = QDir::cleanPath(QDir::isAbsolutePath(fromEnv) ? fromEnv : QDir(root).filePath(fromEnv)); if (good(fromEnv)) return fromEnv; }
        const auto cached = jsonToolPath(root, "GW_BLENDER"); if (good(cached)) return cached;
    }
    // Blender Foundation installs, newest 4.x+ first.
    QList<QPair<QList<int>, QString>> found;
    for (const char *key : {"ProgramFiles", "LOCALAPPDATA"}) {
        const auto base = env.value(key); if (base.isEmpty()) continue;
        const QDir foundation(QString(key) == "LOCALAPPDATA" ? base + "/Programs/Blender Foundation" : base + "/Blender Foundation");
        for (const auto &name : foundation.entryList({"Blender *"}, QDir::Dirs)) {
            QList<int> version;
            auto matches = QRegularExpression("[0-9]+").globalMatch(name);
            while (matches.hasNext()) version << matches.next().captured().toInt();
            const auto exe = foundation.filePath(name + "/blender.exe");
            if (!version.isEmpty() && version[0] >= 4 && good(exe)) found.append({version, exe});
        }
    }
    std::sort(found.begin(), found.end(), [](const auto &a, const auto &b) { return a.first > b.first; });
    if (!found.isEmpty()) return found.first().second;
    const auto steamBase = env.value("ProgramFiles(x86)");
    if (!steamBase.isEmpty()) {
        const QString steam = steamBase + "/Steam";
        QStringList libraries{steam};
        QFile vdf(steam + "/steamapps/libraryfolders.vdf");
        if (vdf.open(QIODevice::ReadOnly)) {
            const auto text = QString::fromUtf8(vdf.readAll());
            auto matches = QRegularExpression(R"re("path"\s*"((?:\\.|[^"\\])*)")re").globalMatch(text);
            while (matches.hasNext()) {
                auto library = matches.next().captured(1); library.replace("\\\\", "\\").replace("\\\"", "\"");
                if (QDir::isAbsolutePath(library)) libraries << library;
            }
        }
        for (const auto &library : libraries) {
            const auto exe = library + "/steamapps/common/Blender/blender.exe";
            if (good(exe)) return QDir::cleanPath(exe);
        }
    }
    return {};
}
}
