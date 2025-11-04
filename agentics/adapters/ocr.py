"""OCR para imagens e PDFs (via utilitário), com Tesseract e EasyOCR.

Inclui normalizações para reduzir erros comuns de OCR em números e separadores.
"""

import os
import shutil
from typing import List

# Suporte a execução como pacote (agentics.*) e como módulos no topo (/app)
try:
    from agentics.settings import get_settings
except ImportError:
    from settings import get_settings


def _normalize_ocr_text(text: str) -> str:
    """Normaliza texto OCR corrigindo caracteres comuns e espaçamentos entre dígitos."""
    import re
    if not text:
        return text
    out = text.replace("\r", "\n")
    out = re.sub(r"[\t\f\v]+", " ", out)
    def _num_ctx(subst_pattern: str, repl: str, s: str) -> str:
        return re.sub(rf"(?<=\d|[\./\-\s]){subst_pattern}(?=\d|[\./\-\s])", repl, s)
    out = _num_ctx(r"[Oo]", "0", out)
    out = _num_ctx(r"[Il\|]", "1", out)
    out = _num_ctx(r"S", "5", out)
    out = _num_ctx(r"B", "8", out)
    out = _num_ctx(r"Z", "2", out)
    out = _num_ctx(r"g", "9", out)
    out = _num_ctx(r",", ".", out)
    out = re.sub(r"(?<=\d)[\s\._-]{1,}(?=\d)", " ", out)
    out = re.sub(r"(?<=\d)[^\d\s\./-]{1,2}(?=\d)", " ", out)
    out = re.sub(r"[ ]{2,}", " ", out)
    return out


def _read_image_text(path: str) -> str:
    """Executa OCR em uma imagem com pré-processamento e múltiplas passadas.

    Prioriza Tesseract; em falha, tenta EasyOCR.
    """
    try:
        from PIL import Image, ImageEnhance  # type: ignore
        import pytesseract  # type: ignore
        settings = get_settings()
        tesseract_cmd = settings.tesseract_cmd
        if not tesseract_cmd:
            # Primeiro tenta encontrar via PATH (funciona no Linux/Docker)
            tesseract_cmd = shutil.which("tesseract")
            if not tesseract_cmd:
                # Fallbacks específicos por plataforma
                if os.name == "nt":  # Windows
                    common_paths = [
                        r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
                        r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
                    ]
                else:  # Linux (Docker)
                    common_paths = [
                        "/usr/bin/tesseract",
                        "/usr/local/bin/tesseract",
                    ]
                for p in common_paths:
                    if os.path.exists(p):
                        tesseract_cmd = p
                        break
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        # Pré-processamento: rotações + escala + contraste (+ threshold com cv2 se disponível)
        img0 = Image.open(path).convert("L")
        try:
            import cv2  # type: ignore
            import numpy as _np  # type: ignore
            _has_cv2 = True
        except Exception:
            _has_cv2 = False

        def _preproc(pil_img: "Image.Image") -> "Image.Image":
            # escala leve e aumento de contraste
            w, h = pil_img.size
            pil_img = pil_img.resize((int(w * 1.5), int(h * 1.5)))
            pil_img = ImageEnhance.Contrast(pil_img).enhance(1.8)
            if _has_cv2:
                arr = _np.array(pil_img)
                arr = cv2.adaptiveThreshold(arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)
                from PIL import Image as _Image
                return _Image.fromarray(arr)
            return pil_img

        texts: list[str] = []
        for angle in (0, 90, 180, 270):
            img_rot = img0.rotate(angle, expand=True)
            img_pp = _preproc(img_rot)
            # Passadas gerais (pt+en) com PSM diferentes
            t1_parts: list[str] = []
            for psm in (6, 7, 11):
                t_try = pytesseract.image_to_string(
                    img_pp, lang="por+eng", config=f"--oem 3 --psm {psm}"
                ) or ""
                if t_try.strip():
                    t1_parts.append(t_try)
            t1 = "\n".join(t1_parts)
            if t1.strip():
                texts.append(t1)
            # Passadas focadas em dígitos e separadores (boa para linha digitável/valores)
            t2_parts: list[str] = []
            for psm in (6, 7, 11):
                t_try = pytesseract.image_to_string(
                    img_pp,
                    lang="eng",
                    config=f"--oem 3 --psm {psm} -c tessedit_char_whitelist=0123456789./-"
                ) or ""
                if t_try.strip():
                    t2_parts.append(t_try)
            t2 = "\n".join(t2_parts)
            if t2.strip():
                texts.append(t2)
        text = "\n".join([t for t in texts if t.strip()])
        if text.strip():
            try:
                from agentics.adapters.post_ocr import postprocess_text  # type: ignore
            except Exception:
                postprocess_text = lambda s: s  # type: ignore
            try:
                normalized = _normalize_ocr_text(text)
            except Exception:
                normalized = text
            return postprocess_text(normalized)
    except Exception as e:
        # Log do erro para debug (pode ser removido em produção se necessário)
        import sys
        print(f"Erro no Tesseract OCR: {e}", file=sys.stderr)
        pass
    try:
        from PIL import Image  # type: ignore
        import numpy as _np  # type: ignore
        import easyocr  # type: ignore
        img = Image.open(path).convert("RGB")
        reader = easyocr.Reader(["pt", "en"], gpu=False)
        lines = reader.readtext(_np.array(img), detail=False, paragraph=True)
        text = "\n".join(lines)
        if text.strip():
            try:
                return _normalize_ocr_text(text)
            except Exception:
                return text
    except Exception as e:
        # Log do erro para debug
        import sys
        print(f"Erro no EasyOCR: {e}", file=sys.stderr)
        return ""


def pdf_to_image_and_ocr(pdf_path: str, save_images: bool = False, output_dir: str | None = None) -> str:
    """Gera imagens das páginas e aplica OCR agregando o texto resultante."""
    try:
        from PIL import ImageEnhance  # type: ignore
        import easyocr  # type: ignore
        try:
            from agentics.adapters.pdf import _pdf_pages_to_images_pymupdf
        except ImportError:
            from adapters.pdf import _pdf_pages_to_images_pymupdf
        settings = get_settings()
        images = _pdf_pages_to_images_pymupdf(pdf_path, settings.ocr_dpi)
        if save_images and output_dir:
            import os as _os
            _os.makedirs(output_dir, exist_ok=True)
            base_name = _os.path.splitext(_os.path.basename(pdf_path))[0]
            for i, img in enumerate(images[:settings.ocr_max_pages]):
                img_path = _os.path.join(output_dir, f"{base_name}_page_{i+1}.png")
                img.save(img_path, "PNG")
        reader = easyocr.Reader(["pt", "en"], gpu=False)
        ocr_parts: List[str] = []
        for img in images[:settings.ocr_max_pages]:
            img_gray = img.convert("L")
            enhancer = ImageEnhance.Contrast(img_gray)
            img_contrast = enhancer.enhance(2.0)
            _np = __import__("numpy")
            arr = _np.array(img_contrast.convert("RGB"))
            lines = reader.readtext(arr, detail=False, paragraph=True)
            if lines:
                ocr_parts.append("\n".join(lines))
        return "\n".join(ocr_parts)
    except Exception:
        return ""


