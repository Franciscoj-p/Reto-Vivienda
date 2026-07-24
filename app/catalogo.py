from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def cargar_catalogo_proyectos() -> list[dict[str, Any]]:
    """Carga el catálogo desde data/proyectos.csv."""
    ruta_csv = DATA_DIR / "proyectos.csv"
    if not ruta_csv.exists():
        return []

    with ruta_csv.open("r", encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        proyectos: list[dict[str, Any]] = []
        for fila in lector:
            fila["precio"] = int(fila.get("precio", 0))
            fila["ingreso_promedio_comprador"] = int(
                fila.get("ingreso_promedio_comprador", 0)
            )
            fila["edad_promedio_comprador"] = int(
                fila.get("edad_promedio_comprador", 0)
            )
            proyectos.append(fila)
    return proyectos


CATALOGO_PROYECTOS = cargar_catalogo_proyectos()
