#include "../testfixture.h"
#include "engine_link.h"
#include <QCoreApplication>
#include <QElapsedTimer>
#include <QTemporaryDir>
#include <QtTest>
#include <memory>

using namespace wb;

namespace {
// Authored independently of FrameInfo::toJson; this is Task 12's wire format.
QJsonObject liveFrame() {
    return QJsonDocument::fromJson(R"JSON({
      "row":"dair","motion":70,"frame":6,
      "bones":[{"joint":3,"parent":1,"pos":{"x":1.5,"y":2,"z":-0.25}}],
      "hitboxes":[{"slot":0,"joint":3,"offset":{"x":0,"y":1,"z":2},
                   "radius":2.8,"world":{"x":1.5,"y":4,"z":-0.25},"active":true}],
      "hurtboxes":[{"joint":1,"a":{"x":1,"y":2,"z":3},
                    "b":{"x":4,"y":5,"z":6},"radius":1.25}],
      "ecb":{"bottom":{"x":0.5,"y":-2},"top":{"x":1,"y":8}},
      "floorY":-3,"lowestY":-2.5
    })JSON").object();
}
QString jsonReply(const QJsonObject &o) {
    return QString::fromUtf8(QJsonDocument(o).toJson(QJsonDocument::Compact)) + "\n>>> ok\n";
}
}

class EngineLinkTest : public QObject {
    Q_OBJECT
private slots:
    void luaLiteralQuotesAndNests() {
        QJsonObject o{{"name", "a\"b\n"}, {"n", 2.5}, {"ok", true},
                      {"list", QJsonArray{1, 2}}, {"child", QJsonObject{{"x", false}}}};
        const QString s = luaLiteral(o);
        QVERIFY(s.contains("[\"name\"]=\"a\\\"b\\n\""));
        QVERIFY(s.contains("[\"n\"]=2.5"));
        QVERIFY(s.contains("[\"ok\"]=true"));
        QVERIFY(s.contains("[\"list\"]={1,2}"));
        QVERIFY(s.contains("[\"child\"]={[\"x\"]=false}"));
        QCOMPARE(luaLiteral(QJsonValue(QJsonValue::Null)), QString("nil"));
        QCOMPARE(luaLiteral(QJsonValue(QJsonValue::Undefined)), QString("nil"));
    }
    void luaLiteralEscapesControlBytesAndKeys() {
        QString value = QStringLiteral("\\\"\r\n\t");
        value += QChar(0); value += '7'; value += QChar(31); value += QChar(127);
        QCOMPARE(luaLiteral(value), QString("\"\\\\\\\"\\r\\n\\009\\0007\\031\\127\""));
        QCOMPARE(luaLiteral(QJsonObject{{"a\"\\", "value"}}),
                 QString("{[\"a\\\"\\\\\"]=\"value\"}"));
        const QString unicode = QString::fromUtf8("caf\xc3\xa9");
        QCOMPARE(luaLiteral(unicode), '"' + unicode + '"');
        QCOMPARE(luaLiteral(0.12345678901234566), QString("0.12345678901234566"));
    }
    void consoleCallParsesOkAndError() {
        wbtest::FakeConsole fc([](const QString &l) {
            return l.contains("bad") ? QString("nope\n>>> error\n") : QString("hello\n>>> ok\n");
        });
        ConsoleClient c; QString err = "old error";
        QVERIFY2(c.connectTo(fc.port(), 2000, &err), qPrintable(err));
        QVERIFY(err.isEmpty());
        QVERIFY(c.banner().contains("GD's Melee console"));
        auto r = c.call("= 1", 2000);
        QVERIFY(r.ok); QCOMPARE(r.text.trimmed(), QString("hello"));
        r = c.call("bad", 2000);
        QVERIFY(!r.ok); QCOMPARE(r.text.trimmed(), QString("nope"));
        QVERIFY(c.connected());
    }
    void fragmentedBannerAndMarkers() {
        wbtest::FakeConsole fc([](const QString &) {
            return QString("line 1\r\n>>> okay\r\nline 2\r\n>>> ok\r\n");
        });
        fc.fragmentBytes = 2;
        ConsoleClient c; QString err;
        QVERIFY2(c.connectTo(fc.port(), 2000, &err), qPrintable(err));
        const auto r = c.call("= 1", 2000);
        QVERIFY(r.ok);
        QCOMPARE(r.text, QString("line 1\n>>> okay\nline 2"));
    }
    void bannerHasADeadlineAndIsValidated() {
        wbtest::FakeConsole silent(nullptr); silent.greeting.clear();
        ConsoleClient c; QString err; QElapsedTimer t; t.start();
        QVERIFY(!c.connectTo(silent.port(), 100, &err));
        QCOMPARE(err, QString("timeout")); QVERIFY(t.elapsed() < 1000);
        QVERIFY(!c.connected());
        wbtest::FakeConsole wrong(nullptr); wrong.greeting = "unrelated service\n";
        QVERIFY(!c.connectTo(wrong.port(), 1000, &err));
        QVERIFY(err.contains("banner")); QVERIFY(!c.connected());
    }
    void timeoutDoesNotHangOrReuseTheReply() {
        wbtest::FakeConsole fc([](const QString &) { return QString("late\n>>> ok\n"); });
        fc.replyDelayMs = 200;
        ConsoleClient c; QString err;
        QVERIFY(c.connectTo(fc.port(), 2000, &err));
        QElapsedTimer t; t.start();
        const auto r = c.call("= 1", 50);
        QVERIFY(!r.ok); QCOMPARE(r.text, QString("timeout")); QVERIFY(t.elapsed() < 1000);
        QVERIFY(!c.connected()); // Late output must not become the next command's result.
        fc.replyDelayMs = 0;
        QVERIFY(c.connectTo(fc.port(), 2000, &err));
        QVERIFY(c.call("= 2", 2000).ok);
    }
    void commandByteLimitAndSingleLine() {
        int served = 0;
        wbtest::FakeConsole fc([&](const QString &) { ++served; return QString("ok\n>>> ok\n"); });
        ConsoleClient c; QString err;
        QVERIFY(c.connectTo(fc.port(), 2000, &err));
        QVERIFY(!c.call(QString(4096, 'a'), 100).ok);
        QVERIFY(!c.call(QString(2048, QChar(0xe9)), 100).ok); // 4096 UTF-8 bytes
        QVERIFY(!c.call("one\ntwo", 100).ok);
        QVERIFY(!c.call("one\rtwo", 100).ok);
        QVERIFY(!c.call(QString("a") + QChar(0) + 'b', 100).ok);
        QVERIFY(c.call(QString(4095, 'a'), 2000).ok);
        QCOMPARE(served, 1);
    }
    void droppedSocketIsAnErrorNotAHang() {
        wbtest::FakeConsole fc([](const QString &) { return QString("{}\n>>> ok\n"); });
        EngineLink link({}); QString err;
        QVERIFY2(link.attach(fc.port(), &err), qPrintable(err));
        fc.dropClients();
        QElapsedTimer t; t.start();
        QVERIFY(link.call("frame", {}, &err).isEmpty());
        QCOMPARE(err, QString("engine connection lost"));
        QCOMPARE(link.status(), QString("error: engine connection lost"));
        QVERIFY(t.elapsed() < 1000);
    }
    void headlessSetsEnv() {
        EngineLink::Launch l;
        l.modId = "synth"; l.modsDir = "mods"; l.wbDir = "wb"; l.headless = true;
        l.env = QProcessEnvironment::systemEnvironment();
        EngineLink on(l);
        QCOMPARE(on.buildEnvironment(5000).value("MELEE_WB_HEADLESS"), QString("1"));
        l.headless = false;
        l.env.insert("MELEE_WB_HEADLESS", "1"); // an inherited value must not leak into a windowed engine
        EngineLink off(l);
        const auto env = off.buildEnvironment(5000);
        QVERIFY(!env.contains("MELEE_WB_HEADLESS"));
        for (const auto &e2 : {env, on.buildEnvironment(5000)}) {
            QCOMPARE(e2.value("MELEE_CONSOLE_PORT"), QString("5000"));
            QVERIFY(e2.value("MELEE_SCENE").contains("mode=workbench"));
            QCOMPARE(e2.value("MELEE_WB_DIR"), QString("wb"));
        }
    }
    void engineDiesMidCall() {
        wbtest::FakeConsole fc(nullptr);
        EngineLink link({}); QString err; link.setTimeoutMs(2000);
        QVERIFY(link.attach(fc.port(), &err));
        QTimer::singleShot(20, &fc, [&] { fc.dropClients(); });
        QElapsedTimer t; t.start();
        QVERIFY(link.call("frame_info", {}, &err).isEmpty());
        QCOMPARE(err, QString("engine connection lost"));
        QCOMPARE(link.status(), QString("error: engine connection lost"));
        QVERIFY(t.elapsed() < 1000);
    }
    void inlineJsonUsesLastNonemptyLineAndQuotesArguments() {
        QString command;
        wbtest::FakeConsole fc([&](const QString &line) {
            command = line; return QString("diagnostic\n{\"row\":\"dair\"}\n\n>>> ok\n");
        });
        EngineLink link({}); QString err = "old";
        QVERIFY(link.attach(fc.port(), &err));
        const auto r = link.call("row", {{"name", "a\"b\n"}}, &err);
        QCOMPARE(r["row"].toString(), QString("dair"));
        QVERIFY(err.isEmpty());
        QCOMPARE(command, QString("=wb.row({[\"name\"]=\"a\\\"b\\n\"})"));
        command.clear();
        QVERIFY(link.call("row();bad", {}, &err).isEmpty());
        QVERIFY(!err.isEmpty()); QVERIFY(command.isEmpty());
    }
    void badRepliesAreErrorsAndRecover() {
        QString reply;
        wbtest::FakeConsole fc([&](const QString &) { return reply; });
        EngineLink link({}); QString err;
        QVERIFY(link.attach(fc.port(), &err));
        reply = "Lua: bad motion\n>>> error\n";
        QVERIFY(link.call("row", {}, &err).isEmpty());
        QCOMPARE(err, QString("Lua: bad motion"));
        reply = "{broken\n>>> ok\n";
        QVERIFY(link.call("frame_info", {}, &err).isEmpty());
        QVERIFY(err.contains("JSON"));
        reply = "unexpected\n>>> ok\n";
        QVERIFY(link.call("frame_info", {}, &err).isEmpty()); QVERIFY(!err.isEmpty());
        reply = "ok\n>>> ok\n";
        QVERIFY(link.call("row", {}, &err)["ok"].toBool());
        QVERIFY(err.isEmpty()); QCOMPARE(link.status(), QString("ready"));
    }
    void payloadFileIsReadFromWbDir() {
        QTemporaryDir wbd;
        wbtest::put(wbd.path(), "frame.json", R"JSON({"frame":7,"row":"dair"})JSON");
        QString payload = wbd.filePath("frame.json");
        wbtest::FakeConsole fc([&](const QString &) { return "@" + payload + "\n>>> ok\n"; });
        EngineLink::Launch l; l.wbDir = wbd.path();
        EngineLink link(l); QString err;
        QVERIFY(link.attach(fc.port(), &err));
        QCOMPARE(link.call("frame", {{"frame", 7}}, &err)["frame"].toInt(), 7);
        QVERIFY(err.isEmpty());
        payload = "frame.json";
        QCOMPARE(link.call("frame_info", {}, &err)["row"].toString(), QString("dair"));
        QVERIFY(err.isEmpty());
    }
    void oversizedInlineReplyFails() {
        wbtest::FakeConsole fc([](const QString &) {
            return jsonReply({{"note", QString(20000, 'x')}});
        });
        EngineLink link({}); QString err;
        QVERIFY(link.attach(fc.port(), &err));
        QVERIFY(link.call("frame_info", {}, &err).isEmpty());
        QVERIFY(err.contains("too large"));
        QVERIFY(link.status().startsWith("error"));
    }
    void payloadCanExceedConsoleBuffer() {
        QTemporaryDir wbd;
        auto frame = liveFrame(); frame.insert("note", QString(20000, 'x'));
        wbtest::put(wbd.path(), "frame.json", QJsonDocument(frame).toJson());
        wbtest::FakeConsole fc([](const QString &) { return QString("@frame.json\n>>> ok\n"); });
        EngineLink::Launch l; l.wbDir = wbd.path();
        EngineLink link(l); QString err; QVERIFY(link.attach(fc.port(), &err));
        QCOMPARE(link.call("frame_info", {}, &err)["note"].toString().size(), 20000);
        QVERIFY(err.isEmpty());
    }
    void payloadPathCannotEscapeWbDir() {
        QTemporaryDir base;
        const QString inside = base.filePath("wb"), sibling = base.filePath("wb-other");
        wbtest::put(inside, "frame.json", "{}");
        wbtest::put(sibling, "frame.json", "{}");
        QString payload = sibling + "/frame.json";
        wbtest::FakeConsole fc([&](const QString &) { return "@" + payload + "\n>>> ok\n"; });
        EngineLink::Launch l; l.wbDir = inside;
        EngineLink link(l); QString err; QVERIFY(link.attach(fc.port(), &err));
        QVERIFY(link.call("frame_info", {}, &err).isEmpty()); QVERIFY(err.contains("outside"));
        payload = "../wb-other/frame.json";
        QVERIFY(link.call("frame_info", {}, &err).isEmpty()); QVERIFY(err.contains("outside"));
#ifndef Q_OS_WIN
        // QFile::link creates shortcuts on Windows, not filesystem symlinks.
        QVERIFY(QFile::link(sibling + "/frame.json", inside + "/escape.json"));
        payload = "escape.json";
        QVERIFY(link.call("frame_info", {}, &err).isEmpty()); QVERIFY(err.contains("outside"));
#endif
    }
    void payloadReadAndJsonFailures() {
        QTemporaryDir wbd;
        QString payload = "@missing.json\n>>> ok\n";
        wbtest::FakeConsole fc([&](const QString &) { return payload; });
        EngineLink::Launch l; l.wbDir = wbd.path();
        EngineLink link(l); QString err; QVERIFY(link.attach(fc.port(), &err));
        QVERIFY(link.call("frame_info", {}, &err).isEmpty()); QVERIFY(!err.isEmpty());
        wbtest::put(wbd.path(), "bad.json", "[]");
        payload = "@bad.json\n>>> ok\n";
        QVERIFY(link.call("frame_info", {}, &err).isEmpty()); QVERIFY(err.contains("JSON"));
        wbtest::put(wbd.path(), "bad.json", "{");
        QVERIFY(link.call("frame_info", {}, &err).isEmpty()); QVERIFY(err.contains("JSON"));
        EngineLink noDirectory({});
        QVERIFY(noDirectory.attach(fc.port(), &err));
        QVERIFY(noDirectory.call("frame_info", {}, &err).isEmpty()); QVERIFY(!err.isEmpty());
    }
    void frameInfoUsesTask12ShapeThroughBackend() {
        wbtest::FakeEngine fake; fake.canned["frame_info"] = liveFrame();
        EngineBackend &backend = fake; QString err;
        const FrameInfo fi = FrameInfo::fromJson(backend.call("frame_info", {}, &err));
        QCOMPARE(fi.row, QString("dair")); QCOMPARE(fi.motion, 70); QCOMPARE(fi.frame, 6);
        QCOMPARE(fi.bones.size(), 1); QCOMPARE(fi.bones[0].parent, 1);
        QCOMPARE(fi.bones[0].pos.z, -0.25);
        QCOMPARE(fi.hitboxes.size(), 1); QCOMPARE(fi.hitboxes[0].world.y, 4.0);
        QCOMPARE(fi.hitboxes[0].offset.z, 2.0); QVERIFY(fi.hitboxes[0].active);
        QCOMPARE(fi.hurtboxes.size(), 1); QCOMPARE(fi.hurtboxes[0].b.z, 6.0);
        QCOMPARE(fi.ecbBottom.y, -2.0); QCOMPARE(fi.ecbTop.y, 8.0);
        QCOMPARE(fi.floorY, -3.0); QCOMPARE(fi.lowestY, -2.5);
        QCOMPARE(fi.toJson(), liveFrame());
    }
    void framePollsPendingUntilRequestedFrame() {
        QStringList commands; int polls = 0;
        wbtest::FakeConsole fc([&](const QString &line) {
            commands.append(line);
            if (line.startsWith("=wb.frame(")) return QString("pending\n>>> ok\n");
            ++polls;
            return jsonReply({{"frame", polls == 1 ? -1 : 6}, {"motion", 70}}) /* the engine says -1 while pending */;
        });
        EngineLink link({}); QString err; QVERIFY(link.attach(fc.port(), &err));
        const auto r = link.call("frame", {{"frame", 6}, {"motion", 70}}, &err);
        QVERIFY2(err.isEmpty(), qPrintable(err)); QCOMPARE(r["frame"].toInt(), 6);
        QCOMPARE(polls, 2);
        QCOMPARE(commands[0], QString("=wb.frame({[\"frame\"]=6,[\"motion\"]=70})"));
        QCOMPARE(commands[1], QString("=wb.frame_info({})"));
        QCOMPARE(commands[2], QString("=wb.frame_info({})"));
    }
    void frameBeyondTheMoveEndsFailsPromptly() {
        // The move ends after frame 39: asking for 40 gets a finished (not pending) reply for another frame.
        bool past = false;
        wbtest::FakeConsole fc([&](const QString &line) {
            if (line.startsWith("=wb.frame(")) { past = line.contains("40"); return QString("pending\n>>> ok\n"); }
            return jsonReply({{"frame", past ? 1 : 39}, {"motion", past ? 29 : 69}});
        });
        EngineLink link({}); QString err; QVERIFY(link.attach(fc.port(), &err));
        QVERIFY(!link.call("frame", {{"frame", 39}, {"motion", 69}}, &err).isEmpty());
        QElapsedTimer t; t.start();
        QVERIFY(link.call("frame", {{"frame", 40}, {"motion", 69}}, &err).isEmpty());
        QVERIFY(t.elapsed() < 1500);
        QVERIFY2(err.contains("past the end") && err.contains("last frame 39"), qPrintable(err));
        QVERIFY(!err.contains("timeout"));
        QCOMPARE(link.status(), QString("ready")); // not a transport failure
    }
    void framePollsStalePayloadAndRequiresAFrameField() {
        int polls = 0;
        wbtest::FakeConsole fc([&](const QString &line) {
            if (line.startsWith("=wb.frame(")) return jsonReply({{"row", "dair"}});
            ++polls;
            return jsonReply({{"frame", 0}});
        });
        EngineLink link({}); QString err; QVERIFY(link.attach(fc.port(), &err));
        QCOMPARE(link.call("frame", {{"frame", 0}}, &err)["frame"].toInt(-1), 0);
        QVERIFY(err.isEmpty()); QCOMPARE(polls, 1);
    }
    void framePollingHasOneDeadline() {
        wbtest::FakeConsole fc([](const QString &line) {
            return line.startsWith("=wb.frame(") ? QString("pending\n>>> ok\n")
                                                : QString("{\"frame\":1}\n>>> ok\n");
        });
        EngineLink link({}); QString err; link.setTimeoutMs(150);
        QVERIFY(link.attach(fc.port(), &err));
        QElapsedTimer t; t.start();
        QVERIFY(link.call("frame", {{"frame", 6}}, &err).isEmpty());
        QVERIFY(err.contains("timeout")); QVERIFY(t.elapsed() < 1000);
    }
    void deadSocketDuringFramePolling() {
        wbtest::FakeConsole *server = nullptr;
        wbtest::FakeConsole fc([&](const QString &line) {
            if (line.startsWith("=wb.frame(")) return QString("pending\n>>> ok\n");
            server->dropClients(); return QString();
        });
        server = &fc;
        EngineLink link({}); QString err; QVERIFY(link.attach(fc.port(), &err));
        QVERIFY(link.call("frame", {{"frame", 6}}, &err).isEmpty());
        QCOMPARE(err, QString("engine connection lost"));
        QCOMPARE(link.status(), QString("error: engine connection lost"));
    }
    void configuredCallTimeoutAndStoppedStatus() {
        EngineLink link({}); QString err;
        QCOMPARE(link.status(), QString("stopped"));
        QVERIFY(link.call("frame_info", {}, &err).isEmpty()); QVERIFY(!err.isEmpty());
        wbtest::FakeConsole fc(nullptr); link.setTimeoutMs(50);
        QVERIFY(link.attach(fc.port(), &err));
        QElapsedTimer t; t.start();
        QVERIFY(link.call("frame_info", {}, &err).isEmpty());
        QCOMPARE(err, QString("timeout")); QVERIFY(t.elapsed() < 1000);
        QVERIFY(link.status().startsWith("error"));
        link.stop(); QCOMPARE(link.status(), QString("stopped"));
    }
    void eventPumpRefusesReentrantCalls() {
        wbtest::FakeConsole fc([](const QString &) { return QString("{\"frame\":6}\n>>> ok\n"); });
        fc.replyDelayMs = 50;
        EngineLink link({}); QString err; QVERIFY(link.attach(fc.port(), &err));
        QString nestedError; QJsonObject nested;
        QTimer::singleShot(10, &fc, [&] { nested = link.call("step", {{"n", 1}}, &nestedError); });
        QCOMPARE(link.call("frame_info", {}, &err)["frame"].toInt(), 6);
        QVERIFY(err.isEmpty()); QVERIFY(nested.isEmpty()); QVERIFY(nestedError.contains("progress"));
    }
    void renderReturnsContainedPathBeforePngExists() {
        QTemporaryDir base;
        const QString inside = base.filePath("wb");
        QVERIFY(QDir().mkpath(inside));
        QString payload = "view.png";
        wbtest::FakeConsole fc([&](const QString &) { return "@" + payload + "\n>>> ok\n"; });
        EngineLink::Launch l; l.wbDir = inside;
        EngineLink link(l); QString err; QVERIFY(link.attach(fc.port(), &err));
        const auto r = link.call("render", {{"w", 640}, {"h", 480}}, &err);
        QVERIFY2(err.isEmpty(), qPrintable(err));
        QCOMPARE(r["path"].toString(), QFileInfo(inside).canonicalFilePath() + "/view.png");
        QVERIFY(!QFile::exists(r["path"].toString()));
        payload = "../escape.png";
        QVERIFY(link.call("render", {}, &err).isEmpty()); QVERIFY(err.contains("outside"));
    }
    void stopDoesNotStopAnAttachedEngine() {
        wbtest::FakeConsole fc([](const QString &) { return QString("{}\n>>> ok\n"); });
        EngineLink link({}); QString err;
        QVERIFY(link.attach(fc.port(), &err)); link.stop();
        QCOMPARE(link.status(), QString("stopped"));
        ConsoleClient second;
        QVERIFY(second.connectTo(fc.port(), 2000, &err)); QVERIFY(second.call("= 1", 2000).ok);
    }
    void failedStartAndAttachAreReported() {
        QTemporaryDir d;
        EngineLink::Launch l; l.exe = d.filePath("not-an-executable"); l.wbDir = d.path();
        EngineLink link(l); QString err;
        QVERIFY(!link.start(&err)); QVERIFY(!err.isEmpty()); QVERIFY(link.status().startsWith("error"));
        QVERIFY(!link.attach(0, &err)); QVERIFY(!err.isEmpty()); QVERIFY(link.status().startsWith("error"));
    }
    void startAndReloadOwnOnlyTheirChild() {
        QTemporaryDir d;
        EngineLink::Launch l;
        l.exe = QCoreApplication::applicationFilePath(); l.extraArgs = {"--fake-workbench"};
        l.workDir = d.path(); l.wbDir = d.filePath("wb"); l.modsDir = d.filePath("mods"); l.modId = "synth";
        l.env = QProcessEnvironment::systemEnvironment();
        l.env.insert("MELEE_NETPLAY", "1"); l.env.insert("WB_TEST_ENV", "kept");
        EngineLink link(l); QString err;
        QVERIFY2(link.start(&err), qPrintable(err)); QCOMPARE(link.status(), QString("ready"));
        auto info = link.call("frame_info", {}, &err);
        QVERIFY2(err.isEmpty(), qPrintable(err));
        QCOMPARE(info["scene"].toString(), QString("mode=workbench;p1=geno:synth/hu;stage=fd"));
        QCOMPARE(info["mods"].toString(), l.modsDir); QCOMPARE(info["wb"].toString(), l.wbDir);
        QCOMPARE(info["netplay"].toString(), QString());
        QCOMPARE(info["x"].toString(), QString("100")); QCOMPARE(info["y"].toString(), QString("80"));
        QCOMPARE(info["custom"].toString(), QString("kept"));
        QCOMPARE(info["cwd"].toString(), QDir::fromNativeSeparators(d.path()));
        QVERIFY(info["port"].toString().toInt() > 0);
        const QString oldPid = info["pid"].toString();
        QVERIFY(!oldPid.isEmpty());
        QVERIFY(link.call("reload", {}, &err)["ok"].toBool());
        QVERIFY2(err.isEmpty(), qPrintable(err));
        info = link.call("frame_info", {}, &err);
        QVERIFY2(err.isEmpty(), qPrintable(err)); QVERIFY(info["pid"].toString() != oldPid);
        link.stop(); QCOMPARE(link.status(), QString("stopped"));
    }
};

// A synthetic child process exercises QProcess lifecycle without starting the game.
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    if (app.arguments().contains("--fake-workbench")) {
        wbtest::FakeConsole fc([](const QString &line) {
            if (line.startsWith("=wb.reload(")) return QString("reload needs restart\n>>> error\n");
            return jsonReply({{"frame", 0}, {"pid", QString::number(QCoreApplication::applicationPid())},
                {"scene", qEnvironmentVariable("MELEE_SCENE")}, {"mods", qEnvironmentVariable("MELEE_MODS_DIR")},
                {"wb", qEnvironmentVariable("MELEE_WB_DIR")}, {"netplay", qEnvironmentVariable("MELEE_NETPLAY")},
                {"x", qEnvironmentVariable("MELEE_WINDOW_X")}, {"y", qEnvironmentVariable("MELEE_WINDOW_Y")},
                {"custom", qEnvironmentVariable("WB_TEST_ENV")}, {"port", qEnvironmentVariable("MELEE_CONSOLE_PORT")},
                {"cwd", QDir::currentPath()}});
        }, quint16(qEnvironmentVariableIntValue("MELEE_CONSOLE_PORT")));
        return app.exec();
    }
    EngineLinkTest test;
    return QTest::qExec(&test, argc, argv);
}
#include "engine_link_test.moc"
