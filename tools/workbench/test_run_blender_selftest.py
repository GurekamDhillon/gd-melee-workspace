"""Portable runner checks plus the optional real Blender integration test."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import time

import pytest


_RUNNER_PATH = Path(__file__).resolve().with_name("run_blender_selftest.py")
_SPEC = importlib.util.spec_from_file_location(
    "_geno_wb_selftest_runner_tests", _RUNNER_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
runner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(runner)


def test_no_blender_returns_77(monkeypatch, capsys):
    monkeypatch.setattr(
        runner.launch, "find_blender", lambda **kwargs: None
    )
    assert runner.main([]) == 77
    assert capsys.readouterr().out.strip() == "SKIP: no Blender"


def test_streams_markers_and_preserves_exit_code(capsys):
    code = (
        "import sys\n"
        "print('ordinary Blender output', flush=True)\n"
        "print('GENO_WB_CHECK stream OK', flush=True)\n"
        "sys.exit(7)\n"
    )
    result = runner.stream_process([sys.executable, "-u", "-c", code], timeout=10)
    captured = capsys.readouterr()
    assert result == 7
    assert "GENO_WB_CHECK stream OK" in captured.out
    assert "ordinary Blender output" not in captured.out
    assert "ordinary Blender output" in captured.err


def test_timeout_is_bounded(capsys):
    code = "import time\ntime.sleep(30)\n"
    started = time.monotonic()
    result = runner.stream_process(
        [sys.executable, "-u", "-c", code], timeout=0.25
    )
    elapsed = time.monotonic() - started
    captured = capsys.readouterr()
    assert result == 124
    assert elapsed < 10
    assert "GENO_WB_SELFTEST FAIL timeout" in captured.out


def test_run_blender_selftest():
    completed = subprocess.run(
        [sys.executable, "-u", str(_RUNNER_PATH)],
        cwd=str(_RUNNER_PATH.parents[2]),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=360,
        check=False,
    )
    if completed.returncode == 77:
        pytest.skip(completed.stdout.strip() or "SKIP: no Blender")
    assert completed.returncode == 0, completed.stdout
    assert "GENO_WB_SELFTEST OK" in completed.stdout, completed.stdout
