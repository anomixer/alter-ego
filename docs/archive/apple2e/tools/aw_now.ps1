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
$p = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $p) { Write-Host 'no AppleWin'; return }
Write-Host "pid=$($p.Id)"
$h = $p.MainWindowHandle
Focus2 $h | Out-Null
Tap $h 0x76 0x3F
Start-Sleep -Seconds 3
$p = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
$h = $p.MainWindowHandle
Focus2 $h | Out-Null
Shot2 $h "$shots\awpc_now.png" | Out-Null
Write-Host ("awpc_now " + (HS2 "$shots\awpc_now.png"))
& $py -c "
from PIL import Image
im = Image.open(r'$shots\awpc_now.png').convert('RGB')
im.crop((330, 60, 470, 210)).resize((140*6, 150*6), Image.NEAREST).save(r'$shots\awpc_now_regs.png')
im.crop((0, 60, 340, 300)).resize((340*3, 240*3), Image.NEAREST).save(r'$shots\awpc_now_dis.png')
print('crops ok')
"
