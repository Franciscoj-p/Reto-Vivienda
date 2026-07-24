"""
ETL offline — genera `data/perfiles_proyectos.csv` a partir de la base
cruda de compradores (`data/compradores_crudo.csv`).

Se ejecuta manualmente (o por un job programado), NUNCA durante una
petición en vivo de /perfilar (RNF-03, latencia). El API en producción solo
lee el CSV de salida, a través de `ProyectosCSVRepository`.

Uso:
    python -m app.etl.generar_perfiles
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict

from app.catalogo import CATALOGO_PROYECTOS
from app.config import CONFIG
from app.etl.limpieza import corregir_valor_vivienda, es_compra_vigente, normalizar_texto
from app.identificadores import slug_proyecto
from app.repositories.compradores_csv import CompradoresCSVRepository


def _municipio_por_proyecto() -> dict[str, str]:
    """Mapa proyecto (nombre crudo tal como viene en la base de compradores)
    -> municipio, usando el catálogo como fuente de verdad."""
    return {
        normalizar_texto(p["proyecto"]): normalizar_texto(p.get("municipio", ""))
        for p in CATALOGO_PROYECTOS
    }


def _grupo_geografico(municipio: str) -> str | None:
    if municipio in CONFIG["MUNICIPIOS_SUR"]:
        return "grupo_sur"
    if municipio in CONFIG["MUNICIPIOS_NORTE"]:
        return "grupo_norte"
    return None


def _distribucion_porcentual(filas: list[dict], campo: str) -> dict[str, float]:
    """% de filas por cada valor distinto de `campo`. Ignora vacíos (estrato
    y otros campos incompletos no suman 100%, tal como se documentó)."""
    valores = [normalizar_texto(f.get(campo)) for f in filas]
    valores = [v for v in valores if v]
    if not valores:
        return {}
    total = len(valores)
    conteo = Counter(valores)
    return {categoria: round(cantidad / total * 100, 1) for categoria, cantidad in conteo.items()}


def _moda(filas: list[dict], campo: str) -> str | None:
    valores = [normalizar_texto(f.get(campo)) for f in filas if f.get(campo)]
    if not valores:
        return None
    return Counter(valores).most_common(1)[0][0]


def _promedio_numerico(filas: list[dict], campo: str) -> float | None:
    valores = []
    for f in filas:
        try:
            valores.append(float(f.get(campo, "")))
        except (TypeError, ValueError):
            continue
    if not valores:
        return None
    return round(sum(valores) / len(valores), 1)


def _agregar_grupo(nombre_grupo: str, filas: list[dict]) -> dict:
    """Arma una fila del CSV de salida para un proyecto o para un grupo
    geográfico (sur/norte)."""
    fila_salida: dict = {
        "proyecto_id": nombre_grupo,
        "n_compradores": len(filas),
        "valor_promedio_vivienda": _promedio_numerico(filas, "_valor_vivienda_limpio"),
        "personas_a_cargo_promedio": _promedio_numerico(filas, "personas_a_cargo"),
        "entidad_financiera_predominante": _moda(filas, "entidad_financiera"),
    }

    # Cada dimensión configurada en CONFIG se expande a columnas
    # "<dimension>__<categoria>" = porcentaje. Agregar una dimensión nueva
    # es solo agregar el nombre del campo a CONFIG["DIMENSIONES_PERFIL_COMPRADORES"].
    for dimension in CONFIG["DIMENSIONES_PERFIL_COMPRADORES"]:
        for categoria, porcentaje in _distribucion_porcentual(filas, dimension).items():
            fila_salida[f"{dimension}__{categoria}"] = porcentaje

    return fila_salida


def generar_perfiles() -> list[dict]:
    repo_compradores = CompradoresCSVRepository()
    filas_crudas = repo_compradores.listar_compras()

    if CONFIG["ETL_EXCLUIR_DESISTIDOS"]:
        filas_crudas = [f for f in filas_crudas if es_compra_vigente(f)]

    for fila in filas_crudas:
        fila["_valor_vivienda_limpio"] = corregir_valor_vivienda(fila.get("valor_vivienda_crudo"))

    municipio_por_proyecto = _municipio_por_proyecto()

    filas_por_proyecto: dict[str, list[dict]] = defaultdict(list)
    filas_por_grupo: dict[str, list[dict]] = defaultdict(list)

    for fila in filas_crudas:
        nombre_proyecto = normalizar_texto(fila.get("proyecto"))
        if not nombre_proyecto:
            continue

        proyecto_id = slug_proyecto(nombre_proyecto)
        filas_por_proyecto[proyecto_id].append(fila)

        municipio = municipio_por_proyecto.get(nombre_proyecto, "")
        grupo = _grupo_geografico(municipio)
        if grupo:
            filas_por_grupo[grupo].append(fila)

    resultado = [
        _agregar_grupo(proyecto_id, filas) for proyecto_id, filas in filas_por_proyecto.items()
    ]
    resultado += [
        _agregar_grupo(nombre_grupo, filas) for nombre_grupo, filas in filas_por_grupo.items()
    ]
    return resultado


def escribir_csv(filas: list[dict], ruta_salida: str | None = None) -> str:
    ruta_salida = ruta_salida or CONFIG["RUTA_CSV_PROYECTOS_PERFIL"]

    columnas: list[str] = []
    for fila in filas:
        for columna in fila:
            if columna not in columnas:
                columnas.append(columna)

    with open(ruta_salida, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        for fila in filas:
            escritor.writerow(fila)

    return ruta_salida


if __name__ == "__main__":
    filas_generadas = generar_perfiles()
    ruta = escribir_csv(filas_generadas)
    print(f"Perfiles generados: {len(filas_generadas)} filas -> {ruta}")