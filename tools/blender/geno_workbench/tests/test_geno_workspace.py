import geno_workspace as gw


def test_sync_moves_playhead_to_workbench_frame():
    assert gw.frame_to_sync(1, 12, True, False) == 12


def test_sync_noop_when_equal_or_disconnected():
    assert gw.frame_to_sync(12, 12, True, False) is None
    assert gw.frame_to_sync(1, 12, False, False) is None


def test_sync_leaves_baked_animation_alone():
    assert gw.frame_to_sync(1, 12, True, True) is None


def test_sync_bad_frame():
    assert gw.frame_to_sync(1, None, True, False) is None
    assert gw.frame_to_sync(1, "x", True, False) is None


def test_names():
    assert gw.NAME == "Geno" and "VIEW_3D" in gw.WANT_AREAS


def test_sidebar_tab_matches_panels():
    from props import STRINGS
    assert gw.SIDEBAR_TAB == STRINGS["tab"]
