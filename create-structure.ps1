# Check if key files exist
$files = @(
    ".env",
    ".env.example", 
    "requirements.txt",
    "requirements-dev.txt",
    "Dockerfile",
    "docker-compose.yml",
    ".gitignore",
    "README.md",
    "pytest.ini",
    "alembic.ini",
    "app\main.py",
    "app\__init__.py",
    "app\db\base.py",
    "app\db\session.py"
)

Write-Host "Checking files..." -ForegroundColor Yellow
foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "✓ $file" -ForegroundColor Green
    } else {
        Write-Host "✗ $file" -ForegroundColor Red
    }
}

# Check for router.py files in endpoints
$endpoints = @("auth", "campaigns", "creators", "applications", "deliverables", "payments", "analytics", "integrations", "notifications", "admin")
Write-Host "`nChecking router files..." -ForegroundColor Yellow
foreach ($endpoint in $endpoints) {
    $routerPath = "app\api\v1\endpoints\$endpoint\router.py"
    if (Test-Path $routerPath) {
        Write-Host "✓ $routerPath" -ForegroundColor Green
    } else {
        Write-Host "✗ $routerPath" -ForegroundColor Red
    }
}