Melee Linux port — development build

Open ./GD-Melee for the Qt launcher, disc library and installed-mod controls.
Or run ./launch-melee --iso "/path/to/your/disc.iso" directly.
Use --data-dir "/path/to/state" for an isolated writable profile.
The game requires a legally obtained Melee NTSC-U 1.02, Akaneia, or ACE disc image.
Disc images are not included.

This is an i686 executable for an x86-64 Linux host. Install the distribution's
32-bit glibc runtime and 32-bit Vulkan driver matching your GPU. Vulkan 1.1 or
newer is required. Mesa users need their distribution's 32-bit Mesa Vulkan
package; NVIDIA users need the matching 32-bit NVIDIA driver package.
The 64-bit Qt launcher also requires the distribution's OpenGL/EGL loader
libraries (libglx0, libgl1, libopengl0 and libegl1 on Ubuntu). These normally come with the
desktop graphics drivers and are deliberately not bundled with the package.
A glibc newer than the portable baseline may be needed for a LOCAL DEVELOPMENT
archive: consult manifest.json. Such an archive is not a portable release.

Native Wayland is supported by the Qt launcher and SDL game. The package includes
separate 64-bit Qt and 32-bit SDL Wayland runtimes. To force Wayland during a check,
use QT_QPA_PLATFORM=wayland for the launcher and SDL_VIDEO_DRIVER=wayland for the game.

The Qt launcher keeps one save folder per disc and imports legacy launcher.cfg
without modifying it. Its new settings are in launcher.json. Rename or Change ISO
keeps the disc's save folder. --data-dir selects a separate profile.
The launcher stores settings, cards, mods, script data and logs under XDG user
directories. Each run gets a separate log/cache directory. Existing saves are
never copied over. The installation directory can be read-only.

GameCube adapter: use Wii U/Switch mode. For permission errors, install the
included udev/51-melee-gamecube.rules as an administrator in /etc/udev/rules.d,
reload udev rules, then unplug/replug the adapter. The rule grants the active
local desktop session access only to USB 057e:0337. Close other programs that
own the adapter. No root privileges are required to run the game.
MELEE_SDL_GAMECUBE=1 selects SDL's adapter path instead of the raw USB transport.
Physical raw-adapter validation is pending; no adapter was available during development.

This release's acceptance scope is offline Windows parity. Networking, remote
mod downloads and crash uploads are outside the Qt launcher's current scope.

Debug symbols are distributed separately. Match the ELF build ID and artifact
checksums before symbolizing a core. Never upload a core without reviewing its
contents: it contains process memory.
