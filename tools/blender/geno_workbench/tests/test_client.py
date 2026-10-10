import json
import socket
import threading
import time
import pytest
import client as C
from fake_engine import FakeWorkbench


def test_rejects_non_local_host():
    with pytest.raises(ValueError):
        C.McpClient(host="8.8.8.8", port=1)


def test_call_roundtrip_and_tools():
    fake = FakeWorkbench(); port = fake.start()
    try:
        c = C.McpClient(port=port); c.connect()
        assert "frame_info" in c.tools()
        assert c.call("engine_status") == {"status": "running"}
        rows = c.call("list_rows")["rows"]
        assert [r["name"] for r in rows] == ["wait", "jab", "dair"]
    finally:
        fake.stop()


def test_tool_error_is_wberror():
    fake = FakeWorkbench(); port = fake.start()
    try:
        c = C.McpClient(port=port); c.connect()
        fake.fail_next = "boom"
        with pytest.raises(C.WbError, match="boom"):
            c.call("engine_status")
        assert c.call("engine_status")["status"] == "running"
    finally:
        fake.stop()


def test_timeout_does_not_hang():
    srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1)
    port = srv.getsockname()[1]
    threading.Thread(target=lambda: srv.accept(), daemon=True).start()
    c = C.McpClient(port=port, timeout=0.3); c.connect()
    t = time.time()
    with pytest.raises(C.WbError):
        c.call("engine_status")
    assert time.time() - t < 3


def test_dropped_socket_is_wberror():
    fake = FakeWorkbench(); port = fake.start()
    try:
        c = C.McpClient(port=port, timeout=1.0); c.connect()
        fake.drop_after = 0
        with pytest.raises(C.WbError):
            c.call("engine_status")
    finally:
        fake.stop()


def test_connect_refused_is_wberror():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    with pytest.raises(C.WbError):
        C.McpClient(port=port, timeout=0.5).connect()


def test_cli_client_parses_envelope(tmp_path):
    script = tmp_path / "fake_launcher.py"
    script.write_text("import sys,json\nprint('noise')\nprint(json.dumps({'ok': True, 'result': {'args': sys.argv[1:]}}))\n")
    c = C.CliClient(["python", str(script)], "proj", extra=["--engine-port", "5"])
    out = c.call("list_rows", {"a": 1})
    assert out["args"][-3:] == ["--wb-call", "list_rows", '{"a": 1}'] and "--project" in out["args"]


def test_cli_client_error_envelope(tmp_path):
    script = tmp_path / "bad.py"
    script.write_text("import json\nprint(json.dumps({'ok': False, 'error': 'no row'}))\nraise SystemExit(1)\n")
    with pytest.raises(C.WbError, match="no row"):
        C.CliClient(["python", str(script)], "proj").call("x")
