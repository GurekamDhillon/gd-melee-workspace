"""Small, dependency-free System One client. Never logs requests or exceptions."""
import argparse
from http.client import HTTPException
import json
import math
import os
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ENDPOINT = "https://api.typesafe.ai/v1/systemone"


def sanitize(value):
    """Redact credentials and absolute paths before sending or displaying text."""
    if isinstance(value, dict):
        return {k: sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if not isinstance(value, str):
        return value
    key = os.environ.get("TYPESAFE_API_KEY")
    if key:
        value = value.replace(key, "[redacted]")
    value = re.sub(r"(?im)^.*(?:GW_ISO_\w+|TYPESAFE_API_KEY)\s*=.*$", "[redacted assignment]", value)
    value = re.sub(r"(?i)Bearer\s+\S+", "Bearer [redacted]", value)
    value = re.sub(r'''["'](?:[A-Za-z]:[\\/]|/|\\\\)[^"'\r\n]*["']''', '"[absolute path]"', value)
    value = re.sub(r"[A-Za-z]:[\\/][^\r\n\"'<>|]*", "[absolute path]", value)
    value = re.sub(r"\\\\[^\s\"']+", "[absolute path]", value)
    value = re.sub(r"(?<![\w:])/(?:[^\s/]+/)*[^\s]+", "[absolute path]", value)
    return value


def bounded(text, limit=4096):
    return sanitize(text).encode("utf-8")[-limit:].decode("utf-8", "ignore")


def impact(text):
    """Deterministic test fixture scoring; not a substitute for model judgments."""
    text = text.lower()
    for score, pattern in ((4, r"crash|data loss|corrupt"), (3, r"desync"),
                           (2, r"stuck|softlock|unable to play"), (1, r"wrong result|incorrect|winner")):
        if re.search(pattern, text):
            return score
    return 0


def _stub(state, questions, values):
    answers = {}
    for name, question in questions.items():
        kind = question["type"]
        value = values.get(name) if values else None
        if kind == "noul":
            answer = {"type": kind, "noul": 0.5 if value is None else value}
        else:
            criteria = question["criteria"]
            if kind == "choice":
                value = value or next(iter(criteria))
                answer = {"type": kind, "choice": value,
                          "probabilities": {k: float(k == value) for k in criteria}, "confidence": 1.0}
            else:
                value = min(impact(json.dumps(state)), len(criteria) - 1) if value is None else value
                answer = {"type": kind, "score": float(value), "confidence": 1.0,
                          "legend": {str(i): v for i, v in enumerate(criteria)},
                          "probabilities": {str(i): float(i == value) for i in range(len(criteria))}}
        answer["source"] = "stub"
        answers[name] = answer
    return answers


def _number(value, maximum=1):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= maximum


def _validate(answers, questions):
    for name, q in questions.items():
        a = answers[name]
        if a["type"] != q["type"]:
            raise ValueError("type")
        if q["type"] == "noul":
            if not _number(a["noul"]):
                raise ValueError("noul")
        else:
            keys = set(q["criteria"]) if q["type"] == "choice" else {str(i) for i in range(len(q["criteria"]))}
            p = a["probabilities"]
            if not isinstance(p, dict) or set(p) != keys or not all(_number(v) for v in p.values()) or abs(sum(p.values()) - 1) > 0.02 or not _number(a["confidence"]):
                raise ValueError("distribution")
            if q["type"] == "choice" and a["choice"] not in keys:
                raise ValueError("choice")
            if q["type"] == "score" and (not _number(a["score"], len(keys) - 1) or set(a["legend"]) != keys):
                raise ValueError("score")
        a["source"] = "jev"
    return answers


def call(state, questions, *, offline=False, timeout=8.0, stub_values=None):
    """Return typed answers or None. Retry transient failures exactly once."""
    if offline:
        return _stub(state, questions, stub_values)
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if key:
        payload = json.dumps({"state": sanitize(state), "questions": sanitize(questions), "model": "jev-latest"}).encode()
        request = Request(ENDPOINT, data=payload, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
        for attempt in range(2):
            try:
                with urlopen(request, timeout=timeout) as response:
                    return _validate(json.load(response)["answers"], questions)
            except HTTPError as exc:
                if exc.code not in (408, 429, 500, 502, 503, 504, 529):
                    break
            except (URLError, OSError, TimeoutError, HTTPException):
                pass
            except (ValueError, KeyError, TypeError):
                break
            if attempt == 0:
                time.sleep(0.25)
    print("jev: unavailable", file=sys.stderr)
    return None


def options(parser):
    parser.add_argument("--dry-run", "--offline", dest="offline", action="store_true", help="deterministic offline stub; no key or network")
    parser.add_argument("--timeout", type=float, default=8.0, help="seconds per attempt (one retry)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options(parser)
    args = parser.parse_args()
    result = call("Synthetic smoke check", {"smoke": {"type": "noul", "instructions": "Is this a synthetic smoke check?"}}, offline=args.offline, timeout=args.timeout)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
