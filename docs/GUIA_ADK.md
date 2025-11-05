# 🤖 Guia de Uso - Interface Visual com Google ADK

## 📋 Pré-requisitos

1. **API Key do Google Gemini**
   - Acesse: https://makersuite.google.com/app/apikey
   - Crie uma nova API key
   - Copie a chave gerada

2. **Configurar a API Key**

**Opção 1: Variável de ambiente (temporária - apenas nesta sessão)**

```powershell
# Windows PowerShell (recomendado)
$env:GOOGLE_API_KEY='sua-chave-aqui'

# Linux/Mac
export GOOGLE_API_KEY='sua-chave-aqui'

# Windows CMD
set GOOGLE_API_KEY=sua-chave-aqui
```

**Opção 2: Arquivo .env (permanente - recomendado)**

Crie um arquivo `.env` na raiz do projeto:
```
GOOGLE_API_KEY=sua-chave-aqui
```

**Opção 3: Variável de ambiente permanente no Windows**

```powershell
# Defina para o usuário atual (permanente)
[System.Environment]::SetEnvironmentVariable('GOOGLE_API_KEY', 'sua-chave-aqui', 'User')

# Ou para todo o sistema (requer admin)
[System.Environment]::SetEnvironmentVariable('GOOGLE_API_KEY', 'sua-chave-aqui', 'Machine')
```

## 🚀 Como Usar

### Opção 1: Interface Web Visual (Recomendado)

```bash
python adk/web_server.py
```

Acesse no navegador: **http://localhost:8001**

**Funcionalidades:**
- ✅ Interface visual de chat moderna
- ✅ Upload de arquivos (PDF/imagens)
- ✅ Conversação natural com o agent
- ✅ Respostas em tempo real

### Opção 2: CLI Interativo

```bash
python adk/adk_agent.py
```

**Comandos:**
- Digite mensagens para conversar
- Use "processar arquivo.pdf" para processar arquivos
- Digite "sair" para encerrar

## 💬 Exemplos de Uso

### Exemplo 1: Processar Boleto

```
Você: Processe este boleto e me diga o valor e vencimento
[Upload: boleto.pdf]

Agent: Analisando o boleto...
Encontrei os seguintes dados:
- Valor: R$ 200,00
- Vencimento: 27/06/2020
- Linha digitável: 04791.50104...
```

### Exemplo 2: Extrair Texto

```
Você: Extraia todo o texto deste documento
[Upload: documento.pdf]

Agent: Processando o documento...
Extraí texto de 3 páginas. O documento contém...
```

### Exemplo 3: Perguntas sobre Documento

```
Você: Qual é o nome do banco neste boleto?
[Upload: boleto.pdf]

Agent: Analisando o documento...
O banco identificado é: Banese (código 047)
```

## 🔧 Troubleshooting

### Erro: "GOOGLE_API_KEY não encontrada"

**Solução:** Configure a variável de ambiente conforme mostrado acima.

### Erro: "Google Generative AI não está instalado"

**Solução:**
```bash
pip install google-generativeai
```

### Interface não carrega

**Solução:** Verifique se a porta 8001 está livre:
```bash
# Linux/Mac
lsof -i :8001

# Windows
netstat -ano | findstr :8001
```

## 📝 Notas

- A primeira execução pode ser mais lenta (download de modelos)
- Arquivos grandes podem demorar para processar
- O agent mantém contexto da conversa
- Máximo de ~5000 caracteres por arquivo para o contexto do chat

## 🎯 Próximos Passos

1. Configure sua API key
2. Execute o servidor web
3. Comece a conversar e processar arquivos!
