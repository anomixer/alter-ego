# Page through the AppleWin debugger's `help` output and capture every page.
#
# The debugger prints "...press SPACE continue, ESC skip..." between pages, so
# the full command reference is only visible by pressing SPACE repeatedly.
# Capture with Shot3 (PrintWindow): Shot2/CopyFromScreen fails on this host with
# "The handle is invalid" and silently returns a stale frame.
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
  Start-Sleep -Milliseconds 150
  [A2S8]::PostMessage($h, 0x0101, [IntPtr]$vk, $up) | Out-Null
}
function DbgCmd([IntPtr]$h, [string]$cmd) {
  foreach ($ch in $cmd.ToCharArray()) {
    [A2S8]::PostMessage($h, 0x0102, [IntPtr]([int]$ch), [IntPtr]0) | Out-Null
    Start-Sleep -Milliseconds 30
  }
  Start-Sleep -Milliseconds 200
  Tap $h 0x0D 0x1C
  Start-Sleep -Milliseconds 500
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
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
Tap $h 0x76 0x3F
Start-Sleep -Seconds 3
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
DbgCmd $h 'help'
for ($i = 1; $i -le 10; $i++) {
  Shot3 $h "$shots\awh_p$i.png" | Out-Null
  Write-Host ("  page $i " + (HS3 "$shots\awh_p$i.png"))
  Tap $h 0x20 0x39
  Start-Sleep -Milliseconds 400
}
& $py -c "
from PIL import Image
for i in range(1, 11):
    p = r'$shots\awh_p%d.png' % i
    im = Image.open(p).convert('RGB')
    im.crop((0, 190, 631, 431)).resize((631*2, 241*2), Image.NEAREST).save(r'$shots\awh_pc%d.png' % i)
print('ok')
"
