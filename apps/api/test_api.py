import csv
import io
import unittest

from fastapi.testclient import TestClient

from apps.api.main import crear_app


class ApiPibTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(crear_app(demo_activa=True))
        self.params = {"anio_desde": 2025, "anio_hasta": 2025, "valoracion": "real"}

    def test_corte_csv_y_procedencia(self):
        r = self.client.get("/api/v1/pib", params={**self.params, "limite": 2})
        self.assertEqual(r.status_code, 200)
        page = r.json()
        self.assertEqual(page["total"], 17)
        self.assertEqual(len(page["datos"]), 2)
        cut = r.headers["X-Publicacion"]
        export = self.client.get("/api/v1/pib.csv", params={**self.params, "publicacion": cut})
        self.assertEqual(export.headers["X-Publicacion"], cut)
        records = list(csv.DictReader(io.StringIO(export.text)))
        self.assertEqual(len(records), 17)
        self.assertEqual(records[0]["valor"], page["datos"][0]["valor"])
        row_id = page["datos"][0]["id"]
        source = self.client.get(f"/api/v1/observaciones/{row_id}/procedencia")
        self.assertEqual(source.json()["publicacion"], cut)
        self.assertEqual(page["datos"][0]["clase"], "prueba")

    def test_faltante_explicito(self):
        response = self.client.get("/api/v1/pib", params={
            **self.params, "anio_desde": 2013, "anio_hasta": 2013,
            "territorios": "11", "metrica": "crecimiento",
        })
        self.assertEqual(response.status_code, 200)
        row = response.json()["datos"][0]
        self.assertIsNone(row["valor"])
        self.assertEqual(row["clase"], "no_disponible")

    def test_filtros_invalidos(self):
        for overrides in ({"territorios": ["11", "11"]}, {"anio_desde": 2026},
                          {"metrica": "participacion"}, {"limite": 501}):
            with self.subTest(overrides=overrides):
                result = self.client.get("/api/v1/pib", params={**self.params, **overrides})
                self.assertEqual(result.status_code, 422)
                self.assertEqual(result.json()["codigo"], "filtros_invalidos")

    def test_corte_inexistente(self):
        result = self.client.get("/api/v1/pib", params={**self.params, "publicacion": "otro"})
        self.assertEqual(result.status_code, 404)
