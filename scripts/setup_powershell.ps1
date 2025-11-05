# Script de configuração para PowerShell
# Configure a API Key do Google Gemini

Write-Host "🔧 Configurando Agent OCR com Google ADK" -ForegroundColor Cyan
Write-Host ""

# Solicita API Key
$apiKey = Read-Host "Digite sua GOOGLE_API_KEY (ou pressione Enter para usar a atual)"

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    $apiKey = $env:GOOGLE_API_KEY
    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        Write-Host "❌ API Key não encontrada!" -ForegroundColor Red
        Write-Host "   Configure manualmente: " -ForegroundColor Yellow
        Write-Host "   `$env:GOOGLE_API_KEY='sua-chave-aqui'" -ForegroundColor Yellow
        exit 1
    }
}

# Configura para a sessão atual
$env:GOOGLE_API_KEY = $apiKey

# Opção para configurar permanentemente
$permanente = Read-Host "Deseja configurar permanentemente? (S/N)"

if ($permanente -eq "S" -or $permanente -eq "s") {
    [System.Environment]::SetEnvironmentVariable('GOOGLE_API_KEY', $apiKey, 'User')
    Write-Host "✅ API Key configurada permanentemente!" -ForegroundColor Green
} else {
    Write-Host "✅ API Key configurada para esta sessão!" -ForegroundColor Green
}

Write-Host ""
Write-Host "📝 Próximos passos:" -ForegroundColor Cyan
Write-Host "   1. Execute: python adk_web_server.py" -ForegroundColor White
Write-Host "   2. Acesse: http://localhost:8001" -ForegroundColor White
Write-Host ""
