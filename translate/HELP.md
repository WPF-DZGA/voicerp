# VoiceRP settings and recommendations

Every setting that matters, in the order you should set it. The app reads this
file for its Help window, so the repo copy and the in-app copy cannot drift.

Rule of thumb: **nothing selects VoiceRP as its microphone.** VoiceRP grabs your
real mic itself and writes into a virtual cable. Apps listen to the cable.

---

## 0. What you need to run this

Measured on the reference rig, not estimated from model file sizes:

| | VoiceRP costs |
|---|---|
| VRAM (whisper `small` float16 on CUDA) | **0.84 - 1.12 GB** |
| RAM, whisper loaded | **0.9 GB** |
| RAM, 5 languages + 5 voices warm | **2.4 GB** |
| Disk, 6 languages | **≈ 3.5 GB** (whisper 464 MB, voices 64 MB each, Argos ≈ 1 GB, Python + deps ≈ 2.4 GB) |
| Disk, all 37 languages | **≈ 10.8 GB** |

Arma Reforger asks for a Core i5-4460 and a GTX 1650 at minimum, a Core i7-6700
and a GTX 1070 Ti recommended, 8/16 GB RAM, and 15-20 GB of disk. Running both
at once is what sets the real floor:

| | Minimum for game + translation | Comfortable |
|---|---|---|
| GPU | 6 GB VRAM (GTX 1660 Super, RTX 2060) | 8-12 GB (RTX 3060, RTX 4060) |
| CPU | 6 cores | 8 cores or more |
| RAM | **16 GB** | 32 GB |
| Disk | 25 GB free, SSD | SSD |

Why the minimum is above the game's own: whisper wants ~1 GB of VRAM that the
game would otherwise use, so a 4 GB card ends up swapping textures. 8 GB of
system RAM is not viable - Reforger alone asks for that much, and VoiceRP adds
2.4 GB on top.

**No GPU, or a 4 GB card**: set whisper to CPU and leave VRAM to the game. It
costs about 1.2 s per phrase instead of 0.2 s on the reference i9-13900KF, and
it needs roughly two cores flat out for that second - on a 4-core machine the
game will hitch while it runs. Playable if you speak between contacts, annoying
during one.

The first phrase in a new language is slower: **2.2 - 3.5 s**, because the Argos
model and the Piper voice load on demand. After that it is ~650 ms. The GUI
pre-warms Russian, Ukrainian, Spanish, French, Polish and English at startup.

## 1. Quick start

1. `voicerp-gui.bat`
2. Wait for `models ready (whisper on cuda, 37 languages)` in the log - 30-45 s.
3. Pick an output language, hold **F9**, speak one short sentence, release.

If the log says `whisper on cpu`, CUDA did not load. Still works, about 1.2 s
instead of 0.2 s.

---

## 2. Settings inside VoiceRP

| Setting | Recommended | Why |
|---|---|---|
| Microphone | your real mic, not the cable | picking the cable feeds it its own output |
| Send to | `CABLE Input (VB-Audio Virtual Cable)` | this is what other apps will hear |
| I speak | `English` or `Polish`, not auto | auto-detect misreads one-word callouts |
| Talk key | `f9` | must not collide with a game bind |
| Headset | your headphones | only used if the box below is ticked |
| also play in my headset | on while testing, off in a firefight | it is a separate stream, others do not hear it twice |
| Voice | whichever you prefer | per-language, remembered |
| Language | English or Polish | the interface only; it does not affect translation |

Choices are saved to `translate/gui_state.json` when you change them, and
restored next launch. Delete that file to start clean.

The Polish interface reads `translate/HELP.pl.md` for this page; strings live in
`translate/i18n.py`. Engine log lines stay English on purpose - they get pasted
into bug reports and searched for verbatim.

**Voice gender**: nine languages have no female Piper voice (German,
Portuguese, Romanian, Bulgarian, Latvian, Slovenian, Albanian, Arabic, Farsi).
That is the voice catalogue, not a setting.

**Not possible at all**: Japanese and Thai. Translation packs exist, speech
synthesis does not - Piper has no OpenJTalk phonemiser and no Thai word
segmenter. See `translate/langs_broken.json`.

---

## 3. Microphone level - the setting that breaks everything

Watch `input peak` after each release.

| Peak | Meaning | Do |
|---|---|---|
| above 0 dB | clipped in hardware | turn the gain knob down |
| **-30 to -6 dB** | correct | nothing |
| -45 to -30 dB | usable, quiet | move closer |
| below -60 dB | nothing arriving | section 7 |

A clipped mic does not produce quiet transcripts, it produces **confident
nonsense** - "THANK YOU FOR WATCHING!" and similar. That is whisper's output on
noise. If you get a transcript that has nothing to do with what you said, look
at the peak before anything else.

On the Razer Seiren Elite the knob range measured **-2.7 dB fully down to
+19.5 dB fully up**. Roughly a third up is right. Fully down still works.

---

## 4. Windows sound settings

**Turn off audio enhancements on the microphone.** This is mandatory.

```
Settings > System > Sound > Input > (your mic) > Audio enhancements = Off
```

Windows 11 "Voice Clarity" attaches an effect to microphone capture and can gate
a studio mic to digital zero, or leave a 30 dB tilt below 300 Hz that makes
whisper detect the wrong language entirely. It lives in the audio engine, so
every application sees the damage and no software fix is possible.

Verify from PowerShell - a `VocaEffectPack` value means it is still attached:

```powershell
Get-ChildItem "HKLM:\SYSTEM\CurrentControlSet\Control\MMDevices\Audio\Capture" -Recurse |
  Where-Object { $_.Name -like '*FxProperties*' } |
  ForEach-Object { $_.Name; Get-ItemProperty $_.PSPath }
```

**Default devices.** Decide which app should hear the translation:

| Goal | Default Device (playback) | Default **Communications** input |
|---|---|---|
| game hears translation, Discord hears your real voice | your headset | `CABLE Output` |
| neither, testing only | your headset | your real mic |

Arma Reforger has no microphone picker - it follows the Windows default
communications input. Discord has its own picker, so it can be pointed at your
Arctis mic explicitly and will keep carrying your real voice regardless.

**Do not enable "Listen to this device"** on CABLE Output. Use the app's own
headset box instead; Listen adds its own delay and can feed back.

---

## 5. Discord settings

```
Settings > Voice & Video
  Input Device ......... CABLE Output (VB-Audio Virtual Cable)   <- to send translation
                         or your Arctis mic                      <- to send your voice
  Input Volume ......... 100%
  Input Sensitivity .... Manual, around -45 dB   (or use push-to-talk)
  Noise Suppression .... None       (NOT Krisp)
  Echo Cancellation .... off
  Noise Reduction ...... off
  Automatic Gain ....... off
```

Krisp and AGC are tuned for a human at a microphone. A synthesised stream
arriving in bursts gets chopped, gated or half-swallowed. If the translation
sounds clipped to everyone but fine in your headset, this is why.

**Push-to-talk in Discord fights push-to-talk in VoiceRP.** Either give Discord
voice activity for the cable, or bind Discord's PTT to the same F9.

---

## 6. VB-Audio Virtual Cable

Defaults are correct. It was measured transparent here: **0 glitches in 124,000
samples, tone-to-junk 95.4 dB.** If you open its control panel:

| | |
|---|---|
| Internal Sample Rate | 48000 Hz |
| Max Latency | 7168 smp (default) |

Both endpoints must agree on format, so leave CABLE Input and CABLE Output at
**48000 Hz, 16-bit, 2 channel** in Windows Sound > Device properties > Advanced.

**SteelSeries Sonar**: its virtual devices only open at their exact native rate
and channel count - 8 channel at 96 kHz for Gaming/Media/Aux, 2 channel at
48 kHz for Chat/Microphone. VoiceRP negotiates this automatically, but if you
route through Sonar instead of straight to the headset, expect the app to pick
the odd-looking combination on purpose.

---

## 7. Troubleshooting, in the order that finds it fastest

| Symptom | Cause | Fix |
|---|---|---|
| `loudest sample: -120 dB` | Voice Clarity, or mic muted in Windows | section 4 |
| transcript unrelated to speech | clipped input | section 3 |
| nothing heard, peak fine | too short, or `no_speech_prob` above 0.9 | speak a full sentence |
| crackling | buffer underrun, or piper piping to stdout | `docs/GOTCHAS.txt` #16, #22 |
| `PaErrorCode -9999` | WASAPI stream opened off the main thread | restart the app |
| `PaErrorCode -9997` | sample rate mismatch | section 6 |
| others hear it chopped | Krisp / AGC | section 5 |
| others hear you twice | VCClient is also writing to the cable | close VCClient |

**Swap the microphone first.** If two different mics fail identically, the bug
is in software, not hardware. That single test once ended an hour of chasing a
microphone that was fine.

---

## 8. How to speak to it

1. **One thought per press.** Hold, say a complete short sentence, release.
   "Contact north, two vehicles" works. Half a sentence does not.
2. **Release cleanly.** A 150 ms tail is captured after release; cutting the key
   mid-word loses the word.
3. **Pause before pressing again.** The previous line is still synthesising.
4. **Short is faster.** Latency scales with audio length, not sentence
   difficulty.
5. **Numbers and callsigns survive translation badly.** Say them in the target
   language yourself, or keep them in the same sentence as plain words.

Measured on an RTX 4080 / i9-13900KF: **648 ms** total for
"One, two, three, four, five." - stt 101 ms, translate 74 ms, speech 473 ms.
Expect 650 ms to 1.0 s. On CPU only, roughly double.

---

## 9. Running it with the voice changer

Both tools write into the same cable. Running them together means everyone
hears your converted voice **and** the translation.

- Translation only: close the VCClient console window.
- Voice changer only: close VoiceRP.
- Check what is running: `powershell -File D:\VoiceRP\voice.ps1 -Status`

---

## 10. Before you ask for a fix

Have these three lines ready - they identify almost every failure on their own:

1. the `input peak` value
2. the whole `seg [...] nsp=... logp=...` line
3. whether `drops` appeared in the status bar

`docs/GOTCHAS.txt` holds 25 numbered findings, each with the measurement that
proved it. Read it before changing any audio setting.
