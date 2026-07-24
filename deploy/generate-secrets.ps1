# Generates two random secrets for Railway production env.
# Run: .\deploy\generate-secrets.ps1

Write-Host "Copy these into Railway Variables:" -ForegroundColor Cyan
Write-Host ""

function New-Secret {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    [Convert]::ToBase64String($bytes)
}

Write-Host "SECRET_KEY=$(New-Secret)"
Write-Host "METRICS_TOKEN=$(New-Secret)"
Write-Host ""
Write-Host "Full guide: deploy/DEPLOYMENT.md" -ForegroundColor Green
