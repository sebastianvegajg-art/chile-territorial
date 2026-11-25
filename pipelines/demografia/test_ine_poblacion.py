"""Pruebas unitarias sin red para el extractor de población INE y PIB per cápita."""

from __future__ import annotations

from contextlib import redirect_stdout
from datetime import date
from decimal import Decimal
from hashlib import sha256
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pipelines.demografia import ine_poblacion
from pipelines.economia import bde_api


def construir_catalogo_poblacion(
    excluir: set[str] | None = None,
    titulos_override: dict[str, str] | None = None,
    codificacion: str = "utf-8",
) -> bytes:
    """Genera un payload sintético de ``SearchSeries(ANNUAL)`` con las 17 series INE."""
    excluir_set = excluir or set()
    overrides = titulos_override or {}
    filas: list[dict] = []

    for territorio in bde_api.TERRITORIOS:
        codigo = ine_poblacion.SERIES_POBLACION_INE[territorio]
        if codigo in excluir_set:
            continue
        if territorio == "CL":
            titulo = overrides.get(codigo, "Población total, INE (número de personas)")
            actualizado = "30-01-2026"
        else:
            nombre = bde_api.NOMBRES_TERRITORIOS[territorio]
            titulo = overrides.get(
                codigo,
                f"Población total; Población por sexo, región y edad, Región de {nombre}; "
                "nominal; stock; anual; número de personas; INE",
            )
            actualizado = "14-06-2022"
        filas.append({
            "seriesId": codigo,
            "frequencyCode": "ANNUAL",
            "spanishTitle": titulo,
            "englishTitle": f"Total population {territorio} (number of people); INE",
            "firstObservation": "01-01-2002",
            "lastObservation": "01-01-2035",
            "updatedAt": actualizado,
            "createdAt": actualizado,
        })

    payload = {"Codigo": 0, "Descripcion": "Success", "SeriesInfos": filas}
    return json.dumps(payload, ensure_ascii=False).encode(codificacion)


def construir_serie_poblacion(
    codigo: str,
    observaciones: list[tuple[str, str | None, str]],
    descrip_es: str | None = None,
    codificacion: str = "utf-8",
) -> bytes:
    payload = {
        "Codigo": 0,
        "Descripcion": "Success",
        "Series": {
            "seriesId": codigo,
            "descripEsp": descrip_es or f"Población total {codigo} (número de personas)",
            "Obs": [
                {"indexDateString": fecha, "value": valor, "statusCode": estado}
                for fecha, valor, estado in observaciones
            ],
        },
    }
    return json.dumps(payload, ensure_ascii=False).encode(codificacion)


def construir_insumos_17_series(
    anios: tuple[int, ...] = (2013, 2014, 2025, 2030),
    nd_en: dict[tuple[str, int], str] | None = None,
    desfase_cl: int = 0,
    codificacion: str = "utf-8",
) -> tuple[bytes, dict[str, bytes]]:
    """Genera bytes de catálogo y de las 17 series INE con valores deterministas."""
    nd_mapa = nd_en or {}
    catalogo_bytes = construir_catalogo_poblacion(codificacion=codificacion)
    series_bytes: dict[str, bytes] = {}

    # Primero genera las 16 regiones para calcular suma regional exacta.
    poblaciones_reg: dict[tuple[str, int], int] = {}
    for idx, region in enumerate(bde_api.REGIONES, start=1):
        codigo = ine_poblacion.SERIES_POBLACION_INE[region]
        obs: list[tuple[str, str | None, str]] = []
        for anio in anios:
            if (region, anio) in nd_mapa:
                obs.append((f"01-01-{anio}", None, nd_mapa[(region, anio)]))
                continue
            val = 100_000 * idx + (anio - 2013) * 1_000
            poblaciones_reg[(region, anio)] = val
            obs.append((f"01-01-{anio}", str(val), "OK"))
        series_bytes[codigo] = construir_serie_poblacion(codigo, obs, codificacion=codificacion)

    codigo_cl = ine_poblacion.SERIES_POBLACION_INE["CL"]
    obs_cl: list[tuple[str, str | None, str]] = []
    for anio in anios:
        if ("CL", anio) in nd_mapa:
            obs_cl.append((f"01-01-{anio}", None, nd_mapa[("CL", anio)]))
            continue
        suma_reg = sum(poblaciones_reg.get((r, anio), 0) for r in bde_api.REGIONES)
        obs_cl.append((f"01-01-{anio}", str(suma_reg + desfase_cl), "OK"))
    series_bytes[codigo_cl] = construir_serie_poblacion(codigo_cl, obs_cl, codificacion=codificacion)

    return catalogo_bytes, series_bytes


def construir_lote_pib_sintetico(
    niveles_real: dict[tuple[str, int], str | None],
    niveles_nominal: dict[tuple[str, int], str | None] | None = None,
    estado_override: dict[tuple[str, str, int], str] | None = None,
    clase: str = "oficial",
    incluir_2012: bool = True,
) -> dict:
    """Construye un lote compatible con ``pib-bde-api.json``."""
    est_ov = estado_override or {}
    nom = niveles_nominal if niveles_nominal is not None else niveles_real
    pub_id = "bcch-bde-api-2026-11-24-prueba0000000001"
    observaciones: list[dict] = []

    if incluir_2012:
        observaciones.append({
            "id": f"{pub_id}.CL.2012.nivel.real",
            "territorio": "CL",
            "anio": 2012,
            "metrica": "nivel",
            "valoracion": "real",
            "valor": "1000",
            "unidad": "millones CLP",
            "anio_referencia": 2018,
            "estado": "informado",
            "clase": clase,
            "publicacion": pub_id,
        })

    for (territorio, anio), valor in sorted(niveles_real.items()):
        estado = est_ov.get(("real", territorio, anio), "informado" if valor is not None else "faltante")
        observaciones.append({
            "id": f"{pub_id}.{territorio}.{anio}.nivel.real",
            "territorio": territorio,
            "anio": anio,
            "metrica": "nivel",
            "valoracion": "real",
            "valor": valor,
            "unidad": "millones CLP",
            "anio_referencia": 2018,
            "estado": estado,
            "clase": clase if estado in {"informado", "preliminar"} else "no_disponible",
            "publicacion": pub_id,
        })

    for (territorio, anio), valor in sorted(nom.items()):
        estado = est_ov.get(("nominal", territorio, anio), "informado" if valor is not None else "faltante")
        observaciones.append({
            "id": f"{pub_id}.{territorio}.{anio}.nivel.nominal",
            "territorio": territorio,
            "anio": anio,
            "metrica": "nivel",
            "valoracion": "nominal",
            "valor": valor,
            "unidad": "millones CLP",
            "anio_referencia": None,
            "estado": estado,
            "clase": clase if estado in {"informado", "preliminar"} else "no_disponible",
            "publicacion": pub_id,
        })

    return {
        "publicacion": {"id": pub_id, "estado": "aprobada", "fuente": "BCCh-BDE"},
        "observaciones": observaciones,
    }


def construir_lote_poblacion_sintetico(
    poblaciones: dict[tuple[str, int], str | None],
    estado_override: dict[tuple[str, int], str] | None = None,
    clase: str = "estimacion",
) -> dict:
    est_ov = estado_override or {}
    pub_id = "ine-poblacion-bde-2026-11-24-prueba0000000001"
    observaciones: list[dict] = []
    for (territorio, anio), valor in sorted(poblaciones.items()):
        estado = est_ov.get((territorio, anio), "informado" if valor is not None else "faltante")
        observaciones.append({
            "id": f"{pub_id}.{territorio}.{anio}.poblacion",
            "territorio": territorio,
            "nombre_territorio": bde_api.NOMBRES_TERRITORIOS.get(territorio, territorio),
            "anio": anio,
            "metrica": "poblacion",
            "valor": valor,
            "unidad": "personas",
            "estado": estado,
            "clase": clase if estado in {"informado", "preliminar"} else "no_disponible",
            "publicacion": pub_id,
        })
    return {
        "publicacion": {"id": pub_id, "estado": "aprobada", "fuente": "INE vía BCCh-BDE"},
        "observaciones": observaciones,
    }


class TestCatalogoYCredenciales(unittest.TestCase):
    def test_mapeo_exacto_17_series_verificadas(self) -> None:
        self.assertEqual(len(ine_poblacion.SERIES_POBLACION_INE), 17)
        self.assertEqual(set(ine_poblacion.SERIES_POBLACION_INE.keys()), set(bde_api.TERRITORIOS))
        self.assertEqual(len(set(ine_poblacion.SERIES_POBLACION_INE.values())), 17)
        self.assertEqual(ine_poblacion.SERIES_POBLACION_INE["CL"], "F049.POB.STO.INE1.01.A")
        self.assertEqual(ine_poblacion.SERIES_POBLACION_INE["11"], "F049.POBAI.STO.INE.AT.A")
        self.assertEqual(ine_poblacion.SERIES_POBLACION_INE["13"], "F049.POBRM.STO.INE.AT.A")
        self.assertEqual(ine_poblacion.SERIES_POBLACION_INE["16"], "F049.POBNB.STO.INE.AT.A")

    def test_credenciales_rechaza_alias_vite_y_next_public(self) -> None:
        entorno_invalido = {
            "VITE_BCCH_API_TOKEN": "secreto-no-permitido",
            "NEXT_PUBLIC_BCCH_API_TOKEN": "secreto-no-permitido-2",
            "VITE_BCCH_API_USER": "u",
            "NEXT_PUBLIC_BCCH_API_PASS": "p",
        }
        with self.assertRaises(bde_api.BdeApiError):
            ine_poblacion.resolver_credenciales(entorno_invalido)

        cred = ine_poblacion.resolver_credenciales({"BCCH_API_TOKEN": "tok-valido"})
        self.assertEqual(cred.modo, "token")
        self.assertNotIn("tok-valido", repr(cred))

    def test_descubrimiento_rechaza_serie_faltante_o_unidad_miles(self) -> None:
        cat_faltante = construir_catalogo_poblacion(excluir={"F049.POBAI.STO.INE.AT.A"})
        catalogo = bde_api.parsear_catalogo_anual(bde_api._cargar_json_bde(cat_faltante))
        with self.assertRaises(ine_poblacion.InePoblacionError):
            ine_poblacion.descubrir_series_poblacion(catalogo)

        cat_miles = construir_catalogo_poblacion(
            titulos_override={"F049.POB.STO.INE1.01.A": "Población total, INE (miles de personas)"}
        )
        catalogo_m = bde_api.parsear_catalogo_anual(bde_api._cargar_json_bde(cat_miles))
        with self.assertRaises(ine_poblacion.InePoblacionError):
            ine_poblacion.descubrir_series_poblacion(catalogo_m)


class TestExtraccionYReproduccion(unittest.TestCase):
    def test_extraccion_manifiesto_sha256_y_reproduccion_sin_red(self) -> None:
        anios = tuple(range(2013, 2031))
        catalogo_bytes, series_bytes = construir_insumos_17_series(
            anios=anios,
            desfase_cl=12500,
            codificacion="iso-8859-1",
        )
        cred = bde_api.Credenciales(modo="token", token="SECRETO_INE_TEST_9988")

        def mock_descargar(_cred, funcion, timeout=30, **params):
            if funcion == "SearchSeries":
                self.assertEqual(params.get("frequency"), "ANNUAL")
                return catalogo_bytes, bde_api._cargar_json_bde(catalogo_bytes, parse_float=str)
            if funcion == "GetSeries":
                codigo = params["timeseries"]
                self.assertEqual(params["firstdate"], "2013-01-01")
                self.assertEqual(params["lastdate"], "2030-12-31")
                crudo = series_bytes[codigo]
                return crudo, bde_api._cargar_json_bde(crudo, parse_float=str)
            raise AssertionError(f"Función inesperada: {funcion}")

        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            insumos_dir = base / "data" / "raw" / "ine-poblacion-20261125T000000Z"
            salida_1 = base / "data" / "published" / "poblacion-ine-regiones.json"
            salida_2 = base / "data" / "published" / "poblacion-reproducida.json"

            with patch.object(ine_poblacion, "descargar", side_effect=mock_descargar):
                resumen = ine_poblacion.ejecutar_extraccion(
                    cred,
                    insumos_dir=insumos_dir,
                    desde=date(2013, 1, 1),
                    hasta=date(2030, 12, 31),
                    salida_poblacion=salida_1,
                )

            self.assertEqual(resumen["publicacion"]["cobertura"]["series_esperadas"], 17)
            self.assertEqual(resumen["publicacion"]["cobertura"]["esperadas"], 17 * 18)
            self.assertEqual(resumen["publicacion"]["cobertura"]["disponibles"], 17 * 18)

            # Ningún archivo contiene el secreto.
            for archivo in [insumos_dir / "manifiesto.json", salida_1]:
                self.assertNotIn(b"SECRETO_INE_TEST_9988", archivo.read_bytes())

            # Manifiesto incluye catálogo + 17 series con SHA-256 exactos.
            manifiesto = json.loads((insumos_dir / "manifiesto.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifiesto["artefactos"]), 18)
            for art in manifiesto["artefactos"]:
                ruta_art = insumos_dir / art["archivo"]
                self.assertEqual(sha256(ruta_art.read_bytes()).hexdigest(), art["sha256"])

            # Verifica distinción estimación vs proyección y conciliación nacional-regional.
            publicado = json.loads(salida_1.read_text(encoding="utf-8"))
            self.assertEqual(
                publicado["publicacion"]["advertencia_escala_territorial"],
                ine_poblacion.ADVERTENCIA_ESCALA_PIB,
            )
            obs_aysen_2022 = next(
                o for o in publicado["observaciones"] if o["territorio"] == "11" and o["anio"] == 2022
            )
            obs_aysen_2025 = next(
                o for o in publicado["observaciones"] if o["territorio"] == "11" and o["anio"] == 2025
            )
            self.assertEqual(obs_aysen_2022["clase"], "estimacion")
            self.assertEqual(obs_aysen_2025["clase"], "proyeccion")

            conc_2013 = next(c for c in publicado["conciliacion_nacional_regional"] if c["anio"] == 2013)
            self.assertEqual(conc_2013["diferencia_cl_menos_regiones"], "12500")
            self.assertEqual(conc_2013["estado"], "diferencia_corte_vintage")

            # Reproducción bit-a-bit sin red ni credenciales.
            with patch.object(
                ine_poblacion, "descargar", side_effect=AssertionError("No debe usar red en --reproducir")
            ), redirect_stdout(io.StringIO()):
                codigo_cli = ine_poblacion.main([
                    "--reproducir",
                    "--insumos",
                    str(insumos_dir),
                    "--salida",
                    str(salida_2),
                ])

            self.assertEqual(codigo_cli, 0)
            self.assertEqual(salida_1.read_bytes(), salida_2.read_bytes())

            # Alterar 1 byte de un insumo debe fallar la verificación SHA-256.
            ruta_alterada = insumos_dir / "series" / "F049.POBAI.STO.INE.AT.A.json"
            ruta_alterada.write_bytes(ruta_alterada.read_bytes() + b" ")
            with self.assertRaises(ine_poblacion.InePoblacionError):
                ine_poblacion.reproducir_desde_raw(insumos_dir, salida_poblacion=base / "otra.json")

    def test_normalizar_maneja_nd_sin_inventar_cero(self) -> None:
        catalogo_bytes, series_bytes = construir_insumos_17_series(
            anios=(2013, 2014),
            nd_en={("11", 2014): "ND"},
        )
        lote = ine_poblacion.normalizar_poblacion_ine(
            catalogo_bytes,
            series_bytes,
            extraido_en="2026-11-25T01:00:00+00:00",
            desde=date(2013, 1, 1),
            hasta=date(2014, 12, 31),
        )
        obs = next(o for o in lote["observaciones"] if o["territorio"] == "11" and o["anio"] == 2014)
        self.assertIsNone(obs["valor"])
        self.assertEqual(obs["estado"], "faltante")
        self.assertEqual(obs["clase"], "no_disponible")


class TestPibPerCapitaYSigmaConvergencia(unittest.TestCase):
    def test_calculo_exacto_decimal34_ratio_ranking_y_sigma_convergencia(self) -> None:
        # Año 2013: 8 regiones con 10_000_000 CLP/persona y 8 con 30_000_000 CLP/persona
        # -> media exacta = 20_000_000, sigma poblacional exacta = 10_000_000, CV = 0.5 (50%)
        # Año 2014: todas convergen a 20_000_000 CLP/persona -> sigma = 0, CV = 0 -> tendencia "convergencia"
        niveles_real: dict[tuple[str, int], str | None] = {}
        niveles_nom: dict[tuple[str, int], str | None] = {}
        poblaciones: dict[tuple[str, int], str | None] = {}

        # Chile 2013: 100 millones CLP / 3 personas -> precisión exacta 34 dígitos: 33333333.33333333333333333333333333
        niveles_real[("CL", 2013)] = "100"
        niveles_nom[("CL", 2013)] = "120"
        poblaciones[("CL", 2013)] = "3"

        niveles_real[("CL", 2014)] = "200"
        niveles_nom[("CL", 2014)] = "240"
        poblaciones[("CL", 2014)] = "10"

        for idx, reg in enumerate(bde_api.REGIONES, start=1):
            pob = 100_000
            poblaciones[(reg, 2013)] = str(pob)
            poblaciones[(reg, 2014)] = str(pob)
            # 10_000_000 CLP/persona = 1_000_000 millones CLP para 100_000 personas
            if idx <= 8:
                niveles_real[(reg, 2013)] = "1000000"
                niveles_nom[(reg, 2013)] = "1100000"
            else:
                niveles_real[(reg, 2013)] = "3000000"
                niveles_nom[(reg, 2013)] = "3300000"
            niveles_real[(reg, 2014)] = "2000000"
            niveles_nom[(reg, 2014)] = "2200000"

        lote_pib = construir_lote_pib_sintetico(niveles_real, niveles_nom)
        lote_pob = construir_lote_poblacion_sintetico(poblaciones)

        res = ine_poblacion.calcular_pib_per_capita_nacional_y_regional(lote_pib, lote_pob)

        self.assertEqual(res["advertencia_escala_territorial"], ine_poblacion.ADVERTENCIA_ESCALA_PIB)
        self.assertTrue(res["metadatos"]["imputacion_pib_comunal_prohibida"])
        self.assertEqual(res["metadatos"]["anios"], [2013, 2014])

        # Verifica precisión Decimal(34) en 100 * 1_000_000 / 3
        cl_2013 = res["por_anio"]["2013"]["territorios"]["CL"]
        self.assertEqual(cl_2013["pib_real_per_capita_clp"], "33333333.33333333333333333333333333")
        self.assertEqual(cl_2013["pib_nominal_per_capita_clp"], "40000000")
        self.assertEqual(cl_2013["ratio_vs_chile_real"], "100")
        self.assertIsNone(cl_2013["ranking_regional_real"])

        # Verifica ratio vs Chile y empates en ranking regional (8 empatadas en #1, 8 empatadas en #9)
        r09_2013 = res["por_anio"]["2013"]["territorios"]["09"]
        r01_2013 = res["por_anio"]["2013"]["territorios"]["01"]
        self.assertEqual(r09_2013["pib_real_per_capita_clp"], "30000000")
        self.assertEqual(r09_2013["ranking_regional_real"], 1)
        self.assertEqual(r01_2013["pib_real_per_capita_clp"], "10000000")
        self.assertEqual(r01_2013["ranking_regional_real"], 9)
        # 30_000_000 / (100_000_000 / 3) * 100 = 90 exactamente
        self.assertEqual(Decimal(r09_2013["ratio_vs_chile_real"]).quantize(Decimal("0.0001")), Decimal("90.0000"))

        # Verifica σ-convergencia exacta en 2013 y 2014
        sigma_2013 = res["por_anio"]["2013"]["sigma_convergencia"]
        self.assertEqual(sigma_2013["estado"], "informado")
        self.assertEqual(sigma_2013["media_regional_real_clp"], "20000000")
        self.assertEqual(sigma_2013["desviacion_estandar_real_clp"], "10000000")
        self.assertEqual(sigma_2013["coeficiente_variacion_real"], "0.5")
        self.assertEqual(sigma_2013["coeficiente_variacion_real_pct"], "50")
        self.assertEqual(sigma_2013["brecha_max_min_real"], "3")

        sigma_2014 = res["por_anio"]["2014"]["sigma_convergencia"]
        self.assertEqual(sigma_2014["coeficiente_variacion_real"], "0")
        self.assertEqual(res["resumen_sigma_convergencia"]["tendencia_descriptiva"], "convergencia")
        self.assertEqual(res["resumen_sigma_convergencia"]["delta_coeficiente_variacion_real"], "-0.5")

    def test_denominador_cero_y_region_faltante_en_sigma(self) -> None:
        niveles = {(t, 2020): "1000" for t in bde_api.TERRITORIOS}
        poblaciones = {(t, 2020): "10000" for t in bde_api.TERRITORIOS}
        poblaciones[("11", 2020)] = "0"  # denominador cero

        lote_pib = construir_lote_pib_sintetico(niveles)
        lote_pob = construir_lote_poblacion_sintetico(poblaciones)
        res = ine_poblacion.calcular_pib_per_capita_nacional_y_regional(lote_pib, lote_pob)

        aysen = res["por_anio"]["2020"]["territorios"]["11"]
        self.assertIsNone(aysen["pib_real_per_capita_clp"])
        self.assertEqual(aysen["estado_real"], "faltante")
        self.assertIn("cero", aysen["motivo_real"].lower())

        sigma = res["por_anio"]["2020"]["sigma_convergencia"]
        self.assertEqual(sigma["estado"], "faltante")
        self.assertEqual(sigma["regiones_faltantes"], ["11"])
        self.assertIsNone(sigma["coeficiente_variacion_real"])

    def test_prohibe_imputar_pib_a_comunas(self) -> None:
        lote_pib_comunal = {
            "publicacion": {"id": "invalido"},
            "observaciones": [
                {
                    "id": "x.11101.2024.nivel.real",
                    "territorio": "11101",
                    "anio": 2024,
                    "metrica": "nivel",
                    "valoracion": "real",
                    "valor": "500",
                    "unidad": "millones CLP",
                    "anio_referencia": 2018,
                    "estado": "informado",
                    "clase": "oficial",
                }
            ],
        }
        lote_pob = construir_lote_poblacion_sintetico({("CL", 2024): "20000000"})
        with self.assertRaises(ine_poblacion.InePoblacionError) as ctx:
            ine_poblacion.calcular_pib_per_capita_nacional_y_regional(lote_pib_comunal, lote_pob)
        self.assertIn("346 comunas", str(ctx.exception))

        lote_pib_ok = construir_lote_pib_sintetico({("CL", 2024): "1000"})
        lote_pob_comunal = construir_lote_poblacion_sintetico({("11101", 2024): "60000"})
        with self.assertRaises(ine_poblacion.InePoblacionError) as ctx2:
            ine_poblacion.calcular_pib_per_capita_nacional_y_regional(lote_pib_ok, lote_pob_comunal)
        self.assertIn("346 comunas", str(ctx2.exception))


class TestImportarPoblacionComunalIne(unittest.TestCase):
    def test_importar_csv_largo_y_distincion_comuna_vs_municipalidad(self) -> None:
        csv_texto = (
            "codigo_comuna,nombre_comuna,region,anio,poblacion,tipo_dato\n"
            "1101,Iquique,1,2024,223.463,estimacion\n"
            "12201,Cabo de Hornos,12,2024,2.063,estimacion\n"
            "12202,Antártica,12,2024,138,estimacion\n"
            "11102,Lago Verde,11,2024,0,estimacion\n"
            "11303,Tortel,11,2024,ND,estimacion\n"
        ).encode("utf-8-sig")

        res = ine_poblacion.importar_poblacion_comunal_ine(csv_texto, "ine_comunas_2024.csv")

        self.assertEqual(res["archivo"]["formato_detectado"], "largo")
        self.assertEqual(res["archivo"]["sha256"], sha256(csv_texto).hexdigest())
        self.assertTrue(res["imputacion_pib_comunal_prohibida"])
        self.assertEqual(res["advertencia_escala_territorial"], ine_poblacion.ADVERTENCIA_ESCALA_PIB)

        # No inventa las comunas faltantes respecto a las 346 oficiales.
        self.assertEqual(res["cobertura"]["comunas_importadas"], 5)
        self.assertEqual(res["cobertura"]["comunas_faltantes_vs_346"], 341)
        self.assertFalse(res["cobertura"]["cobertura_completa_346"])
        # 5 comunas pero 4 municipalidades porque Antártica (12202) la administra Cabo de Hornos (12201).
        self.assertEqual(res["cobertura"]["municipalidades_representadas"], 4)
        self.assertTrue(res["cobertura"]["incluye_antartica_12202"])

        por_cut = {c["cut"]: c for c in res["comunas"]}
        self.assertIn("01101", por_cut)  # cero inicial normalizado
        self.assertFalse(por_cut["12202"]["tiene_municipalidad_propia"])
        self.assertEqual(por_cut["12202"]["cut_municipalidad_administradora"], "12201")
        self.assertTrue(por_cut["12201"]["tiene_municipalidad_propia"])

        # Distingue cero informado vs faltante ND.
        obs_por_cut = {o["cut"]: o for o in res["observaciones"]}
        self.assertEqual(obs_por_cut["01101"]["valor"], "223463")
        self.assertEqual(obs_por_cut["11102"]["valor"], "0")
        self.assertEqual(obs_por_cut["11102"]["estado"], "informado")
        self.assertIsNone(obs_por_cut["11303"]["valor"])
        self.assertEqual(obs_por_cut["11303"]["estado"], "faltante")

    def test_importar_346_comunas_formato_ancho_da_345_municipalidades(self) -> None:
        # Genera exactamente 346 CUTs válidos incluyendo 12201 (Cabo de Hornos) y 12202 (Antártica).
        cuts: list[tuple[str, str]] = [
            ("12201", "Cabo de Hornos"),
            ("12202", "Antártica"),
        ]
        for reg_num in range(1, 17):
            for idx in range(1, 30):
                if len(cuts) >= 346:
                    break
                cut = f"{reg_num:02d}1{idx:02d}"
                if cut in {"12201", "12202"}:
                    continue
                cuts.append((cut, f"Comuna {cut}"))
        self.assertEqual(len(cuts), 346)

        lineas = ["cut;comuna;2023;2024"]
        for cut, nombre in cuts:
            lineas.append(f"{cut};{nombre};1000;1050")
        contenido = ("\n".join(lineas) + "\n").encode("cp1252")

        res = ine_poblacion.importar_poblacion_comunal_ine(contenido, "ine_346_comunas.csv")
        self.assertEqual(res["archivo"]["formato_detectado"], "ancho")
        self.assertEqual(res["cobertura"]["comunas_importadas"], 346)
        self.assertTrue(res["cobertura"]["cobertura_completa_346"])
        self.assertEqual(res["cobertura"]["comunas_faltantes_vs_346"], 0)
        self.assertEqual(res["cobertura"]["municipalidades_representadas"], 345)
        self.assertEqual(res["cobertura"]["observaciones_disponibles"], 346 * 2)

    def test_importar_comunal_rechaza_pib_duplicados_negativos_y_region_inconsistente(self) -> None:
        csv_pib = b"cut,comuna,anio,poblacion,pib_comunal\n11101,Coyhaique,2024,60000,100\n"
        with self.assertRaises(ine_poblacion.InePoblacionError) as ctx:
            ine_poblacion.importar_poblacion_comunal_ine(csv_pib, "invalido_pib.csv")
        self.assertIn("346 comunas", str(ctx.exception))

        csv_dup = (
            b"cut,comuna,anio,poblacion\n"
            b"11101,Coyhaique,2024,60000\n"
            b"11101,Coyhaique,2024,61000\n"
        )
        with self.assertRaises(ine_poblacion.InePoblacionError):
            ine_poblacion.importar_poblacion_comunal_ine(csv_dup, "dup.csv")

        csv_neg = b"cut,comuna,anio,poblacion\n11101,Coyhaique,2024,-5\n"
        with self.assertRaises(ine_poblacion.InePoblacionError):
            ine_poblacion.importar_poblacion_comunal_ine(csv_neg, "neg.csv")

        csv_reg_mal = b"cut,comuna,region,anio,poblacion\n11101,Coyhaique,13,2024,60000\n"
        with self.assertRaises(ine_poblacion.InePoblacionError):
            ine_poblacion.importar_poblacion_comunal_ine(csv_reg_mal, "reg_mal.csv")


if __name__ == "__main__":
    unittest.main()
