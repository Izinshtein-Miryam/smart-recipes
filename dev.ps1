# Runs backend (uvicorn :8000) and frontend (vite :5173) together. Ctrl+C stops both.
$root = $PSScriptRoot

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
