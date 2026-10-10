"""Launcher and Blender discovery, argument construction, and serve startup.

Explicit executable settings are returned as supplied, without existence
checks. start_serve owns startup failure cleanup and continuously drains the
server's output after returning its process and port.
"""

from __future__ import annotations

from collections import deque
import math
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import threading
import time
from typing import Mapping, Sequence

if __package__:
    from .client import WbError
else:
    from client import WbError


_SERVE_LINE = re.compile(r"\s*WB_SERVE\s+port=([0-9]+)\s*")


def _on_path(name: str, env: Mapping[str, str]) -> str | None:
    path = env.get("PATH", "")
    if not path:
        return None
    return shutil.which(name, path=path) or shutil.which(name + ".exe", path=path)


def find_launcher(
    env: Mapping[str, str] = os.environ,
    root: str | Path | None = None,
) -> str | None:
    override = env.get("GW_LAUNCHER", "").strip()
    if override:
        return override

    repo_root = Path(root) if root is not None else Path(__file__).resolve().parents[3]
    candidates = []
    try:
        for candidate in (repo_root / "_build").rglob("gd-melee-launcher*"):
            if candidate.name not in ("gd-melee-launcher", "gd-melee-launcher.exe"):
                continue
            try:
                if candidate.is_file():
                    candidates.append(
                        (candidate.stat().st_mtime_ns, str(candidate.resolve()))
                    )
            except OSError:
                continue
    except OSError:
        pass

    if candidates:
        return max(candidates)[1]
    return _on_path("gd-melee-launcher", env)


def find_blender(
    env: Mapping[str, str] = os.environ,
    settings_value: str = "",
) -> str | None:
    if settings_value.strip():
        return settings_value
    override = env.get("GW_BLENDER", "")
    if override.strip():
        return override
    return _on_path("blender", env)


def serve_argv(
    exe: str,
    project: str,
    engine_exe: str = "",
    headless: bool = True,
) -> list[str]:
    argv = [os.fspath(exe), "--project", os.fspath(project), "--serve"]
    if engine_exe:
        argv.extend(("--engine-exe", os.fspath(engine_exe)))
    if not headless:
        argv.append("--engine-windowed")
    return argv


def parse_serve_line(line: str) -> int | None:
    match = _SERVE_LINE.fullmatch(line)
    if match is None:
        return None
    port = int(match.group(1))
    return port if 1 <= port <= 65535 else None


def blender_argv(
    blender: str,
    addon_dir: str,
    project: str,
    port: int,
) -> list[str]:
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("Blender connection port must be between 1 and 65535")
    bootstrap = (Path(addon_dir) / "bootstrap.py").as_posix()
    return [
        os.fspath(blender),
        "--python",
        bootstrap,
        "--",
        "--project",
        os.fspath(project),
        "--port",
        str(port),
    ]


def _stop_process(proc: subprocess.Popen) -> None:
    try:
        if proc.poll() is None:
            proc.terminate()
        try:
            proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=1.0)
    except (OSError, subprocess.TimeoutExpired):
        pass


def start_serve(
    argv: Sequence[str],
    timeout: float = 30.0,
) -> tuple[subprocess.Popen, int]:
    budget = float(timeout)
    if not math.isfinite(budget) or budget <= 0:
        raise ValueError("timeout must be finite and greater than zero")
    if isinstance(argv, (str, bytes)) or not argv:
        raise ValueError("argv must be a non-empty sequence of arguments")
    command = [os.fspath(part) for part in argv]
    deadline = time.monotonic() + budget

    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except (OSError, ValueError) as exc:
        raise WbError(f"cannot start workbench server: {exc}") from exc

    events: queue.Queue[tuple[str, str | None]] = queue.Queue(maxsize=64)
    handshake_done = threading.Event()
    recent: deque[str] = deque(maxlen=20)
    stream = proc.stdout
    if stream is None:
        _stop_process(proc)
        raise WbError("workbench server has no stdout pipe")

    def publish(kind: str, value: str | None) -> None:
        while not handshake_done.is_set():
            try:
                events.put((kind, value), timeout=0.05)
                return
            except queue.Full:
                continue

    def read_output() -> None:
        try:
            while True:
                line = stream.readline()
                if not line:
                    break
                publish("line", line)
        except (OSError, ValueError) as exc:
            publish("error", str(exc))
        finally:
            try:
                stream.close()
            except OSError:
                pass
            publish("eof", None)

    def failure(message: str) -> WbError:
        detail = "\n".join(recent)[-2000:]
        return WbError(message + (": " + detail if detail else ""))

    reader = threading.Thread(
        target=read_output,
        name="geno-workbench-serve-output",
        daemon=True,
    )
    try:
        reader.start()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise failure("timeout waiting for WB_SERVE")

            try:
                kind, value = events.get(timeout=min(remaining, 0.1))
            except queue.Empty:
                code = proc.poll()
                if code is not None:
                    raise failure(
                        f"workbench server exited with code {code} before WB_SERVE"
                    )
                continue

            if kind == "line":
                line = value or ""
                recent.append(line.rstrip())
                port = parse_serve_line(line)
                if port is not None:
                    code = proc.poll()
                    if code is not None:
                        raise failure(
                            f"workbench server exited with code {code} during startup"
                        )
                    handshake_done.set()
                    return proc, port
            elif kind == "error":
                raise failure(f"cannot read workbench server output: {value}")
            else:
                code = proc.poll()
                if code is None:
                    raise failure("workbench server closed stdout before WB_SERVE")
                raise failure(
                    f"workbench server exited with code {code} before WB_SERVE"
                )
    except BaseException:
        handshake_done.set()
        _stop_process(proc)
        raise
