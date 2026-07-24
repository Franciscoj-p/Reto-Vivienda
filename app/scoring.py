from __future__ import annotations

from app.catalogo import CATALOGO_PROYECTOS
from app.config import CONFIG
from app.reglas import _valor_vivienda_dentro_de_tope


# ======================================================================
# Helpers de acceso a estructura anidada del lead (mismo criterio que
# reglas.py: el lead llega como dict, `finanzas` y `condiciones_especiales`
# ya vienen como sub-dicts).
# ======================================================================

def _finanzas(lead: dict) -> dict:
    return lead.get("finanzas") or {}


def _condiciones_especiales(lead: dict) -> dict:
    return lead.get("condiciones_especiales") or {}


# ======================================================================
# Similitud histórica — SIN REDISEÑAR (pendiente Fase 5.3 del plan: pasar
# a afinidad por perfiles porcentuales por proyecto, requiere el CSV de
# perfiles que genera el ETL de Fase 2. Se mantiene la fórmula de
# distancia-a-promedio actual mientras tanto).
# ======================================================================

def _similitud_proyecto(lead: dict, proyecto: dict) -> float:
    ingresos_lead = lead.get("ingresos_mensuales", 0)
    ingresos_proy = proyecto["ingreso_promedio_comprador"]
    dif_ingresos = abs(ingresos_lead - ingresos_proy) / max(ingresos_proy, 1)
    score_ingresos = max(0.0, 1 - dif_ingresos)

    edad_lead = lead.get("edad", proyecto["edad_promedio_comprador"])
    dif_edad = abs(edad_lead - proyecto["edad_promedio_comprador"]) / 20
    score_edad = max(0.0, 1 - dif_edad)

    score_empresa = (
        1.0
        if lead.get("tipo_empresa") == proyecto["tipo_empresa_predominante"]
        else 0.3
    )

    return round(0.5 * score_ingresos + 0.3 * score_edad + 0.2 * score_empresa, 3)


def _similitud_promedio_catalogo(lead: dict) -> float:
    if not CATALOGO_PROYECTOS:
        return 0.0
    similitudes = [_similitud_proyecto(lead, p) for p in CATALOGO_PROYECTOS]
    return max(similitudes)


# ======================================================================
# Subsidio Concurrente por SISBEN (informativo para scoring — la
# elegibilidad legal a compra/subsidio principal vive en reglas.py)
# ------------------------------------------------------------------
# PENDIENTE DE NEGOCIO: el lead no trae todavía el campo de zona
# urbana/rural, así que se usa CONFIG["SISBEN_ZONA_DEFAULT"] como
# fallback. Ajustar en cuanto exista el campo real en el lead.
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

    # Afiliado: regla 90/10 en ambos sentidos — suma si es afiliado,
    # RESTA activamente si no lo es (antes solo dejaba de sumar).
    factores["afiliado"] = (
        w["afiliado"] if lead.get("afiliado", False) else w["no_afiliado_penalizacion"]
    )

    factores["cierre_financiero_viable"] = (
        w["cierre_financiero_viable"]
        if validacion["cierre_financiero"]["cierre_viable"]
        else 0
    )

    similitud_historica = _similitud_promedio_catalogo(lead)
    factores["matching_historico"] = round(w["matching_historico"] * similitud_historica)

    # Cesantías y ahorros separados: cesantías inmovilizadas puntúan más.
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

    # Override RN-04: crédito preaprobado + subsidio aplicable + cierre
    # financiero cubre el valor total -> prioridad ALTA aunque el score
    # numérico no llegue a 70. El score_total expuesto NO se altera.
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
# Matching de proyectos
# ======================================================================

def match_proyectos(lead: dict, validacion: dict, top_n: int = 3) -> list[dict]:
    cuota_maxima = validacion["cuota_maxima_mensual"]
    subsidio_general = validacion["subsidio_estimado"]
    finanzas = _finanzas(lead)
    ahorro_base = finanzas.get("cesantias", 0) + finanzas.get("ahorros", 0)
    zona_preferida = (lead.get("zona_preferida") or "").strip().lower()

    candidatos = []
    for proyecto in CATALOGO_PROYECTOS:
        # Filtro VIS/No VIS conectado (plan 5.4): proyectos fuera del tope
        # VIS/VIP de su municipio se EXCLUYEN del matching por completo,
        # no se recomiendan (decisión confirmada).
        proyecto_dentro_tope = _valor_vivienda_dentro_de_tope(
            proyecto["precio"], proyecto["municipio"]
        )
        if not proyecto_dentro_tope:
            continue

        subsidio_aplicable = subsidio_general
        monto_credito_estimado = cuota_maxima * 120
        monto_total_disponible = ahorro_base + subsidio_aplicable + monto_credito_estimado
        asequible = proyecto["precio"] <= monto_total_disponible
        if not asequible:
            continue

        # Cierre financiero por proyecto (plan 5.4): ya no se compara
        # contra el precio promedio del portafolio VIS, sino contra el
        # precio real de este candidato.
        cuota_inicial_requerida = round(
            proyecto["precio"] * CONFIG["PORCENTAJE_CUOTA_INICIAL_REQUERIDO"]
        )
        ahorro_disponible_proyecto = ahorro_base + subsidio_aplicable
        cierre_viable_proyecto = ahorro_disponible_proyecto >= cuota_inicial_requerida

        similitud = _similitud_proyecto(lead, proyecto)
        bono_zona = 0.1 if zona_preferida and zona_preferida in proyecto["municipio"].lower() else 0.0
        match_score = round(min(1.0, similitud + bono_zona), 3)

        motivo = (
            f"Similitud de ingresos/perfil con compradores de {proyecto['proyecto']} "
            f"({round(similitud * 100)}% de match)"
        )
        if bono_zona:
            motivo += f"; coincide con la zona de interés ({lead.get('zona_preferida')})"

        candidatos.append(
            {
                "proyecto": proyecto["proyecto"],
                "municipio": proyecto["municipio"],
                "tipo": proyecto["tipo"],
                "precio": proyecto["precio"],
                "match_score": match_score,
                "motivo": motivo,
                "cierre_financiero": {
                    "cuota_inicial_requerida": cuota_inicial_requerida,
                    "ahorro_disponible": ahorro_disponible_proyecto,
                    "cierre_viable": cierre_viable_proyecto,
                    "subsidio_aplicable": subsidio_aplicable,
                },
            }
        )

    candidatos.sort(key=lambda c: c["match_score"], reverse=True)
    return candidatos[:top_n]