"""Pruebas unitarias sin red para el conector oficial MOP Aysén (`mop_proyectos.py`)."""

from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import unittest

DIRECTORIO = Path(__file__).resolve().parent
if str(DIRECTORIO) not in sys.path:
    sys.path.insert(0, str(DIRECTORIO))

import mop_proyectos as mp


def _feature_mop(**overrides) -> dict:
    base = {
        "OBJECTID": 1,
        "SERV_CODIGO": "0204",
        "SERV_NOMBRE": "Dirección de Vialidad",
        "REG_CODIGO": 11,
        "REG_NOMBRE": "Aysén del General Carlos Ibáñez del Campo",
        "COMUNAS": "AYSÉN",
        "CODIGOBIP": " 40031165-0",
        "COD_CONTRATO": 416127,
        "NOM_PROYECTO": "CONSERVACION CAMINOS BASICOS REGION DE AYSEN",
        "NOM_CONTRATO": "Conservación Global Mixta Caminos Red Vial Comuna de Aysén",
        "NUEVOARRASTRE": "A   ",
        "ESTADO_1": "En Ejecución",
        "MONTO_PRESUPUESTADO": 1300000,
        "MONTO_CONTRATO": 1361000,
        "MONTO_AGNO_ACT": 900000,
        "PAGADO": 621400,
        "PAGADO_AGNO_ANT": 250000,
        "SALDO": 489600,
        "CONTRATISTA": "CONSTRUCTORA AUSTRAL SPA",
        "FECHA_INICIO": "16122025",
        "FECHA_TERMINO": "30112026",
        "LINK_FICHA_PROY": "http://sipro.mop.gov.cl/Proyecto/Detalle/56685",
        "LINK_FICHA_CTTO": "http://sipro.mop.gov.cl/Contrato/Detalle/416127",
        "LINK_MERCADO_PUB": "http://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idLicitacion=5283-5-O125",
        "AVANCE_FISICO": 72.02,
        "last_edited_date": 1794820874000,
    }
    base.update(overrides)
    return {"attributes": base}


class MopProyectosTest(unittest.TestCase):
    def test_conversion_exacta_miles_a_millones_con_decimal(self):
        # 1723099.854 miles CLP / 1000 = 1723.099854 millones CLP sin error binario de float
        millones = mp.miles_a_millones_clp("1723099.854")
        self.assertEqual(millones, Decimal("1723.099854"))
        self.assertEqual(mp.formatear_decimal(millones), "1723.099854")

        # Exactitud con decimales repetitivos o montos muy grandes
        grande = mp.miles_a_millones_clp(Decimal("56732178.125"))
        self.assertEqual(grande, Decimal("56732.178125"))
        self.assertEqual(mp.formatear_decimal(grande), "56732.178125")

        # MONTO_CONTRATO == 0 en licitación -> costo_total_contrato_millones = None
        licitacion = mp.normalizar_proyecto_mop(
            _feature_mop(
                COD_CONTRATO=427025,
                ESTADO_1="En Licitación",
                MONTO_CONTRATO=0,
                MONTO_PRESUPUESTADO=56732178,
                MONTO_AGNO_ACT=10,
                PAGADO=0,
                NUEVOARRASTRE="N   ",
                FECHA_INICIO="31122026",
            )
        )
        self.assertIsNone(licitacion["costo_total_contrato_millones"])
        self.assertEqual(licitacion["costo_total_presupuestado_millones"], "56732.178")
        self.assertEqual(licitacion["compromiso_anio_millones"], "0.01")
        self.assertEqual(licitacion["pagado_anio_millones"], "0")

    def test_parseo_fechas_y_clasificacion_administraciones_fronteras(self):
        self.assertEqual(mp.parsear_fecha_mop("16122025"), "2025-12-16")
        self.assertEqual(mp.parsear_fecha_mop("11032026"), "2026-03-11")
        self.assertIsNone(mp.parsear_fecha_mop(""))
        self.assertIsNone(mp.parsear_fecha_mop(None))
        self.assertIsNone(mp.parsear_fecha_mop("00000000"))
        self.assertIsNone(mp.parsear_fecha_mop("31022026"))
        self.assertIsNone(mp.parsear_fecha_mop("invalida"))

        casos = [
            ("2014-03-10", "Administración anterior a 2014"),
            ("2014-03-11", "Administración 2014–2018"),
            ("2018-03-10", "Administración 2014–2018"),
            ("2018-03-11", "Administración 2018–2022"),
            ("2022-03-10", "Administración 2018–2022"),
            ("2022-03-11", "Administración 2022–2026"),
            ("2026-03-10", "Administración 2022–2026"),
            ("2026-03-11", "Administración 2026–2030"),
            ("2027-08-01", "Administración 2026–2030"),
            (None, None),
            ("no-es-fecha", None),
        ]
        for fecha_iso, esperado in casos:
            with self.subTest(fecha=fecha_iso):
                self.assertEqual(mp.clasificar_administracion(fecha_iso), esperado)

    def test_normalizacion_comunas_aysen_y_multicomunales(self):
        self.assertEqual(
            mp.normalizar_comunas("AYSÉN, CHILE CHICO, RIO IBAÑEZ"),
            ["Aysén", "Chile Chico", "Río Ibáñez"],
        )
        self.assertEqual(
            mp.normalizar_comunas("O'HIGGINS, TORTEL, O'HIGGINS"),
            ["O'Higgins", "Tortel"],
        )
        self.assertEqual(
            mp.normalizar_comunas("LAGO VERDE, CISNES, GUAITECAS"),
            ["Lago Verde", "Cisnes", "Guaitecas"],
        )

    def test_deduplicacion_entre_capas_0_1_2_conserva_mayor_completitud(self):
        # El mismo contrato 500001 aparece incompleto en capa 0, repetido en 2 tramos en capa 1,
        # y completo en capa 2. Debe quedar 1 solo registro con los datos más completos.
        capa0 = [
            _feature_mop(
                OBJECTID=10,
                COD_CONTRATO=500001,
                MONTO_CONTRATO=None,
                PAGADO=None,
                FECHA_INICIO="",
                NUEVOARRASTRE="",
            )
        ]
        capa1 = [
            _feature_mop(
                OBJECTID=20,
                COD_CONTRATO=500001,
                MONTO_CONTRATO=2500000,
                MONTO_AGNO_ACT=1000000,
                PAGADO=400000,
                FECHA_INICIO="15052024",
                NUEVOARRASTRE="A   ",
                LINK_MERCADO_PUB=None,
            ),
            _feature_mop(
                OBJECTID=21,
                COD_CONTRATO=500001,
                MONTO_CONTRATO=2500000,
                MONTO_AGNO_ACT=1000000,
                PAGADO=400000,
                FECHA_INICIO="15052024",
                NUEVOARRASTRE="A   ",
                LINK_MERCADO_PUB="http://www.mercadopublico.cl/licitacion/500001",
            ),
        ]
        capa2 = [
            _feature_mop(
                OBJECTID=30,
                COD_CONTRATO=500001,
                MONTO_CONTRATO=2500000,
                MONTO_AGNO_ACT=1000000,
                PAGADO=400000,
                FECHA_INICIO="",
                NUEVOARRASTRE="A   ",
            ),
            _feature_mop(
                OBJECTID=31,
                COD_CONTRATO=500002,
                SERV_NOMBRE="Dirección de Aeropuertos",
                COMUNAS="COYHAIQUE",
            ),
        ]

        dedup, stats = mp.deduplicar_registros_mop([(0, capa0), (1, capa1), (2, capa2)])
        self.assertEqual(stats["total_registros_crudos"], 5)
        self.assertEqual(stats["contratos_unicos"], 2)
        self.assertEqual(stats["duplicados_eliminados"], 3)
        self.assertEqual(len(dedup), 2)

        reg_500001 = next(r for r in dedup if r["id_contrato"] == "500001")
        self.assertEqual(reg_500001["capa_ganadora"], 1)
        self.assertEqual(reg_500001["capas_origen"], [0, 1, 2])
        self.assertEqual(reg_500001["registros_geograficos_origen"], 4)
        self.assertEqual(reg_500001["attributes"]["FECHA_INICIO"], "15052024")
        self.assertEqual(
            reg_500001["attributes"]["LINK_MERCADO_PUB"],
            "http://www.mercadopublico.cl/licitacion/500001",
        )

    def test_separacion_exacta_dos_preguntas_y_aislamiento_insuficientes(self):
        # 1) Arrastre Vialidad firmado en 2025 (antes de 2026-03-11):
        #    compromiso = 600 MM, pagado = 300 MM
        p_arrastre_ant = mp.normalizar_proyecto_mop(
            _feature_mop(
                COD_CONTRATO=101,
                SERV_NOMBRE="Dirección de Vialidad",
                COMUNAS="COYHAIQUE",
                NUEVOARRASTRE="A   ",
                FECHA_INICIO="16122025",
                MONTO_AGNO_ACT=600000,
                PAGADO=300000,
            )
        )
        # 2) Nuevo 2026 de Vialidad PERO firmado el 25-02-2026 (antes de 2026-03-11):
        #    compromiso = 200 MM (NO es arrastre), pagado = 100 MM (SÍ firmado antes de admin actual!)
        p_nuevo_antes_cambio = mp.normalizar_proyecto_mop(
            _feature_mop(
                COD_CONTRATO=102,
                SERV_NOMBRE="Dirección de Vialidad",
                COMUNAS="COYHAIQUE, AYSÉN",
                NUEVOARRASTRE="N   ",
                FECHA_INICIO="25022026",
                MONTO_AGNO_ACT=200000,
                PAGADO=100000,
            )
        )
        # 3) Nuevo 2026 de Aeropuertos firmado el 13-05-2026 (después de 2026-03-11):
        #    compromiso = 200 MM, pagado = 100 MM (admin actual)
        p_nuevo_actual = mp.normalizar_proyecto_mop(
            _feature_mop(
                COD_CONTRATO=103,
                SERV_NOMBRE="Dirección de Aeropuertos",
                COMUNAS="COYHAIQUE",
                NUEVOARRASTRE="N   ",
                FECHA_INICIO="13052026",
                MONTO_AGNO_ACT=200000,
                PAGADO=100000,
            )
        )
        # 4) Insuficiente: sin fecha de inicio ni marca NUEVOARRASTRE, con montos grandes
        #    que NO deben contaminar ninguno de los dos porcentajes.
        p_insuficiente = mp.normalizar_proyecto_mop(
            _feature_mop(
                COD_CONTRATO=104,
                SERV_NOMBRE="Dirección de Vialidad",
                COMUNAS="COYHAIQUE",
                NUEVOARRASTRE="",
                FECHA_INICIO="",
                MONTO_AGNO_ACT=9000000,
                PAGADO=5000000,
            )
        )
        self.assertEqual(p_insuficiente["calidad_informacion"], "insuficiente")
        self.assertIn(
            "falta_fecha_contratacion_y_nuevo_arrastre",
            p_insuficiente["motivos_insuficiencia"],
        )

        # Total MOP Aysén (4 proyectos: 3 documentados, 1 insuficiente)
        resumen = mp.calcular_resumen_proyectos(
            [p_arrastre_ant, p_nuevo_antes_cambio, p_nuevo_actual, p_insuficiente],
            anio_corte=2026,
        )
        self.assertEqual(resumen["proyectos_documentados"], 3)
        self.assertEqual(resumen["proyectos_insuficientes"], 1)

        # Pregunta 1: pagado antes de 2026-03-11 = (300 + 100) / (300 + 100 + 100) = 400 / 500 = 80.00%
        q1 = resumen["pagos_contratos_administraciones_anteriores"]
        self.assertEqual(q1["monto_millones"], "400")
        self.assertEqual(q1["total_pagado_anio_documentado_millones"], "500")
        self.assertEqual(q1["porcentaje"], "80.00")
        self.assertEqual(q1["cantidad_contratos"], 2)

        # Pregunta 2: arrastre = 600 / (600 + 200 + 200) = 600 / 1000 = 60.00%
        q2 = resumen["arrastre_presupuesto_inversion"]
        self.assertEqual(q2["monto_millones"], "600")
        self.assertEqual(q2["total_compromiso_anio_documentado_millones"], "1000")
        self.assertEqual(q2["porcentaje"], "60.00")
        self.assertEqual(q2["cantidad_contratos"], 1)

        # Bloque aislado de información insuficiente
        insuf = resumen["informacion_insuficiente"]
        self.assertEqual(insuf["cantidad_contratos"], 1)
        self.assertEqual(insuf["compromiso_anio_millones"], "9000")
        self.assertEqual(insuf["pagado_anio_millones"], "5000")
        self.assertEqual(insuf["ids_contratos"], ["104"])

        # Reutilización dinámica sobre filtro piloto Vialidad:
        # Vialidad documentados = 101 y 102 -> pagos anteriores = 400/400 = 100.00%, arrastre = 600/800 = 75.00%
        vialidad = [
            p
            for p in [p_arrastre_ant, p_nuevo_antes_cambio, p_nuevo_actual, p_insuficiente]
            if p["es_piloto_vialidad"]
        ]
        res_vial = mp.calcular_resumen_proyectos(vialidad, anio_corte=2026)
        self.assertEqual(res_vial["pagos_contratos_administraciones_anteriores"]["porcentaje"], "100.00")
        self.assertEqual(res_vial["arrastre_presupuesto_inversion"]["porcentaje"], "75.00")
        self.assertEqual(res_vial["informacion_insuficiente"]["cantidad_contratos"], 1)

    def test_frase_radial_y_linea_tiempo_sin_inventar_fechas(self):
        obra = mp.normalizar_proyecto_mop(
            _feature_mop(
                COD_CONTRATO=416127,
                SERV_NOMBRE="Dirección de Vialidad",
                COMUNAS="AYSÉN",
                FECHA_INICIO="16122025",
                FECHA_TERMINO="30112026",
                MONTO_CONTRATO=1361000,
                PAGADO=621400,
                ESTADO_1="En Ejecución",
            ),
            anio_corte=2026,
        )
        self.assertEqual(
            obra["frase_radial"],
            "Esta obra en Aysén fue contratada por la Dirección de Vialidad del MOP "
            "el 16-12-2025 (Administración 2022–2026), tiene un monto contractual de "
            "$1.361,0 millones y durante 2026 registra pagos por $621,4 millones.",
        )

        # Verificar los 4 hitos ordenados y que aprobación no inventa fecha
        hitos = obra["linea_tiempo"]
        self.assertEqual(
            [h["hito"] for h in hitos],
            [
                "aprobacion_financiamiento",
                "contratacion",
                "pagos",
                "entrada_en_funcionamiento",
            ],
        )
        self.assertIsNone(hitos[0]["fecha"])
        self.assertIsNone(hitos[0]["administracion"])
        self.assertEqual(hitos[1]["fecha"], "2025-12-16")
        self.assertEqual(hitos[1]["administracion"], "Administración 2022–2026")
        self.assertEqual(hitos[3]["fecha"], "2026-11-30")
        self.assertEqual(hitos[3]["administracion"], "Administración 2026–2030")
        for hito in hitos:
            for campo in (
                "hito",
                "titulo",
                "fecha",
                "institucion",
                "administracion",
                "detalle",
                "documento_respaldo_label",
                "documento_respaldo_url",
            ):
                self.assertIn(campo, hito)

        # Caso en licitación sin pagos
        licit = mp.normalizar_proyecto_mop(
            _feature_mop(
                COD_CONTRATO=427025,
                ESTADO_1="En Licitación",
                COMUNAS="COYHAIQUE",
                MONTO_CONTRATO=0,
                MONTO_PRESUPUESTADO=56732178,
                PAGADO=0,
                PAGADO_AGNO_ANT=0,
                FECHA_INICIO="31122026",
            ),
            anio_corte=2026,
        )
        self.assertIn("en licitación", licit["frase_radial"])
        self.assertIn("aún no registra pagos", licit["frase_radial"])
        self.assertIsNone(licit["linea_tiempo"][2]["fecha"])

    def test_paginacion_arcgis_y_reproducir_bit_a_bit_con_sha256(self):
        # Simula paginación en capa 1 (2 páginas por exceededTransferLimit=True)
        respuestas = {
            "/0/query": [
                {"features": [_feature_mop(OBJECTID=1, COD_CONTRATO=9001, SERV_NOMBRE="Dirección de Aeropuertos", COMUNAS="COYHAIQUE", NUEVOARRASTRE="A", FECHA_INICIO="09042025", MONTO_AGNO_ACT=500000, PAGADO=250000)]}
            ],
            "/1/query": [
                {
                    "exceededTransferLimit": True,
                    "features": [_feature_mop(OBJECTID=2, COD_CONTRATO=9002, SERV_NOMBRE="Dirección de Vialidad", COMUNAS="AYSÉN", NUEVOARRASTRE="A", FECHA_INICIO="16122025", MONTO_AGNO_ACT=1000000, PAGADO=600000)],
                },
                {
                    "exceededTransferLimit": False,
                    "features": [_feature_mop(OBJECTID=3, COD_CONTRATO=9003, SERV_NOMBRE="Dirección de Vialidad", COMUNAS="COCHRANE, TORTEL", NUEVOARRASTRE="N", FECHA_INICIO="13052026", MONTO_AGNO_ACT=500000, PAGADO=200000)],
                },
            ],
            "/2/query": [
                # Duplicado de 9002 que debe deduplicarse
                {"features": [_feature_mop(OBJECTID=4, COD_CONTRATO=9002, SERV_NOMBRE="Dirección de Vialidad", COMUNAS="AYSÉN", NUEVOARRASTRE="A", FECHA_INICIO="16122025", MONTO_AGNO_ACT=1000000, PAGADO=600000)]}
            ],
        }
        contadores = {k: 0 for k in respuestas}

        def fetcher_simulado(url: str) -> bytes:
            for clave, paginas in respuestas.items():
                if clave in url:
                    idx = contadores[clave]
                    contadores[clave] += 1
                    return json.dumps(paginas[idx], ensure_ascii=False).encode("utf-8")
            raise AssertionError(f"URL inesperada: {url}")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_dir = tmp_path / "mop-aysen-raw"
            salida_1 = tmp_path / "proyectos-1.json"
            salida_2 = tmp_path / "proyectos-2.json"

            res1 = mp.ejecutar_extraccion_mop(
                insumos_dir=raw_dir,
                salida=salida_1,
                anio_corte=2026,
                extraido_en="2026-11-25T02:30:00+00:00",
                fetcher=fetcher_simulado,
            )
            self.assertEqual(contadores["/1/query"], 2)
            self.assertTrue((raw_dir / "manifiesto.json").is_file())
            self.assertTrue((raw_dir / "capa-1-pagina-1.json").is_file())
            self.assertTrue((raw_dir / "capa-1-pagina-2.json").is_file())
            self.assertEqual(res1["deduplicacion"]["total_registros_crudos"], 4)
            self.assertEqual(res1["deduplicacion"]["contratos_unicos"], 3)

            # Reproducir vía CLI --reproducir --insumos sin red
            codigo_salida = mp.main(
                ["--reproducir", "--insumos", str(raw_dir), "--salida", str(salida_2)]
            )
            self.assertEqual(codigo_salida, 0)
            self.assertEqual(salida_1.read_bytes(), salida_2.read_bytes())

            # Si se altera un archivo raw, debe fallar la verificación SHA-256
            archivo_alterado = raw_dir / "capa-0.json"
            archivo_alterado.write_bytes(archivo_alterado.read_bytes() + b" ")
            with self.assertRaises(mp.MopProyectosError) as ctx:
                mp.reproducir_desde_raw(raw_dir, tmp_path / "proyectos-3.json")
            self.assertIn("SHA-256 inválido", str(ctx.exception))


class TestDipresBipAysenLive(unittest.TestCase):
    def test_parsear_trayectoria_plurianual_decimal34_y_reproducir_sha256(self):
        import dipres_bip_live as bip

        csv_2024 = (
            "Año;Mes;Partida;Nombre Partida;Capítulo;Nombre Capítulo;Programa;Nombre Programa;"
            "Región Destino;Nombre Región Destino;Provincia Destino;Nombre Provincia Destino;"
            "Comuna Destino;Nombre Comuna Destino;Moneda;Código BIP;Nombre Proyecto;"
            "Suma de Monto Identificado Ley de Pptos.;Suma de Monto Devengado Ley de Pptos.\n"
            "2024;Diciembre;05;INTERIOR;71;GOBIERNO REGIONAL REGIÓN DE AYSÉN;02;INVERSIÓN REGIONAL;"
            "11;AYSÉN;1;COYHAIQUE;01;Coyhaique;Miles de Pesos;30418427-0;CONSTRUCCION MIRADORES AYSEN;1.000.000;800.000\n"
            # Otra región debe excluirse
            "2024;Diciembre;05;INTERIOR;63;GORE METROPOLITANO;02;INVERSION;"
            "13;METROPOLITANA;1;SANTIAGO;01;Santiago;Miles de Pesos;40000001-0;OTRA REGION;9.000.000;9.000.000\n"
        ).encode("utf-8")
        csv_2025 = (
            "Año;Mes;Partida;Nombre Partida;Capítulo;Nombre Capítulo;Programa;Nombre Programa;"
            "Región Destino;Nombre Región Destino;Provincia Destino;Nombre Provincia Destino;"
            "Comuna Destino;Nombre Comuna Destino;Moneda;Código BIP;Nombre Proyecto;"
            "Suma de Monto Identificado Ley de Pptos.;Suma de Monto Devengado Ley de Pptos.\n"
            "2025;Diciembre;05;INTERIOR;71;GOBIERNO REGIONAL REGIÓN DE AYSÉN;02;INVERSIÓN REGIONAL;"
            "11;AYSÉN;1;COYHAIQUE;01;Coyhaique;Miles de Pesos;30418427-0;CONSTRUCCION MIRADORES AYSEN;2.000.000;1.500.000\n"
            "2025;Diciembre;18;VIVIENDA;31;SERVIU REGIÓN DE AYSÉN;01;SERVIU;"
            "11;AYSÉN;2;AYSÉN;01;Aysén;Miles de Pesos;40055555-0;PARQUE URBANO PUERTO AYSEN;500.000;250.000\n"
        ).encode("utf-8")

        def fake_json(url: str, timeout: int) -> dict:
            return {
                "result": {
                    "results": [
                        {
                            "name": "ejecucion-presupuestaria-de-iniciativas-de-inversion-acumulado-2024",
                            "title": "Ejecución Presupuestaria de Iniciativas de Inversión Acumulado 2024 - Total",
                            "metadata_modified": "2026-07-22",
                            "resources": [{"id": "r24", "name": "Inversiones a Diciembre 2024 en pesos", "url": "https://fake/2024.csv"}],
                        },
                        {
                            "name": "ejecucion-presupuestaria-de-iniciativas-de-inversion-acumulado-2025-total",
                            "title": "Ejecución Presupuestaria de Iniciativas de Inversión Acumulado 2025 - Total",
                            "metadata_modified": "2026-07-22",
                            "resources": [{"id": "r25", "name": "Inversiones a Diciembre 2025 en pesos", "url": "https://fake/2025.csv"}],
                        },
                    ]
                }
            }

        def fake_bytes(url: str, timeout: int) -> bytes:
            return csv_2024 if "2024" in url else csv_2025

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            salida = base / "published" / "proyectos-bip-aysen.json"
            pub = bip.extraer_dipres_bip_live(
                anios=(2024, 2025),
                raw_root=base / "raw",
                salida_path=salida,
                http_get_json=fake_json,
                http_get_bytes=fake_bytes,
                timestamp="20261125T160000Z",
            )
            # 2024 es primer año de la serie -> no infiere arrastre (insuficiente)
            self.assertEqual(pub["resumen_por_anio"]["2024"]["total_iniciativas"], 1)
            self.assertEqual(pub["por_anio"]["2024"][0]["nuevo_o_arrastre"], "sin_dato")

            # 2025: Miradores (30418427-0) es arrastre con 800 MM previos; Parque (40055555-0) es nuevo
            items_25 = {p["codigo_bip"]: p for p in pub["por_anio"]["2025"]}
            self.assertEqual(len(items_25), 2)
            mir = items_25["30418427-0"]
            self.assertEqual(mir["institucion"], "Gobierno Regional de Aysén (FNDR)")
            self.assertEqual(mir["nuevo_o_arrastre"], "arrastre")
            self.assertEqual(mir["compromiso_anio_millones"], "2000.000")
            self.assertEqual(mir["pagado_anio_millones"], "1500.000")
            self.assertEqual(mir["pagado_anios_anteriores_millones"], "800.000")
            self.assertIsNone(mir["fecha_contratacion"])
            self.assertIsNone(mir["firmado_antes_administracion_actual"])

            parque = items_25["40055555-0"]
            self.assertEqual(parque["institucion"], "SERVIU Región de Aysén (MINVU)")
            self.assertEqual(parque["nuevo_o_arrastre"], "nuevo")
            self.assertEqual(parque["comunas"], ["Aysén"])

            # Reproducir sin red y rechazar corrupción SHA-256
            dir_insumos = Path(pub["fuente_trazabilidad"]["directorio_insumos"])
            repro = bip.reproducir_dipres_bip(dir_insumos, salida_path=None)
            self.assertEqual(repro["por_anio"], pub["por_anio"])
            (dir_insumos / "dipres-iniciativas-2025.csv").write_bytes(b"corrupto")
            with self.assertRaises(RuntimeError):
                bip.reproducir_dipres_bip(dir_insumos, salida_path=None)


if __name__ == "__main__":
    unittest.main()
