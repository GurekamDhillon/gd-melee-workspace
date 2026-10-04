# Tap jump off: netplay-safe design (2026-10-04)

This dated source review supersedes any earlier suggestion that controller remapping already implements tap jump off. It specifies future work only. No game code changed, build, launch, or gameplay acceptance was performed. References are repository-relative and line numbers describe the reviewed source, which other parallel jobs may change.

## Decision

Build tap jump off as an agreed, immutable **per-player match setting**, with a game-side predicate that gates stick-triggered jump requests while retaining the original stick values and X/Y behavior. Keep physical remapping in its existing local input layer. Store the user's preference in a controls profile, but copy it into the authoritative match configuration before play; simulation must never consult the live local profile.

The existing controls model supports deterministic remapping of physical controls into GameCube pad inputs. It does **not** expose a separate jump action or an independent tap-jump bit. Removing upward stick input can be rollback-safe but cannot implement the intended option while retaining upward aiming, tilts, smashes, movement and other stick semantics. Netplay safety and correct controls behavior are separate requirements.

## Verified current path

| Source | What it establishes |
|---|---|
| `melee/pc/platform/gw_controls_model.h:1`, `:15`, `:24`, `:29` | Destinations are GC inputs, explicitly not fighter actions. `GcMap` contains bindings, swap, analog-off, shield, deadzones and rumble. `GcIntent` contains buttons, four stick bytes and two triggers; neither has tap-jump metadata. |
| `gw_controls_model.h:68` (`gc_map_apply_range`) | Transformation combines physical sources into the GC button/axis values. There is no fighter-state query or jump-intent channel. |
| `gw_controls_model.h:114` (`gc_intent_wire`), `:120` (`gc_map_encode`), `:130` (`gc_map_decode`) | The model's eight-byte helper serializes pad intent, not a jump flag. Profile serialization is version 1 and validates the existing fields. This helper is not the actual online packet encoder. |
| `melee/pc/platform/gw_controls_runtime.inc:161`, `:172`, `:329` | Runtime options expose only the six existing options; profile transforms execute in `ctl_poll`. Inherited deadzone settings are resolved there, before the sample enters gameplay. |
| `melee/pc/platform/shim_pad.c:674` onward (`ctl_poll`, then `gw_Script_PadApply`) | Physical remapping precedes scripted pad overrides. A new physical-only transform would not automatically transform script-generated inputs. |
| `melee/src/sysdolphin/baselib/controller.c:56` (`HSD_PadRenewRawStatus`) | The game calls PADRead, then latches the returned values through `RB_PadLatch` before subsequent processing. |
| `melee/pc/platform/gw_rollback.c:725` (`rb_live_sample`), `:1184` (`rb_prepare`) | Live values are assigned to the delayed frame and stored in the input history. Resimulation uses stored truth/predictions. Sampling skips an already-sampled frame and skips remote slots in real netplay. |
| `gw_rollback.c:700` (`gw_RB_PadGoverned`), `:704` (`gw_RB_PadField`); `controller.c:378` onward | Governed simulation consumes session pad values rather than remapping remote controller devices locally. |
| `melee/pc/platform/gw_rollback.h:55` (`GwRbInput`) | The raw format holds a complete PADStatus-equivalent sample; processed replay fields are also supported. There is no tap-jump field. |
| `melee/pc/platform/gw_netplay.c:154`, `:168` (`np_encode`, `np_decode`) | Online input is eleven bytes: buttons, four stick bytes, analog values and error. Decode marks it raw, present and confirmed. No tap-jump metadata is sent. |
| `gw_netplay.c:189` (`np_build_scene`), `:1885` (`np_start_session`) | Current authoritative scene includes fighters, stage and match rules. No tap-jump setting is emitted. Actual transport uses this scene as its match blob. |
| `melee/pc/platform/gw_net.h:129` onward (`gw_net_config`) | Existing agreement infrastructure has executable/content identities, seed, delay, slot ownership, a host match blob and guest choices. This can carry a future agreed setting; it does not implement it today. |

Paths abbreviated in the table retain the directory of their preceding full reference.

## Approach A: transform before simulation, then exchange the result

For ordinary remapping, the sender transforms its own physical input exactly once before rollback latching/history. Both peers consume the same resulting pad sample for that frame. The receiver must not apply its own controller profile to remote input, and resimulation must not rerun the physical transform using today's profile. Profiles need not be identical: players can use different devices and bindings because agreement is on the canonical resulting input bytes. Both peers still need compatible input interpretation and game rules.

A hypothetical transform that zeros positive stick Y, removes the Stick Up destination, or caps Y below jump thresholds can fit this boundary and avoid a profile-induced desync. It also removes or distorts information used by the rest of the game. Grounded normal and relaxed jump tests use different thresholds (`melee/src/melee/ft/kinds/ftCommon/ftCo_Jump.c:30`, `:63`); a guessed raw-byte clamp does not account for the game's processed stick pipeline and thresholds. This is not an acceptable full tap-jump-off implementation.

An action-level input design could preserve Y and add an independent canonical jump request/permission. That requires new input representation, wire/version agreement, prediction/equality handling, recording/replay support and game consumers. Merely adding a member to `GcMap` or `GcIntent` does not create that channel. A transform that consults current fighter state before sampling would also run before the delayed frame it influences; it cannot stand in for a deterministic jump decision during that frame's simulation.

Thus Approach A is already supported for GC-input remaps, but **not for lossless separation of stick Y from tap jump**. If pursued, both peers must negotiate the new format/semantics before starting, reject unsupported peers, and store the final canonical action metadata with each frame. Historical frames cannot consult mutable local settings.

## Approach B: agreed simulation setting (recommended)

The pad bytes remain unchanged. Add a match-level `tap_jump_enabled[player]` value, default on, and gate only the stick branch of jump requests using that player's agreed value. Different players may choose different values; both peers must agree on the whole vector and its mapping to simulation ports. The host must incorporate the guest's preference rather than silently imposing the host's local controls profile.

The source already demonstrates why this needs more than one hook:

- `ftCo_Jump_GetInput` and `fn_800CAF78` in `ftCo_Jump.c:30` and `:63` handle ordinary and relaxed grounded stick jumps; retain X/Y branches.
- `ft_did_jump` in `ftCo_JumpAerial.c:46` handles aerial jumps, while `ftCo_800D730C` in `ftCo_JumpAerialF1.c:18` has a later repeated-multijump check at `:64` using held X/Y or stick Y. Gating only `ft_did_jump` misses that branch.
- `ftCo_KneeBend.c:50` checks stick release after jump initiation. Preserve short-hop/button release behavior and audit jump-input provenance rather than globally replacing stick Y or timers.
- `ftPeach/ftpeachfloat.c:22`, `:99`, `ftCommon/ftCo_PassiveWall.c:56`, `ftCo_CaptureWaitKirby.c:50` and `ftCo_CaptureWait.c:313` also reference the jump threshold. Their intended behavior needs explicit classification: float activation, wall recovery, and capture escape are not automatically the same controls feature. Do not blanket-gate every threshold reference. C-stick use in `melee/src/melee/ft/ft_0DF1.c:219` is a separate input path, not proof of left-stick tap jump.

This list is a source-audit starting point, not proof that every modded or interpreter-backed fighter path has been covered. Audit fighter extensions and supported m-ex jump behavior before claiming all-roster support.

## Implementation contract

1. Extend profile persistence with a versioned preference and migrate version-1 profiles to tap jump on. Add a clearly named menu option and preview; preserve GC destinations. Profile ownership is device/local port today, so explicitly map preference to match player when selecting the local online player.
2. Carry guest preference through both direct/boot and menu lobby flows; include the final per-player vector in the authoritative scene or a versioned match extension. Validate values and player ownership before arming play. Rebuild it for rematches and clear it on exit. Offline play uses the same match initialization contract. Reject peers that cannot interpret the option instead of silently falling back.
3. Put simulation-readable values in game-owned, snapshot-covered state, initialized before the first match snapshot. Use a per-port query with explicit follower/CPU behavior; followers share their controlling player's option, and legacy/CPU defaults remain on unless a separate rule says otherwise. Native shim settings are not automatically snapshotted: `melee/pc/platform/gw_snap.c:8` documents MEM1 and game-object globals, while shim/runtime state is excluded. A scalar shim accessor is only safe with explicitly captured or proven immutable agreed session state; do not read `settings.cfg` from jump checks.
4. Keep the vector immutable during a match. Change the user's saved preference for a subsequent match; do not alter historical rollback semantics. Record/replay the vector with the initial match configuration. Current raw and processed replay inputs lack it; old recordings default on, and any unsupported export/import format must explicitly reject or preserve the extension rather than claim faithful reproduction.
5. Gate the actual jump requests under the port's game-side boundary rules. Preserve analog Y, UCF raw-byte reads, stick timers, X/Y and non-jump actions. Confirm specialized jump initiation and release paths individually.

## Required future acceptance

Compare identical canonical inputs with on/off settings: grounded jump, relaxed jump, aerial jump, repeated multijump, X/Y jump and short-hop timing. Demonstrate preserved upward tilts/smashes, specials, aerial aiming and other Y-dependent behavior. Specify and test Peach float, wall jump/recovery and capture escape semantics. Test adapter/SDL remaps, player reassignment, followers, CPU defaults, scripted pads and old profiles.

Run two peers with opposite preferences and different device profiles, then delay/jitter/loss and rollback corrections. State hashes must agree after resimulation, including scene transitions and rematches. Attempt incompatible/malformed settings and unsupported peers; they must fail before match start. Rewind and replay must restore identical settings and outcomes, including a recording made with tap jump off. Those are proposed acceptance checks; none ran in this design-only task.
