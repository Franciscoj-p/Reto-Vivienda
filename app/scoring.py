from __future__ import annotations

from app.catalogo import CATALOGO_PROYECTOS
from app.config import SCORE_THRESHOLDS, SCORING_WEIGHTS


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


def calcular_score(lead: dict, validacion: dict) -> dict:
    factores: dict[str, int] = {}
    w = SCORING_WEIGHTS

    factores["afiliado"] = w["afiliado"] if lead.get("afiliado", False) else 0
    factores["cierre_financiero_viable"] = (
        w["cierre_financiero_viable"]
        if validacion["cierre_financiero"]["cierre_viable"]
        else 0
    )
    similitud_historica = _similitud_promedio_catalogo(lead)
    factores["matching_historico"] = round(w["matching_historico"] * similitud_historica)
    tiene_ahorro = (lead.get("cesantias", 0) + lead.get("ahorros", 0)) > 0
    factores["ahorro_previo"] = w["ahorro_previo"] if tiene_ahorro else 0
    condicion_especial = (
        lead.get("cabeza_de_hogar", False)
        or lead.get("tiene_discapacidad_hogar", False)
        or (lead.get("edad") or 0) >= 65
    )
    factores["condicion_especial"] = w["condicion_especial"] if condicion_especial else 0
    factores["origen_organico"] = (
        w["origen_organico"] if lead.get("origen") == "organico" else 0
    )

    score_total = sum(factores.values())
    if not validacion["puede_comprar"]:
        prioridad = "BAJA"
    elif score_total >= SCORE_THRESHOLDS["ALTA"]:
        prioridad = "ALTA"
    elif score_total >= SCORE_THRESHOLDS["MEDIA"]:
        prioridad = "MEDIA"
    else:
        prioridad = "BAJA"

    return {"score_total": score_total, "prioridad": prioridad, "factores": factores}


def match_proyectos(lead: dict, validacion: dict, top_n: int = 3) -> list[dict]:
    cuota_maxima = validacion["cuota_maxima_mensual"]
    subsidio = validacion["subsidio_estimado"]
    ahorro_disponible = validacion["cierre_financiero"]["ahorro_disponible"]
    zona_preferida = (lead.get("zona_preferida") or "").strip().lower()

    candidatos = []
    for proyecto in CATALOGO_PROYECTOS:
        monto_credito_estimado = cuota_maxima * 120
        monto_total_disponible = ahorro_disponible + subsidio + monto_credito_estimado
        asequible = proyecto["precio"] <= monto_total_disponible
        if not asequible:
            continue

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
            }
        )

    candidatos.sort(key=lambda c: c["match_score"], reverse=True)
    return candidatos[:top_n]
