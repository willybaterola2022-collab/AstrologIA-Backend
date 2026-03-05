from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
import swisseph as swe
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings

# --- RATE LIMITING ---
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AstrologIA Backend (Control Plane)",
    description="API para conectar Lovable con Swisseph y Supabase",
    version="1.2.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",             # Entorno Local (Lovable)
        "https://*.vercel.app"               # Entorno Preview/Prod de Vercel
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

# --- AUTH MIDDLEWARE (JWT SUPABASE) ---
security = HTTPBearer()

def verify_jwt(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        # Usamos el secret de Pydantic BaseSettings (oculto en .env)
        payload = jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], options={"verify_aud": False})
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado. Lovable debe refrescar la sesion.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalido o corrompido.")

# --- SCHEMAS ---
class NatalChartRequest(BaseModel):
    year: int
    month: int
    day: int
    hour: float 
    lat: float
    lon: float

# --- ENDPOINTS ---
@app.get("/")
def read_root():
    return {"status": "ok", "message": "AstrologIA API is running"}

@app.post("/api/carta-natal")
@limiter.limit("5/minute")  # Limitado a 5 peticiones por minuto por IP para evitar ataques DDoS
def calculate_natal_chart(request: Request, req: NatalChartRequest, user: dict = Depends(verify_jwt)):
    """
    IMPORTANTE: API Astrologica Ultra-Avanzada
    Incluye planetas, Nodos kármicos, Carta Dracónica y Matriz de Aspectos.
    """
    try:
        # 1. Calcular Fecha Juliana
        julian_day = swe.julday(req.year, req.month, req.day, req.hour)
        
        # 2. Definir Cuerpos Celestes (Añadido Kármico: Quirón, Nodos, Lilith)
        planets = {
            "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, 
            "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER, 
            "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, 
            "Pluto": swe.PLUTO, "Chiron": swe.CHIRON, 
            "True_Node": swe.TRUE_NODE, # Nodo Norte Verdadero
            "Lilith": swe.MEAN_APOG     # Lilith (Apogeo lunar medio)
        }
        
        results = {}
        for name, planet_id in planets.items():
            pos, ret = swe.calc_ut(julian_day, planet_id, 258) # 258 = FLG_SWIEPH + FLG_SPEED
            lon = pos[0]
            results[name] = {"longitude": lon, "sign": int(lon / 30), "degree": lon % 30}
        
        # 3. Calcular Ascendente y 12 Casas
        cusps, ascmc = swe.houses_ex(julian_day, req.lat, req.lon, b'P')
        results["Ascendant"] = {"longitude": ascmc[0], "sign": int(ascmc[0] / 30), "degree": ascmc[0] % 30}
        results["Midheaven"] = {"longitude": ascmc[1], "sign": int(ascmc[1] / 30), "degree": ascmc[1] % 30}

        # 4. Cálculo Cármico: Carta Dracónica (Matemática del Alma)
        # Se calcula restando la longitud del Nodo Norte Verdadero a cada planeta
        north_node_lon = results["True_Node"]["longitude"]
        draconic = {}
        for name, data in results.items():
            draco_lon = (data["longitude"] - north_node_lon) % 360  # Rotación del zodiaco
            draconic[name] = {"longitude": draco_lon, "sign": int(draco_lon / 30), "degree": draco_lon % 30}

        # 5. Cálculo Geométrico: Aspectos Mayores (Matriz)
        aspects_base = [
            {"name": "Conjunction", "angle": 0, "orb": 8},
            {"name": "Opposition", "angle": 180, "orb": 8},
            {"name": "Trine", "angle": 120, "orb": 8},
            {"name": "Square", "angle": 90, "orb": 8},
            {"name": "Sextile", "angle": 60, "orb": 6}
        ]
        
        aspect_results = []
        keys = list(results.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                p1, p2 = keys[i], keys[j]
                lon1, lon2 = results[p1]["longitude"], results[p2]["longitude"]
                
                # Diferencia angular absoluta (distancia mas corta)
                dist = abs(lon1 - lon2)
                if dist > 180:
                    dist = 360 - dist
                
                for asp in aspects_base:
                    if abs(dist - asp["angle"]) <= asp["orb"]:
                        exactness = abs(dist - asp["angle"])
                        aspect_results.append({
                            "planet_1": p1,
                            "planet_2": p2,
                            "aspect": asp["name"],
                            "orb_degrees": round(exactness, 2)
                        })

        return {
            "status": "success",
            "metadata": {
                "julian_day": julian_day,
                "user_authenticated": user.get("sub"),
                "astrological_engine": "Swiss Ephemeris v2.10 (Ultra-Precision)"
            },
            "data": {
                "tropical_positions": results,
                "draconic_positions": draconic,
                "houses_placidus": {f"House_{i+1}": cusps[i] for i in range(12)},
                "major_aspects_matrix": aspect_results
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
