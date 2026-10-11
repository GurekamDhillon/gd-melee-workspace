#pragma once
#include "launcher_core.h"
#include <QDate>
#include <QDateTime>
#include <QNetworkAccessManager>
#include <QTimer>
#include <QUrl>
#include <array>
#include <optional>

namespace launcher {
struct Version {
    std::array<int, 4> parts{};
    static std::optional<Version> parse(const QString &text);
    QString text() const;
    int compare(const Version &other) const;
};
enum class ManifestPolicy { NotifyOnlyUnsigned, RequireSignature };
struct UpdateManifest {
    Version version;
    QDate released;
    int protocol = -1;
    QUrl notesUrl, packageUrl;
    QString notesEn, notesEs, packageSha256, filesManifestSha256;
    qint64 packageSize = 0;
};
// Phase 1 validates bounded metadata only. RequireSignature always fails closed:
// offline keys and the Ed25519 verifier are prerequisites of phase 2.
std::optional<UpdateManifest> parseUpdateManifest(const QByteArray &raw,
    ManifestPolicy policy = ManifestPolicy::NotifyOnlyUnsigned, QString *error = nullptr);
bool updateCheckDue(const Settings &settings, const QDateTime &now);
bool updateChecksSuppressed(const QStringList &args, const QProcessEnvironment &env);
struct UpdateCheckConfig {
    QUrl url;
    QString installedVersion;
    int installedProtocol = -1;
    bool suppressed = false;
    int connectTimeoutMs = 5000, totalTimeoutMs = 15000;
};
UpdateCheckConfig updateConfig(const QString &appDir, bool suppressed = false);
enum class UpdateState { Idle, Checking, UpToDate, Available, Skipped, Failed, Disabled };
class UpdateChecker : public QObject {
    Q_OBJECT
public:
    UpdateChecker(Settings &settings, QString userDir, UpdateCheckConfig config, QObject *parent = nullptr);
    ~UpdateChecker() override;
    bool check(bool manual = false, const QDateTime &now = QDateTime::currentDateTimeUtc());
    void setEnabled(bool enabled);
    void setGameRunning(bool running);
    void skipVersion();
    bool enabled() const { return settings_.flag("update_enabled", true); }
    bool suppressed() const { return config_.suppressed; }
    bool gameRunning() const { return gameRunning_; }
    UpdateState state() const { return state_; }
    const QString &error() const { return error_; }
    const std::optional<UpdateManifest> &manifest() const { return manifest_; }
    const std::optional<UpdateManifest> &cachedManifest() const { return cached_; }
signals:
    void changed();
private:
    Settings &settings_;
    QString userDir_;
    UpdateCheckConfig config_;
    QNetworkAccessManager network_;
    QNetworkReply *reply_ = nullptr;
    QTimer connectTimer_, totalTimer_;
    QByteArray bytes_;
    UpdateState state_ = UpdateState::Idle;
    bool gameRunning_ = false;
    QString error_;
    std::optional<UpdateManifest> manifest_, cached_;
    void persist() noexcept;
    void cancel();
    void readResponse();
    void finish();
};
}
