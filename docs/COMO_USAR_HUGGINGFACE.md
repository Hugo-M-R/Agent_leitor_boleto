# Como Usar Hugging Face API no Projeto

## 🚀 Configuração Rápida

### 1. Instalar Dependência

```powershell
pip install huggingface_hub
```

Ou instale todas as dependências:

```powershell
pip install -r requirements.txt
```

### 2. Obter Chave da API

1. Acesse: https://huggingface.co/settings/tokens
2. Faça login (ou crie uma conta gratuita)
3. Clique em "New token"
4. Dê um nome (ex: "ocr-agent")
5. Selecione permissões: "Read" (suficiente para Inference API)
6. Clique em "Generate token"
7. **Copie a chave** (ela só aparece uma vez!)

### 3. Configurar Variável de Ambiente

#### Windows PowerShell:

```powershell
$env:HUGGINGFACE_API_KEY='hf_sua-chave-aqui'
```

Ou use `HF_TOKEN` (também funciona):

```powershell
$env:HF_TOKEN='hf_sua-chave-aqui'
```

#### Linux/Mac:

```bash
export HUGGINGFACE_API_KEY='hf_sua-chave-aqui'
```

#### Ou criar arquivo `.env` na raiz do projeto:

```env
HUGGINGFACE_API_KEY=hf_sua-chave-aqui
```

**⚠️ IMPORTANTE:** Adicione `.env` ao `.gitignore` para não commitar a chave!

### 4. Iniciar o Servidor

```powershell
python -m uvicorn adk.web_server:app --host 0.0.0.0 --port 8001
```

Você deve ver:

```
[OK] Agent ADK inicializado com HUGGINGFACE!
✅ Hugging Face mistralai/Mistral-7B-Instruct-v0.2 configurado!
```

## 🎯 Como Funciona a Auto-Detecção

O código detecta automaticamente qual API usar na seguinte ordem:

1. **Hugging Face** (se `HUGGINGFACE_API_KEY` ou `HF_TOKEN` estiver configurada)
2. **OpenAI** (se `OPENAI_API_KEY` estiver configurada)
3. **Gemini** (se `GOOGLE_API_KEY` estiver configurada)

**Prioridade:** Hugging Face > OpenAI > Gemini

## 📋 Modelos Disponíveis

O código tenta usar estes modelos em ordem:

1. `mistralai/Mistral-7B-Instruct-v0.2` ⭐ (Recomendado)
2. `meta-llama/Llama-2-7b-chat-hf`
3. `google/flan-t5-large`
4. `microsoft/Phi-3-mini-4k-instruct`

Se nenhum funcionar, usa o modelo padrão do Hugging Face.

## ✅ Verificar se Está Funcionando

### Teste 1: Verificar Variável

```powershell
# Windows
echo $env:HUGGINGFACE_API_KEY

# Linux/Mac
echo $HUGGINGFACE_API_KEY
```

### Teste 2: Iniciar Servidor

```powershell
python -m uvicorn adk.web_server:app --host 0.0.0.0 --port 8001
```

Procure por:
```
✅ Hugging Face mistralai/Mistral-7B-Instruct-v0.2 configurado!
```

### Teste 3: Acessar Interface

Abra no navegador: http://localhost:8001

Envie uma mensagem de teste e veja se o agente responde.

## 🔧 Forçar Uso de Hugging Face

Se você tiver múltiplas APIs configuradas e quiser forçar Hugging Face:

```python
from adk.adk_agent import OCRAgent

agent = OCRAgent(provider="huggingface")
```

## 🐛 Troubleshooting

### Erro: "Hugging Face não está instalado"

```powershell
pip install huggingface_hub
```

### Erro: "HUGGINGFACE_API_KEY não encontrada"

Verifique se a variável está configurada:

```powershell
# Windows
echo $env:HUGGINGFACE_API_KEY

# Se vazio, configure:
$env:HUGGINGFACE_API_KEY='hf_sua-chave-aqui'
```

### Erro: "Modelo não disponível"

O código tenta automaticamente outros modelos. Se todos falharem:

1. Verifique se sua chave tem permissão de leitura
2. Verifique se o modelo existe: https://huggingface.co/models
3. Tente usar um modelo específico (veja seção abaixo)

### Erro: "Rate limit exceeded"

Hugging Face tem limite de ~30 requisições/minuto no tier gratuito.

**Solução:** Aguarde alguns segundos e tente novamente.

## 🎨 Usar Modelo Específico

Se quiser usar um modelo específico, você pode modificar o código em `adk/adk_agent.py`:

```python
# Na função _init_huggingface, altere a lista:
model_names = [
    "seu-modelo-preferido-aqui",  # Adicione no início
    "mistralai/Mistral-7B-Instruct-v0.2",
    # ...
]
```

## 📊 Limites do Tier Gratuito

- ✅ **30.000 requisições/mês**
- ✅ **~30 requisições/minuto** (rate limit)
- ✅ **Sem necessidade de cartão de crédito**
- ✅ **Modelos open-source gratuitos**

## 🔗 Links Úteis

- **Obter chave:** https://huggingface.co/settings/tokens
- **Documentação:** https://huggingface.co/docs/huggingface_hub
- **Modelos disponíveis:** https://huggingface.co/models
- **Inference API:** https://huggingface.co/docs/api-inference

## 💡 Dicas

1. **Use `HF_TOKEN`** se preferir (também funciona)
2. **Adicione `.env` ao `.gitignore`** para não commitar chaves
3. **Monitore uso** em: https://huggingface.co/settings/billing
4. **Teste diferentes modelos** para encontrar o melhor para seu caso

## 📝 Exemplo Completo

```powershell
# 1. Instalar
pip install huggingface_hub

# 2. Configurar chave
$env:HUGGINGFACE_API_KEY='hf_sua-chave-aqui'

# 3. Iniciar servidor
python -m uvicorn adk.web_server:app --host 0.0.0.0 --port 8001

# 4. Acessar interface
# Abra: http://localhost:8001
```

Pronto! O agente agora usa Hugging Face gratuitamente! 🎉

