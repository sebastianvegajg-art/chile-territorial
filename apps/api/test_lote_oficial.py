"""Pruebas unitarias para el modo de lectura desde lote oficial local."""

from copy import deepcopy
import csv
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.api.lote_oficial import CAMPOS, LoteOficial, validar_lote_oficial
from apps.api.main import crear_app


CORTE = "bcch-oficial-test-2026"
CONTRATO_PRUEBA = Path(__file__).resolve().parents[2] / "contracts/pib-prueba.json"


def construir_lote_oficial():
    obs_2012_11 = f"{CORTE}.11.2012.nivel.real"
    obs_2013_11_real = f"{CORTE}.11.2013.nivel.real"
    obs_2013_cl_real = f"{CORTE}.CL.2013.nivel.real"
    obs_2024_05_real = f"{CORTE}.05.2024.nivel.real"
    obs_2024_11_real = f"{CORTE}.11.2024.nivel.real"
    obs_2024_cl_real = f"{CORTE}.CL.2024.nivel.real"
    obs_2013_11_crec = f"{CORTE}.11.2013.crecimiento.real"
    obs_2013_cl_crec = f"{CORTE}.CL.2013.crecimiento.real"
    obs_2024_05_nom = f"{CORTE}.05.2024.nivel.nominal"
    obs_2024_11_nom = f"{CORTE}.11.2024.nivel.nominal"
    obs_2024_cl_nom = f"{CORTE}.CL.2024.nivel.nominal"
    obs_2024_05_part = f"{CORTE}.05.2024.participacion.nominal"
    obs_2024_11_part = f"{CORTE}.11.2024.participacion.nominal"

    observaciones = [
        # Auxiliar 2012: válido para linaje, excluido de /pib y de cobertura desde 2013.
        {
            "id": obs_2012_11,
            "territorio": "11",
            "anio": 2012,
            "metrica": "nivel",
            "valoracion": "real",
            "valor": "1000000",
            "unidad": "millones CLP",
            "anio_referencia": 2018,
            "estado": "informado",
            "clase": "oficial",
            "publicacion": CORTE,
        },
        # Desordenadas intencionalmente para verificar orden estable (anio, territorio).
        {
            "id": obs_2024_cl_real,
            "territorio": "CL",
            "anio": 2024,
            "metrica": "nivel",
            "valoracion": "real",
            "valor": "210000000",
            "unidad": "millones CLP",
            "anio_referencia": 2018,
            "estado": "preliminar",
            "clase": "oficial",
            "publicacion": CORTE,
        },
        {
            "id": obs_2024_11_real,
            "territorio": "11",
            "anio": 2024,
            "metrica": "nivel",
            "valoracion": "real",
            "valor": "1350000",
            "unidad": "millones CLP",
            "anio_referencia": 2018,
            "estado": "preliminar",
            "clase": "oficial",
            "publicacion": CORTE,
        },
        {
            "id": obs_2024_05_real,
            "territorio": "05",
            "anio": 2024,
            "metrica": "nivel",
            "valoracion": "real",
            "valor": "19800000",
            "unidad": "millones CLP",
            "anio_referencia": 2018,
            "estado": "preliminar",
            "clase": "oficial",
            "publicacion": CORTE,
        },
        {
            "id": obs_2013_cl_real,
            "territorio": "CL",
            "anio": 2013,
            "metrica": "nivel",
            "valoracion": "real",
            "valor": "169864000",
            "unidad": "millones CLP",
            "anio_referencia": 2018,
            "estado": "informado",
            "clase": "oficial",
            "publicacion": CORTE,
        },
        {
            "id": obs_2013_11_real,
            "territorio": "11",
            "anio": 2013,
            "metrica": "nivel",
            "valoracion": "real",
            "valor": "1050000",
            "unidad": "millones CLP",
            "anio_referencia": 2018,
            "estado": "informado",
            "clase": "oficial",
            "publicacion": CORTE,
        },
        {
            "id": obs_2013_cl_crec,
            "territorio": "CL",
            "anio": 2013,
            "metrica": "crecimiento",
            "valoracion": "real",
            "valor": None,
            "unidad": "%",
            "anio_referencia": 2018,
            "estado": "faltante",
            "clase": "no_disponible",
            "publicacion": CORTE,
        },
        {
            "id": obs_2013_11_crec,
            "territorio": "11",
            "anio": 2013,
            "metrica": "crecimiento",
            "valoracion": "real",
            "valor": "5.00",
            "unidad": "%",
            "anio_referencia": 2018,
            "estado": "informado",
            "clase": "oficial",
            "publicacion": CORTE,
        },
        {
            "id": obs_2024_cl_nom,
            "territorio": "CL",
            "anio": 2024,
            "metrica": "nivel",
            "valoracion": "nominal",
            "valor": "300000000",
            "unidad": "millones CLP",
            "anio_referencia": None,
            "estado": "preliminar",
            "clase": "oficial",
            "publicacion": CORTE,
        },
        {
            "id": obs_2024_11_nom,
            "territorio": "11",
            "anio": 2024,
            "metrica": "nivel",
            "valoracion": "nominal",
            "valor": "1800000",
            "unidad": "millones CLP",
            "anio_referencia": None,
            "estado": "preliminar",
            "clase": "oficial",
            "publicacion": CORTE,
        },
        {
            "id": obs_2024_05_nom,
            "territorio": "05",
            "anio": 2024,
            "metrica": "nivel",
            "valoracion": "nominal",
            "valor": "27000000",
            "unidad": "millones CLP",
            "anio_referencia": None,
            "estado": "preliminar",
            "clase": "oficial",
            "publicacion": CORTE,
        },
        {
            "id": obs_2024_11_part,
            "territorio": "11",
            "anio": 2024,
            "metrica": "participacion",
            "valoracion": "nominal",
            "valor": "0.60",
            "unidad": "%",
            "anio_referencia": None,
            "estado": "preliminar",
            "clase": "oficial",
            "publicacion": CORTE,
        },
        {
            "id": obs_2024_05_part,
            "territorio": "05",
            "anio": 2024,
            "metrica": "participacion",
            "valoracion": "nominal",
            "valor": "9.00",
            "unidad": "%",
            "anio_referencia": None,
            "estado": "preliminar",
            "clase": "oficial",
            "publicacion": CORTE,
        },
    ]

    procedencias = [
        {
            "observacion": obs_2012_11,
            "publicacion": CORTE,
            "serie_bde": "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.T",
            "artefacto": "bde-pib-real",
            "selector": "#grilla · Aysén · 2012",
            "formula_version": None,
            "insumos": [],
            "motivo": None,
        },
        {
            "observacion": obs_2013_11_real,
            "publicacion": CORTE,
            "serie_bde": "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.T",
            "artefacto": "bde-pib-real",
            "selector": "#grilla · Aysén · 2013",
            "formula_version": None,
            "insumos": [],
            "motivo": None,
        },
        {
            "observacion": obs_2013_cl_real,
            "publicacion": CORTE,
            "serie_bde": "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.CL.0.T",
            "artefacto": "bde-pib-real",
            "selector": "#grilla · Chile · 2013",
            "formula_version": None,
            "insumos": [],
            "motivo": None,
        },
        {
            "observacion": obs_2024_05_real,
            "publicacion": CORTE,
            "serie_bde": "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.05.0.T",
            "artefacto": "bde-pib-real",
            "selector": "#grilla · Valparaíso · 2024",
            "formula_version": None,
            "insumos": [],
            "motivo": None,
        },
        {
            "observacion": obs_2024_11_real,
            "publicacion": CORTE,
            "serie_bde": "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.T",
            "artefacto": "bde-pib-real",
            "selector": "#grilla · Aysén · 2024",
            "formula_version": None,
            "insumos": [],
            "motivo": None,
        },
        {
            "observacion": obs_2024_cl_real,
            "publicacion": CORTE,
            "serie_bde": "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.CL.0.T",
            "artefacto": "bde-pib-real",
            "selector": "#grilla · Chile · 2024",
            "formula_version": None,
            "insumos": [],
            "motivo": None,
        },
        {
            "observacion": obs_2013_11_crec,
            "publicacion": CORTE,
            "serie_bde": None,
            "artefacto": None,
            "selector": None,
            "formula_version": "crecimiento-real-v1",
            "insumos": [obs_2012_11, obs_2013_11_real],
            "motivo": None,
        },
        {
            "observacion": obs_2013_cl_crec,
            "publicacion": CORTE,
            "serie_bde": None,
            "artefacto": None,
            "selector": None,
            "formula_version": "crecimiento-real-v1",
            "insumos": [obs_2013_cl_real],
            "motivo": "Sin nivel real comparable de 2012 para Chile.",
        },
        {
            "observacion": obs_2024_05_nom,
            "publicacion": CORTE,
            "serie_bde": "F035.PIB.FLU.N.CLP.0.Z.Z.Z.05.0.T",
            "artefacto": "bde-pib-nominal",
            "selector": "#grilla · Valparaíso · 2024",
            "formula_version": None,
            "insumos": [],
            "motivo": None,
        },
        {
            "observacion": obs_2024_11_nom,
            "publicacion": CORTE,
            "serie_bde": "F035.PIB.FLU.N.CLP.0.Z.Z.Z.11.0.T",
            "artefacto": "bde-pib-nominal",
            "selector": "#grilla · Aysén · 2024",
            "formula_version": None,
            "insumos": [],
            "motivo": None,
        },
        {
            "observacion": obs_2024_cl_nom,
            "publicacion": CORTE,
            "serie_bde": "F035.PIB.FLU.N.CLP.0.Z.Z.Z.CL.0.T",
            "artefacto": "bde-pib-nominal",
            "selector": "#grilla · Chile · 2024",
            "formula_version": None,
            "insumos": [],
            "motivo": None,
        },
        {
            "observacion": obs_2024_05_part,
            "publicacion": CORTE,
            "serie_bde": None,
            "artefacto": None,
            "selector": None,
            "formula_version": "participacion-nominal-v1",
            "insumos": [obs_2024_05_nom, obs_2024_cl_nom],
            "motivo": None,
        },
        {
            "observacion": obs_2024_11_part,
            "publicacion": CORTE,
            "serie_bde": None,
            "artefacto": None,
            "selector": None,
            "formula_version": "participacion-nominal-v1",
            "insumos": [obs_2024_11_nom, obs_2024_cl_nom],
            "motivo": None,
        },
    ]

    publicables = [fila for fila in observaciones if fila["anio"] >= 2013]
    return {
        "publicacion": {
            "id": CORTE,
            "fecha": "2026-11-24T12:00:00Z",
            "estado": "aprobada",
            "fuente": "BCCh-BDE",
            "cobertura": {
                "esperadas": len(publicables),
                "disponibles": sum(fila["valor"] is not None for fila in publicables),
            },
            "cambios": ["Corte oficial para pruebas unitarias."],
        },
        "artefactos": [
            {
                "id": "bde-pib-real",
                "fuente": "BCCh-BDE",
                "url": "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_CCNN/MN_CCNN76/CCNN2018_PIB_REGIONAL",
                "sha256": "a" * 64,
                "corte": "2026-03-18",
                "extraido_en": "2026-11-24T12:00:00Z",
            },
            {
                "id": "bde-pib-nominal",
                "fuente": "BCCh-BDE",
                "url": "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_CCNN/MN_CCNN76/CCNN2018_PIB_REGIONAL_N",
                "sha256": "b" * 64,
                "corte": "2026-03-18",
                "extraido_en": "2026-11-24T12:00:00Z",
            },
        ],
        "observaciones": observaciones,
        "procedencias": procedencias,
    }


class ValidacionLoteOficialTest(unittest.TestCase):
    def setUp(self):
        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        self.directorio = Path(directorio.name)
        self.lote = construir_lote_oficial()
        self.ruta = self.directorio / "lote-oficial.json"
        self.ruta.write_text(json.dumps(self.lote), encoding="utf-8")

    def escribir(self, nombre, contenido):
        ruta = self.directorio / nombre
        ruta.write_text(json.dumps(contenido), encoding="utf-8")
        return ruta

    def test_carga_lote_oficial_y_excluye_auxiliar_2012_de_consultas(self):
        repo = LoteOficial.desde_archivo(self.ruta)
        territorios = repo.territorios()
        self.assertEqual(len(territorios), 17)
        self.assertEqual(
            [t["codigo"] for t in territorios],
            [*(f"{n:02}" for n in range(1, 17)), "CL"],
        )
        self.assertEqual(territorios[5]["nombre"], "Libertador General Bernardo O’Higgins")
        self.assertEqual(territorios[-1], {
            "codigo": "CL",
            "nombre": "Chile",
            "nivel": "nacional",
            "vigente_desde": None,
            "vigente_hasta": None,
        })

        publicaciones = repo.publicaciones()
        self.assertEqual(len(publicaciones), 1)
        self.assertEqual(publicaciones[0]["id"], CORTE)
        self.assertEqual(publicaciones[0]["estado"], "aprobada")

        filas = repo.observaciones(CORTE, ["CL", "11", "05"], 2012, 2025, "nivel", "real")
        self.assertEqual(
            [(f["anio"], f["territorio"]) for f in filas],
            [(2013, "11"), (2013, "CL"), (2024, "05"), (2024, "11"), (2024, "CL")],
        )
        self.assertEqual(repo.observaciones("otro-corte", ["CL"], 2013, 2025, "nivel", "real"), [])

        # La observación auxiliar de 2012 conserva su procedencia para linaje.
        proc_2012 = repo.procedencia(f"{CORTE}.11.2012.nivel.real")
        self.assertIsNotNone(proc_2012)
        self.assertEqual(proc_2012["artefacto"], "bde-pib-real")
        self.assertIsNone(repo.procedencia("inexistente"))

    def test_rechaza_estado_prueba_y_fixture_sintetico(self):
        invalido = deepcopy(self.lote)
        invalido["publicacion"]["estado"] = "prueba"
        ruta = self.escribir("estado-prueba.json", invalido)
        with self.assertRaisesRegex(ValueError, "aprobada"):
            crear_app(lote_oficial=ruta)

        with self.assertRaisesRegex(ValueError, "aprobada"):
            crear_app(lote_oficial=CONTRATO_PRUEBA)

    def test_rechaza_observacion_con_clase_prueba_estimacion_o_estado_error(self):
        con_prueba = deepcopy(self.lote)
        con_prueba["observaciones"][1]["clase"] = "prueba"
        with self.assertRaisesRegex(ValueError, "prueba"):
            crear_app(lote_oficial=self.escribir("obs-prueba.json", con_prueba))

        con_estimacion = deepcopy(self.lote)
        con_estimacion["observaciones"][1]["clase"] = "estimacion"
        with self.assertRaisesRegex(ValueError, "estimacion"):
            crear_app(lote_oficial=self.escribir("obs-estimacion.json", con_estimacion))

        con_error = deepcopy(self.lote)
        objetivo = con_error["observaciones"][6]  # fila faltante nula
        objetivo["estado"] = "error"
        with self.assertRaisesRegex(ValueError, "error"):
            crear_app(lote_oficial=self.escribir("obs-error.json", con_error))

    def test_rechaza_incumplimiento_contrato_cobertura_y_rutas_invalidas(self):
        sin_fecha_valida = deepcopy(self.lote)
        sin_fecha_valida["publicacion"]["fecha"] = "2026-11-24"
        with self.assertRaisesRegex(ValueError, "publicacion.fecha"):
            validar_lote_oficial(sin_fecha_valida)

        sin_procedencia = deepcopy(self.lote)
        sin_procedencia["procedencias"].pop()
        with self.assertRaisesRegex(ValueError, "procedencia"):
            validar_lote_oficial(sin_procedencia)

        cobertura_incorrecta = deepcopy(self.lote)
        cobertura_incorrecta["publicacion"]["cobertura"]["disponibles"] += 1
        with self.assertRaisesRegex(ValueError, "cobertura"):
            validar_lote_oficial(cobertura_incorrecta)

        with self.assertRaisesRegex(ValueError, "vacía"):
            crear_app(lote_oficial="")
        with self.assertRaisesRegex(ValueError, "archivo"):
            crear_app(lote_oficial=self.directorio)
        with self.assertRaisesRegex(ValueError, "archivo"):
            crear_app(lote_oficial=self.directorio / "no-existe.json")

        roto = self.directorio / "roto.json"
        roto.write_text("{invalido", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "leer el lote oficial"):
            crear_app(lote_oficial=roto)

    def test_prioridad_entre_demo_lote_oficial_y_postgres(self):
        ruta_invalida = self.directorio / "inexistente.json"

        # 1. demo_activa=True siempre tiene prioridad sobre lote_oficial y CT_LOTE_OFICIAL.
        with patch.dict(os.environ, {"CT_LOTE_OFICIAL": str(ruta_invalida)}, clear=False):
            app_demo = crear_app(demo_activa=True, lote_oficial=ruta_invalida)
            self.assertIsNotNone(app_demo)

        # 2. DATABASE_URL tiene prioridad sobre la variable de entorno CT_LOTE_OFICIAL cuando lote_oficial=None.
        with patch.dict(
            os.environ,
            {"DATABASE_URL": "postgresql://ejemplo/db", "CT_LOTE_OFICIAL": str(ruta_invalida)},
            clear=False,
        ):
            app_pg = crear_app()
            self.assertIsNotNone(app_pg)
            # Pero pasar lote_oficial explícitamente sí carga y valida el archivo.
            with self.assertRaisesRegex(ValueError, "archivo"):
                crear_app(lote_oficial=ruta_invalida)

        # 3. Sin DATABASE_URL y sin demo, CT_LOTE_OFICIAL activa validación inmediata al iniciar.
        env_sin_db = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
        env_sin_db["CT_LOTE_OFICIAL"] = str(ruta_invalida)
        with patch.dict(os.environ, env_sin_db, clear=True):
            with self.assertRaisesRegex(ValueError, "archivo"):
                crear_app()
            env_sin_db["CT_LOTE_OFICIAL"] = str(self.ruta)
            with patch.dict(os.environ, env_sin_db, clear=True):
                self.assertIsNotNone(crear_app())


class ApiLoteOficialTest(unittest.TestCase):
    def setUp(self):
        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        self.lote = construir_lote_oficial()
        self.ruta = Path(directorio.name) / "lote-oficial.json"
        self.ruta.write_text(json.dumps(self.lote), encoding="utf-8")
        self.client = TestClient(crear_app(lote_oficial=self.ruta))
        self.addCleanup(self.client.close)

    def test_cinco_endpoints_csv_paginacion_y_cabecera_x_publicacion(self):
        # 1. /territorios
        r_terr = self.client.get("/api/v1/territorios")
        self.assertEqual(r_terr.status_code, 200)
        territorios = r_terr.json()
        self.assertEqual(len(territorios), 17)
        self.assertEqual(
            [t["codigo"] for t in territorios],
            [*(f"{n:02}" for n in range(1, 17)), "CL"],
        )

        # 2. /publicaciones
        r_pub = self.client.get("/api/v1/publicaciones")
        self.assertEqual(r_pub.status_code, 200)
        publicaciones = r_pub.json()
        self.assertEqual(publicaciones, [self.lote["publicacion"]])
        self.assertNotIn("prueba-local", {p["id"] for p in publicaciones})

        # 3. /pib con paginación y orden estable (anio, territorio)
        filtros = {"anio_desde": 2013, "anio_hasta": 2024, "valoracion": "real", "metrica": "nivel"}
        p1 = self.client.get("/api/v1/pib", params={**filtros, "limite": 2, "pagina": 1})
        p2 = self.client.get("/api/v1/pib", params={**filtros, "limite": 2, "pagina": 2})
        p3 = self.client.get("/api/v1/pib", params={**filtros, "limite": 2, "pagina": 3})
        for pagina in (p1, p2, p3):
            self.assertEqual(pagina.status_code, 200)
            self.assertEqual(pagina.headers["X-Publicacion"], CORTE)
            self.assertEqual(pagina.json()["publicacion"], CORTE)
            self.assertEqual(pagina.json()["total"], 5)

        todas = p1.json()["datos"] + p2.json()["datos"] + p3.json()["datos"]
        self.assertEqual(
            [(f["anio"], f["territorio"]) for f in todas],
            [(2013, "11"), (2013, "CL"), (2024, "05"), (2024, "11"), (2024, "CL")],
        )
        self.assertTrue(all(f["clase"] == "oficial" and f["publicacion"] == CORTE for f in todas))

        # Crecimiento real con valor calculado oficial y faltante explícito.
        r_crec = self.client.get(
            "/api/v1/pib",
            params={"anio_desde": 2013, "anio_hasta": 2013, "valoracion": "real", "metrica": "crecimiento"},
        )
        self.assertEqual(r_crec.status_code, 200)
        self.assertEqual(r_crec.headers["X-Publicacion"], CORTE)
        crec_datos = r_crec.json()["datos"]
        self.assertEqual(len(crec_datos), 2)
        self.assertEqual((crec_datos[0]["territorio"], crec_datos[0]["valor"], crec_datos[0]["clase"]), ("11", "5.00", "oficial"))
        self.assertEqual((crec_datos[1]["territorio"], crec_datos[1]["valor"], crec_datos[1]["estado"], crec_datos[1]["clase"]), ("CL", None, "faltante", "no_disponible"))

        # Participación nominal regional.
        r_part = self.client.get(
            "/api/v1/pib",
            params={"anio_desde": 2024, "anio_hasta": 2024, "valoracion": "nominal", "metrica": "participacion"},
        )
        self.assertEqual(r_part.status_code, 200)
        self.assertEqual([f["territorio"] for f in r_part.json()["datos"]], ["05", "11"])

        # 4. /pib.csv completo sin paginación y conservando celdas vacías para nulos
        r_csv = self.client.get(
            "/api/v1/pib.csv",
            params={"anio_desde": 2013, "anio_hasta": 2013, "valoracion": "real", "metrica": "crecimiento"},
        )
        self.assertEqual(r_csv.status_code, 200)
        self.assertEqual(r_csv.headers["X-Publicacion"], CORTE)
        lector = csv.DictReader(io.StringIO(r_csv.text))
        self.assertEqual(tuple(lector.fieldnames), CAMPOS)
        filas_csv = list(lector)
        self.assertEqual(len(filas_csv), 2)
        self.assertEqual(filas_csv[0]["valor"], "5.00")
        self.assertEqual(filas_csv[1]["valor"], "")
        self.assertEqual(filas_csv[1]["publicacion"], CORTE)

        # 5. /observaciones/{id}/procedencia para nivel oficial, derivada, faltante y auxiliar 2012
        for proc in self.lote["procedencias"]:
            r_proc = self.client.get(f"/api/v1/observaciones/{proc['observacion']}/procedencia")
            self.assertEqual(r_proc.status_code, 200)
            self.assertEqual(r_proc.json(), proc)

    def test_consulta_vacia_retiene_cabecera_x_publicacion(self):
        filtros = {"anio_desde": 2090, "anio_hasta": 2090, "valoracion": "real"}
        r_json = self.client.get("/api/v1/pib", params=filtros)
        self.assertEqual(r_json.status_code, 200)
        self.assertEqual(r_json.headers["X-Publicacion"], CORTE)
        self.assertEqual((r_json.json()["total"], r_json.json()["datos"]), (0, []))

        r_csv = self.client.get("/api/v1/pib.csv", params=filtros)
        self.assertEqual(r_csv.status_code, 200)
        self.assertEqual(r_csv.headers["X-Publicacion"], CORTE)
        lector = csv.DictReader(io.StringIO(r_csv.text))
        self.assertEqual(tuple(lector.fieldnames), CAMPOS)
        self.assertEqual(list(lector), [])

    def test_filtros_invalidos_422_y_corte_inexistente_404(self):
        base = {"anio_desde": 2013, "anio_hasta": 2024, "valoracion": "real"}
        casos_422 = (
            {"anio_desde": 2025, "anio_hasta": 2024},
            {"anio_desde": 2013, "anio_hasta": 2113},
            {"anio_desde": 2012},
            {"territorios": ["11", "11"]},
            {"territorios": ["17"]},
            {"valoracion": "nominal", "metrica": "crecimiento"},
            {"valoracion": "real", "metrica": "participacion"},
            {"valoracion": "nominal", "metrica": "participacion", "territorios": ["CL"]},
            {"limite": 501},
            {"pagina": 0},
        )
        for cambios in casos_422:
            with self.subTest(cambios=cambios):
                r = self.client.get("/api/v1/pib", params={**base, **cambios})
                self.assertEqual(r.status_code, 422)
                self.assertEqual(r.json()["codigo"], "filtros_invalidos")

        for corte_invalido in ("prueba-local", "corte-inexistente"):
            with self.subTest(publicacion=corte_invalido):
                r_pib = self.client.get("/api/v1/pib", params={**base, "publicacion": corte_invalido})
                self.assertEqual(r_pib.status_code, 404)
                self.assertEqual(r_pib.json()["codigo"], "no_encontrado")
                r_csv = self.client.get("/api/v1/pib.csv", params={**base, "publicacion": corte_invalido})
                self.assertEqual(r_csv.status_code, 404)
                self.assertEqual(r_csv.json()["codigo"], "no_encontrado")

        r_proc = self.client.get("/api/v1/observaciones/observacion-inexistente/procedencia")
        self.assertEqual(r_proc.status_code, 404)
        self.assertEqual(r_proc.json()["codigo"], "no_encontrado")

    def test_variable_entorno_ct_lote_oficial_sin_database_url(self):
        env = {k: v for k, v in os.environ.items() if k not in {"DATABASE_URL", "CT_MODO"}}
        env["CT_LOTE_OFICIAL"] = str(self.ruta)
        with patch.dict(os.environ, env, clear=True):
            cliente = TestClient(crear_app())
            self.addCleanup(cliente.close)
            r_pub = cliente.get("/api/v1/publicaciones")
            self.assertEqual(r_pub.status_code, 200)
            self.assertEqual(r_pub.json()[0]["id"], CORTE)
            r_pib = cliente.get("/api/v1/pib", params={"anio_desde": 2024, "anio_hasta": 2024, "valoracion": "real"})
            self.assertEqual(r_pib.status_code, 200)
            self.assertEqual(r_pib.headers["X-Publicacion"], CORTE)
            self.assertEqual(r_pib.json()["total"], 3)


if __name__ == "__main__":
    unittest.main()
