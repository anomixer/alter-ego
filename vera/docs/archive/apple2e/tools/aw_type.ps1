iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw_cap.ps1')
if (-not ('A2K2' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class A2K2 {
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
}
"@
}
$shots = 'C:\dev\alter-ego\build\a2\shots'
$py = 'C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 2
$p = Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList '-d1','C:\dev\alter-ego\build\a2\ae2_game.dsk','-model','apple2e','-no-full-screen' -PassThru
Start-Sleep -Seconds 4
Write-Host "pid=$($p.Id)"

# Type straight into the emulated keyboard: AppleWin turns WM_CHAR into a
# keyboard strobe, so this is the same as pressing the keys on the emulated
# machine.  Used to reach the Monitor's "press a key" pause.
function TypeEm([IntPtr]$h, [string]$s) {
  foreach ($ch in $s.ToCharArray()) {
    [A2K2]::PostMessage($h, 0x0102, [IntPtr]([int]$ch), [IntPtr]0) | Out-Null
    Start-Sleep -Milliseconds 60
  }
  [A2K2]::PostMessage($h, 0x0102, [IntPtr]13, [IntPtr]0) | Out-Null
  Start-Sleep -Milliseconds 60
}

for ($i = 1; $i -le 4; $i++) {
  Start-Sleep -Seconds 4
  $p = Get-Process -Id $p.Id
  Shot3 $p.MainWindowHandle "$shots\awk_$i.png" | Out-Null
  Write-Host ("  t=$($i*4)s  " + (HS3 "$shots\awk_$i.png"))
}
$p = Get-Process -Id $p.Id
Write-Host 'sending 20 spaces'
foreach ($n in 1..20) {
  TypeEm $p.MainWindowHandle ' '
  Start-Sleep -Milliseconds 200
  $p = Get-Process -Id $p.Id
  Shot3 $p.MainWindowHandle "$shots\awk_sp.png" | Out-Null
}
Write-Host ("after spaces  " + (HS3 "$shots\awk_sp.png"))
& $py -c "
from PIL import Image
im = Image.open(r'$shots\awk_sp.png').convert('RGB')
im.resize((im.width*2, im.height*2), Image.NEAREST).save(r'$shots\awk_sp_big.png')
print('ok')
"
