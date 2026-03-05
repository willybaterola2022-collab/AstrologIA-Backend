import jwt
import time
SUPABASE_JWT_SECRET = "Yl6eZL7tNOKeO2YMKsHOms0FqTkcknyhSPETPV0Unzc"
payload = {"sub": "user_id_123", "role": "authenticated", "exp": int(time.time() + 3600)}
token = jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")
print(token)
