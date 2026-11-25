"""Pruebas del adaptador de cuadros públicos con tablas fabricadas."""

import unittest

from pipelines.economia.bde_publico import leer_cuadro, normalizar


def tabla(valoracion, valor="1.000", duplicar=False):
    marca = {"real": "R", "nominal": "N"}[valoracion]
    medicion = {
        "real": "volumen a precios del año anterior encadenado",
        "nominal": "precios corrientes",
    }[valoracion]
    unidad = "pesos encadenados" if valoracion == "real" else "pesos"
    regionales = [f"F035.PIB.FLU.{marca}.CLP.2018.Z.Z.Z.{n:02}.0.T" for n in range(1, 17)]
    codigos = [*regionales, f"F032.PIB.FLU.{marca}.CLP.EP18.Z.Z.0.T"]
    if duplicar:
        codigos.append(regionales[0])
    filas = "".join(
        f'<tr><td><input class="chkGrid" data-serie="{codigo}" data-decimales="0" data-calc="NONE">'
        f'</td><td>Título &amp; detalle</td><td>{valor}</td><td>1.050</td></tr>'
        for codigo in codigos
    )
    return (
        f'<legend id="lgCuadro" data-descname="PIB, {medicion}, referencia 2018 '
        f'(miles de millones de {unidad})"></legend>'
        '<table id="grilla"><tr><th>Sel.</th><th>Serie</th><th>2013</th><th>2014</th></tr>'
        f"{filas}</table>"
    ).encode()


class CuadrosPublicosTests(unittest.TestCase):
    def test_preserva_codigo_conversion_y_linaje(self):
        insumos = {tipo: tabla(tipo) for tipo in ("real", "nominal")}
        fecha = "2026-11-24T12:00:00+00:00"
        lote = normalizar(insumos, fecha)
        self.assertEqual(lote, normalizar(insumos, fecha))
        self.assertEqual(lote["publicacion"]["cobertura"], {"esperadas": 134, "disponibles": 117})
        nivel = lote["observaciones"][0]
        self.assertEqual((nivel["valor"], nivel["unidad"]), ("1000000", "millones CLP"))
        self.assertEqual(lote["procedencias"][0]["serie_bde"], "F032.PIB.FLU.R.CLP.EP18.Z.Z.0.T")
        self.assertIn("Título & detalle", lote["procedencias"][0]["selector"])
        crecimiento = [fila for fila in lote["observaciones"] if fila["metrica"] == "crecimiento"]
        self.assertEqual([(fila["estado"], fila["valor"]) for fila in crecimiento[:2]],
                         [("faltante", None), ("informado", "5")])

    def test_celda_ausente_falla_sin_imputar(self):
        with self.assertRaisesRegex(ValueError, "valor irreconocible"):
            leer_cuadro(tabla("real", valor="—"), "real")

    def test_duplicado_falla(self):
        with self.assertRaisesRegex(ValueError, "duplicada"):
            leer_cuadro(tabla("nominal", duplicar=True), "nominal")


if __name__ == "__main__":
    unittest.main()
