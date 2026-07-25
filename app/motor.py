"""
Orquestador del motor de perfilamiento.

Flujo: lead -> reglas -> score -> matching -> respuesta -> (best effort) CRM.

NOTA DE ESTA SESIÓN: la respuesta de `procesar_lead` sigue siendo el
`PerfilamientoResponse` completo (pensado para Salesforce/el asesor). El
rediseño para que `/perfilar` devuelva algo distinto al usuario final
(matches si es ALTA, motivos si es BAJA) queda pendiente para la próxima
sesión — ver plan.md. Lo que sí se conecta aquí es el envío del lead
perfilado completo al CRM externo (RF-11).
"""

from __future__ import annotations

import json

from app.integrations.crm_client import enviar_lead_perfilado
from app.reglas import validar_reglas
from app.scoring import calcular_score, evaluar_proyecto_interes, match_proyectos


def procesar_lead(lead: dict, enviar_a_crm: bool = True) -> dict:
    """Procesa un lead y devuelve el `PerfilamientoResponse` completo.

    `enviar_a_crm=True` por defecto: el lead perfilado completo se manda
    al sistema externo (RF-11) de forma best-effort — si falla, no rompe
    la respuesta de `/perfilar` (ver app/integrations/crm_client.py). Se
    puede desactivar por llamada (ej. en tests) con `enviar_a_crm=False`,
    además del flag global `CONFIG["CRM_INTEGRACION_HABILITADA"]`.
    """
    validacion = validar_reglas(lead)
    score = calcular_score(lead, validacion)
    proyectos = match_proyectos(lead, validacion)
    evaluacion_interes = evaluar_proyecto_interes(lead, validacion)

    prioridad_label = f"{score['prioridad']}"
    if lead.get("afiliado") and score["prioridad"] == "ALTA":
        prioridad_label += " (90/10)"

    resultado = {
        "lead_info": {
            "nombre": lead.get("nombre"),
            "afiliado": lead.get("afiliado", False),
            "prioridad": prioridad_label,
            "segmentacion_caja": validacion["segmentacion_caja"],
        },
        "financial_score": {
            "viable": "SI" if validacion["puede_comprar"] else "NO",
            "motivos_rechazo": validacion["motivos_rechazo"],
            "subsidio_estimado": validacion["subsidio_estimado"],
            "descalifica_subsidio_por_techo_ingresos": validacion[
                "descalifica_subsidio_por_techo_ingresos"
            ],
            "capacidad_max_cuota": validacion["cuota_maxima_mensual"],
            "cierre_financiero": validacion["cierre_financiero"],
            "subsidio_concurrente_mi_casa_ya": validacion["subsidio_concurrente_mi_casa_ya"],
            "subsidio_arrendamiento": validacion["subsidio_arrendamiento_sugerido"],
            "condiciones_subsidio": validacion["condiciones_subsidio"],
        },
        "score_detalle": score,
        "evaluacion_proyecto_interes": evaluacion_interes,
        "matching_projects": proyectos,
        "ai_summary": _generar_resumen(lead, validacion, score, proyectos),
        "lead_original": lead,
    }

    if enviar_a_crm:
        envio = enviar_lead_perfilado(resultado)
        # Informativo/auditable, no cambia el contrato que ya consume el
        # front hoy (RNF-02 explicabilidad: que quede rastro de si el CRM
        # recibió el lead o no).
        print(f"\n================ [CRM STATUS] ================\nEnviado: {envio.enviado}\nDetalle: {envio.detalle}\nStatus Code: {envio.status_code}\n==============================================\n")
        
        resultado["crm_envio"] = envio.to_dict()

    return resultado


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
            "id_usuario": "1018300400",
            "nombre": "Diana Martínez",
            "afiliado": True,
            "categoria": "B",
            "antiguedad_meses": 24,
            "tipo_cotizante": "dependiente",
            "ingresos_mensuales": 2_900_000,
            "grupo_sisben": "C2",
            "edad": 31,
            "personas_a_cargo": 2,
            "condiciones_especiales": {
                "cabeza_de_hogar": True,
                "discapacidad_hogar": False,
                "mayor_65_anos": False,
            },
            "propietario_vivienda": False,
            "subsidio_previo": False,
            "subsidio_previo_fue_arrendamiento": False,
            "finanzas": {
                "cesantias": 3_000_000,
                "ahorros": 5_000_000,
                "credito_preaprobado": True,
            },
            "tipo_empresa": "Medianas",
            "zona_preferida": "Bogotá",
            "valor_vivienda_deseada": 150_000_000,
            "origen": "organico",
        },
    ]

    for lead in leads_ejemplo:
        resultado = procesar_lead(lead)
        print("=" * 70)
        print(f"LEAD: {lead['nombre']}")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))