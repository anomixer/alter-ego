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
$py = 'C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'

# Breakpoints armed by the debugger's auto-run file before the machine starts.
Set-Content -Path 'C:\dev\applewin\ae2_bp.txt' -Encoding ASCII -Value @(
  'BP $7DA9',   # _main
  'BP $8688',   # _lv_load
  'BP $8792',   # _lv_fail_halt
  'BP $C2B0',   # the runaway address seen in the register panel
  'BP $04FF'    # DOS 3.3's CSW hook
)
Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 2
$p = Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList @(
    '-d1','C:\dev\alter-ego\build\a2\ae2_game.dsk','-model','apple2e','-no-full-screen',
    '-debugger-auto-run','ae2_bp.txt') -PassThru
Start-Sleep -Seconds 4
Write-Host "pid=$($p.Id)"
$h = $p.MainWindowHandle
Focus2 $h | Out-Null
Start-Sleep -Seconds 2
Tap $h 0x71 0x43          # F2 = RUN
for ($i = 1; $i -le 8; $i++) {
  Start-Sleep -Seconds 4
  $p2 = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  if (-not $p2) { Write-Host '  gone'; break }
  $h = $p2.MainWindowHandle
  Focus2 $h | Out-Null
  $f = "$shots\awb_$i.png"
  Shot2 $h $f | Out-Null
  $hs = HS2 $f
  Write-Host ("  t=$($i*4)s  $hs")
  if ($i -eq 3 -or $i -eq 6) {
    & $py -c "
from PIL import Image
im = Image.open(r'$f').convert('RGB')
im.crop((0, 0, 631, 431)).resize((631*2, 431*2), Image.NEAREST).save(r'$shots\awb_$i\_big.png')
" 2>$null
  }
}
