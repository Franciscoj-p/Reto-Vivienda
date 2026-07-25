from __future__ import annotations

import unicodedata

from app.catalogo import CATALOGO_PROYECTOS
from app.config import CONFIG


# ======================================================================
# Helpers de conversión — puros, sin acceso a `lead`
# ======================================================================

def _valor_a_smmlv(valor: float) -> float:
    return valor / CONFIG["SMMLV_2026"]


def _ingresos_a_smmlv(ingresos: float) -> float:
    return _valor_a_smmlv(ingresos)


def _zona_normalizada(zona: str | None) -> str:
    """minúsculas + sin tildes. BUG encontrado y corregido en esta sesión:
    antes solo hacía `.lower()`, así que "Bogotá" (con tilde) nunca
    coincidía contra "bogota" en `MUNICIPIOS_PRINCIPALES` ni en
    `ZONAS_COBERTURA_SUBSIDIO` — el tope VIS y el subsidio general salían
    mal justo para la ciudad más grande del catálogo."""
    texto = (zona or "").strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def _zona_coincide(zona: str | None, lista: list[str]) -> bool:
    """True si `zona` contiene (o es contenida por) alguno de los valores de `lista`."""
    zona_norm = _zona_normalizada(zona)
    if not zona_norm:
        return False
    return any(candidato in zona_norm for candidato in lista)


def _es_municipio_principal(zona: str | None) -> bool:
    return _zona_coincide(zona, CONFIG["MUNICIPIOS_PRINCIPALES"])


def _zona_tiene_cobertura_subsidio(zona: str | None) -> bool:
    """El subsidio de Colsubsidio solo aplica en Bogotá y Cundinamarca.

    Si el lead no informó zona, no se bloquea aquí (se asume cobertura y se
    valida más adelante con el asesor); ajustar este comportamiento en
    CONFIG["ZONAS_COBERTURA_SUBSIDIO"] o cambiando el default de esta función.
    """
    zona_norm = _zona_normalizada(zona)
    if not zona_norm:
        return True
    return _zona_coincide(zona, CONFIG["ZONAS_COBERTURA_SUBSIDIO"])


# ======================================================================
# Helpers de acceso a estructura anidada del lead (Fase 4: `finanzas`,
# `condiciones_especiales`). El lead llega como dict (model_dump() del
# LeadInput de Pydantic), así que los sub-objetos ya vienen como dicts.
# ======================================================================

def _finanzas(lead: dict) -> dict:
    return lead.get("finanzas") or {}


def _cesantias(lead: dict) -> float:
    return _finanzas(lead).get("cesantias", 0) or 0


def _ahorros(lead: dict) -> float:
    return _finanzas(lead).get("ahorros", 0) or 0


# ======================================================================
# Reglas duras de rechazo — cada una es una función independiente que
# devuelve un mensaje (str) si el lead NO cumple, o None si sí cumple.
# Agregar una regla nueva = agregar una función aquí + una línea en
# `_REGLAS_RECHAZO`.
# ======================================================================

def _regla_propietario_vivienda(lead: dict) -> str | None:
    if lead.get("propietario_vivienda", False):
        return "El postulante o su hogar ya son propietarios de vivienda"
    return None


def _regla_antiguedad_afiliacion(lead: dict) -> str | None:
    if not lead.get("afiliado", False):
        return None

    tipo_cotizante = (lead.get("tipo_cotizante") or "").strip().lower()
    minimo = CONFIG["ANTIGUEDAD_MINIMA_MESES_POR_TIPO"].get(
        tipo_cotizante, CONFIG["ANTIGUEDAD_MINIMA_MESES_DEFAULT"]
    )
    antiguedad = lead.get("antiguedad_meses") or 0
    if antiguedad < minimo:
        return (
            f"Antigüedad de afiliación insuficiente "
            f"({antiguedad} meses, mínimo {minimo})"
        )
    return None


def _regla_beneficiario_subsidio_previo(lead: dict) -> str | None:
    """Si algún miembro del hogar ya recibió subsidio de vivienda antes,
    no puede volver a acceder, EXCEPTO si el subsidio previo fue de
    arrendamiento (RN nueva)."""
    recibio_subsidio_previo = lead.get("subsidio_previo", False)
    fue_arrendamiento = lead.get("subsidio_previo_fue_arrendamiento", False)
    if recibio_subsidio_previo and not fue_arrendamiento:
        return (
            "El hogar ya fue beneficiario de un subsidio de vivienda "
            "anteriormente (no aplica excepción de arrendamiento)"
        )
    return None


def _regla_ingresos_insuficientes(lead: dict) -> str | None:
    ingresos = lead.get("ingresos_mensuales", 0)
    cuota_maxima = round(ingresos * CONFIG["LIMITE_CUOTA_INGRESO"])
    if cuota_maxima <= 0:
        return "Ingresos insuficientes para calcular cuota de crédito"
    return None


# Orden de evaluación. Para agregar una regla nueva: escribir la función
# arriba y añadirla a esta lista.
_REGLAS_RECHAZO = [
    _regla_propietario_vivienda,
    _regla_antiguedad_afiliacion,
    _regla_beneficiario_subsidio_previo,
    _regla_ingresos_insuficientes,
]


def _evaluar_reglas_rechazo(lead: dict) -> list[str]:
    motivos = []
    for regla in _REGLAS_RECHAZO:
        motivo = regla(lead)
        if motivo:
            motivos.append(motivo)
    return motivos


# ======================================================================
# Subsidio de vivienda (monto) — condiciones de aplicación + cálculo
# ======================================================================

def _calcular_subsidio_por_ingresos(ingresos_en_smmlv: float) -> int:
    piso_smmlv = 0
    for rango in CONFIG["MATRIZ_SUBSIDIOS"]:
        if piso_smmlv <= ingresos_en_smmlv < rango["max_smmlv"]:
            return rango["subsidio_smmlv"] * CONFIG["SMMLV_2026"]
        piso_smmlv = rango["max_smmlv"]
    return 0


def _tope_smmlv_por_tipo_proyecto(tipo_proyecto: str | None, zona: str | None) -> float | None:
    """Tope de valor (en SMMLV) aplicable según el tipo de proyecto.

    - "VIS": 150 SMMLV en municipio principal, 135 en el resto.
    - "VIP": 90 SMMLV fijo. Antes estaba definido en config pero nunca
      conectado aquí — la función comparaba siempre contra el tope VIS
      sin importar el tipo real del proyecto (pendiente #10 de plan.md,
      ahora resuelto).
    - Cualquier otro valor (ej. "NO VIS", mercado libre): sin tope, esas
      viviendas no están sujetas a la Ley de Vivienda VIS/VIP.
    - Si no se informa `tipo_proyecto`, se asume "VIS" por compatibilidad
      con el uso histórico de esta función (validación general del lead,
      que no está atada a un proyecto concreto del catálogo).
    """
    tipo_norm = (tipo_proyecto or "VIS").strip().upper()
    if tipo_norm == "VIP":
        return CONFIG["VIP_TOPE_SMMLV"]
    if tipo_norm == "VIS":
        return (
            CONFIG["VIS_TOPE_SMMLV_PRINCIPAL"]
            if _es_municipio_principal(zona)
            else CONFIG["VIS_TOPE_SMMLV_OTROS"]
        )
    return None


def _valor_vivienda_dentro_de_tope(
    valor_vivienda: float | None,
    zona: str | None,
    tipo_proyecto: str | None = "VIS",
) -> bool:
    """El subsidio/tope solo aplica a vivienda VIS (hasta 135/150 SMMLV
    según municipio) o VIP (hasta 90 SMMLV). Si no se conoce el valor
    deseado, o el tipo de proyecto no tiene tope aplicable (ej. "NO VIS"),
    no se bloquea por este criterio.

    `tipo_proyecto` es opcional, por defecto "VIS": la validación general
    de elegibilidad del lead (sección 3.2 del plan, sobre
    `valor_vivienda_deseada` declarado por el usuario) no está atada a un
    proyecto específico del catálogo. El matching por proyecto
    (scoring.py `match_proyectos`) sí pasa el `tipo_proyecto` real de cada
    tipología candidata.
    """
    if valor_vivienda is None:
        return True
    tope_smmlv = _tope_smmlv_por_tipo_proyecto(tipo_proyecto, zona)
    if tope_smmlv is None:
        return True
    valor_en_smmlv = _valor_a_smmlv(valor_vivienda)
    return valor_en_smmlv <= tope_smmlv


def _evaluar_aplicacion_subsidio(lead: dict, ingresos_en_smmlv: float, motivos_rechazo: list[str]) -> dict:
    """Devuelve el detalle de elegibilidad al subsidio y su monto.

    Reúne TODAS las condiciones que hacen que el subsidio sea 0, para que
    sea auditable (RNF-02 Explicabilidad / No caja negra).
    """
    zona = lead.get("zona_preferida")
    valor_vivienda = lead.get("valor_vivienda_deseada")

    condiciones = {
        "dentro_de_tope_ingresos": ingresos_en_smmlv <= CONFIG["TOPE_INGRESOS_SMMLV"],
        "sin_rechazo_por_reglas_duras": len(motivos_rechazo) == 0,
        "zona_con_cobertura_subsidio": _zona_tiene_cobertura_subsidio(zona),
        "vivienda_dentro_de_tope_vis_vip": _valor_vivienda_dentro_de_tope(valor_vivienda, zona),
    }
    aplica_subsidio = all(condiciones.values())
    subsidio_estimado = (
        _calcular_subsidio_por_ingresos(ingresos_en_smmlv) if aplica_subsidio else 0
    )

    return {
        "aplica_subsidio": aplica_subsidio,
        "subsidio_estimado": subsidio_estimado,
        "condiciones_subsidio": condiciones,
    }


def _evaluar_subsidio_concurrente_mi_casa_ya(ingresos_en_smmlv: float) -> dict:
    """Informativo: si el hogar gana menos de 2 SMMLV, puede sumar subsidio
    adicional del gobierno (Mi Casa Ya) al de la caja."""
    disponible = ingresos_en_smmlv < CONFIG["MI_CASA_YA_TOPE_INGRESOS_SMMLV"]
    monto_adicional = (
        CONFIG["MI_CASA_YA_SUBSIDIO_ADICIONAL_SMMLV"] * CONFIG["SMMLV_2026"]
        if disponible
        else 0
    )
    return {"disponible": disponible, "monto_adicional_estimado": monto_adicional}


def _evaluar_subsidio_arrendamiento(cierre_viable: bool) -> dict:
    """Ruta alterna sugerida cuando el lead no logra el cierre financiero
    hoy: subsidio de arrendamiento mientras ahorra."""
    monto_mensual = round(
        CONFIG["SUBSIDIO_ARRENDAMIENTO_SMMLV_MENSUAL"] * CONFIG["SMMLV_2026"]
    )
    meses = CONFIG["SUBSIDIO_ARRENDAMIENTO_MESES"]
    return {
        "sugerido": not cierre_viable,
        "monto_mensual_estimado": monto_mensual,
        "meses": meses,
        "monto_total_estimado": monto_mensual * meses,
    }


# ======================================================================
# Segmentación de Caja (Básico / Medio / Alto / Joven)
# ======================================================================

def _calcular_segmentacion_caja(lead: dict, ingresos_en_smmlv: float) -> str:
    edad = lead.get("edad")
    personas_a_cargo = lead.get("personas_a_cargo") or 0
    sin_personas_a_cargo = personas_a_cargo <= 0

    es_joven = (
        edad is not None
        and edad < CONFIG["SEGMENTACION_CAJA_JOVEN_EDAD_MAX"]
        and sin_personas_a_cargo
    )
    if es_joven:
        return "Joven"

    if ingresos_en_smmlv <= CONFIG["SEGMENTACION_CAJA_BASICO_MAX_SMMLV"]:
        return "Basico"
    if ingresos_en_smmlv <= CONFIG["SEGMENTACION_CAJA_MEDIO_MAX_SMMLV"]:
        return "Medio"
    return "Alto"


# ======================================================================
# Cierre financiero general (informativo, no bloquea `puede_comprar`)
# ------------------------------------------------------------------
# Este es el cierre financiero "de referencia" (contra el precio promedio
# del portafolio VIS), usado en `financial_score.cierre_financiero` de la
# respuesta general. El cierre financiero POR PROYECTO/tipología candidata
# vive en scoring.py `match_proyectos` (plan.md §5.4) y es independiente
# de este.
# ======================================================================

def _precio_referencia_vis() -> int:
    """Precio de referencia = promedio de la tipología más barata de cada
    proyecto VIS del catálogo (aproximación razonable de "entrada" al
    portafolio VIS). Si no hay proyectos VIS con tipologías, es 0."""
    precios_minimos = []
    for proyecto in CATALOGO_PROYECTOS:
        if (proyecto.get("tipo_proyecto") or "").strip().upper() != "VIS":
            continue
        precios = [t["precio"] for t in proyecto.get("tipologias", []) if "precio" in t]
        if precios:
            precios_minimos.append(min(precios))
    return round(sum(precios_minimos) / len(precios_minimos)) if precios_minimos else 0


def _calcular_cierre_financiero(lead: dict, subsidio_estimado: int) -> dict:
    precio_referencia = _precio_referencia_vis()
    cuota_inicial_requerida = round(
        precio_referencia * CONFIG["PORCENTAJE_CUOTA_INICIAL_REQUERIDO"]
    )
    ahorro_disponible = _cesantias(lead) + _ahorros(lead) + subsidio_estimado
    cierre_viable = ahorro_disponible >= cuota_inicial_requerida

    return {
        "precio_referencia_vivienda": precio_referencia,
        "cuota_inicial_requerida": cuota_inicial_requerida,
        "ahorro_disponible": ahorro_disponible,
        "cierre_viable": cierre_viable,
    }


# ======================================================================
# Orquestador del módulo
# ======================================================================

def validar_reglas(lead: dict) -> dict:
    """Aplica las reglas duras de negocio/ley de vivienda sobre un lead."""
    ingresos = lead.get("ingresos_mensuales", 0)
    ingresos_en_smmlv = _ingresos_a_smmlv(ingresos)

    motivos_rechazo = _evaluar_reglas_rechazo(lead)

    subsidio = _evaluar_aplicacion_subsidio(lead, ingresos_en_smmlv, motivos_rechazo)

    descalifica_subsidio_por_techo_ingresos = (
        ingresos_en_smmlv > CONFIG["TOPE_INGRESOS_SMMLV"]
    )

    cuota_maxima_mensual = round(ingresos * CONFIG["LIMITE_CUOTA_INGRESO"])

    cierre_financiero = _calcular_cierre_financiero(lead, subsidio["subsidio_estimado"])

    subsidio_concurrente = _evaluar_subsidio_concurrente_mi_casa_ya(ingresos_en_smmlv)
    subsidio_arrendamiento = _evaluar_subsidio_arrendamiento(cierre_financiero["cierre_viable"])

    segmentacion_caja = _calcular_segmentacion_caja(lead, ingresos_en_smmlv)

    return {
        "puede_comprar": len(motivos_rechazo) == 0,
        "motivos_rechazo": motivos_rechazo,
        "ingresos_en_smmlv": round(ingresos_en_smmlv, 2),
        "aplica_subsidio": subsidio["aplica_subsidio"],
        "subsidio_estimado": subsidio["subsidio_estimado"],
        "condiciones_subsidio": subsidio["condiciones_subsidio"],
        "descalifica_subsidio_por_techo_ingresos": descalifica_subsidio_por_techo_ingresos,
        "cuota_maxima_mensual": cuota_maxima_mensual,
        "cierre_financiero": cierre_financiero,
        "subsidio_concurrente_mi_casa_ya": subsidio_concurrente,
        "subsidio_arrendamiento_sugerido": subsidio_arrendamiento,
        "segmentacion_caja": segmentacion_caja,
    }