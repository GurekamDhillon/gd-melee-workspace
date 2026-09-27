# Ultimate Kirby ground Stone timing (13.0.2)

The public `SpecialLw.txt` dump schedules two 14% hitboxes at absolute frame 14,
then calls `frame(2)` and clears them. This ordering is present in the local
version-matched Ultimate binary, rather than a transcription error in the dump.

Source binary: `fighter/kirby`'s extracted `lua2cpp_kirby.nro`, SHA-256
`0d73bec6963f8e49d2008fcbb697dab36012e2536c2817f22ed986c308c69a63`.
The binary remains git-ignored. Addresses below use its Ghidra image base
`0x7100000000`; its text bytes map directly to file offsets after subtracting
that base.

| Address | Verified operation |
|---|---|
| `0x71004862ec` | Constructs hash40 `special_lw` (`0xab6928cf2`) for the Stone article. |
| `0x710048639c` | Calls `sv_animcmd::frame(5)`. |
| `0x710048645c` | Calls `sv_animcmd::frame(14)`. |
| `0x7100486488` | Calls helper `0x7100485690` in the same ACMD coroutine. |
| `0x7100485700` | Helper constructs hash40 `special_lw_to_ground` (`0x1476694801`). |
| `0x710048577c`, `0x7100485b0c` | Helper constructs two 14% hitboxes. |
| `0x7100485ec0` | Helper calls `sv_animcmd::frame(2)`. |
| `0x7100485f20` | Helper calls `AttackModule::clear_all`. |

[`smashline`'s ACMD documentation](https://github.com/HDR-Development/smashline/blob/master/src/lib.rs#L546-L604)
describes `frame(n)` as yielding until the frame timer is at least `n`. Thus
`frame(2)` after `frame(14)` adds no later active frame. The inference is that
the ground transformation's hitboxes have zero persistent frames. We did not
observe Ultimate runtime collision resolution directly. Melee Kirby's native
ground Stone motion row 332 likewise contains no ftcmd Hitbox opcode; its
native state remains in use. The aerial Stone hitbox is transferred separately
to row 336.

`ports/kirby-ultimate/tools/build_stone.py` accepts this ground resolution only
when the exact NRO hash, public source event shape, and empty host hitbox row
all match. Otherwise its manifest retains a ground timing blocker.
