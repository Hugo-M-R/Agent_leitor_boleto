"""
Agent de Transcrição - OCR com extração de campos de boleto
Suporta PDF e imagens com múltiplos engines de OCR
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io
import os
import json
import tempfile
import subprocess
import re
from datetime import datetime
from pathlib import Path
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agent de Transcrição OCR",
    description="Serviço de OCR com extração de campos de boleto",
    version="1.0.0"
)

# Armazena o último JSON extraído para integração com agente validador
last_json_extracted: Dict[str, Any] = {}
ID_SEQUENCIAL: int = 0


def ocr_with_tesseract(image_bytes: bytes, lang: str = "por+eng") -> str:
    """Executa OCR usando Tesseract"""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, lang=lang)
        return text.strip()
    except Exception as e:
        logger.error(f"Erro no Tesseract: {e}")
        return ""


def ocr_with_easyocr(image_bytes: bytes, languages: List[str] = ["pt", "en"]) -> str:
    """Executa OCR usando EasyOCR como fallback"""
    try:
        import easyocr
        reader = easyocr.Reader(languages, gpu=False)
        results = reader.readtext(image_bytes, detail=0)
        return " ".join(results)
    except Exception as e:
        logger.error(f"Erro no EasyOCR: {e}")
        return ""


def ocr_pdf(pdf_path: str, lang: str = "por+eng", use_ocrmypdf: bool = True) -> List[Dict[str, Any]]:
    """Processa PDF com OCR usando ocrmypdf ou PyMuPDF + Tesseract"""
    result = []
    
    try:
        if use_ocrmypdf:
            # Tenta usar ocrmypdf primeiro (melhor qualidade)
            out_path = pdf_path.replace(".pdf", "_ocr.pdf")
            try:
                subprocess.run([
                    "ocrmypdf", "--force-ocr", "-l", lang,
                    "--rotate-pages", "--deskew", "--quiet",
                    pdf_path, out_path
                ], check=True, capture_output=True)
                
                pdf = fitz.open(out_path)
                for i, page in enumerate(pdf):
                    text = page.get_text("text")
                    result.append({"page": i + 1, "text": text})
                pdf.close()
                
                # Remove arquivo temporário
                if os.path.exists(out_path):
                    os.remove(out_path)
                
                return result
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("ocrmypdf não disponível, usando PyMuPDF + Tesseract")
        
        # Fallback: PyMuPDF + Tesseract por página
        pdf = fitz.open(pdf_path)
        total_pages = len(pdf)
        logger.info(f"Processando PDF com {total_pages} página(s)")
        
        for i, page in enumerate(pdf):
            # Primeiro tenta extrair texto direto (se PDF tem texto)
            text_directo = page.get_text("text").strip()
            
            # Se não houver texto ou muito pouco (menos de 20 caracteres), faz OCR na imagem
            if len(text_directo) < 20:
                logger.info(f"Página {i+1}: Sem texto extraível, fazendo OCR na imagem...")
                
                text = ""
                best_text = ""
                best_length = 0
                
                # Tenta múltiplas resoluções para melhor OCR
                resolutions = [
                    (3, 3, "300 DPI"),   # Alta resolução
                    (4, 4, "400 DPI"),   # Muito alta resolução
                    (2, 2, "200 DPI"),   # Resolução média
                ]
                
                for zoom_x, zoom_y, dpi_label in resolutions:
                    try:
                        logger.info(f"Página {i+1}: Tentando OCR com {dpi_label}...")
                        matrix = fitz.Matrix(zoom_x, zoom_y)
                        pix = page.get_pixmap(matrix=matrix)
                        img_bytes = pix.tobytes("png")
                        
                        # OCR com Tesseract
                        text_tess = ocr_with_tesseract(img_bytes, lang)
                        if len(text_tess.strip()) > best_length:
                            best_text = text_tess
                            best_length = len(text_tess.strip())
                            logger.info(f"Página {i+1}: {dpi_label} encontrou {best_length} caracteres")
                        
                        # Se já encontrou texto suficiente, para
                        if best_length > 100:
                            break
                            
                    except Exception as e:
                        logger.warning(f"Página {i+1}: Erro com {dpi_label}: {e}")
                        continue
                
                text = best_text if best_text else ""
                
                # Se ainda pouco texto, tenta EasyOCR com a melhor imagem
                if len(text.strip()) < 50:
                    logger.info(f"Página {i+1}: Tesseract retornou pouco texto ({len(text)} chars), tentando EasyOCR...")
                    try:
                        # Usa a maior resolução para EasyOCR
                        matrix = fitz.Matrix(4, 4)
                        pix = page.get_pixmap(matrix=matrix)
                        img_bytes = pix.tobytes("png")
                        
                        text_easy = ocr_with_easyocr(img_bytes)
                        if len(text_easy.strip()) > len(text.strip()):
                            text = text_easy
                            logger.info(f"Página {i+1}: EasyOCR obteve melhor resultado ({len(text)} chars)")
                    except Exception as e:
                        logger.warning(f"Página {i+1}: EasyOCR falhou: {e}")
                
                # Se ainda não encontrou texto, tenta processamento adicional
                if len(text.strip()) < 20:
                    # Tenta aplicar filtros de imagem para melhorar OCR
                    try:
                        logger.info(f"Página {i+1}: Aplicando processamento de imagem...")
                        matrix = fitz.Matrix(4, 4)
                        pix = page.get_pixmap(matrix=matrix)
                        img_bytes = pix.tobytes("png")
                        
                        # Processa imagem com PIL para melhorar contraste
                        img = Image.open(io.BytesIO(img_bytes))
                        
                        # Converte para escala de cinza se necessário
                        if img.mode != 'L':
                            img = img.convert('L')
                        
                        # Melhora contraste
                        enhancer = ImageEnhance.Contrast(img)
                        img = enhancer.enhance(2.0)
                        
                        # Aplica sharpening
                        img = img.filter(ImageFilter.SHARPEN)
                        
                        # Converte de volta para bytes
                        img_buffer = io.BytesIO()
                        img.save(img_buffer, format='PNG')
                        img_bytes_processed = img_buffer.getvalue()
                        
                        # Tenta OCR novamente com imagem processada
                        text_processed = ocr_with_tesseract(img_bytes_processed, lang)
                        if len(text_processed.strip()) > len(text.strip()):
                            text = text_processed
                            logger.info(f"Página {i+1}: Imagem processada melhorou OCR ({len(text)} chars)")
                    except Exception as e:
                        logger.warning(f"Página {i+1}: Processamento de imagem falhou: {e}")
                
                # Se ainda não encontrou texto significativo
                if len(text.strip()) < 10:
                    text = f"[AVISO: Página {i+1} - OCR não encontrou texto significativo após múltiplas tentativas. O arquivo pode estar em branco, com baixa qualidade, ou protegido.]"
                    logger.warning(f"Página {i+1}: OCR não encontrou texto significativo após todas as tentativas")
                else:
                    logger.info(f"Página {i+1}: Extraído {len(text)} caracteres via OCR")
            else:
                # PDF já tem texto extraível
                text = text_directo
                logger.info(f"Página {i+1}: Extraído {len(text)} caracteres do texto do PDF")
            
            result.append({"page": i + 1, "text": text})
        
        pdf.close()
        return result
        
    except Exception as e:
        logger.error(f"Erro ao processar PDF: {e}")
        import traceback
        traceback.print_exc()
        raise


def extract_boleto_fields(text: str) -> Dict[str, Any]:
    """Extrai campos principais de um boleto bancário"""
    fields = {
        "banco": None,
        "linha_digitavel": None,
        "vencimento": None,
        "valor": None,
        "sacado": None,
        "cedente": None,
        "nosso_numero": None,
        "agencia": None,
        "conta": None,
        "cpf_cnpj": None,
        "codigo_barras": None
    }
    
    # Normaliza texto (remove espaços extras, mantém estrutura)
    text_normalized = re.sub(r'\s+', ' ', text)
    text_lines = text.split('\n')
    
    # Linha digitável (47 dígitos) - padrões mais flexíveis
    linha_patterns = [
        r'\b\d{5}\.\d{5}\s+\d{5}\.\d{6}\s+\d{5}\.\d{6}\s+\d\s+\d{14}\b',  # Com espaços
        r'\b\d{5}\.\d{5}\.\d{5}\.\d{6}\.\d{5}\.\d{6}\.\d\.\d{14}\b',  # Sem espaços
        r'\d{5}\.\d{5}\s*\d{5}\.\d{6}\s*\d{5}\.\d{6}\s*\d\s*\d{14}',  # Espaços variáveis
        r'\d{47}',  # Apenas 47 dígitos consecutivos
    ]
    for pattern in linha_patterns:
        match = re.search(pattern, text.replace('\n', ' ').replace('\r', ' '))
        if match:
            linha = match.group(0).strip()
            # Valida se tem aproximadamente 47 dígitos
            if len(re.sub(r'[^\d]', '', linha)) >= 44:
                fields["linha_digitavel"] = linha
                break
    
    # Código de barras (44 dígitos)
    codigo_barras_patterns = [
        r'\b\d{44}\b',
        r'\b\d{5}\s*\d{5}\s*\d{5}\s*\d{6}\s*\d{5}\s*\d{6}\s*\d{1}\s*\d{14}\b',
    ]
    for pattern in codigo_barras_patterns:
        match = re.search(pattern, text.replace('\n', ' ').replace('\r', ' '))
        if match:
            codigo = re.sub(r'[^\d]', '', match.group(0))
            if len(codigo) >= 44:
                fields["codigo_barras"] = codigo[:44]
                break
    
    # Valor (R$ X.XXX,XX) - padrões mais abrangentes
    valor_patterns = [
        r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
        r'valor[:\s=]+R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
        r'valor[:\s=]+(\d{1,3}(?:\.\d{3})*(?:,\d{2}))',
        r'(\d{1,3}(?:\.\d{3})*(?:,\d{2}))\s*reais',
        r'R\$\s*(\d+,\d{2})',
        r'(\d{1,3}(?:\.\d{3})*(?:,\d{2}))',  # Sem R$
    ]
    for pattern in valor_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            valor = match.group(1) if match.lastindex else match.group(0)
            # Valida se parece um valor monetário (tem vírgula e centavos)
            if ',' in valor and len(valor.split(',')[-1]) == 2:
                fields["valor"] = valor
                break
        if fields["valor"]:
            break
    
    # Data de vencimento - padrões mais flexíveis
    vencimento_patterns = [
        r'vencimento[:\s=]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'data[:\s=]+vencimento[:\s=]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'venc[:\s=]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',  # Data completa (4 dígitos)
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2})',  # Data com 2 dígitos
    ]
    for pattern in vencimento_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            data = match.group(1)
            # Valida formato básico de data
            if re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', data):
                fields["vencimento"] = data
                break
        if fields["vencimento"]:
            break
    
    # Banco (código + nome) - padrões melhorados
    banco_patterns = [
        r'(\d{3})[-/]\s*\d+.*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'Banco\s+([A-Z][a-z]+)',
        r'([A-Z][a-z]+)\s*\[\s*(\d{3})',
        r'(\d{3})\s*-\s*([A-Z][a-z]+)',
        r'Banco\s+(\d{3})\s*-\s*([A-Z][a-z]+)',
    ]
    for pattern in banco_patterns:
        match = re.search(pattern, text)
        if match:
            if match.lastindex >= 2:
                fields["banco"] = f"{match.group(1)} - {match.group(2)}"
            else:
                fields["banco"] = match.group(1)
            break
    
    # CPF/CNPJ - padrões mais flexíveis
    cpf_cnpj_patterns = [
        r'\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b',
        r'\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b',
        r'\b(\d{11})\b',  # CPF sem formatação
        r'\b(\d{14})\b',  # CNPJ sem formatação
    ]
    for pattern in cpf_cnpj_patterns:
        match = re.search(pattern, text)
        if match:
            cpf_cnpj = match.group(1)
            # Formata se necessário
            if len(re.sub(r'[^\d]', '', cpf_cnpj)) == 11:
                cpf_cnpj = re.sub(r'(\d{3})(\d{3})(\d{3})(\d{2})', r'\1.\2.\3-\4', cpf_cnpj)
            elif len(re.sub(r'[^\d]', '', cpf_cnpj)) == 14:
                cpf_cnpj = re.sub(r'(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})', r'\1.\2.\3/\4-\5', cpf_cnpj)
            fields["cpf_cnpj"] = cpf_cnpj
            break
    
    # Sacado/Pagador - padrões melhorados
    sacado_patterns = [
        r'(?:pagador|sacado)[:\s=]+([A-ZÁÉÍÓÚ][a-záéíóú]+(?:\s+[A-ZÁÉÍÓÚ][a-záéíóú]+)+)',
        r'(?:pagador|sacado)[:\s=]+(.{10,60})',  # Captura linha completa
        r'sacado[:\s=]+([A-ZÁÉÍÓÚ][a-záéíóú]+(?:\s+[A-ZÁÉÍÓÚ][a-záéíóú]+)+)',
    ]
    for pattern in sacado_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            nome = match.group(1).strip()
            # Limita tamanho e remove caracteres especiais no final
            nome = re.sub(r'[^\w\s]+$', '', nome)
            if len(nome) > 5 and len(nome) < 100:
                fields["sacado"] = nome
                break
    
    # Cedente/Beneficiário
    cedente_patterns = [
        r'(?:cedente|benefici[áa]rio)[:\s=]+([A-ZÁÉÍÓÚ][a-záéíóú]+(?:\s+[A-ZÁÉÍÓÚ][a-záéíóú]+)+)',
        r'(?:cedente|benefici[áa]rio)[:\s=]+(.{10,60})',
    ]
    for pattern in cedente_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            nome = match.group(1).strip()
            nome = re.sub(r'[^\w\s]+$', '', nome)
            if len(nome) > 5 and len(nome) < 100:
                fields["cedente"] = nome
                break
    
    # Nosso Número
    nosso_numero_patterns = [
        r'nosso\s+n[úu]mero[:\s=]+(\d+)',
        r'n[úu]mero[:\s=]+(\d{10,20})',
    ]
    for pattern in nosso_numero_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fields["nosso_numero"] = match.group(1).strip()
            break
    
    # Agência
    agencia_patterns = [
        r'ag[êe]ncia[:\s=]+(\d{1,10})',
        r'ag[:\s=]+(\d{1,10})',
    ]
    for pattern in agencia_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fields["agencia"] = match.group(1).strip()
            break
    
    # Conta
    conta_patterns = [
        r'conta[:\s=]+(\d{1,15})',
        r'conta[:\s=]+corrente[:\s=]+(\d{1,15})',
    ]
    for pattern in conta_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fields["conta"] = match.group(1).strip()
            break
    
    # Remove campos None
    return {k: v for k, v in fields.items() if v is not None}


def format_boleto_core_fields(full_text: str) -> Dict[str, Any]:
    """Mapeia os campos extraídos para o formato mínimo solicitado.
    Retorna apenas: vencimento, linha_digitavel, beneficiario_cnpj, beneficiario_nome.
    """
    extracted = extract_boleto_fields(full_text)
    return {
        "vencimento": extracted.get("vencimento"),
        "linha_digitavel": extracted.get("linha_digitavel"),
        "beneficiario_cnpj": extracted.get("cpf_cnpj"),
        "beneficiario_nome": extracted.get("cedente"),
    }


@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "service": "Agent de Transcrição OCR",
        "version": "1.0.0",
        "endpoints": {
            "/extract": "POST - Extrai texto de PDF ou imagem",
            "/extract-boleto": "POST - Extrai texto e campos de boleto",
            "/extract-boleto-fields": "POST - Retorna e armazena JSON mínimo (pré-setado) para validador",
            "/get_last_json_extracted": "GET - Retorna último JSON extraído"
        }
    }


@app.post("/extract")
async def extract(
    file: UploadFile = File(...),
    lang: str = Form("por+eng"),
    extract_fields: bool = Form(False)
):
    """
    Extrai texto de PDF ou imagem usando OCR
    
    Args:
        file: Arquivo PDF ou imagem (jpg, png, etc)
        lang: Idioma para OCR (padrão: por+eng)
        extract_fields: Se True, tenta extrair campos de boleto
    """
    try:
        # Validação de extensão
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
            raise HTTPException(
                status_code=400,
                detail=f"Formato não suportado: {ext}. Use PDF ou imagem."
            )
        
        # Salva arquivo temporário
        content = await file.read()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            tmp.flush()
            tmp_path = tmp.name
        
        try:
            pages = []
            metadata = {
                "engine": "tesseract",
                "lang": lang,
                "ocr_confidence": None
            }
            
            if ext == ".pdf":
                # Processa PDF
                pages = ocr_pdf(tmp_path, lang)
                metadata["engine"] = "ocrmypdf+tesseract"
            else:
                # Processa imagem
                text = ocr_with_tesseract(content, lang)
                
                # Fallback para EasyOCR se resultado muito curto
                if len(text.strip()) < 20:
                    logger.info("Tesseract retornou pouco texto, tentando EasyOCR...")
                    text = ocr_with_easyocr(content)
                    metadata["engine"] = "easyocr"
                
                pages = [{"page": 1, "text": text}]
            
            # Extração de campos (se solicitado)
            extracted_fields = None
            if extract_fields and pages:
                full_text = " ".join([p["text"] for p in pages])
                extracted_fields = extract_boleto_fields(full_text)
            
            result = {
                "success": True,
                "source": file.filename,
                "pages": pages,
                "metadata": metadata
            }
            
            if extracted_fields:
                result["extracted_fields"] = extracted_fields
            
            return JSONResponse(content=result)
            
        finally:
            # Remove arquivo temporário
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except Exception as e:
        logger.error(f"Erro ao processar arquivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract-boleto")
async def extract_boleto(
    file: UploadFile = File(...),
    lang: str = Form("por+eng")
):
    """
    Extrai texto e campos de boleto de PDF ou imagem
    
    Args:
        file: Arquivo PDF ou imagem do boleto
        lang: Idioma para OCR (padrão: por+eng)
    """
    return await extract(file=file, lang=lang, extract_fields=True)


@app.post("/extract-boleto-fields")
async def extract_boleto_fields_min(
    file: UploadFile = File(...),
    lang: str = Form("por+eng")
):
    """
    Extrai apenas os campos essenciais do boleto e retorna JSON mínimo:
      - vencimento
      - linha_digitavel
      - beneficiario_cnpj
      - beneficiario_nome
    """
    # Validação de extensão
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não suportado: {ext}. Use PDF ou imagem."
        )

    content = await file.read()

    # Salva temporário se PDF para processar por páginas
    if ext == ".pdf":
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            tmp.flush()
            tmp_path = tmp.name
        try:
            pages = ocr_pdf(tmp_path, lang)
            full_text = " ".join([p["text"] for p in pages])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    else:
        # Imagem única
        text = ocr_with_tesseract(content, lang)
        if len(text.strip()) < 20:
            text = ocr_with_easyocr(content)
        full_text = text

    core = format_boleto_core_fields(full_text)

    # Armazena último JSON extraído em formato mínimo para consumo externo
    global last_json_extracted, ID_SEQUENCIAL
    ID_SEQUENCIAL += 1
    last_json_extracted = {
        "id_processo": ID_SEQUENCIAL,
        "arquivo": file.filename,
        "linha_digitavel": core.get("linha_digitavel"),
        "data_vencimento": core.get("vencimento"),
        "cnpj_beneficiario": core.get("beneficiario_cnpj"),
        "beneficiario": core.get("beneficiario_nome"),
        "status_pronto": True
    }

    return {
        "success": True,
        "source": file.filename,
        "fields": core
    }


@app.get("/get_last_json_extracted")
def get_last_json_extracted():
    """
    Retorna o último JSON extraído/simulado para consumo por outro agente (via GET).
    """
    if not last_json_extracted:
        raise HTTPException(status_code=404, detail="Nenhum dado extraído disponível.")
    # Oculta campos internos
    hidden_keys = {"id_processo", "arquivo", "status_pronto"}
    filtered = {k: v for k, v in last_json_extracted.items() if k not in hidden_keys}
    return filtered


@app.post("/extract-from-path")
async def extract_from_path(
    path: str = Form(...),
    lang: str = Form("por+eng"),
    extract_fields: bool = Form(False)
):
    """
    Extrai texto de arquivo pelo caminho no servidor
    
    Args:
        path: Caminho do arquivo no servidor
        lang: Idioma para OCR
        extract_fields: Se True, tenta extrair campos de boleto
    """
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {path}")
    
    ext = os.path.splitext(path)[1].lower()
    if ext not in [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não suportado: {ext}"
        )
    
    try:
        pages = []
        metadata = {
            "engine": "tesseract",
            "lang": lang
        }
        
        if ext == ".pdf":
            pages = ocr_pdf(path, lang)
            metadata["engine"] = "ocrmypdf+tesseract"
        else:
            with open(path, "rb") as f:
                content = f.read()
            
            text = ocr_with_tesseract(content, lang)
            if len(text.strip()) < 20:
                text = ocr_with_easyocr(content)
                metadata["engine"] = "easyocr"
            
            pages = [{"page": 1, "text": text}]
        
        # Extração de campos
        extracted_fields = None
        if extract_fields and pages:
            full_text = " ".join([p["text"] for p in pages])
            extracted_fields = extract_boleto_fields(full_text)
        
        result = {
            "success": True,
            "source": path,
            "pages": pages,
            "metadata": metadata
        }
        
        if extracted_fields:
            result["extracted_fields"] = extracted_fields
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Erro ao processar arquivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
