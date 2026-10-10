"""Compare numeric components of two workbench frame_info snapshots.

Compared fields are bones[].pos/mtx, root.mtx, hitboxes[].world,
hurtboxes[].a/b, and every numeric component under ecb.

Lists are compared by index. Unlisted metadata is ignored. Selected fields
absent from both snapshots are skipped; one-sided absence, differing counts,
invalid numeric values, and incompatible structures raise ValueError.

"fields" counts scalar numeric components, including equal components.
"worst" is empty when all components are equal. Ties retain the first path
visited, with dictionary keys visited in sorted order.

Usage:
    python tools/workbench/frame_info_diff.py A.json B.json --tol 1e-3

Exit codes: 0 for OK, 1 for DIFF, 2 for invalid inputs or tolerance.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path


def _mapping(value, path):
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    return value


def _sequence(value, path):
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{path} must be a list")
    return value


def _number(value, path):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"non-numeric value at {path}")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"non-finite value at {path}") from exc
    if not math.isfinite(number):
        raise ValueError(f"non-finite value at {path}")
    return number


def _compare_field(a, b, key, path, result):
    in_a, in_b = key in a, key in b
    if in_a != in_b:
        missing = "b" if in_a else "a"
        raise ValueError(f"field missing at {path}: {missing}")
    if in_a:
        _compare_numeric(a[key], b[key], path, result)


def _compare_numeric(a, b, path, result):
    if isinstance(a, Mapping) or isinstance(b, Mapping):
        left = _mapping(a, path)
        right = _mapping(b, path)
        keys = set(left) | set(right)
        if any(not isinstance(key, str) for key in keys):
            raise ValueError(f"object keys at {path} must be strings")
        for key in sorted(keys):
            _compare_field(left, right, key, f"{path}.{key}", result)
        return

    if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
        left = _sequence(a, path)
        right = _sequence(b, path)
        if len(left) != len(right):
            raise ValueError(
                f"component count differs at {path}: {len(left)} vs {len(right)}"
            )
        for index, (av, bv) in enumerate(zip(left, right)):
            _compare_numeric(av, bv, f"{path}[{index}]", result)
        return

    av, bv = _number(a, path), _number(b, path)
    delta = abs(av - bv)
    result["fields"] += 1
    if delta > result["max_abs"]:
        result["max_abs"] = delta
        result["worst"] = path


def _compare_entries(a, b, key, selected, label, result):
    left = _sequence(a.get(key, []), f"a.{key}")
    right = _sequence(b.get(key, []), f"b.{key}")
    if len(left) != len(right):
        raise ValueError(f"{label} count differs: {len(left)} vs {len(right)}")
    for index, (av, bv) in enumerate(zip(left, right)):
        av = _mapping(av, f"a.{key}[{index}]")
        bv = _mapping(bv, f"b.{key}[{index}]")
        for field in selected:
            _compare_field(av, bv, field, f"{key}[{index}].{field}", result)


def diff(a: dict, b: dict) -> dict:
    """Return maximum absolute difference, its path, and component count."""
    a = _mapping(a, "a")
    b = _mapping(b, "b")
    result = {"max_abs": 0.0, "worst": "", "fields": 0}

    _compare_entries(a, b, "bones", ("pos", "mtx"), "bone", result)

    root_a = _mapping(a.get("root", {}), "a.root")
    root_b = _mapping(b.get("root", {}), "b.root")
    _compare_field(root_a, root_b, "mtx", "root.mtx", result)

    _compare_entries(a, b, "hitboxes", ("world",), "hitbox", result)
    _compare_entries(a, b, "hurtboxes", ("a", "b"), "hurtbox", result)
    _compare_field(a, b, "ecb", "ecb", result)
    return result


def _tolerance(tol):
    try:
        value = float(tol)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("tol must be finite and nonnegative") from exc
    if not math.isfinite(value) or value < 0:
        raise ValueError("tol must be finite and nonnegative")
    return value


def ok(a: dict, b: dict, tol=1e-3) -> bool:
    """Whether all compared components differ by at most tol."""
    tol = _tolerance(tol)
    return diff(a, b)["max_abs"] <= tol


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("a", type=Path, metavar="A.json")
    parser.add_argument("b", type=Path, metavar="B.json")
    parser.add_argument("--tol", type=float, default=1e-3)
    args = parser.parse_args(argv)

    try:
        tol = _tolerance(args.tol)
        with args.a.open("r", encoding="utf-8-sig") as stream:
            a = json.load(stream)
        with args.b.open("r", encoding="utf-8-sig") as stream:
            b = json.load(stream)
        result = diff(a, b)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    matches = result["max_abs"] <= tol
    status = "OK" if matches else "DIFF"
    worst = result["worst"] or "-"
    print(
        f"max_abs={result['max_abs']:.12g} worst={worst} "
        f"fields={result['fields']} {status}"
    )
    return 0 if matches else 1


if __name__ == "__main__":
    sys.exit(main())
