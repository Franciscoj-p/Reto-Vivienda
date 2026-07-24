from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from app.api.schemas import LeadInput
from app.motor import procesar_lead

from app.api.routes_afiliados import router as router_afiliados

app = FastAPI(
    title="Motor de Perfilamiento - Asesor Digital de Vivienda",
    description="Recibe un lead en JSON y devuelve validación, score y proyectos recomendados.",
    version="1.0.0",
)

app.include_router(router_afiliados)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/perfilar")
def perfilar_lead(lead: LeadInput) -> dict[str, Any]:
    try:
        return procesar_lead(lead.model_dump(exclude_none=False))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
