# Langfuse e Configuração do Servidor ADK

## 📊 Como o Langfuse foi Aplicado

### 1. Arquitetura de Observabilidade

O Langfuse foi integrado de forma **centralizada** através do módulo `api/observability.py`, seguindo boas práticas de separação de responsabilidades.

#### Estrutura do Módulo de Observabilidade

```python
api/observability.py
├── Configuração (variáveis de ambiente)
├── Inicialização do cliente Langfuse
├── Funções de mascaramento de PII (mask_pii)
├── Context Managers (TraceContext, SpanContext)
├── Funções helper (create_trace, create_span)
└── Funções de log (log_error)
```

### 2. Configuração via Variáveis de Ambiente

O Langfuse é **opcional** e controlado pela variável `LANGFUSE_ENABLED`:

```python
LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "false").lower() in ("1", "true", "yes")
```

**Variáveis necessárias:**
- `LANGFUSE_ENABLED`: "true" para habilitar
- `LANGFUSE_PUBLIC_KEY`: Chave pública do Langfuse
- `LANGFUSE_SECRET_KEY`: Chave secreta do Langfuse
- `LANGFUSE_HOST`: URL do servidor Langfuse (ex: `https://us.cloud.langfuse.com`)

### 3. Proteção de Dados Sensíveis (PII Masking)

Antes de enviar dados ao Langfuse, informações sensíveis são **automaticamente mascaradas**:

```python
def mask_pii(value: str) -> str:
    # CNPJ (14 dígitos) → XX.XXX.XXX/XXXX-XX
    # CPF (11 dígitos) → XXX.XXX.XXX-XX
    # Linha digitável (≥20 dígitos) → 123456…789012
```

**Exemplo:**
- Input: `"09.516.419/0001-75"`
- Enviado ao Langfuse: `"XX.XXX.XXX/XXXX-75"`

### 4. Context Managers para Traces e Spans

O código usa **context managers** (`with` statement) para gerenciar automaticamente o ciclo de vida dos traces/spans:

```python
# Trace (operações de alto nível)
with create_trace("nome_operacao", input_data={...}):
    # código aqui
    pass

# Span (operações específicas dentro de um trace)
with create_span("nome_operacao", input_data={...}):
    # código aqui
    pass
```

**Vantagens:**
- ✅ Garante que traces/spans são finalizados corretamente
- ✅ Suporta async/await
- ✅ Tratamento automático de erros
- ✅ Flush automático dos dados

### 5. Integração na API REST (api/agent.py)

#### Middleware HTTP (Rastreamento Automático)

Todas as requisições HTTP são **automaticamente rastreadas**:

```43:72:api/agent.py
@app.middleware("http")
async def langfuse_http_tracing(request: Request, call_next):
    """Middleware para rastrear requisições HTTP no Langfuse"""
    if not is_enabled():
        return await call_next(request)
    
    trace_ctx = create_trace(
        name=f"HTTP {request.method} {request.url.path}",
        input_data={
            "path": request.url.path,
            "query": dict(request.query_params),
            "method": request.method,
        },
        metadata={"service": "ocr-service", "framework": "fastapi"}
    )
    
    async with trace_ctx:
        try:
            response = await call_next(request)
            trace_ctx.update(output={"status_code": response.status_code})
            return response
        except Exception as e:
            trace_ctx.update(output={"error": str(e)})
            log_error(f"HTTP {request.method} {request.url.path}: {e}")
            raise
```

**O que é rastreado:**
- ✅ Método HTTP (GET, POST, etc.)
- ✅ Caminho da URL
- ✅ Parâmetros de query
- ✅ Status code da resposta
- ✅ Erros (se houver)

#### Spans em Funções OCR

Cada função de OCR cria um **span** para rastrear sua execução:

```76:99:api/agent.py
def ocr_with_tesseract(image_bytes: bytes, lang: str = "por+eng") -> str:
    """Executa OCR usando Tesseract"""
    span_ctx = create_span(name="ocr_tesseract", input_data={"lang": lang})
    
    with span_ctx:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image, lang=lang)
            span_ctx.update(output={"chars": len(text)})
            return text.strip()
        except Exception as e:
            logger.error(f"Erro no Tesseract: {e}")
            log_error(f"ocr_tesseract_error: {e}")
            return ""
```

**Spans rastreados:**
- `ocr_tesseract`: OCR com Tesseract
- `ocr_easyocr`: OCR com EasyOCR
- `ocr_pdf`: Processamento de PDF
- `extract_boleto_fields`: Extração de campos de boleto

### 6. Integração no Agente ADK (adk/adk_agent.py)

#### Trace de Conversação

Cada conversa com o agente cria um **trace** principal:

```267:273:adk/adk_agent.py
trace_ctx = create_trace(name="adk_chat", input_data={"message": message[:200]})

if not trace_ctx:
    # Fallback se Langfuse desabilitado
    return await self._chat_internal(message, file_path)

with trace_ctx:
    # ... processamento ...
```

#### Span de Geração do Gemini

Cada chamada ao modelo Gemini cria um **span** dentro do trace:

```313:337:adk/adk_agent.py
gen_span_ctx = create_span(
    name="gemini_generate",
    input_data={
        "model": self.model_name,
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 40
    }
)

with gen_span_ctx:
    response = self.model.generate_content(full_message, ...)
    response_text = response.text
    gen_span_ctx.update(output={"response_preview": response_text[:500]})
```

**Hierarquia de rastreamento:**
```
Trace: adk_chat
  └─ Span: gemini_generate
      └─ Input: mensagem do usuário
      └─ Output: preview da resposta (500 chars)
```

### 7. Fallback Gracioso

Se o Langfuse estiver **desabilitado ou falhar**, o código continua funcionando normalmente:

```python
span_ctx = create_span(...)
if not span_ctx:
    # Executa sem rastreamento
    return processar_sem_observabilidade()
    
with span_ctx:
    # Executa com rastreamento
    return processar_com_observabilidade()
```

---

## 🖥️ Como o Servidor ADK foi Configurado

### 1. Estrutura do Servidor (adk/web_server.py)

O servidor ADK é uma aplicação **FastAPI** que fornece:
- Interface web de chat (HTML/JavaScript)
- WebSocket para comunicação em tempo real
- Endpoints REST para upload de arquivos
- Integração com o agente OCR

### 2. Inicialização do Servidor

#### Lifespan Handler

O servidor usa um **lifespan handler** para inicializar recursos na startup:

```37:56:adk/web_server.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler para inicializar e limpar recursos"""
    global agent
    
    # Startup
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            agent = OCRAgent(api_key=api_key)
            print("[OK] Agent ADK inicializado!")
        except Exception as e:
            print(f"[ERRO] Erro ao inicializar agent: {e}")
    else:
        print("[AVISO] GOOGLE_API_KEY nao configurada. Configure a variavel de ambiente.")
    
    yield
    
    # Shutdown (limpeza se necessário)
    pass
```

**O que acontece na startup:**
1. ✅ Carrega variáveis de ambiente (`.env` via `python-dotenv`)
2. ✅ Lê `GOOGLE_API_KEY`
3. ✅ Inicializa `OCRAgent` com a API key
4. ✅ Armazena instância globalmente

#### Criação da Aplicação FastAPI

```59:59:adk/web_server.py
app = FastAPI(title="Agent OCR - Interface ADK", lifespan=lifespan)
```

### 3. Interface Web de Chat

#### HTML/JavaScript Integrado

O servidor retorna uma **interface HTML completa** no endpoint raiz (`/`):

```62:65:adk/web_server.py
@app.get("/", response_class=HTMLResponse)
async def get_chat_interface():
    """Retorna interface HTML do chat"""
    return """<!DOCTYPE html>..."""
```

**Características da interface:**
- ✅ Design moderno com gradiente roxo
- ✅ Chat em tempo real via WebSocket
- ✅ Upload de arquivos (drag & drop)
- ✅ Renderização de Markdown (via `marked.js`)
- ✅ Histórico de conversas
- ✅ Indicadores visuais (loading, erros)

#### Renderização de Markdown

A interface usa **marked.js** para renderizar respostas do agente:

```72:72:adk/web_server.py
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
```

```javascript
// No JavaScript da interface
const html = marked.parse(text);  // Converte Markdown → HTML
element.innerHTML = html;          // Renderiza
```

### 4. WebSocket para Chat em Tempo Real

O servidor implementa **WebSocket** para comunicação bidirecional:

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # ... processamento de mensagens ...
```

**Funcionalidades:**
- ✅ Aceita conexões WebSocket
- ✅ Processa mensagens do cliente
- ✅ Envia respostas do agente em tempo real
- ✅ Suporta upload de arquivos via WebSocket
- ✅ Tratamento de erros e desconexões

### 5. Endpoints REST

#### Upload de Arquivo

```python
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), message: str = Form("")):
    # Salva arquivo temporariamente
    # Processa com o agente
    # Retorna resposta
```

#### Health Check

```521:527:adk/web_server.py
@app.get("/health")
async def health():
    """Endpoint de health check"""
    return {
        "status": "ok",
        "agent_ready": agent is not None
    }
```

### 6. Configuração de Encoding (Windows)

O servidor configura **encoding UTF-8** para Windows:

```18:22:adk/web_server.py
# Configura encoding UTF-8 para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")
```

### 7. Execução do Servidor

#### Via Uvicorn (Padrão)

```530:532:adk/web_server.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

**Porta padrão:** `8001`

#### Via Script PowerShell

```powershell
# scripts/iniciar_servidor.ps1
python -m uvicorn adk.web_server:app --host 0.0.0.0 --port 8001
```

### 8. Integração com o Agente OCR

O servidor usa a classe `OCRAgent` do módulo `adk/adk_agent.py`:

```31:34:adk/web_server.py
from adk.adk_agent import OCRAgent

# Instância global do agent (será inicializada na startup)
agent: Optional[OCRAgent] = None
```

**Fluxo de processamento:**
1. Usuário envia mensagem/arquivo via WebSocket ou REST
2. Servidor recebe e valida
3. Chama `agent.chat(message, file_path)`
4. Agente processa com Gemini
5. Servidor retorna resposta ao cliente

---

## 📋 Resumo da Configuração

### Langfuse

| Componente | Localização | Função |
|------------|-------------|--------|
| **Módulo central** | `api/observability.py` | Configuração e helpers |
| **Middleware HTTP** | `api/agent.py` | Rastreamento automático de requisições |
| **Spans OCR** | `api/agent.py` | Rastreamento de funções OCR |
| **Trace ADK** | `adk/adk_agent.py` | Rastreamento de conversas |
| **Span Gemini** | `adk/adk_agent.py` | Rastreamento de gerações |

### Servidor ADK

| Componente | Localização | Função |
|------------|-------------|--------|
| **Aplicação FastAPI** | `adk/web_server.py` | Servidor web |
| **Interface HTML** | `adk/web_server.py` | UI do chat |
| **WebSocket** | `adk/web_server.py` | Comunicação em tempo real |
| **Agente OCR** | `adk/adk_agent.py` | Lógica do agente |
| **Lifespan** | `adk/web_server.py` | Inicialização/shutdown |

### Variáveis de Ambiente

**Langfuse:**
- `LANGFUSE_ENABLED="true"`
- `LANGFUSE_PUBLIC_KEY="pk-lf-..."`
- `LANGFUSE_SECRET_KEY="sk-lf-..."`
- `LANGFUSE_HOST="https://us.cloud.langfuse.com"`

**Servidor ADK:**
- `GOOGLE_API_KEY="AIzaSy..."`

---

## 🔍 Como Verificar se Está Funcionando

### Langfuse

```python
# Verificar se está habilitado
python -c "import api.observability as o; print(o.is_enabled())"
# Deve retornar: True

# Verificar no dashboard
# Acesse: https://us.cloud.langfuse.com
# Procure por traces: "HTTP GET /extract", "adk_chat", etc.
```

### Servidor ADK

```bash
# Verificar se está rodando
curl http://localhost:8001/health
# Deve retornar: {"status":"ok","agent_ready":true}

# Acessar interface
# Abra: http://localhost:8001
```

---

## 📚 Referências

- [Documentação Langfuse](https://langfuse.com/docs)
- [FastAPI Lifespan](https://fastapi.tiangolo.com/advanced/events/)
- [WebSocket FastAPI](https://fastapi.tiangolo.com/advanced/websockets/)
- [Google ADK](https://ai.google.dev/adk)

