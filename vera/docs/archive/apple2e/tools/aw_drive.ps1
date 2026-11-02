Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class KD {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT4 r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
  [StructLayout(LayoutKind.Sequential)] public struct RECT4 { public int Left, Top, Right, Bottom; }
}
"@
function Grab([IntPtr]$h, [string]$out) {
  $r = New-Object KD+RECT4
  [KD]::GetWindowRect($h, [ref]$r) | Out-Null
  $w = $r.Right - $r.Left; $ht = $r.Bottom - $r.Top
  $bmp = New-Object System.Drawing.Bitmap($w, $ht)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $hdc = $g.GetHdc(); [KD]::PrintWindow($h, $hdc, 2) | Out-Null; $g.ReleaseHdc($hdc)
  $g.Dispose(); $bmp.Save($out); $bmp.Dispose()
  Write-Host "  saved $(Split-Path $out -Leaf) ${w}x${ht}"
}
function Focus([IntPtr]$h) {
  $fg = [KD]::GetForegroundWindow()
  $fgPid = 0; $fgTid = [KD]::GetWindowThreadProcessId($fg, [ref]$fgPid)
  $myPid = 0; $myTid = [KD]::GetWindowThreadProcessId($h, [ref]$myPid)
  $cur = [KD]::GetCurrentThreadId()
  if ($fgTid -ne $cur) { [KD]::AttachThreadInput($cur, $fgTid, $true) | Out-Null }
  if ($fgTid -ne $myTid) { [KD]::AttachThreadInput($myTid, $fgTid, $true) | Out-Null }
  [KD]::SetForegroundWindow($h) | Out-Null
  Start-Sleep -Milliseconds 250
  $ok = ([KD]::GetForegroundWindow() -eq $h)
  Write-Host "  focus=$ok"
  return $ok
}
$shots = 'C:\dev\alter-ego\build\a2\shots'
$q = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $q) { Write-Host 'AppleWin not running'; return }
$h = $q.MainWindowHandle
Write-Host "pid=$($q.Id) hwnd=$h"
Focus $h | Out-Null
# DOS prompt: run the game
[System.Windows.Forms.SendKeys]::SendWait("brun ae2game{ENTER}")
Write-Host "sent: brun ae2game"
foreach ($t in 2,4,8,16) {
  Start-Sleep -Seconds $t
  Grab $h "$shots\aw_run_$t.png"
}
