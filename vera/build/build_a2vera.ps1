$ErrorActionPreference='Stop'
$root=$PSScriptRoot
if(-not $root){
  $candidate=(Get-Location).Path
  while($candidate -and -not (Test-Path (Join-Path $candidate 'vera\src\a2vera\main.c'))){
    $parent=Split-Path $candidate -Parent
    if($parent -eq $candidate){$candidate=$null}else{$candidate=$parent}
  }
  $root=$candidate
}else{$root=Join-Path $root '..\..'}
if(-not $root -or -not (Test-Path (Join-Path $root 'vera\src\a2vera\main.c'))){
  throw 'Could not locate the repository root (expected vera\src\a2vera\main.c). Run this script from inside the repository.'
}
$root=(Resolve-Path $root).Path
$work=Join-Path $root 'vera\build'
# The live FamiTone image is the default build.  AE2VERA_PSG_BUILD=1 selects
# the streamed PSG image instead; AE2VERA_FTM_BUILD is still honoured as an
# explicit override (1 = FTM, 0 = PSG) for commands written before the flip.
$psgBuild=$env:AE2VERA_PSG_BUILD -eq '1'
if($env:AE2VERA_FTM_BUILD -eq '0'){$psgBuild=$true}
elseif($env:AE2VERA_FTM_BUILD -eq '1'){$psgBuild=$false}
$ftmBuild=-not $psgBuild
$cc=$env:CC65_BIN
if(-not $cc){
  $cc65Command=Get-Command cc65.exe -ErrorAction SilentlyContinue
  if($cc65Command){$cc=Split-Path $cc65Command.Source -Parent}
}
if(-not $cc -or -not (Test-Path (Join-Path $cc 'cc65.exe'))){
  throw 'cc65 toolchain not found. Set CC65_BIN to the cc65 bin directory or add cc65.exe to PATH.'
}
$level=1
if($env:AE2VERA_LEVEL){$level=[int]$env:AE2VERA_LEVEL}
if($level -lt 0 -or $level -gt 25){throw 'AE2VERA_LEVEL must be 0..25'}
Get-Process AppleWin* -ErrorAction SilentlyContinue | Stop-Process -Force
if(-not $env:AE2VERA_SKIP_ASSETS){
python "$root\vera\tools\a2vera_level.py" $level $work
if($LASTEXITCODE -ne 0){throw 'level converter failed'}
for($n=0;$n -lt 26;$n++){
  $id=$n.ToString('00'); $out="$work\levels\LV$id"
  python "$root\vera\tools\a2vera_level.py" $n $out
  if($LASTEXITCODE -ne 0){throw "level $n converter failed"}
}
python "$root\vera\tools\a2vera_title.py" $work
if($LASTEXITCODE -ne 0){throw 'title converter failed'}
python "$root\vera\tools\a2vera_art.py"
if($LASTEXITCODE -ne 0){throw 'ending art converter failed'}
}
New-Item -ItemType Directory -Force -Path "$work\music" | Out-Null
if(-not $ftmBuild){
  Copy-Item "$root\vera\src\a2vera\music_assets\*" "$work\music" -Force
  foreach($song in @('TITLE','LEVEL1','LEVEL2','LEVEL2ALT','LEVEL3','LEVEL4','LEVEL5','GAMEOVER','CONGRATS','CLEAR')){
    node "$root\vera\tools\check_vera_psg.mjs" "$work\music\$song.psg"
    if($LASTEXITCODE -ne 0){throw "$song PSG validation failed"}
  }
}else{
  python "$root\vera\tools\a2vera_ftm_tables.py" "$work\ftm_tables.h"
  if($LASTEXITCODE -ne 0){throw 'FamiTone table generation failed'}
  python "$root\vera\tools\a2vera_ftm_sfx.py" "$work\ftm_sfx_data.s"
  if($LASTEXITCODE -ne 0){throw 'FamiTone SFX conversion failed'}
  & "$cc\ca65.exe" --cpu 6502 -I "$root\vera\src" -I "$root\src" -D FTM_VERA=1 -o "$work\fami_modules_ftm.o" "$root\vera\src\a2vera\fami_modules.s"
  if($LASTEXITCODE -ne 0){throw 'FamiTone track data assembly failed'}
  & "$cc\ca65.exe" --cpu 6502 -o "$work\ftm_sfx_data.o" "$work\ftm_sfx_data.s"
  if($LASTEXITCODE -ne 0){throw 'FamiTone SFX frame data assembly failed'}
  & "$cc\ca65.exe" --cpu 6502 -o "$work\ftm_envelopes.o" "$root\vera\src\a2vera\ftm_envelopes.s"
  if($LASTEXITCODE -ne 0){throw 'FamiTone envelope assembly failed'}
  & "$cc\ca65.exe" --cpu 6502 -o "$work\ftm_pitch_table.o" "$work\ftm_pitch_table.s"
  if($LASTEXITCODE -ne 0){throw 'FamiTone pitch table assembly failed'}
}
if($ftmBuild){$musicApiSource="$root\vera\src\a2vera\music_api_ftm.s"}else{$musicApiSource="$root\vera\src\a2vera\music_api.s"}
& "$cc\ca65.exe" --cpu 6502 -o "$work\music_api.o" $musicApiSource
if($LASTEXITCODE -ne 0){throw 'ca65 music API failed'}
if($ftmBuild){$musicImportsSource="$root\vera\src\a2vera\music_imports_ftm.s"}else{$musicImportsSource="$root\vera\src\a2vera\music_imports.s"}
& "$cc\ca65.exe" --cpu 6502 -o "$work\music_imports.o" $musicImportsSource
if($LASTEXITCODE -ne 0){throw 'ca65 music imports failed'}
$mainIobufBase=33792
if($ftmBuild){$mainIobufBase=3072} # $0C00-$0FFF; $8400 would overwrite the FTM pitch table.
& "$cc\ca65.exe" --cpu 6502 -I "$root\vera\src\a2vera\include" -D "IOBUF_BASE=$mainIobufBase" -D IOBUF_COUNT=1 -o "$work\iobuf_main.o" "$root\vera\src\a2vera\iobuf.s"
if($LASTEXITCODE -ne 0){throw 'ca65 main I/O buffers failed'}
if(-not $ftmBuild){
  & "$cc\ca65.exe" --cpu 6502 -I "$root\vera\src\a2vera\include" -D IOBUF_BASE=34816 -D IOBUF_COUNT=2 -o "$work\iobuf_music.o" "$root\vera\src\a2vera\iobuf.s"
  if($LASTEXITCODE -ne 0){throw 'ca65 music I/O buffers failed'}
}
& "$cc\ca65.exe" --cpu 6502 -o "$work\input.o" "$root\vera\src\a2vera\input.s"
if($LASTEXITCODE -ne 0){throw 'ca65 joystick input failed'}
foreach($variant in @(@('2','C200'),@('4','C400'))){
  $slot=$variant[0]; $hex=$variant[1]
  $ccDefine="-DVERA_BASE=0x$hex"; $asmDefine='VERA_BASE=$'+$hex
  # Use the base Apple II target/library: apple2enh.lib contains 65C02-only
  # opcodes (including $92), which jam an NMOS 6502 in the Apple II+.
  & "$cc\ca65.exe" --cpu 6502 -D $asmDefine -o "$work\title$slot.o" "$root\vera\src\a2vera\title.s"
  if($LASTEXITCODE -ne 0){throw "ca65 title failed for Slot $slot"}
  $mainOpt='-Oirs'; if($ftmBuild){$mainOpt='-Os'}
  $mainDefines=@($ccDefine)
  if($ftmBuild){$mainDefines+=@('-D','FTM_VERA=1')}
  & "$cc\cc65.exe" -t apple2 --cpu 6502 -g $mainOpt -Cl @mainDefines -o "$work\main$slot.s" "$root\vera\src\a2vera\main.c"
  if($LASTEXITCODE -ne 0){throw "cc65 main failed for Slot $slot"}
  & "$cc\cc65.exe" -t apple2 --cpu 6502 -Oirs -Cl $ccDefine -o "$work\oam$slot.s" "$root\vera\src\a2vera\oam.c"
  if($LASTEXITCODE -ne 0){throw "cc65 OAM failed for Slot $slot"}
  if($ftmBuild){
    & "$cc\cc65.exe" -t apple2 --cpu 6502 -Os -Cl $ccDefine -I "$work" -o "$work\ftm_player$slot.s" "$root\vera\src\a2vera\ftm_player.c"
    if($LASTEXITCODE -ne 0){throw "cc65 FamiTone player failed for Slot $slot"}
    & "$cc\ca65.exe" --cpu 6502 -o "$work\ftm_player$slot.o" "$work\ftm_player$slot.s"
    if($LASTEXITCODE -ne 0){throw "ca65 FamiTone player failed for Slot $slot"}
    $sfxAsmDefine='VERA_BASE=$'+$hex
    & "$cc\ca65.exe" --cpu 6502 -I "$work" -D $sfxAsmDefine -o "$work\ftm_sfx_simple$slot.o" "$root\vera\src\a2vera\ftm_sfx_simple.s"
    if($LASTEXITCODE -ne 0){throw "ca65 compact FamiTone SFX failed for Slot $slot"}
  }else{
    & "$cc\cc65.exe" -t apple2 --cpu 6502 -Oirs -Cl $ccDefine -o "$work\music$slot.s" "$root\vera\src\a2vera\music.c"
    if($LASTEXITCODE -ne 0){throw "cc65 music failed for Slot $slot"}
  }
  & "$cc\ca65.exe" --cpu 6502 -g -o "$work\main$slot.o" "$work\main$slot.s"
  if($LASTEXITCODE -ne 0){throw "ca65 main failed for Slot $slot"}
  & "$cc\ca65.exe" --cpu 6502 -o "$work\oam$slot.o" "$work\oam$slot.s"
  if($LASTEXITCODE -ne 0){throw "ca65 OAM failed for Slot $slot"}
  $oamDefines=@($asmDefine)
  if($ftmBuild){$oamDefines+=@('-D','FTM_VERA=1')}
  & "$cc\ca65.exe" --cpu 6502 -D @oamDefines -o "$work\oam_core$slot.o" "$root\vera\src\a2vera\oam.s"
  if($LASTEXITCODE -ne 0){throw "ca65 OAM core failed for Slot $slot"}
  if($ftmBuild){
    & "$cc\ld65.exe" -C "$root\vera\src\a2vera\music_ftm.cfg" -m "$work\music$slot.map" -o "$work\AEMUSIC$slot#061000" "$work\music_api.o" "$work\ftm_player$slot.o" "$work\ftm_envelopes.o" "$work\ftm_sfx_data.o" "$cc\..\lib\apple2.lib"
  }else{
    & "$cc\ca65.exe" --cpu 6502 -o "$work\music$slot.o" "$work\music$slot.s"
    if($LASTEXITCODE -ne 0){throw "ca65 music failed for Slot $slot"}
    & "$cc\ld65.exe" -C "$root\vera\src\a2vera\music.cfg" -m "$work\music$slot.map" -o "$work\AEMUSIC$slot#061000" "$work\music_api.o" "$work\music$slot.o" "$work\iobuf_music.o" "$cc\..\lib\apple2.lib"
  }
  if($LASTEXITCODE -ne 0){throw "music overlay link failed for Slot $slot"}
  if($ftmBuild){
    & "$cc\ld65.exe" -C "$root\vera\src\a2vera\title_ftm.cfg" --dbgfile "$work\game$slot.dbg" -m "$work\level$slot.map" -o "$work\AE2VERA$slot#062000" "$work\title$slot.o" "$work\main$slot.o" "$work\oam$slot.o" "$work\oam_core$slot.o" "$work\input.o" "$work\music_imports.o" "$work\iobuf_main.o" "$work\fami_modules_ftm.o" "$work\ftm_pitch_table.o" "$work\ftm_sfx_simple$slot.o" "$cc\..\lib\apple2.lib"
  }else{
    & "$cc\ld65.exe" -C "$root\vera\src\a2vera\title.cfg" --dbgfile "$work\game$slot.dbg" -m "$work\level$slot.map" -o "$work\AE2VERA$slot#062000" "$work\title$slot.o" "$work\main$slot.o" "$work\oam$slot.o" "$work\oam_core$slot.o" "$work\input.o" "$work\music_imports.o" "$work\iobuf_main.o" "$cc\..\lib\apple2.lib"
  }
  if($LASTEXITCODE -ne 0){throw "game link failed for Slot $slot"}
}
# Keep Slot 2 as the default symbols/map target for the existing emulator tools.
Copy-Item "$work\game2.dbg" "$work\game.dbg" -Force
if($ftmBuild){Copy-Item "$work\game2.dbg" "$work\game-ftm.dbg" -Force}
Copy-Item "$work\level2.map" "$work\level1.map" -Force
if($ftmBuild){node "$root\vera\tools\a2vera_title_pack.mjs" --ftm}
else{node "$root\vera\tools\a2vera_title_pack.mjs"}
if($LASTEXITCODE -ne 0){throw 'ProDOS packaging failed'}
if($ftmBuild -and $env:AE2VERA_FTM_FLOPPY -eq '1'){
  node "$root\vera\tools\a2vera_ftm_floppy_pack.mjs"
  if($LASTEXITCODE -ne 0){throw 'FTM dual-floppy packaging failed'}
}
