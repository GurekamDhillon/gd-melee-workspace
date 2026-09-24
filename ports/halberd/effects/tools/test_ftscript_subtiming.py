"""ftscript: a Subroutine call runs its body's waits inside the caller's timeline.  python effects/tools/test_ftscript_subtiming.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ftscript as FS


def mem(blocks):
    """{offset: [words]} -> u32(offset) reader."""
    m = {}
    for base, ws in blocks.items():
        for i, w in enumerate(ws): m[base + 4 * i] = w
    return lambda o: m[o]


def test_subroutine_timing():
    SYNC = lambda n: (FS.SYNC << 26) | n
    GFX0 = FS.GFX << 26
    blink = [13 << 26, SYNC(7), FS.RET << 26]                           # a 1-word command, SyncWait 7, Return
    outer = [(FS.SUB << 26), 0x100, SYNC(3), (FS.SUB << 26), 0x200, FS.RET << 26]   # blink, SyncWait 3, then itself (guarded: 0)
    recur = [(FS.SUB << 26), 0x300, (FS.SUB << 26), 0x100, FS.RET << 26]  # calls itself (guarded: 0 frames), then blink
    loop = [(FS.SETLOOP << 26) | 3, SYNC(2), FS.EXECLOOP << 26, FS.RET << 26]   # 3 x 2 frames
    u32 = mem({0x100: blink, 0x200: outer, 0x300: recur, 0x400: loop})
    cmds = [(FS.SYNC, [SYNC(20)]), (FS.SUB, [FS.SUB << 26, 0x100]), (FS.GFX, [GFX0] * 5),
            (FS.SUB, [FS.SUB << 26, 0x200]), (FS.SUB, [FS.SUB << 26, 0x300]), (FS.SUB, [FS.SUB << 26, 0x400]),
            (FS.GFX, [GFX0] * 5), (FS.END, [0])]
    tl, end = FS.timeline(cmds, u32=u32)
    assert tl == [0, 20, 27, 27, 37, 44, 50, 50], tl                      # 20+7 blink; +7+3 nested; +7 after the guarded self-call; +3x2 loop
    assert FS.timeline(cmds)[0][2] == 20                                  # without a reader: the old 0-frame call
    # insert(): an event at frame 30 lands after the 7-frame blink, i.e. at true frame 30, not 37
    new, rep = FS.insert([(FS.SYNC, [SYNC(20)], 0), (FS.SUB, [FS.SUB << 26, 0x100], 4), (FS.SYNC, [SYNC(20)], 12),
                          (FS.END, [0], 16)], [(30, [GFX0] * 5, "fx")], u32=u32)
    ntl, _ = FS.timeline(new, u32=u32)
    assert [f for f, c in zip(ntl, new) if c[2] is None and c[0] == FS.GFX] == [30], (ntl, new)
    assert ntl[-1] == 47


if __name__ == "__main__":
    test_subroutine_timing(); print("ok")
