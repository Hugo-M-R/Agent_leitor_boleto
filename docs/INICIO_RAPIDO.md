# 🚀 Início Rápido

## ✅ Tudo Pronto!

1. ✅ Dependências instaladas
2. ✅ Porta 8001 liberada
3. ✅ API Key configurada

## 🎯 Como Executar

### Opção 1: Script Automático (Recomendado)

```powershell
.\scripts\iniciar_servidor.ps1
```

### Opção 2: Manual

```powershell
# 1. Ativar venv (se ainda não ativou)
.\venv\Scripts\Activate.ps1

# 2. Configurar API Key (se necessário)
$env:GOOGLE_API_KEY='sua-chave-aqui'

# 3. Executar servidor (interface visual)
python adk\web_server.py
```

## 🌐 Acessar Interface

Depois que o servidor iniciar, acesse:

**http://localhost:8001**

## ⚠️ Se a Porta Estiver em Uso

```powershell
# Encontrar processo
netstat -ano | findstr :8001

# Finalizar processo (substitua PID pelo número encontrado)
taskkill /F /PID <PID>
```

## 💡 Dica

Para configurar a API key permanentemente, crie um arquivo `.env`:
```
GOOGLE_API_KEY=sua-chave-aqui
```

Ou use o script:
```powershell
.\scripts\setup_powershell.ps1
```
