# Migração de Gemini para OpenAI

## 🚨 IMPORTANTE: Segurança de API Keys

**NUNCA compartilhe sua API key publicamente!** Se você já compartilhou uma chave:
1. Revogue imediatamente no painel da OpenAI
2. Crie uma nova chave
3. Configure usando variáveis de ambiente (veja abaixo)

## 📋 Como Configurar

### 1. Instalar Dependências

```bash
pip install openai
```

Ou instale todas as dependências:

```bash
pip install -r requirements.txt
```

### 2. Configurar Variável de Ambiente

#### Windows PowerShell:

```powershell
$env:OPENAI_API_KEY='sk-proj-sua-chave-aqui'
```

#### Linux/Mac:

```bash
export OPENAI_API_KEY='sk-proj-sua-chave-aqui'
```

#### Ou criar arquivo `.env` na raiz do projeto:

```env
OPENAI_API_KEY=sk-proj-sua-chave-aqui
```

**⚠️ IMPORTANTE:** Adicione `.env` ao `.gitignore` para não commitar a chave!

### 3. Como Funciona a Auto-Detecção

O código agora detecta automaticamente qual API usar:

1. **Prioridade 1:** Se `OPENAI_API_KEY` estiver configurada → usa OpenAI
2. **Prioridade 2:** Se `GOOGLE_API_KEY` estiver configurada → usa Gemini
3. **Erro:** Se nenhuma estiver configurada → erro

### 4. Forçar um Provider Específico

Se você quiser forçar o uso de um provider específico:

```python
from adk.adk_agent import OCRAgent

# Força OpenAI
agent = OCRAgent(provider="openai")

# Força Gemini
agent = OCRAgent(provider="gemini")
```

## 🔄 Modelos Disponíveis

### OpenAI (prioridade de uso):

1. `gpt-4o-mini` - Mais barato, rápido (recomendado)
2. `gpt-4o` - Mais capaz
3. `gpt-4-turbo` - Alternativa
4. `gpt-3.5-turbo` - Fallback

### Gemini (se OpenAI não estiver disponível):

1. `gemini-2.0-flash-exp`
2. `gemini-pro`
3. `gemini-1.5-flash`
4. `gemini-1.5-pro`

## ✅ Verificar se Está Funcionando

```powershell
# Verificar se a variável está configurada
echo $env:OPENAI_API_KEY

# Iniciar servidor
python -m uvicorn adk.web_server:app --host 0.0.0.0 --port 8001
```

Você deve ver no log:
```
[OK] Agent ADK inicializado com OPENAI!
✅ OpenAI gpt-4o-mini configurado!
```

## 💰 Custos da OpenAI

- **gpt-4o-mini:** ~$0.15 por 1M tokens de entrada, ~$0.60 por 1M tokens de saída
- **gpt-4o:** ~$2.50 por 1M tokens de entrada, ~$10 por 1M tokens de saída
- **Créditos gratuitos:** Geralmente $5-10 ao criar conta

## 🔍 Troubleshooting

### Erro: "OpenAI não está instalado"

```bash
pip install openai
```

### Erro: "OPENAI_API_KEY não encontrada"

Verifique se a variável está configurada:

```powershell
# Windows
echo $env:OPENAI_API_KEY

# Linux/Mac
echo $OPENAI_API_KEY
```

### Erro: "Invalid API key"

1. Verifique se a chave está correta
2. Revogue a chave antiga se foi compartilhada
3. Crie uma nova chave em: https://platform.openai.com/api-keys

## 📚 Referências

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [OpenAI Pricing](https://openai.com/api/pricing/)
- [OpenAI API Keys](https://platform.openai.com/api-keys)

