iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw2.ps1')
$shots = 'C:\dev\alter-ego\build\a2\shots'
$p = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $p) { Write-Host 'no AppleWin running'; return }
$h = $p.MainWindowHandle
Focus2 $h | Out-Null
Shot2 $h "$shots\awlive.png" | Out-Null
Write-Host ("awlive.png " + (HS2 "$shots\awlive.png"))
$py='C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
& $py -c "
from PIL import Image
im=Image.open(r'$shots\awlive.png').convert('RGB')
im.resize((im.width*2, im.height*2), Image.NEAREST).save(r'$shots\awlive_big.png')
print('ok')
"
