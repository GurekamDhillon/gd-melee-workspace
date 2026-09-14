# Replay-diff harness

Turns "play until it crashes" into a bisect. Given a real Slippi replay and the port's per-frame
state trace, it reports the **first frame and field** where the port diverges from Dolphin. That is
the tool for hunting the GC-layout alias-view class (`docs/DEVLOG.md` §16): a wrong-memory read shows
up as a specific frame where an action state or position goes wrong, not as a later crash.

The methodology is adapted from Hero88go/melee-unlocked's `tools/replay_compare.py` (GPL-2.0-or-later);
the `.slp` reader here keeps that project's validated raw-block offsets. Unlike theirs, this differ
also reports **missing frames and players**, so a replay that the port terminates early is caught
instead of silently accepted.

## What is compared

Per `(frame, (player, follower))`, the first differing post-frame field among:

```
action_state, x, y, facing, percent, stocks, char
```

The recording's frames and the port trace's frames are intersected; frames the recording has but the
port does not are reported as `missing_frames`.

## Files

| File | Role |
|---|---|
| `slp.py` | `.slp` reader → per-frame pre-frame inputs and post-frame state |
| `trace.py` | reads the port's `MELEE_STATE_TRACE` CSV in the same shape |
| `diff.py` | frame-exact comparison, first divergence, missing frames/players |
| `replay_compare.py` | CLI: `replay_compare.py original.slp port-trace.csv` |
| `test_diff.py`, `test_trace.py` | unit tests (`python3 tools/replay/test_diff.py`) |

## Port side (to implement)

The harness needs the port to emit a per-frame trace and to consume replay inputs. Proposed,
matching the existing shim conventions in `pc/platform`:

- `MELEE_STATE_TRACE=<csv>` — in `gw_frame_tick` (after the game has advanced one frame), write one
  CSV row per player:
  `frame,player,follower,char,action_state,x,y,facing,percent,stocks`.
  Read the fields from the game's player structs through the `gw_r*` accessors — the same source the
  Slippi post-frame is derived from — so the two sides encode the same values.
- `MELEE_REPLAY_SCRIPT=<csv>` — frame-indexed controller input
  (`frame,player,stick_x,stick_y,cstick_x,cstick_y,trigger,buttons`), fed through `PADRead` exactly
  like `MELEE_PAD_SCRIPT` (`shim_pad.c`), so the game sees replay inputs as real pad state.

### Prerequisite: deterministic time

The port's virtual clock and field pacing are wall-clock based (`shim_vi.c`: `gw_time_ticks`,
`gw_pace_field`, `Sleep(1)`), and alarms/audio advance on real time. A frame-exact replay needs the
clock to be a function of the retrace count for the duration of a replay. This is the first port-side
change; without it the run is not reproducible and every diff is noise.

## Status

- [x] `.slp` reader, trace reader, differ, CLI, unit tests.
- [ ] Port-side `MELEE_STATE_TRACE` / `MELEE_REPLAY_SCRIPT` and retrace-driven time.
- [ ] Validated against a real `.slp` fixture (none in-tree yet).
