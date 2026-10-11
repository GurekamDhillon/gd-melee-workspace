#include "combo_model.h"
#include "commands.h"
#include <cmath>

namespace wb {
namespace {
bool isInt(const QJsonValue &v) { return v.isDouble() && std::isfinite(v.toDouble()) && std::floor(v.toDouble()) == v.toDouble(); }
} // namespace

const QStringList &comboInputs() { static const QStringList v{"light", "heavy", "special", "jump", "grab", "shield", "none"}; return v; }
const QStringList &comboDirs() { static const QStringList v{"any", "neutral", "forward", "back", "up", "down", "side"}; return v; }
const QStringList &comboOns() { static const QStringList v{"any", "hit", "whiff", "block", "contact"}; return v; }
const QStringList &comboWheres() { static const QStringList v{"any", "ground", "air"}; return v; }

QStringList comboRouteSources(const QJsonObject &route) {
    QStringList out;
    const auto from = route.value("from");
    if (from.isString()) out << from.toString();
    else if (from.isArray()) for (const auto &v : from.toArray()) if (v.isString()) out << v.toString();
    return out;
}
QString comboInputClass(const QJsonObject &route) {
    const QString input = route.value("input").toString();
    return comboInputs().contains(input) ? input : QStringLiteral("none");
}
QString comboTargetName(const QString &to) { return to.startsWith("geno:") ? to.mid(5) : to; }
QString comboRouteLabel(const QJsonObject &route) {
    const QString on = route.contains("on") ? route.value("on").toString() : QStringLiteral("hit");
    QString when;
    if (on == "hit") when = t("on hit", "al golpear");
    else if (on == "whiff") when = t("on whiff", "al fallar");
    else if (on == "block") when = t("on block", "al ser bloqueado");
    else if (on == "contact") when = t("on contact", "al contacto");
    else when = t("any time", "en cualquier momento");
    return QString("%1 · %2 · %3").arg(comboTargetName(route.value("to").toString()), comboInputClass(route), when);
}
QPair<int, int> comboRouteWindow(const QJsonObject &route) {
    const auto w = route.value("window").toArray();
    if (w.size() != 2) return {1, 0};
    return {w[0].toInt(1), w[1].toInt(0)};
}
QString validateComboRoute(const QJsonObject &r) {
    if (comboRouteSources(r).isEmpty()) return t("from: a move name, or a list of move names, is required", "from: a move name, or a list of move names, is required");
    if (r.value("from").isArray())
        for (const auto &v : r.value("from").toArray())
            if (!v.isString() || v.toString().isEmpty()) return t("from: every entry must be a move name", "from: every entry must be a move name");
    if (!r.value("to").isString() || r.value("to").toString().isEmpty()) return t("to: a target move is required", "to: a target move is required");
    if (!r.value("input").isString() || !comboInputs().contains(r.value("input").toString()))
        return t("input: expected one of %1", "input: expected one of %1").arg(comboInputs().join(", "));
    const struct { const char *key; const QStringList &vocabulary; } names[] =
        {{"dir", comboDirs()}, {"on", comboOns()}, {"where", comboWheres()}};
    for (const auto &n : names)
        if (r.contains(n.key) && (!r.value(n.key).isString() || !n.vocabulary.contains(r.value(n.key).toString())))
            return t("%1: expected one of %2", "%1: expected one of %2").arg(n.key, n.vocabulary.join(", "));
    if (r.contains("window")) {
        const auto w = r.value("window");
        if (!w.isArray() || w.toArray().size() != 2 || !isInt(w.toArray()[0]) || !isInt(w.toArray()[1]))
            return t("window: expected [first, last] whole frames", "window: expected [first, last] whole frames");
        const int lo = w.toArray()[0].toInt(), hi = w.toArray()[1].toInt();
        if (lo < 1) return t("window: the first frame is at least 1 (frame 1 is the first frame of the move)", "window: the first frame is at least 1 (frame 1 is the first frame of the move)");
        if (hi != 0 && hi < lo) return t("window: the last frame must not be before the first (0 means to the end)", "window: the last frame must not be before the first (0 means to the end)");
    }
    for (const char *key : {"buffer", "priority", "ki_cost", "ki_min", "hold", "depth"})
        if (r.contains(key)) {
            const bool signedOk = QLatin1String(key) == "priority";
            if (!isInt(r.value(key)) || (!signedOk && r.value(key).toInt() < 0))
                return t("%1: expected a whole number", "%1: expected a whole number").arg(key);
        }
    for (const char *key : {"name", "source"})
        if (r.contains(key) && !r.value(key).isString()) return t("%1: expected text", "%1: expected text").arg(key);
    return {};
}
QString validateComboString(const QJsonObject &s) {
    if (!s.value("name").isString() || s.value("name").toString().isEmpty()) return t("name: a string needs a name", "name: a string needs a name");
    if (!s.value("steps").isArray() || s.value("steps").toArray().size() < 1) return t("steps: a string needs at least one step", "steps: a string needs at least one step");
    for (const auto &v : s.value("steps").toArray())
        if (!v.isString() || v.toString().isEmpty()) return t("steps: every step must be a move name", "steps: every step must be a move name");
    return {};
}

QVector<Problem> comboWindowProblems(const QJsonArray &routes, const QHash<QString, ComboRowTiming> &timing) {
    QVector<Problem> out;
    for (int i = 0; i < routes.size(); ++i) {
        const auto route = routes[i].toObject();
        if (!validateComboRoute(route).isEmpty()) continue;
        const QString on = route.contains("on") ? route.value("on").toString() : QStringLiteral("hit");
        const bool needsContact = on == "hit" || on == "block" || on == "contact";
        const auto window = comboRouteWindow(route);
        const QString name = route.value("name").toString(QString("#%1").arg(i));
        const QString target = comboTargetName(route.value("to").toString());
        for (const QString &source : comboRouteSources(route)) {
            const auto it = timing.constFind(source);
            if (it == timing.constEnd()) continue;
            const auto &row = it.value();
            if (needsContact && row.firstHit > 0 && window.second > 0 && window.second < row.firstHit)
                out.append({"combo_window", row.row,
                    t("Route %1 (%2 -> %3) needs a contact (%4), but its window ends at frame %5, before %2 first hits on frame %6: it can never open. Move the window's end to frame %6 or later, or move the hit earlier.",
                      "Route %1 (%2 -> %3) needs a contact (%4), but its window ends at frame %5, before %2 first hits on frame %6: it can never open. Move the window's end to frame %6 or later, or move the hit earlier.")
                        .arg(name, row.row, target, on).arg(window.second).arg(row.firstHit), i});
            else if (row.length > 0 && window.first > row.length)
                out.append({"combo_window", row.row,
                    t("Route %1 (%2 -> %3) opens at frame %4, after %2 has ended (it lasts %5 frames): it can never open. Move the window's start to frame %5 or earlier.",
                      "Route %1 (%2 -> %3) opens at frame %4, after %2 has ended (it lasts %5 frames): it can never open. Move the window's start to frame %5 or earlier.")
                        .arg(name, row.row, target).arg(window.first).arg(row.length), i});
        }
    }
    return out;
}
} // namespace wb
