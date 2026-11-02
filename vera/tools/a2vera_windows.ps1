if (-not ('AEWindow' -as [type])) {
Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public class AEWindow {
  public delegate bool EnumProc(IntPtr h, IntPtr arg);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr arg);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumProc cb, IntPtr arg);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr h);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint key, uint mode);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a,uint b,bool flag);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  public static bool Focus(IntPtr h) {
    uint pid=0;
    uint fg=GetWindowThreadProcessId(GetForegroundWindow(),out pid);
    uint current=GetCurrentThreadId();
    AttachThreadInput(current,fg,true);
    BringWindowToTop(h);
    bool result=SetForegroundWindow(h);
    AttachThreadInput(current,fg,false);
    return result;
  }
}
'@
}

function Start-AEEmulator([int]$bootWaitSeconds=10,[ValidateSet(2,4)][int]$veraSlot=2,[string]$imagePath='C:\dev\alter-ego\vera\build\alter-ego-vera-psg.hdv') {
  Get-Process AppleWin* -ErrorAction SilentlyContinue | Stop-Process -Force
  $slotArg="-s$veraSlot vera"
  $p=Start-Process 'C:\dev\applewin\release\AppleWin.exe' -WorkingDirectory 'C:\dev\alter-ego\vera\build\shots' -ArgumentList "-h1 $imagePath -s6 empty -s7 hdc -model apple2ee $slotArg -no-full-screen -power-on -log" -PassThru
  $deadline=(Get-Date).AddSeconds(15)
  do {
    Start-Sleep -Milliseconds 100
    $frame=Get-AEWindows $p.Id | Where-Object Class -eq 'APPLE2FRAME'
  } while (!$frame -and (Get-Date) -lt $deadline)
  if (!$frame) { throw "AppleWin did not create a window for VERA Slot $veraSlot" }
  Start-Sleep -Seconds $bootWaitSeconds
  [void][AEWindow]::Focus($frame.Handle)
  return $p.Id
}

function Send-AEKey([int]$processId,[string]$key,[int]$holdMs=0) {
  $frame=Get-AEWindows $processId | Where-Object Class -eq 'APPLE2FRAME'
  if (!$frame) { throw 'Emulator frame not found' }
  $vk=[int][char]$key.ToUpperInvariant()[0]
  $scan=[AEWindow]::MapVirtualKey($vk,0)
  if ($holdMs) { [void][AEWindow]::PostMessage($frame.Handle,0x100,[IntPtr]$vk,[IntPtr](1+($scan -shl 16))) }
  [void][AEWindow]::PostMessage($frame.Handle,0x102,[IntPtr]$vk,[IntPtr]0)
  if ($holdMs) {
    Start-Sleep -Milliseconds $holdMs
    [void][AEWindow]::PostMessage($frame.Handle,0x101,[IntPtr]$vk,[IntPtr](3221225473L+($scan -shl 16)))
  }
}

function Capture-AEFrame([int]$processId,[string]$output) {
  $frame=Get-AEWindows $processId | Where-Object Class -eq 'APPLE2FRAME'
  $before=Get-Date
  [void][AEWindow]::PostMessage($frame.Handle,0x312,[IntPtr]0x404,[IntPtr]0)
  Start-Sleep -Milliseconds 300
  $shot=Get-ChildItem 'C:\dev\alter-ego\vera\build' -Filter '*.bmp' | Where-Object LastWriteTime -ge $before | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (!$shot) { throw 'AppleWin did not produce a screenshot' }
  Copy-Item -LiteralPath $shot.FullName -Destination $output
}
function Get-AEWindows([int]$processId, [IntPtr]$parent=[IntPtr]::Zero) {
  $result=[System.Collections.Generic.List[object]]::new()
  $cb=[AEWindow+EnumProc]{param($h,$arg)
    [uint32]$owner=0
    [void][AEWindow]::GetWindowThreadProcessId($h,[ref]$owner)
    if ($owner -eq $processId) {
      $title=[System.Text.StringBuilder]::new(1024)
      $class=[System.Text.StringBuilder]::new(256)
      [void][AEWindow]::GetWindowText($h,$title,$title.Capacity)
      [void][AEWindow]::GetClassName($h,$class,$class.Capacity)
      $result.Add([pscustomobject]@{Handle=$h;Title=$title.ToString();Class=$class.ToString();Id=[AEWindow]::GetDlgCtrlID($h)})
    }
    return $true
  }.GetNewClosure()
  if ($parent -eq [IntPtr]::Zero) { [void][AEWindow]::EnumWindows($cb,[IntPtr]::Zero) }
  else { [void][AEWindow]::EnumChildWindows($parent,$cb,[IntPtr]::Zero) }
  return $result
}

function Save-AEState([int]$processId, [string]$output) {
  $frame=Get-AEWindows $processId | Where-Object Class -eq 'APPLE2FRAME'
  [void][AEWindow]::PostMessage($frame.Handle,0x100,[IntPtr]0x7A,[IntPtr]0)
  [void][AEWindow]::PostMessage($frame.Handle,0x101,[IntPtr]0x7A,[IntPtr]0)
  Start-Sleep -Milliseconds 300
  $dialog=Get-AEWindows $processId | Where-Object Title -eq 'Select Save State file'
  [void][AEWindow]::PostMessage($dialog.Handle,0x111,[IntPtr]1,[IntPtr]0)
  Start-Sleep -Milliseconds 300
  $confirm=Get-AEWindows $processId | Where-Object {$_.Class -eq '#32770' -and $_.Title -ne 'Select Save State file'}
  foreach($d in $confirm) {
    [void][AEWindow]::PostMessage($d.Handle,0x111,[IntPtr]6,[IntPtr]0)
  }
  Start-Sleep -Milliseconds 500
  $source=(Get-ItemProperty 'HKCU:\Software\AppleWin\CurrentVersion\Configuration').'Save State Filename'
  if ((Get-AEWindows $processId | Where-Object Class -eq '#32770').Count) { throw 'Snapshot dialog is still open' }
  Copy-Item -LiteralPath $source -Destination $output
  [void][AEWindow]::Focus($frame.Handle)
}
