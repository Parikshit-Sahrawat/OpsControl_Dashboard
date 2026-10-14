param([Parameter(Mandatory=$true)][string]$Backend,[Parameter(Mandatory=$true)][string]$EnrollmentFile)
$ErrorActionPreference = 'Stop'
$Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]$Identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run locally as administrator on the approved target.' }
$Uri = [uri]$Backend
if ($Uri.Scheme -ne 'https' -or $Uri.UserInfo -or $Uri.Query -or $Uri.Fragment -or $Uri.AbsolutePath -ne '/') { throw 'HTTPS backend origin required.' }
$Root = 'C:\ProgramData\OpsControlAgent'
$Binary = Join-Path $PSScriptRoot 'otelcol-contrib.exe'
if (-not (Test-Path $Binary)) { throw 'Verified bundled Windows Collector missing.' }
$Expected = ((Get-Content (Join-Path $PSScriptRoot 'runtime.sha256')).Trim() -split '\s+')[0]
if ((Get-FileHash $Binary -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Expected.ToLowerInvariant()) { throw 'Collector checksum mismatch.' }
New-Item -Force -ItemType Directory "$Root\bin","$Root\state" | Out-Null
icacls $Root /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-19:(OI)(CI)RX' | Out-Null
icacls "$Root\state" /grant:r '*S-1-5-19:(OI)(CI)M' | Out-Null
Copy-Item $Binary "$Root\bin\otelcol-contrib.exe" -Force
Copy-Item "$PSScriptRoot\opscontrol_agent.py","$PSScriptRoot\windows_service.py" "$Root\bin" -Force
Copy-Item $EnrollmentFile "$Root\state\enrollment" -Force
@{backend=$Backend} | ConvertTo-Json | Set-Content "$Root\service.json"
# Install the approved Python/pywin32 environment before invoking this script.
python "$Root\bin\windows_service.py" --username 'NT AUTHORITY\LocalService' --startup auto install
python "$Root\bin\windows_service.py" start
Get-Service OpsControlAgent
Write-Output 'Grant explicit read permissions for configured application logs or approved Event Log reader rights. Agent reports permission failures.'
