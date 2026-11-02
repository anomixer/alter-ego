Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class PW {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT3 r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [StructLayout(LayoutKind.Sequential)] public struct RECT3 { public int Left, Top, Right, Bottom; }
}
"@
function Grab([IntPtr]$h, [string]$out) {
  $r = New-Object PW+RECT3
  [PW]::GetWindowRect($h, [ref]$r) | Out-Null
  $w = $r.Right - $r.Left; $ht = $r.Bottom - $r.Top
  if ($w -lt 8 -or $ht -lt 8) { Write-Host "  too small ${w}x${ht}"; return }
  $bmp = New-Object System.Drawing.Bitmap($w, $ht)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $hdc = $g.GetHdc()
  # flag 2 = PW_RENDERFULLCONTENT: renders DirectDraw/GDI content even when occluded
  $ok = [PW]::PrintWindow($h, $hdc, 2)
  $g.ReleaseHdc($hdc)
  $g.Dispose()
  $bmp.Save($out)
  $bmp.Dispose()
  Write-Host "  PrintWindow=$ok saved $(Split-Path $out -Leaf) ${w}x${ht}"
}
$q = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $q) { Write-Host 'AppleWin not running'; return }
Write-Host "pid=$($q.Id) hwnd=$($q.MainWindowHandle)"
Grab $q.MainWindowHandle 'C:\dev\alter-ego\build\a2\shots\aw_pw.png'
