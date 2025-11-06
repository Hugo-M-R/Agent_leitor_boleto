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
    print("⚠️  Google Generative AI não encontrado. Instale com: pip install google-generativeai")
    genai = None
    GEMINI_AVAILABLE = False

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
    """Agent de OCR usando Google ADK"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa o agent
        
        Args:
            api_key: Chave da API do Google (ou usa GOOGLE_API_KEY do env)
        """
        if not GEMINI_AVAILABLE:
            raise ImportError("Google Generative AI não está instalado. Execute: pip install google-generativeai")
        
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY não encontrada. "
                "Configure a variável de ambiente ou passe api_key"
            )
        
        # Configura API do Google
        genai.configure(api_key=self.api_key)
        
        # Tenta diferentes modelos em ordem de preferência
        model_names = [
            "gemini-2.0-flash-exp", # Modelo experimental mais recente
            "gemini-pro",           # Modelo mais amplamente disponível
            "gemini-1.5-flash",     # Alternativa rápida
            "gemini-1.5-pro",       # Modelo avançado (pode não estar disponível)
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
                logger.info(f"Modelo {model_name} inicializado com sucesso!")
                break
            except Exception as e:
                logger.warning(f"Modelo {model_name} nao disponivel: {e}")
                continue
        
        if self.model is None:
            raise ValueError(
                "Nenhum modelo Gemini disponível. "
                "Verifique sua API key e permissões do projeto."
            )
        
        # Histórico de conversa
        self.chat_history = []
    
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
                
                # Gera resposta usando o modelo
                gen_span_ctx = create_span(name="gemini_generate")
                
                if gen_span_ctx:
                    with gen_span_ctx:
                        gen_span_ctx.update(input={
                            "model": self.model_name,
                            "temperature": 0.7,
                            "top_p": 0.8,
                            "top_k": 40
                        })
                        
                        response = self.model.generate_content(
                            full_message,
                            generation_config={
                                "temperature": 0.7,
                                "top_p": 0.8,
                                "top_k": 40,
                            }
                        )
                        
                        response_text = response.text
                        
                        # Não enviar resposta completa: truncar/mask
                        gen_span_ctx.update(output={"response_preview": response_text[:500]})
                else:
                    # Fallback sem rastreamento
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
                self.chat_history.append({"role": "model", "parts": [response_text]})
                
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
