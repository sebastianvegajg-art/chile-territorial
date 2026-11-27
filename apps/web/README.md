# Comparador regional

## Vista previa local de Confía Sur

En Windows, abre `Ver-Confia-Sur.cmd` desde la raíz del repositorio. El lanzador usa Node.js 22.12 o posterior, instala las dependencias la primera vez y abre [la portada local](http://127.0.0.1:4173/#portada). Deja la terminal abierta mientras revisas. En otros sistemas, desde la raíz del repositorio:

```sh
npm --prefix apps/web ci
npm --prefix apps/web run dev:local
```

El modo local sirve el corte oficial incluido en el repositorio con las mismas rutas de la función de Netlify. Funciona sin iniciar FastAPI ni configurar credenciales. La cobertura corresponde al corte guardado. Consulta [el estado del corte](http://127.0.0.1:4173/healthz).

Vite actualiza la página cuando se guardan cambios de código en esta copia. Para ver nuevos commits de la rama de revisión en otro equipo, sincroniza la rama en Antigravity o usa `git pull --ff-only` con la rama de revisión activa. Si cambia el archivo de dependencias, vuelve a ejecutar `npm --prefix apps/web ci` con el servidor detenido. Si el puerto 4173 ya está en uso, cierra la sesión anterior o abre directamente su dirección local.

## Desarrollo con FastAPI

Requiere Node.js 22.12 o posterior y la API local de Chile Territorial en `127.0.0.1:8000`.

```sh
npm ci
npm run dev
```

Abre http://127.0.0.1:5173. La vista inicial consulta publicaciones oficiales. Para abrir con el corte aislado de prueba, inicia la API en modo demostración y ejecuta `npm run dev:demo`. El modo se puede cambiar en «Origen de los datos».

`npm run build` verifica tipos y genera la compilación local. El frontend solicita las rutas de `/api/v1` en el mismo origen. Vite las redirige a la API en desarrollo.

El período inicial del comparador comienza en 2013 y termina en el último año disponible para el indicador. El primer año seleccionado sirve de base para el índice y el crecimiento acumulado. El ranking muestra el último año del intervalo entre las regiones seleccionadas.

Para generar un HTML autónomo con un corte oficial, inicia la API en modo oficial, compila y ejecuta:

```sh
npm run build
node scripts/export-html.mjs /ruta/Chile_Territorial_Oficial.html http://127.0.0.1:8000/api/v1
```

Puedes agregar un ID de publicación como último argumento. Abre el HTML directamente en un navegador. Incluye las observaciones y su procedencia en el archivo y genera las descargas localmente.

Si el archivo generado está en `data/published/Chile_Territorial_Oficial.html` desde la raíz del repositorio, Vite ofrece la descarga en el comparador local. El HTML incluye todas las regiones e indicadores del corte exportado al generarlo. Los filtros de la sesión actual se aplican a la descarga CSV.
