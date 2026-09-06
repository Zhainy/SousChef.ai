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

# Asegurar configuraciones optimizadas para la VM de OCI
if grep -q "OCI_AUTH_TYPE=api_key" "${APP_DIR}/.env" 2>/dev/null; then
    sed -i 's/OCI_AUTH_TYPE=api_key/OCI_AUTH_TYPE=instance_principal/' "${APP_DIR}/.env"
    echo "   ✓ OCI_AUTH_TYPE actualizado a 'instance_principal' para autenticacion IAM nativa."
fi
if grep -q "LLAMA_THREADS=" "${APP_DIR}/.env" 2>/dev/null; then
    sed -i 's/LLAMA_THREADS=.*/LLAMA_THREADS=2/' "${APP_DIR}/.env"
    echo "   ✓ LLAMA_THREADS ajustado a 2 para alinearse con los 2 nucleos fisicos ARM."
fi

# Detectar IP pública de la instancia en OCI
PUBLIC_IP=$(curl -s -m 5 https://ifconfig.me || curl -s -m 5 https://api.ipify.org || echo "IP_PUBLICA")

echo "→ 3. Verificando modelo GGUF para fallback local (llama.cpp)..."
if ls "${SOUSCHEF_DIR}"/models/*.gguf 1>/dev/null 2>&1; then
    echo "   Modelos disponibles en ${SOUSCHEF_DIR}/models/:"
    for m in "${SOUSCHEF_DIR}"/models/*.gguf; do
        echo "   - $(basename "${m}")"
    done
fi

if [ ! -f "${SOUSCHEF_DIR}/models/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf" ]; then
    echo ""
    echo "   💡 Modelo de alta velocidad recomendado: Qwen2.5-1.5B-Instruct Q4_K_M (~1 GB, 15-20 t/s en ARM)"
    read -p "   ¿Deseas descargarlo ahora para optimizar el rendimiento? [S/n]: " DOWNLOAD_QWEN
    DOWNLOAD_QWEN=${DOWNLOAD_QWEN:-S}
    if [[ "${DOWNLOAD_QWEN}" =~ ^[sSyY]$ ]]; then
        MODEL_FILE="Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
        MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
        echo "   → Descargando Qwen2.5-1.5B desde Hugging Face..."
        curl -L --progress-bar -o "${SOUSCHEF_DIR}/models/${MODEL_FILE}" "${MODEL_URL}" || {
            echo "   ⚠️ No se pudo completar la descarga. Continuando con el modelo actual."
        }
        sed -i 's/LOCAL_LLM_MODEL=.*/LOCAL_LLM_MODEL=qwen2.5-1.5b/' "${APP_DIR}/.env" 2>/dev/null || true
        sed -i 's/LLAMA_MODEL_FILE=.*/LLAMA_MODEL_FILE=Qwen2.5-1.5B-Instruct-Q4_K_M.gguf/' "${APP_DIR}/.env" 2>/dev/null || true
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

    # 1. Verificar si el certificado para este dominio ya existe
    if [ -f "${SOUSCHEF_DIR}/certbot/conf/live/${DOMAIN}/fullchain.pem" ]; then
        echo "   ✓ Certificado SSL ya existente para ${DOMAIN}. Omitiendo solicitud a Let's Encrypt."
    else
        echo "   → Obteniendo certificado SSL gratuito con Certbot para ${DOMAIN}..."
        # Liberar el puerto 80 si algún contenedor ya lo está ocupando (ej. frontend anterior)
        RUNNING_PORT_80=$(docker ps -q --filter "publish=80" || true)
        if [ -n "${RUNNING_PORT_80}" ]; then
            echo "   → Liberando puerto 80 temporalmente (deteniendo contenedor)..."
            docker stop ${RUNNING_PORT_80} 2>/dev/null || true
        fi

        docker run --rm \
            -v "${SOUSCHEF_DIR}/certbot/conf:/etc/letsencrypt" \
            -v "${SOUSCHEF_DIR}/certbot/www:/var/www/certbot" \
            -p 80:80 \
            certbot/certbot certonly --standalone \
            -d "${DOMAIN}" --non-interactive --agree-tos -m "${EMAIL}"
    fi

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
