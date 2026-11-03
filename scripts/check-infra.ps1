#Requires -Version 5.1
$ErrorActionPreference = "Stop"

function Assert-Healthy {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Status
    )
    if ($Status -ne "healthy") {
        throw "Service '$Name' is not healthy (status='$Status')."
    }
    Write-Host "OK  $Name is healthy"
}

Write-Host "Validating docker compose configuration..."
docker compose config --quiet
if ($LASTEXITCODE -ne 0) {
    throw "docker compose config failed"
}

Write-Host "Reading container health..."
$services = @(
    "postgres-airport",
    "postgres-itinerary",
    "postgres-notification",
    "redis",
    "rabbitmq",
    "jaeger",
    "otel-collector",
    "prometheus",
    "grafana"
)

foreach ($service in $services) {
    $status = docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" "pis-$service" 2>$null
    if (-not $status) {
        throw "Container 'pis-$service' was not found. Run: docker compose up --build -d"
    }
    if ($status -eq "running") {
        Write-Host "OK  $service is running (no Docker healthcheck)"
        continue
    }
    Assert-Healthy -Name $service -Status $status
}

function Test-HttpOk {
    param(
        [string]$Name,
        [string]$Url,
        [string]$User = "",
        [string]$Password = ""
    )
    try {
        if ($User) {
            $pair = "{0}:{1}" -f $User, $Password
            $bytes = [System.Text.Encoding]::ASCII.GetBytes($pair)
            $token = [Convert]::ToBase64String($bytes)
            $headers = @{ Authorization = "Basic $token" }
            $response = Invoke-WebRequest -Uri $Url -Headers $headers -UseBasicParsing -TimeoutSec 10
        }
        else {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        }
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
            Write-Host "OK  $Name HTTP $($response.StatusCode) $Url"
            return
        }
        throw "Unexpected status $($response.StatusCode)"
    }
    catch {
        throw "HTTP check failed for $Name ($Url): $($_.Exception.Message)"
    }
}

Test-HttpOk -Name "Prometheus" -Url "http://127.0.0.1:9090/-/healthy"
Test-HttpOk -Name "Grafana" -Url "http://127.0.0.1:3000/api/health"
Test-HttpOk -Name "Jaeger UI" -Url "http://127.0.0.1:16686/"

$rabbitUser = if ($env:RABBITMQ_USER) { $env:RABBITMQ_USER } else { "itinerary" }
$rabbitPass = if ($env:RABBITMQ_PASSWORD) { $env:RABBITMQ_PASSWORD } else { "rabbitmq_dev_only" }
Test-HttpOk -Name "RabbitMQ management" -Url "http://127.0.0.1:15672/api/health/checks/alarms" -User $rabbitUser -Password $rabbitPass

Write-Host ""
Write-Host "Phase 1 infrastructure checks passed."

