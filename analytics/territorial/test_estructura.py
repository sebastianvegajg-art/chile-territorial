import unittest
from decimal import localcontext

from analytics.territorial.estructura import (
    ESPECIALIZACION_VERSION,
    HHI_VERSION,
    KRUGMAN_VERSION,
    PARTICIPACION_SECTORIAL_VERSION,
    concentracion_hhi,
    especializacion,
    indice_krugman,
    participacion_sectorial,
)


def va(**cambios):
    return {
        "id": "va-02-2024-mineria",
        "territorio": "02",
        "anio": 2024,
        "metrica": "valor_agregado",
        "valoracion": "nominal",
        "valor": "100",
        "unidad": "millones CLP",
        "anio_referencia": None,
        "actividad": "mineria",
        "clasificacion": "ccnn-12",
        "perimetro": "va_precios_basicos",
        "estado": "informado",
        "clase": "oficial",
        "publicacion": "corte-2024",
        **cambios,
    }


def va_total(**cambios):
    return va(
        **{
            "id": "va-02-2024-total",
            "actividad": "total",
            "valor": "200",
            **cambios,
        }
    )


def participacion_obs(**cambios):
    return va(
        **{
            "metrica": "participacion_sectorial",
            "unidad": "porcentaje",
            **cambios,
        }
    )


class IndicadoresEstructura(unittest.TestCase):
    def test_participacion_sectorial_exacta_e_independiente_del_contexto(self):
        actividad = va(valor="1", estado="preliminar", clase="oficial")
        total = va_total(valor="3")
        with localcontext() as contexto:
            contexto.prec = 4
            resultado = participacion_sectorial(actividad, total)
        self.assertEqual(resultado.valor, "33.33333333333333333333333333333333")
        self.assertIsNone(resultado.motivo)
        self.assertEqual(resultado.formula_version, PARTICIPACION_SECTORIAL_VERSION)
        self.assertEqual(resultado.insumos, ("va-02-2024-mineria", "va-02-2024-total"))
        self.assertEqual(resultado.estado, "preliminar")
        self.assertEqual(resultado.clase, "oficial")

        # También funciona para el agregado nacional CL, metrica="nivel" y total sin campo actividad.
        act_cl = va(id="va-CL-2024-mineria", territorio="CL", metrica="nivel", valor="25")
        tot_cl = va_total(id="va-CL-2024-total", territorio="CL", metrica="nivel", actividad=None, valor="100")
        res_cl = participacion_sectorial(act_cl, tot_cl)
        self.assertEqual(res_cl.valor, "25")
        self.assertEqual(res_cl.estado, "informado")

    def test_participacion_sectorial_redondeo_round_half_even(self):
        # 100 * 2000...0001 / 200 = 1000...0000.5 (digito 34 es par -> 0)
        par = va(valor="2000000000000000000000000000000001")
        # 100 * 2000...0003 / 200 = 1000...0001.5 (digito 34 es impar -> 2)
        impar = va(valor="2000000000000000000000000000000003")
        total = va_total(valor="200")
        self.assertEqual(
            participacion_sectorial(par, total).valor,
            "1000000000000000000000000000000000",
        )
        self.assertEqual(
            participacion_sectorial(impar, total).valor,
            "1000000000000000000000000000000002",
        )

    def test_participacion_sectorial_rechaza_real_y_dimensiones_incompatibles(self):
        actividad = va()
        total = va_total()

        res_real = participacion_sectorial({**actividad, "valoracion": "real", "anio_referencia": 2018}, total)
        self.assertIsNone(res_real.valor)
        self.assertEqual(res_real.estado, "faltante")
        self.assertEqual(res_real.clase, "no_disponible")
        self.assertIn("no son aditivos", res_real.motivo)

        for cambios in (
            {"publicacion": "otro-corte"},
            {"anio": 2023},
            {"anio": True},
            {"territorio": "13"},
            {"unidad": "CLP"},
            {"anio_referencia": 2018},
            {"clasificacion": "ciiu-rev4"},
            {"perimetro": "pib_precios_mercado"},
            {"metrica": "nivel"},
            {"clase": "prueba"},
            {"actividad": "industria"},
        ):
            with self.subTest(cambios=cambios):
                resultado = participacion_sectorial(actividad, {**total, **cambios})
                self.assertIsNone(resultado.valor)
                self.assertEqual(resultado.clase, "no_disponible")
                self.assertTrue(resultado.motivo)

        # Actividad faltante o igual a "total" en numerador.
        self.assertIsNone(participacion_sectorial({**actividad, "actividad": "total"}, total).valor)
        self.assertIsNone(participacion_sectorial({**actividad, "clasificacion": ""}, total).valor)

    def test_participacion_sectorial_cero_denominador_estados_y_formatos(self):
        actividad_cero = va(valor="0")
        total = va_total(valor="200")
        res_cero = participacion_sectorial(actividad_cero, total)
        self.assertEqual(res_cero.valor, "0")
        self.assertEqual(res_cero.estado, "informado")
        self.assertIsNone(res_cero.motivo)

        # Denominador cero y negativo.
        res_div0 = participacion_sectorial(va(), va_total(valor="0.00"))
        self.assertIsNone(res_div0.valor)
        self.assertIn("cero", res_div0.motivo)
        self.assertIsNone(participacion_sectorial(va(), va_total(valor="-50")).valor)
        self.assertIsNone(participacion_sectorial(va(), None).valor)

        # Estados ausentes distintos de cero informado.
        for estado in ("faltante", "suprimido", "no_aplicable", "error"):
            with self.subTest(estado=estado):
                res = participacion_sectorial(va(valor=None, estado=estado), total)
                self.assertIsNone(res.valor)
                self.assertEqual(res.estado, estado)
                self.assertEqual(res.clase, "no_disponible")

        # Estado inválido y formatos de valor inválidos.
        self.assertEqual(participacion_sectorial(va(estado="desconocido"), total).estado, "error")
        for valor_malo in (0, "NaN", "1E2", None):
            with self.subTest(valor_malo=valor_malo):
                self.assertEqual(participacion_sectorial(va(valor=valor_malo), total).estado, "error")

        # Propagación de estimación.
        self.assertEqual(participacion_sectorial(va(clase="estimacion"), total).clase, "estimacion")

    def test_especializacion_lq_exacto_y_sin_doble_redondeo(self):
        reg_act = va(id="reg-act", territorio="02", valor="60")
        reg_tot = va_total(id="reg-tot", territorio="02", valor="100")
        nac_act = va(id="nac-act", territorio="CL", valor="150")
        nac_tot = va_total(id="nac-tot", territorio="CL", valor="1000")

        res = especializacion(reg_act, reg_tot, nac_act, nac_tot)
        self.assertEqual(res.valor, "4")
        self.assertEqual(res.formula_version, ESPECIALIZACION_VERSION)
        self.assertEqual(res.insumos, ("reg-act", "reg-tot", "nac-act", "nac-tot"))
        self.assertEqual(res.estado, "informado")
        self.assertEqual(res.clase, "oficial")
        self.assertIsNone(res.motivo)

        # (1/6) / (1/3) = 0.5 exacto sin error de doble redondeo, independiente del contexto.
        with localcontext() as contexto:
            contexto.prec = 4
            res_exacto = especializacion(
                {**reg_act, "valor": "1", "estado": "preliminar"},
                {**reg_tot, "valor": "6"},
                {**nac_act, "valor": "1", "clase": "estimacion"},
                {**nac_tot, "valor": "3"},
            )
        self.assertEqual(res_exacto.valor, "0.5")
        self.assertEqual(res_exacto.estado, "preliminar")
        self.assertEqual(res_exacto.clase, "estimacion")

        # Totales sin campo clasificacion pero con actividad clasificada de igual esquema.
        res_sin_clas_tot = especializacion(
            reg_act,
            {**reg_tot, "clasificacion": None},
            nac_act,
            {**nac_tot, "clasificacion": None},
        )
        self.assertEqual(res_sin_clas_tot.valor, "4")

    def test_especializacion_cero_informado_vs_denominadores_y_estados(self):
        reg_act = va(id="reg-act", territorio="02", valor="0")
        reg_tot = va_total(id="reg-tot", territorio="02", valor="100")
        nac_act = va(id="nac-act", territorio="CL", valor="50")
        nac_tot = va_total(id="nac-tot", territorio="CL", valor="1000")

        # Cero informado en la actividad regional produce LQ = 0.
        res_cero = especializacion(reg_act, reg_tot, nac_act, nac_tot)
        self.assertEqual(res_cero.valor, "0")
        self.assertEqual(res_cero.estado, "informado")

        # Denominadores cero: reg_tot, nac_tot o nac_act.
        for caso in (
            (reg_act, {**reg_tot, "valor": "0"}, nac_act, nac_tot),
            (reg_act, reg_tot, {**nac_act, "valor": "0.0"}, nac_tot),
            (reg_act, reg_tot, nac_act, {**nac_tot, "valor": "0"}),
        ):
            with self.subTest(caso=[c["id"] for c in caso]):
                res = especializacion(*caso)
                self.assertIsNone(res.valor)
                self.assertEqual(res.estado, "faltante")
                self.assertIn("cero", res.motivo)

        # Denominadores negativos o actividad regional negativa.
        self.assertIsNone(especializacion({**reg_act, "valor": "-5"}, reg_tot, nac_act, nac_tot).valor)
        self.assertIsNone(especializacion(reg_act, {**reg_tot, "valor": "-10"}, nac_act, nac_tot).valor)
        self.assertIsNone(especializacion(reg_act, reg_tot, {**nac_act, "valor": "-10"}, nac_tot).valor)

        # Suprimido y prioridad error > suprimido > faltante.
        res_sup = especializacion({**reg_act, "valor": None, "estado": "suprimido"}, reg_tot, nac_act, nac_tot)
        self.assertIsNone(res_sup.valor)
        self.assertEqual(res_sup.estado, "suprimido")

        res_prio = especializacion(
            {**reg_act, "valor": None, "estado": "faltante"},
            reg_tot,
            {**nac_act, "valor": None, "estado": "suprimido"},
            nac_tot,
        )
        self.assertEqual(res_prio.estado, "suprimido")

    def test_especializacion_rechaza_real_y_comparabilidad_rota(self):
        reg_act = va(id="reg-act", territorio="02", valor="60")
        reg_tot = va_total(id="reg-tot", territorio="02", valor="100")
        nac_act = va(id="nac-act", territorio="CL", valor="150")
        nac_tot = va_total(id="nac-tot", territorio="CL", valor="1000")

        # Valoración real rechazada.
        res_real = especializacion(
            {**reg_act, "valoracion": "real", "anio_referencia": 2018},
            {**reg_tot, "valoracion": "real", "anio_referencia": 2018},
            {**nac_act, "valoracion": "real", "anio_referencia": 2018},
            {**nac_tot, "valoracion": "real", "anio_referencia": 2018},
        )
        self.assertIsNone(res_real.valor)
        self.assertIn("no son aditivos", res_real.motivo)

        casos_invalidos = (
            (reg_act, reg_tot, {**nac_act, "actividad": "industria"}, nac_tot),
            (reg_act, reg_tot, {**nac_act, "clasificacion": "ciiu-rev4"}, nac_tot),
            (reg_act, reg_tot, {**nac_act, "anio": 2023}, nac_tot),
            (reg_act, reg_tot, {**nac_act, "publicacion": "otro"}, nac_tot),
            (reg_act, reg_tot, {**nac_act, "perimetro": "otro"}, nac_tot),
            ({**reg_act, "territorio": "CL"}, {**reg_tot, "territorio": "CL"}, nac_act, nac_tot),
            (reg_act, {**reg_tot, "territorio": "03"}, nac_act, nac_tot),
            (reg_act, reg_tot, {**nac_act, "territorio": "13"}, {**nac_tot, "territorio": "13"}),
            (reg_act, reg_tot, {**nac_act, "clase": "prueba"}, nac_tot),
            (reg_act, reg_tot, None, nac_tot),
        )
        for entrada in casos_invalidos:
            with self.subTest(entrada=entrada):
                res = especializacion(*entrada)
                self.assertIsNone(res.valor)
                self.assertEqual(res.clase, "no_disponible")
                self.assertTrue(res.motivo)

    def test_concentracion_hhi_desde_niveles_y_participaciones(self):
        # 4 sectores iguales -> HHI = 2500.
        cuatro = (
            va(id=f"s-{i}", actividad=f"act-{i}", valor="250")
            for i in range(4)
        )
        res_4 = concentracion_hhi(cuatro)
        self.assertEqual(res_4.valor, "2500")
        self.assertEqual(res_4.formula_version, HHI_VERSION)
        self.assertEqual(res_4.insumos, ("s-0", "s-1", "s-2", "s-3"))
        self.assertEqual(res_4.estado, "informado")

        # 3 sectores iguales -> 3333.333... (34 dígitos), independiente del contexto.
        tres = [
            va(id="s-a", actividad="agro", valor="100", estado="preliminar"),
            va(id="s-b", actividad="mineria", valor="100"),
            va(id="s-c", actividad="servicios", valor="100", clase="estimacion"),
        ]
        with localcontext() as contexto:
            contexto.prec = 4
            res_3 = concentracion_hhi(tres)
        self.assertEqual(res_3.valor, "3333.333333333333333333333333333333")
        self.assertEqual(res_3.estado, "preliminar")
        self.assertEqual(res_3.clase, "estimacion")

        # Cero informado incluido en la estructura: [500, 0, 0] -> monopolio exacto 10000.
        monopolio = [
            va(id="m-1", actividad="mineria", valor="500"),
            va(id="m-2", actividad="agro", valor="0"),
            va(id="m-3", actividad="pesca", valor="0.00"),
        ]
        res_mono = concentracion_hhi(monopolio)
        self.assertEqual(res_mono.valor, "10000")
        self.assertEqual(res_mono.estado, "informado")

        # Desde participaciones porcentuales que suman 100%: 50^2 + 30^2 + 20^2 = 3800.
        shares = [
            participacion_obs(id="p-1", actividad="mineria", valor="50"),
            participacion_obs(id="p-2", actividad="industria", valor="30"),
            participacion_obs(id="p-3", actividad="servicios", valor="20"),
        ]
        self.assertEqual(concentracion_hhi(shares).valor, "3800")

        # Participaciones con unidad "%" y redondeo a 34 dígitos dentro de tolerancia.
        tercios = [
            participacion_obs(
                id=f"t-{i}",
                actividad=f"act-{i}",
                unidad="%",
                clase="prueba",
                valor="33.33333333333333333333333333333333",
            )
            for i in range(3)
        ]
        res_tercios = concentracion_hhi(tercios)
        self.assertEqual(res_tercios.valor, "3333.333333333333333333333333333333")
        self.assertEqual(res_tercios.clase, "prueba")

        # Participaciones que no concilian con 100% (ni por defecto ni por exceso) -> faltante.
        incompletas = [
            participacion_obs(id="p-1", actividad="mineria", valor="50"),
            participacion_obs(id="p-2", actividad="industria", valor="30"),
        ]
        res_inc = concentracion_hhi(incompletas)
        self.assertIsNone(res_inc.valor)
        self.assertEqual(res_inc.estado, "faltante")
        self.assertIn("100%", res_inc.motivo)

        exceso = [
            participacion_obs(id="p-1", actividad="mineria", valor="70"),
            participacion_obs(id="p-2", actividad="industria", valor="50"),
        ]
        self.assertIsNone(concentracion_hhi(exceso).valor)

        # Mezcla de nivel y participación -> incompatible.
        self.assertIsNone(concentracion_hhi([va(id="v-1", actividad="mineria"), shares[1]]).valor)

    def test_concentracion_hhi_duplicados_supresion_real_y_denominador_cero(self):
        base = [
            va(id="s-1", actividad="mineria", valor="60"),
            va(id="s-2", actividad="industria", valor="40"),
        ]

        # Actividad duplicada -> estado error.
        dup = [base[0], va(id="s-dup", actividad="mineria", valor="10")]
        res_dup = concentracion_hhi(dup)
        self.assertIsNone(res_dup.valor)
        self.assertEqual(res_dup.estado, "error")
        self.assertIn("duplicada", res_dup.motivo.lower())

        # Total mezclado como actividad -> estado error.
        con_total = [base[0], va_total(id="s-tot", valor="100")]
        self.assertEqual(concentracion_hhi(con_total).estado, "error")

        # Actividad suprimida / faltante: no calcula HHI sesgado y reporta cobertura.
        for estado in ("suprimido", "faltante", "no_aplicable", "error"):
            with self.subTest(estado=estado):
                parcial = [
                    base[0],
                    base[1],
                    va(id="s-3", actividad="pesca", valor=None, estado=estado),
                ]
                res = concentracion_hhi(parcial)
                self.assertIsNone(res.valor)
                self.assertEqual(res.estado, estado)
                self.assertIn("2 de 3", res.motivo)
                self.assertIn("pesca", res.motivo)

        # Valoración real rechazada.
        reales = [{**f, "valoracion": "real", "anio_referencia": 2018} for f in base]
        res_real = concentracion_hhi(reales)
        self.assertIsNone(res_real.valor)
        self.assertIn("no son aditivos", res_real.motivo)

        # Suma total cero (todos cero informado) -> denominador cero.
        ceros = [va(id="z-1", actividad="mineria", valor="0"), va(id="z-2", actividad="agro", valor="0")]
        res_z = concentracion_hhi(ceros)
        self.assertIsNone(res_z.valor)
        self.assertEqual(res_z.estado, "faltante")
        self.assertIn("cero", res_z.motivo)

        # Valores negativos, publicación/año/territorio distintos, vacío o None.
        self.assertIsNone(concentracion_hhi([base[0], {**base[1], "valor": "-5"}]).valor)
        self.assertIsNone(concentracion_hhi([base[0], {**base[1], "publicacion": "otra"}]).valor)
        self.assertIsNone(concentracion_hhi([base[0], {**base[1], "anio": 2023}]).valor)
        self.assertIsNone(concentracion_hhi([base[0], {**base[1], "territorio": "13"}]).valor)
        self.assertIsNone(concentracion_hhi([]).valor)
        self.assertIsNone(concentracion_hhi(None).valor)

    def test_indice_krugman_exacto_limites_y_precision(self):
        # Estructuras idénticas -> 0.
        reg_igual = [
            va(id="r-1", territorio="02", actividad="mineria", valor="10"),
            va(id="r-2", territorio="02", actividad="industria", valor="20"),
            va(id="r-3", territorio="02", actividad="servicios", valor="70"),
        ]
        nac_igual = [
            va(id="n-3", territorio="CL", actividad="servicios", valor="700"),
            va(id="n-1", territorio="CL", actividad="mineria", valor="100"),
            va(id="n-2", territorio="CL", actividad="industria", valor="200"),
        ]
        res_0 = indice_krugman(reg_igual, nac_igual)
        self.assertEqual(res_0.valor, "0")
        self.assertEqual(res_0.formula_version, KRUGMAN_VERSION)
        self.assertEqual(res_0.insumos, ("r-1", "r-2", "r-3", "n-3", "n-1", "n-2"))
        self.assertEqual(res_0.estado, "informado")
        self.assertEqual(res_0.clase, "oficial")

        # Estructuras completamente disjuntas (usando cero informado) -> 1.
        reg_disj = [
            va(id="r-a", territorio="02", actividad="mineria", valor="100"),
            va(id="r-b", territorio="02", actividad="agro", valor="0"),
        ]
        nac_disj = [
            va(id="n-a", territorio="CL", actividad="mineria", valor="0"),
            va(id="n-b", territorio="CL", actividad="agro", valor="100"),
        ]
        self.assertEqual(indice_krugman(reg_disj, nac_disj).valor, "1")

        # Caso intermedio exacto: [60, 40] vs [20, 80] -> 0.5 * (|0.6-0.2| + |0.4-0.8|) = 0.4.
        reg_mid = [
            va(id="rm-1", territorio="02", actividad="mineria", valor="60", estado="preliminar"),
            va(id="rm-2", territorio="02", actividad="servicios", valor="40"),
        ]
        nac_mid = [
            va(id="nm-1", territorio="CL", actividad="mineria", valor="20"),
            va(id="nm-2", territorio="CL", actividad="servicios", valor="80", clase="estimacion"),
        ]
        res_mid = indice_krugman(reg_mid, nac_mid)
        self.assertEqual(res_mid.valor, "0.4")
        self.assertEqual(res_mid.estado, "preliminar")
        self.assertEqual(res_mid.clase, "estimacion")

        # Precisión 34 independiente del contexto: [1, 2] vs [1, 5] -> 1/6.
        with localcontext() as contexto:
            contexto.prec = 4
            res_prec = indice_krugman(
                [
                    va(id="rp-1", territorio="02", actividad="a", valor="1"),
                    va(id="rp-2", territorio="02", actividad="b", valor="2"),
                ],
                [
                    va(id="np-1", territorio="CL", actividad="a", valor="1"),
                    va(id="np-2", territorio="CL", actividad="b", valor="5"),
                ],
            )
        self.assertEqual(res_prec.valor, "0.1666666666666666666666666666666667")

    def test_indice_krugman_validaciones_duplicados_real_faltantes_y_cero(self):
        reg = [
            va(id="r-1", territorio="02", actividad="mineria", valor="60"),
            va(id="r-2", territorio="02", actividad="servicios", valor="40"),
        ]
        nac = [
            va(id="n-1", territorio="CL", actividad="mineria", valor="20"),
            va(id="n-2", territorio="CL", actividad="servicios", valor="80"),
        ]

        # Conjuntos de actividades distintos.
        res_diff = indice_krugman(reg, [nac[0]])
        self.assertIsNone(res_diff.valor)
        self.assertEqual(res_diff.estado, "faltante")
        self.assertIn("servicios", res_diff.motivo)

        # Actividad duplicada regional o nacional -> error.
        res_dup_r = indice_krugman([reg[0], {**reg[0], "id": "r-dup"}], nac)
        self.assertEqual(res_dup_r.estado, "error")
        self.assertIn("duplicada", res_dup_r.motivo.lower())

        res_dup_n = indice_krugman(reg, [nac[0], {**nac[0], "id": "n-dup"}])
        self.assertEqual(res_dup_n.estado, "error")

        # Valoración real rechazada.
        res_real = indice_krugman(
            [{**f, "valoracion": "real", "anio_referencia": 2018} for f in reg],
            [{**f, "valoracion": "real", "anio_referencia": 2018} for f in nac],
        )
        self.assertIsNone(res_real.valor)
        self.assertIn("no son aditivos", res_real.motivo)

        # Estados suprimido / faltante reportan cobertura.
        res_sup = indice_krugman(
            [reg[0], {**reg[1], "valor": None, "estado": "suprimido"}],
            nac,
        )
        self.assertIsNone(res_sup.valor)
        self.assertEqual(res_sup.estado, "suprimido")
        self.assertIn("3 de 4", res_sup.motivo)

        # Denominador cero (suma regional o nacional igual a cero).
        res_cero = indice_krugman(
            [{**reg[0], "valor": "0"}, {**reg[1], "valor": "0"}],
            nac,
        )
        self.assertIsNone(res_cero.valor)
        self.assertIn("cero", res_cero.motivo)

        # Incompatibilidades de año, publicación, territorio, clasificación, clases, negativos y None.
        self.assertIsNone(indice_krugman(reg, [{**f, "anio": 2023} for f in nac]).valor)
        self.assertIsNone(indice_krugman(reg, [{**f, "publicacion": "otra"} for f in nac]).valor)
        self.assertIsNone(indice_krugman(reg, [{**f, "clasificacion": "ciiu-rev4"} for f in nac]).valor)
        self.assertIsNone(indice_krugman([{**f, "territorio": "CL"} for f in reg], nac).valor)
        self.assertIsNone(indice_krugman([reg[0], {**reg[1], "territorio": "03"}], nac).valor)
        self.assertIsNone(indice_krugman(reg, [{**f, "territorio": "13"} for f in nac]).valor)
        self.assertIsNone(indice_krugman([{**f, "clase": "prueba"} for f in reg], nac).valor)
        self.assertIsNone(indice_krugman([reg[0], {**reg[1], "valor": "-1"}], nac).valor)
        self.assertEqual(indice_krugman([reg[0], None], nac).estado, "error")
        res_none = indice_krugman(reg, None)
        self.assertIsNone(res_none.valor)
        self.assertEqual(res_none.insumos, ("r-1", "r-2"))


if __name__ == "__main__":
    unittest.main()
