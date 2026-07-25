# Especificación Técnica de API y Contratos de Datos

> **Motor de Perfilamiento — Asesor Digital de Vivienda (Colsubsidio)**  
> **Versión de la API:** 1.0.0  
> **Base URL:** `http://localhost:8000`

---

## 1. Principios Arquitectónicos y Separación de Responsabilidades

El motor de perfilamiento cumple estrictamente con el principio de **Responsabilidad Única**:

- **Entrada:** Lead estructurado en formato JSON.
- **Procesamiento:** Validación de elegibilidad legal, scoring de prioridad comercial, evaluación de proyectos de interés y recomendación por tipologías.
- **Salida:** Lead enriquecido en formato estructurado JSON.

```
[ Frontend / Chatbot / WhatsApp ]
              │
              ▼ (JSON de entrada estructurado)
┌────────────────────────────────────────────────────────┐
│             MOTOR DE PERFILAMIENTO (CORE)              │
│  - Sin lógica de interfaz / sin renderizado HTML        │
│  - Sin procesamiento de lenguaje natural (NLP)         │
│  - Sin persistencia de datos (Stateless Engine)        │
└────────────────────────────────────────────────────────┘
              │
              ▼ (JSON de salida enriquecido)
[ CRM Salesforce / Hubspot / Interfaz Comercial ]
```

### Reglas de desacoplamiento:
1. **Sin NLP en el Core:** Si la interacción con el usuario se realiza mediante voz o texto libre (ej. WhatsApp), una capa externa (Adaptador de Entrada / LLM Agent) interpreta la respuesta y construye el JSON del Lead.
2. **Sin Presentación en el Core:** El motor devuelve datos limpios (números, booleanos, razones de rechazo y URLs de brochures). Las capas externas formatean las respuestas visuales, tarjetas o mensajes.

---

## 2. Diagrama de Arquitectura por Capas

```mermaid
flowchart TD
    subgraph Capa_Captura [Capa de Captura / Interacción]
        A1[Formulario Web] --> B1[Adaptador Entrada]
        A2[Chatbot WhatsApp] --> B1
        A3[Consulta Asesor] --> B1
    end

    subgraph Capa_Adaptacion_Entrada [Capa de Adaptación]
        B1 -->|POST /perfilar| C[LeadInput Schema]
        B2[GET /afiliados/{id}] --> D[AfiliadosRepository]
    end

    subgraph Motor_Core [Motor de Perfilamiento Core]
        C --> E[app/reglas.py: Elegibilidad]
        E --> F[app/scoring.py: Scoring & Matching]
        D --> E
        F --> G[app/motor.py: Orquestador]
    end

    subgraph Capa_Adaptacion_Salida [Capa de Adaptación / Consumidores]
        G --> H1[CRM Salesforce / Hubspot]
        G --> H2[Interfaz Web Comercial]
    end
```

---

## 3. Endpoints de la API REST

### `GET /health`
Verifica el estado del microservicio.
- **Respuesta `200 OK`:** `{"status": "ok"}`

---

### `GET /afiliados/{id_usuario}`
Consulta si un ciudadano es afiliado a Colsubsidio y sus datos precargados.
- **Parámetros:** `id_usuario` (Cédula / Documento).
- **Respuesta `200 OK` (Afiliado):**
  ```json
  {
    "afiliado": true,
    "datos": {
      "id_usuario": "1018300400",
      "nombre": "Diana Martinez Rojas",
      "categoria": "B",
      "antiguedad_meses": 24,
      "tipo_cotizante": "dependiente",
      "ingresos_mensuales": 2900000,
      "personas_a_cargo": 2,
      "estrato": "3",
      "grupo_sisben": "C2",
      "subsidio_previo": false,
      "subsidio_previo_fue_arrendamiento": false,
      "edad": 31,
      "zona": "urbana"
    }
  }
  ```
- **Respuesta `200 OK` (No Afiliado):**
  ```json
  {
    "afiliado": false,
    "datos": null
  }
  ```

---

### `POST /perfilar`
Procesa el lead completo y retorna la evaluación financiera, scoring y proyectos recomendados.
- **Headers:** `Content-Type: application/json`
- **Body:** [JSON de Entrada](#4-json-de-entrada)
- **Response:** `200 OK` con [JSON de Salida](#5-json-de-salida)

---

## 4. Matriz de Uso de Datos por Atributo

| Atributo | Origen / Proveedor | Obligatorio | Valores Aceptados | Uso en el Motor | Reglas Afectadas | Scoring | Matching |
|---|---|---|---|---|---|---|---|
| `id_usuario` | CRM / Formulario | Opcional | String (Cédula) | Identificador único | N/A | N/A | N/A |
| `nombre` | Formulario / Afiliados | Opcional | String | Personalización y trazabilidad | N/A | N/A | N/A |
| `afiliado` | Colsubsidio (Afiliados) | Requerido | `true` / `false` | Determina regla 90/10 y subsidio | Elegibilidad | +25 / -10 | Prioridad |
| `categoria` | Colsubsidio | Opcional | `"A"`, `"B"`, `"C"` | Informativo de caja | N/A | N/A | N/A |
| `antiguedad_meses` | Colsubsidio | Requerido si afiliado | Entero ≥ 0 | Antigüedad mínima (≥ 6 meses) | Rechazo Duro | N/A | N/A |
| `tipo_cotizante` | Colsubsidio / Lead | Opcional | `"dependiente"`, `"independiente"`, `"pensionado"` | Define mínimo de antigüedad | Rechazo Duro | N/A | N/A |
| `ingresos_mensuales` | Formulario / Afiliados | Requerido | Flotante ≥ 0 | Capacidad de pago y subsidio | Regla 40%, Subsidio, Segmentación | N/A | Asequibilidad |
| `edad` | Colsubsidio / Lead | Opcional | Entero (18 - 100) | Segmentación Joven y afinidad | N/A | +15 max | BuyerPersona |
| `personas_a_cargo` | Colsubsidio / Lead | Opcional | Entero ≥ 0 | Segmentación Joven vs Básico/Medio/Alto | Segmentación | +10 max | BuyerPersona |
| `condiciones_especiales` | Lead Input | Opcional | Objeto Booleano | Prioridad vulnerabilidad | N/A | +10 | N/A |
| `propietario_vivienda` | Lead Input | Requerido | `true` / `false` | Verificación de vivienda previa | Rechazo Duro | N/A | N/A |
| `subsidio_previo` | Lead Input | Requerido | `true` / `false` | Verificación de subsidio anterior | Rechazo Duro | N/A | N/A |
| `subsidio_previo_fue_arrendamiento` | Lead Input | Opcional | `true` / `false` | Excepción de subsidio previo | Rechazo Duro | N/A | N/A |
| `finanzas` | Lead Input | Opcional | Objeto (`cesantias`, `ahorros`, `credito_preaprobado`) | Cierre financiero y cuota inicial | Cierre | +8 cesantías, +4 ahorros, +10 crédito, Override RN-04 | Asequibilidad |
| `zona` | Colsubsidio / Lead | Opcional | `"urbana"`, `"rural"` | Cobertura Subsidio SISBEN | Subsidio SISBEN | N/A | N/A |
| `zona_preferida` | Lead Input | Opcional | String (ej. `"Bogotá"`) | Cobertura geográfica y bono zona | Subsidio Cobertura | N/A | Bono +0.10 |
| `proyecto_interes` | Formulario Comercial | Opcional | String (Nombre proyecto) | Evaluación obligatoria de interés directo | N/A | Priorización | Match #1 |
| `valor_vivienda_deseada` | Lead Input | Opcional | Flotante COP | Verificación tope VIS/VIP | Elegibilidad Subsidio | N/A | N/A |
| `origen` | Lead Input | Opcional | `"organico"`, `"meta"`, etc. | Canal de entrada | N/A | +5 si orgánico | N/A |

---

## 5. JSON de Entrada

### Ejemplo Completo de Request
```json
{
  "id_usuario": "1018300400",
  "nombre": "Diana Martínez Rojas",
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
  "zona": "urbana",
  "zona_preferida": "Bogotá",
  "proyecto_interes": "Versalles",
  "valor_vivienda_deseada": 150000000,
  "origen": "organico"
}
```

### Explicación Campo a Campo
- **`id_usuario`** `(string | null)`: Documento de identidad. Utilizado para auditar en CRM.
- **`nombre`** `(string | null)`: Nombre del cliente.
- **`afiliado`** `(boolean, por defecto false)`: Si es afiliado a Colsubsidio. Activa regla 90/10.
- **`antiguedad_meses`** `(integer | null)`: Meses continuos o discontinuos de afiliación.
- **`tipo_cotizante`** `(string | null)`: `"dependiente"`, `"independiente"`, `"pensionado"`.
- **`ingresos_mensuales`** `(number, ≥ 0)`: Ingresos brutos del hogar en COP. Base para capacidad del 40%.
- **`grupo_sisben`** `(string | null)`: Clasificación SISBEN IV (ej. `"A1"` a `"D21"`).
- **`edad`** `(integer | null)`: Edad cumplida del solicitante.
- **`personas_a_cargo`** `(integer | null)`: Número de dependientes económicos.
- **`condiciones_especiales`** `(object)`:
  - `cabeza_de_hogar` `(boolean)`: Condición de madre/padre cabeza de familia.
  - `discapacidad_hogar` `(boolean)`: Al menos un integrante con discapacidad.
  - `mayor_65_anos` `(boolean)`: Adultos mayores en el hogar.
- **`propietario_vivienda`** `(boolean)`: Si ya posee vivienda a nivel nacional.
- **`subsidio_previo`** `(boolean)`: Si ha recibido subsidio de vivienda estatal o de caja.
- **`subsidio_previo_fue_arrendamiento`** `(boolean)`: Si el subsidio previo fue exclusivamente para arriendo.
- **`finanzas`** `(object)`:
  - `cesantias` `(number)`: Fondo de cesantías acumulado en COP.
  - `ahorros` `(number)`: Ahorro voluntario disponible en COP.
  - `credito_preaprobado` `(boolean)`: Carta o estado de crédito hipotecario pre-aprobado.
- **`zona`** `(string | null)`: Zona de residencia (`"urbana"` o `"rural"`).
- **`zona_preferida`** `(string | null)`: Municipio donde busca vivienda.
- **`proyecto_interes`** `(string | null)`: Nombre del proyecto por el que preguntó el lead.
- **`valor_vivienda_deseada`** `(number | null)`: Presupuesto estimado de vivienda.
- **`origen`** `(string | null)`: Canal publicitario (`"organico"`, `"meta"`, `"google"`).

---

## 6. JSON de Salida

### Ejemplo Completo de Response
```json
{
  "lead_info": {
    "nombre": "Diana Martínez Rojas",
    "afiliado": true,
    "prioridad": "ALTA (90/10)",
    "segmentacion_caja": "Medio"
  },
  "financial_score": {
    "viable": "SI",
    "motivos_rechazo": [],
    "subsidio_estimado": 52527150,
    "descalifica_subsidio_por_techo_ingresos": false,
    "capacidad_max_cuota": 1160000,
    "cierre_financiero": {
      "precio_referencia_vivienda": 150000000,
      "cuota_inicial_requerida": 45000000,
      "ahorro_disponible": 60527150,
      "cierre_viable": true
    },
    "subsidio_concurrente_mi_casa_ya": {
      "disponible": true,
      "monto_adicional_estimado": 35018100
    },
    "subsidio_arrendamiento": {
      "sugerido": false,
      "monto_mensual_estimado": 1050543,
      "meses": 24,
      "monto_total_estimado": 25213032
    },
    "condiciones_subsidio": {
      "dentro_de_tope_ingresos": true,
      "sin_rechazo_por_reglas_duras": true,
      "zona_con_cobertura_subsidio": true,
      "vivienda_dentro_de_tope_vis_vip": true
    }
  },
  "score_detalle": {
    "score_total": 93,
    "prioridad": "ALTA",
    "factores": {
      "afiliado": 25,
      "cierre_financiero_viable": 10,
      "matching_historico": 13,
      "cesantias": 8,
      "ahorros": 4,
      "condicion_especial": 10,
      "grupo_sisben": 8,
      "credito_preaprobado": 10,
      "origen_organico": 5
    },
    "override_rn04_aplicado": false
  },
  "evaluacion_proyecto_interes": {
    "proyecto": "Versalles",
    "viable": true,
    "motivo": "Proyecto de interés viable y priorizado como primera recomendación."
  },
  "matching_projects": [
    {
      "proyecto": "Versalles",
      "ubicacion": "Ciudadela Maiporé",
      "municipio": "soacha",
      "tipo_proyecto": "VIS",
      "tipologia": "Tipo E",
      "precio": 180000000,
      "brochure_url": "https://colsubsidio.com/brochures/versalles.pdf",
      "match_score": 0.648,
      "motivo": "Afinidad con el perfil histórico de compradores de Versalles (65% de match); (Proyecto de interés directo del lead - Priorizado)",
      "cierre_financiero": {
        "cuota_inicial_requerida": 54000000,
        "ahorro_disponible": 60527150,
        "cierre_viable": true,
        "subsidio_aplicable": 52527150
      }
    }
  ],
  "ai_summary": "Lead ALTA interesado en Bogotá. Mejor match: Versalles. Subsidio estimado: $52,527,150.",
  "lead_original": { "...": "Copia íntegra del JSON enviado" }
}
```

### Explicación de Secciones Clave para CRM
- **`lead_info.prioridad`**: Muestra la prioridad calculada y añade `(90/10)` si aplica la regla de priorización a afiliados.
- **`financial_score.viable`**: `"SI"` o `"NO"`. Permite al CRM filtrar leads descartados inmediatamente.
- **`financial_score.motivos_rechazo`**: Arreglo de cadenas explicativas en lenguaje comprensible si `viable == "NO"`.
- **`evaluacion_proyecto_interes`**: Objeto explicativo si el lead consultó por un proyecto específico. Devuelve `viable` (boolean) y `motivo` detallado si fue descartado.
- **`matching_projects[].brochure_url`**: Enlace al PDF/Brochure para que el frontend o CRM renderice el botón "Ver brochure".
- **`matching_projects[].cierre_financiero`**: Cierre financiero específico recalculado contra el precio exacto de la tipología del proyecto, no contra un promedio del portafolio.