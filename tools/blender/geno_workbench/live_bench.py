"""Live playback benchmark, run inside an interactive Blender after bootstrap.py (R4).

Set GW_WB_DRIVER to this file's path; bootstrap.py runs it from a timer once the fighter is loaded.
Environment:
  GW_WB_BENCH_ROWS   comma list of engine rows to play (default "dair,jab1")
  GW_WB_BENCH_SECONDS  playback length per row (default 10)
  GW_WB_BENCH_OUT    JSON results file (default <tempdir>/geno_wb_bench.json)
  GW_WB_BENCH_QUIT   1: quit Blender when finished
  GW_WB_BENCH_SHOT   path: save a Blender screenshot of the window mid-playback (needs --enable-event-simulate)

For each row it (1) loads it and waits for the frame cache (when the add-on has one), (2) steps 60 frames
with perf_counter around pose apply and overlay update, (3) plays through the real geno_wb.play operator for the
requested time while a 4 ms heartbeat timer records the longest main-thread gap (the stall). It uses only
public add-on entry points, so it also runs against an older add-on to give "before" numbers.
"""

import json
import os
import statistics
import tempfile
import time

import bpy


def _stats(values):
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    return {
        "n": len(values),
        "mean_ms": round(statistics.fmean(values), 3),
        "p95_ms": round(ordered[int(0.95 * (len(ordered) - 1))], 3),
        "max_ms": round(ordered[-1], 3),
    }


def _equivalence(session, pose, frame):
    """Largest difference between the armature-space bone matrices of the closed-form pose and Blender's own."""
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.pose)
    shots = {}
    for mode in ("fast", "slow"):
        if mode == "slow":
            pose._FAST[arm.name] = (len(arm.pose.bones), arm.data, False)
        else:
            pose._FAST.pop(arm.name, None)
        session.set_frame(frame)
        bpy.context.view_layer.update()
        shots[mode] = {b.name: [v for row in b.matrix for v in row] for b in arm.pose.bones}
    pose._FAST.pop(arm.name, None)
    worst = max(abs(x - y) for n in shots["fast"] for x, y in zip(shots["fast"][n], shots["slow"][n]))
    return {"frame": frame, "bones": len(shots["fast"]), "max_abs_diff": worst,
            "fast_path_used": bool(pose._fast_ok(arm))}


def run():
    from geno_workbench import api, operators, operators_fighter, overlays, pose

    session = api.session()
    rows = [r for r in os.environ.get("GW_WB_BENCH_ROWS", "dair,jab1").split(",") if r]
    seconds = float(os.environ.get("GW_WB_BENCH_SECONDS", "10"))
    out_path = os.environ.get("GW_WB_BENCH_OUT") or os.path.join(tempfile.gettempdir(), "geno_wb_bench.json")
    if os.environ.get("GW_WB_BENCH_FPS"):
        bpy.context.scene.render.fps = int(os.environ["GW_WB_BENCH_FPS"])
        bpy.context.scene.render.fps_base = 1.0
    results = {"addon_has_cache": hasattr(session, "cache"), "blender": bpy.app.version_string, "rows": {}}

    samples = {"pose": [], "overlay": [], "geom": [], "show": [], "frames": 0}

    def timed(owner, name, key):
        original = getattr(owner, name)

        def wrapper(*args, **kwargs):
            started = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                samples[key].append((time.perf_counter() - started) * 1000)

        setattr(owner, name, wrapper)
        return lambda: setattr(owner, name, original)

    undo = [
        timed(pose, "apply_frame", "pose"),
        timed(overlays, "update", "overlay"),
        timed(overlays.shapes, "overlay_geometry", "geom"),
        timed(operators_fighter, "_show_frame", "show"),
    ]

    def count_frame(_session):
        samples["frames"] += 1

    session.on_frame.append(count_frame)

    bpy.context.scene.geno_wb.loop = True   # short moves (jab1 is 5 frames) must keep playing for the whole run

    def window_context():
        window = bpy.context.window_manager.windows[0]
        area = next(a for a in window.screen.areas if a.type == "VIEW_3D")
        region = next(r for r in area.regions if r.type == "WINDOW")
        return bpy.context.temp_override(window=window, area=area, region=region)

    def frame_view():
        """Frame the fighter in the 3D view so a screenshot shows him (best effort)."""
        try:
            with window_context():
                bpy.ops.object.select_all(action="DESELECT")
                for obj in bpy.data.objects:
                    if obj.type in {"MESH", "ARMATURE"} and not obj.name.startswith("GenoWB"):
                        obj.select_set(True)
                bpy.ops.view3d.view_selected()
                bpy.ops.object.select_all(action="DESELECT")
        except Exception as exc:  # noqa: BLE001
            print("GENO_WB_BENCH frame_view_warning %s" % exc)

    beat = {"last": time.perf_counter(), "max": 0.0, "gaps": [], "on": False}

    def heartbeat():
        now = time.perf_counter()
        if beat["on"]:
            gap = (now - beat["last"]) * 1000
            beat["gaps"].append(gap)
            beat["max"] = max(beat["max"], gap)
        beat["last"] = now
        return 0.004

    bpy.app.timers.register(heartbeat, first_interval=0.004)

    def wait(seconds_, predicate=None):
        end = time.monotonic() + seconds_
        while time.monotonic() < end and not (predicate and predicate()):
            yield 0.02

    def script():
        for row in rows:
            entry = results["rows"][row] = {}
            for key in samples:
                samples[key] = [] if key != "frames" else 0
            started = time.perf_counter()
            if bpy.ops.geno_wb.load_row(row=row) != {"FINISHED"}:
                entry["error"] = session.last_error
                continue
            entry["load_row_s"] = round(time.perf_counter() - started, 2)
            if hasattr(session, "cache"):
                started = time.perf_counter()
                yield from wait(120, session.cache_ready)
                entry["cache_ready_s"] = round(time.perf_counter() - started, 2)
                entry["cache_frames"] = session.cache.progress()[0]
            total = session.row_frames() or 30
            entry["row_frames"] = total
            if hasattr(pose, "_fast_ok") and "pose_equivalence" not in results:
                results["pose_equivalence"] = _equivalence(session, pose, min(total, 10))
            # (2) step through the move: per-frame cost of the cache/engine read plus pose plus overlays
            for key in samples:
                samples[key] = [] if key != "frames" else 0
            step_ms = []
            for n in list(range(1, min(total, 60) + 1)):
                t0 = time.perf_counter()
                session.set_frame(n)
                step_ms.append((time.perf_counter() - t0) * 1000)
                yield 0.0
            entry["step_total"] = _stats(step_ms)
            entry["step_pose"] = _stats(samples["pose"])
            entry["step_overlay"] = _stats(samples["overlay"])
            if os.environ.get("GW_WB_BENCH_PROFILE"):
                import cProfile, io, pstats
                prof = cProfile.Profile()
                prof.enable()
                for n in list(range(1, total + 1)) * 6:
                    session.set_frame(n)
                prof.disable()
                text = io.StringIO()
                pstats.Stats(prof, stream=text).sort_stats("tottime").print_stats(14)
                for line in text.getvalue().splitlines():
                    print("GENO_WB_PROF " + line[:170])
            # (3) real playback through the operator
            for key in samples:
                samples[key] = [] if key != "frames" else 0
            session.set_frame(1)
            frame_view()
            yield 0.5
            beat.update(last=time.perf_counter(), max=0.0, gaps=[], on=True)
            with window_context():
                bpy.ops.geno_wb.play()
            began = time.monotonic()
            print("GENO_WB_PLAYING %s" % row, flush=True)
            shot = os.environ.get("GW_WB_BENCH_SHOT")
            shot_done = not shot
            while time.monotonic() - began < seconds:
                if not shot_done and time.monotonic() - began > seconds / 2:
                    shot_done = True
                    try:
                        with window_context():
                            bpy.ops.screen.screenshot(filepath=shot.replace(".png", "_%s.png" % row))
                    except Exception as exc:  # screenshot is a bonus
                        entry["shot_error"] = str(exc)
                yield 0.02
            elapsed = time.monotonic() - began
            beat["on"] = False
            operators.stop_playback()
            entry["status_after"] = session.status
            entry["play_seconds"] = round(elapsed, 2)
            entry["frames_shown"] = samples["frames"]
            entry["achieved_fps"] = round(samples["frames"] / elapsed, 1)
            entry["scene_fps"] = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
            entry["play_show"] = _stats(samples["show"])
            entry["play_pose"] = _stats(samples["pose"])
            entry["play_overlay"] = _stats(samples["overlay"])
            entry["play_overlay_geometry"] = _stats(samples["geom"])
            entry["max_stall_ms"] = round(beat["max"], 1)
            gaps = sorted(beat["gaps"])
            entry["stall_p99_ms"] = round(gaps[int(0.99 * (len(gaps) - 1))], 1) if gaps else 0
            entry["engine_calls_during_run"] = getattr(session, "engine_calls", None)
            entry["play_stats"] = dict(getattr(operators, "PLAY_STATS", {}))
            print("GENO_WB_BENCH %s %s" % (row, json.dumps(entry)))
            yield 0.5
        for restore in undo:
            restore()
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(results, handle, indent=1)
        print("GENO_WB_BENCH done %s" % out_path)
        if os.environ.get("GW_WB_BENCH_QUIT"):
            bpy.ops.wm.quit_blender()

    steps = script()

    def tick():
        try:
            return next(steps)
        except StopIteration:
            return None
        except Exception as exc:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            results["error"] = str(exc)
            with open(out_path, "w", encoding="utf-8") as handle:
                json.dump(results, handle, indent=1)
            return None

    bpy.app.timers.register(tick, first_interval=0.5)


run()
