"""Confidence routing shared by the Jev tools.

Docs: https://docs.typesafe.ai/confidence and /patterns/confidence-routing.
Choice and Score answers carry a `confidence` (0..1, concentration of the
distribution); a Noul answer carries only a probability, whose confidence we
compute as |2p-1|. The thresholds below are CONSERVATIVE DEFAULTS AND HAVE NOT
BEEN CALIBRATED on this repo's data: plot confidence against accuracy on real
labelled runs before loosening them. Override per call (`thresholds=`), per
process (env JEV_THRESHOLDS = JSON object or path to a JSON file) or in code.

Bands: "act" (use the answer), "confirm" (use it but flag for a quick human
check), "human" (do not act; a person reads the source text).
"""
import json
import os
from pathlib import Path

DEFAULTS = {
    "choice_floor": 0.6,    # below this: human
    "choice_act": 0.85,     # at/above this: act; between floor and act: confirm
    "noul_yes": 0.8,        # p >= yes: true
    "noul_no": 0.2,         # p <= no: false; in between: unsure -> human
    "score_floor": 0.5,
    "score_act": 0.8,
}


def thresholds(override=None):
    t = dict(DEFAULTS)
    raw = os.environ.get("JEV_THRESHOLDS", "").strip()
    if raw:
        try:
            t.update(json.loads(raw if raw.startswith("{") else Path(raw).read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            pass  # a bad override must never loosen the defaults
    if override:
        t.update(override)
    return t


def noul_confidence(p):
    return abs(2 * p - 1)


def noul_state(answer, t=None):
    """'yes' | 'no' | 'unsure' for a noul answer dict (or bare probability)."""
    t = thresholds(t)
    p = answer["noul"] if isinstance(answer, dict) else answer
    return "yes" if p >= t["noul_yes"] else "no" if p <= t["noul_no"] else "unsure"


def band(answer, t=None):
    """'act' | 'confirm' | 'human' for a choice/score answer dict.
    Stub and rule answers carry confidence 1.0; callers must keep `source`."""
    t = thresholds(t)
    if answer is None or answer.get("source") == "unavailable":
        return "human"
    kind = answer.get("type", "choice")
    c = answer.get("confidence", 0.0)
    floor, act = (t["score_floor"], t["score_act"]) if kind == "score" else (t["choice_floor"], t["choice_act"])
    return "human" if c < floor else "act" if c >= act else "confirm"


def order_stable(a, b):
    """Shuffle-check (Jev 1.13 leans to the first option): two answers to the same
    choice with the options in different orders must agree."""
    return a is not None and b is not None and a.get("choice") == b.get("choice")
