param(
  [string]$Prg = 'x16\spike\dist\LOADER.PRG',
  [string]$Root = 'x16\spike\dist',
  [int]$TitleWaitSeconds = 20,
  [string]$Stamp = 'play',
  [int]$Step1 = 8,
  [string]$KeySequence = 'enter,right:2,z,enter,enter',
  [string]$Wav = '',
  [int]$TailSeconds = 0
)
# Scripted x16emu play test.  Sends real scan-code key events (arrows also need
# the extended-key flag) and captures one screenshot per step.
#
# KeySequence grammar: comma separated "name" or "name:seconds" entries where
# name is enter, space, right, left, up, down, z, x, a, s, esc.  A direction
# with a duration is held for that many seconds, everything else is a tap.
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class PT {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, IntPtr extra);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint code, uint mapType);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
}
public struct RECT { public int Left, Top, Right, Bottom; }
"@

$scanCodes = @{
  enter = 0x0D; space = 0x20; right = 0x27; left = 0x25; up = 0x26; down = 0x28
  z = 0x5A; x = 0x58; a = 0x41; s = 0x53; w = 0x57; d = 0x44; k = 0x4B; j = 0x4A; esc = 0x1B
  t = 0x54; m = 0x4D; n = 0x4E; one = 0x31
}
$extended = @('right', 'left', 'up', 'down')

function Save-Shot([IntPtr]$h, [string]$path) {
  $rect = New-Object RECT
  [void][PT]::GetWindowRect($h, [ref]$rect)
  $bmp = New-Object System.Drawing.Bitmap ($rect.Right - $rect.Left), ($rect.Bottom - $rect.Top)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bmp.Size)
  $g.Dispose()
  $bmp.Save([System.IO.Path]::GetFullPath($path), [System.Drawing.Imaging.ImageFormat]::Png)
  $bmp.Dispose()
  Write-Host "saved $path"
}

function Send-Key([string]$name, [double]$holdSeconds) {
  Send-Keys @($name) $holdSeconds
}

# Press several keys together, hold, then release them all (e.g. right+z walks
# off a ledge with the exchange button already down).
function Send-Keys([string[]]$names, [double]$holdSeconds) {
  $down = @()
  foreach ($name in $names) {
    $vk = [int]$scanCodes[$name]
    if ($vk -eq 0) { throw "unknown key '$name'" }
    $scan = [byte][PT]::MapVirtualKey([uint32]$vk, 0)
    $flags = if ($extended -contains $name) { [uint32]1 } else { [uint32]0 }
    $down += ,@([byte]$vk, $scan, $flags)
    [PT]::keybd_event([byte]$vk, $scan, $flags, [IntPtr]::Zero)
  }
  $holdMs = if ($holdSeconds -gt 0) { [int]($holdSeconds * 1000) } else { 130 }
  Start-Sleep -Milliseconds $holdMs
  foreach ($k in $down) {
    [PT]::keybd_event($k[0], $k[1], ($k[2] -bor 2), [IntPtr]::Zero)
  }
  Start-Sleep -Milliseconds 120
}

function Focus-Emulator([IntPtr]$h) {
  # Another x16emu window (the user's own session) may own the desktop.  Force
  # ours to the top and borrow the foreground thread so SetForegroundWindow
  # takes effect; otherwise the key events and screenshots belong to it.
  [void][PT]::SetWindowPos($h, [IntPtr](-1), 40, 40, 0, 0, 0x0003)
  if ([PT]::GetForegroundWindow() -ne $h) {
    $fgPid = 0
    $fgThread = [PT]::GetWindowThreadProcessId([PT]::GetForegroundWindow(), [ref]$fgPid)
    $me = [PT]::GetCurrentThreadId()
    [void][PT]::AttachThreadInput($me, $fgThread, $true)
    [void][PT]::BringWindowToTop($h)
    [void][PT]::SetForegroundWindow($h)
    [void][PT]::AttachThreadInput($me, $fgThread, $false)
    Start-Sleep -Milliseconds 300
  }
  return ([PT]::GetForegroundWindow() -eq $h)
}

$emuDir = 'C:\dev\emu\x16emu'
$prgPath = (Resolve-Path $Prg).Path
$rootPath = (Resolve-Path $Root).Path
$emuArgs = @('-prg', $prgPath, '-run', '-fsroot', $rootPath, '-scale', '2')
if ($Wav) { $emuArgs += @('-wav', $Wav) }
Write-Host 'starting emulator'
$proc = Start-Process -FilePath (Join-Path $emuDir 'x16emu.exe') -ArgumentList $emuArgs `
  -WorkingDirectory $emuDir -RedirectStandardOutput (Join-Path $env:TEMP 'playtest-out.txt') `
  -RedirectStandardError (Join-Path $env:TEMP 'playtest-err.txt') -PassThru

Start-Sleep -Seconds 3
$proc.Refresh()
$hwnd = $proc.MainWindowHandle
Write-Host "hwnd=$hwnd"
if ($hwnd -eq [IntPtr]::Zero) { throw 'emulator window not found' }
if (-not (Focus-Emulator $hwnd)) {
  if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
  throw 'could not focus the test emulator: another x16emu window is in front (close it and retry)'
}
Write-Host "waiting $TitleWaitSeconds s for the title screen"
Start-Sleep -Seconds $TitleWaitSeconds

$step = 0
try {
foreach ($item in $KeySequence.Split(',')) {
  $parts = $item.Split(':')
  $names = @($parts[0].Trim().Split('+') | Where-Object { $_ -ne '' })
  $name = $names -join '+'
  $hold = if ($parts.Count -gt 1) { [double]$parts[1] } else { 0 }
  Write-Host "step $step key $name hold $hold"
  Send-Keys $names $hold
  $step++
  if ($name -eq 'enter' -and $step -eq 1) {
    Start-Sleep -Seconds $Step1
  } else {
    Start-Sleep -Milliseconds 900
  }
  Save-Shot $hwnd ("x16\spike\$Stamp-$step-$name.png")
}
# Let the game keep running with no keys pressed; useful for listening to what
# happens after the last input (new level music, stuck SFX voices) and for
# recordings that need a longer tail.
if ($TailSeconds -gt 0) {
  Write-Host "tail $TailSeconds s"
  Start-Sleep -Seconds $TailSeconds
  Save-Shot $hwnd ("x16\spike\$Stamp-tail.png")
}
} finally {
  # Never leave the emulator alive: its redirected stdout keeps this script's
  # pipeline open, which looks like a hang to a caller that filters the output.
  if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
}
Write-Host 'done'
