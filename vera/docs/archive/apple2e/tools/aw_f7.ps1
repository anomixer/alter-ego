iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw2.ps1')
if (-not ('A2T' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class A2T3 {
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
}
"@
}
function Tap([IntPtr]$h, [int]$vk, [int]$sc) {
  $down = [IntPtr](1 -bor ($sc -shl 16))
  $up   = [IntPtr]([long](1 -bor ($sc -shl 16)) + [long]2147483648)
  [A2T3]::PostMessage($h, 0x0100, [IntPtr]$vk, $down) | Out-Null
  Start-Sleep -Milliseconds 150
  [A2T3]::PostMessage($h, 0x0101, [IntPtr]$vk, $up) | Out-Null
}
$shots = 'C:\dev\alter-ego\build\a2\shots'
$py = 'C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$p = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $p) { Write-Host 'no AppleWin'; return }
Write-Host "pid=$($p.Id) title=[$($p.MainWindowTitle)]"
for ($i = 1; $i -le 4; $i++) {
  $p = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
  $h = $p.MainWindowHandle
  Focus2 $h | Out-Null
  Tap $h 0x76 0x3F
  Start-Sleep -Seconds 2
  $p = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
  $h = $p.MainWindowHandle
  Focus2 $h | Out-Null
  $f = "$shots\awf7_$i.png"
  Shot2 $h $f | Out-Null
  Write-Host ("  try $i  " + (HS2 $f) + "  title=[" + $p.MainWindowTitle + "]")
  & $py -c "
from PIL import Image
im = Image.open(r'$f').convert('RGB')
im.crop((330, 60, 470, 210)).resize((140*6, 150*6), Image.NEAREST).save(r'$shots\awf7_${i}_regs.png')
"
}
