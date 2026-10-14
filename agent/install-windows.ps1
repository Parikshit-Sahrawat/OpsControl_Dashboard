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
if ((& $Binary --version) -notmatch '0.123.0') { throw 'Unsupported runtime version' }
$Existing = Get-Service OpsControlAgent -ErrorAction SilentlyContinue
if ($Existing) { Stop-Service OpsControlAgent }
New-Item -Force -ItemType Directory "$Root\bin","$Root\state" | Out-Null
icacls $Root /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-19:(OI)(CI)RX' | Out-Null
if ($LASTEXITCODE) { throw 'Agent access control setup failed' }
icacls "$Root\state" /grant:r '*S-1-5-19:(OI)(CI)M' | Out-Null
if ($LASTEXITCODE) { throw 'Agent state access control setup failed' }
if ((Resolve-Path $Binary).Path -ne "$Root\bin\otelcol-contrib.exe") { Copy-Item $Binary "$Root\bin\otelcol-contrib.exe" -Force }
if ($PSScriptRoot -ne "$Root\bin") { Copy-Item "$PSScriptRoot\opscontrol_agent.py","$PSScriptRoot\windows_service.py","$PSScriptRoot\service_health.py" "$Root\bin" -Force }
if (-not (Test-Path "$Root\state\identity.json")) { Copy-Item $EnrollmentFile "$Root\state\enrollment" -Force }
@{backend=$Backend} | ConvertTo-Json | Set-Content "$Root\service.json"
# Install the approved Python/pywin32 environment before invoking this script.
$ServiceExe = Join-Path $PSScriptRoot 'OpsControlService.exe'
if (Test-Path $ServiceExe) {
    if ($PSScriptRoot -ne "$Root\bin") { Copy-Item $ServiceExe "$Root\bin\OpsControlService.exe" -Force }
    if (-not $Existing) { & "$Root\bin\OpsControlService.exe" --username 'NT AUTHORITY\LocalService' --startup auto install; if ($LASTEXITCODE) { throw 'Service installation failed' } }
    & "$Root\bin\OpsControlService.exe" start
    if ($LASTEXITCODE) { throw 'Service startup failed' }
} else {
if (-not $Existing) { python "$Root\bin\windows_service.py" --username 'NT AUTHORITY\LocalService' --startup auto install; if ($LASTEXITCODE) { throw 'Service installation failed' } }
python "$Root\bin\windows_service.py" start
if ($LASTEXITCODE) { throw 'Service startup failed' }
}
Get-Service OpsControlAgent
Write-Output 'Grant explicit read permissions for configured application logs or approved Event Log reader rights. Agent reports permission failures.'
