#include "project.h"
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <stdexcept>

namespace wb {
namespace {
[[noreturn]] void fail(const QString &message) {
    throw std::runtime_error(message.toUtf8().constData());
}
QString stringField(const QJsonObject &object, const QString &key) {
    const auto value = object.value(key);
    if (!value.isUndefined() && !value.isString())
        fail("workbench.json: " + key + " must be a string");
    return value.toString();
}
QString sourcePath(const QString &value) {
    if (value.isEmpty()) return {};
    QString error;
    const QString path = FileStore::safeRel(value, &error);
    if (!error.isEmpty()) fail("workbench.json: " + error);
    return path;
}
QStringList argvField(const QJsonObject &object, const QString &key) {
    const auto value = object.value(key);
    if (value.isUndefined()) return {};
    if (!value.isArray()) fail("workbench.json: " + key + " must be an array of strings");
    QStringList argv;
    for (const auto &arg : value.toArray()) {
        if (!arg.isString()) fail("workbench.json: " + key + " must be an array of strings");
        argv.append(arg.toString());
    }
    return argv;
}
} // namespace

ProjectConfig ProjectConfig::load(FileStore &fs, QString *err) {
    if (err) err->clear();
    try {
        if (!fs.exists("workbench.json"))
            fail("workbench.json not found in " + fs.root());
        QJsonParseError parseError;
        const auto document = QJsonDocument::fromJson(fs.read("workbench.json"), &parseError);
        if (parseError.error != QJsonParseError::NoError)
            fail(QString("workbench.json: %1 at offset %2").arg(parseError.errorString()).arg(parseError.offset));
        if (!document.isObject()) fail("workbench.json: expected an object");
        const auto object = document.object();
        if (object.value("schema").toString() != "workbench/1")
            fail("workbench.json: unsupported schema");
        ProjectConfig config;
        config.id = stringField(object, "id");
        config.gameplay = sourcePath(stringField(object, "gameplay"));
        if (config.gameplay.isEmpty()) fail("workbench.json: gameplay is required");
        config.movesDir = sourcePath(stringField(object, "moves_dir"));
        config.fidelity = sourcePath(stringField(object, "fidelity"));
        config.combo = sourcePath(stringField(object, "combo"));
        config.planAbs = stringField(object, "plan_abs");
        config.plan = stringField(object, "plan");
        // plan_abs deliberately overrides even an old project-relative plan path.
        if (config.planAbs.isEmpty()) config.plan = sourcePath(config.plan);
        if (config.planAbs.contains(QChar(0))) fail("workbench.json: invalid plan_abs path");
        config.artBlend = stringField(object, "art_blend");
        config.artGlb = stringField(object, "art_glb");
        if (config.artBlend.contains(QChar(0)) || config.artGlb.contains(QChar(0)))
            fail("workbench.json: invalid art path");
        config.modId = stringField(object, "mod_id");
        config.rebuild = argvField(object, "rebuild");
        config.importClip = argvField(object, "import_clip");
        return config;
    } catch (const std::exception &e) {
        if (err) *err = QString::fromUtf8(e.what());
        return {};
    }
}
} // namespace wb
