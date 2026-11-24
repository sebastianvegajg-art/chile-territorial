"""Pruebas de consistencia del inventario oficial de inversión pública."""

from __future__ import annotations

import csv
import unittest
from pathlib import Path
from urllib.parse import urlsplit

DIRECTORIO = Path(__file__).resolve().parent

COLUMNAS_ESPERADAS = [
    "id",
    "fuente",
    "organismo",
    "billetera",
    "etapa_contable",
    "llave_primaria",
    "llave_territorial",
    "acceso",
    "periodicidad",
    "limite_metodologico",
    "url_oficial",
]

ETAPAS_PERMITIDAS = {
    "planificacion",
    "programacion_y_seguimiento",
    "evaluacion_ex_ante",
    "contratacion_obra",
    "contratacion_ocds",
    "ejecucion_presupuestaria_contraste",
    "inicial_vigente_devengo",
}

BILLETERAS_PERMITIDAS = {"sectorial", "regional", "municipal"}


def leer_fuentes():
    ruta = DIRECTORIO / "fuentes-inversion.csv"
    with ruta.open(encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        return lector.fieldnames, list(lector)


class FuentesInversionTest(unittest.TestCase):
    def setUp(self):
        self.columnas, self.filas = leer_fuentes()

    def test_esquema_exacto_y_campos_completos(self):
        self.assertEqual(self.columnas, COLUMNAS_ESPERADAS)
        self.assertGreaterEqual(len(self.filas), 7)
        for fila in self.filas:
            for col in COLUMNAS_ESPERADAS:
                self.assertTrue(
                    fila[col] and fila[col].strip(),
                    f"Campo '{col}' vacío en fila '{fila.get('id')}'",
                )

    def test_llaves_id_unicas_y_billeteras_validas(self):
        ids = [fila["id"] for fila in self.filas]
        self.assertEqual(len(ids), len(set(ids)))
        for fila in self.filas:
            billeteras = {
                b.strip() for b in fila["billetera"].split(";") if b.strip()
            }
            self.assertTrue(billeteras)
            self.assertTrue(
                billeteras.issubset(BILLETERAS_PERMITIDAS),
                f"Billetera inválida en '{fila['id']}': {billeteras}",
            )

    def test_urls_https_oficiales(self):
        for fila in self.filas:
            url = urlsplit(fila["url_oficial"])
            self.assertEqual(
                url.scheme,
                "https",
                f"URL no HTTPS en '{fila['id']}': {fila['url_oficial']}",
            )
            self.assertTrue(url.hostname, f"URL sin host en '{fila['id']}'")
            self.assertTrue(
                url.hostname.endswith(".cl"),
                f"Se esperaba dominio oficial .cl en '{fila['id']}': {url.hostname}",
            )

    def test_separacion_explicita_de_etapas_contables(self):
        etapas_por_id = {fila["id"]: fila["etapa_contable"] for fila in self.filas}
        for id_fuente, etapa in etapas_por_id.items():
            self.assertIn(
                etapa,
                ETAPAS_PERMITIDAS,
                f"Etapa no reconocida '{etapa}' en '{id_fuente}'",
            )
        # Planificación (ARI/PROPIR), evaluación (BIP), contratación (MOP/OCDS)
        # y ejecución presupuestaria (DIPRES/SUBDERE) deben permanecer separadas.
        self.assertNotEqual(
            etapas_por_id["chileindica-ari"],
            etapas_por_id["chileindica-propir"],
        )
        self.assertNotEqual(
            etapas_por_id["bip-sni"],
            etapas_por_id["dipres-subtitulo-31"],
        )
        self.assertNotEqual(
            etapas_por_id["mercado-publico-ocds"],
            etapas_por_id["dipres-subtitulo-31"],
        )
        self.assertNotEqual(
            etapas_por_id["mop-contratos-obras"],
            etapas_por_id["dipres-subtitulo-31"],
        )
        self.assertNotEqual(
            etapas_por_id["subdere-fndr"],
            etapas_por_id["dipres-subtitulo-31"],
        )

    def test_presencia_obligatoria_de_fuentes_oficiales_clave(self):
        texto_fuentes = " | ".join(
            f"{fila['id']} {fila['fuente']} {fila['organismo']}"
            for fila in self.filas
        ).lower()
        for entidad in (
            "bip",
            "chileindica",
            "ari",
            "propir",
            "mop",
            "mercado publico",
            "chilecompra",
            "subdere",
            "dipres",
        ):
            self.assertIn(
                entidad,
                texto_fuentes,
                f"Falta la fuente oficial requerida '{entidad}' en fuentes-inversion.csv",
            )

    def test_limites_metodologicos_advierten_no_duplicidad_y_etapas(self):
        por_id = {fila["id"]: fila["limite_metodologico"].lower() for fila in self.filas}
        self.assertIn("desembolso", por_id["bip-sni"])
        self.assertIn("no acredita devengo ni pago", por_id["mercado-publico-ocds"])
        self.assertIn("sin sumar", por_id["chileindica-ari"])
        self.assertIn("sin sumar", por_id["chileindica-propir"])
        self.assertIn("una sola vez", por_id["subdere-fndr"])
        self.assertIn("devengo", por_id["dipres-subtitulo-31"])


if __name__ == "__main__":
    unittest.main()
