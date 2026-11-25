"""Pruebas unitarias sin red para el extractor sectorial regional (``bde_sectorial.py``)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from hashlib import sha256
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pipelines.economia import bde_api, bde_sectorial


# Esquema de códigos fiel al catálogo real del BCCh, incluyendo sufijos .21.Z en Tarapacá ("01"),
# asimetría nominal/real en Administración Pública de Tarapacá (12.21.Z vs 12.Z.Z),
# variante "Servicios de vivienda" en real y la errata real de Los Ríos ("14") en COM nominal.
_SEGMENTOS_ESTANDAR: dict[str, tuple[str, str, str]] = {
    "agropecuario_silvicola": ("01", "Z", "Z"),
    "pesca": ("02", "04", "Z"),
    "mineria": ("03", "Z", "Z"),
    "industria_manufacturera": ("04", "Z", "Z"),
    "electricidad_gas_agua": ("05", "Z", "Z"),
    "construccion": ("06", "Z", "Z"),
    "comercio": ("COM", "Z", "Z"),
    "restaurantes_y_hoteles": ("RH", "Z", "Z"),
    "transportes_y_comunicaciones": ("08", "Z", "Z"),
    "servicios_financieros_y_empresariales": ("09", "21", "Z"),
    "propiedad_de_vivienda": ("10", "Z", "Z"),
    "servicios_personales": ("11", "Z", "Z"),
    "administracion_publica": ("12", "Z", "Z"),
}

_TARAPACA_SUFIJO_21 = {
    "agropecuario_silvicola",
    "mineria",
    "industria_manufacturera",
    "electricidad_gas_agua",
    "construccion",
    "comercio",
    "restaurantes_y_hoteles",
}


def _codigo_serie_mock(region: str, actividad_id: str, valoracion: str) -> str:
    marca = "R" if valoracion == "real" else "N"
    act, sub1, sub2 = _SEGMENTOS_ESTANDAR[actividad_id]
    if region == "01":
        if actividad_id in _TARAPACA_SUFIJO_21:
            sub1, sub2 = "21", "Z"
        elif actividad_id == "administracion_publica" and valoracion == "nominal":
            sub1, sub2 = "21", "Z"
    return f"F035.PIB.FLU.{marca}.CLP.2018.{act}.{sub1}.{sub2}.{region}.0.A"


def _titulo_serie_mock(region: str, actividad_id: str, nombre_act: str, valoracion: str) -> str:
    nombre_reg = bde_api.NOMBRES_TERRITORIOS[region]
    etiqueta_act = nombre_act
    if actividad_id == "propiedad_de_vivienda" and valoracion == "real":
        etiqueta_act = "Servicios de vivienda"
    if region == "14" and actividad_id == "comercio" and valoracion == "nominal":
        etiqueta_act = "Comercio, restaurantes y hotele"

    if valoracion == "real":
        return (
            f"PIB {etiqueta_act}, Región de {nombre_reg}, volumen a precios del año anterior "
            f"encadenado, referencia 2018 (miles de millones de pesos encadenados)"
        )
    return (
        f"PIB {etiqueta_act}, Región de {nombre_reg}, precios corrientes, base 2018 "
        f"(miles de millones de pesos)"
    )


def _construir_catalogo_416() -> dict:
    filas: list[dict] = [
        # También incluimos una serie total para confirmar que descubrir_series_sectoriales la excluye
        {
            "seriesId": "F035.PIB.FLU.N.CLP.2018.Z.Z.Z.11.0.A",
            "frequencyCode": "ANNUAL",
            "spanishTitle": "PIB regional Aysén, precios corrientes (miles de millones de pesos)",
            "firstObservation": "01-01-2013",
            "lastObservation": "01-01-2015",
            "updatedAt": "18-03-2026",
        }
    ]
    for region in bde_api.REGIONES:
        for act in bde_sectorial.ACTIVIDADES_CANONICAS:
            act_id = act["id"]
            nombre_act = act["nombre"]
            for valoracion in bde_api.VALORACIONES:
                filas.append({
                    "seriesId": _codigo_serie_mock(region, act_id, valoracion),
                    "frequencyCode": "ANNUAL",
                    "spanishTitle": _titulo_serie_mock(region, act_id, nombre_act, valoracion),
                    "englishTitle": f"GDP {act_id} (billions of pesos)",
                    "firstObservation": "01-01-2013",
                    "lastObservation": "01-01-2015",
                    "updatedAt": "20-03-2026" if region == "11" else "18-03-2026",
                })
    return {"Codigo": 0, "Descripcion": "Success", "SeriesInfos": filas}


def _construir_dataset_sintetico_exacto() -> tuple[bytes, dict[str, bytes]]:
    """Construye catálogo + 416 respuestas GetSeries con valores exactos verificables a mano.

    Diseño analítico para 2013 y 2014 (en miles de millones CLP -> *1000 = millones CLP):
    - Región "01" (Tarapacá): Minería = 50, las otras 12 actividades = 50/12? No, usemos enteros exactos!
      Usemos suma regional limpia = 100 (miles de millones -> 100.000 millones CLP) en 2013 y 2014:
      * Región "01" (Tarapacá): mineria = 50, agropecuario_silvicola = 10, pesca = 4, resto (10 acts) = 3.6 cada una -> suma = 100.
      * Región "11" (Aysén): administracion_publica = 40, pesca = 30, resto (11 acts) = 30/11? Mejor enteros exactos:
        administracion_publica = 30, pesca = 25, comercio = 12, servicios_personales = 9, construccion = 7,
        transportes_y_comunicaciones = 5, industria_manufacturera = 4, agropecuario_silvicola = 3,
        electricidad_gas_agua = 1, servicios_financieros_y_empresariales = 1, propiedad_de_vivienda = 1,
        mineria = 1, restaurantes_y_hoteles = 1 -> suma EXACTA = 100!
      * Otras 14 regiones: cada actividad = 10, excepto administracion_publica = 10 -> todas 10 (13 * 10 = 130).
        Mejor aún: todas las otras 14 regiones tienen cada una de las 13 actividades = 10 (suma = 130).
    - Real:
      * 2013: mismo valor numérico que nominal 2013.
      * 2014: para Tarapacá minería sube +10% (de 50 a 55); para Aysén pesca sube +20% (de 25 a 30);
        para las demás series sube +5%.
    """
    catalogo_dict = _construir_catalogo_416()
    catalogo_bytes = json.dumps(catalogo_dict, ensure_ascii=False).encode("utf-8")

    perfil_aysen_nom = {
        "administracion_publica": Decimal("30"),
        "pesca": Decimal("25"),
        "comercio": Decimal("12"),
        "servicios_personales": Decimal("9"),
        "construccion": Decimal("7"),
        "transportes_y_comunicaciones": Decimal("5"),
        "industria_manufacturera": Decimal("4"),
        "agropecuario_silvicola": Decimal("3"),
        "electricidad_gas_agua": Decimal("1"),
        "servicios_financieros_y_empresariales": Decimal("1"),
        "propiedad_de_vivienda": Decimal("1"),
        "mineria": Decimal("1"),
        "restaurantes_y_hoteles": Decimal("1"),
    }
    perfil_tarapaca_nom = {
        "mineria": Decimal("52"),
        "comercio": Decimal("10"),
        "construccion": Decimal("8"),
        "transportes_y_comunicaciones": Decimal("6"),
        "servicios_personales": Decimal("5"),
        "administracion_publica": Decimal("4"),
        "industria_manufacturera": Decimal("3"),
        "servicios_financieros_y_empresariales": Decimal("3"),
        "propiedad_de_vivienda": Decimal("3"),
        "pesca": Decimal("2"),
        "electricidad_gas_agua": Decimal("2"),
        "agropecuario_silvicola": Decimal("1"),
        "restaurantes_y_hoteles": Decimal("1"),
    }
    assert sum(perfil_aysen_nom.values()) == Decimal("100")
    assert sum(perfil_tarapaca_nom.values()) == Decimal("100")

    series_bytes: dict[str, bytes] = {}
    for region in bde_api.REGIONES:
        for act in bde_sectorial.ACTIVIDADES_CANONICAS:
            act_id = act["id"]
            if region == "11":
                base_2013 = perfil_aysen_nom[act_id]
            elif region == "01":
                base_2013 = perfil_tarapaca_nom[act_id]
            elif act_id == "pesca":
                # Menor peso nacional en pesca para que Aysén tenga sector_principal=admin_publica
                # pero sector_mas_especializado_lq=pesca.
                base_2013 = Decimal("2")
            else:
                base_2013 = Decimal("10")

            for valoracion in bde_api.VALORACIONES:
                codigo = _codigo_serie_mock(region, act_id, valoracion)
                titulo = _titulo_serie_mock(region, act_id, act["nombre"], valoracion)
                if valoracion == "nominal":
                    val_2013 = base_2013
                    val_2014 = base_2013
                else:
                    val_2013 = base_2013
                    if region == "01" and act_id == "mineria":
                        val_2014 = base_2013 * Decimal("1.1")  # +10% exacto
                    elif region == "11" and act_id == "pesca":
                        val_2014 = base_2013 * Decimal("1.2")  # +20% exacto
                    else:
                        val_2014 = base_2013 * Decimal("1.05")  # +5% exacto

                payload = {
                    "Codigo": 0,
                    "Descripcion": "Success",
                    "Series": {
                        "seriesId": codigo,
                        "descripEsp": titulo,
                        "Obs": [
                            {"indexDateString": "01-01-2013", "value": bde_api.formatear_decimal(val_2013), "statusCode": "OK"},
                            {"indexDateString": "01-01-2014", "value": bde_api.formatear_decimal(val_2014), "statusCode": "OK"},
                        ],
                    },
                }
                series_bytes[codigo] = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    return catalogo_bytes, series_bytes


class MapeoCanonicoSectorialTests(unittest.TestCase):
    def test_mapea_416_series_incluyendo_sufijos_21_tarapaca_y_variantes_oficiales(self):
        catalogo_dict = _construir_catalogo_416()
        catalogo = bde_api.parsear_catalogo_anual(catalogo_dict)
        mapa, ordenadas = bde_sectorial.mapear_series_sectoriales(catalogo)

        self.assertEqual(len(ordenadas), 416)
        self.assertEqual(len(mapa), 416)

        # Sufijos .21.Z en Tarapacá preservados literalmente
        self.assertEqual(
            mapa[("01", "mineria", "nominal")].codigo,
            "F035.PIB.FLU.N.CLP.2018.03.21.Z.01.0.A",
        )
        self.assertEqual(
            mapa[("01", "mineria", "real")].codigo,
            "F035.PIB.FLU.R.CLP.2018.03.21.Z.01.0.A",
        )
        self.assertEqual(
            mapa[("01", "comercio", "nominal")].codigo,
            "F035.PIB.FLU.N.CLP.2018.COM.21.Z.01.0.A",
        )
        self.assertEqual(
            mapa[("01", "restaurantes_y_hoteles", "real")].codigo,
            "F035.PIB.FLU.R.CLP.2018.RH.21.Z.01.0.A",
        )
        # Asimetría real en Tarapacá: nominal 12.21.Z vs real 12.Z.Z
        self.assertEqual(
            mapa[("01", "administracion_publica", "nominal")].codigo,
            "F035.PIB.FLU.N.CLP.2018.12.21.Z.01.0.A",
        )
        self.assertEqual(
            mapa[("01", "administracion_publica", "real")].codigo,
            "F035.PIB.FLU.R.CLP.2018.12.Z.Z.01.0.A",
        )
        # Variante real "Servicios de vivienda" -> propiedad_de_vivienda
        self.assertEqual(
            mapa[("11", "propiedad_de_vivienda", "real")].codigo,
            "F035.PIB.FLU.R.CLP.2018.10.Z.Z.11.0.A",
        )
        # Errata verificada en Los Ríos COM nominal ("Comercio, restaurantes y hotele")
        self.assertEqual(
            mapa[("14", "comercio", "nominal")].codigo,
            "F035.PIB.FLU.N.CLP.2018.COM.Z.Z.14.0.A",
        )
        self.assertEqual(
            mapa[("14", "restaurantes_y_hoteles", "nominal")].codigo,
            "F035.PIB.FLU.N.CLP.2018.RH.Z.Z.14.0.A",
        )

    def test_falla_si_falta_una_serie_o_actividad_desconocida(self):
        catalogo_dict = _construir_catalogo_416()
        # Quitar 1 serie sectorial
        catalogo_dict["SeriesInfos"] = [
            f for f in catalogo_dict["SeriesInfos"]
            if f["seriesId"] != "F035.PIB.FLU.N.CLP.2018.12.21.Z.01.0.A"
        ]
        catalogo = bde_api.parsear_catalogo_anual(catalogo_dict)
        with self.assertRaisesRegex(bde_api.BdeApiError, "faltan 1 de las 416"):
            bde_sectorial.mapear_series_sectoriales(catalogo)


class CalculoIndicadoresSectorialesTests(unittest.TestCase):
    def test_calcula_exactamente_participaciones_lq_hhi_diversificacion_krugman_y_crecimiento(self):
        catalogo_bytes, series_bytes = _construir_dataset_sintetico_exacto()
        lote = bde_sectorial.normalizar_sectorial_16_regiones(
            catalogo_bytes,
            series_bytes,
            extraido_en="2026-11-25T02:00:00+00:00",
            desde=date(2013, 1, 1),
            hasta=date(2014, 12, 31),
        )

        # Publicación y trazabilidad
        pub = lote["publicacion"]
        self.assertEqual(pub["estado"], "aprobada")
        self.assertEqual(pub["fuente"], "BCCh-BDE")
        self.assertEqual(pub["series_totales"], 416)
        self.assertEqual(pub["anios"], [2013, 2014])
        self.assertEqual(len(lote["actividades_canonicas"]), 13)
        self.assertEqual(lote["fuente_trazabilidad"]["series_verificadas"], 416)
        self.assertEqual(
            lote["fuente_trazabilidad"]["catalogo_anual_sha256"],
            sha256(catalogo_bytes).hexdigest(),
        )
        self.assertEqual(lote["fuente_trazabilidad"]["actualizado_en"], "2026-03-20")

        # Total regionalizado 2014:
        # 14 regiones * (12*10 + 2) + Tarapacá 100 + Aysén 100 = 14*122 + 200 = 1908 miles de millones = 1.908.000 millones CLP
        anio_2014 = lote["por_anio"]["2014"]
        tot_reg = anio_2014["total_regionalizado_actividades_nominal"]
        self.assertEqual(tot_reg["total_millones"], "1908000")
        self.assertIn("extrarregionales", tot_reg["nota"].lower())

        # Pesca nacional regionalizada = 14*2 + 2 (Tarapacá) + 25 (Aysén) = 55 -> 55.000 millones CLP
        self.assertEqual(tot_reg["por_actividad"]["pesca"], "55000")
        # Minería nacional regionalizada = 14*10 + 52 (Tarapacá) + 1 (Aysén) = 193 -> 193.000 millones CLP
        self.assertEqual(tot_reg["por_actividad"]["mineria"], "193000")

        # Verificar Aysén ("11") en 2014:
        aysen_14 = anio_2014["regiones"]["11"]
        self.assertEqual(aysen_14["total_vab_nominal_millones"], "100000")

        # HHI exacto de Aysén:
        # participaciones = [30, 25, 12, 9, 7, 5, 4, 3, 1, 1, 1, 1, 1]
        # sum(p^2) = 900+625+144+81+49+25+16+9+1+1+1+1+1 = 1854
        self.assertEqual(Decimal(aysen_14["hhi"]), Decimal("1854"))
        # Diversificación = 1 - 1854/10000 = 0.8146 exacto
        self.assertEqual(Decimal(aysen_14["diversificacion"]), Decimal("0.8146"))

        # Verificar suma de participaciones nominales = 100%
        acts_aysen = {a["actividad_id"]: a for a in aysen_14["actividades"]}
        suma_part = sum(Decimal(a["participacion_nominal_pct"]) for a in aysen_14["actividades"])
        self.assertEqual(suma_part, Decimal("100"))
        self.assertEqual(Decimal(acts_aysen["pesca"]["participacion_nominal_pct"]), Decimal("25"))

        # LQ exacto de Pesca en Aysén:
        # (25000 / 100000) / (55000 / 1908000) = (25 * 1908) / (100 * 55) = 8.672727...
        esperado_lq_pesca = (Decimal("25000") * Decimal("1908000")) / (Decimal("100000") * Decimal("55000"))
        self.assertEqual(
            Decimal(acts_aysen["pesca"]["lq_especializacion"]).quantize(Decimal("0.00000001")),
            esperado_lq_pesca.quantize(Decimal("0.00000001")),
        )
        self.assertEqual(aysen_14["sector_principal"]["actividad_id"], "administracion_publica")
        self.assertEqual(aysen_14["sector_mas_especializado_lq"]["actividad_id"], "pesca")

        # Verificar Krugman exacto de Aysén = 0.5 * sum(|s_ir - s_in|)
        tot_nac_dec = Decimal("1908000")
        tot_ay_dec = Decimal("100000")
        esperado_krugman = Decimal("0.5") * sum(
            abs(
                Decimal(acts_aysen[act["id"]]["nominal_millones"]) / tot_ay_dec
                - Decimal(tot_reg["por_actividad"][act["id"]]) / tot_nac_dec
            )
            for act in bde_sectorial.ACTIVIDADES_CANONICAS
        )
        self.assertEqual(
            Decimal(aysen_14["indice_krugman"]).quantize(Decimal("0.00000001")),
            esperado_krugman.quantize(Decimal("0.00000001")),
        )
        self.assertGreaterEqual(Decimal(aysen_14["indice_krugman"]), Decimal("0"))
        self.assertLessEqual(Decimal(aysen_14["indice_krugman"]), Decimal("1"))

        # Crecimiento real: NULO en 2013 para TODAS las regiones y actividades
        anio_2013 = lote["por_anio"]["2013"]
        for region in bde_api.REGIONES:
            for act in anio_2013["regiones"][region]["actividades"]:
                self.assertIsNone(act["crecimiento_real_pct"])

        # Crecimiento real en 2014: Aysén Pesca = +20%, Tarapacá Minería = +10%, resto = +5%
        self.assertEqual(Decimal(acts_aysen["pesca"]["crecimiento_real_pct"]), Decimal("20"))
        self.assertEqual(Decimal(acts_aysen["administracion_publica"]["crecimiento_real_pct"]), Decimal("5"))
        acts_tarapaca = {a["actividad_id"]: a for a in anio_2014["regiones"]["01"]["actividades"]}
        self.assertEqual(Decimal(acts_tarapaca["mineria"]["crecimiento_real_pct"]), Decimal("10"))
        self.assertEqual(acts_tarapaca["mineria"]["serie_bde_nominal"], "F035.PIB.FLU.N.CLP.2018.03.21.Z.01.0.A")

        # Rankings: Tarapacá tiene HHI mayor que Aysén (52^2 = 2704 > 1854) y ambas > regiones uniformes (10000/13 ~ 769.23)
        ranking_hhi = anio_2014["ranking_hhi"]
        self.assertEqual(len(ranking_hhi), 16)
        self.assertEqual(ranking_hhi[0]["territorio"], "01")
        self.assertEqual(ranking_hhi[0]["posicion"], 1)
        self.assertEqual(ranking_hhi[1]["territorio"], "11")
        self.assertEqual(ranking_hhi[1]["posicion"], 2)
        # Las 14 regiones uniformes empatan en posición 3
        self.assertEqual({r["posicion"] for r in ranking_hhi[2:]}, {3})

        ranking_krugman = anio_2014["ranking_krugman"]
        self.assertEqual(len(ranking_krugman), 16)
        # En Krugman (divergencia respecto a la estructura nacional), Aysén supera a Tarapacá
        # por la combinación de alta especialización en pesca y administración pública.
        self.assertEqual(ranking_krugman[0]["territorio"], "11")
        self.assertEqual(ranking_krugman[0]["posicion"], 1)
        self.assertEqual(ranking_krugman[1]["territorio"], "01")
        self.assertEqual(ranking_krugman[1]["posicion"], 2)
        self.assertEqual({r["posicion"] for r in ranking_krugman[2:]}, {3})
        self.assertGreater(
            Decimal(ranking_krugman[0]["indice_krugman"]),
            Decimal(ranking_krugman[1]["indice_krugman"]),
        )

    def test_faltante_nd_no_imputa_cero_en_crecimiento_ni_indicadores(self):
        catalogo_bytes, series_bytes = _construir_dataset_sintetico_exacto()
        # Marcar Aysén Pesca real 2014 como ND
        cod_real = "F035.PIB.FLU.R.CLP.2018.02.04.Z.11.0.A"
        payload_real = json.loads(series_bytes[cod_real].decode("utf-8"))
        payload_real["Series"]["Obs"][1] = {"indexDateString": "01-01-2014", "value": None, "statusCode": "ND"}
        series_bytes[cod_real] = json.dumps(payload_real, ensure_ascii=False).encode("utf-8")

        lote = bde_sectorial.normalizar_sectorial_16_regiones(
            catalogo_bytes,
            series_bytes,
            extraido_en="2026-11-25T02:00:00+00:00",
            desde=date(2013, 1, 1),
            hasta=date(2014, 12, 31),
        )
        acts_aysen_14 = {
            a["actividad_id"]: a for a in lote["por_anio"]["2014"]["regiones"]["11"]["actividades"]
        }
        self.assertIsNone(acts_aysen_14["pesca"]["real_millones"])
        self.assertIsNone(acts_aysen_14["pesca"]["crecimiento_real_pct"])
        # Nominal sigue intacto y calculable
        self.assertEqual(acts_aysen_14["pesca"]["nominal_millones"], "25000")


class ReproducibilidadYSeguridadSectorialTests(unittest.TestCase):
    def test_extraccion_con_concurrencia_reproduccion_bit_a_bit_y_cero_fugas(self):
        catalogo_bytes, series_bytes = _construir_dataset_sintetico_exacto()
        catalogo_payload = json.loads(catalogo_bytes.decode("utf-8"))
        series_payloads = {k: json.loads(v.decode("utf-8")) for k, v in series_bytes.items()}

        secreto_token = "tok-sectorial-super-secreto-9876"
        llamadas: list[tuple[str, str]] = []

        def fake_descargar(cred, funcion, timeout=30, **params):
            self.assertEqual(timeout, 30)
            self.assertEqual(cred.parametros_consulta(), {"token": secreto_token})
            if funcion == "SearchSeries":
                llamadas.append((funcion, params["frequency"]))
                return catalogo_bytes, catalogo_payload
            codigo = params["timeseries"]
            llamadas.append((funcion, codigo))
            return series_bytes[codigo], series_payloads[codigo]

        with TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            env_file = raiz / ".env"
            env_file.write_text(f"BCCH_API_TOKEN={secreto_token}\n", encoding="utf-8")
            insumos_dir = raiz / "raw" / "bde-sectorial-test"
            salida_1 = raiz / "published" / "pib-sectorial-16-regiones.json"
            salida_2 = raiz / "published" / "reproducido.json"

            stdout_cap = io.StringIO()
            with patch.dict("os.environ", {}, clear=True), patch.object(
                bde_sectorial, "descargar", side_effect=fake_descargar
            ), patch("sys.stdout", stdout_cap):
                rc = bde_sectorial.main([
                    "--env", str(env_file),
                    "--desde", "2013",
                    "--hasta", "2014",
                    "--workers", "4",
                    "--insumos", str(insumos_dir),
                    "--salida", str(salida_1),
                ])

            self.assertEqual(rc, 0)
            self.assertEqual(len(llamadas), 417)  # 1 SearchSeries + 416 GetSeries
            self.assertTrue((insumos_dir / "catalogo-anual.json").is_file())
            self.assertTrue((insumos_dir / "manifiesto.json").is_file())
            self.assertEqual(len(list((insumos_dir / "series").glob("*.json"))), 416)
            self.assertTrue(salida_1.is_file())

            # Cero fugas de secretos en manifiesto, salida y stdout
            self.assertNotIn(secreto_token, (insumos_dir / "manifiesto.json").read_text(encoding="utf-8"))
            self.assertNotIn(secreto_token, salida_1.read_text(encoding="utf-8"))
            self.assertNotIn(secreto_token, stdout_cap.getvalue())

            # Reproducir bit-a-bit SIN red ni credenciales
            def prohibir_red(*args, **kwargs):
                raise AssertionError("No debe invocar red en --reproducir")

            stdout_rep = io.StringIO()
            with patch.dict("os.environ", {}, clear=True), patch.object(
                bde_sectorial, "descargar", side_effect=prohibir_red
            ), patch("sys.stdout", stdout_rep):
                rc_rep = bde_sectorial.main([
                    "--reproducir",
                    "--insumos", str(insumos_dir),
                    "--salida", str(salida_2),
                ])

            self.assertEqual(rc_rep, 0)
            bytes_1 = salida_1.read_bytes()
            bytes_2 = salida_2.read_bytes()
            self.assertEqual(bytes_1, bytes_2)
            self.assertEqual(sha256(bytes_1).hexdigest(), sha256(bytes_2).hexdigest())

            # Corromper 1 archivo raw -> falla verificación SHA-256
            archivo_tarapaca = insumos_dir / "series" / "F035.PIB.FLU.N.CLP.2018.03.21.Z.01.0.A.json"
            archivo_tarapaca.write_bytes(archivo_tarapaca.read_bytes() + b" ")
            with self.assertRaisesRegex(bde_api.BdeApiError, "SHA-256"):
                bde_sectorial.reproducir_sectorial_desde_raw(insumos_dir, raiz / "published" / "falla.json")

    def test_error_descarga_no_filtra_credenciales_y_bloquea_escritura_con_secreto(self):
        catalogo_bytes, _series_bytes = _construir_dataset_sintetico_exacto()
        catalogo_payload = json.loads(catalogo_bytes.decode("utf-8"))
        catalogo = bde_api.parsear_catalogo_anual(catalogo_payload)
        _mapa, ordenadas = bde_sectorial.mapear_series_sectoriales(catalogo)

        cred = bde_api.Credenciales(modo="user_pass", usuario="analista@test.cl", clave="ClaveSecreta#42")

        def falla_con_fuga(*args, **kwargs):
            raise bde_api.BdeApiError(
                "GetSeries: HTTP 500 user=analista@test.cl&pass=ClaveSecreta#42"
            )

        with patch.object(bde_sectorial, "descargar", side_effect=falla_con_fuga):
            with self.assertRaises(bde_api.BdeApiError) as caught:
                bde_sectorial.descargar_series_sectoriales(
                    cred,
                    ordenadas[:4],
                    date(2013, 1, 1),
                    date(2014, 12, 31),
                    max_workers=4,
                )
        mensaje = str(caught.exception)
        self.assertNotIn("analista@test.cl", mensaje)
        self.assertNotIn("ClaveSecreta#42", mensaje)

        with TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "salida.json"
            with self.assertRaisesRegex(bde_api.BdeApiError, "credencial"):
                bde_sectorial._escribir_salida_protegida(
                    ruta,
                    b'{"fuga": "ClaveSecreta#42"}',
                    cred,
                )
            self.assertFalse(ruta.exists())


if __name__ == "__main__":
    unittest.main()
