"""Pruebas unitarias exhaustivas sin red para los conectores DIPRES CKAN y SINIM."""

from __future__ import annotations

from decimal import Decimal
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit

_DIR_FISCAL = Path(__file__).resolve().parent
if str(_DIR_FISCAL) not in sys.path:
    sys.path.insert(0, str(_DIR_FISCAL))

import dipres_ckan  # noqa: E402
import sinim_importer  # noqa: E402


class TestClasificacionYParseoDipres(unittest.TestCase):
    def test_clasificar_subtitulos_exactos(self):
        for sub in ("21", "22", "23", "24", "25", "26", "Subtítulo 21", "22 - Bienes"):
            self.assertEqual(dipres_ckan.clasificar_subtitulo(sub), "gasto_corriente")

        for sub in ("29", "30", "31", "Subt. 31"):
            self.assertEqual(dipres_ckan.clasificar_subtitulo(sub), "inversion")

        self.assertEqual(dipres_ckan.clasificar_subtitulo("33"), "transferencias_capital")

        for sub in ("01", "05", "5", "09", "9", "13", "15"):
            self.assertEqual(
                dipres_ckan.clasificar_subtitulo(sub), "ingresos_financiamiento"
            )

        for sub in ("27", "28", "32", "34", "35", "", "TOTAL"):
            self.assertEqual(dipres_ckan.clasificar_subtitulo(sub), "otros_gastos")

    def test_parsear_monto_dipres_formatos_chilenos_y_vacios(self):
        self.assertEqual(dipres_ckan.parsear_monto_dipres("7.011.531"), Decimal("7011531"))
        self.assertEqual(dipres_ckan.parsear_monto_dipres("125.430"), Decimal("125430"))
        self.assertEqual(
            dipres_ckan.parsear_monto_dipres("7.011.531,25"), Decimal("7011531.25")
        )
        self.assertEqual(dipres_ckan.parsear_monto_dipres("123,45"), Decimal("123.45"))
        self.assertEqual(dipres_ckan.parsear_monto_dipres("123.45"), Decimal("123.45"))
        self.assertEqual(dipres_ckan.parsear_monto_dipres("0.500"), Decimal("0.500"))
        self.assertEqual(dipres_ckan.parsear_monto_dipres("-1.250"), Decimal("-1250"))
        self.assertEqual(dipres_ckan.parsear_monto_dipres("(2.500)"), Decimal("-2500"))
        self.assertEqual(dipres_ckan.parsear_monto_dipres("$ 1.000"), Decimal("1000"))
        self.assertEqual(dipres_ckan.parsear_monto_dipres(0), Decimal("0"))
        self.assertEqual(dipres_ckan.parsear_monto_dipres("0"), Decimal("0"))
        self.assertEqual(
            dipres_ckan.parsear_monto_dipres(Decimal("42.5")), Decimal("42.5")
        )

        for vacio in ("-", "--", "", "   ", None, "N/A", "S/I", True, False, float("nan")):
            self.assertIsNone(dipres_ckan.parsear_monto_dipres(vacio))


class TestAgregacionYFlujoDipresLive(unittest.TestCase):
    def test_agregacion_sin_mezclar_ingresos_y_ratio_ausente_con_motivo_brecha(self):
        # Escenario típico Gobierno Central: Partida 31 trae ingresos/traspasos sin subtítulos 29-31
        registros_p31 = [
            {
                "_id": 1,
                "Partida": "31",
                "Nombre Partida": "Financiamiento Gobiernos Regionales",
                "Capitulo": "01",
                "Nombre Capitulo": "Financiamiento Gobiernos Regionales",
                "Programa": "14",
                "Nombre Programa": "Gobierno Regional de Aysén",
                "Subtitulo": "05",
                "Nombre Subtitulo": "Transferencias Corrientes (Ingresos)",
                "Ejecucion a Diciembre": "9.000.000",
                "Presupuesto Vigente": "9.500.000",
            },
            {
                "_id": 2,
                "Partida": "31",
                "Nombre Partida": "Financiamiento Gobiernos Regionales",
                "Capitulo": "01",
                "Nombre Capitulo": "Financiamiento Gobiernos Regionales",
                "Programa": "14",
                "Nombre Programa": "Gobierno Regional de Aysén",
                "Subtitulo": "09",
                "Nombre Subtitulo": "Aporte Fiscal",
                "Ejecucion a Diciembre": "1.500.000",
                "Presupuesto Vigente": "1.500.000",
            },
            {
                "_id": 3,
                "Partida": "31",
                "Nombre Partida": "Financiamiento Gobiernos Regionales",
                "Capitulo": "01",
                "Nombre Capitulo": "Financiamiento Gobiernos Regionales",
                "Programa": "14",
                "Nombre Programa": "Gobierno Regional de Aysén",
                "Subtitulo": "33",
                "Nombre Subtitulo": "Transferencias de Capital",
                "Ejecucion a Diciembre": "40.000.000",
                "Presupuesto Vigente": "42.000.000",
            },
            # Otra región en Partida 31 debe ser ignorada
            {
                "_id": 4,
                "Partida": "31",
                "Nombre Partida": "Financiamiento Gobiernos Regionales",
                "Capitulo": "01",
                "Nombre Capitulo": "Financiamiento Gobiernos Regionales",
                "Programa": "15",
                "Nombre Programa": "Gobierno Regional de Magallanes",
                "Subtitulo": "33",
                "Nombre Subtitulo": "Transferencias de Capital",
                "Ejecucion a Diciembre": "99.999.999",
            },
        ]
        registros_p05 = [
            {
                "_id": 10,
                "Partida": "05",
                "Nombre Partida": "Ministerio del Interior",
                "Capitulo": "05",
                "Nombre Capitulo": "Servicio de Gobierno Interior",
                "Programa": "01",
                "Nombre Programa": "Delegación Presidencial Regional de Aysén",
                "Subtitulo": "21",
                "Nombre Subtitulo": "Gastos en Personal",
                "Ejecucion a Diciembre": "1.250.500",
                "Presupuesto Vigente": "1.300.000",
            },
            # Otra región en Partida 05 ignorada
            {
                "_id": 11,
                "Partida": "05",
                "Nombre Partida": "Ministerio del Interior",
                "Capitulo": "05",
                "Nombre Capitulo": "Servicio de Gobierno Interior",
                "Programa": "02",
                "Nombre Programa": "Delegación Presidencial Regional de Los Lagos",
                "Subtitulo": "21",
                "Ejecucion a Diciembre": "8.000.000",
            },
        ]
        registros_q_aysen = [
            # Duplicado por _id con registros_p31 (no debe duplicarse)
            dict(registros_p31[2]),
            {
                "_id": 20,
                "Partida": "16",
                "Nombre Partida": "Ministerio de Salud",
                "Capitulo": "36",
                "Nombre Capitulo": "Servicio de Salud Aysén",
                "Programa": "01",
                "Nombre Programa": "Servicio de Salud Aysén",
                "Subtitulo": "21",
                "Nombre Subtitulo": "Gastos en Personal",
                "Ejecucion a Diciembre": "70.000.000",
                "Presupuesto Vigente": "71.000.000",
            },
            {
                "_id": 21,
                "Partida": "16",
                "Nombre Partida": "Ministerio de Salud",
                "Capitulo": "36",
                "Nombre Capitulo": "Servicio de Salud Aysén",
                "Programa": "01",
                "Nombre Programa": "Servicio de Salud Aysén",
                "Subtitulo": "31",
                "Nombre Subtitulo": "Iniciativas de Inversión",
                "Ejecucion a Diciembre": "12.500.000",
                "Presupuesto Vigente": "15.000.000",
            },
            # Ingreso subtítulo 13 en servicio público: NUNCA sumar como gasto
            {
                "_id": 22,
                "Partida": "16",
                "Nombre Partida": "Ministerio de Salud",
                "Capitulo": "36",
                "Nombre Capitulo": "Servicio de Salud Aysén",
                "Programa": "01",
                "Nombre Programa": "Servicio de Salud Aysén",
                "Subtitulo": "13",
                "Nombre Subtitulo": "Transferencias para Gastos de Capital (Ingreso)",
                "Ejecucion a Diciembre": "5.000.000",
            },
            # Fila en USD debe excluirse para no mezclar monedas
            {
                "_id": 23,
                "Partida": "16",
                "Nombre Partida": "Ministerio de Salud",
                "Capitulo": "36",
                "Nombre Capitulo": "Servicio de Salud Aysén",
                "Programa": "01",
                "Nombre Programa": "Servicio de Salud Aysén",
                "Subtitulo": "22",
                "Moneda": "DOLARES",
                "Ejecucion a Diciembre": "500.000",
            },
        ]

        res = dipres_ckan.agregar_registros_aysen(
            registros_p31=registros_p31,
            registros_p05=registros_p05,
            registros_q_aysen=registros_q_aysen,
        )

        self.assertEqual(res["columna_ejecucion"], "Ejecucion a Diciembre")
        self.assertEqual(res["columna_vigente"], "Presupuesto Vigente")
        self.assertEqual(res["registros_no_clp_excluidos"], 1)

        gore = res["gore_aysen"]
        self.assertEqual(gore["ingresos_financiamiento_p31"], "10500")
        self.assertEqual(gore["transferencias_capital_sub_33"], "40000")
        self.assertEqual(gore["gasto_corriente_sub_21_26"], "0")
        self.assertEqual(gore["inversion_sub_29_31"], "0")
        self.assertEqual(gore["total_gasto_directo_millones"], "40000")
        self.assertIsNone(gore["ratio_corriente_sobre_inversion_pct"])
        self.assertIsNotNone(gore["motivo_brecha"])
        self.assertIn("Partida 31", gore["motivo_brecha"])

        servicios = res["servicios_publicos_aysen"]
        self.assertEqual(len(servicios), 2)
        salud = servicios[0]
        self.assertEqual(salud["nombre_capitulo"], "Servicio de Salud Aysén")
        self.assertEqual(salud["gasto_corriente_sub_21_26"], "70000")
        self.assertEqual(salud["inversion_sub_29_31"], "12500")
        # Ingreso subtítulo 13 (5000) NO está sumado en total_gasto_millones
        self.assertEqual(salud["total_gasto_millones"], "82500")
        self.assertEqual(salud["ingresos_financiamiento_excluidos"], "5000")

        totales = res["totales_gobierno_central_aysen"]
        # 70000 (Salud) + 1250.5 (DPR Aysén) = 71250.5
        self.assertEqual(totales["gasto_corriente_sub_21_26"], "71250.5")
        self.assertEqual(totales["inversion_sub_29_31"], "12500")
        self.assertEqual(totales["transferencias_capital_sub_33"], "40000")
        # Financiamiento P31 (10500) estrictamente separado del gasto directo
        self.assertEqual(totales["financiamiento_gore_p31"], "10500")
        self.assertEqual(totales["total_gasto_directo_millones"], "123750.5")

    def test_ratio_corriente_sobre_inversion_presente_cuando_ambos_positivos(self):
        registros_p31 = [
            {
                "_id": 101,
                "Partida": "31",
                "Nombre Capitulo": "Gobierno Regional Región de Aysén",
                "Programa": "01",
                "Nombre Programa": "Funcionamiento",
                "Subtitulo": "21",
                "Ejecucion a Diciembre": "3.000.000",
            },
            {
                "_id": 102,
                "Partida": "31",
                "Nombre Capitulo": "Gobierno Regional Región de Aysén",
                "Programa": "01",
                "Nombre Programa": "Funcionamiento",
                "Subtitulo": "22",
                "Ejecucion a Diciembre": "1.500.000",
            },
            {
                "_id": 103,
                "Partida": "31",
                "Nombre Capitulo": "Gobierno Regional Región de Aysén",
                "Programa": "02",
                "Nombre Programa": "Inversión Regional",
                "Subtitulo": "31",
                "Ejecucion a Diciembre": "9.000.000",
            },
        ]
        res = dipres_ckan.agregar_registros_aysen(registros_p31, [], [])
        gore = res["gore_aysen"]
        self.assertEqual(gore["gasto_corriente_sub_21_26"], "4500")
        self.assertEqual(gore["inversion_sub_29_31"], "9000")
        # 100 * 4500 / 9000 = 50%
        self.assertEqual(gore["ratio_corriente_sobre_inversion_pct"], "50")
        self.assertIsNone(gore["motivo_brecha"])

    def test_obtener_ejecucion_aysen_live_con_cache_y_presupuesto_abierto_sin_red(self):
        llamadas: list[str] = []

        def fake_http_get_json(url: str, timeout: int) -> dict:
            llamadas.append(url)
            parsed = urlsplit(url)
            qs = parse_qs(parsed.query)
            if parsed.path.endswith("/package_search"):
                q = qs.get("q", [""])[0]
                if "ley de presupuestos" in q:
                    return {
                        "success": True,
                        "result": {
                            "results": [
                                {
                                    "name": "ley-presupuestos-2025",
                                    "title": "Ley de Presupuestos Inicial y Vigente 2025",
                                    "metadata_modified": "2025-12-30T12:00:00Z",
                                    "resources": [
                                        {
                                            "id": "res-ley-csv",
                                            "name": "Ley Inicial y Vigente CSV",
                                            "format": "CSV",
                                            "datastore_active": False,
                                            "url": "https://datos.gob.cl/ley2025.csv",
                                        }
                                    ],
                                }
                            ]
                        },
                    }
                return {
                    "success": True,
                    "result": {
                        "results": [
                            {
                                "name": "ejecucion-presupuestaria-diciembre-2025",
                                "title": "Ejecución Presupuestaria a Diciembre de 2025 Gobierno Central Total",
                                "metadata_modified": "2026-02-15T18:30:00Z",
                                "resources": [
                                    {
                                        "id": "res-pdf",
                                        "name": "Informe PDF",
                                        "format": "PDF",
                                        "datastore_active": False,
                                    },
                                    {
                                        "id": "res-prog-2025",
                                        "name": "Ejecución Gobierno Central A nivel Programa",
                                        "format": "CSV",
                                        "datastore_active": True,
                                    },
                                ],
                            }
                        ]
                    },
                }

            if parsed.path.endswith("/datastore_search"):
                filtros_raw = qs.get("filters", [None])[0]
                q_text = qs.get("q", [None])[0]
                if filtros_raw:
                    filtros = json.loads(filtros_raw)
                    if filtros.get("Partida") == "31":
                        return {
                            "success": True,
                            "result": {
                                "total": 1,
                                "fields": [
                                    {"id": "Partida"},
                                    {"id": "Nombre Programa"},
                                    {"id": "Subtitulo"},
                                    {"id": "Ejecucion a Diciembre"},
                                ],
                                "records": [
                                    {
                                        "_id": 1,
                                        "Partida": "31",
                                        "Nombre Capitulo": "Financiamiento Gobiernos Regionales",
                                        "Nombre Programa": "Gobierno Regional de Aysén",
                                        "Subtitulo": "24",
                                        "Ejecucion a Diciembre": "7.011.531",
                                    }
                                ],
                            },
                        }
                    if filtros.get("Partida") in ("05", "5"):
                        return {"success": True, "result": {"total": 0, "fields": [], "records": []}}
                if q_text == "AYSÉN":
                    return {
                        "success": True,
                        "result": {
                            "total": 1,
                            "fields": [
                                {"id": "Partida"},
                                {"id": "Nombre Capitulo"},
                                {"id": "Subtitulo"},
                                {"id": "Ejecucion a Diciembre"},
                            ],
                            "records": [
                                {
                                    "_id": 2,
                                    "Partida": "09",
                                    "Nombre Partida": "Ministerio de Educación",
                                    "Capitulo": "90",
                                    "Nombre Capitulo": "SLEP Aysén",
                                    "Programa": "01",
                                    "Nombre Programa": "SLEP Aysén",
                                    "Subtitulo": "21",
                                    "Ejecucion a Diciembre": "25.000.000",
                                }
                            ],
                        },
                    }
            raise AssertionError(f"URL inesperada en prueba: {url}")

        def fake_pa_error(timeout: int) -> dict:
            return {
                "url": f"{dipres_ckan.PRESUPUESTO_ABIERTO_BASE}/about-data",
                "disponible": False,
                "http_status": None,
                "nota": "Sin conexión en prueba controlada.",
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "dipres-aysen-2025.json"

            # 1) Primera llamada: en vivo (desde_cache=False)
            primero = dipres_ckan.obtener_ejecucion_aysen_live(
                anio=2025,
                refresh=False,
                cache_path=cache_file,
                http_get_json=fake_http_get_json,
                check_presupuesto_abierto=fake_pa_error,
            )
            self.assertTrue(cache_file.exists())
            self.assertFalse(primero["fuente_trazabilidad"]["desde_cache"])
            self.assertEqual(primero["fuente_trazabilidad"]["resource_id"], "res-prog-2025")
            self.assertEqual(primero["fuente_trazabilidad"]["unidad_origen"], "miles CLP")
            self.assertEqual(primero["gore_aysen"]["gasto_corriente_sub_21_26"], "7011.531")
            self.assertEqual(primero["servicios_publicos_aysen"][0]["nombre_capitulo"], "SLEP Aysén")
            self.assertEqual(primero["servicios_publicos_aysen"][0]["total_gasto_millones"], "25000")
            self.assertTrue(primero["ley_presupuestos"]["encontrado"])
            self.assertTrue(primero["ley_presupuestos"]["tiene_csv_disponible"])
            self.assertFalse(primero["ley_presupuestos"]["tiene_datastore_active"])
            self.assertFalse(primero["presupuesto_abierto"]["disponible"])
            llamadas_iniciales = len(llamadas)
            self.assertGreaterEqual(llamadas_iniciales, 4)

            # 2) Segunda llamada sin refresh: debe leer desde caché sin llamadas HTTP nuevas
            segundo = dipres_ckan.obtener_ejecucion_aysen_live(
                anio=2025,
                refresh=False,
                cache_path=cache_file,
                http_get_json=fake_http_get_json,
                check_presupuesto_abierto=fake_pa_error,
            )
            self.assertTrue(segundo["fuente_trazabilidad"]["desde_cache"])
            self.assertEqual(len(llamadas), llamadas_iniciales)

            # 3) Con refresh=True: consulta nuevamente en vivo
            tercero = dipres_ckan.obtener_ejecucion_aysen_live(
                anio=2025,
                refresh=True,
                cache_path=cache_file,
                http_get_json=fake_http_get_json,
                check_presupuesto_abierto=fake_pa_error,
            )
            self.assertFalse(tercero["fuente_trazabilidad"]["desde_cache"])
            self.assertGreater(len(llamadas), llamadas_iniciales)

            # 4) Caché vencido (> 12h): refresca automáticamente
            llamadas_antes_exp = len(llamadas)
            hace_13h = time.time() - (13 * 3600)
            os.utime(cache_file, (hace_13h, hace_13h))
            cuarto = dipres_ckan.obtener_ejecucion_aysen_live(
                anio=2025,
                refresh=False,
                cache_path=cache_file,
                http_get_json=fake_http_get_json,
                check_presupuesto_abierto=fake_pa_error,
            )
            self.assertFalse(cuarto["fuente_trazabilidad"]["desde_cache"])
            self.assertGreater(len(llamadas), llamadas_antes_exp)

    def test_fallback_anio_2026_sin_diciembre_y_columna_septiembre(self):
        def fake_http_2026(url: str, timeout: int) -> dict:
            parsed = urlsplit(url)
            qs = parse_qs(parsed.query)
            if parsed.path.endswith("/package_search"):
                q = qs.get("q", [""])[0]
                if "ley de presupuestos" in q:
                    return {"success": True, "result": {"results": []}}
                return {
                    "success": True,
                    "result": {
                        "results": [
                            {
                                "name": "ejecucion-septiembre-2026",
                                "title": "Ejecución Presupuestaria Septiembre 2026 Gobierno Central",
                                "metadata_modified": "2026-10-30T15:00:00Z",
                                "resources": [
                                    {
                                        "id": "res-cap-2026",
                                        "name": "Ejecución A nivel Capítulo",
                                        "format": "CSV",
                                        "datastore_active": True,
                                    }
                                ],
                            }
                        ]
                    },
                }
            if parsed.path.endswith("/datastore_search"):
                q_text = qs.get("q", [None])[0]
                if q_text == "AYSÉN":
                    return {
                        "success": True,
                        "result": {
                            "total": 1,
                            "fields": [
                                {"id": "Partida"},
                                {"id": "Nombre Capitulo"},
                                {"id": "Subtitulo"},
                                {"id": "Ejecución a Septiembre"},
                            ],
                            "records": [
                                {
                                    "_id": 99,
                                    "Partida": "16",
                                    "Capitulo": "36",
                                    "Nombre Capitulo": "Servicio de Salud Aysén",
                                    "Subtitulo": "21",
                                    "Ejecución a Septiembre": "48.000.000",
                                }
                            ],
                        },
                    }
                return {"success": True, "result": {"total": 0, "fields": [], "records": []}}
            raise AssertionError(url)

        with tempfile.TemporaryDirectory() as tmpdir:
            res = dipres_ckan.obtener_ejecucion_aysen_live(
                anio=2026,
                refresh=True,
                cache_path=Path(tmpdir) / "cache2026.json",
                http_get_json=fake_http_2026,
                check_presupuesto_abierto=lambda _t: {
                    "url": f"{dipres_ckan.PRESUPUESTO_ABIERTO_BASE}/about-data",
                    "disponible": True,
                    "http_status": 200,
                    "nota": "OK",
                },
            )
            self.assertEqual(res["fuente_trazabilidad"]["resource_id"], "res-cap-2026")
            self.assertEqual(
                res["fuente_trazabilidad"]["columna_ejecucion"], "Ejecución a Septiembre"
            )
            self.assertEqual(res["totales_gobierno_central_aysen"]["gasto_corriente_sub_21_26"], "48000")
            self.assertTrue(res["presupuesto_abierto"]["disponible"])

    def test_deteccion_mes_corte_12_8_9_y_advertencia_comparabilidad(self):
        self.assertEqual(
            dipres_ckan.detectar_mes_corte("Ejecucion a Diciembre", "Ejecución 2025"),
            12,
        )
        self.assertEqual(
            dipres_ckan.detectar_mes_corte("Ejecución a Agosto", "Ejecución 2026"),
            8,
        )
        self.assertEqual(
            dipres_ckan.detectar_mes_corte("Ejecución a Septiembre", "Ejecución 2026"),
            9,
        )
        # Fallback a package_title cuando columna_ejecucion no trae nombre de mes
        self.assertEqual(
            dipres_ckan.detectar_mes_corte(
                "Ejecución Acumulada",
                "Ejecución Presupuestaria a Agosto de 2026 Gobierno Central",
            ),
            8,
        )
        # Rango "Enero a Agosto" detecta el límite superior (8)
        self.assertEqual(
            dipres_ckan.detectar_mes_corte("Ejecución Enero a Agosto"),
            8,
        )
        self.assertIsNone(dipres_ckan.detectar_mes_corte("Ejecución Acumulada", "Sin mes"))

        def construir_fake_http(anio: int, titulo: str, nombre: str, col_ejec: str):
            def _fake(url: str, timeout: int) -> dict:
                parsed = urlsplit(url)
                qs = parse_qs(parsed.query)
                if parsed.path.endswith("/package_search"):
                    if "ley de presupuestos" in qs.get("q", [""])[0]:
                        return {"success": True, "result": {"results": []}}
                    return {
                        "success": True,
                        "result": {
                            "results": [
                                {
                                    "name": nombre,
                                    "title": titulo,
                                    "metadata_modified": f"{anio}-11-01T10:00:00Z",
                                    "resources": [
                                        {
                                            "id": f"res-{anio}",
                                            "name": "Ejecución A nivel Programa",
                                            "format": "CSV",
                                            "datastore_active": True,
                                        }
                                    ],
                                }
                            ]
                        },
                    }
                if parsed.path.endswith("/datastore_search"):
                    if qs.get("q", [None])[0] == "AYSÉN":
                        return {
                            "success": True,
                            "result": {
                                "total": 1,
                                "fields": [
                                    {"id": "Partida"},
                                    {"id": "Nombre Capitulo"},
                                    {"id": "Subtitulo"},
                                    {"id": col_ejec},
                                ],
                                "records": [
                                    {
                                        "_id": 1,
                                        "Partida": "16",
                                        "Capitulo": "36",
                                        "Nombre Capitulo": "Servicio de Salud Aysén",
                                        "Subtitulo": "21",
                                        col_ejec: "30.000.000",
                                    }
                                ],
                            },
                        }
                    return {"success": True, "result": {"total": 0, "fields": [], "records": []}}
                raise AssertionError(url)

            return _fake

        pa_ok = lambda _t: {  # noqa: E731
            "url": f"{dipres_ckan.PRESUPUESTO_ABIERTO_BASE}/about-data",
            "disponible": True,
            "http_status": 200,
            "nota": "OK",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # 1) Diciembre -> mes_corte=12, es_cierre_anual=True, sin advertencia
            res_dic = dipres_ckan.obtener_ejecucion_aysen_live(
                anio=2025,
                refresh=True,
                cache_path=Path(tmpdir) / "dic2025.json",
                http_get_json=construir_fake_http(
                    2025,
                    "Ejecución Presupuestaria a Diciembre de 2025 Gobierno Central Total",
                    "ejecucion-diciembre-2025",
                    "Ejecucion a Diciembre",
                ),
                check_presupuesto_abierto=pa_ok,
            )
            traza_dic = res_dic["fuente_trazabilidad"]
            self.assertEqual(traza_dic["mes_corte"], 12)
            self.assertTrue(traza_dic["es_cierre_anual"])
            self.assertIsNone(traza_dic["advertencia_comparabilidad_meses"])
            self.assertEqual(traza_dic["estado_actualizacion"], "actualizado_en_vivo")

            # 2) Agosto -> mes_corte=8, es_cierre_anual=False, advertencia explícita
            res_ago = dipres_ckan.obtener_ejecucion_aysen_live(
                anio=2026,
                refresh=True,
                cache_path=Path(tmpdir) / "ago2026.json",
                http_get_json=construir_fake_http(
                    2026,
                    "Ejecución Presupuestaria a Agosto de 2026 Gobierno Central",
                    "ejecucion-agosto-2026",
                    "Ejecución a Agosto",
                ),
                check_presupuesto_abierto=pa_ok,
            )
            traza_ago = res_ago["fuente_trazabilidad"]
            self.assertEqual(traza_ago["mes_corte"], 8)
            self.assertFalse(traza_ago["es_cierre_anual"])
            self.assertIsNotNone(traza_ago["advertencia_comparabilidad_meses"])
            self.assertIn("mes 8", traza_ago["advertencia_comparabilidad_meses"].lower())
            self.assertIn("12 meses", traza_ago["advertencia_comparabilidad_meses"].lower())
            self.assertIn("meses equivalentes", traza_ago["advertencia_comparabilidad_meses"].lower())

            # 3) Septiembre -> mes_corte=9, es_cierre_anual=False, advertencia explícita
            res_sep = dipres_ckan.obtener_ejecucion_aysen_live(
                anio=2026,
                refresh=True,
                cache_path=Path(tmpdir) / "sep2026.json",
                http_get_json=construir_fake_http(
                    2026,
                    "Ejecución Presupuestaria Septiembre 2026 Gobierno Central",
                    "ejecucion-septiembre-2026",
                    "Ejecución Acumulada",
                ),
                check_presupuesto_abierto=pa_ok,
            )
            traza_sep = res_sep["fuente_trazabilidad"]
            self.assertEqual(traza_sep["mes_corte"], 9)
            self.assertFalse(traza_sep["es_cierre_anual"])
            self.assertIsNotNone(traza_sep["advertencia_comparabilidad_meses"])
            self.assertIn("mes 9", traza_sep["advertencia_comparabilidad_meses"].lower())
            self.assertIn("meses equivalentes", traza_sep["advertencia_comparabilidad_meses"].lower())

    def test_respaldo_ultimo_corte_aprobado_cuando_falla_ckan(self):
        def fake_http_ok(url: str, timeout: int) -> dict:
            parsed = urlsplit(url)
            qs = parse_qs(parsed.query)
            if parsed.path.endswith("/package_search"):
                if "ley de presupuestos" in qs.get("q", [""])[0]:
                    return {"success": True, "result": {"results": []}}
                return {
                    "success": True,
                    "result": {
                        "results": [
                            {
                                "name": "ejecucion-agosto-2026",
                                "title": "Ejecución Presupuestaria a Agosto de 2026 Gobierno Central",
                                "metadata_modified": "2026-09-20T12:00:00Z",
                                "resources": [
                                    {
                                        "id": "res-ago-2026",
                                        "name": "Ejecución A nivel Programa",
                                        "format": "CSV",
                                        "datastore_active": True,
                                    }
                                ],
                            }
                        ]
                    },
                }
            if parsed.path.endswith("/datastore_search"):
                if qs.get("q", [None])[0] == "AYSÉN":
                    return {
                        "success": True,
                        "result": {
                            "total": 1,
                            "fields": [
                                {"id": "Partida"},
                                {"id": "Nombre Capitulo"},
                                {"id": "Subtitulo"},
                                {"id": "Ejecución a Agosto"},
                            ],
                            "records": [
                                {
                                    "_id": 50,
                                    "Partida": "16",
                                    "Capitulo": "36",
                                    "Nombre Capitulo": "Servicio de Salud Aysén",
                                    "Subtitulo": "21",
                                    "Ejecución a Agosto": "55.000.000",
                                }
                            ],
                        },
                    }
                return {"success": True, "result": {"total": 0, "fields": [], "records": []}}
            raise AssertionError(url)

        def fake_http_ckan_error(url: str, timeout: int) -> dict:
            raise dipres_ckan.DipresCkanError("HTTP 503 Servicio no disponible en datos.gob.cl")

        def fake_http_red_error(url: str, timeout: int) -> dict:
            raise URLError("Sin conectividad hacia datos.gob.cl")

        pa_ok = lambda _t: {  # noqa: E731
            "url": f"{dipres_ckan.PRESUPUESTO_ABIERTO_BASE}/about-data",
            "disponible": True,
            "http_status": 200,
            "nota": "OK",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "dipres-aysen-2026.json"

            # Sin caché previo, el error debe propagarse sin inventar datos
            with self.assertRaises(dipres_ckan.DipresCkanError):
                dipres_ckan.obtener_ejecucion_aysen_live(
                    anio=2026,
                    refresh=True,
                    cache_path=cache_file,
                    http_get_json=fake_http_ckan_error,
                    check_presupuesto_abierto=pa_ok,
                )
            self.assertFalse(cache_file.exists())

            # Sembrar corte aprobado válido en caché
            aprobado = dipres_ckan.obtener_ejecucion_aysen_live(
                anio=2026,
                refresh=True,
                cache_path=cache_file,
                http_get_json=fake_http_ok,
                check_presupuesto_abierto=pa_ok,
            )
            self.assertEqual(
                aprobado["totales_gobierno_central_aysen"]["gasto_corriente_sub_21_26"],
                "55000",
            )
            self.assertEqual(aprobado["fuente_trazabilidad"]["mes_corte"], 8)

            # 1) Al forzar refresh=True y fallar CKAN -> devuelve respaldo del último corte aprobado
            respaldo_refresh = dipres_ckan.obtener_ejecucion_aysen_live(
                anio=2026,
                refresh=True,
                cache_path=cache_file,
                http_get_json=fake_http_ckan_error,
                check_presupuesto_abierto=pa_ok,
            )
            traza_resp = respaldo_refresh["fuente_trazabilidad"]
            self.assertTrue(traza_resp["desde_cache"])
            self.assertEqual(
                traza_resp["estado_actualizacion"],
                "respaldo_ultimo_corte_aprobado",
            )
            self.assertIsNotNone(traza_resp["advertencia_actualizacion"])
            self.assertIn("503", traza_resp["advertencia_actualizacion"])
            self.assertEqual(traza_resp["mes_corte"], 8)
            self.assertFalse(traza_resp["es_cierre_anual"])
            self.assertIsNotNone(traza_resp["advertencia_comparabilidad_meses"])
            self.assertEqual(
                respaldo_refresh["totales_gobierno_central_aysen"]["gasto_corriente_sub_21_26"],
                "55000",
            )

            # 2) Con caché vencido (> 12h) y error de red (URLError) -> también devuelve último corte aprobado
            hace_20h = time.time() - (20 * 3600)
            os.utime(cache_file, (hace_20h, hace_20h))
            respaldo_red = dipres_ckan.obtener_ejecucion_aysen_live(
                anio=2026,
                refresh=False,
                cache_path=cache_file,
                http_get_json=fake_http_red_error,
                check_presupuesto_abierto=pa_ok,
            )
            self.assertTrue(respaldo_red["fuente_trazabilidad"]["desde_cache"])
            self.assertEqual(
                respaldo_red["fuente_trazabilidad"]["estado_actualizacion"],
                "respaldo_ultimo_corte_aprobado",
            )
            self.assertIn(
                "URLError",
                respaldo_red["fuente_trazabilidad"]["advertencia_actualizacion"],
            )
            self.assertEqual(
                respaldo_red["totales_gobierno_central_aysen"]["gasto_corriente_sub_21_26"],
                "55000",
            )


class TestSinimImporter(unittest.TestCase):
    def test_comunas_aysen_y_plantilla_sin_cifras_inventadas(self):
        self.assertEqual(len(sinim_importer.COMUNAS_AYSEN), 10)
        self.assertEqual(sinim_importer.COMUNAS_AYSEN["11101"], "Coyhaique")
        self.assertEqual(sinim_importer.COMUNAS_AYSEN["11302"], "O’Higgins")
        self.assertEqual(sinim_importer.COMUNAS_AYSEN["11402"], "Río Ibáñez")

        plantilla = sinim_importer.plantilla_sinim_csv()
        lineas = [ln for ln in plantilla.splitlines() if ln.strip()]
        self.assertEqual(len(lineas), 1)
        self.assertEqual(
            lineas[0],
            "cut,municipio,anio,unidad,etapa,ingresos_totales,gasto_total_devengado,"
            "gasto_corriente,gasto_inversion,fuente_archivo",
        )

    def test_importar_csv_coma_utf8_sig_y_comunas_faltantes(self):
        csv_texto = (
            "cut,municipio,anio,unidad,etapa,ingresos_totales,gasto_total_devengado,"
            "gasto_corriente,gasto_inversion,fuente_archivo\n"
            "11101,Coyhaique,2025,miles CLP,devengo,25.000.000,22.500.500,18.000.000,4.500.500,bep_2025.csv\n"
            "11201,Aysén,2025,M$,devengo,15.000.000,14.000.000,11.000.000,3.000.000,bep_2025.csv\n"
        )
        resultado = sinim_importer.importar_sinim_bytes(
            csv_texto.encode("utf-8-sig"), "bep_aysen_2025.csv"
        )
        self.assertTrue(resultado["valido"])
        self.assertEqual(resultado["errores"], [])
        resumen = resultado["resumen"]
        self.assertEqual(resumen["anio"], 2025)
        self.assertEqual(resumen["comunas_cargadas"], 2)
        self.assertEqual(resumen["comunas_esperadas"], 10)
        self.assertEqual(len(resumen["comunas_faltantes"]), 8)
        cuts_faltantes = {c["cut"] for c in resumen["comunas_faltantes"]}
        self.assertNotIn("11101", cuts_faltantes)
        self.assertNotIn("11201", cuts_faltantes)
        self.assertIn("11402", cuts_faltantes)
        self.assertEqual(resumen["total_ingresos_millones"], "40000")
        self.assertEqual(resumen["total_gasto_devengado_millones"], "36500.5")
        self.assertEqual(resumen["total_gasto_corriente_millones"], "29000")
        self.assertEqual(resumen["total_inversion_millones"], "7500.5")
        self.assertEqual(
            resultado["fuente_trazabilidad"]["institucion"],
            "SINIM · SUBDERE (importación oficial local)",
        )
        self.assertRegex(resultado["fuente_trazabilidad"]["sha256"], r"^[0-9a-f]{64}$")

    def test_importar_csv_punto_y_coma_iso8859_con_aliases_y_unidades(self):
        csv_texto = (
            "codigo_comuna;comuna;año;unidad;etapa;ingresos_municipales;gastos_totales\n"
            "11402;Río Ibáñez;2025;CLP;devengo;3.500.000.000;3.250.500.000\n"
            "11301;Cochrane;2025;millones CLP;devengo;4.100,25;3.900,50\n"
        )
        resultado = sinim_importer.importar_sinim_bytes(
            csv_texto.encode("iso-8859-1"), "export_sinim.csv"
        )
        self.assertTrue(resultado["valido"])
        resumen = resultado["resumen"]
        # 3500 + 4100.25 = 7600.25 millones CLP
        self.assertEqual(resumen["total_ingresos_millones"], "7600.25")
        # 3250.5 + 3900.5 = 7151 millones CLP
        self.assertEqual(resumen["total_gasto_devengado_millones"], "7151")
        # Sin columnas opcionales -> None
        self.assertIsNone(resumen["total_gasto_corriente_millones"])
        self.assertIsNone(resumen["total_inversion_millones"])
        self.assertEqual(resumen["comunas_cargadas"], 2)

    def test_importar_json_lista_y_envoltorio_registros_10_comunas(self):
        registros = [
            {
                "codigo": cut,
                "comuna": nombre,
                "ejercicio": 2025,
                "unidad": "miles CLP",
                "etapa": "devengo",
                "ingresos_totales": "1.000.000",
                "gasto_devengado": "900.000",
            }
            for cut, nombre in sinim_importer.COMUNAS_AYSEN.items()
        ]
        # Lista directa
        res_lista = sinim_importer.importar_sinim_bytes(
            json.dumps(registros).encode("utf-8"), "sinim_lista.json"
        )
        self.assertTrue(res_lista["valido"])
        self.assertEqual(res_lista["resumen"]["comunas_cargadas"], 10)
        self.assertEqual(res_lista["resumen"]["comunas_faltantes"], [])
        self.assertEqual(res_lista["resumen"]["total_ingresos_millones"], "10000")
        self.assertEqual(res_lista["resumen"]["total_gasto_devengado_millones"], "9000")

        # Objeto con {"registros": [...]}
        res_obj = sinim_importer.importar_sinim_bytes(
            json.dumps({"registros": registros}).encode("utf-8"), "sinim_obj.json"
        )
        self.assertTrue(res_obj["valido"])
        self.assertEqual(res_obj["resumen"]["comunas_cargadas"], 10)

    def test_rechaza_cut_fuera_de_region_11_duplicado_y_montos_invalidos(self):
        # CUT fuera de Región 11 (13101 Santiago)
        csv_fuera = (
            "cut,municipio,anio,unidad,etapa,ingresos_totales,gasto_total_devengado\n"
            "13101,Santiago,2025,miles CLP,devengo,100000,90000\n"
        )
        res_fuera = sinim_importer.importar_sinim_bytes(
            csv_fuera.encode("utf-8"), "fuera.csv"
        )
        self.assertFalse(res_fuera["valido"])
        self.assertIsNone(res_fuera["resumen"])
        self.assertEqual(res_fuera["comunas"], [])
        self.assertTrue(any("13101" in err for err in res_fuera["errores"]))

        # CUT duplicado para el mismo año
        csv_dup = (
            "cut,municipio,anio,unidad,etapa,ingresos_totales,gasto_total_devengado\n"
            "11101,Coyhaique,2025,miles CLP,devengo,100000,90000\n"
            "11101,Coyhaique,2025,miles CLP,devengo,120000,95000\n"
        )
        res_dup = sinim_importer.importar_sinim_bytes(csv_dup.encode("utf-8"), "dup.csv")
        self.assertFalse(res_dup["valido"])
        self.assertTrue(any("duplicado" in err.lower() for err in res_dup["errores"]))

        # Monto negativo y año fuera de rango y monto no numérico
        csv_invalido = (
            "cut,municipio,anio,unidad,etapa,ingresos_totales,gasto_total_devengado,gasto_corriente\n"
            "11101,Coyhaique,2010,miles CLP,devengo,-500,abc,100\n"
        )
        res_inv = sinim_importer.importar_sinim_bytes(
            csv_invalido.encode("utf-8"), "invalido.csv"
        )
        self.assertFalse(res_inv["valido"])
        self.assertGreaterEqual(len(res_inv["errores"]), 3)

        # Mezcla de etapas contables
        csv_etapas = (
            "cut,municipio,anio,unidad,etapa,ingresos_totales,gasto_total_devengado\n"
            "11101,Coyhaique,2025,miles CLP,inicial,100000,90000\n"
            "11201,Aysén,2025,miles CLP,devengo,100000,90000\n"
        )
        res_etapas = sinim_importer.importar_sinim_bytes(
            csv_etapas.encode("utf-8"), "etapas.csv"
        )
        self.assertFalse(res_etapas["valido"])
        self.assertTrue(any("etapas contables" in err.lower() for err in res_etapas["errores"]))

    def test_persistencia_guardar_y_cargar_sinim(self):
        csv_valido = (
            "cut,municipio,anio,unidad,etapa,ingresos_totales,gasto_total_devengado\n"
            "11101,Coyhaique,2025,miles CLP,devengo,20.000.000,19.500.000\n"
        )
        valido = sinim_importer.importar_sinim_bytes(
            csv_valido.encode("utf-8"), "coyhaique_2025.csv"
        )
        invalido = sinim_importer.importar_sinim_bytes(b"", "vacio.csv")

        with tempfile.TemporaryDirectory() as tmpdir:
            ruta = Path(tmpdir) / "sinim" / "sinim-aysen-2025.json"
            self.assertIsNone(sinim_importer.cargar_importacion_sinim(ruta))

            with self.assertRaises(ValueError):
                sinim_importer.guardar_importacion_sinim(invalido, ruta)
            self.assertFalse(ruta.exists())

            guardado = sinim_importer.guardar_importacion_sinim(valido, ruta)
            self.assertEqual(guardado, ruta)
            self.assertTrue(ruta.exists())

            cargado = sinim_importer.cargar_importacion_sinim(ruta)
            self.assertEqual(cargado, valido)


if __name__ == "__main__":
    unittest.main()
