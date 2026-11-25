"""Pruebas unitarias sin red para el conector en vivo BCCh (``bcch_live.py``)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pipelines.economia import bcch_live, bde_api


ACTIVIDADES_AYSEN_13: tuple[tuple[str, str, str], ...] = (
    # (segmento_codigo, nombre_actividad, valor_miles_millones_ultimo_anio)
    ("12.Z.Z", "Administración pública", "300"),
    ("02.04.Z", "Pesca", "250"),
    ("07.Z.Z", "Comercio, restaurantes y hoteles", "120"),
    ("11.Z.Z", "Servicios personales", "90"),
    ("06.Z.Z", "Construcción", "70"),
    ("08.Z.Z", "Transporte, información y comunicaciones", "50"),
    ("04.Z.Z", "Industria manufacturera", "40"),
    ("01.Z.Z", "Agropecuario-silvícola", "30"),
    ("05.Z.Z", "Electricidad, gas, agua y gestión de desechos", "15"),
    ("09.Z.Z", "Servicios financieros y empresariales", "15"),
    ("10.Z.Z", "Servicios de vivienda e inmobiliarios", "10"),
    ("03.Z.Z", "Minería", "5"),
    ("13.Z.Z", "Otras actividades de servicios", "5"),
)
# Suma exacta de las 13 actividades = 1000 miles de millones CLP = 1.000.000 millones CLP
# PIB total nominal Aysén = 1080 miles de millones CLP = 1.080.000 millones CLP
# Diferencia impuestos sobre los productos = 80.000 millones CLP


def _construir_catalogo_anual_aysen() -> dict:
    filas: list[dict] = [
        {
            "seriesId": "F032.PIB.FLU.R.CLP.HIST18.Z.Z.0.A",
            "frequencyCode": "ANNUAL",
            "spanishTitle": "PIB, volumen a precios del año anterior encadenado, referencia 2018 (miles de millones de pesos encadenados)",
            "englishTitle": "GDP chained volume (billions of pesos)",
            "firstObservation": "01-01-2013",
            "lastObservation": "01-01-2025",
            "updatedAt": "18-03-2026",
        },
        {
            "seriesId": "F032.PIB.FLU.N.CLP.HIST18.Z.Z.0.A",
            "frequencyCode": "ANNUAL",
            "spanishTitle": "PIB, precios corrientes (miles de millones de pesos)",
            "englishTitle": "GDP current prices (billions of pesos)",
            "firstObservation": "01-01-2013",
            "lastObservation": "01-01-2025",
            "updatedAt": "18-03-2026",
        },
    ]

    for region in bde_api.REGIONES:
        nombre = bde_api.NOMBRES_TERRITORIOS[region]
        filas.append({
            "seriesId": f"F035.PIB.FLU.R.CLP.2018.Z.Z.Z.{region}.0.A",
            "frequencyCode": "ANNUAL",
            "spanishTitle": f"PIB regional {nombre}, volumen a precios del año anterior encadenado, referencia 2018 (miles de millones de pesos encadenados)",
            "firstObservation": "01-01-2013",
            "lastObservation": "01-01-2025",
            "updatedAt": "18-03-2026",
        })
        filas.append({
            "seriesId": f"F035.PIB.FLU.N.CLP.2018.Z.Z.Z.{region}.0.A",
            "frequencyCode": "ANNUAL",
            "spanishTitle": f"PIB regional {nombre}, precios corrientes (miles de millones de pesos)",
            "firstObservation": "01-01-2013",
            "lastObservation": "01-01-2025",
            "updatedAt": "18-03-2026",
        })

    for seg, nombre_act, _val in ACTIVIDADES_AYSEN_13:
        filas.append({
            "seriesId": f"F035.PIB.FLU.N.CLP.2018.{seg}.11.0.A",
            "frequencyCode": "ANNUAL",
            "spanishTitle": f"PIB regional Aysén, {nombre_act}, precios corrientes (miles de millones de pesos)",
            "firstObservation": "01-01-2013",
            "lastObservation": "01-01-2025",
            "updatedAt": "20-03-2026",
        })
        filas.append({
            "seriesId": f"F035.PIB.FLU.R.CLP.2018.{seg}.11.0.A",
            "frequencyCode": "ANNUAL",
            "spanishTitle": f"PIB regional Aysén, {nombre_act}, volumen a precios del año anterior encadenado, referencia 2018 (miles de millones de pesos encadenados)",
            "firstObservation": "01-01-2013",
            "lastObservation": "01-01-2025",
            "updatedAt": "20-03-2026",
        })

    return {"Codigo": 0, "Descripcion": "Success", "SeriesInfos": filas}


def _construir_catalogo_trimestral_aysen() -> dict:
    return {
        "Codigo": 0,
        "Descripcion": "Success",
        "SeriesInfos": [
            {
                "seriesId": "F035.PIB.FLU.R.CLP.2018.COM.Z.Z.11.0.T",
                "frequencyCode": "QUARTERLY",
                "spanishTitle": "PIB regional Aysén, Comercio trimestral, volumen encadenado (miles de millones de pesos encadenados)",
                "firstObservation": "01-01-2013",
                "lastObservation": "01-10-2025",
                "updatedAt": "22-03-2026",
            },
            {
                "seriesId": "F035.PIB.FLU.R.CLP.2018.SERV.Z.Z.11.0.T",
                "frequencyCode": "QUARTERLY",
                "spanishTitle": "PIB regional Aysén, Servicios trimestral, volumen encadenado (miles de millones de pesos encadenados)",
                "firstObservation": "01-01-2013",
                "lastObservation": "01-10-2025",
                "updatedAt": "22-03-2026",
            },
            {
                "seriesId": "F035.PIB.FLU.R.CLP.2018.PB.Z.Z.11.0.T",
                "frequencyCode": "QUARTERLY",
                "spanishTitle": "PIB regional Aysén, Producción de bienes trimestral, volumen encadenado (miles de millones de pesos encadenados)",
                "firstObservation": "01-01-2013",
                "lastObservation": "01-10-2025",
                "updatedAt": "22-03-2026",
            },
            {
                "seriesId": "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.T",
                "frequencyCode": "QUARTERLY",
                "spanishTitle": "PIB regional Aysén total trimestral, volumen encadenado (miles de millones de pesos encadenados)",
                "firstObservation": "01-01-2013",
                "lastObservation": "01-10-2025",
                "updatedAt": "22-03-2026",
            },
            {
                "seriesId": "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.13.0.T",
                "frequencyCode": "QUARTERLY",
                "spanishTitle": "PIB regional Metropolitana total trimestral, volumen encadenado (miles de millones de pesos encadenados)",
                "firstObservation": "01-01-2013",
                "lastObservation": "01-10-2025",
                "updatedAt": "22-03-2026",
            },
        ],
    }


def _construir_get_series(codigo: str, descrip: str, obs: list[tuple[str, str | None, str]]) -> dict:
    return {
        "Codigo": 0,
        "Descripcion": "Success",
        "Series": {
            "seriesId": codigo,
            "descripEsp": descrip,
            "Obs": [
                {"indexDateString": fecha, "value": valor, "statusCode": estado}
                for fecha, valor, estado in obs
            ],
        },
    }


class CredencialesBCChLiveTests(unittest.TestCase):
    def setUp(self) -> None:
        bcch_live.limpiar_cache_memoria()

    def test_resuelve_bcch_api_token_y_vite_token_con_precedencia(self):
        with TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "VITE_BCENTRAL_TOKEN=vite-env-secreto\n"
                "NEXT_PUBLIC_BCENTRAL_TOKEN=next-env-secreto\n",
                encoding="utf-8",
            )
            with patch.dict("os.environ", {}, clear=True):
                cred_vite = bcch_live.obtener_credenciales_bcch(env_path=env_file)
                self.assertEqual(cred_vite.modo, "token")
                self.assertEqual(cred_vite.parametros_consulta(), {"token": "vite-env-secreto"})
                self.assertNotIn("vite-env-secreto", repr(cred_vite))
                self.assertNotIn("vite-env-secreto", str(cred_vite))

            # BCCH_API_TOKEN en entorno tiene precedencia sobre .env
            with patch.dict("os.environ", {"BCCH_API_TOKEN": "bcch-proc-secreto"}, clear=True):
                cred_proc = bcch_live.obtener_credenciales_bcch(env_path=env_file)
                self.assertEqual(cred_proc.parametros_consulta(), {"token": "bcch-proc-secreto"})
                self.assertNotIn("bcch-proc-secreto", repr(cred_proc))

            # VITE_BCENTRAL_TOKEN en entorno tiene precedencia sobre BCCH_API_TOKEN en .env
            env_file.write_text("BCCH_API_TOKEN=bcch-env-secundario\n", encoding="utf-8")
            with patch.dict("os.environ", {"VITE_BCENTRAL_TOKEN": "vite-proc-prioritario"}, clear=True):
                cred_ent = bcch_live.obtener_credenciales_bcch(env_path=env_file)
                self.assertEqual(cred_ent.parametros_consulta(), {"token": "vite-proc-prioritario"})

    def test_resuelve_next_public_y_user_pass(self):
        with TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("NEXT_PUBLIC_BCENTRAL_TOKEN=next-tok-123\n", encoding="utf-8")
            with patch.dict("os.environ", {}, clear=True):
                cred = bcch_live.obtener_credenciales_bcch(env_path=env_file)
                self.assertEqual(cred.parametros_consulta(), {"token": "next-tok-123"})

            env_file.write_text("BCCH_API_USER=usr@test.cl\nBCCH_API_PASS=clave#99\n", encoding="utf-8")
            with patch.dict("os.environ", {}, clear=True):
                cred_up = bcch_live.obtener_credenciales_bcch(env_path=env_file)
                self.assertEqual(cred_up.modo, "user_pass")
                self.assertEqual(cred_up.parametros_consulta(), {"user": "usr@test.cl", "pass": "clave#99"})
                self.assertNotIn("clave#99", repr(cred_up))

    def test_falta_token_lanza_error_especifico_y_seguro(self):
        with TemporaryDirectory() as tmp:
            env_inexistente = Path(tmp) / ".env"
            with patch.dict("os.environ", {}, clear=True):
                with self.assertRaises(bcch_live.FaltaTokenBCChError) as caught:
                    bcch_live.obtener_credenciales_bcch(env_path=env_inexistente)
                self.assertIsInstance(caught.exception, bde_api.BdeApiError)
                self.assertEqual(
                    str(caught.exception),
                    "Falta configurar BCCH_API_TOKEN (o VITE_BCENTRAL_TOKEN) en .env local del servidor.",
                )

            # Usuario sin clave lanza FaltaTokenBCChError sin exponer usuario
            with patch.dict("os.environ", {"BCCH_API_USER": "secreto@ejemplo.cl"}, clear=True):
                with self.assertRaises(bcch_live.FaltaTokenBCChError) as caught2:
                    bcch_live.obtener_credenciales_bcch(env_path=env_inexistente)
                self.assertNotIn("secreto@ejemplo.cl", str(caught2.exception))


class BuscarYObtenerSerieLiveTests(unittest.TestCase):
    def setUp(self) -> None:
        bcch_live.limpiar_cache_memoria()

    def test_buscar_series_live_filtra_sin_tildes_limita_y_cachea_15_min(self):
        catalogo_anual = _construir_catalogo_anual_aysen()
        catalogo_trim = _construir_catalogo_trimestral_aysen()
        llamadas: list[tuple[str, str]] = []

        def fake_descargar(cred, funcion, timeout=30, **params):
            llamadas.append((funcion, params.get("frequency", "")))
            payload = catalogo_anual if params.get("frequency") == "ANNUAL" else catalogo_trim
            return json.dumps(payload).encode("utf-8"), payload

        with patch.dict("os.environ", {"VITE_BCENTRAL_TOKEN": "tok-busqueda-secreto"}, clear=True), patch.object(
            bcch_live, "descargar", side_effect=fake_descargar
        ):
            # Consulta con tilde y minúsculas
            res1 = bcch_live.buscar_series_live(frequency="ANNUAL", query="aysen administracion publica", limit=1)
            self.assertEqual(res1["total"], 2)  # nominal y real
            self.assertEqual(len(res1["series"]), 1)
            self.assertEqual(res1["fuente_trazabilidad"]["funcion"], "SearchSeries")
            self.assertEqual(res1["fuente_trazabilidad"]["frecuencia"], "ANNUAL")
            self.assertEqual(res1["fuente_trazabilidad"]["endpoint"], bde_api.ENDPOINT)
            self.assertFalse(res1["fuente_trazabilidad"]["desde_cache"])
            self.assertNotIn("tok-busqueda-secreto", json.dumps(res1))

            item = res1["series"][0]
            for campo in ("seriesId", "spanishTitle", "frequencyCode", "firstObservation", "lastObservation", "updatedAt"):
                self.assertIn(campo, item)

            # Segunda llamada ANNUAL usa caché en memoria
            res2 = bcch_live.buscar_series_live(frequency="ANNUAL", query="02.04.Z", limit=10)
            self.assertEqual(res2["total"], 2)
            self.assertTrue(res2["fuente_trazabilidad"]["desde_cache"])
            self.assertEqual(llamadas, [("SearchSeries", "ANNUAL")])

            # Llamada QUARTERLY dispara nueva descarga para esa frecuencia
            res_q = bcch_live.buscar_series_live(frequency="QUARTERLY", query="comercio", limit=5)
            self.assertEqual(res_q["total"], 1)
            self.assertEqual(res_q["series"][0]["seriesId"], "F035.PIB.FLU.R.CLP.2018.COM.Z.Z.11.0.T")
            self.assertEqual(llamadas, [("SearchSeries", "ANNUAL"), ("SearchSeries", "QUARTERLY")])

        # Frecuencia no soportada
        with self.assertRaises(bde_api.BdeApiError):
            bcch_live.buscar_series_live(frequency="WEEKLY")

    def test_buscar_series_live_expira_cache_despues_de_15_minutos(self):
        catalogo_anual = _construir_catalogo_anual_aysen()
        llamadas = 0

        def fake_descargar(cred, funcion, timeout=30, **params):
            nonlocal llamadas
            llamadas += 1
            return json.dumps(catalogo_anual).encode("utf-8"), catalogo_anual

        reloj = [1000.0]

        with patch.dict("os.environ", {"BCCH_API_TOKEN": "tok-ttl"}, clear=True), patch.object(
            bcch_live, "descargar", side_effect=fake_descargar
        ), patch.object(bcch_live.time, "monotonic", side_effect=lambda: reloj[0]):
            r1 = bcch_live.buscar_series_live("ANNUAL", query="pesca", limit=5)
            self.assertFalse(r1["fuente_trazabilidad"]["desde_cache"])
            reloj[0] = 1500.0  # 500s < 900s
            r2 = bcch_live.buscar_series_live("ANNUAL", query="pesca", limit=5)
            self.assertTrue(r2["fuente_trazabilidad"]["desde_cache"])
            reloj[0] = 1901.0  # > 900s -> expira TTL de 15 min
            r3 = bcch_live.buscar_series_live("ANNUAL", query="pesca", limit=5)
            self.assertFalse(r3["fuente_trazabilidad"]["desde_cache"])

        self.assertEqual(llamadas, 2)

    def test_guardar_cache_bloquea_contenido_con_credencial(self):
        cred = bde_api.Credenciales(modo="token", token="tok-prohibido-en-cache")
        with TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "cache.json"
            with self.assertRaisesRegex(bde_api.BdeApiError, "credencial"):
                bcch_live._guardar_cache_estructura(ruta, {"debug": "tok-prohibido-en-cache"}, cred)
            self.assertFalse(ruta.exists())

    def test_obtener_serie_live_preserva_texto_decimal_exacto_y_status_code(self):
        codigo = "F035.PIB.FLU.N.CLP.2018.02.04.Z.11.0.A"
        payload = _construir_get_series(
            codigo,
            "PIB regional Aysén, Pesca, precios corrientes (miles de millones de pesos)",
            [
                ("01-01-2025", "NaN", "ND"),
                ("01-01-2023", "0", "OK"),
                ("01-01-2024", "250.1234567890123456789", "OK"),
            ],
        )

        def fake_descargar(cred, funcion, timeout=30, **params):
            self.assertEqual(funcion, "GetSeries")
            self.assertEqual(params["timeseries"], codigo)
            self.assertEqual(params["firstdate"], "2023-01-01")
            self.assertEqual(params["lastdate"], "2025-12-31")
            return json.dumps(payload).encode("utf-8"), payload

        with patch.dict("os.environ", {"BCCH_API_TOKEN": "tok-serie-secreto"}, clear=True), patch.object(
            bcch_live, "descargar", side_effect=fake_descargar
        ):
            res = bcch_live.obtener_serie_live(codigo, firstdate="2023-01-01", lastdate="2025-12-31")

        self.assertEqual(res["fuente_trazabilidad"]["funcion"], "GetSeries")
        self.assertEqual(res["fuente_trazabilidad"]["series_consultadas"], [codigo])
        self.assertEqual(res["fuente_trazabilidad"]["endpoint"], bde_api.ENDPOINT)
        self.assertEqual(res["serie"]["seriesId"], codigo)
        self.assertIn("Pesca", res["serie"]["descripEsp"])
        self.assertNotIn("tok-serie-secreto", json.dumps(res))

        obs = res["serie"]["observaciones"]
        self.assertEqual(len(obs), 3)
        # Ordenado cronológicamente
        self.assertEqual(obs[0], {"fecha": "2023-01-01", "anio": 2023, "valor": "0", "estado": "OK"})
        # Precisión mayor a float64 preservada intacta
        self.assertEqual(
            obs[1],
            {"fecha": "2024-01-01", "anio": 2024, "valor": "250.1234567890123456789", "estado": "OK"},
        )
        self.assertEqual(obs[2], {"fecha": "2025-01-01", "anio": 2025, "valor": None, "estado": "ND"})


class EstructuraAysenLiveTests(unittest.TestCase):
    def setUp(self) -> None:
        bcch_live.limpiar_cache_memoria()

    def _hacer_fake_descargar_aysen(self, registro_llamadas: list[tuple[str, dict]]):
        cat_anual = _construir_catalogo_anual_aysen()
        cat_trim = _construir_catalogo_trimestral_aysen()

        series_anuales: dict[str, dict] = {
            # Chile real: 2024=200000, 2025=205000 -> crecimiento = +2.5%
            "F032.PIB.FLU.R.CLP.HIST18.Z.Z.0.A": _construir_get_series(
                "F032.PIB.FLU.R.CLP.HIST18.Z.Z.0.A",
                "PIB, volumen a precios del año anterior encadenado, referencia 2018 (miles de millones de pesos encadenados)",
                [("01-01-2024", "200000", "OK"), ("01-01-2025", "205000", "OK")],
            ),
            # Chile nominal: 2024=250000, 2025=270000
            "F032.PIB.FLU.N.CLP.HIST18.Z.Z.0.A": _construir_get_series(
                "F032.PIB.FLU.N.CLP.HIST18.Z.Z.0.A",
                "PIB, precios corrientes (miles de millones de pesos)",
                [("01-01-2024", "250000", "OK"), ("01-01-2025", "270000", "OK")],
            ),
            # Aysén real: 2024=1000, 2025=1040 -> crecimiento = +4%
            "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.A": _construir_get_series(
                "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.A",
                "PIB regional Aysén, volumen encadenado (miles de millones de pesos encadenados)",
                [("01-01-2024", "1000", "OK"), ("01-01-2025", "1040", "OK")],
            ),
            # Aysén nominal: 2024=1000, 2025=1080 -> participación nacional 2025 = 1080/270000 * 100 = 0.4%
            "F035.PIB.FLU.N.CLP.2018.Z.Z.Z.11.0.A": _construir_get_series(
                "F035.PIB.FLU.N.CLP.2018.Z.Z.Z.11.0.A",
                "PIB regional Aysén, precios corrientes (miles de millones de pesos)",
                [("01-01-2024", "1000", "OK"), ("01-01-2025", "1080", "OK")],
            ),
        }

        for seg, nombre_act, val_2025 in ACTIVIDADES_AYSEN_13:
            cod = f"F035.PIB.FLU.N.CLP.2018.{seg}.11.0.A"
            val_2024 = str(Decimal(val_2025) * Decimal("0.9"))
            series_anuales[cod] = _construir_get_series(
                cod,
                f"PIB regional Aysén, {nombre_act}, precios corrientes (miles de millones de pesos)",
                [("01-01-2024", val_2024, "OK"), ("01-01-2025", val_2025, "OK")],
            )

        series_trimestrales: dict[str, dict] = {
            "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.T": _construir_get_series(
                "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.T",
                "PIB regional Aysén total trimestral (miles de millones de pesos encadenados)",
                [("01-01-2025", "250.5", "OK"), ("01-04-2025", "260.25", "OK")],
            ),
            "F035.PIB.FLU.R.CLP.2018.PB.Z.Z.11.0.T": _construir_get_series(
                "F035.PIB.FLU.R.CLP.2018.PB.Z.Z.11.0.T",
                "PIB regional Aysén, Producción de bienes trimestral (miles de millones de pesos encadenados)",
                [("01-01-2025", "110.1", "OK"), ("01-04-2025", "115.2", "OK")],
            ),
            "F035.PIB.FLU.R.CLP.2018.SERV.Z.Z.11.0.T": _construir_get_series(
                "F035.PIB.FLU.R.CLP.2018.SERV.Z.Z.11.0.T",
                "PIB regional Aysén, Servicios trimestral (miles de millones de pesos encadenados)",
                [("01-01-2025", "140.4", "OK"), ("01-04-2025", "145.05", "OK")],
            ),
        }

        def fake_descargar(cred, funcion, timeout=30, **params):
            registro_llamadas.append((funcion, dict(params)))
            if funcion == "SearchSeries":
                payload = cat_anual if params["frequency"] == "ANNUAL" else cat_trim
                return json.dumps(payload).encode("utf-8"), payload
            cod = params["timeseries"]
            payload = series_anuales.get(cod) or series_trimestrales[cod]
            return json.dumps(payload).encode("utf-8"), payload

        return fake_descargar

    def test_estructura_aysen_calcula_admin_publica_pesca_hhi_trimestral_y_cache(self):
        llamadas: list[tuple[str, dict]] = []
        fake_descargar = self._hacer_fake_descargar_aysen(llamadas)

        with TemporaryDirectory() as tmp:
            cache_file = Path(tmp) / "bcch-aysen-sectorial-live.json"
            with patch.dict("os.environ", {"VITE_BCENTRAL_TOKEN": "tok-aysen-super-secreto"}, clear=True), patch.object(
                bcch_live, "descargar", side_effect=fake_descargar
            ):
                resultado = bcch_live.obtener_estructura_aysen_live(
                    anio_desde=2013,
                    anio_hasta=2025,
                    refresh=False,
                    cache_path=cache_file,
                )

            # Verificar llamadas: 2 SearchSeries (ANNUAL + QUARTERLY) + 17 GetSeries anuales + 3 GetSeries trimestrales
            search_calls = [p["frequency"] for fn, p in llamadas if fn == "SearchSeries"]
            get_calls = [p["timeseries"] for fn, p in llamadas if fn == "GetSeries"]
            self.assertEqual(search_calls, ["ANNUAL", "QUARTERLY"])
            self.assertEqual(len(get_calls), 20)

            # Verificar datos generales y trazabilidad sin secretos
            self.assertEqual(resultado["territorio"]["codigo"], "11")
            self.assertEqual(resultado["ultimo_anio"], 2025)
            self.assertFalse(resultado["fuente_trazabilidad"]["desde_cache"])
            self.assertTrue(cache_file.is_file())
            self.assertNotIn("tok-aysen-super-secreto", cache_file.read_text(encoding="utf-8"))

            resumen = resultado["resumen_pib"]
            # Niveles normalizados a millones CLP (* 1000 exacto)
            self.assertEqual(resumen["aysen_nominal_millones"], "1080000")
            self.assertEqual(resumen["aysen_real_millones"], "1040000")
            self.assertEqual(resumen["chile_nominal_millones"], "270000000")
            self.assertEqual(resumen["chile_real_millones"], "205000000")

            # Participación nacional = 1080000 * 100 / 270000000 = 0.4%
            self.assertEqual(Decimal(resumen["participacion_aysen_en_chile_pct"]), Decimal("0.4"))
            # Crecimiento real Aysén = (1040 - 1000) / 1000 * 100 = 4%
            self.assertEqual(Decimal(resumen["crecimiento_real_aysen_pct"]), Decimal("4"))
            # Crecimiento real Chile = (205000 - 200000) / 200000 * 100 = 2.5%
            self.assertEqual(Decimal(resumen["crecimiento_real_chile_pct"]), Decimal("2.5"))

            # Suma de 13 actividades = 1.000.000 millones; diferencia impuestos productos = 80.000 millones
            self.assertEqual(resumen["suma_actividades_nominal_millones"], "1000000")
            self.assertEqual(resumen["diferencia_impuestos_productos_millones"], "80000")

            # Verificar 13 actividades ordenadas descendentemente por valor_millones
            actividades = resultado["actividades"]
            self.assertEqual(len(actividades), 13)
            valores_dec = [Decimal(a["valor_millones"]) for a in actividades]
            self.assertEqual(valores_dec, sorted(valores_dec, reverse=True))

            # Administración Pública (código 12, valor 300.000 millones):
            # - sobre suma actividades (1.000.000): 30%
            # - sobre PIB Aysén (1.080.000): 300000*100/1080000 = 27.7777...%
            admin_pub = resumen["sectores_clave"]["administracion_publica"]
            self.assertIsNotNone(admin_pub)
            self.assertEqual(admin_pub["codigo_actividad"], "12")
            self.assertEqual(admin_pub["valor_millones"], "300000")
            self.assertEqual(Decimal(admin_pub["participacion_actividades_pct"]), Decimal("30"))
            esperado_admin_pib = (Decimal("300000") * Decimal("100") / Decimal("1080000")).quantize(Decimal("0.000001"))
            self.assertEqual(
                Decimal(admin_pub["participacion_pib_pct"]).quantize(Decimal("0.000001")),
                esperado_admin_pib,
            )
            self.assertTrue(actividades[0]["es_administracion_publica"])

            # Pesca (código 02.04.Z, valor 250.000 millones):
            # - sobre suma actividades (1.000.000): 25%
            # - sobre PIB Aysén (1.080.000): 250000*100/1080000 = 23.148148...%
            pesca = resumen["sectores_clave"]["pesca"]
            self.assertIsNotNone(pesca)
            self.assertEqual(pesca["codigo_actividad"], "02.04.Z")
            self.assertEqual(pesca["valor_millones"], "250000")
            self.assertEqual(Decimal(pesca["participacion_actividades_pct"]), Decimal("25"))
            esperado_pesca_pib = (Decimal("250000") * Decimal("100") / Decimal("1080000")).quantize(Decimal("0.000001"))
            self.assertEqual(
                Decimal(pesca["participacion_pib_pct"]).quantize(Decimal("0.000001")),
                esperado_pesca_pib,
            )
            self.assertTrue(actividades[1]["es_pesca"])

            # HHI exacto = 10000 * sum(v_i^2) / (1000^2)
            # v = [300, 250, 120, 90, 70, 50, 40, 30, 15, 15, 10, 5, 5]
            # sum(v^2) = 90000+62500+14400+8100+4900+2500+1600+900+225+225+100+25+25 = 185500
            # HHI = 10000 * 185500 / 1000000 = 1855
            self.assertEqual(resumen["concentracion_hhi"]["estado"], "informado")
            self.assertEqual(Decimal(resumen["concentracion_hhi"]["valor"]), Decimal("1855"))

            # Trimestral: 3 series clave en prioridad (TOTAL, PB, SERV), excluyendo región 13 y cuarta serie COM
            trim = resultado["trimestral"]
            self.assertTrue(trim["disponible"])
            self.assertEqual(trim["rango"], {"desde": "2023-01-01", "hasta": "2025-12-31"})
            self.assertEqual(
                [s["seriesId"] for s in trim["series"]],
                [
                    "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.T",
                    "F035.PIB.FLU.R.CLP.2018.PB.Z.Z.11.0.T",
                    "F035.PIB.FLU.R.CLP.2018.SERV.Z.Z.11.0.T",
                ],
            )
            self.assertEqual(trim["series"][0]["observaciones"][0]["periodo"], "2025-T1")
            self.assertEqual(trim["series"][0]["observaciones"][0]["valor_millones"], "250500")

            # Segunda llamada sin refresh lee desde caché en disco SIN tocar red ni requerir token
            def prohibir_red(*args, **kwargs):
                raise AssertionError("No debe llamar a descargar cuando el caché 24h está vigente")

            with patch.dict("os.environ", {}, clear=True), patch.object(
                bcch_live, "descargar", side_effect=prohibir_red
            ):
                desde_cache = bcch_live.obtener_estructura_aysen_live(
                    anio_desde=2013,
                    anio_hasta=2025,
                    refresh=False,
                    env_path=Path(tmp) / "no-existe.env",
                    cache_path=cache_file,
                )
            self.assertTrue(desde_cache["fuente_trazabilidad"]["desde_cache"])
            self.assertEqual(desde_cache["resumen_pib"], resultado["resumen_pib"])
            self.assertEqual(desde_cache["actividades"], resultado["actividades"])

            # Si el caché tiene más de 24 horas, vuelve a consultar en vivo
            datos_viejos = json.loads(cache_file.read_text(encoding="utf-8"))
            datos_viejos["fuente_trazabilidad"]["extraido_en"] = (
                datetime.now(timezone.utc) - timedelta(hours=25)
            ).isoformat(timespec="seconds")
            cache_file.write_text(json.dumps(datos_viejos), encoding="utf-8")

            llamadas_expirado: list[tuple[str, dict]] = []
            with patch.dict("os.environ", {"BCCH_API_TOKEN": "tok-renovado"}, clear=True), patch.object(
                bcch_live, "descargar", side_effect=self._hacer_fake_descargar_aysen(llamadas_expirado)
            ):
                renovado = bcch_live.obtener_estructura_aysen_live(
                    anio_desde=2013,
                    anio_hasta=2025,
                    refresh=False,
                    cache_path=cache_file,
                )
            self.assertFalse(renovado["fuente_trazabilidad"]["desde_cache"])
            self.assertGreater(len(llamadas_expirado), 0)

            # Con refresh=True ignora caché vigente y vuelve a consultar
            llamadas_refresh: list[tuple[str, dict]] = []
            with patch.dict("os.environ", {"BCCH_API_TOKEN": "tok-refresh"}, clear=True), patch.object(
                bcch_live, "descargar", side_effect=self._hacer_fake_descargar_aysen(llamadas_refresh)
            ):
                refrescado = bcch_live.obtener_estructura_aysen_live(
                    anio_desde=2013,
                    anio_hasta=2025,
                    refresh=True,
                    cache_path=cache_file,
                )
            self.assertFalse(refrescado["fuente_trazabilidad"]["desde_cache"])
            self.assertEqual(
                [p["frequency"] for fn, p in llamadas_refresh if fn == "SearchSeries"],
                ["ANNUAL", "QUARTERLY"],
            )


if __name__ == "__main__":
    unittest.main()
