iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw_lib.ps1')
$shots = 'C:\dev\alter-ego\build\a2\shots'
$h = A2Win
if (-not $h) { Write-Host 'AppleWin not running'; return }
Write-Host "hwnd=$h"
Write-Host "--- 3x CR (13) ---"
for ($i = 0; $i -lt 3; $i++) { [A2K]::PostMessage($h, 0x0102, [IntPtr]13, [IntPtr]0) | Out-Null; Start-Sleep -Milliseconds 250 }
Start-Sleep -Seconds 2
S $h "$shots\aw_cr13.png"; "  aw_cr13.png  " + (HS "$shots\aw_cr13.png")
Write-Host "--- 3x Ctrl-J (10) ---"
for ($i = 0; $i -lt 3; $i++) { [A2K]::PostMessage($h, 0x0102, [IntPtr]10, [IntPtr]0) | Out-Null; Start-Sleep -Milliseconds 250 }
Start-Sleep -Seconds 2
S $h "$shots\aw_ctrlj.png"; "  aw_ctrlj.png  " + (HS "$shots\aw_ctrlj.png")
Write-Host "--- type 'catalog' then CR ---"
K $h "catalog" 70
Start-Sleep -Milliseconds 500
[A2K]::PostMessage($h, 0x0102, [IntPtr]13, [IntPtr]0) | Out-Null
Start-Sleep -Seconds 4
S $h "$shots\aw_cat2.png"; "  aw_cat2.png  " + (HS "$shots\aw_cat2.png")
