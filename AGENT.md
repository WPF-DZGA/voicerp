# AGENT.md - build this on a new machine

Instructions for an AI coding agent with shell access on the target Windows
machine. A human can follow the same steps; the commands are ordinary.

Read all of it before starting. Steps 0 and 8 are where setups usually fail, and
they are not obvious from the code.

---

## 0. Ask the operator these four things first

Do not guess them. Each one changes the config and two of them cannot be
discovered from software.

1. **Which microphone** is for the rig, and which stays for normal calls.
2. **Which output** they listen on, and **whether it is wireless**. Wireless
   matters: see step 8.
3. **GPU** - `nvidia-smi`. Decides whether whisper runs at ~200 ms or ~1.2 s.
4. **Target languages.** All 37 is ~2.5 GB of voices plus ~3 GB of translation
   packs. A shortlist is often what they actually want.

Then have them install **VB-Audio Virtual Cable** (https://vb-audio.com/Cable/)
and confirm `CABLE Input` and `CABLE Output` appear in Windows sound settings.
You cannot install it for them - signed driver install plus a reboot.

---

## 1. Python

Needs a real Python 3.11-3.13. The Microsoft Store build works; verify it:

```powershell
python --version
python -m venv D:\VoiceRP\xlate\venv
D:\VoiceRP\xlate\venv\Scripts\python -m pip install --upgrade pip
D:\VoiceRP\xlate\venv\Scripts\pip install -r requirements.txt
```

## 2. GPU acceleration for whisper (optional, worth ~1 second)

`faster-whisper` on CUDA needs CUDA 12 runtime DLLs that do not ship with it:

```powershell
D:\VoiceRP\xlate\venv\Scripts\pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

`bridge.py` adds every `site-packages/nvidia/*/bin` to the DLL search path at
import, then tries `cuda` and falls back to `cpu`. Skip this step and you get
`Library cublas64_12.dll is not found` plus a silent CPU fallback - read the
startup line, it prints which backend it actually got.

## 3. Models

```powershell
D:\VoiceRP\xlate\venv\Scripts\python translate\getvoices.py   # Piper voices
D:\VoiceRP\xlate\venv\Scripts\python translate\getargos.py    # Argos packs
```

Both are idempotent and fetch only what is missing. Edit `translate/langs.json`
first for a subset - remove entries and the scripts skip them. whisper's own
model downloads on first run into `translate/whisper/`.

## 4. Confirm every language actually speaks

```powershell
D:\VoiceRP\xlate\venv\Scripts\python translate\validate_langs.py
```

**Do not skip this.** A translation pack plus a voice file is not enough: some
Piper voices produce a 0-byte WAV because there is no phonemiser for that
language. Japanese (`phoneme_type: "japanese"`, needs OpenJTalk) and Thai (needs
a word segmenter) fail this way and are already excluded. `--prune` moves any
new failures into `langs_broken.json` with the reason.

## 5. Wire the audio

`bridge.py` resolves devices **by name**, not index - PortAudio indices shift
whenever a USB audio device is plugged or unplugged. Set the names at the top:

```python
IN_NAME  = 'Microphone (Razer Seiren Elite)'
OUT_NAME = 'CABLE Input (VB-Audio Virtual Cable)'
MON_NAME = None          # see step 8
```

Exact names come from `tools\tone.py` (outputs) and `tools\meter.py` (inputs).

Then make `CABLE Output` the Windows **default recording device AND default
communications device**. Arma Reforger has no reliable in-game microphone
picker; it follows the Windows default.

## 6. Run it

```powershell
D:\VoiceRP\xlate\venv\Scripts\python translate\gui.py      # window
D:\VoiceRP\xlate\venv\Scripts\python translate\bridge.py   # keyboard only
```

Both front ends import `translate/voicerp_core.py`, which owns the models, the
input stream and the pipeline. Add a feature there, not in one front end.

Three rules that the core enforces and any new front end must respect:

- `Engine.open_input()` must be called from the **main thread** (Tk callbacks
  count). A WASAPI stream started on a worker dies with `PaErrorCode -9999`.
- `load_models()` must NOT be on the main thread, or the window is frozen for
  ~40 s. It touches no audio device, so a worker is safe.
- Every callback (`on_log`, `on_level`, `on_result`, `on_state`) fires on a
  worker thread. Tk is not thread-safe: push to a `queue.Queue` and drain it
  from `root.after()`. `gui.py` does exactly this in `_pump()`.

Hold **F9**, speak, release. Watch the `input peak` line:

| Peak | Meaning |
|---|---|
| above 0 dB | clipped at the mic - turn the gain down |
| -30 to -6 dB | correct |
| below -60 dB | nothing arriving - go to step 8 |

## 7. Voice changer (separate, optional)

Install VCClient (`vcclient_win_cuda_*.zip` from
https://huggingface.co/wok000/vcclient000). Two settings are mandatory:

- `voice_changer_input_mode = "server"` - else start returns
  *"Input mode for VC is not server-mode"*
- `wasapi_exclude_emabled = false` - else PortAudio dies with
  `Invalid sample rate [PaErrorCode -9997]`

VCClient reads its module state **and** the device list only at startup. After
plugging in USB audio, restart `main.exe` or it will not see the device. Its
REST API is on `http://127.0.0.1:18000`; `voice-changer/start-voicerp.ps1`
configures everything through it. The first publish of a new RVC model must go
through the GUI - the CLI is rejected for a new asset.

---

## 8. The failure modes that waste hours

Work through these in order when audio misbehaves. Every one was hit for real.

### The microphone produces nothing, or nothing intelligible

**Windows 11 "Voice Clarity"** is an audio-effect processor bound to capture
endpoints. On a studio condenser it gated the signal to digital zero, and
otherwise stripped the speech band: 0-300 Hz at 34-39 dB while 1-3 kHz sat at
9 dB. whisper returned zero segments and guessed the language as "nn".

It lives inside the Windows audio engine, so WASAPI, DirectSound and MME all
receive the damaged stream - which makes it look like a code bug.

```powershell
# a VocaEffectPack value here = Voice Clarity is attached to that endpoint
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture\{GUID}\FxProperties"
```

Fix: Settings > System > Sound > Input > the mic > **Audio enhancements = Off**.
Needs the GUI and elevation; not doable from a non-elevated shell.

### Crackling

1. **Never let Piper write to stdout.** Windows opens stdout in text mode and
   expands every `0x0A` in the PCM to `0x0D 0x0A`. Measured on one 4.5 s line:
   stdout gave **8621** int16 jumps > 32768 (e.g. `32514 -> -32513`), a file gave
   **0**. That is ~1800 full-scale clicks per second. This repo uses the
   in-process Piper API, which cannot hit it.
2. **Never request `latency='low'`** on a sounddevice stream. The buffer is so
   small the write underruns and the whole line comes out as crackle. Use
   `latency=0.2`.
3. **Normalise before playback.** Piper output peaks at 1.000 and clips the
   cable. Scale to -3 dBFS.
4. **Do not open a second output stream for monitoring.** Every variant tried -
   the wireless headset endpoint, Sonar Aux, Sonar Chat - crackled. To let the
   operator hear themselves, use Windows *"Listen to this device"* on
   `CABLE Output`: `mmsys.cpl` > Recording > CABLE Output > Properties > Listen.
   Windows mixes it inside the audio engine, so no extra stream exists.

### Transcription is garbage but levels look fine

- `temperature=0` **disables whisper's temperature fallback**, so any segment
  failing `log_prob_threshold` is dropped instead of retried. Symptom: empty
  transcripts from clean -20 dB audio. Leave the default.
- `vad_filter=True` silently discards quiet lines. This repo leaves it off and
  prints `no_speech_prob` / `avg_logprob` per segment instead.
- Clipped input makes whisper **hallucinate whole sentences** - "THANK YOU FOR
  WATCHING!", "Thanks for watching!" at `nsp` 0.7-0.9. Those are its noise
  outputs, not a mishearing. Check the peak before blaming the model.

### PortAudio errors

| Error | Cause |
|---|---|
| `-9997 Invalid sample rate` | WASAPI exclusive mode, or you asked for 16 kHz on a USB mic. Record at the device native rate and downsample for the ASR. |
| `-9998 Invalid number of channels` | Sonar virtual devices only open at their exact native rate and full channel count (8ch @ 96 kHz). Negotiate instead of assuming 2ch. |
| `-9999 Unanticipated host error` | You started a WASAPI stream **from a worker thread**. PortAudio initialises COM on whichever thread called `Pa_Initialize`. Open it on the main thread. The message blames WDM-KS even when the device is correct - ignore that. |

### Do not kill processes by name

On a machine driven by an MCP/agent bridge, `Get-Process python | Stop-Process`
kills the agent's own server and drops the session. Kill by PID:

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*bridge.py*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

---

## 9. How to diagnose audio properly

The single most useful lesson: **level metrics cannot detect crackle.**
`volumedetect`, mean/max volume and flat factor all reported corrupted audio as
clean, because the level genuinely was fine. Three separate "fixes" were
validated against those metrics and all three were wrong.

Count sample-to-sample slope against what the signal can physically produce. A
440 Hz sine at peak A has a maximum slope of `2*pi*440/48000*A`; anything past
about 4x that is a glitch.

```powershell
python tools\tone.py sonar        # is this output path clean?
python tools\cabletest.py         # tone through VB-Cable, counts glitches
python tools\clip.py              # counts wraps/clipping in raw TTS output
python tools\meter.py             # live input level in dB
python tools\bench.py             # timing comparison
```

Reference measurements from the working rig:

- VB-Cable: 0 glitches in 124,000 samples, tone-to-junk 95.4 dB
- Piper via file: 0 wrap-arounds; via stdout: 8621
- Mic at native rate: claimed 48000, measured 48006 Hz
- whisper on RTX 4080: 140-250 ms; on i9-13900KF CPU int8: ~1260 ms

### Debugging order that worked

1. **Swap the microphone** (`bridge.py --mic arctis`). If two different mics fail
   identically, the bug is in the code, not the hardware. This one test ended an
   hour of chasing a mic that was fine.
2. Feed a known-good WAV through the same code path (`--selftest`).
3. Compare suspect components on **files**, not live audio.
4. Verify the real sample rate by counting frames per wall-clock second.
5. Dump the spectrum in bands - a ~30 dB tilt below 300 Hz means processing
   damage, not a level problem.

---

## 10. Editing these files from PowerShell

Two traps that cost real time if you are an agent driving PowerShell:

- `.Replace()` on a multi-line block **silently misses** on a CRLF file.
- Here-strings mangle Python quotes, and base64 over ~8 KB gets truncated.
- A here-string over roughly 8 KB fails outright with
  `[WinError 206] The filename or extension is too long` - that is the command
  length limit, not a path problem. Split the write, or hand the file over as a
  file rather than as command text.

Write patches as small base64 chunks applied by a Python splice script, or use
`[System.IO.File]::ReadAllLines()` and replace by line index. Always finish with
`python -c "import ast; ast.parse(open(path).read())"` before running anything.
