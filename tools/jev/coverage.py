"""Requirement coverage of an agent report against its brief.

For each requirement in the brief, code retrieves the few report passages that
mention it (token overlap; no model), then three atomic Noul questions are asked
with ONLY those passages as state (docs: decompose state, one condition per Noul,
fan out in parallel, combine in code):

  completed  "The excerpt states the requirement was completed."
  evidence   "The excerpt gives concrete evidence for it (numbers, file paths, log lines, commit hashes)."
  owed       "The excerpt states it was NOT done, is owed, or is unverified."

Combined in code into done | owed | unaddressed | unclear; any unsure answer
(p between the noul thresholds, see confidence.py) or contradictory pair sets
needs_human_read. A requirement with no lexical match in the report is
`unaddressed` without a model call, flagged retrieval=none (a paraphrase with no
shared words would land here: read those).

  python tools/jev/coverage.py BRIEF.md REPORT.md [--offline] [--json]

Brief format: one requirement per line, or a checklist/numbered/bulleted list.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import sys

try:
    from . import jev, confidence
except ImportError:
    import jev
    import confidence

STOP = set("a an and are as at be by for from has have in is it its of on or that the this to was were will with not no must should shall all any each per into out up do does did done after before than then so if when".split())
ITEM = re.compile(r"^\s*(?:[-*+]\s*(?:\[[ xX]\]\s*)?|(?P<n>\d+)[.)]\s+|\(\d+\)\s+|#+\s+)?(?P<t>\S.*)$")
DONE_RX = re.compile(r"\b(done|completed?|fixed|implemented|added|passes|passed|pass|verified|shipped|committed|works?|green|landed|built)\b", re.I)
OWED_RX = re.compile(r"\b(owed|not done|not yet|unverified|not verified|skipped|todo|could not|couldn't|did not|didn't|unable|pending|deferred|not tested|untested)\b", re.I)
EVID_RX = re.compile(r"\d|[\w./\\-]+\.\w{1,5}\b|\b[0-9a-f]{7,40}\b|`[^`]+`")


def requirements(text):
    out = []
    for line in text.splitlines():
        if not line.strip() or re.match(r"^\s*(?:#+\s|---|```)", line) and not re.match(r"^\s*\d", line):
            continue
        m = ITEM.match(line)
        if m and len(m["t"]) > 3:
            out.append({"id": "R%d" % (len(out) + 1), "text": m["t"].strip(), "ref": int(m["n"]) if m["n"] else None})
    return out


def tokens(text):
    words = re.findall(r"[A-Za-z0-9_./\\-]+", text.lower())
    out = set()
    for w in words:
        for piece in re.split(r"[./\\_-]+", w) + ([w] if re.search(r"[./\\_-]", w) else []):
            if len(piece) > 1 and piece not in STOP:
                out.add(piece.rstrip("s") if len(piece) > 3 else piece)
    return out


def chunks(report, window=1):
    lines = [l for l in report.splitlines()]
    out = []
    for i, l in enumerate(lines):
        if l.strip():
            out.append((i, "\n".join(x for x in lines[i:i + window] if x.strip())))
    return out


def retrieve(req_text, report, k=4, limit=1600, ref=None):
    """Greedy weighted set cover: pick up to k report lines that together cover the most
    (IDF-weighted) requirement words, so one common word (a fighter name repeated in table
    rows) cannot crowd out the line that carries the rest. Lines citing the brief's item
    number as `#N` are taken first. Returned in report order."""
    rq = tokens(req_text)
    parts = chunks(report)
    if not rq or not parts:
        return [], 0.0
    df = {}
    toks = [tokens(c) for _, c in parts]
    for t in toks:
        for w in t:
            df[w] = df.get(w, 0) + 1
    n = len(parts)
    weight = {w: 1.0 + (n / df[w]) ** 0.5 for w in rq if w in df}
    refrx = re.compile(r"#\s*(?:\d+\s*,\s*)*%d|items?\s+(?:\d+\s*(?:,|and)\s*)*%d" % (ref, ref), re.I) if ref is not None else None
    chosen, covered = [], set()
    if refrx:
        for (i, c), t in zip(parts, toks):
            if refrx.search(c) and len(chosen) < k:
                chosen.append((i, c))
                covered |= rq & t
    while len(chosen) < k:
        best = None
        for (i, c), t in zip(parts, toks):
            if any(i == j for j, _ in chosen):
                continue
            gain = sum(weight[w] for w in (rq & t) - covered)
            if gain > 0 and (best is None or gain > best[0]):
                best = (gain, i, c, t)
        if not best:
            break
        chosen.append((best[1], best[2]))
        covered |= rq & best[3]
    if not chosen:
        return [], 0.0
    picked, used = [], 0
    for i, c in sorted(chosen):
        picked.append(jev.bounded(c, 600))
        used += len(picked[-1])
        if used > limit:
            break
    return picked, sum(weight[w] for w in covered) / (len(rq) ** 0.5)


def questions_for(req):
    def crit(yes, no):
        return {"true": {"what": yes}, "false": {"what": no}}
    return {
        "completed": {"type": "noul",
                      "instructions": {"requirement": req["text"],
                                       "question": "The report excerpt reports work that finishes this requirement: it says it was fixed, implemented, built, passed or measured."},
                      "criteria": crit("The excerpt says the requirement was done, fixed, built, passed or shipped.",
                                       "The excerpt does not claim completion, or only describes plans or intent.")},
        "evidence": {"type": "noul",
                     "instructions": {"requirement": req["text"],
                                      "question": "The report excerpt gives concrete evidence for this requirement: numbers, file paths, log lines or commit hashes."},
                     "criteria": crit("The excerpt quotes a count, a path, a log line or a hash that bears on the requirement.",
                                      "The excerpt only asserts the outcome in general words.")},
        "owed": {"type": "noul",
                 "instructions": {"requirement": req["text"],
                                  "question": "The report excerpt states that this requirement was NOT done, is still owed, or is unverified."},
                 "criteria": crit("The excerpt says the requirement is undone, owed, skipped, blocked or not verified.",
                                  "The excerpt does not say the requirement is outstanding.")},
    }


def stub_values(excerpt):
    text = "\n".join(excerpt)
    owed = bool(OWED_RX.search(text))
    return {"completed": float(bool(DONE_RX.search(text)) and not owed), "evidence": float(bool(EVID_RX.search(text))),
            "owed": float(owed)}


def combine(ans, t=None):
    """done/owed/unaddressed/unclear from three noul probabilities."""
    s = {k: confidence.noul_state(ans[k], t) for k in ("completed", "evidence", "owed")}
    if "unsure" in (s["completed"], s["owed"]):
        return "unclear", True, "unsure answer(s): " + ", ".join(k for k, v in s.items() if v == "unsure")
    if s["owed"] == "yes" and s["completed"] == "yes":
        return "unclear", True, "excerpt both claims completion and says it is owed"
    if s["owed"] == "yes":
        return "owed", False, "report says outstanding"
    if s["completed"] == "yes":
        if s["evidence"] == "yes":
            return "done", False, "completion claimed with concrete evidence"
        if s["evidence"] == "no":
            return "unclear", False, "completion claimed without concrete evidence"
        return "unclear", True, "evidence answer unsure"
    return "unaddressed", False, "excerpt neither claims completion nor owes it"


def check_one(req, report, *, offline, timeout, t):
    passages, score = retrieve(req["text"], report, ref=req.get("ref"))
    absent = sorted(w for w in tokens(req["text"]) if w not in tokens(report))[:8]
    row = {"id": req["id"], "requirement": jev.bounded(req["text"], 300), "retrieval": round(score, 2), "excerpt_chars": sum(map(len, passages))}
    if not passages:
        return {**row, "status": "unaddressed", "needs_human_read": False, "retrieval": "none", "source": "code",
                "why": "no report passage shares words with the requirement (paraphrase risk: read)"}
    state = {"report_excerpt": passages}
    if absent:
        state["requirement_words_absent_from_whole_report"] = absent
    sv = stub_values(passages)
    ans = jev.call(state, questions_for(req), offline=offline, timeout=timeout, stub_values=sv)
    if not ans:
        return {**row, "status": "unclear", "needs_human_read": True, "source": "unavailable", "why": "jev: unavailable"}
    status, human, why = combine(ans, t)
    return {**row, "status": status, "needs_human_read": human, "source": ans["completed"]["source"], "why": why,
            "p": {k: round(ans[k]["noul"], 2) for k in ans}}


def coverage(brief, report, *, offline=False, timeout=8.0, thresholds=None, workers=4):
    reqs = requirements(brief)
    t = confidence.thresholds(thresholds)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(lambda r: check_one(r, report, offline=offline, timeout=timeout, t=t), reqs))
    tally = {}
    for r in rows:
        tally[r["status"]] = tally.get(r["status"], 0) + 1
    return {"requirements": rows, "tally": tally, "needs_human_read": [r["id"] for r in rows if r["needs_human_read"]]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brief", type=Path)
    ap.add_argument("report", help="report file, or - for stdin")
    ap.add_argument("--json", action="store_true")
    jev.options(ap)
    a = ap.parse_args()
    try:
        brief = a.brief.read_text(encoding="utf-8")
        report = sys.stdin.read() if a.report == "-" else Path(a.report).read_text(encoding="utf-8")
    except OSError:
        ap.exit(2, "coverage: cannot read input\n")
    res = coverage(brief, report, offline=a.offline, timeout=a.timeout)
    if a.json:
        print(json.dumps(jev.sanitize(res), indent=2))
    else:
        for r in res["requirements"]:
            print("%-3s %-11s%s %s" % (r["id"], r["status"], " *" if r["needs_human_read"] else "  ", r["requirement"][:90]))
        print("tally:", res["tally"], "| needs human read:", ", ".join(res["needs_human_read"]) or "none")


if __name__ == "__main__":
    main()
