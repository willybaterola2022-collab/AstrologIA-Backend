# AstrologIA Backend (Control Plane)

## Arquitectura del Proyecto

Este repositorio contiene la arquitectura **limpia** de AstrologIA, diseñada en Python y FastAPI, y completamente disociada de Lovable (Frontend). 

```
/AstrologIA-Backend
  ├── /app                    # Lógica principal
  │   ├── main.py             # Entrypoint FastAPI
  │   ├── /api                # Definición de Routers (endpoints)
  │   ├── /core               # Configuración (Supabase Client, Auth, Settings)
  │   └── /services           # Logica de negocio (ej: cálculos astrológicos)
  ├── requirements.txt        # Dependencias
  └── README.md
```

## Stack Técnico (Fase 1)
- **FastAPI**: Servidor API REST asíncrono y de alto rendimiento.
- **PySwisseph**: Libería oficial de Swiss Ephemeris para cálculo planetario de ultraprecisión.
- **Supabase**: Base de Datos unificada (`homfwprrzeigzltaamzo`).
- **Uvicorn**: ASGI Server.

## ¿Por qué esta arquitectura? (Opción B del Sprint 01)
Al construir esto "desde cero limpio", garantizamos la prevención del *Double Load Bug* anterior, aseguramos una asincronía real para servir las 10 landings sin bloqueo, y garantizamos que la lógica astrológica y de Stripe se mantenga aislada.

## Cómo correr esto localmente
1. **Activar Virtual Env:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Correr el servidor:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
4. **Docs Activas:** `http://localhost:8000/docs`

## Git Local Configurado
Ya hay un entorno `git` configurado localmente en esta carpeta.
Para conectarlo a tu GitHub:
```bash
git add .
git commit -m "Sprint 01 - Fundacion FastAPI backend limpio"
git remote add origin https://github.com/TU-USUARIO/AstrologIA-Backend.git
git push -u origin main
```
