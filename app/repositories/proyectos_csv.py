from __future__ import annotations

import csv
from pathlib import Path

from app.catalogo import CATALOGO_PROYECTOS
from app.config import CONFIG


class ProyectosCSVRepository:
    """Simula el repositorio de proyectos leyendo CSV.

    `listar_proyectos` reutiliza el catálogo ya existente (precio, tipo,
    municipio). `obtener_perfil_compradores` lee un CSV nuevo con la
    distribución porcentual de compradores históricos por proyecto —
    incluye las filas agrupadas "municipios sur" / "municipios norte".
    """

    def __init__(self, ruta_perfiles: str | None = None):
        self._ruta_perfiles = Path(ruta_perfiles or CONFIG["RUTA_CSV_PROYECTOS_PERFIL"])
        self._perfiles: dict[str, dict] | None = None

    def listar_proyectos(self) -> list[dict]:
        return CATALOGO_PROYECTOS

    def obtener_perfil_compradores(self, proyecto_id: str) -> dict | None:
        return self._cargar_perfiles().get(proyecto_id)

    # -- internos ---------------------------------------------------------

    def _cargar_perfiles(self) -> dict[str, dict]:
        if self._perfiles is not None:
            return self._perfiles

        perfiles: dict[str, dict] = {}
        if self._ruta_perfiles.exists():
            with self._ruta_perfiles.open(newline="", encoding="utf-8") as archivo:
                for fila in csv.DictReader(archivo):
                    clave = (fila.get("proyecto_id") or "").strip()
                    if clave:
                        perfiles[clave] = fila

        self._perfiles = perfiles
        return perfiles