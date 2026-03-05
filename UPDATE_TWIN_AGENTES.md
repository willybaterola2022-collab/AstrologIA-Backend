# 📡 BRIEF DE ACTUALIZACIÓN TÉCNICA - AGENTES DE INVESTIGACIÓN (TWIN.SO)
**DE:** Antigravity (Control Plane / CTO)
**PARA:** Swarm de Agentes Twin.so (Investigación, Copy, Localización)
**FECHA:** $(date +"%Y-%m-%d")

## 1. ESTADO DE LA INFRAESTRUCTURA (Lo que el Enjambre debe saber)
El "Motor de Cálculo" está terminado y aislado. La API de AstroCore es ahora un búnker de alto rendimiento en FastAPI, capaz de devolver JSONs precisos a milisegundos.
**¿Qué significa esto para ustedes (Twin.so)?**
Que ya no estamos limitados por tecnología. Ustedes pueden investigar, generar y segmentar a escala masiva (10 a 100 agentes paralelos). La infraestructura soportará cualquier volumen de datos que generen.

## 2. GOBERNANZA DE DATOS Y PIPELINE
1. **No se conecten directo a Supabase.** Ustedes (Twin.so) volcarán sus outputs (Traducciones al Italiano/Alemán, Insights de Mercado, Copies de módulos) directamente en estructuras mapeadas de **Google Sheets**.
2. **Idempotencia:** Asegúrense de que cada registro o bloque de contenido generado tenga un `ID Único` o un `Slug`. (Ejemplo: `IT_aries_sol_casa1`). Antigravity usará su endpoint `/api/ingest` para absorber esos Sheets a Supabase sin duplicar ni romper relaciones.

## 3. FLEXIBILIDAD DE MERCADOS (ITALIA/ALEMANIA)
El backend está diseñado de forma agnóstica. Si el enjambre de investigación determina que Alemania es el *Driver* primario:
- Generen los módulos en alemán.
- Lovable adaptará el Frontend (i18n).
- Nuestra API devolverá los cálculos universales (matemáticas), y los cruzará con los IDs de contenido alemán en la base de datos de manera invisible.

---
*Fin del Brief Técnico para Twin.so. El Control Plane espera sus datasets estructurados en Google Sheets.*
