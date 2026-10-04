Set-Location (Join-Path $PSScriptRoot "frontend")
Write-Host "Starting frontend on http://127.0.0.1:5500"
Write-Host ""
Write-Host "Open this URL in your browser:"
Write-Host "   http://127.0.0.1:5500"
Write-Host ""
Write-Host "Do NOT open http://127.0.0.1:5000  (that is the API only)"
Write-Host "Do NOT open http://[::]:5500     (IPv6 can fail on Windows)"
Write-Host ""
python -m http.server 5500 --bind 127.0.0.1
