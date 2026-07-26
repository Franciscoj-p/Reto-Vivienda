# Motor de Perfilamiento — Asesor Digital de Vivienda (Colsubsidio)

> Microservicio REST inteligente para perfilamiento, evaluación financiera de cuotas y subsidios, y recomendación de vivienda de interés social (VIS/VIP) para Colsubsidio.

---

## 📌 Descripción del Proyecto

El **Motor de Perfilamiento de Vivienda** es una solución tecnológica diseñada para automatizar la evaluación de elegibilidad legal, el cálculo de subsidios gubernamentales y de caja, y la recomendación de proyectos inmobiliarios.

El sistema procesa leads de vivienda en tiempo real y construye un diagnóstico financiero completo, determinístico y transparente, listo para ser consumido por un CRM comercial (ej. Salesforce/Hubspot) o interfaces de usuario (Chatbots, WhatsApp, Web Apps).

---

## ⚙️ Factores Clave de Diseño

- **100% Determinístico y Auditable (RNF-02):** Ninguna decisión es una caja negra. Cada evaluación entrega el desglose exacto de subsidios, score numérico (0-100), motivos de rechazo explicados y la matemática del cierre financiero.
- **100% Configurable (`app/config.py`):** Todos los parámetros normativos (SMMLV 2026, topes VIS/VIP, matrices de subsidios, tasas de interés hipotecario, plazos y pesos de scoring) están centralizados en un único archivo de configuración editable sin alterar el código del motor.
- **Capa de Abstracción de Datos Pluggable (`app/repositories/`):** Implementa el patrón Repositorio + Adaptador (`Protocol`). Las fuentes de prueba (CSV/JSON) pueden ser reemplazadas por bodegas de datos empresariales (SQL Server, Snowflake, Redshift) o APIs REST/gRPC externas mediante configuración limpia (`DATA_SOURCE`), **sin modificar la lógica de negocio del motor ni las reglas**.
- **Estricta Separación de Responsabilidades:** Microservicio *stateless* desacoplado de las capas de presentación. No realiza procesamiento de lenguaje natural (NLP) ni genera elementos gráficos; consume JSON estructurado y devuelve JSON enriquecido.
- **Matemática Financiera Real de Colombia (Ley de Vivienda):**
  - **Cuota Inicial (30%):** Cubierta por cesantías, ahorros y subsidios concurrentes (Caja + Mi Casa Ya + SISBEN). Si existe saldo faltante, calcula la cuota mensual diferida en los meses de entrega del proyecto.
  - **Crédito Hipotecario (70%):** Amortización fija (PMT) a 20 años al 12% E.A. validando que la cuota del crédito jamás supere el 40% del salario del comprador.

---

## 📈 ¿Por qué el Sistema es Escalable?

1. **Arquitectura Stateless (Escalamiento Horizontal Ilimitado):**
   - El motor es 100% libre de estado (*stateless*). No guarda sesiones ni memoria compartida entre peticiones.
   - Permite desplegar **múltiples réplicas en paralelo** en entornos como Kubernetes, AWS ECS o Google Cloud Run detrás de un balanceador de carga sin necesidad de sincronizar sesiones.
2. **Baja Latencia y Alto Rendimiento (< 50 ms por respuesta):**
   - Toda la evaluación se ejecuta en memoria con algoritmos optimizados, respondiendo en **menos de 50 milisegundos**, superando holgadamente la meta de latencia `< 2 segundos` (RNF-03).
3. **Escalabilidad Funcional y Modularidad:**
   - Diseñado bajo el principio de responsabilidad única y pipelines aislados (`Reglas ➔ Scoring ➔ Matching ➔ CRM`). Agregar una nueva regla legal o norma es tan simple como registrar una nueva función pura en la lista `_REGLAS_RECHAZO`.
4. **Capa Abstraída de Datos (Fácil Integración con BDs y Caché):**
   - Gracias al patrón Repositorio (`app/repositories/`), escalar la fuente de datos desde archivos locales hacia cachés distribuidas (Redis), réplicas de lectura SQL o bodegas de datos masivas (Snowflake/Redshift) solo requiere cambiar la configuración (`DATA_SOURCE`), sin alterar el core del motor.

---

## 🚀 Funcionalidades Principales

- [x] **Consulta de Afiliados (`GET /afiliados/{id_usuario}`):** Precarga automática de datos del afiliado (edad, categoría A/B/C, antigüedad, personas a cargo, estrato, zona urbana/rural).
- [x] **Acceso de Datos Intercambiable (`app/repositories/`):** Arquitectura desacoplada mediante patrones de repositorio que permite conectar de ser necesario bodegas de datos reales, bases de datos SQL o APIs externas sin modificar el código core.
- [x] **Evaluación de Reglas Duras:** Filtros de propietario previo, antigüedad mínima (≥6 meses), subsidio previo (con excepción legal de arrendamiento) y capacidad de crédito mínima.
- [x] **Matriz de Subsidios 2026 (SMMLV $1.750.905):** Subsidio Colsubsidio (30 o 20 SMMLV), Subsidio Concurrente Mi Casa Ya (20 SMMLV) y SISBEN (matriz urbana/rural).
- [x] **Segmentación Automática de Caja:** Clasificación en `Joven` (<39 años y sin personas a cargo), `Básico`, `Medio` o `Alto`.
- [x] **Scoring y Priorización Comercial:** Regla 90/10 para afiliados (+25 puntos a afiliados / -10 penalización a no afiliados) y Override RN-04 para clientes financieramente resueltos.
- [x] **Recomendación por Tipología y Brochure:** Exclusión estricta VIS/VIP por tope municipal (90, 135, 150 SMMLV) e inclusión de `brochure_url`.
- [x] **Evaluación de Proyecto de Interés (`proyecto_interes`):** Respuesta explícita de viabilidad o motivo técnico de rechazo; priorización automática en la primera opción (`matching_projects[0]`) si es viable.
- [x] **Ruta de Arrendamiento Sugerido:** Alternativa de ahorro (0.6 SMMLV/mes por 24 meses) si el lead no logra el cierre inicial hoy.

---

## 🎨 Repositorios de Interfaz Visual

El motor de perfilamiento se encuentra desacoplado y puede integrarse con diferentes interfaces visuales. Los repositorios de simulación visual asociados son:

- 💬 **Interfaz Simulación CRM:** [Repositorio CRM Sim](https://github.com/Franciscoj-p/SimCrm)
- 📱 **Interfaz Simulación WhatsApp / Bot:** [Repositorio WhatsApp Sim](https://github.com/Franciscoj-p/SimWha) 
- 👾 **Interfaz Simulación Roadmap Interactivo** [Repositorio Roadmap](https://github.com/maker1dytecnologia-star/vivienda)

---

## 🛠️ Instalación y Uso Local

### Prerrequisitos
- Python 3.10+
- `pip`

### 1. Clonar e Instalar Dependencias
```bash
git clone https://github.com/usuario/Reto-Vivienda.git
cd Reto-Vivienda
pip install -r requirements.txt
```

### 2. Ejecutar el Servidor
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- **Documentación Interactiva (Swagger):** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/health`

---

## 📖 Ejemplos de Uso de la API

### Consulta de Afiliado (`GET /afiliados/{id_usuario}`)
```bash
curl -X GET http://localhost:8000/afiliados/1018300400
```

### Perfilamiento de Lead (`POST /perfilar`)
```bash
curl -X POST http://localhost:8000/perfilar \
  -H "Content-Type: application/json" \
  -d '{
    "id_usuario": "1018300400",
    "nombre": "Diana Martínez",
    "afiliado": true,
    "ingresos_mensuales": 2900000,
    "proyecto_interes": "Versalles"
  }'
```

---

## 📂 Estructura del Proyecto

```
├── app/
│   ├── api/                # Endpoints FastAPI y esquemas Pydantic (schemas.py, routes.py)
│   ├── core/               # Lógica del motor (reglas.py, scoring.py)
│   ├── data/               # Adaptadores de datos (afiliados_csv.py, catalogo.py)
│   ├── repositories/       # Abstracción e interfaces de datos (interfaces.py, afiliados_csv.py)
│   ├── config.py           # Parámetros editables de negocio y matemática financiera
│   └── motor.py            # Orquestador del flujo de perfilamiento
├── data/
│   ├── afiliados.csv       # Simulación de bodega de datos de afiliados Colsubsidio
│   └── proyectos.json      # Catálogo de proyectos, tipologías y buyer personas
├── docs/                   # Documentación técnica detallada
│   ├── API.md              # Especificación técnica de contratos API
│   ├── rules.md            # Explicación funcional de reglas de negocio
│   ├── REVISION_SISTEMA.md # Análisis crítico del algoritmo y evaluación CRM
│   └── CHECKLIST_DEMO.md   # Checklist de funcionalidades y guía para la demo
├── main.py                 # Punto de entrada de la aplicación FastAPI
└── README.md
```

---

## ⚠️ Disclaimer / Exención de Responsabilidad

> **Nota:** Este proyecto fue desarrollado para el **Reto Vivienda**. Los datos de prueba, proyectos y perfiles de afiliados utilizados en el sistema son **simulados**, asumiendo atributos y estructuras que en un entorno de producción real se obtendrían de fuentes empresariales externas (como la **bodega de datos de afiliados de Colsubsidio** y sistemas CRM).  
> 
> Asimismo, las matrices de subsidio, tasas de interés, plazos y parámetros de scoring fueron construidos a partir de **información pública recopilada de portales oficiales de Colsubsidio y normatividad colombiana vigente para el año 2026**. Todos los parámetros y reglas son **100% configurables** en el archivo `app/config.py` para adaptarse a cualquier actualización futura de la caja o regulación gubernamental sin requerir modificaciones en el código fuente.
