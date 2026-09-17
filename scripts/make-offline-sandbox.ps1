param([Parameter(Mandatory=$true)][string]$DistFolder,
      [Parameter(Mandatory=$true)][string]$ResultsFolder)
$ErrorActionPreference = 'Stop'
$dist = (Resolve-Path $DistFolder).Path
New-Item -ItemType Directory -Force -Path $ResultsFolder | Out-Null
$results = (Resolve-Path $ResultsFolder).Path
$d = [System.Security.SecurityElement]::Escape($dist)
$r = [System.Security.SecurityElement]::Escape($results)
@"
<Configuration>
  <Networking>Disable</Networking>
  <MappedFolders>
    <MappedFolder><HostFolder>$d</HostFolder><SandboxFolder>C:\PDFPrep</SandboxFolder><ReadOnly>true</ReadOnly></MappedFolder>
    <MappedFolder><HostFolder>$r</HostFolder><SandboxFolder>C:\Results</SandboxFolder><ReadOnly>false</ReadOnly></MappedFolder>
  </MappedFolders>
  <LogonCommand><Command>cmd /c C:\PDFPrep\PDF-Accessibility-Prep.exe --self-test --report C:\Results\offline-self-test.json</Command></LogonCommand>
</Configuration>
"@ | Set-Content -Encoding utf8 (Join-Path $results 'PDFPrep-offline.wsb')
Write-Host 'Open PDFPrep-offline.wsb on a machine with Windows Sandbox already available. Inspect offline-self-test.json afterward. This script only writes the harness; it does not run or certify the test.'
