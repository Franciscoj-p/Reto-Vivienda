# Plan — Motor de Perfilamiento (Asesor Digital de Vivienda, Colsubsidio)

Este documento es la bitácora de decisiones, arquitectura y checklist del proyecto.

---

## 1. Resumen de Estado del Sistema

- **Capa de Entrada y Esquemas (`app/api/schemas.py`):** Completado. Soporta `zona`, `edad`, `proyecto_interes`, `finanzas`, `condiciones_especiales`.
- **Capa de Datos de Afiliados (`data/afiliados.csv`, `app/repositories/`):** Completado. Incluye columnas `EDAD` y `ZONA` y su correspondiente mapeo dinámico.
- **Motor de Reglas (`app/reglas.py`):** Completado. Incluye reglas duras, topes VIS/VIP (fijos en 90 SMMLV para VIP), matriz de subsidios, programas concurrentes (Mi Casa Ya, SISBEN urbano/rural, arrendamiento) y segmentación de caja.
- **Scoring y Matching (`app/scoring.py`):** Completado. Matching por tipologías, afinidad categórica `buyerPersona`, propagación de `brochure_url`, evaluación obligatoria de `proyecto_interes` y priorización en posición #1 si es viable.
- **Orquestador (`app/motor.py`):** Completado. Ensambla `PerfilamientoResponse` estructurado e integra envío a CRM.
- **Documentación Técnica (`docs/`):**
  - `API.md`: Especificación técnica completa de contratos de entrada/salida y matriz de uso de atributos.
  - `rules.md`: Reglas de negocio funcionales actualizadas.
  - `REVISION_SISTEMA.md`: Análisis crítico del motor, límites algorítmicos, preparación para CRM y mapa de evolución hacia IA.

---

## 2. Checklist de Fases

### Fase 0 — Planeación
- [x] Revisar reglas de negocio y requerimientos
- [x] Definir modelo de datos del lead estructurado
- [x] Documentar principios de separación de responsabilidades (No NLP en Core, Stateless)

### Fase 1 — Capa de Datos (Afiliados y Proyectos)
- [x] Interfaces de repositorios (`AfiliadosRepository`, `ProyectosRepository`)
- [x] Adaptador CSV de afiliados con mapeo dinámico de columnas (`EDAD`, `ZONA`, etc.)
- [x] Endpoint `GET /afiliados/{id_usuario}`
- [x] Adaptador de proyectos JSON (`proyectos.json` con `tipologias` y `buyerPersona`)

### Fase 2 — Parámetros de Negocio (`app/config.py`)
- [x] Parámetros normativos 2026 (SMMLV $1.750.905)
- [x] Topes VIS/VIP (150, 135, 90 SMMLV) y cobertura regional
- [x] Matriz de subsidios y SISBEN urbano/rural
- [x] Pesos de scoring y desempate de segmentación de caja
- [x] Mapeo de columnas de afiliados e integración CRM

### Fase 3 — Esquemas de API (`app/api/schemas.py`)
- [x] Esquema `LeadInput` anidado con `zona`, `proyecto_interes`, `finanzas`, `condiciones_especiales`
- [x] Esquema de salida enriquecido con `brochure_url` y `evaluacion_proyecto_interes`

### Fase 4 — Motor de Reglas (`app/reglas.py`)
- [x] Reglas duras de rechazo (Propietario, Antigüedad, Subsidio Previo con excepción de arriendo, Ingresos)
- [x] Elegibilidad y monto de subsidio de vivienda
- [x] Subsidio concurrente Mi Casa Ya y SISBEN
- [x] Subsidio de arrendamiento sugerido
- [x] Segmentación de caja (Joven, Básico, Medio, Alto)

### Fase 5 — Scoring y Recomendación (`app/scoring.py`)
- [x] Prioridad comercial numérico + override RN-04
- [x] Matching por tipología y exclusión VIS/VIP
- [x] Afinidad histórica por buckets porcentuales (`buyerPersona`)
- [x] Propagación de `brochure_url`
- [x] Evaluación y priorización del `proyecto_interes`

### Fase 6 — Orquestación e Integración (`app/motor.py`)
- [x] Ensamble del JSON enriquecido estructurado
- [x] Cliente CRM de envío *best-effort*
- [x] Resumen determinista para el asesor

### Fase 7 — Documentación de Arquitectura y Evaluación (`docs/`)
- [x] Especificación de API y Contratos de Datos (`docs/API.md`)
- [x] Reglas de Negocio Funcionales (`docs/rules.md`)
- [x] Revisión Crítica del Sistema y Evaluación CRM (`docs/REVISION_SISTEMA.md`)
- [x] Bitácora del proyecto (`docs/plan.md`)