#!/usr/bin/env python3
"""vis_channels.py - Ultimate mesh visibility -> Melee ModelVis "models" (independent selectors).

Ultimate shows and hides whole meshes by name with a Visibility track: any subset of the controlled
meshes can be on at a frame (an eye mesh, a lid mesh, a mouth mesh and a blush overlay together).
Melee's ftData x8 part-visibility table is different: it holds up to 11 MODELS, each with a list of
STATES, each state a list of DObj indexes, and one current state per model (ModelVis(model, state)).
ftParts_80074B6C shows the current state's DObjs and HIDES every other state's of that model, in
state order. Two consequences, both met by Sora (`trail`) before this module:

  * States of one model must not share a DObj. A later state that lists a DObj re-hides it after the
    current state showed it, so a mesh listed in many states is hidden whichever state is current
    (Sora's eyes and open lids sat in 30 overlapping states and were never drawn).
  * A DObj in no state of any model is never hidden: it is drawn always (the blush overlay and the
    closed-lid expression meshes covered the face).

So the visible set is modelled as CHANNELS: each channel is one ModelVis model, state 0 is "none of
its meshes", state k > 0 is exactly mesh group k-1. Groups that are never visible together in any
frame of any clip (the eye shapes, the blink/lid shapes, the mouth shapes) share a channel; groups
that are visible together get different channels. A frame's visible set is then one state per channel.
"""

MAX_MODELS = 11   # ftParts_8007487C: "fighter parts model num over!" above 11


def plan_channels(frame_sets, groups):
    """Partition `groups` into channels. `frame_sets` is every visible set (an iterable of group-name
    collections) that occurs in the clips, base layer included. Groups that never co-occur may share
    a channel; the greedy colouring is deterministic (most-constrained groups first, name order).
    Returns a list of channels, each a sorted list of group names."""
    groups = sorted(set(groups))
    together = {g: set() for g in groups}
    for s in frame_sets:
        s = [g for g in s if g in together]
        for a in s:
            together[a].update(b for b in s if b != a)
    channels = []
    for g in sorted(groups, key=lambda g: (-len(together[g]), g)):
        for ch in channels:
            if not any(o in together[g] for o in ch):
                ch.append(g)
                break
        else:
            channels.append([g])
    channels = [sorted(ch) for ch in channels]
    channels.sort(key=lambda ch: (-len(ch), ch[0]))
    if len(channels) > MAX_MODELS:
        raise ValueError(f"{len(channels)} independent mesh-visibility channels needed, the engine holds "
                         f"{MAX_MODELS}: {[ch[0] + ('+%d' % (len(ch) - 1) if len(ch) > 1 else '') for ch in channels]}")
    return channels


def channel_states(visible, channels):
    """One frame's visible set -> the tuple of per-channel states (0 = none, k = channel[k-1])."""
    out = []
    for ch in channels:
        on = [k + 1 for k, g in enumerate(ch) if g in visible]
        if len(on) > 1:
            raise ValueError(f"visible together in one channel: {[ch[k - 1] for k in on]}")
        out.append(on[0] if on else 0)
    return tuple(out)


def events_for(sequence, channels):
    """A clip's per-frame visible sets -> [(frame, (channel, state))], one entry per channel at frame 0
    and one for each channel whose state changes afterwards."""
    prev, events = None, []
    for f, visible in enumerate(sequence):
        cur = channel_states(visible, channels)
        for c, st in enumerate(cur):
            if prev is None or st != prev[c]:
                events.append((f, (c, st)))
        prev = cur
    return events


def state_lists(channels, dobj_groups):
    """For one costume: per channel, per state, the DObj indexes (`dobj_groups[i]` is DObj i's
    visibility group or None). State 0 is empty."""
    return [[[]] + [[i for i, g in enumerate(dobj_groups) if g == name] for name in ch] for ch in channels]


def apply_events(events, frames, channel_count):
    """Replay `events` over `frames` frames: the per-channel state at each frame (a test oracle)."""
    cur = [None] * channel_count
    out = []
    pend = sorted(events, key=lambda e: e[0])
    for f in range(frames):
        while pend and pend[0][0] <= f:
            _, (c, st) = pend.pop(0)
            cur[c] = st
        out.append(tuple(cur))
    return out
