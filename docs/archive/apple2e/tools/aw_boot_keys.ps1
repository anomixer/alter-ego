iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw_cap.ps1')
if (-not ('A2S5' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class A2S5 {
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
$prev = ''
for ($i = 1; $i -le 6; $i++) {
  Start-Sleep -Seconds 3
  $p = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  if (-not $p) { Write-Host '  gone'; break }
  $f = "$shots\awz_$i.png"
  Shot3 $p.MainWindowHandle $f | Out-Null
  $hs = HS3 $f
  $tag = if ($hs -eq $prev) { 'same   ' } else { 'CHANGED' }
  Write-Host "  t=$($i*3)s  $tag  $hs"
  $prev = $hs
}
# The credits screen waits on a keypress; send a run of them.
$p = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
if ($p) {
  $h = $p.MainWindowHandle
  Focus2 $h | Out-Null
  foreach ($code in (32, 13, 32, 32, 13, 32, 32, 32, 13, 32)) {
    [A2S5]::PostMessage($h, 0x0102, [IntPtr]$code, [IntPtr]0) | Out-Null
    Start-Sleep -Milliseconds 250
  }
  Start-Sleep -Seconds 4
  $p = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  if ($p) {
    Shot3 $p.MainWindowHandle "$shots\awz_keys.png" | Out-Null
    Write-Host ("after keys  " + (HS3 "$shots\awz_keys.png"))
    & $py -c "
from PIL import Image
for nm in ('awz_3', 'awz_keys'):
    im = Image.open(rf'$shots\{nm}.png').convert('RGB')
    im.resize((im.width*2, im.height*2), Image.NEAREST).save(rf'$shots\{nm}_big.png')
print('ok')
"
  }
}
