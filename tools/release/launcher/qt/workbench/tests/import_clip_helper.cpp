// Synthetic retarget subprocess used by the command tests. No shell or Python needed.
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QThread>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    const auto args = app.arguments();
    if (args.size() != 4) return 2;
    const QString mode = args[1], target = args[3];
    // stdin must already be at EOF; leaving a pipe open makes import time out.
    QFile input; if (!input.open(stdin, QIODevice::ReadOnly) || !input.readAll().isEmpty()) return 3;
    QDir().mkpath("bank");
    QFile clip(QDir("bank").filePath(target + ".anim"));
    if (!clip.open(QIODevice::WriteOnly)) return 4;
    clip.write("synthetic imported clip\n"); clip.close();
    if (mode == "built") {
        QFile plan("package/files/plan.json");
        if (!plan.open(QIODevice::WriteOnly)) return 5;
        plan.write("{}\n");
    }
    if (mode == "relative-plan") {
        QFile plan("generated/plan.json");
        if (!plan.open(QIODevice::WriteOnly)) return 5;
        plan.write("{}\n");
    }
    if (mode == "timeout") QThread::sleep(60);
    if (mode == "delete") QFile::remove("moves/dair.genoasm");
    if (mode == "nonzero") return 7;
    QFile output; if (!output.open(stdout, QIODevice::WriteOnly)) return 6;
    if (mode == "not-json") output.write("not json\n");
    else if (mode == "bad-shape") output.write("{\"clip\":\"SYN_IMPORTED\",\"frames\":\"twenty\"}\n");
    else output.write(QJsonDocument(QJsonObject{{"clip", target}, {"frames", 20},
        {"source", args[2]}, {"cwd", QDir::currentPath()}}).toJson(QJsonDocument::Compact) + '\n');
    return 0;
}
