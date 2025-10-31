import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from agents.vencimento_agent import (
	extract_payment_info,
	_read_pdf_text,
	_read_image_text,
	_read_text_file,
	_next_extraction_path,
	_next_transcription_path,
	_is_duplicate_transcription,
)


router = APIRouter()


class ExtractResponse(BaseModel):
	linha_digitavel: Optional[str]
	data_vencimento: Optional[str]
	beneficiario: Optional[str]
	cnpj_beneficiario: Optional[str]
	transcricao_path: Optional[str] = None
	extracao_path: Optional[str] = None


def _ensure_returns_dir() -> str:
	base_dir = os.path.join(os.getcwd(), "retornos")
	os.makedirs(base_dir, exist_ok=True)
	return base_dir


def _save_transcription_if_new(base_dir: str, text: str) -> Optional[str]:
	if not text:
		return None
	if _is_duplicate_transcription(base_dir, text):
		return None
	path = _next_transcription_path(base_dir)
	import json as _json
	with open(path, "w", encoding="utf-8") as tf:
		_tf_obj = {"transcricao": text}
		tf.write(_json.dumps(_tf_obj, ensure_ascii=False, indent=2))
	return path


@router.post("/", response_model=ExtractResponse)
async def extract_upload(file: UploadFile = File(...)):
	# Salvar temporariamente para processar
	if not file.filename:
		raise HTTPException(400, "Arquivo inválido")
	retornos = _ensure_returns_dir()
	# Persistir upload em ./retornos/uploads
	uploads = os.path.join(retornos, "uploads")
	os.makedirs(uploads, exist_ok=True)
	tmp_path = os.path.join(uploads, file.filename)
	with open(tmp_path, "wb") as f:
		shutil.copyfileobj(file.file, f)

	# Extrair texto conforme extensão
	lower = file.filename.lower()
	if lower.endswith(".pdf"):
		text = _read_pdf_text(tmp_path)
	elif lower.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")):
		text = _read_image_text(tmp_path)
	else:
		text = _read_text_file(tmp_path)

	info = extract_payment_info(text)
	# Salvar extracao json
	import json as _json
	extracao_path = _next_extraction_path(retornos)
	with open(extracao_path, "w", encoding="utf-8") as jf:
		jf.write(_json.dumps(info, ensure_ascii=False, indent=2))

	transc_path = _save_transcription_if_new(retornos, text)
	return ExtractResponse(**info, transcricao_path=transc_path, extracao_path=extracao_path)


class ByPathRequest(BaseModel):
	path: str


@router.post("/by-path", response_model=ExtractResponse)
async def extract_by_path(payload: ByPathRequest = Body(...)):
	# Resolve na pasta dados se necessário
	user_path = payload.path
	path = user_path
	if not os.path.exists(path):
		dados_dir = os.path.join(os.getcwd(), "dados")
		cand = os.path.join(dados_dir, user_path)
		if os.path.exists(cand):
			path = cand
		else:
			for fname in os.listdir(dados_dir):
				if fname.lower() == os.path.basename(user_path).lower():
					path = os.path.join(dados_dir, fname)
					break
	if not os.path.exists(path):
		raise HTTPException(404, "Arquivo não encontrado")

	lower = path.lower()
	if lower.endswith(".pdf"):
		text = _read_pdf_text(path)
	elif lower.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")):
		text = _read_image_text(path)
	else:
		text = _read_text_file(path)

	info = extract_payment_info(text)
	retornos = _ensure_returns_dir()
	import json as _json
	extracao_path = _next_extraction_path(retornos)
	with open(extracao_path, "w", encoding="utf-8") as jf:
		jf.write(_json.dumps(info, ensure_ascii=False, indent=2))
	transc_path = _save_transcription_if_new(retornos, text)
	return ExtractResponse(**info, transcricao_path=transc_path, extracao_path=extracao_path)


