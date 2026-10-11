#include "geno_asm.h"
#include <QRegularExpression>
#include <QSet>
#include <algorithm>
#include <limits>

// Article spawns in a straight-line script: read them, move one in time, change its argument, add or remove one.
// A move keeps every other command's frame: the CALL is lifted out and put back at its new frame, splitting the
// waits around it, or, when it sits alone between two waits, the two waits are rebalanced (the tidy case).
// Every edit is re-read and checked: the other commands and spawns must be where they were.
namespace wb {
namespace {
struct Word { QString text; qsizetype offset; };
QVector<Word> words(const QString &line) {
    static const QRegularExpression word(QStringLiteral("\\S+"));
    const qsizetype comment = line.indexOf('#');
    const QString code = comment < 0 ? line : line.left(comment);
    QVector<Word> out;
    auto it = word.globalMatch(code);
    while (it.hasNext()) { const auto m = it.next(); out.append({m.captured(), m.capturedStart()}); }
    return out;
}
bool isSpawn(const QVector<Word> &w) {
    return w.size() >= 3 && w[0].text.compare("call", Qt::CaseInsensitive) == 0 &&
           w[1].text.compare("geno.article.spawn", Qt::CaseInsensitive) == 0;
}
bool isWait(const QVector<Word> &w) { return w.size() == 2 && (w[0].text == "wait" || w[0].text == "wait_until"); }
bool parseUInt(const QString &s, quint32 *out) {
    bool ok = false;
    const qulonglong v = s.toULongLong(&ok, 0);
    if (!ok || v > std::numeric_limits<quint32>::max()) return false;
    *out = quint32(v);
    return true;
}
// Flow that makes straight-line frame arithmetic meaningless (a spawn call is not flow).
bool isFlow(const QVector<Word> &w) {
    static const QSet<QString> flow{"loop", "loop_end", "endloop", "subroutine", "return", "goto", "if", "ifv", "branch"};
    if (w.isEmpty() || isSpawn(w)) return false;
    const QString op = w[0].text.toLower();
    return op == "call" || flow.contains(op);
}
struct Scan { QVector<SpawnRef> spawns; bool straight = true; };
Scan scan(const QStringList &lines) {
    Scan s;
    int time = 0;
    for (int i = 0; i < lines.size(); ++i) {
        const auto w = words(lines[i]);
        if (w.isEmpty()) continue;
        if (isFlow(w)) { s.straight = false; return s; }
        if (isWait(w)) {
            bool ok = false;
            const qint64 n = w[1].text.toLongLong(&ok);
            if (!ok || n < 0 || n > std::numeric_limits<int>::max()) { s.straight = false; return s; }
            const qint64 next = w[0].text == "wait" ? time + n : n;
            if (next > std::numeric_limits<int>::max()) { s.straight = false; return s; }
            time = int(next);
        } else if (isSpawn(w)) {
            quint32 arg = 0;
            if (!parseUInt(w[2].text, &arg)) continue;
            SpawnRef r;
            r.ordinal = int(s.spawns.size()); r.line = i; r.frame = time; r.arg = arg;
            r.article = int(arg & 0xFF); r.variant = int((arg >> 8) & 0xFF);
            int a = int((arg >> 16) & 0xFFFF);
            if (a >= 0x8000) a -= 0x10000;
            r.angle = a;
            s.spawns.append(r);
        }
    }
    return s;
}
QString crOf(const QStringList &lines) {
    return (!lines.isEmpty() && lines[0].endsWith('\r')) ? QStringLiteral("\r") : QString();
}
void setWaitValue(QString &line, int value) {
    const auto w = words(line);
    line.replace(w[1].offset, w[1].text.size(), QString::number(value));
}
// Insert `spawnLine` so it runs at `frame`, every other command keeping its frame.
bool insertAt(QStringList &lines, int frame, const QString &spawnLine, QString *err) {
    int time = 0;
    const QString cr = crOf(lines);
    for (int i = 0; i < lines.size(); ++i) {
        const auto w = words(lines[i]);
        if (w.isEmpty()) continue;
        if (isFlow(w)) { *err = QStringLiteral("the script has loops or calls: edit the spawn by hand"); return false; }
        if (!isWait(w)) continue;
        const int n = w[1].text.toInt();
        const int next = w[0].text == "wait" ? time + n : n;
        if (time == frame) { lines.insert(i, spawnLine); return true; }
        if (next > frame) {
            if (w[0].text == "wait") {
                QString rest = lines[i];
                setWaitValue(lines[i], frame - time);
                setWaitValue(rest, next - frame);
                lines.insert(i + 1, spawnLine);
                lines.insert(i + 2, rest);
            } else {
                lines.insert(i, QStringLiteral("wait_until %1").arg(frame) + cr);
                lines.insert(i + 1, spawnLine);
            }
            return true;
        }
        time = next;
    }
    int at = int(lines.size());
    if (at > 0 && lines[at - 1].isEmpty()) --at; // keep the final newline last
    if (time < frame) { lines.insert(at, QStringLiteral("wait_until %1").arg(frame) + cr); ++at; }
    lines.insert(at, spawnLine);
    return true;
}
// (frame, running index) of every command that is neither a wait nor a spawn: the "nothing else moved" check.
QVector<std::pair<int, int>> others(const QStringList &lines) {
    QVector<std::pair<int, int>> out;
    int time = 0, k = 0;
    for (const auto &l : lines) {
        const auto w = words(l);
        if (w.isEmpty()) continue;
        if (isWait(w)) { const int n = w[1].text.toInt(); time = w[0].text == "wait" ? time + n : n; continue; }
        if (isSpawn(w)) continue;
        out.append({time, ++k});
    }
    return out;
}
} // namespace

QVector<SpawnRef> GenoAsm::spawns() const { return scan(lines_).spawns; }

QString GenoAsm::setSpawnArg(int ordinal, quint32 arg, QString *err) const {
    if (err) err->clear();
    const auto s = scan(lines_);
    if (ordinal < 0 || ordinal >= s.spawns.size()) {
        if (err) *err = QStringLiteral("no spawn #%1").arg(ordinal);
        return {};
    }
    QStringList lines = lines_;
    QString &line = lines[s.spawns[ordinal].line];
    const auto w = words(line);
    line.replace(w[2].offset, w[2].text.size(), QString::number(arg));
    return lines.join('\n');
}

QString GenoAsm::removeSpawn(int ordinal, QString *err) const {
    if (err) err->clear();
    const auto s = scan(lines_);
    if (ordinal < 0 || ordinal >= s.spawns.size()) {
        if (err) *err = QStringLiteral("no spawn #%1").arg(ordinal);
        return {};
    }
    QStringList lines = lines_;
    lines.removeAt(s.spawns[ordinal].line);
    return lines.join('\n');
}

QString GenoAsm::addSpawn(int frame, quint32 arg, QString *err, int *ordinalOut) const {
    if (err) err->clear();
    if (frame < 0) { if (err) *err = QStringLiteral("frame must be non-negative"); return {}; }
    const auto before = scan(lines_);
    if (!before.straight) { if (err) *err = QStringLiteral("the script has loops or calls: add the spawn by hand"); return {}; }
    QStringList lines = lines_;
    QString e;
    if (!insertAt(lines, frame, QStringLiteral("CALL geno.article.spawn %1").arg(arg) + crOf(lines), &e)) {
        if (err) *err = e;
        return {};
    }
    const auto after = scan(lines);
    if (after.spawns.size() != before.spawns.size() + 1 || others(lines) != others(lines_)) {
        if (err) *err = QStringLiteral("could not place the spawn without moving other commands");
        return {};
    }
    bool seen = false;
    for (const auto &r : after.spawns) if (r.frame == frame && r.arg == arg) seen = true;
    if (!seen) { if (err) *err = QStringLiteral("could not place the spawn at frame %1").arg(frame); return {}; }
    if (ordinalOut) {
        // The new line is the first spawn at that frame whose line is new: count the spawns that run before it.
        int pos = 0;
        for (const auto &r : before.spawns) if (r.frame <= frame) ++pos;
        *ordinalOut = pos;
    }
    return lines.join('\n');
}

QString GenoAsm::moveSpawn(int ordinal, int frame, QString *err) const {
    if (err) err->clear();
    const auto before = scan(lines_);
    if (!before.straight) { if (err) *err = QStringLiteral("the script has loops or calls: move the spawn by hand"); return {}; }
    if (ordinal < 0 || ordinal >= before.spawns.size()) { if (err) *err = QStringLiteral("no spawn #%1").arg(ordinal); return {}; }
    if (frame < 0) { if (err) *err = QStringLiteral("frame must be non-negative"); return {}; }
    const SpawnRef target = before.spawns[ordinal];
    if (target.frame == frame) return lines_.join('\n');
    const auto unmoved = others(lines_);
    const auto good = [&](const QStringList &lines) {
        const auto after = scan(lines);
        if (after.spawns.size() != before.spawns.size() || others(lines) != unmoved) return false;
        QVector<std::pair<int, quint32>> want, got;
        for (const auto &r : before.spawns) want.append({r.ordinal == ordinal ? frame : r.frame, r.arg});
        for (const auto &r : after.spawns) got.append({r.frame, r.arg});
        std::sort(want.begin(), want.end());
        std::sort(got.begin(), got.end());
        return want == got;
    };
    // 1. The tidy case: the CALL is alone between two waits (or after one, at the end): rebalance them.
    const int L = target.line;
    int prev = L - 1, next = L + 1;
    while (prev >= 0 && words(lines_[prev]).isEmpty()) --prev;
    while (next < lines_.size() && words(lines_[next]).isEmpty()) ++next;
    if (prev >= 0 && isWait(words(lines_[prev]))) {
        QStringList lines = lines_;
        const int delta = frame - target.frame;
        const int pv = words(lines[prev])[1].text.toInt() + delta;
        bool ok = pv >= 0;
        if (ok) {
            setWaitValue(lines[prev], pv);
            if (next < lines.size() && !words(lines[next]).isEmpty()) {
                const auto nw = words(lines[next]);
                if (!isWait(nw)) ok = false; // another command shares the frame
                else if (nw[0].text == "wait") {
                    const int nv = nw[1].text.toInt() - delta;
                    ok = nv >= 0;
                    if (ok) setWaitValue(lines[next], nv);
                }
            }
        }
        if (ok && good(lines)) return lines.join('\n');
    }
    // 2. Lift the CALL out and put it back at its frame.
    QStringList lines = lines_;
    const QString spawnLine = lines[L];
    lines.removeAt(L);
    QString e;
    if (!insertAt(lines, frame, spawnLine, &e)) { if (err) *err = e; return {}; }
    if (!good(lines)) { if (err) *err = QStringLiteral("could not move the spawn without moving other commands"); return {}; }
    return lines.join('\n');
}
} // namespace wb
