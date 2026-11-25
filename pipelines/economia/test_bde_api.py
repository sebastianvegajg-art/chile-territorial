"""Pruebas unitarias sin red para el extractor autenticado de la API BDE."""

from __future__ import annotations

from datetime import date
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from jsonschema import Draft202012Validator, FormatChecker

from pipelines.economia import bde_api


RAIZ_REPO = Path(__file__).resolve().parents[2]
ESQUEMA_PIB = json.loads((RAIZ_REPO / "contracts" / "pib-datos.schema.json").read_text(encoding="utf-8"))
VALIDADOR_PIB = Draft202012Validator(ESQUEMA_PIB, format_checker=FormatChecker())


def construir_catalogo_completo(
    incluir_sectoriales: bool = True,
    actividades: tuple[str, ...] = tuple(f"{n:02d}" for n in range(1, 14)),
    excluir_codigos: set[str] | None = None,
    extras: list[dict] | None = None,
    titulos_override: dict[str, str] | None = None,
) -> dict:
    """Construye un payload sintético realista de ``SearchSeries(frequency=ANNUAL)``."""
    excluir = excluir_codigos or set()
    overrides = titulos_override or {}
    filas: list[dict] = []

    def agregar(codigo: str, titulo: str, actualizado: str = "18-03-2026") -> None:
        if codigo in excluir:
            return
        filas.append({
            "seriesId": codigo,
            "frequencyCode": "ANNUAL",
            "spanishTitle": overrides.get(codigo, titulo),
            "englishTitle": f"EN {codigo}",
            "firstObservation": "01-01-2012",
            "lastObservation": "01-01-2025",
            "updatedAt": actualizado,
            "createdAt": "01-01-2020",
        })

    agregar(
        "F032.PIB.FLU.R.CLP.HIST18.Z.Z.0.A",
        "PIB, volumen a precios del año anterior encadenado, referencia 2018 (miles de millones de pesos encadenados)",
    )
    agregar(
        "F032.PIB.FLU.N.CLP.HIST18.Z.Z.0.A",
        "PIB, precios corrientes (miles de millones de pesos)",
    )
    for region in bde_api.REGIONES:
        nombre = bde_api.NOMBRES_TERRITORIOS[region]
        agregar(
            f"F035.PIB.FLU.R.CLP.2018.Z.Z.Z.{region}.0.A",
            f"PIB regional {nombre}, volumen a precios del año anterior encadenado, referencia 2018 "
            "(miles de millones de pesos encadenados)",
        )
        agregar(
            f"F035.PIB.FLU.N.CLP.2018.Z.Z.Z.{region}.0.A",
            f"PIB regional {nombre}, precios corrientes (miles de millones de pesos)",
        )
        if incluir_sectoriales:
            for act in actividades:
                agregar(
                    f"F035.PIB.FLU.R.CLP.2018.{act}.Z.Z.{region}.0.A",
                    f"PIB regional {nombre}, actividad {act}, volumen a precios del año anterior encadenado, "
                    "referencia 2018 (miles de millones de pesos encadenados)",
                )
                agregar(
                    f"F035.PIB.FLU.N.CLP.2018.{act}.Z.Z.{region}.0.A",
                    f"PIB regional {nombre}, actividad {act}, precios corrientes (miles de millones de pesos)",
                )

    if extras:
        filas.extend(extras)
    return {"Codigo": 0, "Descripcion": "Success", "SeriesInfos": filas}


def construir_serie_obs(
    codigo: str,
    observaciones: list[tuple[str, str | None, str]],
    descrip_es: str | None = None,
) -> dict:
    return {
        "Codigo": 0,
        "Descripcion": "Success",
        "Series": {
            "seriesId": codigo,
            "descripEsp": descrip_es or f"Descripción {codigo}",
            "Obs": [
                {"indexDateString": fecha, "value": valor, "statusCode": estado}
                for fecha, valor, estado in observaciones
            ],
        },
    }


def construir_insumos_34_series(
    con_2012_en: set[str] | None = None,
    anios_publicados: tuple[int, ...] = (2013, 2014),
    nd_en: dict[tuple[str, str, int], str] | None = None,
    cero_en: set[tuple[str, str, int]] | None = None,
) -> tuple[bytes, dict[str, bytes]]:
    """Genera bytes de catálogo y 34 respuestas GetSeries con decimales exactos."""
    catalogo_payload = construir_catalogo_completo(incluir_sectoriales=True)
    catalogo_bytes = json.dumps(catalogo_payload, ensure_ascii=False).encode("utf-8")
    catalogo = bde_api.parsear_catalogo_anual(catalogo_payload)
    totales = bde_api.descubrir_series_totales(catalogo)

    territorios_2012 = set(bde_api.TERRITORIOS) if con_2012_en is None else con_2012_en
    nd_mapa = nd_en or {}
    ceros = cero_en or set()

    series_bytes: dict[str, bytes] = {}
    for (territorio, valoracion), serie in totales.items():
        base = 100000 if territorio == "CL" else (1000 + int(territorio) * 100)
        obs: list[tuple[str, str | None, str]] = []
        if valoracion == "real" and territorio in territorios_2012:
            # 2012 exacto para poder verificar tasa de crecimiento 2013 con exactitud.
            obs.append(("01-01-2012", f"{base}.000", "OK"))
        for idx, anio in enumerate(anios_publicados):
            clave = (territorio, valoracion, anio)
            if clave in nd_mapa:
                obs.append((f"01-01-{anio}", "NaN", nd_mapa[clave]))
            elif clave in ceros:
                obs.append((f"01-01-{anio}", "0", "OK"))
            else:
                # 2013 sube 5% respecto de 2012, 2014 agrega decimales exactos.
                if idx == 0:
                    valor_str = f"{base * 105 // 100}.000" if territorio == "CL" else f"{base * 105 / 100:.2f}"
                else:
                    valor_str = f"{base + 123.456789:.6f}"
                obs.append((f"01-01-{anio}", valor_str, "OK"))
        payload = construir_serie_obs(serie.codigo, obs, descrip_es=serie.titulo_es)
        series_bytes[serie.codigo] = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return catalogo_bytes, series_bytes


class AutenticacionYSeguridadTests(unittest.TestCase):
    def test_resolver_token_y_user_pass_desde_entorno(self):
        cred_token = bde_api.resolver_credenciales({"BCCH_API_TOKEN": "tok-ficticio-123"})
        self.assertEqual(cred_token.modo, "token")
        self.assertEqual(cred_token.parametros_consulta(), {"token": "tok-ficticio-123"})
        self.assertNotIn("tok-ficticio-123", repr(cred_token))
        self.assertNotIn("tok-ficticio-123", str(cred_token))

        cred_up = bde_api.resolver_credenciales({
            "BCCH_API_USER": "analista@ejemplo.test",
            "BCCH_API_PASS": "clave#secreta+99",
        })
        self.assertEqual(cred_up.modo, "user_pass")
        self.assertEqual(
            cred_up.parametros_consulta(),
            {"user": "analista@ejemplo.test", "pass": "clave#secreta+99"},
        )
        self.assertNotIn("analista@ejemplo.test", repr(cred_up))
        self.assertNotIn("clave#secreta+99", str(cred_up))

    def test_resolver_desde_archivo_env_y_precedencia_entorno(self):
        with TemporaryDirectory() as tmp:
            archivo_env = Path(tmp) / ".env"
            archivo_env.write_text(
                "\n".join([
                    "# Credenciales locales de prueba",
                    "export BCCH_API_USER='usuario.env@ejemplo.test'",
                    'BCCH_API_PASS="clave#env\\"123" # comentario ignorado',
                    "OTRA_VAR=valor#sin#espacio # comentario inline",
                ]) + "\n",
                encoding="utf-8",
            )
            leido = bde_api.cargar_archivo_env(archivo_env)
            self.assertEqual(leido["OTRA_VAR"], "valor#sin#espacio")

            cred = bde_api.resolver_credenciales({}, env_path=archivo_env)
            self.assertEqual(cred.modo, "user_pass")
            self.assertEqual(cred.parametros_consulta(), {
                "user": "usuario.env@ejemplo.test",
                "pass": 'clave#env"123',
            })

            # El entorno del proceso tiene precedencia sobre .env.
            cred_override = bde_api.resolver_credenciales(
                {"BCCH_API_TOKEN": "token-entorno-prioritario"},
                env_path=archivo_env,
            )
            self.assertEqual(cred_override.modo, "token")
            self.assertEqual(cred_override.parametros_consulta(), {"token": "token-entorno-prioritario"})

    def test_credenciales_incompletas_o_ausentes_fallan(self):
        with self.assertRaisesRegex(bde_api.BdeApiError, "Faltan credenciales"):
            bde_api.resolver_credenciales({})
        with self.assertRaisesRegex(bde_api.BdeApiError, "Autenticación incompleta"):
            bde_api.resolver_credenciales({"BCCH_API_USER": "solo-usuario@ejemplo.test"})
        with self.assertRaisesRegex(bde_api.BdeApiError, "Autenticación incompleta"):
            bde_api.resolver_credenciales({"BCCH_API_PASS": "solo-clave"})

    @patch.object(bde_api, "build_opener")
    def test_descargar_envia_parametros_user_pass_y_token(self, mock_build_opener):
        captured_urls: list[str] = []

        def fake_open(req, timeout=30):
            captured_urls.append(req.full_url)
            return BytesIO(b'{"Codigo":0,"Descripcion":"Success","SeriesInfos":[]}')

        opener = Mock()
        opener.open.side_effect = fake_open
        mock_build_opener.return_value = opener

        cred_token = bde_api.Credenciales(modo="token", token="tok-abc")
        bde_api.descargar(cred_token, "SearchSeries", frequency="ANNUAL")

        cred_up = bde_api.Credenciales(modo="user_pass", usuario="usr@ejemplo.test", clave="pwd+1")
        bde_api.descargar(cred_up, "GetSeries", timeseries="F032.TEST")

        q1 = parse_qs(urlparse(captured_urls[0]).query)
        self.assertEqual(q1, {"token": ["tok-abc"], "function": ["SearchSeries"], "frequency": ["ANNUAL"]})

        q2 = parse_qs(urlparse(captured_urls[1]).query)
        self.assertEqual(
            q2,
            {
                "user": ["usr@ejemplo.test"],
                "pass": ["pwd+1"],
                "function": ["GetSeries"],
                "timeseries": ["F032.TEST"],
            },
        )

    @patch.object(bde_api, "build_opener")
    def test_rechaza_respuesta_que_refleja_usuario_o_clave_o_token(self, mock_build_opener):
        opener = Mock()
        mock_build_opener.return_value = opener

        # Reflejo codificado de pass en modo user_pass
        opener.open.return_value = BytesIO(b'{"Codigo":0,"echo":"clave%2Bficticia"}')
        cred_up = bde_api.Credenciales(modo="user_pass", usuario="usr@ejemplo.test", clave="clave+ficticia")
        with self.assertRaisesRegex(bde_api.BdeApiError, "reflejada") as caught:
            bde_api.descargar(cred_up, "GetSeries")
        self.assertNotIn("ficticia", str(caught.exception))
        self.assertNotIn("usr@ejemplo.test", str(caught.exception))

        # Reflejo de usuario
        opener.open.return_value = BytesIO(b'{"Codigo":0,"msg":"usr%40ejemplo.test"}')
        with self.assertRaisesRegex(bde_api.BdeApiError, "reflejada") as caught2:
            bde_api.descargar(cred_up, "GetSeries")
        self.assertNotIn("ejemplo.test", str(caught2.exception))

    @patch.object(bde_api, "sleep")
    @patch.object(bde_api, "build_opener")
    def test_error_http_no_filtra_credenciales_ni_reintenta_401(self, mock_build_opener, mock_sleep):
        opener = Mock()
        opener.open.side_effect = HTTPError(
            "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx?user=u@test&pass=secreto-999",
            401,
            "Unauthorized",
            None,
            None,
        )
        mock_build_opener.return_value = opener
        cred = bde_api.Credenciales(modo="user_pass", usuario="u@test", clave="secreto-999")
        with self.assertRaisesRegex(bde_api.BdeApiError, "HTTP 401") as caught:
            bde_api.descargar(cred, "GetSeries")
        self.assertNotIn("secreto-999", str(caught.exception))
        self.assertNotIn("u@test", str(caught.exception))
        mock_sleep.assert_not_called()

    def test_sanear_mensaje_oculta_secretos_y_query(self):
        cred = bde_api.Credenciales(modo="user_pass", usuario="analista@test.cl", clave="clave+super")
        saneado = bde_api.sanear_mensaje(
            "Error en https://x/?user=analista@test.cl&pass=clave%2Bsuper detalle clave+super",
            cred,
        )
        self.assertNotIn("analista@test.cl", saneado)
        self.assertNotIn("clave+super", saneado)
        self.assertNotIn("clave%2Bsuper", saneado)


class NormalizacionPibTotalTests(unittest.TestCase):
    def test_34_series_con_2012_cumplen_esquema_y_calculan_crecimiento_2013(self):
        catalogo_bytes, series_bytes = construir_insumos_34_series(
            con_2012_en=set(bde_api.TERRITORIOS),
            anios_publicados=(2013, 2014),
        )
        extraido = "2026-11-24T22:50:00+00:00"
        lote = bde_api.normalizar_pib_total(
            catalogo_bytes,
            series_bytes,
            extraido_en=extraido,
            desde=date(2012, 1, 1),
            hasta=date(2025, 12, 31),
        )

        # Cumplimiento estricto de contracts/pib-datos.schema.json
        errores = list(VALIDADOR_PIB.iter_errors(lote))
        self.assertEqual(errores, [])

        # 1 catálogo + 34 series = 35 artefactos, todos con URL limpia sin query string
        self.assertEqual(len(lote["artefactos"]), 35)
        for art in lote["artefactos"]:
            self.assertEqual(art["url"], bde_api.ENDPOINT)
            self.assertNotIn("?", art["url"])

        # Cobertura publicable (anio >= 2013, conforme a 001_pib.sql): 34*2 niveles + 17*2 crecimientos + 16*2 participaciones = 134
        # Los 17 niveles auxiliares de 2012 permanecen en observaciones/procedencias como insumo del crecimiento 2013.
        self.assertEqual(len(lote["observaciones"]), 151)
        self.assertEqual(lote["publicacion"]["cobertura"], {"esperadas": 134, "disponibles": 134})

        # Verificar precisión decimal exacta (miles de millones * 1000 -> millones CLP)
        obs_por_clave = {
            (o["territorio"], o["anio"], o["metrica"], o["valoracion"]): o
            for o in lote["observaciones"]
        }
        self.assertEqual(obs_por_clave[("CL", 2012, "nivel", "real")]["valor"], "100000000")
        self.assertEqual(obs_por_clave[("CL", 2013, "nivel", "real")]["valor"], "105000000")
        # 2014: 100123.456789 * 1000 = 100123456.789 exacto sin pérdida de decimales
        self.assertEqual(obs_por_clave[("CL", 2014, "nivel", "real")]["valor"], "100123456.789")
        # Crecimiento 2013 de CL calculado exactamente: (105000000 - 100000000) * 100 / 100000000 = 5
        crec_cl_2013 = obs_por_clave[("CL", 2013, "crecimiento", "real")]
        self.assertEqual(crec_cl_2013["estado"], "informado")
        self.assertEqual(crec_cl_2013["clase"], "oficial")
        self.assertEqual(crec_cl_2013["valor"], "5")

        # Verificar que no existan observaciones nominales ni derivadas para 2012
        self.assertNotIn(("CL", 2012, "nivel", "nominal"), obs_por_clave)
        self.assertNotIn(("CL", 2012, "crecimiento", "real"), obs_por_clave)
        self.assertNotIn(("11", 2012, "participacion", "nominal"), obs_por_clave)

        # Verificar compatibilidad estricta con el cargador oficial de la API
        from apps.api.lote_oficial import validar_lote_oficial
        validar_lote_oficial(lote)

        # Procedencia de crecimiento 2013 referencia ambos niveles (2013 y 2012)
        proc_por_obs = {p["observacion"]: p for p in lote["procedencias"]}
        self.assertEqual(
            proc_por_obs[crec_cl_2013["id"]]["insumos"],
            [
                obs_por_clave[("CL", 2013, "nivel", "real")]["id"],
                obs_por_clave[("CL", 2012, "nivel", "real")]["id"],
            ],
        )

    def test_faltante_explicito_cuando_2012_falta_y_caso_mixto_cl_con_2012(self):
        # Caso 1: Ningún territorio tiene 2012
        cat_b, ser_b = construir_insumos_34_series(con_2012_en=set(), anios_publicados=(2013, 2014))
        lote_sin_2012 = bde_api.normalizar_pib_total(
            cat_b, ser_b, "2026-11-24T22:50:00+00:00", date(2012, 1, 1), date(2025, 12, 31)
        )
        self.assertEqual(list(VALIDADOR_PIB.iter_errors(lote_sin_2012)), [])
        self.assertEqual(lote_sin_2012["publicacion"]["cobertura"], {"esperadas": 134, "disponibles": 117})
        crec_2013 = [
            o for o in lote_sin_2012["observaciones"] if o["anio"] == 2013 and o["metrica"] == "crecimiento"
        ]
        self.assertEqual(len(crec_2013), 17)
        self.assertTrue(all(o["estado"] == "faltante" and o["valor"] is None and o["clase"] == "no_disponible" for o in crec_2013))

        # Caso 2: Solo Chile (CL) tiene 2012, las 16 regiones comienzan en 2013
        cat_m, ser_m = construir_insumos_34_series(con_2012_en={"CL"}, anios_publicados=(2013, 2014))
        lote_mixto = bde_api.normalizar_pib_total(
            cat_m, ser_m, "2026-11-24T22:50:00+00:00", date(2012, 1, 1), date(2025, 12, 31)
        )
        self.assertEqual(list(VALIDADOR_PIB.iter_errors(lote_mixto)), [])
        obs_m = {(o["territorio"], o["anio"], o["metrica"], o["valoracion"]): o for o in lote_mixto["observaciones"]}
        self.assertEqual(obs_m[("CL", 2013, "crecimiento", "real")]["estado"], "informado")
        self.assertEqual(obs_m[("CL", 2013, "crecimiento", "real")]["valor"], "5")
        self.assertEqual(obs_m[("11", 2013, "crecimiento", "real")]["estado"], "faltante")
        self.assertIsNone(obs_m[("11", 2013, "crecimiento", "real")]["valor"])

    def test_distingue_cero_informado_de_faltante_nd_y_rechaza_nan_ok(self):
        cat_b, ser_b = construir_insumos_34_series(
            con_2012_en={"CL"},
            anios_publicados=(2013, 2014),
            nd_en={("11", "nominal", 2014): "ND"},
            cero_en={("12", "nominal", 2014)},
        )
        lote = bde_api.normalizar_pib_total(
            cat_b, ser_b, "2026-11-24T22:50:00+00:00", date(2012, 1, 1), date(2025, 12, 31)
        )
        self.assertEqual(list(VALIDADOR_PIB.iter_errors(lote)), [])
        obs = {(o["territorio"], o["anio"], o["metrica"], o["valoracion"]): o for o in lote["observaciones"]}

        # Cero informado se preserva como "0" informado/oficial
        self.assertEqual(obs[("12", 2014, "nivel", "nominal")]["valor"], "0")
        self.assertEqual(obs[("12", 2014, "nivel", "nominal")]["estado"], "informado")
        self.assertEqual(obs[("12", 2014, "participacion", "nominal")]["valor"], "0")

        # ND queda como faltante y su participación derivada hereda faltante
        self.assertIsNone(obs[("11", 2014, "nivel", "nominal")]["valor"])
        self.assertEqual(obs[("11", 2014, "nivel", "nominal")]["estado"], "faltante")
        self.assertEqual(obs[("11", 2014, "participacion", "nominal")]["estado"], "faltante")

        # NaN con statusCode=OK debe fallar
        codigo_aysen = "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.A"
        ser_b[codigo_aysen] = json.dumps(
            construir_serie_obs(
                codigo_aysen,
                [("01-01-2013", "NaN", "OK")],
                descrip_es="PIB regional Aysén, volumen encadenado (miles de millones de pesos encadenados)",
            )
        ).encode("utf-8")
        with self.assertRaisesRegex(bde_api.BdeApiError, "no finito"):
            bde_api.normalizar_pib_total(
                cat_b, ser_b, "2026-11-24T22:50:00+00:00", date(2012, 1, 1), date(2025, 12, 31)
            )

    def test_falla_si_falta_una_de_las_34_series_totales_o_titulo_inconsistente(self):
        cat_incompleto = construir_catalogo_completo(
            excluir_codigos={"F035.PIB.FLU.N.CLP.2018.Z.Z.Z.16.0.A"}
        )
        catalogo = bde_api.parsear_catalogo_anual(cat_incompleto)
        with self.assertRaisesRegex(bde_api.BdeApiError, "16/nominal"):
            bde_api.descubrir_series_totales(catalogo)

        cat_inconsistente = construir_catalogo_completo(
            titulos_override={
                "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.A": "PIB regional Aysén, precios corrientes (miles de millones de pesos)"
            }
        )
        with self.assertRaisesRegex(bde_api.BdeApiError, "inconsistente"):
            bde_api.descubrir_series_totales(bde_api.parsear_catalogo_anual(cat_inconsistente))


class InventarioSectorialTests(unittest.TestCase):
    def test_inventario_sectorial_416_exacto_y_determinista(self):
        catalogo_bytes = json.dumps(construir_catalogo_completo(incluir_sectoriales=True)).encode("utf-8")
        extraido = "2026-11-24T22:55:00+00:00"
        inv1 = bde_api.construir_inventario_sectorial(catalogo_bytes, extraido)
        inv2 = bde_api.construir_inventario_sectorial(catalogo_bytes, extraido)
        self.assertEqual(inv1, inv2)

        self.assertEqual(inv1["referencia_prueba_excel"]["encontradas"], 416)
        self.assertEqual(inv1["referencia_prueba_excel"]["diferencia_total"], 0)
        self.assertTrue(inv1["referencia_prueba_excel"]["coincide_total_416"])
        self.assertEqual(inv1["cobertura"]["por_valoracion"]["real"]["encontradas"], 208)
        self.assertEqual(inv1["cobertura"]["por_valoracion"]["nominal"]["encontradas"], 208)
        self.assertEqual(inv1["cobertura"]["anomalias"], [])
        self.assertEqual(inv1["comparacion_identificadores"]["estado"], "pendiente_inventario_original")
        self.assertEqual(len(inv1["inventario"]["hashes"]["codigos_sectoriales_sha256"]), 64)

    def test_inventario_sectorial_reporta_altas_bajas_y_cambios_metadatos(self):
        # Línea base de 416 series
        cat_base = json.dumps(construir_catalogo_completo(incluir_sectoriales=True)).encode("utf-8")
        inv_base = bde_api.construir_inventario_sectorial(cat_base, "2026-01-15T10:00:00+00:00")
        ref_bytes = json.dumps(inv_base, ensure_ascii=False).encode("utf-8")

        # Nuevo corte: baja 1 serie en región 11, alta 1 nueva actividad "14" en región 15,
        # y cambio de título/unidad en región 01 actividad 01 real.
        codigo_baja = "F035.PIB.FLU.N.CLP.2018.13.Z.Z.11.0.A"
        codigo_alta = "F035.PIB.FLU.R.CLP.2018.14.Z.Z.15.0.A"
        codigo_cambio = "F035.PIB.FLU.R.CLP.2018.01.Z.Z.01.0.A"
        cat_nuevo = construir_catalogo_completo(
            incluir_sectoriales=True,
            excluir_codigos={codigo_baja},
            extras=[{
                "seriesId": codigo_alta,
                "frequencyCode": "ANNUAL",
                "spanishTitle": "PIB regional Arica y Parinacota, actividad 14 nueva, volumen encadenado (miles de millones de pesos encadenados)",
                "updatedAt": "24-11-2026",
            }],
            titulos_override={
                codigo_cambio: "PIB regional Tarapacá, agropecuario revisado, volumen encadenado (millones de pesos encadenados)"
            },
        )
        inv_nuevo = bde_api.construir_inventario_sectorial(
            json.dumps(cat_nuevo).encode("utf-8"),
            "2026-11-24T22:55:00+00:00",
            referencia_sectorial_bytes=ref_bytes,
            nombre_referencia="catalogo-base-416.json",
        )

        # Total sigue siendo 416 (416 - 1 + 1), pero hay anomalías de cobertura por región y actividad
        self.assertEqual(inv_nuevo["referencia_prueba_excel"]["encontradas"], 416)
        self.assertFalse(inv_nuevo["referencia_prueba_excel"]["coincide_total_416"])
        self.assertEqual(inv_nuevo["cobertura"]["por_region"]["11"]["diferencia"], -1)
        self.assertEqual(inv_nuevo["cobertura"]["por_region"]["15"]["diferencia"], 1)

        comp = inv_nuevo["comparacion_identificadores"]
        self.assertEqual(comp["estado"], "comparado")
        self.assertEqual(comp["altas"], [codigo_alta])
        self.assertEqual(comp["bajas"], [codigo_baja])
        self.assertEqual(len(comp["cambios_metadatos"]), 1)
        self.assertEqual(comp["cambios_metadatos"][0]["serie_bde"], codigo_cambio)
        self.assertIn("unidad", comp["cambios_metadatos"][0]["cambios"])
        self.assertIn("titulo_es", comp["cambios_metadatos"][0]["cambios"])


class FlujoCompletoYReproducibilidadTests(unittest.TestCase):
    def test_extraccion_completa_y_reproduccion_bit_a_bit_sin_red_ni_credenciales(self):
        catalogo_bytes, series_bytes = construir_insumos_34_series(
            con_2012_en=set(bde_api.TERRITORIOS),
            anios_publicados=(2013, 2014),
        )
        catalogo_payload = json.loads(catalogo_bytes.decode("utf-8"))
        series_payloads = {
            codigo: json.loads(raw.decode("utf-8")) for codigo, raw in series_bytes.items()
        }

        def fake_descargar(credenciales, funcion, timeout=30, **params):
            if funcion == "SearchSeries":
                return catalogo_bytes, catalogo_payload
            codigo = params["timeseries"]
            return series_bytes[codigo], series_payloads[codigo]

        cred = bde_api.Credenciales(
            modo="user_pass",
            usuario="usuario-secreto@ejemplo.test",
            clave="clave-secreta-xyz",
        )

        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            insumos_dir = base / "raw" / "bde-api-prueba"
            salida_pib = base / "published" / "pib-bde-api.json"
            salida_sec = base / "published" / "catalogo-sectorial-bde.json"

            with patch.object(bde_api, "descargar", side_effect=fake_descargar):
                bde_api.ejecutar_extraccion(
                    cred,
                    insumos_dir=insumos_dir,
                    desde=date(2012, 1, 1),
                    hasta=date(2025, 12, 31),
                    salida_pib=salida_pib,
                    salida_sectorial=salida_sec,
                )

            pib_original = salida_pib.read_bytes()
            sec_original = salida_sec.read_bytes()
            manifiesto_original = (insumos_dir / "manifiesto.json").read_bytes()

            # Ningún secreto en ningún archivo escrito
            for contenido in (pib_original, sec_original, manifiesto_original):
                self.assertFalse(bde_api.contiene_credencial(contenido, cred))

            # Validar lote publicado contra esquema oficial
            self.assertEqual(list(VALIDADOR_PIB.iter_errors(json.loads(pib_original.decode("utf-8")))), [])

            # Reproducir a nuevas rutas SIN RED y SIN CREDENCIALES mediante CLI main()
            salida_pib_repro = base / "repro" / "pib-bde-api.json"
            salida_sec_repro = base / "repro" / "catalogo-sectorial-bde.json"

            def prohibir_red(*args, **kwargs):
                raise AssertionError("No debe realizarse ninguna llamada de red en --reproducir")

            with patch.object(bde_api, "descargar", side_effect=prohibir_red), patch.dict(
                "os.environ", {}, clear=True
            ):
                codigo_salida = bde_api.main([
                    "--reproducir",
                    "--completo",
                    "--insumos",
                    str(insumos_dir),
                    "--salida",
                    str(salida_pib_repro),
                    "--salida-sectorial",
                    str(salida_sec_repro),
                ])
            self.assertEqual(codigo_salida, 0)
            self.assertEqual(salida_pib_repro.read_bytes(), pib_original)
            self.assertEqual(salida_sec_repro.read_bytes(), sec_original)

            # Si se altera 1 byte en raw, la verificación SHA-256 debe rechazar la reproducción
            archivo_catalogo = insumos_dir / "catalogo-anual.json"
            archivo_catalogo.write_bytes(archivo_catalogo.read_bytes() + b" ")
            with self.assertRaisesRegex(bde_api.BdeApiError, "Integridad SHA-256"):
                bde_api.reproducir_desde_raw(insumos_dir, salida_pib=base / "repro" / "fallo.json")

    def test_cli_inventario_sectorial_desde_env_solo_consulta_catalogo(self):
        catalogo_payload = construir_catalogo_completo(incluir_sectoriales=True)
        catalogo_bytes = json.dumps(catalogo_payload, ensure_ascii=False).encode("utf-8")
        llamadas: list[str] = []

        def fake_descargar(credenciales, funcion, timeout=30, **params):
            llamadas.append(funcion)
            self.assertEqual(credenciales.modo, "token")
            return catalogo_bytes, catalogo_payload

        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            env_file = base / ".env"
            env_file.write_text("BCCH_API_TOKEN=tok-env-solo-sectorial\n", encoding="utf-8")
            insumos_dir = base / "raw" / "bde-api-sec"
            salida_sec = base / "published" / "catalogo-sectorial-bde.json"

            with patch.object(bde_api, "descargar", side_effect=fake_descargar), patch.dict(
                "os.environ", {}, clear=True
            ):
                rc = bde_api.main([
                    "--env",
                    str(env_file),
                    "--inventario-sectorial",
                    "--insumos",
                    str(insumos_dir),
                    "--salida-sectorial",
                    str(salida_sec),
                ])

            self.assertEqual(rc, 0)
            self.assertEqual(llamadas, ["SearchSeries"])
            self.assertTrue(salida_sec.is_file())
            self.assertNotIn("tok-env-solo-sectorial", salida_sec.read_text(encoding="utf-8"))
            self.assertNotIn("tok-env-solo-sectorial", (insumos_dir / "manifiesto.json").read_text(encoding="utf-8"))

            # Reproducir solo el inventario sectorial sin red
            salida_sec_repro = base / "repro" / "catalogo-sectorial-bde.json"
            with patch.object(bde_api, "descargar", side_effect=AssertionError("Sin red")):
                rc2 = bde_api.main([
                    "--reproducir",
                    "--inventario-sectorial",
                    "--insumos",
                    str(insumos_dir),
                    "--salida-sectorial",
                    str(salida_sec_repro),
                ])
            self.assertEqual(rc2, 0)
            self.assertEqual(salida_sec_repro.read_bytes(), salida_sec.read_bytes())

    @patch.object(bde_api, "sleep")
    @patch.object(bde_api, "build_opener")
    def test_reintenta_error_transitorio_503_y_recupera(self, mock_build_opener, mock_sleep):
        opener = Mock()
        opener.open.side_effect = [
            HTTPError("https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx?token=tok", 503, "Busy", None, None),
            BytesIO(b'{"Codigo":0,"Descripcion":"Success","SeriesInfos":[]}'),
        ]
        mock_build_opener.return_value = opener
        cred = bde_api.Credenciales(modo="token", token="tok-transitorio")
        _raw, payload = bde_api.descargar(cred, "SearchSeries", frequency="ANNUAL")
        self.assertEqual(payload["Codigo"], 0)
        mock_sleep.assert_called_once_with(2)


if __name__ == "__main__":
    unittest.main()
