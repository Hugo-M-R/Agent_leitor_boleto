from typing import Optional, Dict, Any, List
import os
import json

from agentics.facade import (
    extract_payment_info,
    extract_due_date,
    extract_due_date_from_path,
    _read_pdf_text,
    _read_image_text,
    _read_text_file,
    pdf_to_images,
    pdf_to_image_and_ocr,
    next_extraction_path as _next_extraction_path,
    next_transcription_path as _next_transcription_path,
    last_transcription_path as _last_transcription_path,
    is_duplicate_transcription as _is_duplicate_transcription,
)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Agente simples para extrair vencimento")
    parser.add_argument("input", help="Caminho do arquivo (.txt ou .pdf) ou '-' para stdin")
    parser.add_argument("--dump-text", action="store_true", help="Mantido por compatibilidade; agora o texto completo é sempre salvo em <arquivo>_texto.txt")
    args = parser.parse_args()

    def _resolve_input_path(user_path: str) -> str:
        if os.path.exists(user_path):
            return user_path
        dados_dir = os.path.join(os.getcwd(), "dados")
        dados_path = os.path.join(dados_dir, user_path)
        if os.path.exists(dados_path):
            return dados_path
        try:
            for fname in os.listdir(dados_dir):
                if fname.lower() == os.path.basename(user_path).lower():
                    return os.path.join(dados_dir, fname)
        except Exception:
            pass
        return user_path

    input_path = _resolve_input_path(args.input)

    if args.input == "-":
        import sys
        text = sys.stdin.read()
        res = extract_due_date(text)
    else:
        path_lower = input_path.lower()
        raw_text = ""
        if path_lower.endswith(".txt"):
            raw_text = _read_text_file(input_path)
        elif path_lower.endswith(".pdf"):
            raw_text = _read_pdf_text(input_path)
        elif path_lower.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")):
            raw_text = _read_image_text(input_path)
        payment_info = extract_payment_info(raw_text)
        res = {
            "due_date": payment_info.get("data_vencimento") or None,
            "original": "",
            "confidence": "",
        }
        try:
            base_dir = os.path.join(os.getcwd(), "retornos")
            os.makedirs(base_dir, exist_ok=True)
            json_out = _next_extraction_path(base_dir)
            with open(json_out, "w", encoding="utf-8") as jf:
                jf.write(json.dumps(payment_info, ensure_ascii=False, indent=2))
            new_text = raw_text or ""
            if not _is_duplicate_transcription(base_dir, new_text):
                trans_out = _next_transcription_path(base_dir)
                with open(trans_out, "w", encoding="utf-8") as tf:
                    _tf_obj = {"transcricao": new_text}
                    tf.write(json.dumps(_tf_obj, ensure_ascii=False, indent=2))
        except Exception:
            pass

    print(json.dumps(res or {}, ensure_ascii=False))


if __name__ == "__main__":
    main()


