"""Run the synthetic Blender workbench self-test without importing bpy."""

import argparse
from collections import deque
import math
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time


_ADDON_DIR = Path(__file__).resolve().parents[1] / "blender" / "geno_workbench"
if str(_ADDON_DIR) not in sys.path:
    sys.path.insert(0, str(_ADDON_DIR))

import launch


DEFAULT_TIMEOUT = 300.0


def _kill_and_wait(process):
    if process.poll() is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        pass


def stream_process(argv, timeout=DEFAULT_TIMEOUT):
    """Stream GENO_WB_ lines, retaining other output for failure diagnostics."""
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")

    try:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError as exc:
        print("GENO_WB_SELFTEST FAIL cannot start Blender: " + str(exc), flush=True)
        return 1

    messages = queue.Queue()
    tail = deque(maxlen=80)
    deadline = time.monotonic() + timeout

    def read_output():
        try:
            for line in process.stdout:
                messages.put(("line", line.rstrip("\r\n")))
        except (OSError, ValueError) as exc:
            messages.put(("error", str(exc)))
        finally:
            messages.put(("end", None))

    reader = threading.Thread(
        target=read_output, name="geno-wb-selftest-output", daemon=True
    )
    reader.start()
    failure = None
    saw_failure_marker = False
    return_code = 1

    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(argv, timeout)
            try:
                kind, value = messages.get(timeout=min(remaining, 0.2))
            except queue.Empty:
                continue
            if kind == "end":
                break
            if kind == "error":
                raise OSError(value)
            if value.startswith("GENO_WB_"):
                print(value, flush=True)
                if value.startswith("GENO_WB_SELFTEST FAIL"):
                    saw_failure_marker = True
            else:
                tail.append(value)

        remaining = deadline - time.monotonic()
        if remaining <= 0 and process.poll() is None:
            raise subprocess.TimeoutExpired(argv, timeout)
        return_code = process.wait(timeout=max(remaining, 0.001))
    except subprocess.TimeoutExpired:
        return_code = 124
        failure = "timeout after {:g} seconds".format(timeout)
    except KeyboardInterrupt:
        return_code = 130
        failure = "interrupted"
    except OSError as exc:
        return_code = 1
        failure = "output read failed: " + str(exc)
    finally:
        if process.poll() is None:
            _kill_and_wait(process)
        reader.join(timeout=1.0)
        # A descendant retaining stdout must not make close() block on the
        # reader's TextIO lock. The daemon reader cannot hold up our exit.
        if not reader.is_alive():
            process.stdout.close()

    if return_code != 0:
        if tail:
            print("Blender output preceding failure:", file=sys.stderr)
            for line in tail:
                print(line, file=sys.stderr)
        if failure is not None:
            print("GENO_WB_SELFTEST FAIL " + failure, flush=True)
        elif not saw_failure_marker:
            print(
                "GENO_WB_SELFTEST FAIL Blender exited with code "
                + str(return_code),
                flush=True,
            )
    return return_code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", default="", help="Blender executable")
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT,
        help="Maximum seconds for Blender (default: 300)",
    )
    args = parser.parse_args(argv)
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and positive")

    blender = launch.find_blender(settings_value=args.blender)
    if not blender:
        print("SKIP: no Blender", flush=True)
        return 77

    selftest = _ADDON_DIR / "selftest.py"
    if not selftest.is_file():
        print("GENO_WB_SELFTEST FAIL missing " + str(selftest), flush=True)
        return 1

    with tempfile.TemporaryDirectory(prefix="geno-wb-selftest-") as out_dir:
        command = [
            str(blender),
            "--background",
            "--factory-startup",
            "--python-exit-code", "1",
            "--python", str(selftest),
            "--", "--out", out_dir,
        ]
        return stream_process(command, timeout=args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
