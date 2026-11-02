$ErrorActionPreference='Stop'
iex (Get-Content -Raw 'C:\dev\alter-ego\vera\tools\a2vera_windows.ps1')
iex (Get-Content -Raw 'C:\dev\alter-ego\vera\tools\a2vera_cpu.ps1')
$processId=Start-AEEmulator
[AECPU]::Attach([uint32]$processId)
$symbols=Get-AEGameSymbols
Send-AEKey $processId ' '
Start-Sleep -Seconds 4
$steps=python 'C:\dev\alter-ego\vera\tools\a2vera_route.py' 1 --json | ConvertFrom-Json
foreach($step in $steps) {
  Send-AEKey $processId $step.key
  Start-Sleep -Milliseconds ([int][Math]::Ceiling($step.frames*1000/60))
}
$deadline=(Get-Date).AddSeconds(5)
while([AECPU]::Byte($symbols['_level_cleared']) -eq 0 -and (Get-Date) -lt $deadline) {
  Start-Sleep -Milliseconds 5
}
if([AECPU]::Byte($symbols['_level_cleared']) -ne 1) { throw 'Normal route did not reach LEVEL CLEAR' }
Capture-AEFrame $processId 'C:\dev\alter-ego\vera\build\shots\verified_level_clear.bmp'
Save-AEState $processId 'C:\dev\alter-ego\vera\build\shots\verified_level_clear.aws.yaml'
python -c "import sys; sys.path.insert(0,'C:/dev/alter-ego/vera/tools'); from a2vera_snapshot import read_snapshot; _,_,v,_=read_snapshot('C:/dev/alter-ego/vera/build/shots/verified_level_clear.aws.yaml'); cells=[v[(row*64+col+4)*2] for row in (2,3) for col in range(21,30)]; assert not any(cells),cells; print('PASS: LEVEL CLEAR has no trailing level-name letters')"
if($LASTEXITCODE -ne 0) { throw 'Old level-name letters remain beside LEVEL CLEAR' }
[AECPU]::Detach()
Start-Sleep -Seconds 5
Save-AEState $processId 'C:\dev\alter-ego\vera\build\shots\route_clear.aws.yaml'
Capture-AEFrame $processId 'C:\dev\alter-ego\vera\build\shots\route_clear.bmp'
python 'C:\dev\alter-ego\vera\tools\a2vera_snapshot.py' 'C:\dev\alter-ego\vera\build\shots\route_clear.aws.yaml' --symbols 'C:\dev\alter-ego\vera\build\game.dbg' --expect current_level=2 --expect lives_remaining=5 --expect level_skip=0
if($LASTEXITCODE -ne 0) { throw 'Physical item-collection route did not clear Level 1' }
