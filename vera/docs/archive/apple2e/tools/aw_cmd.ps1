param([string[]]$Cmds = @('PC'), [int]$HangSec = 12)
$cmdFile = 'C:\dev\alter-ego\build\a2\dbg_cmds.txt'
if (Test-Path $cmdFile) {
  $Cmds = @(Get-Content $cmdFile | Where-Object { $_ -match '\S' })
  Write-Host ("commands from file: " + $Cmds.Count)
}
iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw2.ps1')
iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw_cap.ps1')   # Shot3 / HS3
if (-not ('A2T' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class A2T {
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
}
"@
}
function Tap([IntPtr]$h, [int]$vk, [int]$sc) {
  $down = [IntPtr](1 -bor ($sc -shl 16))
  $up   = [IntPtr]([long](1 -bor ($sc -shl 16)) + [long]2147483648)
  [A2T]::PostMessage($h, 0x0100, [IntPtr]$vk, $down) | Out-Null
  Start-Sleep -Milliseconds 120
  [A2T]::PostMessage($h, 0x0101, [IntPtr]$vk, $up) | Out-Null
}
function DbgCmd([IntPtr]$h, [string]$cmd) {
  foreach ($ch in $cmd.ToCharArray()) {
    [A2T]::PostMessage($h, 0x0102, [IntPtr]([int]$ch), [IntPtr]0) | Out-Null
    Start-Sleep -Milliseconds 30
  }
  Start-Sleep -Milliseconds 200
  Tap $h 0x0D 0x1C
  Start-Sleep -Milliseconds 400
  for ($i = 0; $i -lt 4; $i++) { Tap $h 0x20 0x39 }
  Start-Sleep -Milliseconds 300
}
$shots = 'C:\dev\alter-ego\build\a2\shots'
Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 2
$p = Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList '-d1','C:\dev\alter-ego\build\a2\ae2_game.dsk','-model','apple2e','-no-full-screen' -PassThru
Start-Sleep -Seconds 4
$ap = [uint32]$p.Id
Write-Host "pid=$ap"
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
Start-Sleep -Seconds $HangSec
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
Tap $h 0x76 0x3F
Start-Sleep -Seconds 3
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
foreach ($c in $Cmds) { DbgCmd $h $c }
# Shot2/HS2 (CopyFromScreen) fails on this host with "The handle is invalid" and
# silently returns a stale frame, so every screenshot taken here was the boot
# frame.  Shot3 (PrintWindow with PW_RENDERFULLCONTENT) is the path that
# measurably captures the live window.
Shot3 $h "$shots\awc3.png" | Out-Null
Write-Host ("  awc3.png " + (HS3 "$shots\awc3.png"))
