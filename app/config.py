"""
Parámetros de negocio — Motor de Perfilamiento (Colsubsidio).

Este archivo NO contiene lógica, solo constantes. Cualquier cambio normativo
o de negocio se ajusta AQUÍ. Ver `plan.md` sección 8 para el historial de
decisiones que originaron cada bloque.
"""

CONFIG = {
    # ==================================================================
    # Generales
    # ==================================================================
    "SMMLV_2026": 1_750_905,
    "TOPE_INGRESOS_SMMLV": 4,  # límite superior para calificar a subsidio de vivienda nueva
    "LIMITE_CUOTA_INGRESO": 0.40,  # Regla del 40% (Ley de Vivienda)
    "PORCENTAJE_CUOTA_INICIAL_REQUERIDO": 0.30,

    # ==================================================================
    # Matriz de subsidio por rango de ingresos (en SMMLV)
    # ------------------------------------------------------------------
    # CORREGIDO (Fase 3): se pasó de rangos [min, max) a un límite superior
    # (max_smmlv) evaluado en orden con "<=", así el borde queda inclusivo
    # tal como pide el negocio ("0 a 2 SMMLV" incluye el 2 exacto).
    # Se recorre en orden y se aplica el primer rango cuyo "max_smmlv" sea
    # mayor o igual al ingreso. Si no hay coincidencia (ingreso > último
    # max_smmlv), el subsidio es 0.
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
    # ==================================================================
    "VIS_TOPE_SMMLV_PRINCIPAL": 150,  # municipios principales (Bogotá, etc.)
    "VIS_TOPE_SMMLV_OTROS": 135,      # resto de municipios
    "VIP_TOPE_SMMLV": 90,

    "MUNICIPIOS_PRINCIPALES": [
        "bogota", "soacha", "chia", "cota", "girardot",
    ],

    # ==================================================================
    # Cobertura geográfica del subsidio Colsubsidio (Bogotá y Cundinamarca)
    # ==================================================================
    "ZONAS_COBERTURA_SUBSIDIO": [
        "bogota", "soacha", "chia", "cota", "girardot",
        "cundinamarca", "zipaquira", "facatativa", "mosquera", "madrid",
        "funza", "cajica", "fusagasuga",
    ],

    # ==================================================================
    # Subsidio concurrente "Mi Casa Ya" (informativo)
    # ==================================================================
    "MI_CASA_YA_TOPE_INGRESOS_SMMLV": 2,
    "MI_CASA_YA_SUBSIDIO_ADICIONAL_SMMLV": 20,

# ==================================================================
    # Subsidio Concurrente por grupo SISBEN (RN — tabla oficial recibida)
    # ------------------------------------------------------------------
    # PENDIENTE DE NEGOCIO: falta el campo del lead que indique zona
    # urbana/rural (no viene hoy en el JSON de entrada). Mientras tanto,
    # scoring.py debe tratar todo lead como "urbana" por defecto (ajustar
    # aquí cuando se agregue el campo real, ej. lead["zona_tipo"]).
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
    # (Básico / Medio / Alto / Joven), según ingresos, personas a cargo y edad
    # ==================================================================
    "SEGMENTACION_CAJA_BASICO_MAX_SMMLV": 1.44,
    "SEGMENTACION_CAJA_MEDIO_MAX_SMMLV": 20,
    "SEGMENTACION_CAJA_JOVEN_EDAD_MAX": 39,

    # ==================================================================
    # Pesos de scoring (0-100). El score SIEMPRE se expone como número;
    # "prioridad" es solo una etiqueta derivada de estos puntos + el
    # override de RN-04 (ver reglas de scoring, Fase 6).
    # ------------------------------------------------------------------
    # `no_afiliado_penalizacion` es negativo a propósito: aplica la regla
    # 90/10 activamente restando puntos, no solo dejando de sumar el bono
    # de `afiliado`.
    # ==================================================================
    "SCORING_WEIGHTS": {
        "afiliado": 25,
        "no_afiliado_penalizacion": -10,
        "condicion_especial": 10,
        "cesantias": 8,          # cesantías inmovilizadas puntúan más que ahorro simple
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
        "IND_AFILIADO": "afiliado",
        "COD_CATEGORIA": "categoria",
        "AFIL_ANTIGUEDAD_MESES": "antiguedad_meses",
        "TIPO_COTIZANTE": "tipo_cotizante",
        "NUM_PERSONAS_A_CARGO": "personas_a_cargo",
    },

    # ==================================================================
    # Fase 1/2 — capa de datos: proyectos y perfiles de compradores
    # ==================================================================
    "RUTA_CSV_PROYECTOS_PERFIL": "data/perfiles_proyectos.csv",

    # ==================================================================
    # Fase 2 — ETL de compradores
    # ==================================================================
    "RUTA_CSV_COMPRADORES_CRUDO": "data/compradores_crudo.csv",
    "FACTOR_CORRECCION_VALOR_VIVIENDA": 1000,  # ⚠️ validar con datos reales
    "ETL_EXCLUIR_DESISTIDOS": True,
    "MUNICIPIOS_SUR": ["soacha", "ricaurte", "girardot", "fusagasuga"],
    "MUNICIPIOS_NORTE": ["chia", "cota", "cajica", "zipaquira"],
    "DIMENSIONES_PERFIL_COMPRADORES": [
        "afiliado", "categoria", "rango_salarial", "segmento_familiar", "piramide_empresa",
    ],
}