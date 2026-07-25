# Revisión Crítica del Motor y Evaluación Técnica para CRM

Este documento presenta una evaluación profunda de la arquitectura, reglas y salidas del **Motor de Perfilamiento (Asesor Digital de Vivienda - Colsubsidio)**. Su objetivo es identificar límites, riesgos, robustez del algoritmo y la preparación comercial para CRM.

---

## 1. Revisión Crítica del Corazón del Sistema

### 1.1. ¿El motor realmente puede recomendar correctamente un proyecto?
**Sí, dentro de un alcance determinista y basado en asequibilidad financiera estricta.**

El motor actual garantiza con un 100% de precisión matemática que el usuario no reciba proyectos fuera de su capacidad de pago ni fuera de los topes legales de vivienda VIS/VIP. Sin embargo, en términos de preferencias de estilo de vida, transporte o acabados, el motor se basa en coincidencias categóricas y promedios poblacionales (`buyerPersona`).

### 1.2. Información utilizada para la recomendación
- **Capacidad de Pago Real:** Cesantías + Ahorros + Subsidio Estimado (Caja + Mi Casa Ya) + Capacidad de Crédito (40% de ingresos a 120 meses).
- **Cumplimiento Normativo:** Topes legales VIS/VIP (90, 135 o 150 SMMLV según municipio y tipo de proyecto).
- **Afinidad Poblacional (`buyerPersona`):** Cruce del perfil del lead (salario, edad, personas a cargo, tipo de empresa, estrato) con la distribución porcentual real de compradores históricos por proyecto.
- **Interés Directo (`proyecto_interes`):** Evaluación obligatoria y priorización directa como primera recomendación si el proyecto es financieramente viable.
- **Ubicación Geográfica:** Coincidencia entre `zona_preferida` o `zona` del lead y el municipio del proyecto.

### 1.3. Información faltante para mejorar la precisión
1. **Composición Familiar Detallada:** Actualmente se infiere de `personas_a_cargo` y `cabeza_de_hogar`. Conocer la estructura exacta (pareja, hijos, adultos mayores) refinaría la tipología recomendada.
2. **Capacidad de Endeudamiento Real (Buroes de Crédito):** El motor asume capacidad de crédito basada en el 40% de los ingresos, pero no conoce deudas activas o centrales de riesgo del lead (salvo el flag `credito_preaprobado`).
3. **Preferencia de Entrega / Tiempos:** Proyectos en preventa (entrega a 2-3 años) vs. entrega inmediata. Un lead con subsidio asignado urgente necesita entrega rápida.
4. **Cercanía a Puntos de Interés:** Distancia real a lugares de trabajo o transporte público.

### 1.4. Inconsistencias y Riesgos Algorítmicos
- **Riesgo de Perpetuación de Sesgos Históricos:** Al usar la afinidad histórica (`buyerPersona`), si un proyecto históricamente fue comprado por personas de cierto estrato o empresa, el score tiende a favorecer a leads similares. *Solución aplicada:* El `matching_historico` actúa **únicamente como criterio de ordenamiento**, jamás como filtro de exclusión.
- **Supuesto de Crédito a 10 Años:** Se usa un estimador global (120 cuotas máximas). En la práctica, plazos a 15 o 20 años cambian drásticamente la capacidad de compra.

---

## 2. Evaluación de Preparación para CRM Comercial

### 2.1. ¿La salida actual alimentaría correctamente un CRM?
**Sí.** La estructura JSON devuelta por `procesar_lead` está diseñada específicamente para consumo por sistemas de ventas como Salesforce, Hubspot o Dynamics. Separar la información en bloques (`lead_info`, `financial_score`, `score_detalle`, `evaluacion_proyecto_interes`, `matching_projects`) permite que el CRM clasifique leads automáticamente.

### 2.2. ¿Un asesor tiene toda la información para cerrar la venta?
El asesor cuenta con los datos clave:
- **Elegibilidad inmediata:** Sabe si puede venderle ya o si debe rechazarlo/enrumbarlo a ahorro.
- **Monto de subsidio exacto:** Sabe con cuánto subsidio cuenta el cliente para estructurar el negocio.
- **Motivos de rechazo claros:** No hay adivinanzas; sabe exactamente por qué no califica.
- **Evaluación de Interés Directo:** Conoce si el proyecto por el que preguntó el usuario es viable o por qué razón técnica fue descartado.
- **Brochure y tipología sugerida:** Tiene a la mano el enlace comercial (`brochure_url`) y el precio específico de entrada.

### 2.3. Recomendaciones de Campos Adicionales para el CRM (Mejoras Futuras)
Para ahorrar tiempo al asesor y mejorar la conversión comercial, se sugiere agregar en versiones posteriores:
1. **Canal Preferido de Contacto y Horario:** `WhatsApp`, `Llamada`, `Email` y franja horaria preferida.
2. **Fecha de Vencimiento de Subsidio Asignado:** Si el usuario ya tiene subsidio aprobado por otra entidad, el tiempo restante para aplicarlo.
3. **Argumento Comercial Sugerido (Pitch para Asesor):** Frase técnica resumida para la llamada (ej. *"Cliente con crédito preaprobado y subsidio completo de 30 SMMLV; cerrar en proyecto Versalles tipología E"*).
4. **Calculadora de Cuota Mensual Estimada por Proyecto:** Detalle exacto de la cuota mensual proyectada para la tipología recomendada.

---

## 3. Estricta Separación de Responsabilidades

El motor de perfilamiento se mantiene **100% desacoplado de las capas de presentación e interacción**:

```
[ Frontend / Chatbot / WhatsApp / CRM ]
                 │
                 ▼ (Lead estructurado JSON)
┌─────────────────────────────────────────────────┐
│          MOTOR DE PERFILAMIENTO (CORE)           │
│  Perfilamiento ➔ Elegibilidad ➔ Score ➔ Matching│
└─────────────────────────────────────────────────┘
                 │
                 ▼ (Lead enriquecido JSON)
[ CRM Salesforce / Asesor Comercial / Interfaz UI ]
```

- **Sin NLP ni Conversación en el Core:** El motor opera únicamente sobre datos estructurados. Si el canal es WhatsApp o un chatbot, las capas externas traducen el lenguaje natural a JSON antes de llamar al motor.
- **Sin Generación de UI:** El motor devuelve datos puros (`brochure_url`, precios, motivos). Las capas externas renderizan las tarjetas, textos comprensibles o interfaces de ventas.
