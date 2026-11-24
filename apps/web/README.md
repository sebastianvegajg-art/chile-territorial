# Comparador regional

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
