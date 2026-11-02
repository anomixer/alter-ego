Add-Type -AssemblyName System.Drawing
if (-not ('A2C' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class A2C {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECTC r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct RECTC { public int Left, Top, Right, Bottom; }
}
"@
}
function FocusWin([IntPtr]$h) {
  $fg = [A2C]::GetForegroundWindow()
  $p1 = 0; $t1 = [A2C]::GetWindowThreadProcessId($fg, [ref]$p1)
  $p2 = 0; $t2 = [A2C]::GetWindowThreadProcessId($h, [ref]$p2)
  $cur = [A2C]::GetCurrentThreadId()
  if ($t1 -ne $cur) { [A2C]::AttachThreadInput($cur, $t1, $true) | Out-Null }
  if ($t1 -ne $t2) { [A2C]::AttachThreadInput($t2, $t1, $true) | Out-Null }
  [A2C]::ShowWindow($h, 5) | Out-Null      # SW_SHOW
  [A2C]::SetForegroundWindow($h) | Out-Null
  Start-Sleep -Milliseconds 300
  $ok = ([A2C]::GetForegroundWindow() -eq $h)
  if ($t1 -ne $cur) { [A2C]::AttachThreadInput($cur, $t1, $false) | Out-Null }
  if ($t1 -ne $t2) { [A2C]::AttachThreadInput($t2, $t1, $false) | Out-Null }
  return $ok
}
function Shot([IntPtr]$h, [string]$out) {
  $r = New-Object A2C+RECTC
  [A2C]::GetWindowRect($h, [ref]$r) | Out-Null
  $w = $r.Right - $r.Left; $ht = $r.Bottom - $r.Top
  $bmp = New-Object System.Drawing.Bitmap($w, $ht)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($r.Left, $r.Top, 0, 0, $bmp.Size)
  $g.Dispose(); $bmp.Save($out); $bmp.Dispose()
}
function HS([string]$p) { (Get-FileHash -Algorithm SHA256 -Path $p).Hash.Substring(0,12) }
$shots = 'C:\dev\alter-ego\build\a2\shots'
$q = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $q) { Write-Host 'AppleWin not running'; return }
$h = $q.MainWindowHandle
Write-Host "pid=$($q.Id) hwnd=$h title='$($q.MainWindowTitle)'"
Write-Host ("focus=" + (FocusWin $h))
Shot $h "$shots\aw_cfs_1.png"; Write-Host ("  cfs1=" + (HS "$shots\aw_cfs_1.png"))
Start-Sleep -Seconds 2
Write-Host ("focus=" + (FocusWin $h))
Shot $h "$shots\aw_cfs_2.png"; Write-Host ("  cfs2=" + (HS "$shots\aw_cfs_2.png"))
