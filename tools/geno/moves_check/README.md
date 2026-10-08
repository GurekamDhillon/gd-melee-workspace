# moves_check: move-by-move and whole-mode checks of a Geno define fighter

Headless (turbo, offscreen window, muted), vanilla disc, one game per run. Needs the game worktree built
(`tools/port/build.sh`), `GW_MELEE`, `GW_BUILD_ROOT`, and for the Courier its built files in `files/`
(`tools/geno/build_courier.sh --install`).

    bash tools/geno/moves_check/make_mods.sh "$GW_BUILD_ROOT/mods"            # geno-lab + the two fixtures + enabled.txt
    export MELEE_MODS_DIR="$GW_BUILD_ROOT/mods"
    bash tools/geno/moves_check/run_moves_check.sh mc-courier vanilla-courier 300
    GW_MELEE=... python -m tools.geno.moves_check.moves_report \
        "$GW_MELEE/pc/geno/mods/vanilla-courier" "$GW_BUILD_ROOT/runs/mc-courier/melee-pc.log"

`moves_check.lua` (a `MELEE_PAD_SCRIPT`) runs 40 scenarios in the LAB against a standing Mario: every jab, tilt, smash,
aerial, grab, pummel, throw and special (ground and air), the landing lag of each aerial, and the counter inside and outside
its window. Each move is run twice from one saved state: once on an empty stage (live hitboxes per action frame) and once with
Mario put on the first live hitbox (does it connect, damage dealt, his state, the launch). `moves_report.py` joins the
`MOVECHK` log lines with the declared data (`tools.geno.report`: damage, angle, growth, base knockback, size, start frame
with the rate and the N-2 readout offset of geno.md 22, throw and pummel damage, the landing attributes, the declared attributes
read back through `gd.attrs`) and prints works / wrong / crashes per move. A tolerance of 1 frame at rate 1.0 and 2 frames
at any other rate is used for the start frame.

`drive.lua` + `run_drive.sh` run a whole mode with the fighter as P1: `win` flies P1 with the debug cursor so each stage or
match ends (the fighter's own moves are moves_check's job), `lose` leaves P1 standing so the CPU takes its stocks.
    bash tools/geno/moves_check/run_drive.sh vs-win-courier win 300 "mode=vs;stage=fd;p1=geno:vanilla-courier/hu;p2=mario/cpu0;stocks=1"
    bash tools/geno/moves_check/run_drive.sh classic-courier win 1500 "mode=classic;p1=geno:vanilla-courier/stocks3;difficulty=2"
Then read the run's `melee-pc.log` (`DRIVE` lines, `assert`, `PANIC`, `interpreter attempts`, `crashlogs/`).
