#include "error_help.h"
#include "window.h"

// Every CommandError the Workbench can show is mapped here to wording that says what to do. The core strings
// stay as they are: tests, the MCP server and the Blender add-on match on them.
namespace wb {
using launcher::t;
namespace {
bool has(const QString &raw, const char *needle) { return raw.contains(QLatin1String(needle), Qt::CaseInsensitive); }
QString after(const QString &raw, const char *prefix) {
    const int at = raw.indexOf(QLatin1String(prefix), 0, Qt::CaseInsensitive);
    return at < 0 ? raw : raw.mid(at + int(qstrlen(prefix))).trimmed();
}
ErrorHelp help(const QString &message, FixKind fix = FixKind::None, const QString &label = {}) { return {message, fix, label}; }
bool isEdit(const QString &command) {
    static const QStringList edits{"edit_hitbox", "add_hitbox", "delete_hitbox", "duplicate_hitbox", "edit_attribute",
                                   "assign_clip", "ground_modes", "revert_change", "revert_all", "accept", "undo", "redo"};
    return edits.contains(command);
}
}
QString fixName(FixKind fix) {
    switch (fix) {
    case FixKind::ChooseGameExe: return "choose_game_exe";
    case FixKind::ChooseBlender: return "choose_blender";
    case FixKind::StartGame: return "start_game";
    case FixKind::StartBlender: return "start_blender";
    case FixKind::Rebuild: return "rebuild";
    case FixKind::ReloadFromDisk: return "reload_from_disk";
    case FixKind::None: break;
    }
    return {};
}
ErrorHelp explainStatus(const QString &raw) {
    // The game program.
    if (has(raw, "Game executable not found") || has(raw, "engine executable is not configured"))
        return help(t("The game program was not found. Choose the game exe, then start the game. (%1)",
                      "No se encontró el programa del juego. Elige el ejecutable del juego y inicia el juego. (%1)").arg(raw),
                    FixKind::ChooseGameExe, t("Choose game exe…", "Elegir ejecutable…"));
    if (has(raw, "Select a disc on Play"))
        return help(t("No game disc is selected. Pick a disc on the Play tab, then reopen this fighter. (%1)",
                      "No hay disco seleccionado. Elige un disco en la pestaña Jugar y vuelve a abrir el luchador. (%1)").arg(raw));
    if (has(raw, "engine exited before console was ready") || has(raw, "cannot reserve console port") ||
        has(raw, "Process failed to start") || has(raw, "workbench payload directory"))
        return help(t("The game could not start. If the Game exe is wrong, choose the right one; otherwise start it again. (%1)",
                      "El juego no pudo iniciarse. Si el ejecutable es incorrecto, elige el correcto; si no, inícialo de nuevo. (%1)").arg(raw),
                    FixKind::ChooseGameExe, t("Choose game exe…", "Elegir ejecutable…"));
    if (has(raw, "scene rejected or fighter not loaded") || has(raw, "engine exited while loading the fighter"))
        return help(t("The game started but did not load this fighter. The built package may be out of date: rebuild it, then start the game. (%1)",
                      "El juego se inició pero no cargó este luchador. Puede que el paquete esté desactualizado: reconstrúyelo e inicia el juego. (%1)").arg(raw),
                    FixKind::Rebuild, t("Rebuild + reload", "Reconstruir + recargar"));
    if (has(raw, "timeout waiting for engine console") || has(raw, "engine start cancelled"))
        return help(t("The game did not answer in time. Start it again; if it keeps failing, read its log in the run folder. (%1)",
                      "El juego no respondió a tiempo. Vuelve a iniciarlo; si sigue fallando, lee su registro en la carpeta de ejecución. (%1)").arg(raw),
                    FixKind::StartGame, t("Start game", "Iniciar juego"));
    // Blender.
    if (has(raw, "Blender not found") || has(raw, "Blender executable is not configured") || has(raw, "Could not start Blender"))
        return help(t("Blender could not be started. Choose the Blender program (or set GW_BLENDER), then open Blender again. (%1)",
                      "No se pudo iniciar Blender. Elige el programa de Blender (o define GW_BLENDER) y ábrelo de nuevo. (%1)").arg(raw),
                    FixKind::ChooseBlender, t("Choose Blender…", "Elegir Blender…"));
    if (has(raw, "Blender is not running") || has(raw, "Blender is closed") || has(raw, "Blender closed"))
        return help(t("Blender is closed. Start Blender with this fighter, then try again. (%1)",
                      "Blender está cerrado. Inícialo con este luchador y vuelve a intentarlo. (%1)").arg(raw),
                    FixKind::StartBlender, t("Start Blender", "Iniciar Blender"));
    if (has(raw, "add-on not found") || has(raw, "bootstrap.py was not found") || has(raw, "Set art_blend or art_glb") ||
        has(raw, "Fighter art file was not found"))
        return help(t("Blender cannot open this project yet. %1", "Blender aún no puede abrir este proyecto. %1").arg(raw));
    // The play tool.
    if (has(raw, "Package is stale"))
        return help(t("The built package is out of date and no rebuild step is set. Add a rebuild entry to workbench.json, or build from the terminal, then play. (%1)",
                      "El paquete compilado está desactualizado y no hay paso de reconstrucción. Añade rebuild a workbench.json o compila desde la terminal y luego juega. (%1)").arg(raw));
    if (has(raw, "Python was not found"))
        return help(t("Python is needed to play from the Workbench. Install Python or set GW_PYTHON, then try again. (%1)",
                      "Se necesita Python para jugar desde el Workbench. Instala Python o define GW_PYTHON y vuelve a intentarlo. (%1)").arg(raw));
    return help(raw);
}
ErrorHelp explainError(const QString &command, const QString &raw) {
    if (raw.compare("engine not running", Qt::CaseInsensitive) == 0)
        return help(t("Engine not running. Start the game, then try again.", "Motor detenido. Inicia el juego y vuelve a intentarlo."),
                    FixKind::StartGame, t("Start game", "Iniciar juego"));
    // The game, Blender and play launch problems share one table.
    const ErrorHelp launch = explainStatus(raw);
    if (launch.fix != FixKind::None || launch.message != raw) return launch;
    if (has(raw, "changed externally") || has(raw, "stale proposal"))
        return help(t("Not applied: changed externally. %1 was edited outside the Workbench since it was loaded. Reload from disk to pick up that change, then repeat your edit.",
                      "No aplicado: cambiado externamente. %1 se editó fuera del Workbench desde que se cargó. Recarga desde el disco para tomar ese cambio y repite tu edición.")
                        .arg(after(raw, "changed externally:")),
                    FixKind::ReloadFromDisk, t("Reload from disk", "Recargar desde disco"));
    if (has(raw, "rollback failed"))
        return help(t("An edit failed partway and could not be fully undone. The original files are kept in .workbench/snapshots: copy them back by hand. (%1)",
                      "Una edición falló a medias y no se pudo deshacer por completo. Los archivos originales están en .workbench/snapshots: cópialos a mano. (%1)").arg(raw));
    if (command == "reload_from_disk")
        return help(t("The project files could not be read: %1. Fix the file on disk (usually invalid JSON), then reload again.",
                      "No se pudieron leer los archivos del proyecto: %1. Corrige el archivo en el disco (suele ser JSON no válido) y recarga de nuevo.").arg(raw),
                    FixKind::ReloadFromDisk, t("Try again", "Reintentar"));
    if (has(raw, "reload failed"))
        return help(t("Your edit was saved, but the project data could not be read again. Fix the file, then reload from disk. (%1)",
                      "Tu edición se guardó, pero no se pudieron releer los datos del proyecto. Corrige el archivo y recarga desde el disco. (%1)").arg(raw),
                    FixKind::ReloadFromDisk, t("Reload from disk", "Recargar desde disco"));
    if (has(raw, "cannot save history"))
        return help(t("The edit history could not be saved. Check that the project folder is writable and the disk is not full. (%1)",
                      "No se pudo guardar el historial de ediciones. Comprueba que la carpeta del proyecto se pueda escribir y que el disco no esté lleno. (%1)").arg(raw));
    // Rebuilds.
    if (has(raw, "rebuild not configured"))
        return help(t("This project has no rebuild step. Add a \"rebuild\" command to workbench.json, or build from the terminal. (%1)",
                      "Este proyecto no tiene paso de reconstrucción. Añade un comando \"rebuild\" a workbench.json o compila desde la terminal. (%1)").arg(raw));
    if (has(raw, "rebuild refused"))
        return help(t("The rebuild was refused: a hitbox's timing disagrees with its script. Fix the hitbox frames, then rebuild again. (%1)",
                      "Se rechazó la reconstrucción: el tiempo de un hitbox no coincide con su script. Corrige los cuadros del hitbox y reconstruye de nuevo. (%1)").arg(raw));
    if (has(raw, "rebuild failed to start"))
        return help(t("The rebuild command could not start. Check the rebuild entry in workbench.json. (%1)",
                      "No pudo iniciarse el comando de reconstrucción. Revisa la entrada rebuild de workbench.json. (%1)").arg(raw));
    if (has(raw, "rebuild timed out"))
        return help(t("The rebuild ran for 30 minutes and was stopped. Try again; if it keeps hanging, run the build from the terminal to see why. (%1)",
                      "La reconstrucción duró 30 minutos y se detuvo. Inténtalo de nuevo; si se cuelga, ejecuta la compilación desde la terminal para ver por qué. (%1)").arg(raw),
                    FixKind::Rebuild, t("Rebuild again", "Reconstruir de nuevo"));
    if (has(raw, "full build") || (has(raw, "rebuild failed") && (has(raw, "Stage A") || has(raw, "refused"))))
        return help(t("The built package is out of date and needs a full build first. Rebuild runs it for you; it takes longer than a gameplay-only build. (%1)",
                      "El paquete compilado está desactualizado y necesita una compilación completa. Reconstruir la ejecuta por ti y tarda más que una de solo jugabilidad. (%1)").arg(raw),
                    FixKind::Rebuild, t("Run full rebuild", "Compilación completa"));
    if (has(raw, "rebuild failed"))
        return help(t("The rebuild failed. Read the output below, fix the cause, then rebuild again. (%1)",
                      "Falló la reconstrucción. Lee la salida, corrige la causa y reconstruye de nuevo. (%1)").arg(raw),
                    FixKind::Rebuild, t("Rebuild again", "Reconstruir de nuevo"));
    if (has(raw, "No build baseline"))
        return help(t("There is no build to compare against yet. Rebuild once, then this works. (%1)",
                      "Aún no hay una compilación con la que comparar. Reconstruye una vez y esto funcionará. (%1)").arg(raw),
                    FixKind::Rebuild, t("Rebuild + reload", "Reconstruir + recargar"));
    // Edits and navigation.
    if (has(raw, "unknown row:"))
        return help(t("That move is no longer in the project. Reload from disk to refresh the move list. (%1)",
                      "Ese movimiento ya no está en el proyecto. Recarga desde el disco para actualizar la lista. (%1)").arg(raw),
                    FixKind::ReloadFromDisk, t("Reload from disk", "Recargar desde disco"));
    if (has(raw, "no row loaded"))
        return help(t("Choose a move first, then try again. (%1)", "Elige primero un movimiento y vuelve a intentarlo. (%1)").arg(raw));
    if (raw.compare("nothing to undo", Qt::CaseInsensitive) == 0) return help(t("Nothing to undo.", "Nada que deshacer."));
    if (raw.compare("nothing to redo", Qt::CaseInsensitive) == 0) return help(t("Nothing to redo.", "Nada que rehacer."));
    if (has(raw, "play timed out"))
        return help(t("Playback took too long and was stopped. Restart the game and try again. (%1)",
                      "La reproducción tardó demasiado y se detuvo. Reinicia el juego y vuelve a intentarlo. (%1)").arg(raw),
                    FixKind::StartGame, t("Restart game", "Reiniciar juego"));
    if (command == "engine_restart" || command == "reload")
        return help(t("The game could not start: %1. Start it again, or choose a different Game exe in Settings.",
                      "El juego no pudo iniciarse: %1. Inícialo de nuevo o elige otro ejecutable en Ajustes.").arg(raw),
                    FixKind::StartGame, t("Start game", "Iniciar juego"));
    if (isEdit(command))
        return help(t("Your edit was not applied: %1. Check the value and try again.", "Tu edición no se aplicó: %1. Revisa el valor e inténtalo de nuevo.").arg(raw));
    return help(t("Command failed: %1. Nothing was changed; try again.", "Error del comando: %1. No se cambió nada; inténtalo de nuevo.").arg(raw));
}
}
