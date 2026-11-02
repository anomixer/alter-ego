# FamiStudio/FamiTone music to VERA PSG

## Live FTM build: current verification (2026-10-14)

The live FamiTone image -- the default build since 2026-11-03, with PSG opt-in
via `AE2VERA_PSG_BUILD=1` -- uses the original FamiTone song modules. The main
ProDOS buffer sits at `$0C00-$0FFF`; its former `$8400` location occupied a
full kilobyte and destroyed the phase table starting at
`$8500`. AppleWin register capture after the move shows Level 1's opening
330 Hz and 196 Hz pulses and 263 Hz triangle. An earlier title mix was
approved by ear; later feedback found the title too fast. That led to a
temporary FTM-only ten-tick row speed and 9/12 source-tick scheduler, which
subsequent listening found far too slow. The title now uses its original
seven-tick row speed at one source tick per VSYNC. The live player advances its eleven
envelopes in a compact 6502 routine. In AppleWin, Level 1 advances 185 game
logic frames over three seconds idle and 63 in one second while moving.
Since its display loop runs about 40 times per second, gameplay logic, SFX,
and level music each alternate one or two NES-time steps per iteration. The
title runs about 61 display iterations per second and advances one source tick
per iteration; BGM 00 follows the same route. AppleWin measured 121 title
iterations in two seconds, and the user confirmed the resulting tempo. Sound
test tracks 1-7 still advance one FamiTone source tick per VSYNC. The current
build also aligns SFX repeat durations with FamiTone's `command - $10`
behavior and fixes pattern-reference return handling in the music decoder. The
duplicate NES-noise phase table was removed; the music player shares the phase
values already generated with the SFX data. Triangle SFX now use the NES
triangle's divide-by-32 timer rate and full-scale output. SFX envelope levels
now use a nonlinear VERA gain curve, capped at VERA volume `$3C` (60/63).
The current curve is about 20% louder than the previous setting. The SFX-only noise table also caps bright
noise at 8 kHz because VERA cannot reproduce the NES APU's fastest periods.
The FTM build passed and is now a user-accepted playable variant; it is also
the builder default since 2026-11-03. Both variants can briefly hesitate at game
entry or level-clear transitions but play steadily during normal gameplay.
The linked SFX verifier reports effect 14 audible for 90 of its 91 source
frames and terminated normally; at the restored 60 Hz game cadence that is
about 1.5 seconds.

`vera/tools/famitone2vera_psg.mjs` converts one song from a FamiStudio/FamiTracker
`.ftm` project into the 60 Hz `.psg` event stream used by `C:\dev\veramusic`.

```powershell
node vera/tools/famitone2vera_psg.mjs src/sound_src/Simpl0r.ftm 1 vera/build/music/LEVEL1.psg
node C:/dev/veramusic/tools/check_psg.mjs vera/build/music/LEVEL1.psg
```

Song indices in `Simpl0r.ftm` are:

| Index | Song |
|---:|---|
| 0 | Title |
| 1 | Level 1 |
| 2 | Level 2 |
| 3 | Level 2 Alt |
| 4 | Level 3 |
| 5 | Level 4 |
| 6 | Level 5 |
| 7 | Game Over |
| 8 | Congratulations |
| 9 | Level Clear |

These are the ten background songs. The 15 FamiTone effects live separately in
`src/sounds.s`. `vera/tools/famitone_sfx_to_vera_psg.py` converts each effect to
fixed-size VERA voice-4 frame data; the packer stores all effects in the
`SFXBANK` ProDOS file. The runtime mirrors each frame to VERA voices 4 and 5
for an approximately 6 dB level increase. It plays the source-indexed effect
for Start, menu, exchange, pickups, hazards, bridge drops, movement and level
clear. The effect uses its own buffer and voices 4/5 while background music
continues.

**Quiet SFX repair (2026-10-14):** The original converter treated NES noise
period indices as powers of two, placing SFX 11/12 below audible pitch. It now
uses the NES APU period table and sustains those one-frame source bursts for
four 60 Hz frames. SFX 9's low triangle envelope is boosted 3x. The updated
streams are regenerated in `vera/src/a2vera/music_assets/SFX*`; AppleWin listening
confirmation is pending.
Pause mutes/restores the four music voices without rewinding their stream.

The NES game loop uses the five Level 1–5 tracks in order. It selects the
project's Level 2 Alt for its second theme, so runtime level groups select
FamiStudio indices `1, 3, 4, 5, 6`. The NES's Level Clear transition is effect 14; the
separate FamiStudio Level Clear song is not selected by the original game loop.
Game Over and Congratulations remain indices 7 and 8.

The direct FamiTone VERA build uses the original NES module directory. Its
second level theme is stored as native module index 2. Directory index 3 is
an alias of index 2, so its gameplay groups select module indices
`1, 2, 4, 5, 6`; sound-test BGM 02 selects index 2.
The FTM sound test matches the PSG build's BGM 00-07 range and NES order:
title, Level 1, the formal Level 2 theme, Levels 3-5, Game Over, and ending.
Its map is `0, 1, 2, 4, 5, 6, 7, 8`; duplicate native directory index 3 is
skipped. The PSG sound-test BGM 02 maps to FamiStudio index 3
(`LEVEL2ALT.PSG`).

The converter asks FamiStudio to render the selected song to separate 44.1 kHz
NES channel stems. It tracks pitch and amplitude once per frame and maps the two
pulse channels, triangle, and noise to VERA PSG voices 0–3. VERA frequency uses
the 17-bit phase increment (`frequency_word = Hz * 131072 / 48828.125`). The
output uses the `.psg` format: each 60 Hz frame has a count and PSG
register/value pairs, followed by `$FF` and a loop-frame index. The current loop
point is frame 0, matching FamiStudio's whole-song repeat.

This is an **audio-derived approximation**, not a register-exact FamiTone2
interpreter. It preserves separate voices, approximate pitch, frame timing, and
volume contours, while VERA uses its own oscillator waveforms and pulse width.
The listening mix uses a fixed 50% VERA pulse width and per-note noise rates
derived from the FTM's NES APU period table. The native `ftmplay.exe` parser
exports a 60 Hz noise-pitch timeline; the converter aligns it to the
FamiStudio-rendered stream length and replaces only VERA voice 3's frequency
registers. FamiStudio remains the source for the noise volume envelope and the
other three voices. Approved noise gain is 1.2x for Title and 1.0x for other
songs, matched by ear against the isolated FamiStudio noise WAV. The game and
`psgplay.exe` both consume the resulting `.psg` register stream, so they use
the same changing noise pitch. The first Triangle pitch detector used raw AMDF, which
always favored the shortest lag on the smooth Triangle waveform and produced
the repetitive high "bo" tone. It now uses normalized autocorrelation and only
accepts a strong periodic peak; Triangle uses 1.25x gain. The noise stem is
gated by RMS only and does not pass through pitch detection. This remains an
audio-derived approximation for the tonal channels. Noise periods come from
the source FTM; FamiStudio WAV stems still provide its amplitude envelope. Pass
`--mute-noise` to omit VERA voice 3.
The shipped NES source uses FamiTone v1.24 (`src/famitone.s`), despite the
converter's historical FamiTone2 name. `src/crt0.s` disables DPCM sample
initialization, and `music_level2.s` exports a sample channel containing rests.
FamiStudio's nonempty Level 2 DPCM stem is therefore not evidence of missing
sample playback from the shipped NES soundtrack.

## Live FamiTone runtime development history (2026-10-13)

The following measurements and prototype cautions describe the early build;
the current supported status is recorded above.

`vera/src/a2vera/ftm_player.c` is a new FamiTone v1.24 stream interpreter that
writes directly to VERA PSG; it does not call the Mockingboard AY player in
`src/a2/ftm.s`. It is the default image since 2026-11-03:

```powershell
$env:CC65_BIN='C:\dev\cc65\bin'
iex (Get-Content -Raw vera/build/build_a2vera.ps1)
```

The result is `vera/build/alter-ego-vera.hdv`. Its disk contains the
FamiTone modules and phase table in the extended game binary and omits all ten
background `.PSG` files and `SFXBANK`. The eight songs used by the NES game
plus their shared instruments and directory use 6,733 bytes; the period lookup
uses another 3,548 bytes. The music overlay links to 4,095 bytes at `$1000`;
its live state is at `$9300`. The FTM game binary is 29,184 bytes, loaded from
`$2000` through `$91FF`. Cadius reports 430 disk blocks used, compared with
613 for the stable image: 183 fewer allocated blocks (93,696 bytes) and 11
fewer files.

The full FTM image rebuilt and packaged successfully on 2026-10-13 after fixing
two PSG register bugs: the frequency high byte was truncated to two bits, and
the NES 4-bit envelope was incorrectly mapped to VERA gain. The player now
writes all eight frequency high bits and expands envelope volume to VERA's
6-bit range while enabling both stereo channels. Noise playback now applies
FamiTone's noise note offset and NES APU period index; the fastest periods are
capped at VERA's representable frequency. AppleWin 1.32.1.0 loaded the
title menu and Level 1 on enhanced Apple //e with Slot 2 VERA. Four-second
Remote Audio loopback captures were silent for both FTM and the unchanged
stable image. A temporary AppleWin diagnostic build later captured the output
of the actual VERA audio core directly to WAV, without a Windows audio device.
It was restored after capture. The FTM player applies the stable converter's
2x nonlinear VERA gain curve. Measured RMS from matched 10-second recordings:
title 0.0222 (FTM) vs 0.0466 (stable), Level 1 0.0136 (FTM) vs 0.0375 (stable).
The experimental track remains quieter by these measurements; listen to
`vera/build/shots/ftm_title_boosted.wav`,
`vera/build/shots/ftm_level1_verified_10s.wav`, and the stable excerpts before
tuning gain further. Noise periods above VERA's range and experimental SFX
remain approximate; the SFX are compact generated tones rather than the
original 15 effects. This image is a runtime prototype; the
stable `alter-ego-vera-psg.hdv` remains on the `.PSG` player until all FTM songs and
effects are verified against the NES.

### Tonal voice fix, 2026-10-13

The earlier RMS comparison included a major interpreter bug: FamiTone
instruments store envelope pointers as volume, note offset, pitch offset,
but the live C player rotated them for pulse and triangle. Consequently the
noise was audible while the three tonal voices were very weak. The pointer
order now follows `src/music_instruments.s` and the `setInstrument` loop in
`src/famitone.s`. Triangle uses half the pulse frequency for the same NES
timer period. The updated FTM image builds and reaches Level 1 in AppleWin.
Direct VERA-core stem recordings show all tonal voices active: at second 16
of the title capture their RMS values were 0.0251, 0.0263, 0.0328, versus
noise 0.0119; at second 16 of the Level 1 capture they were 0.0343, 0.0266,
0.0420, versus noise 0.0047. Hear `vera/build/shots/ftm_title_fixed.mp3`
and `vera/build/shots/ftm_level1_fixed.mp3`; the user found the first Level 1
sample unacceptable, leading to the repair below.
The older A/B files above reflect the broken interpreter and should not be
used to assess this build.

### Level 1 audio repair, 2026-10-13

The first `ftm_level1_fixed.mp3` was also invalid. The SFX interpreter was
linked into the game binary separately from the music overlay. When the
overlay's SFXDATA moved by one byte, its table, period and noise addresses in
the game binary did not move. The generator now reads SFXDATA's start address
from `music_ftm.cfg` and emits all three addresses for the SFX interpreter.
The current layout is table `$1C10`, period table `$1C2E`, noise table `$1D0A`.
Additionally, FamiTone's rest note `63` now sets VERA volume zero; previously
frequency zero left the oscillator producing DC through the rest. NES 75% pulse
duty now uses VERA's phase-inverted 25% equivalent. Rebuild passed and AppleWin
remained in Level 1 during a 45-second direct VERA audio recording.
The listening sample is `vera/build/shots/ftm_level1_repaired.mp3` (30 seconds).

`C:\dev\FamiStudio450-SoundEngine` contains the 4.5.0 player source. Its
configuration and update code remain reference material; this runtime reads
the original FamiTone v1.24 modules exported from the checked-in `.s` data.
FamiStudio is not run when building the FTM image.

Initial outputs are under `vera/build/music/`. All ten streams generated from
`src/sound_src/Simpl0r.ftm` pass `veramusic/tools/check_psg.mjs` structural and
loop-boundary validation. They are integrated into the game. Actual AppleWin ending audio was recorded
in `vera/build/shots/ending_focused.wav` with RMS 0.03072 and peak 0.12817.
The four-voice mix was approved by the user; full register-level fidelity
remains outside this WAV-derived converter.

**Sound-test navigation (2026-10-13):** Up/down/left/right now react only to
the initial press edge, so holding a key or direction cannot skip through the
SFX/song list. A fresh press advances exactly one item.

**SFX playback repair (2026-10-13):** K/PAD_B now triggers once per press.
Previously, holding K restarted the chosen SFX every frame. The deeper silence
and noise bug was in the 6502 byte reader: ca65 shortened `LDA $0000` to the
two-byte zero-page form, while the player patched two operand bytes. The second
patch overwrote `RTS` and corrupted execution. The byte-reader placeholder is
now `$FFFF`, which forces the three-byte absolute instruction. The linked
binary test `python vera/tools/a2vera_ftm_sfx_verify.py all` executes all 15 effects
through the 6502 routines and confirms that every effect writes a nonzero PSG
voice and reaches its terminator. AppleWin also showed the SFX 00 stream
advancing during a held K press. The FTM HDV rebuilt with `RESULT: OK`.

**SFX level increase (2026-10-13):** The VERA gain curve is raised by about
20%, and its peak limit is now `$3C` (60/63), up from `$30` (48/63). This
raises quieter effects too while keeping a small amount of headroom.

The sound-test `SFX NN / BGM N` row was moved to y=216, beneath the title
menu's SOUND row at y=200. Its label and all three value sprites move together.
