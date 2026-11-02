# aw_dump.ps1 - launch AppleWin, open the debugger, run debugger commands, report.
#
# Everything this session had to learn the hard way, in one place:
#   - MainWindowHandle is the 'Configuration' dialog, not the emulator.  Close it.
#   - The emulator window is a separate top-level window, found by title.
#   - F7 is a main-window accelerator: post it to the EMULATOR window.
#   - The debugger window opens with an EMPTY title and vis=False.  Show it
#     (SW_SHOW) before typing, or the keystrokes go nowhere.
#   - BSAVE writes RAW bytes into AppleWin's current directory, which follows the
#     -d1 disk's folder, so run with -WorkingDirectory build\a2 and read files
#     from there.
#   - PrintWindow works on the emulator window (aw_child.ps1's A2C::Shot);
#     CopyFromScreen fails on this host.
#
# Usage:
#   iex (Get-Content -Raw tools\aw_dump.ps1)
#   Invoke-AwDump @('BSAVE "ae2_hgr.bin",$2000,$1E00')

iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw_emu.ps1')
iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw_child.ps1')

function Invoke-AwDump([string[]]$Cmds, [int]$BootSec = 10, [int]$HangSec = 4) {
  $ap = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $ap) { Write-Host 'no AppleWin process'; return $null }
  $apid = [int]$ap.Id

  $em = Get-AwEmu -Quiet
  if (-not $em) { Write-Host 'no emulator window'; return $null }
  Start-Sleep -Seconds $BootSec

  # F7 on the emulator window toggles the debugger.
  $down = [IntPtr](1 -bor (0x3F -shl 16))
  $up   = [IntPtr]([long](1 -bor (0x3F -shl 16)) + [long]2147483648)
  [void][A2E]::PostMessage($em, 0x0100, [IntPtr]0x76, $down)
  Start-Sleep -Milliseconds 150
  [void][A2E]::PostMessage($em, 0x0101, [IntPtr]0x76, $up)
  Start-Sleep -Seconds 3

  $dbg = Get-AwWindows $apid | Where-Object { $_.Title -eq '' } | Select-Object -First 1
  if (-not $dbg) { Write-Host 'no debugger window'; return $null }
  Write-Host "debugger window $($dbg.H) vis=$($dbg.Vis)"
  [void][A2E]::ShowWindow($dbg.H, 5)          # SW_SHOW - required
  Start-Sleep -Seconds 1
  [void][A2E]::BringWindowToTop($dbg.H)
  [void][A2E]::SetForegroundWindow($dbg.H)
  Start-Sleep -Seconds 1
  $dbg = $dbg.H

  foreach ($c in $Cmds) {
    foreach ($ch in $c.ToCharArray()) {
      [void][A2E]::PostMessage($dbg, 0x0102, [IntPtr]([int]$ch), [IntPtr]0)
      Start-Sleep -Milliseconds 25
    }
    Start-Sleep -Milliseconds 300
    $d = [IntPtr](1 -bor (0x1C -shl 16)); $u = [IntPtr]([long](1 -bor (0x1C -shl 16)) + [long]2147483648)
    [void][A2E]::PostMessage($dbg, 0x0100, [IntPtr]0x0D, $d)
    Start-Sleep -Milliseconds 120
    [void][A2E]::PostMessage($dbg, 0x0101, [IntPtr]0x0D, $u)
    Start-Sleep -Milliseconds 400
    for ($i = 0; $i -lt 4; $i++) {
      $sd = [IntPtr](1 -bor (0x39 -shl 16)); $su = [IntPtr]([long](1 -bor (0x39 -shl 16)) + [long]2147483648)
      [void][A2E]::PostMessage($dbg, 0x0100, [IntPtr]0x20, $sd)
      Start-Sleep -Milliseconds 100
      [void][A2E]::PostMessage($dbg, 0x0101, [IntPtr]0x20, $su)
    }
    Start-Sleep -Seconds 1
  }
  Start-Sleep -Seconds $HangSec
  return $dbg
}
