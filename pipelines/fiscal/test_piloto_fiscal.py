"""Pruebas unitarias sin red para el Piloto Fiscal (SINIM oficial + DIPRES Piloto).

Cubre:
- Parseo HTML de fichas BEP SINIM (Municipalidad de Aysén 11201 y otras comunas),
  conversión M$ -> millones CLP con Decimal(34), % gasto corriente, frase radial,
  separación costo administrativo interno vs programas comunitarios, y
  presupuesto_inicial/vigente estrictamente en None.
- Archivado HTML + manifiesto.json SHA-256, reproducción sin red (--reproducir
  --insumos <dir>) y rechazo ante corrupción de SHA-256.
- obtener_presupuestos_piloto_live: Inicial/Vigente/Ejecutado, 4 entidades
  (Gobierno Central Nacional, GORE Aysén, Vialidad MOP 12-02, Servicios Aysén),
  filtro estricto de moneda PESOS vs DOLARES, Ley con datastore_active=False sin
  inventar cifras, comparación mismo mes año anterior (enero–agosto 2026 vs
  enero–agosto 2025), caché TTL y respaldo automático ante falla CKAN.
"""

from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit

_DIR_FISCAL = Path(__file__).resolve().parent
if str(_DIR_FISCAL) not in sys.path:
    sys.path.insert(0, str(_DIR_FISCAL))

import dipres_ckan  # noqa: E402
import sinim_ficha_live  # noqa: E402


def _html_ficha_aysen_11201() -> bytes:
    """Fixture HTML representativa de ficha SINIM para Municipalidad de Aysén (11201).

    Montos en miles CLP (M$):
    - Gasto total devengado: 13.991.900 M$ -> 13.991,9 millones CLP
    - Subt. 21 Personal: 6.500.000 M$ -> 6.500 millones CLP
      * Planta 215.21.01: 3.100.000 M$ -> 3.100 millones
      * Contrata 215.21.02: 1.900.000 M$ -> 1.900 millones
      * Honorarios 215.21.03: 600.000 M$ -> 600 millones
      * Programas comunitarios 215.21.04.004: 900.000 M$ -> 900 millones
      (Costo admin interno = 3.100 + 1.900 + 600 = 5.600 millones)
    - Subt. 22 Bienes y Servicios: 4.077.876 M$ -> 4.077,876 millones CLP
    - Gasto corriente observable = 10.577,876 millones CLP
    - % gasto corriente = 100 * 10577.876 / 13991.9 = 75.599997... -> 75.60% -> $75,6
    """
    html = """<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><title>Ficha Comunal SINIM - Aysén</title></head>
<body>
  <h1>Ficha Comunal: Municipalidad de Aysén (CUT 11201)</h1>
  <table>
    <thead>
      <tr><th colspan="2">Ingresos Municipales (M$) 2025 (Fuente BEP)</th></tr>
    </thead>
    <tbody>
      <tr><td>Ingresos Municipales (Ingreso Total Percibido)</td><td>15.240.500</td></tr>
      <tr><td>Ingresos por Fondo Común Municipal</td><td>9.450.000</td></tr>
      <tr><td>Ingresos Propios Permanentes (IPP)</td><td>4.120.300</td></tr>
      <tr><td>Participación del Fondo Común Municipal en el Ingreso Total</td><td>62,01%</td></tr>
    </tbody>
  </table>
  <table>
    <thead>
      <tr><th colspan="2">Gastos Municipales (M$) 2025 (Fuente BEP)</th></tr>
    </thead>
    <tbody>
      <tr><td>Gastos Municipales (Gastos Total Devengado)</td><td>13.991.900</td></tr>
      <tr><td>Gastos en Personal Municipal (Subtítulo 21)</td><td>6.500.000</td></tr>
      <tr><td>Personal de Planta (215.21.01)</td><td>3.100.000</td></tr>
      <tr><td>Personal a Contrata (215.21.02)</td><td>1.900.000</td></tr>
      <tr><td>Otras Remuneraciones / Honorarios (215.21.03)</td><td>600.000</td></tr>
      <tr><td>Prestación de Servicios en Programas Comunitarios (215.21.04.004)</td><td>900.000</td></tr>
      <tr><td>Gastos en Bienes y Servicios de Consumo (Subtítulo 22)</td><td>4.077.876</td></tr>
    </tbody>
  </table>
  <table>
    <thead>
      <tr><th colspan="2">Educación Municipal</th></tr>
    </thead>
    <tbody>
      <tr><td>Realizó Traspaso de la Educación Municipal al SLEP</td><td>Sí</td></tr>
    </tbody>
  </table>
</body>
</html>
"""
    return html.encode("utf-8")


def _html_ficha_coyhaique_11101() -> bytes:
    html = """<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><title>Ficha Comunal SINIM - Coyhaique</title></head>
<body>
  <table>
    <tr><th colspan="2">Ingresos Municipales (M$) 2025 (Fuente BEP)</th></tr>
    <tr><td>Ingresos Municipales (Ingreso Total Percibido)</td><td>28.000.000</td></tr>
    <tr><td>Ingresos por Fondo Común Municipal</td><td>14.000.000</td></tr>
    <tr><td>Ingresos Propios Permanentes (IPP)</td><td>11.200.000</td></tr>
    <tr><td>Participación del Fondo Común Municipal en el Ingreso Total</td><td>50,00%</td></tr>
    <tr><td>Gastos Municipales (Gastos Total Devengado)</td><td>25.000.000</td></tr>
    <tr><td>Gastos en Personal Municipal (Subtítulo 21)</td><td>10.000.000</td></tr>
    <tr><td>Personal de Planta (215.21.01)</td><td>5.000.000</td></tr>
    <tr><td>Personal a Contrata (215.21.02)</td><td>3.000.000</td></tr>
    <tr><td>Honorarios (215.21.03)</td><td>1.000.000</td></tr>
    <tr><td>Programas Comunitarios (215.21.04.004)</td><td>1.000.000</td></tr>
    <tr><td>Gastos en Bienes y Servicios de Consumo (Subtítulo 22)</td><td>7.500.000</td></tr>
    <tr><td>Realizó Traspaso de la Educación Municipal</td><td>Sí</td></tr>
  </table>
</body>
</html>
"""
    return html.encode("utf-8")


class TestSinimFichaLive(unittest.TestCase):
    def test_parsear_ficha_aysen_11201_exacto_y_frase_radial(self):
        ficha = sinim_ficha_live.parsear_ficha_sinim_html(
            _html_ficha_aysen_11201(),
            "11201",
            archivo_html="ficha-11201.html",
        )

        self.assertEqual(ficha["cut"], "11201")
        self.assertEqual(ficha["municipio"], "Aysén")
        self.assertTrue(ficha["es_piloto_destacado"])
        self.assertEqual(ficha["anio"], 2025)
        self.assertEqual(ficha["etapa_contable"], "devengo")

        # Nunca inventar inicial ni vigente en ficha BEP SINIM
        self.assertIsNone(ficha["presupuesto_inicial_millones"])
        self.assertIsNone(ficha["presupuesto_vigente_millones"])

        # Conversión exacta M$ -> millones CLP
        self.assertEqual(ficha["ingresos_percibidos_millones"], "15240.5")
        self.assertEqual(ficha["ingresos_fcm_millones"], "9450")
        self.assertEqual(ficha["ingresos_propios_permanentes_millones"], "4120.3")
        self.assertEqual(ficha["dependencia_fcm_pct"], "62.01")
        self.assertEqual(ficha["gasto_total_devengado_millones"], "13991.9")
        self.assertEqual(ficha["gasto_personal_sub21_millones"], "6500")
        self.assertEqual(ficha["personal_planta_millones"], "3100")
        self.assertEqual(ficha["personal_contrata_millones"], "1900")
        self.assertEqual(ficha["personal_honorarios_millones"], "600")
        self.assertEqual(ficha["personal_programas_comunitarios_millones"], "900")
        self.assertEqual(ficha["gasto_bienes_servicios_sub22_millones"], "4077.876")
        self.assertEqual(ficha["traspaso_educacion_slep"], "Sí")

        # Cálculos Decimal(34)
        self.assertEqual(ficha["gasto_corriente_observable_millones"], "10577.876")
        self.assertEqual(ficha["porcentaje_gasto_corriente_pct"], "75.6")
        self.assertEqual(ficha["otros_gastos_no_desglosados_millones"], "3414.024")
        self.assertEqual(
            Decimal(ficha["gasto_corriente_observable_millones"])
            + Decimal(ficha["otros_gastos_no_desglosados_millones"]),
            Decimal(ficha["gasto_total_devengado_millones"]),
        )

        # Costo admin interno separado de programas comunitarios (3100 + 1900 + 600 = 5600)
        self.assertEqual(ficha["costo_admin_interno_millones"], "5600")
        self.assertEqual(ficha["costo_admin_interno_pct"], "40.02")
        self.assertIn("215.21.04.004", ficha["nota_costo_administracion"])

        # Base de cálculo y frase radial exacta
        self.assertEqual(
            ficha["base_calculo_gasto_corriente"],
            sinim_ficha_live.BASE_CALCULO_GASTO_CORRIENTE,
        )
        self.assertEqual(
            ficha["frase_radial"],
            "De cada $100 ejecutados por la Municipalidad de Aysén en 2025, $75,6 "
            "correspondieron a gasto corriente observable en personal y bienes y servicios "
            "(base: $13.991,9 millones devengados según ficha BEP SINIM 2025).",
        )

    def test_sinim_gasto_total_cero_no_divide_por_cero(self):
        html_cero = """<html><body><table>
          <tr><th colspan="2">Ingresos Municipales (M$) 2025 (Fuente BEP)</th></tr>
          <tr><td>Gastos Municipales (Gastos Total Devengado)</td><td>0</td></tr>
          <tr><td>Gastos en Personal Municipal (Subtítulo 21)</td><td>0</td></tr>
          <tr><td>Gastos en Bienes y Servicios de Consumo (Subtítulo 22)</td><td>0</td></tr>
        </table></body></html>""".encode("utf-8")
        ficha = sinim_ficha_live.parsear_ficha_sinim_html(html_cero, "11201")
        self.assertEqual(ficha["gasto_total_devengado_millones"], "0")
        self.assertIsNone(ficha["porcentaje_gasto_corriente_pct"])
        self.assertIsNone(ficha["frase_radial"])

    def test_extraer_archivar_y_reproducir_sin_red_con_validacion_sha256(self):
        paginas = {
            sinim_ficha_live.URL_FICHA_PLANTILLA.format(cut="11201"): _html_ficha_aysen_11201(),
            sinim_ficha_live.URL_FICHA_PLANTILLA.format(cut="11101"): _html_ficha_coyhaique_11101(),
        }
        llamadas: list[str] = []

        def fake_get_bytes(url: str, timeout: int) -> tuple[bytes, int]:
            llamadas.append(url)
            return paginas[url], 200

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            raw_root = base / "raw"
            salida_vivo = base / "published" / "sinim-aysen-oficial.json"
            salida_repro = base / "published" / "sinim-reproducido.json"

            pub_vivo = sinim_ficha_live.extraer_fichas_sinim_live(
                comunas=["11201", "11101"],
                raw_root=raw_root,
                salida_path=salida_vivo,
                http_get_bytes=fake_get_bytes,
                timestamp="20261125T023000Z",
            )
            self.assertEqual(len(llamadas), 2)
            self.assertTrue(salida_vivo.exists())

            dir_insumos = Path(pub_vivo["fuente_trazabilidad"]["directorio_insumos"])
            self.assertEqual(dir_insumos.name, "sinim-fichas-20261125T023000Z")
            self.assertTrue((dir_insumos / "manifiesto.json").exists())
            self.assertTrue((dir_insumos / "ficha-11201.html").exists())
            self.assertTrue((dir_insumos / "ficha-11101.html").exists())

            # Resumen regional exacto (13991.9 + 25000 = 38991.9; 10577.876 + 17500 = 28077.876)
            self.assertEqual(pub_vivo["resumen"]["anio"], 2025)
            self.assertEqual(pub_vivo["resumen"]["comunas_procesadas"], 2)
            self.assertEqual(pub_vivo["resumen"]["total_gasto_devengado_millones"], "38991.9")
            self.assertEqual(
                pub_vivo["resumen"]["total_gasto_corriente_observable_millones"], "28077.876"
            )
            self.assertIsNone(pub_vivo["resumen"]["presupuesto_inicial_millones"])
            self.assertIsNone(pub_vivo["resumen"]["presupuesto_vigente_millones"])
            self.assertEqual(pub_vivo["piloto_aysen"]["cut"], "11201")

            # Reproducción vía CLI --reproducir --insumos sin tocar la red
            rc = sinim_ficha_live.main(
                [
                    "--reproducir",
                    "--insumos",
                    str(dir_insumos),
                    "--salida",
                    str(salida_repro),
                ]
            )
            self.assertEqual(rc, 0)
            pub_repro = json.loads(salida_repro.read_text(encoding="utf-8"))
            self.assertEqual(pub_repro["fuente_trazabilidad"]["modo"], "reproducido_sin_red")
            self.assertTrue(pub_repro["fuente_trazabilidad"]["integridad_sha256_verificada"])
            self.assertEqual(pub_repro["comunas"], pub_vivo["comunas"])
            self.assertEqual(pub_repro["resumen"], pub_vivo["resumen"])

            # Alterar un byte en el HTML archivado debe gatillar SinimIntegridadError
            ficha_corrupta = dir_insumos / "ficha-11201.html"
            ficha_corrupta.write_bytes(ficha_corrupta.read_bytes() + b" ")
            with self.assertRaises(sinim_ficha_live.SinimIntegridadError):
                sinim_ficha_live.reproducir_fichas_sinim(dir_insumos, escribir_salida=False)

    def test_tabla_cuatro_columnas_toma_comunal_y_nunca_nacional(self):
        html_real_4col = """<!doctype html><html><body>
        <h3>Gastos Municipales (M$) 2025 (Fuente BEP)</h3>
        <table class="tabla_datos">
          <tr><th>Descripción</th><th>Unidad Medida</th><th>Comunal</th><th>Nacional</th></tr>
          <tr><td>Gastos en Personal Municipal (Subtítulo 21)</td><td>M$</td><td>6.881.918</td><td>2.497.079.455</td></tr>
          <tr><td>Gastos en Bienes y Servicios de Consumo (Subtítulo 22)</td><td>M$</td><td>3.691.026</td><td>2.479.473.616</td></tr>
          <tr><td>Gastos Municipales (Gastos Total Devengado)</td><td>M$</td><td>13.991.886</td><td>9.090.501.730</td></tr>
          <tr><td>Gasto Personal Planta (cuenta presupuestaria 215.21.01)</td><td>M$</td><td>3.044.450</td><td>1.108.176.516</td></tr>
          <tr><td>Gasto Personal a Contrata (cuenta presupuestaria 215.21.02)</td><td>M$</td><td>1.269.147</td><td>576.133.012</td></tr>
          <tr><td>Gasto Personal a Honorarios (cuenta presupuestaria 215.21.03)</td><td>M$</td><td>665.800</td><td>178.935.016</td></tr>
          <tr><td>Gasto Personal por Prestaciones de Servicios en Programas Comunitarios (cuenta presupuestaria 215.21.04.004)</td><td>M$</td><td>1.815.588</td><td>601.679.597</td></tr>
        </table></body></html>""".encode("utf-8")
        reg = sinim_ficha_live.parsear_ficha_sinim_html(html_real_4col, "11201")
        self.assertEqual(reg["gasto_total_devengado_millones"], "13991.886")
        self.assertEqual(reg["gasto_personal_sub21_millones"], "6881.918")
        self.assertEqual(reg["gasto_bienes_servicios_sub22_millones"], "3691.026")
        self.assertEqual(reg["gasto_corriente_observable_millones"], "10572.944")
        self.assertEqual(reg["porcentaje_gasto_corriente_pct"], "75.56")
        self.assertEqual(reg["costo_admin_interno_millones"], "4979.397")
        self.assertEqual(reg["costo_admin_interno_pct"], "35.59")


class TestDipresPilotoPresupuestarioLive(unittest.TestCase):
    def _crear_mock_ckan_2025(self):
        """Mock CKAN sin red para 2025 (Ejecución dic + Ley Inicial/Vigente activa + USD)."""
        llamadas: list[str] = []

        def fake_http(url: str, timeout: int) -> dict:
            llamadas.append(url)
            parsed = urlsplit(url)
            qs = parse_qs(parsed.query)

            if parsed.path.endswith("/package_search"):
                q = qs.get("q", [""])[0].lower()
                if "ley de presupuestos" in q and "2025" in q:
                    return {
                        "success": True,
                        "result": {
                            "results": [
                                {
                                    "name": "ley-de-presupuestos-inicial-y-vigente-a-diciembre-de-2025-del-gobierno-central-total",
                                    "title": "Ley de Presupuestos Inicial y Vigente a Diciembre de 2025 del Gobierno Central - Total",
                                    "metadata_modified": "2026-01-20T12:00:00Z",
                                    "resources": [
                                        {
                                            "id": "res-ley-nac-2025",
                                            "name": "A nivel Nacional",
                                            "format": "CSV",
                                            "datastore_active": True,
                                        },
                                        {
                                            "id": "res-ley-prog-2025",
                                            "name": "A nivel Programa",
                                            "format": "CSV",
                                            "datastore_active": True,
                                        },
                                    ],
                                }
                            ]
                        },
                    }
                if "ejecucion presupuestaria" in q and "2025" in q:
                    return {
                        "success": True,
                        "result": {
                            "results": [
                                {
                                    "name": "ejecucion-presupuestaria-a-diciembre-de-2025-del-gobierno-central-total",
                                    "title": "Ejecución Presupuestaria a Diciembre de 2025 del Gobierno Central - Total",
                                    "metadata_modified": "2026-02-15T18:00:00Z",
                                    "resources": [
                                        {
                                            "id": "res-ejec-nac-2025",
                                            "name": "A nivel Nacional",
                                            "format": "CSV",
                                            "datastore_active": True,
                                        },
                                        {
                                            "id": "res-ejec-prog-2025",
                                            "name": "A nivel Programa",
                                            "format": "CSV",
                                            "datastore_active": True,
                                        },
                                    ],
                                }
                            ]
                        },
                    }
                return {"success": True, "result": {"results": []}}

            if parsed.path.endswith("/datastore_search"):
                rid = qs.get("resource_id", [""])[0]
                filtros_raw = qs.get("filters", ["{}"])[0]
                filtros = json.loads(filtros_raw)
                q_text = qs.get("q", [""])[0]

                # --- Ejecución 2025 A nivel Nacional ---
                if rid == "res-ejec-nac-2025":
                    return {
                        "success": True,
                        "result": {
                            "fields": [
                                {"id": "Moneda"},
                                {"id": "Subtitulo"},
                                {"id": "Ejecucion a Diciembre"},
                            ],
                            "total": 6,
                            "records": [
                                # Ingresos Subt. 01 -> nunca sumar al gasto
                                {
                                    "_id": 1,
                                    "Moneda": "PESOS",
                                    "Subtitulo": "01",
                                    "Ejecucion a Diciembre": "60.000.000.000",
                                },
                                # Personal Subt. 21: 20.000.000M
                                {
                                    "_id": 2,
                                    "Moneda": "PESOS",
                                    "Subtitulo": "21",
                                    "Ejecucion a Diciembre": "20.000.000.000",
                                },
                                # Bienes y servicios Subt. 22: 10.000.000M
                                {
                                    "_id": 3,
                                    "Moneda": "PESOS",
                                    "Subtitulo": "22",
                                    "Ejecucion a Diciembre": "10.000.000.000",
                                },
                                # Transferencias corrientes Subt. 24: 45.000.000M
                                {
                                    "_id": 4,
                                    "Moneda": "PESOS",
                                    "Subtitulo": "24",
                                    "Ejecucion a Diciembre": "45.000.000.000",
                                },
                                # Inversión física Subt. 31: 15.000.000M
                                {
                                    "_id": 5,
                                    "Moneda": "PESOS",
                                    "Subtitulo": "31",
                                    "Ejecucion a Diciembre": "15.000.000.000",
                                },
                                # Transferencias de capital Subt. 33: 10.000.000M
                                {
                                    "_id": 6,
                                    "Moneda": "PESOS",
                                    "Subtitulo": "33",
                                    "Ejecucion a Diciembre": "10.000.000.000",
                                },
                                # DOLARES -> DEBE EXCLUIRSE ESTRICTAMENTE
                                {
                                    "_id": 7,
                                    "Moneda": "DOLARES",
                                    "Subtitulo": "22",
                                    "Ejecucion a Diciembre": "999.999.999",
                                },
                            ],
                        },
                    }

                # --- Ley 2025 A nivel Nacional ---
                if rid == "res-ley-nac-2025":
                    return {
                        "success": True,
                        "result": {
                            "fields": [
                                {"id": "Moneda"},
                                {"id": "Subtitulo"},
                                {"id": "Monto Ley Inicial"},
                                {"id": "Monto Ley Vigente a Diciembre"},
                            ],
                            "total": 6,
                            "records": [
                                {
                                    "_id": 101,
                                    "Moneda": "PESOS",
                                    "Subtitulo": "21",
                                    "Monto Ley Inicial": "19.500.000.000",
                                    "Monto Ley Vigente a Diciembre": "20.500.000.000",
                                },
                                {
                                    "_id": 102,
                                    "Moneda": "PESOS",
                                    "Subtitulo": "22",
                                    "Monto Ley Inicial": "9.500.000.000",
                                    "Monto Ley Vigente a Diciembre": "10.500.000.000",
                                },
                                {
                                    "_id": 103,
                                    "Moneda": "PESOS",
                                    "Subtitulo": "24",
                                    "Monto Ley Inicial": "44.000.000.000",
                                    "Monto Ley Vigente a Diciembre": "46.000.000.000",
                                },
                                {
                                    "_id": 104,
                                    "Moneda": "PESOS",
                                    "Subtitulo": "31",
                                    "Monto Ley Inicial": "15.000.000.000",
                                    "Monto Ley Vigente a Diciembre": "16.000.000.000",
                                },
                                {
                                    "_id": 105,
                                    "Moneda": "PESOS",
                                    "Subtitulo": "33",
                                    "Monto Ley Inicial": "10.000.000.000",
                                    "Monto Ley Vigente a Diciembre": "11.000.000.000",
                                },
                                {
                                    "_id": 106,
                                    "Moneda": "DOLARES",
                                    "Subtitulo": "22",
                                    "Monto Ley Inicial": "888.888.888",
                                    "Monto Ley Vigente a Diciembre": "888.888.888",
                                },
                            ],
                        },
                    }

                # --- Ejecución 2025 A nivel Programa ---
                if rid == "res-ejec-prog-2025":
                    if filtros.get("Partida") == "31":
                        return {
                            "success": True,
                            "result": {
                                "total": 3,
                                "records": [
                                    {
                                        "_id": 201,
                                        "Partida": "31",
                                        "Capitulo": "01",
                                        "Programa": "14",
                                        "Nombre Programa": "GOBIERNO REGIONAL REGIÓN DE AYSÉN",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "09",
                                        "Ejecucion a Diciembre": "80.000.000",
                                    },
                                    {
                                        "_id": 202,
                                        "Partida": "31",
                                        "Capitulo": "01",
                                        "Programa": "14",
                                        "Nombre Programa": "GOBIERNO REGIONAL REGIÓN DE AYSÉN",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "24",
                                        "Ejecucion a Diciembre": "10.000.000",
                                    },
                                    {
                                        "_id": 203,
                                        "Partida": "31",
                                        "Capitulo": "01",
                                        "Programa": "14",
                                        "Nombre Programa": "GOBIERNO REGIONAL REGIÓN DE AYSÉN",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "33",
                                        "Ejecucion a Diciembre": "70.000.000",
                                    },
                                ],
                            },
                        }
                    if filtros.get("Partida") == "12":
                        return {
                            "success": True,
                            "result": {
                                "total": 3,
                                "records": [
                                    {
                                        "_id": 301,
                                        "Partida": "12",
                                        "Capitulo": "02",
                                        "Nombre Capitulo": "DIRECCIÓN GENERAL DE OBRAS PÚBLICAS",
                                        "Programa": "04",
                                        "Nombre Programa": "DIRECCIÓN DE VIALIDAD",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "21",
                                        "Ejecucion a Diciembre": "200.000.000",
                                    },
                                    {
                                        "_id": 302,
                                        "Partida": "12",
                                        "Capitulo": "02",
                                        "Nombre Capitulo": "DIRECCIÓN GENERAL DE OBRAS PÚBLICAS",
                                        "Programa": "04",
                                        "Nombre Programa": "DIRECCIÓN DE VIALIDAD",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "31",
                                        "Ejecucion a Diciembre": "1.800.000.000",
                                    },
                                    # Otro programa DGOP (Obras Portuarias) no debe mezclarse con Vialidad
                                    {
                                        "_id": 303,
                                        "Partida": "12",
                                        "Capitulo": "02",
                                        "Nombre Capitulo": "DIRECCIÓN GENERAL DE OBRAS PÚBLICAS",
                                        "Programa": "06",
                                        "Nombre Programa": "DIRECCIÓN DE OBRAS PORTUARIAS",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "31",
                                        "Ejecucion a Diciembre": "500.000.000",
                                    },
                                ],
                            },
                        }
                    if filtros.get("Partida") == "05":
                        return {
                            "success": True,
                            "result": {
                                "total": 1,
                                "records": [
                                    {
                                        "_id": 401,
                                        "Partida": "05",
                                        "Capitulo": "05",
                                        "Nombre Programa": "Delegación Presidencial Regional de Aysén",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "21",
                                        "Ejecucion a Diciembre": "2.000.000",
                                    }
                                ],
                            },
                        }
                    if q_text:
                        return {
                            "success": True,
                            "result": {
                                "total": 2,
                                "records": [
                                    {
                                        "_id": 501,
                                        "Partida": "16",
                                        "Capitulo": "36",
                                        "Nombre Capitulo": "Servicio de Salud Aysén",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "21",
                                        "Ejecucion a Diciembre": "80.000.000",
                                    },
                                    {
                                        "_id": 502,
                                        "Partida": "16",
                                        "Capitulo": "36",
                                        "Nombre Capitulo": "Servicio de Salud Aysén",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "31",
                                        "Ejecucion a Diciembre": "18.000.000",
                                    },
                                ],
                            },
                        }

                # --- Ley 2025 A nivel Programa ---
                if rid == "res-ley-prog-2025":
                    if filtros.get("Partida") == "31":
                        return {
                            "success": True,
                            "result": {
                                "total": 2,
                                "records": [
                                    {
                                        "_id": 601,
                                        "Partida": "31",
                                        "Capitulo": "01",
                                        "Programa": "14",
                                        "Nombre Programa": "GOBIERNO REGIONAL REGIÓN DE AYSÉN",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "24",
                                        "Monto Ley Inicial": "10.000.000",
                                        "Monto Ley Vigente a Diciembre": "10.500.000",
                                    },
                                    {
                                        "_id": 602,
                                        "Partida": "31",
                                        "Capitulo": "01",
                                        "Programa": "14",
                                        "Nombre Programa": "GOBIERNO REGIONAL REGIÓN DE AYSÉN",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "33",
                                        "Monto Ley Inicial": "72.000.000",
                                        "Monto Ley Vigente a Diciembre": "75.000.000",
                                    },
                                ],
                            },
                        }
                    if filtros.get("Partida") == "12":
                        return {
                            "success": True,
                            "result": {
                                "total": 2,
                                "records": [
                                    {
                                        "_id": 701,
                                        "Partida": "12",
                                        "Capitulo": "02",
                                        "Programa": "04",
                                        "Nombre Programa": "DIRECCIÓN DE VIALIDAD",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "21",
                                        "Monto Ley Inicial": "210.000.000",
                                        "Monto Ley Vigente a Diciembre": "215.000.000",
                                    },
                                    {
                                        "_id": 702,
                                        "Partida": "12",
                                        "Capitulo": "02",
                                        "Programa": "04",
                                        "Nombre Programa": "DIRECCIÓN DE VIALIDAD",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "31",
                                        "Monto Ley Inicial": "1.900.000.000",
                                        "Monto Ley Vigente a Diciembre": "2.000.000.000",
                                    },
                                ],
                            },
                        }
                    return {"success": True, "result": {"total": 0, "records": []}}

                return {"success": True, "result": {"total": 0, "records": []}}

            raise AssertionError(f"URL inesperada en mock: {url}")

        return fake_http, llamadas

    def test_piloto_2025_inicial_vigente_ejecutado_filtro_moneda_y_4_entidades(self):
        fake_http, llamadas = self._crear_mock_ckan_2025()

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "dipres-piloto-2025.json"
            res = dipres_ckan.obtener_presupuestos_piloto_live(
                anio=2025,
                refresh=True,
                cache_path=cache_file,
                http_get_json=fake_http,
            )

            self.assertEqual(res["anio"], 2025)
            self.assertEqual(res["mes_corte"], 12)
            self.assertTrue(res["es_cierre_anual"])
            self.assertIsNone(res["comparacion_interanual"])
            self.assertTrue(res["ley_presupuestos"]["tiene_datastore_active"])

            # 1. Gobierno Central Nacional (solo PESOS, excluye DOLARES e ingresos Subt. 01)
            nac = res["entidades"]["gobierno_central_nacional"]
            self.assertEqual(nac["territorio_etiqueta"], "Chile (Nivel Nacional)")
            self.assertEqual(nac["inicial_millones"], "98000000")
            self.assertEqual(nac["vigente_millones"], "104000000")
            self.assertEqual(nac["ejecutado_millones"], "100000000")
            self.assertEqual(nac["gasto_corriente_millones"], "75000000")
            self.assertEqual(nac["gasto_corriente_pct"], "75")
            self.assertEqual(nac["inversion_y_capital_millones"], "25000000")
            self.assertEqual(nac["inversion_y_capital_pct"], "25")
            self.assertEqual(nac["ingresos_financiamiento_excluidos_millones"], "60000000")
            self.assertEqual(nac["registros_no_clp_excluidos"], 2)  # 1 en ejecución + 1 en ley
            self.assertEqual(nac["costo_administrar"]["disponible"], True)
            # Subt. 21 (20M) + Subt. 22 (10M) = 30M sobre 100M = 30%
            self.assertEqual(nac["costo_administrar"]["monto_millones"], "30000000")
            self.assertEqual(nac["costo_administrar"]["porcentaje"], "30")
            self.assertIn("De cada $100 ejecutados", nac["frase_radial"])
            self.assertIn("$75,0", nac["frase_radial"])
            self.assertEqual(
                nac["url_respaldo"],
                "https://datos.gob.cl/dataset/ejecucion-presupuestaria-a-diciembre-de-2025-del-gobierno-central-total",
            )
            self.assertIsNone(nac["comparacion_mismo_mes_anterior"])
            codigos_desglose = [p["codigo"] for p in nac["desglose_partidas"]]
            self.assertEqual(codigos_desglose, ["21", "22", "24", "29-31", "33"])

            # 2. GORE Aysén (Partida 31)
            gore = res["entidades"]["gore_aysen"]
            self.assertEqual(gore["territorio_etiqueta"], "Región de Aysén")
            self.assertEqual(gore["inicial_millones"], "82000")
            self.assertEqual(gore["vigente_millones"], "85500")
            self.assertEqual(gore["ejecutado_millones"], "80000")
            self.assertEqual(gore["gasto_corriente_millones"], "10000")
            self.assertEqual(gore["gasto_corriente_pct"], "12.5")
            self.assertEqual(gore["inversion_y_capital_millones"], "70000")
            self.assertEqual(gore["inversion_y_capital_pct"], "87.5")
            self.assertEqual(gore["costo_administrar"]["monto_millones"], "10000")
            self.assertEqual(gore["costo_administrar"]["porcentaje"], "12.5")

            # 3. Vialidad MOP (Partida 12 Cap 02 — sin mezclar Obras Portuarias!)
            vial = res["entidades"]["vialidad_mop_nacional"]
            self.assertIn("Dirección de Vialidad MOP", vial["territorio_etiqueta"])
            self.assertEqual(vial["inicial_millones"], "2110000")
            self.assertEqual(vial["vigente_millones"], "2215000")
            self.assertEqual(vial["ejecutado_millones"], "2000000")
            self.assertEqual(vial["gasto_corriente_pct"], "10")
            self.assertEqual(vial["inversion_y_capital_pct"], "90")

            # 4. Servicios regionales Aysén (DPR 2.000 + Salud 98.000 = 100.000M)
            serv = res["entidades"]["servicios_regionales_aysen"]
            self.assertEqual(serv["ejecutado_millones"], "100000")
            self.assertEqual(serv["gasto_corriente_millones"], "82000")
            self.assertEqual(serv["inversion_y_capital_millones"], "18000")

            # Caché vigente: no vuelve a llamar a CKAN
            llamadas_antes = len(llamadas)
            res_cache = dipres_ckan.obtener_presupuestos_piloto_live(
                anio=2025,
                refresh=False,
                cache_path=cache_file,
                http_get_json=fake_http,
            )
            self.assertEqual(len(llamadas), llamadas_antes)
            self.assertTrue(res_cache["fuente_trazabilidad"]["desde_cache"])
            self.assertEqual(
                res_cache["fuente_trazabilidad"]["estado_actualizacion"],
                dipres_ckan.ESTADO_ACTUALIZACION_CACHE,
            )

            # Respaldo automático ante falla CKAN con refresh=True
            def fake_http_caido(url: str, timeout: int) -> dict:
                raise URLError("CKAN fuera de servicio")

            res_respaldo = dipres_ckan.obtener_presupuestos_piloto_live(
                anio=2025,
                refresh=True,
                cache_path=cache_file,
                http_get_json=fake_http_caido,
            )
            self.assertEqual(
                res_respaldo["fuente_trazabilidad"]["estado_actualizacion"],
                dipres_ckan.ESTADO_ACTUALIZACION_RESPALDO,
            )
            self.assertTrue(res_respaldo["fuente_trazabilidad"]["desde_cache"])
            self.assertIsNotNone(res_respaldo["fuente_trazabilidad"]["advertencia_actualizacion"])
            self.assertEqual(
                res_respaldo["entidades"]["gobierno_central_nacional"]["ejecutado_millones"],
                "100000000",
            )

    def test_piloto_2026_agosto_sin_ley_activa_y_comparacion_mismo_mes_2025(self):
        def fake_http_2026(url: str, timeout: int) -> dict:
            parsed = urlsplit(url)
            qs = parse_qs(parsed.query)

            if parsed.path.endswith("/package_search"):
                q = qs.get("q", [""])[0].lower()
                if "ley de presupuestos" in q and "2026" in q:
                    return {
                        "success": True,
                        "result": {
                            "results": [
                                {
                                    "name": "ley-de-presupuestos-inicial-y-vigente-a-agosto-de-2026-del-gobierno-central-total",
                                    "title": "Ley de Presupuestos Inicial y Vigente a Agosto de 2026 del Gobierno Central - Total",
                                    "metadata_modified": "2026-09-30T10:00:00Z",
                                    "resources": [
                                        {
                                            "id": "res-ley-2026-inactivo",
                                            "name": "A nivel Nacional",
                                            "format": "CSV",
                                            "datastore_active": False,
                                        }
                                    ],
                                }
                            ]
                        },
                    }
                if "ejecucion presupuestaria" in q and "2026" in q:
                    return {
                        "success": True,
                        "result": {
                            "results": [
                                {
                                    "name": "ejecucion-presupuestaria-a-agosto-de-2026-del-gobierno-central-total",
                                    "title": "Ejecución Presupuestaria a Agosto de 2026 del Gobierno Central - Total",
                                    "metadata_modified": "2026-10-01T12:00:00Z",
                                    "resources": [
                                        {
                                            "id": "res-nac-ago-2026",
                                            "name": "A nivel Nacional",
                                            "datastore_active": True,
                                        },
                                        {
                                            "id": "res-prog-ago-2026",
                                            "name": "A nivel Programa",
                                            "datastore_active": True,
                                        },
                                    ],
                                }
                            ]
                        },
                    }
                if "agosto" in q and "2025" in q:
                    return {
                        "success": True,
                        "result": {
                            "results": [
                                {
                                    "name": "ejecucion-presupuestaria-a-agosto-de-2025-del-gobierno-central-total",
                                    "title": "Ejecución Presupuestaria a Agosto de 2025 del Gobierno Central - Total",
                                    "metadata_modified": "2025-10-01T12:00:00Z",
                                    "resources": [
                                        {
                                            "id": "res-nac-ago-2025",
                                            "name": "A nivel Nacional",
                                            "datastore_active": True,
                                        },
                                        {
                                            "id": "res-prog-ago-2025",
                                            "name": "A nivel Programa",
                                            "datastore_active": True,
                                        },
                                    ],
                                }
                            ]
                        },
                    }
                return {"success": True, "result": {"results": []}}

            if parsed.path.endswith("/datastore_search"):
                rid = qs.get("resource_id", [""])[0]
                filtros = json.loads(qs.get("filters", ["{}"])[0])

                if rid == "res-nac-ago-2026":
                    return {
                        "success": True,
                        "result": {
                            "total": 2,
                            "records": [
                                {
                                    "_id": 1,
                                    "Moneda": "PESOS",
                                    "Subtitulo": "21",
                                    "Ejecucion a Agosto": "55.000.000.000",
                                },
                                {
                                    "_id": 2,
                                    "Moneda": "PESOS",
                                    "Subtitulo": "31",
                                    "Ejecucion a Agosto": "11.000.000.000",
                                },
                            ],
                        },
                    }
                if rid == "res-nac-ago-2025":
                    return {
                        "success": True,
                        "result": {
                            "total": 2,
                            "records": [
                                {
                                    "_id": 11,
                                    "Moneda": "PESOS",
                                    "Subtitulo": "21",
                                    "Ejecucion a Agosto": "50.000.000.000",
                                },
                                {
                                    "_id": 12,
                                    "Moneda": "PESOS",
                                    "Subtitulo": "31",
                                    "Ejecucion a Agosto": "10.000.000.000",
                                },
                            ],
                        },
                    }
                if rid == "res-prog-ago-2026":
                    if filtros.get("Partida") == "31":
                        return {
                            "success": True,
                            "result": {
                                "total": 2,
                                "records": [
                                    {
                                        "_id": 21,
                                        "Partida": "31",
                                        "Programa": "14",
                                        "Nombre Programa": "GOBIERNO REGIONAL REGIÓN DE AYSÉN",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "24",
                                        "Ejecucion a Agosto": "6.000.000",
                                    },
                                    {
                                        "_id": 22,
                                        "Partida": "31",
                                        "Programa": "14",
                                        "Nombre Programa": "GOBIERNO REGIONAL REGIÓN DE AYSÉN",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "33",
                                        "Ejecucion a Agosto": "54.000.000",
                                    },
                                ],
                            },
                        }
                    return {"success": True, "result": {"total": 0, "records": []}}
                if rid == "res-prog-ago-2025":
                    if filtros.get("Partida") == "31":
                        return {
                            "success": True,
                            "result": {
                                "total": 2,
                                "records": [
                                    {
                                        "_id": 31,
                                        "Partida": "31",
                                        "Programa": "14",
                                        "Nombre Programa": "GOBIERNO REGIONAL REGIÓN DE AYSÉN",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "24",
                                        "Ejecucion a Agosto": "5.000.000",
                                    },
                                    {
                                        "_id": 32,
                                        "Partida": "31",
                                        "Programa": "14",
                                        "Nombre Programa": "GOBIERNO REGIONAL REGIÓN DE AYSÉN",
                                        "Moneda": "PESOS",
                                        "Subtitulo": "33",
                                        "Ejecucion a Agosto": "45.000.000",
                                    },
                                ],
                            },
                        }
                    return {"success": True, "result": {"total": 0, "records": []}}

            raise AssertionError(f"URL inesperada en mock 2026: {url}")

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "dipres-piloto-2026.json"
            res = dipres_ckan.obtener_presupuestos_piloto_live(
                anio=2026,
                refresh=True,
                cache_path=cache_file,
                http_get_json=fake_http_2026,
            )

            self.assertEqual(res["anio"], 2026)
            self.assertEqual(res["mes_corte"], 8)
            self.assertFalse(res["es_cierre_anual"])
            self.assertIsNotNone(res["fuente_trazabilidad"]["advertencia_comparabilidad_meses"])
            self.assertFalse(res["ley_presupuestos"]["tiene_datastore_active"])

            # Cuando Ley 2026 tiene datastore_active=False -> inicial=None, vigente=None con motivo
            nac = res["entidades"]["gobierno_central_nacional"]
            self.assertIsNone(nac["inicial_millones"])
            self.assertIsNone(nac["vigente_millones"])
            self.assertIn("datastore_active=False", nac["motivo_inicial_vigente"])
            self.assertEqual(nac["ejecutado_millones"], "66000000")
            self.assertIn("enero y agosto de 2026", nac["frase_radial"])

            # Comparación mismo mes año anterior (enero–agosto 2026 vs enero–agosto 2025)
            # Nacional: 66.000.000 vs 60.000.000 -> +6.000.000 (+10%)
            comp_nac = nac["comparacion_mismo_mes_anterior"]
            self.assertTrue(comp_nac["disponible"])
            self.assertEqual(comp_nac["etiqueta"], "enero–agosto 2026 vs enero–agosto 2025")
            self.assertEqual(comp_nac["ejecutado_mismo_mes_anterior_millones"], "60000000")
            self.assertEqual(comp_nac["diferencia_millones"], "6000000")
            self.assertEqual(comp_nac["variacion_nominal_pct"], "10")

            # GORE Aysén: 60.000 vs 50.000 -> +10.000 (+20%)
            gore = res["entidades"]["gore_aysen"]
            self.assertIsNone(gore["inicial_millones"])
            self.assertIsNone(gore["vigente_millones"])
            comp_gore = gore["comparacion_mismo_mes_anterior"]
            self.assertTrue(comp_gore["disponible"])
            self.assertEqual(comp_gore["etiqueta"], "enero–agosto 2026 vs enero–agosto 2025")
            self.assertEqual(comp_gore["ejecutado_mismo_mes_anterior_millones"], "50000")
            self.assertEqual(comp_gore["diferencia_millones"], "10000")
            self.assertEqual(comp_gore["variacion_nominal_pct"], "20")


if __name__ == "__main__":
    unittest.main()
