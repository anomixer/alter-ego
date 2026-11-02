iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw_lib.ps1')
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class A2F {
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
}
"@
$WM_KEYDOWN = 0x0100
$WM_KEYUP   = 0x0101
$VK_F7 = 0x70
$SC_F7 = 0x3F
function Tap([IntPtr]$h, [int]$vk, [int]$sc) {
  $down = [IntPtr]((1 -bor ($sc -shl 16)))
  # lParam: repeat count 1, scancode, no extended; for KEYUP add bit31 (transition)
  $up   = [IntPtr]([long]((1 -bor ($sc -shl 16)) -bor (1 -shl 31)))
  [A2F]::PostMessage($h, $WM_KEYDOWN, [IntPtr]$vk, $down) | Out-Null
  Start-Sleep -Milliseconds 120
  [A2F]::PostMessage($h, $WM_KEYUP,   [IntPtr]$vk, $up) | Out-Null
}
$shots = 'C:\dev\alter-ego\build\a2\shots'
$h = A2Win
if (-not $h) { Write-Host 'AppleWin not running'; return }
Write-Host "hwnd=$h  title=$((Get-Process -Name 'AppleWin*' | Select-Object -First 1).MainWindowTitle)"
Tap $h $VK_F7 $SC_F7
Start-Sleep -Seconds 3
S $h "$shots\aw_dbg.png"
Write-Host ("  aw_dbg.png  " + (HS "$shots\aw_dbg.png"))
Write-Host "  title=$((Get-Process -Name 'AppleWin*' | Select-Object -First 1).MainWindowTitle)"
