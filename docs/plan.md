# Plan — Motor de Perfilamiento (Asesor Digital de Vivienda, Colsubsidio)

> Este documento es la fuente de verdad del proyecto. Antes de retomar el trabajo
> en cualquier sesión nueva, léelo completo: contiene el contexto de negocio, las
> decisiones ya tomadas (y por qué), el diseño de datos/arquitectura acordado, y
> el checklist de fases. Marca cada casilla `[x]` cuando la fase quede completa
> y agrega la fecha/commit si aplica.
>
> **Documento complementario:** `REGLAS_DE_NEGOCIO.md` — explica cada regla ya
> implementada (dónde vive en el código, cómo decide, por qué), pensado para
> explicar el sistema en la demo. Este `plan.md` es la bitácora de decisiones y
> checklist; `REGLAS_DE_NEGOCIO.md` es la referencia funcional.

---

## 1. Contexto del proyecto

Motor de perfilamiento para el Asesor Digital de Vivienda de Colsubsidio. Recibe
un lead (afiliado o no), determina si califica legalmente para comprar vivienda
y/o recibir subsidio, calcula un score de prioridad comercial, y recomienda
proyectos del catálogo VIS/VIP.

**Documentos fuente originales:**
- `Requerimientos` (RF-01 a RF-12, RN-01 a RN-04, RNF-01 a RNF-04)
- `API.md` (contrato de API, arquitectura de módulos: `api/`, `motor.py`,
  `reglas.py`, `scoring.py`, `catalogo.py`, `config.py`)
- `REGLAS_DE_NEGOCIO.md` (nuevo — referencia funcional de cada regla)

**Restricciones de negocio que gobiernan todo el diseño:**
- RN-01 / RNF: Regla del 40% — ninguna recomendación puede exceder el 40% de
  los ingresos del hogar en cuota mensual.
- RN-02: No se le pregunta al usuario nada que Colsubsidio ya sepa (afiliados).
- RN-03: El portafolio VIS concentra el 80% de la oferta — se prioriza.
- RN-04: Prioridad Alta = crédito pre-aprobado + subsidio aplicable + cierre
  financiero cubre el valor total de la vivienda (esto es un **override**, no
  solo una suma de puntos — ver sección 4).
- RNF-02: Explicabilidad — nada de caja negra, todo factor debe quedar
  auditable en la respuesta.
- RNF-03: Latencia — respuesta en menos de 2 segundos (condiciona decisiones
  de arquitectura de datos, ver sección 5).

---

## 2. Modelo de datos del Lead (JSON de entrada — versión vigente, implementada)

```json
{
  "id_usuario": "1018300400",
  "nombre": "Diana Martínez",
  "afiliado": true,
  "categoria": "B",
  "antiguedad_meses": 24,
  "tipo_cotizante": "dependiente",
  "ingresos_mensuales": 2900000,
  "grupo_sisben": "C2",
  "edad": 31,
  "personas_a_cargo": 2,
  "condiciones_especiales": {
    "cabeza_de_hogar": true,
    "discapacidad_hogar": false,
    "mayor_65_anos": false
  },
  "propietario_vivienda": false,
  "subsidio_previo": false,
  "subsidio_previo_fue_arrendamiento": false,
  "finanzas": {
    "cesantias": 3000000,
    "ahorros": 5000000,
    "credito_preaprobado": true
  },
  "tipo_empresa": "Medianas",
  "zona_preferida": "Soacha",
  "valor_vivienda_deseada": 150000000,
  "origen": "organico"
}
```

Implementado en `app/api/schemas.py` (`LeadInput` con submodelos
`CondicionesEspeciales` y `Finanzas`). Rompe compatibilidad con el schema plano
anterior a propósito — cualquier request que mande `cabeza_de_hogar` o
`cesantias` en el nivel raíz ya no lo reconoce ahí.

**Pendiente real, sin bloquear nada:** no existe todavía un campo de zona
urbana/rural en el lead (afecta el cálculo de Subsidio Concurrente por SISBEN,
ver sección 3.5). Mientras tanto se usa un default de "urbana".

---

## 3. Reglas de negocio — estado y decisiones

### 3.1 Reglas duras de rechazo (`puede_comprar = false`) — IMPLEMENTADO

| # | Condición | Estado |
|---|---|---|
| 1 | `propietario_vivienda == true` | Vigente, sin cambios |
| 2 | `afiliado == true` y `antiguedad_meses < mínimo` (mínimo por `tipo_cotizante`, hoy 6 para los tres: dependiente/independiente/pensionado) | Vigente |
| 3 | `subsidio_previo == true` y NO `subsidio_previo_fue_arrendamiento` | Vigente (excepción de arrendamiento se conserva) |
| 4 | `ingresos_mensuales * 0.40 <= 0` | Vigente |

**Importante:** el techo de 4 SMMLV **NO** está en esta tabla — ver 3.2.

### 3.2 Elegibilidad al subsidio (NO bloquea la compra, solo el monto) — IMPLEMENTADO

`aplica_subsidio` es `true` solo si se cumplen TODAS:
1. `ingresos_en_smmlv <= TOPE_INGRESOS_SMMLV` (4 SMMLV / $7.003.620 en 2026)
2. Sin motivos de rechazo duro (sección 3.1)
3. `zona_preferida` dentro de cobertura (Bogotá y Cundinamarca)
4. `valor_vivienda_deseada` dentro del tope VIS (135–150 SMMLV según
   municipio) — si no hay dato, no bloquea

Si `aplica_subsidio == false`, se expone `subsidio_estimado = 0` y el motivo
específico en `condiciones_subsidio` (para RNF-02, explicabilidad).

**Implementado:** `descalifica_subsidio_por_techo_ingresos` (booleano, separado
de `puede_comprar`) ya se expone en la respuesta.

**Bug real detectado y aún sin corregir:** el chequeo de tope de vivienda
(`_valor_vivienda_dentro_de_tope`) siempre compara contra el tope VIS, nunca
contra el tope VIP (90 SMMLV), porque hasta esta sesión no había un campo
confiable de tipo de proyecto (VIS/VIP). Con `tipo_proyecto` ya disponible en
`proyectos.json` (sección 5), falta conectar el tope correcto según el tipo.

### 3.3 Monto del subsidio (SMMLV 2026 = $1.750.905) — IMPLEMENTADO

| Rango ingresos (SMMLV) | Subsidio |
|---|---|
| 0 ≤ ingresos < 2 SMMLV | 30 SMMLV ($52.527.150) |
| 2 ≤ ingresos < 4 SMMLV | 20 SMMLV ($35.018.100) |
| ≥ 4 SMMLV | $0 |

Corregido: `MATRIZ_SUBSIDIOS` se recorre en orden por `max_smmlv` (piso
implícito = techo del rango anterior), ya no depende de un campo `min_smmlv`
que se había quitado del formato del dato real.

### 3.4 Regla del 40% — IMPLEMENTADO

`cuota_maxima_mensual = round(ingresos_mensuales * 0.40)` — sin cambios.

### 3.5 Subsidios complementarios (informativos, no bloquean) — IMPLEMENTADO

- **Mi Casa Ya concurrente**: si `ingresos_en_smmlv < 2`, informa que puede
  sumar hasta 20 SMMLV adicionales.
- **Subsidio de arrendamiento**: si `cierre_financiero.cierre_viable == false`,
  sugiere 0.6 SMMLV/mes por 24 meses como ruta alterna de ahorro.
- **Subsidio Concurrente por SISBEN** — tabla oficial recibida y ya
  implementada:

  | Zona | Grupos SISBEN | Subsidio |
  |---|---|---|
  | Urbana | A1 – C7 | 30 SMMLV |
  | Urbana | C8 – D11 | 20 SMMLV |
  | Rural | A1 – C14 | 30 SMMLV |
  | Rural | C15 – D20 | 20 SMMLV |

  Comparación por índice de posición en una lista ordenada de grupos
  (`SISBEN_ORDEN_GRUPOS`, A1→D21), no por comparación de texto — comparar
  `"C14" < "C7"` como string da un resultado incorrecto (evaluación
  lexicográfica, no numérica).

  **Pendiente real:** el lead no trae campo de zona urbana/rural, así que se
  usa `SISBEN_ZONA_DEFAULT = "urbana"` como fallback — subvalora a leads
  rurales que calificarían en el tramo más alto (C15-D20 vs. C8-D11 urbano).

  Grupo fuera de A1-D21 o vacío → no califica, sin bloquear ninguna otra
  regla. **SISBEN y Segmentación de Caja se manejan como criterios
  independientes** (decisión tomada), no uno reemplaza al otro.

---

## 4. Sistema de score — decisiones cerradas, IMPLEMENTADO

**El score es SIEMPRE numérico (0–100)**. `prioridad` (ALTA/MEDIA/BAJA) es
solo una etiqueta derivada para UI — ningún cálculo interno (matching,
ordenamiento, overrides) se hace sobre la palabra, siempre sobre el número.

| Factor | Peso | Notas |
|---|---|---|
| `afiliado == true` suma | 25 | Regla 90/10 |
| `afiliado == false` **resta** | -10 | Penalización activa, no solo ausencia de bono — regla 90/10 en ambos sentidos |
| `condicion_especial` (cabeza hogar / discapacidad / 65+) | 10 | Los tres viven en `condiciones_especiales`, son datos explícitos del lead (ya no se calcula `mayor_65_anos` de `edad`) |
| `finanzas.cesantias` | 8 | Separado de ahorros — cesantías inmovilizadas puntúan más que ahorro voluntario |
| `finanzas.ahorros` | 4 | — |
| `grupo_sisben` | 8 | Binario: si el grupo del lead califica al Subsidio Concurrente (sección 3.5) |
| `finanzas.credito_preaprobado` | 10 | Existía en RN-04 pero nunca se había implementado en scoring |
| `matching_historico` | hasta 20 | **En rediseño** — ver sección 5.3 |
| `cierre_financiero_viable` | 10 | — |
| `origen_organico` | 5 | — |

**Override de prioridad (RN-04), implementado:** si `credito_preaprobado == true`
AND `aplica_subsidio == true` AND `cierre_financiero.ahorro_disponible` cubre el
**valor total** de la vivienda (no solo la cuota inicial) AND `puede_comprar == true`
→ `prioridad = "ALTA"` **aunque el score_total no llegue a 70**. El score
numérico se sigue exponiendo tal cual, sin alterarse; el override solo afecta
la etiqueta. Se expone `override_rn04_aplicado` (booleano) para auditar cuándo
se activó.

**Segmentación de Caja — implementada, con tie-breaker confirmado con negocio:**

| Segmento | Regla |
|---|---|
| Joven | `edad < 39` **y** sin personas a cargo registradas — tiene prioridad sobre los demás |
| Básico | (si no es Joven) ingresos ≤ 1.44 SMMLV |
| Medio | (si no es Joven) 1.44–20 SMMLV |
| Alto | (si no es Joven) > 20 SMMLV |

El desempate real (confirmado con negocio) es la presencia de personas a
cargo: decide entre Joven y el resto, no es un solape de rangos de ingreso.

**Supuesto sin confirmar del todo, documentado en el código:** la tabla
original menciona "grupo familiar" como requisito adicional de Básico/Medio,
pero se interpretó que las personas a cargo son *solo* el desempate frente a
Joven, no un requisito duro aparte. Afecta a leads de 39+ años sin personas a
cargo — caen en Básico/Medio/Alto por ingreso igual.

---

## 5. Matching — histórico y catálogo (REDISEÑO EN CURSO, Fase 5.3)

> Cambio de arquitectura grande respecto a la versión anterior de este plan:
> el catálogo deja de construirse con un ETL propio sobre una base cruda de
> compradores, porque **Colsubsidio ya entrega el perfil de comprador
> pre-calculado** en `proyectos.json`. La sección 5 anterior (ETL offline +
> CSV de perfiles agregados) queda **obsoleta y se reemplaza completa** por
> lo que sigue.

### 5.1 Fuente única del catálogo: `proyectos.json`

Cada proyecto trae:

```json
{
  "id": 12,
  "nombre": "Versalles",
  "ubicacion": "Ciudadela Maiporé",
  "tipo_proyecto": "VIS | No VIS | VIP",
  "tipologias": [
    { "nombre": "Tipo D", "precio": 150000000 },
    { "nombre": "Tipo E", "precio": 180000000 }
  ],
  "buyerPersona": {
    "afiliacion": [ { "valor": "Afiliado", "porcentaje": 71 }, ... ],
    "genero": [ ... ],
    "salario": [ ... ],
    "edad": [ ... ],
    "segmento": [ ... ],
    "familia": [ ... ],
    "pac": [ ... ],
    "estrato": [ ... ],
    "top_empresas": [ ... ],
    "seg_empresas": [ ... ],
    "departamento": [ ... ],
    "localidades": [ ... ],
    "entidadesFinancieras": [ ... ]
  }
}
```

- `buyerPersona` reemplaza por completo el ETL: son las mismas distribuciones
  porcentuales que `generar_perfiles.py` intentaba calcular a partir de la
  base cruda de compradores, pero ya vienen agregadas desde Colsubsidio.
- **`app/etl/generar_perfiles.py`, `compradores_crudo.csv`,
  `perfiles_proyectos.csv` y `CompradoresCSVRepository` quedan obsoletos** —
  se eliminan del proyecto, no se actualizan.
- `tipologias` (nombre + precio) reemplaza el precio único que tenía el
  catálogo CSV — un proyecto puede tener varias unidades de precio distinto,
  y el filtro de asequibilidad debe evaluarse por tipología, no por proyecto.
- `ingreso_promedio_comprador` y `edad_promedio_comprador` del catálogo viejo
  quedan retirados: el bucket del lead se compara directo contra
  `buyerPersona`, mantener los promedios sería una segunda fuente de verdad
  que se puede desincronizar.

### 5.2 Catálogo cerrado de ubicaciones — CERRADO

`ubicacion` por proyecto (fusión de municipio/departamento) usa un catálogo
cerrado de 8 valores reales:

```
Bogotá, Chía, Ciudadela Maiporé, Ciudadela calle 80,
Girardot, Ricaute, Tocancipá, Ubate
```

`"Ciudadela Maiporé"` y `"Ciudadela calle 80"` **no son municipios** — son
desarrollos dentro de un municipio. Para que el tope VIS/VIP y la cobertura de
subsidio sigan funcionando (comparan contra nombre de municipio), se agregó un
mapeo `UBICACION_A_MUNICIPIO` en `config.py`:

| Ubicación | Municipio real |
|---|---|
| Bogotá | bogota |
| Chía | chia |
| Ciudadela Maiporé | soacha |
| Ciudadela calle 80 | bogota |
| Girardot | girardot |
| Ricaute | ricaurte |
| Tocancipá | tocancipa |
| Ubate | ubate |

**Corrección de listas heredadas del catálogo viejo (inventado):**
Tocancipá, Ricaurte y Ubaté no estaban en `ZONAS_COBERTURA_SUBSIDIO` ni en
`MUNICIPIOS_PRINCIPALES` — era una inconsistencia del catálogo anterior
(basado en datos de prueba, no reales), no una decisión de negocio. Se
agregaron los tres a `ZONAS_COBERTURA_SUBSIDIO` (son Cundinamarca, igual que
zipaquirá/facatativá/etc. que ya estaban). Para `MUNICIPIOS_PRINCIPALES` (tope
VIS 150 vs. 135 SMMLV) se dejaron como "otros" (135 SMMLV) — no son municipios
metropolitanos conurbados con Bogotá D.C. como sí lo son Soacha/Chía/Cota.

`MUNICIPIOS_SUR` / `MUNICIPIOS_NORTE` se eliminan de `config.py` — solo
existían para la agrupación del ETL obsoleto (sección 5.1).

### 5.3 Rediseño de la fórmula de matching histórico — EN DISEÑO

Cambia de "distancia a un promedio" (diseño anterior) a **"afinidad por
bucket poblacional"**: para cada dimensión de `buyerPersona`, se ubica al
lead en la categoría correspondiente y se lee directamente qué porcentaje de
compradores históricos comparte esa categoría — sin restas ni normalizaciones
arbitrarias.

**Detalle técnico real encontrado al revisar datos de ejemplo:** los buckets
de `salario` **no son un catálogo cerrado** — varían por proyecto. Algunos
usan buckets binarios (`"Hasta 2 smlv"` / `"Mas de 2 smlv"`), otros usan
rangos (`"Entre 4 y 6 smlv"`, `"Entre 6 y 8 smlv"`, etc., visto en el proyecto
Araucaria). La solución: parsear el texto del bucket a un rango numérico en
tiempo real (no una lista fija de categorías) y ubicar ahí el ingreso del
lead en SMMLV. Si el lead no cae en ningún bucket de un proyecto puntual, esa
dimensión no suma para ese proyecto — no es un error, es una señal de baja
afinidad real.

**Dimensiones planeadas** (`propuesta.md`):
- Fase 1 (equivalente al modelo actual, migrado a buckets): salario, edad, segmento de empresa
- Fase 2 (nuevas, sin costo adicional de captura): afiliación, composición familiar, estrato/PAC, ubicación (con `localidades` real del proyecto en vez de bono fijo de zona)

**Pesos por dimensión: pendientes de definir con negocio** — no es una
decisión técnica.

**Principio de diseño confirmado:** la afinidad histórica (`matching_historico`)
es **solo señal de score/orden, nunca filtro de exclusión**. El único filtro
de exclusión por perfil es la asequibilidad financiera (sección 5.4) — son
ejes independientes. Ver `REGLAS_DE_NEGOCIO.md` sección 7 para el
razonamiento completo.

**Exclusiones de catálogo, cerradas:**
- **Abeto y Vibonce**: fuera del matching por muestra histórica muy chica
  (1-2 compradores → sus porcentajes son ruido estadístico, no señal real).
- **Fila "Total"**: fuera del matching — es el agregado consolidado de todo
  el histórico, no un proyecto real comprable.

### 5.4 Matching con catálogo (disponibilidad) — parcialmente implementado, pendiente migrar a tipologías

- `zona_preferida` filtra contra proyectos disponibles.
- **Filtro VIS/No VIS: decisión cerrada — exclusión total.** Una tipología
  fuera del tope VIS/VIP de su municipio **no se recomienda en absoluto** (no
  es solo informativo). Ya implementado sobre el catálogo CSV viejo; falta
  migrar a tipologías por proyecto.
- El cierre financiero (30% de cuota inicial) se calcula **por tipología
  candidata**, no contra un precio promedio del portafolio — ya implementado
  sobre el catálogo CSV viejo; falta migrar a tipologías por proyecto.
- **Pendiente de definir con la migración a tipologías:** cuando un proyecto
  tiene varias tipologías asequibles, ¿se recomienda la más cara que el lead
  sí puede pagar (mejor opción real), o todas las asequibles? (`propuesta.md`
  sugiere la primera).

---

## 6. Endpoint de consulta de afiliados — CERRADA, IMPLEMENTADO

Necesidad detectada: el front necesita, **antes** de armar la conversación del
chat, saber si un `id_usuario` está afiliado y con qué datos ya cuenta
Colsubsidio (RF-03/RF-04). Esto no es scoring ni elegibilidad — es una simple
consulta de identidad. Vive en la capa de datos, no en el perfilador
(`motor.py`/`reglas.py`/`scoring.py` no se tocan para esto).

```
GET /afiliados/{id_usuario}
```

**Respuesta 200** (siempre 200 — "no afiliado" es una respuesta de negocio
válida, no un error):
```json
{ "afiliado": true, "datos": { "nombre": "...", "categoria": "...", "antiguedad_meses": ..., "personas_a_cargo": ... } }
```
o
```json
{ "afiliado": false, "datos": null }
```

**Implementación:** capa delgada en `api/routes.py` que llama directamente a
`AfiliadosRepository.obtener_afiliado(id_usuario)`. Si devuelve `None` →
`afiliado: false`; si devuelve datos → `afiliado: true` + los datos.

Mock ampliado de `data/afiliados.csv` entregado (más columnas que la versión
original: fecha de nacimiento, estrato, grupo SISBEN, subsidio previo, etc. —
con el mapeo de columnas actualizado en `config.py`).

**Decisión de responsabilidad — Opción A (elegida):** el front consulta este
endpoint, arma la conversación, y es quien ensambla el JSON completo del lead
(incluyendo los campos de afiliación) para mandarlo a `POST /perfilar`. El
backend confía en lo que el front envía en `/perfilar` — no vuelve a consultar
el repositorio de afiliados dentro de `motor.py`.

Se evaluó la Opción B (que `motor.py` re-consultara el repositorio con
`id_usuario` y sobreescribiera los campos de afiliación del payload, para que
el backend fuera la única fuente de verdad y nadie pudiera falsear su
afiliación). **Se descarta para el alcance de este MVP/hackathon** — no aporta
valor demostrable dado el contexto, aunque queda documentado como mejora futura
si el proyecto pasa a producción real.

---

## 7. Arquitectura de acceso a datos — CERRADA

**Patrón elegido: Repositorio + Adaptador, en el mismo proceso** (no
microservicio separado). Motivo: da la misma modularidad/escalabilidad sin el
costo de latencia de red, que pondría en riesgo RNF-03.

```
Lógica de negocio (motor.py, reglas.py, scoring.py)
        ↓ solo conoce interfaces
Interfaces de repositorio (AfiliadosRepository, ProyectosRepository)
        ↓ implementadas hoy por
Adaptador CSV de afiliados (simulación) | Adaptador JSON de proyectos
```

- **Afiliados**: diseñado ya pensando en que la fuente real será una **bodega
  de datos empresarial** (Redshift/Snowflake/BigQuery/SQL Server — se asume
  SQL como mínimo común denominador). Incluye una capa de **mapeo de
  columnas** en `config.py` (nombre de columna real → nombre de campo
  interno), para que cambiar de fuente sea editar un diccionario, no
  reescribir código. Cadena de conexión desde variable de entorno, nunca
  hardcodeada.
- **Proyectos**: pasa de CSV a JSON (`proyectos.json`, sección 5) — es la
  fuente que entrega Colsubsidio directamente, ya no hay ETL propio de por
  medio. `CompradoresRepository` y el adaptador CSV de proyectos quedan
  obsoletos.
- **Selección de adaptador**: variable de entorno (`DATA_SOURCE=csv|bodega`),
  resuelta en un único punto de arranque (`app/dependencies.py`), nunca
  esparcida por el código.

---

## 8. Tabla de decisiones (todas las rondas, para referencia rápida)

| # | Tema | Decisión |
|---|---|---|
| 1 | Techo de 4 SMMLV | Solo descalifica el subsidio, no `puede_comprar` |
| 2 | Excepción de arrendamiento en `subsidio_previo` | Se conserva, campo opcional |
| 3 | SISBEN vs. Segmentación de Caja | Ambos criterios, independientes |
| 4 | Penalización por no ser afiliado | Resta activa de puntos (no solo ausencia de bono) — regla 90/10 |
| 5 | Pesos de scoring | Todos en `config.py`, ajustables |
| 6 | Formato del score | Numérico (0–100) como fuente de verdad; `prioridad` es solo etiqueta derivada |
| 7 | Base de compradores (4.142 filas) | **Obsoleto** — reemplazado por `buyerPersona` pre-calculado en `proyectos.json`, ya no hay ETL propio |
| 8 | Arquitectura de acceso a datos | Repositorio + adaptador en el mismo proceso (no microservicio) |
| 9 | Fuente real de afiliados | Bodega de datos empresarial (SQL) — se diseña con mapeo de columnas configurable |
| 10 | Variable "foco" | Fuera de alcance, sin información suficiente |
| 11 | Responsable de ensamblar el lead afiliado en `/perfilar` | Opción A: el front lo arma tras consultar `GET /afiliados/{id_usuario}`; el backend confía en el payload (sin re-validación server-side, fuera de alcance para el MVP) |
| 12 | Tabla oficial de Subsidio Concurrente SISBEN | Recibida e implementada (sección 3.5); zona urbana/rural del lead sigue pendiente |
| 13 | Tie-breaker de Segmentación de Caja (Joven vs. resto) | Personas a cargo registradas, no un solape de rangos de ingreso |
| 14 | Precio único por proyecto vs. tipologías | Se reemplaza por lista de tipologías (nombre + precio) por proyecto — un proyecto puede tener varias unidades de precio distinto |
| 15 | Afinidad histórica como filtro vs. señal | Es solo señal de score/orden — nunca excluye una opción financieramente viable |
| 16 | Proyectos con muestra histórica chica (Abeto, Vibonce) | Excluidos del catálogo — es una hackathon, en producción real la empresa decide |
| 17 | Fila "Total" en `proyectos.json` | Excluida del matching — es un agregado, no un proyecto real |
| 18 | Filtro VIS/No VIS en matching | Exclusión total (no solo informativo) — una tipología fuera de tope no se recomienda |
| 19 | Ubicaciones no-municipio (Ciudadela Maiporé, Ciudadela calle 80) | Mapeo explícito a municipio real vía `UBICACION_A_MUNICIPIO`, no se comparan como texto |
| 20 | Tocancipá/Ricaurte/Ubaté ausentes de listas de cobertura | Era un error del catálogo viejo (inventado) — corregido, se agregaron |

---

## 9. Checklist de fases

> Marcar `[x]` al completar. Agregar fecha y, si aplica, referencia de commit
> o de archivo entregado.

### Fase 0 — Planeación
- [x] Revisar reglas de negocio faltantes vs. `Requerimientos` original
- [x] Definir modelo de datos del lead (JSON anidado)
- [x] Cerrar las decisiones iniciales de la tabla (sección 8)
- [x] Documentar arquitectura de acceso a datos
- [x] Crear este `plan.md`

### Fase 1 — Capa de datos (repositorios + adaptadores)
- [x] Definir interfaces (`Protocol`) para `AfiliadosRepository`,
      `ProyectosRepository`, `CompradoresRepository` (esta última hoy
      obsoleta, ver sección 5)
- [x] Implementar adaptador CSV de afiliados con mapeo de columnas
      configurable (simula bodega de datos) — ampliado con más columnas
      (SISBEN, estrato, subsidio previo)
- [x] Endpoint `GET /afiliados/{id_usuario}` (capa delgada sobre
      `AfiliadosRepository`, ver sección 6) — Opción A, sin re-validación en
      `/perfilar`
- [ ] Adaptador de proyectos: migrar de CSV a JSON (`proyectos.json`) — ver
      Fase 5.3/5.4 abajo

### Fase 2 — ETL offline de la base de compradores — OBSOLETO, NO SE COMPLETA
- [x] ~~Script de limpieza~~ — ya no aplica
- [x] ~~Generación de CSV de perfil por proyecto~~ — ya no aplica,
      `buyerPersona` viene pre-calculado en `proyectos.json`
- Se elimina `app/etl/generar_perfiles.py`, `data/compradores_crudo.csv`,
  `data/perfiles_proyectos.csv`, `CompradoresCSVRepository`. Fase cerrada
  como obsoleta, no como completada.

### Fase 3 — `config.py`
- [x] Agregar todos los parámetros nuevos (topes VIS/VIP, cobertura de
      zonas, Mi Casa Ya, arrendamiento, segmentación de caja, pesos de score
      separados cesantías/ahorros, penalización no-afiliado, mapeo de
      columnas de afiliados)
- [x] Corregir borde de 2 SMMLV en `MATRIZ_SUBSIDIOS`
- [x] Tabla SISBEN oficial (`SISBEN_ORDEN_GRUPOS`, `SISBEN_SUBSIDIO_MATRIZ`)
- [x] Catálogo cerrado de ubicaciones + mapeo a municipio real
      (`UBICACIONES_DISPONIBLES`, `UBICACION_A_MUNICIPIO`)
- [x] Corrección de `ZONAS_COBERTURA_SUBSIDIO` (Tocancipá/Ricaurte/Ubaté)
- [ ] Eliminar claves obsoletas del ETL (`MUNICIPIOS_SUR`, `MUNICIPIOS_NORTE`,
      `RUTA_CSV_COMPRADORES_CRUDO`, `RUTA_CSV_PROYECTOS_PERFIL`,
      `FACTOR_CORRECCION_VALOR_VIVIENDA`, `ETL_EXCLUIR_DESISTIDOS`,
      `DIMENSIONES_PERFIL_COMPRADORES`)
- [ ] Pesos por dimensión de `buyerPersona` (Fase 5.3) — pendientes de
      negocio

### Fase 4 — `api/schemas.py` — COMPLETA
- [x] Migrar `LeadInput` a la estructura anidada nueva
      (`condiciones_especiales`, `finanzas`)
- [x] Agregar `id_usuario`, `grupo_sisben`, `subsidio_previo`,
      `subsidio_previo_fue_arrendamiento`, `tipo_cotizante`,
      `valor_vivienda_deseada`

### Fase 5 — `reglas.py` — COMPLETA (sobre el catálogo CSV viejo; falta migrar a tipologías, ver Fase 5.3/5.4 en sección 5)
- [x] Adaptar lectura de campos a la estructura anidada
- [x] Agregar regla de `subsidio_previo`
- [x] Separar techo de 4 SMMLV como descalificador de subsidio (no de compra)
- [x] Calcular Segmentación de Caja
- [x] Conectar validación VIS/No VIS al flujo principal

### Fase 6 — `scoring.py` — PARCIAL
- [x] Separar factor cesantías / ahorros
- [x] Agregar factor SISBEN
- [x] Agregar factor `credito_preaprobado`
- [x] Agregar penalización activa por no afiliado
- [x] Implementar override de prioridad ALTA por RN-04
- [x] Conectar filtro VIS/No VIS y cierre financiero por proyecto a
      `match_proyectos` (sobre catálogo CSV viejo)
- [ ] Rediseñar `matching_historico` con perfiles porcentuales de
      `buyerPersona` (sección 5.3) — **en diseño, no implementado en código
      todavía**
- [ ] Migrar `match_proyectos` de precio único a tipologías por proyecto

### Fase 7 — `motor.py` — COMPLETA
- [x] Exponer campos nuevos en la respuesta (condiciones de subsidio,
      subsidio concurrente, subsidio de arrendamiento, descalificación por
      techo de ingresos, segmentación de caja, `override_rn04_aplicado`)
- [x] Corregido bug real: `validacion.get("subsidio_concurrente")` apuntaba a
      una clave que no existe (la real es `subsidio_concurrente_mi_casa_ya`)

### Fase 8 — Documentación — EN CURSO
- [x] `REGLAS_DE_NEGOCIO.md` — documento nuevo con cada regla, dónde vive,
      cómo decide, por qué
- [x] Actualizar este `plan.md`
- [ ] Actualizar `API.md` con el contrato completo — en curso, mismo commit
      que este `plan.md`
- [ ] Actualizar `API.md` otra vez cuando cierre la Fase 5.3/5.4 (matching
      con `buyerPersona` y tipologías) — quedará una segunda pasada

---

## 10. Pendientes / información faltante

- **`proyectos.json` completo real** — solo se han visto 3 proyectos de
  ejemplo (Versalles, Payandé, Araucaria) de los ~20 que existen. Bloquea
  terminar Fase 5.3/5.4.
- **Precios de tipologías reales** — los vistos hasta ahora son placeholders
  ("están por estar"), pendientes de precio real.
- **`tipo_proyecto` (VIS/No VIS/VIP) vacío** en los 3 ejemplos vistos —
  pendiente de llenar con dato real. Bloquea terminar el filtro VIS/No VIS
  sobre el catálogo nuevo.
- **Pesos por dimensión de `buyerPersona`** (afiliación, salario, edad,
  segmento, familia, PAC, estrato, empresa, entidad financiera, ubicación) —
  decisión de negocio, no técnica.
- **Zona urbana/rural del lead** — no existe el campo todavía, bloquea que el
  Subsidio Concurrente SISBEN use el tramo correcto para leads rurales.
- **Tope VIP (90 SMMLV)** — la función de tope de vivienda no lo usa todavía,
  siempre compara contra el tope VIS.
- Estructura exacta de columnas de la bodega de datos real de afiliados (hoy
  se simula con nombres razonables; ajustar el mapeo cuando se conozca el
  esquema real) — bloquea parte de la Fase 1.
- Variable "foco" de la base de compradores — fuera de alcance por ahora, no
  bloquea ninguna fase.