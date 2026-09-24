"""Melee subaction-script editing for the sound pass: effects/tools/ftscript.py's insert() and fix_overlay_skips(),
with any op strippable (the effects pass strips only GFX) and skip targets that land on a stripped command moved to the
next command that survives. Everything else (parse_at, parse_words, timeline, ...) is ftscript's."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "effects", "tools"))
from ftscript import *          # noqa: F401,F403  (LEN, cmd_len, parse_at, parse_words, timeline, to_words, ops)
import ftscript as _FS

SFX, SMASH = 17, 18             # ftcmd 0x11 (3 words: behavior | id | volume, pan) and 0x12 (random smash voice, 1 word)
STOP_OF = {1: 10, 2: 11, 3: 12, 4: 13, 5: 14, 6: 15}   # play behavior -> the behavior that stops its channel
NONE_ID = 0x83D60              # 540000: Melee's "no sound" (ftData sfx fields, ft_800881D8 ignores it)


def sfx_words(sid, behavior=0, vol=0x7F, pan=0x40):
    return [(SFX << 26) | ((behavior & 0xFF) << 18), sid & 0xFFFFFFFF, ((vol & 0xFF) << 8) | (pan & 0xFF)]


def stop_words(behavior):
    return [(SFX << 26) | ((STOP_OF[behavior] & 0xFF) << 18), 0, 0]


def smash_word():
    return [SMASH << 26]


def insert(cmds, events, strip=None, clip=None, u32=None):
    """ftscript.insert, but strip(cmd) -> bool decides which old commands are dropped."""
    ev = sorted(events, key=lambda e: e[0])
    out = []; cur = 0; k = 0; rep = {"placed": [], "dropped": [], "stripped": 0}
    in_loop = 0

    def emit_upto(limit_exclusive):
        nonlocal k
        while k < len(ev) and ev[k][0] < limit_exclusive:
            out.append((ev[k][1][0] >> 26, list(ev[k][1]), None)); rep["placed"].append((max(ev[k][0], cur), ev[k][2])); k += 1

    for idx, c in enumerate(cmds):
        op, words = c[0], c[1]
        if strip is not None and strip(c):
            rep["stripped"] += 1; continue
        if op == SETLOOP: in_loop += 1
        if op in (SYNC, ASYNC) and not in_loop:
            target = cur + wait_value(words[0]) if op == SYNC else max(cur, wait_value(words[0]))
            emit_upto(cur + 1)
            while k < len(ev) and ev[k][0] < target:
                f = ev[k][0]
                if op == SYNC: out.append((SYNC, [(SYNC << 26) | (f - cur)], None))
                else: out.append((ASYNC, [(ASYNC << 26) | f], None))
                cur = f
                emit_upto(f + 1)
            if op == SYNC: out.append((SYNC, [(SYNC << 26) | (target - cur)], idx))
            else: out.append((ASYNC, list(words), idx))
            cur = target
            continue
        if op in (SYNC, ASYNC) and in_loop:
            out.append((op, list(words), idx)); continue
        if op == SUB and u32 is not None and not in_loop:
            emit_upto(cur + 1)
            out.append((op, list(words), idx)); cur = _FS.run_sub(u32, words[1], cur)
            continue
        if op == EXECLOOP:
            in_loop = max(0, in_loop - 1)
            out.append((op, list(words), idx)); continue
        if op in (END, RET, GOTO):
            emit_upto(cur + 1)
            if op == GOTO:
                for e in ev[k:]: rep["dropped"].append((e[0], e[2], "past the loop cycle (counter %d)" % cur))
                k = len(ev)
            else:
                while k < len(ev):
                    f = ev[k][0]
                    if clip is not None and f >= clip:
                        rep["dropped"].append((f, ev[k][2], "past the clip (%d frames)" % clip)); k += 1; continue
                    if f > cur:
                        out.append((ASYNC, [(ASYNC << 26) | f], None)); cur = f
                    emit_upto(f + 1)
            out.append((op, list(words), idx))
            continue
        out.append((op, list(words), idx))
    return out, rep


def fix_overlay_skips(old_cmds, new_cmds):
    """ftscript.fix_overlay_skips, tolerant of stripped commands (a skip whose old target was stripped lands on the next
    old command that survived, or the end)."""
    old_pos = []; p = 0
    for op, words in old_cmds:
        old_pos.append(p); p += len(words)
    old_end = p
    pos2idx = {pp: i for i, pp in enumerate(old_pos)}
    new_pos = []; p = 0
    for c in new_cmds:
        new_pos.append(p); p += len(c[1])
    new_end = p
    idx2new = {c[2]: i for i, c in enumerate(new_cmds) if c[2] is not None}
    fixed = []
    for i, c in enumerate(new_cmds):
        op, words, oi = c
        if op == GENO and oi is not None:
            sub = (words[0] >> 20) & 0x3F
            fld = {0x10: 2, 0x11: 1, 0x12: 3}.get(sub)
            if fld is None:
                continue
            old_after = old_pos[oi] + len(words)
            tgt_old = old_after + words[fld]
            if tgt_old == old_end:
                tgt_new_pos = new_end
            else:
                ti = pos2idx[tgt_old]
                while ti < len(old_cmds) and ti not in idx2new: ti += 1
                if ti >= len(old_cmds):
                    tgt_new_pos = new_end
                else:
                    j = idx2new[ti]; tgt_new_pos = new_pos[j]
                    while j > 0 and new_cmds[j - 1][2] is None and new_pos[j - 1] > new_pos[i]:
                        j -= 1
                    tgt_new_pos = new_pos[j] if j > i else tgt_new_pos
            nw = list(words); nw[fld] = tgt_new_pos - (new_pos[i] + len(words))
            if nw[fld] != words[fld]: fixed.append((i, words[fld], nw[fld]))
            new_cmds[i] = (op, nw, oi)
    return new_cmds, fixed


_FS_insert = _FS.insert   # (kept for reference: the effects pass's version)
