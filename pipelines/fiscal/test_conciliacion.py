"""Pruebas unitarias para cruces-investigacion.json y conciliacion.py."""

from __future__ import annotations

import json
import unittest
from decimal import Decimal
from pathlib import Path

from conciliacion import (
    BILLETERAS_VALIDAS,
    COBERTURAS_TERRITORIALES_VALIDAS,
    PRECISION_DECIMAL,
    MovimientoFiscal,
    TransferenciaConciliada,
    clasificar_cobertura_territorial,
    consolidar_billeteras,
    saldo_no_comprometido,
    saldo_por_devengar,
    tasa_ejecucion,
)

DIRECTORIO = Path(__file__).resolve().parent


class CrucesInvestigacionTest(unittest.TestCase):
    def setUp(self):
        ruta = DIRECTORIO / "cruces-investigacion.json"
        with ruta.open(encoding="utf-8") as archivo:
            self.especificacion = json.load(archivo)

    def test_cuatro_cruces_completos_y_trazables(self):
        cruces = self.especificacion.get("cruces", [])
        esperados = {
            "gasto_publico_pib",
            "inversion_publica_pib",
            "programas_beneficiarios_cobertura",
            "costo_administrativo_eficiencia",
        }
        actuales = {cruce["id"] for cruce in cruces}
        self.assertEqual(actuales, esperados)
        self.assertEqual(len(cruces), 4)

        campos_obligatorios = (
            "id",
            "nombre",
            "pregunta_investigacion",
            "formula",
            "numerador",
            "denominador",
            "fuentes_oficiales",
            "llaves_union",
            "perimetro",
            "etapas_contables_validas",
            "etapas_excluidas_de_suma",
            "reglas_anti_doble_contabilizacion",
            "brechas_cobertura_vigentes",
            "criterio_no_atribucion_causal",
        )
        for cruce in cruces:
            for campo in campos_obligatorios:
                self.assertIn(campo, cruce, f"Falta '{campo}' en {cruce['id']}")
                self.assertTrue(cruce[campo], f"Campo vacío '{campo}' en {cruce['id']}")
            self.assertEqual(cruce["etapas_contables_validas"], ["devengo"])
            self.assertIn("inicial", cruce["etapas_excluidas_de_suma"])
            self.assertIn("vigente", cruce["etapas_excluidas_de_suma"])
            self.assertIn("compromiso", cruce["etapas_excluidas_de_suma"])
            self.assertIn("pago", cruce["etapas_excluidas_de_suma"])
            self.assertIn(
                "causal",
                cruce["criterio_no_atribucion_causal"].lower(),
            )
            self.assertEqual(
                set(cruce["perimetro"]["billeteras"]),
                set(BILLETERAS_VALIDAS),
            )

    def test_fuentes_oficiales_requeridas_presentes_en_cruces(self):
        organismos = set()
        for cruce in self.especificacion["cruces"]:
            for fuente in cruce["fuentes_oficiales"]:
                self.assertTrue(fuente["organismo"].strip())
                self.assertTrue(fuente["recurso"].strip())
                self.assertTrue(fuente["rol"].strip())
                organismos.add(fuente["organismo"])

        for requerido in (
            "DIPRES",
            "ChileIndica",
            "BIP",
            "SUBDERE",
            "SINIM",
            "Mercado Público",
            "MOP",
            "BCCh",
        ):
            self.assertIn(requerido, organismos)


class PresupuestoYSaldosTest(unittest.TestCase):
    def test_saldo_por_devengar_normal_negativo_y_faltante(self):
        normal = saldo_por_devengar(Decimal("1000.50"), Decimal("400.25"))
        self.assertEqual(normal.valor, Decimal("600.25"))
        self.assertEqual(normal.estado, "calculado")
        self.assertFalse(normal.requiere_revision)
        self.assertIsNone(normal.motivo)

        negativo = saldo_por_devengar("1000", "1250.75")
        self.assertEqual(negativo.valor, Decimal("-250.75"))
        self.assertEqual(negativo.estado, "requiere_revision")
        self.assertTrue(negativo.requiere_revision)
        self.assertIsNotNone(negativo.motivo)

        faltante = saldo_por_devengar(None, Decimal("100"))
        self.assertIsNone(faltante.valor)
        self.assertEqual(faltante.estado, "no_calculable")
        self.assertIsNotNone(faltante.motivo)

    def test_saldo_no_comprometido_normal_ausente_y_negativo(self):
        normal = saldo_no_comprometido("1000", "600", "250")
        self.assertEqual(normal.valor, Decimal("150"))
        self.assertEqual(normal.estado, "calculado")
        self.assertFalse(normal.requiere_revision)

        # Compromiso ausente: retorna None con motivo explícito sin estimar.
        sin_compromiso = saldo_no_comprometido("1000", "600", None)
        self.assertIsNone(sin_compromiso.valor)
        self.assertEqual(sin_compromiso.estado, "no_calculable")
        self.assertEqual(
            sin_compromiso.motivo,
            "compromisos_incompletos_o_no_disponibles",
        )

        # Fuente declara compromisos incompletos aunque entregue monto parcial.
        incompleto = saldo_no_comprometido(
            "1000", "600", "100", compromisos_completos=False
        )
        self.assertIsNone(incompleto.valor)
        self.assertEqual(incompleto.estado, "no_calculable")
        self.assertEqual(
            incompleto.motivo,
            "compromisos_incompletos_o_no_disponibles",
        )

        # Saldo negativo: conserva el signo y marca revisión.
        negativo = saldo_no_comprometido("1000", "700", "450")
        self.assertEqual(negativo.valor, Decimal("-150"))
        self.assertEqual(negativo.estado, "requiere_revision")
        self.assertTrue(negativo.requiere_revision)
        self.assertEqual(
            negativo.motivo,
            "saldo_no_comprometido_negativo_revisar",
        )

        with self.assertRaises(ValueError):
            saldo_no_comprometido("1000", "500", "-10")

    def test_tasa_ejecucion_precision_y_casos_borde(self):
        normal = tasa_ejecucion("750", "1000")
        self.assertEqual(normal.valor, Decimal("75"))
        self.assertEqual(normal.estado, "calculado")

        # Precisión Decimal 34 en división periódica (100 * 1 / 3).
        periodica = tasa_ejecucion("1", "3")
        self.assertIsNotNone(periodica.valor)
        assert periodica.valor is not None
        self.assertEqual(len(periodica.valor.as_tuple().digits), PRECISION_DECIMAL)
        self.assertTrue(str(periodica.valor).startswith("33.33333333333333333333333333333333"))

        # Denominador cero produce valor faltante con causa.
        cero = tasa_ejecucion("100", "0")
        self.assertIsNone(cero.valor)
        self.assertEqual(cero.estado, "no_calculable")
        self.assertEqual(cero.motivo, "denominador_cero_vigente")

        # Denominador faltante produce valor faltante con causa.
        faltante = tasa_ejecucion("100", None)
        self.assertIsNone(faltante.valor)
        self.assertEqual(faltante.estado, "no_calculable")

        # Ejecución superior al 100% conserva valor exacto y marca revisión.
        sobre = tasa_ejecucion("1100", "1000")
        self.assertEqual(sobre.valor, Decimal("110"))
        self.assertTrue(sobre.requiere_revision)
        self.assertEqual(sobre.estado, "requiere_revision")

        # Rechaza float para preservar exactitud decimal.
        with self.assertRaises(TypeError):
            tasa_ejecucion(100.5, 1000)  # type: ignore[arg-type]


class ConsolidacionBilleterasTest(unittest.TestCase):
    def test_conservacion_aritmetica_bruto_a_neto_y_cobertura_territorial(self):
        movimientos = [
            # Sectorial: gasto directo localizado + transferencia al GORE + gasto nacional sin asignación
            MovimientoFiscal(
                id_movimiento="SEC-01",
                billetera="sectorial",
                monto=Decimal("500.00"),
                etapa="devengo",
                territorio="11",
            ),
            MovimientoFiscal(
                id_movimiento="SEC-TR-GORE",
                billetera="sectorial",
                monto=Decimal("300.00"),
                etapa="devengo",
                territorio="sin_asignacion",
                es_transferencia_interna=True,
                id_documento="RES-P31-2025-01",
            ),
            MovimientoFiscal(
                id_movimiento="SEC-MULT",
                billetera="sectorial",
                monto=Decimal("200.00"),
                etapa="devengo",
                territorio="multirregional",
            ),
            MovimientoFiscal(
                id_movimiento="SEC-SIN",
                billetera="sectorial",
                monto=Decimal("150.00"),
                etapa="devengo",
                territorio="sin_asignacion",
            ),
            # Regional: ejecuta inversión financiada por transferencia + transfiere a municipio
            MovimientoFiscal(
                id_movimiento="REG-OBRA",
                billetera="regional",
                monto=Decimal("400.00"),
                etapa="devengo",
                territorio="11",
                id_documento="RES-P31-2025-01",
            ),
            MovimientoFiscal(
                id_movimiento="REG-TR-MUN",
                billetera="regional",
                monto=Decimal("120.00"),
                etapa="devengo",
                territorio="11",
                es_transferencia_interna=True,
                id_documento="CONV-FNDR-11101",
            ),
            # Municipal: ejecuta obra en Coyhaique (11101)
            MovimientoFiscal(
                id_movimiento="MUN-OBRA",
                billetera="municipal",
                monto=Decimal("220.00"),
                etapa="devengo",
                territorio="11101",
                id_documento="CONV-FNDR-11101",
            ),
        ]
        transferencias = [
            TransferenciaConciliada(
                id_conciliacion="CONC-01",
                id_documento="RES-P31-2025-01",
                id_movimiento_emisor="SEC-TR-GORE",
                id_movimiento_receptor="REG-OBRA",
                monto_conciliado=Decimal("300.00"),
            ),
            TransferenciaConciliada(
                id_conciliacion="CONC-02",
                id_documento="CONV-FNDR-11101",
                id_movimiento_emisor="REG-TR-MUN",
                id_movimiento_receptor="MUN-OBRA",
                monto_conciliado=Decimal("120.00"),
            ),
        ]

        res = consolidar_billeteras(movimientos, transferencias)

        self.assertEqual(res.etapa, "devengo")
        self.assertEqual(res.totales_brutos_por_billetera["sectorial"], Decimal("1150.00"))
        self.assertEqual(res.totales_brutos_por_billetera["regional"], Decimal("520.00"))
        self.assertEqual(res.totales_brutos_por_billetera["municipal"], Decimal("220.00"))
        self.assertEqual(res.total_bruto, Decimal("1890.00"))
        self.assertEqual(res.total_transferencias_eliminadas, Decimal("420.00"))
        self.assertEqual(res.consolidado_neto, Decimal("1470.00"))
        self.assertTrue(res.conservacion_aritmetica_ok)
        self.assertEqual(
            sum(res.totales_brutos_por_billetera.values(), Decimal("0"))
            - res.total_transferencias_eliminadas,
            res.consolidado_neto,
        )
        self.assertEqual(res.residuales_pendientes, ())
        self.assertEqual(res.total_residuales_pendientes, Decimal("0"))

        # Cobertura territorial separada y aritméticamente conservada:
        # Bruto: localizado = 500 + 400 + 120 + 220 = 1240; multirregional = 200; sin_asignacion = 300 + 150 = 450
        # Eliminaciones descontadas al emisor: 300 de sin_asignacion y 120 de localizado
        # Neto: localizado = 1120; multirregional = 200; sin_asignacion = 150 -> suma = 1470
        self.assertEqual(res.bruto_por_cobertura["localizado"], Decimal("1240.00"))
        self.assertEqual(res.bruto_por_cobertura["multirregional"], Decimal("200.00"))
        self.assertEqual(res.bruto_por_cobertura["sin_asignacion"], Decimal("450.00"))
        self.assertEqual(res.neto_por_cobertura["localizado"], Decimal("1120.00"))
        self.assertEqual(res.neto_por_cobertura["multirregional"], Decimal("200.00"))
        self.assertEqual(res.neto_por_cobertura["sin_asignacion"], Decimal("150.00"))
        self.assertEqual(
            sum(res.neto_por_cobertura.values(), Decimal("0")),
            res.consolidado_neto,
        )
        self.assertEqual(
            set(res.neto_por_cobertura.keys()),
            set(COBERTURAS_TERRITORIALES_VALIDAS),
        )

    def test_transferencia_parcial_y_contraparte_ausente_quedan_en_residual(self):
        movimientos = [
            # Transferencia parcialmente conciliada (600 de 1000)
            {
                "id_movimiento": "SEC-PARCIAL",
                "billetera": "sectorial",
                "monto": "1000",
                "etapa": "devengo",
                "territorio": "11",
                "es_transferencia_interna": True,
                "id_documento": "DEC-2025-10",
            },
            {
                "id_movimiento": "MUN-REC",
                "billetera": "municipal",
                "monto": "600",
                "etapa": "devengo",
                "territorio": "11101",
                "id_documento": "DEC-2025-10",
            },
            # Transferencia sin contraparte en las transferencias conciliadas
            {
                "id_movimiento": "REG-SIN-CONTRA",
                "billetera": "regional",
                "monto": "250",
                "etapa": "devengo",
                "territorio": "11",
                "es_transferencia_interna": True,
                "id_documento": "RES-PEND-99",
            },
            # Transferencia cuya contraparte receptora está fuera del perímetro
            {
                "id_movimiento": "SEC-FUERA-PERIM",
                "billetera": "sectorial",
                "monto": "180",
                "etapa": "devengo",
                "territorio": "sin_asignacion",
                "es_transferencia_interna": True,
                "id_documento": "RES-OUT-07",
            },
        ]
        transferencias = [
            {
                "id_conciliacion": "C-PARCIAL",
                "id_documento": "DEC-2025-10",
                "id_movimiento_emisor": "SEC-PARCIAL",
                "id_movimiento_receptor": "MUN-REC",
                "monto_conciliado": "600",
            },
            {
                "id_conciliacion": "C-AUSENTE",
                "id_documento": "RES-OUT-07",
                "id_movimiento_emisor": "SEC-FUERA-PERIM",
                "id_movimiento_receptor": "MUN-NO-CARGADO",
                "monto_conciliado": "180",
            },
        ]

        res = consolidar_billeteras(movimientos, transferencias)

        self.assertEqual(res.total_bruto, Decimal("2030"))
        self.assertEqual(res.total_transferencias_eliminadas, Decimal("600"))
        self.assertEqual(res.consolidado_neto, Decimal("1430"))
        self.assertTrue(res.conservacion_aritmetica_ok)

        residuales_por_id = {r.id_movimiento: r for r in res.residuales_pendientes}
        self.assertEqual(
            set(residuales_por_id.keys()),
            {"SEC-PARCIAL", "REG-SIN-CONTRA", "SEC-FUERA-PERIM"},
        )
        self.assertEqual(residuales_por_id["SEC-PARCIAL"].monto_pendiente, Decimal("400"))
        self.assertEqual(residuales_por_id["SEC-PARCIAL"].motivo, "conciliacion_parcial")
        self.assertEqual(residuales_por_id["REG-SIN-CONTRA"].monto_pendiente, Decimal("250"))
        self.assertEqual(residuales_por_id["REG-SIN-CONTRA"].motivo, "contraparte_ausente")
        self.assertEqual(residuales_por_id["SEC-FUERA-PERIM"].monto_pendiente, Decimal("180"))
        self.assertEqual(residuales_por_id["SEC-FUERA-PERIM"].motivo, "contraparte_ausente")
        self.assertEqual(res.total_residuales_pendientes, Decimal("830"))

    def test_prohibe_conciliacion_sin_documento_y_mezcla_de_etapas(self):
        movimientos_devengo = [
            {
                "id_movimiento": "M1",
                "billetera": "sectorial",
                "monto": "100",
                "etapa": "devengo",
                "territorio": "11",
            },
            {
                "id_movimiento": "M2",
                "billetera": "municipal",
                "monto": "100",
                "etapa": "devengo",
                "territorio": "11101",
            },
        ]
        # Sin id_documento: prohibido conciliar solo por monto/fecha.
        with self.assertRaises(ValueError):
            consolidar_billeteras(
                movimientos_devengo,
                [
                    {
                        "id_conciliacion": "C-SINDOC",
                        "id_documento": "",
                        "id_movimiento_emisor": "M1",
                        "id_movimiento_receptor": "M2",
                        "monto_conciliado": "100",
                    }
                ],
            )

        # Mezcla de etapas contables (vigente + devengo): prohibido.
        movimientos_mixtos = [
            {
                "id_movimiento": "M1",
                "billetera": "sectorial",
                "monto": "100",
                "etapa": "vigente",
                "territorio": "11",
            },
            {
                "id_movimiento": "M2",
                "billetera": "municipal",
                "monto": "100",
                "etapa": "devengo",
                "territorio": "11101",
            },
        ]
        with self.assertRaises(ValueError):
            consolidar_billeteras(movimientos_mixtos, [])

    def test_clasificacion_cobertura_territorial(self):
        self.assertEqual(clasificar_cobertura_territorial("11"), "localizado")
        self.assertEqual(clasificar_cobertura_territorial("11101"), "localizado")
        self.assertEqual(
            clasificar_cobertura_territorial("multirregional"),
            "multirregional",
        )
        self.assertEqual(
            clasificar_cobertura_territorial("sin_asignacion"),
            "sin_asignacion",
        )
        self.assertEqual(
            clasificar_cobertura_territorial(None),
            "sin_asignacion",
        )


if __name__ == "__main__":
    unittest.main()
