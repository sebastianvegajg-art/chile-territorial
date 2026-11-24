"""Controles de caja negra para el corte sintético de la API de PIB."""
import csv
import io
import json
import os
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen


BASE = os.getenv("CT_AUDIT_API_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
CORTE = "prueba-local"
REGIONES = {f"{numero:02}" for numero in range(1, 17)}
CAMPOS = (
    "id", "territorio", "anio", "metrica", "valoracion", "valor", "unidad",
    "anio_referencia", "estado", "clase", "publicacion",
)


def consultar(ruta, **parametros):
    query = urlencode(parametros, doseq=True)
    url = f"{BASE}/{ruta}"
    if query:
        url = f"{url}?{query}"
    try:
        respuesta = urlopen(url, timeout=5)
    except HTTPError as error:
        respuesta = error
    with respuesta:
        cuerpo = respuesta.read().decode("utf-8")
        if respuesta.headers.get_content_type() == "application/json":
            cuerpo = json.loads(cuerpo)
        return respuesta.status, respuesta.headers, cuerpo


class AuditoriaPIB(unittest.TestCase):
    def pib(self, ruta="pib", **cambios):
        filtros = {"anio_desde": 2024, "anio_hasta": 2025, "valoracion": "real"}
        filtros.update(cambios)
        return consultar(ruta, **filtros)

    def test_cobertura_regional_y_corte_sintetico(self):
        estado, _, territorios = consultar("territorios")
        self.assertEqual(estado, 200)
        regiones = [fila["codigo"] for fila in territorios if fila["nivel"] == "regional"]
        self.assertEqual(len(regiones), 16)
        self.assertEqual(set(regiones), REGIONES)
        self.assertEqual([fila["codigo"] for fila in territorios if fila["nivel"] == "nacional"], ["CL"])
        estado, _, publicaciones = consultar("publicaciones")
        self.assertEqual(estado, 200)
        self.assertEqual([(fila["id"], fila["estado"]) for fila in publicaciones], [(CORTE, "prueba")])
        estado, cabeceras, cuerpo = self.pib()
        self.assertEqual(estado, 200)
        self.assertEqual(cuerpo["publicacion"], CORTE)
        self.assertEqual(cabeceras["X-Publicacion"], CORTE)
        filas = cuerpo["datos"]
        self.assertEqual(cuerpo["total"], 34)
        self.assertEqual(len(filas), 34)
        self.assertEqual({(fila["anio"], fila["territorio"]) for fila in filas},
                         {(anio, codigo) for anio in (2024, 2025) for codigo in REGIONES | {"CL"}})
        self.assertEqual(len({fila["id"] for fila in filas}), 34)
        self.assertTrue(all(fila["clase"] == "prueba" and fila["publicacion"] == CORTE
                            and isinstance(fila["valor"], str) for fila in filas))

    def test_paginacion_y_csv_conservan_corte_orden_y_valores(self):
        filtros = {"territorios": ["11", "05", "CL"], "publicacion": CORTE}
        _, _, completa = self.pib(**filtros)
        pagina_uno = self.pib(limite=3, **filtros)
        pagina_dos = self.pib(limite=3, pagina=2, **filtros)
        estado, cabeceras, contenido = self.pib("pib.csv", **filtros)
        self.assertEqual(estado, 200)
        lector = csv.DictReader(io.StringIO(contenido))
        self.assertEqual(tuple(lector.fieldnames), CAMPOS)
        esperado = [
            {campo: "" if fila[campo] is None else str(fila[campo]) for campo in CAMPOS}
            for fila in completa["datos"]
        ]
        self.assertEqual(list(lector), esperado)
        self.assertEqual(cabeceras["X-Publicacion"], CORTE)
        self.assertEqual([pagina_uno[0], pagina_dos[0]], [200, 200])
        self.assertEqual([pagina_uno[1]["X-Publicacion"], pagina_dos[1]["X-Publicacion"]], [CORTE, CORTE])
        self.assertEqual(pagina_uno[2]["datos"] + pagina_dos[2]["datos"], completa["datos"])
        coordenadas = [(fila["anio"], fila["territorio"]) for fila in completa["datos"]]
        self.assertEqual(coordenadas, sorted(coordenadas))

    def test_faltante_y_procedencia_sintetica(self):
        filtros = {"anio_desde": 2013, "anio_hasta": 2013, "metrica": "crecimiento",
                   "territorios": ["11"]}
        estado, _, cuerpo = self.pib(**filtros)
        self.assertEqual(estado, 200)
        fila, = cuerpo["datos"]
        self.assertEqual((fila["valor"], fila["estado"], fila["clase"]),
                         (None, "faltante", "no_disponible"))
        estado, _, texto = self.pib("pib.csv", **filtros)
        self.assertEqual(estado, 200)
        self.assertEqual(next(csv.DictReader(io.StringIO(texto)))["valor"], "")
        estado, _, origen = consultar(f"observaciones/{fila['id']}/procedencia")
        self.assertEqual(estado, 200)
        self.assertEqual(origen["observacion"], fila["id"])
        self.assertEqual(origen["publicacion"], CORTE)
        self.assertIsNone(origen["serie_bde"])
        self.assertTrue(origen["motivo"])

    def test_participacion_regional(self):
        estado, _, cuerpo = self.pib(metrica="participacion", valoracion="nominal")
        self.assertEqual(estado, 200)
        self.assertEqual(cuerpo["total"], 32)
        self.assertEqual({fila["territorio"] for fila in cuerpo["datos"]}, REGIONES)
        self.assertTrue(all(fila["unidad"] == "%" for fila in cuerpo["datos"]))

    def test_filtros_invalidos_y_publicacion_inexistente(self):
        casos = (
            {"anio_desde": 2025, "anio_hasta": 2024},
            {"anio_hasta": 2124},
            {"territorios": ["11", "11"]},
            {"territorios": ["17"]},
            {"valoracion": "nominal", "metrica": "crecimiento"},
            {"valoracion": "nominal", "metrica": "participacion", "territorios": ["CL"]},
            {"limite": 501},
        )
        for filtros in casos:
            with self.subTest(filtros=filtros):
                estado, _, cuerpo = self.pib(**filtros)
                self.assertEqual(estado, 422)
                self.assertEqual(set(cuerpo), {"codigo", "mensaje"})
        self.assertEqual(self.pib(publicacion="inexistente")[0], 404)
        self.assertEqual(consultar("observaciones/inexistente/procedencia")[0], 404)

    def test_conjunto_vacio_retiene_corte(self):
        filtros = {"anio_desde": 2090, "anio_hasta": 2090}
        estado, cabeceras, cuerpo = self.pib(**filtros)
        self.assertEqual(estado, 200)
        self.assertEqual(cabeceras["X-Publicacion"], CORTE)
        self.assertEqual((cuerpo["total"], cuerpo["datos"]), (0, []))
        estado, cabeceras, contenido = self.pib("pib.csv", **filtros)
        self.assertEqual(estado, 200)
        self.assertEqual(cabeceras["X-Publicacion"], CORTE)
        lector = csv.DictReader(io.StringIO(contenido))
        self.assertEqual(tuple(lector.fieldnames), CAMPOS)
        self.assertEqual(list(lector), [])


if __name__ == "__main__":
    unittest.main()
