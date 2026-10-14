#define AppVersion "1.5.0"
[Setup]
AppId={{1C8AF623-F3CC-45B8-A09F-A5B70F96B453}
AppName=OpsControl Agent
AppVersion={#AppVersion}
DefaultDirName={commonappdata}\OpsControlAgent\bin
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=OpsControlAgent-1.5.0-Windows-x64
OutputDir=output
Compression=lzma2
SolidCompression=yes
[Files]
Source: "stage\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\install-windows.ps1"" -Backend ""{code:GetBackend}"" -EnrollmentFile ""{code:GetEnrollment}"""; Flags: runhidden waituntilterminated
[UninstallRun]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\uninstall-windows.ps1"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveService"
[Code]
var ConfigPage: TInputQueryWizardPage;
procedure InitializeWizard;
begin
 ConfigPage := CreateInputQueryPage(wpSelectDir, 'Agent enrollment', 'Approved backend and enrollment file', 'Enrollment is one-use. Existing identity and checkpoints survive upgrades.');
 ConfigPage.Add('HTTPS backend origin:', False);
 ConfigPage.Add('Path to enrollment token file:', False);
end;
function GetBackend(Param: String): String;
begin Result := ConfigPage.Values[0]; end;
function GetEnrollment(Param: String): String;
begin Result := ConfigPage.Values[1]; end;
function NextButtonClick(CurPageID: Integer): Boolean;
begin
 Result := True;
 if CurPageID = ConfigPage.ID then begin
  if (Pos('https://', Lowercase(ConfigPage.Values[0])) <> 1) or (Pos('"', ConfigPage.Values[0]) > 0) or (Pos('"', ConfigPage.Values[1]) > 0) or not FileExists(ConfigPage.Values[1]) then begin
   MsgBox('Provide an HTTPS origin and an existing enrollment file without quotation marks.', mbError, MB_OK); Result := False;
  end;
 end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var ResultCode: Integer;
begin
 Result := '';
 if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), '-NoProfile -NonInteractive -Command "$s=Get-Service OpsControlAgent -ErrorAction SilentlyContinue; if($s){Stop-Service OpsControlAgent -ErrorAction Stop}"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
  Result := 'Unable to stop the existing Agent safely. Stop it and retry installation.';
end;
