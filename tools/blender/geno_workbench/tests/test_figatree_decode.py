import importlib
import importlib.util
import math
import struct

import pytest

from figatree_fixtures import F, archive, bank, model, stream, varint


def decoder():
    assert importlib.util.find_spec("figatree_decode") is not None, "figatree decoder is missing"
    return importlib.import_module("figatree_decode")


@pytest.mark.parametrize("frac,encoded,want", [
    (0, struct.pack("<f", -1.25), -1.25),
    (0x24, struct.pack("<h", -20), -1.25),
    (0x44, struct.pack("<H", 40000), 2500),
    (0x63, b"\xf6", -1.25),
    (0x82, b"\xff", 63.75),
])
def test_all_key_compression_formats(frac, encoded, want):
    keys = decoder().decode_keys(b"\x01" + encoded, frac, 0)
    assert keys[0].value == want
    assert keys[0].wait is None


def test_packed_counts_and_multibyte_waits():
    # 130 LIN keys: (count - 1) = 129 = 1 + (16 << 3).
    body = b"\x92\x10" + b"".join(struct.pack("<h", i) + (varint(130) if i < 129 else b"") for i in range(130))
    keys = decoder().decode_keys(body, 0x20, 0)
    assert len(keys) == 130
    assert keys[0].wait == 130 and keys[-1].value == 129


@pytest.mark.parametrize("keys,frame,want", [
    ([(1, 2, None, 4), (1, 6, None, None)], 3.99, 2),
    ([(1, 2, None, 4), (1, 6, None, None)], 4, 6),
    ([(2, 2, None, 4), (2, 6, None, None)], 1, 3),
    ([(3, 0, None, 2), (3, 2, None, None)], .5, .3125),
    ([(3, 0, None, 2), (4, 2, -1, None)], 1, 1.25),
    ([(4, 0, 2, 2), (5, None, -1, None), (4, 4, 0, None)], 1, 1.75),
    # SLP between LIN keys supplies the incoming slope, not the outgoing one.
    ([(2, 0, None, 2), (5, None, 2, None), (2, 4, None, None)], 1, 1.5),
    ([(6, 2, None, 4), (6, 6, None, None)], 3.99, 2),
    ([(6, 2, None, 4), (6, 6, None, None)], 4, 6),
    ([(2, 0, None, 0), (2, 2, None, 2), (2, 4, None, None)], 0, 2),
    ([(2, 0, None, 0), (2, 2, None, 2), (2, 4, None, None)], 1, 3),
])
def test_fobj_interpolation(keys, frame, want):
    d = decoder()
    clip = d.read_bank(archive([[(5, stream(keys), 0, 0)]]))[0]
    assert clip.joints[0][0].evaluate(frame, default=9) == pytest.approx(want)


def test_startframe_is_signed_and_is_added_to_the_clock():
    d = decoder()
    keys = [(2, 2, None, 4), (2, 6, None, None)]
    clip = d.read_bank(archive([[(5, stream(keys), 0, 0)]], starts={0: -2}))[0]
    track = clip.joints[0][0]
    assert track.start == -2
    assert [track.evaluate(f, default=9) for f in (0, 1, 2, 3, 6)] == [9, 9, 2, 3, 6]
    clip = d.read_bank(archive([[(5, stream(keys), 0, 0)]], starts={0: 2}))[0]
    assert clip.joints[0][0].evaluate(0) == 4


def test_mixed_key_packets_preserve_rest_until_launch_and_override_interpolation():
    keys = [(6, 2, None, 2), (2, 6, None, 2), (6, 10, None, None)]
    track = decoder().read_bank(archive([[(5, stream(keys), 0, 0)]]))[0].joints[0][0]
    assert [track.evaluate(f, default=9) for f in (0, 1, 2, 3, 4)] == [9, 9, 6, 6, 10]


def test_terminal_linear_and_spline_segments_continue_within_longer_clips():
    linear = [(2, 2, None, 4), (2, 6, None, None)]
    spline = [(4, 0, 0, 2), (4, 2, 0, None)]
    a = decoder().read_bank(archive([[(5, stream(linear), 0, 0)]], frames=6))[0].joints[0][0]
    b = decoder().read_bank(archive([[(5, stream(spline), 0, 0)]], frames=4))[0].joints[0][0]
    assert [a.evaluate(f) for f in (4, 5, 6)] == [6, 7, 8]
    assert b.evaluate(3) == -0.0  # Hermite u=1.5, 0 -> 2, both slopes zero.


def test_bank_names_empty_nodes_and_plan_slices():
    a = archive([[], [(8, *F.encode_const(1.5)[:3])]], name="PlySynthetic_ACTION_Stretch_figatree")
    b = archive([[], []], frames=0, name="PlySynthetic_ACTION_Rest_figatree")
    d = decoder()
    clips = d.read_bank(bank(a, b))
    assert [clip.name for clip in clips] == ["Stretch", "Rest"]
    assert len(clips[0].joints) == 2 and clips[1].frames == 0
    plan = {"clips": {"new": {"offset": 0, "bytes": len(a)}}}
    assert [clip.name for clip in d.read_bank(bank(a, b), plan)] == ["new"]


@pytest.mark.parametrize("body", [b"\x07", b"\x01\x00", b"\x82", b"\x02" + struct.pack("<f", 1) + b"\x80",
                                        b"\x12" + struct.pack("<f", 1)])
def test_truncated_or_unknown_keys_are_rejected(body):
    with pytest.raises(ValueError):
        decoder().decode_keys(body, 0, 0)


def test_nonfinite_and_invalid_compression_are_rejected():
    d = decoder()
    for fv, body in [(0, b"\x01" + struct.pack("<f", math.nan)), (0xA0, b"\x01\0\0\0\0")]:
        with pytest.raises(ValueError):
            d.decode_keys(body, fv, 0)


def test_bad_bank_bounds_and_missing_node_terminator_are_rejected():
    d = decoder()
    raw = bytearray(archive([[]]))
    for bad in (bytes(raw[:25]), bytes(raw[:-1]), bank(bytes(raw)) + b"garbage"):
        with pytest.raises(ValueError):
            d.read_bank(bad)
    dsz, nrel = struct.unpack_from(">II", raw, 4)
    root = struct.unpack_from(">I", raw, 32 + dsz + nrel * 4)[0]
    struct.pack_into(">I", raw, 32 + root + 12, dsz + 100)
    with pytest.raises(ValueError):
        d.read_bank(bytes(raw))


def test_model_rest_walk_uses_relocations_and_depth_first_order():
    raw = model([(None, (0, 0, .5), (2, 3, 4), (1, 2, 3), 8),
                 (0, (0, .25, 0), (0, 5, 0), (1, 1, 1), 8),
                 (0, (0, 0, 0), (0, 0, 1), (1, 1, 1), 8)])
    joints = decoder().read_model(raw)
    assert [joint.parent for joint in joints] == [None, 0, 0]
    assert joints[0].translation == (2, 3, 4)
    assert joints[0].scale == (1, 2, 3)
    assert joints[1].rotation == (0, .25, 0)


def test_exporter_roundtrip_keeps_spline_curves_without_changing_exporter():
    pts = [(0, -.5, .25), (2, .75, -.125), (5, .25, 0)]
    body, fv, fs, _ = F.encode_spline(pts, 0x2C, 0x2C)
    imported = decoder().read_bank(archive([[(1, body, fv, fs)]], frames=5))[0].joints[0][0]
    rebuilt_pts, t = [], 0
    for key in imported.keys:
        rebuilt_pts.append((t, key.value, key.slope))
        t += key.wait or 0
    rebuilt, rfv, rfs, _ = F.encode_spline(rebuilt_pts, fv, fs)
    assert (rebuilt, rfv, rfs) == (body, fv, fs)
    expected_keys = F.decode_keys(rebuilt, 0, len(rebuilt), rfv, rfs)
    for frame in (0, .25, .5, 1, 1.5, 2, 2.5, 4.25, 5):
        assert imported.evaluate(frame) == pytest.approx(F.evaluate(expected_keys, frame), abs=1e-7)
