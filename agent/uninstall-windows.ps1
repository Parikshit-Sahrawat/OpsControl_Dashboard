$ErrorActionPreference = 'Stop'
$Root = 'C:\ProgramData\OpsControlAgent'
$Service = Get-Service OpsControlAgent -ErrorAction SilentlyContinue
if ($Service) {
    Stop-Service OpsControlAgent
    if (Test-Path "$Root\bin\OpsControlService.exe") { & "$Root\bin\OpsControlService.exe" remove; if ($LASTEXITCODE) { throw 'Service removal failed' } }
    else { python "$Root\bin\windows_service.py" remove; if ($LASTEXITCODE) { throw 'Service removal failed' } }
}
Write-Output 'Service removed. Identity and checkpoints retained for reinstall. Revoke Agent in OpsControl before disposing of this host.'
