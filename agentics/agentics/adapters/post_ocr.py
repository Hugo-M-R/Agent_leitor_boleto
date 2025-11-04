import os


def postprocess_text(text: str) -> str:
    """Opcionalmente melhora texto OCR usando Gemini, se configurado.

    Usa GEMINI_API_KEY e o modelo gemini-1.5-flash por padrão.
    Em qualquer erro ou falta de dependências, retorna o texto original.
    """
    try:
        if not text or not text.strip():
            return text
        if os.environ.get("POST_OCR_ENABLED", "1") not in ("1", "true", "TRUE", "True"):
            return text
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return text
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=api_key)
        model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)
        prompt = (
            "Corrija o texto OCR abaixo mantendo apenas o conteúdo útil do boleto, "
            "sem comentários, sem notas e sem formatação adicional. "
            "Corrija erros ortográficos típicos de OCR e preserve números e datas.\n\n" 
            "TEXTO OCR:\n" + text
        )
        resp = model.generate_content(prompt)
        cleaned = (resp.text or "").strip()
        return cleaned or text
    except Exception:
        return text


