"""Pruebas unitarias e integración local para Fase 2:
- Auditoría de seguridad en apps/api/conectores.py
- GET /api/v1/sectorial/regiones
- GET /api/v1/demografia/poblacion
- GET /api/v1/cruces/resumen
- POST /api/v1/laboratorio/consultar y apps/api/laboratorio.py

Utiliza invocación ASGI directa (sin abrir sockets loopback) para compatibilidad
total en sandbox.
"""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from apps.api import conectores
from apps.api.laboratorio import RAIZ_REPO, ejecutar_investigacion
from apps.api.main import crear_app
from apps.api.test_conectores import invocar_asgi


CAMPOS_PROTOCOLO_10 = (
    "pregunta_formulada",
    "variables_y_fuentes",
    "hipotesis_y_metodo",
    "consultas_verificadas",
    "resultados_reproducibles",
    "tabla_evidencia",
    "hipotesis_alternativas",
    "interpretacion",
    "limitaciones",
    "dossier_markdown",
)


def _construir_sectorial_prueba() -> dict:
    return {
        "publicacion": {
            "id": "bcch-sectorial-16r-test-2026-11-24",
            "fecha": "2026-11-24T23:30:00+00:00",
            "estado": "aprobada",
            "fuente": "BCCh-BDE",
            "series_totales": 416,
            "anios": [2024, 2025],
        },
        "actividades_canonicas": [
            {"id": "02_pesca", "nombre": "Pesca"},
            {"id": "12_administracion_publica", "nombre": "Administración pública"},
        ],
        "por_anio": {
            "2024": {
                "regiones": {
                    "11": {
                        "nombre": "Aysén del General Carlos Ibáñez del Campo",
                        "total_vab_nominal_millones": "1672337.42",
                        "hhi": "1395.10",
                        "diversificacion": "0.8605",
                        "indice_krugman": "0.7120",
                        "actividades": [
                            {
                                "actividad_id": "02_pesca",
                                "nombre": "Pesca",
                                "serie_bde_nominal": "F035.PIB.FLU.N.CLP.2018.02.04.Z.11.0.A",
                                "nominal_millones": "410000.00",
                                "participacion_nominal_pct": "24.52",
                                "lq_especializacion": "12.40",
                            },
                            {
                                "actividad_id": "12_administracion_publica",
                                "nombre": "Administración pública",
                                "serie_bde_nominal": "F035.PIB.FLU.N.CLP.2018.12.Z.Z.11.0.A",
                                "nominal_millones": "285000.00",
                                "participacion_nominal_pct": "17.04",
                                "lq_especializacion": "3.20",
                            },
                        ],
                    },
                    "13": {
                        "nombre": "Metropolitana de Santiago",
                        "total_vab_nominal_millones": "130000000.00",
                        "hhi": "1120.00",
                        "diversificacion": "0.8880",
                        "indice_krugman": "0.2150",
                        "actividades": [],
                    },
                },
                "ranking_hhi": [
                    {"posicion": 1, "territorio": "11", "nombre": "Aysén", "hhi": "1395.10"},
                    {"posicion": 2, "territorio": "13", "nombre": "Metropolitana", "hhi": "1120.00"},
                ],
                "ranking_krugman": [
                    {"posicion": 1, "territorio": "11", "nombre": "Aysén", "indice_krugman": "0.7120"},
                    {"posicion": 2, "territorio": "13", "nombre": "Metropolitana", "indice_krugman": "0.2150"},
                ],
            },
            "2025": {
                "regiones": {
                    "11": {
                        "nombre": "Aysén del General Carlos Ibáñez del Campo",
                        "total_vab_nominal_millones": "1990584.34",
                        "hhi": "1420.87",
                        "diversificacion": "0.8579",
                        "indice_krugman": "0.7410",
                        "actividades": [
                            {
                                "actividad_id": "02_pesca",
                                "nombre": "Pesca",
                                "serie_bde_nominal": "F035.PIB.FLU.N.CLP.2018.02.04.Z.11.0.A",
                                "nominal_millones": "540695.58",
                                "participacion_nominal_pct": "27.16",
                                "lq_especializacion": "13.10",
                            },
                            {
                                "actividad_id": "12_administracion_publica",
                                "nombre": "Administración pública",
                                "serie_bde_nominal": "F035.PIB.FLU.N.CLP.2018.12.Z.Z.11.0.A",
                                "nominal_millones": "319569.54",
                                "participacion_nominal_pct": "16.05",
                                "lq_especializacion": "3.05",
                            },
                        ],
                    },
                    "13": {
                        "nombre": "Metropolitana de Santiago",
                        "total_vab_nominal_millones": "140000000.00",
                        "hhi": "1115.00",
                        "diversificacion": "0.8885",
                        "indice_krugman": "0.2100",
                        "actividades": [],
                    },
                },
                "ranking_hhi": [
                    {"posicion": 1, "territorio": "11", "nombre": "Aysén", "hhi": "1420.87"},
                    {"posicion": 2, "territorio": "13", "nombre": "Metropolitana", "hhi": "1115.00"},
                ],
                "ranking_krugman": [
                    {"posicion": 1, "territorio": "11", "nombre": "Aysén", "indice_krugman": "0.7410"},
                    {"posicion": 2, "territorio": "13", "nombre": "Metropolitana", "indice_krugman": "0.2100"},
                ],
            },
        },
        "fuente_trazabilidad": {
            "institucion": "Banco Central de Chile (BDE SI3 REST API)",
            "series_verificadas": 416,
            "actualizado_en": "2026-04-23",
            "extraido_en": "2026-11-24T23:30:00+00:00",
        },
    }


def _construir_poblacion_ine_prueba() -> dict:
    """Construye un lote compatible con pipelines.demografia.ine_poblacion para 2024-2026."""
    poblaciones_base = {
        "CL": 20000000,
        "01": 400000,
        "02": 720000,
        "03": 320000,
        "04": 870000,
        "05": 2020000,
        "06": 1020000,
        "07": 1170000,
        "08": 1680000,
        "09": 1030000,
        "10": 910000,
        "11": 108000,
        "12": 183000,
        "13": 8420000,
        "14": 412000,
        "15": 261000,
        "16": 521000,
    }
    observaciones = []
    for anio in (2024, 2025, 2026):
        factor = 1 + (anio - 2024) * 0.005
        for cod, base in poblaciones_base.items():
            valor = str(int(round(base * factor)))
            observaciones.append(
                {
                    "id": f"pob-ine-{cod}-{anio}",
                    "territorio": cod,
                    "anio": anio,
                    "metrica": "poblacion",
                    "valor": valor,
                    "unidad": "personas",
                    "estado": "informado",
                    "clase": "oficial" if anio <= 2025 else "proyeccion",
                    "publicacion": "ine-poblacion-test-2026-11-24",
                }
            )
    return {
        "publicacion": {
            "id": "ine-poblacion-test-2026-11-24",
            "fecha": "2026-11-24T23:40:00+00:00",
            "estado": "aprobada",
            "fuente": "INE vía BCCh-BDE",
        },
        "observaciones": observaciones,
    }


class AuditoriaSeguridadConectoresTest(unittest.TestCase):
    def test_sin_alias_publicos_de_token_en_conectores(self):
        ruta_conectores = Path(conectores.__file__).resolve()
        codigo_fuente = ruta_conectores.read_text(encoding="utf-8")
        self.assertNotIn("VITE_BCENTRAL_TOKEN", codigo_fuente)
        self.assertNotIn("NEXT_PUBLIC_BCENTRAL_TOKEN", codigo_fuente)
        self.assertEqual(
            conectores._VARS_SENSIBLES,
            ("BCCH_API_TOKEN", "BCCH_API_USER", "BCCH_API_PASS"),
        )


class Fase2EndpointsTest(unittest.TestCase):
    def setUp(self):
        self.app = crear_app(demo_activa=True)
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmp = Path(self.tmpdir.name)

    def test_sectorial_regiones_no_disponible_y_disponible_con_filtros(self):
        inexistente = self.tmp / "no-existe-sectorial.json"
        with patch.dict(os.environ, {"CT_SECTORIAL_PATH": str(inexistente)}, clear=False):
            status, _, cuerpo = invocar_asgi(self.app, "GET", "/api/v1/sectorial/regiones")
        self.assertEqual(status, 200)
        vacio = json.loads(cuerpo)
        self.assertFalse(vacio["disponible"])
        self.assertIn("motivo", vacio)
        self.assertIn("fuente_trazabilidad", vacio)

        ruta_sec = self.tmp / "pib-sectorial-16-regiones.json"
        ruta_sec.write_text(
            json.dumps(_construir_sectorial_prueba(), ensure_ascii=False),
            encoding="utf-8",
        )
        with patch.dict(os.environ, {"CT_SECTORIAL_PATH": str(ruta_sec)}, clear=False):
            # Sin filtros
            status, _, cuerpo = invocar_asgi(self.app, "GET", "/api/v1/sectorial/regiones")
            self.assertEqual(status, 200)
            completo = json.loads(cuerpo)
            self.assertTrue(completo["disponible"])
            self.assertEqual(set(completo["por_anio"].keys()), {"2024", "2025"})
            self.assertTrue(completo["fuente_trazabilidad"]["solo_lectura"])

            # Filtrado por año y territorio
            status, _, cuerpo = invocar_asgi(
                self.app,
                "GET",
                "/api/v1/sectorial/regiones",
                params={"anio": 2025, "territorio": "11"},
            )
            self.assertEqual(status, 200)
            filtrado = json.loads(cuerpo)
            self.assertTrue(filtrado["disponible"])
            self.assertEqual(list(filtrado["por_anio"].keys()), ["2025"])
            self.assertEqual(list(filtrado["por_anio"]["2025"]["regiones"].keys()), ["11"])
            self.assertEqual(filtrado["por_anio"]["2025"]["regiones"]["11"]["hhi"], "1420.87")
            self.assertEqual(len(filtrado["por_anio"]["2025"]["ranking_hhi"]), 1)

            # Validación 422 para territorio inválido
            status, _, cuerpo = invocar_asgi(
                self.app,
                "GET",
                "/api/v1/sectorial/regiones",
                params={"territorio": "99"},
            )
            self.assertEqual(status, 422)
            self.assertEqual(json.loads(cuerpo)["codigo"], "filtros_invalidos")

    def test_demografia_poblacion_pendiente_y_cruce_real_con_pib(self):
        inexistente = self.tmp / "no-existe-poblacion.json"
        with patch.dict(os.environ, {"CT_POBLACION_PATH": str(inexistente)}, clear=False):
            status, _, cuerpo = invocar_asgi(self.app, "GET", "/api/v1/demografia/poblacion")
        self.assertEqual(status, 200)
        vacio = json.loads(cuerpo)
        self.assertFalse(vacio["disponible"])
        self.assertIn("motivo", vacio)

        ruta_pob = self.tmp / "poblacion-ine-regiones.json"
        ruta_pob.write_text(
            json.dumps(_construir_poblacion_ine_prueba(), ensure_ascii=False),
            encoding="utf-8",
        )
        ruta_pib_real = RAIZ_REPO / "data" / "published" / "pib-bde-api.json"
        self.assertTrue(ruta_pib_real.is_file(), "Se espera data/published/pib-bde-api.json en el repositorio.")

        with patch.dict(
            os.environ,
            {
                "CT_POBLACION_PATH": str(ruta_pob),
                "CT_LOTE_OFICIAL": str(ruta_pib_real),
            },
            clear=False,
        ):
            status, _, cuerpo = invocar_asgi(
                self.app,
                "GET",
                "/api/v1/demografia/poblacion",
                params={"anio": 2025, "territorio": "11"},
            )
        self.assertEqual(status, 200)
        datos = json.loads(cuerpo)
        self.assertTrue(datos["disponible"])
        self.assertEqual(datos["poblacion"]["unidad"], "personas")
        self.assertEqual(datos["poblacion"]["total_observaciones"], 1)
        self.assertIsNotNone(datos["pib_per_capita"])
        self.assertEqual(len(datos["pib_per_capita"]["series"]), 1)
        fila_aysen = datos["pib_per_capita"]["series"][0]
        self.assertEqual(fila_aysen["territorio"], "11")
        self.assertEqual(fila_aysen["anio"], 2025)
        self.assertIsNotNone(fila_aysen["pib_real_per_capita_clp"])
        self.assertIsNotNone(fila_aysen["pib_nominal_per_capita_clp"])
        self.assertEqual(len(datos["sigma_convergencia"]), 1)
        self.assertEqual(datos["sigma_convergencia"][0]["n_regiones"], 16)
        self.assertTrue(datos["fuente_trazabilidad"]["imputacion_pib_comunal_prohibida"])

    def test_cruces_resumen_y_matriz_dependencia_estatal(self):
        status, _, cuerpo = invocar_asgi(self.app, "GET", "/api/v1/cruces/resumen")
        self.assertEqual(status, 200)
        datos = json.loads(cuerpo)
        self.assertEqual(datos["total_cruces"], 4)
        ids_cruces = [c["id"] for c in datos["cruces"]]
        self.assertEqual(
            ids_cruces,
            [
                "gasto_publico_pib",
                "inversion_publica_pib",
                "programas_beneficiarios_cobertura",
                "costo_administrativo_eficiencia",
            ],
        )

        matriz = datos["matriz_dependencia_estatal"]
        self.assertIn("regla_separacion", matriz)
        self.assertIn("actividad_economica_administracion_publica", matriz)
        self.assertIn("gasto_publico_presupuestario", matriz)
        self.assertIn("empleo_publico", matriz)

        # (a) BCCh CCNN Aysén disponible desde data/raw/bcch-aysen-sectorial-live.json
        adm = matriz["actividad_economica_administracion_publica"]
        self.assertTrue(adm["disponible"])
        self.assertEqual(adm["territorio"], "11")
        self.assertEqual(adm["participacion_pib_nominal_pct"], "16.05")

        # (b) DIPRES CKAN Aysén 2025 disponible
        gasto = matriz["gasto_publico_presupuestario"]
        self.assertTrue(gasto["disponible"])
        self.assertEqual(gasto["gasto_directo_gobierno_central_millones"], "766660.849")
        self.assertEqual(gasto["financiamiento_gore_p31_millones"], "79897.034")
        self.assertIsNotNone(gasto["ratio_gasto_directo_sobre_pib_nominal_pct"])

        # (c) Empleo público explícitamente pendiente (ENE/INE)
        empleo = matriz["empleo_publico"]
        self.assertFalse(empleo["disponible"])
        self.assertEqual(empleo["estado"], "pendiente")
        self.assertIn("ENE", empleo["motivo"])

    def test_laboratorio_consultar_10_pasos_solo_lectura_y_validaciones(self):
        ruta_pib_real = RAIZ_REPO / "data" / "published" / "pib-bde-api.json"
        hash_antes = sha256(ruta_pib_real.read_bytes()).hexdigest()

        payload = {
            "pregunta": "¿Qué tan dependiente del Estado es la economía de Aysén según CCNN y DIPRES?",
            "territorio": "11",
        }
        status1, _, cuerpo1 = invocar_asgi(
            self.app, "POST", "/api/v1/laboratorio/consultar", json_body=payload
        )
        status2, _, cuerpo2 = invocar_asgi(
            self.app, "POST", "/api/v1/laboratorio/consultar", json_body=payload
        )
        self.assertEqual(status1, 200)
        self.assertEqual(status2, 200)
        # Determinismo exacto
        self.assertEqual(cuerpo1, cuerpo2)

        # Solo lectura: el archivo oficial no fue alterado
        hash_despues = sha256(ruta_pib_real.read_bytes()).hexdigest()
        self.assertEqual(hash_antes, hash_despues)

        res = json.loads(cuerpo1)
        for campo in CAMPOS_PROTOCOLO_10:
            self.assertIn(campo, res, f"Falta el paso del protocolo: {campo}")

        self.assertEqual(res["pregunta_formulada"]["eje_tematico"], "dependencia_estatal")
        self.assertEqual(res["pregunta_formulada"]["territorio"]["codigo"], "11")
        self.assertEqual(res["pregunta_formulada"]["modo_ejecucion"], "solo_lectura_determinista")

        for consulta in res["consultas_verificadas"]:
            self.assertEqual(consulta["modo"], "solo_lectura")

        self.assertTrue(res["resultados_reproducibles"]["pib"]["disponible"])
        self.assertEqual(res["resultados_reproducibles"]["pib"]["ultimo_anio"], 2025)
        self.assertFalse(
            res["resultados_reproducibles"]["dependencia_estatal_matriz"]["empleo_publico"]["disponible"]
        )
        self.assertTrue(len(res["tabla_evidencia"]) >= 6)
        self.assertTrue(any("pendiente" in lim.lower() for lim in res["limitaciones"]))

        md = res["dossier_markdown"]
        self.assertIn("# Dossier de Investigación", md)
        self.assertIn("## 5. Tabla de evidencia reproducible", md)
        self.assertIn("## 8. Limitaciones y fuentes pendientes", md)
        self.assertIn("Banco Central de Chile", md)

        # Validaciones 422
        for invalido in (
            {"pregunta": "abc", "territorio": "11"},
            {"pregunta": "     ", "territorio": "11"},
            {"pregunta": "a" * 601, "territorio": "11"},
            {"pregunta": "¿Cómo evoluciona el PIB regional?", "territorio": "99"},
        ):
            with self.subTest(invalido=invalido):
                status, _, cuerpo = invocar_asgi(
                    self.app, "POST", "/api/v1/laboratorio/consultar", json_body=invalido
                )
                self.assertEqual(status, 422)
                self.assertEqual(json.loads(cuerpo)["codigo"], "filtros_invalidos")

    def test_ejecutar_investigacion_clasificacion_ejes_y_cortes_pendientes(self):
        casos = [
            ("¿Cuánto creció el PIB real de Aysén entre 2013 y 2025?", "crecimiento_y_pib"),
            ("¿Cuál es la estructura sectorial, pesca y concentración HHI?", "estructura_y_especializacion"),
            ("¿Cómo evoluciona el PIB per cápita y la σ-convergencia con población INE?", "per_capita_y_convergencia"),
            ("¿Cuál es la dependencia estatal y peso de administración pública?", "dependencia_estatal"),
            ("¿Cómo se ejecuta el presupuesto DIPRES y SINIM por billeteras?", "finanzas_y_billeteras"),
            ("Necesito un panorama integral y diagnóstico territorial de la región", "panorama_integral"),
        ]
        for pregunta, eje_esperado in casos:
            with self.subTest(eje_esperado=eje_esperado):
                out = ejecutar_investigacion(
                    pregunta,
                    territorio="11",
                    ruta_sectorial=self.tmp / "pendiente-sec.json",
                    ruta_poblacion=self.tmp / "pendiente-pob.json",
                    ruta_sinim=self.tmp / "pendiente-sinim.json",
                )
                self.assertEqual(out["pregunta_formulada"]["eje_tematico"], eje_esperado)
                self.assertFalse(out["resultados_reproducibles"]["estructura_sectorial"]["disponible"])
                self.assertFalse(out["resultados_reproducibles"]["demografia_y_per_capita"]["disponible"])
                self.assertTrue(
                    any("pib-sectorial-16-regiones.json" in lim for lim in out["limitaciones"])
                )
                self.assertTrue(
                    any("poblacion-ine-regiones.json" in lim for lim in out["limitaciones"])
                )


if __name__ == "__main__":
    unittest.main()
