Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W2 {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT2 r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern IntPtr FindWindow(string cls, string title);
  [StructLayout(LayoutKind.Sequential)] public struct RECT2 { public int Left, Top, Right, Bottom; }
}
"@
function Get-Shot2([IntPtr]$h, [string]$out) {
  $r = New-Object W2+RECT2
  [W2]::GetWindowRect($h, [ref]$r) | Out-Null
  $w = $r.Right - $r.Left; $ht = $r.Bottom - $r.Top
  if ($w -lt 8 -or $ht -lt 8) { Write-Host "  window too small: ${w}x${ht}"; return }
  $bmp = New-Object System.Drawing.Bitmap($w, $ht)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($r.Left, $r.Top, 0, 0, $bmp.Size)
  $bmp.Save($out)
  $g.Dispose(); $bmp.Dispose()
  Write-Host "  saved $(Split-Path $out -Leaf)  ${w}x${ht}"
}
$dsk = 'C:\dev\alter-ego\build\a2\ae2_game.dsk'
$shotDir = 'C:\dev\alter-ego\build\a2\shots'
$p = Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList '-d1', $dsk, '-model', 'apple2e', '-no-full-screen' -PassThru
for ($i = 1; $i -le 40; $i++) {
  Start-Sleep -Milliseconds 250
  $q = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  if (-not $q) { Write-Host "t=$($i*0.25)s: process gone"; break }
  if ($q.MainWindowHandle -ne 0) {
    Write-Host "t=$($i*0.25)s title='$($q.MainWindowTitle)'"
    [W2]::SetForegroundWindow($q.MainWindowHandle) | Out-Null
    Get-Shot2 $q.MainWindowHandle "$shotDir\aw_boot.png"
    break
  }
}
"pid=$($p.Id)"
