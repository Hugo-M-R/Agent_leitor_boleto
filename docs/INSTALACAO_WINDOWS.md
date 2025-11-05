# 🔧 Guia de Instalação - Windows

## ✅ Status das Dependências

**Todas as dependências principais estão instaladas!**
- ✅ `google-generativeai`
- ✅ `easyocr` (opcional)
- ✅ `pytesseract`
- ✅ `PyMuPDF` (fitz)
- ✅ `python-dotenv`
- ✅ `fastapi` e `uvicorn`

**✅ Verificação completa:** Todos os módulos estão funcionando!

## 🚀 Como Executar

### 1. Configure a API Key (se ainda não fez)

```powershell
$env:GOOGLE_API_KEY='sua-chave-aqui'
```

### 2. Execute o servidor (interface visual)

```powershell
python adk\web_server.py
```

### 3. Acesse no navegador

**http://localhost:8001**

## 📋 Instalação Completa (se necessário)

Se precisar instalar tudo do zero:

```powershell
# Instalar versão mínima (sem easyocr)
pip install -r requirements-minimal.txt

# Instalar easyocr separadamente (opcional)
pip install easyocr
```

## ⚠️ Problemas Comuns

### Erro ao instalar easyocr

**Solução:** O easyocr é opcional! O sistema funciona com Tesseract:

```powershell
pip install -r requirements-minimal.txt
```

### Erro: "GOOGLE_API_KEY não encontrada"

**Solução:**
```powershell
# Para esta sessão
$env:GOOGLE_API_KEY='sua-chave'

# Ou crie arquivo .env
echo "GOOGLE_API_KEY=sua-chave" > .env
```

### Erro ao importar módulos

**Solução:** Certifique-se de estar no ambiente virtual:

```powershell
# Ativar venv
.\venv\Scripts\Activate.ps1

# Verificar instalações
pip list
```

## 🎯 Próximos Passos

1. ✅ Dependências instaladas
2. ⏳ Configure GOOGLE_API_KEY
3. ⏳ Execute: `python adk\web_server.py`
4. ⏳ Acesse: http://localhost:8001

## 💡 Dica

Se tiver problemas com easyocr, use apenas o Tesseract. O código já tem fallback automático.
