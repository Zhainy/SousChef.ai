#!/bin/bash
# deploy_oci.sh — Script de despliegue post-Terraform para la instancia OCI (Ubuntu ARM64)
# Ejecutar directamente en la instancia: bash /opt/souschef/app/scripts/deploy_oci.sh
set -e

SOUSCHEF_DIR="/opt/souschef"
APP_DIR="${SOUSCHEF_DIR}/app"

echo "=== Despliegue de SousChef.ai en OCI (Always Free) ==="

echo "→ Creando estructura de directorios en ${SOUSCHEF_DIR}..."
mkdir -p "${SOUSCHEF_DIR}/data"
mkdir -p "${SOUSCHEF_DIR}/models"
mkdir -p "${SOUSCHEF_DIR}/certbot/conf"
mkdir -p "${SOUSCHEF_DIR}/certbot/www"

echo "→ Configurando archivo de entorno (.env)..."
if [ ! -f "${APP_DIR}/.env" ]; then
    cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
    echo ""
    echo "⚠️  AVISO: Se ha creado ${APP_DIR}/.env desde .env.example."
    echo "   Verifica los siguientes parámetros antes de continuar:"
    echo "     - OCI_COMPARTMENT_ID=ocid1.compartment.oc1..xxxxx"
    echo "     - OCI_AUTH_TYPE=instance_principal"
    echo "     - ALLOW_ORIGINS=https://tudominio.com"
    echo ""
fi

echo "→ Verificando presencia del modelo GGUF en ${SOUSCHEF_DIR}/models/..."
HAS_MODEL=0
for model_file in "${SOUSCHEF_DIR}"/models/*.gguf; do
    if [ -f "${model_file}" ]; then
        HAS_MODEL=1
        echo "   ✓ Modelo encontrado: $(basename "${model_file}")"
        break
    fi
done

if [ "${HAS_MODEL}" -eq 0 ]; then
    echo "⚠️  No se encontró ningún archivo .gguf en ${SOUSCHEF_DIR}/models/"
    echo "   Sube el modelo GGUF antes de continuar:"
    echo "   scp Qwen3.5-4B-Q4_K_M.gguf opc@<IP>:${SOUSCHEF_DIR}/models/"
    exit 1
fi

echo "→ Certificado SSL con Let's Encrypt (Certbot)..."
echo "   Asegúrate de que el registro DNS (tipo A) de tu dominio apunte a la IP pública de esta instancia."
read -p "   Ingresa tu dominio (ej: souschef.tudominio.com): " DOMAIN

if [ -z "${DOMAIN}" ]; then
    echo "❌ Error: El nombre de dominio no puede estar vacío."
    exit 1
fi

read -p "   Ingresa tu email para renovación Let's Encrypt: " EMAIL
if [ -z "${EMAIL}" ]; then
    EMAIL="admin@${DOMAIN}"
fi

# Generación del certificado SSL standalone (puerto 80 temporal)
docker run --rm \
    -v "${SOUSCHEF_DIR}/certbot/conf:/etc/letsencrypt" \
    -v "${SOUSCHEF_DIR}/certbot/www:/var/www/certbot" \
    -p 80:80 \
    certbot/certbot certonly --standalone \
    -d "${DOMAIN}" --non-interactive --agree-tos -m "${EMAIL}"

echo "→ Arrancando el stack de producción con Docker Compose..."
cd "${APP_DIR}"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo ""
echo "========================================================="
echo "✓ SousChef.ai desplegado exitosamente!"
echo "  URL: https://${DOMAIN}"
echo "========================================================="
