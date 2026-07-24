from __future__ import annotations

import csv
from pathlib import Path

from app.config import CONFIG


class CompradoresCSVRepository:
    """Lee la base cruda de compradores (~4.142 filas).

    Uso exclusivo del ETL offline (`app/etl/generar_perfiles.py`). Ningún
    módulo del camino de /perfilar debe importar esto — por eso vive
    separado de `afiliados_csv.py` y `proyectos_csv.py`, que sí se usan en
    vivo.
    """

    def __init__(self, ruta_csv: str | None = None):
        self._ruta_csv = Path(ruta_csv or CONFIG["RUTA_CSV_COMPRADORES_CRUDO"])

    def listar_compras(self) -> list[dict]:
        if not self._ruta_csv.exists():
            return []
        with self._ruta_csv.open(newline="", encoding="utf-8") as archivo:
            return list(csv.DictReader(archivo))