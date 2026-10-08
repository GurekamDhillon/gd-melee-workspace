"""Convert PCM WAV files into the .gnsnd container (format version 1).

A .gnsnd file is a 32-byte header of big-endian u32 fields followed by signed
16-bit big-endian interleaved samples at 32000 Hz (at most 10 seconds).
Standard library only.

    python -m tools.geno.audio IN.wav OUT.gnsnd
"""

from __future__ import annotations

import argparse
import array
import os
import struct
import sys
import wave

MAGIC = b"GNSD"
VERSION = 1
RATE = 32000
MAX_FRAMES = 320000
HEADER_SIZE = 32

# version, sample_rate, channels, frames, data_offset, data_bytes, reserved
_HEADER = struct.Struct(">7I")


def _read_pcm(src_path):
    """Return (channels, width, rate, frames, raw_bytes) for an uncompressed PCM WAV."""
    try:
        wf = wave.open(os.fspath(src_path), "rb")
    except (wave.Error, EOFError) as exc:
        raise ValueError(f"not an uncompressed PCM WAV file: {exc}") from exc
    with wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    if channels not in (1, 2):
        raise ValueError(f"only mono or stereo is accepted; file has {channels} channels")
    if width not in (1, 2, 3, 4):
        raise ValueError(f"unsupported sample width of {width} bytes; PCM must be 8, 16, 24 or 32 bit")
    if rate <= 0:
        raise ValueError(f"invalid sample rate {rate}")
    frame_bytes = channels * width
    frames = len(raw) // frame_bytes
    if frames == 0:
        raise ValueError("WAV file contains no audio frames")
    return channels, width, rate, frames, raw[: frames * frame_bytes]


def _decode(raw, width):
    """Decode little-endian integer PCM to a list of signed 16-bit ints (interleaved)."""
    if width == 1:
        return [(b - 128) << 8 for b in raw]
    if width == 2:
        return list(struct.unpack("<%dh" % (len(raw) // 2), raw))
    if width == 3:
        return [int.from_bytes(raw[i:i + 3], "little", signed=True) >> 8
                for i in range(0, len(raw), 3)]
    return [int.from_bytes(raw[i:i + 4], "little", signed=True) >> 16
            for i in range(0, len(raw), 4)]


def _resample(chan, out_n):
    """Linear-interpolate one channel to out_n frames, mapping first and last frames onto each other."""
    last = len(chan) - 1
    step = last / (out_n - 1) if out_n > 1 else 0.0
    out = []
    for j in range(out_n):
        pos = j * step
        i0 = int(pos)
        if i0 >= last:
            out.append(chan[last])
            continue
        a = chan[i0]
        b = chan[i0 + 1]
        out.append(round(a + (b - a) * (pos - i0)))
    return out


def convert_wav(src_path, dst_path) -> dict:
    """Convert a PCM WAV to a .gnsnd file at dst_path and return its summary."""
    dst = os.fspath(dst_path)
    if not dst.endswith(".gnsnd"):
        raise ValueError(f"output must end in .gnsnd (got {dst!r}); refusing to overwrite other files")

    channels, width, src_rate, frames, raw = _read_pcm(src_path)
    if src_rate == RATE:
        out_n = frames
    else:
        out_n = max(1, round(frames * RATE / src_rate))
    if out_n > MAX_FRAMES:
        raise ValueError(
            f"clip would be {out_n} frames at {RATE} Hz, longer than 10 seconds "
            f"(maximum {MAX_FRAMES} frames)")

    values = _decode(raw, width)
    out = [0] * (out_n * channels)
    for ch in range(channels):
        chan = values[ch::channels]
        if src_rate != RATE:
            chan = _resample(chan, out_n)
        out[ch::channels] = chan

    data = array.array("h", out)
    if sys.byteorder == "little":
        data.byteswap()
    data_bytes = data.tobytes()

    header = MAGIC + _HEADER.pack(VERSION, RATE, channels, out_n, HEADER_SIZE, len(data_bytes), 0)
    with open(dst, "wb") as fh:
        fh.write(header)
        fh.write(data_bytes)

    return {
        "frames": out_n,
        "channels": channels,
        "seconds": out_n / RATE,
        "source_rate": src_rate,
    }


def parse(blob: bytes) -> dict:
    """Validate a .gnsnd blob and return rate, channels, frames and interleaved samples."""
    blob = bytes(blob)
    if len(blob) < HEADER_SIZE:
        raise ValueError(f"file is {len(blob)} bytes, shorter than the {HEADER_SIZE}-byte header")
    if blob[:4] != MAGIC:
        raise ValueError(f"bad magic {blob[:4]!r}, expected {MAGIC!r}")
    version, rate, channels, frames, data_offset, data_bytes, reserved = _HEADER.unpack(
        blob[4:HEADER_SIZE])
    if version != VERSION:
        raise ValueError(f"unsupported version {version}, expected {VERSION}")
    if rate != RATE:
        raise ValueError(f"sample rate {rate}, expected {RATE}")
    if channels not in (1, 2):
        raise ValueError(f"channels {channels}, expected 1 or 2")
    if not 1 <= frames <= MAX_FRAMES:
        raise ValueError(f"frames {frames} outside 1..{MAX_FRAMES}")
    if data_offset != HEADER_SIZE:
        raise ValueError(f"data_offset {data_offset}, expected {HEADER_SIZE}")
    if data_bytes != frames * channels * 2:
        raise ValueError(
            f"data_bytes {data_bytes}, expected {frames * channels * 2} (frames * channels * 2)")
    if reserved != 0:
        raise ValueError(f"reserved field is {reserved}, expected 0")
    expected = HEADER_SIZE + data_bytes
    if len(blob) < expected:
        raise ValueError(f"truncated: file is {len(blob)} bytes, header requires {expected}")
    if len(blob) > expected:
        raise ValueError(f"trailing bytes: file is {len(blob)} bytes, header requires {expected}")
    samples = list(struct.unpack(">%dh" % (frames * channels), blob[HEADER_SIZE:]))
    return {"rate": rate, "channels": channels, "frames": frames, "samples": samples}


def check_file(path) -> list[str]:
    """Return a list of problems with the .gnsnd file at path (empty when valid)."""
    try:
        with open(os.fspath(path), "rb") as fh:
            blob = fh.read()
    except OSError as exc:
        return [f"cannot read {path}: {exc}"]
    try:
        parse(blob)
    except ValueError as exc:
        return [str(exc)]
    return []


def write_tone(dst_path, hz=660.0, ms=400, volume=0.5) -> dict:
    """Write an original test clip: a sine tone with a short fade in and out (a placeholder call for a fighter that has no recorded one yet)."""
    import math
    dst = os.fspath(dst_path)
    if not dst.endswith(".gnsnd"):
        raise ValueError(f"output must end in .gnsnd (got {dst!r})")
    frames = max(1, int(RATE * ms / 1000))
    if frames > MAX_FRAMES:
        raise ValueError("a tone longer than 10 seconds")
    fade = max(1, min(frames // 2, RATE // 100))
    out = []
    for i in range(frames):
        env = min(1.0, i / fade, (frames - 1 - i) / fade)
        out.append(int(round(32767 * volume * env * math.sin(2 * math.pi * hz * i / RATE))))
    data = array.array("h", out)
    if sys.byteorder == "little":
        data.byteswap()
    body = data.tobytes()
    with open(dst, "wb") as fh:
        fh.write(MAGIC + _HEADER.pack(VERSION, RATE, 1, frames, HEADER_SIZE, len(body), 0))
        fh.write(body)
    return {"frames": frames, "channels": 1, "seconds": frames / RATE, "source_rate": RATE}


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "--tone":
        tone = argparse.ArgumentParser(prog="python -m tools.geno.audio --tone", description="Write a sine-tone test clip.")
        tone.add_argument("dst")
        tone.add_argument("--hz", type=float, default=660.0)
        tone.add_argument("--ms", type=int, default=400)
        tone.add_argument("--volume", type=float, default=0.5)
        a = tone.parse_args(argv[1:])
        try:
            info = write_tone(a.dst, a.hz, a.ms, a.volume)
        except (ValueError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"{a.dst}: {info['frames']} frames, 1 channel(s), {info['seconds']:.2f} s (tone {a.hz:g} Hz)")
        return 0
    parser = argparse.ArgumentParser(
        prog="python -m tools.geno.audio",
        description="Convert a PCM WAV file to a .gnsnd v1 clip (32000 Hz, mono or stereo, <= 10 s).")
    parser.add_argument("src", help="input PCM WAV file")
    parser.add_argument("dst", help="output .gnsnd file")
    args = parser.parse_args(argv)
    try:
        info = convert_wav(args.src, args.dst)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"{args.dst}: {info['frames']} frames, {info['channels']} channel(s), "
          f"{info['seconds']:.2f} s (from {info['source_rate']} Hz)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
