"""Internal directory references keep chunk model paths on one canonical pool."""
import os
from pathlib import Path
import struct


def model_reference(link, target):
    """Relative directory symlink where available; privilege-free NTFS junction otherwise.

    Junctions bind the final published path, never the staging directory. They
    must be recreated by export after relocating a mission on Windows.
    """
    link, target = Path(link), Path(target).absolute()
    link.parent.mkdir(parents=True, exist_ok=True)
    # Published link is <mission>/chunks/<id>/models -> <mission>/models.
    # Relative references survive a moved/renamed mission where symlinks work.
    try:
        os.symlink(os.path.join('..', '..', 'models'), link, target_is_directory=True)
        return
    except OSError:
        if os.name != 'nt': raise
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    device = kernel.DeviceIoControl
    device.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                       ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    device.restype = wintypes.BOOL
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]; close.restype = wintypes.BOOL
    # MOUNT_POINT_REPARSE_BUFFER: substitute name and print name, UTF-16.
    printable = str(target)
    substitute = '\\??\\' + printable
    sub = substitute.encode('utf-16-le'); printed = printable.encode('utf-16-le')
    names = sub + b'\0\0' + printed + b'\0\0'
    data = struct.pack('<IHHHHHH', 0xA0000003, 8+len(names), 0, 0, len(sub), len(sub)+2, len(printed)) + names
    link.mkdir()
    handle = create(str(link), 0x40000000, 0, None, 3, 0x00200000 | 0x02000000, None)
    if handle == ctypes.c_void_p(-1).value:
        code = ctypes.get_last_error(); link.rmdir(); raise ctypes.WinError(code)
    try:
        buffer = ctypes.create_string_buffer(data)
        got = wintypes.DWORD()
        if not device(handle, 0x000900A4, buffer, len(data), None, 0, ctypes.byref(got), None):
            raise ctypes.WinError(ctypes.get_last_error())
    except OSError:
        close(handle); handle = None; link.rmdir(); raise
    finally:
        if handle is not None: close(handle)
