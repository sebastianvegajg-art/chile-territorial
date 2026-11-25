"""Pruebas unitarias e integración local para el Piloto Aysén (4 pestañas):
- GET /api/v1/aysen/resumen
- GET /api/v1/aysen/economia
- GET /api/v1/aysen/presupuestos
- GET /api/v1/aysen/proyectos

Verifica:
- Aritmética exacta con Decimal y respeto a la no aditividad de volúmenes encadenados.
- Municipalidad de Aysén (11201): porcentaje de gasto corriente observable, base de
  cálculo explícita, frase radial, desglose Subt. 21/22 y enlace oficial SINIM.
- Tres billeteras + Gobierno Central Nacional separado (nunca sumado al consolidado).
- Año en curso (2026): mes de corte y comparación contra el mismo período del año anterior.
- Proyectos MOP (Vialidad): 2 preguntas separadas (pagos de contratos anteriores vs
  arrastre presupuestario), 4 hitos en línea de tiempo y aislamiento de proyectos con
  información insuficiente.
- Degradación honesta ("Sin dato disponible") sin inventar cifras cuando faltan cortes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from apps.api import aysen_piloto as ap


def _fixture_pib() -> dict:
    return {
        "publicacion": {"id": "bcch-test-2025", "fecha": "2026-03-18"},
        "observaciones": [
            {"territorio": "11", "anio": 2024, "metrica": "crecimiento", "valoracion": "real", "valor": "2.10"},
            {"territorio": "CL", "anio": 2024, "metrica": "crecimiento", "valoracion": "real", "valor": "2.60"},
            {"territorio": "11", "anio": 2025, "metrica": "crecimiento", "valoracion": "real", "valor": "8.49"},
            {"territorio": "CL", "anio": 2025, "metrica": "crecimiento", "valoracion": "real", "valor": "2.46"},
            {"territorio": "11", "anio": 2025, "metrica": "participacion", "valoracion": "nominal", "valor": "0.59"},
            {"territorio": "11", "anio": 2025, "metrica": "nivel", "valoracion": "nominal", "valor": "1990584.34"},
            {"territorio": "CL", "anio": 2025, "metrica": "nivel", "valoracion": "nominal", "valor": "337000000.00"},
            {"territorio": "11", "anio": 2025, "metrica": "nivel", "valoracion": "real", "valor": "1430527.61"},
        ],
    }


def _fixture_sectorial() -> dict:
    return {
        "publicacion": {"id": "bcch-sectorial-test", "fecha": "2026-03-18"},
        "por_anio": {
            "2024": {
                "regiones": {
                    "11": {
                        "hhi": "1400.00",
                        "diversificacion": "0.8600",
                        "indice_krugman": "0.3900",
                        "actividades": [
                            {"actividad_id": "pesca", "nombre": "Pesca", "participacion_nominal_pct": "25.00"},
                            {"actividad_id": "administracion_publica", "nombre": "Administración pública", "participacion_nominal_pct": "17.00"},
                            {"actividad_id": "construccion", "nombre": "Construcción", "participacion_nominal_pct": "8.00"},
                        ],
                    }
                }
            },
            "2025": {
                "regiones": {
                    "11": {
                        "hhi": "1420.87",
                        "diversificacion": "0.8579",
                        "indice_krugman": "0.3870",
                        "actividades": [
                            {
                                "actividad_id": "pesca",
                                "nombre": "Pesca",
                                "participacion_nominal_pct": "27.16",
                                "nominal_millones": "520000.00",
                                "real_millones": "380000.00",
                                "crecimiento_real_pct": "18.44",
                                "lq_especializacion": "12.50",
                                "serie_bde_nominal": "F035.PESCA.11.N",
                                "serie_bde_real": "F035.PESCA.11.R",
                            },
                            {
                                "actividad_id": "administracion_publica",
                                "nombre": "Administración pública",
                                "participacion_nominal_pct": "16.10",
                                "nominal_millones": "310000.00",
                                "real_millones": "230000.00",
                                "crecimiento_real_pct": "1.20",
                                "lq_especializacion": "3.10",
                                "serie_bde_nominal": "F035.ADM.11.N",
                                "serie_bde_real": "F035.ADM.11.R",
                            },
                            {
                                "actividad_id": "construccion",
                                "nombre": "Construcción",
                                "participacion_nominal_pct": "7.20",
                                "nominal_millones": "135000.00",
                                "real_millones": "98000.00",
                                "crecimiento_real_pct": "-3.50",
                                "lq_especializacion": "0.95",
                                "serie_bde_nominal": "F035.CON.11.N",
                                "serie_bde_real": "F035.CON.11.R",
                            },
                        ],
                    }
                }
            },
        },
    }


def _fixture_sinim() -> dict:
    return {
        "esquema": "sinim-fichas-aysen-v1",
        "resumen": {"anio": 2025, "comunas_procesadas": 1},
        "comunas": [
            {
                "cut": "11201",
                "municipio": "Aysén",
                "anio": 2025,
                "etapa_contable": "devengo",
                "unidad_salida": "millones CLP",
                "presupuesto_inicial_millones": None,
                "presupuesto_vigente_millones": None,
                "ingresos_percibidos_millones": "15200.500",
                "gasto_total_devengado_millones": "13991.886",
                "gasto_personal_sub21_millones": "6881.918",
                "personal_planta_millones": "3044.450",
                "personal_contrata_millones": "1269.147",
                "personal_honorarios_millones": "665.800",
                "personal_programas_comunitarios_millones": "1815.588",
                "gasto_bienes_servicios_sub22_millones": "3691.026",
                "gasto_corriente_observable_millones": "10572.944",
                "porcentaje_gasto_corriente_pct": "75.56",
                "costo_admin_interno_millones": "4979.397",
                "costo_admin_interno_pct": "35.59",
                "base_calculo_gasto_corriente": "Subt. 21 + Subt. 22 / Gasto Total Devengado BEP SINIM.",
                "frase_radial": "De cada $100 ejecutados por la Municipalidad de Aysén en 2025, $75,6 correspondieron a gasto corriente observable.",
                "url_respaldo": "https://datos.sinim.gov.cl/impresion_ficha_comunal.php?municipio=11201",
            }
        ],
    }


def _fixture_dipres(anio: int, mes_corte: int) -> dict:
    comp = (
        {
            "disponible": True,
            "comparable": True,
            "anio_anterior": anio - 1,
            "mes_corte": mes_corte,
            "etiqueta": f"enero–agosto {anio} vs enero–agosto {anio - 1}",
            "ejecutado_mismo_mes_anterior_millones": "64164.878",
            "variacion_nominal_pct": "-2.78",
            "nota": "Variación nominal interanual en meses acumulados equivalentes.",
        }
        if mes_corte < 12
        else None
    )
    return {
        "esquema": "dipres-piloto-presupuestario-v1",
        "anio": anio,
        "mes_corte": mes_corte,
        "es_cierre_anual": mes_corte == 12,
        "entidades": {
            "gobierno_central_nacional": {
                "nombre": "Gobierno Central de Chile (Nivel Nacional)",
                "territorio_etiqueta": "Chile (Nivel Nacional)",
                "inicial_millones": "88493814.691",
                "vigente_millones": "100620653.653",
                "ejecutado_millones": "98802752.751",
                "tasa_ejecucion_pct": "98.19",
                "gasto_corriente_millones": "66156353.625",
                "gasto_corriente_pct": "66.96",
                "inversion_y_capital_millones": "13367862.856",
                "inversion_y_capital_pct": "13.53",
                "desglose_partidas": [{"codigo": "21", "etiqueta": "Personal (Subt. 21)", "ejecutado_millones": "17033303.555", "porcentaje_ejecutado_pct": "17.24"}],
                "costo_administrar": {"disponible": True, "monto_millones": "23699452.634", "porcentaje": "23.99", "explicacion": "Subt. 21 + Subt. 22."},
                "url_respaldo": "https://datos.gob.cl/dataset/ejecucion-presupuestaria-nacional",
            },
            "gore_aysen": {
                "nombre": "Gobierno Regional de Aysén (Partida 31)",
                "territorio_etiqueta": "Región de Aysén",
                "inicial_millones": "90662.776",
                "vigente_millones": "88494.495",
                "ejecutado_millones": "79897.034" if mes_corte == 12 else "62378.411",
                "tasa_ejecucion_pct": "90.28" if mes_corte == 12 else "65.96",
                "gasto_corriente_millones": "8585.033" if mes_corte == 12 else "5717.262",
                "gasto_corriente_pct": "10.75" if mes_corte == 12 else "9.17",
                "inversion_y_capital_millones": "71312.001" if mes_corte == 12 else "56661.149",
                "inversion_y_capital_pct": "89.25" if mes_corte == 12 else "90.83",
                "desglose_partidas": [
                    {"codigo": "24", "etiqueta": "Transferencias corrientes (Subt. 24)", "ejecutado_millones": "8585.033", "porcentaje_ejecutado_pct": "10.75"},
                    {"codigo": "33", "etiqueta": "Transferencias de capital (Subt. 33)", "ejecutado_millones": "71312.001", "porcentaje_ejecutado_pct": "89.25"},
                ],
                "costo_administrar": {"disponible": True, "monto_millones": "8585.033", "porcentaje": "10.75", "explicacion": "Gasto corriente Partida 31."},
                "comparacion_mismo_mes_anterior": comp,
                "url_respaldo": "https://datos.gob.cl/dataset/ejecucion-presupuestaria-gore",
            },
            "vialidad_mop_nacional": {
                "nombre": "Dirección de Vialidad — MOP (Partida 12, Capítulo 02)",
                "territorio_etiqueta": "Chile (Nacional — Dirección de Vialidad MOP)",
                "inicial_millones": "2429283.946",
                "vigente_millones": "2512149.164",
                "ejecutado_millones": "2476648.939",
                "gasto_corriente_millones": "218735.496",
                "gasto_corriente_pct": "8.83",
                "inversion_y_capital_millones": "2070821.336",
                "inversion_y_capital_pct": "83.61",
                "desglose_partidas": [{"codigo": "29-31", "etiqueta": "Inversión física (Subt. 29–31)", "ejecutado_millones": "2070821.336", "porcentaje_ejecutado_pct": "83.61"}],
                "url_respaldo": "https://datos.gob.cl/dataset/ejecucion-vialidad",
            },
            "servicios_regionales_aysen": {
                "nombre": "Servicios Públicos del Gobierno Central en Aysén",
                "territorio_etiqueta": "Región de Aysén",
                "inicial_millones": "628410.326",
                "vigente_millones": "686410.861",
                "ejecutado_millones": "686763.815",
                "gasto_corriente_millones": "488161.822",
                "gasto_corriente_pct": "71.08",
                "inversion_y_capital_millones": "67751.190",
                "inversion_y_capital_pct": "9.87",
                "url_respaldo": "https://datos.gob.cl/dataset/servicios-aysen",
            },
        },
        "fuente_trazabilidad": {
            "package_name": f"ejecucion-presupuestaria-{anio}",
            "mes_corte": mes_corte,
        },
    }


def _fixture_mop() -> dict:
    return {
        "version_esquema": "mop-aysen-proyectos-v1",
        "publicacion": {
            "id": "mop-aysen-2026",
            "anio_corte": 2026,
            "fecha_cambio_administracion": "2026-03-11",
        },
        "proyectos": [
            {
                "id_contrato": "C-101",
                "codigo_bip": "30113737-0",
                "nombre_proyecto": "Mejoramiento Ruta 7 Sur",
                "nombre_contrato": "Mejoramiento Ruta 7 Sur tramo Puerto Aysén",
                "institucion": "Dirección de Vialidad",
                "comunas": ["Aysén"],
                "nuevo_o_arrastre": "arrastre",
                "calidad_informacion": "documentado",
                "motivos_insuficiencia": [],
                "costo_total_contrato_millones": "12000.000",
                "compromiso_anio_millones": "800.000",
                "pagado_anio_millones": "600.000",
                "pagado_anios_anteriores_millones": "5000.000",
                "saldo_pendiente_millones": "6400.000",
                "fecha_contratacion": "2024-06-15",
                "administracion_contratacion": "Administración 2022–2026",
                "firmado_antes_administracion_actual": True,
                "fecha_termino_programada": "2027-06-15",
                "frase_radial": "Esta obra en Aysén fue contratada por la Dirección de Vialidad del MOP el 15-06-2024 (Administración 2022–2026) y registra $600,0 millones pagados en 2026.",
                "linea_tiempo": [
                    {"hito": "aprobacion_financiamiento", "titulo": "Aprobación del financiamiento", "fecha": "2024-01-10", "institucion_responsable": "MDSF / BIP", "administracion_vigente": "Administración 2022–2026", "url_respaldo": "https://sipro.mop.gob.cl/1"},
                    {"hito": "contratacion", "titulo": "Contratación", "fecha": "2024-06-15", "institucion_responsable": "Dirección de Vialidad", "administracion_vigente": "Administración 2022–2026", "url_respaldo": "https://www.mercadopublico.cl/1"},
                    {"hito": "pagos", "titulo": "Pagos ejecutados", "fecha": "2026-11-16", "institucion_responsable": "Dirección de Vialidad", "administracion_vigente": "Administración 2026–2030", "url_respaldo": "https://sipro.mop.gob.cl/c1"},
                    {"hito": "entrada_funcionamiento", "titulo": "Entrada en funcionamiento", "fecha": "2027-06-15", "institucion_responsable": "Dirección de Vialidad", "administracion_vigente": "Administración 2026–2030", "url_respaldo": None},
                ],
                "enlaces_oficiales": {"ficha_proyecto_sipro": "https://sipro.mop.gob.cl/1"},
            },
            {
                "id_contrato": "C-102",
                "codigo_bip": "40099999-0",
                "nombre_proyecto": "Conservación Puente Coyhaique",
                "nombre_contrato": "Conservación Puente Coyhaique 2026",
                "institucion": "Dirección de Vialidad",
                "comunas": ["Coyhaique"],
                "nuevo_o_arrastre": "nuevo",
                "calidad_informacion": "documentado",
                "motivos_insuficiencia": [],
                "costo_total_contrato_millones": "1500.000",
                "compromiso_anio_millones": "200.000",
                "pagado_anio_millones": "200.000",
                "fecha_contratacion": "2026-05-01",
                "administracion_contratacion": "Administración 2026–2030",
                "firmado_antes_administracion_actual": False,
                "fecha_termino_programada": "2026-12-30",
                "frase_radial": "Esta obra en Coyhaique fue contratada por la Dirección de Vialidad del MOP el 01-05-2026 (Administración 2026–2030) y registra $200,0 millones pagados en 2026.",
                "linea_tiempo": [],
            },
            {
                "id_contrato": "C-999",
                "codigo_bip": None,
                "nombre_proyecto": "Obra sin fecha verificable",
                "institucion": "Dirección de Vialidad",
                "comunas": ["Aysén"],
                "calidad_informacion": "insuficiente",
                "motivos_insuficiencia": ["Sin fecha contractual ni monto anual verificable."],
            },
        ],
    }


class TestAysenPilotoEndpoints(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.pib_path = self.base / "pib.json"
        self.sec_path = self.base / "sectorial.json"
        self.sinim_path = self.base / "sinim.json"
        self.mop_path = self.base / "mop.json"
        self.pib_path.write_text(json.dumps(_fixture_pib()), encoding="utf-8")
        self.sec_path.write_text(json.dumps(_fixture_sectorial()), encoding="utf-8")
        self.sinim_path.write_text(json.dumps(_fixture_sinim()), encoding="utf-8")
        self.mop_path.write_text(json.dumps(_fixture_mop()), encoding="utf-8")

        self._env = patch.dict(
            os.environ,
            {
                "CT_PIB_PATH": str(self.pib_path),
                "CT_SECTORIAL_PATH": str(self.sec_path),
                "CT_SINIM_OFICIAL_PATH": str(self.sinim_path),
                "CT_PROYECTOS_MOP_PATH": str(self.mop_path),
                "CT_DIPRES_PATH": "",
            },
        )
        self._env.start()

    def tearDown(self) -> None:
        self._env.stop()
        self._tmp.cleanup()

    def test_resumen_2025_y_2026_mismo_mes_sin_inventar_pib_2026(self):
        def fake_dipres(anio: int):
            if anio == 2025:
                return _fixture_dipres(2025, 12), "cache_local"
            if anio == 2026:
                return _fixture_dipres(2026, 8), "cache_local"
            return None, None

        with patch.object(ap, "_obtener_datos_dipres_piloto", side_effect=fake_dipres):
            r25 = ap.aysen_resumen(anio=2025, comuna="11201")
            self.assertEqual(r25["anio_seleccionado"], 2025)
            self.assertIsNone(r25["mes_corte_vigente"])
            self.assertTrue(r25["tarjetas"]["economia"]["disponible"])
            self.assertEqual(r25["tarjetas"]["economia"]["valor"], "8.49")
            self.assertTrue(r25["tarjetas"]["inversion"]["disponible"])
            # Corte MOP es 2026, por lo que no se atribuye arrastre 2026 al resumen 2025
            self.assertFalse(r25["tarjetas"]["arrastre"]["disponible"])

            r26 = ap.aysen_resumen(anio=2026, comuna="11201")
            self.assertEqual(r26["mes_corte_vigente"], 8)
            self.assertFalse(r26["tarjetas"]["economia"]["disponible"])
            self.assertIsNone(r26["tarjetas"]["economia"]["valor"])
            self.assertTrue(r26["tarjetas"]["inversion"]["disponible"])
            self.assertEqual(r26["tarjetas"]["inversion"]["comparacion_mismo_periodo_anterior"]["variacion_pct"], "-2.78")
            self.assertTrue(r26["tarjetas"]["arrastre"]["disponible"])

    def test_economia_tamano_vs_aporte_y_no_inventa_2026(self):
        e25 = ap.aysen_economia(anio=2025)
        self.assertTrue(e25["datos_anio_disponibles"])
        self.assertEqual(e25["resumen_anio"]["crecimiento_real_aysen_pct"], "8.49")
        self.assertEqual(len(e25["actividades"]), 3)
        self.assertEqual(e25["sectores_crecieron"][0]["actividad_id"], "pesca")
        self.assertEqual(e25["sectores_cayeron"][0]["actividad_id"], "construccion")
        # Aporte estimado pesca = 25.00 * 18.44 / 100 = 4.61 pp
        pesca = next(a for a in e25["actividades"] if a["actividad_id"] == "pesca")
        self.assertEqual(pesca["aporte_estimado_pp"], "4.61")
        self.assertIn("tamaño", e25["frase_tamano_vs_aporte"].lower())
        self.assertTrue(e25["fuente_trazabilidad"]["regla_no_aditividad_volumenes_encadenados"])

        e26 = ap.aysen_economia(anio=2026)
        self.assertFalse(e26["datos_anio_disponibles"])
        self.assertIsNone(e26["resumen_anio"]["crecimiento_real_aysen_pct"])
        self.assertIn("2025", e26["aviso_sin_cierre_anual"])

    def test_presupuestos_piloto_muni_aysen_gore_vialidad_gc_y_consolidacion(self):
        def fake_dipres(anio: int):
            if anio == 2025:
                return _fixture_dipres(2025, 12), "cache_local"
            if anio == 2026:
                return _fixture_dipres(2026, 8), "cache_local"
            return None, None

        with patch.object(ap, "_obtener_datos_dipres_piloto", side_effect=fake_dipres):
            p25 = ap.aysen_presupuestos(anio=2025, comuna="11201")
            muni = p25["billeteras"]["municipal"]
            self.assertTrue(muni["disponible"])
            self.assertEqual(muni["nombre"], "Municipalidad de Aysén")
            self.assertEqual(muni["devengado_bep_millones"], "13991.886")
            self.assertEqual(muni["gasto_corriente_observable_pct"], "75.56")
            self.assertEqual(muni["costo_administracion_interna"]["porcentaje_sobre_devengado"], "35.59")
            self.assertIsNone(muni["inicial_millones"])
            self.assertEqual(muni["url_ficha_oficial"], "https://datos.sinim.gov.cl/impresion_ficha_comunal.php?municipio=11201")

            gore = p25["billeteras"]["gore_aysen"]
            self.assertEqual(gore["inicial_millones"], "90662.776")
            self.assertEqual(gore["vigente_millones"], "88494.495")
            self.assertEqual(gore["ejecutado_millones"], "79897.034")
            self.assertEqual(gore["proporcion_gasto_corriente_pct"], "10.75")
            self.assertEqual(gore["inversion_pct"], "89.25")
            self.assertEqual(len(gore["desglose_partidas"]), 2)

            gc = p25["gobierno_central_nacional"]
            self.assertTrue(gc["disponible"])
            self.assertEqual(gc["proporcion_gasto_corriente_pct"], "66.96")

            # Consolidación regional excluye estrictamente Gobierno Central Nacional
            consol = p25["consolidacion"]
            self.assertTrue(consol["disponible"])
            self.assertTrue(consol["conservacion_aritmetica_ok"])
            self.assertEqual(consol["consolidado_neto_millones"], "780652.735")

            # 2026 en curso: comparación mismo mes y SINIM honestamente sin dato
            p26 = ap.aysen_presupuestos(anio=2026, comuna="11201")
            self.assertEqual(p26["mes_corte"], 8)
            self.assertTrue(p26["comparacion_mismo_mes"]["disponible"])
            self.assertEqual(p26["comparacion_mismo_mes"]["variacion_gore_pct"], "-2.78")
            self.assertFalse(p26["billeteras"]["municipal"]["disponible"])

    def test_proyectos_dos_preguntas_separadas_y_aislamiento_insuficientes(self):
        pr = ap.aysen_proyectos(anio=2026, comuna="", institucion="Vialidad", q="")
        self.assertTrue(pr["disponible"])
        self.assertEqual(pr["total_documentados"], 2)
        self.assertEqual(pr["total_informacion_insuficiente"], 1)
        self.assertEqual(pr["proyectos_informacion_insuficiente"][0]["id_contrato"], "C-999")

        # Pregunta 1: 600 / (600 + 200) = 75.00%
        self.assertEqual(pr["pagos_contratos_anteriores"]["porcentaje"], "75.00")
        self.assertEqual(pr["pagos_contratos_anteriores"]["monto_pagado_contratos_anteriores_millones"], "600.000")
        # Pregunta 2: 800 / (800 + 200) = 80.00% (diferente a Pregunta 1!)
        self.assertEqual(pr["arrastre_presupuesto"]["porcentaje"], "80.00")
        self.assertEqual(pr["arrastre_presupuesto"]["monto_arrastre_comprometido_millones"], "800.000")

        # Búsqueda por comuna
        pr_aysen = ap.aysen_proyectos(anio=2026, comuna="11201", institucion="Vialidad", q="")
        self.assertEqual(pr_aysen["total_documentados"], 1)
        self.assertEqual(pr_aysen["proyectos_documentados"][0]["id_contrato"], "C-101")
        self.assertEqual(len(pr_aysen["proyectos_documentados"][0]["linea_tiempo"]), 4)

    def test_proyectos_combinados_mop_y_dipres_bip_sin_doble_conteo_ni_contaminar_p1(self):
        bip_fixture = {
            "esquema": "dipres-bip-aysen-v1",
            "por_anio": {
                "2025": [
                    {
                        "id_contrato": "BIP-2025-0571-30418427-0",
                        "origen_fuente": "dipres_subt31_bip",
                        "codigo_bip": "30418427-0",
                        "nombre_proyecto": "Construcción Miradores Aysén",
                        "institucion": "Gobierno Regional de Aysén (FNDR)",
                        "partida": "05",
                        "capitulo": "71",
                        "comunas": ["Coyhaique"],
                        "anio_ejercicio": 2025,
                        "nuevo_o_arrastre": "arrastre",
                        "calidad_informacion": "documentado",
                        "motivos_insuficiencia": [],
                        "compromiso_anio_millones": "3000.000",
                        "pagado_anio_millones": "2500.000",
                        "fecha_contratacion": None,
                        "firmado_antes_administracion_actual": None,
                    },
                    {
                        "id_contrato": "BIP-2025-1831-40088888-0",
                        "origen_fuente": "dipres_subt31_bip",
                        "codigo_bip": "40088888-0",
                        "nombre_proyecto": "Parque Urbano Aysén",
                        "institucion": "SERVIU Región de Aysén (MINVU)",
                        "partida": "18",
                        "capitulo": "31",
                        "comunas": ["Aysén"],
                        "anio_ejercicio": 2025,
                        "nuevo_o_arrastre": "nuevo",
                        "calidad_informacion": "documentado",
                        "motivos_insuficiencia": [],
                        "compromiso_anio_millones": "1000.000",
                        "pagado_anio_millones": "400.000",
                        "fecha_contratacion": None,
                        "firmado_antes_administracion_actual": None,
                    },
                ],
                "2026": [
                    # Mismo BIP que MOP C-101 (Partida 12) -> NO debe duplicarse
                    {
                        "id_contrato": "BIP-2026-1202-30113737-0",
                        "origen_fuente": "dipres_subt31_bip",
                        "codigo_bip": "30113737-0",
                        "nombre_proyecto": "Mejoramiento Ruta 7 Sur (duplicado MOP)",
                        "institucion": "MOP — Dirección General de Obras Públicas (BIP)",
                        "partida": "12",
                        "capitulo": "02",
                        "comunas": ["Aysén"],
                        "anio_ejercicio": 2026,
                        "nuevo_o_arrastre": "arrastre",
                        "calidad_informacion": "documentado",
                        "motivos_insuficiencia": [],
                        "compromiso_anio_millones": "9999.000",
                        "pagado_anio_millones": "9999.000",
                        "fecha_contratacion": None,
                        "firmado_antes_administracion_actual": None,
                    },
                    # GORE Aysén FNDR 2026 -> SÍ debe sumarse a Pregunta 2, pero NO contaminar Pregunta 1
                    {
                        "id_contrato": "BIP-2026-0571-30418427-0",
                        "origen_fuente": "dipres_subt31_bip",
                        "codigo_bip": "30418427-0",
                        "nombre_proyecto": "Construcción Miradores Aysén",
                        "institucion": "Gobierno Regional de Aysén (FNDR)",
                        "partida": "05",
                        "capitulo": "71",
                        "comunas": ["Coyhaique"],
                        "anio_ejercicio": 2026,
                        "nuevo_o_arrastre": "arrastre",
                        "calidad_informacion": "documentado",
                        "motivos_insuficiencia": [],
                        "compromiso_anio_millones": "1000.000",
                        "pagado_anio_millones": "500.000",
                        "fecha_contratacion": None,
                        "firmado_antes_administracion_actual": None,
                    },
                ],
            },
            "indice_bip_historico": {
                "30113737-0": {"primer_anio_observado": 2021, "anios_activos": [2021, 2026]}
            },
        }
        bip_path = self.base / "proyectos-bip.json"
        bip_path.write_text(json.dumps(bip_fixture), encoding="utf-8")
        with patch.dict(os.environ, {"CT_PROYECTOS_BIP_PATH": str(bip_path)}):
            # 2026 combinado: 2 MOP doc + 1 GORE BIP doc = 3 doc (duplicado MOP 30113737-0 excluido!)
            p26 = ap.aysen_proyectos(anio=2026, comuna="", institucion="", q="")
            self.assertEqual(p26["total_documentados"], 3)
            # Pregunta 1 sigue siendo estrictamente MOP (600 / 800 = 75.00%), sin contaminar con GORE sin fecha contrato
            self.assertEqual(p26["pagos_contratos_anteriores"]["porcentaje"], "75.00")
            # Pregunta 2 incluye GORE arrastre: (800 + 1000) / (800 + 200 + 1000) = 1800 / 2000 = 90.00%
            self.assertEqual(p26["arrastre_presupuesto"]["porcentaje"], "90.00")

            # 2025 histórico DIPRES BIP: 3000 / 4000 = 75.00% arrastre, P1 no disponible sin fecha contrato
            p25 = ap.aysen_proyectos(anio=2025, comuna="", institucion="", q="")
            self.assertEqual(p25["total_documentados"], 2)
            self.assertFalse(p25["pagos_contratos_anteriores"]["disponible"])
            self.assertEqual(p25["arrastre_presupuesto"]["porcentaje"], "75.00")

    def test_comuna_invalida_devuelve_422(self):
        with self.assertRaises(HTTPException) as ctx:
            ap.aysen_presupuestos(anio=2025, comuna="13101")
        self.assertEqual(ctx.exception.status_code, 422)

    def test_healthz_y_cors_despliegue_produccion(self):
        from fastapi.testclient import TestClient
        from apps.api.main import crear_app

        with patch.dict(os.environ, {"CT_CORS_ORIGINS": "https://chile-territorial.netlify.app"}):
            app = crear_app(demo_activa=True)
            client = TestClient(app)
            resp = client.get(
                "/healthz",
                headers={"origin": "https://chile-territorial.netlify.app"},
            )
            self.assertEqual(resp.status_code, 200)
            payload = resp.json()
            self.assertEqual(payload["estado"], "ok")
            self.assertEqual(payload["servicio"], "chile-territorial-api")
            self.assertIn("datos_publicados", payload)
            self.assertEqual(
                resp.headers.get("access-control-allow-origin"),
                "https://chile-territorial.netlify.app",
            )


if __name__ == "__main__":
    unittest.main()
