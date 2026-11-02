param([switch]$SkipAudio)
$ErrorActionPreference='Stop'
iex (Get-Content -Raw (Join-Path $PSScriptRoot 'a2vera_windows.ps1'))
iex (Get-Content -Raw (Join-Path $PSScriptRoot 'a2vera_cpu.ps1'))
$s=Get-AEGameSymbols
function V([string]$name) { return [AECPU]::Byte($s['_'+$name]) }
function Wait-State([scriptblock]$predicate,[string]$description,[int]$timeout=12) {
  $clock=[Diagnostics.Stopwatch]::StartNew()
  while (-not (& $predicate)) {
    if ($clock.Elapsed.TotalSeconds -ge $timeout) { throw "Timeout: $description" }
    Start-Sleep -Milliseconds 10
  }
}
$processId=Start-AEEmulator
[AECPU]::Attach([uint32]$processId)
Send-AEKey $processId 'T'
Start-Sleep -Seconds 2
Capture-AEFrame $processId 'C:\dev\alter-ego\vera\build\shots\sound_test.bmp'
Send-AEKey $processId 'D'
Start-Sleep -Milliseconds 40
Send-AEKey $processId 'W'
Start-Sleep -Milliseconds 40
Send-AEKey $processId 'K'
if (!$SkipAudio) {
  python 'C:\dev\alter-ego\vera\tools\a2vera_record_audio.py' 'C:\dev\alter-ego\vera\build\shots\sound_test_music.wav' --seconds 3
  if($LASTEXITCODE -ne 0) { throw 'Sound test music is silent' }
}
Send-AEKey $processId ' '
Wait-State { (V 'start_delay') -gt 0 } 'first level intro'
Wait-State { (V 'start_delay') -eq 0 } 'first level ready'
for($reserve=4;$reserve -ge 0;$reserve--) {
  Send-AEKey $processId ' '
  Wait-State { (V 'paused') -eq 1 } 'pause'
  Send-AEKey $processId 'S'
  Wait-State { (V 'pause_choice') -eq 1 } 'restart selection'
  Send-AEKey $processId ' '
  Wait-State { (V 'start_delay') -gt 0 } 'restart intro'
  Wait-State { (V 'start_delay') -eq 0 } 'restart ready'
  if ((V 'lives_remaining') -ne $reserve -or (V 'game_over')) { throw 'Reserve count/game-over differs from NES' }
  Write-Output "PASS restart: reserve=$reserve, current life still playable"
}
Send-AEKey $processId ' '
Wait-State { (V 'paused') -eq 1 } 'pause with zero reserves'
Send-AEKey $processId 'S'
Start-Sleep -Milliseconds 50
if ((V 'pause_choice') -ne 0) { throw 'Restart was offered with zero reserves' }
Send-AEKey $processId ' '
Wait-State { (V 'paused') -eq 0 } 'resume with zero reserves'
Start-Sleep -Milliseconds 80
Save-AEState $processId 'C:\dev\alter-ego\vera\build\shots\zero_reserve.aws.yaml'
Capture-AEFrame $processId 'C:\dev\alter-ego\vera\build\shots\zero_reserve.bmp'
# Descend via the normal puzzle route, then approach the enemy/platform edge.
# Either enemy collision or water must end the final life.
# Holding Left at the initial position stops against the upper platform wall.
$steps=python 'C:\dev\alter-ego\vera\tools\a2vera_route.py' 1 --json | ConvertFrom-Json
foreach($step in ($steps | Select-Object -First 6)) {
  Send-AEKey $processId $step.key
  Start-Sleep -Milliseconds ([int][Math]::Ceiling($step.frames*1000/60))
}
Send-AEKey $processId 'D' 4000
Wait-State { (V 'game_over') -eq 1 -and (V 'gameover_music_started') -eq 1 } 'final death/game over'
Save-AEState $processId 'C:\dev\alter-ego\vera\build\shots\verified_gameover.aws.yaml'
Capture-AEFrame $processId 'C:\dev\alter-ego\vera\build\shots\verified_gameover.bmp'
Write-Output "PASS final death: y=$(V 'player_y'), game over"
[AECPU]::Detach()
