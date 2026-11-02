# aw_grab.ps1 - capture a window by screen region (CopyFromScreen).
#
# PrintWindow (aw_cap.ps1's Shot3) returns "pw" - it fails - on the
# 'Apple //e (original) Emulator' window even when it is visible and foreground.
# It works on plain dialogs, which is exactly why every "screen" hash taken
# through MainWindowHandle while the Configuration dialog was open was a hash of
# the dialog: three builds that paint visibly different HGR pages produced
# byte-identical hashes.
#
# CopyFromScreen grabs pixels off the desktop, so it needs the window visible and
# on top.  aw_emu.ps1 closes the dialog and raises the emulator window.
#
# Usage:
#   iex (Get-Content -Raw tools\aw_emu.ps1)
#   iex (Get-Content -Raw tools\aw_grab.ps1)
#   $h = Get-AwEmu
#   AwGrab $h 'C:\dev\alter-ego\build\a2\shots\em.png'

Add-Type -ReferencedAssemblies 'System.Drawing' @"
using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.IO;
public class A2G {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECTZ r);
  public struct RECTZ { public int Left, Top, Right, Bottom; }

  public static string Grab(IntPtr h, string path) {
    RECTZ r = new RECTZ();
    if (!GetWindowRect(h, out r)) return "norect";
    int w = r.Right - r.Left, hh = r.Bottom - r.Top;
    if (w < 8 || hh < 8) return "size:" + w + "x" + hh;
    using (Bitmap bmp = new Bitmap(w, hh)) {
      using (Graphics g = Graphics.FromImage(bmp)) {
        g.CopyFromScreen(r.Left, r.Top, 0, 0, bmp.Size);
      }
      bmp.Save(path);
    }
    using (var fs = File.OpenRead(path)) {
      var sha = new System.Security.Cryptography.SHA256Managed();
      byte[] b = sha.ComputeHash(fs);
      return BitConverter.ToString(b).Replace("-","").Substring(0,12);
    }
  }
}
"@

function AwGrab([IntPtr]$h, [string]$path) {
  return [A2G]::Grab($h, $path)
}
