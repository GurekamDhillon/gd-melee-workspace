// Synthetic process boundary for hub tests. Never starts Python, a shell or a game.
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTextStream>
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    const auto args = app.arguments().mid(1);
    const int index = args.indexOf("--project");
    if (index < 0 || index + 1 >= args.size()) return 3;
    const auto project = args[index + 1];
    QFile requests(QDir(project).filePath(".play-requests.json"));
    QJsonArray calls;
    if (requests.open(QIODevice::ReadOnly)) {
        calls = QJsonDocument::fromJson(requests.readAll()).array(); requests.close();
    }
    calls.append(QJsonArray::fromStringList(args));
    if (!requests.open(QIODevice::WriteOnly | QIODevice::Truncate)) return 4;
    requests.write(QJsonDocument(calls).toJson()); requests.close();
    const bool stale = qEnvironmentVariableIsSet("WB_PLAY_HELPER_STALE") && !args.contains("--rebuild");
    const bool fail = qEnvironmentVariableIsSet("WB_PLAY_HELPER_FAIL") && !args.contains("--check");
    const QJsonObject result{{"ok", !fail}, {"stale", stale ? QJsonArray{"moves/jab1.genoasm is newer"} : QJsonArray{}},
        {"can_rebuild", true}, {"log_path", QDir(project).filePath("runs/play/melee-pc.log")},
        {"error", fail ? QString("synthetic rebuild refused") : QString{}}};
    QTextStream(stdout) << QJsonDocument(result).toJson(QJsonDocument::Compact) << Qt::endl;
    return fail ? 1 : 0;
}
