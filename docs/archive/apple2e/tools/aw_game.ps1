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
$WM_CHAR_K = 0x0102
function K([IntPtr]$h, [string]$s, [int]$gapMs = 45) {
  foreach ($ch in $s.ToCharArray()) {
    $code = if ($ch -eq "`n") { 13 } else { [int]$ch }
    [A2K]::PostMessage($h, $WM_CHAR_K, [IntPtr]$code, [IntPtr]0) | Out-Null
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
function H([string]$p) { (Get-FileHash -Algorithm SHA256 -Path $p).Hash.Substring(0,12) }
$shots = 'C:\dev\alter-ego\build\a2\shots'
$q = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $q) { Write-Host 'AppleWin not running'; return }
$h = $q.MainWindowHandle
Write-Host "pid=$($q.Id) hwnd=$h"
# clear the line first in case a partial command is sitting at the prompt
K $h "`n"
Start-Sleep -Seconds 1
Write-Host "sending: brun ae2game"
K $h "brun ae2game`n"
$prev = ''
for ($i = 1; $i -le 12; $i++) {
  Start-Sleep -Seconds 2
  $f = "$shots\aw_g_$i.png"
  S $h $f
  $hh = H $f
  $mark = if ($hh -eq $prev) { 'same' } else { 'CHANGED' }
  Write-Host ("  t={0,2}s  {1}  {2}" -f ($i*2), $mark, $hh)
  $prev = $hh
}
