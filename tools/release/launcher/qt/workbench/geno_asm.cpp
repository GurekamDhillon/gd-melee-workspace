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
            for (int ordinal : open) out[ordinal].endFrame = time;
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

} // namespace wb
