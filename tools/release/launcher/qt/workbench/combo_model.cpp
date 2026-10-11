#include "combo_model.h"
#include "commands.h"
#include <cmath>
#include <functional>

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

int ComboGraph::node(const QString &name) const {
    for (int i = 0; i < nodes.size(); ++i) if (nodes[i].name == name) return i;
    return -1;
}
ComboGraph buildComboGraph(const QJsonArray &routes, const QJsonArray &strings) {
    ComboGraph g;
    const auto add = [&](const QString &name) {
        if (name.isEmpty() || name == "*") return -1;
        int i = g.node(name);
        if (i < 0) { g.nodes.append({name, 0, 0}); i = int(g.nodes.size()) - 1; }
        return i;
    };
    for (const auto &s : strings) for (const auto &step : s.toObject().value("steps").toArray()) add(step.toString());
    for (const auto &v : routes) {
        const auto r = v.toObject();
        for (const auto &from : comboRouteSources(r)) add(from);
        add(r.value("to").toString());
    }
    for (int i = 0; i < routes.size(); ++i) {
        const auto r = routes[i].toObject();
        const int to = g.node(r.value("to").toString());
        for (const auto &from : comboRouteSources(r)) {
            const int f = g.node(from);
            if (f >= 0 && to >= 0 && f != to) g.edges.append({f, to, i, comboInputClass(r)});
        }
    }
    // Depth-first from the nodes in order marks back edges (an edge to a node still on the stack); the rest is a DAG.
    const int n = int(g.nodes.size());
    QVector<int> state(n, 0);
    QVector<bool> back(g.edges.size(), false);
    QVector<int> order;
    std::function<void(int)> visit = [&](int u) {
        state[u] = 1;
        for (int e = 0; e < g.edges.size(); ++e) {
            if (g.edges[e].from != u) continue;
            const int v = g.edges[e].to;
            if (state[v] == 1) back[e] = true;
            else if (state[v] == 0) visit(v);
        }
        state[u] = 2; order.prepend(u);
    };
    for (int u = 0; u < n; ++u) if (state[u] == 0) visit(u);
    // The strings pin their steps to the left (step i sits in column >= i), then longest path along the forward edges.
    QVector<int> col(n, 0);
    for (const auto &s : strings) {
        const auto steps = s.toObject().value("steps").toArray();
        for (int i = 0; i < steps.size(); ++i) { const int k = g.node(steps[i].toString()); if (k >= 0) col[k] = qMax(col[k], i); }
    }
    for (int u : order)
        for (int e = 0; e < g.edges.size(); ++e)
            if (g.edges[e].from == u && !back[e]) col[g.edges[e].to] = qMax(col[g.edges[e].to], col[u] + 1);
    QVector<int> perCol;
    for (int i = 0; i < n; ++i) {
        g.nodes[i].col = col[i];
        while (perCol.size() <= col[i]) perCol.append(0);
        g.nodes[i].row = perCol[col[i]]++;
        g.cols = qMax(g.cols, col[i] + 1);
        g.rows = qMax(g.rows, g.nodes[i].row + 1);
    }
    return g;
}

QVector<ComboSegment> planComboString(const QStringList &steps, const QJsonArray &routes,
                                      const QHash<QString, ComboStepInfo> &info, int defaultBuffer, bool addBuffer) {
    QVector<ComboSegment> plan;
    int start = 1;
    for (int i = 0; i < steps.size(); ++i) {
        ComboSegment seg;
        seg.move = steps[i];
        seg.start = start;
        const auto step = info.value(steps[i]);
        seg.length = step.length;
        const int playedOut = step.length > 0 ? step.length : 30;
        seg.cut = playedOut;
        if (i + 1 < steps.size()) {
            // The route to the next step: an exact source beats "*", then priority, then file order.
            int best = -1, bestScore = -1, bestPriority = 0;
            for (int r = 0; r < routes.size(); ++r) {
                const auto route = routes[r].toObject();
                if (route.value("to").toString() != steps[i + 1] || !validateComboRoute(route).isEmpty()) continue;
                const auto sources = comboRouteSources(route);
                const int score = sources.contains(steps[i]) ? 2 : sources.contains("*") ? 1 : 0;
                if (score == 0) continue;
                const int priority = route.value("priority").toInt();
                if (best < 0 || score > bestScore || (score == bestScore && priority > bestPriority)) { best = r; bestScore = score; bestPriority = priority; }
            }
            if (best >= 0) {
                const auto route = routes[best].toObject();
                const auto window = comboRouteWindow(route);
                const QString on = route.contains("on") ? route.value("on").toString() : QStringLiteral("hit");
                int cut = window.first;
                if ((on == "hit" || on == "block" || on == "contact") && step.firstHit > 0) cut = qMax(cut, step.firstHit);
                const int buffer = route.contains("buffer") ? route.value("buffer").toInt() : defaultBuffer;
                if (addBuffer) cut += buffer;
                if (window.second > 0) cut = qMin(cut, window.second);
                if (step.length > 0) cut = qMin(cut, step.length);
                seg.cut = qMax(1, cut);
                seg.linked = true; seg.route = route.value("name").toString(); seg.input = comboInputClass(route);
                seg.lo = window.first; seg.hi = window.second; seg.buffer = buffer;
            }
        }
        plan.append(seg);
        start += seg.cut;
    }
    return plan;
}
int comboStringFrames(const QVector<ComboSegment> &plan) {
    return plan.isEmpty() ? 0 : plan.last().start + plan.last().cut - 1;
}
} // namespace wb
