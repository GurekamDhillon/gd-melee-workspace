"""Foot-contact statistics from a clip's baked sole points (pure Python; used by validate.py and the dev checks).
A sole point (heel, ball, toe tip) is planted when it is within TOL of the ground in two consecutive frames; the body is
in place, so a planted point must move back (+y in authoring space) at the ground speed v: speed = y[i+1] - y[i]."""
TOL = 0.06

def contacts(soles, loop=True):
    n = len(soles)
    out = {"speeds": [], "per_foot": {"L": 0, "R": 0}, "flight_frames": 0, "min_z": 9e9, "frames": n}
    for i in range(n):
        j = (i + 1) % n
        if not loop and j == 0: break
        anyc = False
        for sd in "LR":
            c = False
            for k in range(3):
                a, b = soles[i][sd][k], soles[j][sd][k]
                out["min_z"] = min(out["min_z"], a[2])
                if a[2] < TOL and b[2] < TOL:
                    out["speeds"].append((sd, k, b[1] - a[1], i)); c = True
            if c: out["per_foot"][sd] += 1; anyc = True
        if not anyc: out["flight_frames"] += 1
    return out

def summarize(soles, v, loop=True):
    c = contacts(soles, loop)
    sp = [s[2] for s in c["speeds"]]
    if not sp: return dict(ok=False, why="no planted frames", **{k: c[k] for k in ("flight_frames", "min_z")})
    mean = sum(sp) / len(sp)
    return dict(ref=v, mean=round(mean, 4), lo=round(min(sp), 4), hi=round(max(sp), 4), n=len(sp), planted_L=c["per_foot"]["L"], planted_R=c["per_foot"]["R"],
                flight_frames=c["flight_frames"], min_z=round(c["min_z"], 3), spread=round((max(sp) - min(sp)) / max(v, 1e-6), 3), err=round((mean - v) / max(v, 1e-6), 3))
