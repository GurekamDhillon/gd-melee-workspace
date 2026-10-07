#include "atlas.h"
#include <QDebug>
#include <QFile>
#include <QFontDatabase>
#include <QJsonDocument>
#include <QJsonObject>

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
}
