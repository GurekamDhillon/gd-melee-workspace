"""Aggregates every clip definition. all_clips() returns the Clip list; ALIASES maps engine rows to clips."""
import importlib
import clips_moves, clips_common

def all_clips():
    out = list(clips_moves.register())
    out += clips_common.register()
    names = [c.name for c in out]
    assert len(names) == len(set(names)), "duplicate clip names: " + str([n for n in names if names.count(n) > 1])
    return out

def aliases():
    return clips_common.ALIASES
