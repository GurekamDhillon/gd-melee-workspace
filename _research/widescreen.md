# Widescreen support — recovered plan, mechanism, and seams (2026-09-28)

**Status: plan recovered; steps 1-2 implemented 2026-09-28 (game `afbe4bc37`, published to pc-port);
steps 3-6 remain.** The job that was supposed to do it (`worktrees/codex-widescreen`,
branch `codex/widescreen`) never ran: its transcript (`_build/tmp/codex-codex-widescreen.jsonl`) is a
single usage-limit failure ("try again at Oct 3rd"). No widescreen commit exists on any branch. This
file recovers the specification and maps it onto our code so it can be executed directly.

## Credits and attribution (read first)

- **Mechanism — Slippi's "Optional: Widescreen 16:9" Gecko code**, authored
  **[Dan Salvato, mirrorbender, Achilles1515, UnclePunch]** (credit line as shipped in the code
  list), from **Project Slippi / Slippi Ishiiruka** (`GameSettings/GALE01r2.ini`, GPL-2.0).
- **Reference implementation and presentation policy — [melee-unlocked](https://github.com/hero88go/melee-unlocked)**
  by **Hero88go** (GPL-2.0). A local checkout exists at `_build/refs/melee-unlocked` (git-excluded,
  read-only; reference use is permitted — see `docs/PAUSED-2026-09-27.md` item 4: "keep attribution
  on copied code"). Its vendored copy of the Slippi code list is at
  `_build/refs/melee-unlocked/port/slippi_sys/GameSettings/GALE01r2.ini` (~line 7298).
- **Rule:** we reimplement the behavior as a specification in decompiled C (as with m-ex). No code is
  copied verbatim; every ported site carries a comment crediting the code's authors, and the entries
  in `DEPENDENCIES.md` (workspace, spec references) and `melee/pc/DEPENDENCIES.md` record the
  arrangement. README credits get the names at ship time.

## What the plan was

From `docs/PAUSED-2026-09-27.md` (item 4): **Hor+ aspect setting, HUD anchoring, kit safe area, live
toggle** — reference `melee-unlocked`, explicitly *not* 999sian/melee-pc.

Translated into requirements:

1. **Hor+ aspect setting** — widen the horizontal view for gameplay (not stretch), selectable
   (native 73:60 / 4:3 / 16:9 / stretch), persisted like the other video settings.
2. **HUD anchoring** — the game's own 2D interface must sit correctly in the wider frame (the Slippi
   code patches exactly the elements that break; see the table below).
3. **Kit safe area** — our own menus/kit UI (and scripts) need a defined wide layout/safe area;
   `gd.safe_area` is already probed by `gw_comm.lua` ("the widescreen lane's API, when it exists").
4. **Live toggle** — changeable at runtime (settings page; testable via an env var).

**Landed so far (game `afbe4bc37`):** the `widescreen` setting / `MELEE_WIDESCREEN`
(`gw_Widescreen_Enabled`, `pc/platform/gw_settings.c`), the core camera widen in `CObjLoad`
(`src/sysdolphin/baselib/cobj.c`), and the presenter aspect through Aurora's own viewport policy
(`AURORA_VIEWPORT_STRETCH` synced per frame in `pc/platform/shim_vi.c`). Verified numerically:
headless suite 203/203; `gd.project` of fixed world points matches a 16:9 frustum to sub-pixel
(predicted 117.2/954.2 vs measured 117.5/953.5) and native 73:60 with the flag off (-98.5 vs
-98.54); the render target fills the window (1345 px fit vs 1920 px). Not yet: the peripheral
sites below, kit safe area, the settings-page row / aspect pickers, and the rollback question.
Note: `AURORA_VIEWPORT_STRETCH` fills whatever window shape it gets — on a 16:9 window the widened
frame is exactly right; on other shapes it stretches until the aspect pickers land.

## The specification: Slippi's "Optional: Widescreen 16:9" code

Melee never renders 4:3: every camera asks for aspect 1.2173333 (73:60) — our decomp's camera
template has the same constant (`src/melee/cm/camera.c:170`), and our log's `camtrans` DIAG agrees
(`aspect=1.21733`). The code multiplies the camera aspect by 320/219, and 73/60 × 320/219 is exactly
16:9. The code is online-safe (presentation only; it writes no simulation state).

Full code block (from the vendored `GALE01r2.ini`), with our symbol map
(`melee/config/GALE01/symbols.txt`, addresses → name + offset):

| Gecko line | address | our symbol | effect |
|---|---|---|---|
| `C236A4A8 00000007` | 0x8036A4A8 | `CObjLoad +0x1BC` | **the core widen**: scales a loaded CObj value by 320/219 (floats 0x43A00000 / 0x435B0000) so camera aspect becomes 16:9 |
| `04030C7C 38000064` | 0x80030C7C | `Camera_80030BBC +0xC0` | "Left Camera Bound" = 100 |
| `04030C88 3800021C` | 0x80030C88 | `Camera_80030BBC +0xCC` | "Right Camera Bound" = 540 |
| `04086B24 60000000` | 0x80086B24 | `ftLib_80086A8C +0x98` (`src/melee/ft/ftlib.c:537`) | NOP → "Draw High Poly Models" at the wider edges |
| `C22FCFC4 00000004` | 0x802FCFC4 | `NameTag_Create +0x8C` (`src/melee/if/ifnametag.c`) | nametag background X scale ×~6.887 (raw 0x40DC7AE1) |
| `044DDB84 3E89FEFA` | 0x804DDB84 | `if`-area float (≈0.2695) | nametag text X scale |
| `044DDB58 3E4CCCCD` | 0x804DDB58 | `if`-area float (0.2) | bubble (offscreen indicator) zoom |
| `044DDB28 43660000` / `044DDB2C C3660000` | 0x804DDB28/2C | `if`-area floats (+230.0 / −230.0) | extend bubble vertical bounds |
| `044DDB30 3F666666` / `044DDB34 BF666666` | 0x804DDB30/34 | `if`-area floats (0.9 / −0.9) | bubble corner values |
| `044DDB4C 3D916873` | 0x804DDB4C | `if`-area float (≈0.0710) | widen bubble region |
| `043BB05C 3EB00000` | 0x803BB05C | `lbl_803BB028` (`src/melee/lb/lbbgflash.c:65`, the screen-flash `HSD_CameraDescPerspective`) +0x34 | "Fix Screen Flash" (0.34375) |

Note the 0x4DDBxx floats sit in the interface TUs (`ifMagnify_804DDB60` is at 0x4DDB60, so the table
is the neighbouring anonymous data); resolve exact arrays by address during implementation.

## Reference implementation notes (melee-unlocked)

From `port/runtime/gx/gx_d3d12.h:181-211` (comments) and `port/app/main.cpp`:

- Presentation policy: default aspect **73:60**; `--aspect auto|73:60|4:3|16:9|stretch`; with the
  widescreen code on, **auto** picks 16:9 only for "widenable" scenes (a mode's
  character/stage-select through its results screen — i.e. scenes with 3D content). The bare menu
  shell (main menu, options, trophies, VS mode select) stays 73:60 letterboxed: it is almost
  entirely the 2D layer, which is *deliberately never widened*, so a 16:9 claim there would just
  stretch.
- Two modes, mutually exclusive: `--widescreen` (run the Gecko code; present 16:9) and experimental
  `--true-widescreen` (widen the frustum in the renderer instead — HUD/2D keep authored size,
  nothing written to guest memory).
- The presenter letterboxes to the chosen aspect (`gx_d3d12.cpp` present path); the game-side code
  is toggled through Slippi's `request_widescreen(...)` when the option changes.
- Their vendored Slippi sys README credits Slippi Ishiiruka (GPL-2.0) for the code list/bootloader.

## Our port's seams today

- **Camera aspect:** `src/melee/cm/camera.c:170` (`1.2173333f` in the camera template;
  `Camera_80030BBC`/`Camera_80030DE4` nearby). The CObj widen (top row above) is what actually
  multiplies at load time.
- **Projection / viewport diagnostics:** `pc/platform/shim_gx.c` `gw_diag_cam_translate`
  (line ~258) already receives the camera viewport and the computed aspect — the same values the
  widescreen change touches; remove or reuse this TEMP DIAG when implementing.
- **Presentation:** `pc/platform/shim_vi.c` presents the 640×480 EFB scaled by `render_scale`
  (line ~391-513); there is **no aspect or letterbox handling yet** — widescreen needs this.
- **Settings:** `pc/platform/gw_settings.c` (`gw_Settings_Int/SetInt`, `settings.cfg`); the kit
  Settings screen is in `src/melee/gm/gmfrontend*`; env-var convention for tests is `MELEE_*`.
- **UI space:** scripts/menus draw in the 640×480 virtual screen (`gd.text`, `gd.kit`,
  `gs_project`); `gw_comm.lua` already probes `gd.safe_area`; a wide layout needs both the game's
  2D interface pieces (the table above) and our kit screens.
- **Precedent for runtime game patches:** our port already reimplements Slippi/UCF code behavior
  natively (`pc/platform/gw_slippi_*`), so a `widescreen` flag applied as C conditionals (not
  instruction patches) fits the codebase.

## Proposed implementation (phases)

1. **Flag + plumbing:** `settings.cfg` key (`widescreen=auto|off|16:9|stretch`), `MELEE_WIDESCREEN`
   for runs, a Video page row; expose current aspect to scripts (and the future `gd.safe_area`).
2. **Core widen:** make the camera aspect dynamic at the CObj path (`CObjLoad` equivalent) to
   16:9 when on — same result as ×320/219, as a C conditional.
3. **The peripheral sites:** port the remaining rows of the table (bounds, high-poly, bubble
   constants, nametag scales, screen-flash desc) behind the same flag; each site gets its credit
   comment.
4. **Presentation:** present 16:9 when on (letterbox policy mirroring melee-unlocked's
   `presented_aspect`, including "widen only scenes with 3D content" if we keep native screens).
5. **Kit safe area + layouts:** define the wide safe area in our UI space, expose `gd.safe_area`,
   and lay out kit screens (main menu/lobby/CSS/SSS/settings) for the wide frame.
6. **Validation:** LAB checks (HUD elements, offscreen bubbles, nametags, screen flash, high-poly),
   menus, netplay/rollback (below), replays, and the crash sweep.

## Open questions / risks

- **Rollback and snapshots:** the code writes guest memory (CObj floats, scissor values). Slippi
  calls it online-safe because it never touches simulation, but our rollback snapshots/compare game
  memory — verify these values are either forced deterministically on both peers or excluded from
  the state hash before enabling online.
- **Which scenes widen:** follow melee-unlocked's `widenable_scene` policy or widen everything with
  3D content (our kit menus replace most native 2D screens, which changes the calculus).
- **Default presentation:** letterboxed 16:9 vs anamorphic stretch at the window's aspect; pick a
  default and keep the picker (`--aspect` equivalent).
- **HUD audit list:** percent/stocks, timer, nametags, offscreen bubbles, magnifier, screen flash,
  crowd/background effects — the table covers the known ones; audit the rest on screen.
- **Performance:** a wider view can draw more scene per frame; measure with `gd.perf` (120 fps
  headroom target).

## Attribution checklist (for the implementation)

- [ ] Every ported site: comment citing "Slippi's Optional: Widescreen 16:9 code — Dan Salvato,
      mirrorbender, Achilles1515, UnclePunch" + the `GALE01r2.ini` line.
- [ ] `DEPENDENCIES.md` (workspace, "Specification references") — Slippi code entry. *(added 2026-09-28)*
- [ ] `DEPENDENCIES.md` — melee-unlocked reference checkout entry. *(added 2026-09-28)*
- [ ] `melee/pc/DEPENDENCIES.md` — entry when code lands (mirrors the existing Slippi packet-codec entry).
- [ ] README credits at ship: code authors + melee-unlocked.
