"""
Adaptador de envío del lead perfilado a un sistema externo (CRM/Salesforce).

RF-11: transferir automáticamente toda la data del perfilamiento (score,
subsidios aplicables, proyecto sugerido) al CRM para gestión del asesor
humano. El backend confía en lo que arma `motor.procesar_lead` — no vuelve
a recalcular nada aquí.

Mismo patrón que el resto del proyecto (Repositorio + Adaptador, plan.md
§7): esta función es la única puerta de salida hacia el sistema externo.
Si mañana cambia de Salesforce a otra cosa, se edita solo este archivo.

Estado actual: sin URL/auth reales todavía -> deshabilitado por defecto
(`CONFIG["CRM_INTEGRACION_HABILITADA"]`) para no bloquear `/perfilar`
mientras se define el contrato con el sistema externo. Cuando se habilite,
el envío es "best effort": si falla o se agota el timeout, se registra el
error pero NUNCA se propaga — la respuesta al usuario de `/perfilar` no
debe depender de que el CRM esté disponible (RNF-03, latencia).
"""

from __future__ import annotations

import logging

from app.config import CONFIG

logger = logging.getLogger("crm_client")


class EnvioCRMResultado:
    """Resultado del intento de envío, para que quien llame decida si le
    interesa loguear/exponer algo (ej. en un panel de diagnóstico)."""

    def __init__(self, enviado: bool, detalle: str, status_code: int | None = None):
        self.enviado = enviado
        self.detalle = detalle
        self.status_code = status_code

    def to_dict(self) -> dict:
        return {
            "enviado": self.enviado,
            "detalle": self.detalle,
            "status_code": self.status_code,
        }


def _construir_payload(resultado_perfilamiento: dict) -> dict:
    """Arma el payload hacia el CRM a partir de la respuesta completa de
    `motor.procesar_lead`. Por ahora se envía el `PerfilamientoResponse`
    completo (incluye `lead_original`) tal cual: es lo que pide RF-11
    ("toda la data del perfilamiento, el score, los subsidios aplicables
    y el proyecto sugerido"). Si el contrato real del CRM pide un shape
    distinto, se transforma aquí — el resto del motor no se toca.
    """
    return resultado_perfilamiento


def enviar_lead_perfilado(resultado_perfilamiento: dict) -> EnvioCRMResultado:
    """Envía el lead perfilado completo al CRM externo. Nunca lanza
    excepción hacia quien la llama — siempre devuelve un resultado, para
    que `/perfilar` pueda seguir respondiendo al usuario aunque el CRM
    esté caído.
    """
    if not CONFIG["CRM_INTEGRACION_HABILITADA"]:
        return EnvioCRMResultado(
            enviado=False,
            detalle="Integración CRM deshabilitada (CRM_INTEGRACION_HABILITADA=false).",
        )

    endpoint = CONFIG["CRM_ENDPOINT_URL"]
    if not endpoint:
        logger.warning("CRM_INTEGRACION_HABILITADA=true pero falta CRM_ENDPOINT_URL.")
        return EnvioCRMResultado(enviado=False, detalle="Falta configurar CRM_ENDPOINT_URL.")

    payload = _construir_payload(resultado_perfilamiento)

    try:
        import requests
        headers = {"Content-Type": "application/json"}
        if CONFIG["CRM_API_KEY"]:
            headers["Authorization"] = f"Bearer {CONFIG['CRM_API_KEY']}"
        respuesta = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=CONFIG["CRM_TIMEOUT_SEGUNDOS"],
        )
        if 200 <= respuesta.status_code < 300:
            print(f"✅ ¡WEBHOOK ENVIADO CON ÉXITO! Status: {respuesta.status_code}")
            return EnvioCRMResultado(
                enviado=True, detalle="OK", status_code=respuesta.status_code
            )
        logger.warning(
            "CRM respondió %s al enviar lead %s",
            respuesta.status_code,
            payload.get("lead_original", {}).get("id_usuario"),
        )
        return EnvioCRMResultado(
            enviado=False,
            detalle=f"CRM respondió status {respuesta.status_code}",
            status_code=respuesta.status_code,
        )
    except ImportError:
        import json
        import urllib.request
        import urllib.error

        payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if CONFIG["CRM_API_KEY"]:
            headers["Authorization"] = f"Bearer {CONFIG['CRM_API_KEY']}"

        req = urllib.request.Request(endpoint, data=payload_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=CONFIG["CRM_TIMEOUT_SEGUNDOS"]) as response:
                status_code = response.getcode()
                if 200 <= status_code < 300:
                    print(f"[OK] WEBHOOK ENVIADO CON EXITO! Status: {status_code}")
                    return EnvioCRMResultado(enviado=True, detalle="OK", status_code=status_code)
                return EnvioCRMResultado(enviado=False, detalle=f"CRM respondió status {status_code}", status_code=status_code)
        except urllib.error.HTTPError as err:
            return EnvioCRMResultado(enviado=False, detalle=f"CRM respondió status {err.code}", status_code=err.code)
        except Exception as exc:
            logger.error("Error enviando lead al CRM: %s", exc)
            return EnvioCRMResultado(enviado=False, detalle=f"Error de conexión: {exc}")
    except Exception as exc:  # noqa: BLE001 — best effort, nunca debe tumbar /perfilar
        logger.error("Error enviando lead al CRM: %s", exc)
        return EnvioCRMResultado(enviado=False, detalle=f"Error de conexión: {exc}")