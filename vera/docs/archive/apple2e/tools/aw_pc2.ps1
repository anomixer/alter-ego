iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw_cap.ps1')
if (-not ('A2S3' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class A2S3 {
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
}
"@
}
# PostMessage of WM_KEYDOWN reaches the window proc, and AppleWin's accelerator
# table is consulted for the posted message; measured to open the debugger.
function Tap([IntPtr]$h, [int]$vk, [int]$sc) {
  $down = [IntPtr](1 -bor ($sc -shl 16))
  $up   = [IntPtr]([long](1 -bor ($sc -shl 16)) + [long]2147483648)
  [A2S3]::PostMessage($h, 0x0100, [IntPtr]$vk, $down) | Out-Null
  Start-Sleep -Milliseconds 150
  [A2S3]::PostMessage($h, 0x0101, [IntPtr]$vk, $up) | Out-Null
}
function DbgCmd([IntPtr]$h, [string]$cmd) {
  foreach ($ch in $cmd.ToCharArray()) {
    [A2S3]::PostMessage($h, 0x0102, [IntPtr]([int]$ch), [IntPtr]0) | Out-Null
    Start-Sleep -Milliseconds 30
  }
  Start-Sleep -Milliseconds 200
  Tap $h 0x0D 0x1C
  Start-Sleep -Milliseconds 400
  for ($i = 0; $i -lt 4; $i++) { Tap $h 0x20 0x39 }
  Start-Sleep -Milliseconds 300
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
Start-Sleep -Seconds 14
$p = Get-Process -Id $p.Id
$h = $p.MainWindowHandle
Focus2 $h | Out-Null
Tap $h 0x76 0x3F
Start-Sleep -Seconds 3
$p = Get-Process -Id $p.Id
$h = $p.MainWindowHandle
Focus2 $h | Out-Null
Shot3 $h "$shots\awq_a.png" | Out-Null
Write-Host ("after F7  " + (HS3 "$shots\awq_a.png") + "  title=[" + $p.MainWindowTitle + "]")
DbgCmd $h 'PC'
Shot3 $h "$shots\awq_b.png" | Out-Null
Write-Host ("after PC  " + (HS3 "$shots\awq_b.png"))
& $py -c "
from PIL import Image
for nm in ('awq_a', 'awq_b'):
    im = Image.open(rf'$shots\{nm}.png').convert('RGB')
    im.crop((330, 60, 470, 210)).resize((140*6, 150*6), Image.NEAREST).save(rf'$shots\{nm}_regs.png')
    im.crop((0, 200, 631, 431)).resize((631*2, 231*2), Image.NEAREST).save(rf'$shots\{nm}_con.png')
print('crops ok')
"
