#include "../testfixture.h"
#include "geno_data.h"
#include "session.h"
#include <QTemporaryDir>
#include <QtTest>

using namespace wb;

class SessionTest : public QObject {
    Q_OBJECT
    static HitboxEdit damageEdit(double d) {
        HitboxEdit e;
        e.damage = d;
        return e;
    }
private slots:
    void commitReloadsData() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        QCOMPARE(session.data().hitboxes("dair").first().damage, 14.0);
        QString err;
        const auto changes = session.data().editHitbox("dair", 0, damageEdit(19), &err);
        QVERIFY2(!changes.isEmpty(), qPrintable(err));
        CommandContext ctx{session};
        QVERIFY(session.commit(ctx, "edit_hitbox", {}, "dair damage", changes)["applied"].toBool());
        QCOMPARE(session.data().hitboxes("dair").first().damage, 19.0);
    }
    void proposalLeavesDataUnchanged() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        QString err;
        const auto changes = session.data().editHitbox("dair", 0, damageEdit(19), &err);
        CommandContext ctx{session};
        ctx.propose = true;
        QVERIFY(session.commit(ctx, "edit_hitbox", {}, "dair damage", changes)["proposed"].toBool());
        QCOMPARE(session.data().hitboxes("dair").first().damage, 14.0);
    }
    void externalEditRefusesCommit() {
        QTemporaryDir dir;
        wbtest::makeSynthFighter(dir.path());
        Session session(dir.path(), nullptr);
        QString err;
        const auto changes = session.data().editHitbox("dair", 0, damageEdit(19), &err);
        QFile f(QDir(dir.path()).filePath("moves/dair.genoasm"));
        QVERIFY(f.open(QIODevice::WriteOnly | QIODevice::Append));
        f.write("# hand edit\n");
        f.close();
        CommandContext ctx{session};
        bool refused = false;
        try {
            session.commit(ctx, "edit_hitbox", {}, "dair damage", changes);
        } catch (const CommandError &e) {
            refused = e.message.contains("changed externally");
        }
        QVERIFY(refused);
        QCOMPARE(session.data().hitboxes("dair").first().damage, 14.0);
    }
};
QTEST_MAIN(SessionTest)
#include "session_test.moc"
