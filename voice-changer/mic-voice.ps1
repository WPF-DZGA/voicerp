Import-Module AudioDeviceCmdlets -Force
$d=(Get-AudioDevice -List | Where-Object {$_.Type -eq "Recording" -and $_.Name -like "CABLE Output*"})
Set-AudioDevice -ID $d.ID | Out-Null
try{ Set-AudioDevice -ID $d.ID -CommunicationOnly | Out-Null }catch{}
"mic -> CABLE Output (voice changer live)"
