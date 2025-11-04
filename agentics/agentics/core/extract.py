import re
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any


KEYWORDS = [
    "vencimento",
    "data de vencimento",
    "venc",
    "vcto",
    "pagamento até",
    "pagar até",
    "vencto",
]


DATE_REGEX = re.compile(r"\b(\d{1,2})\s*[\./\-]\s*(\d{1,2})\s*[\./\-]\s*(\d{2,4})\b")
KWD_DATE_REGEX = re.compile(
    r"(vencimento|data\s+de\s+vencimento|venc|vcto|vencto|pagamento\s+até|pagar\s+até)[^\d]{0,60}(\d{1,2}\s*[\./\-]\s*\d{1,2}\s*[\./\-]\s*\d{2,4})",
    re.IGNORECASE,
)

DIGITABLE_REGEX = re.compile(r"(?:\b|^)(?:\d[\s\.-]?){44,56}(?:\b|$)")
CNPJ_MASKED_REGEX = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
CNPJ_PLAIN_REGEX = re.compile(r"\b\d{14}\b")
CPF_MASKED_REGEX = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
CPF_PLAIN_REGEX = re.compile(r"\b\d{11}\b")


def _normalize_year(two_or_four: str) -> int:
    if len(two_or_four) == 4:
        return int(two_or_four)
    yy = int(two_or_four)
    return 2000 + yy if yy <= 49 else 1900 + yy


def _parse_date(d: str, m: str, y: str) -> Optional[datetime]:
    try:
        year = _normalize_year(y)
        return datetime(year, int(m), int(d))
    except ValueError:
        return None


def _find_all_dates(text: str) -> List[Tuple[datetime, Tuple[int, int]]]:
    results: List[Tuple[datetime, Tuple[int, int]]] = []
    for match in DATE_REGEX.finditer(text):
        day, month, year = match.group(1), match.group(2), match.group(3)
        parsed = _parse_date(day, month, year)
        if parsed is not None:
            results.append((parsed, match.span()))
    for m in KWD_DATE_REGEX.finditer(text):
        date_text = m.group(2)
        m2 = DATE_REGEX.search(date_text)
        if not m2:
            continue
        day, month, year = m2.group(1), m2.group(2), m2.group(3)
        parsed = _parse_date(day, month, year)
        if parsed is None:
            continue
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
    start, end = span
    min_dist = min(
        min(abs(start - ks[0]), abs(end - ks[1])) for _, ks in keyword_spans
    )
    base_score = 1.0 / (1.0 + min_dist)
    try:
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", end)
        if line_end == -1:
            line_end = len(text)
        line_text = text[line_start:line_end].lower()
        for kw, _ in keyword_spans:
            if kw in line_text:
                kw_pos = line_text.find(kw)
                dt_pos = line_text.find(text[start:end].lower())
                if dt_pos != -1 and dt_pos >= kw_pos:
                    base_score *= 3.0
                    break
    except Exception:
        pass
    return base_score


def extract_due_date(text: str) -> Optional[Dict[str, str]]:
    if not text:
        return None
    dates = _find_all_dates(text)
    if not dates:
        return None
    kw_spans = _find_keywords_positions(text)
    best = None
    best_score = -1.0
    for dt, span in dates:
        score = _score_date(span, kw_spans, text)
        if score > best_score:
            best = (dt, span)
            best_score = score
    assert best is not None
    best_dt, best_span = best
    original = text[best_span[0]:best_span[1]]
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


def _modulo11_codigo_barras(campo: str) -> int:
    soma = 0
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    idx = 0
    for d in reversed(campo):
        soma += int(d) * pesos[idx % len(pesos)]
        idx += 1
        resto = soma % 11
    if resto < 2:
        return 0
    return 11 - resto


def _modulo10_linha_digitavel(campo: str) -> int:
    soma = 0
    soma_val = 0
    mult = 2
    for d in reversed(campo):
        prod = int(d) * mult
        if prod > 9:
            prod = sum(int(x) for x in str(prod))
        soma_val += prod
        mult = 3 - mult
    resto = soma_val % 10
    if resto == 0:
        return 0
    return 10 - resto


def _validate_linha_digitavel(linha: str) -> Dict[str, Any]:
    digits = _clean_digits(linha)
    if len(digits) != 47:
        return {"valido": False, "erro": f"Linha digitável deve ter 47 dígitos, encontrados {len(digits)}", "detalhes": {}}
    bloco1 = digits[0:9]
    dv1 = int(digits[9])
    bloco2 = digits[10:20]
    dv2 = int(digits[20])
    bloco3 = digits[21:31]
    dv3 = int(digits[31])
    bloco4 = digits[32:47]
    ok1 = _modulo10_linha_digitavel(bloco1) == dv1
    ok2 = _modulo10_linha_digitavel(bloco2) == dv2
    ok3 = _modulo10_linha_digitavel(bloco3) == dv3
    cod_banco = digits[0:3]
    moeda = digits[3]
    fator_venc = int(digits[33:37])
    valor_str = digits[37:47]
    data_base = datetime(1997, 10, 7)
    try:
        from datetime import timedelta
        venc_dt = data_base + timedelta(days=fator_venc)
    except Exception:
        venc_dt = None
    valor = float(valor_str) / 100.0 if valor_str else None
    codigo_barras_44 = cod_banco + moeda + f"{fator_venc:04d}" + valor_str + bloco1[4:] + bloco2 + bloco3
    if len(codigo_barras_44) >= 4:
        _ = _modulo11_codigo_barras(codigo_barras_44)
    return {
        "valido": ok1 and ok2 and ok3,
        "erro": None if (ok1 and ok2 and ok3) else "Um ou mais dígitos verificadores estão incorretos",
        "detalhes": {
            "codigo_banco": cod_banco,
            "moeda": moeda,
            "fator_vencimento": fator_venc,
            "data_vencimento_do_fator": venc_dt.strftime("%Y-%m-%d") if venc_dt else None,
            "valor": valor,
            "validacao_bloco1": ok1,
            "validacao_bloco2": ok2,
            "validacao_bloco3": ok3,
        }
    }


def _extract_valor_boleto(text: str) -> Optional[float]:
    patterns = [
        r"(?i)valor\s*(?:do\s+)?(?:documento|boleto)?\s*[:\-]?\s*r?\$?\s*([\d.,]+)",
        r"(?i)valor\s*(?:a\s+)?(?:pagar|cobrar)?\s*[:\-]?\s*r?\$?\s*([\d.,]+)",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            valor_str = m.group(1).replace(".", "").replace(",", ".")
            try:
                return float(valor_str)
            except Exception:
                continue
    return None


def _extract_banco_emissor(text: str) -> Optional[str]:
    banco_pat = r"(?i)banco\s+(\d{3})|\b(\d{3})\s*-\s*(?:banese|brasil|banco|bradesco|itau|caixa|santander|bb)"
    for m in re.finditer(banco_pat, text):
        cod = m.group(1) or m.group(2)
        if cod:
            return cod
    return None


def _extract_nosso_numero(text: str) -> Optional[str]:
    pat = r"(?i)nosso\s+n(?:ú|u)mero\s*[:\-]?\s*([\d\s\-\.]+)"
    for m in re.finditer(pat, text):
        nn = re.sub(r"\s+", "", m.group(1))
        if nn:
            return nn
    return None


def _looks_like_digitable(s: str) -> bool:
    digits = re.sub(r"\D+", "", s)
    return len(digits) >= 20 or bool(DIGITABLE_REGEX.search(s))


def _is_mostly_digits_or_codes(s: str) -> bool:
    digits = sum(ch.isdigit() for ch in s)
    return digits >= max(8, int(0.5 * max(1, len(s))))


def _extract_beneficiario(text: str) -> Optional[str]:
    cedente_pat = r"(?i)\b(cedente)\b\s*[:\-]?\s*(.*)"
    for m in re.finditer(cedente_pat, text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.end())
        if line_end == -1:
            line_end = len(text)
        line_text = text[line_start:line_end]
        parts = re.split(r"[:\-]", line_text, maxsplit=1)
        cand = parts[1].strip() if len(parts) == 2 else ""
        cand = cand.split("\n")[0].strip()
        if not cand:
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


def _extract_linha_digitavel(text: str) -> Optional[str]:
    candidates = []
    for m in DIGITABLE_REGEX.finditer(text):
        raw = m.group(0)
        digits = _clean_digits(raw)
        if len(digits) in (47, 48):
            candidates.append(digits)
    if not candidates:
        flex = re.compile(r"((?:\d[\s\u00A0\.-\u2013\u2014]{0,3}){45,70})")
        for m in flex.finditer(text):
            digits = _clean_digits(m.group(1))
            if len(digits) in (47, 48):
                candidates.append(digits)
        if not candidates:
            flex2 = re.compile(r"([\d\s\u00A0\.-\u2013\u2014]{60,150})")
            for m in flex2.finditer(text):
                digits = _clean_digits(m.group(1))
                if 45 <= len(digits) <= 80:
                    candidates.append(digits)
    if not candidates:
        for line in text.splitlines():
            clean = _clean_digits(line)
            if 40 <= len(clean) <= 60:
                candidates.append(clean)
    seen = set()
    ordered = []
    for d in candidates:
        if d not in seen:
            seen.add(d)
            ordered.append(d)
    for d in ordered:
        if len(d) in (47, 48):
            return d
    for d in ordered:
        if len(d) > 48:
            for L in (48, 47):
                for i in range(0, len(d) - L + 1):
                    seg = d[i:i+L]
                    if seg[:3].isdigit() and seg[3] in ("9", "6", "8", "7"):
                        return seg
    return ordered[0] if ordered else None


def extract_payment_info(text: str) -> Dict[str, Any]:
    res_due = extract_due_date(text)
    linha_dig = _extract_linha_digitavel(text)
    validacao_linha = None
    if linha_dig:
        validacao_linha = _validate_linha_digitavel(linha_dig)
    valor = _extract_valor_boleto(text)
    banco_emissor = _extract_banco_emissor(text)
    nosso_numero = _extract_nosso_numero(text)
    validacoes = {
        "linha_digitavel": validacao_linha or {"valido": False, "erro": "Linha digitável não encontrada", "detalhes": {}},
        "data_vencimento": {
            "valido": res_due is not None and res_due.get("due_date") is not None,
            "valor": res_due.get("due_date") if res_due else None,
            "confianca": res_due.get("confidence") if res_due else "low",
        },
        "valor": {
            "valido": valor is not None and valor > 0,
            "valor": valor,
            "valor_da_linha_digitavel": validacao_linha.get("detalhes", {}).get("valor") if validacao_linha else None,
        },
        "banco_emissor": {
            "valido": banco_emissor is not None,
            "codigo": banco_emissor,
            "codigo_da_linha_digitavel": validacao_linha.get("detalhes", {}).get("codigo_banco") if validacao_linha else None,
            "consistente": banco_emissor == validacao_linha.get("detalhes", {}).get("codigo_banco") if (banco_emissor and validacao_linha) else None,
        },
        "beneficiario": {
            "valido": _extract_beneficiario(text) is not None,
            "nome": _extract_beneficiario(text),
        },
        "cnpj_beneficiario": {
            "valido": _extract_cnpj(text) is not None,
            "valor": _extract_cnpj(text),
        },
    }
    boleto_valido = validacoes["linha_digitavel"]["valido"] and validacoes["data_vencimento"]["valido"]
    if valor and validacao_linha and validacao_linha.get("detalhes", {}).get("valor"):
        boleto_valido = boleto_valido and abs(valor - validacao_linha["detalhes"]["valor"]) < 0.01
    return {
        "linha_digitavel": linha_dig,
        "data_vencimento": res_due.get("due_date") if res_due else None,
        "beneficiario": _extract_beneficiario(text),
        "cnpj_beneficiario": _extract_cnpj(text),
        "valor": valor,
        "banco_emissor": banco_emissor,
        "nosso_numero": nosso_numero,
        "validacoes": validacoes,
        "boleto_valido": boleto_valido,
    }


def _extract_cnpj(text: str) -> Optional[str]:
    avoid_spans: List[Tuple[int, int]] = []
    for dmatch in DIGITABLE_REGEX.finditer(text):
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
            if len(digits) == 14:
                return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"
            if len(digits) == 11:
                return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"
    for rx in (CNPJ_MASKED_REGEX, CPF_MASKED_REGEX, CNPJ_PLAIN_REGEX, CPF_PLAIN_REGEX):
        m = rx.search(text)
        if m and not _is_in_avoid(m.start()):
            d = _clean_digits(m.group(0))
            if len(d) == 14:
                return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"
            if len(d) == 11:
                return f"{d[0:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}"
    return None


