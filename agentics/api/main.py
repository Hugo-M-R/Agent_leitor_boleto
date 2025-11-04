"""Aplicação FastAPI que expõe endpoints de extração de boletos.

Rotas:
- GET /health: checagem simples de saúde
- POST /extract: upload de arquivo e extração
- POST /extract/by-path: extração por caminho local
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import extract


def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI com CORS e rotas."""
	app = FastAPI(title="Agente Leitor de Boleto", version="0.1.0")
	# CORS para permitir acesso do frontend
	app.add_middleware(
		CORSMiddleware,
		allow_origins=["*"],
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)
	app.include_router(extract.router, prefix="/extract", tags=["extract"])

	@app.get("/health")
    def health() -> dict:
        """Endpoint de verificação de saúde da API."""
		return {"status": "ok"}
	return app


app = create_app()


