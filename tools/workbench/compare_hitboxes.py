#!/usr/bin/env python3
"""Cross-check live workbench hitboxes against the installed package.

Build the same fighter package that the running game loads. By default this uses
_build/goku-xv2/author-source/package, including mods/goku-xv2/files/plan.json,
the installed .words scripts and animation bank, and build/mesh_*.json for rest
transforms. --package also accepts the mod directory directly; --mesh overrides
the generated rest mesh. No source assets or ACMD inputs are needed.

Start the game in mode=workbench with MELEE_CONSOLE_PORT=51726 and MELEE_WB_DIR
set to an existing absolute local directory. Keep its window rendering, with
MELEE_TURBO unset. Then, from the workspace root:

    python tools/workbench/compare_hitboxes.py --port 51726 --row dair \
        --motion 70 --frames 6,9 --tol 0.5

--row names the installed overlay's .words basename, or its numeric subaction.
--motion is the engine motion id, which can differ from the subaction id.
The reference uses HP.hitbox_events/HP.live_spheres and HP.sphere evaluated via
HP.pose_matrices. Geno banks use the ground_audit.py/audit_gameplay.py adapter;
Pl/AJ installs use HP.read_installed_words and HP.installed_tree as in
HP.check_install. The latter require a numeric --row and --mesh rest context.

compare() requires only the standard library. The CLI additionally needs the
existing checker's dependencies (including NumPy and SciPy) and gd_prompt.
Positions are compared directly: the workbench fighter's origin, facing, scale
and animation clock must agree with the installed pose. Radius tolerance is
always 0.1 model units; --tol controls centre distance only.
Exit codes: 0 matches, 1 differences, 2 missing files/engine or invalid input.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACKAGE = ROOT / "_build/goku-xv2/author-source/package"


def compare(wb_hits, ref_spheres, tol) -> list[dict]:
    """Compare active workbench spheres by slot, without modifying either input.

    Each result has slot, ok, d and why; d is None when a sphere is missing.
    Inactive workbench slots are absent, so an active reference at that slot is
    reported as missing in wb. Results are ordered by slot.
    """
    if not math.isfinite(tol) or tol < 0:
        raise ValueError("tol must be finite and nonnegative")
    wb = {hit["slot"]: hit for hit in wb_hits if hit["active"]}
    ref = {sphere["slot"]: sphere for sphere in ref_spheres}
    results = []
    for slot in sorted(wb.keys() | ref.keys()):
        if slot not in wb or slot not in ref:
            why = "missing in wb" if slot not in wb else "missing in reference"
            results.append({"slot": slot, "ok": False, "d": None, "why": why})
            continue
        position = tuple(wb[slot]["world"][axis] for axis in "xyz")
        distance = math.dist(position, ref[slot]["pos"])
        radius_delta = abs(wb[slot]["radius"] - ref[slot]["radius"])
        why = []
        if not distance <= tol:
            why.append("position mismatch")
        if not radius_delta <= 0.1:
            why.append("radius mismatch")
        results.append({"slot": slot, "ok": not why, "d": distance,
                        "why": "; ".join(why)})
    return results


def _dependencies():
    # Lazy imports keep the pure tests independent of game sources and SciPy.
    sys.path.insert(0, str(ROOT / "ports/ir/tools"))
    sys.path.insert(0, str(ROOT / "tools/port"))
    import check_hitbox_positions as HP
    from gd_prompt import Console

    class WorkbenchConsole(Console):
        # The shared client's banner loop does not handle EOF. Keep its line API,
        # but bound the handshake and close the socket if the engine disappears.
        def _banner(self):
            deadline = time.monotonic() + self.timeout
            try:
                while b"\n" not in self.buf:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError("timed out waiting for the console banner")
                    self.sock.settimeout(remaining)
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        raise ConnectionError("game closed the socket before its console banner")
                    self.buf += chunk
                line, self.buf = self.buf.split(b"\n", 1)
                return line.decode("utf-8", "replace").rstrip("\r")
            except OSError:
                self.sock.close()
                raise

    return HP, WorkbenchConsole


def _json_file(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _load_reference(HP, package, mod_id, row, motion, mesh_path):
    package = Path(package)
    if (package / "mods").is_dir():
        package = package / "mods" / mod_id
    files = package / "files"
    plan = _json_file(files / "plan.json")
    if mesh_path is None:
        meshes = sorted((package.parent.parent / "build").glob("mesh_*.json"))
        if not meshes:
            raise FileNotFoundError(
                f"no generated rest mesh beside {package}; supply --mesh")
        mesh_path = next((p for p in meshes if p.name == "mesh_hu.json"), meshes[0])
    mesh = _json_file(mesh_path)
    rest = {joint["name"]: (HP.np.asarray(joint["trans"]), None,
                            HP.np.asarray(joint["scale"]), HP.np.asarray(joint["rot"]))
            for joint in mesh["joints"]}
    # Artist synthesized joints have real rest transforms (not identity).
    native = {"joints": [dict(joint, synthesized=False) for joint in plan["joints"]]}

    if "bank" in plan and (package / "geno.json").is_file():
        fighters = _json_file(package / "geno.json")["fighters"]
        candidates = [f for f in fighters if f.get("define", {}).get("key") == mod_id]
        if not candidates and len(fighters) == 1:
            candidates = fighters
        if len(candidates) != 1:
            raise ValueError(f"cannot select fighter {mod_id!r} in {package}")
        fighter = candidates[0]
        overlays = [o for o in fighter.get("subactions", [])
                    if str(o["index"]) == row or Path(o.get("file", "")).stem == row]
        if not overlays:
            raise ValueError(f"no installed overlay for row {row!r} in {package}")
        row_clips = plan["row_clips"]
        clips = {row_clips[o["index"]] for o in overlays}
        motion_clips = {m["clip"] for m in plan.get("motion_rows", [])
                        if m["motion"] == motion and m.get("clip")}
        if len(motion_clips) > 1:
            raise ValueError(f"motion {motion} has ambiguous installed clips")
        if motion_clips:
            clip = next(iter(motion_clips))
            if clip not in clips:
                raise ValueError(f"row {row!r} does not match motion {motion}'s clip {clip!r}")
        elif len(clips) == 1:
            clip = next(iter(clips))
        else:
            raise ValueError(f"row {row!r} selects multiple clips; use a numeric --row")
        if not clip:
            raise ValueError(f"row {row!r} has no installed animation clip")
        overlay = next(o for o in overlays if row_clips[o["index"]] == clip)
        if "file" in overlay:
            text = (package / overlay["file"]).read_text(encoding="utf-8-sig")
            tokens = " ".join(line.split("#", 1)[0] for line in text.splitlines()).split()
            words = [int(token, 16) for token in tokens]
        else:
            words = [int(word, 0) if isinstance(word, str) else word
                     for word in overlay["words"]]
        if not words:
            raise ValueError(f"row {row!r} has an empty installed script")
        # Geno overlays need not end with End; this is the audit_gameplay adapter.
        words = [word & 0xFFFFFFFF for word in words] + [0]
        record = plan["bank"]["clips"][clip]
        archive = (files / plan["bank"]["file"]).read_bytes()
        offset, size = record["offset"], record["bytes"]
        if offset < 0 or size <= 0 or offset + size > len(archive):
            raise ValueError(f"clip {clip!r} is outside the installed animation bank")
        _, tree = HP.F.parse_archive(archive[offset:offset + size])
    else:
        try:
            subaction = int(row)
        except ValueError:
            raise ValueError("Pl/AJ installs require a numeric --row (subaction)") from None
        if subaction < 0:
            raise ValueError("--row subaction must be nonnegative")
        from install_ultimate import Writer
        meta = _json_file(package / "INSTALL.json")
        writer = Writer((files / meta["pl"]).read_bytes())
        symbols = [symbol for symbol, _ in writer.ar.publics if symbol.startswith("ftData")]
        if len(symbols) != 1:
            raise ValueError("installed archive must have exactly one ftData symbol")
        ftdata = writer.ar.public(symbols[0])
        words = HP.read_installed_words(writer, ftdata, subaction)
        archive = (files / (meta["pl"][:-4] + "AJ.dat")).read_bytes()
        _, tree = HP.installed_tree(writer, ftdata, subaction, archive)
    return HP.hitbox_events(words), tree, native, rest


def _reference_spheres(HP, reference, frame):
    events, tree, plan, rest = reference
    pose = HP.pose_matrices(tree, plan, rest, min(frame, tree["frames"]))
    spheres = []
    for words in HP.live_spheres(events, frame):
        position, radius = HP.sphere(words, pose)
        spheres.append({"slot": (words[0] >> 23) & 7,
                        "pos": tuple(float(value) for value in position),
                        "radius": float(radius)})
    return spheres


def _command(console, line, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("timed out waiting for the requested workbench frame")
    console.timeout = remaining
    console.sock.settimeout(remaining)
    output, ok = console.run(line)
    reply = "\n".join(output).strip()
    if not ok:
        raise ValueError(f"engine rejected {line}: {reply or 'console error'}")
    return reply


def _wait_frame(console, motion, frame, timeout):
    deadline = time.monotonic() + timeout
    reply = _command(console, f"= wb.frame({{motion={motion}, frame={frame}}})", deadline)
    if reply != "pending" and not reply.startswith("@"):
        raise ValueError(f"unexpected wb.frame reply: {reply!r}")
    last = "no frame payload"
    while time.monotonic() < deadline:
        reply = _command(console, "= wb.frame_info()", deadline)
        if reply == "pending":
            last = "engine still pending"
        elif reply.startswith("@") and reply[1:].strip():
            path = Path(reply[1:].strip())
            try:
                info = _json_file(path)
            except FileNotFoundError:
                last = f"payload file is missing: {path}"
            else:
                if not isinstance(info, dict):
                    raise ValueError(f"invalid frame JSON in {path}: expected an object")
                if info.get("frame") == frame and info.get("motion") == motion:
                    if not isinstance(info.get("hitboxes"), list):
                        raise ValueError(f"invalid frame JSON in {path}: hitboxes must be a list")
                    return info
                last = f"received motion={info.get('motion')} frame={info.get('frame')}"
        else:
            raise ValueError(f"unexpected wb.frame_info reply: {reply!r}")
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(0.05, remaining))
    raise TimeoutError(
        f"wb.frame_info did not reach motion={motion} frame={frame} "
        f"within {timeout:g}s ({last})")


def _frames(text):
    try:
        frames = [int(value.strip()) for value in text.split(",")]
    except ValueError:
        raise argparse.ArgumentTypeError("--frames needs comma-separated integers") from None
    if not frames or any(frame < 0 for frame in frames):
        raise argparse.ArgumentTypeError("--frames must be nonnegative")
    return frames


def _position(values):
    if values is None:
        return "-"
    return "(" + ",".join(f"{value:.3f}" for value in values) + ")"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=51726)
    parser.add_argument("--row", required=True)
    parser.add_argument("--motion", type=int, required=True)
    parser.add_argument("--frames", type=_frames, required=True)
    parser.add_argument("--tol", type=float, default=0.5)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--mod-id", default="goku-xv2")
    parser.add_argument("--mesh", type=Path, help="generated mesh JSON for rest transforms")
    parser.add_argument("--timeout", type=float, default=5.0, help="seconds per requested frame")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.motion < 0:
        parser.error("--motion must be nonnegative")
    if not math.isfinite(args.tol) or args.tol < 0:
        parser.error("--tol must be finite and nonnegative")
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and positive")

    console = None
    try:
        HP, Console = _dependencies()
        reference = _load_reference(
            HP, args.package, args.mod_id, args.row, args.motion, args.mesh)
        try:
            console = Console("127.0.0.1", args.port, timeout=args.timeout)
        except OSError as error:
            raise ConnectionError(
                f"cannot connect to game console at 127.0.0.1:{args.port}; "
                f"start workbench mode with MELEE_CONSOLE_PORT={args.port} "
                f"and keep the window rendering ({error})") from None
        different, checked = False, 0
        for frame in args.frames:
            info = _wait_frame(console, args.motion, frame, args.timeout)
            ref = _reference_spheres(HP, reference, frame)
            wb = {hit["slot"]: hit for hit in info["hitboxes"] if hit["active"]}
            spheres = {sphere["slot"]: sphere for sphere in ref}
            for result in compare(info["hitboxes"], ref, args.tol):
                slot = result["slot"]
                hit = wb.get(slot)
                centre = tuple(hit["world"][axis] for axis in "xyz") if hit else None
                ref_hit = spheres.get(slot)
                ref_centre = ref_hit["pos"] if ref_hit else None
                distance = f"{result['d']:.2f}" if result["d"] is not None else "n/a"
                status = "OK" if result["ok"] else "DIFF"
                why = f" why={result['why']}" if result["why"] else ""
                print(f"{status} frame={frame} slot={slot} wb={_position(centre)} "
                      f"ref={_position(ref_centre)} d={distance}{why}")
                checked += 1
                different |= not result["ok"]
        if not checked:
            raise ValueError("no active hitboxes on either side at the requested frames")
        return 1 if different else 0
    except (OSError, ValueError, TypeError, KeyError, IndexError, ImportError) as error:
        print(f"compare_hitboxes: {error}", file=sys.stderr)
        return 2
    finally:
        if console is not None:
            console.sock.close()


if __name__ == "__main__":
    sys.exit(main())
