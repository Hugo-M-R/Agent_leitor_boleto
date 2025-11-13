# Script para iniciar o servidor da API (porta 8000)
# Este servidor expõe os endpoints de OCR e extração de boletos

Write-Host "=== Iniciando Servidor API (OCR) ===" -ForegroundColor Cyan
Write-Host ""

# Verifica porta 8000
Write-Host "Verificando porta 8000..." -ForegroundColor Cyan
$porta = netstat -ano | findstr :8000
if ($porta) {
    Write-Host "Porta 8000 em uso. Finalizando processo..." -ForegroundColor Yellow
    $pid = ($porta -split '\s+')[-1]
    taskkill /F /PID $pid 2>$null
    Start-Sleep -Seconds 1
}

# Verifica se está no diretório correto
if (-not (Test-Path "api\agent.py")) {
    Write-Host "[ERRO] Execute este script da raiz do projeto!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Servidor será iniciado em:" -ForegroundColor Green
Write-Host "  - Local: http://localhost:8000" -ForegroundColor Green
Write-Host "  - Rede: http://0.0.0.0:8000 (aceita conexões externas)" -ForegroundColor Green
Write-Host ""
Write-Host "Endpoints disponíveis:" -ForegroundColor Yellow
Write-Host "  - GET  /get_last_json_extracted" -ForegroundColor White
Write-Host "  - POST /extract-boleto-fields" -ForegroundColor White
Write-Host "  - POST /extract" -ForegroundColor White
Write-Host "  - GET  /docs (Swagger UI)" -ForegroundColor White
Write-Host ""
Write-Host "Pressione CTRL+C para parar o servidor" -ForegroundColor Gray
Write-Host ""

# Ativa venv e executa servidor
if (Test-Path "venv\Scripts\Activate.ps1") {
    & .\venv\Scripts\python.exe -m uvicorn api.agent:app --host 0.0.0.0 --port 8000
} else {
    python -m uvicorn api.agent:app --host 0.0.0.0 --port 8000
}

