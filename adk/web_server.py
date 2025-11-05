"""
Servidor web para interface visual do Agent ADK
Integra com FastAPI para fornecer interface de chat
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional
import os
import sys
import json
import asyncio
import tempfile
from pathlib import Path

# Configura encoding UTF-8 para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Carrega variáveis de ambiente do arquivo .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv é opcional

from adk.adk_agent import OCRAgent

# Instância global do agent (será inicializada na startup)
agent: Optional[OCRAgent] = None


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


app = FastAPI(title="Agent OCR - Interface ADK", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def get_chat_interface():
    """Retorna interface HTML do chat"""
    return """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent OCR - Chat Interface</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .container {
            width: 90%;
            max-width: 800px;
            height: 90vh;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 14px;
        }
        
        .chat-area {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
        }
        
        .message {
            margin-bottom: 15px;
            display: flex;
            animation: fadeIn 0.3s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            justify-content: flex-end;
        }
        
        .message.agent {
            justify-content: flex-start;
        }
        
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
        }
        
        .message.user .message-content {
            background: #667eea;
            color: white;
            border-bottom-right-radius: 4px;
        }
        
        .message.agent .message-content {
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
            border-bottom-left-radius: 4px;
        }
        
        .input-area {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 10px;
        }
        
        .file-input-wrapper {
            position: relative;
        }
        
        .file-input {
            display: none;
        }
        
        .file-btn {
            padding: 12px 20px;
            background: #f0f0f0;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 20px;
        }
        
        .file-btn:hover {
            background: #e0e0e0;
        }
        
        .text-input {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            outline: none;
        }
        
        .text-input:focus {
            border-color: #667eea;
        }
        
        .send-btn {
            padding: 12px 24px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 600;
        }
        
        .send-btn:hover {
            background: #5568d3;
        }
        
        .send-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        
        .loading {
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid #667eea;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 0.6s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .file-info {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Agent OCR</h1>
            <p>Chat com seu assistente de OCR e extração de boletos</p>
        </div>
        
        <div class="chat-area" id="chatArea">
            <div class="message agent">
                <div class="message-content">
                    Olá! Sou seu assistente de OCR. Posso ajudar você a:
                    <br>• Extrair texto de PDFs e imagens
                    <br>• Identificar campos de boletos bancários
                    <br>• Responder perguntas sobre documentos
                    <br><br>Envie um arquivo ou faça uma pergunta!
                </div>
            </div>
        </div>
        
        <div class="input-area">
            <div class="file-input-wrapper">
                <input type="file" id="fileInput" class="file-input" accept=".pdf,.jpg,.jpeg,.png,.tiff,.bmp">
                <button class="file-btn" onclick="document.getElementById('fileInput').click()">📎</button>
            </div>
            <input type="text" id="textInput" class="text-input" placeholder="Digite sua mensagem..." onkeypress="handleKeyPress(event)">
            <button id="sendBtn" class="send-btn" onclick="sendMessage()">Enviar</button>
        </div>
    </div>
    
    <script>
        const chatArea = document.getElementById('chatArea');
        const textInput = document.getElementById('textInput');
        const sendBtn = document.getElementById('sendBtn');
        const fileInput = document.getElementById('fileInput');
        
        let currentFile = null;
        
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                currentFile = file;
                addMessage('user', `📎 Arquivo selecionado: ${file.name}`);
            }
        });
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
        
        function addMessage(sender, text) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            messageDiv.innerHTML = `<div class="message-content">${text}</div>`;
            chatArea.appendChild(messageDiv);
            chatArea.scrollTop = chatArea.scrollHeight;
        }
        
        async function sendMessage() {
            const message = textInput.value.trim();
            const file = currentFile;
            
            if (!message && !file) {
                return;
            }
            
            // Adiciona mensagem do usuário
            if (message) {
                addMessage('user', message);
            }
            if (file) {
                addMessage('user', `📎 Enviando arquivo: ${file.name}`);
            }
            
            textInput.value = '';
            sendBtn.disabled = true;
            sendBtn.innerHTML = '<span class="loading"></span>';
            
            // Mostra mensagem de loading
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message agent';
            loadingDiv.id = 'loadingMessage';
            loadingDiv.innerHTML = '<div class="message-content">🤔 Pensando...</div>';
            chatArea.appendChild(loadingDiv);
            chatArea.scrollTop = chatArea.scrollHeight;
            
            try {
                const formData = new FormData();
                if (file) {
                    formData.append('file', file);
                }
                if (message) {
                    formData.append('message', message);
                }
                
                const response = await fetch('/chat', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                // Remove loading
                loadingDiv.remove();
                
                // Adiciona resposta
                addMessage('agent', data.response || '❌ Erro ao processar');
                
                // Limpa arquivo
                if (file) {
                    currentFile = null;
                    fileInput.value = '';
                }
                
            } catch (error) {
                loadingDiv.remove();
                addMessage('agent', `❌ Erro: ${error.message}`);
            } finally {
                sendBtn.disabled = false;
                sendBtn.innerHTML = 'Enviar';
            }
        }
    </script>
</body>
</html>
    """


@app.post("/chat")
async def chat_endpoint(
    message: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """Endpoint para processar mensagens do chat"""
    global agent
    
    if not agent:
        return JSONResponse(
            status_code=503,
            content={"error": "Agent não inicializado. Configure GOOGLE_API_KEY."}
        )
    
    try:
        # Salva arquivo temporário se fornecido
        file_path = None
        if file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
                content = await file.read()
                tmp.write(content)
                file_path = tmp.name
        
        # Processa mensagem
        user_message = message or "Processe este arquivo"
        if file:
            user_message = f"{user_message}\n\nArquivo: {file.filename}"
        
        response = await agent.chat(user_message, file_path)
        
        # Remove arquivo temporário
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        return JSONResponse(content={"response": response})
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/health")
async def health():
    """Endpoint de health check"""
    return {
        "status": "ok",
        "agent_ready": agent is not None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
