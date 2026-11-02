# Read the emulated CPU RAM through AppleWin's matching release PDB.
# This is a read-only observation channel; game actions still use normal keys.
if (-not ('AECPU' -as [type])) {
Add-Type @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
public class AECPU {
  [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr OpenProcess(uint access,bool inherit,uint pid);
  [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
  [DllImport("kernel32.dll",SetLastError=true)] static extern bool ReadProcessMemory(IntPtr h,IntPtr addr,byte[] data,IntPtr size,out IntPtr read);
  [DllImport("dbghelp.dll",SetLastError=true,CharSet=CharSet.Ansi)] static extern bool SymInitialize(IntPtr h,string path,bool invade);
  [DllImport("dbghelp.dll")] static extern uint SymSetOptions(uint options);
  [DllImport("dbghelp.dll",SetLastError=true,CharSet=CharSet.Ansi)] static extern bool SymFromName(IntPtr h,string name,IntPtr info);
  [DllImport("dbghelp.dll")] static extern bool SymCleanup(IntPtr h);
  static IntPtr process;
  static long ram;
  public static void Attach(uint pid) {
    Detach();
    process=OpenProcess(0x410,false,pid);
    if(process==IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error());
    SymSetOptions(0x206);
    if(!SymInitialize(process,"C:\\dev\\applewin\\release",true)) throw new Win32Exception(Marshal.GetLastWin32Error());
    IntPtr info=Marshal.AllocHGlobal(1112);
    try {
      Marshal.WriteInt32(info,0,88);
      Marshal.WriteInt32(info,80,1024);
      if(!SymFromName(process,"AppleWin!mem",info)) throw new Win32Exception(Marshal.GetLastWin32Error());
      long address=Marshal.ReadInt64(info,56);
      byte[] pointer=new byte[4];IntPtr read;
      if(!ReadProcessMemory(process,new IntPtr(address),pointer,new IntPtr(4),out read)) throw new Win32Exception(Marshal.GetLastWin32Error());
      ram=BitConverter.ToUInt32(pointer,0);
    } finally { Marshal.FreeHGlobal(info); }
  }
  public static byte[] Read(int addr,int count) {
    if(addr<0 || count<0 || addr+count>65536) throw new ArgumentOutOfRangeException();
    byte[] data=new byte[count];IntPtr read;
    if(!ReadProcessMemory(process,new IntPtr(ram+addr),data,new IntPtr(count),out read) || read.ToInt64()!=count) throw new Win32Exception(Marshal.GetLastWin32Error());
    return data;
  }
  public static long Symbol(string name) {
    IntPtr info=Marshal.AllocHGlobal(1112);
    try {
      Marshal.WriteInt32(info,0,88);
      Marshal.WriteInt32(info,80,1024);
      if(!SymFromName(process,"AppleWin!"+name,info)) throw new Win32Exception(Marshal.GetLastWin32Error());
      return Marshal.ReadInt64(info,56);
    } finally { Marshal.FreeHGlobal(info); }
  }
  public static byte[] ReadProcess(long addr,int count) {
    byte[] data=new byte[count];IntPtr read;
    if(!ReadProcessMemory(process,new IntPtr(addr),data,new IntPtr(count),out read) || read.ToInt64()!=count) throw new Win32Exception(Marshal.GetLastWin32Error());
    return data;
  }
  public static byte Byte(int addr) { return Read(addr,1)[0]; }
  public static void Detach() {
    if(process!=IntPtr.Zero) { SymCleanup(process);CloseHandle(process);process=IntPtr.Zero; }
  }
}
'@
}
function Get-AEGameSymbols([string]$debugPath='C:\dev\alter-ego\vera\build\game.dbg') {
  $result=@{}
  foreach($line in Get-Content -LiteralPath $debugPath) {
    if($line -match '^sym\s+.*name="([^"]+)".*val=0x([0-9A-Fa-f]+)') {
      $result[$matches[1]]=[Convert]::ToInt32($matches[2],16)
    }
  }
  return $result
}
