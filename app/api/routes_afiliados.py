from __future__ import annotations

from fastapi import APIRouter

from app.dependencies import get_afiliados_repository

router = APIRouter()


@router.get("/afiliados/{id_usuario}")
def consultar_afiliado(id_usuario: str) -> dict:
    """RF-03/RF-04: el front consulta esto ANTES de armar la conversación,
    para saber si la persona es afiliada y con qué datos ya cuenta la caja.

    Siempre responde 200 — "no afiliado" es una respuesta de negocio válida,
    no un error.
    """
    repositorio = get_afiliados_repository()
    datos = repositorio.obtener_afiliado(id_usuario)

    if datos is None:
        return {"afiliado": False, "datos": None}

    return {"afiliado": True, "datos": datos}