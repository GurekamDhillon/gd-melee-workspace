# Build a from-scratch frontend for a Super Smash Bros. Melee PC port

You have no access to our codebase, and you don't need it. This document is complete: it gives you the facts about the target, a C interface boundary (**section 4**) you build against, and what we need back. We integrate your work into the game on our side.

## 1. What this is

**GD's Melee** is a native Windows PC port of *Super Smash Bros. Melee* (GameCube, NTSC 1.02), built from the community's decompilation rather than by emulation. The gameplay, rollback netplay, mod support, settings and matchmaking all work. The menus work too, but they run on a small, limited renderer: pre-rendered images as textured quads in a fixed 640×480 space, a few keyframes of animation, and no shaders.

**We want you to build the entire graphical frontend from scratch:** every menu, screen, transition and overlay. **There are no design constraints.** Art direction, motion language, layout system, rendering techniques and interaction model are all yours to invent. Make players stop and stare. The only limits are the engineering and legal requirements below; treat them as hard walls.

## 2. The target, as facts

- **Platform:** Windows, and the game is a **32-bit x86 (i686)** executable. Your code must compile for i686 with clang or MSVC. The mock app (section 5) may also build 64-bit.
- **Languages:** C11 or C++17. There's no managed runtime, and no Python or JavaScript at runtime.
- **Graphics:** the game renders through **WebGPU (Google's Dawn implementation, the standard `webgpu.h` C API)**. The host gives you a `WGPUDevice`, a `WGPUQueue`, and each frame a target `WGPUTextureView` plus its format and size. You record your own passes: you can write WGSL shaders and use render-to-texture, compute, anything WebGPU allows.
  - While a menu is showing, you own the whole frame.
  - During matches you may draw overlays (pause menu, HUD extras) on top of the game's already-rendered frame, so don't clear it.
- **Windowing and input:** handled by the host (SDL3 in the game). You receive per-frame input state (section 4). **You don't create windows or read devices.**
- **Frame model:** the game's logic runs at a fixed **60 Hz** and must stay deterministic, because rollback netplay depends on it. The display may run faster: the host can call your render more often than your update and passes an interpolation alpha. Your UI must never affect the simulation.
- **Latency budget:** the host samples controllers right after its frame-pacing wait, and submits a finished frame immediately. Your per-frame work must be cheap and predictable. Target **≤ 1.5 ms CPU and ≤ 2 ms GPU per frame at 1440p** on a mid-range GPU. Never block, and never allocate in steady state.
- **Resolution:** any window size and any aspect ratio (16:9, 21:9, 16:10, 4:3), at native resolution, with no fixed logical canvas. It must look right from 720p to 4K.
- **Controllers:**
  - **GameCube controllers** (via adapter) are the primary input: analog stick, C-stick, A/B/X/Y/Z, L/R (analog plus digital), Start, d-pad. Also standard SDL gamepads and the keyboard.
  - **Four local players** use the character select at the same time, each with their own cursor.
  - **Text entry** (player names, 4-character room codes) comes from the keyboard. While a text field is focused, tell the host (section 4) so the keyboard stops acting as a controller.
- **Memory:** the game's own heap is small and fixed. Allocate your memory and GPU resources yourself through normal allocation. Never assume you can use the game's heap.

## 3. Hard requirements

**Legal and provenance**
1. **Everything you ship must be original:** art, icons, fonts, sounds and code. **Do not use or recreate Nintendo or HAL assets,** logos or trade dress.
2. **Game art stays on the user's machine.** At runtime the host can hand you images read from the user's own disc (fighter portraits, stage previews, name plates) as RGBA pixel buffers. You may display them. They never go into your deliverables.
3. **Permissive licences only:** MIT, BSD, zlib, Apache-2.0, and OFL for fonts. No GPL or LGPL. List every dependency with its licence.

**Engineering**

4. **Build only against the section 4 interface.** It's the whole contract. If you need something it doesn't provide, add it to the header in a clearly marked "PROPOSED" section with a justification. Don't assume hidden internals.
5. **Keep rendering separate from logic.** Menu logic, navigation and state machines must run with no GPU present, and be unit-testable headless.
6. **Scriptable and inspectable.** This is non-negotiable.
   - `fe_query_state()` (section 4) must return an accurate snapshot at any moment: current screen id, focused element id, each player's cursor and selection on the character and stage selects, the current page, whether a modal or text field is open, and whether a transition is running.
   - Values are always current, never stale from a previous screen.
   - Automated tests drive the UI by waiting for a specific state before sending each input, so every screen needs a clear "ready" state.
7. **Data-driven and moddable.** Rosters and stage lists change at runtime: mods add fighters and stages, so plan for 25 to 150+ of each. Themes, layouts and screens should be definable in data files, so modders can restyle and add screens or settings rows without recompiling. Keep any data format simple, documented and safe to load.
8. **Never touch the simulation.** You only read the state the host gives you and emit actions.

## 4. The interface boundary (build against this exactly)

```c
/* fe_api.h - the contract between the game (host) and the frontend (you).
 * All strings are UTF-8. All arrays are owned by whoever provided them and valid until the
 * next call into that side unless stated otherwise. Ints, not bools, for ABI simplicity. */
#include <stdint.h>
#include <webgpu/webgpu.h>

/* ---------- identifiers ---------- */
typedef int32_t fe_fighter_id;   /* opaque; stable for the session */
typedef int32_t fe_stage_id;     /* opaque; stable for the session */

/* ---------- input (host -> frontend), once per 60 Hz update ---------- */
enum { FE_BTN_A=1<<0, FE_BTN_B=1<<1, FE_BTN_X=1<<2, FE_BTN_Y=1<<3, FE_BTN_Z=1<<4,
       FE_BTN_L=1<<5, FE_BTN_R=1<<6, FE_BTN_START=1<<7,
       FE_BTN_UP=1<<8, FE_BTN_DOWN=1<<9, FE_BTN_LEFT=1<<10, FE_BTN_RIGHT=1<<11 };
typedef struct fe_pad {
  int32_t connected;
  uint32_t held, pressed, released;  /* FE_BTN_* bitmasks; pressed/released = edges this update */
  float stick_x, stick_y;            /* -1..1, y up */
  float cstick_x, cstick_y;          /* -1..1 */
  float trigger_l, trigger_r;        /* 0..1 */
} fe_pad;
typedef struct fe_input {
  fe_pad pads[4];
  const char *text_utf8;             /* characters typed this update (only while text entry is on) */
  int32_t key_backspace, key_enter, key_escape, key_paste; /* edges */
} fe_input;

/* ---------- content (host -> frontend) ---------- */
typedef struct fe_image { int32_t w, h; const uint8_t *rgba; } fe_image; /* straight alpha */
typedef struct fe_fighter {
  fe_fighter_id id; const char *name; const char *series;  /* series may be "" */
  int32_t costume_count; int32_t is_mod;                    /* added by a mod */
  int32_t available_online;  /* 1 both players have it, 0 not in common, -1 not known yet / offline */
} fe_fighter;
typedef struct fe_stage {
  fe_stage_id id; const char *name; const char *series;
  int32_t is_mod, locked, legal_competitive;                /* in the 6-stage legal list */
  int32_t available_online;
} fe_stage;

/* ---------- settings (host -> frontend): a generic, self-describing list ---------- */
enum { FE_SET_TOGGLE, FE_SET_CHOICE, FE_SET_SLIDER, FE_SET_TEXT, FE_SET_ACTION };
typedef struct fe_setting {
  const char *page;          /* "Video", "Audio", "Controls", "Online", "Mods", "Gameplay", ... */
  const char *key, *label, *help;
  int32_t type;
  int32_t value, min, max, step;      /* TOGGLE/CHOICE/SLIDER */
  const char *const *choices; int32_t choice_count;  /* CHOICE */
  const char *text; int32_t max_len;  /* TEXT (e.g. player name, server address) */
  int32_t needs_restart;
} fe_setting;

/* ---------- mods (host -> frontend) ---------- */
typedef struct fe_mod {
  const char *id, *name, *version, *kind, *description;  /* kind: base|fighter|stage|script|misc */
  int32_t active_now;        /* mounted this boot */
  int32_t enabled_next_boot;
  int32_t status;            /* 0 ok, 1 off, 2 missing requirement, 3 conflict */
  const char *status_text;
} fe_mod;

/* ---------- online (host -> frontend) ---------- */
enum { FE_NET_OFF, FE_NET_HOSTING_WAIT, FE_NET_JOINING, FE_NET_SEARCHING_RANDOM,
       FE_NET_LOBBY, FE_NET_IN_MATCH, FE_NET_RESULTS, FE_NET_ERROR };
enum { FE_LOBBY_CHARS_BLIND, FE_LOBBY_COIN, FE_LOBBY_STRIKE, FE_LOBBY_BAN, FE_LOBBY_PICK,
       FE_LOBBY_CHAR_WINNER, FE_LOBBY_CHAR_LOSER, FE_LOBBY_READY, FE_LOBBY_COUNTDOWN, FE_LOBBY_GO };
enum { FE_STAGE_FREE, FE_STAGE_STRUCK_P1, FE_STAGE_STRUCK_P2, FE_STAGE_BANNED, FE_STAGE_PICKED };
typedef struct fe_lobby_player {
  const char *name; fe_fighter_id fighter; int32_t costume;
  int32_t locked_in, ready, is_me, is_host, ping_ms;
} fe_lobby_player;
typedef struct fe_online {
  int32_t state;                    /* FE_NET_* */
  const char *status_text;          /* human-readable host message ("Waiting for opponent...") */
  const char *room_code;            /* 4 chars, "" if none */
  int32_t random_search_seconds;
  /* lobby (valid when state == FE_NET_LOBBY) */
  int32_t lobby_phase;              /* FE_LOBBY_* */
  int32_t game_number, score_me, score_them;
  int32_t my_turn, actions_left;    /* whose move it is, and how many strikes/bans are left */
  int32_t stage_mode;               /* 0 competitive (strike the 6 legal), 1 all common stages */
  const fe_stage_id *lobby_stages; const int32_t *lobby_stage_state; int32_t lobby_stage_count;
  fe_lobby_player players[2];
  int32_t countdown_frames;
  int32_t coin_winner_is_me;
} fe_online;
/* Lobby rules (the host enforces them; you display and send actions):
 * Game 1: both pick characters blind (hidden until both lock in); a coin flip decides who strikes
 * first; competitive mode strikes 1-2-2 over the 6 legal stages until one remains; "all stages"
 * mode: coin winner bans 2, the other picks. Game 2+: previous winner bans 2, loser picks the
 * stage, then winner picks a character, then loser. Then both READY -> 3 s countdown -> match ->
 * results -> back to the lobby (same room) for the next game. Leaving is possible at every step. */

/* ---------- host services (host implements; you call) ---------- */
typedef struct fe_host {
  /* graphics */
  WGPUDevice device; WGPUQueue queue;
  /* content */
  int32_t (*fighter_count)(void);
  const fe_fighter *(*fighter_at)(int32_t i);
  int32_t (*stage_count)(void);
  const fe_stage *(*stage_at)(int32_t i);
  /* disc art for display only (may return w=h=0 if unavailable); kinds: "portrait",
   * "icon", "nameplate" for fighters, "preview", "icon", "nameplate" for stages */
  fe_image (*fighter_image)(fe_fighter_id, int32_t costume, const char *kind);
  fe_image (*stage_image)(fe_stage_id, const char *kind);
  /* settings */
  int32_t (*setting_count)(void);
  const fe_setting *(*setting_at)(int32_t i);
  void (*setting_set_value)(const char *key, int32_t value);
  void (*setting_set_text)(const char *key, const char *text);
  /* mods */
  int32_t (*mod_count)(void);
  const fe_mod *(*mod_at)(int32_t i);
  int32_t (*mod_set_enabled)(const char *id, int32_t on);  /* returns number of mods changed */
  /* online */
  const fe_online *(*online)(void);
  /* game state */
  int32_t (*in_match)(void);
  const char *(*build_version)(void);
  /* text entry: while on, the keyboard types instead of acting as a controller */
  void (*text_entry)(int32_t on);
  void (*clipboard_set)(const char *utf8);
  void (*log)(const char *utf8);
} fe_host;

/* ---------- actions (frontend -> host) ---------- */
enum {
  FE_ACT_START_VS_MATCH,      /* uses fe_match_setup below */
  FE_ACT_START_TRAINING,
  FE_ACT_ONLINE_HOST,         /* a = stage_mode */
  FE_ACT_ONLINE_JOIN,         /* s = 4-char code */
  FE_ACT_ONLINE_RANDOM,
  FE_ACT_ONLINE_CANCEL,       /* leave a room / stop searching */
  FE_ACT_LOBBY_PICK_FIGHTER,  /* a = fighter id, b = costume */
  FE_ACT_LOBBY_STRIKE,        /* a = index into lobby_stages */
  FE_ACT_LOBBY_BAN, FE_ACT_LOBBY_PICK_STAGE,
  FE_ACT_LOBBY_READY,         /* a = 1 ready, 0 unready */
  FE_ACT_RESULTS_CONTINUE,
  FE_ACT_QUIT_GAME
};
typedef struct fe_port_setup { int32_t kind; /* 0 off, 1 human, 2 cpu */ int32_t cpu_level;
  fe_fighter_id fighter; int32_t costume; int32_t team; } fe_port_setup;
typedef struct fe_match_setup {
  fe_port_setup ports[4]; fe_stage_id stage;   /* stage may be -1 = random */
  int32_t mode;          /* 0 time, 1 stock */
  int32_t stocks, minutes, items /* 0 off .. 4 very high */, teams, friendly_fire, pause;
  int32_t damage_ratio_pct, handicap;
} fe_match_setup;
typedef struct fe_action { int32_t type; int32_t a, b; const char *s; const fe_match_setup *match; } fe_action;

/* ---------- the frontend (you implement; host calls) ---------- */
typedef struct fe_frame_target { WGPUTextureView view; WGPUTextureFormat format; int32_t w, h;
  int32_t clear;   /* 1 = menu owns the frame, 0 = draw over the game's frame */ } fe_frame_target;
typedef struct fe_ui_state {        /* for automated tests: always current */
  const char *screen;               /* stable id, e.g. "main", "css", "sss", "online.lobby" */
  const char *focus;                /* stable id of the focused element, "" if none */
  int32_t transitioning;            /* 1 while animating between screens (don't send input) */
  int32_t modal_open, text_entry_open;
  int32_t page, page_count;
  struct { int32_t active; float cursor_x, cursor_y; fe_fighter_id hovered, picked; int32_t costume; } css[4];
  fe_stage_id sss_hovered;
} fe_ui_state;

int32_t fe_init(const fe_host *host, const char *data_dir);   /* data_dir: your assets/themes */
void    fe_update(const fe_input *in, int32_t out_action_cap, fe_action *out_actions, int32_t *out_count);
void    fe_render(const fe_frame_target *t, float interp_alpha);   /* may be called > 60 Hz */
void    fe_query_state(fe_ui_state *out);
void    fe_notify(const char *event);  /* host events: "match_ended", "results", "connection_lost", ... */
void    fe_shutdown(void);
```

- **Actions** are queued by `fe_update` and executed by the host after it returns. When the host changes scenes (a match starts, results come in), it calls `fe_notify`. The host decides when the frontend is active.
- **Anything missing:** if you need something the interface doesn't have, add it under a clearly marked PROPOSED section with a reason.

## 5. What we need back

1. **The frontend library:** source for everything behind `fe_api.h`, building with CMake for Windows i686, with no dependencies beyond `webgpu.h` and the permissive libraries you choose (vendored or fetched, with licences).
2. **A mock host app** (`mock/`): a standalone Windows app that creates a window, gets a WebGPU device through Dawn or wgpu-native, and implements `fe_host` with fake data:
   - a roster of ~60 fighters and ~80 stages, with procedurally generated placeholder portraits and previews;
   - a scripted fake online opponent that walks through the full lobby;
   - settings and mods lists.
   - It needs gamepad and keyboard input, and 1 to 4 local players (keyboard plus any connected pads).
   - This is how you, and we, run and judge the UI without the game.
3. **Screens, all working in the mock:**
   - **Boot / title:** press Start.
   - **Main menu:** Versus, Online, Training, Settings, Mods, Data/records, Quit.
   - **VS match setup:** every field of `fe_match_setup`.
   - **Character select:**
     - 4 players at once, each human, CPU (with level) or off;
     - costumes (no duplicate costume on the same fighter), teams, Random;
     - pages or scrolling for 150+ fighters;
     - a player picking for a CPU, name tags, "ready to fight" when all are set.
   - **Stage select:** paging for 150+ stages, Random, lock state, legal-stage filter, previews.
   - **Loading / versus splash** before a match.
   - **Results.**
   - **Online:**
     - Host (with the room code shown big and copied to the clipboard), Join (4-character code entry with paste), and Random (a search timer and cancel);
     - the waiting room;
     - the full lobby: blind picks, coin, strikes and bans on a stage board, ready, countdown;
     - rematch flow, leave at any time;
     - fighters and stages with `available_online == 0` visibly unavailable, with a hint.
   - **Settings:** generated from the `fe_setting` list: every page, and live apply.
   - **Mods:** the list, enable for the next boot, status, and a restart-needed notice.
   - **In-match pause overlay:** optional, but welcome.
4. **Themes, layouts and screens in data files,** with a documented format: a modder can reskin and add a screen or settings page without recompiling.
5. **Tests:**
   - Headless unit tests for navigation and state machines, the CSS rules (costume uniqueness, ready conditions) and the lobby display logic.
   - A scripted walkthrough in the mock that visits every screen by waiting on `fe_query_state()`, never on frame counts, and captures a PNG per screen.
6. **`DESIGN.md`:** your architecture (renderer, scene graph, layout, animation, text, input focus, theming, data formats), your art direction and why, measured frame-time costs, and a list of anything you added to the interface.

## 6. Quality bar
- It should feel faster and more alive than any fighting-game menu players have seen. Responsive to every press within a frame, no dead time, transitions that never block input longer than they have to.
- Crisp text at any resolution (e.g. SDF or MSDF), with full Unicode support for player names.
- Readable from a couch at 3 metres, and usable with only a GameCube controller.
- Accessible: colour is never the only signal, text contrast is high, and flashing is limited.

Now go. Surprise us.
