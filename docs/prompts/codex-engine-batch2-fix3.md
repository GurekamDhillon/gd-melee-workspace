# Packet F follow-up 3: Zelda in stand mode still transforms (2026-10-03)

Same rules. Your fix made both halves report CPU kind 0 and a stood Zelda held position for 600 frames, and through a
forced transform. But the tester still sees the stood Zelda/Sheik perform a transform about 700 frames after
`gd.cpu_mode(port,"stand")` (actions 355/362), with or without bench/call (control run without bench: a transform at about
frame 720). So something other than the partner's CPU kind triggers it: find what makes a kind-0 Zelda use down special
(a CPU routine keyed on time or on character that runs even in the stand kind; a timer in the CPU struct that our stand
mode does not reset; the Sheik/Zelda auto-transform logic for CPU players), and make "stand" mean no inputs at all for
every character, with a fixture. Also from another lane: `gd.cpu_mode(port,"stand")` called on the very first frame of a
match does not stick (the CPU's own initialisation overwrites it; called at frame 2 or later it holds): make it stick or
queue it until the fighter is ready.
Reply with the causes in two lines each; `_build/tmp/codex-engine-batch2-fix3-report.md`.
