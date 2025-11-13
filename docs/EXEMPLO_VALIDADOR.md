# Exemplo: Endpoint do Validador Corrigido

## Problema Identificado

O endpoint `get_boleto_agent_data` está retornando um JSON de validação (`status_geral`, `validacoes`) em vez de retornar o JSON recebido do extrator.

## Código Corrigido

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
from api.observability import create_span, log_error, update_span_output

@app.get("/get_boleto_agent_data", response_class=JSONResponse)
async def get_boleto_agent_data():
    """
    Busca dados de um boleto em outro agente. 
    Retorna o JSON recebido do extrator, sem modificações.
    """
    url = "http://10.148.9.40:8000/get_last_json_extracted"
    
    span_ctx = create_span("get_boleto_agent_data", input_data={"url": url})
    
    if not span_ctx:
        # Fallback se Langfuse desabilitado
        try:
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )
    
    with span_ctx:
        try:
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            
            # IMPORTANTE: Retorna o JSON recebido diretamente
            data = r.json()
            
            # Log apenas as chaves (sem dados sensíveis)
            keys = list(data.keys()) if isinstance(data, dict) else []
            span_ctx.update(output={"ok": True, "keys": keys[:20], "field_count": len(keys)})
            
            # Retorna o JSON recebido do extrator, sem modificações
            return JSONResponse(
                content=data,
                media_type="application/json; charset=utf-8"
            )
            
        except requests.exceptions.Timeout:
            error_msg = "Timeout ao buscar dados do agente extrator"
            log_error("get_boleto_agent_data_timeout", error=error_msg)
            span_ctx.update(output={"error": error_msg})
            return JSONResponse(
                status_code=504,
                content={"error": error_msg, "type": "timeout"}
            )
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Erro de conexão: {str(e)}"
            log_error("get_boleto_agent_data_connection_error", error=error_msg)
            span_ctx.update(output={"error": error_msg})
            return JSONResponse(
                status_code=503,
                content={"error": error_msg, "type": "connection_error"}
            )
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Erro HTTP: {str(e)}"
            log_error("get_boleto_agent_data_http_error", error=error_msg)
            span_ctx.update(output={"error": error_msg, "status_code": r.status_code})
            return JSONResponse(
                status_code=r.status_code,
                content={"error": error_msg, "status_code": r.status_code}
            )
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Erro na requisição: {str(e)}"
            log_error("get_boleto_agent_data_request_error", error=error_msg)
            span_ctx.update(output={"error": error_msg})
            return JSONResponse(
                status_code=500,
                content={"error": error_msg, "type": "request_error"}
            )
            
        except Exception as e:
            error_msg = f"Erro inesperado: {str(e)}"
            log_error("get_boleto_agent_data_unexpected_error", error=error_msg)
            span_ctx.update(output={"error": error_msg})
            return JSONResponse(
                status_code=500,
                content={"error": error_msg, "type": "unexpected_error"}
            )
```

## Pontos Importantes

1. **Retorna `data` diretamente**: O endpoint deve retornar o JSON recebido do extrator sem modificações
2. **Não processa/valida aqui**: Este endpoint apenas busca e retorna os dados
3. **Validação em outro lugar**: A validação (`status_geral`, `validacoes`) deve ser feita em outro endpoint ou função

## Estrutura Esperada

### JSON Recebido do Extrator:
```json
{
  "linha_digitavel": "38090.10006 01429.920059 05875.050311 1 12560000003735",
  "data_vencimento": "05/11/2025",
  "cnpj_beneficiario": "09.516.419/0001-75",
  "beneficiario": "PicPay Bank Banco Múltiplo S.A."
}
```

### JSON que NÃO deve ser retornado aqui:
```json
{
  "status_geral": "REPROVADO",
  "validacoes": {
    "linha_digitavel_valida": false,
    "cnpj_verificado": false,
    "beneficiario_corresponde": false,
    "data_status": "Não avaliado"
  },
  "mensagem_acao": "..."
}
```

## Verificação

Para verificar se está funcionando corretamente:

1. **Teste direto no extrator:**
```bash
curl http://10.148.9.40:8000/get_last_json_extracted
```

2. **Teste no validador:**
```bash
curl http://SEU_IP_VALIDADOR:PORTA/get_boleto_agent_data
```

3. **Compare os JSONs**: Devem ser idênticos (exceto campos internos filtrados)

## Debug

Adicione logs temporários para verificar:

```python
# No validador, antes de retornar:
print(f"[DEBUG] JSON recebido: {data}")
print(f"[DEBUG] Tipo: {type(data)}")
print(f"[DEBUG] Chaves: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
```

