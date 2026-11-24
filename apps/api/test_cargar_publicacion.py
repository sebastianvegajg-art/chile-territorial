import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from apps.api.cargar_publicacion import validar_lote


class CargaPublicacionTest(unittest.TestCase):
    def setUp(self):
        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        self.ruta = Path(directorio.name) / "lote.json"
        self.original = Path(directorio.name) / "origen.html"
        datos = b"<table></table>"
        self.original.write_bytes(datos)
        self.lote = {
            "publicacion": {
                "id": "lote-test",
                "fecha": "2026-01-01T00:00:00Z",
                "estado": "aprobada",
                "fuente": "test",
                "cobertura": {"esperadas": 0, "disponibles": 0},
                "cambios": [],
            },
            "artefactos": [{
                "id": "origen",
                "fuente": "test",
                "url": "https://example.org/origen.html",
                "sha256": hashlib.sha256(datos).hexdigest(),
                "corte": None,
                "extraido_en": "2026-01-01T00:00:00Z",
            }],
            "observaciones": [],
            "procedencias": [],
        }

    def validar(self, originales=None):
        self.ruta.write_text(json.dumps(self.lote), encoding="utf-8")
        return validar_lote(self.ruta, {"origen": self.original} if originales is None else originales)

    def test_valida_archivo_original(self):
        self.assertEqual(self.validar(), self.lote)

    def test_rechaza_huella_y_archivo_faltante(self):
        with self.assertRaisesRegex(ValueError, "identificadores"):
            self.validar({})
        self.original.write_bytes(b"<table>modificada</table>")
        with self.assertRaisesRegex(ValueError, "huella"):
            self.validar()

    def test_rechaza_lote_sintetico_y_fecha_invalida(self):
        self.lote["publicacion"]["estado"] = "prueba"
        with self.assertRaisesRegex(ValueError, "aprobados"):
            self.validar()
        self.lote["publicacion"]["estado"] = "aprobada"
        self.lote["publicacion"]["fecha"] = "2026-01-01"
        with self.assertRaisesRegex(ValueError, "publicacion.fecha"):
            self.validar()
