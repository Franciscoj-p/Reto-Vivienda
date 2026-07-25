from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import CONFIG

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _resolver_municipio(ubicacion: str) -> str | None:
    """`ubicacion` del proyecto -> municipio real (plan.md §5.2).

    Algunas ubicaciones son desarrollos, no municipios (ej. "Ciudadela
    Maiporé" -> Soacha). Si la ubicación no está en el mapeo configurado,
    devuelve None y se deja constancia para que el resto del motor no
    asuma un municipio incorrecto.
    """
    return CONFIG["UBICACION_A_MUNICIPIO"].get((ubicacion or "").strip().lower())


def cargar_catalogo_proyectos() -> list[dict[str, Any]]:
    """Carga el catálogo desde data/proyectos.json.

    Cada proyecto conserva su estructura original (`tipologias`,
    `buyerPersona`, `tipo_proyecto`, `ubicacion`) y se le agrega el campo
    derivado `municipio` (usado por reglas.py/scoring.py para topes
    VIS/VIP y cobertura de subsidio, que comparan contra municipio, no
    contra ubicación comercial).

    Excluye del catálogo los proyectos configurados en
    `PROYECTOS_EXCLUIDOS_MATCHING` (muestra histórica muy chica, o filas
    agregadas como "Total" — decisiones #16/#17 de plan.md).
    """
    ruta_json = DATA_DIR / "proyectos.json"
    if not ruta_json.exists():
        # Fallback opcional a la ruta configurable en config.py.
        ruta_json = Path(CONFIG["RUTA_JSON_PROYECTOS"])
        if not ruta_json.is_absolute():
            ruta_json = Path(__file__).resolve().parent.parent / ruta_json
    if not ruta_json.exists():
        return []

    with ruta_json.open("r", encoding="utf-8") as archivo:
        proyectos_crudos = json.load(archivo)

    excluidos = {n.lower() for n in CONFIG["PROYECTOS_EXCLUIDOS_MATCHING"]}

    proyectos: list[dict[str, Any]] = []
    for proyecto in proyectos_crudos:
        nombre = (proyecto.get("nombre") or "").strip()
        if nombre.lower() in excluidos:
            continue

        proyecto = dict(proyecto)  # copia defensiva, no mutar el JSON original
        proyecto["municipio"] = _resolver_municipio(proyecto.get("ubicacion"))
        proyecto.setdefault("tipologias", [])
        proyecto.setdefault("buyerPersona", {})
        proyectos.append(proyecto)

    return proyectos


CATALOGO_PROYECTOS = cargar_catalogo_proyectos()