import unittest
from decimal import localcontext

from analytics.territorial.pib import (
    crecimiento, crecimiento_acumulado, indice_historico, participacion, ranking_regional,
)


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

    def test_acumulado_e_indice_en_intervalo(self):
        base = nivel(id="nivel-11-2013", anio=2013, valor="80")
        actual = nivel(valor="120", estado="preliminar")
        acumulado = crecimiento_acumulado(actual, base)
        indice = indice_historico(actual, base)
        self.assertEqual(acumulado.valor, "50")
        self.assertEqual(indice.valor, "150")
        self.assertEqual(indice.estado, "preliminar")
        self.assertEqual(indice.insumos, ("nivel-11-2024", "nivel-11-2013"))
        self.assertEqual(indice_historico(base, base).valor, "100")
        self.assertEqual(crecimiento_acumulado(base, base).valor, "0")
        self.assertIsNone(crecimiento(actual, base).valor)
        self.assertIsNone(indice_historico(base, actual).valor)
        self.assertIsNone(indice_historico(actual, {**base, "anio_referencia": 2013}).valor)
        self.assertIsNone(indice_historico(actual, {**base, "valor": "0"}).valor)
        self.assertIsNone(crecimiento_acumulado(actual, None).valor)

    def test_ranking_usa_valor_exacto_y_empates(self):
        filas = [
            nivel(id="id-11", territorio="11", valor="100.00"),
            nivel(id="id-13", territorio="13", valor="90"),
            nivel(id="id-08", territorio="08", valor="100"),
            nivel(id="id-CL", territorio="CL", valor="500"),
            nivel(id="id-16", territorio="16", valor=None, estado="faltante"),
        ]
        resultado = ranking_regional(filas)
        self.assertEqual(
            [(fila.posicion, fila.territorio, fila.observacion_id) for fila in resultado],
            [(1, "08", "id-08"), (1, "11", "id-11"), (3, "13", "id-13")],
        )

    def test_ranking_rechaza_dimensiones_incomparables_y_duplicados(self):
        primera = nivel()
        otra = nivel(id="nivel-08-2024", territorio="08")
        for cambio in (
            {"clase": "prueba"}, {"publicacion": "otro"}, {"anio": 2023},
            {"valoracion": "nominal", "anio_referencia": None}, {"anio_referencia": 2013},
            {"territorio": "11"},
        ):
            with self.subTest(cambio=cambio), self.assertRaises(ValueError):
                ranking_regional([primera, {**otra, **cambio}])

    def test_ranking_de_indices_exige_un_ano_base_comun(self):
        primera = nivel(metrica="indice_historico", anio_base=2013, unidad="indice base 100")
        otra = {**primera, "id": "nivel-08-2024", "territorio": "08"}
        self.assertEqual([fila.posicion for fila in ranking_regional([primera, otra])], [1, 1])
        with self.assertRaises(ValueError):
            ranking_regional([primera, {**otra, "anio_base": 2018}])

    def test_estimacion_y_formato_invalido(self):
        actual = nivel(clase="estimacion", valor="80")
        previo = nivel(id="nivel-11-2023", anio=2023)
        self.assertEqual(crecimiento(actual, previo).clase, "estimacion")
        for valor in (0, "NaN", "1E2", None):
            with self.subTest(valor=valor):
                self.assertEqual(crecimiento({**actual, "valor": valor}, previo).estado, "error")


if __name__ == "__main__":
    unittest.main()
