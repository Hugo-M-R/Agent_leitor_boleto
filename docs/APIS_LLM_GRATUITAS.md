# APIs de LLM Gratuitas e Alternativas

## 🆓 APIs com Tier Gratuito Generoso

### 1. **Hugging Face Inference API** ⭐ Recomendado

**Tier Gratuito:**
- ✅ 30.000 requisições/mês gratuitas
- ✅ Modelos open-source (Llama, Mistral, etc.)
- ✅ Sem necessidade de cartão de crédito
- ✅ Rate limit: ~30 req/min

**Como usar:**
```python
pip install huggingface_hub

from huggingface_hub import InferenceClient

client = InferenceClient(
    token="hf_sua-chave-aqui",  # Obter em: https://huggingface.co/settings/tokens
    model="mistralai/Mistral-7B-Instruct-v0.2"
)

response = client.text_generation(
    prompt="Seu prompt aqui",
    max_new_tokens=500
)
```

**Obter chave:** https://huggingface.co/settings/tokens

**Modelos populares:**
- `mistralai/Mistral-7B-Instruct-v0.2`
- `meta-llama/Llama-2-7b-chat-hf`
- `google/flan-t5-large`

---

### 2. **Cohere API**

**Tier Gratuito:**
- ✅ 100 requisições/minuto
- ✅ Sem limite mensal explícito (mas pode ter rate limits)
- ✅ Modelos: `command`, `command-light`

**Como usar:**
```python
pip install cohere

import cohere

co = cohere.Client("sua-chave-aqui")  # Obter em: https://dashboard.cohere.com/api-keys

response = co.generate(
    model='command',
    prompt='Seu prompt aqui',
    max_tokens=500
)
```

**Obter chave:** https://dashboard.cohere.com/api-keys

---

### 3. **Anthropic Claude** (já mencionado, mas detalhando)

**Tier Gratuito:**
- ⚠️ Não tem tier gratuito permanente
- ✅ Pode oferecer créditos promocionais ($5-10)
- ✅ Requer cartão para ativar (mas não cobra até usar créditos)

**Como usar:**
```python
pip install anthropic

import anthropic

client = anthropic.Anthropic(
    api_key="sua-chave-aqui"  # Obter em: https://console.anthropic.com/settings/keys
)

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Seu prompt aqui"}]
)
```

**Obter chave:** https://console.anthropic.com/settings/keys

---

### 4. **Groq API** ⭐ Muito Rápido

**Tier Gratuito:**
- ✅ 14.400 requisições/dia (muito generoso!)
- ✅ Modelos Llama, Mistral, Mixtral
- ✅ Extremamente rápido (inferência rápida)
- ✅ Sem necessidade de cartão

**Como usar:**
```python
pip install groq

from groq import Groq

client = Groq(api_key="sua-chave-aqui")  # Obter em: https://console.groq.com/keys

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Seu prompt aqui"
        }
    ],
    model="llama-3.1-70b-versatile"  # ou mistral-large, mixtral-8x7b
)
```

**Obter chave:** https://console.groq.com/keys

**Modelos disponíveis:**
- `llama-3.1-70b-versatile`
- `llama-3.1-8b-instant`
- `mistral-large-2402`
- `mixtral-8x7b-32768`

---

### 5. **Together AI**

**Tier Gratuito:**
- ✅ $25 em créditos gratuitos ao criar conta
- ✅ Modelos Llama, Mistral, Mixtral
- ✅ Requer cartão (mas não cobra até usar créditos)

**Como usar:**
```python
pip install together

import together

together.api_key = "sua-chave-aqui"  # Obter em: https://api.together.xyz/settings/api-keys

output = together.Complete.create(
    prompt="Seu prompt aqui",
    model="mistralai/Mixtral-8x7B-Instruct-v0.1",
    max_tokens=512
)
```

**Obter chave:** https://api.together.xyz/settings/api-keys

---

### 6. **Replicate** (Modelos Open-Source)

**Tier Gratuito:**
- ✅ $5 em créditos gratuitos
- ✅ Modelos open-source (Llama, Stable Diffusion, etc.)
- ✅ Pay-as-you-go após créditos

**Como usar:**
```python
pip install replicate

import replicate

output = replicate.run(
    "meta/llama-2-70b-chat",
    input={"prompt": "Seu prompt aqui"}
)
```

**Obter chave:** https://replicate.com/account/api-tokens

---

### 7. **Perplexity AI**

**Tier Gratuito:**
- ✅ 5 requisições/dia no tier gratuito
- ✅ Modelo com busca na web integrada
- ⚠️ Limite muito baixo

**Como usar:**
```python
pip install perplexity-ai

from perplexity import Perplexity

client = Perplexity(api_key="sua-chave-aqui")  # Obter em: https://www.perplexity.ai/settings/api

response = client.chat.completions.create(
    model="llama-3-sonar-large-32k-online",
    messages=[{"role": "user", "content": "Seu prompt aqui"}]
)
```

**Obter chave:** https://www.perplexity.ai/settings/api

---

### 8. **Fireworks AI**

**Tier Gratuito:**
- ✅ $5 em créditos gratuitos
- ✅ Modelos Llama, Mistral
- ✅ Requer cartão

**Como usar:**
```python
pip install fireworks-ai

from fireworks.client import Fireworks

client = Fireworks(api_key="sua-chave-aqui")  # Obter em: https://fireworks.ai/settings/api-keys

response = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3-70b-instruct",
    messages=[{"role": "user", "content": "Seu prompt aqui"}]
)
```

**Obter chave:** https://fireworks.ai/settings/api-keys

---

## 🏆 Recomendações por Caso de Uso

### Para Desenvolvimento/Testes:
1. **Groq** - Mais rápido, 14k req/dia
2. **Hugging Face** - 30k req/mês, muitos modelos
3. **Cohere** - 100 req/min, sem limite mensal explícito

### Para Produção (com budget):
1. **OpenAI** - Melhor qualidade, mas pago
2. **Anthropic Claude** - Excelente qualidade
3. **Together AI** - $25 créditos iniciais

### Para Modelos Open-Source:
1. **Hugging Face** - Maior variedade
2. **Groq** - Mais rápido
3. **Replicate** - Fácil de usar

---

## 📊 Comparação Rápida

| API | Tier Gratuito | Requer Cartão | Velocidade | Qualidade |
|-----|---------------|---------------|------------|-----------|
| **Groq** | 14.4k/dia | ❌ Não | ⚡⚡⚡ Muito rápido | ⭐⭐⭐ Boa |
| **Hugging Face** | 30k/mês | ❌ Não | ⚡⚡ Rápido | ⭐⭐⭐ Boa |
| **Cohere** | 100/min | ❌ Não | ⚡⚡ Rápido | ⭐⭐⭐ Boa |
| **Together AI** | $25 créditos | ✅ Sim | ⚡⚡ Rápido | ⭐⭐⭐ Boa |
| **Replicate** | $5 créditos | ✅ Sim | ⚡ Normal | ⭐⭐⭐ Boa |
| **Perplexity** | 5/dia | ❌ Não | ⚡ Normal | ⭐⭐⭐⭐ Excelente (com web) |

---

## 🔧 Integração no Seu Código

### Exemplo: Adicionar Groq como Alternativa

```python
# adk/adk_agent.py

# Adicionar import
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    Groq = None
    GROQ_AVAILABLE = False

# No __init__:
def _init_groq(self, api_key: Optional[str]):
    """Inicializa cliente Groq"""
    if not GROQ_AVAILABLE:
        raise ImportError("Groq não está instalado. Execute: pip install groq")
    
    self.client = Groq(api_key=api_key)
    self.model_name = "llama-3.1-70b-versatile"
    logger.info(f"✅ Groq {self.model_name} configurado!")

# No chat:
if self.provider == "groq":
    response = self.client.chat.completions.create(
        model=self.model_name,
        messages=messages,
        temperature=0.7,
    )
    response_text = response.choices[0].message.content
```

---

## 🔗 Links Rápidos

- **Groq:** https://console.groq.com/keys
- **Hugging Face:** https://huggingface.co/settings/tokens
- **Cohere:** https://dashboard.cohere.com/api-keys
- **Together AI:** https://api.together.xyz/settings/api-keys
- **Replicate:** https://replicate.com/account/api-tokens
- **Fireworks:** https://fireworks.ai/settings/api-keys
- **Perplexity:** https://www.perplexity.ai/settings/api

---

## 💡 Dica Final

Para seu caso de uso (OCR e extração de boletos), recomendo:

1. **Groq** - Mais rápido, muito generoso (14k/dia)
2. **Hugging Face** - 30k/mês, muitos modelos
3. **Cohere** - Sem limite mensal explícito

Todos são gratuitos e não requerem cartão de crédito!

