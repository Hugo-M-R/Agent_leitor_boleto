# Troubleshooting: Problemas de Conexão entre Agentes

## Erro: ConnectionRefusedError / Nenhuma conexão pôde ser feita

### Sintomas
```
ConnectionRefusedError: [WinError 10061] Nenhuma conexão pôde ser feita porque a máquina de destino as recusou ativamente
```

### Causas Possíveis

1. **Servidor não está rodando**
   - O servidor da API (porta 8000) precisa estar ativo
   - Verifique se há um processo Python rodando na porta 8000

2. **Servidor rodando apenas em localhost**
   - O servidor precisa escutar em `0.0.0.0` para aceitar conexões externas
   - Verifique o comando de inicialização

3. **Firewall bloqueando conexão**
   - Windows Firewall pode estar bloqueando a porta 8000
   - Firewall de rede corporativa

4. **IP incorreto**
   - Verifique o IP do servidor
   - Use `ipconfig` (Windows) ou `ifconfig` (Linux/Mac) para verificar o IP

## Soluções

### 1. Verificar se o servidor está rodando

**No computador do servidor (onde roda a API):**

```powershell
# Verifica se há processo na porta 8000
netstat -ano | findstr :8000

# Se não houver nada, o servidor não está rodando
```

### 2. Iniciar o servidor corretamente

**No computador do servidor:**

```powershell
# Opção 1: Usar o script
.\scripts\iniciar_api.ps1

# Opção 2: Comando direto
python -m uvicorn api.agent:app --host 0.0.0.0 --port 8000

# Opção 3: Se estiver na raiz do projeto
cd C:\Users\Hugo\Desktop\ProjectGit\UserCase
python -m uvicorn api.agent:app --host 0.0.0.0 --port 8000
```

**IMPORTANTE:** O servidor DEVE usar `--host 0.0.0.0` para aceitar conexões de outros computadores.

### 3. Verificar IP do servidor

**No computador do servidor:**

```powershell
# Windows
ipconfig

# Procure por "IPv4 Address" na interface de rede ativa
# Exemplo: 10.148.9.47
```

### 4. Configurar Firewall do Windows

**No computador do servidor:**

```powershell
# Abrir porta 8000 no firewall (executar como Administrador)
New-NetFirewallRule -DisplayName "API OCR Port 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

Ou manualmente:
1. Abra "Firewall do Windows Defender"
2. Clique em "Configurações avançadas"
3. Clique em "Regras de Entrada" > "Nova Regra"
4. Selecione "Porta" > "TCP" > "8000"
5. Permita a conexão
6. Aplique para todos os perfis

### 5. Testar conexão local primeiro

**No computador do servidor:**

```powershell
# Teste se o servidor responde localmente
curl http://localhost:8000/
# ou
Invoke-RestMethod -Uri "http://localhost:8000/" -Method Get
```

Se funcionar localmente mas não de outro computador, o problema é firewall/rede.

### 6. Testar do computador validador

**No computador do validador:**

```powershell
# Substitua 10.148.9.47 pelo IP real do servidor
curl http://10.148.9.47:8000/
# ou
Invoke-RestMethod -Uri "http://10.148.9.47:8000/" -Method Get
```

### 7. Verificar logs do servidor

Quando o validador tentar conectar, você deve ver no servidor:

```
INFO:     10.148.9.47:59100 - "GET /get_last_json_extracted HTTP/1.1" 200 OK
```

Se não aparecer nada, a conexão não está chegando ao servidor (firewall/rede).

## Checklist Rápido

- [ ] Servidor está rodando? (`netstat -ano | findstr :8000`)
- [ ] Servidor está usando `--host 0.0.0.0`?
- [ ] Firewall permite porta 8000?
- [ ] IP do servidor está correto?
- [ ] Teste local funciona? (`curl http://localhost:8000/`)
- [ ] Teste remoto funciona? (`curl http://IP_SERVIDOR:8000/`)

## Comandos Úteis

```powershell
# Ver processos na porta 8000
netstat -ano | findstr :8000

# Ver IP do computador
ipconfig

# Testar conexão
Test-NetConnection -ComputerName 10.148.9.47 -Port 8000

# Ver regras de firewall
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*8000*"}
```

