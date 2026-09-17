param([string]$PythonExe = "python")
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Windows x64 required' }
& $PythonExe -m venv .build-venv
if ($LASTEXITCODE -ne 0) { throw 'Python venv failed' }
$py = Join-Path $PWD '.build-venv/Scripts/python.exe'
& $py -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& $py scripts/build_resources.py
if ($LASTEXITCODE -ne 0) { throw 'Resource assembly failed' }
& $py scripts/collect_notices.py
if ($LASTEXITCODE -ne 0) { throw 'License collection failed' }
& $py -m pytest tests -q --junitxml=build/test-results.xml
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $py -m PyInstaller --noconfirm --clean PDF-Accessibility-Prep.spec
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
$exe = Join-Path $PWD 'dist/PDF-Accessibility-Prep.exe'
$report = Join-Path $PWD 'build/packaged-self-test.json'
$p = Start-Process -FilePath $exe -ArgumentList @('--self-test', '--report', "`"$report`"") -PassThru -Wait
if ($p.ExitCode -ne 0) { throw 'Packaged self-test failed' }
if (-not (Test-Path $report)) { throw 'Packaged self-test produced no report' }
$result = Get-Content $report -Raw | ConvertFrom-Json
if (-not $result.passed) { throw 'Packaged PDF/UA/OCR/worker checks failed' }
Get-FileHash $exe -Algorithm SHA256 | Format-List | Out-File dist/SHA256.txt
Copy-Item README.md, LICENSE, THIRD-PARTY-NOTICES.md dist
Copy-Item resources/licenses dist/licenses -Recurse -Force
Write-Host 'Built executable and packaged self-test passed. Clean Windows offline and assistive-technology acceptance are separate manual release gates.'
