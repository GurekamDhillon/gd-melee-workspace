#pragma once
#include <QJsonObject>

namespace wb {
class Session;
QJsonObject throwStandIn(Session &);
void registerThrowStandInCommands(Session &);
} // namespace wb
