"""Rebuild + reload off the UI thread: progress parsing, the state machine, cancel, failure keeps the row.

The build is a fake process (a Popen stand-in fed scripted lines); the engine is fake_engine.
"""
import threading
import time

import api
import client
import props
import rebuild_job
from fake_engine import FakeWorkbench


class FakeProc:
    """Popen stand-in: stdout yields the scripted lines, optionally blocking on `gate`."""

    def __init__(self, lines, code=0, gate=None):
        self.pid = 4242
        self.killed = False
        self.code = code
        self._lines = list(lines)
        self._gate = gate
        self._dead = threading.Event()
        self.stdout = self._iter()

    def _iter(self):
        for line in self._lines:
            yield line
        if self._gate is not None:
            while not self._dead.is_set():
                if self._gate.wait(0.01):
                    break
        if self.killed:
            self.code = -9

    def wait(self):
        return self.code

    def kill(self):
        self.killed = True
        self._dead.set()


def make_session():
    fake = FakeWorkbench()
    port = fake.start()
    session = api.WbSession(lambda: client.McpClient(port=port, timeout=2.0))
    session.connect()
    session.refresh_rows()
    session.load_row("jab")
    session.set_frame(6)
    return fake, session


def wait_done(job, limit=10.0):
    end = time.monotonic() + limit
    while not job.poll():
        assert time.monotonic() < end, "job did not finish"
        time.sleep(0.005)
    return job


def run_job(job, limit=10.0):
    job.start()
    return wait_done(job, limit)


def job_for(session, proc, **kw):
    return rebuild_job.RebuildJob(session, "rebuild", argv=["python", "build.py"], cwd=".", env={},
                                  popen=lambda argv, cwd, env: proc, **kw)


# -- progress parsing -------------------------------------------------------------------------------

def test_progress_parses_steps_reason_and_mode():
    p = rebuild_job.BuildProgress()
    p.feed("build: full build needed: animation input changed: goku.blend\n")
    assert p.reason == "animation input changed: goku.blend"
    p.feed("[2/5] plan, mesh and animation bank -> out\n")
    assert abs(p.fraction - 0.2) < 1e-9 and p.step.startswith("plan, mesh")
    p.feed("[1/3] reapply gameplay\n")        # another series never runs the bar backwards
    assert abs(p.fraction - 0.2) < 1e-9
    p.feed("BUILD_PHASE: audit gameplay\n")
    assert p.step == "audit gameplay"
    p.feed("BUILD_MODE: full 312.4s\n")
    assert (p.mode, p.build_seconds, p.fraction) == ("full", 312.4, 1.0)
    assert p.built() == {"mode": "full", "build_seconds": 312.4}


def test_progress_ignores_noise_and_caps_steps_below_done():
    p = rebuild_job.BuildProgress()
    for line in ("", "   \n", "random text", "[5/5] install\n"):
        p.feed(line)
    assert p.fraction < 1.0 and p.mode == "" and p.built() == {}


def test_expand_argv_and_work_dir(tmp_path):
    (tmp_path / ".git").write_text("gitdir: x")
    project = tmp_path / "ports" / "g"
    project.mkdir(parents=True)
    assert rebuild_job.work_dir(str(project)) == str(tmp_path)
    got = rebuild_job.expand_argv(["py", "{project}", "{package}/x"], str(project))
    assert got[1] == str(project) and got[2].endswith("x") and "{" not in got[2]


# -- the state machine ------------------------------------------------------------------------------

def test_successful_rebuild_reloads_and_keeps_row_and_frame():
    fake, s = make_session()
    try:
        lines = ["build: full build needed: Stage A inputs changed\n", "[1/5] validate\n", "[3/5] models\n",
                 "BUILD_MODE: full 12.5s\n"]
        job = run_job(job_for(s, FakeProc(lines)))
        assert job.ok and not s.stale and s.busy == ""
        assert s.source_row == "jab" and s.frame == 6
        assert s.last_rebuild["mode"] == "full" and s.last_rebuild["reason"] == "Stage A inputs changed"
        assert "full build because: Stage A inputs changed" in s.status
        assert job.phase == rebuild_job.PHASE_RESTORE
    finally:
        fake.stop()


def test_gameplay_only_status_has_no_reason():
    fake, s = make_session()
    try:
        job = run_job(job_for(s, FakeProc(["[1/3] reapply gameplay\n", "BUILD_MODE: gameplay-only 14.0s\n"])))
        assert job.ok and "gameplay-only build 14.0" in s.status and "because" not in s.status
    finally:
        fake.stop()


def test_failed_build_keeps_row_frame_and_stale_and_reports_tail():
    fake, s = make_session()
    try:
        info, row = dict(s.info), s.source_row
        job = run_job(job_for(s, FakeProc(["[1/5] validate\n", "STOPPED: fix the blockers above\n"], code=1)))
        assert not job.ok and s.stale and s.busy == ""
        assert "exit 1" in s.last_error and "STOPPED" in s.last_error
        assert s.info == info and s.source_row == row and s.frame == 6
    finally:
        fake.stop()


def test_cancel_kills_the_build_and_never_reloads_the_engine():
    fake, s = make_session()
    try:
        gate = threading.Event()
        proc = FakeProc(["[1/5] validate\n"], gate=gate)
        killed = []
        job = job_for(s, proc, killer=lambda p: (killed.append(p), p.kill()))
        job.start()
        deadline = time.monotonic() + 5
        while job.progress.step != "validate":
            assert time.monotonic() < deadline
            time.sleep(0.005)
        assert job.can_cancel and s.busy == "rebuild"
        assert job.cancel() and killed == [proc]
        wait_done(job, 5)
        assert job.cancelled and not job.ok
        assert s.busy == "" and s.stale and "cancelled" in s.status
        assert s.source_row == "jab" and s.frame == 6          # the loaded row is as it was
        assert job.cancel() is False
    finally:
        fake.stop()


def test_cannot_cancel_after_the_build_phase():
    fake, s = make_session()
    try:
        job = run_job(job_for(s, FakeProc(["BUILD_MODE: gameplay-only 1.0s\n"])))
        assert job.cancel() is False and not s.stale
    finally:
        fake.stop()


def test_no_argv_falls_back_to_the_servers_rebuild_without_cancel():
    fake, s = make_session()
    try:
        job = rebuild_job.RebuildJob(s, "rebuild")
        assert job.can_cancel is False
        run_job(job)
        assert job.ok and s.last_rebuild["mode"] == fake.build_mode and not s.stale
    finally:
        fake.stop()


def test_timeout_kills_a_hung_build():
    fake, s = make_session()
    try:
        proc = FakeProc([], gate=threading.Event())
        job = job_for(s, proc, timeout=0.05, killer=lambda p: p.kill())
        run_job(job)
        assert proc.killed and "timed out" in s.last_error and s.stale
    finally:
        fake.stop()


def test_engine_restart_job_clears_the_loaded_row():
    fake, s = make_session()
    try:
        job = run_job(rebuild_job.RebuildJob(s, "restart"))
        assert job.ok and s.busy == "" and s.loaded_row == "" and "engine restarted" in s.status
        assert job.can_cancel is False
    finally:
        fake.stop()


def test_ui_thread_stays_free_while_the_build_runs():
    """poll() returns immediately while the worker is blocked: the main thread is never held."""
    fake, s = make_session()
    try:
        gate = threading.Event()
        job = job_for(s, FakeProc(["[2/5] plan\n"], gate=gate))
        job.start()
        t0 = time.monotonic()
        ticks = 0
        while time.monotonic() - t0 < 0.3:
            assert job.poll() is False
            ticks += 1
            time.sleep(0.01)
        assert ticks > 10 and s.busy == "rebuild"
        gate.set()
        wait_done(job)
        assert job.ok
    finally:
        fake.stop()


# -- disabling conflicting operators ------------------------------------------------------------------

def test_guard_busy_disables_polls_with_a_reason():
    class Op:
        bl_idname = "geno_wb.x"
        reason = ""

        @classmethod
        def poll_message_set(cls, reason):
            cls.reason = reason

        @classmethod
        def poll(cls, context):
            return True

    class Free:
        bl_idname = "geno_wb.rebuild_cancel"
        poll_message_set = Op.poll_message_set

        @classmethod
        def poll(cls, context):
            return True

    class NoPoll:
        bl_idname = "geno_wb.y"
        reason = ""
        poll_message_set = Op.poll_message_set

    props.guard_busy([Op, Free, NoPoll], allow=("geno_wb.rebuild_cancel",))
    session = api.session()
    session.busy = ""
    assert Op.poll(None) and NoPoll.poll(None)
    session.busy = "rebuild"
    try:
        assert Op.poll(None) is False and Op.reason == props.STRINGS["rebuild_running"]
        assert NoPoll.poll(None) is False
        assert Free.poll(None) is True
    finally:
        session.busy = ""


def test_progress_text_names_phase_step_and_percent():
    class J:
        phase, detail, percent, elapsed = "build", "models", 36.0, 12.0

    assert props.rebuild_progress_text(J) == "Building: models 36% (12 s)"
    J.phase, J.detail = "restart", ""
    assert props.rebuild_progress_text(J) == "Restarting engine: 36% (12 s)"
