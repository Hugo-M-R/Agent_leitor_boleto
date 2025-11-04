"""Exemplo de uso das funções de conversão PDF -> Imagem + OCR"""

from agents.vencimento_agent import pdf_to_images, pdf_to_image_and_ocr, extract_payment_info
import json

# Exemplo 1: Converter PDF para imagens PNG/JPG e salvar
print("=== Exemplo 1: Converter PDF para imagens ===")
pdf_path = r".\dados\Modelo-de-Boleto.pdf"
imagens_geradas = pdf_to_images(
    pdf_path=pdf_path,
    output_dir=r".\imagens",  # Pasta onde salvar as imagens
    dpi=400,
    format="PNG"  # ou "JPG"
)

if imagens_geradas:
    print(f"OK: {len(imagens_geradas)} imagem(ns) salva(s):")
    for img in imagens_geradas:
        print(f"   - {img}")
else:
    print("ERRO: Falha na conversao (verifique se Poppler esta instalado)")

print("\n" + "="*50 + "\n")

# Exemplo 2: Converter PDF para imagem + OCR automático
print("=== Exemplo 2: PDF -> Imagem -> OCR -> Extração ===")
texto_ocr = pdf_to_image_and_ocr(
    pdf_path=pdf_path,
    save_images=True,  # Salva as imagens PNG geradas
    output_dir=r".\imagens"
)

if texto_ocr:
    print(f"OK: Texto extraido ({len(texto_ocr)} caracteres)")
    print(f"   Primeiros 200 caracteres: {texto_ocr[:200]}...")
    
    # Extrair informações do boleto
    print("\n=== Extraindo informacoes do boleto ===")
    info = extract_payment_info(texto_ocr)
    print(json.dumps(info, indent=2, ensure_ascii=False))
else:
    print("ERRO: Falha no OCR (verifique Tesseract/Poppler)")

