"""Row sweep: pose every row of a Workbench project in the real engine and report which ones the engine refuses
or dies on, then check that a dead engine recovers (engine_restart, then the next row).

    python tools/blender/geno_workbench/engine_check/sweep_rows.py --project <dir> --mods <dir> \
        --engine <melee-pc.exe> --work <dir> [--rows a,b] [--frames 1,5] [--expect-refused rebirth,rebirth_wait] [--recover]

Per row: load_row, then set_frame at each --frames. Outcomes: ok / refused (the engine answered with an error and
stayed alive) / DEAD (the engine process went away: that is a PANIC and fails the sweep). After a DEAD row the engine
is restarted with engine_restart so the sweep continues (and so the restart path is exercised).
Exit 0 only when no row is DEAD and every --expect-refused row was refused.
--recover: first load a refused/crashing row, then the wait row, and fail unless the session still works.
Windows only; the engine runs headless (MELEE_WB_HEADLESS=1), no window.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import client  # noqa: E402
import launch  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--mods", required=True)
    ap.add_argument("--engine", required=True, help="melee-pc.exe to run (copied into --work/engine)")
    ap.add_argument("--work", required=True)
    ap.add_argument("--rows", default="")
    ap.add_argument("--frames", default="1,5")
    ap.add_argument("--expect-refused", default="")
    ap.add_argument("--recover", action="store_true")
    ap.add_argument("--wait-row", default="wait")
    args = ap.parse_args(argv)
    import shutil
    root = Path(__file__).resolve().parents[4]
    paths = launch.tool_paths(root=root)
    work = Path(args.work)
    (work / "engine").mkdir(parents=True, exist_ok=True)
    (work / "payloads").mkdir(parents=True, exist_ok=True)
    engine = work / "engine" / "melee-pc.exe"
    src = Path(args.engine)
    if src.resolve() != engine.resolve():
        shutil.copy2(src, engine)
    for dll in ("SDL3.dll", "webgpu_dawn.dll"):
        for cand in [src.parent / dll] + sorted(src.parent.glob("runs/*/" + dll)):
            if cand.is_file():
                if not (engine.parent / dll).exists():
                    shutil.copy2(cand, engine.parent / dll)
                break
    argv_s, env = launch.serve_launch(paths["GW_LAUNCHER"], args.project, engine_exe=str(engine), mods_dir=args.mods,
                                      iso=paths["GW_ISO_VANILLA"], headless=True, env=paths, root=root)
    argv_s[argv_s.index("--wb-dir") + 1] = str(work / "payloads")
    proc, port = launch.start_serve(argv_s, timeout=120, env=env)
    print("WB_SERVE port=%d engine=%s" % (port, engine))
    failed = []
    try:
        c = client.McpClient(port=port, timeout=60.0)
        c.connect()
        rows = [r["name"] for r in c.call("list_rows")["rows"]]
        wanted = [r for r in args.rows.split(",") if r] or rows
        frames = [int(f) for f in args.frames.split(",") if f]
        expect = {r for r in args.expect_refused.split(",") if r}

        def alive():
            return c.call("engine_status").get("status") == "ready"

        def recover():
            c.call("engine_restart", timeout=120.0)
            if not alive():
                raise RuntimeError("engine_restart did not bring the engine back")

        results = {}
        for row in wanted:
            outcome = "ok"
            try:
                c.call("load_row", {"row": row})
                for f in frames:
                    c.call("set_frame", {"frame": f})
            except Exception as exc:  # WbError or a dropped connection
                outcome = ("refused: %s" % exc) if alive() else ("DEAD: %s" % exc)
            if not alive():
                outcome = outcome if outcome.startswith("DEAD") else "DEAD (" + outcome + ")"
                try:
                    recover()
                except Exception as exc:
                    outcome += "; RECOVERY FAILED: %s" % exc
                    failed.append(row)
            results[row] = outcome
            print("%-28s %s" % (row, outcome[:160]), flush=True)
        dead = [r for r, o in results.items() if o.startswith("DEAD")]
        failed += [r for r in dead if r not in failed]
        for row in expect:
            if not results.get(row, "").startswith("refused"):
                failed.append(row)
                print("EXPECTED refused but got: %s -> %s" % (row, results.get(row)))
        if args.recover:
            bad = next(iter(expect), wanted[0])
            try:
                c.call("load_row", {"row": bad})
            except Exception as exc:
                print("recover: %s -> %s" % (bad, str(exc)[:100]))
            if not alive():
                recover()
            c.call("load_row", {"row": args.wait_row})
            c.call("set_frame", {"frame": 5})
            print("recover: %s loads after %s: OK" % (args.wait_row, bad))
        print("SWEEP rows=%d refused=%d dead=%d failed=%s" % (
            len(results), sum(o.startswith("refused") for o in results.values()), len(dead), sorted(set(failed))))
    finally:
        launch._stop_process(proc)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
