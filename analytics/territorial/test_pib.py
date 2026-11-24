import unittest
from decimal import localcontext

from analytics.territorial.pib import crecimiento, participacion


def nivel(**cambios):
    return {
        "id": "nivel-11-2024",
        "territorio": "11",
        "anio": 2024,
        "metrica": "nivel",
        "valoracion": "real",
        "valor": "100",
        "unidad": "millones CLP",
        "anio_referencia": 2018,
        "estado": "informado",
        "clase": "oficial",
        "publicacion": "corte",
        **cambios,
    }


class IndicadoresPIB(unittest.TestCase):
    def test_crecimiento_con_nivel_auxiliar(self):
        actual = nivel(id="nivel-11-2013", anio=2013, valor="110.000")
        previo = nivel(id="nivel-11-2012", anio=2012)
        resultado = crecimiento(actual, previo)
        self.assertEqual(resultado.valor, "10.000")
        self.assertEqual(resultado.formula_version, "pib-crecimiento-v1")
        self.assertEqual(resultado.insumos, ("nivel-11-2013", "nivel-11-2012"))
        self.assertIsNone(resultado.motivo)

    def test_crecimiento_compatible(self):
        actual = nivel()
        for cambios in (
            {"anio": 2022}, {"territorio": "10"}, {"valoracion": "nominal"},
            {"anio_referencia": 2013}, {"anio_referencia": None},
            {"unidad": "CLP"}, {"publicacion": "otro"}, {"metrica": "crecimiento"},
        ):
            with self.subTest(cambios=cambios):
                previo = nivel(**{"id": "nivel-11-2023", "anio": 2023, **cambios})
                resultado = crecimiento(actual, previo)
                self.assertIsNone(resultado.valor)
                self.assertEqual(resultado.clase, "no_disponible")
                self.assertTrue(resultado.motivo)

    def test_faltante_y_cero_tienen_resultados_distintos(self):
        actual = nivel(valor="0")
        previo = nivel(id="nivel-11-2023", anio=2023)
        self.assertEqual(crecimiento(actual, previo).valor, "-100")
        self.assertIsNone(crecimiento(actual, None).valor)
        self.assertIn("cero", crecimiento(actual, {**previo, "valor": "0.00"}).motivo)
        for estado in ("faltante", "suprimido", "no_aplicable", "error"):
            with self.subTest(estado=estado):
                resultado = crecimiento(actual, {**previo, "valor": None, "estado": estado})
                self.assertIsNone(resultado.valor)
                self.assertEqual(resultado.estado, estado)

    def test_participacion_decimal_independiente_del_contexto(self):
        region = nivel(valoracion="nominal", anio_referencia=None, valor="1",
                       estado="preliminar", clase="prueba")
        chile = {**region, "id": "nivel-CL-2024", "territorio": "CL", "valor": "3"}
        with localcontext() as contexto:
            contexto.prec = 4
            resultado = participacion(region, chile)
        self.assertEqual(resultado.valor, "33.33333333333333333333333333333333")
        self.assertEqual(resultado.estado, "preliminar")
        self.assertEqual(resultado.clase, "prueba")
        self.assertEqual(resultado.formula_version, "pib-participacion-v1")
        self.assertIsNone(participacion(chile, region).valor)
        self.assertIsNone(participacion(region, {**chile, "anio": 2023}).valor)
        self.assertIsNone(participacion(region, {**chile, "clase": "oficial"}).valor)

    def test_estimacion_y_formato_invalido(self):
        actual = nivel(clase="estimacion", valor="80")
        previo = nivel(id="nivel-11-2023", anio=2023)
        self.assertEqual(crecimiento(actual, previo).clase, "estimacion")
        for valor in (0, "NaN", "1E2", None):
            with self.subTest(valor=valor):
                self.assertEqual(crecimiento({**actual, "valor": valor}, previo).estado, "error")


if __name__ == "__main__":
    unittest.main()
