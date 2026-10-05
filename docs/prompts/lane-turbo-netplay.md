# Lane packet: Turbo mode, native and netplay-safe, with a private-lobby toggle (2026-10-04)

For an engine lane that can build and run the game. One engine writer at a time: start only when no other lane is
editing engine source. Read `CLAUDE.md`, `melee/CLAUDE.md`, `melee/pc/platform/CLAUDE.md`, `docs/TERMINOLOGY.md`,
`_research/turbo-mode-projectm-2026-10-04.md` (what Turbo is in Project M / Project+, the rules they tightened, where it
hooks in Melee: read all of it), `docs/scripting.md` on netplay and rollback, and the netplay sources
(`melee/pc/platform/gw_netplay.c`, `gw_rollback.c`, `gw_net.c`, the lobby in `melee/src/melee/gm/gmfrontend*.inc`).

## The owner (verbatim)
"Needs to be netplay safe (Our netcode, not slippi.) I want a toggle exposed for people making private lobbies online
with their friends to play with"

So Turbo is a MATCH RULE of the port's own online play, not a script effect: scripts may not write gameplay during
netplay, and a rule both players must share cannot live in one player's mod. It is also wanted later as a keystone in
the offline loot layer: build the native mechanism once and let both use it.

## Build
1. **A native "interrupt window" mechanism in the simulation.** Per fighter, in game memory covered by the rollback
   snapshot: a turbo window (frames remaining), the identity of the move that granted it (for the repeat guard), and
   the exits it allows. When a fighter's attack connects (fighter hit `ft/ftcoll.c` ~784, item/projectile hit ~1464,
   and optionally a shield hit: a rule option) the window opens; while it is open, the fighter's current action is
   interruptible through a widened exit list at the point the per-action interrupt callback runs (`fp->input_cb`,
   `ft/fighter.c` ~2712; gated by `fp->allow_interrupt`, `types.h` ~1719), subject to the rules below. Everything is
   decided inside the simulation from simulation state, in a fixed order: no host time, no Lua, no per-peer data.
   Decide and document: whether the window can be used during hitlag (retail skips the input callback in hitlag,
   `fighter.c` ~2709); what happens to the move's remaining hitboxes on a cancel; landing lag.
2. **The first rule set** (from what Project M learned: start strict, loosen by play): a move cannot cancel into itself
   (use the attack identity the engine already tracks, `x2068_attackID` / `x206C_attack_instance`; smash startup, charge
   and release are one move; multi-hit moves count as one); only jabs and dash attacks may cancel into a dash; smashes
   may not cancel into crouch, jump or dash; grounded attacks may not cancel into shield; aerials and specials may not
   cancel into air dodge; landing a hit in the air restores air jumps; throws do not grant it; the window is short
   (state the frames) and is consumed by the first cancel. Each rule is a bit in ONE rule word so variants are data.
   Add an indicator a player can read (a brief flash or aura on the fighter while the window is open, using the game's
   own colour overlay so it is deterministic and costs nothing).
3. **A match rule, agreed by both peers.** Add Turbo (off / on, and the rule word for future variants) to the port's
   online match settings: where the lobby already carries shared settings (delay, stage mode: `Netplay_SetStageMode`,
   the settings in `gmfrontend_settings.inc`), in the handshake so both sides start with identical rules or the match
   is refused with a clear message, in whatever the port records for replays and crash reports, and in the protocol
   version if the wire format changes (say what an older client sees). Only the lobby host of a PRIVATE lobby can set
   it; it is shown to the guest before they ready up; public/ranked matchmaking never enables it.
4. **The toggle in the menus**: in the private-lobby screen (and for local Versus as a rule under the existing rules
   or special-mode path, so friends on one machine can use it too), built from the existing menu kit, with a one-line
   description. Persisted in `settings.cfg` for the host's next lobby.
5. **Proof of netplay safety**: the rollback/SyncTest path (`gd.rewind_test`, the SyncTest compare, the local two-client
   netplay scripts under `_build/` and `tools/netplay/`) with Turbo ON: zero desyncs over long scripted matches with
   heavy cancelling, rollbacks forced across the frame a window opens, is used and expires; a mismatch (one side on,
   one off) is refused at the handshake, not discovered mid-match. Native suite tests for the rule word, the repeat
   guard, each exclusion, snapshot exactness.
6. **For the offline loot layer**: expose the same mechanism to scripts offline only (`gd.fighter_interrupt(port,
   {frames=, exits=, guard=})` or as a fighter capability), so a keystone or a technique ability can open a window
   (the held feature packet `docs/prompts/codex-earned-states-crits-held.md` wants "wavedash into super armour"-style
   abilities). Do not build modifiers here: report the data a modifier would need.
Credit: Project M / Project+ Turbo (the Project M Development Team, the Project+ team; source consulted at
github.com/Fracture17/ProjectMCodes) and UnclePunch's Melee turbo code for 20XX as prior art: add to `CREDITS.md` in the
same change. Ideas only; no code copied.
Report: the rule set as built, file:line, the handshake and version behaviour, the SyncTest evidence, how to enable it
in a private lobby and in local Versus, and a play script for the owner and a friend.
