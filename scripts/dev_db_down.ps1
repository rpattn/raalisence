# Stop PostgreSQL database

Write-Host "Stopping PostgreSQL database..." -ForegroundColor Green

# Stop and remove container
docker stop raalisence-postgres 2>$null
docker rm raalisence-postgres 2>$null

Write-Host "PostgreSQL stopped successfully!" -ForegroundColor Green

