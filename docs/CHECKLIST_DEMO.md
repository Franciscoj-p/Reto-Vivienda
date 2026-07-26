# Checklist de Funcionalidades y Guía de Presentación (Demo Motor de Perfilamiento)

> **Estado del Proyecto:** 🟢 **100% TERMINADO Y COMPLEMENTADO**  
> Este documento contiene el checklist completo de capacidades del motor y los puntos clave que debes **remarcar y destacar durante la presentación/demo** del Reto Vivienda.

---

## 1. Checklist de Funcionalidades a Presentar

### A. Capa de Consulta de Afiliados (`GET /afiliados/{id_usuario}`)
- [x] **Precarga de Datos de la Caja (RN-02):** Si el usuario ingresa la cédula, el sistema recupera sus datos precargados (nombre, categoría A/B/C, antigüedad, personas a cargo, edad, estrato, zona urbana/rural).
- [x] **No duplicación de preguntas:** Cumple la regla de no preguntarle al usuario lo que Colsubsidio ya conoce de sus afiliados.

### B. Evaluación de Elegibilidad Legal y Reglas Duras (`app/reglas.py`)
- [x] **Filtro de Propietario:** Verifica si el lead o su hogar ya poseen vivienda propia.
- [x] **Filtro de Antigüedad de Afiliación:** Exige el mínimo de antigüedad (≥ 6 meses para cotizantes).
- [x] **Filtro de Subsidio Previo con Excepción Legal:** Rechaza si recibió subsidio previo, **salvo que haya sido de arrendamiento** (excepción legal de vivienda).
- [x] **Regla del 40% (Capacidad de Cuota):** Limita la capacidad de cuota mensual al 40% de los ingresos brutos del hogar.

### C. Subsidios y Beneficios 2026 (`SMMLV = $1.750.905`)
- [x] **Matriz de Subsidios Colsubsidio:**
  - 0 a 2 SMMLV ➔ **30 SMMLV** ($52.527.150 COP).
  - 2 a 4 SMMLV ➔ **20 SMMLV** ($35.018.100 COP).
  - > 4 SMMLV ➔ $0 COP (Descalificado por techo de ingresos, pero sin bloquear compra libre).
- [x] **Subsidio Concurrente "Mi Casa Ya":** Si los ingresos son < 2 SMMLV, calcula el bono adicional de **20 SMMLV** ($35.018.100 COP) sumable a la cuota inicial.
- [x] **Subsidio Concurrente SISBEN:** Matriz por grupos SISBEN (A1-D21) diferenciando zona **urbana** vs **rural**.
- [x] **Ruta de Arrendamiento Sugerido:** Si el lead no logra el cierre inicial, sugiere subsidio de arrendamiento (**0.6 SMMLV/mes por 24 meses = $25.213.032 COP**) como alternativa de ahorro.

### D. Segmentación Automática de Caja
- [x] **Categorización Inteligente:** Clasifica automáticamente al lead en `Joven`, `Basico`, `Medio` o `Alto`.
- [x] **Desempate del Segmento Joven:** Si tiene `< 39 años` y `0 personas a cargo`, se asigna a `Joven` prioritariamente.

### E. Priorización Comercial y Scoring (0 a 100 puntos)
- [x] **Explicabilidad Total (RNF-02):** Desglose detallado punto por punto (Afiliado, Cesantías, Ahorros, Crédito preaprobado, SISBEN, Condición especial, Origen).
- [x] **Regla 90/10 de Afiliados:** Premia con **+25 puntos** a afiliados y aplica **penalización activa de -10 puntos** a no afiliados.
- [x] **Override de Prioridad RN-04:** Si el cliente tiene crédito preaprobado, aplica subsidio y sus ahorros cubren el 100% del valor del inmueble, fuerza la etiqueta a **`ALTA (90/10)`**.

### F. Matemática Financiera de Cierre por Proyecto y Tipología
- [x] **Desglose de Cuota Inicial (30% antes de entrega):**
  - Suma de aportes (`Cesantías + Ahorros + Subsidio Caja + Subsidio Mi Casa Ya`).
  - Cálculo de `saldo_faltante`. Si existe saldo, calcula la cuota mensual requerida diferida a los meses de entrega del proyecto (ej. 24 meses).
- [x] **Desglose de Crédito Hipotecario (70% después de entrega):**
  - Cálculo de amortización mensual a cuota fija (sistema francés PMT) a 20 años al 12% E.A.
- [x] **Doble Criterio de Viabilidad:** Valida que la cuota inicial esté cubierta (o diferida pagable) **Y** que la cuota mensual del crédito no supere el 40% del salario.

### G. Recomendación por Tipologías y Proyecto de Interés (`proyecto_interes`)
- [x] **Exclusión Estricta VIS / VIP:** Filtra automáticamente si el precio excede los topes legales (90 SMMLV para VIP, 135/150 para VIS).
- [x] **Evaluación del Proyecto de Interés:**
  - Si el usuario declara un proyecto por el que preguntó, el sistema emite `evaluacion_proyecto_interes`.
  - Si no es viable, explica la razón exacta (falta de subsidio, excede 40% de cuota, fuera de tope legal).
  - Si es viable, se prioriza automáticamente en la **posición #1 (`matching_projects[0]`)**.
- [x] **Propagación de Brochure:** Incluye `brochure_url` en cada recomendación para renderizar el botón "Ver Brochure" en el frontend o CRM.

---

## 2. Lo que Debes Remarcar en la Presentación / Demo (Highlights)

### 💡 Highlight 1: "Nada es una caja negra (Explicabilidad RNF-02)"
> *Remarcar:* "A diferencia de un algoritmo opaco, nuestro motor no solo dice si un cliente califica o no. Devuelve la justificación matemática exacta: el desglose de su subsidio, sus motivos de rechazo si los hay, y el desglose paso a paso del score."

### 💡 Highlight 2: "Matemática Financiera Real de Colombia (Cierre 30% / 70%)"
> *Remarcar:* "El motor aplica la estructura financiera real de la compra de vivienda en Colombia. Valida que los aportes del cliente (cesantías, ahorros y subsidios concurrentes) cubran el 30% de la cuota inicial, y calcula la cuota amortizada del crédito hipotecario del 70% restante a 20 años, asegurando que jamás supere el 40% de los ingresos del hogar."

### 💡 Highlight 3: "Evaluación Transparente del Proyecto de Interés"
> *Remarcar:* "Si el usuario llega preguntando por un proyecto específico (ej. Versalles), el motor no lo ignora. Lo evalúa financieramente y, si es viable, lo prioriza como su primera opción. Si no es viable, le explica con números claros al asesor la razón exacta por la cual no califica (ej. la cuota del crédito superaría el 40% de sus ingresos)."

### 💡 Highlight 4: "Arquitectura Stateless y Desacoplada (Próxima para Salesforce / WhatsApp)"
> *Remarcar:* "El motor es un microservicio puro en FastAPI, completamente desacoplado de la interfaz. No asume responsabilidades de frontend ni de NLP. Consume un JSON estructurado y devuelve un JSON enriquecido con URLs de brochures y métricas, listo para ser consumido por un CRM como Salesforce, un agente de WhatsApp o una aplicación web."

---

## 3. Ejemplo de Script para la Demostración

1. **Mostrar el endpoint `GET /afiliados/1018300400`:**
   - *Ver como precarga edad (31), categoría B, antigüedad (24 meses) y zona urbana.*
2. **Ejecutar `POST /perfilar` enviando un Lead con `proyecto_interes: "Versalles"`:**
   - *Destacar que la respuesta trae `financial_score.viable: "SI"`.*
   - *Destacar la prioridad `ALTA (90/10)`.*
   - *Mostrar `evaluacion_proyecto_interes`: `viable: true`.*
   - *Mostrar `matching_projects[0]`: Ver los números detallados de la cuota inicial del 30% ($45.000.000) cubierta con subsidios y la cuota del crédito ($1.111.555/mes) respetando el límite del 40% ($1.160.000/mes).*
3. **Ejecutar `POST /perfilar` enviando un Lead con ingresos de $1.500.000 preguntando por un proyecto de $210.000.000:**
   - *Mostrar cómo `evaluacion_proyecto_interes` responde `viable: false` y explica el motivo matemático exacto de por qué excede la capacidad de pago.*
   - *Mostrar la recomendación alternativa del subsidio de arrendamiento.*
