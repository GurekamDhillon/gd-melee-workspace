#include "atlas.h"
#include <QDebug>
#include <QFile>
#include <QFontDatabase>
#include <QJsonDocument>
#include <QJsonObject>
#ifdef Q_OS_WIN
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

namespace launcher::atlas {
static QJsonObject tokens;
static bool loaded = false;
static QString barlow = "Barlow Condensed", sans = "Source Sans 3";

static QJsonObject readJson(const char *path) {
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly)) { qWarning() << "atlas: cannot open" << path; return {}; }
    return QJsonDocument::fromJson(f.readAll()).object();
}
void initialize() {
    if (loaded) return;
    loaded = true;
    tokens = readJson(":/atlas/tokens.json");
    for (const char *p : {":/fonts/barlow-semibold.ttf", ":/fonts/barlow-bold.ttf", ":/fonts/sourcesans-semibold.otf"}) {
        const int id = QFontDatabase::addApplicationFont(p);
        if (id < 0) qWarning() << "atlas: font did not load:" << p;
    }
}
QColor colour(const QString &token) {
    const auto v = tokens["colours"].toObject().value(token);
    if (!v.isDouble()) return {};
    const quint32 c = quint32(v.toDouble());                        // 0xRRGGBBAA
    return QColor(int(c >> 24 & 0xff), int(c >> 16 & 0xff), int(c >> 8 & 0xff), int(c & 0xff));
}
int px(const QString &token) { return tokens["px"].toObject().value(token).toInt(0); }
int ms(const QString &token) { return tokens["ms"].toObject().value(token).toInt(0); }
bool reducedMotion() {
#ifdef Q_OS_WIN
    BOOL on = TRUE;
    if (SystemParametersInfoW(SPI_GETCLIENTAREAANIMATION, 0, &on, 0)) return !on;
#endif
    return false;                                                    // no platform hint: the tweens run
}
int motion(const QString &token) { return reducedMotion() ? 0 : ms(token); }

QFont font(Role role) {
    const bool cap = role == Role::Cap12 || role == Role::Cap14 || role == Role::Cap16 || role == Role::Cap20;
    const bool bold = role == Role::Title || role == Role::Hero;
    QFont f(cap || bold ? barlow : sans);
    int size = 16;
    switch (role) {
    case Role::Cap12: case Role::Body12: size = px("t-cap"); break;
    case Role::Cap14: case Role::Body14: size = px("t-body"); break;
    case Role::Cap16: case Role::Row16: size = px("t-row"); break;
    case Role::Cap20: size = px("t-label"); break;
    case Role::Title: size = px("t-title"); break;
    case Role::Hero: size = px("t-hero"); break;
    }
    if (size < 12) size = 12;
    f.setPixelSize(size);
    f.setWeight(bold ? QFont::Bold : QFont::DemiBold);
    if (cap) f.setLetterSpacing(QFont::AbsoluteSpacing, 0.1 * size);   // tracked +0.10 em
    return f;
}

QPolygonF plate(const QRectF &r, qreal c) {
    if (c <= 0 || c * 2 >= r.width() || c * 2 >= r.height()) return QPolygonF{r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft()};
    return QPolygonF{{r.left() + c, r.top()}, {r.right(), r.top()}, {r.right(), r.bottom() - c}, {r.right() - c, r.bottom()}, {r.left(), r.bottom()}, {r.left(), r.top() + c}};
}
QRectF lifted(const QRectF &r, bool focus) { return focus ? r.translated(0, -2) : r; }
QRectF frontEdge(const QRectF &r, qreal e) { return QRectF(r.left(), r.bottom() - e, r.width(), e); }
QRectF tick(const QRectF &row) { return QRectF(row.left(), row.top() + 6, 4, row.height() - 12); }
QVector<QRectF> brackets(const QRectF &c, qreal arm, qreal s) {
    return { {c.left(), c.top(), arm, s}, {c.left(), c.top(), s, arm}, {c.right() - arm, c.top(), arm, s}, {c.right() - s, c.top(), s, arm},
             {c.left(), c.bottom() - s, arm, s}, {c.left(), c.bottom() - arm, s, arm}, {c.right() - arm, c.bottom() - s, arm, s}, {c.right() - s, c.bottom() - arm, s, arm} };
}
QString fit(const QFontMetricsF &fm, const QString &text, qreal width) {
    if (width < 8 || text.isEmpty()) return {};
    if (fm.horizontalAdvance(text) <= width) return text;
    return fm.elidedText(text, Qt::ElideRight, width);
}
static double lum(const QColor &c) {
    auto ch = [](double v) { v /= 255.0; return v <= 0.03928 ? v / 12.92 : std::pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * ch(c.red()) + 0.7152 * ch(c.green()) + 0.0722 * ch(c.blue());
}
double contrast(const QColor &a, const QColor &b) {
    const double la = lum(a), lb = lum(b), hi = std::max(la, lb), lo = std::min(la, lb);
    return (hi + 0.05) / (lo + 0.05);
}
}
