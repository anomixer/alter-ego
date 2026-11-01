iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw2.ps1')
$shots = 'C:\dev\alter-ego\build\a2\shots'
Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 2
$p = Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList '-d1','C:\dev\alter-ego\build\a2\ae2_game.dsk','-model','apple2e','-no-full-screen' -PassThru
Write-Host "pid=$($p.Id)"
$prev = ''
$t = 0
foreach ($step in 2,2,2,3,3,4,6,8,10,10) {
  Start-Sleep -Seconds $step
  $t += $step
  $q = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  if (-not $q) { Write-Host "t=${t}s: process gone"; break }
  $h = $q.MainWindowHandle
  if (-not $h) { Write-Host "t=${t}s: no window"; continue }
  $f = "$shots\awb_$t.png"
  Focus2 $h | Out-Null
  $ok = Shot2 $h $f
  if (-not $ok) { Write-Host "t=${t}s: capture failed"; continue }
  $hh = HS2 $f
  $mark = if ($hh -eq $prev) {'same'} else {'CHANGED'}
  Write-Host ("  t={0,3}s  {1}  {2}  {3}" -f $t, $mark, $hh, $q.MainWindowTitle)
  $prev = $hh
}
