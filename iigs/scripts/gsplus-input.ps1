# Helper for scripts/test-alterego.mjs: drive a running GSplus window.
#
# Actions:
#   window  - wait for the process' main window and print its handle (exit 1 on timeout)
#   focus   - bring the window to the foreground
#   <key>   - tap a key: f1-f12, return, tab, space, escape, left, right, up, down, or a single
#             letter / digit (q, y, n, r, 1, ...)
#
# The key is delivered as WM_KEYDOWN/WM_KEYUP posted to the emulator's window, not with
# keybd_event: a posted message goes straight to GSplus and does not depend on which window Windows
# considers active or on the system's modifier state, while keybd_event only reaches the emulated
# keyboard when this process manages to activate the window first (SetForegroundWindow is refused
# while another program owns the foreground) and it is easy to leave Caps Lock or a modifier latched
# from an earlier run.  The window is still activated first, because GSplus ignores keyboard input
# from a window that does not have the keyboard focus.
param(
    [Parameter(Mandatory = $true)][int]$ProcessId,
    [Parameter(Mandatory = $true)][string]$Action,
    [int]$TimeoutSeconds = 20
)

$ErrorActionPreference = 'Stop'

if (-not ('AeGsplus' -as [type])) {
    Add-Type -Namespace AeGsplus -Name Input -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
[DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);
[DllImport("user32.dll")] public static extern uint MapVirtualKey(uint uCode, uint uMapType);
'@
}

$proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
if (-not $proc) { [Console]::Error.WriteLine("no process with id $ProcessId"); exit 1 }

function Get-Handle([int]$timeoutSeconds) {
    $deadline = [DateTime]::UtcNow.AddSeconds($timeoutSeconds)
    do {
        $p = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($p -and $p.MainWindowHandle -ne [IntPtr]::Zero) { return $p.MainWindowHandle }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    return [IntPtr]::Zero
}

function Focus-Window {
    $handle = Get-Handle -timeoutSeconds $TimeoutSeconds
    if ($handle -eq [IntPtr]::Zero) { [Console]::Error.WriteLine('GSplus window never appeared'); exit 1 }
    [AeGsplus.Input]::SetForegroundWindow($handle) | Out-Null
    Start-Sleep -Milliseconds 150
    return $handle
}

if ($Action -eq 'window') {
    $handle = Get-Handle -timeoutSeconds $TimeoutSeconds
    if ($handle -eq [IntPtr]::Zero) { [Console]::Error.WriteLine('GSplus window never appeared'); exit 1 }
    Write-Output ('0x{0:X}' -f $handle.ToInt64())
    exit 0
}

if ($Action -eq 'focus') {
    $handle = Focus-Window
    Write-Output ('0x{0:X}' -f $handle.ToInt64())
    exit 0
}

# virtual-key code, scan code, extended-key flag
$keys = @{
    'f10'    = @(0x79, 0x44, $false)
    'return' = @(0x0D, 0x1C, $false)
    'tab'    = @(0x09, 0x0F, $false)
    'space'  = @(0x20, 0x39, $false)
    'escape' = @(0x1B, 0x01, $false)
    'left'   = @(0x25, 0x4B, $true)
    'right'  = @(0x27, 0x4D, $true)
    'up'     = @(0x26, 0x48, $true)
    'down'   = @(0x28, 0x50, $true)
}

# A single letter or digit: VK is the ASCII code of its upper-case form, the scan code comes from
# the keyboard layout table.
if (-not $keys.ContainsKey($Action) -and $Action -match '^[a-z0-9]$') {
    $vk = [byte]([int][char]$Action.ToUpperInvariant())
    $keys[$Action] = @($vk, [int][AeGsplus.Input]::MapVirtualKey($vk, 0), $false)
}

# F1-F12: VK $70-$7B.
if (-not $keys.ContainsKey($Action) -and $Action -match '^f([1-9]|1[0-2])$') {
    $vk = [byte](0x70 + [int]$Action.Substring(1) - 1)
    $keys[$Action] = @($vk, [int][AeGsplus.Input]::MapVirtualKey($vk, 0), $false)
}

if (-not $keys.ContainsKey($Action)) {
    [Console]::Error.WriteLine("unknown key '$Action'")
    exit 1
}

$vk, $scan, $extended = $keys[$Action]
$handle = Focus-Window
$bits = [int64]$scan -shl 16
if ($extended) { $bits = $bits -bor (1 -shl 24) }

# WM_KEYDOWN / WM_KEYUP, with the repeat count in the low word and the transition bits of the keyup
# message set (bit 30 "was down", bit 31 "released").
$down = [IntPtr]($bits -bor 1)
$up = [IntPtr]($bits -bor 1 -bor (1 -shl 30) -bor (1 -shl 31))
[AeGsplus.Input]::PostMessage($handle, 0x0100, [IntPtr]$vk, $down) | Out-Null
Start-Sleep -Milliseconds 60
[AeGsplus.Input]::PostMessage($handle, 0x0101, [IntPtr]$vk, $up) | Out-Null
exit 0
