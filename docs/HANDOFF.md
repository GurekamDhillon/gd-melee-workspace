# Handoff — m-ex port / Sonic proof-of-life

**Written: 2026-09-15 20:29 PDT (2026-09-16 03:29 UTC).**
Supersedes the previous stage-authoring handoff, which is preserved in git history
(`docs/HANDOFF.md` as of commit `d665c31`). **Stage authoring / Blender-as-level-editor is
DROPPED by user decision** — do not resume it. Existing committed work (the `.tt` mod loader,
`MELEE_TARGET_TEST`, `hsd_export`/`stagec`, Blender I/O tooling) remains in the tree and functional;
dropping means no further development, not removal.

Read `_research/port-dev-quickref.md` (commands, env vars, toolchain) and `docs/MEX_PORT_STATUS.md`
(the 49-flag inventory + verification results) before touching anything.

---

## 1. Committed baseline

Committing was explicitly authorised and is **done**. Both repos are clean apart from the items in
§4 and §5.

```
ROOT  (master)                          MELEE FORK (pc-port)
───────────────────────────────         ─────────────────────────────────────────
6645c59 build: surface per-TU           c204fa4b2 pc: port m-ex behaviors behind
        compile failures;                       MELEE_MEX flags
        refresh manifests               c9f044983 pc: add an in-engine unit test suite
d665c31 docs: m-ex port status,
        handoff and research;
        drop stage authoring
17db6d2 tools: m-ex patch
        resolution, PPC disasm,
        verify and lint
```

Verified at commit time: 33 files compile in **both** `TARGET_PC` and non-`TARGET_PC` (0 failures);
lint 50 call sites / 0 violations; `MELEE_PC_LINK_OK`; tests 15/15 exit 0 in both flag
configurations; boots and renders with flags enabled (0 FATAL).

## 2. IN FLIGHT — Tier C hooks (agent was still running at handoff)

Agent `bg_ee8bfe51`, session `ses_f57eb454effe01zDNEdpb7VWYu` — **still active when this was
written** (56 messages, 7 todos). It is implementing step 1 of `_research/mex-tier-c-hooks.md`
§7: the `OnFrame` hook via the `ftData_UnkMotionStates3` table at `Fighter_8006A360`, plus the
§5 native API (`gw_Mex_HookRegister` / `gw_Mex_PredicateRegister`).

**Uncommitted, UNVERIFIED, all-additive (+329 / -0):**

| File | Δ | What |
|---|---|---|
| `pc/platform/gw.h` | +55 | the new API declarations |
| `pc/platform/gw_runtime.c` | +98 | dispatch implementation |
| `pc/tests/mex_tests.c` | +72 | tests |
| `src/melee/ft/fighter.c` | +63 | OnFrame call site |
| `src/melee/ft/ftcommon.c` | +28 | |
| `src/melee/ft/ftdemo.c` | +13 | |

**Do NOT trust this until verified.** Run, in order:

```bash
cd "/mnt/c/Users/Gurek/Desktop/GD's Melee"
bash tools/mex_port/verify_changed.sh          # both compile modes
python3 tools/mex_port/lint_ports.py melee/src
cd melee && cmd.exe /c "cd /d C:\gdm\_build\ax86m && ..\build_melee_pc.bat"
cmd.exe /c "cd /d C:\gdm\_build && run_tests.bat"
```

The design's §6 risks are the acceptance criteria — all three compile perfectly while failing
silently: **flat table dispatch** (not a linked list — this runs n_fighters × 60 Hz); **NULL must be
clearable** (vanilla's `cmpli/beq` means "no callback", so a set-only API destroys vanilla
behaviour); **re-apply after mode reinit** (`ftData_*` are static tables).

## 3. Sonic port — FULLY UNBLOCKED, ready to start

Goal (user): port Sonic as a **file proof of life** that the whole m-ex content pipeline works.

**All three prerequisites are now done and verified:**

| Prerequisite | State |
|---|---|
| `xdelta3` | installed at `~/.local/tools/xdelta3/usr/bin/xdelta3` (3.0.11, unpacked from a .deb — **no root needed**, `sudo` requires a password here) |
| Clean ISO | `/mnt/c/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso` — MD5 verified `0e63d4223b01d9aba596259dc155a174` ✓ |
| Akaneia disc | **BUILT**: `/mnt/c/iso/Akaneia.iso`, 1,459,978,240 B, MD5 **`63ea8e113e451c9369f17f7a49012412`** ✓ (the exact documented v1.0.1 hash). Took 11m40s. |

Reproduce the disc with:

```bash
~/.local/tools/xdelta3/usr/bin/xdelta3 -d -f \
  -s "/mnt/c/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso" \
  patch.xdelta /mnt/c/iso/Akaneia.iso
```

**IMMEDIATE NEXT STEP — extract the disc.** `tools/gc_extract.py` was just written for this
(GameCube FST walker, stdlib only, `--list` / `--only <prefix>` supported). It is **untested** —
run `--list` first to sanity-check, then extract:

```bash
python3 tools/gc_extract.py /mnt/c/iso/Akaneia.iso /tmp/akaneia-extract --list | head -40
python3 tools/gc_extract.py /mnt/c/iso/Akaneia.iso /tmp/akaneia-extract
```

That yields the `files/` and `sys/` that the repo cannot ship (Nintendo's assets aren't
redistributable — the patch is a diff against a disc you own, which is why this route is legitimate).
`pyisotools 2.4.7` + `dolreader` are also installed user-level as a fallback/validator.

**Where Sonic is (confirmed by reconnaissance):**
- Fighter **031** = `"Sonic"`, joint symbols `PlySonic5K_Share_joint` / `PlySonic5KRe_Share_joint`
  (two models).
- Series: `"Sonic the Hedgehog"`; stage **082** = `"Targets!Sonic"`; music ids 51/66/74.
- Metadata lives in `akaneia-build/data/`, portraits in `akaneia-build/assets/`
  (428 CSPs, 68 CSS entries).
- The actual fighter/stage **data files are NOT in the repo** — they only exist inside
  `Akaneia.iso`. Extraction (above) is what produces them.

## 4. Uncommitted / needs attention

- `akaneia-build/` — 60 MB, 1592 dirty files right after clone (CRLF normalisation). **Not
  gitignored.** Add an entry before any `git add -A`-adjacent work.
- `patch.xdelta` — 244 MB, untracked, in the project root.
- `tools/gc_extract.py` — untracked, written this session, **untested**.
- `_build/` — 153 untracked artefacts (Blender/HSDLib/glTF/PNG/DAT). **Deliberately never
  committed.** Do not `git add` them.

## 5. Known traps (each cost real time)

- **`pipe_wsl.sh` `$?` is meaningless** — the script `exit 0`s regardless. The **only** failure
  signal is `CC_FAIL`/`GW_FAIL` in the output **text**. Same class of bug appeared in five separate
  checks this project (a `grep` for the wrong assert wording, a never-reached loop, a
  `git --porcelain` that hid untracked dirs). **Treat any green result as untrusted until you have
  shown the check can fail.**
- **Never poll a background task.** Absence of a completion notification is **not** evidence of
  progress. Five agents in this project died silently and were reported as "running" for hours; one
  had finished the answer 3h20m earlier and its result was recovered only by reading its session
  transcript. Check `session_info` timestamps and inspect the working tree ("are files on disk?").
- **Batch agents must be told to write incrementally.** The first attempt produced **zero files**
  from four agents because they planned everything and wrote nothing at the end. Adding "save each
  edit as you make it" turned it into two successful deliveries.
- **`taskkill`/`Start-Process -PassThru` from WSL hang.** Read logs with WSL-side tools; kill with
  `cmd.exe /c taskkill /F /IM melee-pc.exe` at most, and never wait on it.
- **CRLF**: the melee fork normalises CRLF→LF; ~33 files will be rewritten on next touch. Consider
  `.gitattributes` rather than discovering churn later.

## 6. Conventions

- All game-source changes `#if defined(TARGET_PC)`-guarded with the original under `#else`, so the
  non-PC matching build stays byte-identical. Pattern: `src/melee/gr/ground.c` near `Ground_801C4210`.
- Runtime gating: `extern int Mex_Enabled(const char *); if (Mex_Enabled("<snake_case_name>"))`.
  Flag names must be **globally unique** — 49 are taken, see `docs/MEX_PORT_STATUS.md`.
- Attribution at every change site:
  `Ported from m-ex (https://github.com/akaneia/m-ex): <path>, @ <address>. <what changes>.`
- **m-ex has NO LICENCE** (upstream issue #20 unanswered). It is a **specification only** —
  reimplement behaviour in original C; never vendor, copy or transcribe its `.asm`/`.h`/`.dat`.
- `GIT_MASTER=1` on git commands; per-command `-c user.name="GD" -c user.email="gd@gsd.sh"`;
  melee subjects `pc:`, root subjects `docs:`/`build:`/`tools:`. **Never `git add -A`.**
- Compile check a single game TU: `bash /mnt/c/gdm/_build/masstest/pipe_wsl.sh <file>` (silent = OK).

## 7. What is NOT proven

The 49 flags are **compile/link/run** clean, with flags enabled, no faults. Only 4 families were
hand-audited against the m-ex originals (`default_*`, the four `unlock_*`, `stage_music_5050`,
`skip_result_screen`) — all faithful. **The other ~45 are not behaviourally verified.** 15 tests are
not load-bearing for 49 flags. Per-flag play testing is outstanding.
