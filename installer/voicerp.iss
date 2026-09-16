; VoiceRP installer.
;
; Deliberately small: it ships the app source and the bootstrap only. Python,
; the wheels and the models are fetched from python.org, PyPI and Hugging Face
; on first run, so nothing third-party is redistributed here and the download
; matches the languages the user actually picked.
;
; Build:  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" voicerp.iss
; Output: dist\VoiceRP-Setup-<version>.exe
;
; Unsigned on purpose - this is an internal WPF tool. SmartScreen will show
; "Windows protected your PC"; More info -> Run anyway. Documented in README.

#define AppName       "VoiceRP"
#define AppVersion    "1.0.0"
#define AppPublisher  "WPF-DZGA"
#define AppURL        "https://github.com/WPF-DZGA/voicerp"
#define SrcRoot       ".."

[Setup]
AppId={{8F3A2D71-6C45-4B9E-9A21-3D7C1B9E4A02}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
; LOCALAPPDATA, not Program Files: the venv and the models are written after
; install by a non-elevated process, and 11 GB of models do not belong in
; Program Files anyway.
DefaultDirName={localappdata}\VoiceRP
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=VoiceRP-Setup-{#AppVersion}
; The payload is a few hundred KB of source. lzma2/max spent 22 minutes on
; it for no gain, so this stays at normal and non-solid.
Compression=lzma2/normal
SolidCompression=no
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#AppName}
; Setup itself is tiny; the space is needed by the bootstrap, which checks
; again with the real figure once the languages are known.
ExtraDiskSpaceRequired=10485760

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "pl"; MessagesFile: "compiler:Languages\Polish.isl"

[CustomMessages]
en.SizeWarning=VoiceRP runs entirely offline, so the speech models have to be downloaded once.%n%nWith six languages that is about 2 GB, or 4 GB with NVIDIA acceleration. All 37 languages is about 11 GB.%n%nThe download happens at the end of this install and takes 10-40 minutes. You choose the languages on the next pages.
pl.SizeWarning=VoiceRP dziala w pelni offline, wiec modele mowy trzeba raz pobrac.%n%nDla szesciu jezykow to okolo 2 GB, albo 4 GB z akceleracja NVIDIA. Wszystkie 37 jezykow to okolo 11 GB.%n%nPobieranie odbywa sie na koncu instalacji i zajmuje 10-40 minut. Jezyki wybierasz na kolejnych stronach.
en.CableTitle=VB-Audio Virtual Cable
en.CableSubtitle=Required, and not included in this installer
pl.CableTitle=VB-Audio Virtual Cable
pl.CableSubtitle=Wymagane, nie jest zawarte w tym instalatorze
en.LangTitle=Languages to install
en.LangSubtitle=Each one adds about 185 MB. You can add more later by re-running the setup script.
pl.LangTitle=Jezyki do instalacji
pl.LangSubtitle=Kazdy dodaje okolo 185 MB. Wiecej mozna dodac pozniej, uruchamiajac ponownie skrypt setup.
en.GpuTitle=Acceleration
en.GpuSubtitle=How speech recognition should run
pl.GpuTitle=Akceleracja
pl.GpuSubtitle=Jak ma dzialac rozpoznawanie mowy

[Files]
Source: "{#SrcRoot}\translate\*.py";      DestDir: "{app}\translate"; Flags: ignoreversion
Source: "{#SrcRoot}\translate\*.json";    DestDir: "{app}\translate"; Flags: ignoreversion
Source: "{#SrcRoot}\translate\*.md";      DestDir: "{app}\translate"; Flags: ignoreversion
Source: "{#SrcRoot}\translate\shims\*";   DestDir: "{app}\translate\shims"; Flags: ignoreversion
Source: "{#SrcRoot}\tools\*";             DestDir: "{app}\tools";     Flags: ignoreversion
Source: "{#SrcRoot}\docs\*";              DestDir: "{app}\docs";      Flags: ignoreversion
Source: "{#SrcRoot}\requirements-slim.txt"; DestDir: "{app}";         Flags: ignoreversion
Source: "{#SrcRoot}\requirements.txt";    DestDir: "{app}";           Flags: ignoreversion
Source: "{#SrcRoot}\README.md";           DestDir: "{app}";           Flags: ignoreversion
Source: "{#SrcRoot}\LICENSE";             DestDir: "{app}";           Flags: ignoreversion
Source: "bootstrap.ps1";                  DestDir: "{app}\installer"; Flags: ignoreversion
Source: "voicerp-gui.bat";                DestDir: "{app}";           Flags: ignoreversion
Source: "voicerp-setup.bat";              DestDir: "{app}";           Flags: ignoreversion

[Icons]
Name: "{group}\VoiceRP";              Filename: "{app}\voicerp-gui.bat";   WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 138
; No "/" in a shortcut Name: Windows reads it as a path separator, so
; "VoiceRP setup / repair" makes Inno try to create a FOLDER called
; "VoiceRP setup " and fails with IPersistFile::Save 0x80070003.
Name: "{group}\VoiceRP setup and repair"; Filename: "{app}\voicerp-setup.bat"; WorkingDir: "{app}"
Name: "{group}\Settings and help (English)"; Filename: "{app}\translate\HELP.md"
Name: "{group}\Ustawienia i pomoc (Polski)"; Filename: "{app}\translate\HELP.pl.md"
Name: "{userdesktop}\VoiceRP";        Filename: "{app}\voicerp-gui.bat";   WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 138; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Run]
; Visible on purpose. This downloads gigabytes; pip's own output is the only
; honest progress indicator, and a hidden 30-minute step looks like a hang.
Filename: "powershell.exe"; \
  Parameters: "-ExecutionPolicy Bypass -NoProfile -File ""{app}\installer\bootstrap.ps1"" -AppDir ""{app}"" {code:BootstrapArgs}"; \
  WorkingDir: "{app}"; \
  StatusMsg: "Downloading Python, packages and speech models..."; \
  Flags: waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{app}\venv"
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\translate\voices"
Type: filesandordirs; Name: "{app}\translate\whisper"
Type: filesandordirs; Name: "{app}\translate\__pycache__"
Type: files;          Name: "{app}\installed.json"
Type: files;          Name: "{app}\bootstrap-*.log"
Type: files;          Name: "{app}\translate\gui_state.json"

[Code]
var
  CablePage: TWizardPage;
  CableStatus: TNewStaticText;
  CableLink: TNewStaticText;
  CableRecheck: TNewButton;
  LangPage: TInputOptionWizardPage;
  GpuPage: TInputOptionWizardPage;
  PlanLabel: TNewStaticText;

const
  LANG_CODES = 'ru,uk,pl,es,fr,de,ar,zh';
  NAME_KEY = '{a45c254e-df1c-4efd-8020-67d146a850e0},2';

function SplitItem(S: string; Index: Integer): string;
var
  I, Start: Integer;
  Count: Integer;
begin
  Result := '';
  Count := 0;
  Start := 1;
  S := S + ',';
  for I := 1 to Length(S) do
  begin
    if S[I] = ',' then
    begin
      if Count = Index then
      begin
        Result := Copy(S, Start, I - Start);
        Exit;
      end;
      Count := Count + 1;
      Start := I + 1;
    end;
  end;
end;

{ VB-Cable leaves no uninstall entry and no service under a guessable name.
  What it does leave is an audio render endpoint called "CABLE Input", so that
  is what gets checked - the same thing the app itself looks for. }
function CableInstalled: Boolean;
var
  Keys: TArrayOfString;
  I: Integer;
  Name: string;
begin
  Result := False;
  if not RegGetSubkeyNames(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render', Keys) then
    Exit;
  for I := 0 to GetArrayLength(Keys) - 1 do
  begin
    if RegQueryStringValue(HKLM,
         'SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render\' + Keys[I] + '\Properties',
         NAME_KEY, Name) then
    begin
      if Pos('CABLE Input', Name) > 0 then
      begin
        Result := True;
        Exit;
      end;
    end;
  end;
end;

procedure RefreshCable;
begin
  if CableInstalled then
  begin
    CableStatus.Caption := 'Found: VB-Audio Virtual Cable is installed on this machine.';
    CableStatus.Font.Color := clGreen;
    CableRecheck.Caption := 'Re-check (found)';
  end
  else
  begin
    CableStatus.Caption :=
      'Not found. VoiceRP writes its audio into this virtual cable, and other' + #13#10 +
      'applications listen to it. Without the cable nothing can hear VoiceRP.' + #13#10 + #13#10 +
      'It is donationware from VB-Audio and cannot be redistributed inside this' + #13#10 +
      'installer, so install it yourself, then press Re-check. A reboot may be' + #13#10 +
      'needed. You can also continue now and install it later.';
    CableStatus.Font.Color := clMaroon;
    CableRecheck.Caption := 'Re-check';
  end;
end;

procedure CableLinkClick(Sender: TObject);
var
  Code: Integer;
begin
  ShellExec('open', 'https://vb-audio.com/Cable/', '', '', SW_SHOW, ewNoWait, Code);
end;

procedure CableRecheckClick(Sender: TObject);
begin
  RefreshCable;
end;

procedure UpdatePlan;
var
  N, I: Integer;
  Gb: Extended;
  S: string;
begin
  if PlanLabel = nil then Exit;
  N := 0;
  if LangPage.Values[8] then
    N := 37
  else
    for I := 0 to 7 do
      if LangPage.Values[I] then N := N + 1;

  Gb := 0.42 + 0.47 + (N * 0.18);
  if (GpuPage <> nil) and GpuPage.Values[0] then Gb := Gb + 2.0;

  S := 'Languages selected: ' + IntToStr(N) + #13#10 +
       'Download on first run: about ' + Format('%.1f', [Gb]) + ' GB' + #13#10 +
       'Time: roughly ' + IntToStr(10 + Round(Gb * 8)) + ' minutes on a 50 Mbit line';
  if N = 0 then
    S := S + #13#10 + 'Pick at least one language, or the app will have nothing to speak.';
  PlanLabel.Caption := S;
end;

procedure LangClick(Sender: TObject);
begin
  UpdatePlan;
end;

procedure InitializeWizard;
begin
  { size expectation, before anything else }
  WizardForm.WelcomeLabel2.Caption := ExpandConstant('{cm:SizeWarning}');

  CablePage := CreateCustomPage(wpWelcome,
    ExpandConstant('{cm:CableTitle}'), ExpandConstant('{cm:CableSubtitle}'));

  CableStatus := TNewStaticText.Create(CablePage);
  CableStatus.Parent := CablePage.Surface;
  CableStatus.Left := 0;
  CableStatus.Top := 0;
  CableStatus.Width := CablePage.SurfaceWidth;
  CableStatus.AutoSize := True;
  CableStatus.WordWrap := True;

  CableLink := TNewStaticText.Create(CablePage);
  CableLink.Parent := CablePage.Surface;
  CableLink.Left := 0;
  CableLink.Top := 120;
  CableLink.Caption := 'Open vb-audio.com/Cable to download it';
  CableLink.Font.Color := clBlue;
  CableLink.Font.Style := [fsUnderline];
  CableLink.Cursor := crHand;
  CableLink.OnClick := @CableLinkClick;

  CableRecheck := TNewButton.Create(CablePage);
  CableRecheck.Parent := CablePage.Surface;
  CableRecheck.Left := 0;
  CableRecheck.Top := 150;
  CableRecheck.Width := 120;
  CableRecheck.Height := 26;
  CableRecheck.OnClick := @CableRecheckClick;

  RefreshCable;

  LangPage := CreateInputOptionPage(CablePage.ID,
    ExpandConstant('{cm:LangTitle}'), ExpandConstant('{cm:LangSubtitle}'),
    '', False, False);
  LangPage.Add('Russian');
  LangPage.Add('Ukrainian');
  LangPage.Add('Polish');
  LangPage.Add('Spanish');
  LangPage.Add('French');
  LangPage.Add('German');
  LangPage.Add('Arabic');
  LangPage.Add('Chinese');
  LangPage.Add('All 37 languages (about 11 GB)');
  LangPage.Values[0] := True;    { Russian }
  LangPage.Values[2] := True;    { Polish - also a source language }
  LangPage.CheckListBox.OnClickCheck := @LangClick;

  GpuPage := CreateInputOptionPage(LangPage.ID,
    ExpandConstant('{cm:GpuTitle}'), ExpandConstant('{cm:GpuSubtitle}'),
    'Speech recognition is the slow part. On an NVIDIA card it takes about' + #13#10 +
    '0.2 s per phrase; on the CPU about 1.2 s, and it needs two cores flat out' + #13#10 +
    'for that second, which a game will feel.',
    True, False);
  GpuPage.Add('NVIDIA GPU with CUDA - adds 2.0 GB, needs 6 GB of VRAM to share with a game');
  GpuPage.Add('CPU only - smaller install, slower, leaves the GPU alone');
  GpuPage.Values[0] := True;
  GpuPage.CheckListBox.OnClickCheck := @LangClick;

  PlanLabel := TNewStaticText.Create(GpuPage);
  PlanLabel.Parent := GpuPage.Surface;
  PlanLabel.Left := 0;
  PlanLabel.Top := 110;
  PlanLabel.Width := GpuPage.SurfaceWidth;
  PlanLabel.AutoSize := True;
  PlanLabel.WordWrap := True;
  UpdatePlan;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  I, N: Integer;
begin
  Result := True;
  if (LangPage <> nil) and (CurPageID = LangPage.ID) then
  begin
    N := 0;
    if LangPage.Values[8] then
      N := 37
    else
      for I := 0 to 7 do
        if LangPage.Values[I] then N := N + 1;
    if N = 0 then
    begin
      MsgBox('Pick at least one language, otherwise there is nothing for VoiceRP to speak.',
             mbError, MB_OK);
      Result := False;
    end;
  end;
  if (GpuPage <> nil) and (CurPageID = GpuPage.ID) then
    UpdatePlan;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (CablePage <> nil) and (CurPageID = CablePage.ID) then
    RefreshCable;
  if (GpuPage <> nil) and (CurPageID = GpuPage.ID) then
    UpdatePlan;
end;

function DryRunRequested: Boolean;
begin
  { /DRYRUN lets the whole installer be tested without pulling gigabytes:
    files are laid down and the bootstrap runs, but prints its plan and stops. }
  Result := CompareText(ExpandConstant('{param:DRYRUN|no}'), 'no') <> 0;
end;

{ Arguments handed to bootstrap.ps1 }
function BootstrapArgs(Param: string): string;
var
  I: Integer;
  Langs: string;
begin
  if LangPage.Values[8] then
    Result := '-AllLanguages'
  else
  begin
    Langs := '';
    for I := 0 to 7 do
      if LangPage.Values[I] then
      begin
        if Langs <> '' then Langs := Langs + ',';
        Langs := Langs + SplitItem(LANG_CODES, I);
      end;
    Result := '-Languages ' + Langs;
  end;

  { Polish is offered as a source language, so its reverse pack is needed too }
  if LangPage.Values[2] or LangPage.Values[8] then
    Result := Result + ' -Sources en,pl'
  else
    Result := Result + ' -Sources en';

  if GpuPage.Values[0] then
    Result := Result + ' -Cuda';

  if DryRunRequested then
    Result := Result + ' -DryRun';
end;
