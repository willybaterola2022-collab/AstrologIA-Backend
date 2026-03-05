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
from app.advanced_content_db import get_advanced_module
from app.stripe_router import router as stripe_router

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
