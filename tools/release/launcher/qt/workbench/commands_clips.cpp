#include "commands.h"
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QMap>
#include <QProcess>
#include <QRegularExpression>
#include <QTemporaryDir>

namespace wb {
namespace {
using Tree = QMap<QString, QByteArray>;

bool metadata(const QString &rel) {
    return rel == ".workbench" || rel.startsWith(".workbench/") ||
           rel == ".git" || rel.startsWith(".git/");
}
void readTree(FileStore &reader, const QString &rel, Tree &tree) {
    QDir dir(QDir(reader.root()).filePath(rel));
    for (const auto &file : dir.entryInfoList(QDir::AllEntries | QDir::NoDotAndDotDot | QDir::Hidden | QDir::System,
                                               QDir::Name)) {
        const QString name = rel.isEmpty() ? file.fileName() : rel + '/' + file.fileName();
        if (metadata(name)) continue;
        if (file.isSymLink())
            throw CommandError{t("import source contains a symbolic link: %1",
                                 "import source contains a symbolic link: %1").arg(name)};
        if (file.isDir()) readTree(reader, name, tree);
        else if (file.isFile()) tree.insert(name, reader.read(name));
        else throw CommandError{t("import source is not a regular file: %1",
                                  "import source is not a regular file: %1").arg(name)};
    }
}
Tree readTree(const QString &root) {
    FileStore reader(root);
    Tree tree; readTree(reader, {}, tree); return tree;
}
bool builtOutput(const QString &rel, const QString &planPath, const QString &root) {
    if (rel == "package" || rel.startsWith("package/") || rel == "_build" || rel.startsWith("_build/"))
        return true;
    if (planPath.isEmpty()) return false;
    // GenoData exposes the path it actually resolved/read, including workspace-
    // relative plan_abs. Do not independently guess at its workspace-root rules.
    const auto normalized = [&root](const QString &name) {
        return QDir::cleanPath(QDir::fromNativeSeparators(QDir(root).absoluteFilePath(name)));
    };
#ifdef Q_OS_WIN
    constexpr auto sensitivity = Qt::CaseInsensitive;
#else
    constexpr auto sensitivity = Qt::CaseSensitive;
#endif
    return normalized(rel).compare(normalized(planPath), sensitivity) == 0;
}
void copyTree(const QString &root, const QString &staging, const Tree &tree) {
    for (auto it = tree.constBegin(); it != tree.constEnd(); ++it) {
        const auto target = QDir(staging).filePath(it.key());
        if (!QDir().mkpath(QFileInfo(target).absolutePath()))
            throw CommandError{t("cannot create import staging directory", "cannot create import staging directory")};
        QFile file(target);
        if (!file.open(QIODevice::WriteOnly) || file.write(it.value()) != it.value().size())
            throw CommandError{t("cannot stage import source: %1", "cannot stage import source: %1").arg(it.key())};
        file.close();
        file.setPermissions(QFileInfo(QDir(root).filePath(it.key())).permissions());
    }
}
QString expandArg(const QString &arg, const QMap<QString, QString> &values) {
    static const QRegularExpression placeholders(R"(\{(source|target|project|package|row)\})");
    QString result; qsizetype end = 0;
    auto matches = placeholders.globalMatch(arg);
    while (matches.hasNext()) {
        const auto match = matches.next();
        result += arg.mid(end, match.capturedStart() - end);
        result += values.value(match.captured(1));
        end = match.capturedEnd();
    }
    // A substituted source containing "{target}" is a literal filename. Never
    // expand placeholders inside already-substituted values.
    return result + arg.mid(end);
}
QJsonObject importClip(const QJsonObject &args, CommandContext &ctx) {
    auto &session = ctx.session;
    const auto project = session.data().project();
    const auto planPath = session.data().planPath();
    if (project.importClip.isEmpty() || project.importClip.first().isEmpty())
        throw CommandError{t("import_clip not configured", "import_clip not configured")};
    const QString source = args["source"].toString(), target = args["target_name"].toString();
    if (source.isEmpty())
        throw CommandError{t("source must not be empty", "source must not be empty")};
    static const QRegularExpression unsafeTarget(R"([\\/:*?"<>|])");
    if (target.isEmpty() || target == "." || target == ".." || target.contains(QChar(0)) ||
        target.contains(unsafeTarget))
        throw CommandError{t("invalid target_name", "invalid target_name")};
    if (args.contains("row")) needRow(session, args["row"].toString());
    ctx.propose |= args["propose"].toBool();
    const auto external = session.files().externalChanges();
    if (!external.isEmpty())
        throw CommandError{t("changed externally: %1", "changed externally: %1").arg(external.first())};

    const QString root = session.files().root();
    const Tree before = readTree(root);
    const auto scratch = QDir(root).filePath(".workbench");
    if (!QDir().mkpath(scratch))
        throw CommandError{t("cannot create import staging directory", "cannot create import staging directory")};
    QTemporaryDir staging(QDir(scratch).filePath("import-XXXXXX"));
    if (!staging.isValid())
        throw CommandError{t("cannot create import staging directory", "cannot create import staging directory")};
    copyTree(root, staging.path(), before);
    const QMap<QString, QString> values{{"source", QDir(root).absoluteFilePath(source)}, {"target", target},
        {"project", staging.path()}, {"package", QDir(staging.path()).filePath("package")},
        {"row", args["row"].toString()}};
    QStringList argv;
    for (const auto &arg : project.importClip) argv.append(expandArg(arg, values));
    QString program = argv.takeFirst();
    // A configured relative script/executable belongs to this project copy;
    // a plain program name (e.g. python) is resolved through PATH by QProcess.
    if (QDir::isRelativePath(program) && (program.contains('/') || program.contains('\\')))
        program = QDir(staging.path()).filePath(program);
    QProcess process;
    process.setWorkingDirectory(staging.path());
    process.setStandardInputFile(QProcess::nullDevice()); // Contract: no stdin.
    process.start(program, argv);
    if (!process.waitForStarted(5000))
        throw CommandError{t("cannot start import_clip: %1", "cannot start import_clip: %1").arg(process.errorString())};
    if (!process.waitForFinished(30000)) {
        process.kill(); process.waitForFinished(1000); // Only this subprocess.
        throw CommandError{t("import_clip timed out", "import_clip timed out")};
    }
    const QByteArray output = process.readAllStandardOutput().trimmed();
    if (process.exitStatus() != QProcess::NormalExit || process.exitCode() != 0)
        throw CommandError{t("import_clip exit %1: %2", "import_clip exit %1: %2")
            .arg(process.exitCode()).arg(QString::fromUtf8(process.readAllStandardError()).right(4000))};
    QJsonParseError parse;
    const auto doc = QJsonDocument::fromJson(output, &parse);
    if (output.size() > 64 * 1024 || parse.error != QJsonParseError::NoError || !doc.isObject())
        throw CommandError{t("import_clip stdout is not JSON", "import_clip stdout is not JSON")};
    auto result = doc.object();
    if (!result["clip"].isString() || result["clip"].toString().isEmpty())
        throw CommandError{t("import_clip JSON requires clip", "import_clip JSON requires clip")};
    intArg(result, "frames");
    if (!result.contains("frames"))
        throw CommandError{t("import_clip JSON requires frames", "import_clip JSON requires frames")};

    const Tree after = readTree(staging.path());
    // FileChange represents byte replacements/new files, not deletions.
    for (auto it = before.constBegin(); it != before.constEnd(); ++it)
        if (!after.contains(it.key()))
            throw CommandError{t("import_clip deleted source: %1", "import_clip deleted source: %1").arg(it.key())};
    QVector<FileChange> changes;
    for (auto it = after.constBegin(); it != after.constEnd(); ++it) {
        if (before.contains(it.key()) && before.value(it.key()) == it.value()) continue;
        if (builtOutput(it.key(), planPath, root))
            throw CommandError{t("import_clip changed built output: %1", "import_clip changed built output: %1").arg(it.key())};
        changes.append({it.key(), before.value(it.key()), it.value()});
    }
    const auto committed = session.commit(ctx, "import_clip", args,
        t("Import clip %1", "Import clip %1").arg(result["clip"].toString()), changes);
    for (const char *key : {"applied", "proposed", "entry", "note"}) result.remove(key);
    for (auto it = committed.constBegin(); it != committed.constEnd(); ++it) result[it.key()] = it.value();
    if (!committed["proposed"].toBool() && !committed["applied"].toBool()) {
        const auto error = session.data().reload();
        if (!error.isEmpty()) throw CommandError{error};
    }
    return result;
}
} // namespace

void registerClipCommands(Session &s) {
    s.registry().add({"list_clips", t("List available clips", "List available clips"), commandSchema(), false,
        [](const QJsonObject &, CommandContext &ctx) {
            QJsonArray clips;
            for (const auto &clip : ctx.session.data().clips())
                clips.append(QJsonObject{{"name", clip.name}, {"frames", clip.frames}});
            return QJsonObject{{"clips", clips}};
        }});
    s.registry().add({"preview_clip", t("Preview an animation clip", "Preview an animation clip"),
        commandSchema({{"clip", argType("string")}, {"frame", argType("integer")}}, {"clip"}), false,
        [](const QJsonObject &args, CommandContext &ctx) {
            needEngine(ctx.session);
            const auto clip = needClip(ctx.session, args["clip"].toString());
            const int frame = intArg(args, "frame");
            ctx.session.currentRow.clear();
            return engineCall(ctx.session, "clip", {{"clip", clip.name}, {"frame", frame}});
        }});
    s.registry().add({"assign_clip", t("Assign a clip to a move", "Assign a clip to a move"),
        commandSchema({{"row", argType("string")}, {"clip", argType("string")},
            {"crop_start", argType("integer")}, {"propose", argType("boolean")}}, {"row", "clip"}), true,
        [](const QJsonObject &args, CommandContext &ctx) {
            auto &session = ctx.session;
            std::optional<int> crop;
            if (args.contains("crop_start")) crop = intArg(args, "crop_start");
            ctx.propose |= args["propose"].toBool();
            QString error;
            const auto changes = session.data().assignClip(args["row"].toString(), args["clip"].toString(), crop, &error);
            if (!error.isEmpty()) throw CommandError{error};
            return session.commit(ctx, "assign_clip", args,
                t("Assign clip %1 to %2", "Assign clip %1 to %2")
                    .arg(args["clip"].toString(), args["row"].toString()), changes);
        }});
    s.registry().add({"import_clip", t("Import a retargeted clip", "Import a retargeted clip"),
        commandSchema({{"source", argType("string")}, {"target_name", argType("string")},
            {"row", argType("string")}, {"propose", argType("boolean")}}, {"source", "target_name"}), true, importClip});
}
} // namespace wb
