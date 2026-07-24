"""
Único lugar donde se decide QUÉ implementación de cada repositorio se usa.

Nada más en el proyecto debe importar `AfiliadosCSVRepository` ni ninguna
otra clase de `app/repositories/*` directamente — todo pasa por las
funciones `get_*_repository()` de este archivo. Así, agregar una fuente de
datos nueva (ej. la bodega de datos real) es: escribir la clase adaptadora
en `app/repositories/`, y agregar una rama aquí.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import CONFIG
from app.repositories.afiliados_csv import AfiliadosCSVRepository
from app.repositories.proyectos_csv import ProyectosCSVRepository


@lru_cache
def get_afiliados_repository():
    fuente = CONFIG.get("DATA_SOURCE_AFILIADOS", "csv")

    if fuente == "csv":
        return AfiliadosCSVRepository()

    # Cuando exista la bodega de datos real:
    # if fuente == "bodega":
    #     return AfiliadosBodegaRepository()

    raise NotImplementedError(
        f"DATA_SOURCE_AFILIADOS='{fuente}' no tiene adaptador implementado."
    )


@lru_cache
def get_proyectos_repository():
    return ProyectosCSVRepository()