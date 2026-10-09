# falcon_parity: retail Captain Falcon against the standalone Geno Falcon

Proof that a `base: "none"`, `template: "captain"` define built from the disc plays like retail (game `docs/geno.md` 22.10). Local only: the package and every trace are disc-derived.

    # 1. the disc files (once)
    python tools/gc_extract.py "$GW_ISO_VANILLA" _build/falcon-geno/disc --only PlCa
    python tools/gc_extract.py "$GW_ISO_VANILLA" _build/falcon-geno/disc --only PlCo
    # 2. the package (GW_MELEE = the game checkout)
    python ports/ir/tools/retail_define.py captain --disc-dir _build/falcon-geno/disc --out _build/falcon-geno/geno-falcon
    python -m tools.geno.check _build/falcon-geno/geno-falcon
    # 3. a mods folder with geno-lab and the package, enabled.txt listing both, MELEE_MODS_DIR naming it (a Windows path)
    # 4. the two traces, then the diff
    bash tools/geno/falcon_parity/run_parity.sh par_retail captain all
    bash tools/geno/falcon_parity/run_parity.sh par_geno   geno:geno-falcon all
    python tools/geno/falcon_parity/parity_diff.py $GW_BUILD_ROOT/runs/par_retail/parity.txt $GW_BUILD_ROOT/runs/par_geno/parity.txt
    # one scenario with every hurtbox capsule: run_parity.sh <run> <token> <name,name> detail ; parity_diff.py ... --show <name>

`run_parity.sh` sets `MELEE_LOG=all,-render,...` (the log guard drops a prefix after 400 lines per 10 s, which silently truncated the first trace) and honours `MELEE_WINDOW_X/Y` (default
off screen; set them to watch, e.g. 700 / 40). Scenarios are in `falcon_parity.lua` (add one with `add(name, setup, steps)`); `ONLY` picks a subset. Every line carries the RNG seed:
if two runs part ways there first, `MELEE_RAND_TRACE=<file>` on both names the consumer (`melee-pc.map` resolves the caller). The mutation check that the package is live: edit an
attribute or a `.words` timer in the mods copy and the diff must report it.
