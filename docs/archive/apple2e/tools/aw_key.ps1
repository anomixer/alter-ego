Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class A2 {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT5 r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct RECT5 { public int Left, Top, Right, Bottom; }
}
"@
$WM_CHAR = 0x0102
function Send-A2([IntPtr]$h, [string]$s) {
  foreach ($ch in $s.ToCharArray()) {
    if ($ch -eq "`n") { $code = 13 } else { $code = [int]$ch }
    [A2]::PostMessage($h, $WM_CHAR, [IntPtr]$code, [IntPtr]0) | Out-Null
    Start-Sleep -Milliseconds 45
  }
}
function Grab([IntPtr]$h, [string]$out) {
  $r = New-Object A2+RECT5
  [A2]::GetWindowRect($h, [ref]$r) | Out-Null
  $w = $r.Right - $r.Left; $ht = $r.Bottom - $r.Top
  $bmp = New-Object System.Drawing.Bitmap($w, $ht)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $hdc = $g.GetHdc(); [A2]::PrintWindow($h, $hdc, 2) | Out-Null; $g.ReleaseHdc($hdc)
  $g.Dispose(); $bmp.Save($out); $bmp.Dispose()
}
$shots = 'C:\dev\alter-ego\build\a2\shots'
$q = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $q) { Write-Host 'AppleWin not running'; return }
$h = $q.MainWindowHandle
Write-Host "pid=$($q.Id) hwnd=$h"
Write-Host "sending: catalog"
Send-A2 $h "catalog`n"
Start-Sleep -Seconds 3
Grab $h "$shots\aw_catalog.png"
Write-Host "  saved aw_catalog.png"
