# PowerShell script to check ports for LLM Council
# For Windows PowerShell

Write-Host "Checking ports for LLM Council..." -ForegroundColor Cyan
Write-Host ""

function Check-Port {
    param(
        [int]$Port,
        [string]$Service
    )
    
    $connections = netstat -ano | Select-String ":$Port "
    
    if ($connections) {
        Write-Host "✗ Port $Port ($Service) is IN USE" -ForegroundColor Red
        Write-Host "  Process using the port:" -ForegroundColor Yellow
        $connections | ForEach-Object { Write-Host "  $_" }
        return $false
    } else {
        Write-Host "✓ Port $Port ($Service) is AVAILABLE" -ForegroundColor Green
        return $true
    }
}

# Check backend port (8001)
$backendAvailable = Check-Port -Port 8001 -Service "Backend"

# Check frontend port (5174)
$frontendAvailable = Check-Port -Port 5174 -Service "Frontend"

Write-Host ""
if ($backendAvailable -and $frontendAvailable) {
    Write-Host "All ports are available! You can start the application." -ForegroundColor Green
} else {
    Write-Host "Some ports are in use. You can:" -ForegroundColor Yellow
    Write-Host "1. Stop the process using the port" -ForegroundColor White
    Write-Host "2. Modify ports in docker-compose.yml (see README.md)" -ForegroundColor White
    Write-Host "3. Use this script to find available ports" -ForegroundColor White
}

