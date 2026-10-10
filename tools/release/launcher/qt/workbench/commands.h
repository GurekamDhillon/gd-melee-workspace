#pragma once
#include "file_store.h"
#include <QJsonObject>
#include <QVector>

namespace wb {
class Session;
void registerViewCommands(Session &);    // Task 10
void registerRowCommands(Session &);     // Task 10
void registerHitboxCommands(Session &);  // Task 10
void registerClipCommands(Session &);    // Task 10
void registerGroundCommands(Session &);  // Task 14
void registerSaveCommands(Session &);
// App entry points register explicitly; a Session constructor does not register commands.
void registerAllCommands(Session &);
// {changes:[{path, bytes_before, bytes_after}]}; no source bytes in a command reply.
QJsonObject changeToJson(const QVector<FileChange> &);
} // namespace wb
