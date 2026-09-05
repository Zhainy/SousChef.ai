# SousChef.ai

Despensa inteligente y asistente de cocina con Inteligencia Artificial Híbrida. Cuenta con CRUD de ingredientes en Vue 3 y un agente que valida el inventario en tiempo real mediante Tool Calling, sugiere recetas aprovechando los ingredientes disponibles y descuenta el stock atómicamente al cocinar.

La arquitectura de IA utiliza un modelo **híbrido con alta disponibilidad y costo $0**:
1. **OCI Generative AI (Llama 3.3 70B)** como proveedor primario en la nube.
2. **llama.cpp local (Qwen 3.5 4B GGUF)** como motor de inferencia local o fallback automático transparente ante fallas de red, timeout o agotamiento de cuota.

Las imágenes de las recetas se obtienen mediante un pipeline gratuito sin API keys (TheMealDB con traducción gastronómica automática + Unsplash Source), almacenadas en caché local y respaldadas por placeholders SVG.

---

## Stack Tecnológico

- **Backend**: Python 3.12, FastAPI, SQLModel / SQLite, `oci-openai`, httpx, uv, Ruff, pytest
- **Frontend**: Vue 3 (Composition API, TypeScript), Pinia, Vue Router, Tailwind CSS, `marked` + `dompurify`, Vite, vitest
- **LLM Primario**: [OCI Generative AI](https://docs.oracle.com/en-us/iaas/Content/generative-ai/overview.htm) (`meta.llama-3.3-70b-instruct`)
- **LLM Local / Fallback**: [llama.cpp](https://github.com/ggml-org/llama.cpp) (`llama-server`) con `Qwen3.5-4B-Q4_K_M.gguf`
- **Infraestructura**: Oracle Cloud Infrastructure (OCI) Always Free (Ampere A1 Flex ARM64, 2 OCPU, 12 GB RAM), Terraform, Docker Compose multi-arch, Nginx Reverse Proxy con SSL automático (Certbot / Let's Encrypt).

---

## Arquitectura de la Solución

```
                                  ┌───────────────────────────┐
                                  │   Browser / Client (Vue)  │
                                  └─────────────┬─────────────┘
                                                │ HTTPS / SSE
                                                ▼
                                  ┌───────────────────────────┐
                                  │    Nginx Reverse Proxy    │
                                  └──────┬─────────────┬──────┘
                                         │             │
                    /api/ & /static/     │             │ /*
                                         ▼             ▼
                    ┌─────────────────────────┐   ┌───────────────────────────┐
                    │  FastAPI Backend (:8000)│   │ Frontend Dist (HTML/JS/CSS│
                    └────────────┬────────────┘   └───────────────────────────┘
                                 │
                   ┌─────────────┴─────────────┐
                   │  Capa de IA Híbrida       │
                   ▼                           ▼
      ┌─────────────────────────┐ ┌───────────────────────────┐
      │   OCI Generative AI     │ │ llama.cpp Server (:8080)  │
      │  (Llama 3.3 70B Cloud)  │ │ (Qwen 3.5 4B Local/VM)   │
      │  [Proveedor Primario]   │ │ [Fallback Automático]     │
      └─────────────────────────┘ └───────────────────────────┘
```

### Secuencia de Eventos SSE en el Chat
El endpoint `POST /api/chat` emite eventos Server-Sent Events (SSE) en tiempo real:
- `provider_info`: Indica si responde OCI (`oci`) o el modelo local (`local`, y si fue activación por fallback).
- `token`: Texto incremental en streaming.
- `tool_call` / `tool_result`: Ejecución de herramientas (`get_inventario`, `descontar_stock`).
- `recipe`: Objeto estructurado de la receta normalizada (ingredientes, pasos, porciones).
- `recipe_image`: URL de la imagen generada o resuelta.
- `done`: Fin de la respuesta y mensaje final formateado.

---

## Configuración de Entorno

Copia el archivo de variables de ejemplo:
```bash
cp .env.example .env
```

Variables disponibles en `.env`:

| Variable | Default | Descripción |
|---|---|---|
| `LLM_PROVIDER` | `oci` | Proveedor activo (`oci` o `local`) |
| `AI_FALLBACK_ENABLED` | `true` | Activa fallback automático a llama.cpp si OCI falla |
| `OCI_COMPARTMENT_ID` | — | OCID de tu compartment en OCI |
| `OCI_REGION` | `us-ashburn-1` | Región de OCI |
| `OCI_MODEL_ID` | `meta.llama-3.3-70b-instruct` | Modelo en OCI Generative AI |
| `OCI_AUTH_TYPE` | `api_key` | `api_key` (desarrollo local) o `instance_principal` (en VM OCI) |
| `LOCAL_LLM_BASE_URL` | `http://llama-cpp:8080/v1` | Endpoint compatible OpenAI de llama.cpp |
| `LOCAL_LLM_MODEL` | `qwen3.5-4b` | Identificador del modelo local |
| `IMAGE_SOURCE` | `web` | `web` (TheMealDB + Unsplash) o `none` (tests) |
| `DATABASE_URL` | `sqlite:////data/souschef.db` | Ruta a la base de datos SQLite |
| `ALLOW_ORIGINS` | `http://localhost` | Orígenes permitidos para CORS |

---

## Desarrollo Local

### Opción A: Con Docker Compose (Recomendada)

1. Descarga el modelo GGUF recomendado si deseas usar el LLM local:
   ```bash
   mkdir -p models
   # Coloca Qwen3.5-4B-Q4_K_M.gguf en el directorio models/
   ```

2. Inicia todo el stack (Backend, Frontend y llama.cpp):
   ```bash
   docker compose up --build
   ```
   Abre [http://localhost](http://localhost) en tu navegador.

### Opción B: Ejecución Bare-Metal (Nativo)

1. **LLM Local (Opcional con GPU host):**
   ```bash
   ./scripts/serve_local.sh
   ```

2. **Backend:**
   ```bash
   cd backend
   uv sync
   uv run fastapi dev
   ```

3. **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Abre [http://localhost:5173](http://localhost:5173).

---

## Despliegue en OCI (Always Free)

La infraestructura está 100% automatizada con **Terraform** para correr sin costo en el tier Always Free de Oracle Cloud (Compute Ampere A1 ARM64).

### Pre-requisitos
- Cuenta activa en Oracle Cloud Infrastructure (OCI).
- OCI CLI y Terraform >= 1.5 instalados localmente.
- Dominio propio con acceso a la gestión de registros DNS.

### Paso a paso

1. **Configurar variables de Terraform:**
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   ```
   Edita `terraform.tfvars` con tus OCIDs (`tenancy_ocid`, `user_ocid`, etc.) y tu llave pública SSH.

2. **Provisionar la infraestructura:**
   ```bash
   terraform init
   terraform apply
   ```
   Terraform creará la VCN, subred pública, security lists, Dynamic Group e IAM Policy para Instance Principal, además de la instancia Ampere A1 (2 OCPU / 12 GB RAM) con Docker preinstalado.

3. **Subir el modelo GGUF a la instancia:**
   ```bash
   scp ../models/Qwen3.5-4B-Q4_K_M.gguf opc@<IP_PUBLICA_INSTANCIA>:/opt/souschef/models/
   ```

4. **Configurar registro DNS:**
   Crea un registro **A** en tu proveedor de dominio apuntando a la IP pública de la instancia.

5. **Ejecutar script de despliegue en la instancia:**
   ```bash
   ssh opc@<IP_PUBLICA_INSTANCIA>
   bash /opt/souschef/app/scripts/deploy_oci.sh
   ```
   El script configurará los directorios, obtendrá el certificado SSL con Let's Encrypt y levantará el stack de producción con `docker-compose.prod.yml`.

Tu aplicación estará disponible en `https://tudominio.com` con renovación automática de certificados SSL.

---

## Comandos de Calidad y Tests

```bash
# Tests unitarios y de integración del Backend (51 tests)
cd backend && uv run pytest

# Verificación de tipos y linter
cd backend && uv run ruff check .

# Tests unitarios del Frontend (73 tests)
cd frontend && npm test -- --run
```
