"""
Orquestador del motor de perfilamiento.

Flujo: lead -> reglas -> score -> matching -> respuesta para Salesforce.
"""

from __future__ import annotations

import json

from app.reglas import validar_reglas
from app.scoring import calcular_score, match_proyectos


def procesar_lead(lead: dict) -> dict:
    validacion = validar_reglas(lead)
    score = calcular_score(lead, validacion)
    proyectos = match_proyectos(lead, validacion)

    prioridad_label = f"{score['prioridad']}"
    if lead.get("afiliado") and score["prioridad"] == "ALTA":
        prioridad_label += " (90/10)"

    return {
        "lead_info": {
            "nombre": lead.get("nombre"),
            "afiliado": lead.get("afiliado", False),
            "prioridad": prioridad_label,
        },
        "financial_score": {
            "viable": "SI" if validacion["puede_comprar"] else "NO",
            "motivos_rechazo": validacion["motivos_rechazo"],
            "subsidio_estimado": validacion["subsidio_estimado"],
            "capacidad_max_cuota": validacion["cuota_maxima_mensual"],
            "cierre_financiero": validacion["cierre_financiero"],
            "subsidio_concurrente_mi_casa_ya": validacion.get("subsidio_concurrente"),
            "subsidio_arrendamiento": validacion.get("subsidio_arrendamiento_sugerido"),
            "condiciones_subsidio": validacion["condiciones_subsidio"],
        },
        "score_detalle": score,
        "matching_projects": proyectos,
        "ai_summary": _generar_resumen(lead, validacion, score, proyectos),
        "lead_original": lead,
    }


def _generar_resumen(lead: dict, validacion: dict, score: dict, proyectos: list[dict]) -> str:
    if not validacion["puede_comprar"]:
        return (
            f"Lead no viable por ahora: {', '.join(validacion['motivos_rechazo'])}. "
            f"Requiere ruta de mejora de perfil."
        )
    zona = lead.get("zona_preferida", "sin preferencia declarada")
    top = proyectos[0]["proyecto"] if proyectos else "sin match disponible"
    return (
        f"Lead {score['prioridad']} interesado en {zona}. "
        f"Mejor match: {top}. Subsidio estimado: ${validacion['subsidio_estimado']:,}."
    )


if __name__ == "__main__":
    leads_ejemplo = [
        {
            "nombre": "Diana Martínez",
            "afiliado": True,
            "categoria": "B",
            "antiguedad_meses": 24,
            "ingresos_mensuales": 2_900_000,
            "edad": 31,
            "personas_a_cargo": 2,
            "cabeza_de_hogar": True,
            "tiene_discapacidad_hogar": False,
            "propietario_vivienda": False,
            "tipo_empresa": "Medianas",
            "cesantias": 3_000_000,
            "ahorros": 5_000_000,
            "zona_preferida": "Bogotá",
            "origen": "organico",
            "tipo_cotizante": "dependiente",
            "subsidio_vivienda_previo": False,
            "subsidio_previo_fue_arrendamiento": False,
            "valor_vivienda_deseada": 150_000_000,
            
        },
    ]

    for lead in leads_ejemplo:
        resultado = procesar_lead(lead)
        print("=" * 70)
        print(f"LEAD: {lead['nombre']}")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
