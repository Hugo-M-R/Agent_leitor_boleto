import re
from datetime import datetime
import os
from typing import List, Optional, Tuple, Dict


KEYWORDS = [
	"vencimento",
	"data de vencimento",
	"venc",
	"vcto",
	"pagamento até",
	"pagar até",
	"vencto",
]


# Padrões de datas comuns no BR: 15/11/2025, 15/11/25, 15-11-2025, 15.11.2025
# Aceita espaços ao redor dos separadores para lidar com extrações de PDF que inserem espaços.
DATE_REGEX = re.compile(
	 r"\b(\d{1,2})\s*[\./\-]\s*(\d{1,2})\s*[\./\-]\s*(\d{2,4})\b"
)

# Regex focado: keyword de vencimento seguida por até 60 caracteres (ruído, espaços, tabs, pontuação)
# e então a data. Isso ajuda quando o PDF injeta caixas/ruídos entre a palavra e a data.
KWD_DATE_REGEX = re.compile(
	 r"(vencimento|data\s+de\s+vencimento|venc|vcto|vencto|pagamento\s+até|pagar\s+até)[^\d]{0,60}(\d{1,2}\s*[\./\-]\s*\d{1,2}\s*[\./\-]\s*\d{2,4})",
	 re.IGNORECASE,
)

# Linha digitável de boletos: normalmente 47 (bancos) ou 48 (arrecadação) dígitos.
DIGITABLE_REGEX = re.compile(r"(?:\b|^)(?:\d[\s\.\-]?){44,56}(?:\b|$)")

# CNPJ: formatos com máscara ou só dígitos
CNPJ_MASKED_REGEX = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
CNPJ_PLAIN_REGEX = re.compile(r"\b\d{14}\b")
CPF_MASKED_REGEX = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
CPF_PLAIN_REGEX = re.compile(r"\b\d{11}\b")


def _normalize_year(two_or_four: str) -> int:
	if len(two_or_four) == 4:
		return int(two_or_four)
	yy = int(two_or_four)
	# Assunção simples: 00-49 => 2000-2049, 50-99 => 1950-1999
	return 2000 + yy if yy <= 49 else 1900 + yy


def _parse_date(d: str, m: str, y: str) -> Optional[datetime]:
	try:
		year = _normalize_year(y)
		return datetime(year, int(m), int(d))
	except ValueError:
		return None


def _find_all_dates(text: str) -> List[Tuple[datetime, Tuple[int, int]]]:
	results: List[Tuple[datetime, Tuple[int, int]]] = []
	# Tentativa 1: padrões gerais de datas
	for match in DATE_REGEX.finditer(text):
		day, month, year = match.group(1), match.group(2), match.group(3)
		parsed = _parse_date(day, month, year)
		if parsed is not None:
			results.append((parsed, match.span()))

	# Tentativa 2: padrões focados em keyword -> data (caso não tenha sido capturado acima ou para reforçar spans)
	for m in KWD_DATE_REGEX.finditer(text):
		date_text = m.group(2)
		m2 = DATE_REGEX.search(date_text)
		if not m2:
			continue
		day, month, year = m2.group(1), m2.group(2), m2.group(3)
		parsed = _parse_date(day, month, year)
		if parsed is None:
			continue
		# Span relativo ao texto completo (usa span da captura da data dentro do match principal)
		start = m.start(2)
		end = m.end(2)
		results.append((parsed, (start, end)))
	return results


def _find_keywords_positions(text: str) -> List[Tuple[str, Tuple[int, int]]]:
	positions: List[Tuple[str, Tuple[int, int]]] = []
	lower = text.lower()
	for kw in KEYWORDS:
		for m in re.finditer(re.escape(kw), lower):
			positions.append((kw, m.span()))
	return positions


def _score_date(span: Tuple[int, int], keyword_spans: List[Tuple[str, Tuple[int, int]]], text: str) -> float:
	if not keyword_spans:
		return 0.0
	# Distância mínima em caracteres a qualquer keyword
	start, end = span
	min_dist = min(
		min(abs(start - ks[0]), abs(end - ks[1])) for _, ks in keyword_spans
	)
	base_score = 1.0 / (1.0 + min_dist)

	# Bônus se estiver na mesma linha e à direita de alguma keyword (layout de tabela)
	try:
		line_start = text.rfind("\n", 0, start) + 1
		line_end = text.find("\n", end)
		if line_end == -1:
			line_end = len(text)
		line_text = text[line_start:line_end].lower()
		for kw, _ in keyword_spans:
			if kw in line_text:
				# distância em caracteres na linha
				kw_pos = line_text.find(kw)
				dt_pos = line_text.find(text[start:end].lower())
				if dt_pos != -1 and dt_pos >= kw_pos:
					base_score *= 3.0  # forte indício de associação
					break
	except Exception:
		pass

	return base_score


def extract_due_date(text: str) -> Optional[Dict[str, str]]:
	"""
	Extrai a data de vencimento de um texto de documento.

	Retorna um dicionário com:
	- "due_date": data normalizada em formato YYYY-MM-DD
	- "original": a data original como aparecia no texto (se disponível)
	- "confidence": string "high" | "medium" | "low"

	Se não encontrar, retorna None.
	"""
	if not text:
		return None

	dates = _find_all_dates(text)
	if not dates:
		return None

	kw_spans = _find_keywords_positions(text)

	# Seleciona a data com maior score de proximidade às keywords
	best = None
	best_score = -1.0
	for dt, span in dates:
		score = _score_date(span, kw_spans, text)
		if score > best_score:
			best = (dt, span)
			best_score = score

	assert best is not None
	best_dt, best_span = best

	# Extrai a substring original da data
	original = text[best_span[0]:best_span[1]]

	# Define confiança simples baseada na proximidade: >0.05 high, >0.005 medium, senão low
	confidence = "low"
	if best_score > 0.05:
		confidence = "high"
	elif best_score > 0.005:
		confidence = "medium"

	return {
		"due_date": best_dt.strftime("%Y-%m-%d"),
		"original": original,
		"confidence": confidence,
	}


def _clean_digits(s: str) -> str:
	return re.sub(r"\D+", "", s)


def _extract_linha_digitavel(text: str) -> Optional[str]:
	# Prioriza sequências que, após remover não-dígitos, tenham 47 ou 48 dígitos
	candidates = []
	for m in DIGITABLE_REGEX.finditer(text):
		raw = m.group(0)
		digits = _clean_digits(raw)
		if len(digits) in (47, 48):
			candidates.append(digits)
	# Remove duplicatas preservando ordem
	seen = set()
	ordered = []
	for d in candidates:
		if d not in seen:
			seen.add(d)
			ordered.append(d)
	return ordered[0] if ordered else None


def _extract_cnpj(text: str) -> Optional[str]:
	# 0) Evitar capturar números na mesma linha/linha próxima da linha digitável
	avoid_spans: List[Tuple[int, int]] = []
	for dmatch in DIGITABLE_REGEX.finditer(text):
		# marca a linha inteira da linha digitável como faixa de exclusão
		ls = text.rfind("\n", 0, dmatch.start()) + 1
		le = text.find("\n", dmatch.end())
		if le == -1:
			le = len(text)
		avoid_spans.append((ls, le))

	def _is_in_avoid(i: int) -> bool:
		for a, b in avoid_spans:
			if a <= i <= b:
				return True
		return False

	# 1) Preferir rótulos explícitos de CPF/CNPJ
	label_patterns = [
		r"(?i)\b(cpf\s*/\s*cnpj|cpf\s*[- ]?cnpj|cnpj\s*/\s*cpf)\b\s*[:\-]?\s*([\d\./\-]+)",
		r"(?i)\b(cpf\s*cnpj)\b\s*[:\-]?\s*([\d\./\-]+)",
		r"(?i)\b(cnpj)\b\s*[:\-]?\s*([\d\./\-]+)",
		r"(?i)\b(cpf)\b\s*[:\-]?\s*([\d\./\-]+)",
	]
	for pat in label_patterns:
		for m in re.finditer(pat, text):
			if _is_in_avoid(m.start()):
				continue
			value = (m.group(2) if m.lastindex and m.lastindex >= 2 else "").strip()
			digits = _clean_digits(value)
			if len(digits) == 14:  # CNPJ
				return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"
			if len(digits) == 11:  # CPF
				return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"

	# 2) Fallback: procurar CNPJ/CPF isolados mas fora da área de linha digitável
	for rx in (CNPJ_MASKED_REGEX, CPF_MASKED_REGEX, CNPJ_PLAIN_REGEX, CPF_PLAIN_REGEX):
		m = rx.search(text)
		if m and not _is_in_avoid(m.start()):
			d = _clean_digits(m.group(0))
			if len(d) == 14:
				return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"
			if len(d) == 11:
				return f"{d[0:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}"

	return None


def _looks_like_digitable(s: str) -> bool:
    digits = re.sub(r"\D+", "", s)
    return len(digits) >= 20 or bool(DIGITABLE_REGEX.search(s))


def _is_mostly_digits_or_codes(s: str) -> bool:
    digits = sum(ch.isdigit() for ch in s)
    return digits >= max(8, int(0.5 * max(1, len(s))))


def _extract_beneficiario(text: str) -> Optional[str]:
    # 1) Priorizar "Cedente". Se valor não estiver na mesma linha, pegar a próxima linha não vazia.
    cedente_pat = r"(?i)\b(cedente)\b\s*[:\-]?\s*(.*)"
    for m in re.finditer(cedente_pat, text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.end())
        if line_end == -1:
            line_end = len(text)
        line_text = text[line_start:line_end]
        # tenta após separador na mesma linha
        parts = re.split(r"[:\-]", line_text, maxsplit=1)
        cand = parts[1].strip() if len(parts) == 2 else ""
        cand = cand.split("\n")[0].strip()
        if not cand:
            # pega até 10 próximas linhas não vazias após "Cedente"
            scan_pos = line_end + 1
            stop_labels = (
                "cpf", "cnpj", "agência", "agencia", "código", "codigo",
                "benefici", "favorecido", "linha", "digit", "nosso", "número",
                "numero", "vencimento", "data", "valor", "carteira",
                "quantidade", "espécie", "especie", "agência/código do cedente",
                "agencia/codigo do cedente"
            )
            for _ in range(10):
                next_line_end = text.find("\n", scan_pos)
                if next_line_end == -1:
                    next_line_end = len(text)
                candidate_line = text[scan_pos:next_line_end].strip()
                scan_pos = next_line_end + 1
                if not candidate_line:
                    continue
                low = candidate_line.lower()
                # ignora linhas que são rótulos de doc: cpf/cnpj, agência, linha digitável, etc.
                if any(lbl in low for lbl in stop_labels):
                    continue
                if ("linha" in low and "digit" in low) or _looks_like_digitable(candidate_line) or _is_mostly_digits_or_codes(candidate_line):
                    continue
                cand = candidate_line
                break
        cand_clean = re.sub(r"\s+", " ", cand)
        if cand_clean and len(cand_clean) >= 3:
            low = cand_clean.lower()
            if not (("linha" in low and "digit" in low) or _looks_like_digitable(cand_clean) or _is_mostly_digits_or_codes(cand_clean)):
                if not (re.search(r"\b\d{3,}\b", cand_clean) and len(cand_clean.split()) <= 3):
                    return cand_clean

    # 2) Demais rótulos comuns
    patterns = [
        r"(?i)\b(beneficiário|beneficiario|favorecido)\b\s*[:\-]?\s*(.+)",
        r"(?i)\b(agência/código\s+beneficiário|agencia/codigo\s+beneficiario)\b\s*[:\-]?\s*(.+)",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            line = m.group(0)
            parts = re.split(r"[:\-]", line, maxsplit=1)
            if len(parts) != 2:
                continue
            cand = parts[1].split("\n")[0].strip()
            cand_clean = re.sub(r"\s+", " ", cand)
            if not cand_clean or len(cand_clean) < 3:
                continue
            low = cand_clean.lower()
            if "linha" in low and "digit" in low:
                continue
            if _looks_like_digitable(cand_clean) or _is_mostly_digits_or_codes(cand_clean):
                continue
            if re.search(r"\b\d{3,}\b", cand_clean) and len(cand_clean.split()) <= 3:
                continue
            return cand_clean

    # Fallback: linha anterior ao CNPJ, mas filtrando ruído
    cnpj_m = CNPJ_MASKED_REGEX.search(text) or CNPJ_PLAIN_REGEX.search(text)
    if cnpj_m:
        start = max(0, text.rfind("\n", 0, cnpj_m.start()))
        prev_line = text[start:cnpj_m.start()].strip().split("\n")[-1].strip()
        prev_line = re.sub(r"\s+", " ", prev_line)
        if 3 <= len(prev_line) <= 120 and not _looks_like_digitable(prev_line) and not _is_mostly_digits_or_codes(prev_line):
            low = prev_line.lower()
            if not ("linha" in low and "digit" in low):
                return prev_line
    return None


def extract_payment_info(text: str) -> Dict[str, Optional[str]]:
	"""Extrai informações principais de boleto do texto."""
	res_due = extract_due_date(text)
	return {
		"linha_digitavel": _extract_linha_digitavel(text),
		"data_vencimento": res_due.get("due_date") if res_due else None,
		"beneficiario": _extract_beneficiario(text),
		"cnpj_beneficiario": _extract_cnpj(text),
	}


def _read_text_file(path: str) -> str:
	with open(path, "r", encoding="utf-8", errors="ignore") as f:
		return f.read()


def _read_pdf_text(path: str) -> str:
	try:
		import PyPDF2  # type: ignore
	except Exception:
		return ""
	try:
		text_parts: List[str] = []
		with open(path, "rb") as f:
			reader = PyPDF2.PdfReader(f)
			for page in reader.pages:
				text_parts.append(page.extract_text() or "")
		text = "\n".join(text_parts)
		if text.strip():
			return text
		# Fallback: tentar pdfminer.six caso PyPDF2 não retorne texto útil
		try:
			from pdfminer.high_level import extract_text  # type: ignore
			text2 = extract_text(path) or ""
			if text2.strip():
				return text2
		except Exception:
			pass

		# Fallback OCR 1: pytesseract + pdf2image
		try:
			import pytesseract  # type: ignore
			from pdf2image import convert_from_path  # type: ignore
			images = convert_from_path(path, dpi=200)
			ocr_parts: List[str] = []
			for img in images[:5]:
				ocr_parts.append(pytesseract.image_to_string(img, lang="por+eng"))
			ocr_text = "\n".join(ocr_parts)
			if ocr_text.strip():
				return ocr_text
		except Exception:
			pass

		# Fallback OCR 2: EasyOCR (não requer binário do Tesseract)
		try:
			from pdf2image import convert_from_path  # type: ignore
			import numpy as _np  # type: ignore
			import easyocr  # type: ignore
			images = convert_from_path(path, dpi=200)
			reader = easyocr.Reader(["pt", "en"], gpu=False)
			ocr_parts: List[str] = []
			for img in images[:5]:
				arr = _np.array(img.convert("RGB"))
				lines = reader.readtext(arr, detail=False, paragraph=True)
				if lines:
					ocr_parts.append("\n".join(lines))
			return "\n".join(ocr_parts)
		except Exception:
			return ""
	except Exception:
		return ""


def _read_image_text(path: str) -> str:
	"""Extrai texto de imagens usando Tesseract, se disponível."""
	# Tentativa 1: pytesseract
	try:
		from PIL import Image  # type: ignore
		import pytesseract  # type: ignore
		img = Image.open(path)
		text = pytesseract.image_to_string(img, lang="por+eng") or ""
		if text.strip():
			return text
	except Exception:
		pass

	# Tentativa 2: EasyOCR
	try:
		from PIL import Image  # type: ignore
		import numpy as _np  # type: ignore
		import easyocr  # type: ignore
		img = Image.open(path).convert("RGB")
		reader = easyocr.Reader(["pt", "en"], gpu=False)
		lines = reader.readtext(_np.array(img), detail=False, paragraph=True)
		return "\n".join(lines)
	except Exception:
		return ""


def extract_due_date_from_path(path: str) -> Optional[Dict[str, str]]:
	path_lower = path.lower()
	text = ""
	if path_lower.endswith(".txt"):
		text = _read_text_file(path)
	elif path_lower.endswith(".pdf"):
		text = _read_pdf_text(path)
	elif path_lower.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")):
		text = _read_image_text(path)
	else:
		# formato não suportado no modo simples
		return None
	return extract_due_date(text)


def _next_extraction_path(base_dir: str) -> str:
	# encontra próximo extracao_N.json
	n = 1
	while True:
		candidate = os.path.join(base_dir, f"extracao_{n}.json")
		if not os.path.exists(candidate):
			return candidate
		n += 1


def _next_transcription_path(base_dir: str) -> str:
	# encontra próximo transcricao_N.json
	n = 1
	while True:
		candidate = os.path.join(base_dir, f"transcricao_{n}.json")
		if not os.path.exists(candidate):
			return candidate
		n += 1


def main() -> None:
	import argparse
	import json

	parser = argparse.ArgumentParser(description="Agente simples para extrair vencimento")
	parser.add_argument("input", help="Caminho do arquivo (.txt ou .pdf) ou '-' para stdin")
	parser.add_argument("--dump-text", action="store_true", help="Mantido por compatibilidade; agora o texto completo é sempre salvo em <arquivo>_texto.txt")
	args = parser.parse_args()

	if args.input == "-":
		import sys
		text = sys.stdin.read()
		res = extract_due_date(text)
	else:
		# Carrega texto bruto para possível dump, e extrai vencimento
		path_lower = args.input.lower()
		raw_text = ""
		if path_lower.endswith(".txt"):
			raw_text = _read_text_file(args.input)
		elif path_lower.endswith(".pdf"):
			raw_text = _read_pdf_text(args.input)
		elif path_lower.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")):
			raw_text = _read_image_text(args.input)
		# extrai informações completas
		payment_info = extract_payment_info(raw_text)
		res = {
			"due_date": payment_info.get("data_vencimento") or None,
			"original": "",
			"confidence": "",
		}

		# Caminho base apenas para referência de diretório
		base, _ = os.path.splitext(args.input)

		# Gravar JSON sequencial com as informações para outro agente (único arquivo gerado)
		try:
			import json as _json
			# Padroniza saída na pasta 'retornos' da CWD
			base_dir = os.path.join(os.getcwd(), "retornos")
			os.makedirs(base_dir, exist_ok=True)
			json_out = _next_extraction_path(base_dir)
			with open(json_out, "w", encoding="utf-8") as jf:
				jf.write(_json.dumps(payment_info, ensure_ascii=False, indent=2))

			# Gravar JSON de transcrição completa do documento
			trans_out = _next_transcription_path(base_dir)
			with open(trans_out, "w", encoding="utf-8") as tf:
				_tf_obj = {"transcricao": raw_text or ""}
				tf.write(_json.dumps(_tf_obj, ensure_ascii=False, indent=2))
		except Exception:
			pass

	print(json.dumps(res or {}, ensure_ascii=False))


if __name__ == "__main__":
	main()


