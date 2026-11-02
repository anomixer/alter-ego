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
function Tap([IntPtr]$h, [int]$vk, [int]$sc) {
  $down = [IntPtr](1 -bor ($sc -shl 16))
  $up   = [IntPtr]([long](1 -bor ($sc -shl 16)) + [long]2147483648)
  [A2T]::PostMessage($h, 0x0100, [IntPtr]$vk, $down) | Out-Null
  Start-Sleep -Milliseconds 150
  [A2T]::PostMessage($h, 0x0101, [IntPtr]$vk, $up) | Out-Null
}
function TypeDbg([IntPtr]$h, [string]$s, [int]$gapMs = 35) {
  foreach ($ch in $s.ToCharArray()) {
    $code = if ($ch -eq "`n") { 13 } else { [int]$ch }
    [A2T]::PostMessage($h, 0x0102, [IntPtr]$code, [IntPtr]0) | Out-Null
    Start-Sleep -Milliseconds $gapMs
  }
}
$out = 'C:\dev\alter-ego\build\a2\dbg'
New-Item -ItemType Directory -Force -Path $out | Out-Null
Get-ChildItem "$out\*.bin" -ErrorAction SilentlyContinue | Remove-Item -Force
$shots = 'C:\dev\alter-ego\build\a2\shots'
Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 2
$p = Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList '-d1','C:\dev\alter-ego\build\a2\ae2_game.dsk','-model','apple2e','-no-full-screen' -PassThru
Start-Sleep -Seconds 4
$ap = [uint32]$p.Id
Write-Host "pid=$ap"
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
Write-Host "-- let it boot and hang (12 s) --"
Start-Sleep -Seconds 12
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
Write-Host "-- F7 -> debugger --"
Tap $h 0x76 0x3F
Start-Sleep -Seconds 3
$h = (Get-Process -Id $p.Id).MainWindowHandle
Focus2 $h | Out-Null
Write-Host "-- debugger console commands --"
TypeDbg $h "pc`n"
Start-Sleep -Milliseconds 400
TypeDbg $h "bsave ""$out\zp.bin"",0:100`n"
Start-Sleep -Milliseconds 600
TypeDbg $h "bsave ""$out\code8800.bin"",8800:100`n"
Start-Sleep -Milliseconds 600
TypeDbg $h "bsave ""$out\scr2000.bin"",2000:200`n"
Start-Sleep -Milliseconds 600
Shot2 $h "$shots\awc_dbg.png" | Out-Null
Write-Host ("  awc_dbg.png " + (HS2 "$shots\awc_dbg.png"))
Write-Host "--- dumped files ---"
Get-ChildItem "$out\*.bin" -ErrorAction SilentlyContinue | ForEach-Object { "  $($_.Name)  $($_.Length) B" }
