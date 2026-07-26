# Reglas de Negocio del Motor de Perfilamiento

Este documento explica **cada regla que aplica el sistema**, dónde vive en el código, cómo decide y por qué se diseñó así.

---

## 1. Reglas Duras de Rechazo (`app/reglas.py`)

Bloquean `puede_comprar`. Si **cualquiera** de estas falla, el lead se clasifica como `viable: "NO"`.

| Regla | Función | Cómo decide | Razón |
|---|---|---|---|
| Ya es propietario | `_regla_propietario_vivienda` | `lead.propietario_vivienda == True` → rechazo | Requisito legal del subsidio VIS/VIP |
| Antigüedad de afiliación | `_regla_antiguedad_afiliacion` | Si `afiliado == True`, `antiguedad_meses` debe ser ≥ mínimo según `tipo_cotizante` (6 meses) | Requisito de caja de compensación |
| Subsidio de vivienda previo | `_regla_beneficiario_subsidio_previo` | `subsidio_previo == True` **y** `subsidio_previo_fue_arrendamiento == False` → rechazo | Excepción legal de arrendamiento permitida |
| Ingresos insuficientes | `_regla_ingresos_insuficientes` | Capacidad máxima mensual `ingresos_mensuales * 0.40 <= 0` → rechazo | Sin ingresos no hay capacidad de crédito |

---

## 2. Elegibilidad y Monto de Subsidio (`app/reglas.py`)

Se evalúan **todas** las condiciones de elegibilidad para garantizar explicabilidad total (RNF-02):

- `dentro_de_tope_ingresos`: `ingresos_en_smmlv <= 4 SMMLV`.
- `sin_rechazo_por_reglas_duras`: `motivos_rechazo` vacío.
- `zona_con_cobertura_subsidio`: Cobertura en Bogotá y Cundinamarca (`ZONAS_COBERTURA_SUBSIDIO`).
- `vivienda_dentro_de_tope_vis_vip`: `_valor_vivienda_dentro_de_tope` — evalúa según tipo:
  - VIS Principal (Bogotá, Soacha, Chía, Cota, Girardot): 150 SMMLV.
  - VIS Otros: 135 SMMLV.
  - VIP: 90 SMMLV (`VIP_TOPE_SMMLV`).

**Monto de Subsidio:**
- 0 a 2 SMMLV → 30 SMMLV ($52.527.150 COP).
- 2 a 4 SMMLV → 20 SMMLV ($35.018.100 COP).
- > 4 SMMLV → $0 COP (descalificado por techo de ingresos).

---

## 3. Subsidios Concurrentes y Alternos

- **Mi Casa Ya:** Si `ingresos_en_smmlv < 2`, informa disponibilidad de 20 SMMLV adicionales del Gobierno Nacional.
- **Subsidio Concurrente SISBEN:** Evalúa `grupo_sisben` contra matriz `SISBEN_SUBSIDIO_MATRIZ` según la `zona` (`"urbana"` o `"rural"`) asignada o provista.
- **Subsidio de Arrendamiento:** Sugerido (0.6 SMMLV/mes por 24 meses) cuando el cliente no logra el cierre financiero actual.

---

## 4. Segmentación de Caja (`app/reglas.py`)

- **Joven:** `edad < 39` **y** `personas_a_cargo <= 0`.
- **Básico / Medio / Alto:** Si no es Joven, clasificado según ingresos (≤ 1.44 SMMLV → Básico, ≤ 20 SMMLV → Medio, > 20 SMMLV → Alto).

---

## 5. Score de Prioridad Comercial (`app/scoring.py`)

Suma de ponderaciones configurables (`SCORING_WEIGHTS`):
- `afiliado` (+25 / -10 penalización)
- `credito_preaprobado` (+10)
- `cierre_financiero_viable` (+10)
- `condicion_especial` (+10)
- `grupo_sisben` (+8)
- `cesantias` (+8)
- `ahorros` (+4)
- `origen_organico` (+5)
- `matching_historico` (hasta +20 por afinidad a `buyerPersona`)

**Override RN-04:** Si el lead es viable, tiene crédito preaprobado, califica a subsidio y su ahorro total cubre el 100% del valor del inmueble → Prioridad forzada a **`ALTA`**.

---

## 5. Cierre Financiero Detallado por Proyecto (`calcular_cierre_financiero_detallado`)

Para cada tipología de proyecto, el cierre financiero se divide en dos fases matemáticas independientes:

### Etapa 1: Cuota Inicial (30% antes de la entrega)
- **Aportes totales:** `cesantias + ahorros + subsidio_caja + (subsidio_mi_casa_ya if disponible else 0)`.
- **`cuota_inicial_30_percent`:** `round(precio_tipologia * 0.30)`.
- **`saldo_faltante`:** `max(0, cuota_inicial_30_percent - total_aportes)`.
- Si `saldo_faltante > 0`, se difiere entre `plazo_entrega_meses` (ej. 24 meses):
  $$\text{cuota\_mensual\_inicial\_estimada} = \text{round}\left(\frac{\text{saldo\_faltante}}{\text{plazo\_entrega\_meses}}\right)$$
- `cumple_cuota_inicial`: `true` si la cuota inicial está 100% cubierta o si `cuota_mensual_inicial_estimada <= cuota_maxima_permitida` (40% del salario).

### Etapa 2: Crédito Hipotecario (70% después de la entrega)
- **`monto_a_financiar`:** `round(precio_tipologia * 0.70)`.
- Amortización mediante cuota fija fija mensual (PMT) a 20 años (240 meses) al 12% E.A. (`TASA_INTERES_CREDITO_EA`):
  $$\text{cuota\_mensual\_credito\_estimada} = \text{PMT}(\text{monto\_a\_financiar}, \text{plazo}=20, \text{tasa}=12\% \text{ EA})$$
- `cumple_limite_cuota`: `true` si `cuota_mensual_credito_estimada <= cuota_maxima_permitida` (40% del salario).

**Viabilidad total del proyecto (`cierre_viable`):**
$$\text{cierre\_viable} = \text{cumple\_cuota\_inicial} \quad \mathbf{AND} \quad \text{cumple\_limite\_cuota}$$

Toda esta desglose matemático se entrega estructurada en la respuesta del proyecto para que el asesor comercial en Salesforce/CRM vea exactamente los números sobre los cuales se calculó la viabilidad.

---

## 6. Recomendación de Proyectos e Interés Directo (`app/scoring.py`)

- **Filtro VIS/VIP y Asequibilidad:** Exclusión estricta por tipología.
- **`brochure_url`:** Propagación del enlace PDF comercial por cada proyecto viable.
- **Evaluación de `proyecto_interes`:**
  - Si el usuario declara un `proyecto_interes`, el motor genera un objeto explicativo `evaluacion_proyecto_interes`.
  - Si NO es viable, detalla el motivo específico (falta de presupuesto, fuera de tope legal, fuera de catálogo).
  - Si SÍ es viable, el proyecto se ubica automáticamente en la **posición #1 de las recomendaciones (`matching_projects[0]`)**.