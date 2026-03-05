# 🎯 DIRECTIVAS CLAUDE & TWIN (ORQUESTACIÓN Y EJECUCIÓN SPRINT 2 Y 3)
**De:** Bárbara (CEO) & AstrologIA-Backend (CTO)
**Para:** Claude (Orquestador Principal) & Twin.so (Swarm Generativo)
**Fecha:** $(date +"%Y-%m-%d")

---

## 🗂️ 1. CONTEXTO TÉCNICO VITAL (EL BÚNKER)
**Para Claude y Twin:** El Backend ("Control Plane" en FastAPI) ya ha finalizado su arquitectura matemática:
- Calcula posiciones de Planetas Clásicos, Transaturninos, Nodos Kármicos (Lilith, Quirón, Nodo Norte), Casas Placidus y Carta Dracónica.
- Expone una Matriz Analítica de Aspectos Exactos (`/api/carta-natal`).
- Nuevo Endpoint Creado: Tránsitos Avanzados comparando Fechas (`/api/transitos`).
- El servidor incluye Middleware JWT anti-hackers y Rate Limiting (Anti-DDoS) y está documentado en `API_CONTRACTS.md`.

* **Implicación:** La tecnología ya no es el cuello de botella. Son 100% libres de diseñar el contenido más mastodóntico y complejo posible, porque el servidor Python se los va a procesar en paralelo y a milisegundos. Nuestro límite ahora es exclusivamente la velocidad de generación del Copywriting Inbound.

---

## 🧠 2. INSTRUCCIONES PARA CLAUDE (MASTER ORCHESTRATOR)

1. **Gestión del Rate Limiting (El Escudo):** El CTO ha puesto un bloqueo provisorio de "5 peticiones por IP/minuto". Necesitamos que diseñes la **lógica de negocio por tiers** (Gratis Logueado vs. Premium Pagador) para que Antigravity conecte ese límite al Token JWT y no a la IP del usuario.
2. **Definición Estructural (El MVP de los Módulos):** En base a las métricas e insights de la investigación de Twin, define explícitamente qué recursos se crearán de los 120 módulos y qué forma adoptarán en nuestras 10 *Super Landings de Lovable* (Ebooks, Webinars, Podcast Interno).
3. **El Inbound Funnel Freemium a Premium:** Tienes la misión de interconectar estas Landing Pages para enamorar a los prospectos y moverlos paso a paso a nuestros 2 *Rockstar Products* (Ej. Cosmic Blueprint).
4. **Diseñar el Pipeline de Ingesta:** Asegúrate de que los millones de caracteres producidos por Twin estén perfectamente ordenados en Google Sheets (Con ID/Slugs Únicos). Luego de eso, le harás la solicitud técnica al CTO para crear el endpoint `/api/ingest` hacia Supabase.

---

## 🐝 3. INSTRUCCIONES PARA TWIN.SO (SWARM DE INVESTIGACIÓN)

1. **Fase Actual: Investigación y Market Fit.** Desplieguen todo su músculo analítico (10 a 100 agentes en paralelo). Investiguen drivers de conversión astrológica en mercados de altísima rentabilidad (Europa Central/Alemania e Italia). Su investigación va a dictaminar qué módulos, productos y *storytelling* tendrán prioridad de desarrollo.
2. **Regla de Ejecución (Contenido Póstumo):** Ninguna línea de Copy para Supabase se escribe de forma masiva hasta no concluir y cruzar el informe de Mercado con el Equipo Directivo (Bárbara + Claude + CTO).
3. **La Bibliografía y la Voz de AstrologIA:** Cuando inicie la fase de redacción de Copywriting (Blogs, Módulos Inbound, Textos para Supabase, etc.), **NO SE DEDICARÁN A COPIAR Y PEGAR**.
	- Su misión es actuar con Liderazgo de Opinión y Autoridad Psicológica.
	- Combinen las variables matemáticas que entregará el Servidor (Quirón, Nodos, Retorno de Saturno, 4 Elementos, Tránsitos) con narrativa clínica y curación astral.
	- Generen explicaciones prácticas y tangibles ("Educar Demostrando").
4. **Localización e Idioma (i18n):** Nuestro Backend devuelve matemáticas. Ustedes tendrán el trabajo de crear los Copies en el idioma target (Italiano/Alemán) para que Lovable se los apropie en pantalla de forma nativa.

*(Quedo atento. Que Claude procese esta información y proponga el Master Plan del Ecosistema de Contenidos).*
