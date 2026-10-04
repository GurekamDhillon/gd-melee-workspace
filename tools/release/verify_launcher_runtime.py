"""Smoke-test the deployed Windows launcher without SDK/toolset DLL lookup paths."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(sys.argv[1]).resolve()
    env = {key.upper(): value for key, value in os.environ.items()}
    for key in ('QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'QML2_IMPORT_PATH',
                'QT_QPA_PLATFORMTHEME', 'QT_STYLE_OVERRIDE'):
        env.pop(key, None)
    # Without an attached console Qt answers --version with a modal message box, which
    # would block this check until the timeout; ask for plain output instead.
    env['QT_COMMAND_LINE_PARSER_NO_GUI_MESSAGE_BOXES'] = '1'
    system = env['SYSTEMROOT']
    env['PATH'] = system+'\\System32;'+system
    for executable in (root/'launcher/bin/gd-melee-launcher.exe', root/'GD Melee.exe'):
        try:
            result = subprocess.run([str(executable), '-platform', 'windows', '--version'],
                                    env=env, capture_output=True, text=True, timeout=20,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired) as error:
            print(f'deployed launcher smoke failed: {error}', file=sys.stderr)
            return 1
        print(result.stdout, end='')
        if result.returncode:
            print(result.stderr, file=sys.stderr)
            print(f'deployed launcher smoke failed: {result.returncode}', file=sys.stderr)
            return 1
    print('deployed launcher runtime OK (SDK-free PATH)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
