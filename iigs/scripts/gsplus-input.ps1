# Helper for scripts/test-alterego.mjs: drive a running GSplus window.
#
# GSplus reads the keyboard only from its focused window, so every key press is preceded by
# SetForegroundWindow.  Actions:
#   window  - wait for the process' main window and print its handle (exit 1 on timeout)
#   focus   - bring the window to the foreground
#   <key>   - focus, then tap a key: f10, return, tab, space, left, right, up, down
param(
    [Parameter(Mandatory = $true)][int]$ProcessId,
    [Parameter(Mandatory = $true)][string]$Action,
    [int]$TimeoutSeconds = 20
)

$ErrorActionPreference = 'Stop'

if (-not ('AeGsplus' -as [type])) {
    Add-Type -Namespace AeGsplus -Name Input -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
[DllImport("user32.dll")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
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
    'f10'   = @(0x79, 0x44, $false)
    'return' = @(0x0D, 0x1C, $false)
    'tab'   = @(0x09, 0x0F, $false)
    'space' = @(0x20, 0x39, $false)
    'left'  = @(0x25, 0x4B, $true)
    'right' = @(0x27, 0x4D, $true)
    'up'    = @(0x26, 0x48, $true)
    'down'  = @(0x28, 0x50, $true)
}

if (-not $keys.ContainsKey($Action)) {
    [Console]::Error.WriteLine("unknown key '$Action'")
    exit 1
}

$vk, $scan, $extended = $keys[$Action]
$flags = if ($extended) { 1 } else { 0 }
Focus-Window | Out-Null
[AeGsplus.Input]::keybd_event($vk, $scan, $flags, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 90
[AeGsplus.Input]::keybd_event($vk, $scan, ($flags + 2), [UIntPtr]::Zero)
exit 0
