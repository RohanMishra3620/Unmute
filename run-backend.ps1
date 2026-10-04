Set-Location $PSScriptRoot
Write-Host "Installing dependencies..."
pip install -r backend\requirements.txt
Write-Host ""
Write-Host "Starting backend on http://127.0.0.1:5000"
Write-Host "Keep this window open. Run run-frontend.ps1 in a second terminal."
Write-Host ""
$env:PYTHONPATH = $PSScriptRoot
python -m backend.app
