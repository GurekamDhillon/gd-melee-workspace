#pragma once
// Crash-report upload client: the Qt port of the C# launcher's Diagnostics-tab upload (commits c2a556b, 8bdd16c).
// Nothing here runs by itself: the window calls it from one button, and only with the opt-in switched on.
// The receiving end is tools/release/crash_upload_server.py (POST /crash over plain TCP, 64 KB at most).
#include <QString>
#include <QStringList>
#include <atomic>

namespace launcher {
constexpr qint64 kCrashUploadMax = 64 * 1024;   // the server's limit; the same cap the C# launcher used

// The first line of netplay_server.txt (next to the game) that is not blank or a # comment: "host:port", or "".
// This is the one server address the game and the old launcher both use; the crash receiver shares its port (TCP).
QString crashServer(const QString &appDir);

// The newest `count` reports the player may send, newest first: crashlogs/crash-*.log, never a -full.log, only
// the compact kind (it starts with the report header), never a fault during shutdown, none over 64 KB.
QStringList uploadableCrashes(const QString &runDir, int count = 3);

// Defence in depth, as in the C# launcher: the game already replaced these, the launcher checks again.
// The profile folder (either slash) becomes %USERPROFILE%; a user name of 3+ characters becomes <user>.
QString scrubCrashReport(QString text, const QString &profile, const QString &user);
QString crashUserName();   // USERNAME / USER, or ""

struct CrashUploadResult {
    enum Failure { None, NoReports, NoServer, TooLarge, ServerRefused, Network, Cancelled } failure = None;
    int sent = 0, total = 0;
    int status = 0;        // ServerRefused: the HTTP status
    QString detail;        // Network: why; ServerRefused: the server's one-line answer
    QString server;
    bool ok() const { return failure == None && total > 0 && sent == total; }
};
// POSTs each file, in order, stopping at the first failure. A report that was accepted gets a "<file>.sent" note
// beside it (time, server, answer); one the server answered 400 gets "refused by the server (400)".
// Blocking (each socket step waits at most timeoutMs): call it off the GUI thread. Setting *cancel (optional)
// ends it within about 200 ms with Failure::Cancelled.
CrashUploadResult uploadCrashReports(const QString &server, const QStringList &files, const QString &version,
                                     const QString &profile, const QString &user, int timeoutMs = 10000,
                                     const std::atomic<bool> *cancel = nullptr);
}
