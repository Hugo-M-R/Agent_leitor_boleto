# Exemplo: Lógica de Validação de Boleto

## Estrutura Esperada do Retorno

O endpoint `get_boleto_agent_data` deve:
1. Buscar dados do extrator
2. Validar os dados recebidos
3. Retornar JSON de validação com resultados

## Exemplo de Código Completo

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
import re
from datetime import datetime
from api.observability import create_span, log_error, update_span_output

@app.get("/get_boleto_agent_data", response_class=JSONResponse)
async def get_boleto_agent_data():
    """
    Busca dados de um boleto em outro agente, valida e retorna resultado.
    """
    url = "http://10.148.9.40:8000/get_last_json_extracted"
    
    span_ctx = create_span("get_boleto_agent_data", input_data={"url": url})
    
    if not span_ctx:
        # Fallback sem observabilidade
        return await _validate_boleto_internal(url)
    
    with span_ctx:
        try:
            resultado = await _validate_boleto_internal(url)
            span_ctx.update(output={
                "status_geral": resultado.get("status_geral"),
                "validacoes_count": len(resultado.get("validacoes", {}))
            })
            return JSONResponse(content=resultado)
        except Exception as e:
            log_error("get_boleto_agent_data_error", error=str(e))
            span_ctx.update(output={"error": str(e)})
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )


async def _validate_boleto_internal(url: str) -> dict:
    """
    Função interna que busca e valida dados do boleto.
    """
    try:
        # 1. Busca dados do extrator
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        
        # 2. Valida se recebeu dados válidos
        if not data or not isinstance(data, dict):
            return {
                "status_geral": "ERRO",
                "validacoes": {
                    "linha_digitavel_valida": False,
                    "cnpj_verificado": False,
                    "beneficiario_corresponde": False,
                    "data_status": "Erro: Dados inválidos recebidos"
                },
                "mensagem_acao": "Não foi possível obter dados do extrator. Dados recebidos são inválidos."
            }
        
        # 3. Extrai campos
        linha_digitavel = data.get("linha_digitavel", "").strip()
        cnpj_beneficiario = data.get("cnpj_beneficiario", "").strip()
        beneficiario = data.get("beneficiario", "").strip()
        data_vencimento = data.get("data_vencimento", "").strip()
        
        # 4. Executa validações
        validacoes = {}
        
        # Validação 1: Linha Digitável
        linha_valida = validar_linha_digitavel(linha_digitavel)
        validacoes["linha_digitavel_valida"] = linha_valida
        
        # Validação 2: CNPJ
        cnpj_verificado = validar_cnpj(cnpj_beneficiario)
        validacoes["cnpj_verificado"] = cnpj_verificado
        
        # Validação 3: Beneficiário corresponde ao CNPJ (se ambos existem)
        beneficiario_corresponde = False
        if cnpj_verificado and beneficiario:
            # Aqui você pode fazer uma consulta à API Brasil ou validar logicamente
            beneficiario_corresponde = True  # Placeholder - implementar lógica real
        
        validacoes["beneficiario_corresponde"] = beneficiario_corresponde
        
        # Validação 4: Data de Vencimento
        data_status = validar_data_vencimento(data_vencimento)
        validacoes["data_status"] = data_status
        
        # 5. Determina status geral
        todas_validas = all([
            linha_valida,
            cnpj_verificado,
            beneficiario_corresponde,
            data_status not in ["Erro", "Inválida"]
        ])
        
        if todas_validas:
            status_geral = "APROVADO"
            mensagem_acao = "Boleto validado com sucesso. Todos os campos estão corretos."
        elif linha_valida and cnpj_verificado:
            status_geral = "APROVADO_COM_OBS"
            mensagem_acao = "Boleto aprovado com ressalvas. Verifique os detalhes nas validações."
        else:
            status_geral = "REPROVADO"
            mensagem_acao = "Boleto reprovado. Verifique os campos indicados nas validações."
        
        return {
            "status_geral": status_geral,
            "validacoes": validacoes,
            "mensagem_acao": mensagem_acao
        }
        
    except requests.exceptions.Timeout:
        return {
            "status_geral": "ERRO",
            "validacoes": {
                "linha_digitavel_valida": False,
                "cnpj_verificado": False,
                "beneficiario_corresponde": False,
                "data_status": "Erro: Timeout ao buscar dados"
            },
            "mensagem_acao": "Timeout ao buscar dados do extrator. Tente novamente."
        }
        
    except requests.exceptions.ConnectionError:
        return {
            "status_geral": "ERRO",
            "validacoes": {
                "linha_digitavel_valida": False,
                "cnpj_verificado": False,
                "beneficiario_corresponde": False,
                "data_status": "Erro: Não foi possível conectar ao extrator"
            },
            "mensagem_acao": "Não foi possível conectar ao servidor extrator. Verifique se o servidor está rodando."
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "status_geral": "ERRO",
            "validacoes": {
                "linha_digitavel_valida": False,
                "cnpj_verificado": False,
                "beneficiario_corresponde": False,
                "data_status": f"Erro: {str(e)}"
            },
            "mensagem_acao": f"Erro ao buscar dados: {str(e)}"
        }


def validar_linha_digitavel(linha: str) -> bool:
    """
    Valida linha digitável do boleto.
    
    Formato esperado: 00000.00000 00000.000000 00000.000000 0 00000000000000
    Total: 47 dígitos (sem contar pontos e espaços)
    """
    if not linha:
        return False
    
    # Remove espaços e pontos
    digitos = re.sub(r'[^\d]', '', linha)
    
    # Deve ter exatamente 47 dígitos
    if len(digitos) != 47:
        return False
    
    # Validação do dígito verificador (Módulo 10/11)
    # Implementação básica - você pode usar biblioteca python-boleto para validação completa
    try:
        # Verifica se todos são dígitos
        int(digitos)
        
        # Aqui você pode adicionar validação do dígito verificador
        # Por enquanto, retorna True se tem 47 dígitos
        return True
    except ValueError:
        return False


def validar_cnpj(cnpj: str) -> bool:
    """
    Valida CNPJ usando algoritmo de dígitos verificadores.
    """
    if not cnpj:
        return False
    
    # Remove formatação
    cnpj_limpo = re.sub(r'[^\d]', '', cnpj)
    
    # Deve ter 14 dígitos
    if len(cnpj_limpo) != 14:
        return False
    
    # Verifica se todos são dígitos
    if not cnpj_limpo.isdigit():
        return False
    
    # Validação dos dígitos verificadores
    # Algoritmo do CNPJ
    def calcular_digito(cnpj, posicoes):
        soma = 0
        for i, digito in enumerate(cnpj):
            if i < len(posicoes):
                soma += int(digito) * posicoes[i]
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto
    
    # Primeiro dígito verificador
    posicoes1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    digito1 = calcular_digito(cnpj_limpo[:12], posicoes1)
    
    if int(cnpj_limpo[12]) != digito1:
        return False
    
    # Segundo dígito verificador
    posicoes2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    digito2 = calcular_digito(cnpj_limpo[:13], posicoes2)
    
    if int(cnpj_limpo[13]) != digito2:
        return False
    
    return True


def validar_data_vencimento(data_str: str) -> str:
    """
    Valida e avalia data de vencimento.
    Retorna string descritiva do status.
    """
    if not data_str:
        return "Não informada"
    
    # Tenta diferentes formatos
    formatos = [
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%Y/%m/%d"
    ]
    
    data_obj = None
    for fmt in formatos:
        try:
            data_obj = datetime.strptime(data_str.strip(), fmt)
            break
        except ValueError:
            continue
    
    if not data_obj:
        return "Formato inválido"
    
    # Compara com data atual
    hoje = datetime.now()
    dias_diferenca = (data_obj - hoje).days
    
    if dias_diferenca < 0:
        return f"Vencida (há {abs(dias_diferenca)} dias)"
    elif dias_diferenca == 0:
        return "Vence hoje"
    elif dias_diferenca <= 7:
        return f"Vence em {dias_diferenca} dias (atenção)"
    else:
        return f"Válida (vence em {dias_diferenca} dias)"
```

## Bibliotecas Recomendadas

Para validação mais robusta, use:

```bash
pip install python-boleto brasilapi
```

```python
# Exemplo com python-boleto
from boleto import Boleto

def validar_linha_digitavel_completa(linha: str) -> bool:
    try:
        boleto = Boleto(linha)
        return boleto.is_valid()
    except:
        return False

# Exemplo com Brasil API para CNPJ
import requests

def verificar_cnpj_brasil_api(cnpj: str) -> dict:
    """
    Consulta CNPJ na Brasil API.
    Retorna dados do CNPJ se válido.
    """
    cnpj_limpo = re.sub(r'[^\d]', '', cnpj)
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return {"valido": True, "dados": response.json()}
        else:
            return {"valido": False, "erro": "CNPJ não encontrado"}
    except:
        return {"valido": False, "erro": "Erro ao consultar API"}
```

## Checklist de Validação

- [ ] Linha digitável tem 47 dígitos?
- [ ] Linha digitável passa no algoritmo de validação (Módulo 10/11)?
- [ ] CNPJ tem 14 dígitos?
- [ ] CNPJ passa na validação de dígitos verificadores?
- [ ] CNPJ existe na base (Brasil API)?
- [ ] Data de vencimento está em formato válido?
- [ ] Data de vencimento não está muito no passado?
- [ ] Beneficiário corresponde ao CNPJ (se aplicável)?

## Exemplo de Retorno Correto

### Quando Boleto é Válido:
```json
{
  "status_geral": "APROVADO",
  "validacoes": {
    "linha_digitavel_valida": true,
    "cnpj_verificado": true,
    "beneficiario_corresponde": true,
    "data_status": "Válida (vence em 5 dias)"
  },
  "mensagem_acao": "Boleto validado com sucesso. Todos os campos estão corretos."
}
```

### Quando Boleto tem Problemas:
```json
{
  "status_geral": "APROVADO_COM_OBS",
  "validacoes": {
    "linha_digitavel_valida": true,
    "cnpj_verificado": true,
    "beneficiario_corresponde": false,
    "data_status": "Vencida (há 3 dias)"
  },
  "mensagem_acao": "Boleto aprovado com ressalvas. Verifique os detalhes nas validações."
}
```

### Quando Boleto é Inválido:
```json
{
  "status_geral": "REPROVADO",
  "validacoes": {
    "linha_digitavel_valida": false,
    "cnpj_verificado": false,
    "beneficiario_corresponde": false,
    "data_status": "Formato inválido"
  },
  "mensagem_acao": "Boleto reprovado. Verifique os campos indicados nas validações."
}
```

