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
    int element = 0; // Source assembler effect code, 0..31; omitted means normal (0).
    int shield = 0;  // Shield damage, signed (-128..127); omitted means 0.
    bool ground = true, air = true; // hit_ground / hit_air: false = cannot hit grounded / airborne targets.
};

// A new hitbox: starts at `frame` and lasts `duration` frames unless it joins an active window.
struct HitboxAdd {
    QString joint;
    int frame = 1, duration = 2;
    double damage = 6, size = 3, x = 0, y = 0, z = 0;
    int angle = 361, kbg = 50, fkb = 0, bkb = 20;
};
constexpr int kHitboxSlots = 4;
// The slot ids the Workbench lets a user write. Slot 4+ (Skull Kid's id 4) waits for ws/research-ace-hitbox-slot4:
// raise this to kHitboxSlots + 1 there once the assembler and engine accept it; a script that already has a
// higher slot shows it read-only. kHitboxSlots (the sound() solver's pool) moves with it.
constexpr int kHitboxEditableSlots = kHitboxSlots;

// One `CALL geno.article.spawn ARG` in a straight-line script (geno.md 19.8: ARG [7:0] article, [15:8] spawn
// variant, [31:16] signed extra angle in degrees).
struct SpawnRef {
    int ordinal = 0; // Order in the file, zero-based.
    int line = 0;    // Zero-based line index of the CALL.
    int frame = 0;   // The move frame (the script's time) it runs at.
    quint32 arg = 0;
    int article = 0, variant = 0, angle = 0;
};

struct HitboxEdit {
    std::optional<QString> joint;
    std::optional<double> damage, size, x, y, z;
    std::optional<int> angle, kbg, fkb, bkb, startFrame, endFrame, element, shield, slot;
    std::optional<bool> ground, air;
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
    // Article spawns (`CALL geno.article.spawn N`). Reading stops at loops, gotos and other calls, as the
    // timeline markers do. The edits return a null string and set *err when the script cannot honour them;
    // every other command keeps its frame, and so does every other spawn.
    QVector<SpawnRef> spawns() const;
    QString moveSpawn(int ordinal, int frame, QString *err) const;
    QString setSpawnArg(int ordinal, quint32 arg, QString *err) const;
    QString addSpawn(int frame, quint32 arg, QString *err, int *ordinalOut = nullptr) const;
    QString removeSpawn(int ordinal, QString *err) const;
    // Readable reasons the script would not run the way hitboxes() describes it (straight-line scripts):
    // a wait_until that goes back in time (the engine does not wait, so what follows runs late) and two
    // overlapping windows on one slot. Empty when the script is sound or has loops/calls/gotos.
    QStringList timingProblems() const;

private:
    // Re-emit the hitbox blocks in start-frame order with distinct slots for windows that overlap in time
    // (other commands stay at their frames). Straight-line scripts only; the text comes back unchanged
    // when it is already sound. A null string plus *err when it cannot (more than kHitboxSlots at once).
    static QString sound(const QString &text, QString *err);
    // The frame edit and the add/remove for scripts that close windows one slot at a time (clear_hitbox).
    QString viaModel(int ordinal, const HitboxEdit *edit, const HitboxAdd *add, bool remove, QString *err,
                     int *ordinalOut) const;
    QString text_;
    // Keep each CR and the final empty line, so joining on LF preserves even mixed endings.
    QStringList lines_;
};

} // namespace wb
