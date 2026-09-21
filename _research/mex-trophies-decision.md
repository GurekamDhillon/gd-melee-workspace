# m-ex trophies 293..341 — decision memo

**Decision needed from GD. Nothing is implemented.** Background: `_research/trophies.md`,
`docs/HANDOFF.md` §1 item 2.

## The problem

Both mod discs ship a `TyDataf.dat` with **342** trophies (ACE's is byte-identical to Akaneia's,
so it's one set, not two); vanilla has 293. The port compiles `TY_TROPHY_COUNT = 293`
(`src/melee/ty/forward.h:4`), and that one constant sizes everything:

* **On-card save data:** `trophy_flags[293]` (`gm/types.h:332`), two `[(293+31)/32]` bitfields
  (`:325`, `:409`) and `times[293]` (`:410`).
* **In-memory only:** `Toy::trophy_flags[293]` / `trophyTable[293]` (`ty/types.h:93,180`), an
  `HSD_MemAlloc(… * TY_TROPHY_COUNT)` in `Toy_Scene_OnEnter`, two 293-entry stack arrays in
  `toy.c:830`, and 40 uses across `toy.c`, `tydisplay.c`, `tyfigupon.c`.

Today every loop is bounded by the constant, so ids 293..341 are simply never visited. They are
invisible, but nothing breaks, and `Toy_SetUnlockState` logs `*** OUT OF RANGE ***` if anything
ever feeds it one. Showing them means widening the on-card arrays, and **that changes the save
format.**

## Options

**A. Keep 293 (status quo).**
No risk and no work. The mod discs' 49 extra trophies stay unobtainable and unseen.

**B. Raise the constant to 342 (or to a disc-derived max) everywhere, save block included.**
It's the simplest diff, but the card layout changes: `trophy_flags` grows 98 bytes, `times` 196,
and each bitfield 8 more bytes, and every later field in those structs moves. Existing port saves
stop loading, or load garbage, unless a migration reads the old layout. A card written by this
build is no longer readable by vanilla Melee or Dolphin-with-vanilla, and it probably doesn't match
what m-ex itself writes on hardware (unverified; m-ex's save handling is in its code patches, not
in `TyDatai.dat`, which it never extended). It also has to fit the fixed save-file size. Check the
slack in the save block before assuming it does.

**C. Split in-memory from on-card (sidecar). Recommended.**
* Size the *in-memory* tables to a compile-time maximum (e.g. 512), bounded at runtime by the
  disc's `tyModelFileTbl` count. That covers the stack arrays, the `HSD_MemAlloc` and the loops.
* Keep the *on-card* struct at exactly 293, byte-for-byte vanilla.
* Store state for ids ≥ 293 (flag, time, bitfield bits) in a small PC-side file next to the card,
  keyed by disc (e.g. `card/mex_trophies_<gameid>.bin`), loaded and saved alongside the card.

That keeps vanilla cards readable both ways, existing port saves keep working, and a vanilla disc
behaves exactly as today because its runtime count is 293. The cost is moderate: one save/load hook
plus the in-memory/on-card split in the ~40 sites. The sidecar is port-only state, so it won't
round-trip to a real GameCube or Dolphin m-ex save.

**D. Match m-ex's own on-card layout.**
Only worth it if importing real Akaneia/ACE memory cards (GCI from Dolphin) is a goal. It needs
reverse-engineering m-ex's save patches first. It could later be layered onto C as an import path.

## Recommendation

**C.** It is the only option that shows the trophies without touching the vanilla save format, and
it fixes the latent overrun class too: the two stack arrays and the alloc stop depending on a
constant the disc can exceed. Before starting, answer one question: does GD want real Akaneia GCI
saves to import? If yes, do D's research first and make the sidecar format follow m-ex's.
