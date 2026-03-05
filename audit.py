import requests
import json

url = "https://homfwprrzeigzltaamzo.supabase.co"
service_role = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhvbWZ3cHJyemVpZ3psdGFhbXpvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjMxOTAyNywiZXhwIjoyMDg3ODk1MDI3fQ.Yl6eZL7tNOKeO2YMKsHOms0FqTkcknyhSPETPV0Unzc"

headers = {
    "apikey": service_role,
    "Authorization": f"Bearer {service_role}"
}

print("--- AUDITORIA DE SUPABASE (homfwprrzeigzltaamzo) ---")

# 1. Inspect OpenAPI schema to see tables
resp = requests.get(f"{url}/rest/v1/", headers=headers)
if resp.status_code == 200:
    data = resp.json()
    tables = data.get("definitions", {})
    print(f"Total Tables/Views/Types found via REST API: {len(tables)}\n")
    for name, metadata in tables.items():
        if getattr(metadata, "type", "") == "object" or metadata.get("type") == "object":
            props = metadata.get("properties", {})
            print(f"- TABLA: {name}")
            print(f"  Columnas: {list(props.keys())}")
            
            # Count records (this requires querying the table directly)
            try:
                count_resp = requests.get(f"{url}/rest/v1/{name}?select=id", headers=headers)
                if count_resp.status_code == 200:
                    print(f"  Total records: {len(count_resp.json())}")
                else:
                    print("  Total records: N/A (Error querying)")
            except:
                print("  Total records: N/A")
            print("")
else:
    print(f"Failed to fetch schema: {resp.status_code}")
    print(resp.text)

# 2. Inspect Storage buckets
resp = requests.get(f"{url}/storage/v1/bucket", headers=headers)
print("--- STORAGE BUCKETS ---")
if resp.status_code == 200:
    buckets = resp.json()
    for b in buckets:
        print(f"- Bucket: {b.get('name')} (Public: {b.get('public')})")
else:
    print(f"Failed to fetch buckets: {resp.status_code}")

