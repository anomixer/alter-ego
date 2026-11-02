$ErrorActionPreference='Stop'
iex (Get-Content -Raw 'C:\dev\alter-ego\vera\tools\a2vera_windows.ps1')
iex (Get-Content -Raw 'C:\dev\alter-ego\vera\tools\a2vera_cpu.ps1')
$ftmMenuTest=$env:AE_MENU_TEST_FTM -eq '1'
$imagePath='C:\dev\alter-ego\vera\build\alter-ego-vera-psg.hdv'
$debugPath='C:\dev\alter-ego\vera\build\game.dbg'
if ($ftmMenuTest) {
  $imagePath='C:\dev\alter-ego\vera\build\alter-ego-vera.hdv'
  $debugPath='C:\dev\alter-ego\vera\build\game-ftm.dbg'
}
$s=Get-AEGameSymbols -debugPath $debugPath
function V([string]$name) { return [AECPU]::Byte($s['_'+$name]) }
function Wait-State([scriptblock]$predicate,[string]$description,[int]$timeout=15) {
  $clock=[Diagnostics.Stopwatch]::StartNew()
  while (-not (& $predicate)) {
    if ($clock.Elapsed.TotalSeconds -ge $timeout) { throw "Timeout: $description" }
    Start-Sleep -Milliseconds 10
  }
}
function Key([string]$key) {
  Send-AEKey $processId $key
  Start-Sleep -Milliseconds 80
}
$processId=Start-AEEmulator -bootWaitSeconds 2 -imagePath $imagePath
[AECPU]::Attach([uint32]$processId)
Wait-State { (V 'credits_visible') -eq 1 } 'credits screen'
Key ' '
Wait-State { (V 'credits_visible') -eq 0 } 'title screen'
Wait-State { (V 'frame_count') -gt 60 } 'title input guard'
if ($ftmMenuTest) {
  $counterBefore=V 'frame_count'
  $watch=[Diagnostics.Stopwatch]::StartNew()
  Start-Sleep -Milliseconds 1200
  $watch.Stop()
  $idleRate=(((V 'frame_count')-$counterBefore+256)%256)/$watch.Elapsed.TotalSeconds
  $counterBefore=V 'frame_count'
  $watch=[Diagnostics.Stopwatch]::StartNew()
  for ($n=0;$n -lt 8;$n++) { Key 'S'; Key 'W' }
  $watch.Stop()
  $navigationRate=(((V 'frame_count')-$counterBefore+256)%256)/$watch.Elapsed.TotalSeconds
  Write-Output ('FTM title frames/s: idle={0:N1}, navigating={1:N1}' -f $idleRate,$navigationRate)
}

Key 'S'
Wait-State { (V 'title_choice') -eq 1 } 'start level selection'
Key 'D'
Wait-State { (V 'title_level') -eq 2 } 'level increment'
Key 'S'
Wait-State { (V 'title_choice') -eq 2 } 'sound selection'
Key 'D'
Wait-State { (V 'music_muted') -eq 1 } 'music mute toggle'
Capture-AEFrame $processId 'C:\dev\alter-ego\vera\build\shots\title_music_off.bmp'
Key ' '
Wait-State { (V 'music_muted') -eq 0 } 'music unmute toggle'
Capture-AEFrame $processId 'C:\dev\alter-ego\vera\build\shots\title_music_on.bmp'
Key 'S'
Wait-State { (V 'title_choice') -eq 3 } 'sound selection'
Key 'D'
Wait-State { (V 'sound_muted') -eq 1 } 'sound mute toggle'
Capture-AEFrame $processId 'C:\dev\alter-ego\vera\build\shots\title_sound_off.bmp'
Key ' '
Wait-State { (V 'sound_muted') -eq 0 } 'sound unmute toggle'
Key 'W'
Wait-State { (V 'title_choice') -eq 2 } 'move to music choice'
Key 'W'
Wait-State { (V 'title_choice') -eq 1 } 'select level choice'
Capture-AEFrame $processId 'C:\dev\alter-ego\vera\build\shots\title_audio_menu.bmp'
Key ' '
Wait-State { (V 'current_level') -eq 2 -and (V 'start_delay') -gt 0 } 'selected level starts'
Wait-State { (V 'start_delay') -eq 0 } 'level ready'
Key ' '
Wait-State { (V 'paused') -eq 1 } 'pause menu'
if ($ftmMenuTest) {
  $counterBefore=V 'pause_frames'
  $watch=[Diagnostics.Stopwatch]::StartNew()
  Start-Sleep -Milliseconds 1200
  $watch.Stop()
  $pauseRate=(((V 'pause_frames')-$counterBefore+256)%256)/$watch.Elapsed.TotalSeconds
  Write-Output ('FTM pause frames/s: {0:N1}' -f $pauseRate)
}
Key 'S'
Wait-State { (V 'pause_choice') -eq 1 } 'restart option'
Start-Sleep -Milliseconds 250
if ((V 'pause_choice') -ne 1) { throw 'One Down press must select only Restart' }
Key 'S'
Wait-State { (V 'pause_choice') -eq 2 } 'exit option'
Capture-AEFrame $processId 'C:\dev\alter-ego\vera\build\shots\pause_exit_menu.bmp'
Key ' '
Wait-State { (V 'paused') -eq 0 -and (V 'title_choice') -eq 0 } 'exit returns to title'
Wait-State { (V 'frame_count') -gt 60 } 'returned title input guard'
if ((V 'start_delay') -ne 0 -or (V 'current_level') -ne 1) {
  throw 'Exit should remain on the title until the next Start press'
}
Capture-AEFrame $processId 'C:\dev\alter-ego\vera\build\shots\title_returned_from_exit.bmp'
[AECPU]::Detach()
Write-Output 'PASS: title audio toggles, level selection, pause Exit, and return to title'
