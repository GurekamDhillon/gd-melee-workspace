#pragma once
#include "command_registry.h"
#include "file_store.h"
#include "history.h"
#include "geno_data.h"
#include <memory>
#include <functional>

namespace wb {
class EngineBackend;


class Session {
public:
    Session(const QString &projectDir, EngineBackend *engine);
    ~Session();
    Session(const Session &) = delete;
    Session &operator=(const Session &) = delete;

    FileStore &files();
    History &history();
    CommandRegistry &registry();
    EngineBackend *engine(); // Borrowed; null for an offline session.
    GenoData &data();        // Lazily built from files(); reloaded after every applied commit.
    bool agentProposals = false; // the MCP server sets true: agent edits are proposals until a human accepts
    QString currentRow;
    QJsonObject camera, overlays;
    // Ephemeral Qt/Blender handoff, accessed only by the Session worker.
    // Never persisted in source or history. ui_view_state ACKs only this PID.
    QJsonObject uiView;
    qint64 blenderPid = 0, blenderAckRevision = 0;
    // Task 6 installs data().reload(); called after persisted edits, never for proposals.
    std::function<void()> onApplied = [] {};

    // The command path for changing source files: snapshot, apply/propose, and persist history.
    QJsonObject commit(const CommandContext &ctx, const QString &command, const QJsonObject &args,
                       const QString &summary, const QVector<FileChange> &changes);
    QString historyPath() const; // <project>/.workbench/history.json

private:
    void saveHistory(const History &history) const;
    FileStore files_;
    std::unique_ptr<GenoData> data_;
    History history_;
    CommandRegistry registry_;
    EngineBackend *engine_;
};
} // namespace wb
