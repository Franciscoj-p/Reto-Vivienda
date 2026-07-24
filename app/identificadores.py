from __future__ import annotations

import re
import unicodedata


def slug_proyecto(nombre_proyecto: str) -> str:
    """Convierte el nombre de un proyecto en un id estable y reproducible.

    Usado tanto por el ETL (para nombrar las filas de `perfiles_proyectos.csv`)
    como por quien consulte `ProyectosRepository.obtener_perfil_compradores`
    a partir de un nombre de catálogo — así ambos lados generan el mismo id
    sin necesidad de mantenerlo sincronizado a mano.

    "Ciudadela Maiporé" -> "ciudadela_maipore"
    """
    texto = unicodedata.normalize("NFKD", nombre_proyecto or "")
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.strip().lower()
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")