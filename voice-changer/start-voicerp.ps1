# VoiceRP launcher - resolves audio devices BY NAME (PortAudio indices shift on replug)
$app='D:\VoiceRP\vcclient_cuda\dist\main'
$b='http://127.0.0.1:18000'
$IN_NAME  = 'Microphone (Razer Seiren Elite)'
$OUT_NAME = 'CABLE Input (VB-Audio Virtual Cable)'
$MON_NAME = ''   # monitor OFF by default - wireless Arctis crackles when two streams hit it

if(-not (Get-Process main -EA 0)){ Start-Process -FilePath "$app\start_http.bat" -WorkingDirectory $app -WindowStyle Minimized }
$ok=$false
for($i=0;$i -lt 45;$i++){ Start-Sleep 2; try{ Invoke-RestMethod "$b/api/hello" -TimeoutSec 3 | Out-Null; $ok=$true; break }catch{} }
if(-not $ok){ Write-Host 'API did not come up'; exit 1 }

$ins  = Invoke-RestMethod "$b/api/audio-device-manager/input_devices"
$outs = Invoke-RestMethod "$b/api/audio-device-manager/output_devices"
$in  = ($ins  | Where-Object { $_.host_api -eq 'Windows WASAPI' -and $_.name -eq $IN_NAME  } | Select-Object -First 1)
$out = ($outs | Where-Object { $_.host_api -eq 'Windows WASAPI' -and $_.name -eq $OUT_NAME } | Select-Object -First 1)
$mon = if($MON_NAME){ $outs | Where-Object { $_.host_api -eq 'Windows WASAPI' -and $_.name -eq $MON_NAME } | Select-Object -First 1 } else { $null }
if(-not $in){ Write-Host "INPUT NOT FOUND: $IN_NAME  (is the Seiren plugged in? restart this script after plugging it)"; exit 1 }
if(-not $out){ Write-Host "OUTPUT NOT FOUND: $OUT_NAME"; exit 1 }

$sr = 48000
if($in.available_samplerates -notcontains 48000){ $sr = [int]$in.default_samplerate }

$c=Invoke-RestMethod "$b/api/configuration-manager/configuration"
$c.voice_changer_input_mode='server'
$c.audio_input_device_index  = $in.index
$c.audio_output_device_index = $out.index
$c.audio_monitor_device_index= if($mon){$mon.index}else{-1}
$c.wasapi_exclude_emabled    = $false          # MUST stay false or PortAudio -9997
$c.audio_input_device_sample_rate = $sr
$c.audio_output_device_sample_rate = 48000
$c.audio_monitor_device_sample_rate = 48000
$c.noise_gate = -40.0
$c.gpu_device_id_int = 0
$c.enable_high_pass_filter = $true; $c.high_pass_filter_cutoff = 90.0
$c.extra_frame_sec = 0.08; $c.crossfade_sec = 0.05
Invoke-RestMethod "$b/api/configuration-manager/configuration" -Method Put -Body ($c|ConvertTo-Json -Depth 6) -ContentType 'application/json' | Out-Null
try{ Invoke-RestMethod "$b/api/local-voice-changer-interface/operation/start" -Method Post -Body '{}' -ContentType 'application/json' | Out-Null }catch{}
Start-Sleep 6
& 'D:\VoiceRP\mic-voice.ps1'
Write-Host ("in  : {0} (idx {1}, {2} Hz)" -f $in.name,$in.index,$sr)
Write-Host ("out : {0} (idx {1})" -f $out.name,$out.index)
Write-Host ("mon : {0}" -f $(if($mon){$mon.name}else{'none'}))
Write-Host ("live: " + (Invoke-RestMethod "$b/api/local-voice-changer-interface/information").local_voice_changer_interface_active)
Write-Host 'UI  : http://127.0.0.1:18000'

