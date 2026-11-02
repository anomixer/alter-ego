$ErrorActionPreference = 'Continue'
$log = 'C:\dev\alter-ego\build\a2\awrun.log'
$png = 'C:\dev\alter-ego\build\a2\aw_screen.png'
function L($m) { Add-Content -Path $log -Value ("{0:HH:mm:ss.fff}  {1}" -f (Get-Date), $m) }
Set-Content -Path $log -Value "=== AppleWin helper ==="

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

$sources = @'
using System;using System.Text;using System.Collections.Generic;using System.Runtime.InteropServices;
public class G{
 [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lp, IntPtr l);
 public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
 [StructLayout(LayoutKind.Sequential)] public struct R{public int l,t,r,b;}
 public static IntPtr FindMain(){ IntPtr f=IntPtr.Zero;
  EnumWindows((h,l)=>{ uint p=0; GetWindowThreadProcessId(h, out p);
   if(IsWindowVisible(h)){ var cn=new StringBuilder(128); GetClassName(h,cn,128);
    if(cn.ToString()=="APPLE2FRAME") f=h; } return true; }, IntPtr.Zero); return f; }
 public static List<string> All(){ var o=new List<string>();
  EnumWindows((h,l)=>{ if(IsWindowVisible(h)){ var cn=new StringBuilder(128); GetClassName(h,cn,128);
    var sb=new StringBuilder(256); GetWindowText(h,sb,256);
    if(cn.ToString()=="APPLE2FRAME" || cn.ToString()=="#32770") o.Add("h="+h+" "+cn+" \""+sb+"\""); } return true; }, IntPtr.Zero);
  return o; }
 public static string Rect(IntPtr h){ R r; GetWindowRect(h, out r); return r.l+","+r.t+" "+(r.r-r.l)+"x"+(r.b-r.t); }
}
'@
Add-Type -TypeDefinition $sources

L("visible windows: " + ([G]::All() -join '  |  '))

$h = [G]::FindMain()
L("AppleWin window = $h  rect=" + [G]::Rect($h))
if ($h -eq [IntPtr]::Zero) { L("no emulator window; abort"); exit 1 }

[void][G]::SetForegroundWindow($h)
[void][G]::BringWindowToTop($h)
Start-Sleep -Milliseconds 400
L("foreground now = " + [G]::GetForegroundWindow())

$sh = New-Object -ComObject WScript.Shell
L("SendKeys: BRUN HGRTEST")
$sh.SendKeys("^c")                     # flush any pending input
Start-Sleep -Milliseconds 200
$sh.SendKeys("BRUN HGRTEST~")
Start-Sleep -Seconds 6

$w = [G]::FindMain()
$r = [G]::Rect($w) -split ' '
$parts = ($r -split ',')
$L = [int]$parts[0]; $T = [int]$parts[1]
$W = [int]($r -split ' ')[1].Split('x')[0]; $H = [int]($r -split ' ')[1].Split('x')[1]
L("capture rect $L,$T ${W}x${H}")
$bmp = New-Object System.Drawing.Bitmap $W, $H
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($L, $T, 0, 0, (New-Object System.Drawing.Size $W, $H))
$bmp.Save($png, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
L("saved $png")
L("DONE")
