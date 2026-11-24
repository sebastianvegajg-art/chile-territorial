# Comparador regional

Requiere Node.js 22.12 o posterior y la API local de Chile Territorial en `127.0.0.1:8000`.

```sh
npm ci
npm run dev
```

Abre http://127.0.0.1:5173. La vista inicial consulta publicaciones oficiales. Para abrir con el corte aislado de prueba, inicia la API en modo demostración y ejecuta `npm run dev:demo`. El modo se puede cambiar en «Origen de los datos».

`npm run build` verifica tipos y genera la compilación local. El frontend solicita las rutas de `/api/v1` en el mismo origen. Vite las redirige a la API en desarrollo.
