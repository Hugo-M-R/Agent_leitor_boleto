# Agent de Transcrição OCR 🎯

Serviço de OCR (Reconhecimento Óptico de Caracteres) com extração automática de campos de boleto bancário. Inclui:
- API REST para OCR (FastAPI)
- Interface visual de chat integrando Google Gemini ("ADK")

## 📁 Estrutura do projeto

- `api/agent.py` — API REST (FastAPI) para OCR e extração de campos
- `adk/adk_agent.py` — Agente de chat usando Google Gemini
- `adk/web_server.py` — Interface web (chat) para conversar com o agente
- `scripts/` — Scripts utilitários (setup, iniciar servidor, verificação)
- `docs/` — Guias e instruções (GUIA_ADK, INICIO_RAPIDO, INSTALACAO_WINDOWS)

## 🚀 Funcionalidades

- ✅ OCR de PDFs e imagens (JPG, PNG, TIFF, BMP)
- ✅ Fallback automático: ocrmypdf → Tesseract → EasyOCR
- ✅ Extração de campos de boleto: linha digitável, valor, vencimento, banco, sacado, etc.
- ✅ Melhorias de OCR: múltiplas resoluções, processamento de imagem (contraste/sharpen)

## 📦 Instalação

### 1) Dependências do sistema (Linux)
```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-por tesseract-ocr-eng ocrmypdf
```

### 2) Python
```bash
pip install -r requirements.txt
```

### Instalação: completo vs minimal
- Completo (`requirements.txt`): inclui EasyOCR e todas as dependências.
```bash
pip install -r requirements.txt
```
- Minimal (`requirements-minimal.txt`): instala somente o essencial (sem EasyOCR). Indicado para Windows/instalação rápida.
```bash
pip install -r requirements-minimal.txt
# (opcional) adicionar EasyOCR depois
pip install easyocr
```

## 🧠 Configuração do Google Gemini ("ADK")

Defina a variável de ambiente `GOOGLE_API_KEY` (Windows PowerShell):
```powershell
$env:GOOGLE_API_KEY='sua-chave-aqui'
```
Ou crie um `.env` na raiz:
```
GOOGLE_API_KEY=sua-chave-aqui
```
O agente tenta os modelos nesta ordem e usa o primeiro disponível:
- `gemini-2.0-flash-exp` (preferido)
- `gemini-pro`
- `gemini-1.5-flash`
- `gemini-1.5-pro`

## 🏃 Como usar

### Opção 1: Interface Visual (recomendado)
```powershell
python adk/web_server.py
```
Acesse: http://localhost:8001

### Opção 2: API REST (OCR)
```powershell
uvicorn api.agent:app --host 0.0.0.0 --port 8000
```

### Endpoints da API
- `POST /extract` — OCR básico (PDF/imagem)
- `POST /extract-boleto` — OCR + extração de campos de boleto
- `POST /extract-from-path` — OCR apontando caminho local

Exemplo:
```bash
curl -X POST http://localhost:8000/extract-boleto \
  -F "file=@dados/Modelo-de-Boleto.pdf" \
  -F "lang=por+eng"
```

## 🔧 Scripts úteis
- `scripts/setup_powershell.ps1` — Configura GOOGLE_API_KEY no Windows
- `scripts/iniciar_servidor.ps1` — Libera porta 8001 e inicia interface web
- `scripts/setup_adk.sh` — Setup em Linux/macOS
- `scripts/verificar_instalacao.ps1` — Verifica dependências

## 🐛 Troubleshooting
- Tesseract/ocrmypdf ausentes: instale dependências do sistema
- Porta 8001 ocupada: finalize processo e reinicie (`scripts/iniciar_servidor.ps1`)
- PDF sem texto: o OCR força extração por imagem com múltiplas resoluções e filtros

## 📚 Documentação
- `docs/GUIA_ADK.md` — Interface visual com Gemini
- `docs/INICIO_RAPIDO.md` — Passo a passo rápido
- `docs/INSTALACAO_WINDOWS.md` — Guia Windows

## 📝 Licença
MIT

