import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine_check"))
import compare_probe as C


def log_for(art, base, facing=1):
    import projectiles as P
    pts = P.trajectory(art, base=base, facing=facing)
    out = ["PROJPROBE spawn tick=3 kind=3 id=7 px=%.4f py=%.4f x=%.4f y=%.4f vx=0.0 vy=0.0 facing=1" % (base[0], base[1], pts[0][0], pts[0][1])]
    for n in range(1, len(pts)):
        out.append("PROJPROBE f=%d kind=3 id=7 x=%.4f y=%.4f vx=1.0 vy=0.0 alive=%d" % (n + 2, pts[n][0], pts[n][1], n))
    return "\n".join(out)


def test_compare_accepts_the_modelled_path_and_rejects_another():
    art = {"name": "A", "lifetime": 12, "velocity": [1.5, 0.5], "spawn": [7, 9.5], "gravity": 0.1}
    text = log_for(art, (10.0, 2.0))
    r = C.compare(text, art, 3)
    assert r["max_error"] < 1e-3 and r["max_alive"] == 12
    other = dict(art, velocity=[3.0, 0.5])
    assert C.compare(text, other, 3)["max_error"] > 1.0


def test_no_rows():
    assert C.compare("nothing here", {"name": "A"}) is None
