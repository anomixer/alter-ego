if (-not ('A2C' -as [type])) {
Add-Type -ReferencedAssemblies 'System.Drawing' @"
using System;
using System.Drawing;
using System.Runtime.InteropServices;
public class A2C {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern IntPtr GetWindowDC(IntPtr h);
  [DllImport("user32.dll")] public static extern int ReleaseDC(IntPtr h, IntPtr dc);
  [DllImport("gdi32.dll")] public static extern bool BitBlt(IntPtr d, int x, int y, int w, int hh, IntPtr s, int sx, int sy, int op);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int left, top, right, bottom; }

  public static string Shot(IntPtr h, string path) {
    RECT r; if (!GetWindowRect(h, out r)) return "norect";
    int w = r.right - r.left, hh = r.bottom - r.top;
    if (w < 8 || hh < 8) return "degenerate";
    string note = "pw";
    using (var bmp = new Bitmap(w, hh))
    using (var g = Graphics.FromImage(bmp)) {
      IntPtr dc = g.GetHdc();
      bool ok = PrintWindow(h, dc, 2);            // PW_RENDERFULLCONTENT
      g.ReleaseHdc(dc);
      if (!ok) {
        note = "bitblt";
        IntPtr src = GetWindowDC(h);
        IntPtr dst = g.GetHdc();
        ok = BitBlt(dst, 0, 0, w, hh, src, 0, 0, 0x00CC0020); // SRCCOPY
        g.ReleaseHdc(dst);
        ReleaseDC(h, src);
      }
      bmp.Save(path);
    }
    return note;
  }
}
"@
}
function Shot3([IntPtr]$h, [string]$path) { [A2C]::Shot($h, $path) }
function HS3([string]$path) {
  $s = [System.Security.Cryptography.SHA256]::Create()
  $bytes = [System.IO.File]::ReadAllBytes($path)
  $hex = ($s.ComputeHash($bytes) | ForEach-Object { $_.ToString('X2') }) -join ''
  $hex.Substring(0, 12)
}
