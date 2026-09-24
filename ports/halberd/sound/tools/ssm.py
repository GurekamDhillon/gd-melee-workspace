"""Melee .ssm sound banks and smash2.sem sound scripts: read and write.

.ssm (big-endian):  u32 header_size, u32 data_size (the ARAM the bank takes), u32 sample_count, u32 first_sample_id,
  then per sample: u32 channel_count, u32 sample_rate, per channel a 0x40-byte DSP voice block:
    u16 loop_flag, u16 format (0 = DSP-ADPCM), u32 loop_addr, u32 end_addr, u32 cur_addr   (nibble addresses from the
    start of the data region; cur = the first frame header's nibble + 2), s16 coefs[16], u16 gain, u16 pred_scale,
    s16 yn1, s16 yn2, u16 loop_pred_scale, s16 loop_yn1, s16 loop_yn2, u16 pad
  header_size counts from 0x10 to the end of the sample table (synth.c reads it that way); the data region starts at
  file offset 0x10 + header_size rounded up to 0x20; data_size is its length.
smash2.sem: five {u32 n, u32[n]} tables. Only two are non-empty on every disc seen: bank_start[bank] (index of a
  bank's first script) and script[] (file offsets of the script word streams, relocated at load). A sound id is
  bank * 10000 + k -> script[bank_start[bank] + k]. Script words: top byte = command (axdriver.c AXDriverInterp):
  01 sample id (global) - 04 priority - 06 volume (0..255) - 08 pan - 0C pitch (s16 cents) - 10 aux send A -
  0E end. Command waits: 06/08/10.. carry a 16-bit wait in bits 8..23, 0C an 8-bit wait in bits 16..23."""
import struct


def read_ssm(b):
    hs, ds, n, base = struct.unpack_from(">4I", b, 0)
    p = 0x10; smp = []
    for i in range(n):
        nch, rate = struct.unpack_from(">2I", b, p)
        chs = []
        for c in range(nch):
            q = p + 8 + c * 0x40
            loop, fmt, la, ea, ca = struct.unpack_from(">2H3I", b, q)
            coefs = list(struct.unpack_from(">16h", b, q + 16))
            gain, ps, yn1, yn2, lps, lyn1, lyn2 = struct.unpack_from(">H H h h H h h", b, q + 48)
            chs.append(dict(loop=loop, fmt=fmt, loop_addr=la, end_addr=ea, cur_addr=ca, coefs=coefs, gain=gain, ps=ps,
                            yn1=yn1, yn2=yn2, lps=lps, lyn1=lyn1, lyn2=lyn2))
        smp.append(dict(rate=rate, chans=chs))
        p += 8 + nch * 0x40
    data_start = (0x10 + hs + 0x1F) & ~0x1F
    return dict(header_size=hs, data_size=ds, base=base, samples=smp, data_start=data_start,
                data=b[data_start:data_start + ds], table_end=p)


def write_ssm(samples, base):
    """samples: [{rate, loop, loop_start_nibble (relative to the sample's first frame, i.e. >= 2), end_nibble (relative),
    adpcm bytes, coefs, gain, ps, yn1, yn2, lps, lyn1, lyn2}] (mono). Each sample's data starts 8-byte aligned (a frame)."""
    data = bytearray(); tbl = bytearray()
    for s in samples:
        while len(data) % 0x20: data.append(0)          # 32-byte aligned per sample (ARAM DMA granularity)
        start_nib = len(data) * 2
        data += s["adpcm"]
        cur = start_nib + 2
        end = start_nib + s["end_nibble"]
        la = start_nib + s["loop_start_nibble"] if s["loop"] else cur
        tbl += struct.pack(">2I", 1, s["rate"])
        tbl += struct.pack(">2H3I", 1 if s["loop"] else 0, 0, la, end, cur)
        tbl += struct.pack(">16h", *s["coefs"])
        tbl += struct.pack(">H H h h H h h H", s["gain"], s["ps"], s["yn1"], s["yn2"], s["lps"], s["lyn1"], s["lyn2"], 0)
    while len(data) % 0x20: data.append(0)
    hs = len(tbl)
    head = struct.pack(">4I", hs, len(data), len(samples), base) + bytes(tbl)
    while len(head) % 0x20: head += b"\0"
    return head + bytes(data)


def read_sem(b):
    o = 0; T = []
    for k in range(5):
        n = struct.unpack_from(">I", b, o)[0]; o += 4
        T.append(list(struct.unpack_from(">%dI" % n, b, o))); o += 4 * n
    return T, o


def sem_script(b, off):
    out = []; o = off
    while True:
        w = struct.unpack_from(">I", b, o)[0]; out.append(w); o += 4
        if w >> 24 in (0x0E, 0x0F) or len(out) > 256:
            return out


def write_sem(old, new_bank_scripts, bank_index):
    """Append (or replace) bank `bank_index` = new_bank_scripts ([[words]]) to smash2.sem bytes `old`.
    Every other bank's scripts are carried over byte for byte."""
    T, end = read_sem(old)
    starts, offs = T[2], T[3]
    assert not T[0] and not T[1] and not T[4], "sem tables A/B/E are not empty: layout not handled"
    nb = len(starts)
    scripts = [sem_script(old, x) for x in offs]
    if bank_index < nb:                                  # replace: drop the old bank's scripts
        lo = starts[bank_index]; hi = starts[bank_index + 1] if bank_index + 1 < nb else len(scripts)
        scripts = scripts[:lo] + scripts[hi:]
        starts = starts[:bank_index] + starts[bank_index + 1:]
        starts = [s - (hi - lo) if i >= bank_index else s for i, s in enumerate(starts)]
        nb -= 1
    assert bank_index == nb, "new bank must be the next index (%d), got %d" % (nb, bank_index)
    starts = starts + [len(scripts)]
    scripts = scripts + [list(s) for s in new_bank_scripts]
    head_len = 4 * 5 + 4 * len(starts) + 4 * len(scripts)
    body = bytearray(); ptrs = []
    for s in scripts:
        ptrs.append(head_len + len(body)); body += b"".join(struct.pack(">I", w) for w in s)
    out = struct.pack(">I", 0) + struct.pack(">I", 0) + struct.pack(">I", len(starts)) + b"".join(struct.pack(">I", x) for x in starts) \
        + struct.pack(">I", len(ptrs)) + b"".join(struct.pack(">I", x) for x in ptrs) + struct.pack(">I", 0) + bytes(body)
    return out
