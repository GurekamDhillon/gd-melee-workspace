#pragma once

#include <QString>
#include <QStringList>
#include <QVector>
#include <optional>

namespace wb {

struct HitboxRef {
    int ordinal = 0; // Order in the file, zero-based.
    int line = 0;    // Zero-based line index of the hitbox op.
    int slot = 0;
    QString joint;  // Without @ signs.
    double damage = 0, size = 0, x = 0, y = 0, z = 0;
    int angle = 0, kbg = 0, fkb = 0, bkb = 0;
    int startFrame = 0;
    int endFrame = -1; // Exclusive; -1 means never cleared.
};

struct HitboxEdit {
    std::optional<QString> joint;
    std::optional<double> damage, size, x, y, z;
    std::optional<int> angle, kbg, fkb, bkb, startFrame, endFrame;
};

class GenoAsm {
public:
    static GenoAsm parse(const QString &text);
    QVector<HitboxRef> hitboxes() const;
    QString apply(int ordinal, const HitboxEdit &edit, QString *err) const;
    QString text() const;

private:
    QString text_;
    // Keep each CR and the final empty line, so joining on LF preserves even mixed endings.
    QStringList lines_;
};

} // namespace wb
