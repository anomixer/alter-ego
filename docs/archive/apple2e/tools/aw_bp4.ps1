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
Tap $h 0x71 0x43          # F2 = RUN
Start-Sleep -Seconds 10
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
for ($i = 1; $i -le 4; $i++) {
  Tap $h 0x76 0x3F        # F7
  Start-Sleep -Seconds 2
  $h = (Get-Process -Id $p.Id).MainWindowHandle
  Focus2 $h | Out-Null
  $f = "$shots\awr_$i.png"
  Shot2 $h $f | Out-Null
  $t = (Get-Process -Id $p.Id).MainWindowTitle
  Write-Host ("  F7 x{0}  {1}  {2}" -f $i, (HS2 $f), $t)
}
$py='C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
& $py -c "
from PIL import Image
im = Image.open(r'build\a2\shots\awr_4.png').convert('RGB')
im.crop((330, 60, 470, 210)).resize((140*6, 150*6), Image.NEAREST).save(r'build\a2\shots\awr_regs.png')
print('ok')
"
