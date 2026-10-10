"""Pure attribute metadata validation and unsaved numeric drafts (no bpy or file writes)."""
from __future__ import annotations

import copy
import math

GROUPS = ("ground", "air", "jump", "landing", "shield_ecb", "misc")


def _finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def validate_value(metadata: dict, value):
    name = metadata.get("name", "attribute")
    if not _finite(value):
        raise ValueError(f"{name} must be a finite number")
    if metadata.get("type") == "integer" and int(value) != value:
        raise ValueError(f"{name} must be an integer")
    bounds = metadata.get("range", {})
    low, high = bounds.get("minimum"), bounds.get("maximum")
    if (low is not None and value < low) or (high is not None and value > high):
        raise ValueError(f"{name} is outside its schema range")
    return int(value) if metadata.get("type") == "integer" else value


def normalize_rows(rows: list[dict]) -> list[dict]:
    if not isinstance(rows, list):
        raise ValueError("attributes must be a list")
    result, names = [], set()
    for original in rows:
        if not isinstance(original, dict):
            raise ValueError("attribute metadata must be an object")
        item = copy.deepcopy(original)
        name = item.get("name")
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("attribute names must be nonempty and unique")
        if item.get("type") not in ("integer", "number"):
            raise ValueError(f"{name}: unsupported attribute type")
        bounds = item.get("range")
        if not isinstance(bounds, dict):
            raise ValueError(f"{name}: missing schema range")
        for boundary in ("minimum", "maximum"):
            if bounds.get(boundary) is not None and not _finite(bounds[boundary]):
                raise ValueError(f"{name}: invalid schema range")
        low, high = bounds.get("minimum"), bounds.get("maximum")
        if low is not None and high is not None and low > high:
            raise ValueError(f"{name}: invalid schema range")
        if item.get("value") is not None:
            item["value"] = validate_value(item, item["value"])
        if item.get("group") not in GROUPS:
            item["group"] = "misc"
        names.add(name)
        result.append(item)
    return result


class AttributeDraft:
    """A batch of explicit edits, retained until applied or acknowledged as a no-op.

    Stop at the first proposal: another whole-file proposal would share its old
    baseline and become stale on acceptance. Proposals retain their drafts.
    A partial batch removes only fields that the
    server already applied. Every value is validated before the first mutation.
    """
    def __init__(self, rows=()):
        self.rows: list[dict] = []
        self._pending: dict[str, int | float] = {}
        self.refresh(list(rows))

    @property
    def changed(self) -> dict:
        return dict(self._pending)

    def _metadata(self, name: str) -> dict:
        for item in self.rows:
            if item["name"] == name:
                return item
        raise ValueError(f"unknown fighter attribute: {name}")

    def value(self, name: str):
        return self._pending.get(name, self._metadata(name).get("value"))

    def set(self, name: str, value):
        metadata = self._metadata(name)
        value = validate_value(metadata, value)
        if value == metadata.get("value"):
            self._pending.pop(name, None)
        else:
            self._pending[name] = value

    def reset(self, name: str):
        self._metadata(name)
        self._pending.pop(name, None)

    def refresh(self, rows: list[dict]):
        updated = normalize_rows(rows)
        by_name = {item["name"]: item for item in updated}
        pending = {}
        for name, value in self._pending.items():
            if name in by_name:
                validate_value(by_name[name], value)
                if value != by_name[name].get("value"):
                    pending[name] = value
        self.rows = updated
        self._pending = pending

    def filtered(self, query: str = "", group: str = "") -> list[dict]:
        query = query.casefold().strip()
        return [item for item in self.rows
                if (not group or item["group"] == group)
                and (not query or query in " ".join(str(item.get(key, ""))
                     for key in ("name", "description", "source_file")).casefold())]

    def apply(self, sess) -> bool:
        try:
            edits = [(name, validate_value(self._metadata(name), value))
                     for name, value in self._pending.items()]
        except ValueError as error:
            return sess.report_error(error)
        for name, value in edits:
            ok = sess.edit_attribute(name, value)
            outcome = sess.last_attribute_edit
            if outcome.get("applied") or outcome.get("unchanged"):
                self._metadata(name)["value"] = value
                self._pending.pop(name, None)
            if not ok:
                return False
            if outcome.get("proposed"):
                return True
        if sess.attributes:
            self.refresh(sess.attributes)
        return True
