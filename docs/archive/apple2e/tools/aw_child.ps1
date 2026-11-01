# aw_child.ps1 - PrintWindow the emulator window AND each of its child windows.
#
# Chain of measured facts:
#   - MainWindowHandle was the 'Configuration' dialog, so every Shot3 hash taken
#     through it was the dialog, not the screen.  Three builds painting visibly
#     different HGR pages produced byte-identical hashes.
#   - PrintWindow on the 'Apple //e (original) Emulator' window returns false
#     ("pw") even when it is visible and foreground.
#   - CopyFromScreen fails on this host with "The handle is invalid".
# AppleWin draws the video into a child window, so the child is the surface worth
# capturing.  This tries the parent and every child, and reports which succeed.
#
# Usage:
#   iex (Get-Content -Raw tools\aw_emu.ps1)
#   iex (Get-Content -Raw tools\aw_child.ps1)
#   $h = Get-AwEmu -Quiet
#   AwChildShots $h 'C:\dev\alter-ego\build\a2\shots'

Add-Type -ReferencedAssemblies 'System.Drawing' @"
using System;
using System.Text;
using System.Drawing;
using System.Runtime.InteropServices;
using System.IO;
public class A2C {
  public delegate bool EnumChildProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr p, EnumChildProc cb, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECTZ r);
  public struct RECTZ { public int Left, Top, Right, Bottom; }
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);

  public static string Shot(IntPtr h, string path) {
    RECTZ r = new RECTZ();
    if (!GetWindowRect(h, out r)) return "norect";
    int w = r.Right - r.Left, hh = r.Bottom - r.Top;
    if (w < 8 || hh < 8) return "size:" + w + "x" + hh;
    using (Bitmap bmp = new Bitmap(w, hh)) {
      using (Graphics g = Graphics.FromImage(bmp)) {
        IntPtr dc = g.GetHdc();
        bool ok = PrintWindow(h, dc, 2);
        g.ReleaseHdc(dc);
        if (!ok) return "pw-fail";
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

function AwChildShots([IntPtr]$parent, [string]$dir) {
  $list = New-Object System.Collections.ArrayList
  $cb = {
    param($h, $l)
    $sb = New-Object System.Text.StringBuilder 260
    [void][A2C]::GetClassName($h, $sb, 260)
    $list.Add([pscustomobject]@{ H=$h; Class=$sb.ToString() }) | Out-Null
    return $true
  }
  [void][A2C]::EnumChildWindows($parent, $cb, [IntPtr]::Zero)
  Write-Host ("children: {0}" -f $list.Count)
  $list | ForEach-Object { Write-Host ("   {0}  {1}" -f $_.H, $_.Class) }

  $r = New-Object A2C+RECTZ
  [void][A2C]::GetWindowRect($parent, [ref]$r)
  Write-Host ("parent rect {0}x{1}" -f ($r.Right-$r.Left), ($r.Bottom-$r.Top))
  Write-Host ("  parent  " + [A2C]::Shot($parent, "$dir\ch_parent.png"))
  $i = 0
  foreach ($c in $list) {
    $i++
    Write-Host ("  child{0} {1}  " -f $i, $c.Class + [A2C]::Shot($c.H, "$dir\ch$i.png"))
  }
}
