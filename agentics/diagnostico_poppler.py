"""Script de diagnostico para encontrar Poppler e Tesseract"""

import os
import sys

print("=== DIAGNOSTICO POPPLER E TESSERACT ===\n")

# 1. Verificar variáveis de ambiente
print("1. Variaveis de ambiente:")
pop_env = os.environ.get("POPPLER_PATH")
tess_env = os.environ.get("TESSERACT_CMD")
print(f"   POPPLER_PATH: {pop_env or 'NAO DEFINIDA'}")
print(f"   TESSERACT_CMD: {tess_env or 'NAO DEFINIDA'}")

# 2. Procurar Poppler nos caminhos comuns
print("\n2. Procurando Poppler nos caminhos comuns:")
candidates_pop = [
    r"C:\Program Files\poppler\Library\bin",
    r"C:\poppler\bin",
    r"C:\poppler\Library\bin",
    r"C:\tools\poppler\bin",
    r"C:\Program Files (x86)\poppler\Library\bin",
]
encontrado_pop = None
for cand in candidates_pop:
    if os.path.exists(cand):
        pdfinfo = os.path.join(cand, "pdfinfo.exe")
        if os.path.exists(pdfinfo):
            print(f"   ENCONTRADO: {cand}")
            encontrado_pop = cand
            break
        else:
            print(f"   Pasta existe mas sem pdfinfo.exe: {cand}")
    else:
        print(f"   Nao encontrado: {cand}")

if not encontrado_pop:
    print("\n   POPPLER NAO ENCONTRADO!")
    print("\n   SOLUCAO:")
    print("   1. Baixe Poppler for Windows: https://github.com/oschwartz10612/poppler-windows/releases/")
    print("   2. Extraia em uma pasta (ex: C:\\poppler)")
    print("   3. Configure a variavel de ambiente:")
    print("      $env:POPPLER_PATH = 'C:\\poppler\\Library\\bin'")
    print("   4. OU adicione a pasta ao PATH do Windows")

# 3. Procurar Tesseract
print("\n3. Procurando Tesseract:")
candidates_tess = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
encontrado_tess = None
for cand in candidates_tess:
    if os.path.exists(cand):
        print(f"   ENCONTRADO: {cand}")
        encontrado_tess = cand
        break
    else:
        print(f"   Nao encontrado: {cand}")

if not encontrado_tess:
    print("\n   TESSERACT NAO ENCONTRADO!")
    print("\n   SOLUCAO:")
    print("   1. Baixe Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
    print("   2. Instale selecionando idioma Portugues")
    print("   3. Configure se necessario:")
    print("      $env:TESSERACT_CMD = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'")

# 4. Testar importações Python
print("\n4. Bibliotecas Python instaladas:")
try:
    from pdf2image import convert_from_path
    print("   OK: pdf2image")
except ImportError:
    print("   ERRO: pdf2image nao instalado (pip install pdf2image)")

try:
    import pytesseract
    print("   OK: pytesseract")
except ImportError:
    print("   ERRO: pytesseract nao instalado (pip install pytesseract)")

try:
    import easyocr
    print("   OK: easyocr")
except ImportError:
    print("   ERRO: easyocr nao instalado (pip install easyocr)")

# 5. Teste prático se Poppler encontrado
if encontrado_pop:
    print(f"\n5. Testando conversao PDF com Poppler em: {encontrado_pop}")
    try:
        from pdf2image import convert_from_path
        test_pdf = r".\dados\Modelo-de-Boleto.pdf"
        if os.path.exists(test_pdf):
            images = convert_from_path(test_pdf, dpi=200, poppler_path=encontrado_pop, first_page=1, last_page=1)
            print(f"   SUCESSO! Convertido 1 pagina do PDF")
            print(f"   Tamanho da imagem: {images[0].size}")
        else:
            print(f"   PDF de teste nao encontrado: {test_pdf}")
    except Exception as e:
        print(f"   ERRO no teste: {e}")
        print(f"   Detalhes: {type(e).__name__}")

print("\n" + "="*60)
print("RECOMENDACAO:")
if encontrado_pop:
    print(f"Configure: $env:POPPLER_PATH = '{encontrado_pop}'")
else:
    print("Instale Poppler e configure POPPLER_PATH")
if encontrado_tess:
    print(f"Tesseract OK: {encontrado_tess}")
else:
    print("Instale Tesseract com suporte a Portugues")

