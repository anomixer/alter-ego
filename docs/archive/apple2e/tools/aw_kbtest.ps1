iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw_cap.ps1')
if (-not ('A2S4' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class A2S4 {
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
}
"@
}
$shots = 'C:\dev\alter-ego\build\a2\shots'
$py = 'C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 2
# A plain DOS 3.3 master disk: boots to the "]" prompt, so typed keys are
# immediately visible and the injection path can be judged.
$p = Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList '-d1','C:\dev\alter-ego\build\a2\master.dsk','-model','apple2e','-no-full-screen' -PassThru
Start-Sleep -Seconds 6
Write-Host "pid=$($p.Id)"
$p = Get-Process -Id $p.Id
$h = $p.MainWindowHandle
Focus2 $h | Out-Null
Shot3 $h "$shots\awkb_0.png" | Out-Null
Write-Host ("boot  " + (HS3 "$shots\awkb_0.png"))

function TypeEm([IntPtr]$h, [string]$s) {
  foreach ($ch in $s.ToCharArray()) {
    [A2S4]::PostMessage($h, 0x0102, [IntPtr]([int]$ch), [IntPtr]0) | Out-Null
    Start-Sleep -Milliseconds 70
  }
  [A2S4]::PostMessage($h, 0x0102, [IntPtr]13, [IntPtr]0) | Out-Null
  Start-Sleep -Milliseconds 70
}

TypeEm $h 'CATALOG'
Start-Sleep -Seconds 3
$p = Get-Process -Id $p.Id
Shot3 $p.MainWindowHandle "$shots\awkb_1.png" | Out-Null
Write-Host ("after CATALOG  " + (HS3 "$shots\awkb_1.png"))
& $py -c "
from PIL import Image
im = Image.open(r'$shots\awkb_1.png').convert('RGB')
im.resize((im.width*2, im.height*2), Image.NEAREST).save(r'$shots\awkb_1_big.png')
print('ok')
"

