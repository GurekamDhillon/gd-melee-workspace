# Section 2 delivery: navigation screens

This covers every navigation screen in the brief. Hubs are generated from one rule. Lists use the section 1 template. The grid, table, event and sound-test screens have their own templates. Section 1's conventions all still hold:
- coordinates are unsheared (`x' = x + (240 - y) * 0.25`, applied last);
- colours are kit tokens;
- text comes from the atlas.

## Build order

```
python pipeline/kit.py && python pipeline/font_atlas.py && python pipeline/glyphs.py \
  && python pipeline/icons.py && python pipeline/kit_ui.py && python pipeline/nav.py
```

Every script exits non-zero if any of its checks fail. All of them pass. `icons.py` draws every icon mask (this section's and the online screen's).

To convert, run from `melee/`, using the `menus` worktree's `png2gx.py`. The main checkout's copy has no I4 and no `--layout`.

```
python ../worktrees/menus/pc/tools/png2gx.py --layout ../menu/out_nav/hub_<screen>_layout.json ... \
    --layout ../menu/out_nav/event_layout.json --outdir ../_build/ui \
    --copy ../menu/out_nav/{hubs_layout,nav_motion,grid_layout,table_layout,soundtest_layout}.json \
           ../menu/out_nav/list_*_layout.json
```

This has been run. `_build/ui` now holds all 29 hub icons, `mark_completed`, `mark_locked`, `mark_new` and every JSON file above. Don't pass `out_nav/manifest.json` to `--layout`: that copies it over the kit's `manifest.json`.

## What was asked, and where it is

| Item | Status | Where |
|---|---|---|
| Versus hub with **Online** beside Melee, Tournament, Special Melee, Rules and Name Entry | done | `hub_versus_layout.json`. Online is rank 1, the biggest secondary tile. `preview/hub_versus_online_*` shows it selected |
| Hub labels from the font atlas, not baked | done | Every hub label is a text slot (the `hero`, `heading`, `label` or `row` role). The baked Arial Black `lbl_*` and `desc_*` textures are retired (listed in `manifest.json` → `retired`). The description strip is the chrome's text slot |
| `ico_data` | done | `2x/ico_data.png` (three stacked disks). The Data breadcrumb now has its icon, including in section 1's previews |
| Hub layout rule for 2–9 tiles | done | `hubs_layout.json`. Checked for n = 1–9 with the worst label in every slot. `preview/hub_rule_sheet.png` shows n = 2–9 |
| The hubs | done | main (5), solo (4), regular (3), stadium (3), versus (6), collection (3), data (5) |
| About 30 hub icons plus completed / locked / new marks | done | 29 icons at 256×256 and 3 marks. `preview/icons_sheet_2x.png` |
| Lists | done | `list_{multiman,special,options,rules,more_rules,records}_layout.json` |
| Item Switch / Random Stage Switch grid | done | `grid_layout.json`. 6 columns × 4 visible rows; any count scrolls. Previews use 31 items and 96 stages |
| Records table | done | `table_layout.json`: header row, stock icon + name, 4 numeric columns, totals row |
| Event Match list + detail | done | `event_layout.json`: number, name, completed/locked marks; detail with a disc-image slot, a 7-line paragraph and the best time |
| Sound Test | done | `soundtest_layout.json`: track rows, a 3-bar playing indicator and its loop |
| Motion | done | `nav_motion.json` is the hub motion moved to the kit convention: unsheared, with colour tokens |

## The hub rule (`hubs_layout.json`)

- **Cluster:** unsheared (90, 82)–(556, 390), the same space the engine's stand-in `fm_build` uses. The hero column is x 90–352. The secondaries share one column, x 360–556. The gutter is 8 px, showing the ink backplate.
- **Column heights:**
  - The step between tiles is r = min(1, 0.76 + 0.06·max(0, s − 3)), where s is the number of secondaries. For s ≤ 3 that is the prototype's 0.76. It flattens as the column fills, so tile 9 never becomes a sliver.
  - Edges use cumulative rounding, so the column ends exactly at the cluster bottom and no tile is more than 1 px off its share.
  - Resulting heights: n = 5 → 93/77/63/51; n = 6 → 70/62/54/48/42; n = 9 → 31–32 each.
- **Size classes** by tile height:

| Class | Height | Pad | Icon | Placement |
|---|---|---:|---:|---|
| hero | (rank 0) | 16 | 96 | icon top-right, label bottom-left |
| tall | ≥ 96 | 10 | 40 | icon top-right, label bottom-left |
| mid | 44–96 | 10 | 28 | icon right, label left, both centred |
| short | < 44 | 8 | 24 | icon right, label left, both centred |

- **Labels:**
  - The hero tries `hero` on 1 line, then 2 lines, then `heading` on 1 or 2, then `title`. So "REGULAR MATCH" and "TARGET TEST" become two `hero` lines, and "COLLECTION" drops to `heading`.
  - The secondaries share **one role per hub**, so the column reads evenly: the largest of `label`, `row`, `body` at which every secondary label fits, in 1 line or, except for short tiles, 2. Versus gets `label`. Data gets `row`, because of "SPECIAL MESSAGES".
  - No vanilla hub truncates, and neither does any 1–9 tile hub made entirely of "SPECIAL MESSAGES".
- **States:** ng uses `@face` / `@face_hi` / bone. sel uses gold / gold_dk / ink, with the plate in gold_dk and the lift at (−6.25, −5) unsheared, which is (−5, −5) on screen as in the prototype. On the main menu each tile takes its own section's colours.
- **Motion** (`nav_motion.json`): `tile_select`, `tile_deselect`, `tile_recoil`, `desc_in`, `desc_out`, `tile_confirm`, `tile_slide_out`, `tile_slide_in`, `chrome_out` and `chrome_in`. Values and timings are the prototype's. The only change is the lift's X, now in unsheared units. `slide_in_offsets` covers 9 tiles.

## Checks (all pass)

- **Hubs.** For every tile of every hub, and for n = 1–9 with worst-case labels:
  - title-safe at peak motion: the lift overshoot 1.3× plus the 1.03 scale, and recoil ±2 in every direction;
  - no label truncates;
  - labels never overlap icons, and labels and icons stay inside their tiles;
  - every icon texture exists;
  - label contrast ≥ 4.5:1 and icon contrast ≥ 3:1 (ng) in every section.
- **Lists:** every label fits at `row`, and every choice value fits.
- **Grid:** 4 rows × 6 columns stay inside title-safe with the cell lift, clear of the description strip and the scroll track.
- **Table:** it ends above the description strip. The name column doesn't reach the numbers. "LOSSES" and "99999" fit a 64 px column. The 20-character test names fit at body or caption.
- **Event:** the 7-line paragraph ends above BEST.
- **Kit checks** on every non-hub preview: footer hints fit, and title-safe holds with the kit's row and cell motion.
- **Icons:** the shape and hole counts survive at 2x of each icon's smallest draw.

## Previews (all looked at)

- Hubs: `hub_main`, `hub_solo`, `hub_regular`, `hub_stadium`, `hub_versus`, `hub_versus_online`, `hub_collection`, `hub_data`, `hub_data_last`, `hub_rule_n9`, `hub_rule_sheet`.
- Lists: `list_rules`, `list_options` (Erase Data with its danger stripe), `list_special` (10 rows, scrolled), `list_multiman`, `list_more_rules`.
- Others: `grid_items`, `grid_stages`, `table_records`, `event_match`, `sound_test`.

## Memory at 2x per composed screen (excluding disc art)

| Screen | KB |
|---|---:|
| Main menu | 577 |
| Solo | 577 |
| Regular Match / Stadium | 545 |
| Versus (6 tiles) | 641 |
| Collection | 417 |
| Data | 577 |
| Hub, 9 tiles | 449 |
| Lists | 161–193 |
| Item / Stage Switch | 194.5 |
| Records table | 194 |
| Event Match | 194 |
| Sound Test | 193.5 |

Everything is under 1 MB. Hubs cost more because the hero label uses the 256 KB `hero` atlas page (plus `heading` at 128 KB when a label steps down). Each hub icon is 32 KB.

## Open issues

1. **The hub is now unsheared** (the kit convention), and `nav_motion.json` matches. The engine currently plays `out_hub/hub_motion.json` in screen space. Moving to these files means applying joint transforms before the shear, in one place (`fp_evaluate` / `fp_draw_text`, as `_research/frontend-menus.md` already notes). `fm_build` can then follow `hubs_layout.json` in place of its ×0.76 stand-in.
2. **Online's rank in the Versus hub.** I put Online at rank 1, the biggest secondary tile, because it is GD's first priority. `fm_vs` doesn't have the item yet. Its icon is `ico_online`.
3. **Hub icons are 256×256** because any of them can be the hero. There are no mipmaps, so a 24 px draw (short tiles, the breadcrumb) minifies about 5:1 at 2x. The legibility check passes, but mipmaps or a 64×64 companion (`ico_*_s`) would be kinder if shimmer shows.
4. **Rows with a `→` chevron are drawn from the atlas.** No texture is needed.
5. **Not done:**
   - the Records sub-tables for bonus and misc (the same table template applies);
   - a dedicated Rumble per-port screen;
   - Movies and Snapshots browsing screens: they stay native per `frontend-menus.md`, and the brief lists no new art for them;
   - `mark_new` is drawn and converted, but no preview uses it yet (vanilla hides locked items).
6. **Sound test and online loops need the player's `loop` addition** (see `out_online/ONLINE.md`).
7. **The old `out_hub/` prototype still builds** and is what the engine reads today. It is superseded by `out_nav/`, but I left it in place so nothing breaks before the engine switches.
