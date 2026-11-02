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
Write-Host "-- F2 = RUN --"
Tap $h 0x71 0x43
Start-Sleep -Seconds 10
$h = (Get-Process -Id $p.Id).MainWindowHandle
$tt = (Get-Process -Id $p.Id).MainWindowTitle
Write-Host "  title: $tt"
Focus2 $h | Out-Null
Shot2 $h "$shots\awq_run.png" | Out-Null
Write-Host ("  awq_run.png " + (HS2 "$shots\awq_run.png"))
Write-Host "-- F7 = debugger --"
Tap $h 0x76 0x3F
Start-Sleep -Seconds 3
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
Shot2 $h "$shots\awq_dbg.png" | Out-Null
Write-Host ("  awq_dbg.png " + (HS2 "$shots\awq_dbg.png"))
# crop the register panel (PC)
$py='C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
& $py -c "
from PIL import Image
im = Image.open(r'build\a2\shots\awq_dbg.png').convert('RGB')
im.crop((330, 60, 470, 210)).resize((140*6, 150*6), Image.NEAREST).save(r'build\a2\shots\awq_regs.png')
im.crop((0, 60, 340, 300)).resize((340*3, 240*3), Image.NEAREST).save(r'build\a2\shots\awq_dis.png')
print('crops saved')
"
