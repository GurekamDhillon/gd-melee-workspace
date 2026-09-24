"""Read-only BRSAR reader: sound names, WAVE-type sound params (RWSD) and their DSP-ADPCM waves.

    import brsar; R = brsar.Brsar(path); s = R.sound_by_name("snd/se/metaknight/swing/l"); w = R.wave_sound(s)

Structures (NW4R snd, as Brawl ships them):
  RSAR  SYMB (names), INFO (sounds, files, groups), FILE (group blobs: RWSD files + their wave data)
  sound -> fileId + WaveSoundInfo.subNo (RWSD DATA index) -> track 0 / event 0 -> note -> waveIndex (RWSD WAVE entry)
  WAVE entry: format (2 = DSP-ADPCM), loop flag, channels, sample rate, loop start, end (nibbles),
  channel info (ADPCM coefs / gain / predictor state), data offset into the file's wave-data block.
Everything big-endian."""
import struct


def u16(b, o): return struct.unpack_from(">H", b, o)[0]
def u32(b, o): return struct.unpack_from(">I", b, o)[0]
def s32(b, o): return struct.unpack_from(">i", b, o)[0]
def f32(b, o): return struct.unpack_from(">f", b, o)[0]


class Brsar:
    def __init__(self, path):
        self.b = b = open(path, "rb").read()
        assert b[:4] == b"RSAR"
        self.symb, self.info, self.file = u32(b, 0x10), u32(b, 0x18), u32(b, 0x20)
        sb = self.symb + 8
        st = sb + u32(b, sb)
        n = u32(b, st)
        self.names = [self._cstr(sb + u32(b, st + 4 + 4 * i)) for i in range(n)]
        ib = self.info + 8

        def ref(o): return ib + u32(b, o + 4)
        snd = ref(ib + 0x00); fil = ref(ib + 0x18); grp = ref(ib + 0x20)
        self.sounds = []
        for i in range(u32(b, snd)):
            o = ref(snd + 4 + 8 * i)
            s = {"index": i, "string": u32(b, o), "file": u32(b, o + 4), "player": u32(b, o + 8),
                 "volume": b[o + 0x14], "prio": b[o + 0x15], "type": b[o + 0x16], "detail": ref(o + 0x18)}
            s["name"] = self.names[s["string"]] if s["string"] < len(self.names) else None
            self.sounds.append(s)
        self.files = []
        for i in range(u32(b, fil)):
            o = ref(fil + 4 + 8 * i)
            pl = []
            if u32(b, o + 0x18):
                pos = ref(o + 0x14)
                for k in range(u32(b, pos)):
                    q = ref(pos + 4 + 8 * k); pl.append((u32(b, q), u32(b, q + 4)))
            self.files.append({"size": u32(b, o), "wsize": u32(b, o + 4), "pos": pl})
        self.groups = []
        for i in range(u32(b, grp)):
            o = ref(grp + 4 + 8 * i)
            it = ref(o + 0x20); items = []
            for k in range(u32(b, it)):
                q = ref(it + 4 + 8 * k)
                items.append({"file": u32(b, q), "off": u32(b, q + 4), "size": u32(b, q + 8),
                              "woff": u32(b, q + 12), "wsize": u32(b, q + 16)})
            sid = u32(b, o)
            self.groups.append({"string": sid, "name": self.names[sid] if 0 <= sid < len(self.names) else None,
                                "off": u32(b, o + 0x10), "size": u32(b, o + 0x14),
                                "woff": u32(b, o + 0x18), "wsize": u32(b, o + 0x1C), "items": items})

    def _cstr(self, o):
        e = self.b.index(b"\0", o); return self.b[o:e].decode("latin1")

    def sound_by_name(self, n):
        return next(s for s in self.sounds if s["name"] == n)

    def file_blob(self, fid, group=None):
        """(rwsd offset, wave-data offset, group) of file fid, via its first (or the given) group."""
        for g, k in self.files[fid]["pos"]:
            if group is not None and g != group:
                continue
            G = self.groups[g]; it = G["items"][k]
            assert it["file"] == fid
            return G["off"] + it["off"], G["woff"] + it["woff"], g
        raise KeyError(fid)

    def wave_sound(self, s, group=None):
        b = self.b
        assert s["type"] == 3, (s["name"], s["type"])
        sub = s32(b, s["detail"])
        fo, wo, g = self.file_blob(s["file"], group)
        assert b[fo:fo + 4] == b"RWSD", b[fo:fo + 4]
        data = fo + u32(b, fo + 0x10); wave = fo + u32(b, fo + 0x18)
        db = data + 8

        def r(o): return db + u32(b, o + 4)
        ent = r(db + 4 + 8 * sub)
        wi = r(ent); tt = r(ent + 8); nt = r(ent + 16)
        info = {"pitch": f32(b, wi), "pan": b[wi + 4], "surround": b[wi + 5], "fxA": b[wi + 6], "fxB": b[wi + 7],
                "fxC": b[wi + 8], "main_send": b[wi + 9]}
        tr = r(tt + 4); ev_tbl = r(tr); ev = r(ev_tbl + 4)
        note_idx = u32(b, ev + 8)
        note = r(nt + 4 + 8 * note_idx)
        ni = {"wave": s32(b, note), "attack": b[note + 4], "decay": b[note + 5], "sustain": b[note + 6],
              "release": b[note + 7], "hold": b[note + 8], "key": b[note + 12], "volume": b[note + 13],
              "pan": b[note + 14], "surround": b[note + 15], "pitch": f32(b, note + 16)}
        w = self.wave_entry(wave, wo, ni["wave"])
        return {"name": s["name"], "index": s["index"], "group": g, "sound_volume": s["volume"], "prio": s["prio"],
                "sub": sub, "info": info, "note": ni, "tracks": u32(b, tt), "events": u32(b, ev_tbl),
                "notes": u32(b, nt), "wave": w}

    def wave_entry(self, wave, wdata, k):
        b = self.b
        assert b[wave:wave + 4] == b"WAVE"
        o = wave + u32(b, wave + 12 + 4 * k)
        fmt, loop, nch = b[o], b[o + 1], b[o + 2]
        rate = (b[o + 3] << 16) | u16(b, o + 4)
        loop_start, end = u32(b, o + 8), u32(b, o + 12)
        cit = o + u32(b, o + 16); dloc = u32(b, o + 20)
        chans = []
        for c in range(nch):
            ci = o + u32(b, cit + 4 * c)
            doff = u32(b, ci); ai = o + u32(b, ci + 4)
            coefs = list(struct.unpack_from(">16h", b, ai))
            gain, ps, yn1, yn2, lps, lyn1, lyn2 = struct.unpack_from(">7H", b, ai + 32)
            chans.append({"data": wdata + dloc + doff, "coefs": coefs, "gain": gain, "ps": ps, "yn1": yn1, "yn2": yn2,
                          "lps": lps, "lyn1": lyn1, "lyn2": lyn2})
        return {"format": fmt, "loop": loop, "channels": nch, "rate": rate, "loop_start": loop_start,
                "end": end, "chans": chans}


def decode_dsp(data, coefs, nsamples, hist=(0, 0)):
    """DSP-ADPCM bytes -> list of int16 (nsamples)."""
    out = []; h1, h2 = hist
    for fr in range(0, len(data), 8):
        ps = data[fr]; scale = 1 << (ps & 0xF); ci = (ps >> 4) & 7
        c1, c2 = coefs[2 * ci], coefs[2 * ci + 1]
        for i in range(14):
            if fr + 1 + i // 2 >= len(data):
                return out
            byte = data[fr + 1 + i // 2]
            nib = (byte >> 4) if i % 2 == 0 else (byte & 0xF)
            if nib >= 8:
                nib -= 16
            v = (((nib * scale) << 11) + c1 * h1 + c2 * h2 + 1024) >> 11
            v = max(-32768, min(32767, v))
            h2, h1 = h1, v; out.append(v)
            if len(out) >= nsamples:
                return out
    return out
