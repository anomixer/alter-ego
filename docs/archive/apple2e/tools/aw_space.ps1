iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw_cap.ps1')
if (-not ('A2S8' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class A2S8 {
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
}
"@
}
function Tap([IntPtr]$h, [int]$vk, [int]$sc) {
  $down = [IntPtr](1 -bor ($sc -shl 16))
  $up   = [IntPtr]([long](1 -bor ($sc -shl 16)) + [long]2147483648)
  [A2S8]::PostMessage($h, 0x0100, [IntPtr]$vk, $down) | Out-Null
  Start-Sleep -Milliseconds 120
  [A2S8]::PostMessage($h, 0x0101, [IntPtr]$vk, $up) | Out-Null
}
function Char([IntPtr]$h, [int]$code) {
  [A2S8]::PostMessage($h, 0x0102, [IntPtr]$code, [IntPtr]0) | Out-Null
  Start-Sleep -Milliseconds 120
}
$shots = 'C:\dev\alter-ego\build\a2\shots'
$py = 'C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 2
$p = Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList '-d1','C:\dev\alter-ego\build\a2\ae2_game.dsk','-model','apple2e','-no-full-screen' -PassThru
Start-Sleep -Seconds 4
Write-Host "pid=$($p.Id)"
$h = $p.MainWindowHandle
Focus2 $h | Out-Null
Start-Sleep -Seconds 12
$p = Get-Process -Id $p.Id
$h = $p.MainWindowHandle
Focus2 $h | Out-Null
Shot3 $h "$shots\awi_0.png" | Out-Null
Write-Host ("live  " + (HS3 "$shots\awi_0.png"))

# Feed the emulated keyboard.  The Monitor's text pause wants SPACE; the game's
# own pad poll wants a key too, so send a generous run of them.
for ($i = 0; $i -lt 40; $i++) { Char $h 32 }
Start-Sleep -Seconds 3
$p = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
if ($p) {
  Shot3 $p.MainWindowHandle "$shots\awi_1.png" | Out-Null
  Write-Host ("after 40 SPACE  " + (HS3 "$shots\awi_1.png"))
  for ($i = 0; $i -lt 20; $i++) { Char $h 13 }
  Start-Sleep -Seconds 3
  $p = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  if ($p) {
    Shot3 $p.MainWindowHandle "$shots\awi_2.png" | Out-Null
    Write-Host ("after 20 CR     " + (HS3 "$shots\awi_2.png"))
    & $py -c "
from PIL import Image
for nm in ('awi_0', 'awi_1', 'awi_2'):
    im = Image.open(rf'$shots\{nm}.png').convert('RGB')
    im.resize((im.width*2, im.height*2), Image.NEAREST).save(rf'$shots\{nm}_big.png')
print('ok')
"
  }
}
