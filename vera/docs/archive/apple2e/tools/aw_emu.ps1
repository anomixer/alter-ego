# aw_emu.ps1 - resolve the AppleWin EMULATOR window handle by title.
#
# Measured this session: (Get-Process).MainWindowHandle returned the
# 'Configuration' dialog, and the 'Apple //e (original) Emulator' window is a
# separate top-level window.  Screenshots and debugger keystrokes sent to the
# main-window handle went to the dialog - which is why three builds that paint
# visibly different HGR pages produced byte-identical "screen" hashes.
#
# Drawing-free on purpose: Add-Type needs -ReferencedAssemblies 'System.Drawing'
# for Bitmap/Graphics, so window discovery stays in its own type and the capture
# itself comes from aw_cap.ps1's Shot3.
#
# Usage:
#   iex (Get-Content -Raw tools\aw_cap.ps1)
#   iex (Get-Content -Raw tools\aw_emu.ps1)
#   $h = Get-AwEmu
#   Shot3 $h 'C:\dev\alter-ego\build\a2\shots\em.png'

if (-not ('A2E' -as [type])) {
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class A2E {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
  public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
}
"@
}

function Get-AwWindows([int]$apid) {
  $script:elist = New-Object System.Collections.ArrayList
  $script:epid = [uint32]$apid
  $cb = {
    param($h, $l)
    $p = [uint32]0
    [void][A2E]::GetWindowThreadProcessId($h, [ref]$p)
    if ($p -eq $script:epid) {
      $sb = New-Object System.Text.StringBuilder 260
      [void][A2E]::GetWindowText($h, $sb, 260)
      $script:elist.Add([pscustomobject]@{ H=$h; Title=$sb.ToString();
                       Vis=[A2E]::IsWindowVisible($h) }) | Out-Null
    }
    return $true
  }
  [void][A2E]::EnumWindows($cb, [IntPtr]::Zero)
  return $script:elist
}

function Get-AwEmu([switch]$Quiet) {
  $ap = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $ap) { Write-Host 'no AppleWin process'; return $null }
  $wins = Get-AwWindows ([int]$ap.Id)
  if (-not $Quiet) {
    Write-Host "windows for pid $($ap.Id):"
    $wins | ForEach-Object { Write-Host ("   {0} vis={1} '{2}'" -f $_.H, $_.Vis, $_.Title) }
  }
  # The Configuration dialog steals focus and swallows keystrokes; close it.
  $cfg = $wins | Where-Object { $_.Title -eq 'Configuration' } | Select-Object -First 1
  if ($cfg) {
    Write-Host "closing Configuration window $($cfg.H)"
    [void][A2E]::PostMessage($cfg.H, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)   # WM_CLOSE
    Start-Sleep -Seconds 2
    $wins = Get-AwWindows ([int]$ap.Id)
  }
  $em = $wins | Where-Object { $_.Title -like 'Apple*Emulator*' } | Select-Object -First 1
  if (-not $em) { Write-Host 'no emulator window'; return $null }
  Write-Host ("emulator window = {0} vis={1} iconic={2}" -f $em.H, $em.Vis,
              [A2E]::IsIconic($em.H))
  # Measured: the emulator window is vis=False while the Configuration dialog is
  # the only visible window, and PrintWindow on a hidden window fails.  Show it.
  if (-not $em.Vis) {
    [void][A2E]::ShowWindow($em.H, 5)          # SW_SHOW
    Start-Sleep -Seconds 2
    Write-Host ("  after SW_SHOW vis={0}" -f [A2E]::IsWindowVisible($em.H))
  }
  [void][A2E]::BringWindowToTop($em.H)
  [void][A2E]::SetForegroundWindow($em.H)
  return $em.H
}
