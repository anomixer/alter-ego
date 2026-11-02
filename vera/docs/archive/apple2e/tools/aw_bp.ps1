iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw2.ps1')
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
  $up   = [IntPtr]([long](1 -bor ($sc -shl 16)) -bor [long]([uint32]0x80000000))
  [A2T]::PostMessage($h, 0x0100, [IntPtr]$vk, $down) | Out-Null
  Start-Sleep -Milliseconds 150
  [A2T]::PostMessage($h, 0x0101, [IntPtr]$vk, $up) | Out-Null
}
$shots = 'C:\dev\alter-ego\build\a2\shots'
Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 2
$p = Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList '-d1','C:\dev\alter-ego\build\a2\ae2_game.dsk','-model','apple2e','-no-full-screen','-debugger-auto-run','C:\dev\alter-ego\build\a2\ae2_bp.txt' -PassThru
Write-Host "pid=$($p.Id)"
Start-Sleep -Seconds 3
$h = (Get-Process -Id $p.Id).MainWindowHandle
Write-Host "hwnd=$h  title='$((Get-Process -Id $p.Id).MainWindowTitle)'"
Write-Host "-- F7 (enter debugger, auto-run sets BP + G) --"
Tap $h 0x70 0x3F
$prev = ''
$t = 0
foreach ($step in 2,2,3,3,4,5,6,8,10) {
  Start-Sleep -Seconds $step
  $t += $step
  $q = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  if (-not $q) { Write-Host "t=${t}s: process gone"; break }
  $hh2 = $q.MainWindowHandle
  $f = "$shots\awbp_$t.png"
  Focus2 $hh2 | Out-Null
  if (-not (Shot2 $hh2 $f)) { Write-Host "t=${t}s capture failed"; continue }
  $hs = HS2 $f
  $mark = if ($hs -eq $prev) {'same'} else {'CHANGED'}
  Write-Host ("  t={0,3}s  {1}  {2}  {3}" -f $t, $mark, $hs, $q.MainWindowTitle)
  $prev = $hs
}
