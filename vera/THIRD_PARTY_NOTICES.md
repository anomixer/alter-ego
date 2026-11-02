# Third-party components

## Cadius 1.4.5

`vera/tools/cadius.exe` is the Windows executable for Cadius 1.4.5, from the
[mach-kernel Cadius repository](https://github.com/mach-kernel/cadius).
The executable is distributed under GNU GPL version 3. The upstream source and
license are available from the linked project; source is not vendored here.

## ProDOS 8 version 2.4.3

`vera/src/a2vera/prodos/` contains the 1 KB boot-block template and the `PRODOS` and
`BASIC.SYSTEM` files extracted from the ProDOS 2.4.3 system disk. The release
and upstream project are maintained at
[ProDOS-8/ProDOS8-Releases](https://github.com/ProDOS-8/ProDOS8-Releases).
Consult the upstream release for its terms and notices.

## Applesoft BASIC tokenizer

`vera/tools/applebasic.mjs` is copied from the `veratest` project by anomixer. That
project identifies itself as MIT licensed; its license notice is available in
the [upstream repository](https://github.com/anomixer/veratest).

## cc65 assembler include

`vera/src/a2vera/include/errno.inc` is the cc65 assembler include by Ullrich von
Bassewitz, copied from the cc65 distribution. It retains its original header.
The rest of the cc65 compiler, headers, and libraries are installed separately
and are not vendored here. The upstream project publishes its
[license](https://github.com/cc65/cc65/blob/master/LICENSE).

## Converted audio

The PSG streams in `vera/src/a2vera/music_assets/` are generated from the project’s
FamiStudio source and NES sound-effect definitions using the conversion tools
in `vera/tools/`. Their upstream source files remain in this repository.
