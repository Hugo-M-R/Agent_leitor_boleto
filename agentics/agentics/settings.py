import os


class Settings:
    def __init__(self) -> None:
        self.ocr_dpi: int = int(os.environ.get("OCR_DPI", "200"))
        self.ocr_max_pages: int = int(os.environ.get("OCR_MAX_PAGES", "1"))
        self.tesseract_cmd: str = os.environ.get("TESSERACT_CMD", "")
        self.poppler_path: str = os.environ.get("POPPLER_PATH", "")


def get_settings() -> Settings:
    return Settings()


