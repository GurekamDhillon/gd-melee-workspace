# ROGUELITE 100/100 acceptance ledger

Integration lane: `_build/integration/roguelite-100`
Wrapper branch `agent/roguelite-100-integration` (from `agent/linux-qt-launcher` @ `6b94b78`)
Game branch `agent/roguelite-100-game` (from `agent/linux` @ `5664a6db1`)

Status vocabulary: `missing` · `implemented` · `integration-tested` · `native-tested` · `human-reviewed` · `accepted`
Evidence provenance: **stub** = deterministic engine double · **native** = real executable · **human** = controller/visual/listening · **PENDING-HUMAN** = required, not yet obtained

## 1. Verified baseline (this lane, 2026-09-30)

| Check | Command | Result |
|---|---|---|
| Pure/stub suite | `python3 -m unittest discover -s tools/roguelite -p 'test_*.py'` | **247 pass, 1 skip** (root 244 + adapter capacity group + export-loss regression + gene-world suite) |
| Native link | `tools/port/build_linux.sh` | **LINK_OK**, 1044 objects, 72 libraries |
| Bridge fixpoint | (same) | **stable** on pass 1/4, `18828/18828` entries resolved |
| Bridge ABI audit | (same) | **OK**, `0` ECX/EDX prologue violations |
| Native tests | `./melee --test --iso <vanilla>` | **214/214 pass** (stub-independent) |
| Genome P1 lane | `_build/model-tests/gene-world-capacity` | **246 pass** |

**Source-to-binary relationship established.** The integration lane reproduces a working executable from:
tracked+seeded native source + 22 untracked-but-included `.inc`/`.h` + **disc-extracted generated headers** (`build/GALE01/include`, gitignored, copied by `tools/port/agent_new.sh:82`). A clone without the disc cannot build; this is correct and must never be committed.

## 1b. Commit map (all local; nothing pushed, no release)

Game repo `agent/roguelite-100-game`:
| Commit | Contents |
|---|---|
| `e9cd3286e` | 17 untracked includes + seam test + its harness (2443 lines) |
| `244f00710` | 33-file native patch. **Also carries two Lua files the message omits:** `gene_actions.lua` (accepted optional intent hooks, `f33fced`) and `main.lua` (R2 notice fix). Flagged for the reviewer rather than rewriting history |
| `d5ba31d98` | `runtime_gene_world.lua` adapter + character_parts_lab + effects_lab |

Wrapper `agent/roguelite-100-integration`:
| Commit | Contents |
|---|---|
| `04060d4` | 6 art generators + review triple + `menu/concepts` + `tools/model_parts` |
| `3c2d6b2` | campaign / presentation / gene-world / gene-action / enemy-behavior suites |
| `b0d5556` | ledger |
| `7baf4c2` | ledger, completion plan, watched retests, scripting, research notes, .gitignore |
| (this) | wire `stage_seam_test.py` into `ci_linux.sh` |

Generated `pc/platform/gw_mex_bridge.c` remains uncommitted by design.

## 2. Integration lane seeding record

| Seeded | Count | Note |
|---|---|---|
| Native modified tracked files | 32 | mirrors root's dirty tree exactly |
| Native untracked entries | 22 | **17 are `#include`d by tracked `.c`** — without these a clean tree cannot compile |
| Wrapper modified tracked | 5 | |
| Wrapper untracked source/docs/tools | 19 | includes the 6 untracked `menu/pipeline/*.py` generators |
| Generated assets | 44 MB | `out_roguelite` 26M, `out_roguelite_expansion` 13M, `out_effects_study` 5M, `out_brand` 344K |
| Frozen candidate | gene-world adapter | `runtime_gene_world.lua` @ `0195e4c0` |

## 3. Milestone status

### M1 — Trustworthy source/build baseline
| Requirement | Status | Evidence / remaining |
|---|---|---|
| Source reproduces tested exe | **integration-tested** | §1. Link+bridge+ABI+214/214 from this lane |
| Native changes inventoried | **integration-tested** | `reports/A1-native-inventory.md`. 54 entries: A=39/3827, B=1/61785, C=4/625, D=10/707 |
| Clean tree compiles | **native-tested** | `e9cd3286e` lands the 17 untracked includes; `244f00710` lands the 33-file native patch. Verified from a **clean clone**: seam test passes, LINK_OK, 214/214. Still requires disc-extracted `build/GALE01/include` (gitignored) |
| Generated assets reproducible | **partial** | `04060d4` lands the 6 generators, so the pipeline is now reproducible. **Remaining:** `DEPENDENCIES.md:36` still claims "Python 3 (standard library only)" while the generators need Pillow/fontTools/rsvg-convert/Blender/playwright, and the Pillow venv has no creation recipe (M1 open item) |
| Native patches landed with focused checks | **native-tested** | `244f00710` (33 files) + `e9cd3286e` (17 includes + seam test) + `d5ba31d98`. `stage_seam_test.py` wired into `ci_linux.sh`; it previously passed ONLY with `script_game.c` dirty and now passes from a clean clone. Generated `gw_mex_bridge.c` deliberately never staged |
| Bridge separated from source | **integration-tested** | `gw_mex_bridge.c` is bucket B, regenerates per build — must never be staged |

### M2 — Physical catalogue and generated runs
| Requirement | Status | Evidence / remaining |
|---|---|---|
| Corrected ascent spawn/arrival | **human-reviewed (partial)** | User: "Stairs are perfect"; Jigglypuff/Kirby ascent+return reach without falling (native) |
| Jigglypuff return pop candidate | **PENDING-HUMAN** | automated classifier candidate, not a confirmed snag |
| Bowser return | **missing** | placement refused; unresolved |
| Both merge arrivals | **missing** | latest automated left-entry fell |
| Drop-through / one-way | **missing** | **no drop traversal pass at all** |
| Full roster coverage | **missing** | large/small/floaters/fast-fallers/swords/partners/transforms unproven |
| Live v2 generation seam | **missing** | **all 29 recipes `certified=false`** (`room_recipes.lua:82`, refused by `adapter.lua:47`) — probed; `route:create` returns nil. Played path is the legacy v1 slice |
| Park unused fighter slots | **missing** | `main.lua:836` always launches `p2='fox/c0/cpu9'`; stands at x=58 in every exploration room |

### M3 — Native gene action integrity
| Requirement | Status | Evidence / remaining |
|---|---|---|
| Adapter contribution-capacity P1 | **integration-tested (landed, committed)** | `d5ba31d98` (game) + wrapper commit pending;  Reserve before `provider.apply`; refuse before spend via intent validation. Verified 1 apply/1 release/1 live token at `max_contributions=1`, guard + conversion, recovery after confirmed release. **Landed.** Coupling found and honoured: the adapter requires the accepted `gene_actions.lua` `f33fced` optional intent hooks; root's `994bfe3d` alone does not work — they must land together |
| Native hit/armor acceptance | **missing (P1 defect)** | `reports/B1-native-hit.md`. `ftColl_80076640` (`src/melee/ft/ftcoll.c:216-237`) has **no refusal arm** — every `false` follows armor mutation at `:221`. `script_game.c:2426-2428,2503` map absorbed→`false`; `main.lua:768` then refunds. `docs/scripting.md:312` contract is wrong. **Zero test coverage** |
| Per-host/per-direction capabilities | **implemented** | honest refusal; unknown occlusion stays unavailable |
| Event provenance | **missing** | no stable attack-instance identity for multihit/linger/trade/reflect |
| Cinder/Rime/Thermal Shock native loops | **missing** | not proven under normal controller combat |
| Families/placements/reactions breadth | **missing** | Core offers Cinder/Rime only |

### M4 — Encounters, bosses, capable opponents
| Requirement | Status | Evidence / remaining |
|---|---|---|
| Encounter composition + handover | **integration-tested** | `runtime_encounters.lua` covered by 42 stub tests (decision logic only) |
| `encounter_behaviors.lua` + `boss_behaviors.lua` | **implemented, NOT REACHABLE** | 1545 lines complete + tested, **absent from `prepare.py:34`, zero callers** |
| Non-fighter differentiation | **missing** | `reports/B2-encounters-ai.md`: all custom actors share one identical gene cycle, fixed 24f telegraph. `motion`/`ledge`/`fall`/`tells` in `enemy_catalogue.lua:16-21` are inert data |
| Boss phases | **missing** | stocks+potency only (`runtime_encounters.lua:198,339`); code admits `phase = kos+1` is not the authored mechanic (`:587-590`) |
| Reinforcement timing / activation regions | **missing** | do not exist |
| Native enemy control surface | **missing (critical path)** | whole scripted enemy API is 6 functions (`gw_script.c:5658-5659`), **none moves an actor or sets vulnerability** |
| AI adequacy | **integration-tested, inadequate** | no 20XX/UnclePunch in code; emits exactly 2 inputs (`technical_ai.inc:139-140`), no spacing/punishment/approach-retreat/gene use |
| Illegal observation | **integration-tested (clean)** | 10/10 verifier checks pass — real strength, preserve |

### M5 — Inventory, equipment, economy
| Requirement | Status | Evidence / remaining |
|---|---|---|
| `inventory.lua`/`equipment.lua`/`run_history.lua` | **implemented, NOT REACHABLE** | `reports/B3`: not bundled (`prepare.py:34-39`), zero callers. 16 tests `loadfile` by path, so they test unshipped code |
| Consumables | **partial** | one item; Restore is a raw int (`core.lua:47`), no ownership/stack/capacity/cooldown |
| Equipment | **missing** | no slots; only genes-as-body-parts (`core.lua:185-196`) |
| Victory export | **missing — R2 OPEN** | Core **refuses** a non-nil id at 128 (`core.lua:321`, "choose no export"); **main elects** `id=nil`. Truthful-notice subfix done and tested: a `failure` notice names the gene, states the cause and states the real consequence, and recommends **no** action that does not exist. **Still required:** an explicit choose/replace/discard flow, or a durable pending export reachable through finished-run UI *and after relaunch*, with original-run ownership and exactly-once export. A finished run cannot be resumed (`core.lua:318` returns the existing result; `main.lua:334` drops the run), so the gene is **not** recoverable from the finished run and the checkpoint bytes do not establish recovery |
| Discard/replacement | **missing** | `menus.lua:236` needs `ctx.capacity` never supplied (`main.lua:779-783`); no `Menus.apply` discard branch |
| v1 restore rollback | **missing** | `main.lua:1021` ignores `save()` return; v2 path is correct |
| Reward-offer persistence | **integration-tested** | v2 only (`route.lua:45`); v1/v2 `claimed` key mismatch remains (`menus.lua:339` vs `runtime_rewards.lua:304`) |
| Economy tuning | **missing** | sim exists but disconnected from live rewards; asserts bounds, never rates |

### M6 — Product UI
| Requirement | Status | Evidence / remaining |
|---|---|---|
| Recursive tree + Up latch | **integration-tested** | verified through real edges; works in both routes since root landed `sync_loadout()` |
| Compact rail | **integration-tested** | drawn at real `Hud.layout` coordinates; 258×61 (~4% canvas); no permanent inventory panel; reduced motion from real `config.txt` |
| HUD ownership restore | **integration-tested** | claimed only while live; returned on leave/error/match-end/unload |
| All screens usable | **missing** | `reports/B4-ui.md`: **reward screen has no exit** (`menus.lua:264` honours B only in `parents`, legend at `:520` advertises it); **4 of 9 screens unreachable** (`map`,`onboarding`,`settings`,`ending`); `Special→Route` toasts counts instead of opening the map (`main.lua:988`) |
| Tutorial skip/revisit | **missing** | `Presentation:skip/revisit` (`runtime_presentation.lua:244-245`) have no caller; 8 toasts, no opt-out |
| Nav consistency | **partial** | v2 reward overlay commits on an already-held A (`main.lua:965`→`508-518`); reconnect reads as release+press (`:858`); no horizontal focus wrap (`menus.lua:274`) |

### M7 — Region genetics, effects, spectacle
| Requirement | Status | Evidence / remaining |
|---|---|---|
| Binding coverage | **partial** | `reports/B5-region-genetics.md`: **28 of 122 costume variants** bound (5 full, 23 smoke); partner/transformation/equipment unbound |
| Three-layer separation | **missing** | anatomy/anchors exist natively (`script_parts.inc:225-256`, `gw_script.c:3027-3062`) but runtime uses **only draw ordinals** (`bindings.lua:32-38`); anchor layer never called → halos/ribbons structurally impossible |
| Invisible fighters | **missing (P1)** | `visuals.lua:37` ignores `gd.dobj_tint` refusal (all 4 konst registers used → −1) and still counts the draw; Samus/Link exposed. **PENDING native confirmation** |
| Zero-draw regions | **missing** | Pikachu c0 (assault+traversal), Pichu c0, Peach/Zelda c0 charge and show in HUD with no body effect |
| Visual states | **partial** | 3 of 6 (dormant/charging/ready); activation/reaction/recovery collapse to one burst |
| Techniques | **partial** | flat persistent accent + release burst work; afterimages, tracers, trails, halos, orbitals, material patterns **all missing**. No overdraw/emitter/history budgets, no quality levels |
| Breed/Mutate/Lock/Compare for visuals | **missing** | 2 founders, 1 blend, 0 genetics |

### M8 — World composition, audio, production feel
| Requirement | Status | Evidence / remaining |
|---|---|---|
| Audio | **missing (blocked)** | `reports/B6-world-audio.md`: 17 declared events, **0 assets, 0 API**; the 126-function `gd.*` surface has **no** sound/music/voice call. `audio_catalogue.lua` never referenced by `main.lua` |
| Gameplay camera | **missing** | zero `gd.camera_*` calls; authored `camera` envelope (`room_recipes.lua:73`) is dead data. Parked CPU at x=58 sits inside both blast zone and FD camera interest |
| Stage bounds | **missing** | `gd.stage_bounds` exists (`gw_script.c:5655`) but never called |
| Transition masking | **missing** | unmasked, single-tick (up to 28 spawns in one frame), no fade; failed art build only `gd.log`ed → a zero-art room still plays |
| Themes/depth/lighting/hazards | **partial** | one-texel atlas recolour, no lighting/depth/hazard |
| Ending/summaries | **missing** | dead code; export automatic; `run_history.lua` unbundled |
| Pacing | **missing** | unmeasured; played route 6–9 rooms vs 12–18 target |

### M9 — Both-platform acceptance
| Requirement | Status | Evidence / remaining |
|---|---|---|
| Linux build | **integration-tested** | this lane; `build_linux.sh` |
| Windows build | **PENDING** | machine-bound, zero CI; `README.md:196-209` explains why |
| Qt launcher | **integration-tested** | building, 9/9 ctest, 4 deployed prefixes — **preserve, do not replace** |
| CI | **partial** | `launcher-qt.yml` covers the launcher only; game `linux-port.yml` is a self-hosted disc runner, **gated off**; nothing gates a Windows game build |
| Disc leak policy | **partial** | tracked tree clean; `.gitignore` misses `.rvz/.ciso/.wia/.wbfs/.gcz/.nkit/.elf` that `check_release.ps1:36-38` forbids; `package_linux.py` has no equivalent guard |
| Wayland | **human-reviewed** | genuine pass (weston, `DISPLAY` unset, 4/4 PNGs) |
| X11/XWayland | **missing** | **no evidence at all**; the only `x11` trace is inside the cancelled benchmark |
| Input hardware | **PENDING-HUMAN** | SDL/GC adapter/hotplug/rumble unverified; user's 8BitDo profile must not be claimed by virtual pads |
| Soak / perf | **missing** | no harness; reference hardware not agreed. Uncapped benchmark correctly dormant — **do not restart** |

### M10 — Full acceptance
**Not started.** Requires M1–M9. Human/hardware evidence outstanding: Jigglypuff return, Bowser return, merges, drops, full roster, X11, physical input, listening review, Windows build, skilled-Melee review.

## 4. Review queue

| ID | Severity | Item | Owner |
|---|---|---|---|
| R1 | P1 | `ftColl_80076640` absorbed→`false`; `main.lua:768` refunds on armor chip | coordinator (needs native edit + build) |
| R2 | **OPEN** (notice subfix only) | Lost export is now reported truthfully. **Remaining:** explicit choose/replace/discard, or durable pending export reachable via finished-run UI and after relaunch, exactly-once, original-run ownership, failure-safe. Player may decline deliberately with clear consequences. Full capacity must never auto-elect no-export. Regression must cover: real product flow → relaunch → resolve capacity → claim the SAME gene once → repeated claim/refused save neither duplicates nor deletes. Root review: `ROOT-REVIEW-R2-2026-10-01.md` |
| R3 | P1 | 5 complete, tested modules unreachable (not in `prepare.py`) | coordinator (`prepare.py` is single-writer) |
| R4 | P1 | Invisible fighters via ignored `dobj_tint` refusal (`visuals.lua:37`) | coordinator + native confirm |
| R5 | P1 | Reward screen has no exit (`menus.lua:264` vs legend `:520`) | coordinator (`menus.lua`) |
| R6 | **CLOSED** | 17 untracked includes + 33-file native patch landed; clean clone builds, bridge fixpoint stable, ABI clean, 214/214, seam test green |
| R7 | P2 | v1 restore ignores `save()` return (`main.lua:1021`) | coordinator |
| R8 | P2 | All 29 recipes uncertified → v2 route unreachable in normal play | root acceptance, human-watched |
| R9 | P2 | Asset generators untracked; tooling undeclared | coordinator |
| R10 | P2 | X11/XWayland unevidenced; `.gitignore` leak gaps | coordinator |

## 5. Rules held
- One writer per protected file (`main.lua`, `core.lua`, `prepare.py`, native, bridge).
- No lane claims human/hardware evidence. `PENDING-HUMAN` is never converted to pass.
- No disc-derived data committed; `build/GALE01/include` stays gitignored and untracked.
- No release, tag or publish. The cancelled uncapped benchmark is not restarted.
- Frozen lanes preserved and unmodified; reviewed, not edited in place.