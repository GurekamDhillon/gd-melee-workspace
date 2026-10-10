"""Standard-library session API for the Geno Workbench front end.

Network replies are validated before replacing cached frame data. Blender
integration is supplied through the optional on_change callback. This module
does not import bpy or write project files.
"""

from __future__ import annotations

from typing import Callable

try:
    from . import client, wbspace
    from .props import STRINGS
except ImportError:
    import client
    import wbspace
    from props import STRINGS


_TRANSPORT_FAILURES = (
    "closed",
    "refused",
    "timeout",
    "timed out",
    "connection reset",
    "reset by peer",
    "broken pipe",
    "connection aborted",
    "connection lost",
    "disconnected",
    "not connected",
    "end of file",
    "eof",
)


class WbSession:
    """One workbench connection and its last successfully received data.

    on_change receives this session after a completed operation or a recorded
    error. The Blender shell uses it only to synchronize UI properties.
    """

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
        self.info: dict | None = None
        self.hitboxes: list[dict] = []
        self.problems: list[dict] = []
        self.stale = False
        self.last_error = ""

        self.suggestion: dict | None = None
        self.jointmap = None
        self.calibration = None
        self.on_change: Callable[[WbSession], None] | None = None

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
        """Publish a successful operation status, including the stale marker."""
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
        """Record an operator or transport failure without raising it."""
        self.last_error = str(error) or type(error).__name__
        if any(word in self.last_error.lower() for word in _TRANSPORT_FAILURES):
            previous, self.client = self.client, None
            self.connected = False
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
        message = STRINGS["invalid_integer"].format(
            field=field, minimum=minimum
        )
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
        return STRINGS["frame_loaded"].format(row=self.row, frame=self.frame)

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
        self.info = None
        self.hitboxes = []
        self.problems = []
        self.suggestion = None
        self.jointmap = None
        self.calibration = None
        return self.set_status(
            STRINGS["connected"].format(
                engine=result.get("status", STRINGS["unknown"])
            )
        )

    def disconnect(self) -> bool:
        previous, self.client = self.client, None
        self.connected = False

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

    def load_row(self, name) -> bool:
        def action():
            row = self._row_name(name)
            result = self._request("load_row", {"row": row})
            parsed = self._read_frame(result, row)
            self._store_frame(parsed)
            self.hitboxes = []
            self.suggestion = None
            return self._frame_status()

        return self._run(action)

    def set_frame(self, n) -> bool:
        def action():
            frame = self._integer(n, "frame")
            result = self._request("set_frame", {"frame": frame})
            self._store_frame(self._read_frame(result, self.row))
            return self._frame_status()

        return self._run(action)

    def step(self, n=1) -> bool:
        def action():
            frames = self._integer(n, "frames", minimum=1)
            result = self._request("play", {"frames": frames, "step": 1})
            self._store_frame(self._read_frame(result, self.row))
            return self._frame_status()

        return self._run(action)

    def refresh_hitboxes(self) -> bool:
        def action():
            row = self._row_name(self.row)
            result = self._request("list_hitboxes", {"row": row})
            hitboxes = self._items(result, "hitboxes")
            self.hitboxes = hitboxes
            return STRINGS["hitboxes_loaded"].format(count=len(hitboxes))

        return self._run(action)

    def run_checks(self) -> bool:
        def action():
            problems = self._items(self._request("run_checks"), "problems")
            self.problems = problems
            return STRINGS["checks_loaded"].format(count=len(problems))

        return self._run(action)

    def edit_hitbox(self, **fields) -> bool:
        def action():
            args = dict(fields)
            args["row"] = self._row_name(args.get("row", self.row))
            args["ordinal"] = self._integer(args.get("ordinal"), "ordinal")
            result = self._request("edit_hitbox", args)

            if "proposal" in result:
                self.stale = False
                return STRINGS["proposal_created"]

            self.stale = True
            self.hitboxes = []
            self.suggestion = None
            return STRINGS["source_edited"]

        return self._run(action)

    def rebuild_reload(self) -> bool:
        """Reload and restore the selection before publishing fresh data."""
        saved_row, saved_frame = self.row, self.frame

        def action():
            self._request("rebuild")
            self.stale = True
            self._request("reload")

            rows = self._items(self._request("list_rows"), "rows")
            parsed = None
            if saved_row:
                self._request("load_row", {"row": saved_row})
                result = self._request("set_frame", {"frame": saved_frame})
                parsed = self._read_frame(result, saved_row)

            self.rows = rows
            if parsed is not None:
                self._store_frame(parsed)
            else:
                self.info = None
            self.hitboxes = []
            self.problems = []
            self.suggestion = None
            self.stale = False
            return STRINGS["reloaded"]

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
        """Explain why the last reply cannot be posed, without rejecting data."""
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
