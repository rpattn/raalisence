# Generate admin key hash

param(
    [Parameter(Mandatory=$true)]
    [string]$AdminKey
)

Write-Host "Generating bcrypt hash for admin key: $AdminKey" -ForegroundColor Green

python scripts\gen.py $AdminKey

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to generate hash" -ForegroundColor Red
    exit 1
}

