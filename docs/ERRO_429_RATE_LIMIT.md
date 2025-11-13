# Erro 429 RESOURCE_EXHAUSTED - Rate Limit do Google Gemini

## Problema

O erro `429 RESOURCE_EXHAUSTED` ocorre quando a API do Google Gemini atinge o limite de requisições (quota ou rate limit).

### Sintomas

- Validação parcial funciona (ex: linha digitável validada)
- Erro aparece no meio do processo
- Retorno vazio ou incompleto
- Mensagem: `429 RESOURCE_EXHAUSTED. Resource exhausted. Please try again later.`

### Logs Típicos

```
[DEBUG] linha_valida: 38090100060142992005905875050311112560000003735
ERROR - adk_web_server.py:1431 - Error in event_generator: 429 RESOURCE_EXHAUSTED
google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED
```

## Causas

1. **Quota diária/mensal excedida**
   - Limite de requisições por dia/mês atingido
   - Verifique na Google Cloud Console

2. **Rate limit (requisições por minuto)**
   - Muitas requisições em um curto período
   - O Gemini tem limites de requisições por minuto

3. **Múltiplas requisições simultâneas**
   - Vários usuários/testes ao mesmo tempo
   - Cada validação faz múltiplas chamadas ao LLM

## Soluções Imediatas

### 1. Aguardar e Tentar Novamente

**Solução mais simples:**
- Aguarde 1-2 minutos
- Tente novamente
- O rate limit geralmente é resetado rapidamente

### 2. Verificar Quota na Google Cloud Console

1. Acesse: https://console.cloud.google.com/
2. Vá em "APIs & Services" > "Quotas"
3. Procure por "Generative AI API" ou "Gemini API"
4. Verifique se há limites atingidos

### 3. Reduzir Frequência de Requisições

- Evite múltiplas validações em sequência rápida
- Implemente um delay entre requisições
- Limite o número de usuários simultâneos

## Soluções de Código

### 1. Implementar Retry com Backoff

O Google ADK já tem retry automático, mas você pode adicionar delays:

```python
import asyncio
import time

async def chat_with_retry(message: str, max_retries=3):
    for attempt in range(max_retries):
        try:
            events = await runner.run_debug(message, quiet=True, verbose=False)
            return events
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 30  # 30s, 60s, 90s
                print(f"Rate limit atingido. Aguardando {wait_time}s antes de tentar novamente...")
                await asyncio.sleep(wait_time)
                continue
            raise
```

### 2. Cache de Validações

Evite validar o mesmo boleto múltiplas vezes:

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def validate_boleto_cached(linha_digitavel_hash: str):
    # Validação aqui
    pass
```

### 3. Usar Modelo Alternativo

Se disponível, use um modelo com maior quota:

```python
root_agent = Agent(
    model='gemini-1.5-flash',  # Pode ter quota diferente
    # ...
)
```

## Prevenção

### 1. Monitorar Uso da API

- Configure alertas na Google Cloud Console
- Monitore métricas de quota

### 2. Implementar Rate Limiting no Código

```python
from collections import deque
import time

class RateLimiter:
    def __init__(self, max_calls=10, period=60):
        self.calls = deque()
        self.max_calls = max_calls
        self.period = period
    
    def can_call(self):
        now = time.time()
        # Remove chamadas antigas
        while self.calls and self.calls[0] < now - self.period:
            self.calls.popleft()
        
        if len(self.calls) >= self.max_calls:
            return False
        
        self.calls.append(now)
        return True
```

### 3. Mensagens de Erro Amigáveis

O código já foi atualizado para retornar mensagens claras quando ocorre erro 429:

```json
{
  "ok": false,
  "error": "rate_limit",
  "message": "Limite de requisições da API do Google Gemini atingido. Por favor, aguarde alguns minutos e tente novamente.",
  "suggestion": "Aguarde 1-2 minutos e tente novamente."
}
```

## Verificação de Quota

### Via Google Cloud Console

1. Acesse: https://console.cloud.google.com/
2. Selecione seu projeto
3. Vá em "APIs & Services" > "Dashboard"
4. Procure por "Generative Language API" ou "Vertex AI API"
5. Verifique métricas de uso

### Via CLI

```bash
gcloud services list --enabled | grep -i gemini
gcloud alpha services quota list --service=generativelanguage.googleapis.com
```

## Limites Típicos do Gemini

- **Free Tier**: ~15 requisições por minuto (RPM)
- **Paid Tier**: Varia conforme plano
- **Quota diária**: Depende do plano contratado

**Nota:** Limites podem variar. Consulte a documentação oficial do Google.

## Referências

- [Google Gemini Rate Limits](https://ai.google.dev/pricing)
- [Error Code 429 Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/error-code-429)
- [Google Cloud Quotas](https://cloud.google.com/apis/design/quotas)

## Resumo Rápido

✅ **Solução Imediata**: Aguarde 1-2 minutos e tente novamente

✅ **Solução de Código**: Tratamento de erro 429 já implementado no endpoint `/chat`

✅ **Prevenção**: Monitore quota, implemente rate limiting, use cache

✅ **Verificação**: Google Cloud Console > APIs & Services > Quotas

