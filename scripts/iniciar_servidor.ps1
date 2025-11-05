# Script para iniciar o servidor ADK
# Para a porta 8001 se estiver em uso
Write-Host "Verificando porta 8001..." -ForegroundColor Cyan

$porta = netstat -ano | findstr :8001
if ($porta) {
    Write-Host "Porta 8001 em uso. Finalizando processo..." -ForegroundColor Yellow
    $pid = ($porta -split '\s+')[-1]
    taskkill /F /PID $pid 2>$null
    Start-Sleep -Seconds 1
}

# Verifica API Key
if (-not $env:GOOGLE_API_KEY) {
    Write-Host "[AVISO] GOOGLE_API_KEY nao configurada!" -ForegroundColor Yellow
    Write-Host "Configure com: `$env:GOOGLE_API_KEY='sua-chave'" -ForegroundColor Yellow
    Write-Host ""
    $apiKey = Read-Host "Digite sua GOOGLE_API_KEY (ou pressione Enter para continuar sem)"
    if ($apiKey) {
        $env:GOOGLE_API_KEY = $apiKey
        Write-Host "API Key configurada!" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Iniciando servidor..." -ForegroundColor Cyan
Write-Host "Acesse: http://localhost:8001" -ForegroundColor Green
Write-Host ""

# Ativa venv e executa servidor
if (Test-Path "venv\Scripts\Activate.ps1") {
    & .\venv\Scripts\python.exe adk_web_server.py
} else {
    python adk_web_server.py
}
