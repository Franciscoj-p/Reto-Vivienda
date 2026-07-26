"""
Parámetros de negocio — Motor de Perfilamiento (Colsubsidio).

Este archivo NO contiene lógica, solo constantes. Cualquier cambio normativo
o de negocio se ajusta AQUÍ. Ver `plan.md` sección 8 para el historial de
decisiones que originaron cada bloque.
"""

import os
from pathlib import Path

# Raíz del proyecto = la carpeta que contiene `app/`.
BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG = {

    
    # ==================================================================
    # Integración con sistema externo (CRM / Salesforce) — RF-11
    # ------------------------------------------------------------------
    # El lead perfilado completo (score, subsidios, proyecto sugerido) se
    # envía a un sistema externo para gestión del asesor humano. Todavía
    # no tenemos URL/auth reales del CRM -> deshabilitado por defecto para
    # no romper `/perfilar` mientras se define. Ver app/integrations/crm_client.py.
    # ==================================================================
    # "CRM_INTEGRACION_HABILITADA": os.getenv("CRM_INTEGRACION_HABILITADA", "false").lower() == "true",
    # "CRM_ENDPOINT_URL": os.getenv("CRM_ENDPOINT_URL", ""),
    # "CRM_API_KEY": os.getenv("CRM_API_KEY", ""),
    # "CRM_TIMEOUT_SEGUNDOS": float(os.getenv("CRM_TIMEOUT_SEGUNDOS", "3")),

    "CRM_INTEGRACION_HABILITADA": True,
    "CRM_ENDPOINT_URL": "http://localhost:8002/webhook/perfilamiento",  # Tu webhook real
    "CRM_TIMEOUT_SEGUNDOS": 10,  # Timeout para la llamada al CRM (en segundos)  
    "CRM_API_KEY":"",
    # ==================================================================
    # Generales
    # ==================================================================
    "SMMLV_2026": 1_750_905,
    "TOPE_INGRESOS_SMMLV": 4,  # límite superior para calificar a subsidio de vivienda nueva
    "LIMITE_CUOTA_INGRESO": 0.40,  # Regla del 40% (Ley de Vivienda)
    "PORCENTAJE_CUOTA_INICIAL_REQUERIDO": 0.30,  # 30% Cuota Inicial obligatoria
    "PORCENTAJE_FINANCIACION_CREDITO": 0.70,     # 70% Financiación Crédito Hipotecario
    "PLAZO_ENTREGA_DEFAULT_MESES": 24,           # Plazo por defecto para pago diferido de cuota inicial
    "PLAZO_CREDITO_HIPOTECARIO_ANOS": 20,         # Plazo estándar de crédito hipotecario (20 años)
    "TASA_INTERES_CREDITO_EA": 0.12,              # Tasa de interés efectiva anual (12% E.A.)

    # ==================================================================
    # Matriz de subsidio por rango de ingresos (en SMMLV)
    # ==================================================================
    "MATRIZ_SUBSIDIOS": [
        {"max_smmlv": 2, "subsidio_smmlv": 30},   # 0 a 2 SMMLV -> $52.527.150
        {"max_smmlv": 4, "subsidio_smmlv": 20},   # 2 a 4 SMMLV -> $35.018.100
        # > 4 SMMLV no hay coincidencia -> subsidio = 0
    ],

    # ==================================================================
    # Antigüedad de afiliación (por tipo de cotizante)
    # ==================================================================
    "ANTIGUEDAD_MINIMA_MESES_POR_TIPO": {
        "dependiente": 6,
        "independiente": 6,
        "pensionado": 6,
    },
    "ANTIGUEDAD_MINIMA_MESES_DEFAULT": 6,

    # ==================================================================
    # Topes de valor de vivienda por tipo (en SMMLV)
    # ------------------------------------------------------------------
    # VIS_TOPE_* se usa cuando el proyecto/tipología es "VIS".
    # VIP_TOPE_SMMLV se usa cuando el proyecto/tipología es "VIP".
    # Un proyecto "NO VIS" (mercado libre) no está sujeto a ninguno de
    # estos topes — ver `_tope_smmlv_por_tipo_proyecto` en reglas.py.
    # ==================================================================
    "VIS_TOPE_SMMLV_PRINCIPAL": 150,  # municipios principales (Bogotá, etc.)
    "VIS_TOPE_SMMLV_OTROS": 135,      # resto de municipios
    "VIP_TOPE_SMMLV": 90,

    "MUNICIPIOS_PRINCIPALES": [
        "bogota", "soacha", "chia", "cota", "girardot",
    ],

    # ==================================================================
    # Cobertura geográfica del subsidio Colsubsidio (Bogotá y Cundinamarca)
    # ------------------------------------------------------------------
    # Se agregaron tocancipa/ricaurte/ubate (decisión #20, plan.md sección
    # 5.2): el catálogo viejo no los traía y era un error, no una decisión
    # de negocio — todos son municipios de Cundinamarca igual que los que
    # ya estaban.
    # ==================================================================
    "ZONAS_COBERTURA_SUBSIDIO": [
        "bogota", "soacha", "chia", "cota", "girardot",
        "cundinamarca", "zipaquira", "facatativa", "mosquera", "madrid",
        "funza", "cajica", "fusagasuga", "tocancipa", "ricaurte", "ubate",
    ],

    # ==================================================================
    # Subsidio concurrente "Mi Casa Ya" (informativo)
    # ==================================================================
    "MI_CASA_YA_TOPE_INGRESOS_SMMLV": 2,
    "MI_CASA_YA_SUBSIDIO_ADICIONAL_SMMLV": 20,

    # ==================================================================
    # Subsidio Concurrente por grupo SISBEN (RN — tabla oficial recibida)
    # ==================================================================
    "SISBEN_ORDEN_GRUPOS": [
        "A1", "A2", "A3", "A4", "A5",
        "B1", "B2", "B3", "B4", "B5", "B6", "B7",
        "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10",
        "C11", "C12", "C13", "C14", "C15", "C16", "C17", "C18",
        "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10",
        "D11", "D12", "D13", "D14", "D15", "D16", "D17", "D18", "D19", "D20", "D21",
    ],

    "SISBEN_SUBSIDIO_MATRIZ": {
        "urbana": [
            {"hasta_grupo": "C7", "subsidio_smmlv": 30},
            {"hasta_grupo": "D11", "subsidio_smmlv": 20},
        ],
        "rural": [
            {"hasta_grupo": "C14", "subsidio_smmlv": 30},
            {"hasta_grupo": "D20", "subsidio_smmlv": 20},
        ],
    },

    "SISBEN_ZONA_DEFAULT": "urbana",  # ⚠️ pendiente: reemplazar por campo real del lead

    # ==================================================================
    # Subsidio de arrendamiento (ruta alterna si no hay cierre financiero)
    # ==================================================================
    "SUBSIDIO_ARRENDAMIENTO_SMMLV_MENSUAL": 0.6,
    "SUBSIDIO_ARRENDAMIENTO_MESES": 24,

    # ==================================================================
    # Segmentación de Caja — cortes para clasificar automáticamente al lead
    # ==================================================================
    "SEGMENTACION_CAJA_BASICO_MAX_SMMLV": 1.44,
    "SEGMENTACION_CAJA_MEDIO_MAX_SMMLV": 20,
    "SEGMENTACION_CAJA_JOVEN_EDAD_MAX": 39,

    # ==================================================================
    # Pesos de scoring (0-100). El score SIEMPRE se expone como número;
    # "prioridad" es solo una etiqueta derivada de estos puntos + el
    # override de RN-04.
    # ==================================================================
    "SCORING_WEIGHTS": {
        "afiliado": 25,
        "no_afiliado_penalizacion": -10,
        "condicion_especial": 10,
        "cesantias": 8,
        "ahorros": 4,
        "grupo_sisben": 8,
        "credito_preaprobado": 10,
        "matching_historico": 20,
        "cierre_financiero_viable": 10,
        "origen_organico": 5,
    },
    "SCORE_THRESHOLDS": {
        "ALTA": 70,
        "MEDIA": 40,
    },

    # ==================================================================
    # Fase 1 — capa de datos: afiliados
    # ==================================================================
    "DATA_SOURCE_AFILIADOS": "csv",
    "RUTA_CSV_AFILIADOS": "data/afiliados.csv",
    "MAPEO_COLUMNAS_AFILIADOS": {
        "ID_USUARIO": "id_usuario",
        "NOMBRE_COMPLETO": "nombre",
        "FEC_NACIMIENTO": "fecha_nacimiento",
        "IND_AFILIADO": "afiliado",
        "COD_CATEGORIA": "categoria",
        "AFIL_ANTIGUEDAD_MESES": "antiguedad_meses",
        "TIPO_COTIZANTE": "tipo_cotizante",
        "INGRESO_BASE_COTIZACION": "ingresos_mensuales",
        "SEG_EMPRESA": "tipo_empresa",
        "NUM_PERSONAS_A_CARGO": "personas_a_cargo",
        "ESTRATO": "estrato",
        "GRUPO_SISBEN": "grupo_sisben",
        "SUBSIDIO_VIVIENDA_PREVIO": "subsidio_previo",
        "SUBSIDIO_PREVIO_FUE_ARRENDAMIENTO": "subsidio_previo_fue_arrendamiento",
        "CELULAR": "celular",
        "CORREO_ELECTRONICO": "email",
        "EDAD": "edad",
        "ZONA": "zona",
    },

    # ==================================================================
    # Catálogo de proyectos — fuente JSON (reemplaza el CSV, plan.md §5)
    # ==================================================================
    "RUTA_JSON_PROYECTOS": "data/proyectos.json",

    # Catálogo cerrado de `ubicacion` (plan.md §5.2). Sirve para validar
    # el dato de entrada y detectar proyectos con una ubicación no
    # reconocida (se cargan igual, pero sin poder resolver municipio).
    "UBICACIONES_DISPONIBLES": [
        "Bogotá", "Chía", "Ciudadela Maiporé", "Ciudadela calle 80",
        "Girardot", "Ricaute", "Tocancipá", "Ubate",
    ],

    # `ubicacion` del proyecto -> municipio real, para poder reutilizar
    # los topes VIS/VIP y la cobertura de subsidio (que comparan contra
    # nombre de municipio). Algunas ubicaciones son desarrollos dentro de
    # un municipio, no el municipio en sí (ej. "Ciudadela Maiporé").
    "UBICACION_A_MUNICIPIO": {
        "bogotá": "bogota",
        "chía": "chia",
        "ciudadela maiporé": "soacha",
        "ciudadela calle 80": "bogota",
        "girardot": "girardot",
        "ricaute": "ricaurte",
        "tocancipá": "tocancipa",
        "ubate": "ubate",
    },

    # Proyectos excluidos del matching por muestra histórica muy chica
    # (decisión #16, plan.md §5.3) o por ser un agregado y no un proyecto
    # real (decisión #17, la fila "Total"). Comparación case-insensitive.
    "PROYECTOS_EXCLUIDOS_MATCHING": ["abeto", "vibonce", "total"],

    # Cuando un proyecto tiene varias tipologías asequibles para el lead,
    # ¿cuál se recomienda? "mas_cara_asequible" = la mejor opción real que
    # el lead sí puede pagar (sugerido en propuesta.md). Alternativa:
    # "todas_asequibles" (devuelve una entrada por tipología asequible).
    "ESTRATEGIA_SELECCION_TIPOLOGIA": "mas_cara_asequible",

    # ==================================================================
    # Pesos de afinidad histórica (matching_historico) por dimensión de
    # `buyerPersona`. PENDIENTES DE VALIDAR CON NEGOCIO (plan.md §5.3 /
    # §10) — valores iniciales razonables, 100% ajustables aquí sin tocar
    # scoring.py. No es necesario que sumen 1: se normalizan por la suma
    # de los pesos de las dimensiones que sí se puedan calcular para un
    # lead+proyecto dado (si falta el dato del lead, o el lead no cae en
    # ningún bucket de esa dimensión para ese proyecto, la dimensión se
    # excluye del promedio en vez de puntuar 0 — no es un error, ver
    # plan.md §5.3).
    # ------------------------------------------------------------------
    # Fase 1 (equivalente al modelo anterior, migrado a buckets):
    #   salario, edad, seg_empresa
    # Fase 2 (nuevas, sin costo adicional de captura):
    #   afiliacion, familia (heurístico), pac, estrato, ubicacion
    # ==================================================================
    "BUYER_PERSONA_WEIGHTS": {
        "salario": 30,
        "edad": 15,
        "seg_empresa": 10,
        "afiliacion": 15,
        "familia": 5,     # heurístico a partir de personas_a_cargo/cabeza_de_hogar, validar con negocio
        "pac": 10,
        "estrato": 5,     # requiere `estrato` en el lead (extra field); si no viene, se excluye
        "ubicacion": 10,  # usa `departamento` del buyerPersona vs. zona_preferida del lead
    },

    # Mapeo heurístico tipo_empresa del lead (Micro/Medianas/Top, catálogo
    # viejo) -> categoría de `seg_empresas` del buyerPersona (taxonomía de
    # Colsubsidio). AJUSTAR cuando negocio confirme la equivalencia real.
    "MAPEO_TIPO_EMPRESA_A_SEG_EMPRESA": {
        "micro": "Micro Transaccional",
        "medianas": "Medianas",
        "top": "Emp Top",
    },

    # Texto de bucket de personas a cargo (buyerPersona.pac) por conteo
    # numérico. Buckets de 6+ no siempre existen en todos los proyectos;
    # si no existe para un proyecto puntual, esa dimensión no suma ahí.
    "PAC_NUMERO_A_TEXTO": {
        0: "Cero", 1: "Uno", 2: "Dos", 3: "Tres",
        4: "Cuatro", 5: "Cinco", 6: "Seis", 7: "Siete", 8: "Ocho",
    },

    # ==================================================================
    # Fase 2 — ETL de compradores (OBSOLETO, ver plan.md §5.1 / Fase 2 del
    # checklist). Se deja sin borrar por ahora; limpieza es un pendiente
    # separado del checklist (Fase 3), no forma parte de este cambio.
    # ==================================================================
}