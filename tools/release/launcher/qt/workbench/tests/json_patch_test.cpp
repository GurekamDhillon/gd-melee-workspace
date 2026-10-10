#include "json_patch.h"
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QtTest>
using namespace wb;

static const QString kDoc = QStringLiteral(
    "{\n  \"version\": 1,\n  \"moves\": [\n    {\n      \"name\": \"jab1\",\n      \"pick\": {\"clip\": \"A\", \"crop_start\": 9},\n"
    "      \"tag\": \"x,}\\\"\"\n    },\n    {\n      \"name\": \"dair\",\n      \"pick\": {\"clip\": \"B\", \"crop_start\": 2}\n    }\n  ],\n"
    "  \"zeta\": 1,\n  \"alpha\": 2\n}\n");

class JsonPatchTest : public QObject {
    Q_OBJECT
private slots:
    void findsNestedValue() {
        int s, e;
        QVERIFY(jsonFind(kDoc, {"moves", "#1", "pick", "clip"}, &s, &e));
        QCOMPARE(kDoc.mid(s, e - s), QString("\"B\""));
    }
    void missingPathFails() {
        int s, e;
        QVERIFY(!jsonFind(kDoc, {"moves", "#5"}, &s, &e));
        QVERIFY(!jsonFind(kDoc, {"nope"}, &s, &e));
    }
    void stringWithBracesAndEscapesIsSkipped() {
        int s, e;
        QVERIFY(jsonFind(kDoc, {"zeta"}, &s, &e));
        QCOMPARE(kDoc.mid(s, e - s), QString("1"));
    }
    void replaceLeavesEveryOtherByteIdentical() {
        QString err;
        QString out = jsonReplace(kDoc, {"moves", "#1", "pick", "clip"}, "\"C\"", &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QString expect = kDoc;
        expect.replace("\"B\"", "\"C\"");
        QCOMPARE(out, expect);
    }
    void replaceKeepsKeyOrder() {
        QString err;
        QString out = jsonReplace(kDoc, {"zeta"}, "7", &err);
        QVERIFY(out.indexOf("zeta") < out.indexOf("alpha"));
    }
    void insertKeyAppendsWithIndent() {
        QString err;
        QString out = jsonInsertKey(kDoc, {"moves", "#0"}, "ground", "{\"mode\": \"hover\"}", &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QVERIFY(out.contains("\"tag\": \"x,}\\\"\",\n      \"ground\": {\"mode\": \"hover\"}\n    }"));
        QJsonParseError pe;
        QJsonDocument::fromJson(out.toUtf8(), &pe);
        QCOMPARE(pe.error, QJsonParseError::NoError);
    }
    void insertIntoEmptyObject() {
        QString err;
        QString out = jsonInsertKey("{\n}\n", {}, "a", "1", &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QJsonParseError pe;
        QCOMPARE(QJsonDocument::fromJson(out.toUtf8(), &pe).object().value("a").toInt(), 1);
    }
    void replaceMissingPathReportsError() {
        QString err;
        QVERIFY(jsonReplace(kDoc, {"moves", "#9", "name"}, "1", &err).isNull());
        QVERIFY(!err.isEmpty());
    }
    void scalarFormatting() {
        QCOMPARE(jsonScalar(QJsonValue(2.8)), QString("2.8"));
        QCOMPARE(jsonScalar(QJsonValue(9)), QString("9"));
        QCOMPARE(jsonScalar(QJsonValue("a\"b")), QString("\"a\\\"b\""));
    }
    void findsEscapedObjectKeys() {
        const QString doc = QString::fromUtf8("{\"na\\u006de\":{\"quote\\\"key\":{\"back\\\\slash\":\"found\"}},\"#0\":9}");
        int s, e;
        QVERIFY(jsonFind(doc, {"name", "quote\"key", "back\\slash"}, &s, &e));
        QCOMPARE(doc.mid(s, e - s), QString("\"found\""));
        QVERIFY(jsonFind(doc, {"#0"}, &s, &e));
        QCOMPARE(doc.mid(s, e - s), QString("9"));
    }
    void rootAndArrayValuesHaveExactSpans() {
        const QString doc = " \r\n[null, true, -1.25e+2, {\"x\": [false, \"end\"]}]\t\n";
        int s, e;
        QVERIFY(jsonFind(doc, {}, &s, &e));
        QCOMPARE(doc.mid(s, e - s), QString("[null, true, -1.25e+2, {\"x\": [false, \"end\"]}]"));
        QVERIFY(jsonFind(doc, {"#2"}, &s, &e));
        QCOMPARE(doc.mid(s, e - s), QString("-1.25e+2"));
        QVERIFY(jsonFind(doc, {"#3", "x", "#0"}, &s, &e));
        QCOMPARE(doc.mid(s, e - s), QString("false"));
        QVERIFY(jsonFind(" \t-1.25e+2\r\n", {}, &s, &e));
        QCOMPARE(s, 2);
        QCOMPARE(e, 10);
        QString err;
        QCOMPARE(jsonReplace(" \ttrue\r\n", {}, "false", &err), QString(" \tfalse\r\n"));
    }
    void rejectsInvalidArrayIndices() {
        int s, e;
        for (const QString &step : {"#", "#x", "#-1", "#+1", "# 1", "#1.0", "#2147483648", "0"})
            QVERIFY2(!jsonFind("[10,20]", {step}, &s, &e), qPrintable(step));
        QVERIFY(!jsonFind(kDoc, {"version", "child"}, &s, &e));
        QVERIFY(!jsonFind(kDoc, {"moves", "name"}, &s, &e));
    }
    void malformedDocumentsAreRejected_data() {
        QTest::addColumn<QString>("doc");
        QTest::newRow("empty") << QString("");
        QTest::newRow("only-whitespace") << QString(" \r\n");
        QTest::newRow("mismatched-close") << QString("{\"x\": [1}}");
        QTest::newRow("missing-comma") << QString("{\"x\":1 \"y\":2}");
        QTest::newRow("missing-value") << QString("{\"x\":}");
        QTest::newRow("trailing-comma") << QString("{\"x\":1,}");
        QTest::newRow("trailing-garbage") << QString("{\"x\":1} garbage");
        QTest::newRow("two-roots") << QString("{},{}");
        QTest::newRow("invalid-literal") << QString("truth");
        QTest::newRow("invalid-number") << QString("01");
        QTest::newRow("unterminated-string") << QString("\"abc");
        QTest::newRow("invalid-escape") << QString::fromUtf8(R"JSON({"x":"\q"})JSON");
    }
    void malformedDocumentsAreRejected() {
        QFETCH(QString, doc);
        int s, e;
        QString err;
        QVERIFY(!jsonFind(doc, {}, &s, &e));
        QVERIFY(jsonReplace(doc, {}, "0", &err).isNull());
        QVERIFY(!err.isEmpty());
        err.clear();
        QVERIFY(jsonInsertKey(doc, {}, "new", "0", &err).isNull());
        QVERIFY(!err.isEmpty());
    }
    void malformedNewValuesAreRejected() {
        for (const QString &value : {"", "1,2", "{", "undefined", "[1,]"}) {
            QString err;
            QVERIFY(jsonReplace(kDoc, {"zeta"}, value, &err).isNull());
            QVERIFY(!err.isEmpty());
            err.clear();
            QVERIFY(jsonInsertKey(kDoc, {}, "new", value, &err).isNull());
            QVERIFY(!err.isEmpty());
        }
    }
    void ambiguousKeysCannotBeEdited() {
        const QString doc = QString::fromUtf8(R"JSON({"a":1,"\u0061":2})JSON");
        int s, e;
        QString err;
        QVERIFY(!jsonFind(doc, {"a"}, &s, &e));
        QVERIFY(jsonReplace(doc, {"a"}, "3", &err).isNull());
        QVERIFY(!err.isEmpty());
        err.clear();
        QVERIFY(jsonInsertKey(doc, {}, "a", "3", &err).isNull());
        QVERIFY(!err.isEmpty());
    }
    void insertUsesParentMemberIndent() {
        const QString doc = "{\n  \"outer\": {\n    \"nested\": {\n      \"deep\": 1\n    }\n  },\n  \"keep\": 2\n}\n";
        QString err;
        const QString out = jsonInsertKey(doc, {"outer"}, "new", "true", &err);
        QVERIFY2(!out.isNull(), qPrintable(err));
        QCOMPARE(out, QString("{\n  \"outer\": {\n    \"nested\": {\n      \"deep\": 1\n    },\n    \"new\": true\n  },\n  \"keep\": 2\n}\n"));
    }
    void insertPreservesTabsAndWindowsLineEndings() {
        const QString doc = "{\r\n\t\"zeta\": 1,\r\n\t\"alpha\": [\r\n\t\t1\r\n\t]\r\n}\r\n";
        QString err;
        QCOMPARE(jsonInsertKey(doc, {}, "new", "null", &err),
                 QString("{\r\n\t\"zeta\": 1,\r\n\t\"alpha\": [\r\n\t\t1\r\n\t],\r\n\t\"new\": null\r\n}\r\n"));
        QCOMPARE(jsonReplace(doc, {"zeta"}, "7", &err),
                 QString("{\r\n\t\"zeta\": 7,\r\n\t\"alpha\": [\r\n\t\t1\r\n\t]\r\n}\r\n"));
    }
    void insertKeepsInlineLayoutAndEscapesKey() {
        QString err;
        QCOMPARE(jsonInsertKey("{\"z\":0 }\n", {}, "a\"b\\c", "[1,2]", &err),
                 QString("{\"z\":0, \"a\\\"b\\\\c\": [1,2] }\n"));
        QCOMPARE(jsonInsertKey("{\"z\": {\n  \"inner\": 0\n}}", {}, "a", "1", &err),
                 QString("{\"z\": {\n  \"inner\": 0\n}, \"a\": 1}"));
    }
    void insertIntoEmptyObjectsKeepsWhitespace() {
        QString err;
        QCOMPARE(jsonInsertKey("{}\n", {}, "a", "1", &err), QString("{\"a\": 1}\n"));
        QCOMPARE(jsonInsertKey("{  }\n", {}, "a", "1", &err), QString("{\"a\": 1  }\n"));
        QCOMPARE(jsonInsertKey("{\r\n}\r\n", {}, "a", "1", &err),
                 QString("{\r\n  \"a\": 1\r\n}\r\n"));
        QCOMPARE(jsonInsertKey("{\n  \"child\": {\n  }\n}\n", {"child"}, "a", "1", &err),
                 QString("{\n  \"child\": {\n    \"a\": 1\n  }\n}\n"));
    }
    void insertRefusesMissingOrNonObjectTargetsAndExistingKeys() {
        for (const JsonPath &path : {JsonPath{"missing"}, JsonPath{"moves"}, JsonPath{"version"}}) {
            QString err;
            QVERIFY(jsonInsertKey(kDoc, path, "a", "1", &err).isNull());
            QVERIFY(!err.isEmpty());
        }
        QString err;
        QVERIFY(jsonInsertKey(kDoc, {}, "zeta", "1", &err).isNull());
        QVERIFY(!err.isEmpty());
    }
    void successfulEditsClearErrorsAndAllowNoErrorPointer() {
        QString err = "old failure";
        QVERIFY(!jsonReplace(kDoc, {"zeta"}, "7", &err).isNull());
        QVERIFY(err.isEmpty());
        err = "old failure";
        QVERIFY(!jsonInsertKey(kDoc, {}, "new", "7", &err).isNull());
        QVERIFY(err.isEmpty());
        QVERIFY(!jsonReplace(kDoc, {"zeta"}, "7", nullptr).isNull());
        QVERIFY(!jsonInsertKey(kDoc, {}, "new", "7", nullptr).isNull());
        QVERIFY(jsonReplace(kDoc, {"missing"}, "7", nullptr).isNull());
        QVERIFY(jsonInsertKey(kDoc, {"missing"}, "new", "7", nullptr).isNull());
    }
    void scalarFormattingCoversAllValueTypes() {
        QCOMPARE(jsonScalar(QJsonValue()), QString("null"));
        QCOMPARE(jsonScalar(QJsonValue(true)), QString("true"));
        QCOMPARE(jsonScalar(QJsonValue(false)), QString("false"));
        QCOMPARE(jsonScalar(QJsonArray{1, "two", QJsonValue()}), QString("[1,\"two\",null]"));
        QCOMPARE(jsonScalar(QJsonObject{{"x", 2}}), QString("{\"x\":2}"));
        const double value = 1.2345678901234567;
        const auto parsed = QJsonDocument::fromJson(("[" + jsonScalar(QJsonValue(value)) + "]").toUtf8());
        QCOMPARE(parsed.array()[0].toDouble(), value);
    }

};
QTEST_MAIN(JsonPatchTest)
#include "json_patch_test.moc"
