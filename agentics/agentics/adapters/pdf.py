import os
import shutil
from typing import List, Any

from agentics.settings import get_settings


def _pdf_pages_to_images_pymupdf(path: str, dpi: int) -> List[Any]:
    import fitz  # type: ignore
    from PIL import Image  # type: ignore
    images: List["Image.Image"] = []
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    with fitz.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
    return images


def _has_text_in_pdf(path: str) -> bool:
    try:
        import PyPDF2  # type: ignore
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            if len(reader.pages) > 0:
                first_page_text = reader.pages[0].extract_text() or ""
                return len(first_page_text.strip()) > 10
    except Exception:
        pass
    return False


def _read_pdf_text(path: str) -> str:
    has_text = _has_text_in_pdf(path)
    try:
        import PyPDF2  # type: ignore
    except Exception:
        PyPDF2 = None  # type: ignore
    if has_text and PyPDF2 is not None:
        try:
            text_parts: List[str] = []
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text_parts.append(page.extract_text() or "")
            text = "\n".join(text_parts)
            if text.strip():
                return text
        except Exception:
            pass
    try:
        from pdfminer.high_level import extract_text  # type: ignore
        text2 = extract_text(path) or ""
        if text2.strip():
            return text2
    except Exception:
        pass
    try:
        # OCRmyPDF: adiciona camada de texto com Tesseract no próprio PDF
        # Melhorias: forçar OCR, DPI alto, limpeza e threshold
        import subprocess, tempfile  # type: ignore
        o_path = tempfile.mktemp(suffix="_ocr.pdf")
        lang = os.environ.get("OCR_LANG", "por")
        dpi = str(get_settings().ocr_dpi or 400)
        cmd = [
            "ocrmypdf",
            "--rotate-pages", "--deskew", "--force-ocr",
            "--clean", "--threshold",
            "--image-dpi", dpi,
            "-l", lang,
            path, o_path,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            from pdfminer.high_level import extract_text  # type: ignore
            from agentics.adapters.post_ocr import postprocess_text  # type: ignore
            t = extract_text(o_path) or ""
            if t.strip():
                return postprocess_text(t)
        except Exception:
            pass
        try:
            import fitz  # type: ignore
            from agentics.adapters.post_ocr import postprocess_text  # type: ignore
            parts: list[str] = []
            with fitz.open(o_path) as doc:
                for page in doc:
                    parts.append(page.get_text() or "")
            t2 = "\n".join(parts)
            if t2.strip():
                return postprocess_text(t2)
        except Exception:
            pass
    except Exception:
        pass
    try:
        import pytesseract  # type: ignore
        from pdf2image import convert_from_path  # type: ignore
        from PIL import ImageEnhance  # type: ignore
        try:
            import cv2  # type: ignore
            _has_cv2 = True
        except Exception:
            _has_cv2 = False
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
        images = convert_from_path(path, dpi=settings.ocr_dpi)
        ocr_parts: List[str] = []
        processed = 0
        for img in images:
            if processed >= settings.ocr_max_pages:
                break
            img_gray = img.convert("L")
            enhancer = ImageEnhance.Contrast(img_gray)
            img_contrast = enhancer.enhance(2.0)
            if _has_cv2:
                import numpy as _np  # type: ignore
                arr = _np.array(img_gray)
                arr = cv2.resize(arr, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
                thr = cv2.adaptiveThreshold(arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)
                ocr_parts.append(pytesseract.image_to_string(thr, lang="por+eng", config="--oem 3 --psm 6"))
                ocr_parts.append(pytesseract.image_to_string(thr, lang="eng", config="--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789./-"))
            else:
                ocr_parts.append(pytesseract.image_to_string(img_contrast, lang="por+eng", config="--oem 3 --psm 6"))
                ocr_parts.append(pytesseract.image_to_string(img_contrast, lang="eng", config="--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789./-"))
            processed += 1
        return "\n".join(ocr_parts)
    except Exception:
        pass
    try:
        from PIL import ImageEnhance  # type: ignore
        import easyocr  # type: ignore
        settings = get_settings()
        images = _pdf_pages_to_images_pymupdf(path, settings.ocr_dpi)
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
        pass
    return ""


def pdf_to_images(pdf_path: str, output_dir: str | None = None, dpi: int = 400, format: str = "PNG") -> List[str]:
    try:
        settings = get_settings()
        dpi_eff = int(os.environ.get("OCR_DPI", str(dpi))) or settings.ocr_dpi
        images = _pdf_pages_to_images_pymupdf(pdf_path, dpi_eff)
        from typing import List as _List
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            saved_paths: _List[str] = []
            max_pages = settings.ocr_max_pages
            for i, img in enumerate(images[:max_pages]):
                ext = "png" if format.upper() == "PNG" else "jpg"
                img_path = os.path.join(output_dir, f"{base_name}_page_{i+1}.{ext}")
                img.save(img_path, format.upper())
                saved_paths.append(img_path)
            return saved_paths
        else:
            import tempfile
            temp_dir = tempfile.mkdtemp()
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            saved_paths: _List[str] = []
            max_pages = settings.ocr_max_pages
            for i, img in enumerate(images[:max_pages]):
                ext = "png" if format.upper() == "PNG" else "jpg"
                img_path = os.path.join(temp_dir, f"{base_name}_page_{i+1}.{ext}")
                img.save(img_path, format.upper())
                saved_paths.append(img_path)
            return saved_paths
    except Exception:
        return []


