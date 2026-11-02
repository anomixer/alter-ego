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
  $up   = [IntPtr]([long](1 -bor ($sc -shl 16)) + [long]2147483648)
  [A2T]::PostMessage($h, 0x0100, [IntPtr]$vk, $down) | Out-Null
  Start-Sleep -Milliseconds 120
  [A2T]::PostMessage($h, 0x0101, [IntPtr]$vk, $up) | Out-Null
}
$shots = 'C:\dev\alter-ego\build\a2\shots'
Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 2
$p = Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList '-d1','C:\dev\alter-ego\build\a2\ae2_game.dsk','-model','apple2e','-no-full-screen','-debugger-auto-run','ae2_bp.txt' -PassThru
Start-Sleep -Seconds 5
$ap = [uint32]$p.Id
Write-Host "pid=$ap"
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
Shot2 $h "$shots\awbp_0.png" | Out-Null
Write-Host ("  t=0  " + (HS2 "$shots\awbp_0.png"))
Write-Host "-- F2 = RUN (breakpoints live) --"
Tap $h 0x71 0x43
$prev = ''
for ($i = 1; $i -le 10; $i++) {
  Start-Sleep -Seconds 3
  $h = (Get-Process -Id $p.Id -ErrorAction SilentlyContinue).MainWindowHandle
  if (-not $h) { Write-Host "  process gone at t=$($i*3)s"; break }
  Focus2 $h | Out-Null
  $f = "$shots\awbp_$i.png"
  Shot2 $h $f | Out-Null
  $hh = HS2 $f
  $t = (Get-Process -Id $p.Id -ErrorAction SilentlyContinue).MainWindowTitle
  if ($hh -ne $prev) { Write-Host ("  t={0,2}s  CHANGED  {1}  {2}" -f ($i*3), $hh, $t) }
  else { Write-Host ("  t={0,2}s  same     {1}" -f ($i*3), $hh) }
  $prev = $hh
}
