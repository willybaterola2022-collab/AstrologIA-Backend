# 🌌 AstrologIA MVP — Fuente de Conocimiento para Diagrama Visual (NotebookLLM / Claude)

> **Instrucciones para el Agente de Diagramación:**
> Lee este documento completo. Tu tarea es generar un **diagrama visual tipo "Universe Map"** que muestre la arquitectura del MVP de AstrologIA: sus capas, módulos, flujos de datos y la relación entre los planetas/arquetipos y los endpoints del backend. Usa Mermaid, GraphViz o cualquier herramienta que produzca un resultado visualmente impactante.

---

## 🏗️ CAPA 1 — EL MOTOR ASTRONÓMICO (Backend FastAPI + Swiss Ephemeris)

**Tecnología:** Python / FastAPI / Swiss Ephemeris (Moshier Ephemeris para MVP)
**Función:** Calcula posiciones planetarias exactas en milisegundos dado: `año, mes, día, hora, latitud, longitud`

**Planetas calculados:**
- ☀️ Sol (Sun) — `swe.SUN`
- 🌙 Luna (Moon) — `swe.MOON`
- ☿ Mercurio — `swe.MERCURY`
- ♀ Venus — `swe.VENUS`
- ♂ Marte — `swe.MARS`
- ♃ Júpiter — `swe.JUPITER`
- ♄ Saturno — `swe.SATURN`
- ⛢ Urano — `swe.URANUS`
- ♆ Neptuno — `swe.NEPTUNE`
- ♇ Plutón — `swe.PLUTO`
- ⚷ Quirón — `swe.CHIRON`
- ☊ Nodo Norte — `swe.TRUE_NODE`
- 🏠 Ascendente — `swe.houses()` (Sistema Placidus)

---

## 🧠 CAPA 2 — EL MOTOR PSICOLÓGICO (Advanced Content Database)

**Archivo:** `app/advanced_content_db.py`
**Función:** Para cada planeta en cada uno de los 12 signos, devuelve la interpretación clínica/arquetípica correspondiente.

**Estructura de datos para cada planeta:**

| Planet | Keys disponibles |
|---|---|
| Quirón | `Chiron_Wound`, `Chiron_Healing` |
| Nodo Norte | `North_Node` |
| Júpiter | `Jupiter_Wealth` |
| Venus | `Venus_Profile` |
| Marte | `Mars_Pluto_Friction` |
| Luna | `Moon_Core_Emotion`, `Moon_Childhood`, `Moon_Healing` |
| Mercurio | `Mercury_Thinking`, `Mercury_Communication`, `Mercury_B2B` |
| Neptuno | `House12_Shadow_Talent` |
| Sol | `Sun_Archetype`, `Sun_Purpose`, `Sun_Shadow` |
| Ascendente | `Ascendant_Mask`, `Ascendant_Gift`, `Ascendant_Blind_Spot` |
| Saturno | `Saturn_Return_Challenge`, `Saturn_Return_Opportunity`, `Saturn_Return_Mantra` |

---

## 🚀 CAPA 3 — LOS 11 ENDPOINTS MVP (API REST con JWT Auth + Rate Limiting)

Todos los endpoints requieren:
- `Authorization: Bearer <JWT_TOKEN>` (Supabase Auth)
- `POST` con payload: `{year, month, day, hour, lat, lon}`

```
┌─────────────────────────────────────────────────────┐
│                  AstrologIA API MVP                  │
│                  /api/[endpoint]                     │
├─────────────────────────────────────────────────────┤
│  IDENTIDAD Y PROPÓSITO                              │
│  ├── /sun-purpose      → Arquetipo Central + Sombra │
│  ├── /ascendant-mask   → Máscara Social Real (GPS)  │
│  └── /karmic-wound     → Quirón + Nodo Norte        │
├─────────────────────────────────────────────────────┤
│  RIQUEZA Y CARRERA                                  │
│  ├── /wealth-blueprint → Júpiter + Saturno          │
│  ├── /career-optimizer → MC + Júpiter + Sol         │
│  └── /saturn-return    → Guía del Retorno (28-30y)  │
├─────────────────────────────────────────────────────┤
│  AMOR, SOMBRA Y VÍNCULOS                           │
│  ├── /venus-attraction → Lenguaje del Amor          │
│  └── /mars-friction    → Disparador de Fricción     │
├─────────────────────────────────────────────────────┤
│  PSICOLOGÍA Y MENTE                                │
│  ├── /moon-conditioning → Luna + Infancia           │
│  ├── /mercury-os        → Sistema Mental B2B        │
│  └── /shadow-talents    → Talentos Ocultos (C.12)   │
└─────────────────────────────────────────────────────┘
```

---

## 🗄️ CAPA 4 — BASE DE DATOS (Supabase / PostgreSQL con RLS)

**Tablas activas:**
| Tabla | Propósito |
|---|---|
| `profiles` | Datos del usuario (fecha, hora, lat/lon de nacimiento) |
| `cosmic_blueprint` | Cache del perfil completo generado |
| `transit_events` | Ventanas predictivas futuras |
| `synastry_insights` | Matrices de compatibilidad de pareja |

---

## 🌊 FLUJO COMPLETO DE DATOS (Para el Diagrama)

```
USUARIO
  │
  ▼ [fecha + hora + lugar de nacimiento]
FRONTEND (Lovable / Base44)
  │
  ▼ [POST /api/[endpoint] + JWT]
ASTROLOGÍA API (FastAPI)
  │
  ├──▶ Swiss Ephemeris → "Sol en Tauro, Luna en Capricornio, Venus en Aries..."
  │
  ├──▶ Advanced Content DB → "El Constructor Paciente... Sientes seguridad cuando hay estructura..."
  │
  └──▶ Response JSON en < 50ms
         │
         ▼
     Supabase (Cache del perfil)
         │
         ▼
     USUARIO recibe su espejo psicológico exacto
```

---

## 🔮 MÓDULOS FUTUROS (Fase 2 — Para ampliar el Universo)

Organizados por dominio para el diagrama:

**Dominio Tiempo & Predicción:**
- Luna Progresada (ciclos emocionales de 28 días)
- Score de Tránsitos Diario (0-100)
- Ventana de Retorno Solar (tu nuevo año personal)

**Dominio Relaciones:**
- Sinastría Completa (12 aspectos inter-personales)
- Composite Chart (la tercera entidad de la pareja)
- Compatibilidad de Socios de Negocio

**Dominio Evolutivo:**
- Retorno de Júpiter (cada 12 años — ciclo de expansión)
- Progresiones Secundarias (la vida interior del alma)
- Ciclos de Plutón Generacionales

**Dominio Cuántico/Ancestral:**
- Asteroides clave: Lilith, Ceres, Palas Atenea
- Linaje Kármico (Nodo Sur profundo)
- Activaciones de Eclipse (máxima transformación)
