from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
import swisseph as swe

app = FastAPI(
    title="AstrologIA Backend (Control Plane)",
    description="API para conectar Lovable con Swisseph y Supabase",
    version="1.1.0"
)

# --- CORS MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",             # Entorno Local (Lovable)
        "https://*.vercel.app"               # Entorno Preview/Prod de Vercel
    ],
    allow_credentials=True,
    allow_methods=["*"],                     # Permite GET, POST, OPTIONS, etc.
    allow_headers=["Authorization", "Content-Type"],
)

# --- AUTH MIDDLEWARE (JWT SUPABASE) ---
# Extraemos el secret que usa supabase para firmar tokens
SUPABASE_JWT_SECRET = "Yl6eZL7tNOKeO2YMKsHOms0FqTkcknyhSPETPV0Unzc"
security = HTTPBearer()

def verify_jwt(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        # Supabase firma usando HS256 y un rol en el payload
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
        return payload  # Retorna el dict del user (id, email, rol, etc)
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
def calculate_natal_chart(req: NatalChartRequest, user: dict = Depends(verify_jwt)):
    """
    IMPORTANTE: Notese el `Depends(verify_jwt)`.
    Si el header 'Authorization: Bearer <token>' no viene o es falso, FastApi responde 401 automático.
    """
    try:
        julian_day = swe.julday(req.year, req.month, req.day, req.hour)
        planets = {"Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN}
        
        results = {}
        for name, planet_id in planets.items():
            pos, ret = swe.calc_ut(julian_day, planet_id, 258)
            lon = pos[0]
            results[name] = {"longitude": lon, "sign": int(lon / 30), "degree": lon % 30}
        
        cusps, ascmc = swe.houses_ex(julian_day, req.lat, req.lon, b'P')
        results["Ascendant"] = {"longitude": ascmc[0], "sign": int(ascmc[0] / 30), "degree": ascmc[0] % 30}
        
        return {
            "status": "success",
            "user_authenticated": user.get("sub"), # Validacion visual de que sabemos quien consulto
            "data": {
                "julian_day": julian_day,
                "planets": results,
                "houses": {f"House_{i+1}": cusps[i] for i in range(12)}
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
