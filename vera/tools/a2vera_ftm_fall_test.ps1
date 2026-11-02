# Exercise falling item stacks (Levels 7/10) and mid-fall exchange (Level 24).
$ErrorActionPreference='Stop'
$toolDir=$PSScriptRoot
if (-not $toolDir) { $toolDir=Join-Path (Get-Location).Path 'vera\tools' }
$root=Split-Path (Split-Path $toolDir -Parent) -Parent
iex (Get-Content -Raw (Join-Path $toolDir 'a2vera_windows.ps1'))
iex (Get-Content -Raw (Join-Path $toolDir 'a2vera_cpu.ps1'))
if (-not ('AEWrite' -as [type])) {
Add-Type @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
public class AEWrite {
  [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr OpenProcess(uint access,bool inherit,uint pid);
  [DllImport("kernel32.dll",SetLastError=true)] static extern bool WriteProcessMemory(IntPtr h,IntPtr addr,byte[] data,IntPtr size,out IntPtr written);
  [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
  static IntPtr process;
  static long ram;
  public static void Attach(uint pid,long ramBase) {
    process=OpenProcess(0x438,false,pid);
    if(process==IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error());
    ram=ramBase;
  }
  public static void Byte(int addr,byte value) {
    byte[] data={value}; IntPtr written;
    if(!WriteProcessMemory(process,new IntPtr(ram+addr),data,new IntPtr(1),out written) || written.ToInt64()!=1)
      throw new Win32Exception(Marshal.GetLastWin32Error());
  }
  public static void Detach() { if(process!=IntPtr.Zero) { CloseHandle(process);process=IntPtr.Zero; } }
}
'@
}
$image=Join-Path $root 'vera\build\alter-ego-vera.hdv'
if (-not (Test-Path -LiteralPath $image)) { throw "FTM image missing: $image" }
$testLevel=7
$testX=200
$testY=88
$initialItemCount=12
$expectedRemaining=6
if ($env:AE_FALL_TEST_LEVEL -eq '10') {
  $testLevel=10
  $testX=168
  $initialItemCount=16
  $expectedRemaining=12
}
if ($env:AE_FALL_TEST_LEVEL -eq '24') { $testLevel=24 }
$appleProcess=$null
try {
  Get-Process AppleWin* -ErrorAction SilentlyContinue | Stop-Process -Force
  $shots=Join-Path $root 'vera\build\shots'
  New-Item -ItemType Directory -Force -Path $shots | Out-Null
  $appleProcess=Start-Process 'C:\dev\applewin\release\AppleWin.exe' -WorkingDirectory $shots -ArgumentList @('-h1',$image,'-s6','empty','-s7','hdc','-model','apple2ee','-s2','vera','-no-full-screen','-power-on') -PassThru
  $deadline=(Get-Date).AddSeconds(20)
  do {
    Start-Sleep -Milliseconds 100
    $frame=Get-AEWindows $appleProcess.Id | Where-Object Class -eq 'APPLE2FRAME'
  } while (!$frame -and (Get-Date) -lt $deadline)
  if (!$frame) { throw 'AppleWin did not create its game window' }
  Start-Sleep -Seconds 15
  [AECPU]::Attach([uint32]$appleProcess.Id)
  $symbols=@{}
  $debugFile=Join-Path $root 'vera\build\game-ftm.dbg'
  if (-not (Test-Path -LiteralPath $debugFile)) { throw 'Build the FTM image to generate game-ftm.dbg first' }
  foreach($line in Get-Content -LiteralPath $debugFile) {
    if($line -match '^sym\s+.*name="([^"]+)".*val=0x([0-9A-Fa-f]+)') {
      $symbols[$matches[1]]=[Convert]::ToInt32($matches[2],16)
    }
  }
  $ramPointer=[AECPU]::ReadProcess([AECPU]::Symbol('mem'),4)
  [AEWrite]::Attach([uint32]$appleProcess.Id,[BitConverter]::ToUInt32($ramPointer,0))
  # Start through the real title Start Level command.
  [AEWrite]::Byte($symbols['_title_choice'],1)
  [AEWrite]::Byte($symbols['_title_level'],[byte]$testLevel)
  Write-Output ("Title state before Start: choice={0}, level={1}, player=({2},{3})" -f [AECPU]::Byte($symbols['_title_choice']),[AECPU]::Byte($symbols['_title_level']),[AECPU]::Byte($symbols['_player_x']),[AECPU]::Byte($symbols['_player_y']))
  [void][AEWindow]::Focus($frame.Handle)
  Send-AEKey $appleProcess.Id ' '
  if ($testLevel -eq 24) {
    $deadline=(Get-Date).AddSeconds(12)
    do {
      Start-Sleep -Milliseconds 20
      $delay=[AECPU]::Byte($symbols['_start_delay'])
    } while ($delay -eq 0 -and (Get-Date) -lt $deadline)
    if ($delay -eq 0) { throw 'Level 24 never loaded' }
  }
  $deadline=(Get-Date).AddSeconds(12)
  do {
    Start-Sleep -Milliseconds 20
    $level=[AECPU]::Byte($symbols['_current_level'])
    $delay=[AECPU]::Byte($symbols['_start_delay'])
    $initialItems=[AECPU]::Byte($symbols['_items_left'])
  } while (($level -ne $testLevel -or $delay -ne 0 -or
            ($testLevel -ne 24 -and $initialItems -ne $initialItemCount)) -and (Get-Date) -lt $deadline)
  if ($level -ne $testLevel -or $delay -ne 0 -or
      ($testLevel -ne 24 -and $initialItems -ne $initialItemCount)) {
    Capture-AEFrame $appleProcess.Id (Join-Path $shots 'ftm_fall_boot_failure.bmp')
    throw "Level $testLevel did not become playable (level=$level delay=$delay items=$initialItems)"
  }
  if ($testLevel -eq 24) {
    $charges=[AECPU]::Byte($symbols['_exchange_left'])
    if ($charges -eq 0 -or [AECPU]::Byte($symbols['_active_music']) -ne 6) {
      throw 'Level 24 charge or Level 5 theme was not initialized'
    }
    $fallSeen=$false
    for ($n=0;$n -lt 12;$n++) {
      Send-AEKey $appleProcess.Id 'D'
      Start-Sleep -Milliseconds 65
      if ([AECPU]::Byte($symbols['_player_fall_steps']) -gt 0) {
        $fallSeen=$true
        break
      }
    }
    if (-not $fallSeen) { throw 'Right movement did not start the Level 24 fall' }
    $deadline=(Get-Date).AddSeconds(3)
    while ([AECPU]::Byte($symbols['_exchange_left']) -eq $charges -and
           (Get-Date) -lt $deadline) {
      Send-AEKey $appleProcess.Id 'J'
      Start-Sleep -Milliseconds 25
    }
    if ([AECPU]::Byte($symbols['_exchange_left']) -eq $charges) {
      throw 'Exchange did not register during the Level 24 fall'
    }
    Write-Output 'PASS: FTM Level 24 falling exchange spent one charge'
    return
  }
  # Start one tile above a vertical stack of items. Level 7 tests both Egos;
  # Level 10 tests a four-item stack collected by the active player.
  [AEWrite]::Byte($symbols['_player_x'],[byte]$testX)
  [AEWrite]::Byte($symbols['_player_y'],[byte]$testY)
  [AEWrite]::Byte($symbols['_player_fall_steps'],0)
  [AEWrite]::Byte($symbols['_player_move_steps'],0)
  $minimum=255
  $deadline=(Get-Date).AddSeconds(4)
  do {
    $remaining=[AECPU]::Byte($symbols['_items_left'])
    if ($remaining -lt $minimum) { $minimum=$remaining }
    if ($minimum -le $expectedRemaining) { break }
    Start-Sleep -Milliseconds 5
  } while ((Get-Date) -lt $deadline)
  if ($minimum -ne $expectedRemaining) { throw "Level $testLevel fall missed a stacked item: minimum items_left=$minimum, expected $expectedRemaining" }
  Write-Output "PASS: FTM Level $testLevel fall collected every item in the tested stack"
  if ($testLevel -eq 7) {
    # Fall through the opposite lower stack too; this should clear the level.
    [AEWrite]::Byte($symbols['_player_x'],48)
    [AEWrite]::Byte($symbols['_player_y'],128)
    [AEWrite]::Byte($symbols['_player_fall_steps'],0)
    [AEWrite]::Byte($symbols['_player_move_steps'],0)
    $deadline=(Get-Date).AddSeconds(8)
    do {
      Start-Sleep -Milliseconds 10
      $level=[AECPU]::Byte($symbols['_current_level'])
      $remaining=[AECPU]::Byte($symbols['_items_left'])
    } while ($level -ne 8 -and (Get-Date) -lt $deadline)
    if ($level -ne 8) { throw "Level 7 failed to clear after both falling item stacks (items_left=$remaining)" }
    Write-Output 'PASS: FTM Level 7 cleared and advanced to Level 8'
  }
} finally {
  [AEWrite]::Detach()
  [AECPU]::Detach()
  if ($appleProcess -and -not $appleProcess.HasExited) { Stop-Process -Id $appleProcess.Id -Force }
}
