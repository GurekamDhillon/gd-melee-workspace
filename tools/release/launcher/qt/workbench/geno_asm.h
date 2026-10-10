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
    int clearLine = -1; // Zero-based line of the clear_hitboxes that closes it; -1 if never cleared.
};

// A new hitbox: starts at `frame` and lasts `duration` frames unless it joins an active window.
struct HitboxAdd {
    QString joint;
    int frame = 1, duration = 2;
    double damage = 6, size = 3, x = 0, y = 0, z = 0;
    int angle = 361, kbg = 50, fkb = 0, bkb = 20;
};
constexpr int kHitboxSlots = 4;

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
    // Insert `add` at its frame; ordinalOut (if given) receives the new hitbox's ordinal.
    QString addHitbox(const HitboxAdd &add, QString *err, int *ordinalOut = nullptr) const;
    // Remove a hitbox, and its window's clear_hitboxes when it was the last one in that window.
    QString removeHitbox(int ordinal, QString *err) const;
    QString text() const;

private:
    QString text_;
    // Keep each CR and the final empty line, so joining on LF preserves even mixed endings.
    QStringList lines_;
};

} // namespace wb
