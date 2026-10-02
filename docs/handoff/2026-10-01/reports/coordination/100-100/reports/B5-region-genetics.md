# B5 — Region genetics, character-part bindings and effects audit (read-only)

Lane: B5. Author: read-only audit agent. Date: 2026-09-30.
Scope (all read):

- Runtime `melee/worktrees/linux/pc/scripts/examples/roguelite/`: `visuals.lua`, `bindings.lua`,
  `roster.lua`, `core.lua`, `gene_catalogue.lua`, `gene_behaviors.lua`, `gene_actions.lua`,
  `equipment.lua`, `feedback.lua`, `runtime_presentation.lua`, `menus.lua`, `main.lua`,
  `encounter_catalogue.lua`, `enemy_genes.lua`.
- Native `melee/worktrees/linux/pc/`: `platform/gw_script.c`, `gameworld/script_parts.inc`,
  `gameworld/script_parts.h`.
- Tools: `tools/roguelite/build_bindings.py`, `tools/roguelite/prepare.py`,
  `tools/roguelite/fx_assets.py`, `tools/model_parts/analyze.py`, `tools/effects_lab/*`,
  `pc/scripts/examples/effects_lab/main.lua`, `menu/pipeline/roguelite_art.py`,
  `menu/pipeline/effects_assets.py`, `menu/pipeline/roguelite_expansion.py`.
- Measurements: `_build/agents/linux/scripts-data/character_parts_lab_main/*-analysis.json` (28).
- Specs: `docs/EFFECTS-LAB-PLAN.md`, `docs/ASTRA-ART-QUEUE.md`, `docs/ASTRA-ART-DELIVERY.md`,
  `docs/GENE-ACTION-CONTRACT.md`, `docs/ROGUELITE-COMPLETION-PLAN.md` (Gate 9 §14, lines 306–347;
  Gate 5 §10, lines 242–256; §2 traps; §3 targets), `docs/ROGUELITE-ACCEPTANCE.md`.

**No build, no game launch, no connection to console 51701.** Nothing was modified, staged or
committed except this report. Frozen lanes under `_build/deepseek-worktrees/`,
`_build/sol-worktrees/`, `_build/model-tests/` were not touched. **No art was generated and no
pipeline script was executed** — the menu pipeline files were read as text only.

What was actually executed (headless, pure, no engine):

```
python3  # read-only re-implementation of tools/roguelite/build_bindings.py:41-74
         # run over the 28 stored *-analysis.json reports; output compared to bindings.lua
         → "repro matches bindings.lua: True, total bound 441"
python3 -c  # Lua-table parse of bindings.lua:3 catalogue (no execution) → 28 entries
git status --porcelain   # read-only provenance check
```

No build system was invoked, no `.gfx.json` was written, no package was installed.

---

## 1. Summary

**Verdict: the region system is real, measured and honest about its own limits; almost everything
above it — states beyond three, attachment visuals, motion, materials, the effects-lab founder
catalogue and the effects genetics — does not exist. What ships is one texture-preserving flat
tint per body region on 26 stock fighters, plus three point-emitted burst packages.**

Seven headline findings:

1. **The three layers are genuinely separated in the native code, then collapsed to two at
   runtime.** Anatomy regions come from the game's own `FighterPartsTable.part_to_joint` skeleton
   table (`script_parts.inc:225-256`, `:458`), not from mesh size. Draw/material surfaces are
   `HSD_DObj` indices. Skeleton anchors are joint indices and exist as `ScriptGame_PartsJoint`
   (`script_parts.inc:936`) plus `gd.fx_attach`. **The runtime uses only the middle layer**: the
   entire roguelite visual path is `Bindings.resolve` → raw draw ordinals → `gd.dobj_tint`
   (`bindings.lua:32-38`, `visuals.lua:37`). The anchor layer is never used by the runtime, so
   halos/weapon ribbons are structurally impossible today rather than merely unbuilt.
2. **Mechanism is a hybrid, and the fingerprint half is weaker than it looks.** Whole-character
   identity is `kind + costume + geometry_signature` (`bindings.lua:24`). The stored
   `asset_sha256` per binding is **dead data at runtime** — never read by `resolve` or `coverage`.
   Per-draw selection *is* raw ordinal lookup, but each ordinal is re-validated live against a
   stored `path`/`joint` pair and filtered for source/status/translucency
   (`bindings.lua:32-38`). So: fingerprint for the character, guarded ordinals for the draws.
3. **Coverage: 28 bindings for 122 stock costume variants (23%).** All 26 fighter kinds are
   present at costume 0; only Pikachu c1 and Jigglypuff c1 have a second costume. **5 of 28 have
   a region with zero draws** (Pikachu c0: no assault, no traversal; Pichu c0: no assault; Peach
   c0, Zelda c0, Pikachu c1: no traversal). Partner (Popo/Nana), transformation (Zelda→Sheik,
  Sheik→Zelda) and all equipment are explicitly `partner_bound=false` /
   `equipment_bound=false` (`bindings.lua:30`, hard-coded in the generator at
   `build_bindings.py:100`).
4. **One real "invisible gene" class, provable from source: tint refusal is ignored.**
   `part_tint_register` returns `-1` when a material already uses all four konst registers
   (`script_parts.inc:176-192`); `ScriptGame_PartsControl` then returns `0`
   (`script_parts.inc:916`) and `gd.dobj_tint` pushes `false` (`gw_script.c:2958-2969`) —
   but `visuals.lua:37` discards the return value and still records the draw as applied. The
   in-game diagnostic string (`bindings.lua:40-42`) never mentions a refusal. Samus (46 bound
   draws, armour materials) and Link (29) are the exposed cases. PENDING for a live check.
5. **States: 3 of 6 exist.** `visuals.lua:18` computes dormant(1)/charging(2)/ready(3) only.
   Activation, reaction and recovery have **no body presentation**; they get one world-space
   burst package. Only 2 of 6 gene families have a colour at all (`visuals.lua:5`), and
   `gene_behaviors.lua:213-216` hard-rejects any unknown placement field, so **a region or
   visual field cannot be added to a placement record without editing the validator** — the
   genetics layer has no visual dimension in its schema at all.
6. **Advertised technique status: 1 working (flat persistent accent), 1 partial (release burst),
   6 missing.** No afterimages, tracers, ribbons, trails, halos, orbitals, silhouette
   attachments, contact/world traces or advanced material patterns exist anywhere in the runtime
   or the native path (`gd.fx_play`/`fx_end` are the only visual-effect calls in the whole
   roguelite: `main.lua:346-348`, `:770-772`). `gd.history` is the netplay rewind system, not
   pose history.
7. **The native foundation is uncommitted.** `pc/gameworld/script_parts.inc`,
   `pc/gameworld/script_parts.h`, `pc/scripts/examples/effects_lab/main.lua` and
   `pc/scripts/examples/character_parts_lab/main.lua` are all **untracked** in the game checkout,
   and `pc/gameworld/script_game.c` carries +383 uncommitted lines that include them. Every
   region, `geometry_signature`, `dobj_tint` and `dobj_solid` capability audited here lives in
   those untracked files. 22 untracked paths in the worktree; `menu/pipeline/roguelite_art.py`,
   `roguelite_expansion.py` and `effects_assets.py` are untracked in the workspace repo.

---

## 2. Q1 — Anatomy/equipment semantics vs draw/material selectors vs skeleton attachments

The separation exists, and it is not cosmetic. Evidence per layer:

| Layer | Native home | What it actually is | Evidence |
|---|---|---|---|
| Anatomy / equipment semantics | `part_joint_region()` + 12-region per-vertex weights | Derived from the game's authored `FighterPartsTable.part_to_joint`, walking each draw's joint parent chain to the first mapped `FtPart_*` node. Not size-based, not guessed. Item-sourced draws are hard-labelled region 11 (`equipment`). | `script_parts.inc:225-256`, `:458`, `:484-485`, `:602`; region names in `gw_script.c:2972-2974` |
| Draw / material surface | `HSD_DObj` index (`d` = draw ordinal) | One draw = one recolourable surface. `recolor_capability = "independent_draw_override"`. Tinting **appends one Tev stage** (K-colour RGB modulation) leaving texture, shading and the alpha/cutout test untouched; the solid mode is a separate constant-fill path. | `gw_script.c:2997-3021`; `script_parts.inc:176-215` (`ScriptParts_Tint`) vs `:107-171` (`ScriptParts_Draw`, constant fill) |
| Skeleton anchor | `ScriptGame_PartsJoint(slot, joint)` + `gd.fx_attach(slot, joint,…)` / `gd.fx_play(…, joint, …)` | A transform, not a surface. Distinct address space from draw indices. | `script_parts.inc:936-943`; `gw_script.c:3027-3043`, `:3045-3062` |

**Where it is conflated: the generator and the runtime.**

- `tools/roguelite/build_bindings.py:58-63` collapses 12 anatomy regions into **3 roles**
  (`assault` = hands+arms, `guard` = torso, `traversal` = feet+legs) by area-weighted argmax.
  `head` (>0.05) and `equipment` are dropped; `equipment_candidate` draws survive only when their
  argmax role is already `assault` (`:52-57`, `:67-69`).
- `bindings.lua:32-38` then emits **raw draw ordinals**, re-validated per frame against a stored
  `path`/`joint`. The anchor layer never reaches the runtime: `bindings.lua`'s entire output
  vocabulary is `{assault={ids}, guard={ids}, traversal={ids}}` (`:30`).
- `visuals.lua:37` applies the role straight to `gd.dobj_tint`. Nothing in the shipped path ever
  calls `gd.fx_attach`, `gd.joints` or `ScriptGame_PartsJoint`.

Consequences that directly contradict the plan's own examples:

- **"Marth blade versus hilt" is not separated.** Marth's weapon draws resolve to
  `right_hand` region (9 such draws of 85 parts) and land in `assault` alongside the fist and
  forearm. There is no blade/hilt/scabbard distinction in the schema — only `guard`=torso.
- **"Link shield separately from tunic and scabbard" is not separated.** Link has 15 `assault`,
  5 `guard`, 9 `traversal` draws; shield/tunic/scabbard are not individually addressable.
- **"Focus / head accessory" role does not exist** in the runtime vocabulary
  (`bindings.lua:5`). The only head draws bound anywhere are Pikachu c1 indices 22/23/24, an
  explicit hand-reviewed exception keyed on the exact signature (`build_bindings.py:29`,
  `:52-54`) — and they are recorded as `role=assault`, not a focus role.
- **Equipment semantics are correctly refused, not faked.** `equipment.lua:34`
  (`native_held_items_supported = false`) and `:97-99` reject native held items; `bindings.lua:30`
  sets `equipment_bound=false`. This is honest, but it means the equipment layer has *no*
  visual surface at all.

**Answer: separated natively (3 distinct address spaces, 3 distinct natives), collapsed to 2 by
the generator, reduced to 1 by the runtime. The anchor layer is dead code for this gamemode.**

---

## 3. Q2 — What is actually bound, and by what mechanism

### 3.1 Mechanism

| Step | Mechanism | Fingerprint or ordinal? | Citation |
|---|---|---|---|
| Character identity | `player.kind` + `player.costume` + `parts.geometry_signature` | Fingerprint (16 hex chars, FNV-style hash of part geometry, `gw_script.c:2988-2990`) | `bindings.lua:24` |
| Asset hash | `asset_sha256` stored per binding | **Unused at runtime** — build-time provenance only | `bindings.lua:3`; `build_bindings.py:98` |
| Draw selection | `entry.slots[slot]` = list of draw indices | **Raw ordinals**, each re-checked live: `p.source==0 and p.status==0 and p.path==expected.path and p.joint==expected.joint`, plus XLU/NO_ZUPDATE render-flag rejection | `bindings.lua:32-38`; render bits 30/29 at `:35` |
| Change detection | `B.topology()` string over `(index, source, item_kind, item_ordinal, path, joint, status)` for every part | Recomputed per port; a change forces re-resolve. Item ordinals are included in the key but transient items are never tinted. | `bindings.lua:47-52`, `visuals.lua:25,31` |
| Persistence | **Nothing is persisted.** No item IDs, no draw ordinals, no native handles. | Correct per `docs/EFFECTS-LAB-PLAN.md:332-338`. | `bindings.lua:45-46` |

So: character-level **fingerprint**, draw-level **guarded ordinals**. Raw ordinals are never
copied between characters or costumes — each binding carries its own ordinals plus its own
`path`/`joint` witnesses, and a mismatch drops the draw rather than tinting the wrong surface.

### 3.2 Coverage table (all 28 measured bindings; reproduced from the stored reports)

Reproduced independently from `_build/agents/linux/scripts-data/character_parts_lab_main/*-analysis.json`
by re-running the selector rules of `build_bindings.py:41-74`; the result is byte-identical to
`bindings.lua`. `A/G/T` = bound draw counts for assault/guard/traversal. `vf=1` = bound draws
visible in **every** measured pose. `altgeo` = number of disjoint-state-mask geometry groups in
the report (action-dependent draws) and how many bound draws sit inside one.

| binding | coverage | pose samples | parts | A | G | T | unbound draws | vf=1 | altgeo groups / bound inside |
|---|---|---|---|---|---|---|---|---|---|
| falco/c0 | **full36** | 36 | 56 | 2 | 5 | 4 | 45 | 6 | 0 / 0 |
| link/c0 | **full36** | 36 | 95 | 15 | 5 | 9 | 66 | 11 | 59 / 5 |
| marth/c0 | **full36** | 36 | 85 | 8 | 8 | 6 | 63 | 4 | 24 / 3 |
| pikachu/c1 | **full36** | 36 | 32 | 3 | 3 | **0** | 26 | 3 | 0 / 0 |
| jigglypuff/c1 | **full36** | 36 | 14 | 2 | 4 | 2 | 6 | 2 | 0 / 0 |
| bowser/c0 | smoke4 | 4 | 115 | 7 | 5 | 4 | 99 | 11 | 2800 / 16 |
| captain/c0 | smoke4 | 4 | 79 | 7 | 14 | 5 | 53 | 15 | 0 / 0 |
| donkey/c0 | smoke4 | 4 | 37 | 3 | 2 | 3 | 29 | 8 | 0 / 0 |
| drmario/c0 | smoke4 | 4 | 58 | 4 | 5 | 3 | 46 | 6 | 0 / 0 |
| fox/c0 | smoke4 | 4 | 77 | 7 | 4 | 6 | 60 | 12 | 0 / 0 |
| gamewatch/c0 | smoke4 | 4 | 116 | 6 | 1 | 4 | 105 | 11 | 624 / 0 |
| ganondorf/c0 | smoke4 | 4 | 90 | 5 | 10 | 8 | 67 | 10 | 0 / 0 |
| jigglypuff/c0 | smoke4 | 4 | 14 | 2 | 4 | 2 | 6 | 5 | 0 / 0 |
| kirby/c0 | smoke4 | 4 | 42 | 2 | 2 | 2 | 36 | 5 | 488 / 2 |
| luigi/c0 | smoke4 | 4 | 53 | 3 | 4 | 5 | 41 | 10 | 0 / 0 |
| mario/c0 | smoke4 | 4 | 59 | 4 | 5 | 6 | 44 | 13 | 0 / 0 |
| mewtwo/c0 | smoke4 | 4 | 42 | 4 | 3 | 8 | 27 | 14 | 0 / 0 |
| ness/c0 | smoke4 | 4 | 70 | 6 | 8 | 8 | 48 | 14 | 0 / 0 |
| peach/c0 | smoke4 | 4 | 85 | 7 | 6 | **0** | 72 | 8 | 169 / 0 |
| pichu/c0 | smoke4 | 4 | 37 | **0** | 3 | 4 | 30 | 5 | 0 / 0 |
| pikachu/c0 | smoke4 | 4 | 26 | **0** | 3 | **0** | 23 | 3 | 0 / 0 |
| popo/c0 (primary climber only) | smoke4 | 4 | 43 | 7 | 2 | 4 | 30 | 10 | 0 / 0 |
| roy/c0 | smoke4 | 4 | 95 | 6 | 8 | 7 | 74 | 16 | 24 / 2 |
| samus/c0 | smoke4 | 4 | 95 | 14 | 17 | 15 | 49 | 33 | 368 / 46 |
| sheik/c0 | smoke4 | 4 | 63 | 9 | 8 | 10 | 36 | 20 | 0 / 0 |
| yoshi/c0 | smoke4 | 4 | 40 | 2 | 7 | 5 | 26 | 14 | 76 / 14 |
| younglink/c0 | smoke4 | 4 | 83 | 8 | 6 | 6 | 63 | 17 | 60 / 5 |
| zelda/c0 | smoke4 | 4 | 55 | 2 | 8 | **0** | 45 | 9 | 0 / 0 |
| **TOTAL** | 5 full36 / 23 smoke4 | — | 1756 | 175 | 176 | 155 | 1315 | 295/441 | 93 of 441 bound draws are action-dependent |

Additional measured facts (not claims about what a player sees — those need a build):

- All 441 bound draws are visible in ≥25% of the measured poses; 295/441 in every pose. So the
  bindings are not pose-blind. `max_coverage` in the reports is a **relative screen area**, not a
  visibility fraction (`tools/model_parts/analyze.py:194`), and most bound draws are small
  (per-slot summed area is 0%–120% of the capture box depending on fighter). Whether a small
  flat tint is legible at gameplay distance is a human-review question → **PENDING**.
- 93/441 bound draws live in disjoint-state-mask groups (`analyze.py:142-148`) — Samus 46/46,
  Bowser 16/16, Yoshi 14/14. These swap with action state. `bindings.lua` never reads
  `alternate_geometry`, so action-dependent regions are handled only implicitly, by the live
  `p and d` presence test (`bindings.lua:36`); when such a draw is absent the gene simply
  disappears for that frame, silently.
- `shared_materials` is empty in all 28 reports, so no cross-draw material aliasing was found in
  the measurements. **PENDING**: `ScriptParts_Tint` mutates the live MObj Tev chain, so a
  genuinely shared material between two tinted and untinted draws would tint both; nothing
  measures that at runtime.

### 3.3 Unbound cases (explicit, not accidental)

| Case | State | Evidence |
|---|---|---|
| Costumes 1..N-1 of the other 24 fighters | No binding → `resolve` refuses, no tint | 28 of 122 variants covered; `bindings.lua:26` |
| Popo/Nana partner (Nana) | `partner_bound=false`, diagnostic says "partner unbound" | `bindings.lua:30,42,128`; `roster.lua:68` |
| Zelda→Sheik, Sheik→Zelda transformation | No separate binding; roster warns only | `roster.lua:68-69` |
| Equipment (weapon/offhand/core/plating/charm/boots/focus/sigil) | `equipment_bound=false`; `native_held_items_supported=false` | `bindings.lua:30`; `equipment.lua:30-34` |
| Held/native articles, projectiles, temporary props | Explicitly out of measurement scope | `marth-analysis.json` `limitations` field |
| Focus role (head/tiara/headgear) | Role does not exist except one reviewed Pikachu c1 exception mapped to `assault` | `bindings.lua:5`; `build_bindings.py:29,52-54` |

---

## 4. Q3 — Invisible fighters and leaked material overrides

### 4.1 Leaked overrides: the machinery is correct

Cleanup is real, not hopeful:

- `visuals.lua:32-33` clears every previously applied draw before re-applying, gated on the draw
  still being live in the current `gd.dobjs` list.
- `PART_CTL_CLEAR` memsets the whole table entry (`script_parts.inc:907-911`), so it does clear a
  **tint**, not only a solid — `visuals.lua:33` calling `gd.dobj_solid_off` is correct despite the
  misleading name.
- `ScriptParts_Forget(dobj)` drops colour entries for a destroyed DObj
  (`script_parts.inc:73-86`), so respawn/model swap cannot leave a dangling pointer match.
- `gd.parts_clear()` is owner-scoped and runs on cleanup (`gw_script.c:3024-3026`,
  `script_parts.inc:51-68`; called at `main.lua:370`).
- Ownership is enforced: another script's entry returns `-3` (`script_parts.inc:904-906`).

Residual leak risks found:

| # | Risk | Where | Severity |
|---|---|---|---|
| L1 | **Tint refusal silently ignored.** `gd.dobj_tint` returns `false`; `visuals.lua:37` ignores it and records the id as applied. Cause: all four konst registers consumed (`part_tint_register` → `-1`, `script_parts.inc:186-192`) or committed Tev stage ≥16 (`script_parts.inc:207`). Result: gene silently invisible, diagnostic still says "Measured N-pair binding / M draws". | `visuals.lua:37`; `script_parts.inc:176-215,916`; `gw_script.c:2958-2969` | **P1** (silent loss of the core legibility promise). Samus/Link most exposed. PENDING live confirmation. |
| L2 | **Action-dependent draws vanish per frame with no diagnostic** (93/441 bound draws). | `bindings.lua:36`; `analyze.py:142-148` | P2 |
| L3 | **Empty regions are never reported in play.** `resolve`'s diagnostic string omits the "; no isolated X draws" note that `coverage()` produces, and `coverage()` is only used on the fighter-select screen. | `bindings.lua:40-42` vs `:12-13`; `roster.lua:70`; `main.lua:960,1000,1168,1190` | **P1** — Pikachu c0 assault/traversal genes are mechanically live and HUD-live but body-silent, and nothing says so. |
| L4 | **`ScriptParts_Tint` mutates the live MObj Tev chain.** A material shared between a tinted and an untinted draw would tint both. All 28 reports have `shared_materials: []`, so this is unmeasured rather than disproven. | `script_parts.inc:196-215`; report field `shared_materials` | P2, PENDING runtime measurement |
| L5 | `lab_part_colors_hi` is a high-water mark only trimmed on reset; stale entries above a reused index would be skipped by the draw-time scan. Bounded by `PART_COLORS 1024`. | `script_parts.inc:12,28,59-62,128-134` | P3 |

**No invisible-fighter mechanism was found** (e.g. no whole-model hide, no alpha-zeroing override):
the tint path never touches alpha (`script_parts.inc:196-215`), and the solid path is only
reachable if a script calls `gd.dobj_solid`, which the roguelite never does. The one
model-wide hide in the runtime is `gd.stage_isolate`, unrelated to part visuals.

---

## 5. Q4 — Family / placement / stats vs states and events

### 5.1 State mapping

| Plan state (`ROGUELITE-COMPLETION-PLAN.md:314`) | Body expression | HUD expression | Effect |
|---|---|---|---|
| dormant | `visuals.lua:18` phase 1 → colour ramp index 1 (dim) | `CHARGING`/`READY`/`COOLDOWN` text (`feedback.lua:160`) | — |
| charging | phase 2 → index 2 | charge ratio bar `min(1, charge/cost)` (`feedback.lua:92`) | — |
| ready | phase 3 → index 3 (bright) | `READY` + pulse (`feedback.lua:107,159,258`) | — |
| activation | **none** | — | one world burst (`main.lua:770`) |
| reaction | **none** | — | `ThermalShock` only (`main.lua:770`) |
| recovery | **none** (cooldown exists mechanically: `core.lua:265` `ready_at`) | `COOLDOWN` + remaining frames (`feedback.lua:160`) | — |

Also missing versus `:314`:

- **No discrete lit segments driven by `capacity`.** Only a continuous charge bar.
- **No potency → core density, duration → aftermath length, true range.** `Core.ability` exposes
  potency/reach/cooldown (`core.lua:236-239`) and the HUD shows them, but no visual parameter
  consumes them.
- **Shape/motion is never a cue.** Colour is the *only* region cue — the exact thing the plan
  forbids relying on alone.

### 5.2 Family / placement / stats

| Dimension | Implemented | Gap |
|---|---|---|
| Families | 6 defined (`gene_catalogue.lua:10-17`, `gene_behaviors.lua:24-31`) | **2 have any visual** (`visuals.lua:5` cinder/rime only). kinetic/aegis/flux/sigil would tint nothing — and they cannot be acquired anyway (`core.lua:5-15` defines only cinder/rime). |
| Placements | 3 slots × 12 genes, each with 2–3 authored variants (`gene_behaviors.lua:80-159`) | **No region field.** `check_placement`'s field whitelist (`:213-216`) asserts on any unknown key, so `region`/`visual`/`states` cannot be added without editing the validator. Placement changes the *mechanic* (eruption/step/counter) but never the *visual grammar* — the visual is chosen by slot alone. |
| Placement preview | Schematic rectangle mannequin coloured by slot (`menus.lua:355-367`) | Schematic, not the real fighter's draws; does not show which region/draw will change. Required to be labelled schematic (`ROGUELITE-COMPLETION-PLAN.md:296`) — it is not labelled as such in code. |
| Unsupported pairings | Slot validation exists (`equipment.lua:105-107`) | **No visual ineligibility.** A placement with zero bound draws (e.g. Pikachu c0 traversal) is offered and accepted, not refused with a visible reason. |
| Events → visuals | `Core.ability().ready/charge` polled 2× per frame + every 30 frames (`visuals.lua:18,22`) | Polling, not event-driven; activation/reaction/recovery carry no body state (see 5.1). |
| Stat → visual | HUD only (`feedback.lua:114-134` shows committed before/after deltas) | Nothing stat-driven in 3D. |
| Exclusive/dominance pairs | `gene_catalogue.lua:53` declares `fire/frost` and `kinetic/aegis` exclusive | **Never read by anything.** Grep: no consumer. No authored priority or per-region dominance resolver exists. |
| Per-region dominance | Implicit only: `Core.equip` allows one gene per slot (`core.lua:192-197`) and the three role sets are disjoint by argmax construction | Works by construction, not by policy. Nothing prevents a future accent layer from double-tinting a region. |

---

## 6. Q5 — Advertised visual techniques: what actually works

"Working" = reachable from the shipped bundle (`_build/agents/linux/mods/roguelite/`).
"Stub" = code/data exists but is not reachable from gameplay.

| Technique | Status | Evidence |
|---|---|---|
| **Persistent region accents** | **Working (flat, single-colour, static)** | `visuals.lua:37` → `gd.dobj_tint` → `PART_CTL_TINT` → `ScriptParts_Tint` appends one Tev K-colour stage; texture, shading, alpha and cutouts preserved (`script_parts.inc:176-215`). Applied per region, held while the phase is unchanged. This is the "production tint that preserves base shading and alpha" the plan called a real next task (`EFFECTS-LAB-PLAN.md:425-427`) — it now exists, but as a **constant additive colour**, not an authored treatment. |
| **Advanced material patterns** | **Missing** | No mask, no animated pattern, no second material layer, no per-region shader. `part_tint_register` only picks one of four konst registers (`script_parts.inc:186-192`). 16 authored "material field" masks exist as **art only** (`docs/ASTRA-ART-DELIVERY.md:16-17`). |
| **Attachment halos** | **Missing** | Anchor layer unused: no `gd.fx_attach`, no `gd.joints`, no `gd.fx_play(..., joint≠0, ...)` anywhere in the runtime. `AegisHalo` is a recipe *name* in `gene_catalogue.lua:32`. Segmented halo art exists as reference only (`ASTRA-ART-DELIVERY.md:17`). |
| **Motion / weapon tracers** | **Missing** | No attachment-history sampling, no ribbon construction, no blade endpoint tracking. `gd.history` is netplay rewind (`gw_script.c:5640-5643`), unusable for pose history. |
| **Trails** | **Missing** | No follow/continuous emission bound to a joint or a path. `recipes.py` emits only `'follow':'none'` except three SRT-attached point layers (`recipes.py:32,57`). `TracerLine`/`WindWake` are names only (`gene_catalogue.lua:30-31`). |
| **Afterimages** | **Missing** | No pose/draw snapshot buffer, no second render pass. Explicitly labelled "reference afterimages" in art (`ASTRA-ART-DELIVERY.md:17`). |
| **Point burst on release / reaction** | **Working** | `main.lua:346-348` (enemy gene release) and `:770-772` (player activation, `ThermalShock` on reaction). 3 packages installed: `RogueCinderRelease`, `RogueRimeRelease`, `ThermalShock`. Bounded by an 8-handle ring buffer (`:348`, `:772`) and `fx_end` on cleanup (`:369`). |
| **Orbitals / continuous fields** | **Missing** | `orbital_shard_storm` exists only as an encounter-catalogue id (`encounter_catalogue.lua:108`). |
| **Silhouette attachments** | **Missing** | No attached-geometry API used. |
| **Contact / world traces** | **Missing** | No decal, footprint or stage-surface path. |
| **Combat/UI connections** | **Stub** | HUD charge bar/READY text exist (`feedback.lua:92,254-258`); nothing travels from body region to HUD icon. |
| **Effects-lab showcase / tour** | **Stub, standalone** | `pc/scripts/examples/effects_lab/main.lua` (175 lines) has founder A/B = 2, one blend slider, 7 narrow controls, layer isolation, play/replay/loop/stop/pause/step, Save/Load, Thermal Shock (`effects_lab/main.lua:45,75-86,125,158-171`). It is a **separate mod**, untracked, and not reachable from the roguelite. |

Budgets actually present in the runtime: 8 concurrent FX handles (`main.lua:348`), 1024 part-colour
entries and 512 parts natively (`script_parts.inc:11-12`), 3 texture-registry slots + 2 stale ids
(`visuals.lua:5`). There is **no overdraw budget, no emitter budget, no per-region budget and no
distance/quality reduction anywhere** in the roguelite path.

---

## 7. Q6 — Founders, blends, traits, and deterministic genetics

### 7.1 Effects-lab authoring (`tools/effects_lab/`, `pc/scripts/examples/effects_lab/main.lua`)

| Item | Target | Actual | Evidence |
|---|---|---|---|
| Founder recipes | 5 (Solar Eruption, Glacial Shatter, Thunder Crown, Astral Vortex, Comet Crescent) | **2** (`SolarEruption`, `GlacialShatter`) | `recipes.py:44-65` (`founder(ice)`), `:74-92` (`recipes()` returns exactly 4 packages); `README.md:11,103` states the remaining three are proposals |
| Unordered pair blends | 10 | **1** (`ThermalBlend`, fire+ice, one authored crossfade package) | `recipes.py:12,79` |
| Semantic layer roles | 7 shared roles | 7 roles exist and align (`charge, core, flow, ring, fragments, aftermath, distortion`) | `recipes.py:11,48-54` |
| Trait controls | Palette / Energy / Turbulence / Cohesion / Rhythm / Persistence / Structure | 7 sliders exist and reach 7 emitter fields each, but documented as narrower than the plan's traits ("palette biases hot/cool lightness, rhythm adjusts density…", `EFFECTS-LAB-PLAN.md:35-37`) | `expression.py:3-20`; `effects_lab/main.lua:158-159` |
| Live parameter tween / instance handles | required | Present (12-frame tween, per-instance handles, pause/step, isolation) | `effects_lab/main.lua:45-60,97,125`; `README.md:27-32` |
| **Breed / Mutate / Lock / Save / Compare** (effects genetics) | required | **Entirely absent.** No genome, no parents, no ancestry, no mutation, no trait lock, no compare. `Save` writes `{schema=1,recipe=2,seed,a,b,blend,layer,values}` — settings + seed, explicitly "not the planned immutable genome format". | `effects_lab/main.lua:75-86`; `README.md:34-39,72-73` |
| Recipe/asset versioning | preserve resolved assets | `VERSION = 2`, SHA-256 verified at install, v1 favourites rejected — but **resolved assets are not stored**, so a future artwork change silently alters a saved favourite. This is the known limitation, not a new one. | `recipes.py:9,14-22,70`; `effects_lab/main.lua:83`; `README.md:36-39` |
| 5 founders + 10 blends as a Gate 9 blocker | required | Not done; the art pass delivered reference sheets for 5 founders and 10 blends at 5 weights, explicitly as art, not implementation | `ASTRA-ART-DELIVERY.md:18-19,62-64,74-79` |

### 7.2 Gene (mechanics) genetics — a different system, and it is real

| Operation | Status | Evidence |
|---|---|---|
| Breed (collection) | Implemented, transactional, costed, previewed in-menu | `core.lua:301-305` (`offspring` + `breed`), `inventory.lua:505-540` (preview/commit, clone-then-commit), `menus.lua:209-216,318-320` |
| Deterministic seeds | Yes — LCG `next_seed`, no wall clock | `core.lua:25` |
| Trait locks | Core supports all 5 stats; **UI exposes only `potency`** | `core.lua:297-299`; `menus.lua:223,315-317` (`stat='potency'`) |
| Mutate | Implicit only — `s%2==0` per-stat coin flip inside `offspring`; no mutation-strength control | `core.lua:290-295` |
| Save / serialise | Yes, strict field/cap validation, numeric keys 1–16, 256-byte strings (plan flags this as inadequate, `:71`) | `core.lua:373-390` |
| Compare / preview | Implemented for genes (side-by-side child stats + locks) | `menus.lua:209-216,421` |
| Fuse (run) | Implemented, consumes parents, refuses equipped parents, averages run upgrades, blocks export of enemy-owned genes | `core.lua:307-315`, `:316-331` |
| Export on success | One gene, run upgrades stripped | `core.lua:323-330` |
| Placement variants changing the ability | Implemented mechanically (12 genes × 2–3 authored variants) but **unoffered**: only cinder/rime | `gene_behaviors.lua:13,80-159`; `docs/GENE-ACTION-CONTRACT.md:36-39` |
| Gene visual ancestry | **Missing.** `Core.ability().recipe` is a string (`core.lua:240`) never mapped to a package. 12 recipes named in `gene_catalogue.lua`, **2 packages installed**. | `gene_catalogue.lua:26-37`; installed `fx/` = 6 dirs, of which the runtime names 3 |

Dead-code note carried over from B3 and re-confirmed here: `equipment.lua`, `gene_behaviors.lua`
and `gene_actions.lua` are **not in the bundle** (`tools/roguelite/prepare.py:34-39`) — the
gene genetics in 7.2 is reachable, but `gene_behaviors`/`gene_actions` (10 prototype genes,
placement transactions) and the entire equipment layer are not installed, so no equipment has any
gameplay or visual consequence.

---

## 8. Q7 — Lifecycle, dominance, budgets, quality levels, reduced flash/motion

| Concern | Status | Evidence |
|---|---|---|
| Attachment/emitter lifecycle | Present and bounded for the two things that exist: FX handle ring buffer of 8 with `fx_end` on cleanup; part overrides cleared before every re-apply and on `parts_clear`. | `main.lua:348,369,370-371`; `visuals.lua:33` |
| Restore on unequip / scene change / respawn | Stale overrides cleared before re-resolve; `ScriptParts_Forget` drops destroyed-DObj entries; `ScriptGame_PartsReset(owner)` is owner-scoped. | `visuals.lua:32-33`; `script_parts.inc:73-86,51-68` |
| No raw handles persisted | Correct — nothing persisted at all in this path. | `bindings.lua:45-46` |
| Per-region dominance | Only by construction (one gene per slot, disjoint role sets). No authored priority, no conflict resolver; `gene_catalogue.exclusive` has no consumer. | `core.lua:192-197`; `gene_catalogue.lua:53` |
| History budget | **Missing** (no pose history exists) | — |
| Attachment budget | **Missing** (no attachment system) | — |
| Emitter budget | Only the 8-handle ring buffer | `main.lua:348` |
| Overdraw budget | **Missing** — no budget, no measurement, no documentation | — |
| Quality levels (low/medium/high FX) | **Missing** — no quality tier anywhere in the roguelite | — |
| Reduced flash | **Missing** — no such setting or code path | — |
| Reduced motion | HUD-only, and it is not a real switch: `reduced` is read from the mod's own config text (`config:find('reduced_motion=true')`), and the comment says so explicitly — "The port exposes no reduced-motion switch". It suppresses the READY pulse and a toast slide only. It has **zero effect on any 3D visual**, because no animated 3D visual exists. | `main.lua:70`; `runtime_presentation.lua:285-291`; `feedback.lua:159,209-211,260` |
| Culled particles never cancel gameplay | Vacuously true today (no particles in the gene path) — but also **untested**, and the plan's acceptance question "are mechanics identical with particles culled" has no harness. | `ROGUELITE-COMPLETION-PLAN.md:254` |

---

## 9. Ranked gap list

Severity per `ROGUELITE-COMPLETION-PLAN.md:122` (P0 crash/data-loss, P1 softlock/broken controls/
unreachable objective/broken platform, P2 major readability/fairness/performance, P3 cosmetic).

| # | Sev | Gap | Evidence |
|---|---|---|---|
| **G1** | **P1** | **Ignored tint refusal ⇒ silently invisible gene with a healthy-looking diagnostic.** Check `gd.dobj_tint`'s boolean and count refusals into `Visuals.status()`; refuse the whole binding if a required region's draws cannot be tinted. | `visuals.lua:37`; `script_parts.inc:186-192,916`; `gw_script.c:2958-2969` |
| **G2** | **P1** | **Zero-draw regions are offered silently.** 5 of 28 bindings have an empty region (Pikachu c0 A+T, Pichu c0 A, Peach/Zelda c0 T, Pikachu c1 T). `Core.equip` accepts the placement and the HUD charges it. Fix: refuse the placement with a visible reason before selection, per `EFFECTS-LAB-PLAN.md:334-337`. | `bindings.lua:30,40-42`; `core.lua:185-197`; `equipment.lua:105-107` (the pattern to copy) |
| **G3** | **P1** | **The native region/tint foundation is uncommitted.** `script_parts.inc`, `script_parts.h`, `effects_lab/main.lua`, `character_parts_lab/main.lua` are untracked; `script_game.c` has +383 uncommitted lines including them. A clean checkout loses every capability in this report. | `git status --porcelain --untracked-files=all` (22 untracked paths) |
| **G4** | **P1** | **Empty in-play diagnostic for bindings.** `resolve`'s diagnostic omits the `coverage()` "no isolated draws" note; `rogue_bindings` logs only that. No HUD surface states which regions are bound. | `bindings.lua:40-42` vs `:12-13`; `main.lua:1273`; `roster.lua:70` |
| **G5** | **P2** | **Placement has no visual dimension.** `check_placement`'s whitelist forbids adding one; visual choice is slot-only, so two mechanically different placements look identical. | `gene_behaviors.lua:213-216`; `visuals.lua:30-37` |
| **G6** | **P2** | **Activation / reaction / recovery have no body state**, and colour is the only cue. No capacity segments, no potency→density, no true-range cue. | `visuals.lua:18`; `ROGUELITE-COMPLETION-PLAN.md:314` |
| **G7** | **P2** | **The entire "beyond bursts" vocabulary is missing** — halos, trails, tracers, afterimages, orbitals, silhouette attachments, contact traces. The anchor layer exists natively and is unused; this is renderer/plumbing work, not new art. | §6 table; `gw_script.c:3027-3062` (capability present, uncalled) |
| **G8** | **P2** | **Effects-lab scope: 2 founders, 1 blend, 0 of 3 remaining founders, no effects genetics at all.** No Breed/Mutate/Lock/Compare for visuals; saved favourites store no resolved assets. | `recipes.py:12,74-92`; `effects_lab/main.lua:75-86`; `README.md:11,72-73,103` |
| **G9** | **P2** | **No per-region dominance/priority policy, and `gene_catalogue.exclusive` has no consumer.** | `gene_catalogue.lua:53` |
| **G10** | **P2** | **Equipment has no visual binding and `equipment.lua` is not bundled**, so the equipment layer is neither visual nor live. | `bindings.lua:30`; `equipment.lua:34,69-87`; `prepare.py:34-39` |
| **G11** | **P2** | **Partner, transformation and second costumes unbound** — 94 of 122 stock costume variants, Popo's partner, Zelda/Sheik forms. Popo and Zelda/Sheik are warned about in the roster text only. | §3.3; `roster.lua:68-69` |
| **G12** | **P2** | **No quality levels, no reduced flash, no overdraw/emitter/history/attachment budgets.** `reduced_motion` is a config-text read that only affects the HUD. | `runtime_presentation.lua:285-291`; `main.lua:70` |
| **G13** | **P3** | **Action-dependent geometry (93/441 bound draws) is unmodelled**; a region's tint can vanish mid-action with no diagnostic. `alternate_geometry` is measured but unused by the generator. | `analyze.py:142-148`; `build_bindings.py:41-74` |
| **G14** | **P3** | **Shared-material tint aliasing unmeasured** (all reports `shared_materials: []`); tint mutates the live MObj Tev chain. | `script_parts.inc:196-215` |
| **G15** | **P3** | **`asset_sha256` is dead data at runtime** — provenance exists but is never verified against the loaded asset; a swapped model with a colliding signature would tint silently. | `bindings.lua:3,24` |
| **G16** | **P3** | **Gene visual ancestry unmapped**: `recipe` string never resolves to a package; 10 of 12 named recipes have no package. Lock is also exposed for one stat only. | `core.lua:240`; `gene_catalogue.lua:26-37`; `menus.lua:223` |
| **G17** | **P3** | Placement preview is a schematic rectangle figure, not labelled as schematic in code. | `menus.lua:355-367` |

---

## 10. Proposed order

1. **Land the native foundation first (G3).** Nothing else is worth building on untracked files.
   This is a provenance action, not a code change, and it is the cheapest item on the list.
2. **Make tint truthful (G1) + bind diagnostics honest (G4) + refuse empty regions (G2).** One
   small change set in `visuals.lua` and `bindings.lua` converts the current "silently invisible"
   class into an explicit, reported refusal. This is the difference between "genes are visible"
   and "genes are claimed to be visible". Do this before any new art.
3. **Give placement a visual dimension (G5).** Extend the `check_placement` whitelist with an
   authored `region`/`accent` field, then make `visuals.lua` resolve visual identity from the
   placement rather than the slot. This is the load-bearing change for everything downstream —
   it is what makes two placements of one gene look different, and it is a prerequisite for
   halos, because a halo needs an anchor, and an anchor needs a placement-level region.
4. **Add the missing states (G6)** using the now-placement-addressed regions: activation,
   reaction, recovery, plus capacity segments and a potency→intensity mapping inside a stated cap.
5. **Then the anchor layer (G7), one representative at a time**, in the plan's own order:
   attachment halo → movement trail → weapon ribbon. Each needs a bounded history buffer and an
   explicit budget. Do not attempt full-model afterimages or animated material patterns until
   these three have motion clips.
6. **Effects-lab scope (G8)** in parallel with 5 but only against the region vocabulary from 3:
   the third founder, then the remaining nine blends, then effects genetics. Record the resolved
   asset set in saved favourites before claiming reproducibility.
7. **Dominance and budgets (G9, G12)** as a single authored policy file consumed by `visuals.lua`:
   one dominant treatment per region, bounded accents, authored precedence, quality tiers wired
   to reduced-flash and reduced-motion — so accessibility lands with the vocabulary, not after it.
8. **Roster expansion (G10, G11)** last: partner, transformation, remaining costumes and
   equipment. Each is a measurement + review cycle, not an implementation problem, and the
   generator already refuses incomplete reports rather than guessing.

---

## 11. PENDING — requires a build or human review

Nothing below was executed or observed by me.

- **PENDING (build):** whether any bound draw is actually imperceptible at gameplay distance.
  Treated area is small for most fighters; only close-up evidence exists.
- **PENDING (build):** live confirmation of the tint-refusal path (G1) on Samus and Link, and how
  often it fires in normal play.
- **PENDING (build):** live confirmation that `ScriptParts_Tint` does not alias across shared
  materials, and that no override survives respawn, unequip, scene change or stock loss.
- **PENDING (build):** normal-speed motion clips at the gameplay camera for every technique
  claimed in §6 — none of these exist, so the acceptance bar is entirely unmet.
- **PENDING (build):** measured emitter/particle/overdraw cost of the two release packages during
  a real run, and behaviour with the 8-handle cap saturated.
- **PENDING (human):** readability of a flat single-colour region tint as a build-identity cue;
  accessibility with reduced flash/motion; whether any halo/trail would falsely imply protection
  or extra hitbox.
- **PENDING (human):** the Astra art packs' browser previews are not native evidence and do not
  certify any of this (`ASTRA-ART-DELIVERY.md:66-79`).

---

## 12. Evidence appendix

Read-only commands used (no build, no run, no console):

```
git -C melee/worktrees/linux status --porcelain --untracked-files=all | grep '^??'
  → pc/gameworld/script_parts.h, script_parts.inc, pc/scripts/examples/effects_lab/main.lua,
    pc/scripts/examples/character_parts_lab/main.lua, +18 more (22 total)
git -C gdm status --porcelain -- menu/pipeline
  → menu/pipeline/roguelite_art.py, roguelite_expansion.py, effects_assets.py untracked
grep -rn 'Equipment' roguelite/*.lua      → equipment.lua only (+1 prose line in gene_actions.lua)
python3 <selector replay>                  → "repro matches bindings.lua: True, total bound 441"
python3 <Lua-table parse of bindings.lua>  → 28 entries, all partner_bound=false
ls _build/agents/linux/mods/roguelite/fx/ → 6 packages; runtime references 3
```

Cross-references to sibling reports: **B3** independently reached the same "not bundled"
conclusion for `inventory.lua`/`equipment.lua`/`run_history.lua`; this report adds the
region/visual dimension (equipment has no binding, and the visual path itself *is* bundled).
**B4** owns the HUD/menu surfaces referenced here (`feedback.lua` READY pulse, `menus.lua`
schematic preview).