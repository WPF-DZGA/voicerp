# Building the installer

```powershell
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\voicerp.iss
# -> installer\dist\VoiceRP-Setup-1.0.0.exe   (about 100 KB)
```

Install Inno Setup with `winget install JRSoftware.InnoSetup` if it is missing.

## What the installer does and does not ship

It contains the app source, the bootstrap script and the launchers. Nothing
else. Python, the wheels and the speech models are fetched on first run from
python.org, PyPI and Hugging Face, which keeps three problems away:

- **No redistribution questions.** Every third-party byte comes from its own
  vendor, over HTTPS, at install time.
- **No 11 GB installer.** The download matches the languages the user picked.
- **No antivirus false positives.** There is no packed interpreter to look
  suspicious - which is the usual fate of PyInstaller onefile builds.

## The four decisions baked in

1. **VB-Cable is a dependency, not a payload.** It is donationware from
   VB-Audio and may not be redistributed, so the second wizard page detects it
   and links to vb-audio.com. Detection looks for an audio render endpoint
   named `CABLE Input` under
   `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render\*\Properties`,
   because VB-Cable leaves no uninstall entry and no service under a guessable
   name. The page has a Re-check button and does not block: someone can install
   the cable afterwards.
2. **Unsigned.** This is an internal WPF tool. SmartScreen will say "Windows
   protected your PC" - *More info* then *Run anyway*. An EV certificate is
   about EUR 300-500 a year and is not worth it here. Tell people to expect
   the warning; that is better than teaching them to ignore warnings in
   general.
3. **Slim by default.** The bootstrap installs `requirements-slim.txt` and then
   verifies torch did not sneak back in through a dependency, removing it if it
   did. 839 MB saved, see `docs/GOTCHAS.txt` #26.
4. **The size is stated before anything is downloaded.** The welcome page gives
   the figure, and the acceleration page recomputes it live from the language
   and GPU choices.

## Install layout

```
%LOCALAPPDATA%\VoiceRP\
  python\              private CPython, installed with Include_tcltk=1
  venv\                the virtual environment
  translate\           app, plus voices\ and whisper\ once downloaded
  installer\bootstrap.ps1
  voicerp-gui.bat      Start menu target
  voicerp-setup.bat    re-run to add languages or repair
  installed.json       what was chosen, and when
  bootstrap-*.log
```

`%LOCALAPPDATA%` rather than Program Files, for two reasons: the venv and the
models are written after install by a non-elevated process, and gigabytes of
model data do not belong in Program Files. The consequence is that the install
is per-user, which suits a tool people run on their own gaming PC.

## Adding languages later

```powershell
%LOCALAPPDATA%\VoiceRP\voicerp-setup.bat -Languages ru,uk,pl,cs -Sources en,pl -Cuda
```

Re-running is safe: present voices and packs are skipped, failed downloads are
retried. `-DryRun` prints the plan and downloads nothing. `-AllLanguages` gets
all 37.

## The embeddable-Python trap

The obvious choice for a private interpreter is the embeddable zip - 11 MB, no
installer. It cannot be used here: **it ships without tkinter**, which the GUI
needs, and without pip. The bootstrap therefore downloads the official
installer and runs it with `/quiet InstallAllUsers=0 TargetDir=... Include_tcltk=1
PrependPath=0`, which touches neither PATH nor any Python the user already has.
It then asserts `import tkinter` before going any further, so the failure is
named at install time rather than on first launch.
