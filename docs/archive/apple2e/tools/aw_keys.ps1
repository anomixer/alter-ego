iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw2.ps1')
if (-not ('A2K' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class A2K {
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
  Start-Sleep -Seconds 4
  $p2 = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  if (-not $p2) { Write-Host '  gone'; break }
  $h = $p2.MainWindowHandle
  Focus2 $h | Out-Null
  $f = "$shots\awkey_$i.png"
  Shot2 $h $f | Out-Null
  $hs = HS2 $f
  $tag = if ($hs -eq $prev) { 'same   ' } else { 'CHANGED' }
  Write-Host "  t=$($i*4)s  $tag  $hs"
  $prev = $hs
  # Press SPACE, then a few letters: the credits/title screens wait on KEYIN.
  foreach ($code in @(32, 13, 32)) {
    [A2K]::PostMessage($h, 0x0102, [IntPtr]$code, [IntPtr]0) | Out-Null
    Start-Sleep -Milliseconds 250
  }
}
& $py -c "
from PIL import Image
im = Image.open(r'$shots\awkey_6.png').convert('RGB')
im.resize((im.width*2, im.height*2), Image.NEAREST).save(r'$shots\awkey_6_big.png')
print('ok')
"
