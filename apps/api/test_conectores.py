"""Pruebas unitarias e integración local para conectores BCCh, DIPRES y SINIM.

Utiliza invocación ASGI directa (sin abrir sockets loopback) para compatibilidad
total con entornos restringidos y con ``unittest``.
"""

from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import urlencode

from apps.api.main import crear_app
from pipelines.economia import bcch_live
from pipelines.fiscal import dipres_ckan, sinim_importer


async def _ejecutar_en_linea(func, *args, **kwargs):
    return func(*args, **kwargs)


def invocar_asgi(
    app,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
) -> tuple[int, dict[str, str], bytes]:
    """Ejecuta una petición HTTP contra una app ASGI sin bucle de eventos ni sockets."""
    body = b""
    headers: list[tuple[bytes, bytes]] = []
    if json_body is not None:
        body = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        headers.append((b"content-type", b"application/json"))
        headers.append((b"content-length", str(len(body)).encode("ascii")))

    query_string = urlencode(params, doseq=True).encode("utf-8") if params else b""
    mensajes: list[dict] = []
    enviado = False

    async def receive():
        nonlocal enviado
        if not enviado:
            enviado = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(mensaje: dict):
        mensajes.append(mensaje)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query_string,
        "headers": headers,
        "client": ("127.0.0.1", 0),
        "server": ("testserver", 80),
    }

    with patch("fastapi.routing.run_in_threadpool", side_effect=_ejecutar_en_linea):
        coro = app(scope, receive, send)
        try:
            while True:
                coro.send(None)
        except StopIteration:
            pass

    inicio = next(m for m in mensajes if m["type"] == "http.response.start")
    cabeceras = {
        k.decode("latin-1").lower(): v.decode("latin-1")
        for k, v in inicio.get("headers", [])
    }
    cuerpo = b"".join(
        m.get("body", b"") for m in mensajes if m["type"] == "http.response.body"
    )
    return inicio["status"], cabeceras, cuerpo


def _construir_csv_sinim_valido() -> str:
    buffer = io.StringIO(newline="")
    escritor = csv.writer(buffer)
    escritor.writerow(sinim_importer.COLUMNAS_PLANTILLA)
    for indice, (cut, nombre) in enumerate(sinim_importer.COMUNAS_AYSEN.items(), start=1):
        ingresos = 1000 * indice
        gasto_corriente = 600 * indice
        gasto_inversion = 300 * indice
        gasto_total = gasto_corriente + gasto_inversion
        escritor.writerow(
            [
                cut,
                nombre,
                2024,
                "millones CLP",
                "devengado",
                str(ingresos),
                str(gasto_total),
                str(gasto_corriente),
                str(gasto_inversion),
                "sinim-aysen-2024-prueba.csv",
            ]
        )
    return buffer.getvalue()


class ConectoresBcchDipresTest(unittest.TestCase):
    def setUp(self):
        self.app = crear_app(demo_activa=True)

    def test_bcch_search_200_y_parametros(self):
        respuesta_esperada = {
            "frecuencia": "ANNUAL",
            "query": "Aysén",
            "total": 1,
            "series": [{"seriesId": "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.A"}],
        }
        with patch.object(
            bcch_live, "buscar_series_live", return_value=respuesta_esperada
        ) as mock_buscar:
            status, _, cuerpo = invocar_asgi(
                self.app,
                "GET",
                "/api/v1/bcch/search",
                params={"frequency": "ANNUAL", "q": "Aysén", "limit": 25},
            )

        self.assertEqual(status, 200)
        self.assertEqual(json.loads(cuerpo), respuesta_esperada)
        mock_buscar.assert_called_once_with(frequency="ANNUAL", query="Aysén", limit=25)

    def test_bcch_search_503_falta_token_y_502_error_red(self):
        with patch.object(
            bcch_live,
            "buscar_series_live",
            side_effect=bcch_live.FaltaTokenBCChError("Falta BCCH_API_TOKEN."),
        ):
            status, _, cuerpo = invocar_asgi(self.app, "GET", "/api/v1/bcch/search")
        self.assertEqual(status, 503)
        datos = json.loads(cuerpo)
        self.assertEqual(datos["codigo"], "falta_token_bcch")
        self.assertIn("BCCH_API_TOKEN", datos["mensaje"])

        with patch.object(
            bcch_live,
            "buscar_series_live",
            side_effect=URLError("tiempo de espera agotado"),
        ):
            status, _, cuerpo = invocar_asgi(self.app, "GET", "/api/v1/bcch/search")
        self.assertEqual(status, 502)
        datos = json.loads(cuerpo)
        self.assertEqual(datos["codigo"], "error_bcch")

    def test_bcch_sanea_credenciales_en_mensajes_de_error(self):
        secreto = "mi-token-super-secreto-999"
        with patch.dict(os.environ, {"BCCH_API_TOKEN": secreto}, clear=False):
            with patch.object(
                bcch_live,
                "buscar_series_live",
                side_effect=bcch_live.BdeApiError(
                    f"Falla remota en token={secreto} con clave {secreto}"
                ),
            ):
                status, _, cuerpo = invocar_asgi(self.app, "GET", "/api/v1/bcch/search")
        self.assertEqual(status, 502)
        texto = cuerpo.decode("utf-8")
        self.assertNotIn(secreto, texto)
        self.assertIn("[REDACTED]", texto)

    def test_bcch_search_validacion_422(self):
        for params in (
            {"frequency": "WEEKLY"},
            {"limit": 0},
            {"limit": 201},
        ):
            with self.subTest(params=params):
                status, _, cuerpo = invocar_asgi(
                    self.app, "GET", "/api/v1/bcch/search", params=params
                )
                self.assertEqual(status, 422)
                self.assertEqual(json.loads(cuerpo)["codigo"], "filtros_invalidos")

    def test_bcch_series_200_503_502_y_422(self):
        serie = "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.A"
        payload_ok = {"series_id": serie, "observaciones": [{"fecha": "2024-01-01", "valor": "1234.5"}]}
        with patch.object(
            bcch_live, "obtener_serie_live", return_value=payload_ok
        ) as mock_serie:
            status, _, cuerpo = invocar_asgi(
                self.app,
                "GET",
                f"/api/v1/bcch/series/{serie}",
                params={"firstdate": "2015-01-01", "lastdate": "2024-12-31"},
            )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(cuerpo), payload_ok)
        mock_serie.assert_called_once_with(
            serie, firstdate="2015-01-01", lastdate="2024-12-31"
        )

        with patch.object(
            bcch_live,
            "obtener_serie_live",
            side_effect=bcch_live.FaltaTokenBCChError("Sin token BCCh."),
        ):
            status, _, cuerpo = invocar_asgi(
                self.app, "GET", f"/api/v1/bcch/series/{serie}"
            )
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(cuerpo)["codigo"], "falta_token_bcch")

        with patch.object(
            bcch_live,
            "obtener_serie_live",
            side_effect=bcch_live.BdeApiError("GetSeries: HTTP 500."),
        ):
            status, _, cuerpo = invocar_asgi(
                self.app, "GET", f"/api/v1/bcch/series/{serie}"
            )
        self.assertEqual(status, 502)
        self.assertEqual(json.loads(cuerpo)["codigo"], "error_bcch")

        status, _, cuerpo = invocar_asgi(
            self.app,
            "GET",
            f"/api/v1/bcch/series/{serie}",
            params={"firstdate": "2025-01-01", "lastdate": "2020-01-01"},
        )
        self.assertEqual(status, 422)
        self.assertEqual(json.loads(cuerpo)["codigo"], "filtros_invalidos")

    def test_estructura_aysen_200_503_502_y_422(self):
        estructura_ok = {
            "territorio": "11",
            "anio_desde": 2018,
            "anio_hasta": 2024,
            "actividades": [],
        }
        with patch.object(
            bcch_live, "obtener_estructura_aysen_live", return_value=estructura_ok
        ) as mock_est:
            status, _, cuerpo = invocar_asgi(
                self.app,
                "GET",
                "/api/v1/territorial/aysen/estructura",
                params={"anio_desde": 2018, "anio_hasta": 2024, "refresh": "true"},
            )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(cuerpo), estructura_ok)
        mock_est.assert_called_once_with(anio_desde=2018, anio_hasta=2024, refresh=True)

        with patch.object(
            bcch_live,
            "obtener_estructura_aysen_live",
            side_effect=bcch_live.FaltaTokenBCChError("Sin token configurado."),
        ):
            status, _, cuerpo = invocar_asgi(
                self.app, "GET", "/api/v1/territorial/aysen/estructura"
            )
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(cuerpo)["codigo"], "falta_token_bcch")

        with patch.object(
            bcch_live,
            "obtener_estructura_aysen_live",
            side_effect=bcch_live.BdeApiError("Error en BDE."),
        ):
            status, _, cuerpo = invocar_asgi(
                self.app, "GET", "/api/v1/territorial/aysen/estructura"
            )
        self.assertEqual(status, 502)
        self.assertEqual(json.loads(cuerpo)["codigo"], "error_bcch")

        status, _, cuerpo = invocar_asgi(
            self.app,
            "GET",
            "/api/v1/territorial/aysen/estructura",
            params={"anio_desde": 2025, "anio_hasta": 2020},
        )
        self.assertEqual(status, 422)
        self.assertEqual(json.loads(cuerpo)["codigo"], "filtros_invalidos")

    def test_fiscal_dipres_200_502_y_422(self):
        dipres_ok = {
            "anio": 2025,
            "region": "11",
            "fuente": "DIPRES · datos.gob.cl",
            "partidas": [],
        }
        with patch.object(
            dipres_ckan, "obtener_ejecucion_aysen_live", return_value=dipres_ok
        ) as mock_dipres:
            status, _, cuerpo = invocar_asgi(
                self.app,
                "GET",
                "/api/v1/fiscal/dipres",
                params={"anio": 2025, "refresh": "true"},
            )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(cuerpo), dipres_ok)
        mock_dipres.assert_called_once_with(anio=2025, refresh=True)

        for exc in (
            dipres_ckan.DipresCkanError("CKAN no responde"),
            URLError("fallo de red DIPRES"),
            TimeoutError("timeout DIPRES"),
        ):
            with self.subTest(exc=type(exc).__name__):
                with patch.object(
                    dipres_ckan, "obtener_ejecucion_aysen_live", side_effect=exc
                ):
                    status, _, cuerpo = invocar_asgi(
                        self.app, "GET", "/api/v1/fiscal/dipres"
                    )
                self.assertEqual(status, 502)
                datos = json.loads(cuerpo)
                self.assertEqual(datos["codigo"], "error_dipres")
                self.assertTrue(datos["mensaje"])

        status, _, cuerpo = invocar_asgi(
            self.app, "GET", "/api/v1/fiscal/dipres", params={"anio": 2019}
        )
        self.assertEqual(status, 422)
        self.assertEqual(json.loads(cuerpo)["codigo"], "filtros_invalidos")


class SinimRealIntegracionTest(unittest.TestCase):
    """Pruebas reales de SINIM (sin mocks) usando CT_SINIM_PATH temporal aislado."""

    def setUp(self):
        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        self.ruta_sinim = Path(directorio.name) / "sinim-aysen-importado.json"
        self.app = crear_app(demo_activa=True)

    def test_estado_pendiente_plantilla_importacion_valida_y_persistencia(self):
        with patch.dict(os.environ, {"CT_SINIM_PATH": str(self.ruta_sinim)}, clear=False):
            # 1. Sin archivo cargado: retorna HTTP 200 con estructura pendiente_importacion
            status, _, cuerpo = invocar_asgi(self.app, "GET", "/api/v1/fiscal/sinim")
            self.assertEqual(status, 200)
            vacio = json.loads(cuerpo)
            self.assertEqual(
                vacio,
                {
                    "cargado": False,
                    "comunas_esperadas": 10,
                    "resumen": None,
                    "comunas": [],
                    "fuente_trazabilidad": {
                        "institucion": "SINIM · SUBDERE (importación oficial local)",
                        "estado": "pendiente_importacion",
                        "nota": (
                            "SUBDERE/SINIM no dispone de API REST pública; importe un archivo "
                            "CSV o JSON oficial de las 10 comunas de Aysén."
                        ),
                    },
                },
            )

            # 2. Plantilla CSV descargable
            status, cabeceras, cuerpo = invocar_asgi(
                self.app, "GET", "/api/v1/fiscal/sinim/plantilla.csv"
            )
            self.assertEqual(status, 200)
            self.assertTrue(cabeceras["content-type"].startswith("text/csv"))
            self.assertIn("sinim-aysen-plantilla.csv", cabeceras["content-disposition"])
            lector = csv.reader(io.StringIO(cuerpo.decode("utf-8")))
            cabecera_csv = tuple(next(lector))
            self.assertEqual(cabecera_csv, sinim_importer.COLUMNAS_PLANTILLA)

            # 3. Importación CSV válida de las 10 comunas de Aysén
            csv_valido = _construir_csv_sinim_valido()
            status, _, cuerpo = invocar_asgi(
                self.app,
                "POST",
                "/api/v1/fiscal/sinim/importar",
                json_body={
                    "nombre_archivo": "sinim-aysen-2024.csv",
                    "contenido": csv_valido,
                },
            )
            self.assertEqual(status, 200)
            importado = json.loads(cuerpo)
            self.assertTrue(importado["cargado"])
            self.assertTrue(importado["valido"])
            self.assertEqual(len(importado["comunas"]), 10)
            self.assertTrue(self.ruta_sinim.is_file())

            # 4. Lectura posterior desde CT_SINIM_PATH
            status, _, cuerpo = invocar_asgi(self.app, "GET", "/api/v1/fiscal/sinim")
            self.assertEqual(status, 200)
            leido = json.loads(cuerpo)
            self.assertTrue(leido["cargado"])
            self.assertEqual(len(leido["comunas"]), 10)
            self.assertEqual(leido["resumen"], importado["resumen"])

    def test_rechaza_esquema_sinim_invalido_422_y_limite_5mb_413(self):
        with patch.dict(os.environ, {"CT_SINIM_PATH": str(self.ruta_sinim)}, clear=False):
            csv_invalido = (
                "cut,municipio,anio,unidad,etapa,ingresos_totales,gasto_total_devengado\n"
                "13101,Santiago,2024,millones CLP,devengado,1000,900\n"
            )
            status, _, cuerpo = invocar_asgi(
                self.app,
                "POST",
                "/api/v1/fiscal/sinim/importar",
                json_body={
                    "nombre_archivo": "santiago-invalido.csv",
                    "contenido": csv_invalido,
                },
            )
            self.assertEqual(status, 422)
            error = json.loads(cuerpo)
            self.assertEqual(error["codigo"], "esquema_sinim_invalido")
            self.assertEqual(
                error["mensaje"],
                "El archivo SINIM no cumple el esquema de las 10 comunas de Aysén.",
            )
            self.assertIsInstance(error["errores"], list)
            self.assertTrue(error["errores"])
            self.assertFalse(self.ruta_sinim.exists())

            # Exceso de tamaño (> 5 MB) -> HTTP 413
            contenido_grande = "a" * (5 * 1024 * 1024 + 1)
            status, _, cuerpo = invocar_asgi(
                self.app,
                "POST",
                "/api/v1/fiscal/sinim/importar",
                json_body={
                    "nombre_archivo": "enorme.csv",
                    "contenido": contenido_grande,
                },
            )
            self.assertEqual(status, 413)
            self.assertEqual(json.loads(cuerpo)["codigo"], "archivo_demasiado_grande")
            self.assertFalse(self.ruta_sinim.exists())


class CompatibilidadOpenApiV01Test(unittest.TestCase):
    """Verifica que los 5 endpoints OpenAPI v0.1.0 siguen intactos."""

    def test_contrato_openapi_y_rutas_base(self):
        app = crear_app(demo_activa=True)
        esquema = app.openapi()
        self.assertEqual(esquema["info"]["version"], "0.1.0")
        self.assertEqual(
            set(esquema["paths"].keys()),
            {
                "/territorios",
                "/publicaciones",
                "/pib",
                "/pib.csv",
                "/observaciones/{id}/procedencia",
            },
        )

        status, _, cuerpo = invocar_asgi(app, "GET", "/api/v1/territorios")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(cuerpo)), 17)

        status, _, cuerpo = invocar_asgi(app, "GET", "/api/v1/publicaciones")
        self.assertEqual(status, 200)
        cut = json.loads(cuerpo)[0]["id"]

        status, cabeceras, cuerpo = invocar_asgi(
            app,
            "GET",
            "/api/v1/pib",
            params={"anio_desde": 2025, "anio_hasta": 2025, "valoracion": "real", "limite": 2},
        )
        self.assertEqual(status, 200)
        self.assertEqual(cabeceras["x-publicacion"], cut)
        datos = json.loads(cuerpo)
        self.assertEqual(datos["total"], 17)
        obs_id = datos["datos"][0]["id"]

        status, cabeceras, cuerpo = invocar_asgi(
            app,
            "GET",
            "/api/v1/pib.csv",
            params={"anio_desde": 2025, "anio_hasta": 2025, "valoracion": "real"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(cabeceras["x-publicacion"], cut)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(cuerpo.decode("utf-8"))))), 17)

        status, _, cuerpo = invocar_asgi(
            app, "GET", f"/api/v1/observaciones/{obs_id}/procedencia"
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(cuerpo)["publicacion"], cut)


if __name__ == "__main__":
    unittest.main()
