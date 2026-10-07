#pragma once
#include <QColor>
#include <QFont>
#include <QFontMetricsF>
#include <QPolygonF>
#include <QRectF>
#include <QString>
#include <QVector>
#include <algorithm>
#include <cmath>
namespace launcher::atlas {
void initialize();                         // loads :/atlas/tokens.json and the font files; safe to call twice
QColor colour(const QString &token);       // an unknown token is an invalid QColor
int px(const QString &token);              // 0 for an unknown token
int ms(const QString &token);
bool reducedMotion();                      // the platform asks for fewer animations (Windows: client-area animation off)
int motion(const QString &token);          // ms(token), or 0 when the platform asks for reduced motion: both tweens become cuts
enum class Role { Cap12, Cap14, Cap16, Cap20, Title, Hero, Body12, Body14, Row16 };
QFont font(Role role);

// geometry: QtGui value types only, so it is tested without a window
QPolygonF plate(const QRectF &r, qreal chamfer);                 // top-left and bottom-right corners cut; 4 points when the chamfer does not fit
QRectF lifted(const QRectF &r, bool focus);                      // 2 px up when focused
QRectF frontEdge(const QRectF &r, qreal edge);                   // the strip along the bottom
QRectF tick(const QRectF &row);                                  // a row's focus tick: 4 px wide at the left, inset 6
QVector<QRectF> brackets(const QRectF &cell, qreal arm, qreal stroke);   // four registration brackets as eight thin rectangles
QString fit(const QFontMetricsF &fm, const QString &text, qreal width);  // the whole text, or elided with an ellipsis; empty under 8 px of room
double contrast(const QColor &a, const QColor &b);               // WCAG relative contrast
}
