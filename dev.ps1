# Starts PostgreSQL (docker compose), then backend (uvicorn :8000) and frontend (vite :5173).
$root = $PSScriptRoot

if (-not (Test-Path "$root\.env")) {
  Write-Error "Missing .env - copy .env.example to .env first (POSTGRES_PASSWORD is required)."
  exit 1
}
docker compose -f "$root\docker-compose.yml" -f "$root\docker-compose.dev.yml" up -d --wait postgres

$back = Start-Process -PassThru -NoNewWindow -WorkingDirectory "$root\backend" `
  -FilePath "$root\backend\.venv\Scripts\uvicorn.exe" `
  -ArgumentList "app.main:app", "--reload", "--port", "8000"
$front = Start-Process -PassThru -NoNewWindow -WorkingDirectory "$root\frontend" `
  -FilePath "npm.cmd" -ArgumentList "run", "dev"

try {
  Wait-Process -Id $back.Id, $front.Id
} finally {
  Stop-Process -Id $back.Id, $front.Id -ErrorAction SilentlyContinue
}
