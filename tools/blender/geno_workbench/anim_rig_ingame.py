"""Play a fighter's jab in the LAB and log where its hand goes, to compare a hand-animated package with the stock one.

    python tools/blender/geno_workbench/anim_rig_ingame.py --fighter goku|falcon --mods MODS_DIR --tag NAME [--visible] [--joint N]
        [--workspace "E:/Projects/Melee Workspace"] [--shots 6,10,14]

MODS_DIR is a mods parent that holds the fighter's mod and geno-lab (copy geno-lab beside it for a stand-alone copy). The run is the
combo tests' pattern: tools/port/run.sh in the workspace, a generated pad script, the LAB (fighter vs an idle Mario on FD).
Prints the HANDPROBE lines (frame, motion, world x y z of the hand joint) and writes <tag>.handprobe.json next to the run log.
--visible runs in real time so gd.screenshot produces PNGs (turbo frames are not presented): MELEE_WINDOW_X/Y=30000 keeps the window
off screen. Needs the disc (GW_ISO_VANILLA in the workspace .env) and the workspace's built exe.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

GIT_BASH = os.environ.get("GW_GIT_BASH", "C:/Program Files/Git/bin/bash.exe")
FIGHTERS = {"goku": ("goku-xv2", "b_L_Hand"), "falcon": ("geno-falcon", "j25")}   # the jab hand of each (Attack11 is a left jab for both)

LUA = """local JOINT = %(joint)d
local TAG = '%(tag)s'
local SHOTS = {%(shots)s}
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 240 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    pcall(gd.teleport, 1, -12, 0); pcall(gd.teleport, 2, 60, 0)
    gd.wait(90)
    gd.input(1, {}, 1); gd.wait(2)
    gd.input(1, {buttons = 'A'}, 2)
    for f = 1, 45 do
      gd.wait(1)
      local p = gd.player(1)
      local j = gd.joints(1)[JOINT + 1]
      gd.log(string.format('HANDPROBE %%s f=%%d motion=%%s x=%%.4f y=%%.4f z=%%.4f', TAG, f, tostring(p.motion_name), j.x, j.y, j.z))
      if SHOTS[f] then gd.screenshot(TAG .. '-f' .. f .. '.png') end
    end
    gd.log('HANDPROBE DONE')
  end)
  if not ok then gd.log('HANDPROBE FAIL ' .. tostring(why)) end
  gd.quit()
end)
"""


def iso(root):
    for line in (Path(root) / ".env").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*(?:export\s+)?GW_ISO_VANILLA\s*=\s*(.+)", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    raise SystemExit("GW_ISO_VANILLA missing from the workspace .env")


def joint_index(mods, key, joint):
    if joint.startswith("j") and joint[1:].isdigit():
        return int(joint[1:])
    plan = json.loads((Path(mods) / key / "files" / "plan.json").read_text(encoding="utf-8"))
    return next(j["index"] for j in plan["joints"] if j["name"] == joint)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fighter", choices=sorted(FIGHTERS), required=True)
    ap.add_argument("--mods", type=Path, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--visible", action="store_true")
    ap.add_argument("--joint", type=int)
    ap.add_argument("--shots", default="4,8,11,14,18")
    ap.add_argument("--workspace", type=Path, default=Path("E:/Projects/Melee Workspace"))
    args = ap.parse_args(argv)
    key, joint = FIGHTERS[args.fighter]
    mods = args.mods.resolve()
    for need in (mods / key, mods / "geno-lab"):
        if not need.is_dir():
            raise SystemExit(f"{need} missing: copy the mod and geno-lab into the mods parent")
    enabled = [e for e in (mods / "enabled.txt").read_text(encoding="utf-8").split() if e] if (mods / "enabled.txt").is_file() else []
    for e in ("geno-lab", key):
        if e not in enabled:
            enabled.append(e)
    (mods / "enabled.txt").write_text("\n".join(enabled) + "\n", encoding="utf-8")
    ji = args.joint if args.joint is not None else joint_index(mods, key, joint)
    ws = args.workspace.resolve()
    run_dir = ws / "_build" / "runs"
    lua = ws / "_build" / f"handprobe-{args.tag}.lua"
    lua.write_text(LUA % {"joint": ji, "tag": args.tag, "shots": ", ".join(f"[{s}] = true" for s in args.shots.split(",")) if args.visible else ""}, encoding="utf-8")
    env = dict(os.environ)
    env.update({"MELEE_MODS_DIR": str(mods), "MELEE_SCENE": f"mode=lab;p1=geno:{key}/hu;p2=mario/cpu0;stage=fd;items=off;time=0",
                "MELEE_UNATTENDED": "1", "MELEE_MAX_SECONDS": "240", "MELEE_LAB_UI": "0", "MELEE_CPU_IDLE": "1",
                "MELEE_WINDOW_X": "30000" if args.visible else "40", "MELEE_WINDOW_Y": "100" if args.visible else "40",
                "MELEE_WINDOW_W": "1280", "MELEE_WINDOW_H": "720", "MELEE_RUN_LABEL": f"hand probe {args.tag}",
                "MELEE_TURBO": "0" if args.visible else "1", "MELEE_PAD_SCRIPT": lua.as_posix()})
    cmd = [GIT_BASH, (ws / "tools/port/run.sh").as_posix()] + (["--realtime"] if args.visible else []) + \
          ["--max-seconds", "240", f"handprobe-{args.tag}", "--iso", iso(ws)]
    out = ws / "_build" / f"handprobe-{args.tag}.run.txt"
    with open(out, "w", encoding="utf-8") as fh:
        subprocess.run(cmd, cwd=ws, env=env, stdout=fh, stderr=subprocess.STDOUT)
    log = run_dir / f"handprobe-{args.tag}" / "melee-pc.log"
    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    rows = []
    for m in re.finditer(r"HANDPROBE (\S+) f=(\d+) motion=(\S+) x=(-?[\d.]+) y=(-?[\d.]+) z=(-?[\d.]+)", text):
        rows.append({"f": int(m.group(2)), "motion": m.group(3), "x": float(m.group(4)), "y": float(m.group(5)), "z": float(m.group(6))})
    done = "HANDPROBE DONE" in text
    (log.parent / f"{args.tag}.handprobe.json").write_text(json.dumps({"tag": args.tag, "joint": ji, "done": done, "rows": rows}, indent=1), encoding="utf-8")
    print(f"HANDPROBE {args.tag}: {len(rows)} frames, done={done}, log {log}")
    for r in rows[:3] + rows[-2:]:
        print(r)
    return 0 if done and rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
