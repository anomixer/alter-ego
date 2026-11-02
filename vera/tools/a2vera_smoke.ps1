$ErrorActionPreference='Stop'
iex (Get-Content -Raw 'C:\dev\alter-ego\vera\tools\a2vera_windows.ps1')
iex (Get-Content -Raw 'C:\dev\alter-ego\vera\tools\a2vera_cpu.ps1')
$symbols=Get-AEGameSymbols
function Wait-AEState([scriptblock]$condition,[string]$description) {
  $deadline=(Get-Date).AddSeconds(20)
  while(-not (& $condition)) {
    if((Get-Date) -ge $deadline) { throw "Timeout: $description" }
    Start-Sleep -Milliseconds 10
  }
}
$shotRoot='C:\dev\alter-ego\vera\build\shots\all_levels'
New-Item -ItemType Directory -Path $shotRoot -Force | Out-Null
$processId=Start-AEEmulator
[AECPU]::Attach([uint32]$processId)
Capture-AEFrame $processId "$shotRoot\title.bmp"
foreach($key in @('K','A','J','K','A','J','1',' ')) {
  Send-AEKey $processId $key
  Start-Sleep -Milliseconds 120
}
Start-Sleep -Seconds 4
for($level=0;$level -lt 26;$level++) {
  $id=$level.ToString('00')
  Wait-AEState {
    [AECPU]::Byte($symbols['_current_level']) -eq $level -and
    [AECPU]::Byte($symbols['_start_delay']) -eq 0 -and
    [AECPU]::Byte($symbols['_level_cleared']) -eq 0
  } "LV$id ready"
  Send-AEKey $processId ' '
  Wait-AEState {
    [AECPU]::Byte($symbols['_paused']) -eq 1 -and
    [AECPU]::Byte($symbols['_pause_frames']) -gt 0
  } "LV$id pause rendering complete"
  Save-AEState $processId "$shotRoot\LV$id.aws.yaml"
  Capture-AEFrame $processId "$shotRoot\LV$id.bmp"
  python 'C:\dev\alter-ego\vera\tools\a2vera_verify_runtime.py' "$shotRoot\LV$id.aws.yaml" --level $level
  if($LASTEXITCODE -ne 0) { throw "LV$id runtime validation failed" }
  Send-AEKey $processId ' '
  Wait-AEState { [AECPU]::Byte($symbols['_paused']) -eq 0 } "LV$id resume"
  Send-AEKey $processId '1'
  Wait-AEState { [AECPU]::Byte($symbols['_level_cleared']) -eq 1 } "LV$id clear"
  if($level -eq 25) { Start-Sleep -Seconds 8 }
}
Capture-AEFrame $processId "$shotRoot\ending.bmp"
Save-AEState $processId "$shotRoot\ending.aws.yaml"
[AECPU]::Detach()
Write-Output 'PASS: all 26 levels loaded and advanced without code overwrite'
