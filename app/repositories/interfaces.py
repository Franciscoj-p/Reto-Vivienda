from __future__ import annotations

from typing import Protocol


class AfiliadosRepository(Protocol):
    """Contrato para consultar si un usuario está afiliado a Colsubsidio.

    La implementación de hoy lee un CSV (simulación). La implementación real
    consultará la bodega de datos empresarial. Nada fuera de este módulo
    debe saber cuál de las dos está detrás.
    """

    def obtener_afiliado(self, id_usuario: str) -> dict | None:
        """Devuelve los datos del afiliado si `id_usuario` existe, o None si
        la persona no está afiliada."""
        ...


class ProyectosRepository(Protocol):
    """Contrato para consultar el catálogo de proyectos y su perfil
    histórico de compradores (porcentajes, no promedios)."""

    def listar_proyectos(self) -> list[dict]:
        """Catálogo de proyectos: nombre, municipio, tipo, precio, etc."""
        ...

    def obtener_perfil_compradores(self, proyecto_id: str) -> dict | None:
        """Distribución porcentual de compradores históricos de un proyecto
        puntual, o de su agrupación (municipios sur / municipios norte)."""
        ...


class CompradoresRepository(Protocol):
    """Contrato para la base cruda de compradores (~4.142 filas).

    Uso exclusivo del ETL offline (Fase 2) — ningún módulo de la ruta de
    /perfilar debe llamar a esto en tiempo real (RNF-03, latencia)."""

    def listar_compras(self) -> list[dict]:
        ...