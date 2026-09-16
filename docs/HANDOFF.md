# Handoff — m-ex port / Sonic proof-of-life

**Written: 2026-09-16.** Supersedes the 2026-09-15 handoff (preserved in git,
`docs/HANDOFF.md` as of `d665c31`). **Stage authoring / Blender-as-level-editor remains DROPPED
by user decision** — do not resume it; the existing committed work is retained, not removed.

Read `_research/port-dev-quickref.md` (commands, env vars, toolchain) and `docs/MEX_PORT_STATUS.md`
(the 49-flag inventory) before touching anything.

---

## 1. Committed baseline

Both repos are clean.

```
ROOT  (master)                                   MELEE FORK (pc-port)
──────────────────────────────────────           ────────────────────────────────────────────
d374ee3 docs: rewrite the handoff for the …      54727c190 pc: add a content-probe dev hook; …
ba29781 tools: add a GameCube disc FST           4e68452ca pc: complete the m-ex Tier C predicate dispatch
        extractor; ignore disc artefacts         f6255d9ee pc: add the m-ex Tier C fighter hook surface
6645c59 build: surface per-TU compile failures   c204fa4b2 pc: port m-ex behaviors behind MELEE_MEX flags
```

Verified at commit time: `verify_changed.sh` 0 failures in **both** compile modes (`src/` and
`pc/`); lint 50 call sites / 0 violations; `MELEE_PC_LINK_OK`; tests **17/17** exit 0.

## 2. Tier C hooks — DONE and verified

The `Fighter On*` table-slot overrides (`OnLoad`, `OnDeath`, `OnDestroy/OnUserDataRemove`,
`OnFrame/UnkMotionStates3`, `OnAbsorb`, head-item, item-visibility, knockback) are re-expressed as a
flat native `[event][kind]` override array dispatched from the 11 decomp call sites. NULL clears a
slot; hooks live out-of-band so `ftData_*` reinit cannot clobber them. The §5 native API is complete
(`gw_Mex_HookRegister` / `gw_Mex_PredicateRegister` + `gw_Mex_GObjDispatch` /
`gw_Mex_GObjPredDispatch`) and both halves are unit-tested.

## 3. Sonic proof of life — extraction + file-level PoL DONE

Prerequisites (unchanged): clean ISO MD5 `0e63d4223b01d9aba596259dc155a174`; `Akaneia.iso` MD5
**`63ea8e113e451c9369f17f7a49012412`** (v1.0.1).

- `tools/gc_extract.py` is **fixed and committed**: a name offset of 0 is the first string in the
  table (the `audio/` directory), and a directory's length field is the index of the **last**
  in-subtree entry. Extraction now matches FST ground truth — Akaneia: root 1308 / `audio` 195 /
  `audio/us` 80 / `plugins` 9 = **1592**; vanilla: root 998 / `audio` 154 / `audio/us` 57 = 1209.
  Extraction lives at `/tmp/akaneia-fixed` (regenerate with `python3 tools/gc_extract.py
  /mnt/c/iso/Akaneia.iso <outdir>`).
- **File-level PoL works.** `MELEE_CONTENT_PROBE=PlSn.dat` against `Akaneia.iso` logs
  `gw: content probe: PlSn.dat -> parsed by lbArchive_LoadArchive` — the port's own HSD loader
  consumes m-ex-produced fighter data from the disc FST.
- Sonic data (recon): fighter **031**, joint `PlySonic5K_Share_joint`, stage **082** = `Targets!Sonic`
  (`/GrTSn.dat`). Music is **105 / 125 / 134** (`sonic.hps` / `ff_sonic.hps` / `sonic2.hps`) — the
  2026-09-15 handoff's "51 / 66 / 74" was wrong (66 is the sound **bank**, `sounds/066.json`).

## 4. BLOCKER FOUND — Akaneia.iso OOMs at boot when a save exists

Running the port against `Akaneia.iso`:

```
lbMemory_80014FC8: ALLOC_FAIL size=0xE9B20 lo=0x801F1940 hi=0x806EBFD0
assertion "memp_kouho" failed   (src/melee/lb/lbmemory.c:163)
```

Isolation (40 s off-screen boot, `MELEE_SKIP_INTRO=1`):

| ISO | card | result |
|---|---|---|
| Akaneia | on (save present) | **ALLOC_FAIL at retrace=4** |
| Akaneia | off (`MELEE_CARD=0`) | boots, renders ~1800 frames |
| Akaneia | empty `MELEE_CARD_PATH` | boots, renders 1830 frames |
| vanilla | on (same save) | boots, renders ~1980 frames |

So the crash is **m-ex content + an existing save**, not the content probe and not the card code per
se. The engine's memory budget is vanilla-sized; the card-save boot path (stack reaches
`lbcardgame.c` and the `lb_800192A8` DVD spin) then needs ~956 KB the `memp` pool cannot supply.
This is the content-expansion **memory plumbing** work — §6.1 grew `lbHeap` for 7 heaps, but the
`lbMemory` pool / file sizes are the next thing to size for m-ex content. **Dev workaround:
`MELEE_CARD=0`.**

## 5. Traps (still true)

- **`pipe_wsl.sh`** now exits non-zero (commit `6645c59`), but the reliable signal remains
  `CC_FAIL`/`GW_FAIL` in the text. Treat any green result as untrusted until you have shown the
  check can fail (`verify_changed.sh` was re-falsified this session).
- **Never poll a background task.** Absence of a completion notice is not progress.
- **`MELEE_WINDOW_HIDE` does not work** (present blocks forever) — park the window off-screen with
  `MELEE_WINDOW_X/Y=30000`.
- **The memory card is on by default**; `MELEE_CARD=0` disables it, `MELEE_CARD_PATH` points it at
  another folder. **Run at most one `melee-pc.exe`; kill with `taskkill /F /IM melee-pc.exe`.**
- **CRLF**: the fork normalises CRLF→LF; changed `src/` files show a rewrite warning on commit.

## 6. Conventions

- Game-source changes `#if defined(TARGET_PC)`-guarded with the original under `#else`.
- Runtime gating: `extern int Mex_Enabled(const char *); if (Mex_Enabled("<snake_case_name>"))`;
  flag names globally unique (49 taken).
- Attribution at every change site:
  `Ported from m-ex (https://github.com/akaneia/m-ex): <path>, @ <address>. <what changes>.`
- **m-ex has NO LICENCE** — specification only; never vendor/copy/transcribe its `.asm`/`.h`/`.dat`.
- `GIT_MASTER=1`; per-command `-c user.name="GD" -c user.email="gd@gsd.sh"`; melee subjects `pc:`,
  root subjects `docs:`/`build:`/`tools:`. **Never `git add -A`.**

## 7. What is NOT proven

- **Sonic is not playable** — only his fighter DAT parses through the loader. Adding a character
  needs the Tier B data plumbing in `_research/mex-content-expansion.md` §6.3.
- The Akaneia-save OOM (§4) is **not fixed**.
- The content probe fires on the memcard-scene leave path (`bootOnLeave`), so it does not run in a
  card-disabled boot; move it to a card-independent hook if that matters.
- ~45 of the 49 flags remain behaviourally unverified.

## 8. Next steps

1. Root-cause the Akaneia + save OOM (§4): find what needs ~956 KB on the save path and size the
   memory budget for m-ex content.
2. Extend the content probe to the stage (`GrTSn.dat`) and target-test files; make it
   card-independent.
3. Then the first real character add (Sonic) per `_research/mex-content-expansion.md`.
