from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.api.schemas import LeadInput
from app.motor import procesar_lead
from app.api.routes_afiliados import router as router_afiliados

INDEX_HTML_PATH = Path(__file__).resolve().parent.parent.parent / "index.html"

app = FastAPI(
    title="Motor de Perfilamiento - Asesor Digital de Vivienda",
    description="Recibe un lead en JSON y devuelve validación, score y proyectos recomendados.",
    version="1.0.0",
)

app.include_router(router_afiliados)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    if INDEX_HTML_PATH.exists():
        return FileResponse(INDEX_HTML_PATH)
    raise HTTPException(status_code=404, detail="index.html no encontrado")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/perfilar")
def perfilar_lead(lead: LeadInput) -> dict[str, Any]:
    try:
        return procesar_lead(lead.model_dump(exclude_none=False))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
