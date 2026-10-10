"""Pure adapter/transport tests; no Blender, game, sockets or disc assets required.

Run: python tools/release/launcher/qt/workbench/tests/blender_sync_test.py
"""

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest

WORKBENCH = Path(__file__).resolve().parents[1]
WORKSPACE = WORKBENCH.parents[4]
sys.path.insert(0, str(WORKSPACE / "tools" / "blender"))
from geno_workbench import api, client, props

spec = importlib.util.spec_from_file_location("blender_sync", WORKBENCH / "blender_sync.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


IDENTITY = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]


def state(revision=1, row="jab", frame=8, x=4):
    matrix = list(IDENTITY)
    matrix[3] = x
    return {
        "revision": revision,
        "row": row,
        "info": {
            "schema": 2, "row": "Attack11" if row == "jab" else "AttackAirLw",
            "frame": frame, "facing": 1,
            "root": {"pos": {"x": x, "y": 0, "z": 0}, "mtx": matrix},
            "bones": [{"joint": 0, "parent": -1,
                       "pos": {"x": x, "y": 0, "z": 0}, "mtx": matrix}],
            "hitboxes": [{"slot": 0, "size": 2, "world": {"x": x, "y": 2, "z": 0}}],
            "hurtboxes": [], "ecb": {}, "floorY": 0,
        },
        "hitboxes": [{"ordinal": 0, "joint": "HAND", "start_frame": 6,
                      "end_frame": 10, "damage": 8, "size": 2}],
    }


class NoCommands:
    def call(self, *args, **kwargs):
        raise AssertionError("adopting a view must never call the engine")


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.session = api.WbSession(NoCommands)
        self.session.client = NoCommands()
        self.session.connected = True
        self.session.prefetch = True
        self.session.rows = [{"name": "jab", "frames": 30}, {"name": "dair", "frames": 40}]
        self.shown = []
        self.session.on_frame.append(lambda session: self.shown.append(deepcopy(session.info)))
        self.settings = SimpleNamespace(row="", frame=0, status="", stale=False, playing=False)
        self.session.on_change = lambda session: props.sync_from_session(session, self.settings)
        self.follower = sync.FrameFollower(self.session)

    def test_adopts_engine_reply_and_source_row_without_engine_round_trip(self):
        self.session.cache.row = "old"
        self.session.cache.frames = {1: {"frame": 1}}
        self.session.travel_anchor = {"x": 90, "y": 0, "z": 0}
        self.assertTrue(self.follower.consume(state()))
        self.assertEqual(self.follower.revision, 1)
        self.assertEqual((self.session.loaded_row, self.session.row, self.session.frame),
                         ("jab", "Attack11", 8))
        self.assertEqual((self.settings.row, self.settings.frame), ("Attack11", 8))
        self.assertEqual(self.session.travel_anchor, {"x": 4.0, "y": 0.0, "z": 0.0})
        self.assertEqual(self.session.hitboxes[0]["joint"], "HAND")
        self.assertEqual(self.shown[0]["hitboxes"][0]["world"]["y"], 2)
        self.assertEqual(self.session.cache.frames, {})
        self.assertEqual(self.session.engine_calls, 0)

    def test_same_row_retains_travel_origin_and_duplicate_does_not_refire(self):
        self.assertTrue(self.follower.consume(state()))
        self.assertFalse(self.follower.consume(state()))
        self.assertTrue(self.follower.consume(state(2, frame=9, x=20)))
        self.assertEqual(len(self.shown), 2)
        self.assertEqual(self.session.travel_anchor["x"], 4.0)
        self.assertFalse(self.follower.consume(state(1)))
        self.assertEqual(self.session.frame, 9)

    def test_zero_revision_does_not_need_frame_fields(self):
        self.assertFalse(self.follower.consume({"revision": 0}))
        self.assertIsNone(self.session.info)
        self.assertEqual(self.follower.revision, 0)

    def test_tombstone_withdraws_ack_without_mutating_or_posing_session(self):
        self.assertTrue(self.follower.consume(state()))
        previous_info = self.session.info
        previous_boxes = self.session.hitboxes
        previous_anchor = self.session.travel_anchor
        previous_generation = self.session.cache.generation
        self.assertFalse(self.follower.consume({"revision": 2, "available": False}))
        self.assertEqual(self.follower.revision, 0)
        self.assertIs(self.session.info, previous_info)
        self.assertIs(self.session.hitboxes, previous_boxes)
        self.assertIs(self.session.travel_anchor, previous_anchor)
        self.assertEqual(self.session.cache.generation, previous_generation)
        self.assertEqual((self.session.loaded_row, self.session.row, self.session.frame),
                         ("jab", "Attack11", 8))
        self.assertEqual(len(self.shown), 1)

    def test_pending_snapshot_cannot_replay_after_tombstone_and_newer_view_applies(self):
        self.assertTrue(self.follower.consume(state()))
        pending = state(2, row="dair", frame=10)
        self.assertFalse(self.follower.consume(pending, ready=False))
        self.assertFalse(self.follower.consume({"revision": 3, "available": False}))
        self.assertFalse(self.follower.consume(pending))
        self.assertEqual((self.session.loaded_row, self.session.frame), ("jab", 8))
        self.assertEqual(len(self.shown), 1)
        newer = dict(state(4, row="dair", frame=12), available=True)
        self.assertTrue(self.follower.consume(newer))
        self.assertEqual(self.follower.revision, 4)
        self.assertEqual((self.session.loaded_row, self.session.frame), ("dair", 12))
        self.assertEqual(len(self.shown), 2)

    def test_tombstone_consumes_local_override_boundary_without_losing_next_click(self):
        self.assertTrue(self.follower.consume(state()))
        self.session._store_frame(self.session._read_frame(state(frame=15)["info"], "jab"))
        self.follower.observe()
        self.assertFalse(self.follower.consume({"revision": 2, "available": False}))
        self.assertTrue(self.follower.consume(dict(state(3, frame=17), available=True)))
        self.assertEqual(self.session.frame, 17)

    def test_older_tombstone_does_not_withdraw_a_newer_applied_view(self):
        self.assertTrue(self.follower.consume(state(3)))
        self.assertFalse(self.follower.consume({"revision": 2, "available": False}))
        self.assertEqual(self.follower.revision, 3)
        self.assertEqual(len(self.shown), 1)

    def test_only_explicit_false_is_a_tombstone(self):
        self.assertTrue(self.follower.consume(dict(state(), available=None)))
        self.assertEqual(self.follower.revision, 1)

    def test_invalid_snapshot_does_not_replace_last_valid_frame(self):
        self.assertTrue(self.follower.consume(state()))
        previous = self.session.info
        cases = []
        broken = state(2); broken["info"]["frame"] = True; cases.append(broken)
        broken = state(2); broken["hitboxes"] = [None]; cases.append(broken)
        broken = state(2); broken["info"]["schema"] = 1; cases.append(broken)
        broken = state(2); broken["info"]["bones"] = []; cases.append(broken)
        broken = state(2); broken["info"]["bones"][0]["mtx"] = [1]; cases.append(broken)
        broken = state(2); broken["row"] = ""; cases.append(broken)
        broken = state(2); broken["revision"] = True; cases.append(broken)
        for broken in cases:
            with self.subTest(broken=broken), self.assertRaises((ValueError, client.WbError)):
                self.follower.consume(broken)
            self.assertIs(self.session.info, previous)
            self.assertEqual(self.follower.revision, 1)

    def test_pending_blender_scrub_wins_and_old_qt_revision_is_not_replayed(self):
        self.assertTrue(self.follower.consume(state()))
        self.session.pending_frame = 12
        self.assertFalse(self.follower.consume(state(2)))
        self.assertEqual(self.session.pending_frame, 12)
        self.assertEqual(self.follower.revision, 0)
        self.session.pending_frame = None
        self.assertFalse(self.follower.consume(state(2)))
        self.assertTrue(self.follower.consume(state(3, frame=14)))
        self.assertEqual(self.session.frame, 14)

    def test_local_frame_replaces_ack_and_discards_existing_qt_request(self):
        self.assertTrue(self.follower.consume(state()))
        self.session._store_frame(self.session._read_frame(state(frame=15)["info"], "jab"))
        self.follower.observe()
        self.assertEqual(self.follower.revision, 0)
        self.assertFalse(self.follower.consume(state(2)))
        self.assertEqual(self.session.frame, 15)
        self.assertTrue(self.follower.consume(state(3, frame=17)))

    def test_playback_or_rebuild_busy_state_does_not_override_view(self):
        self.assertTrue(self.follower.consume(state()))
        self.assertFalse(self.follower.consume(state(2, frame=12), busy=True))
        self.assertEqual(self.session.frame, 8)
        self.assertEqual(self.follower.revision, 0)
        self.assertFalse(self.follower.consume(state(2)))
        self.assertTrue(self.follower.consume(state(3, frame=13)))

    def test_busy_duplicate_does_not_discard_next_new_qt_click(self):
        self.assertTrue(self.follower.consume(state()))
        self.assertFalse(self.follower.consume(state(2), busy=True))
        self.assertFalse(self.follower.consume(state(2), busy=True))
        self.assertFalse(self.follower.consume(state(2)))
        self.assertTrue(self.follower.consume(state(3)))

    def test_missing_viewport_withdraws_an_existing_ack(self):
        self.assertTrue(self.follower.consume(state()))
        self.follower.observe(ready=False)
        self.assertEqual(self.follower.revision, 0)
        self.assertFalse(self.follower.consume(state(), ready=False))
        self.assertTrue(self.follower.consume(state(2)))

    def test_property_notification_does_not_queue_an_engine_request(self):
        class ReactiveSettings:
            row, status, stale, playing = "", "", False, False
            _frame = 0
            @property
            def frame(self):
                return self._frame
            @frame.setter
            def frame(self, value):
                self._frame = value
                props.on_frame_changed(self, None)
        def echo(*args):
            raise AssertionError("property synchronization echoed to the engine")
        previous = props._frame_handler
        try:
            props.set_frame_handler(echo)
            settings = ReactiveSettings()
            self.session.on_change = lambda session: props.sync_from_session(session, settings)
            self.assertTrue(self.follower.consume(state()))
            self.assertEqual(settings.frame, 8)
            self.assertIsNone(self.session.pending_frame)
        finally:
            props.set_frame_handler(previous)

    def test_absent_viewport_defers_without_claiming_sync(self):
        self.assertFalse(self.follower.consume(state(), ready=False))
        self.assertEqual(self.follower.revision, 0)
        self.assertIsNone(self.session.info)
        self.assertTrue(self.follower.consume(state(), ready=True))

    def test_prefetch_is_cancelled_without_waiting_then_cache_is_invalidated(self):
        started, release = threading.Event(), threading.Event()
        def fetch(frame):
            started.set()
            release.wait(2.0)
            return state(frame=frame)["info"]
        self.session.cache.begin("old", 1, 2, fetch)
        self.assertTrue(started.wait(1.0))
        # Cache loading itself is not a Blender user gesture.
        self.follower = sync.FrameFollower(self.session)
        try:
            self.assertFalse(self.follower.consume(state()))
            self.assertTrue(self.session.cache.loading)
            self.assertEqual(self.follower.revision, 0)
            self.assertTrue(self.session.cache._cancel.is_set())
        finally:
            release.set()
            self.session.cache.cancel(wait=True)
        self.assertTrue(self.follower.consume(state()))
        self.assertEqual(self.session.cache.frames, {})
        self.assertEqual(self.session.loaded_row, "jab")

    def test_hook_failure_never_acks_or_erases_error(self):
        def failure(session):
            session.last_error = "pose hook failed"
        self.session.on_frame.append(failure)
        self.assertFalse(self.follower.consume(state()))
        self.assertEqual(self.follower.revision, 0)
        self.assertEqual(self.session.last_error, "pose hook failed")
        self.assertFalse(self.follower.consume(state()))
        self.assertEqual(len(self.shown), 1)

    def test_throwing_hook_or_property_sync_failure_never_acks(self):
        def failure(session):
            raise RuntimeError("hook failed")
        self.session.on_frame.append(failure)
        self.assertFalse(self.follower.consume(state()))
        self.assertEqual(self.follower.revision, 0)
        self.assertEqual(self.session.hook_error, "hook failed")
        self.session.on_frame.remove(failure)
        self.session.on_change = failure
        self.assertFalse(self.follower.consume(state(2)))
        self.assertEqual(self.follower.revision, 0)

    def test_disconnected_session_does_not_apply(self):
        self.session.connected = False
        self.assertFalse(self.follower.consume(state()))
        self.assertIsNone(self.session.info)


class DriverTest(unittest.TestCase):
    def make_driver(self, *, poses=True):
        session = api.WbSession(NoCommands)
        session.connected = True
        session.client = SimpleNamespace(host="127.0.0.1", port=4444)
        settings = SimpleNamespace(playing=False, move="")
        timers = SimpleNamespace(is_registered=lambda callback: False)
        bpy = SimpleNamespace(
            context=SimpleNamespace(
                scene=SimpleNamespace(geno_wb=settings),
                window_manager=SimpleNamespace(windows=[SimpleNamespace(
                    screen=SimpleNamespace(is_animation_playing=False))])),
            app=SimpleNamespace(timers=timers, driver_namespace={}))
        pose = SimpleNamespace(_LAST_APPLIED=None, is_calibrating=lambda: False,
                               calibration_for=lambda arm: (object(), object()))
        def frame_hook(value):
            if poses:
                pose._LAST_APPLIED = (object(), object(), object())
        session.on_frame.append(frame_hook)
        fighter = SimpleNamespace(_frame_hook=frame_hook, _IN_FRAME_UPDATE=False,
                                  active_armature=lambda context: object())
        driver_props = SimpleNamespace(row_items=lambda: [("jab", "Jab", "")],
                                       suspend_frame_updates=props.suspend_frame_updates)
        operators = SimpleNamespace(_active_player=None, _redraw_ui=lambda: None)
        driver = sync._BlenderDriver(bpy, SimpleNamespace(session=lambda: session),
                                     client, operators, fighter, pose, driver_props)
        class Mailbox:
            failed = False
            stopped = False
            revision = 0
            reply = state()
            def acknowledge(self, revision):
                self.revision = revision
            def take(self):
                reply, self.reply = self.reply, None
                return reply
            def stop(self):
                self.stopped = True
        driver.poller = Mailbox()
        return driver, session, bpy

    def test_timer_acks_pose_and_keeps_move_picker_on_source_name(self):
        driver, session, bpy = self.make_driver()
        self.assertEqual(driver.tick(), 0.05)
        self.assertEqual(driver.poller.revision, 1)
        self.assertEqual(bpy.context.scene.geno_wb.move, "jab")
        self.assertEqual(session.row, "Attack11")

    def test_overlay_only_hook_does_not_claim_fighter_was_posed(self):
        driver, session, bpy = self.make_driver(poses=False)
        driver.tick()
        self.assertEqual(session.frame, 8)
        self.assertEqual(driver.poller.revision, 0)

    def test_disconnect_or_closed_window_stops_transport_and_timer(self):
        for reason in ("disconnect", "window", "connection", "listener"):
            with self.subTest(reason=reason):
                driver, session, bpy = self.make_driver()
                if reason == "disconnect":
                    session.connected = False
                elif reason == "window":
                    bpy.context.window_manager.windows = []
                elif reason == "connection":
                    session.client = object()
                else:
                    driver.poller.failed = True
                self.assertIsNone(driver.tick())
                self.assertTrue(driver.poller.stopped)
                self.assertIsNone(session.info)


class PollerTest(unittest.TestCase):
    def test_transport_only_polls_ui_state_with_pid_and_current_ack(self):
        calls, closed = [], threading.Event()
        class Transport:
            def connect(self):
                pass
            def call(self, tool, args):
                calls.append((tool, args))
                if len(calls) == 1:
                    return {"revision": 0}
                raise client.WbError("connection closed")
            def close(self):
                closed.set()
        poller = sync.ViewPoller(Transport, pid=321, interval=0.001)
        poller.acknowledge(7)
        poller.start()
        self.assertTrue(closed.wait(1.0))
        self.assertEqual(calls[0], ("ui_view_state", {"revision": 7, "pid": 321}))
        self.assertTrue(poller.failed)
        self.assertTrue(all(tool == "ui_view_state" for tool, args in calls))

    def test_production_overlap_errors_retry_and_deliver_next_view(self):
        # Worker::call translates its overlap reply; McpServer uses English.
        for message in ("A command is already in progress",
                        "Ya hay un comando en curso",
                        "A tool call is already in progress"):
            with self.subTest(message=message):
                calls = []
                finished = threading.Event()
                snapshot = state(5)
                class Transport:
                    def connect(self):
                        pass
                    def call(self, tool, args):
                        calls.append((tool, args))
                        if len(calls) == 1:
                            raise client.WbError(message)
                        if len(calls) == 2:
                            return snapshot
                        raise client.WbError("connection closed")
                    def close(self):
                        if len(calls) >= 3:
                            finished.set()
                poller = sync.ViewPoller(Transport, pid=321, interval=0.001)
                poller.acknowledge(3)
                poller.start()
                try:
                    self.assertTrue(finished.wait(2.0))
                    self.assertEqual(poller.take(), snapshot)
                    self.assertEqual(calls, [
                        ("ui_view_state", {"revision": 3, "pid": 321}),
                        ("ui_view_state", {"revision": 3, "pid": 321}),
                        ("ui_view_state", {"revision": 3, "pid": 321}),
                    ])
                finally:
                    poller.stop()

    def test_busy_reply_retries_instead_of_stopping_and_close_is_worker_owned(self):
        calls, connected, closed = [], [], []
        finished = threading.Event()
        class Transport:
            def connect(self):
                connected.append(threading.get_ident())
            def call(self, tool, args):
                calls.append(args)
                if len(calls) == 1:
                    raise client.WbError("Workbench is busy")
                raise client.WbError("connection closed")
            def close(self):
                closed.append(threading.get_ident())
                if len(calls) > 1:
                    finished.set()
        poller = sync.ViewPoller(Transport, pid=321, interval=0.001)
        poller.start()
        self.assertTrue(finished.wait(2.0))
        self.assertEqual(len(calls), 2)
        self.assertTrue(connected)
        self.assertTrue(all(owner != threading.get_ident() for owner in closed))


if __name__ == "__main__":
    unittest.main()
