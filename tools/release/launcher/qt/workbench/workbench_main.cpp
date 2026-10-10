#include "workbench_main.h"
#include "engine_link.h"
#include "mcp_server.h"
#include "project.h"
#include "session.h"
#if __has_include("commands.h")
#include "commands.h"
#endif
#include <QCommandLineParser>
#include <QDir>
#include <QEventLoop>
#include <QMetaObject>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonParseError>
#include <QLocale>
#include <QStringList>
#include <exception>
#include <iostream>
#include <memory>
#include <thread>

namespace wb {
namespace {
QString lt(const char *en, const char *es) {
    return QString::fromUtf8(QLocale::system().language() == QLocale::Spanish ? es : en);
}
enum CliMode { McpMode = 1, CallMode = 2, ServeMode = 4 };
int cliModes(int argc, char **argv) {
    // Skip value tokens before interpreting mode flags, even if parsing will
    // later fail. A value named --wb-call must never redirect MCP errors to stdout.
    const QStringList values{"--app-dir", "--data-dir", "--lang", "--add-iso", "--probe",
        "--enable-mod", "--disable-mod", "--shots", "--project", "--engine-port", "--engine-exe",
        "--engine-work-dir", "--mods-dir", "--wb-dir", "--serve-port", "--serve-author"};
    int modes = 0;
    for (int i = 1; i < argc; ++i) {
        const QString arg = QString::fromLocal8Bit(argv[i]);
        if (arg == "--") break;
        if (arg == "--mcp" || arg.startsWith("--mcp=")) modes |= McpMode;
        if (arg == "--serve" || arg.startsWith("--serve=")) modes |= ServeMode;
        if (arg == "--wb-call" || arg.startsWith("--wb-call=")) {
            modes |= CallMode;
            if (arg == "--wb-call") ++i; // The command name is a value too.
        } else if (values.contains(arg)) ++i;
    }
    return modes;
}
QStringList arguments(int argc, char **argv) {
    QStringList args;
    for (int i = 0; i < argc; ++i) args.append(QString::fromLocal8Bit(argv[i]));
    return args;
}
void diagnostic(const QString &text) { std::cerr << text.toUtf8().constData() << '\n' << std::flush; }
void printEnvelope(const QJsonObject &object) {
    std::cout << QJsonDocument(object).toJson(QJsonDocument::Compact).constData() << '\n' << std::flush;
}
struct Options {
    QString projectDir, engineExe, engineWorkDir, modsDir, wbDir;
    quint16 enginePort = 0;
    bool headless = true;
};
struct WorkbenchSession {
    // Reverse destruction order: Session borrows engine, which stops only its
    // own process. An attached engine is never killed when this CLI exits.
    std::unique_ptr<EngineLink> engine;
    std::unique_ptr<Session> session;
};
WorkbenchSession buildSession(const Options &options) {
    WorkbenchSession result;
    if (options.enginePort || !options.engineExe.isEmpty()) {
        FileStore files(options.projectDir);
        QString error;
        const auto project = ProjectConfig::load(files, &error);
        if (!error.isEmpty()) throw CommandError{error};
        EngineLink::Launch launch;
        launch.exe = options.engineExe;
        launch.headless = options.headless;
        launch.workDir = options.engineWorkDir.isEmpty()
            ? (launch.exe.isEmpty() ? options.projectDir : QFileInfo(launch.exe).absolutePath())
            : options.engineWorkDir;
        launch.modsDir = options.modsDir.isEmpty()
            ? qEnvironmentVariable("MELEE_MODS_DIR", QDir(options.projectDir).filePath("package/mods"))
            : options.modsDir;
        launch.wbDir = options.wbDir.isEmpty()
            ? qEnvironmentVariable("MELEE_WB_DIR", QDir(options.projectDir).filePath(".workbench/payloads"))
            : options.wbDir;
        // Resolve before start changes the child's working directory.
        launch.modsDir = QFileInfo(launch.modsDir).absoluteFilePath();
        launch.wbDir = QFileInfo(launch.wbDir).absoluteFilePath();
        launch.modId = project.modId.isEmpty() ? project.id : project.modId;
        launch.env = QProcessEnvironment::systemEnvironment();
        result.engine = std::make_unique<EngineLink>(launch);
        const bool started = options.enginePort ? result.engine->attach(options.enginePort, &error)
                                                : result.engine->start(&error);
        if (!started) diagnostic(error);
        // Keep the failed backend so engine_status and later calls explain the
        // failure; initialization and tool discovery are still available.
    }
    result.session = std::make_unique<Session>(options.projectDir, result.engine.get());
#if __has_include("commands.h")
    registerAllCommands(*result.session);
#else
    diagnostic(lt("Workbench commands are not linked yet.", "Los comandos del editor aun no estan enlazados."));
#endif
    return result;
}
} // namespace

bool isWorkbenchCli(int argc, char **argv) { return cliModes(argc, argv) != 0; }

int runWorkbenchCli(int argc, char **argv) {
    const auto args = arguments(argc, argv);
    // Even parse failures on the one-shot path produce its documented envelope.
    bool callMode = (cliModes(argc, argv) & CallMode) != 0;
    auto fail = [&](const QString &error) {
        if (callMode) printEnvelope({{"ok", false}, {"error", error}});
        else diagnostic(error);
        return 1;
    };
    try {
        QCommandLineParser parser;
        parser.setApplicationDescription(lt("Geno Workbench command interface", "Interfaz de comandos de Geno Workbench"));
        parser.addHelpOption();
        parser.addOptions({
            {"mcp", lt("Serve MCP over standard input/output", "Servir MCP por entrada/salida estandar")},
            {"wb-call", lt("Run one command as a human", "Ejecutar un comando como humano"), "tool"},
            {"serve", lt("Serve MCP on 127.0.0.1 with a persistent session (prints WB_SERVE port=N)", "Servir MCP en 127.0.0.1 con una sesion persistente (imprime WB_SERVE port=N)")},
            {"serve-port", lt("Port for --serve (0 = any)", "Puerto para --serve (0 = cualquiera)"), "port"},
            {"serve-author", lt("Author for --serve: human (default) or agent", "Autor para --serve: human (por defecto) o agent"), "author"},
            {"engine-windowed", lt("Run the engine with a window instead of headless", "Ejecutar el motor con ventana en vez de sin ventana")},
            {"project", lt("Fighter source project directory", "Directorio del proyecto fuente del luchador"), "directory"},
            {"engine-port", lt("Attach to an engine on 127.0.0.1", "Conectar a un motor en 127.0.0.1"), "port"},
            {"engine-exe", lt("Start a workbench engine", "Iniciar un motor del editor"), "path"},
            {"engine-work-dir", lt("Engine working directory", "Directorio de trabajo del motor"), "directory"},
            {"mods-dir", lt("Parent directory of built mods", "Directorio padre de mods compilados"), "directory"},
            {"wb-dir", lt("Engine payload directory (MELEE_WB_DIR)", "Directorio de datos del motor (MELEE_WB_DIR)"), "directory"}
        });
        parser.addPositionalArgument("json", lt("JSON object of command arguments", "Objeto JSON de argumentos del comando"), "[json]");
        if (!parser.parse(args)) return fail(parser.errorText());
        if (parser.isSet("help")) { diagnostic(parser.helpText()); return 0; }
        const bool mcp = parser.isSet("mcp");
        const bool serve = parser.isSet("serve");
        callMode = parser.isSet("wb-call");
        if (int(mcp) + int(callMode) + int(serve) != 1)
            return fail(lt("Choose exactly one of --mcp, --wb-call or --serve.", "Elige exactamente una opcion: --mcp, --wb-call o --serve."));
        for (const QString &key : {"wb-call", "project", "engine-port", "engine-exe", "engine-work-dir", "mods-dir", "wb-dir", "serve-port", "serve-author"}) {
            if (parser.values(key).size() > 1)
                return fail(lt("Repeated option: --%1", "Opcion repetida: --%1").arg(key));
            if (parser.isSet(key) && parser.value(key).isEmpty())
                return fail(lt("Empty value for --%1", "Valor vacio para --%1").arg(key));
        }
        const auto positional = parser.positionalArguments();
        if ((callMode && positional.size() != 1) || ((mcp || serve) && !positional.isEmpty()))
            return fail(lt("Use --wb-call <tool> '<JSON object>' or --mcp.", "Usa --wb-call <tool> '<objeto JSON>' o --mcp."));
        QJsonObject commandArgs;
        if (callMode) {
            QJsonParseError error;
            const auto document = QJsonDocument::fromJson(positional.first().toUtf8(), &error);
            if (error.error != QJsonParseError::NoError)
                return fail(lt("Invalid command JSON: %1", "JSON de comando invalido: %1").arg(error.errorString()));
            if (!document.isObject())
                return fail(lt("Command arguments must be a JSON object.", "Los argumentos del comando deben ser un objeto JSON."));
            commandArgs = document.object();
        }
        Options options;
        options.projectDir = QFileInfo(parser.isSet("project") ? parser.value("project") : QDir::currentPath()).absoluteFilePath();
        quint16 servePort = 0;
        if (parser.isSet("serve-port")) {
            bool ok = false;
            const uint port = parser.value("serve-port").toUInt(&ok);
            if (!ok || port > 65535)
                return fail(lt("--serve-port must be an integer from 0 to 65535.", "--serve-port debe ser un entero entre 0 y 65535."));
            servePort = quint16(port);
        }
        const QString serveAuthor = parser.isSet("serve-author") ? parser.value("serve-author") : QString("human");
        if (serveAuthor != "human" && serveAuthor != "agent")
            return fail(lt("--serve-author must be human or agent.", "--serve-author debe ser human o agent."));
        if (serve && !parser.isSet("project"))
            return fail(lt("--serve requires --project.", "--serve requiere --project."));
        if (parser.isSet("engine-port")) {
            bool ok = false;
            const uint port = parser.value("engine-port").toUInt(&ok);
            if (!ok || port == 0 || port > 65535)
                return fail(lt("--engine-port must be an integer from 1 to 65535.", "--engine-port debe ser un entero entre 1 y 65535."));
            options.enginePort = quint16(port);
        }
        if (parser.isSet("engine-exe")) options.engineExe = QFileInfo(parser.value("engine-exe")).absoluteFilePath();
        if (options.enginePort && !options.engineExe.isEmpty())
            return fail(lt("Use --engine-port to attach or --engine-exe to spawn, not both.", "Usa --engine-port para conectar o --engine-exe para iniciar, no ambos."));
        if (parser.isSet("engine-work-dir")) options.engineWorkDir = QFileInfo(parser.value("engine-work-dir")).absoluteFilePath();
        options.headless = !parser.isSet("engine-windowed");
        options.modsDir = parser.value("mods-dir");
        options.wbDir = parser.value("wb-dir");
        auto owned = buildSession(options);
        if (serve) {
            McpServer server(*owned.session);
            server.setAuthor(serveAuthor);
            QString listenError;
            if (!server.listenLocal(servePort, &listenError)) return fail(listenError);
            std::cout << "WB_SERVE port=" << server.localPort() << std::endl;
            // Run until stdin closes (the parent went away) or the process is terminated. A reader
            // thread keeps the Qt event loop (the listener and the engine link) responsive.
            QEventLoop loop;
            std::thread reader([&loop] {
                char buffer[256];
                while (std::cin.read(buffer, sizeof buffer) || std::cin.gcount() > 0) {}
                QMetaObject::invokeMethod(&loop, [&loop] { loop.quit(); }, Qt::QueuedConnection);
            });
            loop.exec();
            if (owned.engine) owned.engine->stop();
            reader.detach(); // blocked on stdin; the process is exiting
            return 0;
        }
        if (mcp) {
            McpServer server(*owned.session);
            return server.runStdio();
        }
        CommandContext context{*owned.session, "human", false};
        const auto envelope = owned.session->registry().call(parser.value("wb-call"), commandArgs, context);
        printEnvelope(envelope);
        return envelope.value("ok").toBool() ? 0 : 1;
    } catch (const CommandError &error) {
        return fail(error.message);
    } catch (const std::exception &error) {
        return fail(QString::fromUtf8(error.what()));
    } catch (...) {
        return fail(lt("Unexpected workbench error.", "Error inesperado del editor."));
    }
}
} // namespace wb
