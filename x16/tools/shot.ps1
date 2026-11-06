# Capture the x16emu window to a PNG (no emulator cooperation needed).
#   -Prg <prg>     load and autostart a program
#   -FsRoot <dir>  boot normally with HostFS pointed at <dir> (AUTOBOOT.X16 runs)
param(
    [string]$Prg,
    [string]$FsRoot,
    [string]$Bas,
    [Parameter(Mandatory = $true)][string]$Out,
    [int]$WaitSeconds = 4,
    [string]$EmuDir = 'C:\dev\emu\x16emu',
    [int]$Scale = 1
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr after, int x, int y, int cx, int cy, uint flags);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int cmd);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    public struct RECT { public int Left, Top, Right, Bottom; }
}
"@

if (-not $Prg -and -not $FsRoot -and -not $Bas) { throw 'one of -Prg, -FsRoot or -Bas is required' }
$Out = [System.IO.Path]::GetFullPath($Out)
New-Item -ItemType Directory -Force -Path (Split-Path $Out) | Out-Null

$args = @('-scale', "$Scale")
if ($Prg) { $args += @('-prg', (Resolve-Path $Prg).Path, '-run') }
if ($FsRoot) { $args += @('-fsroot', (Resolve-Path $FsRoot).Path) }
if ($Bas) { $args += @('-bas', (Resolve-Path $Bas).Path, '-run') }

# x16emu is a console program: launched normally, its terminal window (Windows
# Terminal on this host, which cannot be hidden with ShowWindow) sits on top of
# the emulated screen and would end up in the capture.  -WindowStyle Hidden
# leaves only the SDL window, which is found by title instead of MainWindowHandle.
$logOut = Join-Path $env:TEMP 'x16emu.out.txt'
$logErr = Join-Path $env:TEMP 'x16emu.err.txt'
$p = Start-Process -FilePath (Join-Path $EmuDir 'x16emu.exe') `
    -ArgumentList $args -WorkingDirectory $EmuDir `
    -RedirectStandardOutput $logOut -RedirectStandardError $logErr -PassThru

try {
    # The emulated screen is the top-level window that belongs to x16emu's own
    # PID; the stdout console belongs to the terminal host and is never matched.
    $hwnd = [IntPtr]::Zero
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 250
        if ($p.HasExited) { throw "x16emu exited early (exit code $($p.ExitCode))" }
        $script:found = [IntPtr]::Zero
        $script:targetPid = [uint32]$p.Id
        $cb = [Win32+EnumProc]{
            param([IntPtr]$h, [IntPtr]$l)
            $pid2 = [uint32]0
            [void][Win32]::GetWindowThreadProcessId($h, [ref]$pid2)
            if ($pid2 -eq $script:targetPid -and [Win32]::IsWindowVisible($h)) {
                $rr = New-Object Win32+RECT
                if ([Win32]::GetWindowRect($h, [ref]$rr)) {
                    if (($rr.Right - $rr.Left) -gt 300 -and ($rr.Bottom - $rr.Top) -gt 200) {
                        $script:found = $h
                        return $false
                    }
                }
            }
            return $true
        }
        [void][Win32]::EnumWindows($cb, [IntPtr]::Zero)
        $hwnd = $script:found
        if ($hwnd -ne [IntPtr]::Zero) { break }
    }
    if ($hwnd -eq [IntPtr]::Zero) { throw 'x16emu did not create its window' }

    Start-Sleep -Seconds $WaitSeconds
    # Park the window so the capture never races a window-manager animation
    # and never falls off-screen (SWP_NOSIZE | SWP_NOZORDER).
    # HWND_TOPMOST: x16emu is a console program and its terminal window would
    # otherwise sit on top and be captured instead of the emulated screen.
    # SWP_NOSIZE only: SWP_NOZORDER would cancel the HWND_TOPMOST request.
    [Win32]::SetWindowPos($hwnd, [IntPtr](-1), 40, 40, 0, 0, 0x0001) | Out-Null
    [Win32]::SetForegroundWindow($hwnd) | Out-Null
    Start-Sleep -Milliseconds 400

    $r = New-Object Win32+RECT
    if (-not [Win32]::GetWindowRect($hwnd, [ref]$r)) { throw 'GetWindowRect failed' }
    $w = $r.Right - $r.Left
    $h = $r.Bottom - $r.Top
    if ($w -le 0 -or $h -le 0) { throw "bad window size ${w}x${h}" }

    $bmp = New-Object System.Drawing.Bitmap $w, $h
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($r.Left, $r.Top, 0, 0, $bmp.Size)
    $g.Dispose()
    $bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    "saved $Out (${w}x${h}) after $WaitSeconds s"
}
finally {
    if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
}
