param([int]$Slot=-1,[Nullable[int]]$Pitch=$null,[Nullable[double]]$Chunk=$null,[switch]$Bypass,[switch]$Status,[switch]$List)
$b='http://127.0.0.1:18000'

function Ensure-Up {
  try{ Invoke-RestMethod "$b/api/hello" -TimeoutSec 3 | Out-Null; return $true }catch{}
  Write-Host 'VCClient not responding - starting it...'
  & 'D:\VoiceRP\start-voicerp.ps1' | Out-Null
  try{ Invoke-RestMethod "$b/api/hello" -TimeoutSec 5 | Out-Null; return $true }catch{ Write-Host 'could not start VCClient'; return $false }
}
function Ensure-Live {
  for($i=0;$i -lt 6;$i++){
    if((Invoke-RestMethod "$b/api/local-voice-changer-interface/information").local_voice_changer_interface_active){ return $true }
    try{ Invoke-RestMethod "$b/api/local-voice-changer-interface/operation/start" -Method Post -Body '{}' -ContentType 'application/json' | Out-Null }catch{}
    Start-Sleep 3
  }
  return (Invoke-RestMethod "$b/api/local-voice-changer-interface/information").local_voice_changer_interface_active
}
function Show-Status {
  $c=Invoke-RestMethod "$b/api/configuration-manager/configuration"
  $s=Invoke-RestMethod "$b/api/slot-manager/slots/$($c.current_slot_index)"
  $l=(Invoke-RestMethod "$b/api/local-voice-changer-interface/information").local_voice_changer_interface_active
  Write-Host ("live={0} bypass={1} slot={2} name={3} pitch={4} chunk={5}" -f $l,$c.pass_through,$c.current_slot_index,$s.name,$s.pitch_shift,$s.chunk_sec)
}

if(-not (Ensure-Up)){ exit 1 }

if($List){ 0..9 | ForEach-Object { $s=Invoke-RestMethod "$b/api/slot-manager/slots/$_"; if($s.model_file){ "$_ : $($s.name)  [$($s.model_file)]  pitch=$($s.pitch_shift) chunk=$($s.chunk_sec)" } }; return }
if($Status){ Show-Status; return }
if($Bypass){
  $c=Invoke-RestMethod "$b/api/configuration-manager/configuration"; $c.pass_through = -not $c.pass_through
  Invoke-RestMethod "$b/api/configuration-manager/configuration" -Method Put -Body ($c|ConvertTo-Json -Depth 6) -ContentType 'application/json' | Out-Null
  Ensure-Live | Out-Null; Show-Status; return
}
if($Slot -ge 0){
  $c=Invoke-RestMethod "$b/api/configuration-manager/configuration"; $c.current_slot_index=$Slot
  Invoke-RestMethod "$b/api/configuration-manager/configuration" -Method Put -Body ($c|ConvertTo-Json -Depth 6) -ContentType 'application/json' | Out-Null
}
if($Pitch -ne $null -or $Chunk -ne $null){
  $c=Invoke-RestMethod "$b/api/configuration-manager/configuration"; $i=$c.current_slot_index
  $s=Invoke-RestMethod "$b/api/slot-manager/slots/$i"
  if($Pitch -ne $null){ $s.pitch_shift=$Pitch }
  if($Chunk -ne $null){ $s.chunk_sec=$Chunk }
  Invoke-RestMethod "$b/api/slot-manager/slots/$i" -Method Put -Body ($s|ConvertTo-Json -Depth 8) -ContentType 'application/json' | Out-Null
}
Ensure-Live | Out-Null
Show-Status
