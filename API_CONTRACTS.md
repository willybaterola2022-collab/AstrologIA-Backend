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

## 🚧 CONTRATOS FUTUROS (SPRINTS 03 y 04)
*(Estos contratos los rellenará el CTO una vez apruebes el desarrollo de esos features).*

* **Contrato 3:** Stripe Checkout (Generación de Links de Pago).
* **Contrato 4:** Stripe Webhooks (Desbloqueo Automático del Producto tras el pago).
* **Contrato 5:** Hub Shadow (Traer contenido desencriptado de Supabase).

---
**CTO Note:** Cumplir esto = 10 landings de Lovable integradas en 1 hora.
