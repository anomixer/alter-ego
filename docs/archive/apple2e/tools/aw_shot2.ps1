# aw_shot2.ps1 - capture the AppleWin EMULATOR window, found by title.
#
# Measured this session: (Get-Process).MainWindowHandle returned the
# 'Configuration' dialog; the 'Apple //e (original) Emulator' window is a
# separate top-level window.  Every hash taken through the main-window handle was
# the dialog, not the screen - which is why three builds that paint visibly
# different HGR pages produced byte-identical "screen" hashes.
#
# Usage:
#   iex (Get-Content -Raw tools\aw_shot2.ps1)
#   $h = Get-AwEmu
#   AwShot $h out.png

Add-Type -AssemblyName System.Drawing

if (-not ('A2S' -as [type])) {
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
using System.Drawing;
using System.IO;
public class A2S {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
  public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECTZ r);
  [StructLayout(LayoutKind.Sequential)] public struct RECTZ { public int Left, Top, Right, Bottom; }
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);

  public static string Shot(IntPtr h, string path) {
    RECTZ r = new RECTZ();
    if (!GetWindowRect(h, out r)) return "norect";
    int w = r.Right - r.Left, ht = r.Bottom - r.Top;
    if (w < 8 || ht < 8) return "size:" + w + "x" + ht;
    using (Bitmap bmp = new Bitmap(w, ht)) {
      using (Graphics g = Graphics.FromImage(bmp)) {
        IntPtr hdc = g.GetHdc();
        bool ok = PrintWindow(h, hdc, 2);   // PW_RENDERFULLCONTENT
        g.ReleaseHdc(hdc);
        if (!ok) return "printwindow-failed";
      }
      bmp.Save(path);   // GDI+ infers the format from the .png extension
    }
    using (var fs = File.OpenRead(path)) {
      var sha = new System.Security.Cryptography.SHA256Managed();
      byte[] b = sha.ComputeHash(fs);
      return BitConverter.ToString(b).Replace("-","").Substring(0,12);
    }
  }
}
"@
}

function Get-AwEmu {
  $ap = Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $ap) { Write-Host 'no AppleWin process'; return $null }
  $script:slist = New-Object System.Collections.ArrayList
  $script:spid = [uint32]$ap.Id
  $cb = {
    param($h, $l)
    $p = [uint32]0
    [void][A2S]::GetWindowThreadProcessId($h, [ref]$p)
    if ($p -eq $script:spid) {
      $sb = New-Object System.Text.StringBuilder 260
      [void][A2S]::GetWindowText($h, $sb, 260)
      $script:slist.Add([pscustomobject]@{ H=$h; Title=$sb.ToString();
                       Vis=[A2S]::IsWindowVisible($h) }) | Out-Null
    }
    return $true
  }
  [void][A2S]::EnumWindows($cb, [IntPtr]::Zero)
  Write-Host "windows for pid $($ap.Id):"
  $script:slist | ForEach-Object { Write-Host ("   {0} vis={1} '{2}'" -f $_.H, $_.Vis, $_.Title) }
  $em = $script:slist | Where-Object { $_.Title -like 'Apple*Emulator*' } | Select-Object -First 1
  if (-not $em) { Write-Host 'no emulator window'; return $null }
  Write-Host ("emulator window = {0}" -f $em.H)
  return $em.H
}

function AwShot([IntPtr]$h, [string]$path) {
  return [A2S]::Shot($h, $path)
}
