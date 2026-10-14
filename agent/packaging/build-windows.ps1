param([Parameter(Mandatory=$true)][string]$Runtime,[Parameter(Mandatory=$true)][string]$RuntimeSha256)
$ErrorActionPreference='Stop'
$Root = (Resolve-Path "$PSScriptRoot\..\..").Path
if ((Get-FileHash $Runtime -Algorithm SHA256).Hash.ToLowerInvariant() -ne $RuntimeSha256.ToLowerInvariant()) { throw 'Approved runtime checksum mismatch' }
if ((& $Runtime --version) -notmatch '0.123.0') { throw 'Unsupported Collector runtime' }
python -m pip install pyinstaller==6.12.0 pywin32==311
python -m PyInstaller --noconfirm --onefile --name OpsControlService --hidden-import win32timezone --hidden-import service_health --paths "$Root\agent" --distpath "$PSScriptRoot\stage" --workpath "$env:TEMP\opscontrol-build" --specpath "$env:TEMP" "$Root\agent\windows_service.py"
if ($LASTEXITCODE) { throw 'Service executable build failed' }
Copy-Item $Runtime "$PSScriptRoot\stage\otelcol-contrib.exe" -Force
Copy-Item "$Root\agent\install-windows.ps1","$Root\agent\uninstall-windows.ps1","$Root\agent\opscontrol_agent.py","$Root\agent\service_health.py","$Root\agent\windows_service.py" "$PSScriptRoot\stage" -Force
"$RuntimeSha256  otelcol-contrib.exe" | Set-Content "$PSScriptRoot\stage\runtime.sha256"
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" "$PSScriptRoot\opscontrol-agent.iss"
if ($LASTEXITCODE) { throw 'Installer compilation failed' }
