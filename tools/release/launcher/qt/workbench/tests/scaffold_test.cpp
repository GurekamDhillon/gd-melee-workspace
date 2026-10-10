#include "../testfixture.h"
#include <QTemporaryDir>
#include <QtTest>

class ScaffoldTest : public QObject {
    Q_OBJECT
private slots:
    void fixtureIsValidJson() {
        QTemporaryDir tmp;
        QVERIFY(tmp.isValid());
        wbtest::makeSynthFighter(tmp.path());
        for (const char *rel : {"gameplay.json", "fidelity.json", "workbench.json", "package/files/plan.json"}) {
            QFile f(QDir(tmp.path()).filePath(rel));
            QVERIFY2(f.open(QIODevice::ReadOnly), rel);
            QJsonParseError err;
            QJsonDocument::fromJson(f.readAll(), &err);
            QVERIFY2(err.error == QJsonParseError::NoError, rel);
        }
        QVERIFY(QFile::exists(QDir(tmp.path()).filePath("moves/dair.genoasm")));
    }
};
QTEST_MAIN(ScaffoldTest)
#include "scaffold_test.moc"
