"""Check ftcmd control flow and adapt kept host animation loops to a new clip.

Offsets are HSD data offsets. The memory object supplies u32/put/ptr/alloc/data/relocs,
as install_ultimate.Writer does. No game or disc access is needed here.
"""
import json
import re
import struct
from pathlib import Path

FLOW_LEN = (1, 1, 1, 1, 1, 2, 1, 2, 1, 1)
OP_LEN = (5, 5, 1, 1, 1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
          3, 1, 1, 1, 7, 4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 3, 2, 1, 4)
MAX_COMMANDS = 16000


def _length(word):
    op = word >> 26
    if op < 10:
        return FLOW_LEN[op]
    if op == 59:
        return max(1, (word >> 16) & 15)
    if op - 10 < len(OP_LEN):
        return OP_LEN[op - 10]
    raise ValueError(f"unsupported ftcmd opcode {op}")


def _inspect(memory, start):
    """Walk reachable commands, including goto targets, subroutines and counted loops.

    Only op 8 and a positive synchronous wait guarantee progress on every pass.
    Op 2 is deliberately excluded: after frame_count passes its target it can set
    a nonpositive timer forever (lbcommand.c Command_02).
    """
    todo = [(start, (), (), False)]
    visited, nodes, edges, unsafe = set(), {}, {}, {}
    while todo:
        at, loops, calls, waited = todo.pop()
        state = (at, loops, calls, waited)
        if state in visited:
            continue
        visited.add(state)
        if len(visited) > MAX_COMMANDS:
            raise ValueError(f"script 0x{start:X}: control flow exceeds {MAX_COMMANDS} states")
        if at < 0 or at % 4 or at + 4 > len(memory.data):
            raise ValueError(f"script 0x{start:X}: invalid command pointer 0x{at:X}")
        word = memory.u32(at)
        op, length = word >> 26, _length(word)
        following = at + 4 * length
        if following > len(memory.data):
            raise ValueError(f"script 0x{start:X}: truncated command at 0x{at:X}")
        nodes[at] = (op, length)
        if op == 0:
            next_states = []
        elif op == 3:
            if len(loops) >= 8:
                raise ValueError(f"script 0x{start:X}: too many nested loops")
            next_states = [(following, loops + (following,), calls, waited)]
        elif op == 4:
            if not loops:
                raise ValueError(f"script 0x{start:X}: loop end without SetLoop at 0x{at:X}")
            target = loops[-1]
            if target <= at and not waited:
                unsafe[(at, target)] = {"jump": at, "target": target, "op": op}
            next_states = [(target, loops, calls, False),
                           (following, loops[:-1], calls, waited)]
        elif op == 5:
            target = memory.u32(at + 4)
            if len(calls) >= 8:
                raise ValueError(f"script 0x{start:X}: too many nested subroutines")
            next_states = [(target, loops, calls + (following,), waited)]
        elif op == 6:
            next_states = [(calls[-1], loops, calls[:-1], waited)] if calls else []
        elif op == 7:
            target = memory.u32(at + 4)
            if target <= at and not waited:
                unsafe[(at, target)] = {"jump": at, "target": target, "op": op}
            next_states = [(target, loops, calls, False if target <= at else waited)]
        else:
            waits = op == 8 or (op == 1 and (word & 0x3FFFFFF) > 0)
            next_states = [(following, loops, calls, waited or waits)]
        edges.setdefault(at, set()).update(n[0] for n in next_states)
        todo.extend(next_states)
    # A pointer can go to a lower address without making a loop: merge_vis
    # appends a prefix that jumps into the original script. Require a path
    # from the target back to the same jump before calling it a back edge.
    cyclic = [edge for edge in unsafe.values()
              if edge["jump"] in _loop_body(edges, edge["target"], edge["jump"])]
    return nodes, edges, sorted(cyclic, key=lambda x: (x["jump"], x["target"]))


def validate_script(memory, start):
    """Return reachable back edges that can be taken without a guaranteed wait."""
    return _inspect(memory, start)[2]


def _loop_body(edges, target, jump):
    """Nodes on any control-flow path from a loop target to its back edge."""
    reachable = {target}
    todo = [target]
    while todo:
        at = todo.pop()
        for successor in edges.get(at, ()):
            if successor not in reachable and not (at == jump and successor == target):
                reachable.add(successor)
                todo.append(successor)
    reverse = {}
    for at, successors in edges.items():
        for successor in successors:
            reverse.setdefault(successor, set()).add(at)
    to_jump = {jump}
    todo = [jump]
    while todo:
        at = todo.pop()
        for predecessor in reverse.get(at, ()):
            if predecessor not in to_jump:
                to_jump.add(predecessor)
                todo.append(predecessor)
    return reachable & to_jump


def rewrite_host_loop(memory, start, host_frames, new_frames):
    """Clone a row's reachable host script, scale loop syncs, and guard back edges.

    The original bytes stay intact because several motion rows can share scripts.
    Returns (new start, change summary); no clone is made for an already safe row.
    """
    nodes, edges, unsafe = _inspect(memory, start)
    if not unsafe:
        return start, {"scaled_syncs": [], "waits_inserted": 0}
    if host_frames <= 0 or new_frames <= 0:
        raise ValueError("looped host script needs positive host and port clip lengths")
    loop_nodes = set()
    for edge in unsafe:
        body = _loop_body(edges, edge["target"], edge["jump"])
        if edge["jump"] not in body:
            raise ValueError(f"no loop body for back edge at 0x{edge['jump']:X}")
        loop_nodes.update(body)
    guarded = {edge["jump"] for edge in unsafe}
    ordered = sorted(nodes)
    total_words = sum(length + (at in guarded) for at, (_, length) in nodes.items())
    base = memory.alloc(bytes(total_words * 4))
    mapping, cursor = {}, base
    for at in ordered:
        op, length = nodes[at]
        mapping[at] = cursor
        cursor += 4 * (length + (at in guarded))
    scaled = []
    for at in ordered:
        op, length = nodes[at]
        dest = mapping[at]
        if at in guarded:
            memory.put(dest, 0x20000000)
            dest += 4
        for i in range(length):
            word = memory.u32(at + 4 * i)
            if i == 0 and op == 2 and at in loop_nodes:
                old = word & 0x3FFFFFF
                new = round(old * new_frames / host_frames)
                if not 0 <= new <= 0x3FFFFFF:
                    raise ValueError(f"scaled sync frame {new} is out of range")
                word = (word & ~0x3FFFFFF) | new
                scaled.append((old, new))
            if i == 1 and op in (5, 7):
                word = mapping[word]
            if at + 4 * i in memory.relocs:
                memory.ptr(dest + 4 * i, word)
            else:
                memory.put(dest + 4 * i, word)
    rewritten = mapping[start]
    findings = validate_script(memory, rewritten)
    if findings:
        raise ValueError(f"rewritten host loop still has unwaited back edges: {findings}")
    return rewritten, {"scaled_syncs": scaled, "waits_inserted": len(guarded)}


def validate_geno_overlays(geno_path):
    """Check both inline and file-backed Geno subaction scripts in a profile."""
    path = Path(geno_path)
    profile = json.loads(path.read_text(encoding="utf-8"))
    findings = []
    for fighter in profile.get("fighters", []):
        for overlay in fighter.get("subactions", []):
            if "file" in overlay:
                source = path.parent / overlay["file"]
                content = re.sub(r"#.*", "", source.read_text(encoding="utf-8"))
                words = [int(token, 0) for token in content.split()]
            else:
                words = [int(word, 0) if isinstance(word, str) else word
                         for word in overlay.get("words", [])]
            # Geno appends End to every overlay in its script pool.
            packed = b"".join(struct.pack(">I", word) for word in words + [0])

            class View:
                data = packed

                @staticmethod
                def u32(offset):
                    return struct.unpack_from(">I", packed, offset)[0]

            try:
                row_findings = validate_script(View(), 0)
            except ValueError as exc:
                raise ValueError(f"Geno overlay row {overlay['index']}: {exc}") from exc
            findings.extend({"row": overlay["index"], **finding} for finding in row_findings)
    return findings
