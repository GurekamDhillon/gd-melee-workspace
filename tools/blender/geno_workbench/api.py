"""Standard-library session API for the Geno Workbench front end.

Frame replies are validated before replacing cached data. Source edits never
replace engine frame data or invoke frame hooks. This module does not import
bpy or write project files.
"""

from __future__ import annotations

import json
import math
import os
from typing import Callable

try:
    from . import client, wbspace
    from .props import STRINGS
except ImportError:
    import client
    import wbspace
    from props import STRINGS


EDITABLE = (
    "bone", "damage", "size", "x", "y", "z", "angle", "kbg", "fkb", "bkb",
    "start_frame", "end_frame",
)

_TRANSPORT_FAILURES = (
    "closed", "refused", "timeout", "timed out", "connection reset",
    "reset by peer", "broken pipe", "connection aborted", "connection lost",
    "disconnected", "not connected", "end of file", "eof",
)


class WbSession:
    """One connection and its last successfully received data.

    on_change synchronizes UI properties. on_frame updates poses and overlays
    only after a complete frame operation has succeeded.
    """

    EDITABLE = EDITABLE
    edit_fields = EDITABLE

    def __init__(
        self,
        client_factory: Callable[[], client.McpClient | client.CliClient],
    ):
        self.client_factory = client_factory
        self.client = None
        self.connected = False
        self.status = STRINGS["disconnected"]
        self.rows: list[dict] = []
        self.row = ""
        self.frame = 0
        self.pending_frame: int | None = None
        self.info: dict | None = None
        self.hitboxes: list[dict] = []
        self.problems: list[dict] = []
        self.stale = False
        self.last_error = ""
        self.suggestion: dict | None = None
        self.jointmap = None
        self.calibration = None
        self.on_change: Callable[[WbSession], None] | None = None
        self.on_frame: list[Callable[[WbSession], None]] = []
        self.hook_error = ""
        self.project_dir = ""
        self.plan_path = ""
        self.art_blend = ""
        self.art_glb = ""
        self.bone_aliases: dict[str, str] = {}

    def _fire_frame(self) -> None:
        """Report hook failures without raising through an operator."""
        self.hook_error = ""
        for hook in list(self.on_frame):
            try:
                hook(self)
            except Exception as exc:
                self.hook_error = str(exc)

    def _status_with_stale(self, message: str) -> str:
        marker = STRINGS["stale_status"]
        if self.stale and marker not in message:
            return f"{message}; {marker}"
        return message

    def _notify(self) -> bool:
        if self.on_change is None:
            return True
        try:
            self.on_change(self)
        except Exception as exc:
            detail = STRINGS["callback_error"].format(error=exc)
            self.last_error = (
                f"{self.last_error}; {detail}" if self.last_error else detail
            )
            self.status = self._status_with_stale(
                STRINGS["error_status"].format(error=self.last_error)
            )
            return False
        return True

    def set_status(self, message: str) -> bool:
        self.last_error = ""
        self.status = self._status_with_stale(message)
        return self._notify()

    @staticmethod
    def _quiet_close(connection):
        close = getattr(connection, "close", None)
        if callable(close):
            try:
                close()
            except (client.WbError, OSError):
                pass

    def report_error(self, error) -> bool:
        self.last_error = str(error) or type(error).__name__
        client.log.error("session error: %s (connected=%s row=%s frame=%s)",
                         self.last_error, getattr(self, "connected", None),
                         getattr(self, "row", None), getattr(self, "frame", None),
                         exc_info=isinstance(error, BaseException))
        if any(word in self.last_error.lower() for word in _TRANSPORT_FAILURES):
            previous, self.client = self.client, None
            self.connected = False
            self.pending_frame = None
            self._quiet_close(previous)
        self.status = self._status_with_stale(
            STRINGS["error_status"].format(error=self.last_error)
        )
        self._notify()
        return False

    def _run(self, action: Callable[[], str]) -> bool:
        try:
            message = action()
        except (client.WbError, OSError, ValueError, TypeError) as exc:
            return self.report_error(exc)
        return self.set_status(message)

    @staticmethod
    def _raw_call(connection, tool: str, args: dict | None = None) -> dict:
        result = connection.call(tool, args or {})
        if not isinstance(result, dict):
            raise client.WbError(STRINGS["invalid_reply"].format(tool=tool))
        return result

    def _request(self, tool: str, args: dict | None = None) -> dict:
        if not self.connected or self.client is None:
            raise client.WbError(STRINGS["not_connected"])
        return self._raw_call(self.client, tool, args)

    @staticmethod
    def _items(result: dict, field: str) -> list[dict]:
        items = result.get(field)
        if not isinstance(items, list) or any(
            not isinstance(item, dict) for item in items
        ):
            raise client.WbError(STRINGS["invalid_list"].format(field=field))
        return [dict(item) for item in items]

    @staticmethod
    def _integer(value, field: str, minimum: int = 0) -> int:
        message = STRINGS["invalid_integer"].format(field=field, minimum=minimum)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise client.WbError(message)
        try:
            number = int(value)
        except (ValueError, OverflowError):
            raise client.WbError(message) from None
        if number < minimum or number != value:
            raise client.WbError(message)
        return number

    @staticmethod
    def _number(value, field: str):
        message = STRINGS["invalid_number"].format(field=field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise client.WbError(message)
        try:
            valid = math.isfinite(value)
        except OverflowError:
            valid = False
        if not valid:
            raise client.WbError(message)
        return value

    @staticmethod
    def _row_name(value) -> str:
        if not isinstance(value, str) or not value.strip():
            raise client.WbError(STRINGS["row_required"])
        return value

    def _read_frame(self, result: dict, fallback_row: str):
        frame = self._integer(result.get("frame"), "frame")
        row = result.get("row", fallback_row)
        if not isinstance(row, str):
            raise client.WbError(STRINGS["invalid_row"])
        return dict(result), row, frame

    def _store_frame(self, parsed):
        info, row, frame = parsed
        if row != self.row:
            self.hitboxes = []
            self.suggestion = None
        self.info = info
        self.row = row
        self.frame = frame

    def _frame_status(self) -> str:
        text = STRINGS["frame_loaded"].format(row=self.row, frame=self.frame)
        return f"{text}; {self.hook_error}" if self.hook_error else text

    def _source_hitboxes(self, row: str) -> list[dict]:
        return self._items(
            self._request("list_hitboxes", {"row": row}), "hitboxes"
        )

    def connect(self) -> bool:
        candidate = None
        try:
            candidate = self.client_factory()
            opener = getattr(candidate, "connect", None)
            if callable(opener):
                opener()
            result = self._raw_call(candidate, "engine_status")
        except (client.WbError, OSError, ValueError, TypeError) as exc:
            self._quiet_close(candidate)
            previous, self.client = self.client, None
            self.connected = False
            if previous is not candidate:
                self._quiet_close(previous)
            return self.report_error(exc)

        previous = self.client
        self.client = candidate
        self.connected = True
        if previous is not candidate:
            self._quiet_close(previous)
        self.rows = []
        self.row = ""
        self.frame = 0
        self.pending_frame = None
        self.info = None
        self.hitboxes = []
        self.problems = []
        self.suggestion = None
        self.jointmap = None
        self.calibration = None
        self.hook_error = ""
        # Reconnecting is not evidence that an edited source was rebuilt.
        return self.set_status(
            STRINGS["connected"].format(
                engine=result.get("status", STRINGS["unknown"])
            )
        )

    def disconnect(self) -> bool:
        previous, self.client = self.client, None
        self.connected = False
        self.pending_frame = None

        def action():
            close = getattr(previous, "close", None)
            if callable(close):
                close()
            return STRINGS["disconnected"]

        return self._run(action)

    def refresh_rows(self) -> bool:
        def action():
            rows = self._items(self._request("list_rows"), "rows")
            self.rows = rows
            return STRINGS["rows_loaded"].format(count=len(rows))

        return self._run(action)

    def load_row(self, name, *, refresh_hitboxes=False) -> bool:
        """Optionally fetch source boxes before publishing the new frame."""
        self.pending_frame = None

        def action():
            row = self._row_name(name)
            loaded = self._request("load_row", {"row": row})
            if "bones" not in loaded:
                # The real server answers load_row with {"ok": true}; the first frame follows.
                loaded = self._request("set_frame", {"frame": 1})
            parsed = self._read_frame(loaded, row)
            boxes = self._source_hitboxes(row) if refresh_hitboxes else []
            self._store_frame(parsed)
            self.hitboxes = boxes
            self.suggestion = None
            self._fire_frame()
            return self._frame_status()

        return self._run(action)

    def set_frame(self, n) -> bool:
        self.pending_frame = None

        def action():
            frame = self._integer(n, "frame")
            result = self._request("set_frame", {"frame": frame})
            self._store_frame(self._read_frame(result, self.row))
            self._fire_frame()
            return self._frame_status()

        return self._run(action)

    def step(self, n=1) -> bool:
        """Seek relative to the acknowledged frame, including negative steps."""
        try:
            offset = self._integer(n, "frames", minimum=-self.frame)
        except client.WbError as exc:
            return self.report_error(exc)
        return self.set_frame(self.frame + offset)

    def coalesced_set_frame(self, n) -> bool:
        """Queue a frame without performing I/O or firing callbacks."""
        try:
            frame = self._integer(n, "frame")
        except client.WbError as exc:
            return self.report_error(exc)
        self.pending_frame = frame
        return True

    def flush_pending(self) -> bool:
        """Send the latest queued frame once; False also means no work."""
        frame = self.pending_frame
        if frame is None:
            return False
        self.pending_frame = None
        return self.set_frame(frame)

    def refresh_hitboxes(self) -> bool:
        def action():
            row = self._row_name(self.row)
            boxes = self._source_hitboxes(row)
            self.hitboxes = boxes
            return STRINGS["hitboxes_loaded"].format(count=len(boxes))

        return self._run(action)

    def run_checks(self) -> bool:
        def action():
            problems = self._items(self._request("run_checks"), "problems")
            self.problems = problems
            return STRINGS["checks_loaded"].format(count=len(problems))

        return self._run(action)

    @classmethod
    def _first_active_frame(cls, boxes, ordinal) -> int:
        index = cls._integer(ordinal, "ordinal")
        if index >= len(boxes):
            return 1
        return cls._integer(boxes[index].get("start_frame", 1), "start_frame")

    def first_active_frame(self, row, ordinal) -> int:
        """Read the source start frame, defaulting to 1 when absent.

        A different row is queried without changing the selected row or pose.
        Invalid input and failed queries raise WbError.
        """
        name = self._row_name(row)
        boxes = self.hitboxes if name == self.row else self._source_hitboxes(name)
        return self._first_active_frame(boxes, ordinal)

    def goto_problem(self, i) -> bool:
        """Publish the problem pose only after all required replies succeed."""
        self.pending_frame = None

        def action():
            index = self._integer(i, "index")
            if index >= len(self.problems):
                raise client.WbError(STRINGS["problem_missing"])
            problem = self.problems[index]
            row = self._row_name(problem.get("row"))
            ordinal = self._integer(problem.get("ordinal", 0), "ordinal")
            self._read_frame(self._request("load_row", {"row": row}), row)
            boxes = self._source_hitboxes(row)
            frame = self._first_active_frame(boxes, ordinal)
            parsed = self._read_frame(
                self._request("set_frame", {"frame": frame}), row
            )
            self._store_frame(parsed)
            self.hitboxes = boxes
            self.suggestion = None
            self._fire_frame()
            return self._frame_status()

        return self._run(action)

    def edit_hitbox(self, **fields) -> bool:
        """Apply a sparse source edit; leave engine data and frame hooks alone."""
        def action():
            unknown = set(fields) - set(EDITABLE) - {"row", "ordinal"}
            if unknown:
                raise client.WbError(
                    STRINGS["unsupported_fields"].format(
                        fields=", ".join(sorted(unknown))
                    )
                )
            row = self._row_name(fields.get("row", self.row))
            ordinal = self._integer(fields.get("ordinal"), "ordinal")
            args = {"row": row, "ordinal": ordinal}
            for field in EDITABLE:
                if field not in fields:
                    continue
                value = fields[field]
                if field == "bone":
                    if not isinstance(value, str) or not value.strip():
                        raise client.WbError(STRINGS["bone_required"])
                elif field in ("start_frame", "end_frame"):
                    value = self._integer(value, field)
                else:
                    value = self._number(value, field)
                args[field] = value
            if len(args) == 2:
                return STRINGS["no_changes"]

            result = self._request("edit_hitbox", args)
            if "proposal" in result:
                # A proposal must not clear a previous successful source edit.
                return STRINGS["proposal_created"]

            self.stale = True
            self.suggestion = None
            if row == self.row:
                # If the source refresh fails, do not label the old list as new.
                self.hitboxes = []
            boxes = self._source_hitboxes(row)
            if row == self.row:
                self.hitboxes = boxes
            return STRINGS["source_edited"]

        return self._run(action)

    def rebuild_reload(self) -> bool:
        """Restore the selection, source list, pose and overlays after reload."""
        saved_row, saved_frame = self.row, self.frame
        self.pending_frame = None

        def action():
            # Every failure from here must leave the stale indication visible.
            self.stale = True
            self._request("rebuild")
            self._request("reload")
            rows = self._items(self._request("list_rows"), "rows")
            parsed = None
            boxes = []
            if saved_row:
                self._read_frame(
                    self._request("load_row", {"row": saved_row}), saved_row
                )
                parsed = self._read_frame(
                    self._request("set_frame", {"frame": saved_frame}), saved_row
                )
                boxes = self._source_hitboxes(saved_row)

            self.rows = rows
            if parsed is not None:
                self._store_frame(parsed)
            else:
                self.info = None
            self.hitboxes = boxes
            self.problems = []
            self.suggestion = None
            self.stale = False
            if parsed is not None:
                self._fire_frame()
            text = STRINGS["reloaded"]
            return f"{text}; {self.hook_error}" if self.hook_error else text

        return self._run(action)

    def suggest_bone(self, ordinal) -> bool:
        def action():
            row = self._row_name(self.row)
            index = self._integer(ordinal, "ordinal")
            result = self._request(
                "suggest_hitbox_bone", {"row": row, "ordinal": index}
            )
            self.suggestion = dict(result)
            suggested = result.get("suggested")
            if suggested:
                return STRINGS["suggested"].format(bone=suggested)
            return STRINGS["no_suggestion"]

        return self._run(action)

    def engine_restart(self) -> bool:
        self.pending_frame = None

        def action():
            result = self._request("engine_restart")
            self.info = None
            self.row = ""
            self.frame = 0
            self.hitboxes = []
            self.problems = []
            self.suggestion = None
            return STRINGS["restarted"].format(
                engine=result.get("status", STRINGS["unknown"])
            )

        return self._run(action)

    def pose_problem(self) -> str:
        if self.info is None:
            return STRINGS["no_frame"]
        try:
            wbspace.check_schema(self.info)
        except (ValueError, TypeError) as exc:
            return str(exc)
        return ""


_session: WbSession | None = None


def session() -> WbSession:
    global _session
    if _session is None:
        _session = WbSession(
            lambda: client.McpClient(host="127.0.0.1", timeout=10.0)
        )
    return _session


def _workspace_root(start: str) -> str:
    """Find the nearest .git ancestor, otherwise return the project directory."""
    here = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(here, ".git")):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            return os.path.abspath(start)
        here = parent


def set_project(project_dir: str) -> bool:
    """Read project paths without writing project or package data."""
    sess = session()
    try:
        config_path = os.path.join(project_dir, "workbench.json")
        with open(config_path, "r", encoding="utf-8-sig") as source:
            config = json.load(source)
        if not isinstance(config, dict):
            raise ValueError(STRINGS["project_object_required"])
        root = _workspace_root(project_dir)

        def resolve(value, relative_to):
            if not isinstance(value, str) or not value:
                return ""
            if "\x00" in value:
                raise ValueError(STRINGS["project_invalid_path"])
            return os.path.normpath(
                value if os.path.isabs(value) else os.path.join(relative_to, value)
            )

        art = config.get("art") or {}
        if not isinstance(art, dict):
            raise ValueError(STRINGS["project_art_required"])
        aliases = art.get("bone_aliases") or {}
        if not isinstance(aliases, dict):
            raise ValueError(STRINGS["project_aliases_required"])
        sess.project_dir = os.path.abspath(project_dir)
        sess.plan_path = (
            resolve(config.get("plan_abs"), root)
            or resolve(config.get("plan"), project_dir)
        )
        sess.art_blend = resolve(config.get("art_blend"), root)
        sess.art_glb = resolve(config.get("art_glb"), root)
        sess.bone_aliases = {str(k): str(v) for k, v in aliases.items()}
    except (OSError, ValueError, TypeError) as exc:
        sess.last_error = str(exc)
        sess.status = sess._status_with_stale(
            STRINGS["error_status"].format(error=exc)
        )
        return False
    return True
