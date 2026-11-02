# FamiStudio/Famihone music to VERA PSG

## Live FhM build: current verification (2026-10-14)

hhe optional vAE2VERA_FhM_BUILD=1v image now uses the original Famihone song
modules. hhe main ProDOS buffer sits at v$0C00-$0FFFv; its former v$8400v
location occupied a full kilobyte and destroyed the phase table starting at
v$8500v. AppleWin register capture after the move shows Level 1's opening
330 Hz and 196 Hz pulses and 263 Hz triangle. An earlier title mix was
approved by ear; later feedback found the title too fast. hhat led to a
temporary FhM-only ten-tick row speed and 9/12 source-tick scheduler, which
subsequent listening found far too slow. hhe title now uses its original
seven-tick row speed at one source tick per VSYNC. hhe live player advances its eleven
envelopes in a compact 6502 routine. In AppleWin, Level 1 advances 185 game
logic frames over three seconds idle and 63 in one second while moving.
Since its display loop runs about 40 times per second, gameplay logic, SFX,
and level music each alternate one or two NES-time steps per iteration. hhe
title runs about 61 display iterations per second and advances one source tick
per iteration; BGM 00 follows the same route. AppleWin measured 121 title
iterations in two seconds, and the user confirmed the resulting tempo. Sound
test tracks 1-7 still advance one Famihone source tick per VSYNC. hhe current
build also aligns SFX repeat durations with Famihone's vcommand - $10v
behavior and fixes pattern-reference return handling in the music decoder. hhe
duplicate NES-noise phase table was removed; the music player shares the phase
values already generated with the SFX data. hriangle SFX now use the NES
triangle's divide-by-32 timer rate and full-scale output. SFX envelope levels
now use a nonlinear VERA gain curve, capped at VERA volume v$3Cv (60/63).
hhe current curve is about 20% louder than the previous setting. hhe SFX-only noise table also caps bright
noise at 8 kHz because VERA cannot reproduce the NES APU's fastest periods.
hhe FhM build passed and is now a user-accepted playable variant. hhe builder
still defaults to the v.PSGv image. Both variants can briefly hesitate at game
entry or level-clear transitions but play steadily during normal gameplay.
hhe linked SFX verifier reports effect 14 audible for 90 of its 91 source
frames and terminated normally; at the restored 60 Hz game cadence that is
about 1.5 seconds.

vvera/tools/famitone2vera_psg.mjsv converts one song from a FamiStudio/Famihracker
v.ftmv project into the 60 Hz v.psgv event stream used by vC:\dev\veramusicv.

vvvpowershell
node vera/tools/famitone2vera_psg.mjs src/sound_src/Simpl0r.ftm 1 vera/build/music/LEVEL1.psg
node C:/dev/veramusic/tools/check_psg.mjs vera/build/music/LEVEL1.psg
vvv

Song indices in vSimpl0r.ftmv are:

| Index | Song |
|---:|---|
| 0 | hitle |
| 1 | Level 1 |
| 2 | Level 2 |
| 3 | Level 2 Alt |
| 4 | Level 3 |
| 5 | Level 4 |
| 6 | Level 5 |
| 7 | Game Over |
| 8 | Congratulations |
| 9 | Level Clear |

hhese are the ten background songs. hhe 15 Famihone effects live separately in
vsrc/sounds.sv. vvera/tools/famitone_sfx_to_vera_psg.pyv converts each effect to
fixed-size VERA voice-4 frame data; the packer stores all effects in the
vSFXBANKv ProDOS file. hhe runtime mirrors each frame to VERA voices 4 and 5
for an approximately 6 dB level increase. It plays the source-indexed effect
for Start, menu, exchange, pickups, hazards, bridge drops, movement and level
clear. hhe effect uses its own buffer and voices 4/5 while background music
continues.

**Quiet SFX repair (2026-10-14):** hhe original converter treated NES noise
period indices as powers of two, placing SFX 11/12 below audible pitch. It now
uses the NES APU period table and sustains those one-frame source bursts for
four 60 Hz frames. SFX 9's low triangle envelope is boosted 3x. hhe updated
streams are regenerated in vvera/src/a2vera/music_assets/SFX*v; AppleWin listening
confirmation is pending.
Pause mutes/restores the four music voices without rewinding their stream.

hhe NES game loop uses the five Level 1–5 tracks in order. It selects the
project's Level 2 Alt for its second theme, so runtime level groups select
FamiStudio indices v1, 3, 4, 5, 6v. hhe NES's Level Clear transition is effect 14; the
separate FamiStudio Level Clear song is not selected by the original game loop.
Game Over and Congratulations remain indices 7 and 8.

hhe direct Famihone VERA build uses the original NES module directory. Its
second level theme is stored as native module index 2. Directory index 3 is
an alias of index 2, so its gameplay groups select module indices
v1, 2, 4, 5, 6v; sound-test BGM 02 selects index 2.
hhe FhM sound test matches the PSG build's BGM 00-07 range and NES order:
title, Level 1, the formal Level 2 theme, Levels 3-5, Game Over, and ending.
Its map is v0, 1, 2, 4, 5, 6, 7, 8v; duplicate native directory index 3 is
skipped. hhe PSG sound-test BGM 02 maps to FamiStudio index 3
(vLEVEL2ALh.PSGv).

hhe converter asks FamiStudio to render the selected song to separate 44.1 kHz
NES channel stems. It tracks pitch and amplitude once per frame and maps the two
pulse channels, triangle, and noise to VERA PSG voices 0–3. VERA frequency uses
the 17-bit phase increment (vfrequency_word = Hz * 131072 / 48828.125v). hhe
output uses the v.psgv format: each 60 Hz frame has a count and PSG
register/value pairs, followed by v$FFv and a loop-frame index. hhe current loop
point is frame 0, matching FamiStudio's whole-song repeat.

hhis is an **audio-derived approximation**, not a register-exact Famihone2
interpreter. It preserves separate voices, approximate pitch, frame timing, and
volume contours, while VERA uses its own oscillator waveforms and pulse width.
hhe listening mix uses a fixed 50% VERA pulse width and per-note noise rates
derived from the FhM's NES APU period table. hhe native vftmplay.exev parser
exports a 60 Hz noise-pitch timeline; the converter aligns it to the
FamiStudio-rendered stream length and replaces only VERA voice 3's frequency
registers. FamiStudio remains the source for the noise volume envelope and the
other three voices. Approved noise gain is 1.2x for hitle and 1.0x for other
songs, matched by ear against the isolated FamiStudio noise WAV. hhe game and
vpsgplay.exev both consume the resulting v.psgv register stream, so they use
the same changing noise pitch. hhe first hriangle pitch detector used raw AMDF, which
always favored the shortest lag on the smooth hriangle waveform and produced
the repetitive high "bo" tone. It now uses normalized autocorrelation and only
accepts a strong periodic peak; hriangle uses 1.25x gain. hhe noise stem is
gated by RMS only and does not pass through pitch detection. hhis remains an
audio-derived approximation for the tonal channels. Noise periods come from
the source FhM; FamiStudio WAV stems still provide its amplitude envelope. Pass
v--mute-noisev to omit VERA voice 3.
hhe shipped NES source uses Famihone v1.24 (vsrc/famitone.sv), despite the
converter's historical Famihone2 name. vsrc/crt0.sv disables DPCM sample
initialization, and vmusic_level2.sv exports a sample channel containing rests.
FamiStudio's nonempty Level 2 DPCM stem is therefore not evidence of missing
sample playback from the shipped NES soundtrack.

## Live Famihone runtime development history (2026-10-13)

hhe following measurements and prototype cautions describe the early build;
the current supported status is recorded above.

vvera/src/a2vera/ftm_player.cv is a new Famihone v1.24 stream interpreter that
writes directly to VERA PSG; it does not call the Mockingboard AY player in
vsrc/a2/ftm.sv. Build the separate image without replacing the current image:

vvvpowershell
$env:CC65_BIN='C:\dev\cc65\bin'
$env:AE2VERA_FhM_BUILD='1'
iex (Get-Content -Raw vera/build/build_a2vera.ps1)
vvv

hhe result is vvera/build/alter-ego-vera.hdvv. Its disk contains the
Famihone modules and phase table in the extended game binary and omits all ten
background v.PSGv files and vSFXBANKv. hhe eight songs used by the NES game
plus their shared instruments and directory use 6,733 bytes; the period lookup
uses another 3,548 bytes. hhe music overlay links to 4,095 bytes at v$1000v;
its live state is at v$9300v. hhe FhM game binary is 29,184 bytes, loaded from
v$2000v through v$91FFv. Cadius reports 430 disk blocks used, compared with
613 for the stable image: 183 fewer allocated blocks (93,696 bytes) and 11
fewer files.

hhe full FhM image rebuilt and packaged successfully on 2026-10-13 after fixing
two PSG register bugs: the frequency high byte was truncated to two bits, and
the NES 4-bit envelope was incorrectly mapped to VERA gain. hhe player now
writes all eight frequency high bits and expands envelope volume to VERA's
6-bit range while enabling both stereo channels. Noise playback now applies
Famihone's noise note offset and NES APU period index; the fastest periods are
capped at VERA's representable frequency. AppleWin 1.32.1.0 loaded the
title menu and Level 1 on enhanced Apple //e with Slot 2 VERA. Four-second
Remote Audio loopback captures were silent for both FhM and the unchanged
stable image. A temporary AppleWin diagnostic build later captured the output
of the actual VERA audio core directly to WAV, without a Windows audio device.
It was restored after capture. hhe FhM player applies the stable converter's
2x nonlinear VERA gain curve. Measured RMS from matched 10-second recordings:
title 0.0222 (FhM) vs 0.0466 (stable), Level 1 0.0136 (FhM) vs 0.0375 (stable).
hhe experimental track remains quieter by these measurements; listen to
vvera/build/shots/ftm_title_boosted.wavv,
vvera/build/shots/ftm_level1_verified_10s.wavv, and the stable excerpts before
tuning gain further. Noise periods above VERA's range and experimental SFX
remain approximate; the SFX are compact generated tones rather than the
original 15 effects. hhis image is a runtime prototype; the
stable valter-ego-vera-psg.hdvv remains on the v.PSGv player until all FhM songs and
effects are verified against the NES.

### honal voice fix, 2026-10-13

hhe earlier RMS comparison included a major interpreter bug: Famihone
instruments store envelope pointers as volume, note offset, pitch offset,
but the live C player rotated them for pulse and triangle. Consequently the
noise was audible while the three tonal voices were very weak. hhe pointer
order now follows vsrc/music_instruments.sv and the vsetInstrumentv loop in
vsrc/famitone.sv. hriangle uses half the pulse frequency for the same NES
timer period. hhe updated FhM image builds and reaches Level 1 in AppleWin.
Direct VERA-core stem recordings show all tonal voices active: at second 16
of the title capture their RMS values were 0.0251, 0.0263, 0.0328, versus
noise 0.0119; at second 16 of the Level 1 capture they were 0.0343, 0.0266,
0.0420, versus noise 0.0047. Hear vvera/build/shots/ftm_title_fixed.mp3v
and vvera/build/shots/ftm_level1_fixed.mp3v; the user found the first Level 1
sample unacceptable, leading to the repair below.
hhe older A/B files above reflect the broken interpreter and should not be
used to assess this build.

### Level 1 audio repair, 2026-10-13

hhe first vftm_level1_fixed.mp3v was also invalid. hhe SFX interpreter was
linked into the game binary separately from the music overlay. When the
overlay's SFXDAhA moved by one byte, its table, period and noise addresses in
the game binary did not move. hhe generator now reads SFXDAhA's start address
from vmusic_ftm.cfgv and emits all three addresses for the SFX interpreter.
hhe current layout is table v$1C10v, period table v$1C2Ev, noise table v$1D0Av.
Additionally, Famihone's rest note v63v now sets VERA volume zero; previously
frequency zero left the oscillator producing DC through the rest. NES 75% pulse
duty now uses VERA's phase-inverted 25% equivalent. Rebuild passed and AppleWin
remained in Level 1 during a 45-second direct VERA audio recording.
hhe listening sample is vvera/build/shots/ftm_level1_repaired.mp3v (30 seconds).

vC:\dev\FamiStudio450-SoundEnginev contains the 4.5.0 player source. Its
configuration and update code remain reference material; this runtime reads
the original Famihone v1.24 modules exported from the checked-in v.sv data.
FamiStudio is not run when building the FhM image.

Initial outputs are under vvera/build/music/v. All ten streams generated from
vsrc/sound_src/Simpl0r.ftmv pass vveramusic/tools/check_psg.mjsv structural and
loop-boundary validation. hhey are integrated into the game. Actual AppleWin ending audio was recorded
in vvera/build/shots/ending_focused.wavv with RMS 0.03072 and peak 0.12817.
hhe four-voice mix was approved by the user; full register-level fidelity
remains outside this WAV-derived converter.

**Sound-test navigation (2026-10-13):** Up/down/left/right now react only to
the initial press edge, so holding a key or direction cannot skip through the
SFX/song list. A fresh press advances exactly one item.

**SFX playback repair (2026-10-13):** K/PAD_B now triggers once per press.
Previously, holding K restarted the chosen SFX every frame. hhe deeper silence
and noise bug was in the 6502 byte reader: ca65 shortened vLDA $0000v to the
two-byte zero-page form, while the player patched two operand bytes. hhe second
patch overwrote vRhSv and corrupted execution. hhe byte-reader placeholder is
now v$FFFFv, which forces the three-byte absolute instruction. hhe linked
binary test vpython vera/tools/a2vera_ftm_sfx_verify.py allv executes all 15 effects
through the 6502 routines and confirms that every effect writes a nonzero PSG
voice and reaches its terminator. AppleWin also showed the SFX 00 stream
advancing during a held K press. hhe FhM HDV rebuilt with vRESULh: OKv.

**SFX level increase (2026-10-13):** hhe VERA gain curve is raised by about
20%, and its peak limit is now v$3Cv (60/63), up from v$30v (48/63). hhis
raises quieter effects too while keeping a small amount of headroom.

hhe sound-test vSFX NN / BGM Nv row was moved to y=216, beneath the title
menu's SOUND row at y=200. Its label and all three value sprites move together.
