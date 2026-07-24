# Plan — Motor de Perfilamiento (Asesor Digital de Vivienda, Colsubsidio)

> Este documento es la fuente de verdad del proyecto. Antes de retomar el trabajo
> en cualquier sesión nueva, léelo completo: contiene el contexto de negocio, las
> decisiones ya tomadas (y por qué), el diseño de datos/arquitectura acordado, y
> el checklist de fases. Marca cada casilla `[x]` cuando la fase quede completa
> y agrega la fecha/commit si aplica.

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

## 2. Modelo de datos del Lead (JSON de entrada — versión vigente)

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

Nota: `subsidio_previo_fue_arrendamiento` es opcional (default `false`) y no
viene en la plantilla original del usuario — se agregó para conservar la regla
legal de excepción de arrendamiento (ver decisión en tabla de la sección 3).

---

## 3. Reglas de negocio — estado y decisiones

### 3.1 Reglas duras de rechazo (`puede_comprar = false`)

| # | Condición | Estado |
|---|---|---|
| 1 | `propietario_vivienda == true` | Vigente, sin cambios |
| 2 | `afiliado == true` y `antiguedad_meses < mínimo` (mínimo por `tipo_cotizante`, hoy 6 para los tres: dependiente/independiente/pensionado) | Vigente |
| 3 | `subsidio_previo == true` y NO `subsidio_previo_fue_arrendamiento` | Vigente (excepción de arrendamiento se conserva) |
| 4 | `ingresos_mensuales * 0.40 <= 0` | Vigente |

**Importante:** el techo de 4 SMMLV **NO** está en esta tabla — ver 3.2.

### 3.2 Elegibilidad al subsidio (NO bloquea la compra, solo el monto)

`aplica_subsidio` es `true` solo si se cumplen TODAS:
1. `ingresos_en_smmlv <= TOPE_INGRESOS_SMMLV` (4 SMMLV / $7.003.620 en 2026)
2. Sin motivos de rechazo duro (sección 3.1)
3. `zona_preferida` dentro de cobertura (Bogotá y Cundinamarca)
4. `valor_vivienda_deseada` dentro del tope VIS (135–150 SMMLV según
   municipio) — si no hay dato, no bloquea

Si `aplica_subsidio == false`, se expone `subsidio_estimado = 0` y el motivo
específico en `condiciones_subsidio` (para RNF-02, explicabilidad).

**Campo de salida nuevo a exponer:** `descalifica_subsidio_por_techo_ingresos`
(booleano, separado de `puede_comprar`) para que el equipo comercial distinga
"no puede comprar" de "puede comprar pero sin ayuda de la caja".

### 3.3 Monto del subsidio (SMMLV 2026 = $1.750.905)

| Rango ingresos (SMMLV) | Subsidio |
|---|---|
| 0 ≤ ingresos ≤ 2 | 30 SMMLV ($52.527.150) |
| 2 < ingresos ≤ 4 | 20 SMMLV ($35.018.100) |
| > 4 | $0 |

**Pendiente de corrección de código:** el borde debe ser `<=` 2 SMMLV para el
primer rango (hoy en el código anterior quedó como `<`, hay que corregirlo).

### 3.4 Regla del 40%

`cuota_maxima_mensual = round(ingresos_mensuales * 0.40)` — sin cambios.

### 3.5 Subsidios complementarios (informativos, no bloquean)

- **Mi Casa Ya concurrente**: si `ingresos_en_smmlv < 2`, informar que puede
  sumar hasta 20 SMMLV adicionales.
- **Subsidio de arrendamiento**: si `cierre_financiero.cierre_viable == false`,
  sugerir 0.6 SMMLV/mes por 24 meses como ruta alterna de ahorro.
- **Subsidio Concurrente por SISBEN**: pendiente de definir tabla de grupos
  SISBEN que califican (A1–D21) — **SISBEN y Segmentación de Caja se manejan
  como criterios independientes** (decisión tomada), no uno reemplaza al otro.

---

## 4. Sistema de score — decisiones cerradas

**El score es SIEMPRE numérico (0–100)**. `prioridad` (ALTA/MEDIA/BAJA) es
solo una etiqueta derivada para UI — ningún cálculo interno (matching,
ordenamiento, overrides) se hace sobre la palabra, siempre sobre el número.

| Factor | Estado | Peso | Notas |
|---|---|---|---|
| `afiliado == true` suma | Vigente | ajustable en config | Regla 90/10 |
| `afiliado == false` **resta** puntos | **Nuevo** | ajustable en config | Antes solo no sumaba; ahora es penalización activa (decisión confirmada — regla 90/10 debe verse en ambos sentidos) |
| Condiciones especiales (cabeza hogar / discapacidad / 65+) | Vigente | ajustable | Hoy es un solo factor todo-o-nada |
| `finanzas.cesantias` | **Cambio** | ajustable, mayor que ahorros | Se separa de `ahorros` — cesantías inmovilizadas puntúan más que ahorro voluntario |
| `finanzas.ahorros` | **Cambio** | ajustable, menor que cesantías | Ver arriba |
| `grupo_sisben` | **Nuevo** | ajustable | Habilita Subsidio Concurrente — falta tabla de grupos calificantes |
| `finanzas.credito_preaprobado` | **Nuevo** | ajustable | Existía en RN-04 pero nunca se implementó en scoring |
| `origen == "organico"` suma | Vigente | ajustable | — |

**Override de prioridad (RN-04):** si `credito_preaprobado == true` AND
`aplica_subsidio == true` AND `cierre_financiero.cierre_viable == true` (cubre
el valor total) → `prioridad = "ALTA"` **aunque el score_total no llegue a 70**.
El score numérico se sigue exponiendo tal cual, sin alterarse; el override
solo afecta la etiqueta.

**Segmentación de Caja — pasa a ser calculada, no un dato de entrada crudo:**

| Segmento | Regla |
|---|---|
| Básico | ingresos ≤ 1.44 SMMLV + personas a cargo registradas |
| Medio | 1.44–20 SMMLV + grupo familiar |
| Alto | > 20 SMMLV |
| Joven | edad < 39 años, sin personas a cargo |

Se deriva de `ingresos_mensuales`, `personas_a_cargo`, `edad`. Los cortes van
en `config.py`.

---

## 5. Matching — histórico y catálogo

### 5.1 Fuentes de datos nuevas (reemplazan/complementan al catálogo actual)

**A. Base de compradores (~4.142 filas, CSV/Excel, transaccional):**
- Proyecto, etapa, código de proyecto
- Fecha de opción / fecha de desistimiento (vacía = compra vigente)
- Entidad financiera, medio de conocimiento del proyecto
- Valor promedio de vivienda — **bug de formato conocido**: hay que quitar
  ceros sobrantes (ej. `523.620` → ≈ $523M). Corregir en la capa de ingesta.
- Afiliado sí/no, segmento, categoría, rango salarial, personas a cargo
- Empresa, pirámide, ranking de empresa
- Variable "foco" — **fuera de alcance por ahora**, no hay info suficiente

**B. Perfil de compradores por proyecto (CSV agregado, % por variable):**
- % afiliados vs. no afiliados
- Distribución por género, rango salarial, rango de edad
- Segmentación de Caja (Básico/Medio/Alto/Joven — ver definiciones sección 4)
- Segmentación familiar DANE (monoparental, nuclear ampliada, etc.)
- Personas a cargo, estrato (dato incompleto, puede no sumar 100%)
- Pirámide de empresa (Top/Micro/Medianas/**Estándar** — falta agregar esta
  categoría, hoy el catálogo solo reconoce 3)
- Ubicación (departamento/localidad/municipio)
- Entidad financiera
- **Versiones agrupadas**: municipios sur (Soacha, Ricaurte, etc.) y
  municipios norte, con la misma estructura condensada

### 5.2 Decisión de arquitectura de datos — CERRADA

La base de 4.142 compradores **nunca se toca en el camino de una petición en
vivo** (viola RNF-03 de latencia). Se procesa **offline**, en un job ETL que:
1. Limpia el formato de valores (quitar ceros sobrantes)
2. Genera/actualiza los CSV de perfil por proyecto (sección 5.1-B)
3. El API en producción solo lee esos perfiles ya agregados

### 5.3 Rediseño de la fórmula de matching histórico

Cambia de "distancia a un promedio" (diseño actual) a "afinidad por
pertenencia a segmento": para cada proyecto, ¿en qué % de compradores
históricos cae el segmento del lead? (segmentación de caja, rango salarial,
rango de edad, tipo de empresa, ubicación). Reemplaza la similitud continua
actual basada solo en `ingreso_promedio_comprador` / `edad_promedio_comprador`.

### 5.4 Matching con catálogo (disponibilidad)

- `zona_preferida` filtra contra proyectos disponibles (incluye agrupados
  sur/norte)
- `valor_vivienda_deseada` valida VIS (≤135–150 SMMLV) vs. No VIS (>150 SMMLV,
  fuera del alcance de subsidio) — la función ya existe (`_valor_vivienda_dentro_de_tope`
  en el `reglas.py` actual) pero falta **conectarla** al filtro de
  `match_proyectos`
- El cierre financiero (30% de cuota inicial) debe calcularse **por proyecto
  candidato**, no contra un precio promedio del portafolio VIS completo (así
  funciona hoy, hay que cambiarlo)

---

## 6. Endpoint de consulta de afiliados — CERRADA

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
Interfaces de repositorio (AfiliadosRepository, ProyectosRepository, CompradoresRepository)
        ↓ implementadas hoy por
Adaptadores CSV (simulación) ←── ETL offline (limpia y agrega la base de 4.142 compradores)
```

- **Afiliados**: diseñado ya pensando en que la fuente real será una **bodega
  de datos empresarial** (Redshift/Snowflake/BigQuery/SQL Server — se asume
  SQL como mínimo común denominador). Incluye una capa de **mapeo de
  columnas** en `config.py` (nombre de columna real → nombre de campo
  interno), para que cambiar de fuente sea editar un diccionario, no
  reescribir código. Cadena de conexión desde variable de entorno, nunca
  hardcodeada.
- **Proyectos** y **Compradores**: se quedan en CSV por ahora (simulación /
  ETL), no hay sistema real todavía del otro lado.
- **Selección de adaptador**: variable de entorno (`DATA_SOURCE=csv|bodega`),
  resuelta en un único punto de arranque (ej. `app/dependencies.py`), nunca
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
| 7 | Base de compradores (4.142 filas) | Nunca se procesa en vivo — solo alimenta un ETL offline |
| 8 | Arquitectura de acceso a datos | Repositorio + adaptador en el mismo proceso (no microservicio) |
| 9 | Fuente real de afiliados | Bodega de datos empresarial (SQL) — se diseña con mapeo de columnas configurable |
| 10 | Variable "foco" | Fuera de alcance, sin información suficiente |
| 11 | Responsable de ensamblar el lead afiliado en `/perfilar` | Opción A: el front lo arma tras consultar `GET /afiliados/{id_usuario}`; el backend confía en el payload (sin re-validación server-side, fuera de alcance para el MVP) |

---

## 9. Checklist de fases

> Marcar `[x]` al completar. Agregar fecha y, si aplica, referencia de commit
> o de archivo entregado.

### Fase 0 — Planeación (esta fase)
- [x] Revisar reglas de negocio faltantes vs. `Requerimientos` original
- [x] Definir modelo de datos del lead (JSON anidado)
- [x] Cerrar las 10 decisiones de la tabla (sección 7)
- [x] Documentar arquitectura de acceso a datos
- [x] Crear este `plan.md`

### Fase 1 — Capa de datos (repositorios + adaptadores)
- [x] Definir interfaces (`Protocol`) para `AfiliadosRepository`,
      `ProyectosRepository`, `CompradoresRepository`
- [x] Implementar adaptador CSV de afiliados con mapeo de columnas
      configurable (simula bodega de datos)
- [x] Implementar adaptador CSV de proyectos (perfil por proyecto —
      lectura lista; falta el CSV con datos reales, se genera en Fase 2)
- [x] Punto único de selección de adaptador (`DATA_SOURCE_AFILIADOS` env
      var, en `app/dependencies.py`)
- [x] Endpoint `GET /afiliados/{id_usuario}` (capa delgada sobre
      `AfiliadosRepository`, ver sección 6) — Opción A, sin re-validación en
      `/perfilar`

> Entregado: `app/repositories/{interfaces,afiliados_csv,proyectos_csv}.py`,
> `app/dependencies.py`, `app/api/routes_afiliados.py`. Probado con
> `TestClient` de FastAPI (200 en afiliado existente y no existente) y con
> CSV de ejemplo (`data/afiliados.csv`). Pendiente: `data/perfiles_proyectos.csv`
> real, se llena en Fase 2 (ETL) — hoy el repositorio ya soporta leerlo, solo
> falta el archivo.

### Fase 2 — ETL offline de la base de compradores
- [x] Script de limpieza (corregir formato de valor de vivienda, quitar
      ceros sobrantes) — `app/etl/limpieza.py`
- [x] Generación de CSV de perfil por proyecto desde la base cruda —
      `app/etl/generar_perfiles.py`, agrupa también sur/norte
- [ ] Validación de que los agregados generados coincidan con los CSV de
      perfil ya entregados (si existen de referencia) — **pendiente**:
      necesitamos el CSV real de compradores para correr el ETL de verdad y
      confirmar el factor de corrección del valor de vivienda

> Entregado: `app/repositories/compradores_csv.py`, `app/etl/limpieza.py`,
> `app/etl/generar_perfiles.py`, `app/identificadores.py` (slug de proyecto
> compartido entre ETL y consulta en vivo). Probado end-to-end con CSV de
> ejemplo: exclusión de desistidos, agregación por proyecto y por grupo
> sur/norte, lectura posterior desde `ProyectosCSVRepository` — todo OK.
> ⚠️ La fórmula de `corregir_valor_vivienda()` es una suposición razonable
> sin datos reales todavía; validar en cuanto llegue el CSV real de
> compradores y ajustar `FACTOR_CORRECCION_VALOR_VIVIENDA` si hace falta.

### Fase 3 — `config.py`
- [x] Agregar todos los parámetros nuevos (topes VIS/VIP, cobertura de
      zonas, Mi Casa Ya, arrendamiento, segmentación de caja, pesos de score
      separados cesantías/ahorros, penalización no-afiliado, mapeo de
      columnas de afiliados)
- [x] Corregir borde de 2 SMMLV en `MATRIZ_SUBSIDIOS` (ahora es
      `max_smmlv` recorrido en orden, en vez de rangos `[min, max)`)

> Entregado: `app/config.py` consolidado (reemplaza el archivo completo).
> ⚠️ Cambio de formato en `MATRIZ_SUBSIDIOS` (se quitó `min_smmlv`) — el
> `reglas.py` de la Fase 0 todavía espera el formato viejo y se romperá
> hasta que se actualice en la Fase 5. No mezclar este `config.py` con ese
> `reglas.py` en producción; van de la mano en el mismo commit.
> Pendiente real: `GRUPOS_SISBEN_CALIFICAN_SUBSIDIO` queda vacío a
> propósito hasta tener la tabla oficial de negocio (bloquea parte de la
> Fase 6, ya registrado en la sección 10).

### Fase 4 — `api/schemas.py`
- [ ] Migrar `LeadInput` a la estructura anidada nueva
      (`condiciones_especiales`, `finanzas`)
- [ ] Agregar `id_usuario`, `grupo_sisben`, `subsidio_previo`,
      `subsidio_previo_fue_arrendamiento`, `tipo_cotizante`,
      `valor_vivienda_deseada`

### Fase 5 — `reglas.py`
- [ ] Adaptar lectura de campos a la estructura anidada
- [ ] Agregar regla de `subsidio_previo`
- [ ] Separar techo de 4 SMMLV como descalificador de subsidio (no de compra)
- [ ] Calcular Segmentación de Caja
- [ ] Conectar validación VIS/No VIS al flujo principal

### Fase 6 — `scoring.py`
- [ ] Separar factor cesantías / ahorros
- [ ] Agregar factor SISBEN (pendiente definir tabla de grupos calificantes)
- [ ] Agregar factor `credito_preaprobado`
- [ ] Agregar penalización activa por no afiliado
- [ ] Implementar override de prioridad ALTA por RN-04
- [ ] Rediseñar `matching_historico` con perfiles porcentuales (sección 5.3)
- [ ] Conectar filtro VIS/No VIS y cierre financiero por proyecto a
      `match_proyectos`

### Fase 7 — `motor.py`
- [ ] Exponer campos nuevos en `PerfilamientoResponse` (condiciones de
      subsidio, subsidio concurrente, subsidio de arrendamiento,
      descalificación por techo de ingresos)

### Fase 8 — Documentación
- [ ] Actualizar `API.md` con el contrato completo nuevo, incluyendo
      `GET /afiliados/{id_usuario}`
- [ ] Actualizar este `plan.md` (marcar fases completas)

---

## 10. Pendientes / información faltante

- Tabla de grupos SISBEN (A1–D21) que califican para Subsidio Concurrente —
  bloquea parte de la Fase 6.
- Estructura exacta de columnas de la bodega de datos real de afiliados (hoy
  se simula con nombres razonables; ajustar el mapeo cuando se conozca el
  esquema real) — bloquea parte de la Fase 1.
- Variable "foco" de la base de compradores — fuera de alcance por ahora, no
  bloquea ninguna fase.
- CSV real de compradores (~4.142 filas) para correr el ETL de verdad y
  confirmar/ajustar la fórmula de `corregir_valor_vivienda()` en
  `app/etl/limpieza.py` (hoy funciona con datos de ejemplo, la fórmula es
  una suposición razonable pendiente de validar) — bloquea el cierre de la
  Fase 2.