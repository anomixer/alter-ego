iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw_cap.ps1')
$shots = 'C:\dev\alter-ego\build\a2\shots'
$py = 'C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 2
$p = Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList '-d1','C:\dev\alter-ego\build\a2\ae2_game.dsk','-model','apple2e','-no-full-screen' -PassThru
Start-Sleep -Seconds 4
Write-Host "pid=$($p.Id)"
$prev = ''
for ($i = 1; $i -le 10; $i++) {
  Start-Sleep -Seconds 3
  $p = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  if (-not $p) { Write-Host '  gone'; break }
  $f = "$shots\awn_$i.png"
  Shot3 $p.MainWindowHandle $f | Out-Null
  $hs = HS3 $f
  $tag = if ($hs -eq $prev) { 'same   ' } else { 'CHANGED' }
  Write-Host "  t=$($i*3)s  $tag  $hs"
  $prev = $hs
}
$p = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
if ($p) {
  Shot3 $p.MainWindowHandle "$shots\awn_last.png" | Out-Null
  & $py -c "
from PIL import Image
im = Image.open(r'$shots\awn_last.png').convert('RGB')
im.resize((im.width*2, im.height*2), Image.NEAREST).save(r'$shots\awn_last_big.png')
print('ok')
"
}
