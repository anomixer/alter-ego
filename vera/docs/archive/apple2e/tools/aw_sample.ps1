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
$py = 'C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 2
$p = Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList '-d1','C:\dev\alter-ego\build\a2\ae2_game.dsk','-model','apple2e','-no-full-screen' -PassThru
Start-Sleep -Seconds 4
$ap = [uint32]$p.Id
Write-Host "pid=$ap"
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
Start-Sleep -Seconds 10
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
Tap $h 0x76 0x3F
Start-Sleep -Seconds 3
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
DbgCmd $h 'PC=6000'
DbgCmd $h 'G'
for ($i = 1; $i -le 3; $i++) {
  Start-Sleep -Seconds 6
  $h = (Get-Process -Id $p.Id).MainWindowHandle
  Focus2 $h | Out-Null
  Tap $h 0x76 0x3F
  Start-Sleep -Seconds 2
  $h = (Get-Process -Id $p.Id).MainWindowHandle
  Focus2 $h | Out-Null
  $f = "$shots\aws_$i.png"
  Shot2 $h $f | Out-Null
  & $py -c "
from PIL import Image
im = Image.open(r'$f').convert('RGB')
im.crop((330, 60, 470, 210)).resize((140*6, 150*6), Image.NEAREST).save(r'$shots\aws_r$i.png')
im.crop((330, 230, 631, 300)).resize((301*4, 70*4), Image.NEAREST).save(r'$shots\aws_cyc$i.png')
"
  Write-Host ("  sample $i -> aws_r$i.png aws_cyc$i.png")
  Tap $h 0x76 0x3F          # leave debugger, keep running
  Start-Sleep -Seconds 2
}
