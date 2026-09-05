#!/bin/bash
# deploy_oci.sh — Script de despliegue para la instancia OCI (Ubuntu ARM64)
# Ejecutar directamente en la instancia: bash /opt/souschef/app/scripts/deploy_oci.sh
set -e

SOUSCHEF_DIR="/opt/souschef"
APP_DIR="${SOUSCHEF_DIR}/app"

echo "================================================================="
echo "        Despliegue de SousChef.ai en OCI (Always Free)           "
echo "================================================================="

echo "→ 1. Creando directorios persistentes en ${SOUSCHEF_DIR}..."
mkdir -p "${SOUSCHEF_DIR}/data"
mkdir -p "${SOUSCHEF_DIR}/models"
mkdir -p "${SOUSCHEF_DIR}/certbot/conf"
mkdir -p "${SOUSCHEF_DIR}/certbot/www"

echo "→ 2. Verificando archivo de configuracion (.env)..."
if [ ! -f "${APP_DIR}/.env" ]; then
    cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
    echo "   ✓ Se ha creado ${APP_DIR}/.env desde .env.example."
fi

# Detectar IP pública de la instancia en OCI
PUBLIC_IP=$(curl -s -m 5 https://ifconfig.me || curl -s -m 5 https://api.ipify.org || echo "IP_PUBLICA")

echo "→ 3. Verificando modelo GGUF para fallback local (llama.cpp)..."
HAS_MODEL=0
for model_file in "${SOUSCHEF_DIR}"/models/*.gguf; do
    if [ -f "${model_file}" ]; then
        HAS_MODEL=1
        echo "   ✓ Modelo detectado: $(basename "${model_file}")"
        break
    fi
done

if [ "${HAS_MODEL}" -eq 0 ]; then
    echo "   ⚠️  No se encontro ningun archivo .gguf en ${SOUSCHEF_DIR}/models/"
    echo "      Opciones para el modelo de fallback:"
    echo "      1) Descargar Qwen3.5-4B-Q4_K_M (~2.5 GB) directamente desde Hugging Face ahora"
    echo "      2) Omitir por ahora (la aplicacion usara OCI GenAI como proveedor principal)"
    read -p "   Selecciona una opcion [1/2] (por defecto: 2): " MODEL_OPTION
    MODEL_OPTION=${MODEL_OPTION:-2}

    if [ "${MODEL_OPTION}" = "1" ]; then
        echo "   → Descargando modelo desde Hugging Face (conexion de alta velocidad OCI)..."
        curl -L --progress-bar -o "${SOUSCHEF_DIR}/models/Qwen3.5-4B-Q4_K_M.gguf" \
            "https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/resolve/main/qwen2.5-coder-3b-instruct-q4_k_m.gguf" || {
            echo "   ⚠️ No se pudo completar la descarga automatica. Continuando sin modelo local."
        }
    else
        echo "   ℹ️  Continuando sin modelo GGUF local. Podras subirlo mas tarde con:"
        echo "      scp models/Qwen3.5-4B-Q4_K_M.gguf ubuntu@${PUBLIC_IP}:${SOUSCHEF_DIR}/models/"
    fi
fi

echo ""
echo "→ 4. Configuracion de Acceso Web y Certificados SSL..."
echo "   IP Publica detectada: ${PUBLIC_IP}"
echo ""
echo "   Elige el modo de exposicion:"
echo "   1) Dominio propio o gratuito con HTTPS/SSL (Let's Encrypt)"
echo "      - Admite tu dominio (ej: misitio.com)"
echo "      - O gratuito como DuckDNS (ej: souschef.duckdns.org)"
echo "      - O comodin DNS directo por IP (ej: ${PUBLIC_IP}.sslip.io)"
echo "   2) Modo HTTP directo por IP (sin dominio ni certificados SSL)"
echo ""
read -p "   Selecciona una opcion [1/2] (por defecto: 1): " ACCESS_MODE
ACCESS_MODE=${ACCESS_MODE:-1}

if [ "${ACCESS_MODE}" = "1" ]; then
    read -p "   Ingresa tu dominio (ej: souschef.duckdns.org o ${PUBLIC_IP}.sslip.io): " DOMAIN
    if [ -z "${DOMAIN}" ]; then
        echo "❌ Error: El dominio no puede estar vacio."
        exit 1
    fi

    read -p "   Ingresa tu email para Let's Encrypt: " EMAIL
    EMAIL=${EMAIL:-"admin@${DOMAIN}"}

    echo "   → Obteniendo certificado SSL gratuito con Certbot para ${DOMAIN}..."
    docker run --rm \
        -v "${SOUSCHEF_DIR}/certbot/conf:/etc/letsencrypt" \
        -v "${SOUSCHEF_DIR}/certbot/www:/var/www/certbot" \
        -p 80:80 \
        certbot/certbot certonly --standalone \
        -d "${DOMAIN}" --non-interactive --agree-tos -m "${EMAIL}"

    # Crear enlace simbolico relativo para que funcione tanto en host como dentro del contenedor Docker
    (cd "${SOUSCHEF_DIR}/certbot/conf/live" && ln -sfn "${DOMAIN}" "souschef-cert")
    chmod -R 755 "${SOUSCHEF_DIR}/certbot/conf/live" "${SOUSCHEF_DIR}/certbot/conf/archive" 2>/dev/null || true

    # Actualizar ALLOW_ORIGINS en .env si es necesario
    if grep -q "ALLOW_ORIGINS=" "${APP_DIR}/.env"; then
        sed -i "s|ALLOW_ORIGINS=.*|ALLOW_ORIGINS=https://${DOMAIN},http://localhost:5173|g" "${APP_DIR}/.env"
    fi

    SITE_URL="https://${DOMAIN}"
else
    echo "   → Configurando Nginx para modo directo HTTP..."
    cp "${APP_DIR}/nginx/nginx.conf" "${APP_DIR}/nginx/nginx.prod.conf"

    if grep -q "ALLOW_ORIGINS=" "${APP_DIR}/.env"; then
        sed -i "s|ALLOW_ORIGINS=.*|ALLOW_ORIGINS=http://${PUBLIC_IP},http://localhost:5173|g" "${APP_DIR}/.env"
    fi

    SITE_URL="http://${PUBLIC_IP}"
fi

echo ""
echo "→ 5. Levantando stack de contenedores con Docker Compose..."
cd "${APP_DIR}"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo ""
echo "================================================================="
echo "✓ ¡SousChef.ai desplegado exitosamente!"
echo "  Acceso: ${SITE_URL}"
echo "================================================================="
