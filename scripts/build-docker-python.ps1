# Build script for Python raalisence Docker images

param(
    [string]$Tag = "latest",
    [switch]$Prod,
    [switch]$Help
)

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Show help
if ($Help) {
    Write-Host "Usage: .\build-docker-python.ps1 [OPTIONS]"
    Write-Host "Options:"
    Write-Host "  -Tag TAG     Set the image tag (default: latest)"
    Write-Host "  -Prod        Build production image (distroless)"
    Write-Host "  -Help        Show this help message"
    exit 0
}

# Default values
$ImageName = "raalisence-python"
$BuildType = "standard"

# Determine Dockerfile to use
if ($Prod) {
    $Dockerfile = "Dockerfile.python.prod"
    $ImageName = "${ImageName}-prod"
    Write-Status "Building production image with distroless base"
} else {
    $Dockerfile = "Dockerfile.python"
    Write-Status "Building standard image with Python slim base"
}

# Check if Dockerfile exists
if (-not (Test-Path $Dockerfile)) {
    Write-Error "Dockerfile not found: $Dockerfile"
    exit 1
}

# Check if required files exist
$RequiredFiles = @("pyproject.toml", "requirements.txt", "config.yaml", "python_raalisence/main.py")
foreach ($file in $RequiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Error "Required file not found: $file"
        exit 1
    }
}

Write-Status "Building Docker image: ${ImageName}:${Tag}"
Write-Status "Using Dockerfile: $Dockerfile"

# Build the image
try {
    docker build -f $Dockerfile -t "${ImageName}:${Tag}" .
    Write-Status "Successfully built ${ImageName}:${Tag}"
    
    # Show image info
    Write-Status "Image information:"
    docker images "${ImageName}:${Tag}"
    
    # Test the image
    Write-Status "Testing the image..."
    try {
        docker run --rm "${ImageName}:${Tag}" python -c "import python_raalisence; print('Import successful')"
        Write-Status "Image test passed"
    } catch {
        Write-Warning "Image test failed - there may be runtime issues"
    }
    
    Write-Status "Build completed successfully!"
    Write-Status "To run the container:"
    Write-Host "  docker run -p 8080:8080 -v `$(pwd)/data:/app/data -v `$(pwd)/config.yaml:/app/config.yaml:ro ${ImageName}:${Tag}"
    
} catch {
    Write-Error "Failed to build image: $_"
    exit 1
}
