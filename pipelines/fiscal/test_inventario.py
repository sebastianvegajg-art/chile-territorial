"""Verificaciones de cobertura y trazabilidad del inventario F01."""

import csv
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


DIRECTORIO = Path(__file__).resolve().parent


def leer_csv(nombre):
    with (DIRECTORIO / nombre).open(encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


class InventarioTest(unittest.TestCase):
    def setUp(self):
        self.matriz = leer_csv("matriz-aysen.csv")
        self.evidencia = leer_csv("evidencia-aysen.csv")

    def test_cobertura_unica_de_tres_billeteras_en_cuatro_ejercicios(self):
        esperados = {
            (billetera, str(ejercicio))
            for billetera in ("sectorial", "regional", "municipal")
            for ejercicio in range(2025, 2029)
        }
        actuales = {(fila["billetera"], fila["ejercicio"]) for fila in self.matriz}
        self.assertEqual(actuales, esperados)
        self.assertEqual(len(actuales), len(self.matriz))

    def test_fuentes_verificadas_tienen_respaldo(self):
        evidencias = {fila["id"]: fila for fila in self.evidencia}
        self.assertEqual(len(evidencias), len(self.evidencia))
        for fila in self.matriz:
            if fila["estado"] != "verificado":
                continue
            referencia = fila["evidencia"]
            if referencia.endswith("*"):
                identificadores = [
                    id_ for id_ in evidencias if id_.startswith(referencia[:-1])
                ]
                self.assertEqual(len(identificadores), 10)
            else:
                self.assertIn(referencia, evidencias)
                self.assertEqual(fila["url"], evidencias[referencia]["url"])
        for fila in self.evidencia:
            self.assertRegex(fila["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(fila["selector"].strip())
            self.assertEqual(date.fromisoformat(fila["consultado"]).isoformat(), fila["consultado"])
            self.assertEqual(urlsplit(fila["url"]).scheme, "https")

    def test_enlaces_municipales_corresponden_a_cada_cut(self):
        esperados = {
            "11101", "11102", "11201", "11202", "11203", "11301", "11302",
            "11303", "11401", "11402",
        }
        actuales = set()
        for fila in self.evidencia:
            if not fila["id"].startswith("sinim-2025-"):
                continue
            cut = fila["id"].rsplit("-", 1)[-1]
            url = urlsplit(fila["url"])
            self.assertEqual(url.hostname, "datos.sinim.gov.cl")
            self.assertEqual(parse_qs(url.query).get("municipio"), [cut])
            actuales.add(cut)
        self.assertEqual(esperados, actuales)

    def test_captura_y_ejercicios_futuros_no_se_tratan_como_ejecucion_verificada(self):
        for fila in self.matriz:
            if fila["ejercicio"] in {"2027", "2028"} or (
                fila["billetera"] == "municipal" and fila["ejercicio"] == "2026"
            ):
                self.assertNotEqual(fila["estado"], "verificado")
                self.assertFalse(fila["evidencia"])
                self.assertTrue(fila["brecha"])


if __name__ == "__main__":
    unittest.main()
