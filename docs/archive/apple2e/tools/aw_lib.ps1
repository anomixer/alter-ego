Add-Type -AssemblyName System.Drawing
if (-not ('A2K' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class A2K {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECTK r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct RECTK { public int Left, Top, Right, Bottom; }
}
"@
}
function K([IntPtr]$h, [string]$s, [int]$gapMs = 45) {
  foreach ($ch in $s.ToCharArray()) {
    $code = if ($ch -eq "`n") { 13 } elseif ($ch -eq "^J") { 10 } else { [int]$ch }
    [A2K]::PostMessage($h, 0x0102, [IntPtr]$code, [IntPtr]0) | Out-Null
    Start-Sleep -Milliseconds $gapMs
  }
}
function S([IntPtr]$h, [string]$out) {
  $r = New-Object A2K+RECTK
  [A2K]::GetWindowRect($h, [ref]$r) | Out-Null
  $w = $r.Right - $r.Left; $ht = $r.Bottom - $r.Top
  $bmp = New-Object System.Drawing.Bitmap($w, $ht)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $hdc = $g.GetHdc(); [A2K]::PrintWindow($h, $hdc, 2) | Out-Null; $g.ReleaseHdc($hdc)
  $g.Dispose(); $bmp.Save($out); $bmp.Dispose()
}
function HS([string]$p) { (Get-FileHash -Algorithm SHA256 -Path $p).Hash.Substring(0,12) }
function A2Win {
  $q = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $q) { return $null }
  return $q.MainWindowHandle
}
