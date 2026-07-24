"""
Parámetros de negocio — Motor de Perfilamiento (Colsubsidio).

Este archivo NO contiene lógica, solo constantes. Cualquier cambio normativo
(nuevo SMMLV, nuevos topes, nuevos rangos de subsidio, etc.) se ajusta AQUÍ,
nunca dentro de app/reglas.py.

"""

CONFIG = {
    # ------------------------------------------------------------------
    # Valores generales 
    # ------------------------------------------------------------------
    "SMMLV_2026": 1_750_905,
    "TOPE_INGRESOS_SMMLV": 4,  # límite superior para calificar a subsidio de vivienda nueva
    "LIMITE_CUOTA_INGRESO": 0.40,  # Regla del 40% (Ley de Vivienda)
    "PORCENTAJE_CUOTA_INICIAL_REQUERIDO": 0.30,

    # Matriz de subsidio por rango de ingresos (en SMMLV).
    # Se recorre en orden y se aplica el primer rango que coincida.
    "MATRIZ_SUBSIDIOS": [
        {"min_smmlv": 0, "max_smmlv": 2, "subsidio_smmlv": 30},   # $52.527.150
        {"min_smmlv": 2, "max_smmlv": 4, "subsidio_smmlv": 20},   # $35.018.100
        # Sobre 4 SMMLV no hay coincidencia -> _calcular_subsidio devuelve 0
    ],

    # ------------------------------------------------------------------
    # Antigüedad de afiliación 
    # Ahora es un
    # diccionario por tipo de cotizante para poder diferenciar a futuro
    # (p. ej. si algún día independientes requieren 12 meses en vez de 6).
    # Todos parten en 6 porque hoy la regla es la misma para los tres casos.
    # ------------------------------------------------------------------
    "ANTIGUEDAD_MINIMA_MESES_POR_TIPO": { 
        "dependiente": 6,
        "independiente": 6,
        "pensionado": 6,
    },
    "ANTIGUEDAD_MINIMA_MESES_DEFAULT": 6,  # se usa si no se informa tipo_cotizante

    # ------------------------------------------------------------------
    # Topes de valor de vivienda por tipo (en SMMLV)
    # ------------------------------------------------------------------
    "VIS_TOPE_SMMLV_PRINCIPAL": 150,  # municipios principales (Bogotá, etc.)
    "VIS_TOPE_SMMLV_OTROS": 135,      # resto de municipios
    "VIP_TOPE_SMMLV": 90,

    "MUNICIPIOS_PRINCIPALES": [
        "bogota", "soacha", "chia", "cota", "girardot",
    ],

    # ------------------------------------------------------------------
    # Cobertura geográfica del subsidio Colsubsidio
    # El subsidio solo aplica para proyectos/zonas de Bogotá y Cundinamarca.
    # Se compara contra `zona_preferida` del lead (substring, case-insensitive).
    # Ajusta esta lista libremente si se habilita otra zona.
    # ------------------------------------------------------------------
    "ZONAS_COBERTURA_SUBSIDIO": [
        "bogota", "soacha", "chia", "cota", "girardot",
        "cundinamarca", "zipaquira", "facatativa", "mosquera", "madrid",
        "funza", "cajica", "fusagasuga",
    ],

    # ------------------------------------------------------------------
    # Subsidio concurrente "Mi Casa Ya"
    # Informativo: si el hogar gana menos de 2 SMMLV, se puede sumar hasta
    # este monto adicional (en SMMLV) al subsidio de caja.
    # ------------------------------------------------------------------
    "MI_CASA_YA_TOPE_INGRESOS_SMMLV": 2,     
    "MI_CASA_YA_SUBSIDIO_ADICIONAL_SMMLV": 20, 

    # ------------------------------------------------------------------
    # Subsidio de arrendamiento (ruta alterna si no hay cierre financiero)
    # ------------------------------------------------------------------
    "SUBSIDIO_ARRENDAMIENTO_SMMLV_MENSUAL": 0.6, 
    "SUBSIDIO_ARRENDAMIENTO_MESES": 24,          

    # ------------------------------------------------------------------
    # Scoring (ya existía, sin cambios funcionales aquí)
    # ------------------------------------------------------------------
    "SCORING_WEIGHTS": {
        "afiliado": 30,
        "cierre_financiero_viable": 25,
        "matching_historico": 20,
        "ahorro_previo": 10,
        "condicion_especial": 10,
        "origen_organico": 5,
    },
    "SCORE_THRESHOLDS": {
        "ALTA": 70,
        "MEDIA": 40,
    },
}