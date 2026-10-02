#include "graphics.h"
#include "launcher_core.h"
#include <QTemporaryDir>
#include <QtTest>
using namespace launcher;
class GraphicsTests : public QObject {
    Q_OBJECT
private slots:
    void rejects64BitAndMalformedReports() {
        QVERIFY(!parseGraphicsReport("{}", 0).ready());
        QVERIFY(!parseGraphicsReport("not json", 0).ready());
        QVERIFY(!parseGraphicsReport(R"({"format":1,"bits":64,"devices":[{"name":"GPU","vendor":4098,"device":29772,"usable":true}]})", 0).ready());
    }
    void usable32BitDeviceAndDriverFailure() {
        auto report = parseGraphicsReport(R"({"format":1,"bits":32,"devices":[{"name":"AMD Radeon RX 7900 XTX","vendor":4098,"device":29772,"usable":true,"api":"1.3","reason":""}]})", 0);
        QVERIFY(report.ready()); QCOMPARE(report.devices[0].selector(), "1002:744c");
        QVERIFY(!parseGraphicsReport(R"({"format":1,"bits":32,"devices":[],"error":"vkCreateInstance: -9"})", 2).ready());
        QVERIFY(!parseGraphicsReport(R"({"format":1,"bits":32,"devices":[{"name":"GPU","vendor":4098,"device":1,"usable":false,"reason":"Vulkan 1.0"}]})", 0).ready());
        QVERIFY(!parseGraphicsReport(R"({"format":1,"bits":32,"devices":[{"name":"GPU","vendor":4098,"device":1,"usable":true}]})", 2).ready());
    }
    void gpuSelectionIsScopedAndVerified() {
        QProcessEnvironment env; env.insert("KEEP", "value");
        env.insert("DRI_PRIME", "inherited");
        auto automatic = graphicsEnvironment(env, "auto"); QCOMPARE(automatic.value("DRI_PRIME"), "inherited");
        auto amd = graphicsEnvironment(env, "1002:744c");
        QCOMPARE(amd.value("DRI_PRIME"), "1002:744c!");
        QCOMPARE(amd.value("MESA_VK_DEVICE_SELECT"), "1002:744c");
        QCOMPARE(amd.value("MESA_VK_DEVICE_SELECT_FORCE_DEFAULT_DEVICE"), "1");
        QCOMPARE(amd.value("KEEP"), "value");
        auto nvidia = graphicsEnvironment(env, "10de:1b06");
        QVERIFY(!nvidia.contains("DRI_PRIME"));
        QCOMPARE(nvidia.value("__VK_LAYER_NV_optimus"), "NVIDIA_only");
        QCOMPARE(nvidia.value("__NV_PRIME_RENDER_OFFLOAD"), "1");
        auto mixed = parseGraphicsReport(R"({"format":1,"bits":32,"devices":[{"name":"AMD","vendor":4098,"device":29772,"usable":true},{"name":"NVIDIA","vendor":4318,"device":6918,"usable":true}]})", 0);
        QVERIFY(!mixed.matchesSelection("1002:744c")); QVERIFY(mixed.matchesSelection("auto"));
        auto isolated = parseGraphicsReport(R"({"format":1,"bits":32,"devices":[{"name":"AMD","vendor":4098,"device":29772,"usable":true}]})", 0);
        QVERIFY(isolated.matchesSelection("1002:744c")); QVERIFY(!isolated.matchesSelection("10de:1b06"));
        QVERIFY_EXCEPTION_THROWN(graphicsEnvironment(env, "bad;command"), std::runtime_error);
    }
    void distroGuidanceDoesNotGuessNvidiaVersion() {
        auto ubuntu = graphicsDriverHelp("ID=ubuntu\nVERSION_ID=24.04\n");
        QVERIFY(ubuntu.contains("mesa-vulkan-drivers:i386")); QVERIFY(ubuntu.contains("libnvidia-gl"));
        QVERIFY(ubuntu.contains("32-bit")); QVERIFY(!ubuntu.contains("libnvidia-gl-550"));
        auto arch = graphicsDriverHelp("ID=arch\n"); QVERIFY(arch.contains("lib32-vulkan-radeon")); QVERIFY(arch.contains("lib32-nvidia-utils"));
        auto fedora = graphicsDriverHelp("ID=fedora\n"); QVERIFY(fedora.contains("mesa-vulkan-drivers.i686"));
        QVERIFY(!graphicsDriverHelp("ID=unknown\n").contains("apt"));
    }
    void recognizesUserCrashWithoutMisclassifyingGameplay() {
        QTemporaryDir dir;
        writeAtomic(dir.path() + "/launcher-process.log", "aurora[error] aurora::gpu: Failed to create adapter: No supported adapters\naurora[fatal] Failed to initialize SDL renderer: Couldn't find matching render driver\n");
        auto message = graphicsStartupFailure(dir.path(), "ID=debian\n");
        QVERIFY(message.contains("32-bit")); QVERIFY(message.contains("No supported adapters"));
        writeAtomic(dir.path() + "/launcher-process.log", "gw: PANIC fighter crashed\n");
        QVERIFY(graphicsStartupFailure(dir.path(), "ID=debian\n").isEmpty());
    }
};
QTEST_GUILESS_MAIN(GraphicsTests)
#include "graphics_tests.moc"
