# Script para iniciar todos los bots simultáneamente

$ErrorActionPreference = "Stop"
$PythonPath = ".\venv\Scripts\python.exe"

if (-Not (Test-Path $PythonPath)) {
    Write-Host "Error: No se encontró el entorno virtual en .\venv" -ForegroundColor Red
    exit 1
}

Write-Host "Iniciando Bot 1 (PZO/CBL)..." -ForegroundColor Cyan
Start-Process -FilePath $PythonPath -ArgumentList "bot.py 1" -WindowStyle Minimized

Write-Host "Iniciando Bot 2 (Puerto La Cruz)..." -ForegroundColor Cyan
Start-Process -FilePath $PythonPath -ArgumentList "bot.py 2" -WindowStyle Minimized

Write-Host "Iniciando Bot 3 (El Tigre)..." -ForegroundColor Cyan
Start-Process -FilePath $PythonPath -ArgumentList "bot.py 3" -WindowStyle Minimized

Write-Host "Iniciando Bot 4 (Porlamar)..." -ForegroundColor Cyan
Start-Process -FilePath $PythonPath -ArgumentList "bot.py 4" -WindowStyle Minimized

Write-Host "¡Todos los bots se han iniciado en ventanas en segundo plano!" -ForegroundColor Green
Write-Host "Puedes revisar las ventanas de consola minimizadas para ver los logs de cada bot."
