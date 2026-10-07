#pragma once
#include <QColor>
#include <QFont>
#include <QString>
namespace launcher::atlas {
void initialize();                         // loads :/atlas/tokens.json and the font files; safe to call twice
QColor colour(const QString &token);       // an unknown token is an invalid QColor
int px(const QString &token);              // 0 for an unknown token
int ms(const QString &token);
enum class Role { Cap12, Cap14, Cap16, Cap20, Title, Hero, Body12, Body14, Row16 };
QFont font(Role role);
}
