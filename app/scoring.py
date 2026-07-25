from __future__ import annotations

import re
import unicodedata

from app.catalogo import CATALOGO_PROYECTOS
from app.config import CONFIG
from app.reglas import _valor_vivienda_dentro_de_tope


# ======================================================================
# Helpers de acceso a estructura anidada del lead
# ======================================================================

def _finanzas(lead: dict) -> dict:
    return lead.get("finanzas") or {}


def _condiciones_especiales(lead: dict) -> dict:
    return lead.get("condiciones_especiales") or {}


# ======================================================================
# Helpers de texto/número para comparar el lead contra los buckets de
# `buyerPersona` (plan.md §5.3). Genéricos y reutilizables entre
# dimensiones — si negocio cambia la redacción de un bucket en
# proyectos.json, no hay que tocar código, solo estas expresiones.
# ======================================================================

def _normalizar_texto(texto: str) -> str:
    """minúsculas + sin tildes, para comparar 'Básico' == 'basico'."""
    texto = (texto or "").strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


_PATRON_ENTRE = re.compile(r"entre\s+(\d+(?:\.\d+)?)\s+y\s+(\d+(?:\.\d+)?)")
_PATRON_A = re.compile(r"(\d+(?:\.\d+)?)\s+a\s+(\d+(?:\.\d+)?)")
_PATRON_HASTA = re.compile(r"hasta\s+(\d+(?:\.\d+)?)")
_PATRON_MAS_DE = re.compile(r"mas\s+de\s+(\d+(?:\.\d+)?)")


def _parsear_rango_numerico(texto_bucket: str) -> tuple[float, float] | None:
    """Convierte el texto de un bucket a un rango numérico [min, max].

    Soporta los formatos vistos en `proyectos.json` (varían por proyecto,
    no es un catálogo cerrado — plan.md §5.3):
    "Entre 4 y 6 smlv", "20 a 35 años", "Hasta 2 smlv", "Mas de 2 smlv".
    Si el texto no matchea ningún formato conocido, devuelve None (esa
    dimensión no se puede evaluar para ese bucket puntual).
    """
    texto = _normalizar_texto(texto_bucket)
    m = _PATRON_ENTRE.search(texto)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = _PATRON_A.search(texto)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = _PATRON_HASTA.search(texto)
    if m:
        return 0.0, float(m.group(1))
    m = _PATRON_MAS_DE.search(texto)
    if m:
        return float(m.group(1)), float("inf")
    return None


def _afinidad_por_rango(buckets: list[dict], valor_lead: float | None) -> float | None:
    """Ubica `valor_lead` en el bucket cuyo texto describe un rango
    numérico y devuelve su porcentaje histórico (0-1). None si no hay
    dato del lead o no cae en ningún bucket de este proyecto puntual
    (no es un error — señal de baja afinidad real, plan.md §5.3)."""
    if valor_lead is None:
        return None
    for bucket in buckets or []:
        rango = _parsear_rango_numerico(bucket.get("valor", ""))
        if rango is None:
            continue
        piso, techo = rango
        if piso <= valor_lead <= techo:
            return (bucket.get("porcentaje", 0) or 0) / 100
    return None


def _afinidad_por_valor_exacto(buckets: list[dict], valor_lead: str | None) -> float | None:
    """Compara texto normalizado (sin tildes/mayúsculas) contra `bucket.valor`."""
    if not valor_lead:
        return None
    valor_norm = _normalizar_texto(valor_lead)
    for bucket in buckets or []:
        if _normalizar_texto(bucket.get("valor", "")) == valor_norm:
            return (bucket.get("porcentaje", 0) or 0) / 100
    return None


# ======================================================================
# Dimensiones de afinidad histórica (matching_historico) — plan.md §5.3.
# Cada función recibe (lead, validacion, buyer_persona) y devuelve un
# float 0-1, o None si esa dimensión no se puede calcular (dato faltante
# en el lead, o el valor del lead no cae en ningún bucket de ESTE
# proyecto). Los pesos viven en CONFIG["BUYER_PERSONA_WEIGHTS"] — agregar
# una dimensión nueva = escribir la función aquí + agregarla a
# `_DIMENSIONES_MATCHING_HISTORICO` + su peso en config.py.
# ======================================================================

def _dimension_salario(lead: dict, validacion: dict, buyer_persona: dict) -> float | None:
    ingresos = lead.get("ingresos_mensuales")
    if not ingresos:
        return None
    ingresos_smmlv = ingresos / CONFIG["SMMLV_2026"]
    return _afinidad_por_rango(buyer_persona.get("salario", []), ingresos_smmlv)


def _dimension_edad(lead: dict, validacion: dict, buyer_persona: dict) -> float | None:
    return _afinidad_por_rango(buyer_persona.get("edad", []), lead.get("edad"))


def _dimension_afiliacion(lead: dict, validacion: dict, buyer_persona: dict) -> float | None:
    valor = "Afiliado" if lead.get("afiliado") else "No afiliado"
    return _afinidad_por_valor_exacto(buyer_persona.get("afiliacion", []), valor)


def _dimension_seg_empresa(lead: dict, validacion: dict, buyer_persona: dict) -> float | None:
    """Heurístico: `tipo_empresa` del lead (Micro/Medianas/Top) se mapea a
    la taxonomía real de `seg_empresas` vía CONFIG — AJUSTAR cuando
    negocio confirme la equivalencia exacta (ver config.py)."""
    tipo_empresa = _normalizar_texto(lead.get("tipo_empresa") or "")
    if not tipo_empresa:
        return None
    valor_mapeado = CONFIG["MAPEO_TIPO_EMPRESA_A_SEG_EMPRESA"].get(tipo_empresa)
    if not valor_mapeado:
        return None
    return _afinidad_por_valor_exacto(buyer_persona.get("seg_empresas", []), valor_mapeado)


def _dimension_pac(lead: dict, validacion: dict, buyer_persona: dict) -> float | None:
    personas_a_cargo = lead.get("personas_a_cargo")
    if personas_a_cargo is None:
        return None
    texto = CONFIG["PAC_NUMERO_A_TEXTO"].get(personas_a_cargo)
    if not texto:
        return None
    return _afinidad_por_valor_exacto(buyer_persona.get("pac", []), texto)


def _dimension_estrato(lead: dict, validacion: dict, buyer_persona: dict) -> float | None:
    """`estrato` no está en el schema formal del lead todavía (extra
    field vía `model_config = extra='allow'`). Si no viene, la dimensión
    simplemente no suma — no bloquea nada."""
    estrato = lead.get("estrato")
    if estrato is None:
        return None
    try:
        texto = CONFIG["PAC_NUMERO_A_TEXTO"].get(int(estrato))
    except (TypeError, ValueError):
        texto = str(estrato)
    if not texto:
        return None
    return _afinidad_por_valor_exacto(buyer_persona.get("estrato", []), texto)


def _dimension_familia(lead: dict, validacion: dict, buyer_persona: dict) -> float | None:
    """Heurístico (Fase 2, sin campo directo en el lead — VALIDAR CON
    NEGOCIO, ver plan.md §10): aproxima la composición familiar a partir
    de `personas_a_cargo` y `cabeza_de_hogar`. Peso bajo por defecto en
    config.py justamente porque es una aproximación, no un dato duro."""
    personas_a_cargo = lead.get("personas_a_cargo")
    if personas_a_cargo is None:
        return None
    cabeza_de_hogar = _condiciones_especiales(lead).get("cabeza_de_hogar", False)
    if personas_a_cargo <= 0:
        valor = "Sin Grupo"
    elif cabeza_de_hogar:
        valor = "Monoparental"
    else:
        valor = "Nuclear Integrada"
    return _afinidad_por_valor_exacto(buyer_persona.get("familia", []), valor)


def _dimension_ubicacion(lead: dict, validacion: dict, buyer_persona: dict) -> float | None:
    """Usa `departamento` de buyerPersona (distribución real de
    compradores por municipio/zona) en vez de un bono fijo por coincidir
    zona — reemplaza el bono_zona plano del diseño anterior (plan.md §5.3)."""
    zona = _normalizar_texto(lead.get("zona_preferida") or "")
    if not zona:
        return None
    mejor: float | None = None
    for bucket in buyer_persona.get("departamento", []):
        valor_norm = _normalizar_texto(bucket.get("valor", ""))
        if valor_norm and (valor_norm in zona or zona in valor_norm):
            porcentaje = (bucket.get("porcentaje", 0) or 0) / 100
            if mejor is None or porcentaje > mejor:
                mejor = porcentaje
    return mejor


_DIMENSIONES_MATCHING_HISTORICO = {
    "salario": _dimension_salario,
    "edad": _dimension_edad,
    "afiliacion": _dimension_afiliacion,
    "seg_empresa": _dimension_seg_empresa,
    "pac": _dimension_pac,
    "estrato": _dimension_estrato,
    "familia": _dimension_familia,
    "ubicacion": _dimension_ubicacion,
}


def _similitud_historica(lead: dict, validacion: dict, proyecto: dict) -> float:
    """Afinidad 0-1 del lead con el perfil histórico de compradores de UN
    proyecto. Promedio ponderado de las dimensiones que sí se pudieron
    calcular (dato disponible en el lead Y el valor cae en algún bucket de
    ESTE proyecto); las demás se excluyen del promedio en vez de sumar 0."""
    buyer_persona = proyecto.get("buyerPersona") or {}
    pesos = CONFIG["BUYER_PERSONA_WEIGHTS"]

    suma_ponderada = 0.0
    suma_pesos = 0.0
    for dimension, funcion in _DIMENSIONES_MATCHING_HISTORICO.items():
        peso = pesos.get(dimension, 0)
        if peso <= 0:
            continue
        afinidad = funcion(lead, validacion, buyer_persona)
        if afinidad is None:
            continue
        suma_ponderada += peso * afinidad
        suma_pesos += peso

    if suma_pesos == 0:
        return 0.0
    return round(suma_ponderada / suma_pesos, 3)


def _similitud_historica_maxima(lead: dict, validacion: dict) -> float:
    if not CATALOGO_PROYECTOS:
        return 0.0
    similitudes = [_similitud_historica(lead, validacion, p) for p in CATALOGO_PROYECTOS]
    return max(similitudes) if similitudes else 0.0


# ======================================================================
# Subsidio Concurrente por SISBEN (informativo para scoring)
# ======================================================================

def _grupo_sisben_indice(grupo: str | None) -> int | None:
    if not grupo:
        return None
    orden = CONFIG["SISBEN_ORDEN_GRUPOS"]
    grupo_norm = grupo.strip().upper()
    if grupo_norm not in orden:
        return None
    return orden.index(grupo_norm)


def _califica_sisben_subsidio(lead: dict) -> bool:
    idx_lead = _grupo_sisben_indice(lead.get("grupo_sisben"))
    if idx_lead is None:
        return False

    zona_tipo = CONFIG.get("SISBEN_ZONA_DEFAULT", "urbana")
    matriz_zona = CONFIG["SISBEN_SUBSIDIO_MATRIZ"][zona_tipo]
    orden = CONFIG["SISBEN_ORDEN_GRUPOS"]
    idx_tope_final = orden.index(matriz_zona[-1]["hasta_grupo"])

    return idx_lead <= idx_tope_final


# ======================================================================
# Score de prioridad comercial
# ======================================================================

def calcular_score(lead: dict, validacion: dict) -> dict:
    factores: dict[str, int] = {}
    w = CONFIG["SCORING_WEIGHTS"]

    factores["afiliado"] = (
        w["afiliado"] if lead.get("afiliado", False) else w["no_afiliado_penalizacion"]
    )

    factores["cierre_financiero_viable"] = (
        w["cierre_financiero_viable"]
        if validacion["cierre_financiero"]["cierre_viable"]
        else 0
    )

    similitud_historica = _similitud_historica_maxima(lead, validacion)
    factores["matching_historico"] = round(w["matching_historico"] * similitud_historica)

    finanzas = _finanzas(lead)
    factores["cesantias"] = w["cesantias"] if finanzas.get("cesantias", 0) > 0 else 0
    factores["ahorros"] = w["ahorros"] if finanzas.get("ahorros", 0) > 0 else 0

    condiciones = _condiciones_especiales(lead)
    condicion_especial = (
        condiciones.get("cabeza_de_hogar", False)
        or condiciones.get("discapacidad_hogar", False)
        or condiciones.get("mayor_65_anos", False)
    )
    factores["condicion_especial"] = w["condicion_especial"] if condicion_especial else 0

    factores["grupo_sisben"] = w["grupo_sisben"] if _califica_sisben_subsidio(lead) else 0

    factores["credito_preaprobado"] = (
        w["credito_preaprobado"] if finanzas.get("credito_preaprobado", False) else 0
    )

    factores["origen_organico"] = (
        w["origen_organico"] if lead.get("origen") == "organico" else 0
    )

    score_total = sum(factores.values())

    if not validacion["puede_comprar"]:
        prioridad = "BAJA"
    elif score_total >= CONFIG["SCORE_THRESHOLDS"]["ALTA"]:
        prioridad = "ALTA"
    elif score_total >= CONFIG["SCORE_THRESHOLDS"]["MEDIA"]:
        prioridad = "MEDIA"
    else:
        prioridad = "BAJA"

    cubre_valor_total = (
        validacion["cierre_financiero"]["ahorro_disponible"]
        >= validacion["cierre_financiero"]["precio_referencia_vivienda"]
    )
    override_rn04 = (
        validacion["puede_comprar"]
        and finanzas.get("credito_preaprobado", False)
        and validacion["aplica_subsidio"]
        and cubre_valor_total
    )
    if override_rn04:
        prioridad = "ALTA"

    return {
        "score_total": score_total,
        "prioridad": prioridad,
        "factores": factores,
        "override_rn04_aplicado": override_rn04,
    }


# ======================================================================
# Matching de proyectos — trabaja por TIPOLOGÍA (plan.md §5.4), no por
# precio único de proyecto.
# ======================================================================

def match_proyectos(lead: dict, validacion: dict, top_n: int = 3) -> list[dict]:
    cuota_maxima = validacion["cuota_maxima_mensual"]
    subsidio_general = validacion["subsidio_estimado"]
    finanzas = _finanzas(lead)
    ahorro_base = finanzas.get("cesantias", 0) + finanzas.get("ahorros", 0)
    zona_preferida = (lead.get("zona_preferida") or "").strip().lower()
    estrategia = CONFIG["ESTRATEGIA_SELECCION_TIPOLOGIA"]

    candidatos = []
    for proyecto in CATALOGO_PROYECTOS:
        tipo_proyecto = proyecto.get("tipo_proyecto")
        municipio = proyecto.get("municipio")

        tipologias_validas = []
        for tipologia in proyecto.get("tipologias", []):
            precio = tipologia.get("precio")
            if precio is None:
                continue

            # Filtro VIS/No VIS/VIP: exclusión total (decisión #18,
            # plan.md §5.4). Una tipología fuera del tope de SU tipo de
            # proyecto no se recomienda, sin importar qué tan asequible
            # sea financieramente.
            if not _valor_vivienda_dentro_de_tope(precio, municipio, tipo_proyecto):
                continue

            monto_credito_estimado = cuota_maxima * 120
            monto_total_disponible = ahorro_base + subsidio_general + monto_credito_estimado
            if precio > monto_total_disponible:
                continue  # no asequible con crédito + ahorro + subsidio

            cuota_inicial_requerida = round(
                precio * CONFIG["PORCENTAJE_CUOTA_INICIAL_REQUERIDO"]
            )
            ahorro_disponible_proyecto = ahorro_base + subsidio_general
            cierre_viable_proyecto = ahorro_disponible_proyecto >= cuota_inicial_requerida

            tipologias_validas.append(
                {
                    "nombre": tipologia.get("nombre"),
                    "precio": precio,
                    "cierre_financiero": {
                        "cuota_inicial_requerida": cuota_inicial_requerida,
                        "ahorro_disponible": ahorro_disponible_proyecto,
                        "cierre_viable": cierre_viable_proyecto,
                        "subsidio_aplicable": subsidio_general,
                    },
                }
            )

        if not tipologias_validas:
            continue

        # Decisión pendiente en plan.md §5.4, resuelta con el default
        # sugerido en propuesta.md: se recomienda la tipología más cara
        # que el lead sí puede pagar (mejor opción real). Ajustable en
        # CONFIG["ESTRATEGIA_SELECCION_TIPOLOGIA"] -> "todas_asequibles".
        if estrategia == "todas_asequibles":
            seleccionadas = tipologias_validas
        else:
            seleccionadas = [max(tipologias_validas, key=lambda t: t["precio"])]

        similitud = _similitud_historica(lead, validacion, proyecto)
        bono_zona = (
            0.1 if zona_preferida and municipio and zona_preferida in municipio else 0.0
        )
        match_score = round(min(1.0, similitud + bono_zona), 3)

        for tipologia_sel in seleccionadas:
            motivo = (
                f"Afinidad con el perfil histórico de compradores de "
                f"{proyecto.get('nombre')} ({round(similitud * 100)}% de match)"
            )
            if bono_zona:
                motivo += f"; coincide con la zona de interés ({lead.get('zona_preferida')})"

            candidatos.append(
                {
                    "proyecto": proyecto.get("nombre"),
                    "ubicacion": proyecto.get("ubicacion"),
                    "municipio": municipio,
                    "tipo_proyecto": tipo_proyecto,
                    "tipologia": tipologia_sel["nombre"],
                    "precio": tipologia_sel["precio"],
                    "brochure_url": proyecto.get("brochure_url"),
                    "match_score": match_score,
                    "motivo": motivo,
                    "cierre_financiero": tipologia_sel["cierre_financiero"],
                }
            )

    candidatos.sort(key=lambda c: c["match_score"], reverse=True)

    # Si existe proyecto_interes y es viable, priorizarlo como primera recomendación
    proyecto_interes_nombre = (lead.get("proyecto_interes") or "").strip().lower()
    if proyecto_interes_nombre:
        idx_interes = next(
            (i for i, c in enumerate(candidatos) if (c.get("proyecto") or "").strip().lower() == proyecto_interes_nombre),
            None,
        )
        if idx_interes is not None:
            candidato_interes = candidatos.pop(idx_interes)
            candidato_interes["motivo"] += "; (Proyecto de interés directo del lead - Priorizado)"
            candidatos.insert(0, candidato_interes)

    return candidatos[:top_n]


def evaluar_proyecto_interes(lead: dict, validacion: dict) -> dict | None:
    """Evalúa explícitamente el proyecto de interés declarado por el lead.

    Si no se especifica `proyecto_interes`, devuelve None.
    Si se especifica y NO es viable, devuelve `viable: false` con el motivo.
    Si se especifica y SÍ es viable, devuelve `viable: true`.
    """
    proyecto_nombre = lead.get("proyecto_interes")
    if not proyecto_nombre or not str(proyecto_nombre).strip():
        return None

    nombre_target = str(proyecto_nombre).strip().lower()

    proyecto_encontrado = None
    for p in CATALOGO_PROYECTOS:
        if (p.get("nombre") or "").strip().lower() == nombre_target:
            proyecto_encontrado = p
            break

    if not proyecto_encontrado:
        return {
            "proyecto": proyecto_nombre,
            "viable": False,
            "motivo": f"El proyecto de interés '{proyecto_nombre}' no existe en el catálogo activo.",
        }

    if not validacion.get("puede_comprar", False):
        motivos = ", ".join(validacion.get("motivos_rechazo", []))
        return {
            "proyecto": proyecto_nombre,
            "viable": False,
            "motivo": f"El postulante no cumple los requisitos de elegibilidad general ({motivos}).",
        }

    tipo_proyecto = proyecto_encontrado.get("tipo_proyecto")
    municipio = proyecto_encontrado.get("municipio")
    cuota_maxima = validacion["cuota_maxima_mensual"]
    subsidio_general = validacion["subsidio_estimado"]
    finanzas = _finanzas(lead)
    ahorro_base = finanzas.get("cesantias", 0) + finanzas.get("ahorros", 0)
    monto_credito_estimado = cuota_maxima * 120
    monto_total_disponible = ahorro_base + subsidio_general + monto_credito_estimado

    tipologias = proyecto_encontrado.get("tipologias", [])
    if not tipologias:
        return {
            "proyecto": proyecto_nombre,
            "viable": False,
            "motivo": f"El proyecto '{proyecto_nombre}' no tiene tipologías configuradas.",
        }

    precios = [t.get("precio") for t in tipologias if t.get("precio") is not None]
    if not precios:
        return {
            "proyecto": proyecto_nombre,
            "viable": False,
            "motivo": f"El proyecto '{proyecto_nombre}' no tiene precios de tipología válidos.",
        }

    precio_minimo = min(precios)
    if not _valor_vivienda_dentro_de_tope(precio_minimo, municipio, tipo_proyecto):
        return {
            "proyecto": proyecto_nombre,
            "viable": False,
            "motivo": f"El precio del proyecto '{proyecto_nombre}' excede los topes legales de vivienda {tipo_proyecto or 'VIS'} ({municipio or 'zona'}).",
        }

    if precio_minimo > monto_total_disponible:
        return {
            "proyecto": proyecto_nombre,
            "viable": False,
            "motivo": f"El precio mínimo del proyecto (${precio_minimo:,.0f}) excede la capacidad financiera total disponible (${monto_total_disponible:,.0f}).",
        }

    return {
        "proyecto": proyecto_nombre,
        "viable": True,
        "motivo": "Proyecto de interés viable y priorizado como primera recomendación.",
    }