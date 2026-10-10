"""Bounded localhost MCP and one-shot launcher clients.

The TCP handshake is sent without waiting in connect(). Its response is
validated during the first RPC, so a silent peer cannot block connect()
waiting for an application-level reply. Requests are serialized, have total
deadlines, and are never automatically retried.
"""

from __future__ import annotations

import json
import math
import os
import socket
import subprocess
import threading
import time
from typing import Sequence

import logging as _logging

# Every engine call, its time and any error go to GW_WB_LOG (default <tmp>/geno_wb.log).
LOG_PATH = os.environ.get("GW_WB_LOG") or os.path.join(
    os.environ.get("TEMP") or os.environ.get("TMPDIR") or "/tmp", "geno_wb.log")
log = _logging.getLogger("geno_wb")
if not log.handlers:
    try:
        _handler = _logging.FileHandler(LOG_PATH, encoding="utf-8")
        _handler.setFormatter(_logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(_handler)
        log.setLevel(_logging.DEBUG)
    except OSError:
        pass


class WbError(RuntimeError):
    """A workbench transport, protocol, or tool failure."""


def _seconds(value: float) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError("timeout must be finite and greater than zero")
    return result


def _error_text(error: object) -> str:
    if isinstance(error, dict):
        return str(error.get("message") or error.get("error") or error)
    return str(error)


def _encode(message: dict) -> bytes:
    return (
        json.dumps(message, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode("utf-8")


class McpClient:
    """Newline-delimited JSON-RPC over one loopback TCP connection."""

    _MAX_LINE_BYTES = 16 * 1024 * 1024

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        timeout: float = 10.0,
    ):
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("workbench connections must use a localhost host")
        if isinstance(port, bool) or not isinstance(port, int):
            raise ValueError("port must be an integer")
        if not 0 <= port <= 65535:
            raise ValueError("port must be between 0 and 65535")

        self.host = host
        self.port = port
        self.timeout = _seconds(timeout)
        self._socket: socket.socket | None = None
        self._buffer = bytearray()
        self._sequence = 0
        self._initialize_id: int | None = None
        self._io_lock = threading.RLock()

    def _next_id(self) -> int:
        self._sequence += 1
        return self._sequence

    @staticmethod
    def _remaining(deadline: float, label: str) -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise WbError(f"timeout calling {label}")
        return remaining

    def _disconnect(self) -> None:
        sock = self._socket
        self._socket = None
        self._initialize_id = None
        self._buffer.clear()
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    def connect(self) -> None:
        deadline = time.monotonic() + self.timeout
        if not self._io_lock.acquire(timeout=self.timeout):
            raise WbError("timeout connecting to workbench")

        try:
            if self._socket is not None:
                return

            initialize_id = self._next_id()
            initialize = {
                "jsonrpc": "2.0",
                "id": initialize_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "geno_workbench",
                        "version": "0.1.0",
                    },
                },
            }
            initialized = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }
            wire = _encode(initialize) + _encode(initialized)
            connect_host = "127.0.0.1" if self.host == "localhost" else self.host

            try:
                self._socket = socket.create_connection(
                    (connect_host, self.port),
                    timeout=self._remaining(deadline, "initialize"),
                )
                self._socket.settimeout(
                    self._remaining(deadline, "initialize")
                )
                self._socket.sendall(wire)
                self._initialize_id = initialize_id
            except socket.timeout as exc:
                self._disconnect()
                raise WbError("timeout connecting to workbench") from exc
            except OSError as exc:
                self._disconnect()
                raise WbError(f"cannot connect to workbench: {exc}") from exc
            except WbError:
                self._disconnect()
                raise
        finally:
            self._io_lock.release()

    def close(self) -> None:
        with self._io_lock:
            self._disconnect()

    def _read_message(self, deadline: float, label: str) -> dict:
        sock = self._socket
        if sock is None:
            raise WbError("engine is not connected")

        while True:
            self._remaining(deadline, label)
            newline = self._buffer.find(b"\n")
            if newline >= 0:
                if newline > self._MAX_LINE_BYTES:
                    raise WbError("JSON-RPC response exceeds the size limit")
                raw = bytes(self._buffer[:newline])
                del self._buffer[:newline + 1]
                if not raw.strip():
                    continue
                try:
                    message = json.loads(raw.decode("utf-8"))
                except (UnicodeError, ValueError) as exc:
                    raise WbError("invalid JSON-RPC response") from exc
                if (
                    not isinstance(message, dict)
                    or message.get("jsonrpc") != "2.0"
                ):
                    raise WbError("invalid JSON-RPC response envelope")
                return message

            if len(self._buffer) > self._MAX_LINE_BYTES:
                raise WbError("JSON-RPC response exceeds the size limit")

            sock.settimeout(self._remaining(deadline, label))
            chunk = sock.recv(65536)
            if not chunk:
                raise WbError("engine connection closed")
            self._buffer.extend(chunk)

    def _request(
        self,
        method: str,
        params: dict,
        label: str,
        timeout: float | None = None,
    ) -> dict:
        budget = self.timeout if timeout is None else _seconds(timeout)
        deadline = time.monotonic() + budget
        if not self._io_lock.acquire(timeout=budget):
            raise WbError(f"timeout calling {label}")

        try:
            sock = self._socket
            if sock is None:
                raise WbError("engine is not connected")

            request_id = self._next_id()
            request = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
            try:
                wire = _encode(request)
            except (TypeError, ValueError, UnicodeError) as exc:
                raise WbError(f"invalid JSON arguments for {label}") from exc

            try:
                sock.settimeout(self._remaining(deadline, label))
                sock.sendall(wire)
                while True:
                    response = self._read_message(deadline, label)
                    response_id = response.get("id")
                    if (
                        self._initialize_id is not None
                        and response_id == self._initialize_id
                    ):
                        self._initialize_id = None
                        if "error" in response:
                            raise WbError(
                                "initialize failed: "
                                + _error_text(response["error"])
                            )
                        if not isinstance(response.get("result"), dict):
                            raise WbError("invalid initialize response")
                        continue
                    if response_id == request_id:
                        break
            except socket.timeout as exc:
                self._disconnect()
                raise WbError(f"timeout calling {label}") from exc
            except OSError as exc:
                self._disconnect()
                raise WbError(f"engine connection failed: {exc}") from exc
            except WbError:
                self._disconnect()
                raise

            if "error" in response:
                raise WbError(_error_text(response["error"]))

            result = response.get("result")
            if not isinstance(result, dict):
                raise WbError(f"invalid JSON-RPC result for {label}")
            return result
        finally:
            self._io_lock.release()

    def call(
        self,
        tool: str,
        args: dict | None = None,
        timeout: float | None = None,
    ) -> dict:
        if not isinstance(tool, str) or not tool:
            raise WbError("tool name must be a non-empty string")
        if args is not None and not isinstance(args, dict):
            raise WbError("tool arguments must be a dictionary")

        started = time.monotonic()
        log.debug("call %s %s", tool, json.dumps(args or {})[:300])
        try:
            body = self._call_body(tool, args, timeout)
        except Exception as exc:
            log.error("call %s failed after %.2fs: %s: %s", tool,
                      time.monotonic() - started, type(exc).__name__, exc)
            raise
        log.debug("call %s ok %.2fs %s", tool, time.monotonic() - started,
                  json.dumps(body)[:300])
        return body

    def _call_body(self, tool, args, timeout):
        result = self._request(
            "tools/call",
            {"name": tool, "arguments": args if args is not None else {}},
            tool,
            timeout,
        )
        content = result.get("content")
        if (
            not isinstance(content, list)
            or not content
            or not isinstance(content[0], dict)
            or not isinstance(content[0].get("text"), str)
        ):
            raise WbError(f"missing text result for {tool}")

        text = content[0]["text"]
        try:
            body = json.loads(text)
        except ValueError as exc:
            if result.get("isError"):
                raise WbError(text or f"{tool} failed") from exc
            raise WbError(f"invalid JSON body returned by {tool}") from exc

        if result.get("isError"):
            error = body.get("error") if isinstance(body, dict) else None
            raise WbError(_error_text(error) if error else text)
        if not isinstance(body, dict):
            raise WbError(f"result for {tool} is not a JSON object")
        return body

    def tools(self) -> list[str]:
        result = self._request("tools/list", {}, "tools/list")
        entries = result.get("tools")
        if not isinstance(entries, list):
            raise WbError("invalid tools/list result")

        names = []
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                raise WbError("invalid tool entry in tools/list")
            names.append(entry["name"])
        return names


class CliClient:
    """One-shot --wb-call client with a bounded subprocess lifetime."""

    def __init__(
        self,
        exe: str | Sequence[str],
        project: str,
        extra: Sequence[str] = (),
        timeout: float = 60.0,
    ):
        if isinstance(exe, (str, os.PathLike)):
            self.exe = [os.fspath(exe)]
        else:
            self.exe = [os.fspath(part) for part in exe]
        if not self.exe or not self.exe[0]:
            raise ValueError("launcher executable prefix cannot be empty")
        if isinstance(extra, (str, bytes)):
            raise ValueError("extra must be a sequence of arguments")
        self.project = os.fspath(project)
        self.extra = [os.fspath(part) for part in extra]
        self.timeout = _seconds(timeout)

    def call(self, tool: str, args: dict | None = None) -> dict:
        if not isinstance(tool, str) or not tool:
            raise WbError("tool name must be a non-empty string")
        if args is not None and not isinstance(args, dict):
            raise WbError("tool arguments must be a dictionary")
        try:
            encoded_args = json.dumps(args or {}, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise WbError(f"invalid JSON arguments for {tool}") from exc

        argv = [
            *self.exe,
            "--project",
            self.project,
            *self.extra,
            "--wb-call",
            tool,
            encoded_args,
        ]
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise WbError(f"timeout calling {tool}") from exc
        except (OSError, ValueError) as exc:
            raise WbError(f"cannot run launcher: {exc}") from exc

        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        envelope = None
        if lines:
            try:
                envelope = json.loads(lines[-1])
            except ValueError:
                pass

        if (
            not isinstance(envelope, dict)
            or not isinstance(envelope.get("ok"), bool)
        ):
            detail = (completed.stderr.strip() or completed.stdout.strip())[-2000:]
            message = (
                "launcher returned no valid --wb-call envelope "
                f"(exit {completed.returncode})"
            )
            if detail:
                message += ": " + detail
            raise WbError(message)

        if not envelope["ok"]:
            raise WbError(
                _error_text(envelope.get("error") or f"{tool} failed")
            )
        result = envelope.get("result")
        if not isinstance(result, dict):
            raise WbError(f"launcher result for {tool} is not a JSON object")
        return result
