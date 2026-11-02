param([switch]$Skip)
$ErrorActionPreference='Stop'
iex (Get-Content -Raw 'C:\dev\alter-ego\vera\tools\a2vera_windows.ps1')
iex (Get-Content -Raw 'C:\dev\alter-ego\vera\tools\a2vera_cpu.ps1')
$symbols=Get-AEGameSymbols
function Value([string]$name) { [AECPU]::Byte($symbols['_'+$name]) }
function Wait-CreditsState([scriptblock]$condition,[string]$description) {
  $deadline=(Get-Date).AddSeconds(12)
  while(-not (& $condition)) {
    if((Get-Date) -ge $deadline) { throw "Timeout: $description" }
    Start-Sleep -Milliseconds 5
  }
}
$processId=Start-AEEmulator -bootWaitSeconds 2
[AECPU]::Attach([uint32]$processId)
Wait-CreditsState { (Value 'credits_visible') -eq 1 } 'intro appears'
if($Skip) { Send-AEKey $processId ' ' }
else {
  # The built-in capture can see the framebuffer halfway through its first
  # VERA scanout after enabling video. Allow several complete refreshes.
  Start-Sleep -Milliseconds 150
  Capture-AEFrame $processId 'C:\dev\alter-ego\vera\build\shots\credits_verified.bmp'
  Save-AEState $processId 'C:\dev\alter-ego\vera\build\shots\credits_verified.aws.yaml'
  python 'C:\dev\alter-ego\vera\tools\a2vera_verify_credits.py'
  if($LASTEXITCODE -ne 0) { throw 'Credits VRAM differs from artwork' }
}
Wait-CreditsState { (Value 'credits_visible') -eq 0 } 'intro ends'
Start-Sleep -Seconds 2
Capture-AEFrame $processId 'C:\dev\alter-ego\vera\build\shots\credits_to_title.bmp'
Send-AEKey $processId ' '
Wait-CreditsState { (Value 'start_delay') -gt 0 } 'level intro'
Wait-CreditsState { (Value 'start_delay') -eq 0 } 'level ready'
if((Value 'current_level') -ne 1 -or (Value 'lives_remaining') -ne 5) {
  throw 'Credits/title transition changed initial gameplay state'
}
Write-Output "PASS: Credits (skip=$Skip) -> Title -> Level 1, five reserves"
[AECPU]::Detach()
