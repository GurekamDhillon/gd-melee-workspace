"""Melee subaction-script (ftcmd) editing for the Meta Knight effects pass.

A script is a list of commands (op, words). Word lengths: Melee ops 0..58 from ftaction.c (the table melee_dump.py uses);
op 59 is a Geno escape whose length is its own [19:16] field (geno_v1_encodings.md). Timing follows the brawl-kirby
convention: counter 0-based, SyncWait n adds n, AsyncWait n moves to n (a command after the wait runs on that counter).

insert(cmds, events) merges (counter, words, label) events into the timeline without moving any existing command's
counter: a wait that straddles an event is split around it. Loops: in a script that ends in Goto (a looping row) events
past the last wait before the Goto are dropped (the cycle never reaches them); SetLoop/ExecLoop bodies are treated as
opaque (events inside them go after the loop - reported). Geno IF / SKIP / IFV skip counts are widened when an insert
lands inside the range they skip.
"""
import struct

LEN = [1, 1, 1, 1, 1, 2, 1, 2, 1, 1] + [5, 5, 1, 1, 1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 1, 1, 7, 4,
                                        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 3, 2, 1, 4]
assert len(LEN) == 59
END, SYNC, ASYNC, SETLOOP, EXECLOOP, SUB, RET, GOTO = 0, 1, 2, 3, 4, 5, 6, 7
GFX, TRAIL, GENO = 10, 49, 59


def cmd_len(w):
    op = w >> 26
    if op == GENO:
        return max(1, (w >> 16) & 0xF)
    return LEN[op] if op < len(LEN) else 1


def parse_words(words):
    """Word list (overlay) -> [(op, [words])]."""
    out = []; i = 0
    while i < len(words):
        L = cmd_len(words[i]); out.append((words[i] >> 26, list(words[i:i + L]))); i += L
    return out


def parse_at(u32, off, limit=4000):
    """Pl-file script at data offset `off` -> [(op, words, offset)], up to End / Return / Goto (inclusive)."""
    out = []; o = off
    while len(out) < limit:
        w = u32(o); op = w >> 26
        L = cmd_len(w)
        out.append((op, [u32(o + 4 * k) for k in range(L)], o))
        o += 4 * L
        if op in (END, RET, GOTO):
            break
    return out


def wait_value(w): return w & 0x3FFFFFF


def run_sub(u32, target, f, depth=0, stack=()):
    """Counter after a Subroutine call to Pl-data offset `target` returns, entered at counter f. Follows the body the way
    ftAction runs it: SyncWait adds, AsyncWait moves to (absolute counter), SetLoop n / ExecLoop repeat the body n times,
    nested Subroutines recurse, Gotos are followed. Guards: a Subroutine already on the call stack (or deeper than 16)
    counts 0 frames, a Goto back to an offset already jumped to (an endless loop) and a 20000-command budget stop the
    walk where they are."""
    if u32 is None or depth > 16 or target in stack:
        return f
    stack = stack + (target,)
    pc = target; loops = []; gotos = set(); steps = 0
    while steps < 20000:
        steps += 1
        w = u32(pc); op = w >> 26; L = cmd_len(w)
        if op == SYNC: f += wait_value(w)
        elif op == ASYNC: f = max(f, wait_value(w))
        elif op == SETLOOP: loops.append([pc + 4 * L, wait_value(w)])
        elif op == EXECLOOP:
            if loops:
                loops[-1][1] -= 1
                if loops[-1][1] > 0: pc = loops[-1][0]; continue
                loops.pop()
        elif op == SUB: f = run_sub(u32, u32(pc + 4), f, depth + 1, stack)
        elif op == GOTO:
            t = u32(pc + 4)
            if t in gotos: return f
            gotos.add(t); pc = t; continue
        elif op in (END, RET): return f
        pc += 4 * L
    return f


def timeline(cmds, u32=None):
    """Counter at which each command runs. With u32 (the Pl-data reader), a Subroutine call adds the time its body
    waits (run_sub); without it a call counts 0 frames."""
    f = 0; res = []
    for op, words, *_ in cmds:
        res.append(f)
        if op == SYNC: f += wait_value(words[0])
        elif op == ASYNC: f = max(f, wait_value(words[0]))
        elif op == SUB and u32 is not None: f = run_sub(u32, words[1], f)
    return res, f


def gfx_words(gfx_id, bone, off=(0, 0, 0), rng=(0, 0, 0), destroy=False):
    """Melee GFX (op 10, 5 words). off/rng: joint-local x, y, z (units), as ftAction_80071028 reads them."""
    def s16(v): return int(round(v * 256)) & 0xFFFF
    w0 = (GFX << 26) | ((bone & 0xFF) << 18) | ((1 if destroy else 0) << 16)
    w1 = (gfx_id & 0xFFFF) << 16
    w2 = (s16(off[0]) << 16) | s16(off[1])
    w3 = (s16(off[2]) << 16) | (int(round(abs(rng[0]) * 256)) & 0xFFFF)
    w4 = ((int(round(abs(rng[1]) * 256)) & 0xFFFF) << 16) | (int(round(abs(rng[2]) * 256)) & 0xFFFF)
    return [w0, w1, w2, w3, w4]


def trail_word(on): return (TRAIL << 26) | (0 if on else 0x1FFFFFF)


def insert(cmds, events, strip=(), keep_after_end=True, clip=None, u32=None):
    """cmds: [(op, words[, offset])]; events: [(counter, words, label)].
    strip: set of ops whose commands are dropped (the row's old GFX, when this pass replaces them).
    u32: Pl-data reader; with it a Subroutine call advances the counter by its body's wait time (run_sub). An event
    that falls inside a call is placed right after it returns.
    Returns (new_cmds [(op, words, old_index or None)], report)."""
    ev = sorted(events, key=lambda e: e[0])
    out = []; cur = 0; k = 0; rep = {"placed": [], "dropped": [], "stripped": 0, "after_loop": []}
    looping = any(c[0] == GOTO for c in cmds)
    in_loop = 0

    def emit_upto(limit_exclusive):
        nonlocal k
        while k < len(ev) and ev[k][0] < limit_exclusive:
            out.append((ev[k][1][0] >> 26, list(ev[k][1]), None)); rep["placed"].append((max(ev[k][0], cur), ev[k][2])); k += 1

    for idx, c in enumerate(cmds):
        op, words = c[0], c[1]
        if op in strip:                                          # (the effects pass strips GFX; the visuals pass SetTexAnim)
            rep["stripped"] += 1; continue
        if op == SETLOOP: in_loop += 1
        if op in (SYNC, ASYNC) and not in_loop:
            target = cur + wait_value(words[0]) if op == SYNC else max(cur, wait_value(words[0]))
            emit_upto(cur + 1)                                   # events due now (or late) before the wait
            while k < len(ev) and ev[k][0] < target:
                f = ev[k][0]
                if op == SYNC: out.append((SYNC, [(SYNC << 26) | (f - cur)], None))
                else: out.append((ASYNC, [(ASYNC << 26) | f], None))
                cur = f
                emit_upto(f + 1)
            if op == SYNC:
                out.append((SYNC, [(SYNC << 26) | (target - cur)], idx))
            else:
                out.append((ASYNC, list(words), idx))
            cur = target
            continue
        if op in (SYNC, ASYNC) and in_loop:
            out.append((op, list(words), idx)); continue
        if op == SUB and u32 is not None and not in_loop:
            emit_upto(cur + 1)
            out.append((op, list(words), idx)); cur = run_sub(u32, words[1], cur)
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


def to_words(cmds):
    return [w for c in cmds for w in c[1]]


def fix_overlay_skips(old_cmds, new_cmds):
    """old_cmds: parse_words(old); new_cmds: insert() output (old index per command). For every Geno IF/SKIP/IFV in
    new_cmds, the target is the old command it skipped to; recompute the word count to that command in new_cmds."""
    old_pos = []; p = 0
    for op, words in old_cmds:
        old_pos.append(p); p += len(words)
    old_end = p
    # old word position -> old command index
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
            if fld is not None:
                old_after = old_pos[oi] + len(words)
                tgt_old = old_after + words[fld]
                if tgt_old == old_end: tgt_new_pos = new_end
                else:
                    ti = pos2idx[tgt_old]; tgt_new_pos = new_pos[idx2new[ti]]
                    # inserted commands directly before the old target stay inside the skipped block only if they
                    # were placed before it; place the landing point at the first inserted command that precedes it
                    j = idx2new[ti]
                    while j > 0 and new_cmds[j - 1][2] is None and new_pos[j - 1] > new_pos[i]:
                        j -= 1
                    tgt_new_pos = new_pos[j] if j > i else tgt_new_pos
                nw = list(words); nw[fld] = tgt_new_pos - (new_pos[i] + len(words))
                if nw[fld] != words[fld]: fixed.append((i, words[fld], nw[fld]))
                new_cmds[i] = (op, nw, oi)
    return new_cmds, fixed
