# Script de verificação de instalação
Write-Host "🔍 Verificando instalação..." -ForegroundColor Cyan
Write-Host ""

$erros = 0

# Verifica Python
Write-Host "Verificando Python..." -NoNewline
try {
    $pythonVersion = python --version 2>&1
    Write-Host " ✅ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host " ❌ Python não encontrado!" -ForegroundColor Red
    $erros++
}

# Verifica API Key
Write-Host "Verificando GOOGLE_API_KEY..." -NoNewline
if ($env:GOOGLE_API_KEY) {
    Write-Host " ✅ Configurada" -ForegroundColor Green
} else {
    Write-Host " ⚠️  Não configurada" -ForegroundColor Yellow
    Write-Host "   Configure com: `$env:GOOGLE_API_KEY='sua-chave'" -ForegroundColor Yellow
}

# Verifica módulos Python
Write-Host "Verificando módulos Python..." -ForegroundColor Cyan
$modulos = @(
    "fastapi",
    "uvicorn",
    "google.generativeai",
    "fitz",
    "pytesseract",
    "PIL",
    "dotenv"
)

foreach ($modulo in $modulos) {
    Write-Host "  $modulo..." -NoNewline
    $result = python -c "import $modulo" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✅" -ForegroundColor Green
    } else {
        Write-Host " ❌ Não instalado" -ForegroundColor Red
        $erros++
    }
}

Write-Host ""
if ($erros -eq 0) {
    Write-Host "✅ Tudo pronto! Execute: python adk_web_server.py" -ForegroundColor Green
} else {
    Write-Host "⚠️  Instale as dependências faltantes:" -ForegroundColor Yellow
    Write-Host "   pip install -r requirements-minimal.txt" -ForegroundColor Yellow
}
