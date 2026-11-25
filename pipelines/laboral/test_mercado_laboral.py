"""Pruebas unitarias sin red para el pipeline laboral INE ENE (BCCh SI3) + SII (2013–2025)."""

from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

_DIR_LAB = Path(__file__).resolve().parent
if str(_DIR_LAB) not in sys.path:
    sys.path.insert(0, str(_DIR_LAB))

import mercado_laboral_live as ml  # noqa: E402


class TestMercadoLaboralLive(unittest.TestCase):
    def test_promediar_mensual_decimal34_y_secreto_estadistico_sii(self):
        self.assertIsNone(ml._a_decimal("*"))
        self.assertIsNone(ml._a_decimal(""))
        self.assertEqual(ml._a_decimal("4680.1"), Decimal("4680.1"))

        obs = [
            {"fecha": f"2025-{m:02d}-01", "valor": "50.000"} for m in range(1, 7)
        ] + [
            {"fecha": f"2025-{m:02d}-01", "valor": "54.000"} for m in range(7, 13)
        ] + [
            {"fecha": "2026-01-01", "valor": "55.000"},
            {"fecha": "2026-02-01", "valor": "57.000"},
        ]
        prom = ml._promediar_mensual_a_anual(obs)
        self.assertEqual(prom[2025], (Decimal("52"), 12))
        self.assertEqual(prom[2026], (Decimal("56"), 2))

    def test_construir_lote_laboral_con_productividad_y_rubro_o_sii(self):
        fake_reg_rows = [
            [2025, "Región Aisén del Gral.Carlos Ibáñez del Campo", 11200, 32000000, 30000, 8000000, 23297.2, 0, 0, 0, 0, 0, 0, 12000, 900000],
            [2025, "Región Metropolitana de Santiago", 500000, 900000000, 3000000, 800000000, 2500000, 0, 0, 0, 0, 0, 0, 400000, 50000000],
        ]
        fake_rubr_rows = [
            # Rubro O: 4680.1 / 23297.2 = 20.09% trab, 2519041.6 / 8000000 = 31.49% masa salarial
            [2025, "Región Aisén del Gral.Carlos Ibáñez del Campo", "O - Administración pública y defensa; planes de seguridad social", 39, "*", 5100, 2519041.6, 4680.1],
            # Comercio con renta suprimida '*' -> debe quedar None y marcar secreto_estadistico_renta=True
            [2025, "Región Aisén del Gral.Carlos Ibáñez del Campo", "G - Comercio al por mayor y al por menor", 3409, 12000000, 4000, "*", 3392.6],
        ]
        fake_comu_rows = [
            [2025, "Aisén", "Aisén", "Región Aisén del Gral.Carlos Ibáñez del Campo", 2100, 5000000, 6200, 1400000, 4800.5, 0, 0, 0, 0, 0, 0, 1800, 150000],
            [2025, "Coyhaique", "Coyhaique", "Región Aisén del Gral.Carlos Ibáñez del Campo", 6800, 21000000, 18500, 5600000, 14800.0, 0, 0, 0, 0, 0, 0, 8100, 650000],
        ]

        def fake_leer_xlsb(raw_bytes: bytes):
            if raw_bytes == b"REG":
                return ["Año Comercial"], fake_reg_rows
            if raw_bytes == b"RUBR":
                return ["Año Comercial"], fake_rubr_rows
            if raw_bytes == b"COMU":
                return ["Año Comercial"], fake_comu_rows
            raise AssertionError(raw_bytes)

        series_bcch = {
            "F049.OCU.PMT.INE9.21.M": [{"fecha": f"2025-{m:02d}-01", "valor": "50.000"} for m in range(1, 13)],
            "F049.DES.TAS.INE9.21.M": [{"fecha": f"2025-{m:02d}-01", "valor": "4.50"} for m in range(1, 13)],
            "F049.OCU.PMT.INE9.01.M": [{"fecha": f"2025-{m:02d}-01", "valor": "9000.000"} for m in range(1, 13)],
            "F049.DES.TAS.INE9.10.M": [{"fecha": f"2025-{m:02d}-01", "valor": "8.40"} for m in range(1, 13)],
            "F049.OCU.PMT.INE4.39B.M": [{"fecha": f"2025-{m:02d}-01", "valor": "540.000"} for m in range(1, 13)],
        }
        lote_pib = {
            "observaciones": [
                {"territorio": "11", "anio": 2025, "metrica": "nivel", "valoracion": "real", "valor": "1500000.00"},
                {"territorio": "CL", "anio": 2025, "metrica": "nivel", "valoracion": "real", "valor": "216000000.00"},
            ]
        }

        with patch.object(ml, "_leer_filas_xlsb", side_effect=fake_leer_xlsb):
            pub = ml.construir_lote_laboral(
                series_bcch=series_bcch,
                sii_reg_bytes=b"REG",
                sii_reg_rubr_bytes=b"RUBR",
                sii_comu_bytes=b"COMU",
                lote_pib=lote_pib,
            )

        # Productividad Aysén: 1.500.000 MM CLP / 50.000 ocupados = 30.000.000 CLP/ocupado
        ene_ay = pub["ine_ene_por_anio"]["2025"]["11"]
        self.assertEqual(ene_ay["ocupados_miles"], "50.000")
        self.assertEqual(ene_ay["tasa_desocupacion_pct"], "4.50")
        self.assertEqual(ene_ay["productividad_laboral_real_clp"], "30000000")

        # Nacional Adm. Pública ENE: 540 / 9000 = 6.00%
        ene_cl = pub["ine_ene_por_anio"]["2025"]["CL"]
        self.assertEqual(ene_cl["participacion_adm_publica_ene_nacional_pct"], "6.00")

        # SII Rubro O Aysén: 4680.1 / 23297.2 = 20.09% trab, 2519041.6 / 8000000 = 31.49% masa salarial
        sii_ay = pub["sii_regiones_por_anio"]["2025"]["11"]
        self.assertEqual(sii_ay["participacion_rubro_o_trabajadores_pct"], "20.09")
        self.assertEqual(sii_ay["participacion_rubro_o_masa_salarial_pct"], "31.49")
        comercio = next(r for r in sii_ay["top_rubros_aysen"] if r["rubro"].startswith("G -"))
        self.assertIsNone(comercio["renta_neta_uf"])
        self.assertTrue(comercio["secreto_estadistico_renta"])

        # Comunas de Aysén (11201 y 11101)
        com_25 = pub["sii_comunas_aysen_por_anio"]["2025"]
        self.assertEqual(com_25["11201"]["comuna"], "Aysén")
        self.assertEqual(com_25["11201"]["empresas"], 2100)
        self.assertEqual(com_25["11101"]["comuna"], "Coyhaique")


if __name__ == "__main__":
    unittest.main()
