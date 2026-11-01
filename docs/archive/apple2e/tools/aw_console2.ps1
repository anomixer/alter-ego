iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw2.ps1')
if (-not ('A2T' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
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
# The debugger console only accepts chars 32..126 via WM_CHAR; Enter must be a
# real VK_RETURN keydown (Debug.cpp:9555 drops everything below 32).
function DbgCmd([IntPtr]$h, [string]$cmd) {
  foreach ($ch in $cmd.ToCharArray()) {
    [A2T]::PostMessage($h, 0x0102, [IntPtr]([int]$ch), [IntPtr]0) | Out-Null
    Start-Sleep -Milliseconds 30
  }
  Start-Sleep -Milliseconds 200
  Tap $h 0x0D 0x1C          # VK_RETURN, scan 0x1C
  Start-Sleep -Milliseconds 400
  # the console pages long output: "press SPACE continue, ESC skip"
  for ($i = 0; $i -lt 4; $i++) { Tap $h 0x20 0x39 }
  Start-Sleep -Milliseconds 300
}
$dir = 'C:\dev\alter-ego\build\a2\dbg'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Remove-Item "$dir\*.bin" -Force -ErrorAction SilentlyContinue
$shots = 'C:\dev\alter-ego\build\a2\shots'
Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 2
$p = Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList '-d1','C:\dev\alter-ego\build\a2\ae2_game.dsk','-model','apple2e','-no-full-screen' -PassThru
Start-Sleep -Seconds 4
$ap = [uint32]$p.Id
Write-Host "pid=$ap"
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
Write-Host "-- boot + hang (12 s) --"
Start-Sleep -Seconds 12
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
Write-Host "-- F7 -> debugger --"
Tap $h 0x76 0x3F
Start-Sleep -Seconds 3
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
DbgCmd $h 'PC'
DbgCmd $h 'BSAVE "ae2_zp.bin",0:100'
DbgCmd $h 'BSAVE "ae2_lo.bin",0:200'
DbgCmd $h 'BSAVE "ae2_code6000.bin",6000:1000'
DbgCmd $h 'BSAVE "ae2_code8800.bin",8800:200'
DbgCmd $h 'BSAVE "ae2_scr2000.bin",2000:400'
DbgCmd $h 'BSAVE "ae2_lc.bin",D000:1000'
Shot2 $h "$shots\awc2.png" | Out-Null
Write-Host ("  awc2.png " + (HS2 "$shots\awc2.png"))
Write-Host "--- dumped ---"
Get-ChildItem "$dir\*.bin" -ErrorAction SilentlyContinue | ForEach-Object { "  $($_.Name)  $($_.Length) B" }
