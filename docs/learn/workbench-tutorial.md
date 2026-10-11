# Workbench tools: a hands-on tour

This tutorial uses the Qt **Geno Workbench** and its connected Blender view. Start with a prepared fighter project, a configured game executable and disc, and Blender. Use a copy of your project for the exercises. A move with at least one hitbox is enough for the first exercises; the Combo exercise needs a project with a combo file.

The Workbench saves source edits immediately. **Rebuild + reload** puts those edits into the game. You can undo an exercise before rebuilding if you only want to explore the tools.

## 1. Find a move and read its view

1. Find **Moves** and use **Search moves** (`Ctrl+F`). You can search by move name, clip name or move tag. Clear the search to see the groups **Ground attacks**, **Aerials**, **Specials**, **Throws** and **Movement** again.
2. Select a move with hitboxes. Its name appears in the central move view, above **Timeline**. Read the **Total**, **Active** and **Cancel** values: move length, active hitbox ranges and the declared cancel frame. Active and Cancel display **None** when the move has no active range or declared cancel frame; Total is numeric.
3. Select one of the move's hitboxes in the Moves list, or click its bar on the timeline. The **Hitbox** tab shows that hitbox's fields.
4. Hover a row marked `(not previewable)` to read why. These rows remain available for source inspection. A missing clip, a revival platform, a capture partner or initialized gameplay state may be needed before the engine can pose them. A motion missing from the current engine is marked for that session; restarting the engine allows another attempt.

In a tall window, Moves becomes an inspector tab. Click the current-move chip to return to it. **Open Hitbox after picking a move** can switch back to the Hitbox tab automatically in this layout.

## 2. Scrub the timeline and change a hitbox window

1. Click the timeline ruler to seek a frame. Frame **0** is the entry pose; frame **1** is the first move frame. Blender follows the selected move and frame when connected.
2. Click **Previous frame** or **Next frame**, or focus the timeline and press Left/Right. Seek to the first active frame of your selected hitbox, then step forward through its active window.
3. Press **Play** to advance the preview and **Pause** to stop it. **Loop** repeats the preview; the playback-speed selector offers **0.5x**, **1x** and **2x**.
4. Drag the start or end of a hitbox bar by one frame. Check **First active frame** and **Last active frame** in the inspector: these are the inclusive frames shown to you. For example, a hitbox shown as active on 3–4 is active on frames 3 and 4.
5. Press `Ctrl+Z` with focus outside a text editor to restore the original window. Press `Ctrl+Y` to redo, then undo again if you want to leave the project as it was.

Hitbox bars describe when the fighter's hitboxes are active. Projectile spawn markers show when a projectile is created. Combo route lanes show when the attacker can take a route into another move. These lanes share the ruler but edit different source records.

For a project with combo routes, click a route bar to select it in **Combo**. Drag the whole bar to move its window, or an end to resize it. Hover the bar to read the route and its window. Undo the drag after inspecting the corresponding **Window (frames)** fields.

## 3. Edit a hitbox and compare it with the built game

With a hitbox selected, try changing **Damage** by one point and finish the field edit. Read **What this hit does** to see the description update. Then inspect the fields below.

| Field | What to try |
|---|---|
| **Bone** / **Joint** | Inspect the attachment or semantic role before changing the hitbox's position. |
| **First active frame**, **Last active frame** | Match the values to the timeline bar. **Not cleared** means the script has no finite clear for this hitbox. |
| **Damage**, **Size** | Compare damage with the hitbox's radius in the Blender view. |
| **Angle**, **Knockback growth**, **Base knockback** | Inspect how launch direction and knockback are authored. |
| **Element**, **Shield damage** | Inspect the element code and the extra shield damage. |
| **Slot** | Inspect which hitbox slot the script writes. |
| **Hits grounded targets**, **Hits airborne targets** | Turn one off, read the description, then undo. |
| **Offsets and fixed knockback** | Expand this section to reveal **Offset X**, **Offset Y**, **Offset Z** and **Fixed knockback**. |

Changed fields have a small **Revert to last build** control. It restores that field to the value from the last build. **Undo** reverses the last edit; **Revert all** restores all changed fields to the built values. These operations can have different results if you have made several edits since building.

To practice duplication, select a hitbox and press `Ctrl+D`. The copy appears in the same move. Inspect it, then undo. **+ Add hitbox** creates a hitbox at the current timeline frame; **Delete** removes the selected hitbox, and undo brings it back.

Use **Checks** → **Run checks** and read **Problems**. The Hitbox tab also shows checks for the current move. Correct any reported timing disagreement before rebuilding.

## 4. Use the other inspector tabs

| Tab | Exercise |
|---|---|
| **Attributes** | Inspect fighter values and their units. Change one value, then undo or use its revert control. |
| **Checks** | Run checks, inspect Problems and the **Fidelity** information, then look at **History and review**. |
| **Clips** | Select an animation and use **Preview**. **Assign to move** changes the selected move's clip assignment; rebuild after an assignment you intend to keep. |
| **Render** | Inspect **Game and Blender**, including **Headless engine (no window)** and **Open in Blender**. This tab also has the frame-export controls. |
| **Projectiles** | Edit projectile definitions and the current move's spawn records, as described below. |
| **Combo** | Edit routes and named strings, as described below. |

## 5. Change a route and play a string

If Combo says the project has no combo file, use a project that declares one for this exercise. The tutorial does not require adding combo behavior to every fighter.

1. Select a move with a route. In **Combo**, select an entry under **Routes**. **All routes** includes routes from other moves; otherwise the list follows the current move.
2. Read **From**, **To**, **Input**, **Direction**, **When** and **Where**. A route is a cancel the attacker takes into another move. The read-only **Source (where this route comes from in XV2)** area preserves provenance where the project supplies it.
3. Change **Window (frames)** by one frame. The window uses inclusive, one-based move frames; an upper bound displayed as **to the end** continues to the move's end. Check that its route lane moves with the fields, then undo.
4. Inspect **Buffer**, **Priority** and **Ki cost**. Buffer controls how long an input press remains usable; the project supplies the combo default when a route omits it.
5. Use **+ Route** only when you want another route; **Delete route** removes the selected one. Undo either operation to restore your exercise state.
6. Under **Strings**, select a named sequence. **Steps** lists move names in order, separated by commas. **+ String** adds a sequence and **Delete string** removes the selected one.
7. Read **String map**. Its moves are nodes and its routes are arrows; click a move to select it.
8. Keep any edits you want, use **Rebuild + reload**, then select the string and press **Play string**. This plays its moves back to back in the game, cutting at route windows. Use it to inspect the sequence, then test the actual inputs with **Play in LAB** when evaluating gameplay.

The Qt Play string control is in the Combo tab. The Qt tooltip also identifies Blender's separate Play string control under Geno → Combo. The Blender card is the connection and visibility control for the 3D view.

## 6. Create and retime a projectile spawn

1. Select a previewable move and open **Projectiles**. If there is an existing projectile, select it. Otherwise **+ Projectile** creates a starter definition with a hitbox.
2. Inspect **Lifetime (frames)**, **Speed forward**, **Speed up**, **Gravity**, **Launch angle (deg)** and **Max live**. **Spawn forward**, **Spawn up** and **Spawn bone (part, -1 none)** control where it starts. **Model scale** and the homing fields apply when the projectile uses those features.
3. In **Hitboxes (offset from the projectile, size is the radius)**, inspect the projectile's own hitbox rows. **+ Hitbox** and **Delete hitbox** edit this list, independently of the fighter hitboxes.
4. Seek to the frame where you want the projectile to fire. Press **+ Spawn at this frame**. A record appears under **Spawns in this move (also on the timeline)** and a marker appears on the spawn lane.
5. Drag that marker by one frame and inspect the updated spawn record. Undo the drag. **Delete spawn** removes the selected spawn; **Delete last** removes the last projectile definition only when it is no longer referenced by a spawn.
6. Undo the starter projectile and spawn if they were only practice, or run checks and rebuild to test the version you want to keep.

Editing a projectile definition changes the projectile's behavior. Editing a spawn marker changes when this move creates it. A definition without a spawn in the move will not fire merely because you selected it.

## 7. Connect Blender, rebuild, and use the offered fixes

The card says **3D view is in Blender** and **Follows this move and frame**. Use **Open in Blender** when Blender is closed and **Show Blender** when it is already running. The connection chip reports whether Blender is running and following the current frame.

Keep the one-point Damage edit from exercise 3, then press the top-bar **Rebuild + reload** button or `F5`. Read the progress and result before comparing the rebuilt hitbox in Blender. Edits made during a rebuild are queued; when the button says **Rebuild again**, those later changes still need another build.

When an error appears, read its explanation and use the action it offers. The action's label names the fix; there is no universal Fix button.

| Offered action | When it helps |
|---|---|
| **Choose game exe…** | The game executable is missing or cannot start. |
| **Start game** | The engine is stopped or did not answer. |
| **Choose Blender…** | The Blender executable cannot be found or started. |
| **Start Blender** | Blender was closed. |
| **Reload from disk** | A file changed outside the Workbench; reload it, then repeat your edit. |
| **Rebuild + reload**, **Rebuild again**, **Run full rebuild** | The explanation calls for a rebuild. Correct the reported cause first if the build failed. |

A `(not previewable)` reason does not always have an automatic fix. For example, choosing a longer clip cannot supply a capture partner or restore missing action-state initialization.

## Shortcut practice

Press `F1` to open **Keyboard shortcuts**. Close it and try the following with focus on the Workbench timeline or another non-editing area.

| Key | Action |
|---|---|
| `F1` | Show or close the shortcut list. |
| `F5` | Rebuild and reload the game. |
| `Ctrl+Z` | Undo the last source edit. |
| `Ctrl+Y` or `Ctrl+Shift+Z` | Redo. |
| Left / Right | Previous / next frame. |
| Space | Play or pause. |
| `Ctrl+D` | Duplicate the selected hitbox. |
| Delete | Delete the selected hitbox. |
| `Ctrl+F` | Search moves. |

While typing in a field, editing keys belong to that field. Arrow keys in lists, selectors and tabs navigate those controls; put focus on the timeline when you want to step frames. Select a hitbox before duplicating or deleting it.

For the Geno engine's authoring format and a first fighter project, continue with [the fighter lessons](geno-fighters/README.md). This tour's labels and behavior were checked against the Qt Workbench's `workbench_window.cpp`, `hub_panel.cpp`, `panels.cpp`, `timeline.cpp`, `combo_widgets.cpp`, `combo_model.h`, `projectile_widgets.cpp` and `error_help.cpp` under `tools/release/launcher/qt/workbench/`.
