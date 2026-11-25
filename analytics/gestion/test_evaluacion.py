import unittest
from decimal import Decimal, localcontext

from analytics.gestion.evaluacion import (
    COBERTURA_PROGRAMA_VERSION,
    EFICIENCIA_ADMINISTRATIVA_VERSION,
    INTENSIDAD_BENEFICIARIO_VERSION,
    cobertura_programa,
    eficiencia_administrativa,
    intensidad_beneficiario,
)


class TestIntensidadBeneficiario(unittest.TestCase):
    def test_calculo_exacto_mensual_diario_y_advertencia(self):
        res = intensidad_beneficiario("120000000", 1000, meses_programa=12, dias_programa=365)
        self.assertEqual(res["formula_version"], INTENSIDAD_BENEFICIARIO_VERSION)
        self.assertEqual(res["estado"], "informado")
        self.assertEqual(res["clase"], "descriptivo")
        self.assertIsNone(res["motivo"])
        self.assertEqual(res["valor"], "120000")
        self.assertEqual(res["monto_por_beneficiario_clp"], "120000")
        self.assertEqual(res["equivalente_mensual_clp"], "10000")
        self.assertEqual(
            res["equivalente_diario_clp"],
            "328.7671232876712328767123287671233",
        )
        self.assertEqual(
            res["advertencia_metodologica"],
            "El monto por beneficiario no permite inferir por sí solo eficiencia, clientelismo ni impacto causal.",
        )

        # Independencia del contexto decimal global y cero informado en gasto.
        with localcontext() as contexto:
            contexto.prec = 4
            res_prec = intensidad_beneficiario(Decimal("100"), 3, meses_programa=6, dias_programa=180)
        self.assertEqual(res_prec["valor"], "33.33333333333333333333333333333333")
        self.assertEqual(res_prec["equivalente_mensual_clp"], "5.555555555555555555555555555555556")
        self.assertEqual(res_prec["equivalente_diario_clp"], "0.1851851851851851851851851851851852")

        res_cero = intensidad_beneficiario("0", 50)
        self.assertEqual(res_cero["valor"], "0")
        self.assertEqual(res_cero["equivalente_mensual_clp"], "0")
        self.assertEqual(res_cero["equivalente_diario_clp"], "0")

    def test_rechaza_beneficiarios_no_positivos_float_y_errores(self):
        res_cero = intensidad_beneficiario("100000", 0)
        self.assertIsNone(res_cero["valor"])
        self.assertIsNone(res_cero["equivalente_mensual_clp"])
        self.assertIsNone(res_cero["equivalente_diario_clp"])
        self.assertEqual(res_cero["estado"], "faltante")
        self.assertEqual(res_cero["clase"], "no_disponible")
        self.assertIn("cero", res_cero["motivo"].lower())
        self.assertEqual(
            res_cero["advertencia_metodologica"],
            "El monto por beneficiario no permite inferir por sí solo eficiencia, clientelismo ni impacto causal.",
        )

        res_neg = intensidad_beneficiario("100000", -10)
        self.assertIsNone(res_neg["valor"])
        self.assertEqual(res_neg["estado"], "error")
        self.assertTrue(res_neg["motivo"])

        for kwargs in (
            {"gasto_devengado_clp": None, "beneficiarios_unicos": 10},
            {"gasto_devengado_clp": "100", "beneficiarios_unicos": None},
            {"gasto_devengado_clp": "-1", "beneficiarios_unicos": 10},
            {"gasto_devengado_clp": "100", "beneficiarios_unicos": "10.5"},
            {"gasto_devengado_clp": 100.5, "beneficiarios_unicos": 10},
            {"gasto_devengado_clp": "100", "beneficiarios_unicos": 10.0},
            {"gasto_devengado_clp": True, "beneficiarios_unicos": 10},
            {"gasto_devengado_clp": "100", "beneficiarios_unicos": 10, "meses_programa": 0},
            {"gasto_devengado_clp": "100", "beneficiarios_unicos": 10, "dias_programa": -1},
            {"gasto_devengado_clp": "100", "beneficiarios_unicos": 10, "dias_programa": 365.25},
        ):
            with self.subTest(kwargs=kwargs):
                res = intensidad_beneficiario(**kwargs)
                self.assertIsNone(res["valor"])
                self.assertEqual(res["clase"], "no_disponible")
                self.assertTrue(res["motivo"])


class TestCoberturaPrograma(unittest.TestCase):
    def test_cobertura_normal_cien_por_ciento_y_marca_revision_sobre_cien(self):
        res_normal = cobertura_programa(250, 1000)
        self.assertEqual(res_normal["formula_version"], COBERTURA_PROGRAMA_VERSION)
        self.assertEqual(res_normal["valor"], "25")
        self.assertEqual(res_normal["cobertura_pct"], "25")
        self.assertFalse(res_normal["requiere_revision"])
        self.assertIsNone(res_normal["motivo_revision"])
        self.assertEqual(res_normal["estado"], "informado")
        self.assertEqual(res_normal["clase"], "descriptivo")

        res_cien = cobertura_programa("1000", "1000")
        self.assertEqual(res_cien["valor"], "100")
        self.assertFalse(res_cien["requiere_revision"])
        self.assertEqual(res_cien["estado"], "informado")

        res_cero = cobertura_programa(0, 500)
        self.assertEqual(res_cero["valor"], "0")
        self.assertFalse(res_cero["requiere_revision"])

        # Supera 100%: calcula valor exacto pero marca revisión explícita.
        res_sobre = cobertura_programa(1050, 1000)
        self.assertEqual(res_sobre["valor"], "105")
        self.assertTrue(res_sobre["requiere_revision"])
        self.assertEqual(res_sobre["estado"], "requiere_revision")
        self.assertIn("duplicidad", res_sobre["motivo_revision"].lower())
        self.assertIn("padrón", res_sobre["motivo_revision"].lower())

        # Población elegible expandida con decimales e independencia de contexto.
        with localcontext() as contexto:
            contexto.prec = 4
            res_exp = cobertura_programa(1, "3")
        self.assertEqual(res_exp["valor"], "33.33333333333333333333333333333333")

    def test_cobertura_validaciones_y_rechazo_de_float(self):
        self.assertEqual(cobertura_programa(10, 0)["estado"], "faltante")
        self.assertIsNone(cobertura_programa(10, 0)["valor"])
        self.assertEqual(cobertura_programa(None, 100)["estado"], "faltante")

        for b, p in ((-1, 100), (10, -5), ("10.5", 100), (10.0, 100), (10, 100.0), (True, 100), ("NaN", 100)):
            with self.subTest(b=b, p=p):
                res = cobertura_programa(b, p)
                self.assertIsNone(res["valor"])
                self.assertEqual(res["estado"], "error")
                self.assertEqual(res["clase"], "no_disponible")


class TestEficienciaAdministrativa(unittest.TestCase):
    def test_calculo_completo_con_y_sin_unidades_resultado(self):
        res = eficiencia_administrativa(
            "15000000",
            "100000000",
            unidades_resultado=30,
            misma_moneda_y_periodo=True,
        )
        self.assertEqual(res["formula_version"], EFICIENCIA_ADMINISTRATIVA_VERSION)
        self.assertEqual(res["estado"], "informado")
        self.assertEqual(res["clase"], "descriptivo")
        self.assertIsNone(res["motivo"])
        self.assertEqual(res["costo_admin_por_peso_invertido"], "0.15")
        self.assertEqual(res["valor"], "0.15")
        self.assertEqual(res["porcentaje_sobre_inversion"], "15")
        self.assertEqual(res["costo_por_resultado"], "500000")
        self.assertIsNone(res["motivo_costo_por_resultado"])
        self.assertIn("inflación", res["advertencia_metodologica"].lower())
        self.assertIn("cambios de funciones", res["advertencia_metodologica"].lower())

        # Sin unidades_resultado -> costo_por_resultado es None.
        res_sin_u = eficiencia_administrativa("1", "3")
        with localcontext() as contexto:
            contexto.prec = 4
            res_sin_u = eficiencia_administrativa("1", "3")
        self.assertEqual(res_sin_u["costo_admin_por_peso_invertido"], "0.3333333333333333333333333333333333")
        self.assertEqual(res_sin_u["porcentaje_sobre_inversion"], "33.33333333333333333333333333333333")
        self.assertIsNone(res_sin_u["costo_por_resultado"])

        # unidades_resultado == 0 -> calcula razones sobre inversión y documenta ausencia de costo_por_resultado.
        res_u_cero = eficiencia_administrativa("10", "100", unidades_resultado=0)
        self.assertEqual(res_u_cero["costo_admin_por_peso_invertido"], "0.1")
        self.assertEqual(res_u_cero["porcentaje_sobre_inversion"], "10")
        self.assertIsNone(res_u_cero["costo_por_resultado"])
        self.assertIn("cero", res_u_cero["motivo_costo_por_resultado"].lower())

        # Cero informado en costo administrativo.
        res_costo_cero = eficiencia_administrativa("0", "1000", unidades_resultado=5)
        self.assertEqual(res_costo_cero["costo_admin_por_peso_invertido"], "0")
        self.assertEqual(res_costo_cero["porcentaje_sobre_inversion"], "0")
        self.assertEqual(res_costo_cero["costo_por_resultado"], "0")

    def test_exige_misma_moneda_y_periodo_y_rechaza_invalidos(self):
        for flag in (False, None, "True", 1):
            with self.subTest(misma_moneda_y_periodo=flag):
                res = eficiencia_administrativa(
                    "100", "1000", unidades_resultado=5, misma_moneda_y_periodo=flag
                )
                self.assertIsNone(res["valor"])
                self.assertIsNone(res["costo_admin_por_peso_invertido"])
                self.assertIsNone(res["porcentaje_sobre_inversion"])
                self.assertIsNone(res["costo_por_resultado"])
                self.assertEqual(res["estado"], "faltante")
                self.assertEqual(res["clase"], "no_disponible")
                self.assertIn("misma_moneda_y_periodo", res["motivo"])
                self.assertIn("inflación", res["advertencia_metodologica"].lower())
                self.assertIn("cambios de funciones", res["advertencia_metodologica"].lower())

        self.assertEqual(eficiencia_administrativa("100", "0")["estado"], "faltante")
        self.assertEqual(eficiencia_administrativa(None, "100")["estado"], "faltante")

        for kwargs in (
            {"costo_administrativo_clp": "-1", "inversion_ejecutada_clp": "100"},
            {"costo_administrativo_clp": "10", "inversion_ejecutada_clp": "-100"},
            {"costo_administrativo_clp": "10", "inversion_ejecutada_clp": "100", "unidades_resultado": -1},
            {"costo_administrativo_clp": 10.5, "inversion_ejecutada_clp": "100"},
            {"costo_administrativo_clp": "10", "inversion_ejecutada_clp": 100.5},
            {"costo_administrativo_clp": "10", "inversion_ejecutada_clp": "100", "unidades_resultado": 2.5},
            {"costo_administrativo_clp": True, "inversion_ejecutada_clp": "100"},
            {"costo_administrativo_clp": "1E2", "inversion_ejecutada_clp": "100"},
        ):
            with self.subTest(kwargs=kwargs):
                res = eficiencia_administrativa(**kwargs)
                self.assertIsNone(res["valor"])
                self.assertEqual(res["estado"], "error")
                self.assertEqual(res["clase"], "no_disponible")


if __name__ == "__main__":
    unittest.main()
