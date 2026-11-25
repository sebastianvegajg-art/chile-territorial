import unittest
from decimal import Decimal, localcontext

from analytics.territorial.convergencia import (
    CRECIMIENTO_REQUERIDO_VERSION,
    DIVERSIFICACION_VERSION,
    PIB_PER_CAPITA_VERSION,
    SIGMA_CONVERGENCIA_VERSION,
    crecimiento_requerido_participacion,
    diversificacion_economica,
    pib_per_capita,
    sigma_convergencia,
)
from analytics.territorial.estructura import concentracion_hhi
from analytics.territorial.pib import Resultado


def obs_pib(**cambios):
    return {
        "id": "pib-02-2024",
        "territorio": "02",
        "anio": 2024,
        "metrica": "nivel",
        "valoracion": "nominal",
        "valor": "12000000",
        "unidad": "millones CLP",
        "anio_referencia": None,
        "estado": "informado",
        "clase": "oficial",
        "publicacion": "bcentral-2024",
        **cambios,
    }


def obs_pob(**cambios):
    return {
        "id": "pob-02-2024",
        "territorio": "02",
        "anio": 2024,
        "metrica": "poblacion",
        "valor": "600000",
        "unidad": "personas",
        "estado": "informado",
        "clase": "oficial",
        "publicacion": "ine-2024",
        **cambios,
    }


def va_sector(**cambios):
    return {
        "id": "va-02-2024-mineria",
        "territorio": "02",
        "anio": 2024,
        "metrica": "valor_agregado",
        "valoracion": "nominal",
        "valor": "50",
        "unidad": "millones CLP",
        "anio_referencia": None,
        "actividad": "mineria",
        "clasificacion": "ccnn-12",
        "perimetro": "va_precios_basicos",
        "estado": "informado",
        "clase": "oficial",
        "publicacion": "bcentral-2024",
        **cambios,
    }


class TestPibPerCapita(unittest.TestCase):
    def test_calculo_nominal_y_real_nacional_y_regional(self):
        res_reg = pib_per_capita(obs_pib(), obs_pob())
        self.assertIsInstance(res_reg, Resultado)
        self.assertEqual(res_reg.valor, "20000000")
        self.assertEqual(res_reg.formula_version, PIB_PER_CAPITA_VERSION)
        self.assertEqual(res_reg.insumos, ("pib-02-2024", "pob-02-2024"))
        self.assertEqual(res_reg.estado, "informado")
        self.assertEqual(res_reg.clase, "oficial")
        self.assertEqual(res_reg.valoracion, "nominal")
        self.assertIsNone(res_reg.anio_referencia)
        self.assertEqual(res_reg.unidad, "CLP por habitante")
        self.assertIsNone(res_reg.motivo)

        pib_cl_real = obs_pib(
            id="pib-CL-2024-real",
            territorio="CL",
            valoracion="real",
            anio_referencia=2018,
            valor="1",
            estado="preliminar",
        )
        pob_cl = obs_pob(
            id="pob-CL-2024",
            territorio="CL",
            valor="3",
            clase="proyeccion",
        )
        with localcontext() as contexto:
            contexto.prec = 4
            res_cl = pib_per_capita(pib_cl_real, pob_cl)

        self.assertEqual(res_cl.valor, "333333.3333333333333333333333333333")
        self.assertEqual(res_cl.valoracion, "real")
        self.assertEqual(res_cl.anio_referencia, 2018)
        self.assertEqual(res_cl.estado, "preliminar")
        self.assertEqual(res_cl.clase, "proyeccion")
        self.assertIsNone(res_cl.motivo)

    def test_rechaza_explicitamente_codigos_comunales(self):
        for comuna in ("13101", "05101", "02101"):
            with self.subTest(comuna=comuna):
                res = pib_per_capita(
                    obs_pib(territorio=comuna),
                    obs_pob(territorio=comuna),
                )
                self.assertIsNone(res.valor)
                self.assertEqual(res.estado, "no_aplicable")
                self.assertEqual(res.clase, "no_disponible")
                self.assertIn("comuna", res.motivo.lower())
                self.assertIn("imputar", res.motivo.lower())

        res_pob_comunal = pib_per_capita(obs_pib(territorio="13"), obs_pob(territorio="13101"))
        self.assertIsNone(res_pob_comunal.valor)
        self.assertEqual(res_pob_comunal.estado, "no_aplicable")
        self.assertIn("imputar", res_pob_comunal.motivo.lower())

    def test_validaciones_compatibilidad_estados_y_errores(self):
        casos_pib = (
            {"metrica": "crecimiento"},
            {"unidad": "CLP"},
            {"territorio": "17"},
            {"valoracion": "real", "anio_referencia": None},
            {"valoracion": "nominal", "anio_referencia": 2018},
            {"valoracion": "constante"},
            {"publicacion": ""},
        )
        for cambios in casos_pib:
            with self.subTest(cambios_pib=cambios):
                res = pib_per_capita(obs_pib(**cambios), obs_pob())
                self.assertIsNone(res.valor)
                self.assertEqual(res.clase, "no_disponible")
                self.assertTrue(res.motivo)

        casos_pob = (
            {"territorio": "13"},
            {"anio": 2023},
            {"unidad": "miles de personas"},
            {"clase": "prueba"},
        )
        for cambios in casos_pob:
            with self.subTest(cambios_pob=cambios):
                res = pib_per_capita(obs_pib(), obs_pob(**cambios))
                self.assertIsNone(res.valor)
                self.assertEqual(res.clase, "no_disponible")
                self.assertTrue(res.motivo)

        # Cero informado en PIB es válido; población cero o negativa se rechaza.
        self.assertEqual(pib_per_capita(obs_pib(valor="0"), obs_pob()).valor, "0")
        res_cero = pib_per_capita(obs_pib(), obs_pob(valor="0"))
        self.assertIsNone(res_cero.valor)
        self.assertEqual(res_cero.estado, "faltante")
        self.assertIn("cero", res_cero.motivo.lower())

        res_neg = pib_per_capita(obs_pib(), obs_pob(valor="-100"))
        self.assertIsNone(res_neg.valor)
        self.assertEqual(res_neg.estado, "error")

        # Propagación de estados ausentes.
        for estado in ("faltante", "suprimido", "no_aplicable", "error"):
            with self.subTest(estado=estado):
                res_aus = pib_per_capita(obs_pib(estado=estado, valor=None), obs_pob())
                self.assertIsNone(res_aus.valor)
                self.assertEqual(res_aus.estado, estado)
                self.assertEqual(res_aus.clase, "no_disponible")

        # Rechazo estricto de float, bool, NaN y notación científica.
        for malo in (12000000.5, True, "NaN", "1E6", None):
            with self.subTest(valor_malo=malo):
                res_err = pib_per_capita(obs_pib(valor=malo), obs_pob())
                self.assertIsNone(res_err.valor)
                self.assertEqual(res_err.estado, "error")


class TestDiversificacionEconomica(unittest.TestCase):
    def test_integracion_con_resultado_hhi_y_escalares(self):
        sectores = [
            va_sector(id="va-1", actividad="mineria", valor="50", estado="preliminar"),
            va_sector(id="va-2", actividad="servicios", valor="50"),
        ]
        hhi = concentracion_hhi(sectores)
        self.assertEqual(hhi.valor, "5000")

        div = diversificacion_economica(hhi)
        self.assertIsInstance(div, Resultado)
        self.assertEqual(div.valor, "0.5")
        self.assertEqual(div.formula_version, DIVERSIFICACION_VERSION)
        self.assertEqual(div.insumos, ("va-1", "va-2"))
        self.assertEqual(div.estado, "preliminar")
        self.assertEqual(div.clase, "oficial")
        self.assertIsNone(div.motivo)

        self.assertEqual(diversificacion_economica("10000").valor, "0")
        self.assertEqual(diversificacion_economica(Decimal("0")).valor, "1")
        self.assertEqual(diversificacion_economica("2500").valor, "0.75")

        # Independencia del contexto decimal global.
        with localcontext() as contexto:
            contexto.prec = 4
            res_prec = diversificacion_economica("3333.333333333333333333333333333333")
        self.assertEqual(res_prec.valor, "0.6666666666666666666666666666666667")

    def test_propaga_ausentes_y_rechaza_fuera_de_rango_o_float(self):
        for estado in ("faltante", "suprimido", "no_aplicable", "error"):
            with self.subTest(estado=estado):
                hhi_aus = Resultado(None, "cobertura incompleta", "estructura-hhi-v1", ("va-1",), estado, "no_disponible")
                div = diversificacion_economica(hhi_aus)
                self.assertIsNone(div.valor)
                self.assertEqual(div.estado, estado)
                self.assertEqual(div.clase, "no_disponible")
                self.assertEqual(div.insumos, ("va-1",))

        self.assertEqual(diversificacion_economica(None).estado, "faltante")

        for invalido in ("-0.01", "10000.01", 2500.0, True, "NaN", "1E3"):
            with self.subTest(invalido=invalido):
                res = diversificacion_economica(invalido)
                self.assertIsNone(res.valor)
                self.assertEqual(res.estado, "error")
                self.assertEqual(res.clase, "no_disponible")


class TestSigmaConvergencia(unittest.TestCase):
    def test_calculo_exacto_16_regiones_e_igualdad_total(self):
        # 8 regiones con 100 y 8 regiones con 300 -> media = 200, desv_est = 100, CV = 0.5
        datos_16 = {
            f"{i:02d}": ("100" if i <= 8 else "300")
            for i in range(1, 17)
        }
        with localcontext() as contexto:
            contexto.prec = 4
            res = sigma_convergencia(datos_16)
        self.assertIsInstance(res, Resultado)
        self.assertEqual(res.valor, "0.5")
        self.assertEqual(res.formula_version, SIGMA_CONVERGENCIA_VERSION)
        self.assertEqual(len(res.insumos), 16)
        self.assertEqual(res.estado, "informado")
        self.assertIsNone(res.motivo)
        self.assertIn("16 de 16", res.advertencia)
        self.assertIn("causal", res.advertencia.lower())

        iguales = {f"{i:02d}": Decimal("250") for i in range(1, 17)}
        self.assertEqual(sigma_convergencia(iguales).valor, "0")

    def test_cobertura_incompleta_advierte_y_rechaza_menos_de_dos_validas(self):
        # 3 regiones: 10, 20, 30 -> media = 20, varianza = 200/3, sqrt(200/3)/20 = sqrt(1/6)
        parcial = {
            "01": "10",
            "02": Decimal("20"),
            "03": "30",
            "04": None,
            "05": "0",
            "06": "-5",
        }
        res = sigma_convergencia(parcial)
        with localcontext() as ctx:
            ctx.prec = 34
            esperado = (Decimal(1) / Decimal(6)).sqrt()
        self.assertEqual(res.valor, format(esperado, "f"))
        self.assertEqual(res.insumos, ("01", "02", "03"))
        self.assertIn("3 de 16", res.advertencia)
        self.assertIn("04 (faltante)", res.advertencia)
        self.assertIn("05 (no positivo)", res.advertencia)
        self.assertIn("06 (no positivo)", res.advertencia)

        # Menos de 2 regiones válidas -> faltante.
        res_una = sigma_convergencia({"01": "100", "02": None, "03": "0"})
        self.assertIsNone(res_una.valor)
        self.assertEqual(res_una.estado, "faltante")

        res_vacio = sigma_convergencia({})
        self.assertIsNone(res_vacio.valor)
        self.assertEqual(res_vacio.estado, "faltante")

    def test_rechaza_codigos_no_regionales_y_float(self):
        for codigo in ("CL", "13101", "17", "00"):
            with self.subTest(codigo=codigo):
                res = sigma_convergencia({codigo: "100", "02": "200"})
                self.assertIsNone(res.valor)
                self.assertEqual(res.estado, "error")

        for malo in (100.5, True, "NaN", "1E2"):
            with self.subTest(malo=malo):
                res = sigma_convergencia({"01": malo, "02": "200"})
                self.assertIsNone(res.valor)
                self.assertEqual(res.estado, "error")


class TestCrecimientoRequeridoParticipacion(unittest.TestCase):
    def test_casos_analiticos_exactos_y_round_trip(self):
        # Sin cambio en participación -> tasa regional == tasa nacional, brecha == 0.
        res_igual = crecimiento_requerido_participacion("10", "100", "3", "10", 5)
        self.assertEqual(res_igual["formula_version"], CRECIMIENTO_REQUERIDO_VERSION)
        self.assertEqual(res_igual["clase"], "simulacion_hipotetica")
        self.assertEqual(res_igual["estado"], "informado")
        self.assertEqual(res_igual["participacion_actual_pct"], "10")
        self.assertEqual(res_igual["participacion_objetivo_pct"], "10")
        self.assertEqual(res_igual["tasa_anual_regional_requerida_pct"], "3")
        self.assertEqual(res_igual["brecha_crecimiento_pp"], "0")
        self.assertIn("aritmético paramétrico", res_igual["advertencia_metodologica"].lower())
        self.assertIn("causal", res_igual["advertencia_metodologica"].lower())

        # Horizonte 1 año: 10% -> 20% con crecimiento nacional 5% => tasa = 110%, brecha = 105 pp.
        res_1 = crecimiento_requerido_participacion("10", "100", "5", "20", 1)
        self.assertEqual(res_1["tasa_anual_regional_requerida_pct"], "110")
        self.assertEqual(res_1["brecha_crecimiento_pp"], "105")

        # Horizonte 2 años: 10% -> 40% con crecimiento nacional 0% => tasa = 100%, brecha = 100 pp.
        res_2 = crecimiento_requerido_participacion("10", "100", "0", "40", 2)
        self.assertEqual(res_2["tasa_anual_regional_requerida_pct"], "100")
        self.assertEqual(res_2["brecha_crecimiento_pp"], "100")

        # Horizonte 3 años: 10% -> 80% con crecimiento nacional 0% => raíz cúbica exacta de 8 = 2 => 100%.
        res_3 = crecimiento_requerido_participacion("10", "100", "0", "80", 3)
        self.assertEqual(res_3["tasa_anual_regional_requerida_pct"], "100")
        self.assertEqual(res_3["brecha_crecimiento_pp"], "100")

        # Caso general 10 años, independiente del contexto decimal global, verificado por round-trip.
        with localcontext() as contexto:
            contexto.prec = 4
            res_10 = crecimiento_requerido_participacion(
                Decimal("1500000"), Decimal("20000000"), "2.5", "10", 10
            )
        self.assertEqual(res_10["estado"], "informado")
        self.assertEqual(res_10["participacion_actual_pct"], "7.5")
        with localcontext() as ctx:
            ctx.prec = 34
            g_r = Decimal(res_10["tasa_anual_regional_requerida_pct"]) / Decimal(100)
            g_n = Decimal("2.5") / Decimal(100)
            y_r_t = Decimal("1500000") * ((Decimal(1) + g_r) ** 10)
            y_n_t = Decimal("20000000") * ((Decimal(1) + g_n) ** 10)
            part_final = Decimal(100) * y_r_t / y_n_t
            self.assertLess(abs(part_final - Decimal("10")), Decimal("1E-30"))

    def test_validaciones_de_parametros_y_rechazo_de_float(self):
        casos_invalidos = (
            ("0", "100", "3", "10", 5),
            ("10", "0", "3", "10", 5),
            ("120", "100", "3", "10", 5),
            ("10", "100", "3", "0", 5),
            ("10", "100", "3", "101", 5),
            ("10", "100", "-100", "10", 5),
            ("10", "100", "3", "10", 0),
            ("10", "100", "3", "10", -2),
            ("10", "100", "3", "10", True),
            (10.5, "100", "3", "10", 5),
            ("10", "100", 3.0, "10", 5),
        )
        for args in casos_invalidos:
            with self.subTest(args=args):
                res = crecimiento_requerido_participacion(*args)
                self.assertEqual(res["clase"], "simulacion_hipotetica")
                self.assertIsNone(res["tasa_anual_regional_requerida_pct"])
                self.assertIsNone(res["brecha_crecimiento_pp"])
                self.assertTrue(res["motivo"])
                self.assertIn("aritmético paramétrico", res["advertencia_metodologica"].lower())


if __name__ == "__main__":
    unittest.main()
