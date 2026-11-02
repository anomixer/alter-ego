Add-Type -AssemblyName System.Drawing
if (-not ('A2D' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class A2D {
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindow(string cls, string title);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECTD r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct RECTD { public int Left, Top, Right, Bottom; }
}
"@
}
function AW { return [A2D]::FindWindow("APPLE2FRAME", $null) }
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class A2E {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECTE r);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [StructLayout(LayoutKind.Sequential)] public struct RECTE { public int Left, Top, Right, Bottom; }
}
"@
function Find-AWWindows([uint32]$pid) {
  $found = New-Object System.Collections.ArrayList
  $cb = [A2E+EnumProc]{
    param($h, $l)
    if ([A2E]::IsWindowVisible($h)) {
      $sb = New-Object System.Text.StringBuilder 260
      [A2E]::GetClassName($h, $sb, 260) | Out-Null
      if ($sb.ToString() -eq 'APPLE2FRAME') {
        $p = 0; [A2E]::GetWindowThreadProcessId($h, [ref]$p) | Out-Null
        $r = New-Object A2E+RECTE
        [A2E]::GetWindowRect($h, [ref]$r) | Out-Null
        $w = $r.Right - $r.Left; $ht = $r.Bottom - $r.Top
        $t2 = New-Object System.Text.StringBuilder 260
        [A2E]::GetWindowText($h, $t2, 260) | Out-Null
        [void]$found.Add([pscustomobject]@{ Hwnd=$h; Pid=$p; W=$w; Ht=$ht; Title=$t2.ToString() })
      }
    }
    return $true
  }
  [A2E]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
  return $found
}
function AW2([uint32]$apd) {
  $all = Find-AWWindows $apd
  $best = $all | Where-Object { $_.Pid -eq $apd -and $_.W -gt 100 -and $_.Ht -gt 100 } |
          Sort-Object -Property @{Expression={$_.W * $_.Ht}; Descending=$true} |
          Select-Object -First 1
  if ($best) { return $best.Hwnd }
  return [IntPtr]::Zero
}
function Focus2([IntPtr]$h) {
  $fg = [A2D]::GetForegroundWindow()
  $p1 = 0; $t1 = [A2D]::GetWindowThreadProcessId($fg, [ref]$p1)
  $p2 = 0; $t2 = [A2D]::GetWindowThreadProcessId($h, [ref]$p2)
  $cur = [A2D]::GetCurrentThreadId()
  $a = $false; $b = $false
  if ($t1 -ne 0 -and $t1 -ne $cur) { [A2D]::AttachThreadInput($cur, $t1, $true) | Out-Null; $a = $true }
  if ($t1 -ne 0 -and $t1 -ne $t2) { [A2D]::AttachThreadInput($t2, $t1, $true) | Out-Null; $b = $true }
  if ([A2D]::IsIconic($h)) { [A2D]::ShowWindow($h, 9) | Out-Null }   # SW_RESTORE
  [A2D]::SetForegroundWindow($h) | Out-Null
  Start-Sleep -Milliseconds 200
  $ok = ([A2D]::GetForegroundWindow() -eq $h)
  if ($a) { [A2D]::AttachThreadInput($cur, $t1, $false) | Out-Null }
  if ($b) { [A2D]::AttachThreadInput($t2, $t1, $false) | Out-Null }
  return $ok
}
function Shot2([IntPtr]$h, [string]$out) {
  $r = New-Object A2D+RECTD
  [A2D]::GetWindowRect($h, [ref]$r) | Out-Null
  $w = $r.Right - $r.Left; $ht = $r.Bottom - $r.Top
  if ($w -lt 16 -or $ht -lt 16) { return $false }
  $bmp = New-Object System.Drawing.Bitmap($w, $ht)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($r.Left, $r.Top, 0, 0, $bmp.Size)
  $g.Dispose(); $bmp.Save($out); $bmp.Dispose()
  return $true
}
function HS2([string]$p) { (Get-FileHash -Algorithm SHA256 -Path $p).Hash.Substring(0,12) }
function Key([IntPtr]$h, [string]$s, [int]$gapMs = 45) {
  foreach ($ch in $s.ToCharArray()) {
    $code = if ($ch -eq "`n") { 13 } else { [int]$ch }
    [A2D]::PostMessage($h, 0x0102, [IntPtr]$code, [IntPtr]0) | Out-Null
    Start-Sleep -Milliseconds $gapMs
  }
}
