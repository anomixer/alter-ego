iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw2.ps1')
if (-not ('A2T' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class A2T {
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECTZ r);
  [StructLayout(LayoutKind.Sequential)] public struct RECTZ { public int Left, Top, Right, Bottom; }
}
"@
}
$script:AW_TARGET = 0
$script:AW_LIST = New-Object System.Collections.ArrayList
$_cb = [A2T+EnumProc]{ param($h,$l)
  if ([A2T]::IsWindowVisible($h)) {
    $p = 0; [A2T]::GetWindowThreadProcessId($h, [ref]$p) | Out-Null
    if ($p -eq $script:AW_TARGET) {
      $sb = New-Object System.Text.StringBuilder 300
      [A2T]::GetWindowText($h, $sb, 300) | Out-Null
      $r = New-Object A2T+RECTZ
      [A2T]::GetWindowRect($h, [ref]$r) | Out-Null
      [void]$script:AW_LIST.Add([pscustomobject]@{ Hwnd=$h; W=($r.Right-$r.Left); Ht=($r.Bottom-$r.Top); Title=$sb.ToString() })
    }
  }
  return $true
}
function List-Win([uint32]$target) {
  $script:AW_TARGET = $target
  $script:AW_LIST = New-Object System.Collections.ArrayList
  [A2T]::EnumWindows($_cb, [IntPtr]::Zero) | Out-Null
  return $script:AW_LIST
}
function Tap([IntPtr]$h, [int]$vk, [int]$sc) {
  $down = [IntPtr](1 -bor ($sc -shl 16))
  $up   = [IntPtr]([long](1 -bor ($sc -shl 16)) + [long]2147483648)
  [A2T]::PostMessage($h, 0x0100, [IntPtr]$vk, $down) | Out-Null
  Start-Sleep -Milliseconds 150
  [A2T]::PostMessage($h, 0x0101, [IntPtr]$vk, $up) | Out-Null
}
$shots = 'C:\dev\alter-ego\build\a2\shots'
Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 2
$p = Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList '-d1','C:\dev\alter-ego\build\a2\ae2_game.dsk','-model','apple2e','-no-full-screen','-debugger-auto-run','ae2_bp.txt' -PassThru
Start-Sleep -Seconds 4
$ap = [uint32]$p.Id
Write-Host "pid=$ap"
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
Tap $h 0x70 0x3F
Write-Host "F7 sent"
$prev = ''
$t = 0
foreach ($step in 2,2,3,3,4,5,6,8,10) {
  Start-Sleep -Seconds $step
  $t += $step
  $q = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  if (-not $q) { Write-Host "t=${t}s: process gone"; break }
  $wins = List-Win $ap
  $dbg = $wins | Where-Object { $_.Title -like '*Emulator for Windows*' } | Select-Object -First 1
  $em  = $wins | Where-Object { $_.Title -like '*Emulator -*' } | Select-Object -First 1
  $target = if ($dbg) { $dbg } else { $em }
  if (-not $target) { Write-Host "t=${t}s: no window"; continue }
  $f = "$shots\awd_$t.png"
  Focus2 $target.Hwnd | Out-Null
  if (-not (Shot2 $target.Hwnd $f)) { Write-Host "t=${t}s capture failed"; continue }
  $hs = HS2 $f
  $mark = if ($hs -eq $prev) {'same'} else {'CHANGED'}
  $kind = if ($dbg) { 'DEBUGGER' } else { 'screen' }
  Write-Host ("  t={0,3}s  {1}  {2}  [{3}] {4}" -f $t, $mark, $hs, $kind, $target.Title)
  $prev = $hs
}
