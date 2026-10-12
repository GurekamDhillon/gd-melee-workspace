// Synthetic rebuild subprocess. Exercises the real QProcess boundary without a shell, Python or a game.
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    const auto args = app.arguments().mid(1);
    if (args.isEmpty()) return 2;
    QFile out, err;
    if (!out.open(stdout, QIODevice::WriteOnly) || !err.open(stderr, QIODevice::WriteOnly)) return 2;
    const QString mode = args.first();
    if (mode == "ok") out.write("rebuilt\n");
    else if (mode == "fail") {
        out.write("before failure\n");
        err.write("stderr failure");
        return 3;
    } else if (mode == "build-mode") out.write("noise\nBUILD_MODE: gameplay-only 12.5s\n");
    else if (mode == "argv") {
        out.write(QJsonDocument(QJsonObject{{"cwd", QDir::currentPath()},
            {"args", QJsonArray::fromStringList(args.mid(1))}}).toJson(QJsonDocument::Compact) + '\n');
    } else if (mode == "tail") {
        out.write(QByteArray(5000, 'O'));
        err.write("stderr-tail");
    } else return 2;
    return 0;
}
