#pragma once
// The combo graph as the Workbench reads it (geno.md 25): routes "from move M, in a window of its action frames, on hit,
// on an input -> move T" and strings (named step lists). Pure helpers over the file's own JSON objects; the server
// commands (commands_combo.cpp), the checks and the widgets (combo_widgets.*) share them.
#include "checks.h"
#include <QHash>
#include <QJsonArray>
#include <QJsonObject>
#include <QPair>
#include <QString>
#include <QStringList>

namespace wb {
// Route sources (`from` is one name or a list of names).
QStringList comboRouteSources(const QJsonObject &route);
// The input class the colour follows: light heavy special jump grab shield none.
QString comboInputClass(const QJsonObject &route);
// "geno:Light3" -> "Light3"; Melee names and motion:N stay as written.
QString comboTargetName(const QString &to);
// "Light3 · light · on hit" (the lane prefixes the arrow).
QString comboRouteLabel(const QJsonObject &route);
// The window as [first, last] action frames (1-based, hitlag excluded); last 0 = to the end of the move.
QPair<int, int> comboRouteWindow(const QJsonObject &route);
// Empty when the route is well formed for the engine's parser (names, vocabularies, window); else a readable reason.
QString validateComboRoute(const QJsonObject &route);
QString validateComboString(const QJsonObject &str);
const QStringList &comboInputs();
const QStringList &comboDirs();
const QStringList &comboOns();
const QStringList &comboWheres();

// What the route-window check needs to know about a move: its length and the first frame a hitbox is active.
struct ComboRowTiming { int length = 0, firstHit = 0; QString row; };
// Problems of kind "combo_window": a route that needs a contact (on hit / block / contact) whose window ends before the
// source move's first active hit frame, or whose window starts after the move has ended. `timing` is keyed by the
// source token as `from` writes it (the row name, "motion:N").
QVector<Problem> comboWindowProblems(const QJsonArray &routes, const QHash<QString, ComboRowTiming> &timing);

// The string map: moves as nodes, routes as edges. Columns follow the strings' step order and the routes' direction
// (longest path, back edges ignored), rows the order of appearance, so the picture is the same every time.
struct ComboNode { QString name; int col = 0, row = 0; };
struct ComboEdge { int from = 0, to = 0, route = -1; QString input; };
struct ComboGraph {
    QVector<ComboNode> nodes;
    QVector<ComboEdge> edges;
    int cols = 0, rows = 0;
    int node(const QString &name) const;     // -1 when absent
};
ComboGraph buildComboGraph(const QJsonArray &routes, const QJsonArray &strings);

// Playing a string: each move runs until the route to the next one opens (its window start; at the first hit when the
// route needs a contact; plus the route's buffer when asked), then the next move starts. Frames are 1-based: the
// string's first move shows its frame 1 on string frame 1, and the next move's frame 1 follows the cut frame.
struct ComboStepInfo { int length = 0, firstHit = 0; };
struct ComboSegment {
    QString move;
    int start = 1;       // string frame this move's frame 1 is shown on
    int cut = 0;         // the last move frame played (the cancel frame; the whole move for the last step)
    int length = 0;      // the move's own length, 0 unknown
    bool linked = false; // false: no route to the next step, so the move plays out
    QString route, input;
    int lo = 0, hi = 0, buffer = 0;
    int cancelFrame() const { return start + cut - 1; } // string frame of the cancel
};
QVector<ComboSegment> planComboString(const QStringList &steps, const QJsonArray &routes,
                                      const QHash<QString, ComboStepInfo> &info, int defaultBuffer, bool addBuffer);
int comboStringFrames(const QVector<ComboSegment> &plan);
} // namespace wb
