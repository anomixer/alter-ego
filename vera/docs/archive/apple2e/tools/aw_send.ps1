iex (Get-Content -Raw 'C:\dev\alter-ego\tools\aw2.ps1')
if (-not ('A2S' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class A2S {
  [StructLayout(LayoutKind.Sequential)]
  public struct KEYBDINPUT { public ushort vk; public ushort scan; public uint flags; public uint time; public IntPtr extra; }
  [StructLayout(LayoutKind.Explicit)]
  public struct INPUT {
    [FieldOffset(0)] public uint type;
    [FieldOffset(8)] public KEYBDINPUT k;
  }
  [DllImport("user32.dll")] public static extern uint SendInput(uint n, INPUT[] p, int cb);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
  public static void Key(ushort vk, ushort scan, bool up) {
    var i = new INPUT();
    i.type = 1;
    i.k.vk = vk;
    i.k.scan = scan;
    i.k.flags = up ? 2u : 0u;      // KEYEVENTF_KEYUP
    i.k.time = 0;
    i.k.extra = IntPtr.Zero;
    SendInput(1, new INPUT[] { i }, Marshal.SizeOf(typeof(INPUT)));
  }
}
"@
}
function Tap([IntPtr]$h, [int]$vk, [int]$sc) {
  [A2S]::Key([ushort]$vk, [ushort]$sc, $false) | Out-Null
  Start-Sleep -Milliseconds 150
  [A2S]::Key([ushort]$vk, [ushort]$sc, $true) | Out-Null
}
function DbgCmd([IntPtr]$h, [string]$cmd) {
  foreach ($ch in $cmd.ToCharArray()) {
    [A2S]::PostMessage($h, 0x0102, [IntPtr]([int]$ch), [IntPtr]0) | Out-Null
    Start-Sleep -Milliseconds 30
  }
  Start-Sleep -Milliseconds 200
  Tap $h 0x0D 0x1C
  Start-Sleep -Milliseconds 400
  for ($i = 0; $i -lt 4; $i++) { Tap $h 0x20 0x39 }
  Start-Sleep -Milliseconds 300
}
$shots = 'C:\dev\alter-ego\build\a2\shots'
$py = 'C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
Get-Process -Name 'AppleWin*' -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force }
Start-Sleep -Seconds 2
$p = Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList '-d1','C:\dev\alter-ego\build\a2\ae2_game.dsk','-model','apple2e','-no-full-screen' -PassThru
Start-Sleep -Seconds 4
Write-Host "pid=$($p.Id)"
$h = $p.MainWindowHandle
Focus2 $h | Out-Null
Start-Sleep -Seconds 12
$p = Get-Process -Id $p.Id
$h = $p.MainWindowHandle
Focus2 $h | Out-Null
Tap $h 0x76 0x3F
Start-Sleep -Seconds 3
$p = Get-Process -Id $p.Id
$h = $p.MainWindowHandle
Focus2 $h | Out-Null
Write-Host ("after F7  " + (HS2 ($shots + '\probe.png')) + "  title=[" + $p.MainWindowTitle + "]")
Shot2 $h ($shots + '\probe.png') | Out-Null
Write-Host ("probe " + (HS2 ($shots + '\probe.png')))
DbgCmd $h 'PC'
DbgCmd $h 'BSAVE "ae2_stk.bin",$100,$100'
DbgCmd $h 'BSAVE "ae2_aux.bin",$C200,$200'
Shot2 $h ($shots + '\awd_pc.png') | Out-Null
Write-Host ("awd_pc " + (HS2 ($shots + '\awd_pc.png')))
& $py -c "
from PIL import Image
im = Image.open(r'$shots\awd_pc.png').convert('RGB')
im.crop((330, 60, 470, 210)).resize((140*6, 150*6), Image.NEAREST).save(r'$shots\awd_pc_regs.png')
im.crop((0, 200, 631, 431)).resize((631*2, 231*2), Image.NEAREST).save(r'$shots\awd_pc_console.png')
print('crops ok')
"
