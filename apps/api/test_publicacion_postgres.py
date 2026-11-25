"""Conformidad de un lote oficial ya cargado en PostgreSQL."""

import csv
import io
import json
import os
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from apps.api.main import crear_app


@unittest.skipUnless(os.getenv("CT_LOTE_OFICIAL"), "Requiere CT_LOTE_OFICIAL y una conexión de lectura.")
class PublicacionPostgresTest(unittest.TestCase):
    def setUp(self):
        self.lote = json.loads(Path(os.environ["CT_LOTE_OFICIAL"]).read_text(encoding="utf-8"))
        self.publicacion = self.lote["publicacion"]
        self.filas = [fila for fila in self.lote["observaciones"] if fila["anio"] >= 2013]
        self.cliente = TestClient(crear_app())
        self.addCleanup(self.cliente.close)

    def test_publicacion_y_catalogo_separados_de_prueba(self):
        respuesta = self.cliente.get("/api/v1/publicaciones")
        self.assertEqual(respuesta.status_code, 200)
        publicaciones = {publicacion["id"]: publicacion for publicacion in respuesta.json()}
        self.assertEqual(publicaciones[self.publicacion["id"]]["cobertura"], self.publicacion["cobertura"])
        self.assertNotIn("prueba-local", publicaciones)
        catalogo = self.cliente.get("/api/v1/territorios")
        self.assertEqual(catalogo.status_code, 200)
        self.assertEqual({territorio["codigo"] for territorio in catalogo.json()}, {"CL", *(f"{i:02}" for i in range(1, 17))})

    def test_valores_csv_paginacion_y_linaje(self):
        for metrica, valoracion in [
            ("nivel", "real"), ("nivel", "nominal"),
            ("crecimiento", "real"), ("participacion", "nominal"),
        ]:
            with self.subTest(metrica=metrica, valoracion=valoracion):
                esperadas = sorted(
                    (fila for fila in self.filas if fila["metrica"] == metrica and fila["valoracion"] == valoracion),
                    key=lambda fila: (fila["anio"], fila["territorio"]),
                )
                parametros = {
                    "anio_desde": min(fila["anio"] for fila in esperadas),
                    "anio_hasta": max(fila["anio"] for fila in esperadas),
                    "metrica": metrica,
                    "valoracion": valoracion,
                    "publicacion": self.publicacion["id"],
                }
                obtenidas = []
                limite = 100
                for offset in range(0, len(esperadas), limite):
                    pagina = self.cliente.get(
                        "/api/v1/pib", params={**parametros, "limite": limite, "pagina": offset // limite + 1}
                    )
                    self.assertEqual(pagina.status_code, 200)
                    self.assertEqual(pagina.headers["X-Publicacion"], self.publicacion["id"])
                    self.assertEqual(pagina.json()["total"], len(esperadas))
                    obtenidas.extend(pagina.json()["datos"])
                self.assertEqual(obtenidas, esperadas)

                archivo = self.cliente.get("/api/v1/pib.csv", params=parametros)
                self.assertEqual(archivo.status_code, 200)
                self.assertEqual(archivo.headers["X-Publicacion"], self.publicacion["id"])
                self.assertEqual(list(csv.DictReader(io.StringIO(archivo.text))), [
                    {campo: str(valor) if valor is not None else "" for campo, valor in fila.items()}
                    for fila in esperadas
                ])

        for procedencia in self.lote["procedencias"]:
            respuesta = self.cliente.get(f"/api/v1/observaciones/{procedencia['observacion']}/procedencia")
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.json(), procedencia)
