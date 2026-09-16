<#
    VoiceRP first-run bootstrap.

    Run by the installer after it copies the app, and safe to re-run by hand.
    Everything it fetches comes straight from the vendor: python.org, PyPI and
    Hugging Face. Nothing is redistributed inside the installer, which is what
    keeps the licensing simple.

    Deliberately visible rather than hidden behind a fake progress bar: this
    downloads gigabytes and takes 10-40 minutes, and pip's own output is the
    only honest progress indicator.
#>
[CmdletBinding()]
param(
    [string]   $AppDir    = (Split-Path -Parent $PSScriptRoot),
    [string[]] $Languages = @('ru', 'uk', 'pl', 'es', 'fr', 'de'),
    [string[]] $Sources   = @('en', 'pl'),
    [switch]   $Cuda,
    [switch]   $AllLanguages,
    [switch]   $DryRun,
    [string]   $PyVersion = '3.13.9'
)

$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'SilentlyContinue'   # Invoke-WebRequest is ~10x faster without it

$XlateDir = Join-Path $AppDir 'translate'
$PyDir    = Join-Path $AppDir 'python'
$VenvDir  = Join-Path $AppDir 'venv'
$PyExe    = Join-Path $PyDir  'python.exe'
$VenvPy   = Join-Path $VenvDir 'Scripts\python.exe'
$Marker   = Join-Path $AppDir 'installed.json'
$LogFile  = Join-Path $AppDir ('bootstrap-{0}.log' -f (Get-Date -Format 'yyyyMMdd-HHmmss'))

function Say($msg, $colour = 'Gray') {
    $line = '[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $msg
    Write-Host $line -ForegroundColor $colour
    Add-Content -LiteralPath $LogFile -Value $line -ErrorAction SilentlyContinue
}

function Fail($msg) {
    Say $msg 'Red'
    Say "Log: $LogFile" 'Yellow'
    Write-Host ''
    Read-Host 'Press Enter to close'
    exit 1
}

function Need-Space($gb) {
    $drive = (Get-Item $AppDir).PSDrive.Name
    $free  = (Get-PSDrive $drive).Free / 1GB
    Say ('Free space on {0}: {1:N1} GB, need about {2:N1} GB' -f $drive, $free, $gb)
    if ($free -lt $gb) {
        Fail ('Not enough free space on {0}: {1:N1} GB free, {2:N1} GB needed.' -f $drive, $free, $gb)
    }
}

# ---------------------------------------------------------------- plan
if ($AllLanguages) {
    $Languages = @()          # empty = every language in langs.json
}
$langCount = if ($AllLanguages) { 37 } else { $Languages.Count }
$sizeGb = 0.42 + 0.47 + ($langCount * 0.18)     # python+deps, whisper, per language
if ($Cuda) { $sizeGb += 2.0 }

Write-Host ''
Write-Host '  VoiceRP setup' -ForegroundColor Cyan
Write-Host '  -------------' -ForegroundColor Cyan
Say ("Target folder : $AppDir")
Say ("Languages     : " + $(if ($AllLanguages) { 'all 37' } else { $Languages -join ', ' }))
Say ("I will speak  : " + ($Sources -join ', '))
Say ("Acceleration  : " + $(if ($Cuda) { 'NVIDIA CUDA (adds ~2.0 GB)' } else { 'CPU only' }))
Say ("Download      : about {0:N1} GB, 10-40 minutes on a home connection" -f $sizeGb) 'Yellow'
Write-Host ''

if ($DryRun) {
    Say 'DryRun: stopping here. Nothing downloaded, nothing installed.' 'Yellow'
    Say ("Would run: getvoices.py " + $(if ($AllLanguages) { '(all)' } else { '--only ' + ($Languages -join ',') }))
    Say ("Would run: getargos.py  " + $(if ($AllLanguages) { '' } else { '--only ' + ($Languages -join ',') }) + " --sources " + ($Sources -join ','))
    exit 0
}

Need-Space $sizeGb

# ---------------------------------------------------------------- python
# The embeddable distribution is NOT usable here: it ships without tkinter,
# which the GUI needs, and without pip. So the official installer is fetched
# and run silently into a private folder, touching neither PATH nor any Python
# the user already has.
if (Test-Path $PyExe) {
    Say 'Python already present, skipping.' 'Green'
} else {
    $url = "https://www.python.org/ftp/python/$PyVersion/python-$PyVersion-amd64.exe"
    $tmp = Join-Path $env:TEMP "python-$PyVersion-amd64.exe"
    Say "Downloading Python $PyVersion ..."
    try { Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing }
    catch { Fail "Could not download Python from $url : $_" }

    Say 'Installing Python privately (no PATH changes, no file associations) ...'
    $a = @("/quiet", "InstallAllUsers=0", "TargetDir=$PyDir", "Include_pip=1",
           "Include_tcltk=1", "Include_test=0", "Include_doc=0", "Include_launcher=0",
           "AssociateFiles=0", "Shortcuts=0", "PrependPath=0")
    $p = Start-Process -FilePath $tmp -ArgumentList $a -Wait -PassThru
    if ($p.ExitCode -ne 0 -or -not (Test-Path $PyExe)) {
        Fail "Python installer returned $($p.ExitCode) and $PyExe is missing."
    }
    Remove-Item $tmp -ErrorAction SilentlyContinue
    Say 'Python installed.' 'Green'
}

& $PyExe -c "import tkinter" 2>$null
if ($LASTEXITCODE -ne 0) { Fail 'This Python has no tkinter, so the GUI cannot run. Re-run with Include_tcltk=1.' }

# ---------------------------------------------------------------- venv + wheels
if (-not (Test-Path $VenvPy)) {
    Say 'Creating the virtual environment ...'
    & $PyExe -m venv $VenvDir
    if (-not (Test-Path $VenvPy)) { Fail 'venv creation failed.' }
}

Say 'Upgrading pip ...'
& $VenvPy -m pip install --upgrade pip --quiet

# --no-deps first: a plain resolve re-drags torch in through argostranslate,
# which is 502 MB we proved is not needed (see docs/GOTCHAS.txt #26).
$req = Join-Path $AppDir 'requirements-slim.txt'
if (-not (Test-Path $req)) { Fail "Missing $req" }

# CPU-only: strip the two CUDA lines rather than installing 2 GB and deleting
# it again. The comment marker in the file makes them easy to find.
$reqUse = $req
if (-not $Cuda) {
    $reqUse = Join-Path $env:TEMP 'voicerp-req-cpu.txt'
    Get-Content $req | Where-Object { $_ -notmatch '^nvidia-' } | Set-Content $reqUse -Encoding UTF8
    Say 'CPU-only install: skipping the 2 GB CUDA runtime.'
}

Say 'Installing packages (this is the slow part) ...'
& $VenvPy -m pip install -r $reqUse
if ($LASTEXITCODE -ne 0) { Fail 'pip install failed. See the output above.' }

# argostranslate separately, with --no-deps: its dependency list pulls spacy
# and stanza, and stanza imports torch at module level. Its real needs are
# already in requirements-slim.txt. See docs/GOTCHAS.txt #26.
Say 'Installing argostranslate without its stanza/torch dependencies ...'
& $VenvPy -m pip install --no-deps argostranslate==1.11.0
if ($LASTEXITCODE -ne 0) { Fail 'argostranslate install failed.' }

# torch must not be here. If some dependency dragged it in anyway, drop it.
& $VenvPy -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('torch') else 1)" 2>$null
if ($LASTEXITCODE -eq 0) {
    Say 'torch got pulled in; removing it (839 MB) ...' 'Yellow'
    & $VenvPy -m pip uninstall -y torch stanza spacy scipy blis thinc sympy 2>$null | Out-Null
}

# Without stanza, anything that imports argostranslate.translate dies on
# sbd.py's unguarded `import stanza` - and that is not only our GUI, it is
# getargos.py and validate_langs.py too. voicerp_core.prefer_minisbd() only
# helps processes that import voicerp_core, so the fix belongs in the venv:
# sitecustomize is imported automatically by every interpreter that uses it.
$sitePkgs = & $VenvPy -c "import sysconfig; print(sysconfig.get_paths()['purelib'])"
$shimDir  = Join-Path $XlateDir 'shims'
$siteCust = Join-Path $sitePkgs 'sitecustomize.py'
& $VenvPy -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('stanza') else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    Say 'Registering the MiniSBD sentence splitter for this environment ...'
    @"
# Written by VoiceRP's installer, for a slim install with no stanza or torch.
#
# argostranslate 1.11 imports stanza unguarded in sbd.py, so every script that
# touches argostranslate needs the stub on sys.path and MINISBD selected - not
# just the ones that import voicerp_core. sitecustomize is imported by every
# interpreter using this environment, which is exactly the right scope.
#
# Delete this file if you ever install the real stanza and torch.
import os, sys

os.environ.setdefault('ARGOS_CHUNK_TYPE', 'MINISBD')
os.environ.setdefault('ARGOS_STANZA_AVAILABLE', '0')

_shim = r'$shimDir'
if os.path.isdir(_shim) and _shim not in sys.path:
    sys.path.append(_shim)      # append, so a real stanza would always win
"@ | Set-Content -LiteralPath $siteCust -Encoding UTF8

    & $VenvPy -c "import os, stanza, sys; assert os.environ['ARGOS_CHUNK_TYPE'] == 'MINISBD'; print('sitecustomize active, stanza is', stanza.__version__)"
    if ($LASTEXITCODE -ne 0) { Fail 'sitecustomize did not take effect.' }
}

# ---------------------------------------------------------------- models
Push-Location $XlateDir
try {
    $only = if ($AllLanguages) { @() } else { @('--only', ($Languages -join ',')) }

    Say 'Downloading Piper voices ...'
    & $VenvPy 'getvoices.py' @only
    if ($LASTEXITCODE -ne 0) { Say 'Some voices failed; re-run this script to retry them.' 'Yellow' }

    Say 'Installing Argos translation packs ...'
    & $VenvPy 'getargos.py' @only '--sources' ($Sources -join ',')
    if ($LASTEXITCODE -ne 0) { Say 'Some packs failed; re-run this script to retry them.' 'Yellow' }

    # Loading the engine here downloads whisper (464 MB) and proves the whole
    # stack at install time, instead of making the first launch look hung.
    Say 'Downloading the speech recognition model and testing the pipeline ...'
    & $VenvPy -c "import voicerp_core as c; e = c.Engine(); e.load_models(); print('OK: whisper on', e.asr_device, '-', len(e.langs), 'languages'); e.shutdown()"
    if ($LASTEXITCODE -ne 0) { Fail 'The engine could not start. See the output above.' }

    Say 'Checking every language actually speaks ...'
    & $VenvPy 'validate_langs.py'
    if ($LASTEXITCODE -ne 0) { Say 'validate_langs reported problems; see above.' 'Yellow' }
} finally {
    Pop-Location
}

# ---------------------------------------------------------------- record
@{
    installed    = (Get-Date -Format 'o')
    pythonVer    = $PyVersion
    languages    = if ($AllLanguages) { 'all' } else { $Languages }
    sources      = $Sources
    cuda         = [bool]$Cuda
    appDir       = $AppDir
} | ConvertTo-Json | Set-Content -LiteralPath $Marker -Encoding UTF8

Write-Host ''
Say 'Setup finished.' 'Green'
Say 'VB-Cable must be installed for anything to be heard by other apps.' 'Yellow'
Say 'Start VoiceRP from the Start menu, or voicerp-gui.bat in this folder.' 'Cyan'
Say "Log: $LogFile"
Write-Host ''
Read-Host 'Press Enter to close'
