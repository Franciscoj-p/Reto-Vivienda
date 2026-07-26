# Plataforma VIVI — Motor Inteligente de Decisión y Reglas Configurable

> **Core Backend del Ecosistema VIVI | Colsubsidio 2026**  
> Microservicio REST inteligente (*stateless*, determinístico y configurable) que impulsa la toma de decisiones, evaluación financiera de cuotas y subsidios, y priorización de prospectos de vivienda de interés social (VIS/VIP).

---

## 📌 Descripción General del Ecosistema VIVI

La **Plataforma VIVI** es un ecosistema inteligente diseñado para transformar la gestión de prospectos en programas de vivienda de Colsubsidio, automatizando el proceso desde el primer contacto hasta la asignación priorizada a un asesor comercial.

La plataforma combina una experiencia de atención cercana y personalizada en múltiples canales con un **Motor Inteligente de Decisión** (contenido en este repositorio) que automatiza el análisis, la validación financiera y la priorización de cada prospecto. De esta manera, los equipos comerciales en Salesforce/Hubspot pueden concentrarse en brindar una asesoría de alto valor, mientras la tecnología se encarga de las tareas operativas y analíticas.

### Arquitectura General de la Solución (4 Componentes)

```
                       ┌─────────────────────────────────────────┐
                       │           PLATAFORMA VIVI               │
                       └────────────────────┬────────────────────┘
                                            │
         ┌──────────────────────────────────┼──────────────────────────────────┐
         │                                  │                                  │
┌────────┴─────────┐              ┌─────────┴────────┐                ┌────────┴────────┐
│ VIVI Conversacional│              │ VIVI Roadmap     │                │ VIVI CRM        │
│ (WhatsApp Bot)   │              │ Inteligente      │                │ Dashboard       │
│ https://whatsapp.│              │ https://roadmap. │                │ https://crm.    │
│ arnarcraft.uk    │              │ arnarcraft.uk    │                │ arnarcraft.uk   │
└────────┬─────────┘              └─────────┬────────┘                └────────┬────────┘
         │                                  │                                  │
         └──────────────────────────────────┼──────────────────────────────────┘
                                            │  (JSON API / REST)
                                            ▼
                       ┌─────────────────────────────────────────┐
                       │     MOTOR INTELIGENTE DE DECISIÓN       │
                       │     & REGLAS CONFIGURABLES (Este Repo)  │
                       │     - Validación de requisitos          │
                       │     - Cierre financiero (30%/70%)       │
                       │     - Subsidios concurrentes 2026       │
                       │     - Scoring 90/10 y priorización     │
                       │     - Rutas de acompañamiento           │
                       └─────────────────────────────────────────┘
```

---

## ⚙️ Capacidades del Motor de Decisión (Este Repositorio)

Este repositorio contiene la **lógica central de negocio, matemática financiera y motor de reglas configurables** que alimenta a todo el ecosistema VIVI:

1. **Motor de Reglas Configurable (`app/config.py`):**
   - Las políticas comerciales, valores de SMMLV 2026 ($1.750.905 COP), matrices de subsidio (Colsubsidio, Mi Casa Ya, SISBEN), topes de vivienda (90, 135, 150 SMMLV) y tasas de interés hipotecario están centralizados en `config.py` y pueden ser modificados por personal autorizado sin tocar el código fuente.
2. **Matemática Financiera Real de Colombia (Cierre 30% / 70%):**
   - **Cuota Inicial (30%):** Suma de cesantías, ahorros y subsidios concurrentes. Si existe un saldo faltante, calcula la cuota mensual diferida en el plazo de entrega del proyecto (ej. 24 meses).
   - **Crédito Hipotecario (70%):** Amortización fija (PMT) a 20 años al 12% E.A., asegurando que la cuota no supere el **40% de los ingresos del hogar**.
3. **Priorización Comercial y Scoring (0 a 100 puntos):**
   - Aplica la **Regla 90/10 de afiliados** (+25 pts a afiliados / -10 pts de penalización a no afiliados) y el **Override RN-04** para compradores resueltos financieramente.
4. **Evaluación Transparente del Proyecto de Interés (`proyecto_interes`):**
   - Si el lead consulta por un proyecto específico (ej. *Versalles*), el motor evalúa su viabilidad. Si es viable, lo posiciona en el **lugar #1 de recomendaciones (`matching_projects[0]`)**; si no lo es, explica el motivo técnico exacto al asesor.
5. **Rutas de Acompañamiento ("Un prospecto no elegible hoy es un futuro comprador"):**
   - Cuando el motor identifica que una persona aún no logra el cierre financiero hoy, no la descarta. Asigna la **Ruta de Arrendamiento Sugerido** (Subsidio de $1.050.543/mes por 24 meses = $25.213.032 COP) como plan estructurado de ahorro previo.
6. **Arquitectura *Stateless* y Repositorios Pluggable (`app/repositories/`):**
   - Permite cambiar la fuente de datos (CSV ➔ SQL Server, Snowflake, Redshift o APIs externas) modificando una variable de entorno (`DATA_SOURCE`), sin alterar el core del motor.

---

## 📈 ¿Por qué el Motor es Escalable?

1. **Sin Estado (*Stateless*):** No guarda sesiones en memoria entre peticiones. Permite escalamiento horizontal ilimitado en Kubernetes, AWS ECS o Google Cloud Run.
2. **Baja Latencia (< 50 ms):** Responde en menos de 50 milisegundos por evaluación, superando la meta de latencia de 2 segundos (RNF-03).
3. **Desacoplamiento Total:** La experiencia de usuario en WhatsApp o Web es 100% independiente del motor de decisión.

---

## 🛠️ Instalación y Uso Local

### Prerrequisitos
- Python 3.10+
- `pip`

### 1. Instalación
```bash
git clone https://github.com/usuario/Reto-Vivienda.git
cd Reto-Vivienda
pip install -r requirements.txt
```

### 2. Ejecución del Servidor
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
- **Portal de Navegación del Ecosistema:** `http://localhost:8000/`
- **Documentación Interactiva (Swagger):** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/health`

---

## 📖 Ejemplos de Uso de la API

### 1. Consulta de Afiliado (`GET /afiliados/{id_usuario}`)
```bash
curl -X GET http://localhost:8000/afiliados/1018300400
```

### 2. Perfilamiento de Lead (`POST /perfilar`)
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
│   ├── repositories/       # Abstracción de datos (interfaces.py, afiliados_csv.py)
│   ├── config.py           # Reglas de negocio y parámetros editables
│   └── motor.py            # Orquestador del flujo de perfilamiento
├── data/
│   ├── afiliados.csv       # Simulación de bodega de datos de afiliados Colsubsidio
│   └── proyectos.json      # Catálogo de proyectos y tipologías
├── docs/                   # Documentación técnica y especificaciones
│   ├── API.md              # Contratos y especificación API
│   ├── rules.md            # Explicación de reglas de negocio
│   ├── REVISION_SISTEMA.md # Análisis crítico y evaluación CRM
│   └── CHECKLIST_DEMO.md   # Checklist para la presentación
├── index.html              # Portal visual de navegación del Ecosistema VIVI
├── main.py                 # Punto de entrada de la API FastAPI
└── README.md
```

---

## ⚠️ Disclaimer / Exención de Responsabilidad

> **Nota:** Los datos de prueba, proyectos y perfiles de afiliados utilizados en el sistema son **simulados**, asumiendo atributos que en un entorno de producción real se obtendrían de fuentes empresariales externas (como la **bodega de datos de afiliados de Colsubsidio** y sistemas CRM).  
> 
> Asimismo, las matrices de subsidio, tasas de interés, plazos y parámetros de scoring fueron construidos a partir de **información pública recopilada de portales oficiales de Colsubsidio y normatividad colombiana vigente para el año 2026**. Todos los parámetros y reglas son **100% configurables** en el archivo `app/config.py`.
