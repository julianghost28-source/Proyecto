$ErrorActionPreference = "Stop"

if (-not $env:PORT) {
    $env:PORT = "8010"
}

$root = Split-Path -Parent $PSScriptRoot
$root = Split-Path -Parent $root
$env:PYTHONPATH = "$root\packages\pis-platform;$root\services\airport-service"

try {
    py -3 -m uvicorn main:app --host 127.0.0.1 --port $env:PORT
}
finally {
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
}
