"""
Agent de Transcrição OCR usando Google ADK (Agent Development Kit)
Interface visual de chatbot para processar PDFs e imagens com OCR
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import requests

# Carrega variáveis de ambiente do arquivo .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv é opcional

# Google Gemini API imports
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GEMINI_AVAILABLE = True
except ImportError:
    # Fallback caso não esteja instalado
    genai = None
    GEMINI_AVAILABLE = False

# OpenAI API imports
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    openai = None
    OPENAI_AVAILABLE = False

# OpenRouter não requer biblioteca especial, usa requests diretamente
OPENROUTER_AVAILABLE = True

# Importa funções do agent de OCR
from api.agent import (
    ocr_with_tesseract,
    ocr_with_easyocr,
    ocr_pdf,
    extract_boleto_fields
)

# Observabilidade centralizada
from api.observability import (
    create_trace, create_span, log_error, is_enabled
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OCRAgent:
    """Agent de OCR usando OpenRouter, OpenAI ou Google Gemini"""
    
    def __init__(self, api_key: Optional[str] = None, provider: Optional[str] = None):
        """
        Inicializa o agent
        
        Args:
            api_key: Chave da API (OpenRouter, OpenAI ou Google)
            provider: "openrouter", "openai" ou "gemini" (auto-detecta se None)
        """
        # Detecta qual provider usar
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        google_key = os.getenv("GOOGLE_API_KEY") or api_key
        
        if provider is None:
            # Auto-detecção: prioriza OpenRouter, depois OpenAI, depois Gemini
            if openrouter_key and OPENROUTER_AVAILABLE:
                provider = "openrouter"
            elif openai_key and OPENAI_AVAILABLE:
                provider = "openai"
            elif google_key and GEMINI_AVAILABLE:
                provider = "gemini"
            else:
                raise ValueError(
                    "Nenhuma API configurada. Configure OPENROUTER_API_KEY, OPENAI_API_KEY ou GOOGLE_API_KEY. "
                    "Instale: pip install openai (ou google-generativeai)"
                )
        
        self.provider = provider.lower()
        self.api_key = api_key
        
        if self.provider == "openrouter":
            self._init_openrouter(openrouter_key)
        elif self.provider == "openai":
            self._init_openai(openai_key)
        elif self.provider == "gemini":
            self._init_gemini(google_key)
        else:
            raise ValueError(f"Provider inválido: {provider}. Use 'openrouter', 'openai' ou 'gemini'")
        
        # Histórico de conversa
        self.chat_history = []
    
    def _init_openrouter(self, api_key: Optional[str]):
        """Inicializa cliente OpenRouter"""
        if not OPENROUTER_AVAILABLE:
            raise ImportError("OpenRouter requer biblioteca requests (já incluída)")
        
        self.api_key = api_key or self.api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY não encontrada. Configure a variável de ambiente.")
        
        # Modelos OpenRouter em ordem de preferência (gratuitos ou baratos)
        # Formato: "provider/model-name"
        model_names = [
            "meta-llama/llama-3.2-3b-instruct",  # Gratuito, leve, FUNCIONA ✅
            "mistralai/mistral-7b-instruct",    # Gratuito
            "google/gemini-2.0-flash-exp",       # Gratuito, rápido (se disponível)
            "google/gemini-1.5-flash",           # Gratuito, rápido
            "openai/gpt-4o-mini",                # Barato, rápido
            "openai/gpt-4o",                     # Mais capaz
            "anthropic/claude-3-haiku",          # Rápido e eficiente
        ]
        
        self.model_name = None
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Testa cada modelo fazendo uma chamada real
        for model_name in model_names:
            try:
                logger.info(f"🧪 Testando modelo OpenRouter: {model_name}...")
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/your-repo",  # Opcional, mas recomendado
                }
                
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "user", "content": "Test"}
                    ],
                    "max_tokens": 5
                }
                
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=15
                )
                
                if response.status_code == 200:
                    self.model_name = model_name
                    logger.info(f"✅ OpenRouter {model_name} configurado e testado com sucesso!")
                    break
                elif response.status_code == 401:
                    logger.warning(f"❌ API key inválida para {model_name}")
                    continue
                elif response.status_code == 402:
                    logger.warning(f"⚠️  Sem créditos para {model_name}")
                    continue
                else:
                    logger.warning(f"⚠️  Modelo {model_name} retornou status {response.status_code}")
                    continue
                    
            except Exception as e:
                logger.warning(f"⚠️  Erro ao testar modelo {model_name}: {e}")
                continue
        
        if not self.model_name:
            raise ValueError(
                f"Nenhum modelo OpenRouter disponível. "
                f"Testados: {', '.join(model_names[:5])}. "
                f"Verifique sua API key e créditos em https://openrouter.ai"
            )
        
        self.model = None  # OpenRouter usa API HTTP direta
    
    def _init_openai(self, api_key: Optional[str]):
        """Inicializa cliente OpenAI"""
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI não está instalado. Execute: pip install openai")
        
        self.api_key = api_key or self.api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY não encontrada. Configure a variável de ambiente.")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        
        # Modelos OpenAI em ordem de preferência
        model_names = [
            "gpt-4o-mini",      # Mais barato, rápido
            "gpt-4o",            # Mais capaz
            "gpt-4-turbo",       # Alternativa
            "gpt-3.5-turbo",     # Fallback
        ]
        
        self.model_name = None
        for model_name in model_names:
            try:
                # Testa se o modelo está disponível
                self.model_name = model_name
                logger.info(f"✅ OpenAI {model_name} configurado!")
                break
            except Exception as e:
                logger.warning(f"Modelo {model_name} não disponível: {e}")
                continue
        
        if not self.model_name:
            raise ValueError("Nenhum modelo OpenAI disponível.")
        
        self.model = None  # OpenAI usa client, não model object
    
    def _init_gemini(self, api_key: Optional[str]):
        """Inicializa cliente Gemini"""
        if not GEMINI_AVAILABLE:
            raise ImportError("Google Generative AI não está instalado. Execute: pip install google-generativeai")
        
        self.api_key = api_key or self.api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY não encontrada. Configure a variável de ambiente.")
        
        # Configura API do Google
        genai.configure(api_key=self.api_key)
        
        # Tenta diferentes modelos em ordem de preferência
        model_names = [
            "gemini-2.0-flash-exp",
            "gemini-pro",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
        
        self.model = None
        self.model_name = None
        for model_name in model_names:
            try:
                self.model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=self._get_system_instruction(),
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }
                )
                self.model_name = model_name
                logger.info(f"✅ Gemini {model_name} inicializado com sucesso!")
                break
            except Exception as e:
                logger.warning(f"Modelo {model_name} não disponível: {e}")
                continue
        
        if self.model is None:
            raise ValueError("Nenhum modelo Gemini disponível. Verifique sua API key.")
    
    def _get_system_instruction(self) -> str:
        """Retorna instruções do sistema para o agent"""
        return """Você é um assistente especializado em OCR (Reconhecimento Óptico de Caracteres) 
e extração de dados de boletos bancários.

Suas responsabilidades:
1. Processar PDFs e imagens com OCR
2. Extrair texto de documentos
3. Identificar e extrair campos de boletos (linha digitável, valor, vencimento, etc.)
4. Responder perguntas sobre o conteúdo extraído
5. Fornecer informações estruturadas sobre os documentos processados

FORMATAÇÃO DE RESPOSTAS:
- Sempre formate dados de boletos de forma visual e organizada
- Use emojis relevantes para melhorar a legibilidade
- Organize informações em seções claras com separadores visuais
- Destaque informações importantes (valores, datas, códigos)
- Use formatação markdown de forma elegante (tabelas, listas, blocos de código quando apropriado)

EXEMPLO DE FORMATAÇÃO PARA DADOS DE BOLETO:
Use este formato quando apresentar dados extraídos de boletos:

## 📋 DADOS DO BOLETO

### Informações Principais
- **📅 Data de Vencimento:** 05/11/2025
- **🏦 Banco:** PicPay Bank
- **💰 Valor:** R$ 1.256,00

### Beneficiário
- **Nome:** PicPay Bank Banco Múltiplo S.A.
- **CNPJ:** 09.516.419/0001-75

### Pagador
- **Nome:** GABRIELA ROCHA SANTOS FREITAS

### Linha Digitável
```
38090.10006 01429.920059 05875.050311 1 12560000003735
```

---

*Qualquer outra informação que precisar, é só perguntar.*

Seja sempre claro, preciso e ofereça informações detalhadas sobre os documentos processados."""
    
    def _get_tools_info(self) -> str:
        """Retorna informações sobre as ferramentas disponíveis"""
        return """
Ferramentas disponíveis:
1. extract_pdf_text(pdf_path, lang="por+eng") - Extrai texto de PDF
2. extract_image_text(image_path, lang="por+eng") - Extrai texto de imagem
3. extract_boleto_data(file_path, lang="por+eng") - Extrai campos de boleto

Use estas ferramentas quando o usuário solicitar processamento de arquivos.
"""
    
    async def extract_pdf_text(self, pdf_path: str, lang: str = "por+eng") -> Dict[str, Any]:
        """Extrai texto de PDF"""
        if not os.path.exists(pdf_path):
            return {"error": f"Arquivo não encontrado: {pdf_path}"}
        
        try:
            pages = ocr_pdf(pdf_path, lang)
            
            # Verifica se encontrou texto significativo
            total_chars = sum(len(p.get('text', '')) for p in pages)
            pages_with_text = sum(1 for p in pages if len(p.get('text', '').strip()) > 20)
            
            full_text = "\n\n".join([f"Página {p['page']}:\n{p['text']}" for p in pages])
            
            # Gera resumo mais informativo
            if total_chars < 50:
                summary = f"AVISO: O PDF foi processado mas pouco ou nenhum texto foi encontrado. {pages_with_text} de {len(pages)} página(s) contêm texto. O arquivo pode estar em branco, ser uma imagem de baixa qualidade, ou conter apenas elementos gráficos."
            else:
                summary = f"Extraído texto de {pages_with_text} de {len(pages)} página(s). Total de {total_chars} caracteres."
            
            return {
                "success": True,
                "pages": len(pages),
                "text": full_text,
                "summary": summary,
                "total_characters": total_chars,
                "pages_with_text": pages_with_text
            }
        except Exception as e:
            logger.error(f"Erro ao extrair PDF: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    async def extract_image_text(self, image_path: str, lang: str = "por+eng") -> Dict[str, Any]:
        """Extrai texto de imagem"""
        if not os.path.exists(image_path):
            return {"error": f"Arquivo não encontrado: {image_path}"}
        
        try:
            with open(image_path, "rb") as f:
                content = f.read()
            
            text = ocr_with_tesseract(content, lang)
            
            # Fallback para EasyOCR se necessário
            if len(text.strip()) < 20:
                text = ocr_with_easyocr(content)
            
            return {
                "success": True,
                "text": text,
                "summary": f"Texto extraído com {len(text)} caracteres"
            }
        except Exception as e:
            logger.error(f"Erro ao extrair imagem: {e}")
            return {"error": str(e)}
    
    async def extract_boleto_data(self, file_path: str, lang: str = "por+eng") -> Dict[str, Any]:
        """Extrai campos de boleto"""
        if not os.path.exists(file_path):
            return {"error": f"Arquivo não encontrado: {file_path}"}
        
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == ".pdf":
                pages = ocr_pdf(file_path, lang)
                full_text = " ".join([p["text"] for p in pages])
            else:
                with open(file_path, "rb") as f:
                    content = f.read()
                
                text = ocr_with_tesseract(content, lang)
                if len(text.strip()) < 20:
                    text = ocr_with_easyocr(content)
                full_text = text
            
            fields = extract_boleto_fields(full_text)
            
            return {
                "success": True,
                "extracted_fields": fields,
                "text_preview": full_text[:500] + "..." if len(full_text) > 500 else full_text
            }
        except Exception as e:
            logger.error(f"Erro ao extrair boleto: {e}")
            return {"error": str(e)}
    
    async def chat(self, message: str, file_path: Optional[str] = None) -> str:
        """
        Processa uma mensagem do usuário e retorna resposta do agent
        
        Args:
            message: Mensagem do usuário
            file_path: Caminho opcional de arquivo para processar
        
        Returns:
            Resposta do agent
        """
        trace_ctx = create_trace(name="adk_chat", input_data={"message": message[:200]})
        
        if not trace_ctx:
            # Fallback se Langfuse desabilitado
            return await self._chat_internal(message, file_path)
        
        with trace_ctx:
            try:
                # Se houver arquivo, processa primeiro
                context = ""
                file_info = ""
                
                if file_path and os.path.exists(file_path):
                    ext = os.path.splitext(file_path)[1].lower()
                    file_info = f"\n[Arquivo processado: {os.path.basename(file_path)}]"
                    
                    if ext == ".pdf":
                        result = await self.extract_pdf_text(file_path)
                    else:
                        result = await self.extract_image_text(file_path)
                    
                    if result.get("success"):
                        # Verifica se encontrou texto significativo
                        total_chars = result.get('total_characters', 0)
                        pages_with_text = result.get('pages_with_text', 0)
                        summary = result.get('summary', '')
                        
                        if total_chars < 50:
                            # Pouco ou nenhum texto encontrado
                            context = f"\n\n[AVISO IMPORTANTE - Conteúdo do arquivo]:\n{summary}\n\nO arquivo foi processado mas não foi possível extrair texto significativo. Possíveis causas:\n1. O PDF pode estar vazio ou conter apenas imagens/graphics\n2. A qualidade da imagem pode ser muito baixa para OCR\n3. O arquivo pode estar protegido ou criptografado\n4. O texto pode estar em uma fonte não reconhecível\n\nRecomendações:\n- Verifique se o arquivo está correto e contém texto legível\n- Tente com um arquivo de melhor qualidade\n- Se for uma fatura/boleto, verifique se não está em formato de imagem muito comprimida"
                        else:
                            text_content = result.get('text', result.get('summary', ''))
                            # Limita tamanho para não sobrecarregar o contexto
                            if len(text_content) > 5000:
                                text_content = text_content[:5000] + "\n... (texto truncado)"
                            context = f"\n\n[Conteúdo extraído do arquivo - {pages_with_text} página(s) com texto]:\n{text_content}"
                    else:
                        context = f"\n\n[Erro ao processar arquivo]: {result.get('error', 'Erro desconhecido')}"
                
                # Prepara mensagem completa
                full_message = message + file_info + context
                
                # Adiciona ao histórico
                self.chat_history.append({"role": "user", "parts": [full_message]})
                
                # Gera resposta usando o modelo (OpenRouter, OpenAI ou Gemini)
                provider_name = f"{self.provider}_generate"
                gen_span_ctx = create_span(
                    name=provider_name,
                    input_data={
                        "model": self.model_name,
                        "provider": self.provider,
                        "temperature": 0.7,
                    }
                )
                
                if self.provider == "openrouter":
                    # Usa OpenRouter
                    messages = [
                        {"role": "system", "content": self._get_system_instruction()}
                    ]
                    # Adiciona histórico (já inclui a mensagem atual que foi adicionada acima)
                    for msg in self.chat_history[-10:]:  # Últimas 10 mensagens
                        role = msg.get("role", "user")
                        if role == "user":
                            messages.append({"role": "user", "content": msg.get("parts", [""])[0]})
                        elif role == "model" or role == "assistant":
                            messages.append({"role": "assistant", "content": msg.get("parts", [""])[0]})
                    
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/your-repo",  # Opcional, mas recomendado
                    }
                    
                    payload = {
                        "model": self.model_name,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 1000
                    }
                    
                    if gen_span_ctx:
                        with gen_span_ctx:
                            response = requests.post(
                                self.api_url,
                                headers=headers,
                                json=payload,
                                timeout=60
                            )
                            response.raise_for_status()
                            result = response.json()
                            response_text = result["choices"][0]["message"]["content"]
                            gen_span_ctx.update(output={"response_preview": response_text[:500]})
                    else:
                        response = requests.post(
                            self.api_url,
                            headers=headers,
                            json=payload,
                            timeout=60
                        )
                        response.raise_for_status()
                        result = response.json()
                        response_text = result["choices"][0]["message"]["content"]
                
                elif self.provider == "openai":
                    # Usa OpenAI
                    messages = [
                        {"role": "system", "content": self._get_system_instruction()}
                    ]
                    # Adiciona histórico (já inclui a mensagem atual que foi adicionada acima)
                    for msg in self.chat_history[-10:]:  # Últimas 10 mensagens
                        role = msg.get("role", "user")
                        if role == "user":
                            messages.append({"role": "user", "content": msg.get("parts", [""])[0]})
                        elif role == "model" or role == "assistant":
                            messages.append({"role": "assistant", "content": msg.get("parts", [""])[0]})
                    
                    if gen_span_ctx:
                        with gen_span_ctx:
                            response = self.client.chat.completions.create(
                                model=self.model_name,
                                messages=messages,
                                temperature=0.7,
                            )
                            response_text = response.choices[0].message.content
                            gen_span_ctx.update(output={"response_preview": response_text[:500]})
                    else:
                        response = self.client.chat.completions.create(
                            model=self.model_name,
                            messages=messages,
                            temperature=0.7,
                        )
                        response_text = response.choices[0].message.content
                
                else:
                    # Usa Gemini (código original)
                    if gen_span_ctx:
                        with gen_span_ctx:
                            response = self.model.generate_content(
                                full_message,
                                generation_config={
                                    "temperature": 0.7,
                                    "top_p": 0.8,
                                    "top_k": 40,
                                }
                            )
                            response_text = response.text
                            gen_span_ctx.update(output={"response_preview": response_text[:500]})
                    else:
                        response = self.model.generate_content(
                            full_message,
                            generation_config={
                                "temperature": 0.7,
                                "top_p": 0.8,
                                "top_k": 40,
                            }
                        )
                        response_text = response.text
                
                # Adiciona resposta ao histórico
                if self.provider == "openai" or self.provider == "openrouter":
                    role = "assistant"
                else:
                    role = "model"
                self.chat_history.append({"role": role, "parts": [response_text]})
                
                # Limita histórico (mantém últimas 10 mensagens)
                if len(self.chat_history) > 20:
                    self.chat_history = self.chat_history[-20:]
                
                trace_ctx.update(output={"response_preview": response_text[:200]})
                
                return response_text
                
            except Exception as e:
                logger.error(f"Erro no chat: {e}")
                import traceback
                traceback.print_exc()
                log_error(f"adk_chat_error: {e}")
                trace_ctx.update(output={"error": str(e)})
                return f"❌ Erro ao processar: {str(e)}"
    
    async def _chat_internal(self, message: str, file_path: Optional[str] = None) -> str:
        """Implementação interna do chat (sem rastreamento)"""
        # Mesma lógica do chat, mas sem Langfuse
        context = ""
        file_info = ""
        
        if file_path and os.path.exists(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            file_info = f"\n[Arquivo processado: {os.path.basename(file_path)}]"
            
            if ext == ".pdf":
                result = await self.extract_pdf_text(file_path)
            else:
                result = await self.extract_image_text(file_path)
            
            if result.get("success"):
                total_chars = result.get('total_characters', 0)
                pages_with_text = result.get('pages_with_text', 0)
                summary = result.get('summary', '')
                
                if total_chars < 50:
                    context = f"\n\n[AVISO IMPORTANTE - Conteúdo do arquivo]:\n{summary}\n\nO arquivo foi processado mas não foi possível extrair texto significativo."
                else:
                    text_content = result.get('text', result.get('summary', ''))
                    if len(text_content) > 5000:
                        text_content = text_content[:5000] + "\n... (texto truncado)"
                    context = f"\n\n[Conteúdo extraído do arquivo - {pages_with_text} página(s) com texto]:\n{text_content}"
            else:
                context = f"\n\n[Erro ao processar arquivo]: {result.get('error', 'Erro desconhecido')}"
        
        full_message = message + file_info + context
        self.chat_history.append({"role": "user", "parts": [full_message]})
        
        response = self.model.generate_content(
            full_message,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
            }
        )
        
        response_text = response.text
        self.chat_history.append({"role": "model", "parts": [response_text]})
        
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]
        
        return response_text


# Função para executar o agent via CLI
async def main():
    """Função principal para executar o agent interativamente"""
    print("🤖 Agent de Transcrição OCR com Google ADK")
    print("=" * 50)
    print()
    
    # Verifica API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("⚠️  GOOGLE_API_KEY não encontrada!")
        print("   Configure: export GOOGLE_API_KEY='sua-chave-aqui'")
        print()
        api_key = input("Ou digite sua API key agora: ").strip()
        if not api_key:
            print("❌ API key obrigatória!")
            return
    
    try:
        agent = OCRAgent(api_key=api_key)
        print("✅ Agent inicializado com sucesso!")
        print()
        print("💡 Comandos disponíveis:")
        print("   - Digite uma mensagem para conversar")
        print("   - Use 'processar arquivo.pdf' para processar um arquivo")
        print("   - Digite 'sair' para encerrar")
        print()
        
        while True:
            user_input = input("Você: ").strip()
            
            if user_input.lower() in ["sair", "exit", "quit"]:
                print("👋 Até logo!")
                break
            
            if not user_input:
                continue
            
            # Detecta se há caminho de arquivo na mensagem
            file_path = None
            if "processar" in user_input.lower() or "arquivo" in user_input.lower():
                # Tenta extrair caminho do arquivo
                words = user_input.split()
                for word in words:
                    if os.path.exists(word):
                        file_path = word
                        break
            
            print("🤖 Agent: ", end="", flush=True)
            response = await agent.chat(user_input, file_path)
            print(response)
            print()
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
