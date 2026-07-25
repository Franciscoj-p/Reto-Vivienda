# Reglas de negocio del Motor de Perfilamiento

Este documento explica **cada regla que aplica el sistema**, dónde vive en el código,
cómo decide, y por qué se decidió así. Es el puente entre la regulación/negocio real
y su traducción a código — pensado para explicar el sistema en la demo sin tener que
leer el código fuente.

Todas las reglas son auditables por diseño (RNF-02): ninguna decisión del motor es una
caja negra — cada resultado (`puede_comprar`, `aplica_subsidio`, `prioridad`, etc.) viene
acompañado de las condiciones exactas que lo produjeron.

---

## 1. Reglas duras de rechazo (`app/reglas.py`)

Bloquean `puede_comprar`. Si **cualquiera** de estas falla, el lead no es viable para
compra, sin importar su score ni su presupuesto. Viven en `_REGLAS_RECHAZO`, una lista
de funciones evaluada en orden — agregar una regla nueva es solo agregar una función a
esa lista, no tocar el resto del flujo.

| Regla | Función | Cómo decide | Por qué |
|---|---|---|---|
| Ya es propietario | `_regla_propietario_vivienda` | `lead.propietario_vivienda == True` → rechazo | Requisito legal: el subsidio de vivienda es para quien no tiene vivienda propia |
| Antigüedad de afiliación insuficiente | `_regla_antiguedad_afiliacion` | Si `afiliado == True`: `antiguedad_meses` debe ser ≥ el mínimo según `tipo_cotizante` (`CONFIG["ANTIGUEDAD_MINIMA_MESES_POR_TIPO"]`, hoy 6 meses para dependiente/independiente/pensionado). Si no está afiliado, esta regla no aplica (no bloquea) | Requisito de Colsubsidio: un afiliado recién ingresado no puede acceder al subsidio de inmediato |
| Subsidio de vivienda previo | `_regla_beneficiario_subsidio_previo` | `subsidio_previo == True` **y** `subsidio_previo_fue_arrendamiento == False` → rechazo. Si el subsidio previo fue de arrendamiento, **no** rechaza (excepción) | Regla nacional: no se puede recibir subsidio de vivienda dos veces, salvo que el anterior haya sido de arrendamiento (no es el mismo beneficio) |
| Ingresos insuficientes | `_regla_ingresos_insuficientes` | `cuota_maxima = ingresos_mensuales * 0.40` (`LIMITE_CUOTA_INGRESO`); si da `<= 0` → rechazo | Sin ingresos no hay forma de calcular capacidad de endeudamiento |

---

## 2. Elegibilidad y monto del subsidio de vivienda (Colsubsidio)

Función `_evaluar_aplicacion_subsidio`. El subsidio (`aplica_subsidio`, `subsidio_estimado`)
es **independiente** de `puede_comprar` — un lead puede comprar sin ayuda de la caja si no
califica al subsidio pero sí tiene ingresos y no está en las reglas duras de rechazo.

Se evalúan **todas** las condiciones (no se detiene en la primera que falla), para que
`condiciones_subsidio` sea siempre auditable:

| Condición | Cómo se calcula | Fuente |
|---|---|---|
| `dentro_de_tope_ingresos` | `ingresos_en_smmlv <= CONFIG["TOPE_INGRESOS_SMMLV"]` (hoy 4 SMMLV) | Tope nacional para calificar a subsidio de vivienda nueva |
| `sin_rechazo_por_reglas_duras` | `len(motivos_rechazo) == 0` | Si no puede comprar, tampoco puede recibir subsidio |
| `zona_con_cobertura_subsidio` | `_zona_tiene_cobertura_subsidio(zona)` — la zona/ubicación del lead cae en `CONFIG["ZONAS_COBERTURA_SUBSIDIO"]` (Bogotá + Cundinamarca) | Colsubsidio solo opera subsidio de vivienda en esa región |
| `vivienda_dentro_de_tope_vis_vip` | `_valor_vivienda_dentro_de_tope` — el valor de vivienda deseado cae dentro del tope VIS (135/150 SMMLV según municipio) o VIP (90 SMMLV) | El subsidio solo aplica a vivienda de interés social/prioritario, no a cualquier vivienda |

Si las 4 son verdaderas, el **monto** sale de `_calcular_subsidio_por_ingresos`
(`CONFIG["MATRIZ_SUBSIDIOS"]`): rangos de ingreso en SMMLV evaluados en orden, con el
límite superior de cada rango inclusive (`<=`). Hoy: 0-2 SMMLV → 30 SMMLV de subsidio;
2-4 SMMLV → 20 SMMLV; por encima de 4 SMMLV no hay coincidencia (subsidio 0, ya
descalificado de todas formas por el tope de ingresos).

**Campo separado `descalifica_subsidio_por_techo_ingresos`**: existe aparte de
`puede_comprar` porque son cosas distintas — alguien puede comprar vivienda (tiene
ingresos, no tiene rechazo duro) pero no calificar al subsidio por ganar más de 4 SMMLV.
Sin este campo, un asesor no podría distinguir "no puede comprar" de "puede comprar pero
sin ayuda de la caja".

### Tope VIS/VIP por ubicación (`_valor_vivienda_dentro_de_tope`)

- VIS en municipio principal (Bogotá, Soacha, Chía, Cota, Girardot): tope 150 SMMLV.
- VIS en otros municipios: tope 135 SMMLV.
- VIP: tope 90 SMMLV (**pendiente de conectar** — hoy la función siempre compara contra
  el tope VIS, nunca contra el de VIP, porque no había un campo confiable de tipo de
  proyecto; con `tipo_proyecto` ya disponible en `proyectos.json`, falta ajustar esta
  función para usar `VIP_TOPE_SMMLV` cuando el proyecto es VIP).
- Si no se conoce el valor de vivienda deseado o la zona, no se bloquea por este criterio
  (se asume que sí aplica, hasta que haya más información).

---

## 3. Programas concurrentes (informativos, no bloquean nada)

| Programa | Función | Cómo decide | Nota |
|---|---|---|---|
| Mi Casa Ya | `_evaluar_subsidio_concurrente_mi_casa_ya` | `ingresos_en_smmlv < 2` → subsidio adicional de 20 SMMLV | Es un subsidio del gobierno nacional, no de Colsubsidio — se suma, no reemplaza |
| Subsidio Concurrente SISBEN | `_califica_sisben_subsidio` (en `scoring.py`) | Grupo SISBEN del lead comparado contra `CONFIG["SISBEN_ORDEN_GRUPOS"]` (lista ordenada A1→D21, evita el bug de comparar "C14" vs "C7" como texto). Zona urbana: hasta C7 → 30 SMMLV, hasta D11 → 20 SMMLV. Zona rural: hasta C14 → 30 SMMLV, hasta D20 → 20 SMMLV | **Pendiente real**: el lead no trae campo de zona urbana/rural, así que se usa `CONFIG["SISBEN_ZONA_DEFAULT"] = "urbana"` como fallback — subvalora a leads rurales que calificarían en el tramo más alto (C15-D20) |
| Subsidio de arrendamiento | `_evaluar_subsidio_arrendamiento` | Si el cierre financiero **no** es viable hoy, se sugiere como ruta alterna: 0.6 SMMLV/mes × 24 meses mientras el lead ahorra | Da una alternativa concreta a un lead que hoy no puede comprar, en vez de solo decirle "no" |

---

## 4. Segmentación de Caja (`_calcular_segmentacion_caja`)

Clasifica al lead en `Basico` / `Medio` / `Alto` / `Joven`. **No son rangos que se pisan** —
hay un desempate explícito confirmado con negocio:

1. **Primero se evalúa Joven**: `edad < 39` **y** sin personas a cargo registradas
   (`personas_a_cargo <= 0`). Si cumple ambas, el segmento es `Joven`, sin importar el
   ingreso.
2. **Si no es Joven** (por edad o porque sí tiene personas a cargo), el segmento se
   decide **solo por ingresos**: `<= 1.44 SMMLV` → Básico; `<= 20 SMMLV` → Medio;
   `> 20 SMMLV` → Alto.

**Supuesto sin confirmar del todo con negocio** (documentado en el código): la tabla
original menciona "grupo familiar" como requisito de Básico/Medio, pero se interpretó
que las personas a cargo son *solo* el desempate entre Joven y el resto, no un requisito
adicional para calificar a Básico/Medio. Esto afecta en la práctica a leads de 39+ años
sin personas a cargo — caen en Básico/Medio/Alto por ingreso igual, aunque no tengan
grupo familiar.

---

## 5. Cierre financiero (`_calcular_cierre_financiero`, informativo)

`ahorro_disponible = finanzas.cesantias + finanzas.ahorros + subsidio_estimado`.
`cuota_inicial_requerida = precio_referencia_vivienda * 0.30` (`PORCENTAJE_CUOTA_INICIAL_REQUERIDO`).
`cierre_viable = ahorro_disponible >= cuota_inicial_requerida`.

No bloquea `puede_comprar` — es información para que el asesor sepa si el lead ya tiene
la cuota inicial cubierta o necesita una ruta alterna (arrendamiento, ahorro programado).

**En `match_proyectos` (Fase 5.4) este cálculo se hace por proyecto candidato**, no
contra un precio de referencia único del portafolio — antes comparaba contra el promedio
de precios VIS de todo el catálogo, lo cual no reflejaba la realidad de un proyecto
específico.

---

## 6. Score de prioridad comercial (`app/scoring.py` → `calcular_score`)

Suma de factores independientes (`CONFIG["SCORING_WEIGHTS"]`), cada uno documentado por
separado para que el score nunca sea una caja negra:

| Factor | Peso | Cómo decide |
|---|---|---|
| `afiliado` | +25 / **-10** | Afiliado suma 25. No afiliado **resta** 10 activamente (`no_afiliado_penalizacion`) — es la regla 90/10 aplicada en ambos sentidos, no solo "dejar de sumar" |
| `cierre_financiero_viable` | +10 | Si `cierre_financiero.cierre_viable == True` |
| `matching_historico` | hasta +20 | Afinidad del lead con el `buyerPersona` histórico del proyecto (**pendiente de rediseño**, ver sección 7) |
| `cesantias` | +8 | Si `finanzas.cesantias > 0` (separado de ahorros porque cesantías inmovilizadas puntúan más — son un ahorro forzoso, más confiable) |
| `ahorros` | +4 | Si `finanzas.ahorros > 0` |
| `condicion_especial` | +10 | Si `cabeza_de_hogar` **o** `discapacidad_hogar` **o** `mayor_65_anos` (los tres viven en `condiciones_especiales`, son datos explícitos del lead, no calculados de `edad`) |
| `grupo_sisben` | +8 | Si el grupo SISBEN del lead califica al subsidio concurrente (sección 3) |
| `credito_preaprobado` | +10 | Si `finanzas.credito_preaprobado == True` |
| `origen_organico` | +5 | Si `origen == "organico"` |

**Prioridad** (`ALTA` / `MEDIA` / `BAJA`):
- Si `puede_comprar == False` → siempre `BAJA`, sin importar el score.
- Si no, se compara `score_total` contra `CONFIG["SCORE_THRESHOLDS"]` (≥70 ALTA, ≥40 MEDIA, si no BAJA).
- **Override RN-04**: si el lead puede comprar, tiene crédito preaprobado, califica al
  subsidio, **y** su ahorro disponible cubre el precio de referencia completo de vivienda
  (no solo la cuota inicial) → `prioridad` se fuerza a `ALTA`, aunque el score numérico
  no llegue a 70. El `score_total` expuesto no se altera, solo la etiqueta de prioridad.
  Esto existe para que un lead financieramente resuelto no quede subestimado por no
  acumular puntos en dimensiones blandas (origen, matching histórico, etc.).

---

## 7. Matching de proyectos (`match_proyectos`)

Dos filtros **independientes**, en orden:

1. **Filtro VIS/No VIS (exclusión total, decidido)**: si el precio de la tipología está
   fuera del tope VIS/VIP del municipio del proyecto, esa tipología **se excluye por
   completo** del matching — no se recomienda, no aparece en la lista. No es solo
   informativo: se decidió explícitamente que un lead no debe ver opciones fuera de
   fondo.
2. **Filtro de asequibilidad**: `precio_tipologia <= ahorro_disponible + subsidio +
   (cuota_maxima_mensual * 120)` (120 meses ≈ crédito a 10 años, estimación simple). Si
   no alcanza, esa tipología tampoco se muestra.

Lo que **sí pasa ambos filtros** se ordena por `match_score` — la afinidad histórica con
el `buyerPersona` del proyecto, más un bono si la zona preferida del lead coincide con la
ubicación del proyecto.

**Principio de diseño explícito**: la afinidad histórica (sección 8) es **solo una señal
de orden/score**, nunca un filtro de exclusión. Un lead que puede pagar una tipología no
se le oculta solo porque "no se parece" al comprador típico de ese proyecto — eso
perpetuaría un patrón histórico como si fuera un límite real, y le quitaría opciones
válidas a un lead atípico pero calificado. La única puerta de exclusión por perfil es la
financiera (asequibilidad + tope VIS/VIP), completamente independiente de la afinidad.

---

## 8. Afinidad histórica / `matching_historico` — EN REDISEÑO (Fase 5.3)

**Estado actual (a reemplazar)**: distancia numérica normalizada entre el lead y un
*promedio* por proyecto (`ingreso_promedio_comprador`, `edad_promedio_comprador`,
`tipo_empresa_predominante`). Ya no será así.

**Rediseño aprobado** (`propuesta.md`): en vez de comparar contra un promedio, se ubica
al lead en el mismo bucket categórico que usa `buyerPersona` de cada proyecto
(distribución porcentual real de compradores históricos), y se lee directamente qué
porcentaje de esos compradores comparte esa categoría con el lead. Elimina las restas
normalizadas arbitrarias (ej. dividir diferencia de edad entre 20) del modelo actual.

Dimensiones planeadas: afiliación, salario, edad, segmento (Básico/Medio/Alto/Joven),
composición familiar, personas a cargo, estrato, segmento de empresa, entidad financiera,
ubicación. Pesos exactos por dimensión: pendientes de definir con negocio.

**Detalle técnico real que apareció al revisar los datos**: los buckets de `salario` no
son un catálogo cerrado — cada proyecto puede traer buckets distintos (ej. "Hasta 2 smlv"
/ "Mas de 2 smlv" en unos proyectos, "Entre 4 y 6 smlv" en otros). La solución es parsear
el texto del bucket a un rango numérico en tiempo real (no una lista fija de categorías),
y ubicar ahí el ingreso del lead. Si el lead no cae en ningún bucket de un proyecto
puntual, esa dimensión simplemente no suma para ese proyecto — no es un error.

**Exclusiones de catálogo decididas**: Abeto y Vibonce se excluyen por tener 1-2
compradores históricos (sus porcentajes son ruido estadístico, no señal real). La fila
"Total" se excluye porque es un agregado de todo el histórico, no un proyecto real
comprable.

---

## 9. Pendientes explícitos (para que nadie los dé por resueltos)

- Zona urbana/rural del lead (afecta SISBEN) — no existe el campo todavía, usa fallback "urbana".
- Tope VIP (90 SMMLV) no está conectado — la función siempre usa tope VIS.
- `tipo_proyecto` vacío en los proyectos de ejemplo vistos hasta ahora — pendiente de llenar con datos reales.
- Pesos de las dimensiones nuevas de `matching_historico` (afiliación, familia, estrato, etc.) — pendientes de definir con negocio.
- Precios de tipologías son placeholders en los datos vistos hasta ahora — pendientes de precio real.