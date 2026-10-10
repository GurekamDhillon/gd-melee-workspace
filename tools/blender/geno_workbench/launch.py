"""Launcher and Blender discovery, argument construction, and serve startup.

Explicit UI executable settings are returned as supplied, without existence
checks; GW_* and .env/config paths are resolved by tools/port/tools_config.py. start_serve owns startup failure cleanup and continuously drains the
server's output after returning its process and port.
"""

from __future__ import annotations

from collections import deque
import math
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
from typing import Mapping, Sequence

if __package__:
    from .client import WbError
else:
    from client import WbError


_SERVE_LINE = re.compile(r"\s*WB_SERVE\s+port=([0-9]+)\s*")


# Scripts and an installed add-on use the workspace's one resolver. An installed
# copy needs GW_ROOT to point at the checkout containing tools/port/tools_config.py.
import sys

_config_root = Path(__file__).resolve().parents[3]
if not (_config_root / "tools/port/tools_config.py").is_file() and os.environ.get("GW_ROOT"):
    _config_root = Path(os.environ["GW_ROOT"])
if (_config_root / "tools/port/tools_config.py").is_file() and str(_config_root) not in sys.path:
    sys.path.insert(0, str(_config_root))
from tools.port import tools_config


def tool_paths(root=None, env: Mapping[str, str] | None = None) -> dict[str, str]:
    try:
        return tools_config.load_config(root, env)
    except tools_config.ToolsConfigError as exc:
        raise WbError(str(exc)) from exc


def find_launcher(env: Mapping[str, str] | None = None, root=None) -> str | None:
    return tool_paths(root, env)["GW_LAUNCHER"] or None


def find_blender(env: Mapping[str, str] | None = None, settings_value: str = "", root=None) -> str | None:
    if settings_value.strip():
        return settings_value
    return tool_paths(root, env)["GW_BLENDER"] or None


def serve_argv(
    exe: str,
    project: str,
    engine_exe: str = "",
    headless: bool = True,
    mods_dir: str = "",
    engine_work_dir: str = "",
    wb_dir: str = "",
) -> list[str]:
    argv = [os.fspath(exe), "--project", os.fspath(project), "--serve"]
    if engine_exe:
        argv.extend(("--engine-exe", os.fspath(engine_exe)))
    if engine_work_dir:
        argv.extend(("--engine-work-dir", os.fspath(engine_work_dir)))
    if mods_dir:
        argv.extend(("--mods-dir", os.fspath(mods_dir)))
    if wb_dir:
        argv.extend(("--wb-dir", os.fspath(wb_dir)))
    if not headless:
        argv.append("--engine-windowed")
    return argv


def serve_settings(
    engine_exe: str = "", mods_dir: str = "", iso: str = "",
    env: Mapping[str, str] | None = None, root=None,
) -> dict[str, str]:
    """Explicit UI values first, then the shared environment/.env/tools.json paths."""
    paths = tool_paths(root, env)
    return {
        "engine_exe": engine_exe.strip() or paths["GW_ENGINE_EXE"],
        "mods_dir": mods_dir.strip() or paths.get("GW_MODS_DIR", "").strip(),
        "iso": iso.strip() or paths["GW_ISO_VANILLA"],
    }


def serve_launch(
    exe: str, project: str, engine_exe: str = "", mods_dir: str = "",
    iso: str = "", headless: bool = True,
    env: Mapping[str, str] | None = None, root=None,
) -> tuple[list[str], dict[str, str]]:
    """Server argv and environment, shared by launch_goku.py and the add-on."""
    paths = tool_paths(root, env)
    s = serve_settings(engine_exe, mods_dir, iso, env=paths, root=paths["GW_ROOT"])
    work = wb = ""
    if s["engine_exe"]:
        parent = Path(s["engine_exe"]).parent
        work = str(parent)
        wb = str(parent.parent / "payloads")
        try:
            Path(wb).mkdir(parents=True, exist_ok=True)
        except OSError:
            wb = ""
    argv = serve_argv(exe, project, s["engine_exe"], headless, s["mods_dir"], work, wb)
    out = dict(paths)
    qt_bin = paths["GW_QT_BIN"]
    if qt_bin:
        out["PATH"] = qt_bin + os.pathsep + out.get("PATH", "")
    if s["iso"]:
        out["MELEE_ISO"] = s["iso"]
    out["MELEE_NETPLAY_BIND"] = "127.0.0.1"
    return argv, out


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
            # Closing stdin is the server's clean shutdown (it stops the engine it started);
            # terminate() alone would orphan the engine process on Windows.
            try:
                if proc.stdin is not None:
                    proc.stdin.close()
                proc.wait(timeout=8.0)
            except (OSError, subprocess.TimeoutExpired):
                pass
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
    env: Mapping[str, str] | None = None,
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
            env=None if env is None else dict(env),
            stdin=subprocess.PIPE,
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
