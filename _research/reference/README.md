# Third-party reference material

Files here are read, not built. Nothing in this directory is referenced by any
build script, and none of it is linked into `melee-pc.exe`.

## FloatUtils.cpp

Verbatim copy of Dolphin Emulator's `Common/FloatUtils.cpp`, kept because it is
the clearest available statement of the Gekko `frsqrte` and `fres` estimate
tables and of the algorithm around them.

**Licence: GPL-2.0-or-later** (header intact).

This matters, because `melee/pc/gameworld/gekko_fp.c` was written by reading it
and reproduces the same 32-entry base/decrement tables. Before the port is
published, decide explicitly whether `gekko_fp.c` is a derivative work:

- The tables themselves are hardware behaviour transcribed from the Gekko/Broadway
  specification, which is a fact about the CPU rather than Dolphin's creative
  expression, and other projects treat them that way.
- The surrounding normalisation and special-case logic is closer to a
  transcription of Dolphin's implementation and is the part that would carry the
  licence if any of it does.

Either add the attribution GPL-2.0 requires, or re-derive `gekko_fp.c` from the
CPU documentation without reference to this file. Do not leave it undecided:
the decomp itself already sits in a delicate legal position and an unlabelled
GPL derivative inside it makes that materially worse.
