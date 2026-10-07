#include "window.h"
#include "diagnostics.h"
#include "legacy_kit.h"
#include <QApplication>
#include <QDateTime>
#include <QElapsedTimer>
#include <QGuiApplication>
#include <QCommandLineParser>
#include <QDir>
#include <QFileInfo>
#include <QJsonDocument>
#include <QLocale>
#include <QMessageBox>
#include <QTextStream>
#include <QTimer>

int main(int argc, char **argv) {
    QApplication app(argc, argv);
    app.setApplicationName("GD Melee"); app.setApplicationVersion("1.0"); app.setOrganizationName("GDMelee");
    app.setQuitOnLastWindowClosed(false);
    launcher::legacy::initialize();
    QCommandLineParser parser; parser.setApplicationDescription("GD's Melee portable offline launcher"); parser.addHelpOption(); parser.addVersionOption();
    parser.addOptions({{"app-dir", "Game installation directory", "path"}, {"data-dir", "User settings and saves directory", "path"},
                       {"lang", "Launcher language: auto, en, es", "language"}, {"add-iso", "Add a disc image", "path"},
                       {"probe", "Inspect a disc and print JSON, without changing settings", "path"},
                       {"play", "Launch the default or named disc without the window"}, {"forget-all", "Forget discs; keep their saves"},
                       {"mods", "Open the installed mods tab"}, {"list-mods", "List installed mods"},
                       {"enable-mod", "Enable an installed mod", "id"}, {"disable-mod", "Disable an installed mod", "id"},
                       {"shots", "Render each tab to PNG and exit", "directory"}, {"diagnose", "Write launch diagnostics without starting the game, print their path and verdict, and exit"}, {"test-game", "With --play, run the engine test suite and return its exit code"}});
    parser.addPositionalArgument("disc", "Disc name or ID for --play", "[disc]"); parser.process(app);
    const bool cli = parser.isSet("probe") || parser.isSet("play") || parser.isSet("list-mods") || parser.isSet("enable-mod") || parser.isSet("disable-mod") || parser.isSet("shots") || parser.isSet("diagnose");
    try {
        if (parser.isSet("probe")) {
            auto d = launcher::probeDisc(parser.value("probe"));
            QTextStream(stdout) << QJsonDocument(QJsonObject{{"accepted", d.verdict != launcher::DiscInfo::Bad}, {"warning", d.verdict == launcher::DiscInfo::Warn}, {"kind", d.kind}, {"message", d.message}, {"game_id", d.gameId}, {"revision", d.revision}, {"files", d.fileCount}}).toJson();
            return d.verdict == launcher::DiscInfo::Bad ? 1 : 0;
        }
        QString root = parser.value("app-dir");
        if (root.isEmpty()) {
            root = app.applicationDirPath();
            // Packaged layout: <game>/launcher/bin/gd-melee-launcher.
            QDir parent(root);
            if (parent.dirName() == "bin" && parent.cdUp() && parent.dirName() == "launcher" && parent.cdUp()) root = parent.absolutePath();
        }
        root = QDir::cleanPath(QFileInfo(root).absoluteFilePath());
        auto user = launcher::pickUserDir(root, parser.value("data-dir")); auto settings = launcher::Settings::load(user);
        auto lang = parser.isSet("lang") ? parser.value("lang") : settings.option("language", "auto");
        launcher::spanish = lang == "es" || (lang == "auto" && QLocale::system().language() == QLocale::Spanish);
        if (parser.isSet("forget-all")) { settings.discs.clear(); settings.defaultId.clear(); settings.save(user); }
        if (parser.isSet("add-iso")) {
            auto path = QFileInfo(parser.value("add-iso")).absoluteFilePath(); auto info = launcher::probeDisc(path);
            if (info.verdict == launcher::DiscInfo::Bad) throw std::runtime_error(info.message.toUtf8().constData());
            if (info.verdict == launcher::DiscInfo::Warn) QTextStream(stderr) << info.message << '\n';
            bool exists = false;
            for (const auto &d : settings.discs) if (QFileInfo(d.path).canonicalFilePath() == QFileInfo(path).canonicalFilePath()) { settings.defaultId = d.id; exists = true; }
            if (!exists) { auto id = settings.newId(info.kind); settings.discs.append({id, info.kind, info.kind, path}); settings.defaultId = id; }
            settings.save(user);
        }
        auto diagContext = [&](bool full) {
            launcher::DiagContext c; c.appDir = root; c.userDir = user; c.full = full; c.platform = QGuiApplication::platformName(); c.launcherExe = QCoreApplication::applicationFilePath();
            for (const auto &d : settings.discs) c.discPaths << d.path;
            return c;
        };
        if (parser.isSet("diagnose")) {
            auto c = diagContext(true); c.finished = true;
            auto report = launcher::writeDiagnostics(c);
            QTextStream(stdout) << "VERDICT: " << report.verdict.line() << Qt::endl << report.verdict.message << Qt::endl << "Report: " << report.latestPath << Qt::endl;
            return 0;
        }
        auto mods = launcher::modsDir(root, user);
        for (const auto &key : {"enable-mod", "disable-mod"}) if (parser.isSet(key)) { launcher::setModEnabled(mods, parser.value(key), QString(key) == "enable-mod"); return 0; }
        if (parser.isSet("list-mods")) { for (const auto &m : launcher::installedMods(mods)) QTextStream(stdout) << (m.enabled ? "+ " : "- ") << m.id << '\t' << m.version << '\t' << m.name << '\n'; return 0; }
        if (parser.isSet("play")) {
            int index = settings.defaultIndex();
            if (!parser.positionalArguments().isEmpty()) {
                index = -1; auto name = parser.positionalArguments().join(' ');
                for (int i = 0; i < settings.discs.size(); ++i) if (settings.discs[i].id == name || settings.discs[i].name == name) { index = i; break; }
            }
            if (index < 0) throw std::runtime_error("No matching disc. Add one with --add-iso first.");
            launcher::LaunchSpec spec;
            try { spec = launcher::prepareLaunch(root, user, settings, settings.discs[index]); }
            catch (const std::exception &e) {
                auto c = diagContext(true); c.prepareError = QString::fromUtf8(e.what()); c.finished = true;
                auto report = launcher::writeDiagnostics(c);
                QTextStream(stderr) << "Launch diagnostics: " << report.latestPath << " (" << report.verdict.line() << ")" << Qt::endl;
                throw;
            }
            if (parser.isSet("test-game")) {
#ifndef Q_OS_WIN
                // Engine tests write fixtures next to their executable. Run a
                // session copy so packaged installations can remain read-only.
                auto testProgram = spec.workingDirectory + "/" + QFileInfo(spec.program).fileName();
                auto map = QFileInfo(spec.program).dir().filePath("melee-pc.msvc.map");
                if (!QFile::copy(spec.program, testProgram) || !QFile::copy(map, spec.workingDirectory + "/melee-pc.msvc.map"))
                    throw std::runtime_error("Cannot prepare isolated engine test executable");
                spec.program = testProgram;
                auto tempDir = spec.workingDirectory + "/tmp";
                if (!QDir().mkpath(tempDir)) throw std::runtime_error("Cannot prepare isolated test temporary directory");
                spec.environment.insert("TMPDIR", tempDir);
#endif
                spec.arguments.prepend("--test");
            }
            settings.options["last_run"] = spec.workingDirectory; settings.save(user);
            QProcess process; process.setProgram(spec.program); process.setArguments(spec.arguments); process.setWorkingDirectory(spec.workingDirectory); process.setProcessEnvironment(spec.environment);
            launcher::captureRedacted(process, spec.logFile, launcher::redactorForLaunch(spec.arguments));
            QTextStream(stdout) << "Logs: " << spec.workingDirectory << Qt::endl;
            QObject::connect(&process, &QProcess::errorOccurred, &app, [&](QProcess::ProcessError error) { if (error == QProcess::FailedToStart) { QTextStream(stderr) << process.errorString() << '\n'; app.exit(1); } });
            QObject::connect(&process, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), &app, [&](int code, QProcess::ExitStatus status) { app.exit(status == QProcess::CrashExit ? 1 : code); });
            auto context = diagContext(true); context.spec = spec; context.haveSpec = true; context.runDir = spec.workingDirectory; context.stamp = QDateTime::currentDateTime().toString("yyyyMMdd-HHmmss");
            context.spawn.attempted = true; context.spawn.program = spec.program; context.spawn.arguments = spec.arguments; context.spawn.workingDirectory = spec.workingDirectory; context.spawn.stdoutFile = spec.logFile;
            QElapsedTimer clock; clock.start();
            auto finish = [&] {
                auto report = launcher::writeDiagnostics(context);
                QTextStream(stdout) << "Launch diagnostics: " << report.latestPath << " (" << report.verdict.line() << ")" << Qt::endl;
            };
            QObject::connect(&process, &QProcess::started, &app, [&] { context.spawn.started = true; });
            QObject::connect(&process, &QProcess::errorOccurred, &app, [&](QProcess::ProcessError error) {
                if (error != QProcess::FailedToStart) return;
                context.spawn.processError = int(error); context.spawn.errorString = process.errorString();
                QStringList env; for (const auto &k : spec.environment.keys()) env << k + "=" + spec.environment.value(k);
                context.spawn.execProbe = launcher::execProbe(spec.program, env); context.finished = true; finish();
            });
            QObject::connect(&process, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), &app, [&](int code, QProcess::ExitStatus status) {
                auto &sp = context.spawn; sp.finished = true; sp.exitCode = code; sp.crashed = status == QProcess::CrashExit; sp.elapsedMs = clock.elapsed();
                if (sp.crashed && code >= 1 && code <= 64) sp.signal = launcher::signalName(code);
                context.finished = true; finish();
            });
            process.start(); return app.exec();
        }
        launcher::Window window(root, user, settings); if (parser.isSet("mods")) window.selectMods(); window.show();
        if (parser.isSet("shots")) { window.screenshots(parser.value("shots")); return 0; }
        return app.exec();
    } catch (const std::exception &e) {
        if (cli) QTextStream(stderr) << e.what() << '\n';
        else QMessageBox::critical(nullptr, "GD's Melee", QString::fromUtf8(e.what()));
        return 1;
    }
}
