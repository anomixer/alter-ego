Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
function Get-Shot([IntPtr]$h, [string]$out) {
  $r = New-Object W+RECT
  [W]::GetWindowRect($h, [ref]$r) | Out-Null
  $w = $r.Right - $r.Left; $ht = $r.Bottom - $r.Top
  if ($w -lt 8 -or $ht -lt 8) { Write-Host "window too small: ${w}x${ht}"; return }
  $bmp = New-Object System.Drawing.Bitmap($w, $ht)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($r.Left, $r.Top, 0, 0, $bmp.Size)
  $bmp.Save($out)
  $g.Dispose(); $bmp.Dispose()
  Write-Host "saved $out  ${w}x${ht}  at ($($r.Left),$($r.Top))"
}
$p = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $p) { Write-Host 'AppleWin not running'; return }
Write-Host "pid=$($p.Id) title='$($p.MainWindowTitle)' hwnd=$($p.MainWindowHandle)"
Write-Host "foreground=$([W]::GetForegroundWindow()) iconic=$([W]::IsIconic($p.MainWindowHandle))"
[W]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 400
Get-Shot $p.MainWindowHandle 'C:\dev\alter-ego\build\a2\shots\aw_launch.png'
