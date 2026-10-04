"""Remove build-user roots from deployed copies; optionally unsign modified Qt DLLs."""
import argparse
from pathlib import Path
import re
import struct

USER_ROOT = re.compile(r'[A-Z]:[\\/]Users[\\/](?!Public[\\/]|Default[\\/])[A-Za-z0-9._ -]{2,}[\\/]', re.I)


def sanitize_image(data, *, strip_signature=False):
    if len(data) < 64 or data[:2] != b'MZ':
        raise ValueError('not a PE image')
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    optional = pe + 24
    if optional + 152 > len(data) or data[pe:pe+4] != b'PE\0\0':
        raise ValueError('truncated PE image')
    magic = struct.unpack_from('<H', data, optional)[0]
    if magic not in (0x10b, 0x20b):
        raise ValueError('invalid PE optional header')
    certificate = optional + (112 if magic == 0x20b else 96) + 4*8
    certificate_start, certificate_size = struct.unpack_from('<II', data, certificate)
    signed = bool(certificate_start or certificate_size)
    result = bytearray(data)
    count = 0
    # Diagnostic strings can be ANSI or UTF-16LE. Inspect both alignments;
    # matching spans are replaced in place, preserving all offsets and lengths.
    spans = [(m.start(), m.end(), 1) for m in USER_ROOT.finditer(data.decode('latin1'))]
    for alignment in (0, 1):
        size = (len(data)-alignment)//2*2
        wide = data[alignment:alignment+size].decode('utf-16le', errors='surrogatepass')
        spans += [(alignment+m.start()*2, alignment+m.end()*2, 2) for m in USER_ROOT.finditer(wide)]
    if spans and signed:
        if not strip_signature:
            raise ValueError('refusing to redact a signed PE image; use a reproducible clean build')
        if not certificate_start or not certificate_size or certificate_start+certificate_size > len(data):
            raise ValueError('invalid signed PE certificate table')
        # This explicitly produces an unsigned deployed copy, rather than
        # presenting a modified image with a broken vendor Authenticode claim.
        # Certificate data is file-only; zeroing it preserves image offsets.
        result[certificate:certificate+8] = bytes(8)
        result[certificate_start:certificate_start+certificate_size] = bytes(certificate_size)
    for start, end, width in spans:
        root = '%BUILDROOT%/'.ljust((end-start)//width, '/')
        replacement = root.encode('ascii' if width == 1 else 'utf-16le')
        result[start:end] = replacement
        count += 1
    if count:
        result[optional+64:optional+68] = bytes(4)  # no stale PE checksum after modification
    return bytes(result), count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+', type=Path)
    parser.add_argument('--strip-qt-signatures', action='store_true',
                        help='make diagnostic-redacted Qt DLL copies explicitly unsigned')
    args = parser.parse_args()
    count = 0
    for path in args.paths:
        images = sorted(p for p in path.rglob('*') if p.suffix.lower() in ('.exe', '.dll')) if path.is_dir() else [path]
        for image in images:
            qt_copy = image.name.startswith('Qt6') or (image.name.startswith('q') and image.suffix.lower() == '.dll')
            data, changed = sanitize_image(image.read_bytes(), strip_signature=args.strip_qt_signatures and qt_copy)
            if changed:
                image.write_bytes(data)
                count += changed
    print(f'launcher diagnostic roots redacted: {count}')


if __name__ == '__main__':
    main()
