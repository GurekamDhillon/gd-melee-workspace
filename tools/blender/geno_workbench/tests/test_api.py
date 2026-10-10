import api
import client
from fake_engine import FakeWorkbench


def make():
    fake = FakeWorkbench(); port = fake.start()
    s = api.WbSession(lambda: client.McpClient(port=port, timeout=2.0))
    return fake, s


def test_connect_and_rows():
    fake, s = make()
    try:
        assert s.connect() and s.connected and s.status.startswith("connected")
        assert s.refresh_rows() and [r["name"] for r in s.rows] == ["wait", "jab", "dair"]
    finally:
        fake.stop()


def test_set_frame_stores_info():
    fake, s = make()
    try:
        s.connect(); s.refresh_rows()
        assert s.load_row("jab") and s.set_frame(6)
        assert s.info["frame"] == 6 and s.info["schema"] == 2 and s.row == "jab"
        assert s.step(2) and s.info["frame"] == 8
    finally:
        fake.stop()


def test_error_is_captured_not_raised():
    fake, s = make()
    try:
        s.connect()
        fake.fail_next = "engine busy"
        assert s.set_frame(3) is False
        assert "engine busy" in s.last_error and s.connected
    finally:
        fake.stop()


def test_dropped_connection_marks_disconnected():
    fake, s = make()
    try:
        s.connect()
        fake.drop_after = 0
        assert s.refresh_rows() is False and s.connected is False and "closed" in s.status.lower() or not s.connected
    finally:
        fake.stop()


def test_old_engine_schema_is_reported():
    fake, s = make()
    try:
        s.connect()
        fake.provider = lambda row, frame, **k: {"row": row, "frame": frame, "bones": [{"joint": 1, "parent": 0, "pos": {"x": 0, "y": 0, "z": 0}}]}
        s.load_row("jab")
        assert s.set_frame(2) is True            # the data call itself works
        assert "schema 2 needed" in s.pose_problem()   # but posing is refused with the explanation
    finally:
        fake.stop()
