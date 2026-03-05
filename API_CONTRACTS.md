# 🤝 CONTRATOS DE INTEGRACIÓN (API CONTRACTS)
**Proyecto:** AstrologIA P001
**Versión:** 1.0 (Sprint 02)
**Destino:** Frontend Developers (Lovable / Next.js)

Este documento sirve como "Acuerdo Legal de Datos" entre el **Diseño Visual (Frontend)** y el **Servidor de Cálculos (Backend)**. 
Para que Lovable se pueda conectar a la velocidad de la luz, toda petición hecha desde el Frontend debe respetar estas estructuras.

---

## CONTRATO 1: SEGURIDAD UNIVERSAL (AUTH)
El Backend de AstrologIA asume que el Frontend usa `supabase-js` para iniciar la sesión del usuario.
**Regla Estricta:** NINGÚN endpoint del Backend calculará o entregará datos si no recibe el Token JWT del usuario en la petición.

* **Headers Obligatorios en TODAS las llamadas al Backend:**
```http
Authorization: Bearer <JWT_ENVIADO_POR_SUPABASE>
Content-Type: application/json
```

---

## CONTRATO 2: CALCULAR CARTA NATAL (CORE MVP)
**Endpoint:** `POST /api/carta-natal`
**Propósito:** Calcular posiciones planetarias con Swiss Ephemeris (`pySwisseph`).

### 📩 Request Body (Lo que Lovable debe enviar)
```json
{
  "year": 1990,
  "month": 6,
  "day": 15,
  "hour": 14.5,
  "lat": 40.4168,
  "lon": -3.7038
}
```
*(Nota: "hour" debe ser en formato decimal UTC).*

### 📤 Response Body (Lo que Lovable recibirá)
```json
{
  "status": "success",
  "data": {
    "planets": {
      "Sun": { "longitude": 84.22, "sign": 2, "degree": 24.22 },
      "Moon": { "longitude": 346.75, "sign": 11, "degree": 16.75 }
      // ... Mercury, Venus, Mars, Jupiter, Saturn y Ascendant
    },
    "houses": {
      "House_1": 201.76,
      "House_2": 229.42
      // ... Hasta House_12
    }
  }
}
```
*(Con este JSON estructurado, Lovable puede pintar la rueda zodiacal y los textos de "Tienes el Sol en Géminis").* 

---

## CONTRATO 3: MATRIZ DE SINASTRÍA 100x100 (`Módulo 11`)
**Endpoint:** `POST /api/sinastria`
**Propósito:** Cruza automáticamente los planetas de dos personas (Persona 1 y Persona 2) y devuelve los aspectos geométricos que impactan en su energía conjunta, junto con un Score Global de Compatibilidad (0 a 100).

### 📩 Request Body
```json
{
  "p1_year": 1990, "p1_month": 6, "p1_day": 15, "p1_hour": 14.5, "p1_lat": 40.41, "p1_lon": -3.70,
  "p2_year": 1992, "p2_month": 8, "p2_day": 2, "p2_hour": 9.0, "p2_lat": 41.38, "p2_lon": 2.15
}
```

### 📤 Response Body
```json
{
  "status": "success",
  "data": {
    "global_compatibility_score": 87.5,
    "synastry_matrix": [
      {
        "p1_planet": "Venus",
        "p2_planet": "Mars",
        "aspect": "Trine",
        "orb_degrees": 1.2,
        "energy_score": 3.8
      }
    ]
  }
}
```

---

## CONTRATO 4: TRANSIT IMPACT SCORING V2 (`Módulo 3`)
**Endpoint:** `POST /api/transit-scoring`
**Propósito:** Proyecta cómo los tránsitos lentos (Júpiter a Plutón) impactarán los planetas natales del usuario en los próximos X días. 

### 📩 Request Body
```json
{
  "user_year": 1990, "user_month": 6, "user_day": 15, "user_hour": 14.5, "user_lat": 40.41, "user_lon": -3.70,
  "start_year": 2026, "start_month": 3, "start_day": 5, "days_to_check": 7
}
```

### 📤 Response Body
```json
{
  "status": "success",
  "data": {
    "timeline": [
      {
        "date": "2026-03-05",
        "total_impact_score": 12.4,
        "key_activations": [
          { "transit": "Pluto", "natal": "Moon", "aspect": "Square", "impact": 8.0 }
        ]
      }
    ]
  }
}
```

## CONTRATO 5: CAREER & VOCATION OPTIMIZER (`Módulo 14`)
**Endpoint:** `POST /api/career-vocational`
**Propósito:** Analiza el Medio Cielo y el Sol para generar un Arquetipo Laboral y áreas de industria donde el usuario pueda brillar y monetizar mejor.

### 📩 Request Body
```json
{
  "year": 1990, "month": 6, "day": 15, "hour": 14.5, "lat": 40.41, "lon": -3.70
}
```

### 📤 Response Body
```json
{
  "status": "success",
  "data": {
    "midheaven_sign": "Leo",
    "career_blueprint": {
      "recommended_industries": "Liderazgo, Emprendimiento, Medios Visibles",
      "natural_soft_skills": ["Iniciativa", "Carisma de Venta"],
      "wealth_expansion_key": "Tu expansión natural se activa con temáticas de Cáncer"
    }
  }
}
```

---

## CONTRATO 6: DECISION WINDOW PLANNER (`Módulo 16`)
**Endpoint:** `POST /api/decision-window`
**Propósito:** Escanea los próximos meses y busca días de máxima suerte/armonía (Júpiter-Sol) omitiendo fallas (Merc Retrógrado) para hacer lanzamientos de negocios.

### 📩 Request Body
```json
{
  "user_year": 1990, "user_month": 6, "user_day": 15, "user_hour": 14.5, "user_lat": 40.41, "user_lon": -3.70,
  "start_year": 2026, "start_month": 3, "start_day": 5,
  "end_year": 2026, "end_month": 5, "end_day": 5,
  "goal_type": "business"
}
```

### 📤 Response Body
```json
{
  "status": "success",
  "data": {
    "top_recommended_dates": [
      {
        "date": "2026-03-22",
        "confidence_score": 15,
        "insight": "Nuevo Ciclo de Identidad y Abundancia. Máxima suerte."
      }
    ]
  }
}
```

---

## 🚧 CONTRATOS FUTUROS (Ventas & Producto)
* **Contrato 5:** Stripe Checkout & Webhooks.
* **Contrato 6:** Hub Shadow (Desencriptación de contenido Supabase).

---
**CTO Note:** Cumplir esto = 10 landings de Lovable integradas en 1 hora.

## 6. MÓDULO 2 & 3: Decodificador de Heridas Kármicas (Karmic Wound & Soul Purpose)
**Descripción:** Calcula la posición de Quirón (Herida Central) y el Nodo Norte (Evolución del Alma) usando efemérides Moshier e inyecta la interpretación arquetípica avanzada.
**Endpoint:** `/api/karmic-wound`
**Método:** `POST`
**Autorización:** Requerida (Bearer Token)
**Rate Limit:** 5/minute

**Request Payload:**
```json
{
  "year": 1990,
  "month": 5,
  "day": 15,
  "hour": 14.5,
  "lat": 40.7128,
  "lon": -74.0060
}
```

**Response (Success - 200 OK):**
```json
{
  "status": "success",
  "metadata": {
    "engine": "Karmic Wound & Soul Purpose (Módulos 2 & 3)"
  },
  "data": {
    "chiron": {
      "sign": "Cancer",
      "core_wound": "La Herida del Abandono y el Hogar...",
      "healing_path": "Sanas creando 'Hogares Sagrados'..."
    },
    "north_node": {
      "sign": "Aquarius",
      "soul_evolution_path": "Tu alma evolucionará cuando dejes la necesidad de aprobación aplaudida (Leo)..."
    }
  }
}
```

## 7. MÓDULO 7: Arquitectura de la Riqueza (Wealth Blueprint)
**Descripción:** Calcula la posición de Júpiter (Expansión) y Saturno (Bloqueos) para generar la estrategia financiera y el patrón de autosabotaje del usuario.
**Endpoint:** `/api/wealth-blueprint`
**Método:** `POST`
**Autorización:** Requerida (Bearer Token)
**Rate Limit:** 5/minute

**Request Payload:**
```json
{
  "year": 1990,
  "month": 5,
  "day": 15,
  "hour": 14.5,
  "lat": 40.7128,
  "lon": -74.0060
}
```
