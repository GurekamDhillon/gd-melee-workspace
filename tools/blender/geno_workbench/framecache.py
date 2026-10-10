"""Row frame cache: every frame of a move, fetched once on a background thread.

Standard library only; no bpy. The worker thread talks to the engine through the
injected ``fetch(frame)`` and never touches Blender. The main thread reads the
cache (``get``) and polls ``progress``; playback and scrubbing then cost no
engine call at all.

Entries are tagged with a generation. Anything that changes what the engine
would answer (a source edit, rebuild/reload, restart, a facing change, another
row) calls ``reset``, which bumps the generation; a worker finishing a stale
request stores nothing.
"""

from __future__ import annotations

import threading
import time

MAX_FRAMES = 600


class FrameCache:
    def __init__(self):
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self._thread = None
        self.generation = 0
        self.row = ""
        self.facing = None
        self.frames: dict[int, dict] = {}
        self.wanted = 0          # frames the current request covers (progress denominator)
        self.error = ""          # why the last fetch stopped early ("" = it did not)
        self.end_hint = 0        # last valid frame, when the engine said a request was past the end
        self.seconds = 0.0       # wall time of the last completed fill
        self.reason = ""

    # ---- state ------------------------------------------------------------
    @property
    def loading(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def progress(self) -> tuple[int, int]:
        with self._lock:
            return len(self.frames), self.wanted

    def has(self, row: str, frame: int) -> bool:
        return self.get(row, frame) is not None

    def get(self, row: str, frame: int):
        """The cached reply for (row, frame), or None. Safe from any thread."""
        with self._lock:
            if row != self.row:
                return None
            return self.frames.get(frame)

    def missing(self, row: str, first: int, last: int) -> list[int]:
        with self._lock:
            if row != self.row:
                return list(range(first, last + 1))
            return [n for n in range(first, last + 1) if n not in self.frames]

    # ---- control ----------------------------------------------------------
    def cancel(self, wait: bool = True) -> None:
        """Ask the worker to stop; wait for it so no engine call trails the caller's."""
        self._cancel.set()
        thread = self._thread
        if wait and thread is not None and thread is not threading.current_thread():
            thread.join(timeout=3.0)
        if thread is not None and not thread.is_alive():
            self._thread = None

    def reset(self, reason: str = "") -> None:
        """Forget everything: the engine's answers may differ now."""
        self.cancel(wait=True)
        with self._lock:
            self.generation += 1
            self.frames = {}
            self.row = ""
            self.facing = None
            self.wanted = 0
            self.error = ""
            self.end_hint = 0
            self.reason = reason

    def begin(self, row: str, first: int, last: int, fetch) -> bool:
        """Fetch the frames of ``row`` in [first, last] that are not cached yet.

        Returns False when nothing needs fetching. ``fetch(n)`` returns the
        reply dict for frame n or raises; the first exception ends the fill
        (``error`` holds its text, ``end_hint`` the last valid frame when it
        was a past-the-end answer).
        """
        self.cancel(wait=True)
        last = min(last, MAX_FRAMES)
        with self._lock:
            if row != self.row:
                self.generation += 1
                self.frames = {}
                self.row = row
            todo = [n for n in range(first, last + 1) if n not in self.frames]
            self.wanted = last - first + 1
            self.error = ""
            self.end_hint = 0
            generation = self.generation
        if not todo:
            return False
        self._cancel = threading.Event()
        cancel = self._cancel
        started = time.perf_counter()

        def work():
            for n in todo:
                if cancel.is_set():
                    return
                try:
                    reply = fetch(n)
                except Exception as exc:  # noqa: BLE001 - reported, never raised through the thread
                    with self._lock:
                        if generation == self.generation:
                            self.error = str(exc) or type(exc).__name__
                    return
                with self._lock:
                    if generation != self.generation or cancel.is_set():
                        return
                    self.frames[n] = reply
            with self._lock:
                if generation == self.generation:
                    self.seconds = time.perf_counter() - started

        self._thread = threading.Thread(target=work, name="geno-wb-frame-cache", daemon=True)
        self._thread.start()
        return True

    def truncate(self, last: int) -> None:
        """The move turned out to end at ``last``: drop anything beyond and shrink the target."""
        with self._lock:
            for n in [n for n in self.frames if n > last]:
                del self.frames[n]
            self.wanted = min(self.wanted, last) if self.wanted else last
