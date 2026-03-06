#!/bin/bash
# =====================================================================
# AstrologIA Backend — Deploy Script v1.4.0
# Ejecuta esto UNA VEZ con tu GitHub token para subir y desplegar todo.
# =====================================================================
# USO:
#   chmod +x DEPLOY.sh
#   GH_TOKEN=ghp_tutoken ./DEPLOY.sh
# =====================================================================

set -e

GH_TOKEN="${GH_TOKEN:-}"
REPO_NAME="${REPO_NAME:-AstrologIA-Backend}"
GH_USER="${GH_USER:-}"

# --- VALIDACIÓN ---
if [ -z "$GH_TOKEN" ]; then
  echo "❌ ERROR: Necesitas pasar tu GitHub token."
  echo "   Obtén uno en: https://github.com/settings/tokens/new"
  echo "   Permisos necesarios: repo (todos)"
  echo ""
  echo "   Uso: GH_TOKEN=ghp_tutoken GH_USER=tu_usuario ./DEPLOY.sh"
  exit 1
fi

if [ -z "$GH_USER" ]; then
  echo "❗ Detectando usuario de GitHub..."
  GH_USER=$(curl -s -H "Authorization: token $GH_TOKEN" https://api.github.com/user | python3 -c "import sys,json; print(json.load(sys.stdin)['login'])")
  echo "   Usuario: $GH_USER"
fi

echo ""
echo "🚀 AstrologIA Backend Deploy — Iniciando..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# --- PASO 1: Crear repo en GitHub ---
echo ""
echo "📦 Paso 1/3: Creando repositorio GitHub '$REPO_NAME'..."
REPO_RESPONSE=$(curl -s -X POST \
  -H "Authorization: token $GH_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/user/repos \
  -d "{\"name\":\"$REPO_NAME\",\"private\":false,\"description\":\"AstrologIA Backend — 18 endpoints, 8 dimensiones del alma. FastAPI + Swiss Ephemeris + Supabase.\"}")

REPO_URL=$(echo "$REPO_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('html_url',''))" 2>/dev/null)
CLONE_URL=$(echo "$REPO_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('clone_url',''))" 2>/dev/null)

if [ -z "$REPO_URL" ]; then
  # Maybe the repo already exists
  echo "   Repo ya existe o error. Obteniendo URL existente..."
  CLONE_URL="https://github.com/$GH_USER/$REPO_NAME.git"
  REPO_URL="https://github.com/$GH_USER/$REPO_NAME"
fi
echo "   ✅ Repo: $REPO_URL"

# --- PASO 2: Push a GitHub ---
echo ""
echo "⬆️  Paso 2/3: Subiendo código a GitHub..."
git remote remove origin 2>/dev/null || true
PUSH_URL="https://${GH_TOKEN}@github.com/${GH_USER}/${REPO_NAME}.git"
git remote add origin "$PUSH_URL"
git push -u origin main --force
echo "   ✅ Código subido. Commits: $(git log --oneline | wc -l | tr -d ' ')"

# Limpiar token de remote por seguridad
git remote set-url origin "https://github.com/${GH_USER}/${REPO_NAME}.git"

# --- PASO 3: Instrucciones Railway ---
echo ""
echo "🚂 Paso 3/3: Deploy a Railway"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   1. Ve a: https://railway.app/new"
echo "   2. Selecciona → 'Deploy from GitHub repo'"
echo "   3. Conecta: $GH_USER/$REPO_NAME"
echo "   4. Railway detectará nixpacks.toml automáticamente"
echo "   5. En 'Variables', añade estas 3 variables de entorno:"
echo ""
echo "      SUPABASE_URL           = [tu URL de Supabase]"
echo "      SUPABASE_SERVICE_ROLE_KEY = [tu clave service_role]"
echo "      JWT_SECRET             = [tu JWT secret de Supabase]"
echo ""
echo "   6. ✅ En ~3 minutos tendrás tu URL pública."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DEPLOY COMPLETO"
echo ""
echo "   📁 Repo:    $REPO_URL"
echo "   📖 Swagger: [tu-url-railway].railway.app/docs"
echo "   💊 Status:  [tu-url-railway].railway.app/api/status"
echo "   🌌 Manual del Ser: POST /api/manual-del-ser"
echo ""
