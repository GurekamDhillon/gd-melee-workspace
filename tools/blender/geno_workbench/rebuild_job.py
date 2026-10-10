"""Rebuild + reload (and Restart engine) off Blender's UI thread. No bpy in this module.

The Workbench used to call the launcher's `rebuild` command from the operator: a blocking socket call
that froze Blender for the whole build (gameplay-only ~15 s, a full Goku build ~5 min). A RebuildJob
does the slow work on a worker thread and is polled from a bpy timer on the main thread:

  worker thread: run the project's rebuild argv (workbench.json "rebuild") ourselves, so its output can
                 drive a progress bar, its "why a full build" line can be shown, and Cancel can kill the
                 process tree; then the engine half (reload, rows, the saved row and frame) as plain
                 requests. It never touches bpy data or session fields the UI reads.
  main thread:   poll() publishes the fetched result (session._rebuild_apply) once the worker is done.

With no argv known (a project that only configures the launcher's rebuild, or a test double), the build
falls back to the server's own `rebuild` command: same result, no live progress, no Cancel.
"""
from __future__ import annotations

import os
import re
import subprocess
import threading
import time
from collections import deque

BUILD_TIMEOUT = 30 * 60.0   # the launcher's own rebuild limit

PHASE_BUILD, PHASE_RESTART, PHASE_ROWS, PHASE_RESTORE = "build", "restart", "rows", "restore"
PHASE_ORDER = (PHASE_BUILD, PHASE_RESTART, PHASE_ROWS, PHASE_RESTORE)
# share of the bar each phase owns: the build is the long one
_PHASE_SPAN = {PHASE_BUILD: (0.0, 90.0), PHASE_RESTART: (90.0, 95.0),
               PHASE_ROWS: (95.0, 97.0), PHASE_RESTORE: (97.0, 100.0)}

_STEP = re.compile(r"^\s*\[(\d+)/(\d+)\]\s*(.*?)\s*$")
_PHASE = re.compile(r"^\s*BUILD_PHASE:\s*(.*?)\s*$")
_MODE = re.compile(r"^\s*BUILD_MODE:\s*(\S+)\s+([0-9]+(?:\.[0-9]+)?)s")
_REASON = re.compile(r"^\s*build:\s*full build needed:\s*(.*?)\s*$")


class BuildProgress:
    """What build.py's output says about the build so far (parsed line by line)."""

    def __init__(self):
        self.fraction = 0.0      # 0..1 of the build phase
        self.step = ""           # the current step's text
        self.reason = ""         # why a full build was chosen ("build: full build needed: <reason>")
        self.mode = ""
        self.build_seconds: float | None = None
        self.tail: deque[str] = deque(maxlen=40)

    def feed(self, line: str) -> None:
        line = line.rstrip("\r\n")
        if not line.strip():
            return
        self.tail.append(line)
        m = _REASON.match(line)
        if m:
            self.reason = m.group(1)
            return
        m = _MODE.match(line)
        if m:
            self.mode, self.build_seconds, self.fraction = m.group(1), float(m.group(2)), 1.0
            return
        m = _STEP.match(line)
        if m:
            index, total = int(m.group(1)), max(1, int(m.group(2)))
            # progress is the share of steps finished; never run backwards between different [i/n] series
            self.fraction = max(self.fraction, min(0.95, (index - 1) / total))
            self.step = m.group(3)
            return
        m = _PHASE.match(line)
        if m:
            self.step = m.group(1)

    def built(self) -> dict:
        out = {}
        if self.mode and self.build_seconds is not None:
            out = {"mode": self.mode, "build_seconds": self.build_seconds}
        return out


def work_dir(project_dir: str) -> str:
    """The build's working directory: the nearest ancestor with .git (the launcher does the same)."""
    here = os.path.abspath(project_dir)
    probe = here
    while True:
        if os.path.exists(os.path.join(probe, ".git")):
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            return here
        probe = parent


def expand_argv(argv, project_dir: str) -> list[str]:
    package = os.path.join(project_dir, "package")
    return [a.replace("{project}", project_dir).replace("{package}", package) for a in argv]


def kill_tree(proc) -> None:
    """Stop the build and everything it started (child pythons, Blender, dotnet) and nothing else."""
    pid = getattr(proc, "pid", None)
    try:
        if os.name == "nt" and pid:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=30,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        elif pid:
            import signal
            os.killpg(os.getpgid(pid), signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        proc.kill()   # the direct child, if the tree kill could not
    except OSError:
        pass


def spawn(argv, cwd, env):
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, **kwargs)


class JobError(RuntimeError):
    pass


class RebuildJob:
    """One background Rebuild + reload (kind="rebuild") or Restart engine (kind="restart")."""

    def __init__(self, session, kind: str = "rebuild", *, argv=None, cwd=None, env=None,
                 popen=None, killer=None, clock=time.monotonic, timeout: float = BUILD_TIMEOUT):
        self.session = session
        self.kind = kind
        self.argv = list(argv) if argv else []
        self.cwd = cwd
        self.env = env
        self._popen = popen or spawn
        self._killer = killer or kill_tree
        self._clock = clock
        self.timeout = timeout
        self.progress = BuildProgress()
        self.phase = PHASE_BUILD if kind == "rebuild" else PHASE_RESTART
        self.cancelled = False
        self.finished = False        # the worker is done (poll() then publishes)
        self.completed = False       # poll() has published; the job is over
        self.error: Exception | None = None
        self.status_text = ""
        self.ok = False
        self._lock = threading.Lock()
        self._proc = None
        self._thread: threading.Thread | None = None
        self._data = None
        self._built = {}
        self._started = 0.0
        self._timed_out = False
        self._was_stale = False

    # -- main-thread API ------------------------------------------------------------------------------
    @property
    def can_cancel(self) -> bool:
        return self.kind == "rebuild" and self.phase == PHASE_BUILD and bool(self.argv) and not self.finished

    @property
    def elapsed(self) -> float:
        return max(0.0, self._clock() - self._started) if self._started else 0.0

    @property
    def percent(self) -> float:
        low, high = _PHASE_SPAN[self.phase] if self.kind == "rebuild" else (0.0, 100.0)
        if self.kind == "restart":
            return 50.0
        if self.phase == PHASE_BUILD:
            return low + (high - low) * self.progress.fraction
        return low

    @property
    def detail(self) -> str:
        return self.progress.step if self.phase == PHASE_BUILD else ""

    def start(self) -> None:
        s = self.session
        s.busy = self.kind
        self._was_stale = s.stale
        if self.kind == "rebuild":
            s.stale = True   # every failure from here leaves the stale indication visible
        s.pause_prefetch()   # the prefetch worker must not race the engine; cached frames stay
        self._saved = (s.source_row, s.frame, bool(s.attributes))
        self._started = self._clock()
        self._thread = threading.Thread(target=self._work, name="geno-wb-rebuild", daemon=True)
        self._thread.start()

    def cancel(self) -> bool:
        """Kill the build (only while it is building). The engine is not touched."""
        with self._lock:
            if not self.can_cancel:
                return False
            self.cancelled = True
            proc = self._proc
        if proc is not None:
            self._killer(proc)
        return True

    def poll(self) -> bool:
        """Main thread, from a timer. True once the job is over and its result is published."""
        if self.completed:
            return True
        if not self.finished:
            return False
        s = self.session
        try:
            if self.cancelled:
                s.stale = True   # the package may be partly built
                s.set_status(_cancel_text())
            elif self.error is not None:
                self.ok = False
                s.report_error(self.error)   # keeps the row, frame and cache; stale stays visible
            elif self.kind == "restart":
                self.ok = s.set_status(s._engine_restart_apply(self._data))
            else:
                text = s._rebuild_apply(self._data, self._built, self._started, self.progress.reason)
                self.ok = s.set_status(text)
        except Exception as exc:   # a hook or a malformed reply must still end the job
            self.ok = s.report_error(exc) and False
        finally:
            s.busy = ""
            if s.connected:
                s.start_prefetch()
            self.completed = True
        return True

    # -- worker thread ----------------------------------------------------------------------------------
    def _note(self, phase: str) -> None:
        self.phase = phase

    def _work(self) -> None:
        s = self.session
        try:
            if self.kind == "restart":
                s.pending_frame = None
                s.cache.reset("engine restart")
                self._data = s._request("engine_restart")
                return
            if self.argv:
                self._build()
            else:
                self._built = s._request("rebuild")
            if self.cancelled:
                return
            self._data = s._rebuild_fetch(*self._saved, progress=self._note)
        except Exception as exc:
            self.error = exc
        finally:
            self.finished = True

    def _build(self) -> None:
        proc = self._popen(self.argv, cwd=self.cwd, env=self.env)
        with self._lock:
            self._proc = proc
            cancelled = self.cancelled
        if cancelled:
            self._killer(proc)
        watchdog = threading.Timer(self.timeout, self._expire)
        watchdog.daemon = True
        watchdog.start()
        try:
            for raw in proc.stdout:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", "replace")
                self.progress.feed(raw)
            code = proc.wait()
        finally:
            watchdog.cancel()
        if self.cancelled:
            return
        if self._timed_out:
            raise JobError("rebuild timed out: " + self._tail())
        if code != 0:
            raise JobError("rebuild failed: exit %s: %s" % (code, self._tail()))
        self._built = self.progress.built()

    def _expire(self) -> None:
        self._timed_out = True
        proc = self._proc
        if proc is not None:
            self._killer(proc)

    def _tail(self) -> str:
        return "\n".join(list(self.progress.tail)[-6:])[-300:]


def _cancel_text() -> str:
    try:
        from .props import STRINGS
    except ImportError:
        try:
            from props import STRINGS
        except ImportError:
            return "rebuild cancelled"
    return STRINGS["rebuild_cancelled"]
