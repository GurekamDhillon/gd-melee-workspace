# Scene launch — booting straight into any screen, in any configuration

**Written 2026-09-19.** Code: `pc/platform/gw_runtime.c` (the `SCENE LAUNCH` block at the end),
`src/melee/gm/gmscenelaunch.h` (the game-side seeder), and the call sites listed in §7.
Tests: `scene_*` in the `--test` suite, 7 of them.

This replaces the three ad-hoc hooks (`MELEE_TRAINING`, `MELEE_TARGET_TEST`, `MELEE_STAGE`), which
still work and are now translated into the same config so there is one seeding path.

---

## 1. The bug this started as

Three scripted launches with `MELEE_TRAINING` and `MELEE_STAGE` set produced **no
`gw: MELEE_TRAINING=...` line at all**, on a game that came up and rendered fine.

The hook lived in `gmboot.c`'s `bootOnLeave` — the boot scene's **exit** handler. The boot mode
has exactly one state and its scene kind is `GS_MEMCARD`: the memory-card prompt. When the card
holds no Melee save the prompt asks *"There is no save data. Create one?"* and **waits for a
button forever**. `gm_801A4014` only calls `state->on_exit` after that scene's frame loop
returns, so `bootOnLeave` never ran, the scene hook was never called, and the absence of its log
line looked exactly like a missing hook.

It worked before because it was run from `_build/`, whose `card/` folder already had a save.
`run.sh` gives every sandbox a **fresh, empty** card folder, so every sandboxed launch hits the
prompt. The old logs show it plainly: `aurora::card: Failed to open file: SuperSmashBros…` at
retrace ~10, then 2600 frames of an unchanging 68-drawcall screen and zero audio voices.

**Fix.** A configured scene launch (or `MELEE_SKIP_MEMCARD=1`) takes the prompt's own
"disable saving and carry on" exit for *any* card status. That generalises m-ex's
`Skip Memcard Prompt` patch, which only covered the two no-card statuses (0xF, 0xD). Saving is
off for that run, which is correct — the run never answered the question. `skipmemcard=0` opts
back in.

**Lesson worth keeping:** a hook in a scene's *exit* handler is gated on that scene ending. On
this boot path the very first scene is a prompt, so "my hook never fired" and "the game is
waiting for a button" are the same symptom. That is why §6's scene trace exists.

---

## 2. THE INDEX SPACES — the definitive answer

There are **four** fighter index spaces and **two** stage ones. A bare number is right in one and
silently wrong in the others.

| space | base for m-ex slot *i* | Sonic (Akaneia m-ex slot 4) | what holds it |
|---|---|---|---|
| port **`FighterKind`** | `Ft_Kind_Mex0` = `0x21` = 33 | **37** | `Fighter::kind`, `ftData_*[kind]` |
| port **`CharacterKind`** | `ChKind_Mex0` = `0x22` = 34 | **38** | `PlayerInitData::ckind`, `ftMapping_list[ck]` |
| m-ex **INTERNAL** | 27 (Akaneia's added seven are 27..33) | 31 | `MxDt.dat` rows |
| m-ex **EXTERNAL** | 26 (Akaneia's added seven are 26..32) | 30 | m-ex CSS / ui tables |

Proof, from the code, not from memory:

- `src/melee/ft/forward.h`: `Ft_Kind_Mex0 = 0x21`, `ChKind_Mex0 = 0x22` (it sits *after*
  `ChKind_None = 0x21`, which keeps its value because ~200 sites store it).
- `src/melee/ft/ftdata.c:1733`: `Player_MexSetMapping(ChKind_Mex0 + slot, fk)` where
  `fk = Ft_Kind_Mex0 + slot`. So for m-ex slots, **`ck = fk + 1`**, always.
- The run logs confirm the fighter side: `gw: ftData_8008572C kind=37 file=PlSn.dat
  sym=ftDataSonic`.

**Both of tonight's numbers were right about different things.** Sonic is FighterKind 37 *and*
CharacterKind 38. `MELEE_TRAINING` writes `PlayerInitData::ckind`, so it takes **38**.
`MELEE_TRAINING=37` selects **Lucas** (m-ex slot 3). `docs/HANDOFF.md` §2 said 37 and was wrong;
it also said "`MELEE_TRAINING=38` … with all 7 registered is Dedede", which came from reading a
FighterKind list as CharacterKinds. Both are corrected.

The full table for Akaneia's seven:

| fighter | m-ex internal | FighterKind | **CharacterKind (`MELEE_TRAINING`)** |
|---|---|---|---|
| Wolf | 27 | 33 | **34** |
| Diddy | 28 | 34 | **35** |
| Charizard | 29 | 35 | **36** |
| Lucas | 30 | 36 | **37** |
| **Sonic** | 31 | 37 | **38** |
| Dedede | 32 | 38 | **39** |
| Tails | 33 | 39 | **40** |

For the **retail** cast the two port spaces are a different permutation, not an offset — Fox is
CharacterKind 2 and FighterKind 1. The conversion table lives in `gw_sl_ck_to_fk` and the test
`scene_ckind_fkind_table` checks every row of it against the game's own `ftMapping_list`, so it
cannot drift.

**Stages** have two spaces (`_research/mex-stages.md`): internal `GrKind` and external `StKind`.
Meta Crystal is internal **76**, external **293**. `StartMeleeRules::stkind` holds the
**external** one.

---

## 3. The grammar

```
MELEE_SCENE="key=value;key=value;…"
MELEE_SCENE_FILE=<path>      # same grammar, one `key value` or `key=value` per line
```

Separators are `;`, `,` or newline. `#` comments to end of line. Keys and names are
case-insensitive. A rejected field is logged, counted and skipped; the rest of the config still
applies.

**A number in a character or stage field must name its index space. A bare integer is
rejected.** This is the one rule the mechanism exists to enforce.

### Character reference

| form | meaning |
|---|---|
| `fox`, `falco`, `ganondorf`, … | a name from the table in `gw_runtime.c` — never ambiguous |
| `ck:N` | port `CharacterKind` |
| `fk:N` | port `FighterKind` (converted to a `CharacterKind`) |
| `mex:N` / `mexint:N` | m-ex INTERNAL id (converted) |
| `mexext:N` | m-ex EXTERNAL id (converted) |
| `random` | a random playable `CharacterKind` (0..25), drawn when the scene is seeded |
| `none` | `ChKind_None` — an empty slot |
| `37` | **rejected** |

### Stage reference

| form | meaning |
|---|---|
| `battlefield`, `fd`, `fod`, `dreamland`, … | a name (see `gw_sl_stage_names`) |
| `ext:N` | external `StKind` — Meta Crystal is `ext:293` |
| `int:N` | internal `GrKind` — Meta Crystal is `int:76`; converted via mexData's map |
| `293` | **rejected** |

### Fields

| key | value | default | notes |
|---|---|---|---|
| `mode` | `training`, `vs`/`melee`, `targettest`/`tt`, `title`, `menu`, `tiny`, `giant`, `stamina`, `camera`, `ssd`, `invisible`, `slomo`, `lightning` | — | required; sets the `GameModeKind` and the `GmVsMode` row it seeds |
| `at` / `screen` | `css`, `sss`, `match` | `match` | the screen within the mode. Both `GM_VS` and `GM_TRAINING` number their states CSS 0 → SSS 1 → playable 2 |
| `p1`..`p4` | `<charref>[/<opt>]…` | — | see below |
| `stage` | `<stageref>` | `izumi` (St_Kind_Izumi) | |
| `teams` | `0`/`1` | leave alone | |
| `time` | seconds | leave alone | 0 disables the timer |
| `items` | item frequency | leave alone | |
| `skipmemcard` | `0`/`1` | `1` when a scene is configured | §1 |
| `select` | `kit`, `native` | leave alone | Training's character / stage select on the port's kit screens or the native ones (gw_uigen.c `gw_Frontend_TrainingSelect`). Applied as the text is read and kept for later Training launches; `mode=training;at=css;select=kit` opens Training on the kit's CSS |

### Player options (`/`-separated, after the character)

| option | meaning |
|---|---|
| `c<N>` | costume / colour index |
| `hu` / `human` | human slot (the default for a named slot) |
| `cpu` | CPU slot |
| `cpu<N>` | CPU slot at level N |
| `demo` / `dummy` | demo slot (the Training dummy's kind) |
| `off` / `na` | empty slot |
| `hmp<N>` | handicap (retail default 9) |
| `team<N>` | team |
| `stocks<N>` | stock count |
| `kind<N>` | CPU kind (`cpu_kind`) |
| `nametag<N>` | nametag index |

---

## 4. Worked examples

```bash
# Training with Fox, default stage.
MELEE_SCENE="mode=training;p1=fox"

# Training as Sonic on Meta Crystal. ck:38 and fk:37 name the same fighter.
MELEE_SCENE="mode=training;p1=ck:38;stage=ext:293"
MELEE_SCENE="mode=training;p1=fk:37;stage=int:76"     # identical

# Training mode's CSS, with Fox preselected, so the character-select screen can be looked at.
MELEE_SCENE="mode=training;at=css;p1=falco"

# A four-player VS match on Final Destination: one human, three CPUs, one of them random.
MELEE_SCENE="mode=vs;p1=fox/c1/hu;p2=falco/cpu5;p3=random/cpu3;p4=ck:38/cpu9;stage=fd"

# The VS character-select screen with four players already configured.
MELEE_SCENE="mode=vs;at=css;p1=fox;p2=marth;p3=random;p4=random"

# Teams, 3 minutes, no items.
MELEE_SCENE="mode=vs;p1=fox/team0;p2=falco/team0/cpu9;p3=marth/team1/cpu9;p4=ganondorf/team1/cpu9;teams=1;time=180;items=0;stage=battlefield"

# Target Test as Fox.
MELEE_SCENE="mode=targettest;p1=fox"

# From a file.
MELEE_SCENE_FILE=C:/gdm/_build/scenes/sonic_metacrystal.txt
```

A scene file:

```
# Sonic on Meta Crystal
mode      training
p1        ck:38          # CharacterKind. FighterKind 37 is the same fighter.
stage     ext:293        # external StKind. Internal GrKind 76.
at        match
```

Run it:

```bash
export GW_MELEE=C:/gdm/worktrees/<agent> GW_BUILD_ROOT=C:/gdm/_build/agents/<agent>
MELEE_SCENE="mode=training;p1=ck:38;stage=ext:293" \
  bash C:/gdm/tools/port/run.sh sonic --iso C:/iso/Akaneia.iso
```

From **WSL**, a Windows binary does not inherit a WSL shell variable unless it is named in
`WSLENV`. `run.sh` now adds the `MELEE_*` variables to `WSLENV` itself, but a raw
`./melee-pc.exe` invocation from WSL still needs it.

---

## 5. The seeding rules, and why each one exists

`SceneLaunch_SeedVs()` (`src/melee/gm/gmscenelaunch.h`) is called from each mode's `on_load`,
which runs before the first state is entered. It does five things, and four of them are
load-bearing for reasons that are not obvious:

1. **Fills `VsModeData.start.players[i]`** from the config — ckind, slot type, colour, cpu
   kind/level, handicap, team, stocks, nametag, and `slot`.
2. **Never leaves the Training dummy at `ChKind_None`.** `ftMapping_list` is `[ChKind_Cap]`, and
   a `ChKind_None` (0x21) entry indexes the retail sentinel row, so the match scene builds a
   fighter with a garbage id and exhausts the heap in `lbMemory_80014FC8`. With `dummy_fallback`
   (Training) an unconfigured player 2 is filled with player 1's character as a CPU.
3. **Sets all three stage seeds so they agree** — `StartMeleeRules::stkind`,
   `gm_80473814.stage_id`, and the preload cache's `game_cache.stkind`. The SSS exit handler
   (`gm_801B1EEC`) normally sets the first two and the CSS handler the third; entering at the
   match skips both, and `lbDvd_SetupVsPreloadCache` then has no stage file to cache, which
   fires the `lbmemory` assert.
4. **Fills the preload cache's per-player entries** (`char_id`, `color`) before calling
   `lbDvd_SetupVsPreloadCache()`, or the cache holds the wrong character files.
5. **Jumps the state machine** with `gm_SetGameModeStateId(at)`.

The hand-off itself is in `gmboot.c`'s `bootOnLeave`: `SceneLaunch_BootGameMode()` returns a
`GameModeKind` and it becomes the pending mode. That still runs *after* the memory-card scene —
see §1 for why that matters and what was done about it.

---

## 6. The scene trace: "what screen am I on?"

Always on; `MELEE_SCENE_TRACE=0` disables it. Everything is edge-triggered, so a screen that
sits still costs one line, not one line a frame.

```
scene: enter  mode=GM_BOOT(40) state=0 screen=GS_MEMCARD(42)
scene: cursor memcard decision=2 option=0 (Yes/left) -- WAITING FOR A BUTTON
scene: cursor memcard-skipped a=1 b=0
scene: leave  mode=GM_BOOT(40) state=0 screen=GS_MEMCARD(42)
scene: enter  mode=GM_TRAINING(28) state=2 screen=GS_TRAINING(4)
scene: cursor menu kind=0 hovered=1 confirmed=0
```

| line | source | meaning |
|---|---|---|
| `scene: enter/leave` | `gm_1A3F.c`, `gm_801A4014` | every mode/state transition, `GameModeKind` and `GameSceneKind` by name |
| `scene: cursor memcard` | `gmscmemcard.c` | `decision` is the scene's own `tickDecision`; `option` is 0 = Yes/left, 1 = No/right. Decisions 2, 3, 5 and 11 wait for a button and say so |
| `scene: cursor menu` | `gmscene.c` frame loop | `MenuFlow`: `MenuKind`, `hovered_selection`, `confirmed_selection` — covers the main menu and every submenu that runs through `mnmain` |
| `gw: scene: …` | `gw_runtime.c` at first use | the parsed config, every field, plus one line per rejected field |

`gw: scene: no scene requested …` is printed when nothing is configured, so "the config was not
seen" and "the config was seen and did nothing" are now different log lines.

---

## 7. What is NOT settable yet

- **The CSS and SSS cursors are not reported.** They keep their state per player inside
  `CSSData`/`SSSData`, not in `MenuFlow`. `at=css` puts you on the screen with the characters
  preselected, but the log will not say where each player's hand is hovering. Adding it means a
  report call in `mncharsel.c` / `mnstagesel.c`.
- **Modes without a `VsModeData` row** take only `mode=` (they boot, nothing is seeded):
  `title`, `menu`, and every 1P mode. `targettest` is special-cased — `p1` becomes the Target
  Test character, which is what `gmmultiman.c` asks for.
- **Rules beyond `teams`, `time` and `items`**: stock count is per player (`stocks<N>`), but
  match kind, damage ratio, game speed, the item mask and the stage-select mode are not exposed.
  `StartMeleeRules` has them; nothing reads them from the config yet.
- **`random` is per slot, not "random with constraints"** — no "random but not Ice Climbers",
  no seeded/reproducible random. It draws from CharacterKind 0..25, so it never picks an m-ex
  fighter.
- **Players 5 and 6.** `GM_MAX_PLAYERS` is 6 but the CSS and this grammar both stop at 4.
- **No stage names for m-ex stages.** They are reachable only as `ext:`/`int:` numbers until the
  SSS expansion lands (`docs/HANDOFF.md` §1, gap 3).
- **Costume validity is not checked.** `c<N>` past a fighter's costume count is passed straight
  through.
- **Target Test still ignores `stage=`** — its stage comes from the character.
- **The boot-time `skipmemcard` disables saving for that run.** A scene launch that needs to
  write the memory card has to set `skipmemcard=0` and then drive the prompt with a pad script.

---

## 8. Testing

Seven headless tests, `--test`, green on vanilla and Akaneia (46/46 total):

| test | what it pins |
|---|---|
| `scene_ckind_fkind_table` | every retail `CharacterKind → FighterKind` row against the game's own `ftMapping_list`, plus `fk 37 ↔ ck 38` for the m-ex slots |
| `scene_parse_training` | `mode=training;p1=fox`, and that the default screen is the playable one |
| `scene_index_spaces` | `ck:38` and `fk:37` are the same fighter, `ck:37` is a different one, a bare `37` is **rejected**, names work |
| `scene_parse_vs_four` | a full four-player VS config with options, plus `random` staying inside 0..25 |
| `scene_parse_stage` | `ext:`, a name, and a bare number being rejected |
| `scene_memcard_default` | a scene skips the prompt; `skipmemcard=0` does not; no scene changes nothing |
| `scene_parse_file_form` | newline form, `key value`, `#` comments |

Parsing is a pure function of a string (`gw_SceneLaunch_LoadForTest`), which is what lets all
seven run in one process. The old hooks each cached their `getenv` in a `static` on first call
and could therefore only be tested once per process; nothing here does that any more.

**Still needs a windowed run**, because `--test` does not run the game's `main()` and so never
enters a scene: that a seeded scene actually renders. The runs to do, in order, on Akaneia:

```bash
MELEE_SCENE="mode=training;p1=fox"                     # cheapest possible proof
MELEE_SCENE="mode=training;p1=ck:38"                   # Sonic, the kind-number fix
MELEE_SCENE="mode=training;p1=ck:38;stage=ext:293"     # Meta Crystal, still never executed
MELEE_SCENE="mode=vs;at=css;p1=fox;p2=marth;p3=random;p4=random"
MELEE_SCENE="mode=vs;p1=fox/hu;p2=falco/cpu5;p3=marth/cpu5;p4=ck:38/cpu9;stage=fd"
```

Expect, in the log: `gw: scene: MELEE_SCENE="…"`, the parsed config, `scene: enter mode=GM_BOOT`,
`scene: cursor memcard-skipped`, then `scene: enter mode=GM_TRAINING(28) state=2
screen=GS_TRAINING(4)`.
