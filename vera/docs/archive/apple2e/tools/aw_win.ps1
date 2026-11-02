# List every top-level window owned by a process (default: the running AppleWin).
param([int]$TargetPid = 0)
if ($TargetPid -eq 0) {
  $ap = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $ap) { Write-Host 'no AppleWin process'; return }
  $TargetPid = $ap.Id
}
if (-not ('A2W' -as [type])) {
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class A2W {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
  public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}
"@
}
$script:found = New-Object System.Collections.ArrayList
$script:tpid = [uint32]$TargetPid
$cb = {
  param($h, $l)
  $pid2 = [uint32]0
  [void][A2W]::GetWindowThreadProcessId($h, [ref]$pid2)
  if ($pid2 -eq $script:tpid) {
    $sb = New-Object System.Text.StringBuilder 260
    [void][A2W]::GetWindowText($h, $sb, 260)
    $script:found.Add(("{0}  vis={1} fg={2}  '{3}'" -f $h, [A2W]::IsWindowVisible($h),
                        ([A2W]::GetForegroundWindow() -eq $h), $sb.ToString())) | Out-Null
  }
  return $true
}
[void][A2W]::EnumWindows($cb, [IntPtr]::Zero)
Write-Host "pid=$TargetPid windows=$($script:found.Count)"
$script:found | ForEach-Object { Write-Host $_ }
