from fastapi import FastAPI
from .routers import extract


def create_app() -> FastAPI:
	app = FastAPI(title="Agente Leitor de Boleto", version="0.1.0")
	app.include_router(extract.router, prefix="/extract", tags=["extract"])
	return app


app = create_app()


