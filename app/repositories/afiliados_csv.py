from __future__ import annotations

import csv
from pathlib import Path

from app.config import BASE_DIR, CONFIG


class AfiliadosCSVRepository:
    """Simula la bodega de datos de afiliados leyendo un CSV.

    Las columnas del CSV representan los nombres que tendría la bodega de
    datos real (ej. `AFIL_ANTIGUEDAD_MESES` en vez de `antiguedad_meses`).
    El mapeo columna-real -> campo-interno vive en
    CONFIG["MAPEO_COLUMNAS_AFILIADOS"], así que:

    - Si cambian los nombres de columna en el CSV de prueba: se edita el
      mapeo en config.py, no este archivo.
    - Cuando exista la bodega real: se escribe una clase nueva (ej.
      `AfiliadosBodegaRepository`) que ejecute SQL en vez de leer CSV, pero
      reutiliza el mismo diccionario de mapeo y expone el mismo método
      `obtener_afiliado`. `reglas.py`/`scoring.py`/`motor.py` no cambian.
    """

    def __init__(self, ruta_csv: str | None = None, mapeo_columnas: dict | None = None):
        # BUGFIX: antes `Path(ruta_csv or CONFIG[...])` quedaba relativo al
        # directorio de trabajo del proceso (cwd). Si el servidor arrancaba
        # desde otro directorio, el archivo "no existía" en silencio y
        # `obtener_afiliado` siempre devolvía None. Ahora se resuelve
        # siempre contra la raíz del proyecto (BASE_DIR).
        self._ruta_csv = Path(ruta_csv) if ruta_csv else BASE_DIR / CONFIG["RUTA_CSV_AFILIADOS"]
        self._mapeo = mapeo_columnas or CONFIG["MAPEO_COLUMNAS_AFILIADOS"]
        self._indice: dict[str, dict] | None = None

    def obtener_afiliado(self, id_usuario: str) -> dict | None:
        return self._cargar().get(str(id_usuario))

    # -- internos ---------------------------------------------------------

    def _cargar(self) -> dict[str, dict]:
        if self._indice is not None:
            return self._indice

        indice: dict[str, dict] = {}
        if self._ruta_csv.exists():
            with self._ruta_csv.open(newline="", encoding="utf-8") as archivo:
                for fila in csv.DictReader(archivo):
                    fila_mapeada = self._mapear_fila(fila)
                    id_usuario = fila_mapeada.get("id_usuario")
                    if id_usuario:
                        indice[str(id_usuario)] = fila_mapeada

        self._indice = indice
        return indice

    def _mapear_fila(self, fila: dict) -> dict:
        resultado = {}
        for columna_fuente, campo_interno in self._mapeo.items():
            if columna_fuente in fila:
                resultado[campo_interno] = self._convertir(campo_interno, fila[columna_fuente])
        return resultado

    @staticmethod
    def _convertir(campo_interno: str, valor: str | None):
        valor = (valor or "").strip()
        if not valor:
            return None
        if campo_interno == "afiliado":
            return valor.lower() in ("1", "true", "si", "sí", "x")
        if campo_interno in ("antiguedad_meses", "personas_a_cargo"):
            try:
                return int(valor)
            except ValueError:
                return None
        return valor