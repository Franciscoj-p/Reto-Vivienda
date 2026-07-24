from __future__ import annotations

from app.config import CONFIG


def corregir_valor_vivienda(valor_crudo: str | None) -> float | None:
    """Corrige el bug de formato conocido: el valor de vivienda viene con
    ceros sobrantes (ej. el crudo representa "523.620" y el valor real es
    ~$523.000.000).

    AJUSTAR AQUÍ cuando se confirme el formato exacto del CSV real: hoy se
    asume que el número crudo, sin separadores, dividido entre
    CONFIG["FACTOR_CORRECCION_VALOR_VIVIENDA"], da el valor en pesos
    correcto multiplicado por 1.000.000 (millones). Si el formato real es
    distinto, este es el único lugar que hay que tocar.
    """
    if not valor_crudo:
        return None

    texto = str(valor_crudo).strip().replace(".", "").replace(",", "").replace("$", "")
    if not texto.isdigit():
        return None

    numero = int(texto)
    factor = CONFIG["FACTOR_CORRECCION_VALOR_VIVIENDA"]
    valor_en_millones = numero / factor
    return round(valor_en_millones * 1_000_000)


def es_compra_vigente(fila: dict) -> bool:
    """True si la compra sigue vigente o terminó bien (sin desistimiento)."""
    fecha_desistimiento = (fila.get("fecha_desistimiento") or "").strip()
    return fecha_desistimiento == ""


def normalizar_texto(valor: str | None) -> str:
    return (valor or "").strip().lower()