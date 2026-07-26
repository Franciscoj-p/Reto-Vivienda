"""
Script para generar y transmitir los 5 leads representativos de la demo
al CRM (SimCRM) vía webhook.
"""

import sys
from pathlib import Path

# Asegurar que el directorio raíz está en sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app.motor import procesar_lead

LEADS_DEMO = [
    {
        "id_usuario": "1018300400",
        "nombre": "Diana Martínez Rojas",
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
        "zona_preferida": "Soacha",
        "proyecto_interes": "Versalles",
        "origen": "organico",
    },
    {
        "id_usuario": "52741889",
        "nombre": "Luisa Fernanda Gómez",
        "afiliado": True,
        "categoria": "A",
        "antiguedad_meses": 10,
        "tipo_cotizante": "independiente",
        "ingresos_mensuales": 1_600_000,
        "grupo_sisben": "B3",
        "edad": 29,
        "personas_a_cargo": 0,
        "condiciones_especiales": {
            "cabeza_de_hogar": False,
            "discapacidad_hogar": False,
            "mayor_65_anos": False,
        },
        "propietario_vivienda": False,
        "subsidio_previo": False,
        "subsidio_previo_fue_arrendamiento": False,
        "finanzas": {
            "cesantias": 1_500_000,
            "ahorros": 2_000_000,
            "credito_preaprobado": True,
        },
        "tipo_empresa": "Micro",
        "zona_preferida": "Soacha",
        "proyecto_interes": "Pamplona",
        "origen": "organico",
    },
    {
        "id_usuario": "79845123",
        "nombre": "Carlos Andrés Peña",
        "afiliado": True,
        "categoria": "C",
        "antiguedad_meses": 89,
        "tipo_cotizante": "dependiente",
        "ingresos_mensuales": 4_200_000,
        "grupo_sisben": "C5",
        "edad": 37,
        "personas_a_cargo": 1,
        "condiciones_especiales": {
            "cabeza_de_hogar": False,
            "discapacidad_hogar": False,
            "mayor_65_anos": False,
        },
        "propietario_vivienda": False,
        "subsidio_previo": True,
        "subsidio_previo_fue_arrendamiento": True,
        "finanzas": {
            "cesantias": 15_000_000,
            "ahorros": 25_000_000,
            "credito_preaprobado": True,
        },
        "tipo_empresa": "Top",
        "zona_preferida": "Bogotá",
        "proyecto_interes": "Los Nogales",
        "origen": "organico",
    },
    {
        "id_usuario": "1030567234",
        "nombre": "Jorge Iván Ruíz",
        "afiliado": True,
        "categoria": "C",
        "antiguedad_meses": 187,
        "tipo_cotizante": "pensionado",
        "ingresos_mensuales": 3_800_000,
        "grupo_sisben": "C9",
        "edad": 51,
        "personas_a_cargo": 3,
        "condiciones_especiales": {
            "cabeza_de_hogar": False,
            "discapacidad_hogar": False,
            "mayor_65_anos": False,
        },
        "propietario_vivienda": False,
        "subsidio_previo": False,
        "subsidio_previo_fue_arrendamiento": False,
        "finanzas": {
            "cesantias": 0,
            "ahorros": 4_000_000,
            "credito_preaprobado": False,
        },
        "tipo_empresa": "Medianas",
        "zona_preferida": "Chía",
        "proyecto_interes": "INARI",
        "origen": "organico",
    },
    {
        "id_usuario": "1014258963",
        "nombre": "Carolina Soto Vargas",
        "afiliado": True,
        "categoria": "A",
        "antiguedad_meses": 36,
        "tipo_cotizante": "dependiente",
        "ingresos_mensuales": 1_400_000,
        "grupo_sisben": "B4",
        "edad": 33,
        "personas_a_cargo": 1,
        "condiciones_especiales": {
            "cabeza_de_hogar": False,
            "discapacidad_hogar": False,
            "mayor_65_anos": False,
        },
        "propietario_vivienda": False,
        "subsidio_previo": True,
        "subsidio_previo_fue_arrendamiento": False,
        "finanzas": {
            "cesantias": 1_000_000,
            "ahorros": 500_000,
            "credito_preaprobado": False,
        },
        "tipo_empresa": "Micro",
        "zona_preferida": "Soacha",
        "proyecto_interes": "La Macarena",
        "origen": "campaña",
    },
]


def ejecutar_demo():
    print("=" * 70)
    print("INICIANDO PROCESAMIENTO Y ENVÍO DE LEADS REPRESENTATIVOS A SIMCRM")
    print("=" * 70)

    for i, lead in enumerate(LEADS_DEMO, 1):
        print(f"\n[{i}/{len(LEADS_DEMO)}] Procesando Lead: {lead['nombre']} ({lead['id_usuario']})...")
        res = procesar_lead(lead, enviar_a_crm=True)
        viable = res["financial_score"]["viable"]
        prioridad = res["lead_info"]["prioridad"]
        matches = len(res["matching_projects"])
        top_match = res["matching_projects"][0]["proyecto"] if matches > 0 else "N/A"
        print(f"    - Viable: {viable} | Prioridad: {prioridad} | Matches: {matches} (Top: {top_match})")
        
        crm_info = res.get("crm_envio", {})
        if crm_info.get("enviado"):
            print(f"    -> Webhook entregado con éxito a SimCRM (Status {crm_info.get('status_code')})")
        else:
            print(f"    -> ATENCIÓN: No se pudo entregar al Webhook. Detalle: {crm_info.get('detalle')}")

    print("\n" + "=" * 70)
    print("PROCESAMIENTO COMPLETADO CON ÉXITO.")
    print("=" * 70)


if __name__ == "__main__":
    ejecutar_demo()
