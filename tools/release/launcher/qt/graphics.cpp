#include "graphics.h"
#include "launcher_core.h"
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QRegularExpression>
#include <algorithm>
#include <stdexcept>
namespace launcher {
QString GraphicsDevice::selector() const { return QString::number(vendor, 16).rightJustified(4, '0') + ":" + QString::number(device, 16).rightJustified(4, '0'); }
bool GraphicsReport::ready() const { return valid && error.isEmpty() && std::any_of(devices.begin(), devices.end(), [](const auto &d) { return d.usable; }); }
bool GraphicsReport::matchesSelection(const QString &selection) const {
    if (!ready()) return false;
    if (selection == "auto" || selection.isEmpty()) return true;
    // An ignored device-selection layer must never silently pick another GPU.
    return std::all_of(devices.begin(), devices.end(), [&](const auto &d) { return d.selector() == selection; });
}
QString GraphicsReport::summary() const {
    QStringList lines;
    if (!error.isEmpty()) lines << error;
    if (devices.isEmpty()) lines << "No 32-bit Vulkan devices detected.";
    for (const auto &d : devices) lines << d.name + " (" + d.selector() + ", Vulkan " + d.api + "): " + (d.usable ? "32-bit device creation passed" : d.reason);
    if (ready()) lines << "This checks Vulkan device creation. The game's renderer and display still need to initialize successfully.";
    return lines.join('\n');
}
GraphicsReport parseGraphicsReport(const QByteArray &json, int exitCode) {
    GraphicsReport report;
    QJsonParseError parseError;
    auto doc = QJsonDocument::fromJson(json, &parseError);
    if (parseError.error != QJsonParseError::NoError || !doc.isObject() || doc["format"].toInt() != 1 || doc["bits"].toInt() != 32 || !doc["devices"].isArray()) {
        report.error = "The 32-bit graphics check returned an invalid report."; return report;
    }
    report.valid = true; report.error = doc["error"].toString();
    for (const auto &value : doc["devices"].toArray()) {
        const auto d = value.toObject();
        if (!d["name"].isString() || !d["vendor"].isDouble() || !d["device"].isDouble() || !d["usable"].isBool()) {
            report.valid = false; report.error = "The graphics check returned an invalid device."; return report;
        }
        report.devices.append({d["name"].toString(), d["api"].toString(), d["reason"].toString(), quint32(d["vendor"].toDouble()), quint32(d["device"].toDouble()), d["usable"].toBool()});
    }
    if (exitCode != 0 && report.error.isEmpty()) report.error = "The 32-bit Vulkan check failed (exit " + QString::number(exitCode) + ").";
    return report;
}
QProcessEnvironment graphicsEnvironment(QProcessEnvironment env, const QString &selection) {
    if (selection.isEmpty() || selection == "auto") return env;
    static const QRegularExpression pattern("^[0-9a-f]{4}:[0-9a-f]{4}$");
    if (!pattern.match(selection).hasMatch()) throw std::runtime_error("Invalid graphics device selection. Choose Automatic and check graphics again.");
    for (const auto &key : {"DRI_PRIME", "MESA_VK_DEVICE_SELECT", "MESA_VK_DEVICE_SELECT_FORCE_DEFAULT_DEVICE", "__NV_PRIME_RENDER_OFFLOAD", "__VK_LAYER_NV_optimus", "__GLX_VENDOR_LIBRARY_NAME"}) env.remove(key);
    if (selection.startsWith("10de:")) {
        env.insert("__NV_PRIME_RENDER_OFFLOAD", "1"); env.insert("__VK_LAYER_NV_optimus", "NVIDIA_only"); env.insert("__GLX_VENDOR_LIBRARY_NAME", "nvidia");
    } else {
        env.insert("DRI_PRIME", selection + "!"); env.insert("MESA_VK_DEVICE_SELECT", selection); env.insert("MESA_VK_DEVICE_SELECT_FORCE_DEFAULT_DEVICE", "1");
    }
    return env;
}
QString graphicsDriverHelp(const QString &osRelease) {
    QString id, like;
    for (auto line : osRelease.split('\n')) {
        auto value = line.section('=', 1).trimmed(); value.remove('"'); value.remove('\'');
        if (line.startsWith("ID=")) id = value;
        if (line.startsWith("ID_LIKE=")) like = value;
    }
    const auto family = id + " " + like;
    QString help = "The launcher is 64-bit, but the game needs a working 32-bit Vulkan driver (Vulkan 1.1 or newer).\n\n";
    if (family.contains(QRegularExpression("\\b(ubuntu|debian)\\b")))
        help += "Ubuntu/Debian: enable the i386 architecture. AMD/Intel: install libvulkan1:i386 and mesa-vulkan-drivers:i386 from your distribution. NVIDIA: install the matching 32-bit NVIDIA userspace libraries; Ubuntu uses libnvidia-gl-<installed-driver-version>:i386, Debian uses nvidia-driver-libs:i386. Match the active driver version; do not install a guessed version.\n";
    else if (family.contains(QRegularExpression("\\b(arch|manjaro|endeavouros)\\b")))
        help += "Arch family: enable multilib. Install lib32-vulkan-icd-loader and, for AMD, lib32-vulkan-radeon (Intel: lib32-vulkan-intel). NVIDIA: use lib32-nvidia-utils matching the active driver; legacy drivers need their matching legacy package.\n";
    else if (family.contains(QRegularExpression("\\b(fedora|rhel)\\b")))
        help += "Fedora family: AMD/Intel need vulkan-loader.i686 and mesa-vulkan-drivers.i686. NVIDIA needs matching i686 userspace libraries from the same repository as the active driver.\n";
    else help += "Install your distribution's 32-bit Vulkan loader and GPU driver. AMD/Intel use Mesa Vulkan drivers; NVIDIA needs 32-bit userspace libraries matching its active driver.\n";
    help += "\nWith AMD and NVIDIA together, install the 32-bit driver for the GPU you choose. Check graphics again after updating drivers. A 64-bit vulkaninfo result alone does not verify the game's drivers.\nDriver changes are performed by you through your distribution's package manager.";
    return help;
}
QString graphicsStartupFailure(const QString &runDir, const QString &osRelease) {
    for (const auto &name : {"launcher-process.log", "melee-pc.log"}) {
        QFile file(runDir + "/" + name); if (!file.open(QIODevice::ReadOnly)) continue;
        if (file.size() > 256 * 1024) file.seek(file.size() - 256 * 1024);
        const auto log = QString::fromUtf8(file.readAll());
        if (!log.contains("Failed to initialize SDL renderer") && !log.contains("Failed to create adapter") && !log.contains("Failed to create renderer")) continue;
        QStringList errors;
        for (auto line : log.split('\n')) if (line.contains("No supported adapters") || line.contains("default EGL display") || line.contains("Failed to initialize SDL renderer")) {
            if (!errors.contains(line.trimmed())) errors << line.trimmed();
            if (errors.size() >= 6) break;
        }
        return "The game could not initialize graphics.\n\n" + errors.join('\n') + "\n\n" + graphicsDriverHelp(osRelease);
    }
    return {};
}
}
