#include "../testfixture.h"
#include "commands.h"
#include "throw_standin.h"
#include <QTemporaryDir>
#include <QtTest>
using namespace wb;
namespace {
QByteArray disk(const QString &root, const QString &path = "gameplay.json") {
    QFile f(QDir(root).filePath(path));
    return f.open(QIODevice::ReadOnly) ? f.readAll() : QByteArray{};
}
QJsonObject call(Session &s, const QString &cmd, const QJsonObject &args = {}) {
    CommandContext ctx{s, "human"}; return s.registry().call(cmd, args, ctx);
}
void source(const QString &root, const QByteArray &bytes) {
    wbtest::makeSynthFighter(root); wbtest::put(root, "gameplay.json", bytes);
}
}
class ThrowStandInTest : public QObject {
    Q_OBJECT
private slots:
    void defaultsAndCanonicalChoices() {
        QTemporaryDir d; source(d.path(), "{}"); Session s(d.path(), nullptr); registerThrowStandInCommands(s);
        auto desc = throwStandIn(s); QCOMPARE(desc["value"].toString(), QString("captain")); QVERIFY(desc["editable"].toBool());
        QCOMPARE(desc["choices"].toArray().size(), 26); QVERIFY(!desc["choices"].toArray().contains("nana"));
        QVERIFY(call(s, "list_throw_standin")["ok"].toBool()); QVERIFY(s.history().entries().isEmpty()); QCOMPARE(disk(d.path()), QByteArray("{}"));
    }
    void editPreservesBytesAndMirrorsFullWithUndo() {
        QTemporaryDir d; const QByteArray before = QByteArray("\xEF\xBB\xBF") + "{\r\n  \"thrown_as\": \"fox\", \"odd\": 1e+2\r\n}\r\n";
        source(d.path(), before); wbtest::put(d.path(), "gameplay.full.json", "{\"thrown_as\":\"falco\",\"other\":true}\n");
        Session s(d.path(), nullptr); registerThrowStandInCommands(s); QCOMPARE(throwStandIn(s)["value"].toString(), QString("falco"));
        QVERIFY(call(s, "edit_throw_standin", {{"value","samus"}})["ok"].toBool());
        auto expected = before; expected.replace("\"fox\"", "\"samus\""); QCOMPARE(disk(d.path()), expected);
        QCOMPARE(disk(d.path(), "gameplay.full.json"), QByteArray("{\"thrown_as\":\"samus\",\"other\":true}\n"));
        QCOMPARE(s.history().entries().size(), 1); QCOMPARE(s.history().entries().first().changes.size(), 2);
        QString err; QVERIFY(s.history().undo(s.files(), &err)); QCOMPARE(disk(d.path()), before);
    }
    void inheritedDefaultCreatesExplicitOverrideAndProposalDoesNotWrite() {
        QTemporaryDir d; source(d.path(), "{}");
        wbtest::put(d.path(), "package/geno.json", "{\"geno\":10,\"fighters\":[{\"define\":{\"key\":\"synth\",\"base\":\"none\"},\"thrown_as\":\"fox\"}]}");
        Session s(d.path(), nullptr); registerThrowStandInCommands(s); auto built = disk(d.path(), "package/geno.json");
        QCOMPARE(throwStandIn(s)["value"].toString(), QString("fox"));
        QVERIFY(call(s,"edit_throw_standin",{{"value","fox"},{"propose",true}})["ok"].toBool()); QCOMPARE(disk(d.path()), QByteArray("{}"));
        QCOMPARE(s.history().entries().first().changes.size(),1); QString err; QVERIFY(s.history().accept(s.history().entries().first().id,s.files(),&err));
        QCOMPARE(QJsonDocument::fromJson(disk(d.path())).object()["thrown_as"].toString(),QString("fox")); QCOMPARE(disk(d.path(),"package/geno.json"),built);
        auto count=s.history().entries().size(); QVERIFY(call(s,"edit_throw_standin",{{"value","fox"}})["ok"].toBool()); QCOMPARE(s.history().entries().size(),count);
    }
    void directSourceSelectsProjectFighterAndDoesNotMirror() {
        QTemporaryDir d; source(d.path(), "{\"geno\":10,\"fighters\":[{\"define\":{\"key\":\"other\",\"base\":\"none\"},\"thrown_as\":\"fox\"},{\"define\":{\"key\":\"synth\",\"base\":\"none\"},\"thrown_as\":\"captain\"}]}");
        wbtest::put(d.path(),"gameplay.full.json","broken"); Session s(d.path(),nullptr); registerThrowStandInCommands(s);
        QVERIFY(throwStandIn(s)["editable"].toBool()); QVERIFY(call(s,"edit_throw_standin",{{"value","falco"}})["ok"].toBool());
        auto fighters=QJsonDocument::fromJson(disk(d.path())).object()["fighters"].toArray(); QCOMPARE(fighters[0].toObject()["thrown_as"].toString(),QString("fox")); QCOMPARE(fighters[1].toObject()["thrown_as"].toString(),QString("falco"));
        QCOMPARE(disk(d.path(),"gameplay.full.json"),QByteArray("broken"));
    }
    void invalidSourcesAreReadOnlyAndNeverTruncated_data() {
        QTest::addColumn<QByteArray>("bytes");
        QTest::newRow("unknown") << QByteArray("{\"thrown_as\":\"nana\"}");
        QTest::newRow("wrong-type") << QByteArray("{\"thrown_as\":null}");
        QTest::newRow("duplicate") << QByteArray("{\"thrown_as\":\"fox\",\"thrown_as\":\"samus\"}");
        QTest::newRow("bad-json") << QByteArray("{broken");
        QTest::newRow("base-mario") << QByteArray("{\"geno\":10,\"fighters\":[{\"define\":{\"key\":\"synth\",\"base\":\"mario\"}}]}");
        QTest::newRow("old-format") << QByteArray("{\"geno\":9,\"fighters\":[{\"define\":{\"key\":\"synth\",\"base\":\"none\"}}]}");
        QTest::newRow("ambiguous") << QByteArray("{\"geno\":10,\"fighters\":[{\"define\":{\"key\":\"synth\",\"base\":\"none\"}},{\"define\":{\"key\":\"synth\",\"base\":\"none\"}}]}");
    }
    void invalidSourcesAreReadOnlyAndNeverTruncated() {
        QFETCH(QByteArray, bytes); QTemporaryDir d; source(d.path(),bytes); Session s(d.path(),nullptr); registerThrowStandInCommands(s);
        auto desc=throwStandIn(s); QVERIFY(!desc["editable"].toBool()); QVERIFY(!desc["note"].toString().isEmpty());
        QVERIFY(!call(s,"edit_throw_standin",{{"value","fox"}})["ok"].toBool()); QCOMPARE(disk(d.path()),bytes); QVERIFY(s.history().entries().isEmpty());
    }
    void inputValidationAndExternalChangesCannotBeAcknowledgedByLists() {
        QTemporaryDir d; source(d.path(),"{}"); Session s(d.path(),nullptr); registerThrowStandInCommands(s);
        for (const auto &value : QJsonArray{"nana","unknown",1,QJsonValue(QJsonValue::Null)}) QVERIFY(!call(s,"edit_throw_standin",{{"value",value}})["ok"].toBool());
        wbtest::put(d.path(),"gameplay.full.json","{\"thrown_as\":\"falco\"}");
        QVERIFY(call(s,"list_throw_standin")["ok"].toBool()); QVERIFY(!call(s,"edit_throw_standin",{{"value","fox"}})["ok"].toBool()); QCOMPARE(disk(d.path()),QByteArray("{}"));
    }
    void knownAliasesRemainAuthoredUntilExplicitCanonicalEdit() {
        QTemporaryDir d; const QByteArray before="{\"thrown_as\":\"FaLcOn\"}"; source(d.path(),before);
        Session s(d.path(),nullptr); registerThrowStandInCommands(s); const auto desc=throwStandIn(s);
        QCOMPARE(desc["value"].toString(),QString("captain")); QVERIFY(desc["editable"].toBool()); QVERIFY(desc["note"].toString().contains("FaLcOn")); QCOMPARE(disk(d.path()),before);
        QVERIFY(call(s,"edit_throw_standin",{{"value","captain"}})["ok"].toBool()); QCOMPARE(disk(d.path()),QByteArray("{\"thrown_as\":\"captain\"}"));
    }
    void unknownExistingTokenRemainsVisibleWithoutDefaultClamping() {
        QTemporaryDir d; source(d.path(),"{\"thrown_as\":\"not-a-fighter\"}"); Session s(d.path(),nullptr); registerThrowStandInCommands(s);
        const auto desc=throwStandIn(s); QCOMPARE(desc["value"].toString(),QString("not-a-fighter")); QVERIFY(!desc["editable"].toBool());
    }
    void invalidFullSourceBlocksPrimaryMutation() {
        QTemporaryDir d; const QByteArray before="{\"thrown_as\":\"fox\"}"; source(d.path(),before);
        const QByteArray full="{\"thrown_as\":\"nana\",\"retained\":1}"; wbtest::put(d.path(),"gameplay.full.json",full);
        Session s(d.path(),nullptr); registerThrowStandInCommands(s); QVERIFY(!throwStandIn(s)["editable"].toBool());
        QVERIFY(!call(s,"edit_throw_standin",{{"value","samus"}})["ok"].toBool()); QCOMPARE(disk(d.path()),before); QCOMPARE(disk(d.path(),"gameplay.full.json"),full);
    }
    void generatedDefaultsRequireBaseNoneAndKnownToken_data() {
        QTest::addColumn<QByteArray>("package");
        QTest::newRow("base-mario") << QByteArray("{\"geno\":10,\"fighters\":[{\"define\":{\"key\":\"synth\",\"base\":\"mario\"}}]}");
        QTest::newRow("bad-standin") << QByteArray("{\"geno\":10,\"fighters\":[{\"define\":{\"key\":\"synth\",\"base\":\"none\"},\"thrown_as\":\"nana\"}]}");
    }
    void generatedDefaultsRequireBaseNoneAndKnownToken() {
        QFETCH(QByteArray, package); QTemporaryDir d; source(d.path(),"{}"); wbtest::put(d.path(),"package/geno.json",package);
        Session s(d.path(),nullptr); registerThrowStandInCommands(s); const auto desc=throwStandIn(s); QVERIFY(!desc["editable"].toBool()); QVERIFY(!desc["note"].toString().isEmpty());
        QVERIFY(!call(s,"edit_throw_standin",{{"value","fox"}})["ok"].toBool()); QCOMPARE(disk(d.path()),QByteArray("{}")); QCOMPARE(disk(d.path(),"package/geno.json"),package);
    }
    void modIdSelectsFighterAheadOfProjectId() {
        QTemporaryDir d; source(d.path(),"{\"geno\":10,\"fighters\":[{\"define\":{\"key\":\"synth\",\"base\":\"none\"},\"thrown_as\":\"fox\"},{\"define\":{\"key\":\"different-mod\",\"base\":\"none\"},\"thrown_as\":\"samus\"}]}");
        auto project=disk(d.path(),"workbench.json"); project.replace("\"mod_id\": \"synth\"","\"mod_id\": \"different-mod\""); wbtest::put(d.path(),"workbench.json",project);
        Session s(d.path(),nullptr); registerThrowStandInCommands(s); QCOMPARE(throwStandIn(s)["value"].toString(),QString("samus"));
        QVERIFY(call(s,"edit_throw_standin",{{"value","falco"}})["ok"].toBool()); const auto fighters=QJsonDocument::fromJson(disk(d.path())).object()["fighters"].toArray();
        QCOMPARE(fighters[0].toObject()["thrown_as"].toString(),QString("fox")); QCOMPARE(fighters[1].toObject()["thrown_as"].toString(),QString("falco"));
    }
};
QTEST_GUILESS_MAIN(ThrowStandInTest)
#include "throw_standin_test.moc"
