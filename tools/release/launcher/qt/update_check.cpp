#include "update_check.h"
#include <QFileInfo>
#include <QJsonDocument>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QRegularExpression>
#include <QSslSocket>
#include <cmath>
#include <limits>

namespace launcher {
constexpr qint64 kMaxManifest = 65536;
static const QString kDefaultUrl = "https://github.com/GurekamDhillon/gd-melee-workspace/releases/latest/download/update.json";
std::optional<Version> Version::parse(const QString &text) {
    static const QRegularExpression re("^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(?:\\.(0|[1-9][0-9]*))?(?:[-+][^\\r\\n]*|\\s[^\\r\\n]*)?$");
    const auto m = re.match(text.trimmed());
    if (!m.hasMatch()) return {};
    Version out;
    for (int i = 0; i < 4; ++i) {
        if (m.captured(i + 1).isEmpty()) continue;
        bool ok = false; out.parts[i] = m.captured(i + 1).toInt(&ok);
        if (!ok) return {};
    }
    return out;
}
QString Version::text() const {
    QString result = QString("%1.%2.%3").arg(parts[0]).arg(parts[1]).arg(parts[2]);
    if (parts[3]) result += "." + QString::number(parts[3]);
    return result;
}
int Version::compare(const Version &other) const { return parts < other.parts ? -1 : parts > other.parts ? 1 : 0; }
static bool stableVersion(const QString &text) {
    static const QRegularExpression re("^[0-9]+\\.[0-9]+\\.[0-9]+(?:\\.[0-9]+)?$");
    return re.match(text).hasMatch() && bool(Version::parse(text));
}
static bool httpsUrl(const QUrl &url) {
    return url.isValid() && url.scheme() == "https" && !url.host().isEmpty() && url.userInfo().isEmpty() && !url.hasFragment() && url.toString().size() <= 4096;
}
static bool updateUrl(const QUrl &url) {
    if (httpsUrl(url)) return true;
    return url.isValid() && url.scheme() == "http" && (url.host() == "127.0.0.1" || url.host() == "::1") && url.userInfo().isEmpty() && !url.hasFragment() && url.toString().size() <= 4096;
}
static bool integer(const QJsonValue &v, double min, double max) {
    const double n = v.toDouble(-1);
    return v.isDouble() && std::isfinite(n) && n >= min && n <= max && std::floor(n) == n;
}
std::optional<UpdateManifest> parseUpdateManifest(const QByteArray &raw, ManifestPolicy policy, QString *error) {
    if (error) error->clear();
    auto bad = [&](const QString &why) -> std::optional<UpdateManifest> { if (error) *error = why; return {}; };
    if (policy == ManifestPolicy::RequireSignature) return bad("Signature verification is not configured; unsigned manifests are notify-only.");
    if (raw.isEmpty() || raw.size() > kMaxManifest) return bad("Manifest exceeds the metadata limit.");
    QJsonParseError parseError; const auto doc = QJsonDocument::fromJson(raw, &parseError);
    if (parseError.error != QJsonParseError::NoError || !doc.isObject()) return bad("Invalid manifest JSON.");
    const auto o = doc.object();
    if (!integer(o["schema"], 1, 1) || o["channel"].toString() != "stable" || !o["critical"].isBool()) return bad("Unsupported manifest schema/channel.");
    if (!stableVersion(o["version"].toString()) || !stableVersion(o["min_launcher_for_self_update"].toString())) return bad("Invalid stable version.");
    UpdateManifest m; m.version = *Version::parse(o["version"].toString());
    const auto date = o["released"].toString(); m.released = QDate::fromString(date, Qt::ISODate);
    if (!m.released.isValid() || m.released.toString(Qt::ISODate) != date) return bad("Invalid release date.");
    if (!integer(o["netplay_protocol"], 1, std::numeric_limits<int>::max())) return bad("Invalid protocol.");
    m.protocol = o["netplay_protocol"].toInt();
    m.notesUrl = QUrl(o["notes_url"].toString(), QUrl::StrictMode);
    const auto notes = o["notes_short"].toObject();
    m.notesEn = notes["en"].toString().trimmed(); m.notesEs = notes["es"].toString().trimmed();
    if (m.notesEn.isEmpty() || m.notesEs.isEmpty() || m.notesEn.toUcs4().size() > 2048 || m.notesEs.toUcs4().size() > 2048) return bad("Both bounded note translations are required.");
    const auto package = o["package"].toObject();
    m.packageUrl = QUrl(package["url"].toString(), QUrl::StrictMode);
    if (!httpsUrl(m.notesUrl) || !httpsUrl(m.packageUrl)) return bad("Release/package URLs must use HTTPS without credentials.");
    if (!integer(package["size"], 1, 9007199254740991.0)) return bad("Invalid package size.");
    m.packageSize = qint64(package["size"].toDouble());
    static const QRegularExpression sha("^[0-9a-f]{64}$");
    m.packageSha256 = package["sha256"].toString(); m.filesManifestSha256 = o["files_manifest_sha256"].toString();
    if (!sha.match(m.packageSha256).hasMatch() || !sha.match(m.filesManifestSha256).hasMatch()) return bad("Invalid SHA-256 metadata.");
    return m;
}
bool updateCheckDue(const Settings &settings, const QDateTime &now) {
    if (!settings.flag("update_enabled", true) || !now.isValid()) return false;
    const auto previous = QDateTime::fromString(settings.option("update_last_attempt"), Qt::ISODateWithMs);
    return !previous.isValid() || previous > now || previous.secsTo(now) >= 24 * 60 * 60;
}
bool updateChecksSuppressed(const QStringList &args, const QProcessEnvironment &env) {
    return args.contains("--no-update-check") || env.value("GDMELEE_NO_UPDATE_CHECK") == "1";
}
UpdateCheckConfig updateConfig(const QString &appDir, bool suppressed) {
    UpdateCheckConfig c; c.url = QUrl(kDefaultUrl); c.suppressed = suppressed;
    try {
        const auto metadata = readText(appDir + "/version.txt", 16384);
        c.installedVersion = metadata.section('\n', 0, 0).trimmed();
        static const QRegularExpression re("^netplay_protocol\\s+([0-9]+)\\s*$", QRegularExpression::MultilineOption);
        auto matches = re.globalMatch(metadata);
        if (matches.hasNext()) {
            const auto m = matches.next(); bool ok = false; const int protocol = m.captured(1).toInt(&ok);
            if (!matches.hasNext() && ok && protocol > 0) c.installedProtocol = protocol;
        }
    } catch (...) {}
    if (QFileInfo::exists(appDir + "/update_url.txt")) {
        try { c.url = QUrl(readText(appDir + "/update_url.txt", 4096).trimmed(), QUrl::StrictMode); }
        catch (...) { c.url = {}; }
        if (!updateUrl(c.url)) c.url = {};
    }
    return c;
}
UpdateChecker::UpdateChecker(Settings &s, QString u, UpdateCheckConfig c, QObject *p)
    : QObject(p), settings_(s), userDir_(std::move(u)), config_(std::move(c)) {
#ifdef Q_OS_WIN
    // Select the deployed native backend; do not depend on external OpenSSL DLLs.
    if (QSslSocket::activeBackend() != "schannel") QSslSocket::setActiveBackend("schannel");
#endif
    state_ = !enabled() || suppressed() ? UpdateState::Disabled : UpdateState::Idle;
    try { cached_ = parseUpdateManifest(readText(userDir_ + "/updates/last-manifest.json", kMaxManifest).toUtf8()); } catch (...) {}
    connectTimer_.setSingleShot(true); totalTimer_.setSingleShot(true);
    auto timeout = [this] { if (reply_) { error_ = "Update request timeout."; reply_->abort(); } };
    connect(&connectTimer_, &QTimer::timeout, this, timeout); connect(&totalTimer_, &QTimer::timeout, this, timeout);
}
void UpdateChecker::persist() noexcept {
    // Settings I/O must never turn a background check into a launch-blocking dialog.
    try { settings_.save(userDir_); } catch (...) {}
}
UpdateChecker::~UpdateChecker() { cancel(); }
bool UpdateChecker::check(bool manual, const QDateTime &now) {
    if (suppressed() || gameRunning_ || reply_ || (!manual && !updateCheckDue(settings_, now))) return false;
    settings_.options["update_last_attempt"] = now.toUTC().toString(Qt::ISODateWithMs); persist();
    manifest_.reset(); error_.clear(); bytes_.clear();
    const auto version = Version::parse(config_.installedVersion);
    if (!updateUrl(config_.url) || !version || (config_.url.scheme() == "https" && !QSslSocket::supportsSsl())) {
        state_ = UpdateState::Failed; error_ = "Update endpoint, installed version or TLS runtime is unavailable."; emit changed(); return false;
    }
    QNetworkRequest request(config_.url);
    request.setRawHeader("User-Agent", "GDMeleeLauncher/" + version->text().toUtf8());
    request.setRawHeader("Accept", "application/json");
    request.setRawHeader("Accept-Language", "en,es"); // fixed, rather than Qt's OS-locale default
    request.setAttribute(QNetworkRequest::CookieLoadControlAttribute, QNetworkRequest::Manual);
    request.setAttribute(QNetworkRequest::CookieSaveControlAttribute, QNetworkRequest::Manual);
    request.setAttribute(QNetworkRequest::AuthenticationReuseAttribute, QNetworkRequest::Manual);
    request.setAttribute(QNetworkRequest::CacheLoadControlAttribute, QNetworkRequest::AlwaysNetwork);
    request.setAttribute(QNetworkRequest::CacheSaveControlAttribute, false);
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::UserVerifiedRedirectPolicy);
    request.setMaximumRedirectsAllowed(5);
    reply_ = network_.get(request); reply_->setReadBufferSize(kMaxManifest + 1);
    connect(reply_, &QNetworkReply::redirected, this, [this, secure = config_.url.scheme() == "https"](const QUrl &url) mutable {
        // An HTTPS source can never downgrade, including to loopback HTTP.
        // Qt may already report the target in reply->url() at this signal.
        if (!updateUrl(url) || (secure && url.scheme() != "https")) {
            error_ = "Unsafe update redirect."; reply_->abort(); return;
        }
        secure = url.scheme() == "https";
        bytes_.clear(); reply_->redirectAllowed();
    });
    connect(reply_, &QNetworkReply::encrypted, this, [this] { connectTimer_.stop(); });
    connect(reply_, &QNetworkReply::metaDataChanged, this, [this] {
        connectTimer_.stop();
        if (reply_->header(QNetworkRequest::ContentLengthHeader).toLongLong() > kMaxManifest) { error_ = "Manifest exceeds the metadata limit."; reply_->abort(); }
    });
    connect(reply_, &QNetworkReply::readyRead, this, &UpdateChecker::readResponse);
    connect(reply_, &QNetworkReply::finished, this, &UpdateChecker::finish);
    connectTimer_.start(config_.connectTimeoutMs); totalTimer_.start(config_.totalTimeoutMs);
    state_ = UpdateState::Checking; emit changed(); return true;
}
void UpdateChecker::cancel() {
    connectTimer_.stop(); totalTimer_.stop();
    if (reply_) { auto *r = reply_; reply_ = nullptr; r->disconnect(this); r->abort(); r->deleteLater(); }
    if (state_ == UpdateState::Checking) state_ = enabled() && !suppressed() ? UpdateState::Idle : UpdateState::Disabled;
}
void UpdateChecker::setEnabled(bool on) {
    settings_.options["update_enabled"] = on ? "1" : "0"; persist();
    if (!on) { cancel(); state_ = UpdateState::Disabled; manifest_.reset(); }
    else if (state_ == UpdateState::Disabled && !suppressed()) state_ = UpdateState::Idle;
    emit changed();
}
void UpdateChecker::setGameRunning(bool running) {
    gameRunning_ = running; if (running) cancel(); emit changed();
}
void UpdateChecker::skipVersion() {
    if (!manifest_) return;
    settings_.options["update_skipped_version"] = manifest_->version.text(); persist(); state_ = UpdateState::Skipped; emit changed();
}
void UpdateChecker::readResponse() {
    if (!reply_ || !error_.isEmpty()) return;
    bytes_ += reply_->read(kMaxManifest + 1 - bytes_.size());
    if (bytes_.size() > kMaxManifest) { error_ = "Manifest exceeds the metadata limit."; reply_->abort(); }
}
void UpdateChecker::finish() {
    if (!reply_) return;
    if (error_.isEmpty() && reply_->error() == QNetworkReply::NoError) readResponse();
    if (!reply_) return;
    connectTimer_.stop(); totalTimer_.stop();
    if (error_.isEmpty() && (reply_->error() != QNetworkReply::NoError || reply_->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt() != 200)) error_ = "Update request failed.";
    auto result = error_.isEmpty() ? parseUpdateManifest(bytes_, ManifestPolicy::NotifyOnlyUnsigned, &error_) : std::optional<UpdateManifest>();
    if (result && cached_ && result->released < cached_->released) { result.reset(); error_ = "Release date moved backwards."; }
    if (result) {
        manifest_ = result;
        const auto installed = Version::parse(config_.installedVersion);
        if (installed && result->version.compare(*installed) > 0) {
            state_ = settings_.option("update_skipped_version") == result->version.text() ? UpdateState::Skipped : UpdateState::Available;
        } else state_ = UpdateState::UpToDate;
        // Older versions cannot replace a newer cached compatibility hint.
        if (!cached_ || result->version.compare(cached_->version) >= 0) {
            cached_ = result;
            try { writeAtomic(userDir_ + "/updates/last-manifest.json", bytes_); } catch (...) {}
        }
    } else state_ = UpdateState::Failed;
    auto *r = reply_; reply_ = nullptr; r->deleteLater(); emit changed();
}
}
