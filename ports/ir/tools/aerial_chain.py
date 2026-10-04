#!/usr/bin/env python3
"""aerial_chain.py - the stage table of a fighter's status-driven aerial chain (Sora nair/fair 1-3).

Pure data, no Geno emission (that belongs to trail_specials_geno.py): for each stage it names the
ACMD game script, the clip, cancel frame, FT_MOTION_RATE segments, and the clip frames of the two
work-flag raises that open the chain-input window and the transition (0xe54c / 0xe540 for nair and
fair stage 2, 0xe56c / 0xe560 for fair stage 1; fair 2 and 3 reuse the nair 2 and 3 clips). See
_build/audit-20261003/sora-normals/aerial-chain-design.md for how a Geno state should consume it.
"""
CHAINS = {"nair": ("game_attackairn", "game_attackairn2", "game_attackairn3"),
          "fair": ("game_attackairf", "game_attackairf2", "game_attackairf3")}
# const_value_table ids: (input window opens, transition allowed) per script
WINDOW_FLAGS = {"game_attackairn": ("0xe54c", "0xe540"), "game_attackairn2": ("0xe54c", "0xe540"),
                "game_attackairf": ("0xe56c", "0xe560"), "game_attackairf2": ("0xe54c", "0xe540")}


def _flag_frame(row, const, cmd="WorkModule::on_flag"):
    frames = [c["frame"] for c in row["commands"] if c["cmd"] == cmd and c["args"] == [{"const": const}]]
    return max(frames) if frames else None


def stage_table(rows, chain):
    """[{stage, script, clip, cancel, rates, window_open, transition, first_hit, hit_damage}] or raises."""
    out = []
    for stage, script in enumerate(CHAINS[chain], 1):
        row = rows[script]
        opens, trans = WINDOW_FLAGS.get(script, (None, None))
        attacks = sorted((c["frame"], c["named"]["damage"]) for c in row["commands"]
                         if c["cmd"] == "ATTACK" and c.get("named"))
        out.append({"stage": stage, "script": script, "clip": row["motion"]["clip"],
                    "cancel": row["motion"]["cancel_frame"],
                    "rates": sorted((c["frame"], c["args"][-1]) for c in row["commands"]
                                    if c["cmd"] == "FT_MOTION_RATE"),
                    "window_open": _flag_frame(row, opens) if opens else None,
                    "transition": _flag_frame(row, trans) if trans else None,
                    "first_hit": attacks[0][0] if attacks else None,
                    "hit_damage": attacks[0][1] if attacks else None})
    return out
