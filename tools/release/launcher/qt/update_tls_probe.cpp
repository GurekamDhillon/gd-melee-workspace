// Packaging test utility, never shipped. Exercises the deployed Network DLL and
// TLS plugin with a loopback server and an explicitly trusted test certificate.
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QSslCertificate>
#include <QSslConfiguration>
#include <QSslSocket>
#include <QTextStream>
#include <QTimer>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv); const auto args = app.arguments();
    const bool backendOnly = args.size() == 2 && args[1] == "--backend-only";
    if (!backendOnly && args.size() != 3) return 2;
    if (!backendOnly) QCoreApplication::setLibraryPaths({QDir(app.applicationDirPath()).filePath("../plugins")});
#ifdef Q_OS_WIN
    if (!QSslSocket::setActiveBackend("schannel")) return 3;
#endif
    if (!QSslSocket::supportsSsl()) return 4;
    if (backendOnly) { QTextStream(stdout) << "TLS backend: " << QSslSocket::activeBackend() << Qt::endl; return 0; }
    const QUrl url(args[1]);
    if (url.scheme() != "https" || url.host() != "127.0.0.1") return 5;
    QFile certFile(args[2]); if (!certFile.open(QIODevice::ReadOnly)) return 6;
    const auto certs = QSslCertificate::fromData(certFile.readAll()); if (certs.size() != 1) return 7;
    auto tls = QSslConfiguration::defaultConfiguration(); tls.addCaCertificate(certs[0]); tls.setProtocol(QSsl::TlsV1_2OrLater);
    QNetworkAccessManager network; QNetworkRequest request(url); request.setSslConfiguration(tls);
    auto *reply = network.get(request); bool encrypted = false; int result = 1;
    QObject::connect(reply, &QNetworkReply::encrypted, &app, [&] { encrypted = true; });
    // No ignoreSslErrors: the probe must validate its explicitly trusted fixture.
    QObject::connect(reply, &QNetworkReply::finished, &app, [&] {
        const auto bytes = reply->readAll();
        if (encrypted && reply->error() == QNetworkReply::NoError && reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt() == 200 && bytes == "GDMELEE-TLS-RUNTIME-OK") {
            result = 0; QTextStream(stdout) << "HTTPS OK (backend=" << QSslSocket::activeBackend() << ")" << Qt::endl;
        } else QTextStream(stderr) << "HTTPS failed: " << reply->errorString() << Qt::endl;
        app.quit();
    });
    QTimer::singleShot(15000, &app, [&] { reply->abort(); app.quit(); });
    app.exec(); return result;
}
