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
from app.content_db import get_interpretation, SIGN_NAMES

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

class TransitRequest(BaseModel):
    user_year: int
    user_month: int
    user_day: int
    user_hour: float
    user_lat: float
    user_lon: float
    target_year: int
    target_month: int
    target_day: int
    target_hour: float

class SinastryRequest(BaseModel):
    p1_year: int
    p1_month: int
    p1_day: int
    p1_hour: float
    p1_lat: float
    p1_lon: float
    p2_year: int
    p2_month: int
    p2_day: int
    p2_hour: float
    p2_lat: float
    p2_lon: float

class TransitScoreRequest(BaseModel):
    user_year: int
    user_month: int
    user_day: int
    user_hour: float
    user_lat: float
    user_lon: float
    start_year: int
    start_month: int
    start_day: int
    days_to_check: int = 30

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
            sign_idx = int(lon / 30)
            results[name] = {
                "longitude": round(lon, 4), 
                "sign": SIGN_NAMES[sign_idx], 
                "degree": round(lon % 30, 2),
                "insight_text": get_interpretation(name, sign_idx) 
            }
        
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

@app.post("/api/transitos")
@limiter.limit("5/minute")
def calculate_transits(request: Request, req: TransitRequest, user: dict = Depends(verify_jwt)):
    """
    IMPORTANTE: Calcula Tránsitos Planetarios.
    Compara las posiciones en 'target_date' con la carta natal en 'user_date'.
    """
    try:
        julian_day_natal = swe.julday(req.user_year, req.user_month, req.user_day, req.user_hour)
        julian_day_transit = swe.julday(req.target_year, req.target_month, req.target_day, req.target_hour)
        
        planets = {
            "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, 
            "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER, 
            "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, 
            "Pluto": swe.PLUTO, "True_Node": swe.TRUE_NODE
        }
        
        natal_results = {}
        transit_results = {}
        for name, planet_id in planets.items():
            natal_pos, ret = swe.calc_ut(julian_day_natal, planet_id, 258)
            transit_pos, ret = swe.calc_ut(julian_day_transit, planet_id, 258)
            natal_results[name] = natal_pos[0]
            transit_results[name] = transit_pos[0]
            
        aspects_base = [
            {"name": "Conjunction", "angle": 0, "orb": 2},
            {"name": "Opposition", "angle": 180, "orb": 2},
            {"name": "Trine", "angle": 120, "orb": 2},
            {"name": "Square", "angle": 90, "orb": 2},
            {"name": "Sextile", "angle": 60, "orb": 1.5}
        ]
        
        active_transits = []
        for t_name, t_lon in transit_results.items():
            for n_name, n_lon in natal_results.items():
                dist = abs(t_lon - n_lon)
                if dist > 180:
                    dist = 360 - dist
                
                for asp in aspects_base:
                    if abs(dist - asp["angle"]) <= asp["orb"]:
                        exactness = abs(dist - asp["angle"])
                        active_transits.append({
                            "transit_planet": t_name,
                            "natal_planet": n_name,
                            "aspect": asp["name"],
                            "orb_degrees": round(exactness, 2)
                        })
                        
        return {
            "status": "success",
            "metadata": {
                "user_authenticated": user.get("sub"),
                "astrological_engine": "Swiss Ephemeris v2.10 (Ultra-Precision)"
            },
            "data": {
                "active_transits": active_transits
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sinastria")
@limiter.limit("5/minute")
def calculate_sinastry_matrix(request: Request, req: SinastryRequest, user: dict = Depends(verify_jwt)):
    """
    IMPORTANTE: Calcula matriz de Sinastría 100x100
    """
    try:
        jd_p1 = swe.julday(req.p1_year, req.p1_month, req.p1_day, req.p1_hour)
        jd_p2 = swe.julday(req.p2_year, req.p2_month, req.p2_day, req.p2_hour)
        
        planets = {
            "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, 
            "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER, 
            "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, 
            "Pluto": swe.PLUTO, "Chiron": swe.CHIRON, "True_Node": swe.TRUE_NODE
        }
        
        p1_pos = {}
        p2_pos = {}
        for name, p_id in planets.items():
            pos1, _ = swe.calc_ut(jd_p1, p_id, 258)
            pos2, _ = swe.calc_ut(jd_p2, p_id, 258)
            p1_pos[name] = pos1[0]
            p2_pos[name] = pos2[0]
            
        aspects_base = [
            {"name": "Conjunction", "angle": 0, "orb": 5},
            {"name": "Opposition", "angle": 180, "orb": 5},
            {"name": "Trine", "angle": 120, "orb": 5},
            {"name": "Square", "angle": 90, "orb": 5},
            {"name": "Sextile", "angle": 60, "orb": 4}
        ]
        
        # Scoring Weights (Simplified Version of the "Oro")
        # Love/Attraction
        love_points = [("Venus", "Mars"), ("Sun", "Moon"), ("Venus", "Sun")]
        # Friction
        friction_points = [("Mars", "Saturn"), ("Saturn", "Moon"), ("Pluto", "Moon")]
        
        matrix = []
        total_score = 0
        
        for name1, lon1 in p1_pos.items():
            for name2, lon2 in p2_pos.items():
                dist = abs(lon1 - lon2)
                if dist > 180: dist = 360 - dist
                
                for asp in aspects_base:
                    if abs(dist - asp["angle"]) <= asp["orb"]:
                        exactness = abs(dist - asp["angle"])
                        power = (asp["orb"] - exactness) / asp["orb"] # 0 to 1 strength
                        
                        points = 1
                        if asp["name"] in ["Trine", "Sextile", "Conjunction"]: points = 2 * power
                        if asp["name"] in ["Square", "Opposition"]: points = -1 * power
                        
                        # Extra multiplier for specific karmic/love links
                        if (name1, name2) in love_points or (name2, name1) in love_points:
                            if points > 0: points *= 2
                        if (name1, name2) in friction_points or (name2, name1) in friction_points:
                            if points < 0: points *= 2
                            
                        total_score += points
                        
                        matrix.append({
                            "p1_planet": name1,
                            "p2_planet": name2,
                            "aspect": asp["name"],
                            "orb_degrees": round(exactness, 2),
                            "energy_score": round(points, 2)
                        })
                        
        # Normalize score 0-100 logically
        base_compat = 50 + (total_score * 2) 
        if base_compat > 100: base_compat = 100
        if base_compat < 0: base_compat = 0
                        
        return {
            "status": "success",
            "metadata": {
                "astrological_engine": "Sinastry Matrix 100x100 Engine"
            },
            "data": {
                "global_compatibility_score": round(base_compat, 1),
                "synastry_matrix": matrix
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transit-scoring")
@limiter.limit("5/minute")
def calculate_transit_scoring(request: Request, req: TransitScoreRequest, user: dict = Depends(verify_jwt)):
    """
    IMPORTANTE: Calcula el nivel de impacto de los tránsitos a lo largo de los días.
    Transit Impact Scoring v2
    """
    try:
        jd_natal = swe.julday(req.user_year, req.user_month, req.user_day, req.user_hour)
        
        natal_planets = { "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS, "Mars": swe.MARS }
        transit_planets = { "Jupiter": swe.JUPITER, "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO }
        
        natal_pos = {}
        for n, pid in natal_planets.items():
            pos, _ = swe.calc_ut(jd_natal, pid, 258)
            natal_pos[n] = pos[0]
            
        aspects_base = [{"name": "Conjunction", "angle": 0, "orb": 2}, {"name": "Opposition", "angle": 180, "orb": 2}, {"name": "Square", "angle": 90, "orb": 2}]
        
        timeline = []
        for i in range(req.days_to_check):
            current_jd = swe.julday(req.start_year, req.start_month, req.start_day, 12.0) + i
            daily_score = 0
            daily_transits = []
            
            for t_name, t_pid in transit_planets.items():
                t_pos, _ = swe.calc_ut(current_jd, t_pid, 258)
                t_lon = t_pos[0]
                
                # Weight by slow planet
                weight = 1
                if t_name == "Pluto": weight = 5
                elif t_name == "Uranus" or t_name == "Neptune": weight = 4
                elif t_name == "Saturn": weight = 3
                elif t_name == "Jupiter": weight = 2
                
                for n_name, n_lon in natal_pos.items():
                    dist = abs(t_lon - n_lon)
                    if dist > 180: dist = 360 - dist
                    
                    for asp in aspects_base:
                        if abs(dist - asp["angle"]) <= asp["orb"]:
                            exact = abs(dist - asp["angle"])
                            power = (asp["orb"] - exact) / asp["orb"]
                            impact = round(weight * power * 2, 2)
                            daily_score += impact
                            daily_transits.append({
                                "transit": t_name, "natal": n_name, "aspect": asp["name"], "impact": impact
                            })
                            
            # Convert Julian Day back to calendar date roughly for output
            y, m, d, h = swe.revjul(current_jd, 1) # 1 = Gregorian
            date_str = f"{y}-{m:02d}-{d:02d}"
            
            timeline.append({
                "date": date_str,
                "total_impact_score": round(daily_score, 2),
                "key_activations": daily_transits
            })
            
        # Sort or process
        return {
            "status": "success",
            "metadata": {"engine": "Transit Impact Scoring v2", "days_analyzed": req.days_to_check},
            "data": {"timeline": timeline}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
