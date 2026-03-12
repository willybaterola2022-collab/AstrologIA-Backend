from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import pytz
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from datetime import datetime
import jwt
import swisseph as swe
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.content_db import get_interpretation, SIGN_NAMES
from app.advanced_content_db import get_advanced_module, get_advanced_module_v2, get_sephirot_for_planet, PLANET_TO_SEPHIROT, get_dignity, get_chart_pattern
from app.stripe_router import router as stripe_router

# --- HELPER: Conversión Grados Decimales → Grados°Minutos'Segundos" ---
def to_dms(decimal_degrees: float) -> str:
    """Convierte grados decimales (ej: 8.9185) a formato DMS (ej: 8°55'06\")."""
    d = int(decimal_degrees)
    m = int((decimal_degrees - d) * 60)
    s = round(((decimal_degrees - d) * 60 - m) * 60)
    if s == 60:
        m += 1; s = 0
    if m == 60:
        d += 1; m = 0
    return f"{d}°{m:02d}'{s:02d}\""

# --- RATE LIMITING ---
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AstrologIA Backend (Control Plane)",
    description="API para conectar Lovable con Swisseph y Supabase",
    version="1.2.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- RUTAS AÑADIDAS ---
app.include_router(stripe_router, prefix="/api/pagos", tags=["Monetización"])

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
    hour: float       # Hora LOCAL del nacimiento
    timezone: Optional[float] = None  # UTC offset (ej: -3.0 para Buenos Aires, +1.0 para Madrid), calculado automatic si es None
    lat: Optional[float] = None
    lon: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None

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

class ModuleRequest(BaseModel):
    year: int
    month: int
    day: int
    hour: float
    lat: float
    lon: float

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

class CareerRequest(BaseModel):
    year: int
    month: int
    day: int
    hour: float
    lat: float
    lon: float

class DecisionWindowRequest(BaseModel):
    user_year: int
    user_month: int
    user_day: int
    user_hour: float
    user_lat: float
    user_lon: float
    start_year: int
    start_month: int
    start_day: int
    end_year: int
    end_month: int
    end_day: int
    goal_type: str = "business"

class SolarReturnRequest(BaseModel):
    """Revolución Solar: carta natal + año target + lugar donde estará el nativo en su cumpleaños."""
    birth_year: int
    birth_month: int
    birth_day: int
    birth_hour: float
    birth_lat: float
    birth_lon: float
    target_year: int
    # Lugar donde estará en su cumpleaños (puede diferir del nacimiento)
    location_lat: float
    location_lon: float

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
        # GEOLOCALIZACIÓN Y HUSO HORARIO AUTOMÁTICO (IANA Tzdata)
        geolocator = Nominatim(user_agent="malka_astrology_1.0")
        tf = TimezoneFinder()
        
        calc_lat, calc_lon = req.lat, req.lon
        
        if calc_lat is None or calc_lon is None:
            if req.city and req.country:
                location = geolocator.geocode(f"{req.city}, {req.country}")
                if location:
                    calc_lat, calc_lon = location.latitude, location.longitude
                else:
                    raise HTTPException(status_code=400, detail="No se pudo geolocalizar la ciudad y país. Reintroduce coordenadas exactas.")
            else:
                raise HTTPException(status_code=400, detail="Debe proporcionar lat/lon explícitamente o city/country para autocompletar.")
                
        calc_tz = req.timezone
        if calc_tz is None:
            # Obtener el huso horario IANA
            tz_str = tf.timezone_at(lng=calc_lon, lat=calc_lat)
            if tz_str:
                local_tz = pytz.timezone(tz_str)
                hh = int(req.hour)
                mm = int((req.hour - hh) * 60)
                try:
                    dt_naive = datetime(req.year, req.month, req.day, hh, mm)
                    dt_aware = local_tz.localize(dt_naive, is_dst=None)
                    calc_tz = dt_aware.utcoffset().total_seconds() / 3600.0
                except pytz.AmbiguousTimeError:
                    dt_aware = local_tz.localize(datetime(req.year, req.month, req.day, hh, mm), is_dst=False)
                    calc_tz = dt_aware.utcoffset().total_seconds() / 3600.0
                except pytz.NonExistentTimeError:
                    raise HTTPException(status_code=400, detail="Hora inexistente en ese país por cambio de horario verano/invierno.")
            else:
                calc_tz = 0.0 # Fallback UT
                
        # 1. Calcular Fecha Juliana (convertir hora local a UT)
        ut_hour = req.hour - calc_tz 
        julian_day = swe.julday(req.year, req.month, req.day, ut_hour)
        
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
            speed = pos[3]
            sign_idx = int(lon / 30)
            dignity_data = get_dignity(name, sign_idx)
            deg_in_sign = lon % 30
            results[name] = {
                "longitude": round(lon, 4),
                "sign": SIGN_NAMES[sign_idx],
                "degree": round(deg_in_sign, 4),
                "degree_dms": to_dms(deg_in_sign),
                "is_retrograde": speed < 0,
                "speed_deg_day": round(speed, 4),
                "dignity": dignity_data.get("status", "Normal"),
                "dignity_score": dignity_data.get("score", 5),
                "dignity_meaning": dignity_data.get("meaning", ""),
                "insight_text": get_interpretation(name, sign_idx)
            }
        
        # 3. Calcular Ascendente y 12 Casas
        cusps, ascmc = swe.houses_ex(julian_day, calc_lat, calc_lon, b'P')
        results["Ascendant"] = {
            "longitude": round(ascmc[0], 4),
            "sign": SIGN_NAMES[int(ascmc[0] / 30)],
            "degree": round(ascmc[0] % 30, 4),
            "degree_dms": to_dms(ascmc[0] % 30)
        }
        results["Midheaven"] = {
            "longitude": round(ascmc[1], 4),
            "sign": SIGN_NAMES[int(ascmc[1] / 30)],
            "degree": round(ascmc[1] % 30, 4),
            "degree_dms": to_dms(ascmc[1] % 30)
        }

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

        # 6. Chart Pattern (Marc Edmund Jones)
        lons_sorted = sorted([v["longitude"] for v in results.values() if "longitude" in v])
        span = max(lons_sorted) - min(lons_sorted) if lons_sorted else 360
        # Count groups (clusters within 30° of each other)
        groups = 1
        for i in range(1, len(lons_sorted)):
            if lons_sorted[i] - lons_sorted[i-1] > 30:
                groups += 1
        n_occupied = len(set(int(l/30) for l in lons_sorted))
        chart_pattern_data = get_chart_pattern(int(span), n_occupied, groups)

        # Casas con DMS
        houses_data = {}
        for i in range(12):
            cusp_deg = cusps[i] % 30
            houses_data[f"House_{i+1}"] = {
                "longitude": round(cusps[i], 4),
                "sign": SIGN_NAMES[int(cusps[i] / 30)],
                "degree": round(cusp_deg, 4),
                "degree_dms": to_dms(cusp_deg)
            }

        return {
            "status": "success",
            "metadata": {
                "julian_day": julian_day,
                "ut_hour": ut_hour,
                "timezone_offset": calc_tz,
                "calculated_lat": calc_lat,
                "calculated_lon": calc_lon,
                "user_authenticated": user.get("sub"),
                "astrological_engine": "Swiss Ephemeris v2.10 (Ultra-Precision)"
            },
            "data": {
                "tropical_positions": results,
                "draconic_positions": draconic,
                "houses_placidus": houses_data,
                "major_aspects_matrix": aspect_results,
                "chart_pattern": chart_pattern_data
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

@app.post("/api/career-vocational")
@limiter.limit("5/minute")
def calculate_career_path(request: Request, req: CareerRequest, user: dict = Depends(verify_jwt)):
    """
    MÓDULO 14: Career & Vocation Optimizer.
    Cruza el Sol, Medio Cielo (Casa 10) y Júpiter para definir roles e industrias rentables.
    """
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        
        # Obtener posiciones de planetas clave para carrera
        planets_to_check = {"Sun": swe.SUN, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN, "Mercury": swe.MERCURY}
        positions = {}
        for name, pid in planets_to_check.items():
            pos, _ = swe.calc_ut(jd, pid, 258)
            sign_idx = int(pos[0] / 30)
            positions[name] = SIGN_NAMES[sign_idx]
            
        # Calcular Medio Cielo (Aspiración Profesional / Imagen Pública / Casa 10)
        cusps, ascmc = swe.houses_ex(jd, req.lat, req.lon, b'P')
        mc_lon = ascmc[1]
        mc_sign_idx = int(mc_lon / 30)
        mc_sign = SIGN_NAMES[mc_sign_idx]
        
        # Algoritmo Base de Arquetipo Laboral (Logica simplificada MVP)
        # 1. El Elemento del Medio Cielo dicta el tipo de industria
        fire_signs = ["Aries", "Leo", "Sagittarius"]
        earth_signs = ["Taurus", "Virgo", "Capricorn"]
        air_signs = ["Gemini", "Libra", "Aquarius"]
        water_signs = ["Cancer", "Scorpio", "Pisces"]
        
        industry_type = ""
        soft_skills = []
        if mc_sign in fire_signs:
            industry_type = "Liderazgo, Emprendimiento, Deportes, Medios Visibles, Innovación Rápida"
            soft_skills = ["Iniciativa", "Carisma de Venta", "Acción Ejecutiva"]
        elif mc_sign in earth_signs:
            industry_type = "Finanzas, Construcción, Salud, Recursos Humanos, Sistemas Corporativos"
            soft_skills = ["Perseverancia", "Gestión de Riesgo", "Organización Práctica"]
        elif mc_sign in air_signs:
            industry_type = "Tecnología, Comunicación, Relaciones Públicas, Educación, Ventas B2B"
            soft_skills = ["Networking", "Análisis Lógico", "Oratoria"]
        elif mc_sign in water_signs:
            industry_type = "Psicología, Arte Receptivo, Terapias Alternativas, Cuidado Humano, RRHH Profundo"
            soft_skills = ["Empatía Táctica", "Intuición de Mercado", "Curación"]
            
        # Júpiter dicta donde está la Suerte/Expansión Económica
        jupiter_blessing = f"Tu expansión natural y 'golpes de suerte' financieros se activan al alinearte con las temáticas de {positions['Jupiter']}."
        
        return {
            "status": "success",
            "metadata": {"engine": "Career & Vocation Optimizer (Módulo 14)"},
            "data": {
                "midheaven_sign": mc_sign,
                "core_competencies": {
                    "sun_identity": positions['Sun'],
                    "communication_style": positions['Mercury'],
                    "discipline_zone": positions['Saturn']
                },
                "career_blueprint": {
                    "recommended_industries": industry_type,
                    "natural_soft_skills": soft_skills,
                    "wealth_expansion_key": jupiter_blessing
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/decision-window")
@limiter.limit("5/minute")
def calculate_decision_windows(request: Request, req: DecisionWindowRequest, user: dict = Depends(verify_jwt)):
    """
    MÓDULO 16: Decision Window Planner (Astrología Electoral Autárquica)
    Encuentra ventanas de tiempo óptimas buscando aspectos armónicos a tu Sol/Júpiter.
    """
    try:
        jd_natal = swe.julday(req.user_year, req.user_month, req.user_day, req.user_hour)
        nat_sun_pos, _ = swe.calc_ut(jd_natal, swe.SUN, 258)
        nat_jup_pos, _ = swe.calc_ut(jd_natal, swe.JUPITER, 258)
        nat_sun = nat_sun_pos[0]
        nat_jup = nat_jup_pos[0]
        
        jd_start = swe.julday(req.start_year, req.start_month, req.start_day, 12.0)
        jd_end = swe.julday(req.end_year, req.end_month, req.end_day, 12.0)
        
        if jd_end < jd_start:
            raise HTTPException(status_code=400, detail="La fecha de fin debe ser posterior a la de inicio")
        if (jd_end - jd_start) > 90:
            raise HTTPException(status_code=400, detail="El rango máximo de búsqueda es 90 días para no saturar el colisionador")
            
        best_days = []
        
        for i in range(int(jd_end - jd_start) + 1):
            current_jd = jd_start + i
            
            # Buscar que el Sol y Júpiter en el cielo hagan Trígono o Sextil a los de nacimiento
            t_sun_pos, _ = swe.calc_ut(current_jd, swe.SUN, 258)
            t_jup_pos, _ = swe.calc_ut(current_jd, swe.JUPITER, 258)
            
            t_sun = t_sun_pos[0]
            t_jup = t_jup_pos[0]
            
            # Evaluar Sol Transitando al Júpiter Natal (Buen momento para lanzamientos)
            dist_sun_jup = abs(t_sun - nat_jup)
            if dist_sun_jup > 180: dist_sun_jup = 360 - dist_sun_jup
            
            score = 0
            reason = ""
            
            # Trígono (120) o Sextil (60) o Conjunción (0)
            if abs(dist_sun_jup - 120) <= 3:
                score += 10; reason = "Día de expansión brutal. Fluidez cósmica para negocios."
            elif abs(dist_sun_jup - 0) <= 3:
                score += 15; reason = "Nuevo Ciclo de Identidad y Abundancia. Máxima suerte."
                
            # Restar si hay Mercurio Retrógrado (Cálculo Simplificado: velocidad diaria negativa)
            merc_pos_1, _ = swe.calc_ut(current_jd, swe.MERCURY, 258)
            # A rough calc for mercury retrograde
            merc_pos_2, _ = swe.calc_ut(current_jd + 0.1, swe.MERCURY, 258)
            dist_merc = merc_pos_2[0] - merc_pos_1[0]
            if dist_merc > 180: dist_merc -= 360
            elif dist_merc < -180: dist_merc += 360
            
            is_retrograde = dist_merc < 0
            if is_retrograde:
                score -= 8; reason += " [ALERTA: Mercurio Retrógrado, evitar firmas de contratos]"
                
            if score > 0:
                y, m, d, _ = swe.revjul(current_jd, 1)
                best_days.append({
                    "date": f"{y}-{m:02d}-{d:02d}",
                    "confidence_score": score,
                    "insight": reason.strip()
                })
                
        # Ordenar por el mejor score
        best_days = sorted(best_days, key=lambda x: x["confidence_score"], reverse=True)
        
        return {
            "status": "success",
            "metadata": {"engine": "Decision Window Planner", "goal_evaluated": req.goal_type},
            "data": {
                "top_recommended_dates": best_days[:5] # Devolver las mejores 5 ventanas
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/karmic-wound")
@limiter.limit("5/minute")
def calculate_karmic_wound(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """
    MÓDULO 2 & 3: Decodificador de Heridas Kármicas y Propósito (Chiron & North Node).
    """
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        
        # Quirón (Usando epemérides de moshier para evitar dependencias de archivos externos en MVP)
        pos_chiron, _ = swe.calc_ut(jd, swe.CHIRON, swe.FLG_MOSEPH)
        sign_idx_chiron = int(pos_chiron[0] / 30)
        
        # Nodo Norte (True Node)
        pos_node, _ = swe.calc_ut(jd, swe.TRUE_NODE, swe.FLG_MOSEPH)
        sign_idx_node = int(pos_node[0] / 30)
        
        wound_text = get_advanced_module("Chiron_Wound", sign_idx_chiron)
        healing_text = get_advanced_module("Chiron_Healing", sign_idx_chiron)
        purpose_text = get_advanced_module("North_Node", sign_idx_node)
        
        return {
            "status": "success",
            "metadata": {"engine": "Karmic Wound & Soul Purpose (Módulos 2 & 3)"},
            "data": {
                "chiron": {
                    "sign": SIGN_NAMES[sign_idx_chiron],
                    "core_wound": wound_text,
                    "healing_path": healing_text
                },
                "north_node": {
                    "sign": SIGN_NAMES[sign_idx_node],
                    "soul_evolution_path": purpose_text
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/wealth-blueprint")
@limiter.limit("5/minute")
def calculate_wealth_blueprint(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """
    MÓDULO 7: Arquitectura de la Riqueza (Jupiter & Saturn mechanics).
    """
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        
        pos_jup, _ = swe.calc_ut(jd, swe.JUPITER, 258)
        sign_idx_jup = int(pos_jup[0] / 30)
        
        pos_sat, _ = swe.calc_ut(jd, swe.SATURN, 258)
        sign_idx_sat = int(pos_sat[0] / 30)
        
        wealth_text = get_advanced_module("Jupiter_Wealth", sign_idx_jup)
        
        # Saturn acts as the financial block or required discipline
        saturn_blocks = [
            "Miedo a emprender solo, dependencia emocional financiera.", "Apego a la pobreza, miedo a perder lo que se tiene.",
            "Incapacidad de retener conocimiento, venta barata de ideas.", "Miedo irracional a no poder alimentar a la familia.",
            "Miedo a apostar por uno mismo, síndrome del impostor creativo.", "Parálisis por análisis, perfeccionismo que evita el lanzamiento.",
            "Incapacidad de asociarse, desconfianza crónica en socios.", "Miedo a la deuda, a inversiones riesgosas pero necesarias.",
            "Falta de visión a largo plazo, limitación a mercados muy locales.", "Exceso de responsabilidad corporativa que ahoga el salto independiente.",
            "Rebeldía contra el sistema del dinero, boicoteando el éxito por ideals.", "Evasión de la realidad material, victimismo financiero ilusorio."
        ]
        
        return {
            "status": "success",
            "metadata": {"engine": "Wealth Blueprint (Módulo 7)"},
            "data": {
                "jupiter_expansion": {
                    "sign": SIGN_NAMES[sign_idx_jup],
                    "wealth_strategy": wealth_text
                },
                "saturn_blockage": {
                    "sign": SIGN_NAMES[sign_idx_sat],
                    "financial_sabotage_pattern": saturn_blocks[sign_idx_sat]
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/venus-attraction")
@limiter.limit("5/minute")
def calculate_venus_profile(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """
    MÓDULO 12: Perfil de Atracción (Venus Love Language).
    """
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        
        pos_venus, _ = swe.calc_ut(jd, swe.VENUS, swe.FLG_MOSEPH)
        sign_idx_venus = int(pos_venus[0] / 30)
        
        venus_text = get_advanced_module("Venus_Profile", sign_idx_venus)
        
        return {
            "status": "success",
            "metadata": {"engine": "Venus Love Language (Módulo 12)"},
            "data": {
                "venus": {
                    "sign": SIGN_NAMES[sign_idx_venus],
                    "attraction_profile": venus_text
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mars-friction")
@limiter.limit("5/minute")
def calculate_mars_pluto_friction(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """
    MÓDULO 13: Disparador de Fricción y Evolución (Mars/Pluto Dynamics).
    """
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        
        pos_mars, _ = swe.calc_ut(jd, swe.MARS, swe.FLG_MOSEPH)
        sign_idx_mars = int(pos_mars[0] / 30)
        
        friction_text = get_advanced_module("Mars_Pluto_Friction", sign_idx_mars)
        
        return {
            "status": "success",
            "metadata": {"engine": "Mars & Pluto Friction (Módulo 13)"},
            "data": {
                "mars": {
                    "sign": SIGN_NAMES[sign_idx_mars],
                    "core_conflict_trigger": friction_text
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/moon-conditioning")
@limiter.limit("5/minute")
def calculate_moon_conditioning(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """MÓDULO 5: Sistema Operativo Emocional (Moon & Childhood Conditioning)."""
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        pos_moon, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_MOSEPH)
        sign_idx = int(pos_moon[0] / 30)
        return {
            "status": "success",
            "metadata": {"engine": "Moon Emotional OS (Módulo 5)"},
            "data": {
                "moon": {
                    "sign": SIGN_NAMES[sign_idx],
                    "core_emotional_pattern": get_advanced_module("Moon_Core_Emotion", sign_idx),
                    "childhood_conditioning": get_advanced_module("Moon_Childhood", sign_idx),
                    "integration_path": get_advanced_module("Moon_Healing", sign_idx)
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mercury-os")
@limiter.limit("5/minute")
def calculate_mercury_os(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """MÓDULO 9: Sistema Operativo Mental y Comunicación B2B (Mercury)."""
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        pos_merc, _ = swe.calc_ut(jd, swe.MERCURY, swe.FLG_MOSEPH)
        sign_idx = int(pos_merc[0] / 30)
        return {
            "status": "success",
            "metadata": {"engine": "Mercury Communication OS (Módulo 9)"},
            "data": {
                "mercury": {
                    "sign": SIGN_NAMES[sign_idx],
                    "thinking_style": get_advanced_module("Mercury_Thinking", sign_idx),
                    "communication_profile": get_advanced_module("Mercury_Communication", sign_idx),
                    "b2b_strategy": get_advanced_module("Mercury_B2B", sign_idx)
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/shadow-talents")
@limiter.limit("5/minute")
def calculate_shadow_talents(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """MÓDULO 10: Talentos Ocultos de la Sombra (Casa 12 via Neptune proxy for MVP)."""
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        pos_nep, _ = swe.calc_ut(jd, swe.NEPTUNE, swe.FLG_MOSEPH)
        sign_idx = int(pos_nep[0] / 30)
        pos_sun, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_MOSEPH)
        sun_sign_idx = int(pos_sun[0] / 30)
        return {
            "status": "success",
            "metadata": {"engine": "12th House Shadow Talents (Módulo 10)"},
            "data": {
                "neptune_generation": {
                    "sign": SIGN_NAMES[sign_idx],
                    "collective_shadow_talent": get_advanced_module("House12_Shadow_Talent", sign_idx)
                },
                "sun_personal_talent": {
                    "sign": SIGN_NAMES[sun_sign_idx],
                    "personal_shadow_talent": get_advanced_module("House12_Shadow_Talent", sun_sign_idx)
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sun-purpose")
@limiter.limit("5/minute")
def calculate_sun_purpose(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """MÓDULO 1: Propósito del Sol y Arquetipo Central (Sun-Sign Psychology)."""
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        pos_sun, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_MOSEPH)
        sign_idx = int(pos_sun[0] / 30)
        return {
            "status": "success",
            "metadata": {"engine": "Sun Purpose Archetype (Módulo 1)"},
            "data": {
                "sun": {
                    "sign": SIGN_NAMES[sign_idx],
                    "archetype": get_advanced_module("Sun_Archetype", sign_idx),
                    "core_purpose": get_advanced_module("Sun_Purpose", sign_idx),
                    "ego_shadow": get_advanced_module("Sun_Shadow", sign_idx)
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ascendant-mask")
@limiter.limit("5/minute")
def calculate_ascendant_mask(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """MÓDULO 15: Máscara Social y Primera Impresión (Ascendant / Rising Sign)."""
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        # Calculate houses using Placidus system to get the Ascendant
        asc_result = swe.houses(jd, req.lat, req.lon, b'P')
        asc_degree = asc_result[1][0]  # First element of cusps_asc is ASC
        sign_idx = int(asc_degree / 30)
        return {
            "status": "success",
            "metadata": {"engine": "Ascendant Social Mask (Módulo 15)"},
            "data": {
                "ascendant": {
                    "sign": SIGN_NAMES[sign_idx],
                    "degree": round(asc_degree % 30, 2),
                    "social_mask": get_advanced_module("Ascendant_Mask", sign_idx),
                    "natural_gift": get_advanced_module("Ascendant_Gift", sign_idx),
                    "blind_spot": get_advanced_module("Ascendant_Blind_Spot", sign_idx)
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/saturn-return")
@limiter.limit("5/minute")
def calculate_saturn_return(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """MÓDULO 16: Guía del Retorno de Saturno (Los Años del Juicio)."""
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        pos_sat, _ = swe.calc_ut(jd, swe.SATURN, swe.FLG_MOSEPH)
        sign_idx = int(pos_sat[0] / 30)
        return {
            "status": "success",
            "metadata": {"engine": "Saturn Return Guide (Módulo 16)"},
            "data": {
                "saturn": {
                    "sign": SIGN_NAMES[sign_idx],
                    "return_age_window": "28-31 años (1er Retorno) | 57-60 años (2do Retorno)",
                    "core_challenge": get_advanced_module("Saturn_Return_Challenge", sign_idx),
                    "growth_opportunity": get_advanced_module("Saturn_Return_Opportunity", sign_idx),
                    "integration_mantra": get_advanced_module("Saturn_Return_Mantra", sign_idx)
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- HEALTH CHECK ---
@app.get("/api/status")
def api_status():
    return {"status": "online", "version": "1.3.0", "engine": "AstrologIA Backend", "endpoints": 15}

# --- NEW ENDPOINTS: CAREER OPTIMIZER (UPGRADED WITH CONTENT) ---
@app.post("/api/career-optimizer")
@limiter.limit("5/minute")
def calculate_career_optimizer(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """MÓDULO 3: Optimizador de Vocación y Carrera (Sun + Jupiter synergy)."""
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        pos_sun, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_MOSEPH)
        pos_jup, _ = swe.calc_ut(jd, swe.JUPITER, swe.FLG_MOSEPH)
        sun_sign = int(pos_sun[0] / 30)
        jup_sign = int(pos_jup[0] / 30)
        return {
            "status": "success",
            "metadata": {
                "engine": "Career Optimizer (Módulo 3)",
                "content_status": "⚠️ Contenido no curado — pendiente revisión de Bárbara"
            },
            "data": {
                "sun_vocation": {
                    "sign": SIGN_NAMES[sun_sign],
                    "archetype": get_advanced_module("Career_Vocation", sun_sign),
                    "ideal_roles": get_advanced_module("Career_Ideal_Role", sun_sign),
                    "monetization_strategy": get_advanced_module("Career_Monetization", sun_sign),
                    "career_shadow": get_advanced_module("Career_Shadow", sun_sign)
                },
                "jupiter_expansion": {
                    "sign": SIGN_NAMES[jup_sign],
                    "wealth_strategy": get_advanced_module("Jupiter_Wealth", jup_sign)
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chart-pattern")
@limiter.limit("5/minute")
def calculate_chart_pattern(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """MÓDULO 17: Patrón Global de la Carta (Marc Edmund Jones 7 Types)."""
    from app.advanced_content_db import get_chart_pattern, CHART_PATTERN
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        planets = [swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS,
                   swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO]
        longitudes = []
        for p in planets:
            pos, _ = swe.calc_ut(jd, p, swe.FLG_MOSEPH)
            longitudes.append(pos[0])
        longitudes_sorted = sorted(longitudes)
        # Calculate distribution metrics
        bundle_span = longitudes_sorted[-1] - longitudes_sorted[0]
        signs_occupied = len(set(int(l / 30) for l in longitudes))
        # Count groups (clusters with gap > 30°)
        gaps = [longitudes_sorted[i+1] - longitudes_sorted[i] for i in range(len(longitudes_sorted)-1)]
        n_groups = sum(1 for g in gaps if g > 30) + 1
        pattern = get_chart_pattern(int(bundle_span), signs_occupied, n_groups)
        return {
            "status": "success",
            "metadata": {
                "engine": "Chart Pattern Type (Módulo 17)",
                "content_status": "⚠️ Contenido no curado — pendiente revisión de Bárbara"
            },
            "data": {
                "chart_pattern": pattern,
                "distribution_stats": {
                    "planetary_span_degrees": round(bundle_span, 1),
                    "signs_occupied": signs_occupied,
                    "planet_clusters": n_groups
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/daily-transit-score")
@limiter.limit("10/minute")
def calculate_daily_transit_score(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """MÓDULO 18: Score de Energía del Día (Luna en Tránsito)."""
    from datetime import datetime
    try:
        # Use today's date for transit moon position
        now = datetime.utcnow()
        jd_transit = swe.julday(now.year, now.month, now.day, now.hour + now.minute/60)
        pos_moon_transit, _ = swe.calc_ut(jd_transit, swe.MOON, swe.FLG_MOSEPH)
        transit_sign_idx = int(pos_moon_transit[0] / 30)
        transit_data = get_advanced_module("Lunar_Transit_Energy", transit_sign_idx).split(" | ")
        energy = transit_data[0] if transit_data else ""
        score_raw = [x for x in transit_data if "Score:" in x]
        score = int(score_raw[0].replace("Score: ", "")) if score_raw else 50
        ideal_raw = [x for x in transit_data if "Para:" in x]
        ideal = ideal_raw[0].replace("Para: ", "") if ideal_raw else ""
        avoid_raw = [x for x in transit_data if "Evita:" in x]
        avoid = avoid_raw[0].replace("Evita: ", "") if avoid_raw else ""
        # Natal sun for personalisation
        jd_natal = swe.julday(req.year, req.month, req.day, req.hour)
        pos_sun, _ = swe.calc_ut(jd_natal, swe.SUN, swe.FLG_MOSEPH)
        natal_sun_idx = int(pos_sun[0] / 30)
        return {
            "status": "success",
            "metadata": {
                "engine": "Daily Transit Score (Módulo 18)",
                "content_status": "⚠️ Contenido no curado — pendiente revisión de Bárbara",
                "transit_date": now.strftime("%Y-%m-%d")
            },
            "data": {
                "today_moon": {
                    "sign": SIGN_NAMES[transit_sign_idx],
                    "energy_level": energy,
                    "daily_score": score,
                    "ideal_for": ideal,
                    "avoid": avoid
                },
                "natal_sun": {
                    "sign": SIGN_NAMES[natal_sun_idx],
                    "archetype": get_advanced_module("Sun_Archetype", natal_sun_idx)
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cosmic-blueprint-full")
@limiter.limit("3/minute")
def calculate_cosmic_blueprint_full(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """MÓDULO MAESTRO: Perfil Completo del Alma (todos los motores en una sola llamada)."""
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        # Calculate all planets
        pos_sun, _   = swe.calc_ut(jd, swe.SUN, swe.FLG_MOSEPH)
        pos_moon, _  = swe.calc_ut(jd, swe.MOON, swe.FLG_MOSEPH)
        pos_merc, _  = swe.calc_ut(jd, swe.MERCURY, swe.FLG_MOSEPH)
        pos_ven, _   = swe.calc_ut(jd, swe.VENUS, swe.FLG_MOSEPH)
        pos_mars, _  = swe.calc_ut(jd, swe.MARS, swe.FLG_MOSEPH)
        pos_jup, _   = swe.calc_ut(jd, swe.JUPITER, swe.FLG_MOSEPH)
        pos_sat, _   = swe.calc_ut(jd, swe.SATURN, swe.FLG_MOSEPH)
        pos_nep, _   = swe.calc_ut(jd, swe.NEPTUNE, swe.FLG_MOSEPH)
        pos_nn, _    = swe.calc_ut(jd, swe.TRUE_NODE, swe.FLG_MOSEPH)
        asc_result   = swe.houses(jd, req.lat, req.lon, b'P')
        asc_degree   = asc_result[1][0]
        # Chiron: try with MOSEPH, gracefully fall back
        try:
            pos_chi, _ = swe.calc_ut(jd, swe.CHIRON, swe.FLG_MOSEPH)
            chi_i = int(pos_chi[0] / 30)
        except Exception:
            chi_i = int(pos_sun[0] / 30)  # use Sun sign as Chiron fallback

        sun_i  = int(pos_sun[0] / 30)
        moon_i = int(pos_moon[0] / 30)
        merc_i = int(pos_merc[0] / 30)
        ven_i  = int(pos_ven[0] / 30)
        mars_i = int(pos_mars[0] / 30)
        jup_i  = int(pos_jup[0] / 30)
        sat_i  = int(pos_sat[0] / 30)
        nep_i  = int(pos_nep[0] / 30)
        nn_i   = int(pos_nn[0] / 30)
        asc_i  = int(asc_degree / 30)

        return {
            "status": "success",
            "metadata": {
                "engine": "Cosmic Blueprint Full (Módulo Maestro)",
                "content_status": "⚠️ Contenido no curado — pendiente revisión de Bárbara",
                "version": "1.3.0"
            },
            "data": {
                "identity": {
                    "sun":  {"sign": SIGN_NAMES[sun_i],  "archetype": get_advanced_module("Sun_Archetype", sun_i),  "purpose": get_advanced_module("Sun_Purpose", sun_i)},
                    "moon": {"sign": SIGN_NAMES[moon_i], "core_emotion": get_advanced_module("Moon_Core_Emotion", moon_i), "integration": get_advanced_module("Moon_Healing", moon_i)},
                    "ascendant": {"sign": SIGN_NAMES[asc_i], "degree": round(asc_degree % 30, 2), "social_mask": get_advanced_module("Ascendant_Mask", asc_i), "gift": get_advanced_module("Ascendant_Gift", asc_i)}
                },
                "psyche": {
                    "mercury": {"sign": SIGN_NAMES[merc_i], "thinking_style": get_advanced_module("Mercury_Thinking", merc_i), "b2b_strategy": get_advanced_module("Mercury_B2B", merc_i)},
                    "chiron":  {"sign": SIGN_NAMES[chi_i],  "wound": get_advanced_module("Chiron_Wound", chi_i),  "healing": get_advanced_module("Chiron_Healing", chi_i)},
                    "shadow_talent": {"neptune_sign": SIGN_NAMES[nep_i], "hidden_gift": get_advanced_module("House12_Shadow_Talent", nep_i)}
                },
                "relationships": {
                    "venus": {"sign": SIGN_NAMES[ven_i],  "love_language": get_advanced_module("Venus_Profile", ven_i)},
                    "mars":  {"sign": SIGN_NAMES[mars_i], "conflict_trigger": get_advanced_module("Mars_Pluto_Friction", mars_i)}
                },
                "destiny": {
                    "north_node": {"sign": SIGN_NAMES[nn_i], "soul_evolution": get_advanced_module("North_Node", nn_i)},
                    "saturn_return": {"sign": SIGN_NAMES[sat_i], "challenge": get_advanced_module("Saturn_Return_Challenge", sat_i), "mantra": get_advanced_module("Saturn_Return_Mantra", sat_i)}
                },
                "abundance": {
                    "jupiter": {"sign": SIGN_NAMES[jup_i], "wealth_strategy": get_advanced_module("Jupiter_Wealth", jup_i)},
                    "career":  {"vocation": get_advanced_module("Career_Vocation", sun_i), "monetization": get_advanced_module("Career_Monetization", sun_i)}
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ancestral-code")
@limiter.limit("5/minute")
def calculate_ancestral_code(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """MÓDULO 19: Código Ancestral (Luna + Saturno como herencia psíquica familiar — Hellinger/Jung)."""
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        pos_moon, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_MOSEPH)
        pos_sat, _  = swe.calc_ut(jd, swe.SATURN, swe.FLG_MOSEPH)
        moon_i = int(pos_moon[0] / 30)
        sat_i  = int(pos_sat[0] / 30)
        return {
            "status": "success",
            "metadata": {
                "engine": "Ancestral Code — Dim 7 (Módulo 19)",
                "content_status": "⚠️ Contenido no curado — pendiente revisión de Bárbara",
                "sources": "Bert Hellinger (Constelaciones Familiares), Liz Greene (Saturn: A New Look), Carl Jung (Complejo Familiar)"
            },
            "data": {
                "moon_ancestry": {
                    "sign": SIGN_NAMES[moon_i],
                    "family_pattern": get_advanced_module_v2("Ancestral_Heritage", moon_i),
                    "inherited_wound": get_advanced_module_v2("Ancestral_Wound", moon_i),
                    "liberation_path": get_advanced_module_v2("Ancestral_Liberation", moon_i)
                },
                "saturn_structure": {
                    "sign": SIGN_NAMES[sat_i],
                    "authority_pattern": get_advanced_module_v2("Ancestral_Heritage", sat_i),
                    "karmic_contract": get_advanced_module("Saturn_Return_Challenge", sat_i)
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sephirot-frequency")
@limiter.limit("5/minute")
def calculate_sephirot_frequency(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """MÓDULO 20: Frecuencia Vibracional Kabbalística (Sephirot del Árbol de la Vida ↔ Carta Natal)."""
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        planets_calc = {
            "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
            "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN
        }
        sephirot_map = {}
        for planet_name, planet_id in planets_calc.items():
            pos, _ = swe.calc_ut(jd, planet_id, swe.FLG_MOSEPH)
            sign_i = int(pos[0] / 30)
            seph = get_sephirot_for_planet(planet_name)
            sephirot_map[planet_name] = {
                "sign": SIGN_NAMES[sign_i],
                "sephirot": seph.get("title", ""),
                "keyword": seph.get("keyword", ""),
                "psychological_key": seph.get("psychological_key", ""),
                "virtue": seph.get("virtue", ""),
                "shadow": seph.get("defect", ""),
                "color": seph.get("color", "")
            }
        # Ascendant → Malkuth
        asc_result = swe.houses(jd, req.lat, req.lon, b'P')
        asc_degree = asc_result[1][0]
        asc_i = int(asc_degree / 30)
        sephirot_map["Ascendant"] = {
            "sign": SIGN_NAMES[asc_i],
            "degree": round(asc_degree % 30, 2),
            "sephirot": "Malkuth — El Reino",
            "keyword": "Encarnación",
            "psychological_key": "El cuerpo como templo del espíritu. La vida material como campo sagrado.",
            "virtue": "Discriminación y encarnación",
            "shadow": "Inercia y materialismo extremo",
            "color": "Marrón/Verde/Ocre"
        }
        return {
            "status": "success",
            "metadata": {
                "engine": "Sephirot Frequency — Dim 8 (Módulo 20)",
                "content_status": "⚠️ Contenido no curado — pendiente revisión de Bárbara",
                "sources": "Sefer Yetzirah, Zohar, Franz Bardon (Initiation into Hermetics), Rabbi Aryeh Kaplan"
            },
            "data": {"sephirot_map": sephirot_map}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/manual-del-ser")
@limiter.limit("2/minute")
def calculate_manual_del_ser(request: Request, req: ModuleRequest, user: dict = Depends(verify_jwt)):
    """EL PRODUCTO FINAL: Manual del Ser — Las 8 Dimensiones del Alma Completas."""
    try:
        jd = swe.julday(req.year, req.month, req.day, req.hour)
        # Core positions
        pos_sun, _   = swe.calc_ut(jd, swe.SUN, swe.FLG_MOSEPH)
        pos_moon, _  = swe.calc_ut(jd, swe.MOON, swe.FLG_MOSEPH)
        pos_merc, _  = swe.calc_ut(jd, swe.MERCURY, swe.FLG_MOSEPH)
        pos_ven, _   = swe.calc_ut(jd, swe.VENUS, swe.FLG_MOSEPH)
        pos_mars, _  = swe.calc_ut(jd, swe.MARS, swe.FLG_MOSEPH)
        pos_jup, _   = swe.calc_ut(jd, swe.JUPITER, swe.FLG_MOSEPH)
        pos_sat, _   = swe.calc_ut(jd, swe.SATURN, swe.FLG_MOSEPH)
        pos_nep, _   = swe.calc_ut(jd, swe.NEPTUNE, swe.FLG_MOSEPH)
        pos_nn, _    = swe.calc_ut(jd, swe.TRUE_NODE, swe.FLG_MOSEPH)
        asc_result   = swe.houses(jd, req.lat, req.lon, b'P')
        asc_degree   = asc_result[1][0]
        # Chiron with graceful fallback
        try:
            pos_chi, _ = swe.calc_ut(jd, swe.CHIRON, swe.FLG_MOSEPH)
            chi_i = int(pos_chi[0] / 30)
        except Exception:
            chi_i = int(pos_sat[0] / 30)
        sun_i  = int(pos_sun[0] / 30)
        moon_i = int(pos_moon[0] / 30)
        merc_i = int(pos_merc[0] / 30)
        ven_i  = int(pos_ven[0] / 30)
        mars_i = int(pos_mars[0] / 30)
        jup_i  = int(pos_jup[0] / 30)
        sat_i  = int(pos_sat[0] / 30)
        nep_i  = int(pos_nep[0] / 30)
        nn_i   = int(pos_nn[0] / 30)
        asc_i  = int(asc_degree / 30)
        return {
            "status": "success",
            "metadata": {
                "engine": "Manual del Ser v1.0 — Las 8 Dimensiones",
                "content_status": "⚠️ Contenido no curado — pendiente revisión de Bárbara",
                "product_note": "La astrología es el motor invisible. El usuario solo siente que alguien finalmente lo entiende.",
                "version": "1.3.0"
            },
            "data": {
                "dim_1_quien_eres": {
                    "title": "Quién eres",
                    "sun":  {"sign": SIGN_NAMES[sun_i],  "archetype": get_advanced_module("Sun_Archetype", sun_i), "purpose": get_advanced_module("Sun_Purpose", sun_i)},
                    "moon": {"sign": SIGN_NAMES[moon_i], "emotional_os": get_advanced_module("Moon_Core_Emotion", moon_i)},
                    "ascendant": {"sign": SIGN_NAMES[asc_i], "degree": round(asc_degree % 30, 2), "social_mask": get_advanced_module("Ascendant_Mask", asc_i), "natural_gift": get_advanced_module("Ascendant_Gift", asc_i)}
                },
                "dim_2_por_que_sufres": {
                    "title": "Por qué sufres",
                    "chiron": {"sign": SIGN_NAMES[chi_i], "primary_wound": get_advanced_module("Chiron_Wound", chi_i), "healing_path": get_advanced_module("Chiron_Healing", chi_i)},
                    "shadow_talent": {"neptune_sign": SIGN_NAMES[nep_i], "hidden_gift": get_advanced_module("House12_Shadow_Talent", nep_i)},
                    "saturn_test": {"sign": SIGN_NAMES[sat_i], "life_challenge": get_advanced_module("Saturn_Return_Challenge", sat_i)}
                },
                "dim_3_para_que_viniste": {
                    "title": "Para qué viniste",
                    "north_node": {"sign": SIGN_NAMES[nn_i], "soul_mission": get_advanced_module("North_Node", nn_i)},
                    "saturn_mantra": get_advanced_module("Saturn_Return_Mantra", sat_i)
                },
                "dim_4_como_te_relacionas": {
                    "title": "Cómo te relacionas y te saboteas",
                    "venus": {"sign": SIGN_NAMES[ven_i], "love_language": get_advanced_module("Venus_Profile", ven_i)},
                    "mars": {"sign": SIGN_NAMES[mars_i], "conflict_pattern": get_advanced_module("Mars_Pluto_Friction", mars_i)},
                    "mercury": {"sign": SIGN_NAMES[merc_i], "communication_style": get_advanced_module("Mercury_Communication", merc_i)}
                },
                "dim_5_como_fluye_tu_dinero": {
                    "title": "Cómo fluye tu dinero y tu energía",
                    "jupiter": {"sign": SIGN_NAMES[jup_i], "wealth_code": get_advanced_module("Jupiter_Wealth", jup_i)},
                    "career": {"vocation": get_advanced_module("Career_Vocation", sun_i), "monetization": get_advanced_module("Career_Monetization", sun_i)}
                },
                "dim_6_cuando_actuar": {
                    "title": "Cuándo actuar y cuándo esperar",
                    "saturn_return": {"sign": SIGN_NAMES[sat_i], "opportunity": get_advanced_module("Saturn_Return_Opportunity", sat_i)},
                    "daily_guidance": "Ver /api/daily-transit-score para el score del día en tiempo real"
                },
                "dim_7_codigo_ancestral": {
                    "title": "Tu código ancestral",
                    "moon_lineage": {"sign": SIGN_NAMES[moon_i], "family_pattern": get_advanced_module_v2("Ancestral_Heritage", moon_i), "inherited_wound": get_advanced_module_v2("Ancestral_Wound", moon_i), "liberation": get_advanced_module_v2("Ancestral_Liberation", moon_i)},
                    "saturn_authority": {"sign": SIGN_NAMES[sat_i], "authority_code": get_advanced_module_v2("Ancestral_Heritage", sat_i)}
                },
                "dim_8_frecuencia_vibracional": {
                    "title": "Tu frecuencia vibracional",
                    "sun_sephirot":  {**get_sephirot_for_planet("Sun"),  "planet": "Sun",  "sign": SIGN_NAMES[sun_i]},
                    "moon_sephirot": {**get_sephirot_for_planet("Moon"), "planet": "Moon", "sign": SIGN_NAMES[moon_i]},
                    "asc_sephirot":  {"planet": "Ascendant", "sign": SIGN_NAMES[asc_i], "sephirot": "Malkuth — El Reino. El cuerpo como templo del espíritu.", "keyword": "Encarnación"}
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── REVOLUCIÓN SOLAR v1.0 ─────────────────────────────────────────────────
@app.post("/api/solar-return")
@limiter.limit("5/minute")
def calculate_solar_return(request: Request, req: SolarReturnRequest, user: dict = Depends(verify_jwt)):
    """
    MÓDULO: Revolución Solar — carta del año personal.
    Calcula el momento exacto en que el Sol regresa al mismo grado natal.
    location_lat/lon = lugar donde estará el nativo en su cumpleaños.
    Paywall: Plan Maestro.
    """
    try:
        jd_natal = swe.julday(req.birth_year, req.birth_month, req.birth_day, req.birth_hour)
        sun_natal_pos, _ = swe.calc_ut(jd_natal, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SPEED)
        sun_natal_lon = sun_natal_pos[0]

        approx_jd = swe.julday(req.target_year, req.birth_month, max(1, req.birth_day - 15), 12.0)
        solar_return_jd = swe.solcross_ut(sun_natal_lon, approx_jd, swe.FLG_SWIEPH)
        rs_year, rs_month, rs_day, rs_hour = swe.revjul(solar_return_jd)

        planets = {
            "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
            "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
            "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE,
            "Pluto": swe.PLUTO, "True_Node": swe.TRUE_NODE, "Lilith": swe.MEAN_APOG
        }

        rs_planets = {}
        for name, pid in planets.items():
            try:
                pos, _ = swe.calc_ut(solar_return_jd, pid, swe.FLG_SWIEPH | swe.FLG_SPEED)
                lon, speed = pos[0], pos[3]
                sign_idx = int(lon / 30)
                rs_planets[name] = {
                    "longitude": round(lon, 4),
                    "sign": SIGN_NAMES[sign_idx],
                    "degree": round(lon % 30, 2),
                    "is_retrograde": speed < 0,
                    "speed_deg_day": round(speed, 4)
                }
            except Exception:
                rs_planets[name] = {"error": "ephemeris_file_missing"}

        cusps_rs, ascmc_rs = swe.houses_ex(solar_return_jd, req.location_lat, req.location_lon, b'P')
        asc_rs, mc_rs = ascmc_rs[0], ascmc_rs[1]
        asc_sign_idx = int(asc_rs / 30)
        mc_sign_idx = int(mc_rs / 30)

        key_aspects = []
        for name, data in rs_planets.items():
            if "longitude" not in data:
                continue
            diff = abs(data["longitude"] - sun_natal_lon) % 360
            if diff > 180:
                diff = 360 - diff
            for asp_name, asp_deg, orb in [("Conjunction",0,3),("Opposition",180,3),("Trine",120,3),("Square",90,3)]:
                if abs(diff - asp_deg) <= orb:
                    key_aspects.append({"rs_planet": name, "aspect": asp_name, "natal_point": "Sun", "orb": round(abs(diff-asp_deg),2)})

        narrative_bullets = []
        moon_sign = rs_planets.get("Moon", {}).get("sign", "")
        jupiter_sign = rs_planets.get("Jupiter", {}).get("sign", "")
        if moon_sign and moon_sign in SIGN_NAMES:
            moon_idx = SIGN_NAMES.index(moon_sign)
            narrative_bullets.append(f"Luna en {moon_sign}: {get_advanced_module('Moon_Core_Emotion', moon_idx)[:150]}...")
        if jupiter_sign and jupiter_sign in SIGN_NAMES:
            jup_idx = SIGN_NAMES.index(jupiter_sign)
            narrative_bullets.append(f"Jupiter en {jupiter_sign}: {get_advanced_module('Jupiter_Wealth', jup_idx)[:150]}...")
        if rs_planets.get("Saturn", {}).get("is_retrograde"):
            narrative_bullets.append("Saturno retrogrado: revision profunda de estructuras previas. Karma que pasa factura.")
        if rs_planets.get("Mercury", {}).get("is_retrograde"):
            narrative_bullets.append("Mercurio retrogrado en RS: cuidado con contratos y firmas el primer trimestre del año personal.")
        for asp in key_aspects:
            if asp["rs_planet"] == "Jupiter" and asp["aspect"] == "Conjunction":
                narrative_bullets.insert(0, f"JUPITER CONJUNCION SOL NATAL (orb:{asp['orb']}deg) — Año de maxima expansion y reconocimiento publico.")

        return {
            "status": "success",
            "metadata": {
                "engine": "Solar Return Engine v1.0 (Swiss Ephemeris solcross_ut)",
                "user_authenticated": user.get("sub"),
                "natal_sun": f"{round(sun_natal_lon%30,2)} {SIGN_NAMES[int(sun_natal_lon/30)]}",
                "plan_required": "maestro"
            },
            "data": {
                "exact_datetime_utc": f"{int(rs_day):02d}/{int(rs_month):02d}/{int(rs_year)} {rs_hour:.4f}h UTC",
                "rs_planets": rs_planets,
                "rs_ascendant": {"longitude": round(asc_rs,4), "sign": SIGN_NAMES[asc_sign_idx], "degree": round(asc_rs%30,2), "mask": get_advanced_module("Ascendant_Mask", asc_sign_idx)},
                "rs_midheaven": {"longitude": round(mc_rs,4), "sign": SIGN_NAMES[mc_sign_idx], "degree": round(mc_rs%30,2)},
                "rs_houses": {f"House_{i+1}": round(cusps_rs[i],4) for i in range(12)},
                "key_aspects_to_natal_sun": key_aspects,
                "year_narrative": narrative_bullets,
                "astrocartography_note": "Cambiar location_lat/lon altera el ASC-RS y todas las casas del año personal."
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Solar Return failed: {str(e)}")
