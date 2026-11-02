$ErrorActionPreference='Stop'
iex (Get-Content -Raw 'C:\dev\alter-ego\vera\tools\a2vera_windows.ps1')
iex (Get-Content -Raw 'C:\dev\alter-ego\vera\tools\a2vera_cpu.ps1')
$symbols=Get-AEGameSymbols
function Value([string]$name) { [AECPU]::Byte($symbols['_'+$name]) }
function Wait-InputState([scriptblock]$condition,[string]$description) {
  $deadline=(Get-Date).AddSeconds(12)
  while(-not (& $condition)) {
    if((Get-Date) -ge $deadline) { throw "Timeout: $description" }
    Start-Sleep -Milliseconds 10
  }
}
function Virtual-Key([int]$processId,[int]$vk,[bool]$extended,[int]$hold=40) {
  $frame=Get-AEWindows $processId | Where-Object Class -eq 'APPLE2FRAME'
  $scan=[AEWindow]::MapVirtualKey($vk,0)
  $flags=1L+($scan -shl 16)
  if($extended) { $flags+=0x1000000 }
  [void][AEWindow]::PostMessage($frame.Handle,0x100,[IntPtr]$vk,[IntPtr]$flags)
  Start-Sleep -Milliseconds $hold
  [void][AEWindow]::PostMessage($frame.Handle,0x101,[IntPtr]$vk,[IntPtr]($flags+3221225472L))
}
$arrow=@{A=0x25;W=0x26;D=0x27;S=0x28}
$joystick=@{A=0x64;W=0x68;D=0x66;S=0x62;J=0x60}
foreach($mode in @('arrows','joystick')) {
  if($mode -eq 'joystick' -and (Get-ItemProperty 'HKCU:\Software\AppleWin\CurrentVersion\Configuration').'Joystick0 Emu Type v3' -ne 3) {
    throw 'Set AppleWin Joystick 1 to NumPad for the joystick regression test'
  }
  $processId=Start-AEEmulator
  [AECPU]::Attach([uint32]$processId)
  function Control([string]$key,[int]$hold=40) {
    if($mode -eq 'joystick') {
      $vk=if($key -eq ' '){0x6E}else{$joystick[$key]}
      Virtual-Key $processId $vk $false $hold
    } elseif($arrow.ContainsKey($key)) { Virtual-Key $processId $arrow[$key] $true $hold }
    else { Send-AEKey $processId $key; Start-Sleep -Milliseconds $hold }
  }
  Control ' '
  Wait-InputState { (Value 'start_delay') -gt 0 } "$mode level intro"
  Wait-InputState { (Value 'start_delay') -eq 0 } "$mode ready"
  foreach($step in @(@('A',176,88),@('D',184,88),@('A',176,88),@('A',168,88),@('J',80,88),@('S',80,96),@('W',80,88))) {
    Control $step[0]
    Wait-InputState {
      (Value 'player_x') -eq $step[1] -and (Value 'player_y') -eq $step[2] -and
      (Value 'player_move_steps') -eq 0 -and (Value 'exchange_active') -eq 0
    } "$mode $($step[0]) to $($step[1]),$($step[2])"
  }
  if((Value 'exchange_left') -ne 1) { throw 'Exchange did not spend exactly one charge' }
  Control ' ' 400
  Wait-InputState { (Value 'paused') -eq 1 -and (Value 'pause_frames') -gt 0 } "$mode pause held once"
  Control 'S' 200
  Wait-InputState { (Value 'pause_choice') -eq 1 } "$mode Restart selection"
  Control 'W' 200
  Wait-InputState { (Value 'pause_choice') -eq 0 } "$mode Resume selection"
  Control 'S' 200
  Wait-InputState { (Value 'pause_choice') -eq 1 } "$mode Restart selection again"
  Control ' '
  Wait-InputState { (Value 'start_delay') -gt 0 } "$mode restart intro"
  Wait-InputState { (Value 'start_delay') -eq 0 } "$mode restart ready"
  if((Value 'lives_remaining') -ne 4) { throw 'Restart did not spend exactly one reserve' }
  $before=Value 'frame_count'; $watch=[Diagnostics.Stopwatch]::StartNew()
  Start-Sleep -Milliseconds 1500
  $rate=((256+(Value 'frame_count')-$before)%256)/$watch.Elapsed.TotalSeconds
  Write-Output ('{0}: {1:F2} updates/sec' -f $mode,$rate)
  if($rate -lt 55) { throw 'Input polling slowed the game below 55 Hz' }
  Write-Output "PASS ${mode}: four directions, ladder, exchange, pause, Restart"
  [AECPU]::Detach()
}
