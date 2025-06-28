# Navigate to shared-types root
cd C:\Users\zuhad\OneDrive\Desktop\LaunchPaid\shared-types

# Create new hyper-scale structure
New-Item -ItemType Directory -Path @(
    "src",
    "src\shared",
    "src\shared\events",
    "src\shared\protocols",
    "src\shared\exceptions",
    "src\services",
    "src\services\auth",
    "src\services\creator",
    "src\services\campaign", 
    "src\services\payment",
    "src\services\analytics",
    "src\services\notification",
    "src\services\integration",
    "src\api-gateway",
    "src\event-bus",
    "infrastructure",
    "infrastructure\terraform",
    "infrastructure\kubernetes",
    "infrastructure\monitoring",
    ".github",
    ".github\workflows"
)

# Create service subdirectories
$services = @("auth", "creator", "campaign", "payment", "analytics", "notification", "integration")
foreach ($service in $services) {
    New-Item -ItemType Directory -Path @(
        "src\services\$service\api",
        "src\services\$service\domain",
        "src\services\$service\infrastructure",
        "src\services\$service\application",
        "src\services\$service\tests"
    )
}

# Create core files
New-Item -ItemType File -Path @(
    "docker-compose.prod.yml",
    "docker-compose.dev.yml",
    ".github\workflows\deploy.yml",
    "infrastructure\kubernetes\namespace.yaml",
    "src\api-gateway\main.py",
    "src\event-bus\kafka_config.py"
)