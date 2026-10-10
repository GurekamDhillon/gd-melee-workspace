#include "geno_asm.h"

#include <QMap>
#include <QRegularExpression>
#include <cmath>
#include <limits>

namespace wb {
namespace {

struct Tok {
    QString text;
    qsizetype offset;
};

QVector<Tok> tokens(const QString &line) {
    static const QRegularExpression word(QStringLiteral("\\S+"));
    const qsizetype comment = line.indexOf('#');
    const QString code = comment < 0 ? line : line.left(comment);
    QVector<Tok> out;
    auto matches = word.globalMatch(code);
    while (matches.hasNext()) {
        const auto match = matches.next();
        out.append({match.captured(), match.capturedStart()});
    }
    return out;
}

QString opOf(const QString &line) {
    const auto words = tokens(line);
    return words.isEmpty() ? QString() : words[0].text;
}

QString fmtDamage(double value) {
    return QString::number(value, 'f', std::trunc(value) == value ? 0 : 2);
}

void replaceField(QString &line, const QString &key, const QString &value) {
    const auto words = tokens(line);
    const QString prefix = key + '=';
    // The parser uses the last occurrence if a field is repeated. Edit only that token.
    for (qsizetype i = words.size() - 1; i > 0; --i) {
        if (words[i].text.startsWith(prefix)) {
            line.replace(words[i].offset, words[i].text.size(), prefix + value);
            return;
        }
    }
    // Append to the code, before its original trailing whitespace/comment (and any CR).
    const auto &last = words.last();
    line.insert(last.offset + last.text.size(), ' ' + prefix + value);
}

bool isWait(const QVector<Tok> &words, const QString &op) {
    if (words.size() != 2 || words[0].text != op) return false;
    bool ok = false;
    const int frame = words[1].text.toInt(&ok);
    return ok && frame >= 0;
}

void replaceWait(QString &line, int value) {
    const auto words = tokens(line);
    line.replace(words[1].offset, words[1].text.size(), QString::number(value));
}

bool validJoint(QString *name) {
    name->remove('@');
    static const QRegularExpression unsafe(QStringLiteral("[\\s#=\\\\\"']"));
    return !name->isEmpty() && !name->contains(QChar(0)) && !name->contains(unsafe);
}

} // namespace

GenoAsm GenoAsm::parse(const QString &text) {
    GenoAsm script;
    script.text_ = text;
    script.lines_ = text.split('\n');
    return script;
}

QString GenoAsm::text() const { return text_; }

QVector<HitboxRef> GenoAsm::hitboxes() const {
    QVector<HitboxRef> out;
    QVector<int> open;
    int time = 0;
    for (int line = 0; line < lines_.size(); ++line) {
        const auto words = tokens(lines_[line]);
        if (words.isEmpty()) continue;
        const QString op = words[0].text;
        if (op == "wait_until" && words.size() > 1) {
            time = words[1].text.toInt();
        } else if (op == "wait" && words.size() > 1) {
            // Malformed/oversized source must not overflow signed arithmetic.
            const qint64 next = qint64(time) + words[1].text.toInt();
            time = int(qBound(qint64(std::numeric_limits<int>::min()), next,
                              qint64(std::numeric_limits<int>::max())));
        } else if (op == "clear_hitboxes") {
            for (int ordinal : open) { out[ordinal].endFrame = time; out[ordinal].clearLine = line; }
            open.clear();
        } else if (op == "hitbox") {
            HitboxRef h;
            h.ordinal = int(out.size());
            h.line = line;
            h.startFrame = time;
            for (qsizetype i = 1; i < words.size(); ++i) {
                const qsizetype eq = words[i].text.indexOf('=');
                if (eq < 0) continue;
                const QString key = words[i].text.left(eq);
                const QString value = words[i].text.mid(eq + 1);
                if (key == "slot") h.slot = value.toInt();
                else if (key == "joint") { h.joint = value; h.joint.remove('@'); }
                else if (key == "damage") h.damage = value.toDouble();
                else if (key == "size") h.size = value.toDouble();
                else if (key == "x") h.x = value.toDouble();
                else if (key == "y") h.y = value.toDouble();
                else if (key == "z") h.z = value.toDouble();
                else if (key == "angle") h.angle = value.toInt();
                else if (key == "kbg") h.kbg = value.toInt();
                else if (key == "fkb") h.fkb = value.toInt();
                else if (key == "bkb") h.bkb = value.toInt();
            }
            open.append(h.ordinal);
            out.append(h);
        }
    }
    return out;
}

QString GenoAsm::apply(int ordinal, const HitboxEdit &edit, QString *err) const {
    if (err) err->clear();
    const auto fail = [err](const QString &reason) -> QString {
        if (err) *err = reason;
        return {};
    };
    const auto boxes = hitboxes();
    if (ordinal < 0 || ordinal >= boxes.size())
        return fail(QStringLiteral("no hitbox #%1").arg(ordinal));
    const HitboxRef &h = boxes[ordinal];
    QMap<QString, QString> replacements;
    if (edit.joint) {
        QString name = *edit.joint;
        name.remove('@');
        static const QRegularExpression unsafe(QStringLiteral("[\\s#=\\\\\"']"));
        if (name.isEmpty() || name.contains(QChar(0)) || name.contains(unsafe))
            return fail(QStringLiteral("joint must be a non-empty name without whitespace or script delimiters"));
        replacements.insert(QStringLiteral("joint"), '@' + name + '@');
    }
    const QMap<QString, std::optional<double>> floats = {
        {"damage", edit.damage}, {"size", edit.size}, {"x", edit.x}, {"y", edit.y}, {"z", edit.z}
    };
    for (auto it = floats.cbegin(); it != floats.cend(); ++it) {
        if (!it.value()) continue;
        const double value = *it.value();
        if (!std::isfinite(value)) return fail(it.key() + QStringLiteral(" must be finite"));
        replacements.insert(it.key(), it.key() == "damage" ? fmtDamage(value) : QString::number(value, 'f', 2));
    }
    const QMap<QString, std::optional<int>> ints = {
        {"angle", edit.angle}, {"kbg", edit.kbg}, {"fkb", edit.fkb}, {"bkb", edit.bkb}
    };
    for (auto it = ints.cbegin(); it != ints.cend(); ++it)
        if (it.value()) replacements.insert(it.key(), QString::number(*it.value()));

    QStringList lines = lines_;
    if (edit.startFrame || edit.endFrame) {
        const auto shapeError = [&fail](const QString &why) {
            return fail(QStringLiteral("frames not editable for this script shape: ") + why);
        };
        const auto significant = [this](int from, int step) {
            for (int i = from + step; i >= 0 && i < lines_.size(); i += step)
                if (!opOf(lines_[i]).isEmpty()) return i;
            return -1;
        };
        const int prev = significant(h.line, -1);
        const int next1 = significant(h.line, 1);
        const int next2 = next1 < 0 ? -1 : significant(next1, 1);
        if (prev < 0 || next1 < 0 || next2 < 0 ||
            !isWait(tokens(lines_[prev]), QStringLiteral("wait_until")) ||
            !isWait(tokens(lines_[next1]), QStringLiteral("wait")) ||
            tokens(lines_[next2]).size() != 1 || opOf(lines_[next2]) != "clear_hitboxes") {
            return shapeError(QStringLiteral("expected wait_until / hitbox / wait / clear_hitboxes"));
        }
        // Adjacency alone misses a hitbox opened before the preceding wait_until.
        // Do not collapse refs by slot: two source hitboxes on one slot are ambiguous too.
        for (int i = h.line - 1; i >= 0; --i) {
            const QString op = opOf(lines_[i]);
            if (op == "clear_hitboxes") break;
            if (op == "hitbox") return shapeError(QStringLiteral("another hitbox is active before this hitbox"));
        }
        const int start = edit.startFrame.value_or(h.startFrame);
        const int end = edit.endFrame.value_or(h.endFrame);
        if (start < 0) return fail(QStringLiteral("start frame must be non-negative"));
        if (end <= start) return fail(QStringLiteral("end frame must be after start frame"));
        replaceWait(lines[prev], start);
        replaceWait(lines[next1], end - start);
    }
    for (auto it = replacements.cbegin(); it != replacements.cend(); ++it)
        replaceField(lines[h.line], it.key(), it.value());
    return lines.join('\n');
}

QString GenoAsm::addHitbox(const HitboxAdd &add, QString *err, int *ordinalOut) const {
    if (err) err->clear();
    const auto fail = [err](const QString &reason) -> QString {
        if (err) *err = reason;
        return {};
    };
    QString joint = add.joint;
    if (!validJoint(&joint))
        return fail(QStringLiteral("joint must be a non-empty name without whitespace or script delimiters"));
    for (double v : {add.damage, add.size, add.x, add.y, add.z})
        if (!std::isfinite(v)) return fail(QStringLiteral("hitbox numbers must be finite"));
    if (add.damage < 0 || add.size < 0) return fail(QStringLiteral("damage and size must be nonnegative"));
    if (add.frame < 0) return fail(QStringLiteral("frame must be non-negative"));
    if (add.duration < 1) return fail(QStringLiteral("duration must be at least 1 frame"));
    const int T = add.frame;
    const auto boxes = hitboxes();
    constexpr int inf = std::numeric_limits<int>::max();
    // A frame inside an active window joins it and ends with that window's clear_hitboxes.
    const HitboxRef *window = nullptr;
    for (const auto &b : boxes)
        if (b.startFrame <= T && (b.endFrame < 0 || T < b.endFrame)) { window = &b; break; }
    int duration = add.duration;
    int newEnd;
    if (window) {
        newEnd = window->endFrame < 0 ? inf : window->endFrame;
    } else {
        // A fresh window must close before the next one opens (clear_hitboxes clears them all).
        for (const auto &b : boxes) if (b.startFrame > T) duration = qMin(duration, b.startFrame - T);
        newEnd = T + duration;
    }
    QVector<bool> used(kHitboxSlots, false);
    for (const auto &b : boxes) {
        const int end = b.endFrame < 0 ? inf : b.endFrame;
        if (b.startFrame < newEnd && end > T && b.slot >= 0 && b.slot < kHitboxSlots) used[b.slot] = true;
    }
    int slot = -1;
    for (int i = 0; i < kHitboxSlots; ++i) if (!used[i]) { slot = i; break; }
    if (slot < 0)
        return fail(QStringLiteral("no free hitbox slot at frame %1 (the game has %2)").arg(T).arg(kHitboxSlots));

    const QString hitLine =
        QStringLiteral("hitbox slot=%1 joint=@%2@ damage=%3 size=%4 x=%5 y=%6 z=%7 angle=%8 kbg=%9 fkb=%10 bkb=%11")
            .arg(slot).arg(joint).arg(fmtDamage(add.damage)).arg(QString::number(add.size, 'f', 2))
            .arg(QString::number(add.x, 'f', 2)).arg(QString::number(add.y, 'f', 2))
            .arg(QString::number(add.z, 'f', 2)).arg(add.angle).arg(add.kbg).arg(add.fkb).arg(add.bkb);

    // First time-advancing line that crosses T; the block goes there so later lines keep their frames.
    QStringList lines = lines_;
    int time = 0, k = -1, before = 0, waitN = 0, waitX = 0;
    for (int i = 0; i < lines.size() && k < 0; ++i) {
        const auto words = tokens(lines[i]);
        if (words.size() < 2) continue;
        const bool abs = words[0].text == "wait_until";
        if (!abs && words[0].text != "wait") continue;
        const int v = words[1].text.toInt();
        const qint64 after = abs ? qint64(v) : qint64(time) + v;
        if (after > T && after > time) {
            k = i; before = time;
            if (abs) waitX = v; else waitN = v;
        }
        time = int(qBound(qint64(std::numeric_limits<int>::min()), after, qint64(inf)));
    }
    int at = 0, replace = 0, hitIndex = 0;
    QStringList block;
    if (k >= 0) {
        at = k;
        const bool cr = lines[k].endsWith('\r');
        const auto eol = [cr](const QString &s) { return cr ? s + '\r' : s; };
        const bool isAbs = opOf(lines[k]) == "wait_until";
        if (window) {
            if (before == T) {
                block << eol(hitLine);
            } else if (isAbs) {
                block << eol(QStringLiteral("wait_until %1").arg(T)) << eol(hitLine);
                hitIndex = 1;
            } else {
                const int lead = T - before;
                QString first = lines[k];
                replaceWait(first, lead);
                block << first << eol(hitLine) << eol(QStringLiteral("wait %1").arg(waitN - lead));
                hitIndex = 1; replace = 1;
            }
        } else if (isAbs) {
            duration = qMin(duration, waitX - T);
            block << eol(QStringLiteral("wait_until %1").arg(T)) << eol(hitLine)
                  << eol(QStringLiteral("wait %1").arg(duration)) << eol(QStringLiteral("clear_hitboxes"));
            hitIndex = 1;
        } else {
            const int lead = T - before;
            duration = qMin(duration, waitN - lead);
            block << eol(QStringLiteral("wait_until %1").arg(T)) << eol(hitLine)
                  << eol(QStringLiteral("wait %1").arg(duration)) << eol(QStringLiteral("clear_hitboxes"));
            if (waitN - lead - duration > 0) block << eol(QStringLiteral("wait %1").arg(waitN - lead - duration));
            hitIndex = 1; replace = 1;
        }
    } else {
        // Past the end of the timeline: append after the last real line.
        at = int(lines.size());
        while (at > 0 && lines[at - 1].trimmed().isEmpty()) --at;
        const bool cr = at > 0 && lines[at - 1].endsWith('\r');
        const auto eol = [cr](const QString &s) { return cr ? s + '\r' : s; };
        if (T > time) block << eol(QStringLiteral("wait_until %1").arg(T));
        hitIndex = int(block.size());
        block << eol(hitLine);
        if (!window) block << eol(QStringLiteral("wait %1").arg(duration)) << eol(QStringLiteral("clear_hitboxes"));
    }
    for (int i = 0; i < replace; ++i) lines.removeAt(at);
    for (int i = 0; i < block.size(); ++i) lines.insert(at + i, block[i]);
    const QString result = lines.join('\n');
    if (ordinalOut) {
        *ordinalOut = -1;
        for (const auto &b : GenoAsm::parse(result).hitboxes()) if (b.line == at + hitIndex) *ordinalOut = b.ordinal;
    }
    return result;
}

QString GenoAsm::removeHitbox(int ordinal, QString *err) const {
    if (err) err->clear();
    const auto boxes = hitboxes();
    if (ordinal < 0 || ordinal >= boxes.size()) {
        if (err) *err = QStringLiteral("no hitbox #%1").arg(ordinal);
        return {};
    }
    const HitboxRef &h = boxes[ordinal];
    int sharing = 0;
    for (const auto &b : boxes) if (b.clearLine == h.clearLine) ++sharing;
    const auto significant = [this](int from, int step) {
        for (int i = from + step; i >= 0 && i < lines_.size(); i += step)
            if (!opOf(lines_[i]).isEmpty()) return i;
        return -1;
    };
    QStringList lines = lines_;
    if (h.clearLine >= 0 && sharing == 1) {
        // The last hitbox of its window: the window's clear_hitboxes goes too. The whole
        // wait_until / hitbox / wait / clear block goes when what follows is an absolute wait or the end
        // (nothing after it depends on this window's length).
        const int prev = significant(h.line, -1), n1 = significant(h.line, 1);
        const int n2 = n1 < 0 ? -1 : significant(n1, 1);
        const int n3 = n2 < 0 ? -1 : significant(n2, 1);
        const bool canonical = prev >= 0 && n2 == h.clearLine &&
            (n3 < 0 || isWait(tokens(lines_[n3]), QStringLiteral("wait_until"))) &&
            isWait(tokens(lines_[prev]), QStringLiteral("wait_until")) &&
            isWait(tokens(lines_[n1]), QStringLiteral("wait")) &&
            tokens(lines_[n2]).size() == 1 &&
            tokens(lines_[prev])[1].text.toInt() == h.startFrame;
        if (canonical) {
            for (int i : {n2, n1, h.line, prev}) lines.removeAt(i);
        } else {
            const bool bareClear = tokens(lines_[h.clearLine]).size() == 1;
            if (bareClear) lines.removeAt(h.clearLine);
            lines.removeAt(h.line);
        }
        return lines.join('\n');
    }
    // A shared window: drop just this line, then undo any split an add left at this spot.
    const int prev = significant(h.line, -1), next = significant(h.line, 1);
    lines.removeAt(h.line);
    if (prev >= 0 && next >= 0) {
        const auto pw = tokens(lines_[prev]), nw = tokens(lines_[next]);
        if (isWait(pw, QStringLiteral("wait")) && isWait(nw, QStringLiteral("wait"))) {
            replaceWait(lines[prev], pw[1].text.toInt() + nw[1].text.toInt());
            lines.removeAt(next - 1);
        } else if (isWait(pw, QStringLiteral("wait_until")) && isWait(nw, QStringLiteral("wait_until")) &&
                   pw[1].text.toInt() == h.startFrame && nw[1].text.toInt() >= h.startFrame) {
            lines.removeAt(prev);
        }
    }
    return lines.join('\n');
}

} // namespace wb
