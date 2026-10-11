"""Bounded, Blender-free readers for Melee FigaTree banks and model rest joints.

HSD archive fields are big endian; compressed FObj numbers are little endian.
Interpolation follows sysdolphin/baselib/fobj.c, including SLP's two slope
registers and KEY's held values. No dependency on the animation exporter.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
import struct

CON, LIN, SPL0, SPL, SLP, KEY = range(1, 7)


class FigatreeError(ValueError):
    """An invalid or unsupported HSD input; safe to show in the file operator."""


def _unpack(fmt, data, offset):
    size = struct.calcsize(fmt)
    if offset < 0 or offset + size > len(data):
        raise FigatreeError(f"truncated HSD field at 0x{offset:x}")
    return struct.unpack_from(fmt, data, offset)


@dataclass(frozen=True)
class Key:
    op: int
    value: float | None
    slope: float | None
    wait: int | None


def decode_keys(body: bytes, fv: int, fs: int) -> tuple[Key, ...]:
    """Decode all six operations, five number formats and packed varints."""
    p = 0

    def byte():
        nonlocal p
        if p >= len(body):
            raise FigatreeError("truncated FObj key stream")
        value = body[p]
        p += 1
        return value

    def varint():
        value = 0
        for shift in range(0, 35, 7):
            b = byte()
            value |= (b & 127) << shift
            if not b & 128:
                return value
        raise FigatreeError("FObj varint exceeds 32 bits")

    def number(frac):
        nonlocal p
        kind, shift = frac >> 5, frac & 31
        if kind > 4 or (kind == 0 and shift):
            raise FigatreeError(f"unsupported FObj compression 0x{frac:02x}")
        fmt = ("<f", "<h", "<H", "<b", "<B")[kind]
        value = _unpack(fmt, body, p)[0]
        p += struct.calcsize(fmt)
        value = float(value) if kind == 0 else value / float(1 << shift)
        if not math.isfinite(value):
            raise FigatreeError("non-finite FObj value or slope")
        return value

    out = []
    while p < len(body):
        header = byte()
        op, count = header & 15, ((header >> 4) & 7) + 1
        if op not in range(CON, KEY + 1):
            raise FigatreeError(f"unsupported FObj opcode {op}")
        if header & 128:
            count += varint() << 3
        # Every key has at least a one-byte value/slope. Bound before looping.
        if count > len(body) - p:
            raise FigatreeError("FObj packet count exceeds its stream")
        for index in range(count):
            value = number(fv) if op != SLP else None
            slope = number(fs) if op in (SPL, SLP) else None
            wait = varint() if op != SLP and p < len(body) else None
            if wait is None and op != SLP and index + 1 < count:
                raise FigatreeError("missing wait inside FObj packet")
            out.append(Key(op, value, slope, wait))
    if not out:
        raise FigatreeError("empty FObj stream")
    return tuple(out)


@dataclass(frozen=True)
class Track:
    type: int
    start: int
    keys: tuple[Key, ...]
    fv: int = 0
    fs: int = 0

    def evaluate(self, frame: float, default: float = 0.0) -> float:
        """Evaluate at archive time (zero is the first imported move frame).

        FigaTrack stores u16 but HSD_FObj.startframe is s16. The engine ADDS
        that offset: negative offsets delay a track; positive offsets skip
        ahead. Before launch the caller's model rest value remains intact.
        The final interpolation interval continues at EOF, as in HSD (a
        shorter LIN/SPL track can extrapolate within a longer animation).
        """
        time = float(frame) + self.start
        if not math.isfinite(time):
            raise FigatreeError("sample frame must be finite")
        if time < 0:
            return default
        p0 = p1 = d0 = d1 = 0.0
        op = intrp = 0
        term = consumed_term = 0
        state, cursor = 1, 0
        held = default
        pending_key = False
        launched = wait_loaded = False
        wait = None

        def launch():
            nonlocal intrp, pending_key, launched, p0
            if pending_key:
                intrp = op
                pending_key = False
                launched = True
                p0 = p1

        def update():
            nonlocal launched, wait_loaded, d0, p0
            if intrp == KEY:
                if launched:
                    launched = False
                    return p0
                return held
            if intrp == CON:
                return p1 if time >= term else p0
            if intrp == LIN:
                if wait_loaded:
                    wait_loaded = False
                    d0 = (p1-p0)/term if term else 0.
                    if not term:
                        p0 = p1
                return d0*time + p0
            if intrp in (SPL0, SPL, SLP):
                if not term:
                    return p1
                u = time/term
                return ((2*u**3 - 3*u**2 + 1)*p0 + (-2*u**3 + 3*u**2)*p1
                        + (u**3 - 2*u**2 + u)*term*d0 + (u**3 - u**2)*term*d1)
            # A single non-KEY value never establishes op_intrp in HSD and
            # writes undefined memory. Give that otherwise invalid constant
            # encoding a deterministic value (the reader/exporter use it).
            return p1 if len(self.keys) == 1 and op != SLP else held

        while True:
            if state == 6:
                time += consumed_term
                launch()
                return update()
            if state in (1, 2):
                if cursor == len(self.keys):
                    state = 6
                    continue
                key = self.keys[cursor]
                cursor += 1
                intrp, op = op, key.op
                if op == SLP:
                    d0, d1 = d1, key.slope
                    continue
                if op == KEY:
                    launch()
                    p1 = key.value
                    pending_key = True
                else:
                    p0, p1 = p1, key.value
                    if op not in (CON, LIN) or intrp != SLP:
                        d0, d1 = d1, key.slope if op == SPL else 0.
                wait = key.wait
                state = 3 if state == 1 else 4
            elif state == 3:
                if launched:
                    held = update()
                if wait is None:
                    state = 6
                else:
                    term = wait
                    wait_loaded = True
                    state = 2
            elif state == 4:
                if term <= time:
                    consumed_term = term
                    time -= term
                    state = 3
                else:
                    return update()

    def key_times(self) -> tuple[float, ...]:
        """Value-key boundaries in archive time, including delayed launch."""
        clock = -self.start
        out = []
        for key in self.keys:
            if key.op != SLP:
                out.append(float(clock))
                clock += key.wait or 0
        return tuple(out)


@dataclass(frozen=True)
class Animation:
    name: str
    symbol: str
    frames: float
    joints: tuple[tuple[Track, ...], ...]
    flags: int = 0


class _Archive:
    def __init__(self, raw):
        size, dsz, nrel, npub, next_ = _unpack(">5I", raw, 0)
        strings = 32 + dsz + nrel * 4 + (npub + next_) * 8
        if size != len(raw) or size < 32 or strings > size:
            raise FigatreeError("invalid HSD archive size or table bounds")
        self.data = raw[32:32 + dsz]
        self.relocs = set()
        for i in range(nrel):
            off = _unpack(">I", raw, 32 + dsz + i * 4)[0]
            target = _unpack(">I", self.data, off)[0]
            if target >= dsz:
                raise FigatreeError("HSD relocation target is outside data")
            self.relocs.add(off)
        self.publics = []
        po = 32 + dsz + nrel * 4
        for i in range(npub):
            off, so = _unpack(">II", raw, po + i * 8)
            if off >= dsz or strings + so >= size:
                raise FigatreeError("HSD public entry is outside archive")
            end = raw.find(b"\0", strings + so)
            if end < 0:
                raise FigatreeError("unterminated HSD public name")
            try:
                name = raw[strings + so:end].decode("utf-8")
            except UnicodeDecodeError as exc:
                raise FigatreeError("invalid HSD public name") from exc
            self.publics.append((name, off))

    def pointer(self, field):
        target = _unpack(">I", self.data, field)[0]
        if field in self.relocs:
            return target  # relocated zero is a valid data address
        if target:
            raise FigatreeError(f"unrelocated HSD pointer at 0x{field:x}")
        return None


def _animations(raw):
    archive = _Archive(raw)
    out = []
    for symbol, off in archive.publics:
        typ, flags, frames, _, _ = _unpack(">IIfII", archive.data, off)
        if typ != 1:
            raise FigatreeError(f"{symbol}: expected a type-1 FigaTree")
        if not math.isfinite(frames) or frames < 0:
            raise FigatreeError(f"{symbol}: invalid frame duration")
        nodes, tracks = archive.pointer(off + 12), archive.pointer(off + 16)
        if nodes is None:
            raise FigatreeError(f"{symbol}: missing FigaTree node counts")
        joints, ti = [], 0
        while True:
            count = _unpack(">B", archive.data, nodes)[0]
            nodes += 1
            if count == 255:
                break
            if count > 127:
                raise FigatreeError(f"{symbol}: negative joint track count")
            joint, types = [], set()
            for _ in range(count):
                if tracks is None:
                    raise FigatreeError(f"{symbol}: missing FigaTree tracks")
                e = tracks + ti * 12
                ti += 1
                length, start, ty, fv, fs, _ = _unpack(">HhBBBxI", archive.data, e)
                ad = archive.pointer(e + 8)
                if ad is None or ad + length > len(archive.data):
                    raise FigatreeError(f"{symbol}: track stream is outside data")
                if ty in types:
                    raise FigatreeError(f"{symbol}: duplicate joint channel {ty}")
                types.add(ty)
                joint.append(Track(ty, start, decode_keys(archive.data[ad:ad + length], fv, fs), fv, fs))
            joints.append(tuple(joint))
        name = re.sub(r"_figatree$", "", symbol.split("ACTION_", 1)[-1])
        out.append(Animation(name, symbol, frames, tuple(joints), flags))
    if not out:
        raise FigatreeError("archive contains no public FigaTree")
    return out


def read_bank(raw: bytes, bank_info: dict | None = None) -> list[Animation]:
    """Read a standalone DAT or 32-byte-aligned AJ bank.

    Optional plan['bank'] restricts selection to its offset/bytes entries and
    retains the plan's clip names, including renamed clips appended by hand_apply.
    """
    if bank_info is not None:
        out = []
        for name, entry in bank_info.get("clips", {}).items():
            off, size = entry["offset"], entry["bytes"]
            if not isinstance(off, int) or not isinstance(size, int) or off < 0 or size < 32 or off + size > len(raw):
                raise FigatreeError(f"{name}: invalid bank slice")
            clips = _animations(raw[off:off + size])
            if len(clips) != 1:
                raise FigatreeError(f"{name}: bank slice must contain one animation")
            clip = clips[0]
            out.append(Animation(name, clip.symbol, clip.frames, clip.joints, clip.flags))
    else:
        out, off = [], 0
        while off < len(raw):
            remainder = raw[off:]
            if not remainder.strip(b"\0") or not remainder.strip(b"\xff"):
                break
            size = _unpack(">I", raw, off)[0]
            if size < 32 or off + size > len(raw):
                raise FigatreeError(f"invalid AJ archive at 0x{off:x}")
            out.extend(_animations(raw[off:off + size]))
            end = off + size
            off = (end + 31) & ~31
            if any(raw[end:min(off, len(raw))]):
                raise FigatreeError("nonzero AJ alignment padding")
    if not out:
        raise FigatreeError("bank contains no animations")
    return out


@dataclass(frozen=True)
class RestJoint:
    parent: int | None
    rotation: tuple[float, float, float]
    translation: tuple[float, float, float]
    scale: tuple[float, float, float]
    flags: int = 8


def read_model(raw: bytes, symbol: str = "") -> tuple[RestJoint, ...]:
    """Read the matching costume's JOBJ rest SRT and depth-first hierarchy."""
    archive = _Archive(raw)
    roots = [(name, off) for name, off in archive.publics if name == symbol] if symbol else [
        (name, off) for name, off in archive.publics if name.endswith("_joint")]
    if len(roots) != 1:
        raise FigatreeError("choose a model DAT with one public _joint root (or supply its symbol)")
    out, seen = [], set()
    todo = [(roots[0][1], None)]
    while todo:
        off, parent = todo.pop()
        if off in seen:
            raise FigatreeError("cycle or shared instance in model joint tree")
        seen.add(off)
        flags = _unpack(">I", archive.data, off + 4)[0]
        rot, scale, trans = (_unpack(">3f", archive.data, off + delta) for delta in (20, 32, 44))
        if not all(math.isfinite(value) for vec in (rot, scale, trans) for value in vec):
            raise FigatreeError("non-finite model rest SRT")
        index = len(out)
        out.append(RestJoint(parent, rot, trans, scale, flags))
        child, sibling = archive.pointer(off + 8), archive.pointer(off + 12)
        if sibling is not None:
            todo.append((sibling, parent))
        if child is not None and not flags & (1 << 12):
            todo.append((child, index))
    return tuple(out)
