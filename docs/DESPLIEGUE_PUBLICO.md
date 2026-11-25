# Guía de despliegue público — Opción 1 (Frontend + Backend FastAPI)

Esta guía permite publicar **Chile Territorial** en internet con arquitectura profesional de dos piezas, manteniendo las credenciales del Banco Central (`BCCH_API_TOKEN`) **estrictamente en el servidor** (nunca en el navegador ni en Git):

- **Backend (`apps/api`, Python + FastAPI):** desplegado en **Render** (o **Railway / Fly.io** usando el `Dockerfile` incluido).
- **Frontend (`apps/web`, React + Vite):** desplegado en **Netlify** (o **Cloudflare Pages**).

---

## Paso 0 · Integrar tu rama en GitHub

Antes de conectar el repositorio en producción, revisa y aprueba en GitHub:
1. **PR #11** (`fase1/integracion-oficial` → `main`)
2. **PR #12** (`fase2/estructura-y-auditoria` → `main`)

*(También puedes desplegar temporalmente apuntando a la rama `fase2/estructura-y-auditoria` si deseas hacer una prueba pública previa antes del merge a `main`.)*

---

## Paso 1 · Publicar el Backend en Render (5 minutos)

El repositorio incluye [`render.yaml`](../render.yaml) y [`Dockerfile`](../Dockerfile) listos para usar.

1. Entra a [https://dashboard.render.com/blueprints](https://dashboard.render.com/blueprints) y haz clic en **New Blueprint Instance**.
2. Conecta tu repositorio `sebastianvegajg-art/chile-territorial`.
3. Render detectará automáticamente el archivo `render.yaml` con el servicio `chile-territorial-api`:
   - **Build:** `pip install -r apps/api/requirements.txt`
   - **Start:** `python infra/preparar-datos-oficiales.py --solo-faltantes && uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check:** `/healthz`
4. Completa las 2 variables privadas en el panel de Render (**Environment Variables**):
   - `BCCH_API_TOKEN`: tu token personal del Banco Central de Chile (el mismo que tienes en tu `.env` local; **nunca lo subas a Git**).
   - `CT_CORS_ORIGINS`: la URL pública de tu frontend una vez creada en el Paso 2 (por ejemplo `https://chile-territorial.netlify.app` o `https://chileterritorial.cl`).
5. Haz clic en **Apply / Deploy** y espera ~2–3 minutos mientras descarga los cortes oficiales (BCCh 34 + 416 series, INE 17 series, SINIM 10 comunas de Aysén, MOP DGOP y DIPRES 2025/2026).
6. Comprueba que quedó vivo abriendo `https://<tu-servicio>.onrender.com/healthz` — debe responder `{"estado":"ok", ...}` con todos los `datos_publicados` en `true`.

> **Alternativa en Railway o Fly.io:** basta con apuntar el servicio al [`Dockerfile`](../Dockerfile) en la raíz del repositorio y cargar las mismas variables (`BCCH_API_TOKEN` y `CT_CORS_ORIGINS`).

---

## Paso 2 · Publicar el Frontend en Netlify (3 minutos)

El repositorio incluye [`netlify.toml`](../netlify.toml) preconfigurado.

1. Si tu URL de Render es distinta a `https://chile-territorial-api.onrender.com`, actualiza la línea `to = "https://<tu-servicio>.onrender.com/api/:splat"` en [`netlify.toml`](../netlify.toml) (o configura la variable pública `VITE_API_BASE=https://<tu-servicio>.onrender.com` en Netlify).
2. Entra a [https://app.netlify.com/](https://app.netlify.com/) → **Add new site** → **Import an existing project** → elige `sebastianvegajg-art/chile-territorial`.
3. Netlify leerá automáticamente `netlify.toml`:
   - **Base directory:** `apps/web`
   - **Build command:** `npm run build`
   - **Publish directory:** `apps/web/dist`
4. Haz clic en **Deploy site**.
5. En ~1 minuto tendrás tu URL HTTPS pública (por ejemplo `https://chile-territorial.netlify.app/#politica`), y si quieres puedes conectar un dominio propio (como `chileterritorial.cl`) desde **Domain management** en Netlify.

> **Importante:** en el plan gratuito de Render el backend se duerme tras 15 minutos sin visitas y tarda ~30 segundos en despertar en la primera consulta. Si necesitas respuesta instantánea 24/7 (por ejemplo, durante lanzamientos o entrevistas radiales), cambia el plan de Render de `free` a `starter` (~US\$7/mes) o usa Railway.

---

## Paso 3 · Lista de verificación de seguridad antes de difundir

- `BCCH_API_TOKEN` existe **únicamente** en las variables de entorno del backend (Render/Railway), **nunca** en Netlify ni en variables `VITE_*`.
- `GET /healthz` responde `200 OK` y no expone tokens ni rutas sensibles.
- `https://<tu-sitio>/#politica` carga en celular (`360px`) las 4 pestañas (**Resumen**, **Economía**, **Presupuestos** con Municipalidad de Aysén y enlace SINIM, y **Proyectos** con Vialidad MOP).
