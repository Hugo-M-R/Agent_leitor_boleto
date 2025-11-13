# Troubleshooting: Erro 429 Insufficient Quota OpenAI

## 🚨 Erro: `insufficient_quota`

```
Error code: 429 - You exceeded your current quota, please check your plan and billing details.
```

## 🔍 Causas Possíveis

### 1. Chave Compartilhada/Exposta

**Problema:** Se você compartilhou a chave publicamente (ex: em chat, código, etc.), outras pessoas podem ter usado e esgotado os créditos.

**Solução:**
1. Revogue a chave antiga: https://platform.openai.com/api-keys
2. Crie uma nova chave
3. Configure usando variáveis de ambiente (não commite no Git)

### 2. Conta Nova sem Créditos

**Problema:** Contas novas podem não ter créditos gratuitos ativados automaticamente.

**Solução:**
1. Acesse: https://platform.openai.com/account/billing
2. Verifique se há créditos disponíveis
3. Se não houver, adicione um método de pagamento (cartão)
4. Mesmo com cartão, você só paga se ultrapassar os créditos gratuitos

### 3. Créditos Esgotados

**Problema:** Os créditos gratuitos ($5-10) foram consumidos.

**Solução:**
1. Verifique uso: https://platform.openai.com/usage
2. Adicione créditos: https://platform.openai.com/account/billing
3. Configure limite de gastos para evitar surpresas

## ✅ Passos para Resolver

### Passo 1: Verificar Status da Conta

1. Acesse: https://platform.openai.com/account/billing
2. Verifique:
   - Créditos disponíveis
   - Histórico de uso
   - Método de pagamento configurado

### Passo 2: Verificar Uso da API

1. Acesse: https://platform.openai.com/usage
2. Veja:
   - Quantas requisições foram feitas
   - Quanto foi gasto
   - Quando os créditos foram esgotados

### Passo 3: Revogar e Criar Nova Chave

1. **Revogar chave antiga:**
   - https://platform.openai.com/api-keys
   - Clique em "Revoke" na chave exposta

2. **Criar nova chave:**
   - Clique em "Create new secret key"
   - Copie a chave (ela só aparece uma vez!)
   - Configure no ambiente:

```powershell
# Windows PowerShell
$env:OPENAI_API_KEY='sk-proj-sua-nova-chave-aqui'
```

### Passo 4: Adicionar Método de Pagamento (se necessário)

1. Acesse: https://platform.openai.com/account/billing
2. Clique em "Add payment method"
3. Adicione um cartão de crédito
4. Configure limite de gastos (ex: $10/mês)

**Nota:** Mesmo com cartão, você só paga se ultrapassar os créditos gratuitos. O cartão é necessário para ativar a conta.

### Passo 5: Verificar Limites de Rate

1. Acesse: https://platform.openai.com/account/limits
2. Verifique:
   - Rate limits (requisições por minuto)
   - Quotas de uso
   - Limites de tokens

## 🔄 Alternativas Temporárias

Se não conseguir resolver imediatamente, você pode:

### Opção 1: Usar Gemini (se tiver billing ativado)

```powershell
# Remove OpenAI e usa Gemini
$env:OPENAI_API_KEY=''
$env:GOOGLE_API_KEY='sua-chave-gemini'
```

### Opção 2: Criar Nova Conta OpenAI

1. Crie uma nova conta com email diferente
2. Use um cartão diferente (se necessário)
3. Obtenha novos créditos gratuitos

### Opção 3: Usar Modelos Locais (Ollama, etc.)

Para desenvolvimento/testes, considere modelos locais:
- Ollama (gratuito, local)
- Hugging Face Inference API (tier gratuito)

## 📊 Como Monitorar Uso

### Via Dashboard OpenAI

1. Acesse: https://platform.openai.com/usage
2. Configure alertas de uso
3. Defina limites de gastos

### Via Código (Opcional)

Adicione logging de uso:

```python
import openai

response = client.chat.completions.create(...)
print(f"Tokens usados: {response.usage.total_tokens}")
print(f"Custo estimado: ${response.usage.total_tokens * 0.0000015:.4f}")
```

## 💡 Prevenção

1. **Nunca compartilhe chaves publicamente**
2. **Use variáveis de ambiente** (não hardcode)
3. **Configure limites de gastos** no dashboard
4. **Monitore uso regularmente**
5. **Revogue chaves expostas imediatamente**

## 🔗 Links Úteis

- [OpenAI Billing](https://platform.openai.com/account/billing)
- [OpenAI Usage](https://platform.openai.com/usage)
- [OpenAI API Keys](https://platform.openai.com/api-keys)
- [OpenAI Pricing](https://openai.com/api/pricing/)
- [OpenAI Error Codes](https://platform.openai.com/docs/guides/error-codes)

## 📝 Resumo Rápido

✅ **Verificar:** https://platform.openai.com/account/billing  
✅ **Revogar chave exposta:** https://platform.openai.com/api-keys  
✅ **Criar nova chave:** https://platform.openai.com/api-keys  
✅ **Adicionar pagamento:** Se necessário para ativar conta  
✅ **Configurar limite:** Para evitar gastos inesperados  

