Import-Module AudioDeviceCmdlets -Force
$d=(Get-AudioDevice -List | Where-Object {$_.Type -eq "Recording" -and $_.Name -like "SteelSeries Sonar - Microphone*"})
Set-AudioDevice -ID $d.ID | Out-Null
try{ Set-AudioDevice -ID $d.ID -CommunicationOnly | Out-Null }catch{}
"mic -> Sonar Microphone (normal voice)"
