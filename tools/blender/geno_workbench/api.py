"""Standard-library session API for the Geno Workbench front end.

Frame replies are validated before replacing cached data. Source edits never
replace engine frame data or invoke frame hooks. This module does not import
bpy or write project files.
"""

from __future__ import annotations

import inspect
import json
import math
import os
import re
import time
from typing import Callable

try:
    from . import client, framecache, travel, wbspace
    from . import attributes as attribute_model
    from .props import STRINGS
except ImportError:
    import client
    import attributes as attribute_model
    import framecache
    import travel
    import wbspace
    from props import STRINGS


EDITABLE = (
    "bone", "damage", "size", "x", "y", "z", "angle", "kbg", "fkb", "bkb",
    "start_frame", "end_frame", "element", "shield", "slot", "ground", "air",
)

# The limits the launcher's edit_hitbox enforces, checked here first so a bad value never leaves Blender.
ELEMENT_RANGE = (0, 31)       # source element code; 0..16 are the retail HitElement ids
SHIELD_RANGE = (-128, 127)    # signed shield damage (Metal Sonic's -3 is legal)
SLOT_RANGE = (0, 3)           # hitbox slots; slot 4+ waits for ws/research-ace-hitbox-slot4 (not writable yet)
BOOL_FIELDS = ("ground", "air")   # hit_ground / hit_air: False = cannot hit grounded / airborne targets

# what add_hitbox may set besides the frame and bone; the server fills the rest with defaults
# A hitbox that is never cleared runs to the playback cap (props/operators stop at engine frame 600).
OPEN_END_FRAME = 600
ADDABLE = frozenset(("damage", "size", "x", "y", "z", "angle", "kbg", "fkb", "bkb", "duration"))

_TRANSPORT_FAILURES = (
    "closed", "refused", "timeout", "timed out", "connection reset",
    "reset by peer", "broken pipe", "connection aborted", "connection lost",
    "disconnected", "not connected", "end of file", "eof",
)


# A frame that cannot be shown (the move ended before it) is the server answering, not the link failing.
_NOT_TRANSPORT = ("requested frame", "past the end")


# seconds a tool may run before the add-on gives up on it (the launcher's own rebuild limit is 30 min)
LONG_CALLS = {"rebuild": 2000.0, "reload": 300.0, "engine_restart": 300.0}


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
        self.attributes: list[dict] = []
        self.attributes_current = False
        self.last_attribute_edit: dict = {}
        self.problems: list[dict] = []
        self.stale = False
        self.job = None   # the running rebuild_job.RebuildJob (set by the operator that started it)
        self.busy = ""   # why other Workbench actions are disabled while a background rebuild/restart runs
        self.rebuild_argv: list[str] = []   # workbench.json "rebuild" (the add-on runs it itself to show progress and cancel)
        self.last_rebuild: dict | None = None  # {mode, build_seconds, total_seconds} of the last Rebuild + reload
        self.last_error = ""
        self.suggestion: dict | None = None
        self.roles: list[dict] = []   # list_hitbox_roles: [{name, group, joint}] the project's joint=@ROLE@ names (empty: unknown)
        self.last_added: int | None = None   # ordinal of the hitbox the last add_hitbox created
        self.jointmap = None
        self.calibration = None
        self.on_change: Callable[[WbSession], None] | None = None
        self.on_frame: list[Callable[[WbSession], None]] = []
        self.hook_error = ""
        self.project_dir = ""
        self.plan_path = ""
        self.art_blend = ""
        self.art_glb = ""
        # what the project says it can do (workbench.json "rebuild", the plan's "roles"); True when unknown
        self.can_rebuild = True
        self.has_roles = True
        self.bone_aliases: dict[str, str] = {}
        # engine frame the add-on calibrates at (action frame = this - 1); 1 unless retail blending needs a later one
        self.calibration_frame = 1
        self.travel_anchor = None   # root position the in-place view keeps fixed (the row's first frame)
        self.loaded_row = ""   # the name given to load_row (list_rows' name; self.row is the engine's label)
        self.row_lengths: dict[str, int] = {}   # learned from the server when a frame is past a move's end
        self.cache = framecache.FrameCache()   # every frame of the loaded row (R1); filled off the main thread
        self.prefetch = False   # the add-on turns this on; plain API users keep one engine call per frame
        self.cache_hits = 0
        self.engine_calls = 0   # set_frame requests that went to the engine (cache misses)

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
        lowered = self.last_error.lower()
        if (any(word in lowered for word in _TRANSPORT_FAILURES)
                and not any(word in lowered for word in _NOT_TRANSPORT)):
            previous, self.client = self.client, None
            self.connected = False
            self.pending_frame = None
            self.cache.reset("transport failure")
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
        # The socket client's default 10 s budget is far below a rebuild (gameplay-only ~15 s, full ~5 min)
        # or an engine reload; those tools get their own, long, budget. Clients that cannot take one (the
        # one-shot CLI client has its own lifetime, test doubles) are called as before.
        budget = LONG_CALLS.get(tool)
        if budget is not None and "timeout" in inspect.signature(connection.call).parameters:
            result = connection.call(tool, args or {}, timeout=budget)
        else:
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

    @classmethod
    def _ranged(cls, value, field: str, bounds) -> int:
        low, high = bounds
        number = cls._integer(value, field, low)
        if number > high:
            raise client.WbError(STRINGS["invalid_range"].format(field=field, minimum=low, maximum=high))
        return number

    @staticmethod
    def _flag(value, field: str) -> bool:
        if not isinstance(value, bool):
            raise client.WbError(STRINGS["invalid_flag"].format(field=field))
        return value

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

    @property
    def source_row(self) -> str:
        """The row NAME the server knows (list_rows' name, e.g. "dair"), for every request that takes a row.

        self.row is the engine's label for the loaded move (e.g. the clip "AttackAirLw"), which is for display only.
        """
        return self.loaded_row or self.row

    def row_frames(self, name: str = "") -> int:
        """Frames in the loaded move: what the server taught us, else list_rows' count; 0 = unknown."""
        name = name or self.loaded_row
        learned = self.row_lengths.get(name, 0)
        if learned:
            return learned
        for item in self.rows:
            if item.get("name") == name or item.get("row") == name:
                count = item.get("frames")
                if isinstance(count, int) and not isinstance(count, bool) and count > 0:
                    return count
        return 0

    @staticmethod
    def _past_end(error, wanted: int):
        """The move's last frame when the server says `wanted` is past its end, else None."""
        text = str(error)
        if "past the end" not in text:
            return None
        found = re.search(r"last frame (\d+)", text)
        last = int(found.group(1)) if found else wanted - 1
        return last if last >= 1 else None

    def _frame_status(self) -> str:
        text = STRINGS["frame_loaded"].format(row=self.row, frame=self.frame)
        return f"{text}; {self.hook_error}" if self.hook_error else text

    @staticmethod
    def source_boxes(items) -> list[dict]:
        """Source hitbox records the way the Blender UI shows them: end_frame is the LAST ACTIVE frame.

        The server (and the .genoasm) store end_frame as the frame the hitbox is cleared on, so a window
        written start=3 / end=5 is active on frames 3 and 4 and the UI says "3-4". A hitbox that is never
        cleared (end_frame -1) is shown running to the playback cap. edit_hitbox converts back (+1).
        """
        out = []
        for item in items:
            box = dict(item)
            end = box.get("end_frame")
            if isinstance(end, int) and not isinstance(end, bool):
                box["end_frame"] = end - 1 if end >= 0 else OPEN_END_FRAME
            out.append(box)
        return out

    def _source_hitboxes(self, row: str) -> list[dict]:
        return self.source_boxes(self._items(
            self._request("list_hitboxes", {"row": row}), "hitboxes"
        ))

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
        self.cache.reset("connect")
        self.attributes = []
        self.attributes_current = False
        self.last_attribute_edit = {}
        self.rows = []
        self.row = ""
        self.loaded_row = ""
        self.travel_anchor = None
        self.row_lengths = {}
        self.frame = 0
        self.pending_frame = None
        self.info = None
        self.hitboxes = []
        self.problems = []
        self.suggestion = None
        self.jointmap = None
        self.calibration = None
        self.hook_error = ""
        self.roles = self._load_roles()
        # Reconnecting is not evidence that an edited source was rebuilt.
        return self.set_status(
            STRINGS["connected"].format(
                engine=result.get("status", STRINGS["unknown"])
            )
        )

    def _load_roles(self) -> list[dict]:
        """The bone names the project's scripts accept; a server without the command leaves the list empty."""
        try:
            roles = self._items(self._request("list_hitbox_roles"), "roles")
        except client.WbError:
            return []
        return [r for r in roles if isinstance(r.get("name"), str) and r["name"]]

    def disconnect(self) -> bool:
        self.cache.reset("disconnect")
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
        self.cache.reset("load_row")

        def action():
            row = self._row_name(name)
            loaded = self._request("load_row", {"row": row})
            if "bones" not in loaded:
                # The real server answers load_row with {"ok": true}; the first frame follows.
                loaded = self._request("set_frame", {"frame": 1})
            parsed = self._read_frame(loaded, row)
            boxes = self._source_hitboxes(row) if refresh_hitboxes else []
            self.loaded_row = row
            self._store_frame(parsed)
            self.travel_anchor = travel.anchor_of(self.info)
            self.hitboxes = boxes
            self.suggestion = None
            self._fire_frame()
            self.start_prefetch()
            return self._frame_status()

        return self._run(action)

    # ---- row frame cache (R1) ----------------------------------------------
    def start_prefetch(self) -> bool:
        """Fill the cache for the loaded row on a background thread (no bpy there).

        Safe to call repeatedly: only frames not cached yet are fetched.
        """
        if not (self.prefetch and self.connected and self.client is not None and self.loaded_row):
            return False
        last = self.row_frames() or framecache.MAX_FRAMES
        connection = self.client

        def fetch(frame: int) -> dict:
            result = self._raw_call(connection, "set_frame", {"frame": frame})
            if result.get("frame") != frame:
                raise client.WbError(
                    f"frame {frame} is past the end of this move (got {result.get('frame')})")
            return result

        return self.cache.begin(self.loaded_row, 1, last, fetch)

    def pause_prefetch(self) -> None:
        """Stop the worker before a tool that moves the engine; the cached frames stay valid."""
        self.cache.cancel(wait=True)

    def invalidate_cache(self, reason: str = "") -> None:
        self.cache.reset(reason)

    def pump_cache(self):
        """Main-thread housekeeping: learn a move's length from the worker. Returns (done, total, loading)."""
        error = self.cache.error
        if error and not self.cache.loading:
            if "past the end" in error:
                last = self._past_end(error, 0)
                if last is None and self.cache.frames:
                    last = max(self.cache.frames)
                if last:
                    self.row_lengths[self.loaded_row] = last
                    self.cache.truncate(last)
            self.cache.error = ""
        done, total = self.cache.progress()
        return done, total, self.cache.loading

    def cache_ready(self) -> bool:
        done, total, loading = self.pump_cache()
        return not loading and total > 0 and done >= total

    def cache_text(self) -> str:
        done, total, loading = self.pump_cache()
        if loading:
            return STRINGS["cache_loading"].format(done=done, total=total)
        if total and done >= total:
            return STRINGS["cache_ready"].format(total=total)
        return ""

    def set_frame(self, n) -> bool:
        self.pending_frame = None

        def action():
            frame = self._integer(n, "frame")
            limit = self.row_frames()
            if limit and frame > limit:
                frame = limit
            cached = self.cache.get(self.loaded_row, frame) if self.loaded_row else None
            if cached is not None:
                self.cache_hits += 1
                self._store_frame(self._read_frame(dict(cached), self.row))
                self._fire_frame()
                return self._frame_status()
            self.engine_calls += 1
            try:
                result = self._request("set_frame", {"frame": frame})
            except client.WbError as exc:
                last = self._past_end(exc, frame)
                if last is None:
                    raise
                # the move is shorter than we thought: remember it and show its last frame instead
                self.row_lengths[self.loaded_row] = last
                self.cache.truncate(last)
                frame = last
                result = self._request("set_frame", {"frame": frame})
            self._note_facing(result)
            self._store_frame(self._read_frame(result, self.row))
            self._fire_frame()
            return self._frame_status()

        return self._run(action)

    def _note_facing(self, result: dict) -> None:
        """A live frame whose facing differs from the cached ones means the cache is stale."""
        facing = result.get("facing")
        if facing is None:
            return
        known = self.cache.facing
        if known is None:
            self.cache.facing = facing
        elif known != facing:
            self.cache.reset("facing")
            self.cache.facing = facing

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
        limit = self.row_frames()
        self.pending_frame = min(frame, limit) if limit else frame
        return True

    def flush_pending(self) -> bool:
        """Send the latest queued frame once; False also means no work."""
        frame = self.pending_frame
        if frame is None:
            return False
        self.pending_frame = None
        return self.set_frame(frame)

    def refresh_attributes(self) -> bool:
        def action():
            self.attributes_current = False
            rows = attribute_model.normalize_rows(
                self._items(self._request("list_attributes"), "attributes")
            )
            self.attributes = rows
            self.attributes_current = True
            return STRINGS["attributes_loaded"].format(count=len(rows))

        return self._run(action)

    def edit_attribute(self, name: str, value) -> bool:
        """Edit one source value through the server; retain the engine pose until reload."""
        self.last_attribute_edit = {}

        def action():
            if not isinstance(name, str) or not name:
                raise client.WbError(STRINGS["attribute_name_required"])
            if not self.attributes:
                self.attributes = attribute_model.normalize_rows(
                    self._items(self._request("list_attributes"), "attributes")
                )
                self.attributes_current = True
            metadata = next((item for item in self.attributes if item["name"] == name), None)
            if metadata is None:
                raise client.WbError(STRINGS["attribute_unknown"].format(name=name))
            number = attribute_model.validate_value(metadata, value)
            self.pause_prefetch()
            result = self._request("edit_attribute", {"name": name, "value": number})
            if result.get("proposed") is True or "proposal" in result:
                self.last_attribute_edit = {"proposed": True}
                return STRINGS["proposal_created"]
            if result.get("applied") is False:
                self.last_attribute_edit = {"unchanged": True}
                self.attributes = [dict(item, value=number) if item["name"] == name else dict(item)
                                   for item in self.attributes]
                return STRINGS["no_changes"]
            if result.get("applied") is not True:
                raise client.WbError(STRINGS["attribute_edit_reply_invalid"])
            self.last_attribute_edit = {"applied": True}
            self.stale = True
            self.cache.reset("attribute edit")
            # The commit acknowledgement proves this field changed. Keep other last-known
            # metadata so a failed refresh cannot erase the panel's unsent batch drafts.
            self.attributes = [dict(item, value=number, source_file=item.get("write_file", ""))
                               if item["name"] == name else dict(item) for item in self.attributes]
            self.attributes_current = False
            self.attributes = attribute_model.normalize_rows(
                self._items(self._request("list_attributes"), "attributes")
            )
            self.attributes_current = True
            return STRINGS["attribute_source_edited"]

        return self._run(action)

    def refresh_hitboxes(self) -> bool:
        def action():
            row = self._row_name(self.source_row)
            boxes = self._source_hitboxes(row)
            self.hitboxes = boxes
            return STRINGS["hitboxes_loaded"].format(count=len(boxes))

        return self._run(action)

    def _restore_engine_row(self) -> None:
        """Put the engine back on the loaded row and frame (run_checks sweeps every row).

        Failures are swallowed: the session keeps its own row either way, and the
        next uncached frame request reloads it if the engine really lost it.
        """
        if not (self.connected and self.client is not None and self.loaded_row):
            return
        try:
            self._request("load_row", {"row": self.loaded_row})
            if self.frame > 1:
                limit = self.row_frames()
                self._request("set_frame", {"frame": min(self.frame, limit) if limit else self.frame})
        except (client.WbError, OSError, ValueError, TypeError):
            pass

    def run_checks(self) -> bool:
        """Run the engine's checks. They sweep rows and frames, so the engine ends up elsewhere:
        the loaded row is put back whether or not the checks succeed (the session never loses its row)."""
        if not self.has_roles:
            return self.blocked(STRINGS["no_roles"])
        self.pause_prefetch()

        def action():
            try:
                problems = self._items(self._request("run_checks"), "problems")
            finally:
                self._restore_engine_row()
                self.start_prefetch()   # the fill was paused for the sweep; resume it even when the checks failed
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
        boxes = self.hitboxes if name == self.source_row else self._source_hitboxes(name)
        return self._first_active_frame(boxes, ordinal)

    def goto_problem(self, i) -> bool:
        """Publish the problem pose only after all required replies succeed."""
        self.pending_frame = None
        self.cache.reset("goto_problem")

        def action():
            index = self._integer(i, "index")
            if index >= len(self.problems):
                raise client.WbError(STRINGS["problem_missing"])
            problem = self.problems[index]
            row = self._row_name(problem.get("row"))
            ordinal = self._integer(problem.get("ordinal", 0), "ordinal")
            self._request("load_row", {"row": row})  # the real server answers {"ok": true}; set_frame carries the pose
            boxes = self._source_hitboxes(row)
            frame = self._first_active_frame(boxes, ordinal)
            parsed = self._read_frame(
                self._request("set_frame", {"frame": frame}), row
            )
            self.loaded_row = row
            self._store_frame(parsed)
            self.travel_anchor = travel.anchor_of(self.info)
            self.hitboxes = boxes
            self.suggestion = None
            self._fire_frame()
            self.start_prefetch()
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
            row = self._row_name(fields.get("row", self.source_row))
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
                    if field == "end_frame":
                        # the UI's last active frame -> the frame the script clears the hitbox on
                        value = -1 if value >= OPEN_END_FRAME else value + 1
                elif field == "element":
                    value = self._ranged(value, field, ELEMENT_RANGE)
                elif field == "shield":
                    value = self._ranged(value, field, SHIELD_RANGE)
                elif field == "slot":
                    value = self._ranged(value, field, SLOT_RANGE)
                elif field in BOOL_FIELDS:
                    value = self._flag(value, field)
                else:
                    value = self._number(value, field)
                args[field] = value
            if len(args) == 2:
                return STRINGS["no_changes"]

            self.pause_prefetch()
            result = self._request("edit_hitbox", args)
            if "proposal" in result:
                # A proposal must not clear a previous successful source edit.
                return STRINGS["proposal_created"]

            self.stale = True
            self.cache.reset("hitbox edit")
            self.suggestion = None
            if row == self.source_row:
                # If the source refresh fails, do not label the old list as new.
                self.hitboxes = []
            boxes = self._source_hitboxes(row)
            if row == self.source_row:
                self.hitboxes = boxes
            return STRINGS["source_edited"]

        return self._run(action)

    def _after_source_edit(self, row: str) -> None:
        self.stale = True
        self.cache.reset("hitbox edit")
        self.suggestion = None
        if row == self.source_row:
            # If the source refresh fails, do not label the old list as new.
            self.hitboxes = []
        boxes = self._source_hitboxes(row)
        if row == self.source_row:
            self.hitboxes = boxes

    def add_hitbox(self, frame=None, bone=None, row=None, **fields) -> bool:
        """Add a hitbox to the loaded move's source at `frame` (default: the shown frame).

        The server picks a free slot, closes the window itself and, without a bone, a default role.
        Like edit_hitbox it changes the source only; Rebuild + reload applies it.
        """
        def action():
            unknown = set(fields) - ADDABLE
            if unknown:
                raise client.WbError(
                    STRINGS["unsupported_fields"].format(fields=", ".join(sorted(unknown)))
                )
            name = self._row_name(row if row is not None else self.source_row)
            args = {"row": name, "frame": self._integer(self.frame if frame is None else frame, "frame")}
            if bone:
                if not isinstance(bone, str) or not bone.strip():
                    raise client.WbError(STRINGS["bone_required"])
                args["bone"] = bone
            for field, value in fields.items():
                if field in ("angle", "kbg", "fkb", "bkb", "duration"):
                    value = self._integer(value, field)
                else:
                    value = self._number(value, field)
                args[field] = value
            self.pause_prefetch()
            result = self._request("add_hitbox", args)
            if "proposal" in result or result.get("proposed"):
                return STRINGS["proposal_created"]
            self._after_source_edit(name)
            ordinal = result.get("ordinal")
            self.last_added = ordinal if isinstance(ordinal, int) and not isinstance(ordinal, bool) else None
            return STRINGS["hitbox_added"].format(
                ordinal=self.last_added if self.last_added is not None else "?",
                bone=result.get("bone", bone or ""), frame=args["frame"],
            )

        return self._run(action)

    def delete_hitbox(self, ordinal, row=None) -> bool:
        def action():
            name = self._row_name(row if row is not None else self.source_row)
            index = self._integer(ordinal, "ordinal")
            self.pause_prefetch()
            result = self._request("delete_hitbox", {"row": name, "ordinal": index})
            if "proposal" in result or result.get("proposed"):
                return STRINGS["proposal_created"]
            self._after_source_edit(name)
            self.last_added = None
            return STRINGS["hitbox_deleted"].format(ordinal=index)

        return self._run(action)

    def blocked(self, reason: str) -> bool:
        """Refuse an action the project cannot do: a plain status message, no error, nothing touched."""
        self.set_status(reason)
        return False

    def rebuild_reload(self) -> bool:
        """Restore the selection, source list, pose and overlays after reload.

        A failure at any step (no build configured, build failure, timeout, reload error) leaves the
        loaded row, frame and frame cache as they were; only a successful reload re-fetches.
        This is the blocking form (scripts, benches); the Workbench button runs the same steps through
        rebuild_job.RebuildJob so Blender stays responsive.
        """
        if not self.can_rebuild:
            return self.blocked(STRINGS["rebuild_unavailable"])
        saved_row, saved_frame = self.source_row, self.frame
        had_attributes = bool(self.attributes)
        self.pause_prefetch()   # the worker must not race the engine; the cached frames stay

        def action():
            # Every failure from here must leave the stale indication visible.
            self.stale = True
            started = time.monotonic()
            built = self._request("rebuild")
            data = self._rebuild_fetch(saved_row, saved_frame, had_attributes)
            return self._rebuild_apply(data, built, started)

        try:
            ok = self._run(action)
        finally:
            if self.connected:
                self.start_prefetch()   # resume the fill the pause stopped (only missing frames are fetched)
        return ok

    def _rebuild_fetch(self, saved_row: str, saved_frame: int, had_attributes: bool, progress=None) -> dict:
        """The engine half of Rebuild + reload: reload, then re-read rows, the saved row/frame and attributes.

        Only requests and plain data here (no bpy, no hooks), so it may run on a worker thread while the
        main thread keeps Blender alive; _rebuild_apply then publishes the result on the main thread.
        """
        note = progress or (lambda phase: None)
        note("restart")
        self._request("reload")
        self.pending_frame = None
        self.cache.reset("rebuild")   # the engine now runs the new build: old frames are out of date
        note("rows")
        rows = self._items(self._request("list_rows"), "rows")
        parsed = None
        boxes = []
        note("restore")
        if saved_row:
            self._request("load_row", {"row": saved_row})  # real server: {"ok": true}, no pose
            parsed = self._read_frame(
                self._request("set_frame", {"frame": saved_frame}), saved_row
            )
            boxes = self._source_hitboxes(saved_row)
        attributes = None
        if had_attributes:
            attributes = attribute_model.normalize_rows(
                self._items(self._request("list_attributes"), "attributes")
            )
        return {"rows": rows, "parsed": parsed, "boxes": boxes, "attributes": attributes}

    def _rebuild_apply(self, data: dict, built, started: float, reason: str = "") -> str:
        """Publish a fetched rebuild on the main thread; returns the status text."""
        if data["attributes"] is not None:
            self.attributes = data["attributes"]
            self.attributes_current = True
        self.rows = data["rows"]
        parsed = data["parsed"]
        if parsed is not None:
            self._store_frame(parsed)
        else:
            self.info = None
        self.hitboxes = data["boxes"]
        self.problems = []
        self.suggestion = None
        self.stale = False
        if parsed is not None:
            self._fire_frame()
            self.start_prefetch()
        text = STRINGS["reloaded"]
        mode = built.get("mode") if isinstance(built, dict) else None
        seconds = built.get("build_seconds") if isinstance(built, dict) else None
        if isinstance(mode, str) and isinstance(seconds, (int, float)):
            # Which build ran (gameplay-only vs full), why a full one was needed, and how long, end to end.
            self.last_rebuild = {
                "mode": mode, "build_seconds": float(seconds),
                "total_seconds": time.monotonic() - started,
            }
            if reason:
                self.last_rebuild["reason"] = reason
            text = STRINGS["reloaded_mode"].format(
                mode=mode, build=float(seconds),
                total=self.last_rebuild["total_seconds"],
            )
            if reason and mode != "gameplay-only":
                text = f"{text}; " + STRINGS["rebuild_why_full"].format(reason=reason)
        return f"{text}; {self.hook_error}" if self.hook_error else text

    def suggest_bone(self, ordinal) -> bool:
        if not self.has_roles:
            return self.blocked(STRINGS["no_roles"])
        def action():
            row = self._row_name(self.source_row)
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
        self.cache.reset("engine restart")
        return self._run(lambda: self._engine_restart_apply(self._request("engine_restart")))

    def _engine_restart_apply(self, result: dict) -> str:
        self.info = None
        self.row = ""
        self.loaded_row = ""
        self.travel_anchor = None
        self.frame = 0
        self.hitboxes = []
        self.problems = []
        self.suggestion = None
        return STRINGS["restarted"].format(
            engine=result.get("status", STRINGS["unknown"])
        )

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


def _plan_has_roles(plan_path: str) -> bool:
    """False only when the plan is readable and carries no role map; unknown counts as yes."""
    if not plan_path:
        return True
    try:
        with open(plan_path, "r", encoding="utf-8-sig") as source:
            plan = json.load(source)
    except (OSError, ValueError):
        return True
    return not isinstance(plan, dict) or bool(plan.get("roles"))


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
        cal_frame = art.get("calibration_frame", 1)
        if isinstance(cal_frame, bool) or not isinstance(cal_frame, int) or cal_frame < 1:
            raise ValueError("art.calibration_frame must be an integer >= 1")
        sess.calibration_frame = cal_frame
        rebuild = config.get("rebuild")
        sess.can_rebuild = bool(rebuild) if "rebuild" in config else True
        sess.rebuild_argv = [str(a) for a in rebuild] if isinstance(rebuild, list) and rebuild and all(
            isinstance(a, str) and a for a in rebuild) else []
        sess.has_roles = _plan_has_roles(sess.plan_path)
    except (OSError, ValueError, TypeError) as exc:
        sess.last_error = str(exc)
        sess.status = sess._status_with_stale(
            STRINGS["error_status"].format(error=exc)
        )
        return False
    return True


GAME_FPS = 60.0
PLAY_SPEEDS = ("1", "0.5", "0.25", "scene")


def playback_rate(speed, scene_fps):
    """Logic frames per second for a Speed setting: real game speed (60) times the
    multiplier, or the scene's own frame rate for "scene"."""
    if speed == "scene":
        return max(1.0, float(scene_fps))
    try:
        return max(1.0, GAME_FPS * float(speed))
    except (TypeError, ValueError):
        return GAME_FPS
