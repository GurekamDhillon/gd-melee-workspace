#!/usr/bin/env python3
"""Package a verified Linux build; reject a nonportable glibc dependency unless --local is explicit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
root=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--build',type=Path,default=root/'_build/agents/linux')
ap.add_argument('--output',type=Path,default=root/'_build/linux/packages')
ap.add_argument('--local',action='store_true')
ap.add_argument('--version',help='Release version for version.txt (default: tools/release/VERSION)')
ap.add_argument('--melee',type=Path,default=Path(os.environ['GW_MELEE']) if os.environ.get('GW_MELEE') else root/'melee',help='Game checkout the executable was built from (for version.txt)')
ap.add_argument('--launcher',type=Path,help='Deployed Qt prefix containing bin/gd-melee-launcher and its runtime')
ap.add_argument('--runtime-lib-dir',type=Path,action='append',default=[],help='Additional directory for 32-bit SDL Wayland runtime libraries')
a=ap.parse_args(); build=a.build.resolve(); a.output.mkdir(parents=True,exist_ok=True)
readelf=os.environ.get('GW_READELF') or shutil.which('llvm-readelf-22') or 'readelf'
exe=build/'melee'
subprocess.run(['python3',str(root/'tools/mex_port/audit_bridge_abi.py'),'--map',str(build/'melee-pc.msvc.map'),'--exe',str(exe),'--bridge',str(build/'bridge/gw_mex_bridge.c')],check=True)
versions=subprocess.check_output([readelf,'--version-info',str(exe)],text=True)
required=max((tuple(map(int,v.split('.'))) for v in re.findall(r'GLIBC_([0-9.]+)',versions)),default=(0,))
if required>(2,35) and not a.local: raise SystemExit(f'GLIBC {required} exceeds portable baseline 2.35; rebuild on Ubuntu 22.04')
def git(repo,*args):
    try:return subprocess.check_output(['git','-C',str(repo),*args],text=True,stderr=subprocess.DEVNULL).strip()
    except (OSError,subprocess.CalledProcessError):return ''
def version_text():
    # Same shape as the Windows release's version.txt (tools/release/build_release.ps1). The game's crash
    # report reads line 1 of <exe dir>/version.txt; the launcher reads <package>/version.txt.
    version=(a.version or (root/'tools/release/VERSION').read_text()).strip()
    if not re.fullmatch(r'[0-9A-Za-z][0-9A-Za-z.+-]*',version):raise SystemExit(f'bad release version {version!r}')
    melee=git(a.melee,'rev-parse','HEAD') or 'unknown'; ws=git(root,'rev-parse','--short=9','HEAD') or 'unknown'
    header=a.melee/'pc/platform/gw_net.h'
    proto=re.search(r'(?m)^\s*#define\s+GW_NET_PROTOCOL_VERSION\s+(\d+)u?\s*$',header.read_text()) if header.is_file() else None
    lines=[f'{version} (melee {melee[:9]})' + (' local' if a.local else ''),
           f'melee      {melee}  https://github.com/GurekamDhillon/melee/tree/{melee}',
           f'workspace  {ws}  https://github.com/GurekamDhillon/gd-melee-workspace',
           'built      '+__import__('datetime').date.today().isoformat()]
    if proto:lines.append('netplay_protocol '+proto[1])
    return chr(10).join(lines)+chr(10)
name='melee-linux-i686'+('-local' if a.local else '')
with tempfile.TemporaryDirectory(prefix='package-',dir=a.output) as temp:
    temp=Path(temp); dest=temp/name; debug=temp/(name+'-debug')
    for d in (dest/'bin',dest/'lib',dest/'assets',dest/'licenses',dest/'udev',debug):d.mkdir(parents=True,exist_ok=True)
    shutil.copy2(exe,dest/'bin/melee')
    subprocess.run(['objcopy','--only-keep-debug',str(exe),str(debug/'melee.debug')],check=True)
    subprocess.run(['strip','--strip-debug',str(dest/'bin/melee')],check=True)
    subprocess.run(['objcopy','--add-gnu-debuglink='+str(debug/'melee.debug'),str(dest/'bin/melee')],check=True)
    shutil.copy2(build/'melee-pc.msvc.map',dest/'bin/melee-pc.msvc.map')
    # The game looks for version.txt beside its executable (gw_log.c, gl_exe_dir), which is bin/ here.
    # The launcher looks beside itself, at the package root. Same text in both.
    text=version_text(); (dest/'version.txt').write_text(text); (dest/'bin/version.txt').write_text(text)
    shutil.copytree(build/'assets/fonts',dest/'assets/fonts')
    shutil.copytree(build/'ui',dest/'assets/ui')
    for f in ('launch-melee','README.txt','GD-Melee'):shutil.copy2(root/'tools/port/release'/f,dest/f)
    (dest/'launch-melee').chmod(0o755)
    (dest/'GD-Melee').chmod(0o755)
    # For players who cannot get past 'the game will not start': POSIX sh, writes one report to attach.
    shutil.copy2(root/'tools/release/linux/gd-melee-diagnose.sh',dest/'gd-melee-diagnose.sh')
    (dest/'gd-melee-diagnose.sh').chmod(0o755)
    launcher=a.launcher or root/'_build/launcher-package/launcher'
    if not (launcher/'bin/gd-melee-launcher').is_file():raise SystemExit('Build/deploy the Qt launcher first with tools/release/build_launcher.sh _build/launcher-package')
    shutil.copytree(launcher,dest/'launcher',symlinks=True)
    probe=launcher/'bin/melee-graphics-probe'
    if not probe.is_file():raise SystemExit('Rebuild the launcher: its 32-bit graphics helper is missing')
    if probe.read_bytes()[:5]!=b'\x7fELF\x01':raise SystemExit('Graphics helper must be a 32-bit ELF executable')
    shutil.copy2(probe,dest/'bin/melee-graphics-probe')
    shutil.copytree(root/'tools/port/udev',dest/'udev',dirs_exist_ok=True)
    shutil.copytree(root/'tools/release/licenses',dest/'licenses',dirs_exist_ok=True)
    shutil.copy2(root/'tools/release/THIRD-PARTY-NOTICES.txt',dest/'licenses/')
    shutil.copy2(root/'_build/linux/libusb-src/COPYING',dest/'licenses/libusb-LGPL-2.1.txt')
    shutil.copy2(root/'docs/LINUX_PORT_STATUS.md',dest/'IMPLEMENTATION_STATUS.md')
    # ldd lists the transitive dependencies of this trusted, locally built executable.
    # libstdc++ and libgcc_s are never bundled: lib/ is first on LD_LIBRARY_PATH, so a bundled copy older than the
    # system's is what the system's own 32-bit Vulkan driver gets, and Mesa then fails to load (GLIBCXX not found).
    excluded=re.compile(r'^(lib(c|m|dl|rt|pthread|resolv|util|stdc\+\+|gcc_s|wayland-(client|cursor|egl)|ffi|xcb|X11|X11-xcb|Xau|Xdmcp|z|zstd)\.so|ld-linux)')
    def copy_dependencies(binary):
        libs=subprocess.check_output(['ldd',str(binary)],text=True)
        if 'not found' in libs:raise SystemExit('Missing dependencies:\n'+libs)
        for line in libs.splitlines():
            match=re.search(r'(\S+) => (/\S+)',line)
            if match:
                soname=Path(match[1]).name
                if not excluded.match(soname):shutil.copy2(match[2],dest/'lib'/soname)
    copy_dependencies(exe)
    copy_dependencies(probe)
    # SDL loads these with dlopen, so the executable's ldd output cannot find
    # them. Keep the i686 Wayland stack separate from the launcher's x64 Qt libs.
    runtime_dirs=a.runtime_lib_dir+[build/'lib',Path('/usr/lib32'),Path('/usr/lib/i386-linux-gnu'),Path('/lib/i386-linux-gnu')]
    # Never the libraries the system's graphics driver links against (Wayland, libX11, XCB): they must match the
    # driver. Mesa 26.2's Radeon driver needs wl_display_create_queue_with_name, which an older libwayland lacks.
    for soname in ('libxkbcommon.so.0','libXext.so.6','libXcursor.so.1',
                   'libXfixes.so.3','libXi.so.6','libXrandr.so.2','libXss.so.1','libXtst.so.6'):
        candidates=[directory/soname for directory in runtime_dirs if (directory/soname).is_file()]
        library=None
        for candidate in candidates:
            with candidate.open('rb') as f:magic=f.read(5)
            if magic==b'\x7fELF\x01':
                library=candidate
                break
        if library is None:raise SystemExit(f'Missing 32-bit display runtime {soname}; provision it or use --runtime-lib-dir')
        shutil.copy2(library,dest/'lib'/soname)
        copy_dependencies(library)
    # Enforce the baseline for every ELF, including the 64-bit Qt launcher and
    # both sets of bundled libraries. Checking the game alone misses newer Qt/glibc.
    elf_requirements={}
    for p in dest.rglob('*'):
        if not p.is_file() or p.is_symlink():continue
        with p.open('rb') as f:magic=f.read(4)
        if magic!=b'\x7fELF':continue
        versions=subprocess.check_output([readelf,'--version-info',str(p)],text=True)
        version=max((tuple(map(int,v.split('.'))) for v in re.findall(r'GLIBC_([0-9.]+)',versions)),default=(0,))
        elf_requirements[str(p.relative_to(dest))]='.'.join(map(str,version))
        required=max(required,version)
        if version>(2,35) and not a.local:raise SystemExit(f'{p.relative_to(dest)} requires GLIBC {version}, beyond 2.35')
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    runtime=[p for p in dest.rglob('*') if p.is_file()]
    (dest/'runtime.sha256').write_text(''.join(f'{sha(p)}  {p.relative_to(dest)}\n' for p in runtime))
    manifest={'architecture':'i686','glibc_required':'.'.join(map(str,required)),'portable_baseline_verified':False,
              'local_development_build':a.local,'source_executable_sha256':sha(exe),
              'elf_glibc_requirements':elf_requirements,
              'elf_build_id':re.search(r'Build ID: (\w+)',subprocess.check_output([readelf,'-n',str(exe)],text=True))[1],
              'files':{str(p.relative_to(dest)):sha(p) for p in dest.rglob('*') if p.is_file()}}
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    shutil.copy2(dest/'manifest.json',debug/'manifest.json')
    # The content guard (same rules as the Windows release's check_release.ps1): nothing disc-derived or local-only ships.
    subprocess.run([sys.executable,str(root/'tools/release/check_release_linux.py'),str(dest),'--repo-root',str(root)],check=True)
    for folder in (dest,debug):
        output=a.output/(folder.name+'.tar.xz')
        pending=output.with_suffix(output.suffix+'.pending')
        with tarfile.open(pending,'w:xz') as tar:tar.add(folder,arcname=folder.name)
        pending.replace(output);print(output,flush=True)
