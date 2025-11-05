#!/bin/bash

# Script de setup para Google ADK Agent

echo "🚀 Configurando Agent OCR com Google ADK"
echo "=========================================="
echo ""

# Verifica Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado!"
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"
echo ""

# Instala dependências Python
echo "📦 Instalando dependências Python..."
pip install -r requirements.txt

echo ""
echo "🔑 Configuração da API Key do Google"
echo "======================================"
echo ""
echo "Você precisa de uma API key do Google (Gemini API)"
echo "Obtenha em: https://makersuite.google.com/app/apikey"
echo ""

read -p "Digite sua GOOGLE_API_KEY (ou pressione Enter para configurar depois): " api_key

if [ -n "$api_key" ]; then
    # Adiciona ao .env ou exporta
    if [ -f ".env" ]; then
        echo "GOOGLE_API_KEY=$api_key" >> .env
    else
        echo "GOOGLE_API_KEY=$api_key" > .env
    fi
    
    # Exporta para sessão atual
    export GOOGLE_API_KEY="$api_key"
    
    echo "✅ API Key configurada!"
else
    echo "⚠️  Configure manualmente:"
    echo "   export GOOGLE_API_KEY='sua-chave-aqui'"
    echo "   ou adicione ao arquivo .env"
fi

echo ""
echo "✅ Setup concluído!"
echo ""
echo "📝 Como usar:"
echo "   1. Interface Web: python adk_web_server.py"
echo "   2. CLI Interativo: python adk_agent.py"
echo ""
echo "   Acesse: http://localhost:8001"
