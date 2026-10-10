import threading
import time

import pytest

import api
import client
import framecache
from fake_engine import FakeWorkbench, ROW_FRAMES


def make(prefetch=True):
    fake = FakeWorkbench()
    port = fake.start()
    s = api.WbSession(lambda: client.McpClient(port=port, timeout=2.0))
    s.prefetch = prefetch
    assert s.connect() and s.refresh_rows()
    return fake, s


def wait_ready(s, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if s.cache_ready():
            return True
        time.sleep(0.01)
    return False


def set_frame_calls(fake):
    return [a["frame"] for t, a in fake.calls if t == "set_frame"]


def test_prefetch_fills_every_frame_and_playback_makes_no_engine_calls():
    fake, s = make()
    try:
        assert s.load_row("jab") and wait_ready(s)
        assert s.cache.progress() == (ROW_FRAMES["jab"], ROW_FRAMES["jab"])
        before = len(fake.calls)
        for n in list(range(1, ROW_FRAMES["jab"] + 1)) + [5, 3, 20]:
            assert s.set_frame(n) and s.info["frame"] == n
        assert s.step(-1) and s.step(1)
        assert len(fake.calls) == before          # every show came from the cache
        assert s.engine_calls == 0 and s.cache_hits > ROW_FRAMES["jab"]
    finally:
        fake.stop()


def test_prefetch_off_by_default_keeps_one_call_per_frame():
    fake, s = make(prefetch=False)
    try:
        assert s.load_row("jab")
        assert s.cache.progress() == (0, 0)
        n = len(set_frame_calls(fake))
        assert s.set_frame(4) and len(set_frame_calls(fake)) == n + 1
    finally:
        fake.stop()


def test_cached_frame_equals_engine_frame():
    fake, s = make()
    try:
        assert s.load_row("dair") and wait_ready(s)
        assert s.set_frame(7)
        cached = s.info
        s.cache.reset("test")
        assert s.set_frame(7)
        assert s.info["bones"] == cached["bones"] and s.info["frame"] == cached["frame"]
    finally:
        fake.stop()


@pytest.mark.parametrize("how", ["edit", "rebuild", "restart", "load", "facing", "disconnect"])
def test_cache_invalidated(how):
    fake, s = make()
    try:
        assert s.load_row("jab") and wait_ready(s)
        generation = s.cache.generation
        if how == "edit":
            assert s.edit_hitbox(row="jab", ordinal=0, damage=9)
            assert s.cache.progress()[0] == 0
        elif how == "rebuild":
            assert s.rebuild_reload()
        elif how == "restart":
            assert s.engine_restart()
            assert s.cache.progress()[0] == 0
        elif how == "load":
            assert s.load_row("dair")
        elif how == "facing":
            s.cache.facing = 1
            s._note_facing({"facing": -1})
            assert s.cache.progress()[0] == 0
        else:
            assert s.disconnect()
            assert s.cache.progress()[0] == 0
        assert s.cache.generation > generation
    finally:
        fake.stop()


def test_rebuild_refills_cache():
    fake, s = make()
    try:
        assert s.load_row("jab") and wait_ready(s)
        assert s.rebuild_reload() and wait_ready(s)
        assert s.cache.progress() == (ROW_FRAMES["jab"], ROW_FRAMES["jab"])
    finally:
        fake.stop()


def test_move_shorter_than_listed_is_learned_and_cache_shrinks():
    fake, s = make()
    try:
        s.rows = [dict(r, frames=ROW_FRAMES[r["name"]] + 10) for r in s.rows]   # list_rows overstates
        assert s.load_row("jab")
        end = time.time() + 5
        while time.time() < end and s.cache.loading:
            time.sleep(0.01)
        s.pump_cache()
        assert s.row_lengths["jab"] == ROW_FRAMES["jab"]
        assert s.cache.progress()[0] == ROW_FRAMES["jab"]
        assert s.cache_ready()
    finally:
        fake.stop()


def test_run_checks_failure_keeps_row_and_asks_for_no_frame_zero():
    fake, s = make()
    try:
        assert s.load_row("dair") and wait_ready(s) and s.set_frame(7)
        fake.checks_unload = True
        assert s.run_checks() is False and "frame 0" in s.last_error
        assert s.loaded_row == "dair" and s.row == "dair" and s.frame == 7
        assert fake.current_row == "dair"                       # the engine row was put back
        assert wait_ready(s)                                    # and the paused cache fill resumed
        fake.checks_unload = False
        assert s.set_frame(9) and s.info["frame"] == 9          # no "no row loaded"
        assert 0 not in set_frame_calls(fake)
        assert s.run_checks() and fake.current_row == "dair"
    finally:
        fake.stop()


def test_prefetch_paused_around_edit_and_checks():
    fake, s = make()
    try:
        assert s.load_row("wait")
        assert s.run_checks()
        assert wait_ready(s)
    finally:
        fake.stop()


def test_framecache_drops_stale_generation():
    cache = framecache.FrameCache()
    gate = threading.Event()

    def slow(n):
        gate.wait(2)
        return {"frame": n}

    assert cache.begin("a", 1, 3, slow)
    cache.generation += 1          # an invalidation arrives while the worker is mid-fetch
    gate.set()
    cache.cancel()
    assert cache.get("a", 1) is None and cache.progress()[0] == 0


def test_framecache_resume_fetches_only_missing():
    cache = framecache.FrameCache()
    seen = []

    def fetch(n):
        seen.append(n)
        return {"frame": n}

    cache.begin("a", 1, 3, fetch)
    cache.cancel(wait=True)
    time.sleep(0.05)
    seen.clear()
    cache.frames.pop(2, None)
    assert cache.begin("a", 1, 3, fetch) in (True, False)
    cache.cancel(wait=True)
    time.sleep(0.05)
    assert set(seen) <= {2}


def test_framecache_error_stops_fill_and_is_reported():
    cache = framecache.FrameCache()

    def fetch(n):
        if n == 3:
            raise client.WbError("frame 3 is past the end of this move; last frame 2")
        return {"frame": n}

    cache.begin("a", 1, 5, fetch)
    end = time.time() + 2
    while time.time() < end and cache.loading:
        time.sleep(0.01)
    assert sorted(cache.frames) == [1, 2] and "last frame 2" in cache.error


def test_playback_rate_defaults_to_game_speed_and_follows_setting():
    assert api.playback_rate("1", 24) == 60.0
    assert api.playback_rate("0.5", 24) == 30.0
    assert api.playback_rate("0.25", 24) == 15.0
    assert api.playback_rate("scene", 24) == 24.0
    assert api.playback_rate("scene", 23.976) == pytest.approx(23.976)
    assert api.playback_rate("bogus", 24) == 60.0
