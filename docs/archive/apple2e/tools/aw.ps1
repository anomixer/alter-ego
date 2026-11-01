# AppleWin automation helpers (dot-source: . aw.ps1)
$s = @'
using System;using System.Text;using System.Collections.Generic;using System.Runtime.InteropServices;
public class W{
 [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lp, IntPtr l);
 public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte sc, uint f, IntPtr e);
 public static IntPtr FindMain(int pid){
  IntPtr found = IntPtr.Zero;
  EnumWindows((h,l)=>{ uint p; GetWindowThreadProcessId(h,out p);
   if((int)p==pid && IsWindowVisible(h)){ var cn=new StringBuilder(128); GetClassName(h,cn,128);
    if(cn.ToString()=="APPLE2FRAME") found=h; } return true; }, IntPtr.Zero);
  return found; }
 public static IntPtr Dialog(int pid){
  IntPtr found = IntPtr.Zero;
  EnumWindows((h,l)=>{ uint p; GetWindowThreadProcessId(h,out p);
   if((int)p==pid && IsWindowVisible(h)){ var cn=new StringBuilder(128); GetClassName(h,cn,128);
    if(cn.ToString()=="#32770") found=h; } return true; }, IntPtr.Zero);
  return found; }
 public static List<string> All(int pid){
  var o=new List<string>(); EnumWindows((h,l)=>{ uint p; GetWindowThreadProcessId(h,out p);
   if((int)p==pid && IsWindowVisible(h)){ var sb=new StringBuilder(256); GetWindowText(h,sb,256);
    var cn=new StringBuilder(128); GetClassName(h,cn,128);
    o.Add("h="+h+" cls="+cn+" text=\""+sb+"\""); } return true; }, IntPtr.Zero);
  return o; }
 public static void Key(IntPtr h, int vk){
  SendMessage(h, 0x0100, (IntPtr)vk, IntPtr.Zero);
  SendMessage(h, 0x0101, (IntPtr)vk, IntPtr.Zero); }
 public static void Type(IntPtr h, string text){
  foreach(char c in text.ToUpper()){
   int vk; bool shift=false;
   if(c>='A'&&c<='Z'){ vk=c-'A'; }
   else if(c>='0'&&c<='9'){ vk=c-'0'; if(c=='0')vk=0x30; }
   else if(c==' '){ vk=0x20; }
   else if(c=='/'){ vk=191; }
   else if(c=='-'){ vk=189; }
   else { vk=0x20; }
   if(c=='/'){ shift=true; }
   if(shift) keybd_event(0x10,0,0,IntPtr.Zero);
   keybd_event((byte)vk,0,0,IntPtr.Zero);
   keybd_event((byte)vk,0,2,IntPtr.Zero);
   if(shift) keybd_event(0x10,0,2,IntPtr.Zero);
   System.Threading.Thread.Sleep(40); }
  keybd_event(0x1D,0,0,IntPtr.Zero); keybd_event(0x1D,0,2,IntPtr.Zero); // Enter
  System.Threading.Thread.Sleep(60); }
}
'@
Add-Type -TypeDefinition $s -ReferencedAssemblies System.Threading

function AW-Pid { (Get-Process -Name "AppleWin*" -ErrorAction SilentlyContinue | Select-Object -First 1).Id }
function AW-Windows { $p = AW-Pid; if ($p) { [W]::All($p) } else { "not running" } }
function AW-Dismiss { $p = AW-Pid; if ($p) { $d = [W]::Dialog($p); if ($d -ne [IntPtr]::Zero) { [W]::Key($d, 0x0D); "dismissed dialog $d" } else { "no dialog" } } }
function AW-Type([string]$text) { $p = AW-Pid; if ($p) { $h = [W]::FindMain($p); if ($h -ne [IntPtr]::Zero) { [W]::Type($h, $text); "typed to $h" } else { "no emulator window" } } }

