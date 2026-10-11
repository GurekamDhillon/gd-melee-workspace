#pragma once
#include <QString>

namespace wb {
// What a failed command or launch step says in the status bar, and the one action that can put it right.
enum class FixKind { None, ChooseGameExe, ChooseBlender, StartGame, StartBlender, Rebuild, ReloadFromDisk };
struct ErrorHelp {
    QString message;                 // always says what to do next, and keeps the raw reason
    FixKind fix = FixKind::None;     // the Fix button, when one action helps
    QString fixLabel;                // the button's text
};
// A stable id for a fix, for object names and tests.
QString fixName(FixKind fix);
// `command` is the command that failed (may be empty for a launch step); `raw` is its CommandError text.
ErrorHelp explainError(const QString &command, const QString &raw);
// The same for a status string that is not a CommandError (a launch check, a Blender step). An unrecognised
// string comes back unchanged with no fix.
ErrorHelp explainStatus(const QString &raw);
}
