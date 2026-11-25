/* ============================================================
   DATASET OFICIAL AUDITADO · POR GOBIERNO (VIVIENDA · PARTIDA 18 MINVU)
   Fuentes: DIPRES (datos.gob.cl Ejecución y Ley Inicial/Vigente 2018-2026),
            BCCh SI3 / INE (IPC G073.IPC.IND.2023.M),
            Leyes de Presupuestos 21.289 (2021) a 21.796 (2026) — DIPRES y BCN LeyChile.
   Generado automáticamente desde fuentes oficiales verificadas.
============================================================ */

export type AdminId = 'pinera_2' | 'boric' | 'actual_2026'
export type GlosaCategoriaId = 'limites_uso' | 'requisitos_transferencia' | 'obligaciones_informar'

export interface AdministracionMeta {
  id: AdminId
  nombre: string
  periodo: string
  anios_completos: number[]
  anios_compartidos: number[]
  en_curso: boolean
  anio_referencia_ene_ago: number
  anio_glosa_defecto: number
  color: string
}

export interface ViviendaPresupuestoRow {
  anio: number
  tramo: 'anual_dic' | 'ene_ago'
  corte_etiqueta: string
  fecha_corte: string
  en_curso: boolean
  es_cambio_mando: boolean
  admin_id: string
  admins_involucradas: string[]
  ley_numero: string
  ley_fecha_publicacion: string
  proyecto_presentado_por: string
  ley_aprobada_alcance: string
  administracion_ejecucion: string
  ipc_promedio: number
  factor_pesos_2025: number
  nominal_mm: {
    inicial: number
    vigente: number
    ejecutado: number
    nacional_inicial: number
    nacional_vigente: number
    nacional_ejecutado: number
  }
  real_2025_mm: {
    inicial: number
    vigente: number
    ejecutado: number
  }
  participacion_nacional_pct: {
    inicial: number
    vigente: number
    ejecutado: number
  }
  avance_sobre_vigente_pct: number
  modificacion_vigente_vs_inicial_pct: number
  desglose_ejecutado_real_2025_mm: {
    corriente: number
    inversion: number
    transferencias_capital_subsidios: number
  }
  desglose_ejecutado_nominal_mm: {
    corriente: number
    inversion: number
    transferencias_capital_subsidios: number
  }
  capitulos_ejecutado_nominal_mm: {
    subsecretaria: number
    serviu_regionales: number
    serviu_count: number
    parque_metropolitano: number
  }
  fuentes: {
    ejecucion_url: string
    ejecucion_titulo: string
    ley_vigente_url: string
    ley_vigente_titulo: string
    ley_texto_url: string
    dipres_partida_url: string
  }
}

export interface GlosaVersionAnio {
  anio: number
  disponible: boolean
  ley_numero: string
  tipo_texto: 'ley_vigente' | 'proyecto_ley'
  tipo_texto_etiqueta: string
  fecha_corte: string
  numero_glosa: string
  ubicacion: string
  texto: string
  url: string
  nota_proyecto_vs_ley?: string | null
  sin_dato_motivo?: string | null
}

export interface GlosaFamilia {
  id: string
  titulo: string
  materia: string
  programa_alcance: string
  categorias: GlosaCategoriaId[]
  cambio_numeracion: boolean
  traza_numeracion: string
  a_que_recursos_aplica: string
  que_permite_o_exige: string
  diferencia_practica: string
  nota_evidencia_gasto: string
  versiones: Record<string, GlosaVersionAnio>
}

export interface RestriccionClaveItem {
  id: string
  aspecto_regulado: string
  glosa_id: string
  ubicacion: string
  condicion_endurecida: string
  evidencia_textual: string
  anios_comparar_sugeridos: [number, number]
}

export interface PorGobiernoViviendaData {
  meta: {
    tema_id: string
    tema_nombre: string
    alcance_territorial: string
    advertencia_alcance: string
    partidas_y_programas: string
    clasificacion_gasto: string
    etapa_ejecucion: string
    anio_base_pesos: number
    fuente_ajuste_ipc: string
    denominador_participacion: string
    fecha_actualizacion: string
    corte_en_curso_2026: string
    nota_proyecto_vs_ley_2025: {
      proyecto_url: string
      ley_vigente_url: string
      resumen: string
    }
    vacios_cobertura: string[]
  }
  administraciones: AdministracionMeta[]
  serie_anual_dic: ViviendaPresupuestoRow[]
  serie_equivalente_ene_ago: ViviendaPresupuestoRow[]
  glosas_anios_disponibles: number[]
  glosas_familias: GlosaFamilia[]
  restricciones_clave: RestriccionClaveItem[]
}

export const POR_GOBIERNO_VIVIENDA: PorGobiernoViviendaData = {
  "meta": {
    "tema_id": "vivienda",
    "tema_nombre": "Vivienda y Urbanismo",
    "alcance_territorial": "Presupuesto Nacional de Chile (Gobierno Central · Partida 18 MINVU)",
    "advertencia_alcance": "Cifras nacionales del Gobierno Central (Partida 18 MINVU). No mezclar con el presupuesto regional de Aysén (GORE/Municipios) de la pestaña Vista Política Aysén.",
    "partidas_y_programas": "Partida 18: Ministerio de Vivienda y Urbanismo — Capítulo 01 Subsecretaría de Vivienda y Urbanismo (incl. Asentamientos Precarios y programas centrales), Servicios Regionales de Vivienda y Urbanización (15 SERVIU en 2018; 16 SERVIU desde 2019 por creación de Ñuble) y Parque Metropolitano de Santiago.",
    "clasificacion_gasto": "Gasto presupuestario del Gobierno Central: Subtítulos 21–26 (gasto corriente), 29–31 (activos e iniciativas de inversión) y 33 (transferencias de capital / subsidios habitacionales). Excluye Subtítulo 32 (Préstamos recuperables) y Subtítulo 34 (Servicio de la Deuda) tanto en el numerador MINVU como en el denominador Gobierno Central Total.",
    "etapa_ejecucion": "Gasto ejecutado en etapa Devengado acumulado oficial (informes mensuales y cierre de diciembre de DIPRES).",
    "anio_base_pesos": 2025,
    "fuente_ajuste_ipc": "Índice de Precios al Consumidor (IPC General Nacional empalmado, base anual 2023=100), serie oficial G073.IPC.IND.2023.M del INE / Banco Central de Chile (SI3). Para años completos se usa el IPC promedio anual (ene–dic); para cortes acumulados enero–agosto se usa el IPC promedio enero–agosto de cada año (base enero–agosto 2025).",
    "denominador_participacion": "Presupuesto inicial, presupuesto vigente o gasto ejecutado (devengado) del Gobierno Central Total (suma de todas las partidas nacionales en Subtítulos 21–26, 29–31 y 33) para el mismo año y corte mensual.",
    "fecha_actualizacion": "2026-11-25",
    "corte_en_curso_2026": "Enero–agosto 2026 (mes 8 · último corte acumulado comparable en la serie oficial DIPRES cargada).",
    "nota_proyecto_vs_ley_2025": {
      "proyecto_url": "https://www.dipres.gob.cl/597/articles-346698_doc_pdf.pdf",
      "ley_vigente_url": "https://www.dipres.gob.cl/597/articles-355270_doc_pdf.pdf",
      "resumen": "El Proyecto de Ley 2025 ingresado por el Ejecutivo contenía 17 glosas comunes de instituciones; la Ley N° 21.722 vigente promulgada el 13/12/2024 cerró con 27 glosas (+10 glosas incorporadas en el Congreso, mayoritariamente obligaciones de información territorial)."
    },
    "vacios_cobertura": [
      "En 2018 la Partida 18 registraba 15 SERVIU regionales; desde 2019 incorpora el SERVIU de la Región de Ñuble (16 SERVIU), sin alterar la comparabilidad agregada nacional.",
      "Para la Administración 2026–2030 (en curso) solo existe ejecución oficial parcial acumulada a agosto de 2026 (8 meses), además de ser un año de cambio de mando compartido con la administración anterior; por ello toda comparación con 2026 se realiza exclusivamente contra cortes equivalentes enero–agosto y sin prorratear el año.",
      "El comparador textual de glosas de Partida 18 cubre 2021–2026 con textos oficiales DIPRES (y Art. 23 BCN 2022–2026); para 2018–2020 y Art. 23 de 2021 se informa explícitamente Sin dato disponible."
    ]
  },
  "administraciones": [
    {
      "id": "pinera_2",
      "nombre": "Sebastián Piñera II",
      "periodo": "11 mar 2018 – 11 mar 2022",
      "anios_completos": [
        2019,
        2020,
        2021
      ],
      "anios_compartidos": [
        2018,
        2022
      ],
      "en_curso": false,
      "anio_referencia_ene_ago": 2021,
      "anio_glosa_defecto": 2021,
      "color": "#1b5e8a"
    },
    {
      "id": "boric",
      "nombre": "Gabriel Boric",
      "periodo": "11 mar 2022 – 11 mar 2026",
      "anios_completos": [
        2023,
        2024,
        2025
      ],
      "anios_compartidos": [
        2022,
        2026
      ],
      "en_curso": false,
      "anio_referencia_ene_ago": 2025,
      "anio_glosa_defecto": 2025,
      "color": "#0d6b58"
    },
    {
      "id": "actual_2026",
      "nombre": "Administración 2026–2030 (en curso)",
      "periodo": "Desde 11 mar 2026 (corte agosto 2026)",
      "anios_completos": [],
      "anios_compartidos": [
        2026
      ],
      "en_curso": true,
      "anio_referencia_ene_ago": 2026,
      "anio_glosa_defecto": 2026,
      "color": "#a8561c"
    }
  ],
  "serie_anual_dic": [
    {
      "anio": 2018,
      "tramo": "anual_dic",
      "corte_etiqueta": "Cierre anual diciembre 2018",
      "fecha_corte": "2018-12-31",
      "en_curso": false,
      "es_cambio_mando": true,
      "admin_id": "compartido_2018",
      "admins_involucradas": [
        "bachelet_2",
        "pinera_2"
      ],
      "ley_numero": "Ley N° 21.053",
      "ley_fecha_publicacion": "2017-12-27",
      "proyecto_presentado_por": "Michelle Bachelet II (septiembre 2017)",
      "ley_aprobada_alcance": "Fijó presupuesto inicial Partida 18 MINVU (Subt. directo) por $1.912.505 millones nominales (15 SERVIU; Ñuble aún en Biobío).",
      "administracion_ejecucion": "Año compartido: Michelle Bachelet II (ene–11 mar 2018) y Sebastián Piñera II (11 mar–dic 2018).",
      "ipc_promedio": 75.7618,
      "factor_pesos_2025": 1.4296,
      "nominal_mm": {
        "inicial": 1912504.6,
        "vigente": 1880246.7,
        "ejecutado": 1876543.6,
        "nacional_inicial": 44940276.6,
        "nacional_vigente": 46657033.5,
        "nacional_ejecutado": 45250326.4
      },
      "real_2025_mm": {
        "inicial": 2734037.5,
        "vigente": 2687923.0,
        "ejecutado": 2682629.2
      },
      "participacion_nacional_pct": {
        "inicial": 4.26,
        "vigente": 4.03,
        "ejecutado": 4.15
      },
      "avance_sobre_vigente_pct": 99.8,
      "modificacion_vigente_vs_inicial_pct": -1.7,
      "desglose_ejecutado_real_2025_mm": {
        "corriente": 258725.2,
        "inversion": 538439.2,
        "transferencias_capital_subsidios": 1885464.7
      },
      "desglose_ejecutado_nominal_mm": {
        "corriente": 180982.6,
        "inversion": 376647.2,
        "transferencias_capital_subsidios": 1318913.9
      },
      "capitulos_ejecutado_nominal_mm": {
        "subsecretaria": 221242.3,
        "serviu_regionales": 1625599.6,
        "serviu_count": 15,
        "parque_metropolitano": 29701.7
      },
      "fuentes": {
        "ejecucion_url": "https://datos.gob.cl/dataset/ejecucion-presupuestaria-a-diciembre-de-2018-del-gobierno-central",
        "ejecucion_titulo": "Ejecución Presupuestaria a Diciembre de 2018 del Gobierno Central",
        "ley_vigente_url": "https://datos.gob.cl/dataset/ley-de-presupuestos-inicial-y-vigente-a-diciembre-de-2018-del-gobierno-central",
        "ley_vigente_titulo": "Ley de Presupuestos Inicial y Vigente a Diciembre de 2018 del Gobierno Central",
        "ley_texto_url": "https://www.bcn.cl/leychile/navegar?idNorma=1112770",
        "dipres_partida_url": "https://www.dipres.gob.cl/597/w3-multipropertyvalues-14766-24043.html"
      }
    },
    {
      "anio": 2019,
      "tramo": "anual_dic",
      "corte_etiqueta": "Cierre anual diciembre 2019",
      "fecha_corte": "2019-12-31",
      "en_curso": false,
      "es_cambio_mando": false,
      "admin_id": "pinera_2",
      "admins_involucradas": [
        "pinera_2"
      ],
      "ley_numero": "Ley N° 21.125",
      "ley_fecha_publicacion": "2018-12-28",
      "proyecto_presentado_por": "Sebastián Piñera II (septiembre 2018)",
      "ley_aprobada_alcance": "Fijó presupuesto inicial Partida 18 MINVU por $2.063.342 millones nominales (incorpora SERVIU Ñuble: 16 SERVIU regionales).",
      "administracion_ejecucion": "Sebastián Piñera II (año completo).",
      "ipc_promedio": 77.4701,
      "factor_pesos_2025": 1.398,
      "nominal_mm": {
        "inicial": 2063341.9,
        "vigente": 2231547.6,
        "ejecutado": 2227261.3,
        "nacional_inicial": 47105007.5,
        "nacional_vigente": 49300402.6,
        "nacional_ejecutado": 48799598.7
      },
      "real_2025_mm": {
        "inicial": 2884626.3,
        "vigente": 3119783.8,
        "ejecutado": 3113791.5
      },
      "participacion_nacional_pct": {
        "inicial": 4.38,
        "vigente": 4.53,
        "ejecutado": 4.56
      },
      "avance_sobre_vigente_pct": 99.8,
      "modificacion_vigente_vs_inicial_pct": 8.2,
      "desglose_ejecutado_real_2025_mm": {
        "corriente": 269799.4,
        "inversion": 575329.4,
        "transferencias_capital_subsidios": 2268662.6
      },
      "desglose_ejecutado_nominal_mm": {
        "corriente": 192984.6,
        "inversion": 411526.9,
        "transferencias_capital_subsidios": 1622749.8
      },
      "capitulos_ejecutado_nominal_mm": {
        "subsecretaria": 243714.7,
        "serviu_regionales": 1951073.4,
        "serviu_count": 16,
        "parque_metropolitano": 32473.2
      },
      "fuentes": {
        "ejecucion_url": "https://datos.gob.cl/dataset/ejecucion-presupuestaria-a-diciembre-de-2019-del-gobierno-central",
        "ejecucion_titulo": "Ejecución Presupuestaria a Diciembre de 2019 del Gobierno Central",
        "ley_vigente_url": "https://datos.gob.cl/dataset/ley-de-presupuestos-inicial-y-vigente-a-diciembre-de-2019-del-gobierno-central",
        "ley_vigente_titulo": "Ley de Presupuestos Inicial y Vigente a Diciembre de 2019 del Gobierno Central",
        "ley_texto_url": "https://www.bcn.cl/leychile/navegar?idNorma=1127149",
        "dipres_partida_url": "https://www.dipres.gob.cl/597/w3-multipropertyvalues-14766-24532.html"
      }
    },
    {
      "anio": 2020,
      "tramo": "anual_dic",
      "corte_etiqueta": "Cierre anual diciembre 2020",
      "fecha_corte": "2020-12-31",
      "en_curso": false,
      "es_cambio_mando": false,
      "admin_id": "pinera_2",
      "admins_involucradas": [
        "pinera_2"
      ],
      "ley_numero": "Ley N° 21.192",
      "ley_fecha_publicacion": "2019-12-19",
      "proyecto_presentado_por": "Sebastián Piñera II (septiembre 2019)",
      "ley_aprobada_alcance": "Fijó presupuesto inicial Partida 18 MINVU por $2.191.501 millones nominales (modificado durante pandemia COVID-19).",
      "administracion_ejecucion": "Sebastián Piñera II (año completo).",
      "ipc_promedio": 79.8294,
      "factor_pesos_2025": 1.3567,
      "nominal_mm": {
        "inicial": 2191501.5,
        "vigente": 2286332.2,
        "ejecutado": 2267016.7,
        "nacional_inicial": 50978516.8,
        "nacional_vigente": 56895316.0,
        "nacional_ejecutado": 57056789.7
      },
      "real_2025_mm": {
        "inicial": 2973246.3,
        "vigente": 3101904.8,
        "ejecutado": 3075699.1
      },
      "participacion_nacional_pct": {
        "inicial": 4.3,
        "vigente": 4.02,
        "ejecutado": 3.97
      },
      "avance_sobre_vigente_pct": 99.2,
      "modificacion_vigente_vs_inicial_pct": 4.3,
      "desglose_ejecutado_real_2025_mm": {
        "corriente": 295988.2,
        "inversion": 525816.3,
        "transferencias_capital_subsidios": 2253894.7
      },
      "desglose_ejecutado_nominal_mm": {
        "corriente": 218165.1,
        "inversion": 387565.3,
        "transferencias_capital_subsidios": 1661286.3
      },
      "capitulos_ejecutado_nominal_mm": {
        "subsecretaria": 287871.9,
        "serviu_regionales": 1943774.2,
        "serviu_count": 16,
        "parque_metropolitano": 35370.6
      },
      "fuentes": {
        "ejecucion_url": "https://datos.gob.cl/dataset/ejecucion-presupuestaria-a-diciembre-de-2020-del-gobierno-central",
        "ejecucion_titulo": "Ejecución Presupuestaria a Diciembre de 2020 del Gobierno Central",
        "ley_vigente_url": "https://datos.gob.cl/dataset/ley-de-presupuestos-inicial-y-vigente-a-diciembre-de-2020-del-gobierno-central",
        "ley_vigente_titulo": "Ley de Presupuestos Inicial y Vigente a Diciembre de 2020 del Gobierno Central",
        "ley_texto_url": "https://www.bcn.cl/leychile/navegar?idNorma=1140219",
        "dipres_partida_url": "https://www.dipres.gob.cl/597/w3-multipropertyvalues-14766-25190.html"
      }
    },
    {
      "anio": 2021,
      "tramo": "anual_dic",
      "corte_etiqueta": "Cierre anual diciembre 2021",
      "fecha_corte": "2021-12-31",
      "en_curso": false,
      "es_cambio_mando": false,
      "admin_id": "pinera_2",
      "admins_involucradas": [
        "pinera_2"
      ],
      "ley_numero": "Ley N° 21.289",
      "ley_fecha_publicacion": "2020-12-16",
      "proyecto_presentado_por": "Sebastián Piñera II (septiembre 2020)",
      "ley_aprobada_alcance": "Fijó presupuesto inicial Partida 18 MINVU por $2.709.957 millones nominales; Glosa 11 fijó tope de 15% del FSEV para compra de terrenos.",
      "administracion_ejecucion": "Sebastián Piñera II (año completo).",
      "ipc_promedio": 83.4407,
      "factor_pesos_2025": 1.298,
      "nominal_mm": {
        "inicial": 2709957.4,
        "vigente": 2504746.0,
        "ejecutado": 2557308.1,
        "nacional_inicial": 56476420.4,
        "nacional_vigente": 58635093.8,
        "nacional_ejecutado": 77690324.9
      },
      "real_2025_mm": {
        "inicial": 3517522.3,
        "vigente": 3251158.1,
        "ejecutado": 3319383.7
      },
      "participacion_nacional_pct": {
        "inicial": 4.8,
        "vigente": 4.27,
        "ejecutado": 3.29
      },
      "avance_sobre_vigente_pct": 102.1,
      "modificacion_vigente_vs_inicial_pct": -7.6,
      "desglose_ejecutado_real_2025_mm": {
        "corriente": 264926.3,
        "inversion": 642194.3,
        "transferencias_capital_subsidios": 2412263.1
      },
      "desglose_ejecutado_nominal_mm": {
        "corriente": 204103.6,
        "inversion": 494757.1,
        "transferencias_capital_subsidios": 1858447.4
      },
      "capitulos_ejecutado_nominal_mm": {
        "subsecretaria": 320993.9,
        "serviu_regionales": 2196161.3,
        "serviu_count": 16,
        "parque_metropolitano": 40152.9
      },
      "fuentes": {
        "ejecucion_url": "https://datos.gob.cl/dataset/ejecucion-presupuestaria-a-diciembre-de-2021-del-gobierno-central-ejecucion-total",
        "ejecucion_titulo": "Ejecución Presupuestaria a Diciembre de 2021 del Gobierno Central - Ejecución Total",
        "ley_vigente_url": "https://datos.gob.cl/dataset/ley-de-presupuestos-inicial-y-vigente-a-diciembre-de-2021-del-gobierno-central-ley-regular",
        "ley_vigente_titulo": "Ley de Presupuestos Inicial y Vigente a Diciembre de 2021 del Gobierno Central - Ley Regular",
        "ley_texto_url": "https://www.dipres.gob.cl/597/articles-213658_doc_pdf.pdf",
        "dipres_partida_url": "https://www.dipres.gob.cl/597/articles-213658_doc_pdf.pdf"
      }
    },
    {
      "anio": 2022,
      "tramo": "anual_dic",
      "corte_etiqueta": "Cierre anual diciembre 2022",
      "fecha_corte": "2022-12-31",
      "en_curso": false,
      "es_cambio_mando": true,
      "admin_id": "compartido_2022",
      "admins_involucradas": [
        "pinera_2",
        "boric"
      ],
      "ley_numero": "Ley N° 21.395",
      "ley_fecha_publicacion": "2021-12-15",
      "proyecto_presentado_por": "Sebastián Piñera II (septiembre 2021)",
      "ley_aprobada_alcance": "Fijó presupuesto inicial Partida 18 MINVU por $2.974.345 millones nominales; redujo tope FSEV para compra de terrenos de 15% a 5% (Glosa 11).",
      "administracion_ejecucion": "Año compartido: Sebastián Piñera II (ene–11 mar 2022) y Gabriel Boric (11 mar–dic 2022).",
      "ipc_promedio": 93.1562,
      "factor_pesos_2025": 1.1626,
      "nominal_mm": {
        "inicial": 2974344.6,
        "vigente": 2820927.8,
        "ejecutado": 2994032.4,
        "nacional_inicial": 59397413.6,
        "nacional_vigente": 66084408.8,
        "nacional_ejecutado": 66975322.2
      },
      "real_2025_mm": {
        "inicial": 3458054.2,
        "vigente": 3279687.7,
        "ejecutado": 3480943.8
      },
      "participacion_nacional_pct": {
        "inicial": 5.01,
        "vigente": 4.27,
        "ejecutado": 4.47
      },
      "avance_sobre_vigente_pct": 106.1,
      "modificacion_vigente_vs_inicial_pct": -5.2,
      "desglose_ejecutado_real_2025_mm": {
        "corriente": 245627.6,
        "inversion": 669537.1,
        "transferencias_capital_subsidios": 2565779.0
      },
      "desglose_ejecutado_nominal_mm": {
        "corriente": 211269.4,
        "inversion": 575882.9,
        "transferencias_capital_subsidios": 2206880.1
      },
      "capitulos_ejecutado_nominal_mm": {
        "subsecretaria": 286984.8,
        "serviu_regionales": 2673458.9,
        "serviu_count": 16,
        "parque_metropolitano": 33588.6
      },
      "fuentes": {
        "ejecucion_url": "https://datos.gob.cl/dataset/ejecucion-presupuestaria-a-diciembre-de-2022-del-gobierno-central-ejecucion-total",
        "ejecucion_titulo": "Ejecución Presupuestaria a Diciembre de 2022 del Gobierno Central - Ejecución Total",
        "ley_vigente_url": "https://datos.gob.cl/dataset/ley-de-presupuestos-inicial-y-vigente-a-diciembre-de-2022-del-gobierno-central-ley-regular",
        "ley_vigente_titulo": "Ley de Presupuestos Inicial y Vigente a Diciembre de 2022 del Gobierno Central - Ley Regular",
        "ley_texto_url": "https://www.bcn.cl/leychile/navegar?i=1169723",
        "dipres_partida_url": "https://www.dipres.gob.cl/597/articles-257470_doc_pdf.pdf"
      }
    },
    {
      "anio": 2023,
      "tramo": "anual_dic",
      "corte_etiqueta": "Cierre anual diciembre 2023",
      "fecha_corte": "2023-12-31",
      "en_curso": false,
      "es_cambio_mando": false,
      "admin_id": "boric",
      "admins_involucradas": [
        "boric"
      ],
      "ley_numero": "Ley N° 21.516",
      "ley_fecha_publicacion": "2022-12-20",
      "proyecto_presentado_por": "Gabriel Boric (septiembre 2022)",
      "ley_aprobada_alcance": "Fijó presupuesto inicial Partida 18 MINVU por $3.155.391 millones nominales; subió cupo Leasing a 5.000 (Glosa 01) y tope compra terrenos a 10% incluyendo DS 19 (Glosa 09).",
      "administracion_ejecucion": "Gabriel Boric (año completo).",
      "ipc_promedio": 100.0,
      "factor_pesos_2025": 1.0831,
      "nominal_mm": {
        "inicial": 3155391.3,
        "vigente": 3169316.4,
        "ejecutado": 3136112.7,
        "nacional_inicial": 70289527.4,
        "nacional_vigente": 72649515.9,
        "nacional_ejecutado": 70210708.5
      },
      "real_2025_mm": {
        "inicial": 3417476.0,
        "vigente": 3432557.6,
        "ejecutado": 3396596.0
      },
      "participacion_nacional_pct": {
        "inicial": 4.49,
        "vigente": 4.36,
        "ejecutado": 4.47
      },
      "avance_sobre_vigente_pct": 99.0,
      "modificacion_vigente_vs_inicial_pct": 0.4,
      "desglose_ejecutado_real_2025_mm": {
        "corriente": 255547.1,
        "inversion": 429373.3,
        "transferencias_capital_subsidios": 2711675.6
      },
      "desglose_ejecutado_nominal_mm": {
        "corriente": 235949.3,
        "inversion": 396444.9,
        "transferencias_capital_subsidios": 2503718.5
      },
      "capitulos_ejecutado_nominal_mm": {
        "subsecretaria": 302127.4,
        "serviu_regionales": 2800072.9,
        "serviu_count": 16,
        "parque_metropolitano": 33912.3
      },
      "fuentes": {
        "ejecucion_url": "https://datos.gob.cl/dataset/ejecucion-presupuestaria-a-diciembre-de-2023-del-gobierno-central",
        "ejecucion_titulo": "Ejecución Presupuestaria a Diciembre de 2023 del Gobierno Central",
        "ley_vigente_url": "https://datos.gob.cl/dataset/ley-de-presupuestos-inicial-y-vigente-a-diciembre-de-2023-del-gobierno-central",
        "ley_vigente_titulo": "Ley de Presupuestos Inicial y Vigente a Diciembre de 2023 del Gobierno Central",
        "ley_texto_url": "https://www.bcn.cl/leychile/navegar?idNorma=1186683",
        "dipres_partida_url": "https://www.dipres.gob.cl/597/articles-299419_doc_pdf.pdf"
      }
    },
    {
      "anio": 2024,
      "tramo": "anual_dic",
      "corte_etiqueta": "Cierre anual diciembre 2024",
      "fecha_corte": "2024-12-31",
      "en_curso": false,
      "es_cambio_mando": false,
      "admin_id": "boric",
      "admins_involucradas": [
        "boric"
      ],
      "ley_numero": "Ley N° 21.640",
      "ley_fecha_publicacion": "2023-12-18",
      "proyecto_presentado_por": "Gabriel Boric (septiembre 2023)",
      "ley_aprobada_alcance": "Fijó presupuesto inicial Partida 18 MINVU por $3.565.006 millones nominales; endureció Art. 23–25 sobre transferencias corrientes y de capital a privados y fijó sub-tope de 1% en estudios preliminares de terrenos (Glosa 08).",
      "administracion_ejecucion": "Gabriel Boric (año completo).",
      "ipc_promedio": 103.9256,
      "factor_pesos_2025": 1.0421,
      "nominal_mm": {
        "inicial": 3565006.2,
        "vigente": 3611703.3,
        "ejecutado": 3587693.1,
        "nacional_inicial": 76021287.5,
        "nacional_vigente": 74557394.5,
        "nacional_ejecutado": 74018614.3
      },
      "real_2025_mm": {
        "inicial": 3715267.1,
        "vigente": 3763932.4,
        "ejecutado": 3738910.3
      },
      "participacion_nacional_pct": {
        "inicial": 4.69,
        "vigente": 4.84,
        "ejecutado": 4.85
      },
      "avance_sobre_vigente_pct": 99.3,
      "modificacion_vigente_vs_inicial_pct": 1.3,
      "desglose_ejecutado_real_2025_mm": {
        "corriente": 286584.7,
        "inversion": 424961.7,
        "transferencias_capital_subsidios": 3027363.8
      },
      "desglose_ejecutado_nominal_mm": {
        "corriente": 274994.1,
        "inversion": 407774.4,
        "transferencias_capital_subsidios": 2904924.6
      },
      "capitulos_ejecutado_nominal_mm": {
        "subsecretaria": 350828.2,
        "serviu_regionales": 3196484.2,
        "serviu_count": 16,
        "parque_metropolitano": 40380.7
      },
      "fuentes": {
        "ejecucion_url": "https://datos.gob.cl/dataset/ejecucion-presupuestaria-a-diciembre-de-2024-del-gobierno-central---total",
        "ejecucion_titulo": "Ejecución Presupuestaria a Diciembre de 2024 del Gobierno Central - Total",
        "ley_vigente_url": "https://datos.gob.cl/dataset/ley-de-presupuestos-inicial-y-vigente-a-diciembre-de-2024-del-gobierno-central---ley-regular",
        "ley_vigente_titulo": "Ley de Presupuestos Inicial y Vigente a Diciembre de 2024 del Gobierno Central - Ley Regular",
        "ley_texto_url": "https://www.bcn.cl/leychile/navegar?idNorma=1199318",
        "dipres_partida_url": "https://www.dipres.gob.cl/597/articles-325504_doc_pdf.pdf"
      }
    },
    {
      "anio": 2025,
      "tramo": "anual_dic",
      "corte_etiqueta": "Cierre anual diciembre 2025",
      "fecha_corte": "2025-12-31",
      "en_curso": false,
      "es_cambio_mando": false,
      "admin_id": "boric",
      "admins_involucradas": [
        "boric"
      ],
      "ley_numero": "Ley N° 21.722",
      "ley_fecha_publicacion": "2024-12-13",
      "proyecto_presentado_por": "Gabriel Boric (septiembre 2024)",
      "ley_aprobada_alcance": "Fijó presupuesto inicial Partida 18 MINVU por $3.983.317 millones nominales; el Congreso agregó 10 glosas respecto del Proyecto de Ley (de 17 a 27 glosas institucionales).",
      "administracion_ejecucion": "Gabriel Boric (año completo).",
      "ipc_promedio": 108.3059,
      "factor_pesos_2025": 1.0,
      "nominal_mm": {
        "inicial": 3983316.8,
        "vigente": 3987868.6,
        "ejecutado": 3972398.7,
        "nacional_inicial": 80198973.2,
        "nacional_vigente": 80760814.1,
        "nacional_ejecutado": 79524216.5
      },
      "real_2025_mm": {
        "inicial": 3983316.8,
        "vigente": 3987868.6,
        "ejecutado": 3972398.7
      },
      "participacion_nacional_pct": {
        "inicial": 4.97,
        "vigente": 4.94,
        "ejecutado": 5.0
      },
      "avance_sobre_vigente_pct": 99.6,
      "modificacion_vigente_vs_inicial_pct": 0.1,
      "desglose_ejecutado_real_2025_mm": {
        "corriente": 279911.3,
        "inversion": 460813.4,
        "transferencias_capital_subsidios": 3231674.0
      },
      "desglose_ejecutado_nominal_mm": {
        "corriente": 279911.3,
        "inversion": 460813.4,
        "transferencias_capital_subsidios": 3231674.0
      },
      "capitulos_ejecutado_nominal_mm": {
        "subsecretaria": 382969.8,
        "serviu_regionales": 3545855.5,
        "serviu_count": 16,
        "parque_metropolitano": 43891.7
      },
      "fuentes": {
        "ejecucion_url": "https://datos.gob.cl/dataset/ejecucion-presupuestaria-a-diciembre-de-2025-del-gobierno-central-total",
        "ejecucion_titulo": "Ejecución Presupuestaria a Diciembre de 2025 del Gobierno Central - Total",
        "ley_vigente_url": "https://datos.gob.cl/dataset/ley-de-presupuestos-inicial-y-vigente-a-diciembre-de-2025-del-gobierno-central-ley-regular",
        "ley_vigente_titulo": "Ley de Presupuestos Inicial y Vigente a Diciembre de 2025 del Gobierno Central - Ley Regular",
        "ley_texto_url": "https://www.bcn.cl/leychile/navegar?i=1209325",
        "dipres_partida_url": "https://www.dipres.gob.cl/597/articles-355270_doc_pdf.pdf"
      }
    }
  ],
  "serie_equivalente_ene_ago": [
    {
      "anio": 2021,
      "tramo": "ene_ago",
      "corte_etiqueta": "Enero–agosto 2021 (mes 8)",
      "fecha_corte": "2021-08-31",
      "en_curso": false,
      "es_cambio_mando": false,
      "admin_id": "pinera_2",
      "admins_involucradas": [
        "pinera_2"
      ],
      "ley_numero": "Ley N° 21.289",
      "ley_fecha_publicacion": "2020-12-16",
      "proyecto_presentado_por": "Sebastián Piñera II (septiembre 2020)",
      "ley_aprobada_alcance": "Fijó presupuesto inicial Partida 18 MINVU por $2.709.957 millones nominales; Glosa 11 fijó tope de 15% del FSEV para compra de terrenos.",
      "administracion_ejecucion": "Sebastián Piñera II (año completo).",
      "ipc_promedio": 82.328,
      "factor_pesos_2025": 1.3097,
      "nominal_mm": {
        "inicial": 2709957.4,
        "vigente": 2398423.8,
        "ejecutado": 1480115.0,
        "nacional_inicial": 56476420.4,
        "nacional_vigente": 54429721.5,
        "nacional_ejecutado": 47404759.8
      },
      "real_2025_mm": {
        "inicial": 3549244.1,
        "vigente": 3141227.1,
        "ejecutado": 1938513.6
      },
      "participacion_nacional_pct": {
        "inicial": 4.8,
        "vigente": 4.41,
        "ejecutado": 3.12
      },
      "avance_sobre_vigente_pct": 61.7,
      "modificacion_vigente_vs_inicial_pct": -11.5,
      "desglose_ejecutado_real_2025_mm": {
        "corriente": 167341.2,
        "inversion": 331302.1,
        "transferencias_capital_subsidios": 1439870.3
      },
      "desglose_ejecutado_nominal_mm": {
        "corriente": 127770.2,
        "inversion": 252959.4,
        "transferencias_capital_subsidios": 1099385.4
      },
      "capitulos_ejecutado_nominal_mm": {
        "subsecretaria": 203833.3,
        "serviu_regionales": 1255384.1,
        "serviu_count": 16,
        "parque_metropolitano": 20897.6
      },
      "fuentes": {
        "ejecucion_url": "https://datos.gob.cl/dataset/ejecucion-presupuestaria-a-agosto-de-2021-del-gobierno-central-ejecucion-total",
        "ejecucion_titulo": "Ejecución Presupuestaria a Agosto de 2021 del Gobierno Central - Ejecución Total",
        "ley_vigente_url": "https://datos.gob.cl/dataset/ley-de-presupuestos-inicial-y-vigente-a-agosto-de-2021-del-gobierno-central-ley-regular",
        "ley_vigente_titulo": "Ley de Presupuestos Inicial y Vigente a Agosto de 2021 del Gobierno Central - Ley Regular",
        "ley_texto_url": "https://www.dipres.gob.cl/597/articles-213658_doc_pdf.pdf",
        "dipres_partida_url": "https://www.dipres.gob.cl/597/articles-213658_doc_pdf.pdf"
      }
    },
    {
      "anio": 2022,
      "tramo": "ene_ago",
      "corte_etiqueta": "Enero–agosto 2022 (mes 8)",
      "fecha_corte": "2022-08-31",
      "en_curso": false,
      "es_cambio_mando": true,
      "admin_id": "compartido_2022",
      "admins_involucradas": [
        "pinera_2",
        "boric"
      ],
      "ley_numero": "Ley N° 21.395",
      "ley_fecha_publicacion": "2021-12-15",
      "proyecto_presentado_por": "Sebastián Piñera II (septiembre 2021)",
      "ley_aprobada_alcance": "Fijó presupuesto inicial Partida 18 MINVU por $2.974.345 millones nominales; redujo tope FSEV para compra de terrenos de 15% a 5% (Glosa 11).",
      "administracion_ejecucion": "Año compartido: Sebastián Piñera II (ene–11 mar 2022) y Gabriel Boric (11 mar–dic 2022).",
      "ipc_promedio": 91.2634,
      "factor_pesos_2025": 1.1815,
      "nominal_mm": {
        "inicial": 2974344.6,
        "vigente": 2716860.0,
        "ejecutado": 1592939.2,
        "nacional_inicial": 59397413.6,
        "nacional_vigente": 57086618.6,
        "nacional_ejecutado": 46522149.6
      },
      "real_2025_mm": {
        "inicial": 3514111.4,
        "vigente": 3209900.1,
        "ejecutado": 1882016.6
      },
      "participacion_nacional_pct": {
        "inicial": 5.01,
        "vigente": 4.76,
        "ejecutado": 3.42
      },
      "avance_sobre_vigente_pct": 58.6,
      "modificacion_vigente_vs_inicial_pct": -8.7,
      "desglose_ejecutado_real_2025_mm": {
        "corriente": 148414.1,
        "inversion": 241244.6,
        "transferencias_capital_subsidios": 1492357.9
      },
      "desglose_ejecutado_nominal_mm": {
        "corriente": 125617.8,
        "inversion": 204189.5,
        "transferencias_capital_subsidios": 1263132.0
      },
      "capitulos_ejecutado_nominal_mm": {
        "subsecretaria": 169612.3,
        "serviu_regionales": 1405165.4,
        "serviu_count": 16,
        "parque_metropolitano": 18161.5
      },
      "fuentes": {
        "ejecucion_url": "https://datos.gob.cl/dataset/ejecucion-presupuestaria-a-agosto-de-2022-del-gobierno-central-ejecucion-total",
        "ejecucion_titulo": "Ejecución Presupuestaria a Agosto de 2022 del Gobierno Central - Ejecución Total",
        "ley_vigente_url": "https://datos.gob.cl/dataset/ley-de-presupuestos-inicial-y-vigente-a-agosto-de-2022-del-gobierno-central-ley-regular",
        "ley_vigente_titulo": "Ley de Presupuestos Inicial y Vigente a Agosto de 2022 del Gobierno Central - Ley Regular",
        "ley_texto_url": "https://www.bcn.cl/leychile/navegar?i=1169723",
        "dipres_partida_url": "https://www.dipres.gob.cl/597/articles-257470_doc_pdf.pdf"
      }
    },
    {
      "anio": 2025,
      "tramo": "ene_ago",
      "corte_etiqueta": "Enero–agosto 2025 (mes 8)",
      "fecha_corte": "2025-08-31",
      "en_curso": false,
      "es_cambio_mando": false,
      "admin_id": "boric",
      "admins_involucradas": [
        "boric"
      ],
      "ley_numero": "Ley N° 21.722",
      "ley_fecha_publicacion": "2024-12-13",
      "proyecto_presentado_por": "Gabriel Boric (septiembre 2024)",
      "ley_aprobada_alcance": "Fijó presupuesto inicial Partida 18 MINVU por $3.983.317 millones nominales; el Congreso agregó 10 glosas respecto del Proyecto de Ley (de 17 a 27 glosas institucionales).",
      "administracion_ejecucion": "Gabriel Boric (año completo).",
      "ipc_promedio": 107.8253,
      "factor_pesos_2025": 1.0,
      "nominal_mm": {
        "inicial": 3983316.8,
        "vigente": 3988826.1,
        "ejecutado": 2387478.6,
        "nacional_inicial": 80198973.2,
        "nacional_vigente": 80040448.0,
        "nacional_ejecutado": 52452735.1
      },
      "real_2025_mm": {
        "inicial": 3983316.8,
        "vigente": 3988826.1,
        "ejecutado": 2387478.6
      },
      "participacion_nacional_pct": {
        "inicial": 4.97,
        "vigente": 4.98,
        "ejecutado": 4.55
      },
      "avance_sobre_vigente_pct": 59.9,
      "modificacion_vigente_vs_inicial_pct": 0.1,
      "desglose_ejecutado_real_2025_mm": {
        "corriente": 167314.1,
        "inversion": 262916.6,
        "transferencias_capital_subsidios": 1957247.9
      },
      "desglose_ejecutado_nominal_mm": {
        "corriente": 167314.1,
        "inversion": 262916.6,
        "transferencias_capital_subsidios": 1957247.9
      },
      "capitulos_ejecutado_nominal_mm": {
        "subsecretaria": 234986.2,
        "serviu_regionales": 2127058.8,
        "serviu_count": 16,
        "parque_metropolitano": 25433.5
      },
      "fuentes": {
        "ejecucion_url": "https://datos.gob.cl/dataset/ejecucion-presupuestaria-a-agosto-de-2025-del-gobierno-central-total",
        "ejecucion_titulo": "Ejecución Presupuestaria a Agosto de 2025 del Gobierno Central - Total",
        "ley_vigente_url": "https://datos.gob.cl/dataset/ley-de-presupuestos-inicial-y-vigente-a-agosto-de-2025-del-gobierno-central-ley-regular",
        "ley_vigente_titulo": "Ley de Presupuestos Inicial y Vigente a Agosto de 2025 del Gobierno Central - Ley Regular",
        "ley_texto_url": "https://www.bcn.cl/leychile/navegar?i=1209325",
        "dipres_partida_url": "https://www.dipres.gob.cl/597/articles-355270_doc_pdf.pdf"
      }
    },
    {
      "anio": 2026,
      "tramo": "ene_ago",
      "corte_etiqueta": "Enero–agosto 2026 (mes 8)",
      "fecha_corte": "2026-08-31",
      "en_curso": true,
      "es_cambio_mando": true,
      "admin_id": "compartido_2026",
      "admins_involucradas": [
        "boric",
        "actual_2026"
      ],
      "ley_numero": "Ley N° 21.796",
      "ley_fecha_publicacion": "2025-12-12",
      "proyecto_presentado_por": "Gabriel Boric (septiembre 2025)",
      "ley_aprobada_alcance": "Fijó presupuesto inicial Partida 18 MINVU por $4.414.712 millones nominales; eliminó préstamos Subt. 32 a municipalidades y para compra de terreno (Glosa 06) y exigió visación previa DIPRES para compra de terrenos FSEV/DS 19 (Glosa 25).",
      "administracion_ejecucion": "Año compartido (en curso, corte agosto 2026): Gabriel Boric (ene–11 mar 2026) y Administración 2026–2030 (desde 11 mar 2026).",
      "ipc_promedio": 111.5815,
      "factor_pesos_2025": 0.9663,
      "nominal_mm": {
        "inicial": 4414712.2,
        "vigente": 4353069.3,
        "ejecutado": 2576017.8,
        "nacional_inicial": 83475813.4,
        "nacional_vigente": 82601956.2,
        "nacional_ejecutado": 57401559.1
      },
      "real_2025_mm": {
        "inicial": 4266099.0,
        "vigente": 4206531.1,
        "ejecutado": 2489300.8
      },
      "participacion_nacional_pct": {
        "inicial": 5.29,
        "vigente": 5.27,
        "ejecutado": 4.49
      },
      "avance_sobre_vigente_pct": 59.2,
      "modificacion_vigente_vs_inicial_pct": -1.4,
      "desglose_ejecutado_real_2025_mm": {
        "corriente": 161470.1,
        "inversion": 170391.6,
        "transferencias_capital_subsidios": 2157439.2
      },
      "desglose_ejecutado_nominal_mm": {
        "corriente": 167095.0,
        "inversion": 176327.3,
        "transferencias_capital_subsidios": 2232595.4
      },
      "capitulos_ejecutado_nominal_mm": {
        "subsecretaria": 272354.0,
        "serviu_regionales": 2279473.2,
        "serviu_count": 16,
        "parque_metropolitano": 24190.6
      },
      "fuentes": {
        "ejecucion_url": "https://datos.gob.cl/dataset/ejecucion-presupuestaria-a-agosto-de-2026-del-gobierno-central-total",
        "ejecucion_titulo": "Ejecución Presupuestaria a Agosto de 2026 del Gobierno Central - Total",
        "ley_vigente_url": "https://datos.gob.cl/dataset/ley-de-presupuestos-inicial-y-vigente-a-agosto-de-2026-del-gobierno-central-ley-regular",
        "ley_vigente_titulo": "Ley de Presupuestos Inicial y Vigente a Agosto de 2026 del Gobierno Central - Ley Regular",
        "ley_texto_url": "https://www.bcn.cl/leychile/navegar?i=1219410",
        "dipres_partida_url": "https://www.dipres.gob.cl/597/articles-406493_doc_pdf.pdf"
      }
    }
  ],
  "glosas_anios_disponibles": [
    2021,
    2022,
    2023,
    2024,
    2025,
    2026
  ],
  "glosas_familias": [
    {
      "id": "terrenos_fsev_ds19",
      "titulo": "Tope para comprar terrenos con subsidios habitacionales (FSEV y DS 19)",
      "materia": "Adquisición de terrenos y estudios preliminares por SERVIU",
      "programa_alcance": "Partida 18 · SERVIU regionales · Fondo Solidario de Elección de Vivienda (DS 49) y, desde 2023, Programa de Integración Social y Territorial (DS 19)",
      "categorias": [
        "limites_uso",
        "requisitos_transferencia"
      ],
      "cambio_numeracion": true,
      "traza_numeracion": "Glosa 11 (2021–2022) → Glosa 09 (2023) → Glosa 08 (2024–2025) → Glosa 25 (2026)",
      "a_que_recursos_aplica": "A los recursos de transferencias de capital (Subtítulo 33) asignados al Fondo Solidario de Elección de Vivienda (DS 49) y, a partir de 2023, también al Programa de Integración Social y Territorial (DS 19).",
      "que_permite_o_exige": "Permite a los SERVIU destinar una fracción máxima del presupuesto de subsidios a comprar y resguardar terrenos donde haya alta demanda de familias del 40% más vulnerable o déficit censal, sujeto a autorización ministerial y resolución visada por DIPRES.",
      "diferencia_practica": "Es una de las reglas que más ha cambiado: en 2022 recortó el tope de 15% a 5%; en 2023 lo subió a 10% sumando DS 19, arriendo y campamentos; en 2024 puso un sub-tope de 1% máximo a estudios preliminares; en 2025 incorporó ciudades intermedias; y en 2026 endureció el control al exigir «visación previa de la Dirección de Presupuestos» además de la autorización del MINVU.",
      "nota_evidencia_gasto": "La glosa fija el techo legal y quién autoriza comprar suelo con cargo a subsidios, pero no determina por sí sola cuánto ejecutó cada SERVIU en terrenos ni explica automáticamente las variaciones del gasto total de la Partida 18; vincular ambos hechos requiere revisar las resoluciones exentas de compra y el avance por asignación.",
      "versiones": {
        "2021": {
          "anio": 2021,
          "disponible": true,
          "ley_numero": "Ley N° 21.289",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2020-12-16",
          "numero_glosa": "Glosa 11",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones (SERVIU) · Glosa 11",
          "texto": "Los SERVIU, con autorización del Ministerio de Vivienda y Urbanismo, podrán destinar hasta el 15% de los recursos de la asignación presupuestaria Fondo Solidario de Elección de Vivienda, para estudios preliminares y adquisición de terrenos en comunas en las que, conforme al sistema de información territorial de la demanda gestionado por el Ministerio de Vivienda y Urbanismo, exista una demanda significativa de viviendas para familias ubicadas en el tramo del 40% más vulnerable de la población, o aquellas donde se concentre principalmente el déficit habitacional de acuerdo a los datos del último censo de población y vivienda disponible. El Ministerio de Vivienda y Urbanismo, mediante resolución, establecerá los criterios de adquisición de los respectivos terrenos, la que requerirá visto bueno de la Dirección de Presupuestos. El SERVIU respectivo destinará los terrenos adquiridos al desarrollo de proyectos para atender a personas y/o grupos que cumplan con los criterios y requisitos establecidos en el reglamento de este programa habitacional para la postulación y selección, sea en forma individual o colectiva. Mediante resolución del Ministro de Vivienda y Urbanismo, visada por la Dirección de Presupuestos, se definirán los aspectos operativos de la presente glosa.",
          "url": "https://www.dipres.gob.cl/597/articles-213658_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2022": {
          "anio": 2022,
          "disponible": true,
          "ley_numero": "Ley N° 21.395",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2021-12-15",
          "numero_glosa": "Glosa 11",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones (SERVIU) · Glosa 11",
          "texto": "Los SERVIU, con autorización del Ministerio de Vivienda y Urbanismo, podrán destinar hasta el 5% de los recursos de la asignación presupuestaria Fondo Solidario de Elección de Vivienda, para estudios preliminares y adquisición de terrenos, incluyendo sus cierres y resguardos, en comunas en las que,conforme al sistema de información territorial de la demanda gestionado por el Ministerio de Vivienda y Urbanismo, exista una demanda significativa de viviendas para familias ubicadas en el tramo del 40% más vulnerable de la población, o aquellas donde se concentre principalmente el déficit habitacional de acuerdo a los datos del último censo de población y vivienda disponible. El Ministerio de Vivienda y Urbanismo, mediante resolución, establecerá los criterios de adquisición de los respectivos terrenos, la que requerirá visto bueno de la Dirección de Presupuestos. El SERVIU respectivo destinará los terrenos adquiridos al desarrollo de proyectos para atender a personas y/o grupos que cumplan con los criterios y requisitos establecidos en el reglamento de este programa habitacional para la postulación y selección, sea en forma individual o colectiva. Mediante resolución del Ministro de Vivienda y Urbanismo, visada por la Dirección de Presupuestos, se definirán los aspectos operativos de la presente glosa.",
          "url": "https://www.dipres.gob.cl/597/articles-257470_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2023": {
          "anio": 2023,
          "disponible": true,
          "ley_numero": "Ley N° 21.516",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2022-12-20",
          "numero_glosa": "Glosa 09",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones (SERVIU) · Glosa 09",
          "texto": "Los SERVIU, con autorización del Ministerio de Vivienda y Urbanismo, podrán destinar hasta el 10% de los recursos de la asignación presupuestaria de los Programas Fondo Solidario de Elección de Vivienda y Programa de Integración Social y Territorial, para estudios preliminares y adquisición de terrenos, incluyendo sus cierres y resguardos, en comunas en las que, conforme al sistema de información territorial de la demanda gestionado por el Ministerio de Vivienda y Urbanismo, exista una demanda significativa de viviendas, en el caso del Programa Fondo Solidario de Elección de Vivienda para familias ubicadas en el tramo del 40% más vulnerable de la población, o aquellas donde se concentre principalmente el déficit habitacional de acuerdo a los datos del último censo de población y vivienda disponible y en el caso del Programa de Integracion Social y Territorial en comunas donde se concentre el déficit habitacional de acuerdo a los datos del último censo de población y vivienda disponible, priorizando en zonas centrales y pericentrales de las grandes ciudades. El Ministerio de Vivienda y Urbanismo, mediante resolución, establecerá los criterios de adquisición de los respectivos terrenos, la que requerirá visto bueno de la Dirección de Presupuestos. El SERVIU respectivo destinará los terrenos adquiridos al desarrollo de proyectos para atender a personas y/o grupos que cumplan con los criterios y requisitos establecidos en los reglamentos de cada programa habitacional para la postulación y selección, sea en forma individual o colectiva, incluyendo personas que cumplan con los requisitos para ser beneficiarios del Subsidio de Arriendo regulado por el D.S. N° 52 (V. y U.) del 2013 o familias de campamentos beneficiados con gastos de traslado transitorio. Mediante resolución del Ministro de Vivienda y Urbanismo, visada por la Dirección de Presupuestos, se definirán los aspectos operativos de la presente glosa.",
          "url": "https://www.dipres.gob.cl/597/articles-299419_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2024": {
          "anio": 2024,
          "disponible": true,
          "ley_numero": "Ley N° 21.640",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2023-12-18",
          "numero_glosa": "Glosa 08",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones (SERVIU) · Glosa 08",
          "texto": "Los SERVIU, con autorización del Ministerio de Vivienda y Urbanismo, podrán destinar hasta el 10% de los recursos de la asignación presupuestaria de los Programas Fondo Solidario de Elección de Vivienda y Programa de Integración Social y Territorial, para estudios preliminares y adquisición de terrenos, incluyendo sus cierres y resguardos, en comunas en las que, conforme al sistema de información territorial de la demanda gestionado por el Ministerio de Vivienda y Urbanismo, exista una demanda significativa de viviendas, en el caso del Programa Fondo Solidario de Elección de Vivienda para familias ubicadas en el tramo del 40% más vulnerable de la población, o aquellas donde se concentre principalmente el déficit habitacional de acuerdo a los datos del último censo de población y vivienda disponible y en el caso del Programa de Integración Social y Territorial en comunas donde se concentre el déficit habitacional de acuerdo a los datos del último censo de población y vivienda disponible, priorizando en zonas centrales y pericentrales de las grandes ciudades. El Ministerio de Vivienda y Urbanismo, mediante resolución, establecerá los criterios de adquisición de los respectivos terrenos, la que requerirá visto bueno de la Dirección de Presupuestos. El SERVIU respectivo destinará los terrenos adquiridos al desarrollo de proyectos para atender a personas y/o grupos que cumplan con los criterios y requisitos establecidos en los reglamentos de cada programa habitacional para la postulación y selección, sea en forma individual o colectiva, incluyendo personas que cumplan con los requisitos para ser beneficiarios del Subsidio de Arriendo regulado por el D.S. N° 52 (V. y U.) del 2013 o familias de campamentos beneficiados con gastos de traslado transitorio. Mediante resolución del Ministro de Vivienda y Urbanismo, visada por la Dirección de Presupuestos, se definirán los aspectos operativos de la presente glosa. Con todo, del total de recursos destinados para este efecto, se destinará como máximo el 1% para los estudios preliminares a que hace mención la presente glosa.",
          "url": "https://www.dipres.gob.cl/597/articles-325504_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2025": {
          "anio": 2025,
          "disponible": true,
          "ley_numero": "Ley N° 21.722",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2024-12-13",
          "numero_glosa": "Glosa 08",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones (SERVIU) · Glosa 08",
          "texto": "Los SERVIU, con autorización del Ministerio de Vivienda y Urbanismo, podrán destinar hasta el 10% de los recursos de la asignación presupuestaria de los Programas Fondo Solidario de Elección de Vivienda y Programa de Integración Social y Territorial, para estudios preliminares y adquisición de terrenos, incluyendo sus cierres y resguardos, en comunas en las que, conforme al sistema de información territorial de la demanda gestionado por el Ministerio de Vivienda y Urbanismo, exista una demanda significativa de viviendas, en el caso del Programa Fondo Solidario de Elección de Vivienda para familias ubicadas en el tramo del 40% más vulnerable de la población, o aquellas donde se concentre principalmente el déficit habitacional de acuerdo a los datos del último censo de población y vivienda disponible y en el caso del Programa de Integración Social y Territorial en comunas donde se concentre el déficit habitacional de acuerdo a los datos del último censo de población y vivienda disponible, priorizando en zonas centrales y pericentrales de las grandes ciudades y ciudades intermedias. El Ministerio de Vivienda y Urbanismo, mediante resolución, establecerá los criterios de adquisición de los respectivos terrenos, la que requerirá visto bueno de la Dirección de Presupuestos. El SERVIU respectivo destinará los terrenos adquiridos al desarrollo de proyectos para atender a personas y/o grupos que cumplan con los criterios y requisitos establecidos en los reglamentos de cada programa habitacional para la postulación y selección, sea en forma individual o colectiva, incluyendo personas que cumplan con los requisitos para ser beneficiarios del Subsidio de Arriendo regulado por el D.S. N° 52 (V. y U.) del 2013 o familias de campamentos beneficiados con gastos de traslado transitorio. Mediante resolución del Ministro de Vivienda y Urbanismo, visada por la Dirección de Presupuestos, se definirán los aspectos operativos de la presente glosa. Con todo, del total de recursos destinados para este efecto, se destinará como máximo el 1% para los estudios preliminares a que hace mención la presente glosa.",
          "url": "https://www.dipres.gob.cl/597/articles-355270_doc_pdf.pdf",
          "nota_proyecto_vs_ley": "En 2025 el Proyecto de Ley y la Ley N° 21.722 mantuvieron el tope de 10% y el sub-tope de 1% para estudios preliminares."
        },
        "2026": {
          "anio": 2026,
          "disponible": true,
          "ley_numero": "Ley N° 21.796",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2025-12-12",
          "numero_glosa": "Glosa 25",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones (SERVIU) · Glosa 25 (p. 923–924)",
          "texto": "Los SERVIU, con autorización del Ministerio de Vivienda y Urbanismo y con la visación previa de la Dirección de Presupuestos, podrán destinar hasta el 10% de los recursos de la asignación presupuestaria de los Programas Fondo Solidario de Elección de Vivienda y Programa de Integración Social y Territorial, para estudios preliminares y adquisición de terrenos, incluyendo sus cierres y resguardos, en comunas en las que, conforme al sistema de información territorial de la demanda gestionado por el Ministerio de Vivienda y Urbanismo, exista una demanda significativa de viviendas, en el caso del Programa Fondo Solidario de Elección de Vivienda para familias ubicadas en el tramo del 40% más vulnerable de la población, o aquellas donde se concentre principalmente el déficit habitacional de acuerdo a los datos del último censo de población y vivienda disponible y en el caso del Programa de Integración Social y Territorial en comunas donde se concentre el déficit habitacional de acuerdo a los datos del último censo de población y vivienda disponible, priorizando en zonas centrales y pericentrales de las grandes ciudades y ciudades intermedias. El Ministerio de Vivienda y Urbanismo, mediante resolución, establecerá los criterios de adquisición de los respectivos terrenos, la que requerirá visto bueno de la Dirección de Presupuestos. El SERVIU respectivo destinará los terrenos adquiridos al desarrollo de proyectos para atender a personas y/o grupos que cumplan con los criterios y requisitos establecidos en los reglamentos de cada programa habitacional para la postulación y selección, sea en forma individual o colectiva, incluyendo personas que cumplan con los requisitos para ser beneficiarios del Subsidio de Arriendo regulado por el D.S. N° 52 (V. y U.) del 2013 o familias de campamentos beneficiados con gastos de traslado transitorio. Mediante resolución del Ministro de Vivienda y Urbanismo, visada por la Dirección de Presupuestos, se definirán los aspectos operativos de la presente glosa. Con todo, del total de recursos destinados para este efecto, se destinará como máximo el 1% para los estudios preliminares a que hace mención la presente glosa.",
          "url": "https://www.dipres.gob.cl/597/articles-406493_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        }
      }
    },
    {
      "id": "prestamos_subtitulo_32",
      "titulo": "Préstamos SERVIU a constructoras, entidades y municipalidades (Subtítulo 32)",
      "materia": "Financiamiento puente y garantías para obras con subsidio habitacional",
      "programa_alcance": "Partida 18 · SERVIU regionales · Subtítulo 32 (Préstamos)",
      "categorias": [
        "requisitos_transferencia",
        "limites_uso",
        "obligaciones_informar"
      ],
      "cambio_numeracion": true,
      "traza_numeracion": "Glosa 09 (2021–2022) → Glosa 07 (2023) → Glosa 06 (2024–2026)",
      "a_que_recursos_aplica": "A los fondos del Subtítulo 32 (Préstamos recuperables) de los 16 SERVIU, que entregan liquidez contra garantías mientras se ejecutan viviendas con subsidio (monto inicial $2,26 billones en Ley 2026; contabilizado fuera del gasto presupuestario directo para evitar doble conteo con Subt. 33).",
      "que_permite_o_exige": "Autoriza a los SERVIU a otorgar préstamos garantizados para construir proyectos con subsidio, limitando en igual monto los anticipos y exigiendo inscripción del terreno o prohibición de enajenar a favor del SERVIU, bajo resolución visada por DIPRES.",
      "diferencia_practica": "En 2023–2025 amplió los préstamos a municipalidades (Plan de Emergencia Habitacional) y proyectos de arriendo DS 52, y endureció la transparencia exigiendo reporte trimestral web reclamable vía Ley 20.285. En 2026 (Ley N° 21.796) restringió el gasto eliminando tanto a las «Municipalidades del país» como la letra a) «Para adquirir el terreno».",
      "nota_evidencia_gasto": "Estos préstamos se registran en el Subtítulo 32 (activos financieros recuperables) y no en el gasto directo (Subt. 21–31 y 33). Su endurecimiento en 2026 acota quién puede pedir crédito puente y para qué fines, pero su efecto efectivo en inicios de obra debe verificarse en los reportes trimestrales de Subt. 32.",
      "versiones": {
        "2021": {
          "anio": 2021,
          "disponible": true,
          "ley_numero": "Ley N° 21.289",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2020-12-16",
          "numero_glosa": "Glosa 09",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Subtítulo 32 · Glosa 09",
          "texto": "Asociada a Subtítulo 32 Con cargo a estos fondos los SERVIU podrán otorgar uno o más préstamos a la Empresa Constructora o a la Entidad Desarrolladora del Proyecto, para la ejecución de proyectos con subsidios, en los siguientes casos: a) Para adquirir el terreno, en cuyo evento, para garantizar dicho préstamo, se inscribirá el terreno a nombre del SERVIU respectivo en el Conservador de Bienes Raíces, y b) Para la ejecución de proyectos de construcción con alguno de los subsidios habitacionales vigentes, por un monto que no podrá ser superior a aquella parte del valor de las obras, expresado en el contrato de construcción, que será cubierto con subsidio del Estado. Los préstamos deberán ser garantizados conforme se establezca en la resolución a que se refiere el párrafo final de la presente glosa. Junto con la presentación de una o más garantías se exigirá que el terreno, en los casos de construcción en nuevos terrenos, se encuentre inscrito a nombre del SERVIU respectivo en el Conservador de Bienes Raíces. c) Para construcciones sujetas al D.S. N° 236,(V. y U.) de 2002, en aquellos casos en que el mandante sea el SERVIU. Tratándose de construcción en nuevos terrenos, si éstos se encuentran inscritos a nombre del respectivo Comité, la inscripción a nombre del SERVIU se reemplazará por la constitución de una prohibición de enajenar y gravar en favor de SERVIU, la que se levantará una vez restituido el préstamo, misma condición se deberá cumplir en caso que la construcción se realice en terrenos fiscales y/o municipales en proceso de transferencia a SERVIU. El otorgamiento de estos préstamos limita en igual monto los giros por anticipo que se efectúen con cargo al subsidio. El otorgamiento de los referidos préstamos y sus garantías se regulará por resolución exenta del Ministerio de Vivienda y Urbanismo, visada por la Dirección de Presupuestos, la que podrá dictarse una vez publicada la Ley de Presupuestos del Sector Público para el año 2021. Los Ministerios de Vivienda y Urbanismo y de Hacienda deberán informar semestralmente a la Comisión Especial Mixta de Presupuestos, respecto de la existencia de estudios tendientes a diseñar instrumentos financieros destinados a reemplazar este sistema de préstamos.",
          "url": "https://www.dipres.gob.cl/597/articles-213658_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2022": {
          "anio": 2022,
          "disponible": true,
          "ley_numero": "Ley N° 21.395",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2021-12-15",
          "numero_glosa": "Glosa 09",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Subtítulo 32 · Glosa 09",
          "texto": "Asociada a Subtítulo 32 Con cargo a estos fondos los SERVIU podrán otorgar uno o más préstamos a la Empresa Constructora o a la Entidad Desarrolladora del Proyecto, para la ejecución de proyectos con subsidios, en los siguientes casos: a) Para adquirir el terreno, en cuyo evento, para garantizar dicho préstamo, se inscribirá el terreno a nombre del SERVIU respectivo en el Conservador de Bienes Raíces, y b) Para la ejecución de proyectos de construcción con alguno de los subsidios habitacionales vigentes, por un monto que no podrá ser superior a aquella parte del valor de las obras, expresado en el contrato de construcción, que será cubierto con subsidio del Estado. Los préstamos deberán ser garantizados conforme se establezca en la resolución a que se refiere el párrafo final de la presente glosa. Junto con la presentación de una o más garantías se exigirá que el terreno, en los casos de construcción en nuevos terrenos, se encuentre inscrito a nombre del SERVIU respectivo en el Conservador de Bienes Raíces. c) Para construcciones sujetas al D.S. N° 236,(V. y U.) de 2002, en aquellos casos en que el mandante sea el SERVIU. Tratándose de construcción en nuevos terrenos, si éstos se encuentran inscritos a nombre del respectivo Comité, la inscripción a nombre del SERVIU se reemplazará por la constitución de una prohibición de enajenar y gravar en favor de SERVIU, la que se levantará una vez restituido el préstamo, misma condición se deberá cumplir en caso que la construcción se realice en terrenos fiscales y/o municipales en proceso de transferencia a SERVIU. El otorgamiento de estos préstamos limita en igual monto los giros por anticipo que se efectúen con cargo al subsidio. El otorgamiento de los referidos préstamos y sus garantías se regulará por resolución exenta del Ministerio de Vivienda y Urbanismo, visada por la Dirección de Presupuestos, la que podrá dictarse una vez publicada la Ley de Presupuestos del Sector Público para el año 2022. Los Ministerios de Vivienda y Urbanismo y de Hacienda deberán informar semestralmente a la Comisión Especial Mixta de Presupuestos, respecto de la existencia de estudios tendientes a diseñar instrumentos financieros destinados a reemplazar este sistema de préstamos. En el caso que la ejecución de los proyectos lo requiera, se podrán suplementar estos recursos.",
          "url": "https://www.dipres.gob.cl/597/articles-257470_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2023": {
          "anio": 2023,
          "disponible": true,
          "ley_numero": "Ley N° 21.516",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2022-12-20",
          "numero_glosa": "Glosa 07",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Subtítulo 32 · Glosa 07",
          "texto": "Asociada a Subtítulo 32 Con cargo a estos fondos los SERVIU podrán otorgar uno o más préstamos a la Empresa Constructora o a la Entidad Desarrolladora del Proyecto o a la entidad responsable de la administración de arriendo para la ejecución de proyectos con subsidios, o durante la aplicación del Plan de Emergencia Habitacional, a Municipalidades del país, esto para la elaboración y/o ejecución de proyectos habitacionales con subsidio, en los siguientes casos: a) Para adquirir el terreno, en cuyo evento, para garantizar dicho préstamo, se inscribirá el terreno a nombre del SERVIU respectivo en el Conservador de Bienes Raíces, y b) Para la ejecución de proyectos de construcción con alguno de los subsidios habitacionales vigentes, por un monto que no podrá ser superior a aquella parte del valor de las obras, expresado en el contrato de construcción, que será cubierto con subsidio del Estado. Los préstamos deberán ser garantizados conforme se establezca en la resolución a que se refiere el párrafo final de la presente glosa. Junto con la presentación de una o más garantías se exigirá que el terreno, en los casos de construcción en nuevos terrenos, se encuentre inscrito a nombre del SERVIU respectivo en el Conservador de Bienes Raíces. c) Para construcciones sujetas al D.S. N° 236, (V. y U.) de 2002, en aquellos casos en que el mandante sea el SERVIU. d) Para la construcción, arriendo, la adquisición y/o remodelación de viviendas, que serán destinadas en todos los casos al arrendamiento a familias que cumplan con los requisitos del Programa regulado por el D.S. N°52, (V. y U.), de 2013. En estos casos, mediante resoluciones del Ministro de Vivienda y Urbanismo se establecerán los estándares técnicos para el desarrollo de dichas obras. Tratándose de construcción en nuevos terrenos, si éstos se encuentran inscritos a nombre del respectivo Comité, la inscripción a nombre del SERVIU se reemplazará por la constitución de una prohibición de enajenar y gravar en favor de SERVIU, la que se levantará una vez restituido el préstamo, salvo que el alzamiento y la transferencia de las viviendas a los beneficiarios se realicen en el mismo acto, mismas condiciones se deberán cumplir en caso que la construcción se realice en terrenos fiscales y/o municipales en proceso de transferencia a SERVIU. El otorgamiento de estos préstamos limita en igual monto los giros por anticipo que se efectúen con cargo al subsidio. El otorgamiento de los referidos préstamos y sus garantías se regulará por resolución exenta del Ministerio de Vivienda y Urbanismo, visada por la Dirección de Presupuestos, la que podrá dictarse una vez publicada la Ley de Presupuestos del Sector Público para el año 2023. El Ministerio de Vivienda y Urbanismo informará trimestralmente a la Comisión Especial Mixta de Presupuestos sobre la ejecución de estos recursos, identificando las empresas o Municipalidades beneficiarias, las condiciones pactadas y las soluciones habitacionales generadas por este subtítulo, distribuido regionalmente. En igual plazo, dicha información deberá ser publicada un lugar destacado en su sitio web permanentemente a disposición del público y actualizada. La omisión de la publicación en la forma señalada o la falta de actualización podrá reclamarse en conformidad con lo dispuesto en el artículo 8° de la Ley de Transparencia de la Función Pública y de Acceso a la Información de la Administración del Estado, aprobada por el artículo primero de la ley Nº 20.285.",
          "url": "https://www.dipres.gob.cl/597/articles-299419_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2024": {
          "anio": 2024,
          "disponible": true,
          "ley_numero": "Ley N° 21.640",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2023-12-18",
          "numero_glosa": "Glosa 06",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Subtítulo 32 · Glosa 06",
          "texto": "Asociada a Subtítulo 32 Con cargo a estos fondos los SERVIU podrán otorgar uno o más préstamos a la Empresa Constructora o a la Entidad Desarrolladora del Proyecto o a la entidad responsable de la administración de arriendo para la ejecución de proyectos con subsidios, o durante la aplicación del Plan de Emergencia Habitacional, a Municipalidades del país, esto para la elaboración y/o ejecución de proyectos habitacionales con subsidio, en los siguientes casos: a) Para adquirir el terreno, en cuyo evento, para garantizar dicho préstamo, se inscribirá el terreno a nombre del SERVIU respectivo en el Conservador de Bienes Raíces, y b) Para la ejecución de proyectos de construcción con alguno de los subsidios habitacionales vigentes, por un monto que no podrá ser superior a aquella parte del valor de las obras, expresado en el contrato de construcción, que será cubierto con subsidio del Estado. Los préstamos deberán ser garantizados conforme se establezca en la resolución a que se refiere el párrafo final de la presente glosa. Junto con la presentación de una o más garantías se exigirá que el terreno, en los casos de construcción en nuevos terrenos, se encuentre inscrito a nombre del SERVIU respectivo en el Conservador de Bienes Raíces. c) Para construcciones sujetas al D.S. N° 236, (V. y U.) de 2002, en aquellos casos en que el mandante sea el SERVIU. d) Para la construcción, arriendo, la adquisición y/o remodelación de viviendas, que serán destinadas en todos los casos al arrendamiento a familias que cumplan con los requisitos del Programa regulado por el D.S. N°52, (V. y U.), de 2013. En estos casos, mediante resoluciones del Ministro de Vivienda y Urbanismo se establecerán los estándares técnicos para el desarrollo de dichas obras. Tratándose de construcción en nuevos terrenos, si éstos se encuentran inscritos a nombre del respectivo Comité, la inscripción a nombre del SERVIU se reemplazará por la constitución de una prohibición de enajenar y gravar en favor de SERVIU, la que se levantará una vez restituido el préstamo, salvo que el alzamiento y la transferencia de las viviendas a los beneficiarios se realicen en el mismo acto, mismas condiciones se deberán cumplir en caso que la construcción se realice en terrenos fiscales y/o municipales en proceso de transferencia a SERVIU. El otorgamiento de estos préstamos limita en igual monto los giros por anticipo que se efectúen con cargo al subsidio. El otorgamiento de los referidos préstamos y sus garantías se regulará por resolución exenta del Ministerio de Vivienda y Urbanismo, visada por la Dirección de Presupuestos, la que podrá dictarse una vez publicada la Ley de Presupuestos del Sector Público para el año 2024. El Ministerio de Vivienda y Urbanismo informará trimestralmente a la Comisión Especial Mixta de Presupuestos sobre la ejecución de estos recursos, identificando las empresas o Municipalidades beneficiarias, las condiciones pactadas y las soluciones habitacionales generadas por este subtítulo, distribuido regionalmente. En igual plazo, dicha información deberá ser publicada un lugar destacado en su sitio web permanentemente a disposición del público y actualizada. La omisión de la publicación en la forma señalada o la falta de actualización podrá reclamarse en conformidad con lo dispuesto en el artículo 8° de la Ley de Transparencia de la Función Pública y de Acceso a la Información de la Administración del Estado, aprobada por el artículo primero de la ley Nº 20.285.",
          "url": "https://www.dipres.gob.cl/597/articles-325504_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2025": {
          "anio": 2025,
          "disponible": true,
          "ley_numero": "Ley N° 21.722",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2024-12-13",
          "numero_glosa": "Glosa 06",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Subtítulo 32 · Glosa 06",
          "texto": "Asociada a Subtítulo 3206 Con cargo a estos fondos los SERVIU podrán otorgar uno o más préstamos a la Empresa Constructora o a la Entidad Desarrolladora del Proyecto o a la entidad responsable de la administración de arriendo para la ejecución de proyectos con subsidios, o durante la aplicación del Plan de Emergencia Habitacional, a Municipalidades del país, esto para la elaboración y/o ejecución de proyectos habitacionales con subsidio, en los siguientes casos: a) Para adquirir el terreno, en cuyo evento, para garantizar dicho préstamo, se inscribirá el terreno a nombre del SERVIU respectivo en el Conservador de Bienes Raíces, y b) Para la ejecución de proyectos de construcción con alguno de los subsidios habitacionales vigentes, por un monto que no podrá ser superior a aquella parte del valor de las obras, expresado en el contrato de construcción, que será cubierto con subsidio del Estado. Los préstamos deberán ser garantizados conforme se establezca en la resolución a que se refiere el párrafo final de la presente glosa. Junto con la presentación de una o más garantías se exigirá que el terreno, en los casos de construcción en nuevos terrenos, se encuentre inscrito a nombre del SERVIU respectivo en el Conservador de Bienes Raíces. c) Para construcciones sujetas al D.S. N° 236, (V. y U.) de 2002, en aquellos casos en que el mandante sea el SERVIU. d) Para la construcción, arriendo, la adquisición y/o remodelación de viviendas, que serán destinadas en todos los casos al arrendamiento a familias que cumplan con los requisitos del Programa regulado por el D.S. N°52, (V. y U.), de 2013. En estos casos, mediante resoluciones del Ministro de Vivienda y Urbanismo se establecerán los estándares técnicos para el desarrollo de dichas obras. Tratándose de construcción en nuevos terrenos, si éstos se encuentran inscritos a nombre del respectivo Comité, la inscripción a nombre del SERVIU se reemplazará por la constitución de una prohibición de enajenar y gravar en favor de SERVIU, la que se levantará una vez restituido el préstamo, salvo que el alzamiento y la transferencia de las viviendas a los beneficiarios se realicen en el mismo acto, mismas condiciones se deberán cumplir en caso que la construcción se realice en terrenos fiscales y/o municipales en proceso de transferencia a SERVIU. El otorgamiento de estos préstamos limita en igual monto los giros por anticipo que se efectúen con cargo al subsidio. El otorgamiento de los referidos préstamos y sus garantías se regulará por resolución exenta del Ministerio de Vivienda y Urbanismo, visada por la Dirección de Presupuestos, la que podrá dictarse una vez publicada la Ley de Presupuestos del Sector Público para el año 2025. El Ministerio de Vivienda y Urbanismo informará trimestralmente a la Comisión Especial Mixta de Presupuestos sobre la ejecución de estos recursos, identificando las empresas o Municipalidades beneficiarias, las condiciones pactadas y las soluciones habitacionales generadas por este subtítulo, distribuido regionalmente. En igual plazo, dicha información deberá ser publicada un lugar destacado en su sitio web permanentemente a disposición del público y actualizada. La omisión de la publicación en la forma señalada o la falta de actualización podrá reclamarse en conformidad con lo dispuesto en el artículo 8° de la Ley de Transparencia de la Función Pública y de Acceso a la Información de la Administración del Estado, aprobada por el artículo primero de la ley Nº 20.285.",
          "url": "https://www.dipres.gob.cl/597/articles-355270_doc_pdf.pdf",
          "nota_proyecto_vs_ley": "En 2025 el Proyecto de Ley y la Ley N° 21.722 mantuvieron la habilitación a Municipalidades y la letra a) para compra de terreno; ambas fueron eliminadas recién en la Ley 2026."
        },
        "2026": {
          "anio": 2026,
          "disponible": true,
          "ley_numero": "Ley N° 21.796",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2025-12-12",
          "numero_glosa": "Glosa 06",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Subtítulo 32 · Glosa 06 (p. 919–920)",
          "texto": "Asociada a Subtítulo 32 Con cargo a estos fondos los SERVIU podrán otorgar uno o más préstamos a la Empresa Constructora o a la Entidad Desarrolladora del Proyecto o a la entidad responsable de la administración de arriendo para la ejecución de proyectos con subsidios, esto para la elaboración y/o ejecución de proyectos habitacionales con subsidio, en los siguientes casos: a) Para la ejecución de proyectos de construcción con alguno de los subsidios habitacionales vigentes, por un monto que no podrá ser superior a aquella parte del valor de las obras, expresado en el contrato de construcción, que será cubierto con subsidio del Estado. Los préstamos deberán ser garantizados conforme se establezca en la resolución a que se refiere el párrafo final de la presente glosa. Junto con la presentación de una o más garantías se exigirá que el terreno, en los casos de construcción en nuevos terrenos, se encuentre inscrito a nombre del SERVIU respectivo en el Conservador de Bienes Raíces. b) Para construcciones sujetas al D.S. N° 236, (V. y U.) de 2002, en aquellos casos en que el mandante sea el SERVIU. c) Para la construcción, arriendo, la adquisición y/o remodelación de viviendas, que serán destinadas en todos los casos al arrendamiento a familias que cumplan con los requisitos del Programa regulado por el D.S. N°52, (V. y U.), de 2013. En estos casos, mediante resoluciones del Ministro de Vivienda y Urbanismo se establecerán los estándares técnicos para el desarrollo de dichas obras. Tratándose de construcción en nuevos terrenos, si éstos se encuentran inscritos a nombre del respectivo Comité, la inscripción a nombre del SERVIU se reemplazará por la constitución de una prohibición de enajenar y gravar en favor de SERVIU, la que se levantará una vez restituido el préstamo, salvo que el alzamiento y la transferencia de las viviendas a los beneficiarios se realicen en el mismo acto, mismas condiciones se deberán cumplir en caso que la construcción se realice en terrenos fiscales y/o municipales en proceso de transferencia a SERVIU. El otorgamiento de estos préstamos limita en igual monto los giros por anticipo que se efectúen con cargo al subsidio. El otorgamiento de los referidos préstamos y sus garantías se regulará por resolución exenta del Ministerio de Vivienda y Urbanismo, visada por la Dirección de Presupuestos, la que podrá dictarse una vez publicada la Ley de Presupuestos del Sector Público para el año 2026. El Ministerio de Vivienda y Urbanismo informará trimestralmente a la Comisión Especial Mixta de Presupuestos sobre la ejecución de estos recursos, identificando las empresas o Municipalidades beneficiarias, las condiciones pactadas y las soluciones habitacionales generadas por este subtítulo, distribuido regionalmente. En igual plazo, dicha información deberá ser publicada en un lugar destacado en su sitio web permanentemente a disposición del público y actualizada. La omisión de la publicación en la forma señalada o la falta de actualización podrá reclamarse en conformidad con lo dispuesto en el artículo 8° de la Ley de Transparencia de la Función Pública y de Acceso a la Información de la Administración del Estado, aprobada por el artículo primero de la ley Nº 20.285.",
          "url": "https://www.dipres.gob.cl/597/articles-406493_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        }
      }
    },
    {
      "id": "transferencias_privados_art23",
      "titulo": "Requisitos y concurso obligatorio para transferir recursos a privados (Art. 23)",
      "materia": "Transferencias corrientes y de capital a fundaciones, corporaciones y entidades privadas",
      "programa_alcance": "Articulado General de la Ley de Presupuestos · Aplicable a toda la Partida 18 MINVU (incl. Asentamientos Precarios y convenios Subt. 24 y 33)",
      "categorias": [
        "requisitos_transferencia"
      ],
      "cambio_numeracion": false,
      "traza_numeracion": "Artículo 23 (2022–2026; complementado desde 2024 por Artículos 24 y 25)",
      "a_que_recursos_aplica": "A todas las transferencias a instituciones privadas del sector público, incluyendo los convenios del MINVU en Asentamientos Precarios y programas urbanos (Subtítulo 24 corriente y, desde 2024, también Subtítulo 33 de capital).",
      "que_permite_o_exige": "Exige concurso público abierto y transparente y suscripción previa de convenio para asignar recursos a privados, limitando la asignación directa a causales taxativas con resolución fundada y bloqueando nuevas transferencias ante incumplimientos.",
      "diferencia_practica": "Desde 2024 (Ley N° 21.640, tras el Caso Convenios) se produjo el mayor endurecimiento normativo en transferencias: pasó de regir solo «transferencias corrientes» (2022–2023) a cubrir obligatoriamente «transferencias corrientes y de capital», cerró el trato directo a causales acotadas (sumando emergencia calificada en 2025–2026) y exigió desde Art. 25 al menos 2 años de antigüedad a entidades ejecutoras.",
      "nota_evidencia_gasto": "Esta regla restringe estrictamente el mecanismo de transferencia a privados (concurso, antigüedad y bloqueo por incumplimiento), pero en la Partida 18 los convenios con fundaciones representan una fracción menor frente a los subsidios directos de los SERVIU; atribuir una caída global del gasto MINVU al Art. 23 requiere desglosar específicamente el Programa 02 Asentamientos Precarios.",
      "versiones": {
        "2021": {
          "anio": 2021,
          "disponible": false,
          "ley_numero": "Ley N° 21.289",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2020-12-16",
          "numero_glosa": "Sin equivalente",
          "ubicacion": "Ley N° 21.289 · Partida 18",
          "texto": "",
          "url": "https://www.dipres.gob.cl/597/articles-213658_doc_pdf.pdf",
          "sin_dato_motivo": "El Articulado completo de la Ley N° 21.289 (2021) no forma parte de este corte automatizado BCN; la comparación verificada del Art. 23 cubre los años 2022 a 2026."
        },
        "2022": {
          "anio": 2022,
          "disponible": true,
          "ley_numero": "Ley N° 21.395",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2021-12-15",
          "numero_glosa": "Artículo 23",
          "ubicacion": "Articulado General Ley N° 21.395 · Artículo 23 (aplicable a Partida 18 MINVU)",
          "texto": "Artículo 23.- El concurso será obligatorio para la asignación de recursos correspondientes a transferencias corrientes a instituciones privadas, salvo que la ley expresamente señale lo contrario. Sin perjuicio de lo que establezcan sus regulaciones específicas dictadas en conformidad a la ley, las transferencias corrientes a instituciones privadas deberán cumplir siempre con los siguientes requisitos: a) Serán transferidas mediante un convenio suscrito entre las partes, en el cual deberá estipularse, a lo menos, las acciones a desarrollar, las metas, plazos y forma de rendir cuenta de su uso. El Ministerio de Hacienda podrá impartir instrucciones complementarias de aplicación general respecto del contenido de estos convenios, con la finalidad de asegurar que los recursos públicos transferidos sean destinados efectivamente al objetivo para el que fueron asignados, así como su restitución, en caso contrario. b) Los convenios no podrán considerar transferencias de todo o parte de lo convenido en un plazo distinto del que resulte de relacionar dichas transferencias con el avance efectivo de la ejecución de las iniciativas durante el año presupuestario, salvo autorización de la Dirección de Presupuestos. c) Los convenios no podrán establecer compromisos que excedan el ejercicio presupuestario, salvo que cuenten con la autorización previa de la Dirección de Presupuestos.",
          "url": "https://www.bcn.cl/leychile/navegar?i=1169723",
          "nota_proyecto_vs_ley": null
        },
        "2023": {
          "anio": 2023,
          "disponible": true,
          "ley_numero": "Ley N° 21.516",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2022-12-20",
          "numero_glosa": "Artículo 23",
          "ubicacion": "Articulado General Ley N° 21.516 · Artículo 23 (aplicable a Partida 18 MINVU)",
          "texto": "Artículo 23.- El concurso será obligatorio para la asignación de recursos correspondientes a transferencias corrientes a instituciones privadas, salvo que la ley expresamente señale lo contrario. Sin perjuicio de lo que establezcan sus regulaciones específicas dictadas en conformidad a la ley, las transferencias corrientes a instituciones privadas deberán cumplir siempre con los siguientes requisitos: a) Serán transferidas mediante un convenio suscrito entre las partes, en el que deberá estipularse, a lo menos, las acciones a desarrollar, las metas, plazos y forma de rendir cuenta de su uso. El Ministerio de Hacienda podrá impartir instrucciones complementarias de aplicación general respecto del contenido de estos convenios, con la finalidad de asegurar que los recursos públicos transferidos sean destinados efectivamente al objetivo para el que fueron asignados, así como su restitución, en caso contrario. b) Los convenios no podrán considerar transferencias de todo o parte de lo convenido en un plazo distinto del que resulte de relacionar dichas transferencias con el avance efectivo de la ejecución de las iniciativas durante el año presupuestario, salvo autorización de la Dirección de Presupuestos. c) Los convenios no podrán establecer compromisos que excedan el ejercicio presupuestario, salvo que cuenten con la autorización previa de la Dirección de Presupuestos.",
          "url": "https://www.bcn.cl/leychile/navegar?idNorma=1186683",
          "nota_proyecto_vs_ley": null
        },
        "2024": {
          "anio": 2024,
          "disponible": true,
          "ley_numero": "Ley N° 21.640",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2023-12-18",
          "numero_glosa": "Artículo 23",
          "ubicacion": "Articulado General Ley N° 21.640 · Artículo 23 (aplicable a Partida 18 MINVU)",
          "texto": "Artículo 23.- Para todos los organismos públicos contenidos en esta ley, la asignación de recursos a instituciones privadas, provenientes de transferencias corrientes y de capital, salvo que la ley expresamente señale lo contrario, será el resultado de un concurso público abierto y transparente, que garantice la probidad, eficiencia y eficacia en el uso de los recursos públicos y la igualdad y la libre concurrencia de los potenciales beneficiarios de la transferencia. Estas transferencias se materializarán previa suscripción de convenio. Asimismo, el concurso y el convenio serán obligatorios para seleccionar a una institución privada en calidad de ejecutor de recursos o programas públicos. Excepcionalmente, se permitirá la asignación de recursos sin concurso a instituciones privadas en los casos que a continuación se señalan: 1. si en los concursos públicos respectivos no se presentaron interesados. 2. si sólo existe una persona jurídica como posible beneficiario de los recursos o como ejecutor de ellos. En los casos señalados anteriormente deberá acreditarse la concurrencia de la circunstancia que justifica la asignación directa, mediante resolución fundada del jefe superior de la entidad que asigne los recursos o a quien éste le haya delegado dicha facultad.",
          "url": "https://www.bcn.cl/leychile/navegar?idNorma=1199318",
          "nota_proyecto_vs_ley": null
        },
        "2025": {
          "anio": 2025,
          "disponible": true,
          "ley_numero": "Ley N° 21.722",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2024-12-13",
          "numero_glosa": "Artículo 23",
          "ubicacion": "Articulado General Ley N° 21.722 · Artículo 23 (aplicable a Partida 18 MINVU)",
          "texto": "Artículo 23.- Para todos los organismos públicos contenidos en esta ley la asignación de recursos a instituciones privadas, provenientes de transferencias corrientes y de capital, salvo que la ley expresamente señale lo contrario o que sean asignaciones nominadas en esta ley, será el resultado de un concurso público abierto y transparente, que garantice la probidad, eficiencia y eficacia en el uso de los recursos públicos, y la igualdad y la libre concurrencia de los potenciales beneficiarios de la transferencia. Estas transferencias se materializarán previa suscripción de convenio. El concurso y el convenio serán obligatorios para seleccionar a una institución privada ejecutora de política pública. Excepcionalmente, se permitirá la asignación de recursos sin concurso a instituciones privadas en los casos que a continuación se señala: a) Si en los concursos públicos respectivos no se presentaron interesados. b) Si sólo existe una persona jurídica como posible beneficiario de los recursos o como su ejecutor. c) En casos de emergencia, urgencia o imprevisto, calificados de conformidad a lo establecido en el inciso siguiente, sin perjuicio de las disposiciones especiales para casos de sismos y catástrofes contenidas en la legislación pertinente. En los casos señalados anteriormente deberá acreditarse la concurrencia de la circunstancia que justifica la asignación directa, mediante resolución fundada del jefe superior de la entidad que asigne los recursos o de aquel a quien éste le haya delegado dicha facultad.",
          "url": "https://www.bcn.cl/leychile/navegar?i=1209325",
          "nota_proyecto_vs_ley": null
        },
        "2026": {
          "anio": 2026,
          "disponible": true,
          "ley_numero": "Ley N° 21.796",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2025-12-12",
          "numero_glosa": "Artículo 23",
          "ubicacion": "Articulado General Ley N° 21.796 · Artículo 23 (aplicable a Partida 18 MINVU)",
          "texto": "Artículo 23.- Para todos los organismos públicos contenidos en esta ley la asignación de recursos a instituciones privadas, provenientes de transferencias corrientes y de capital, salvo que la ley expresamente señale lo contrario o que sean asignaciones nominadas en esta ley, será el resultado de un concurso público abierto y transparente, que garantice la probidad, eficiencia y eficacia en el uso de los recursos públicos, y la igualdad y la libre concurrencia de los potenciales beneficiarios de la transferencia. Estas transferencias se materializarán previa suscripción de convenio. El concurso y el convenio serán obligatorios para seleccionar a una institución privada ejecutora de política pública. Los concursos podrán no considerar soluciones específicas en sus bases. Excepcionalmente, se permitirá la asignación de recursos sin concurso a instituciones privadas en los casos que a continuación se señalan: a) Si en los concursos públicos respectivos no se presentaron interesados. b) Si sólo existe una persona jurídica como posible beneficiario de los recursos o como su ejecutor. c) En casos de emergencia, urgencia o imprevisto, calificados de conformidad a lo establecido en el inciso siguiente, sin perjuicio de las disposiciones especiales para casos de sismos y catástrofes contenidas en la legislación pertinente.",
          "url": "https://www.bcn.cl/leychile/navegar?i=1219410",
          "nota_proyecto_vs_ley": null
        }
      }
    },
    {
      "id": "subsidios_subtitulo_33_llamados",
      "titulo": "Reglas de llamados a subsidios habitacionales y topes de administración (Subt. 33)",
      "materia": "Conformación del programa anual de subsidios, sobregiros SERVIU y topes de gestión",
      "programa_alcance": "Partida 18 · SERVIU regionales y Subsecretaría · Subtítulo 33, Ítem 01 (Transferencias de Capital al Sector Privado)",
      "categorias": [
        "limites_uso",
        "requisitos_transferencia"
      ],
      "cambio_numeracion": false,
      "traza_numeracion": "Glosa 03, letras a) a d) (2021–2026)",
      "a_que_recursos_aplica": "Al corazón del presupuesto de vivienda: el Subtítulo 33, Ítem 01 (más del 70% del gasto directo total de la Partida 18), que financia los subsidios habitacionales de familias vulnerables y sectores medios.",
      "que_permite_o_exige": "Fija el cierre del programa anual al 31 de diciembre, permite flexibilidad regional hasta octubre sin exceder el total del ítem, y pone topes en pesos para gastos de administración de llamados y Plan de Gestión de Calidad, prohibiendo usar esos fondos en personal y exigiendo visación DIPRES.",
      "diferencia_practica": "En 2026 (Ley N° 21.796) la letra a) incorporó una nueva exigencia de disciplina fiscal: la resolución conjunta de llamados debe explicitar obligatoriamente «el número de unidades por programa y los recursos a destinar para su financiamiento» (art. 40 Ley 18.591). Además, el techo del Plan de Gestión de Calidad subió de $1.650 millones (2021) a $5.418 millones (2026), manteniendo la prohibición de gasto en personal.",
      "nota_evidencia_gasto": "La exigencia de fijar unidades y montos en la resolución conjunta de llamados (2026) ordena la programación inicial del Subtítulo 33, pero la ejecución efectiva depende además del ritmo de obras, recepción municipal y pago de certificados de subsidio.",
      "versiones": {
        "2021": {
          "anio": 2021,
          "disponible": true,
          "ley_numero": "Ley N° 21.289",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2020-12-16",
          "numero_glosa": "Glosa 03 (letras a–d)",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Subtítulo 33, Ítem 01 · Glosa 03 (letras a–d)",
          "texto": "Asociada a Subtítulo 33, Ítem 01: a) El programa del año quedará conformado exclusivamente por aquellos subsidios cuyo proceso de postulación haya concluido el 31 de diciembre del 2021. b) Los montos consignados en los presupuestos de cada SERVIU a nivel de asignación del referido ítem podrán ser excedidos hasta el mes de octubre, con el objeto de dar continuidad al pago de los respectivos certificados de subsidios, no pudiendo sobrepasarse la cantidad total del ítem. c) Con cargo a estos recursos se podrá destinar hasta $ 3.040.306 miles para gastos de administración asociados directamente con el proceso de llamado, postulación y selección de beneficiarios. Previo a la ejecución del gasto, el Ministerio de Vivienda y Urbanismo dictará una resolución, visada por la Dirección de Presupuestos, que distribuirá este monto entre los SERVIU y la Subsecretaría conforme a criterios técnicos y al programa de actividades, materias que deberán explicitarse en la resolución señalada. No se podrán efectuar gastos en personal con cargo a estos recursos. d) Con cargo a estos recursos se podrá destinar para el Plan de Gestión de la Calidad, hasta $ 1.649.749 miles, para gastos asociados a la fiscalización, evaluación y otras acciones relacionadas a proyectos en ejecución de los programas habitacionales y obras urbanas relacionadas, como asimismo, respecto a proyectos en los que el Ministerio de Vivienda y Urbanismo prevea una inversión futura. Previo a la ejecución del gasto, el Ministerio de Vivienda y Urbanismo dictará una resolución, visada por la Dirección de Presupuestos, que distribuirá este monto entre los SERVIU y la Subsecretaría conforme a criterios técnicos, y al programa de actividades, materias que deberán explicitarse en la resolución señalada. No se podrán efectuar gastos en personal con cargo a estos recursos.",
          "url": "https://www.dipres.gob.cl/597/articles-213658_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2022": {
          "anio": 2022,
          "disponible": true,
          "ley_numero": "Ley N° 21.395",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2021-12-15",
          "numero_glosa": "Glosa 03 (letras a–d)",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Subtítulo 33, Ítem 01 · Glosa 03 (letras a–d)",
          "texto": "Asociada a Subtítulo 33, Ítem 01: a) El programa del año quedará conformado exclusivamente por aquellos subsidios cuyo proceso de postulación haya concluido el 31 de diciembre del 2022. b) Los montos consignados en los presupuestos de cada SERVIU a nivel de asignación del referido ítem podrán ser excedidos hasta el mes de octubre, con el objeto de dar continuidad al pago de los respectivos certificados de subsidios, no pudiendo sobrepasarse la cantidad total del ítem. c) Con cargo a estos recursos se podrá destinar hasta $ 3.174.080 miles para gastos de administración asociados directamente con el proceso de llamado,postulación y selección de beneficiarios. Previo a la ejecución del gasto, el Ministerio de Vivienda y Urbanismo dictará una resolución, visada por la Dirección de Presupuestos, que distribuirá este monto entre los SERVIU y la Subsecretaría conforme a criterios técnicos y al programa de actividades, materias que deberán explicitarse en la resolución señalada. No se podrán efectuar gastos en personal con cargo a estos recursos. d) Con cargo a estos recursos se podrá destinar para el Plan de Gestión de la Calidad, hasta $ 1.722.338 miles, para gastos asociados a la fiscalización, evaluación y otras acciones relacionadas a proyectos en ejecución de los programas habitacionales y obras urbanas relacionadas, como asimismo, respecto a proyectos en los que el Ministerio de Vivienda y Urbanismo prevea una inversión futura. Previo a la ejecución del gasto, el Ministerio de Vivienda y Urbanismo dictará una resolución, visada por la Dirección de Presupuestos, que distribuirá este monto entre los SERVIU y la Subsecretaría conforme a criterios técnicos, y al programa de actividades, materias que deberán explicitarse en la resolución señalada. No se podrán efectuar gastos en personal con cargo a estos recursos.",
          "url": "https://www.dipres.gob.cl/597/articles-257470_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2023": {
          "anio": 2023,
          "disponible": true,
          "ley_numero": "Ley N° 21.516",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2022-12-20",
          "numero_glosa": "Glosa 03 (letras a–d)",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Subtítulo 33, Ítem 01 · Glosa 03 (letras a–d)",
          "texto": "Asociada a Subtítulo 33, Ítem 01: a) El programa del año quedará conformado exclusivamente por aquellos subsidios cuyo proceso de postulación haya concluido el 31 de diciembre del 2023. b) Los montos consignados en los presupuestos de cada SERVIU a nivel de asignación del referido ítem podrán ser excedidos hasta el mes de octubre, con el objeto de dar continuidad al pago de los respectivos certificados de subsidios, no pudiendo sobrepasarse la cantidad total del ítem. c) Con cargo a estos recursos se podrá destinar hasta $ 3.374.047 miles para gastos de administración asociados directamente con el proceso de llamado, postulación y selección de beneficiarios. Previo a la ejecución del gasto, el Ministerio de Vivienda y Urbanismo dictará una resolución, visada por la Dirección de Presupuestos, que distribuirá este monto entre los SERVIU y la Subsecretaría conforme a criterios técnicos y al programa de actividades, materias que deberán explicitarse en la resolución señalada. No se podrán efectuar gastos en personal con cargo a estos recursos. d) Con cargo a estos recursos se podrá destinar para el Plan de Gestión de la Calidad, hasta $ 4.746.432 miles, para gastos asociados a la fiscalización, evaluación y otras acciones relacionadas a proyectos en ejecución de los programas habitacionales y obras urbanas relacionadas, como asimismo, respecto a proyectos en los que el Ministerio de Vivienda y Urbanismo prevea una inversión futura. Previo a la ejecución del gasto, el Ministerio de Vivienda y Urbanismo dictará una resolución, visada por la Dirección de Presupuestos, que distribuirá este monto entre los SERVIU y la Subsecretaría conforme a criterios técnicos, y al programa de actividades, materias que deberán explicitarse en la resolución señalada. No se podrán efectuar gastos en personal con cargo a estos recursos.",
          "url": "https://www.dipres.gob.cl/597/articles-299419_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2024": {
          "anio": 2024,
          "disponible": true,
          "ley_numero": "Ley N° 21.640",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2023-12-18",
          "numero_glosa": "Glosa 03 (letras a–d)",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Subtítulo 33, Ítem 01 · Glosa 03 (letras a–d)",
          "texto": "Asociada a Subtítulo 33, Ítem 01: a) El programa del año quedará conformado exclusivamente por aquellos subsidios cuyo proceso de postulación haya concluido el 31 de diciembre del 2024. b) Los montos consignados en los presupuestos de cada SERVIU a nivel de asignación del referido ítem podrán ser excedidos hasta el mes de octubre, con el objeto de dar continuidad al pago de los respectivos certificados de subsidios, no pudiendo sobrepasarse la cantidad total del ítem. c) Con cargo a estos recursos se podrá destinar hasta $ 3.492.139 miles para gastos de administración asociados directamente con el proceso de llamado, postulación y selección de beneficiarios. Previo a la ejecución del gasto, el Ministerio de Vivienda y Urbanismo dictará una resolución, visada por la Dirección de Presupuestos, que distribuirá este monto entre los SERVIU y la Subsecretaría conforme a criterios técnicos y al programa de actividades, materias que deberán explicitarse en la resolución señalada. No se podrán efectuar gastos en personal con cargo a estos recursos. d) Con cargo a estos recursos se podrá destinar para el Plan de Gestión de la Calidad, hasta $ 4.912.557 miles, para gastos asociados a la fiscalización, evaluación y otras acciones relacionadas a proyectos en ejecución de los programas habitacionales y obras urbanas relacionadas, como asimismo, respecto a proyectos en los que el Ministerio de Vivienda y Urbanismo prevea una inversión futura. Previo a la ejecución del gasto, el Ministerio de Vivienda y Urbanismo dictará una resolución, visada por la Dirección de Presupuestos, que distribuirá este monto entre los SERVIU y la Subsecretaría conforme a criterios técnicos, y al programa de actividades, materias que deberán explicitarse en la resolución señalada. No se podrán efectuar gastos en personal con cargo a estos recursos.",
          "url": "https://www.dipres.gob.cl/597/articles-325504_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2025": {
          "anio": 2025,
          "disponible": true,
          "ley_numero": "Ley N° 21.722",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2024-12-13",
          "numero_glosa": "Glosa 03 (letras a–d)",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Subtítulo 33, Ítem 01 · Glosa 03 (letras a–d)",
          "texto": "Asociada a Subtítulo 33, Ítem 01: a) El programa del año quedará conformado exclusivamente por aquellos subsidios cuyo proceso de postulación haya concluido el 31 de diciembre del 2025. b) Los montos consignados en los presupuestos de cada SERVIU a nivel de asignación del referido ítem podrán ser excedidos hasta el mes de octubre, con el objeto de dar continuidad al pago de los respectivos certificados de subsidios, no pudiendo sobrepasarse la cantidad total del ítem. c) Con cargo a estos recursos se podrá destinar hasta $3.638.809 miles para gastos de administración asociados directamente con el proceso de llamado, postulación y selección de beneficiarios. Previo a la ejecución del gasto, el Ministerio de Vivienda y Urbanismo dictará una resolución, visada por la Dirección de Presupuestos, que distribuirá este monto entre los SERVIU y la Subsecretaría conforme a criterios técnicos y al programa de actividades, materias que deberán explicitarse en la resolución señalada. No se podrán efectuar gastos en personal con cargo a estos recursos. d) Con cargo a estos recursos se podrá destinar para el Plan de Gestión de la Calidad, hasta $5.254.806 miles, para gastos asociados a la fiscalización, evaluación y otras acciones relacionadas a proyectos en ejecución de los programas habitacionales y obras urbanas relacionadas, como asimismo, respecto a proyectos en los que el Ministerio de Vivienda y Urbanismo prevea una inversión futura. Previo a la ejecución del gasto, el Ministerio de Vivienda y Urbanismo dictará una resolución, visada por la Dirección de Presupuestos, que distribuirá este monto entre los SERVIU y la Subsecretaría conforme a criterios técnicos, y al programa de actividades, materias que deberán explicitarse en la resolución señalada. No se podrán efectuar gastos en personal con cargo a estos recursos.",
          "url": "https://www.dipres.gob.cl/597/articles-355270_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2026": {
          "anio": 2026,
          "disponible": true,
          "ley_numero": "Ley N° 21.796",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2025-12-12",
          "numero_glosa": "Glosa 03 (letras a–d)",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Subtítulo 33, Ítem 01 · Glosa 03 (letras a–d) (p. 914)",
          "texto": "Asociada a Subtítulo 33, Ítem 01: a) El programa del año quedará conformado exclusivamente por aquellos subsidios cuyo proceso de postulación haya concluido el 31 de diciembre del 2026. Conforme a lo indicado en la ley N°18.591 en su Art. 40, la resolución conjunta que autoriza los llamados a postulaciones para los distintos tipos de subsidios habitacionales, deberá incluir el número de unidades por programa y los recursos a destinar para su financiamiento. b) Los montos consignados en los presupuestos de cada SERVIU a nivel de asignación del referido ítem podrán ser excedidos hasta el mes de octubre, con el objeto de dar continuidad al pago de los respectivos certificados de subsidios, no pudiendo sobrepasarse la cantidad total del ítem. c) Con cargo a estos recursos se podrá destinar hasta $3.751.612 miles para gastos de administración asociados directamente con el proceso de llamado, postulación y selección de beneficiarios. Previo a la ejecución del gasto, el Ministerio de Vivienda y Urbanismo dictará una resolución, visada por la Dirección de Presupuestos, que distribuirá este monto entre los SERVIU y la Subsecretaría conforme a criterios técnicos y al programa de actividades, materias que deberán explicitarse en la resolución señalada. No se podrán efectuar gastos en personal con cargo a estos recursos. d) Con cargo a estos recursos se podrá destinar para el Plan de Gestión de la Calidad, hasta $5.417.705 miles, para gastos asociados a la fiscalización, evaluación y otras acciones relacionadas a proyectos en ejecución de los programas habitacionales y obras urbanas relacionadas, como asimismo, respecto a proyectos en los que el Ministerio de Vivienda y Urbanismo prevea una inversión futura. Previo a la ejecución del gasto, el Ministerio de Vivienda y Urbanismo dictará una resolución, visada por la Dirección de Presupuestos, que distribuirá este monto entre los SERVIU y la Subsecretaría conforme a criterios técnicos, y al programa de actividades, materias que deberán explicitarse en la resolución señalada. No se podrán efectuar gastos en personal con cargo a estos recursos.",
          "url": "https://www.dipres.gob.cl/597/articles-406493_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        }
      }
    },
    {
      "id": "subsidios_leasing_cupo",
      "titulo": "Cupo máximo anual de Subsidios Leasing Habitacional (Ley N° 19.281)",
      "materia": "Límite cuantitativo de subsidios de arrendamiento con promesa de compraventa",
      "programa_alcance": "Partida 18 · Conjunto de los SERVIU regionales · Subsidios Leasing (Ley N° 19.281)",
      "categorias": [
        "limites_uso"
      ],
      "cambio_numeracion": false,
      "traza_numeracion": "Glosa 01 (2021–2026)",
      "a_que_recursos_aplica": "A los subsidios habitacionales entregados bajo el sistema de arrendamiento con promesa de compraventa (Ley N° 19.281) administrados por el conjunto de los SERVIU del país.",
      "que_permite_o_exige": "Establece el número máximo absoluto de subsidios Leasing que el conjunto de los SERVIU puede otorgar durante el año presupuestario.",
      "diferencia_practica": "En 2021 y 2022 el tope legal estaba limitado a 3.000 subsidios anuales; a partir de 2023 (Ley N° 21.516) y hasta 2026 se amplió en un 66,7% hasta un máximo de 5.000 subsidios anuales.",
      "nota_evidencia_gasto": "La ampliación del cupo de 3.000 a 5.000 subsidios aumenta el techo legal autorizado, pero no implica automáticamente que se hayan asignado ni devengado los 5.000 cupos; la ejecución real debe revisarse en la asignación 33-01-127 Subsidios Leasing.",
      "versiones": {
        "2021": {
          "anio": 2021,
          "disponible": true,
          "ley_numero": "Ley N° 21.289",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2020-12-16",
          "numero_glosa": "Glosa 01",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Glosa 01",
          "texto": "Aplicación Ley N° 19.281, Subsidios Leasing. La cantidad de subsidios que podrán otorgarse por aplicación de la Ley N° 19.281 será de hasta 3.000, para el conjunto de los SERVIU.",
          "url": "https://www.dipres.gob.cl/597/articles-213658_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2022": {
          "anio": 2022,
          "disponible": true,
          "ley_numero": "Ley N° 21.395",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2021-12-15",
          "numero_glosa": "Glosa 01",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Glosa 01",
          "texto": "Aplicación Ley N° 19.281, Subsidios Leasing. La cantidad de subsidios que podrán otorgarse por aplicación de la Ley N° 19.281 será de hasta 3.000, para el conjunto de los SERVIU.",
          "url": "https://www.dipres.gob.cl/597/articles-257470_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2023": {
          "anio": 2023,
          "disponible": true,
          "ley_numero": "Ley N° 21.516",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2022-12-20",
          "numero_glosa": "Glosa 01",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Glosa 01",
          "texto": "Aplicación Ley N° 19.281, Subsidios Leasing. La cantidad de subsidios que podrán otorgarse por aplicación de la Ley N° 19.281 será de hasta 5.000, para el conjunto de los SERVIU.",
          "url": "https://www.dipres.gob.cl/597/articles-299419_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2024": {
          "anio": 2024,
          "disponible": true,
          "ley_numero": "Ley N° 21.640",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2023-12-18",
          "numero_glosa": "Glosa 01",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Glosa 01",
          "texto": "Aplicación Ley N° 19.281, Subsidios Leasing. La cantidad de subsidios que podrán otorgarse por aplicación de la Ley N° 19.281 será de hasta 5.000, para el conjunto de los SERVIU.",
          "url": "https://www.dipres.gob.cl/597/articles-325504_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2025": {
          "anio": 2025,
          "disponible": true,
          "ley_numero": "Ley N° 21.722",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2024-12-13",
          "numero_glosa": "Glosa 01",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Glosa 01",
          "texto": "Aplicación Ley N° 19.281, Subsidios Leasing. La cantidad de subsidios que podrán otorgarse por aplicación de la Ley N° 19.281 será de hasta 5.000, para el conjunto de los SERVIU.",
          "url": "https://www.dipres.gob.cl/597/articles-355270_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2026": {
          "anio": 2026,
          "disponible": true,
          "ley_numero": "Ley N° 21.796",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2025-12-12",
          "numero_glosa": "Glosa 01",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Glosa 01 (p. 912)",
          "texto": "Aplicación Ley N° 19.281, Subsidios Leasing. La cantidad de subsidios que podrán otorgarse por aplicación de la Ley N° 19.281 será de hasta 5.000, para el conjunto de los SERVIU.",
          "url": "https://www.dipres.gob.cl/597/articles-406493_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        }
      }
    },
    {
      "id": "informes_plan_inversiones_congreso",
      "titulo": "Obligación de informar Plan de Inversiones y avance regional al Congreso",
      "materia": "Rendición trimestral de recursos devengados, subsidios y viviendas entregadas por región",
      "programa_alcance": "Partida 18 · Ministerio de Vivienda y Urbanismo y SERVIU regionales",
      "categorias": [
        "obligaciones_informar"
      ],
      "cambio_numeracion": true,
      "traza_numeracion": "Glosa 05 (2021–2022) → Glosa 19 (2023) → Glosa 14 (2024–2025) → Glosa 12 (2026)",
      "a_que_recursos_aplica": "A toda la inversión y subsidios habitacionales ejecutados por el MINVU y los SERVIU en las 16 regiones, exigiendo distinguir proyectos de arrastre de años previos frente a soluciones nuevas.",
      "que_permite_o_exige": "Obliga al MINVU a enviar antes del 31 de marzo su Plan de Inversiones por región y modalidad, y a remitir informes trimestrales (a 30 días del cierre) con recursos devengados, subsidios otorgados y viviendas construidas y entregadas.",
      "diferencia_practica": "Aunque cambió cuatro veces de numeración (05 → 19 → 14 → 12), mantuvo su núcleo de transparencia regional y desde 2023 agregó el reporte sobre contratación de nuevos funcionarios en SEREMI Atacama. En paralelo, el Congreso multiplicó los reportes obligatorios: en 2025 pasó de 17 glosas en el Proyecto de Ley a 27 glosas en la Ley vigente (sumando desglose comunal trimestral en Glosa 26, que pasó a ser Glosa 23 en 2026).",
      "nota_evidencia_gasto": "Las obligaciones de informar no limitan directamente el monto ejecutable, pero elevan el escrutinio parlamentario sobre el arrastre, los devengos regionales y los compromisos financieros futuros.",
      "versiones": {
        "2021": {
          "anio": 2021,
          "disponible": true,
          "ley_numero": "Ley N° 21.289",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2020-12-16",
          "numero_glosa": "Glosa 05",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Glosa 05",
          "texto": "Antes del 31 de marzo de 2021, el Ministerio de Vivienda y Urbanismo deberá enviar a la Comisión Especial Mixta de Presupuestos el Plan de Inversiones 2021, detallando cantidad de solicitudes habitacionales por región, por modalidad de subsidio, y especificando si son arrastre de 2020 o nuevas soluciones. Asimismo, el MINVU deberá enviar trimestralmente, dentro de los treinta días siguientes al término del período respectivo, a la Comisión Especial Mixta de Presupuestos un informe sobre el avance en la inversión, por región, especificando recursos devengados, subsidios otorgados, y viviendas construidas y entregadas.",
          "url": "https://www.dipres.gob.cl/597/articles-213658_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2022": {
          "anio": 2022,
          "disponible": true,
          "ley_numero": "Ley N° 21.395",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2021-12-15",
          "numero_glosa": "Glosa 05",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Glosa 05",
          "texto": "Antes del 31 de marzo de 2022, el Ministerio de Vivienda y Urbanismo deberá enviar a la Comisión Especial Mixta de Presupuestos el Plan de Inversiones 2022, detallando cantidad de solicitudes habitacionales por región, por modalidad de subsidio, y especificando si son arrastre de 2021 o nuevas soluciones. Asimismo, el MINVU deberá enviar trimestralmente, dentro de los treinta días siguientes al término del período respectivo, a la Comisión Especial Mixta de Presupuestos un informe sobre el avance en la inversión, por región, especificando recursos devengados, subsidios otorgados, y viviendas construidas y entregadas.",
          "url": "https://www.dipres.gob.cl/597/articles-257470_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2023": {
          "anio": 2023,
          "disponible": true,
          "ley_numero": "Ley N° 21.516",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2022-12-20",
          "numero_glosa": "Glosa 19",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Glosa 19",
          "texto": "Antes del 31 de marzo de 2023, el Ministerio de Vivienda y Urbanismo deberá enviar a la Comisión Especial Mixta de Presupuestos el Plan de Inversiones 2023, detallando cantidad de solicitudes habitacionales por región, por modalidad de subsidio, y especificando si son arrastre de 2022 o nuevas soluciones. Asimismo, el MINVU deberá enviar trimestralmente, dentro de los treinta días siguientes al término del período respectivo, a la Comisión Especial Mixta de Presupuestos, un informe sobre el avance en la inversión, por región, especificando recursos devengados, subsidios otorgados, y viviendas construidas y entregadas. También deberá informar respecto de la destinación de recursos para la contratación de nuevos funcionarios en la Secretaría Regional Ministerial de Vivienda y Urbanismo en la Región de Atacama.",
          "url": "https://www.dipres.gob.cl/597/articles-299419_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2024": {
          "anio": 2024,
          "disponible": true,
          "ley_numero": "Ley N° 21.640",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2023-12-18",
          "numero_glosa": "Glosa 14",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Glosa 14",
          "texto": "Antes del 31 de marzo de 2024, el Ministerio de Vivienda y Urbanismo deberá enviar a la Comisión Especial Mixta de Presupuestos el Plan de Inversiones 2024, detallando cantidad de solicitudes habitacionales por región, por modalidad de subsidio, y especificando si son arrastre de 2023 o nuevas soluciones. Asimismo, el MINVU deberá enviar trimestralmente, dentro de los treinta días siguientes al término del período respectivo, a la Comisión Especial Mixta de Presupuestos, un informe sobre el avance en la inversión, por región, especificando recursos devengados, subsidios otorgados, y viviendas construidas y entregadas. También deberá informar respecto de la destinación de recursos para la contratación de nuevos funcionarios en la Secretaría Regional Ministerial de Vivienda y Urbanismo en la Región de Atacama.",
          "url": "https://www.dipres.gob.cl/597/articles-325504_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        },
        "2025": {
          "anio": 2025,
          "disponible": true,
          "ley_numero": "Ley N° 21.722",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2024-12-13",
          "numero_glosa": "Glosa 14",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Glosa 14",
          "texto": "Antes del 31 de marzo de 2025, el Ministerio de Vivienda y Urbanismo deberá enviar a la Comisión Especial Mixta de Presupuestos el Plan de Inversiones 2025, detallando cantidad de solicitudes habitacionales por región, por modalidad de subsidio, y especificando si son arrastre de 2024 o nuevas soluciones. Asimismo, el MINVU deberá enviar trimestralmente, dentro de los treinta días siguientes al término del período respectivo, a la Comisión Especial Mixta de Presupuestos, un informe sobre el avance en la inversión, por región, especificando recursos devengados, subsidios otorgados, y viviendas construidas y entregadas. También deberá informar respecto de la destinación de recursos para la contratación de nuevos funcionarios en la Secretaría Regional Ministerial de Vivienda y Urbanismo en la Región de Atacama.",
          "url": "https://www.dipres.gob.cl/597/articles-355270_doc_pdf.pdf",
          "nota_proyecto_vs_ley": "Proyecto de Ley 2025 traía 17 glosas institucionales; la Ley N° 21.722 vigente agregó 10 glosas adicionales de control e información (Glosas 18 a 27, incluyendo reporte comunal trimestral de 8 programas)."
        },
        "2026": {
          "anio": 2026,
          "disponible": true,
          "ley_numero": "Ley N° 21.796",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2025-12-12",
          "numero_glosa": "Glosa 12",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Glosa 12 (p. 922)",
          "texto": "Antes del 31 de marzo de 2026, el Ministerio de Vivienda y Urbanismo deberá enviar a la Comisión Especial Mixta de Presupuestos el Plan de Inversiones 2026, detallando cantidad de solicitudes habitacionales por región, por modalidad de subsidio, y especificando si son arrastre de 2025 o nuevas soluciones. Asimismo, el MINVU deberá enviar trimestralmente, dentro de los treinta días siguientes al término del período respectivo, a la Comisión Especial Mixta de Presupuestos, un informe sobre el avance en la inversión, por región, especificando recursos devengados, subsidios otorgados, y viviendas construidas y entregadas. También deberá informar respecto de la destinación de recursos para la contratación de nuevos funcionarios en la Secretaría Regional Ministerial de Vivienda y Urbanismo en la Región de Atacama.",
          "url": "https://www.dipres.gob.cl/597/articles-406493_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        }
      }
    },
    {
      "id": "desglose_comunal_trimestral_congreso",
      "titulo": "Reporte trimestral desglosado por comuna de 8 programas habitacionales (Ley vs Proyecto)",
      "materia": "Desglose territorial comunal de beneficiarios, montos asignados y ejecución",
      "programa_alcance": "Partida 18 · 8 programas: Mejoramiento, PPPF, Asentamientos Precarios, Leasing, DS 1, FSEV, Habitabilidad Rural y DS 19",
      "categorias": [
        "obligaciones_informar"
      ],
      "cambio_numeracion": true,
      "traza_numeracion": "Inexistente en 2021–2024 y ausente en Proyecto de Ley 2025 → Agregada por el Congreso como Glosa 26 (Ley 2025) → Glosa 23 (Ley 2026)",
      "a_que_recursos_aplica": "Al seguimiento territorial de los 8 principales programas de subsidios habitacionales y asentamientos precarios del MINVU en todas las comunas del país.",
      "que_permite_o_exige": "Exige al MINVU informar trimestralmente a la Comisión Especial Mixta la cantidad de beneficiarios, montos asignados y ejecución desglosados por región y comuna.",
      "diferencia_practica": "Ejemplifica la diferencia entre Proyecto de Ley y Ley vigente: no existía entre 2021 y 2024 ni venía en el Proyecto de Ley 2025 enviado por el Ejecutivo; fue incorporada por el Congreso en la Ley N° 21.722 (Glosa 26) y mantenida en la Ley N° 21.796 de 2026 (renumerada a Glosa 23).",
      "nota_evidencia_gasto": "Aumenta la trazabilidad comunal de la ejecución, permitiendo contrastar si los montos nacionales llegan efectivamente a comunas pequeñas o aisladas, sin restringir por sí misma la facultad de gastar.",
      "versiones": {
        "2021": {
          "anio": 2021,
          "disponible": false,
          "ley_numero": "Ley N° 21.289",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2020-12-16",
          "numero_glosa": "Sin equivalente",
          "ubicacion": "Ley N° 21.289 · Partida 18",
          "texto": "",
          "url": "https://www.dipres.gob.cl/597/articles-213658_doc_pdf.pdf",
          "sin_dato_motivo": "Esta obligación de desglose comunal trimestral no existía en la Ley N° 21.289 (2021); recién se incorporó en la Ley N° 21.722 de 2025."
        },
        "2022": {
          "anio": 2022,
          "disponible": false,
          "ley_numero": "Ley N° 21.395",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2021-12-15",
          "numero_glosa": "Sin equivalente",
          "ubicacion": "Ley N° 21.395 · Partida 18",
          "texto": "",
          "url": "https://www.dipres.gob.cl/597/articles-257470_doc_pdf.pdf",
          "sin_dato_motivo": "Esta obligación de desglose comunal trimestral no existía en la Ley N° 21.395 (2022); recién se incorporó en la Ley N° 21.722 de 2025."
        },
        "2023": {
          "anio": 2023,
          "disponible": false,
          "ley_numero": "Ley N° 21.516",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2022-12-20",
          "numero_glosa": "Sin equivalente",
          "ubicacion": "Ley N° 21.516 · Partida 18",
          "texto": "",
          "url": "https://www.dipres.gob.cl/597/articles-299419_doc_pdf.pdf",
          "sin_dato_motivo": "Esta obligación de desglose comunal trimestral no existía en la Ley N° 21.516 (2023); recién se incorporó en la Ley N° 21.722 de 2025."
        },
        "2024": {
          "anio": 2024,
          "disponible": false,
          "ley_numero": "Ley N° 21.640",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2023-12-18",
          "numero_glosa": "Sin equivalente",
          "ubicacion": "Ley N° 21.640 · Partida 18",
          "texto": "",
          "url": "https://www.dipres.gob.cl/597/articles-325504_doc_pdf.pdf",
          "sin_dato_motivo": "Esta obligación de desglose comunal trimestral no existía en la Ley N° 21.640 (2024); recién se incorporó en la Ley N° 21.722 de 2025."
        },
        "2025": {
          "anio": 2025,
          "disponible": true,
          "ley_numero": "Ley N° 21.722",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2024-12-13",
          "numero_glosa": "Glosa 26",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Glosa 26 (incorporada en Ley N° 21.722; ausente en Proyecto de Ley 2025)",
          "texto": "El Ministerio de Vivienda y Urbanismo informará trimestralmente a la Comisión Especial Mixta de Presupuestos la cantidad de beneficiarios, montos asignados y ejecución, en forma regionalizada y desglosado por comuna, de los Programas de Mejoramiento de la Vivienda y Barrios; Subsidio de Protección del Patrimonio Familiar; Asentamientos Precarios; Subsidio Leasing; Sistema Integrado de Subsidios; Fondo Solidario de Elección de Vivienda; Habitabilidad Rural y Programa de Integración Social y Territorial.",
          "url": "https://www.dipres.gob.cl/597/articles-355270_doc_pdf.pdf",
          "nota_proyecto_vs_ley": "Diferencia Proyecto vs Ley 2025: ausente en el Proyecto de Ley (articles-346698_doc_pdf.pdf, 17 glosas) e incorporada en el texto vigente aprobado por el Congreso (articles-355270_doc_pdf.pdf, Glosa 26)."
        },
        "2026": {
          "anio": 2026,
          "disponible": true,
          "ley_numero": "Ley N° 21.796",
          "tipo_texto": "ley_vigente",
          "tipo_texto_etiqueta": "Ley vigente publicada",
          "fecha_corte": "2025-12-12",
          "numero_glosa": "Glosa 23",
          "ubicacion": "Partida 18 · Glosas comunes a las Instituciones · Glosa 23 (p. 923)",
          "texto": "El Ministerio de Vivienda y Urbanismo informará trimestralmente a la Comisión Especial Mixta de Presupuestos la cantidad de beneficiarios, montos asignados y ejecución, en forma regionalizada y desglosado por comuna, de los Programas de Mejoramiento de la Vivienda y Barrios; Subsidio de Protección del Patrimonio Familiar; Asentamientos Precarios; Subsidio Leasing; Sistema Integrado de Subsidios; Fondo Solidario de Elección de Vivienda; Habitabilidad Rural y Programa de Integración Social y Territorial.",
          "url": "https://www.dipres.gob.cl/597/articles-406493_doc_pdf.pdf",
          "nota_proyecto_vs_ley": null
        }
      }
    }
  ],
  "restricciones_clave": [
    {
      "id": "restriccion_terrenos",
      "aspecto_regulado": "Compra de terrenos con recursos de subsidios (FSEV / DS 19)",
      "glosa_id": "terrenos_fsev_ds19",
      "ubicacion": "Glosa 11 (2021–2022) → Glosa 08 (2024–2025) → Glosa 25 (2026)",
      "condicion_endurecida": "Recorte del techo de compra de suelo (15% en 2021 a 5% en 2022), sub-tope de 1% máximo para estudios preliminares desde 2024, y nueva exigencia de visación previa de DIPRES en 2026.",
      "evidencia_textual": "Ley 2021 (Glosa 11): «podrán destinar hasta el 15%» → Ley 2022 (Glosa 11): «hasta el 5%» → Ley 2024–2025 (Glosa 08): «se destinará como máximo el 1% para los estudios preliminares» → Ley 2026 (Glosa 25): «con autorización del Ministerio de Vivienda y Urbanismo y con la visación previa de la Dirección de Presupuestos».",
      "anios_comparar_sugeridos": [
        2021,
        2026
      ]
    },
    {
      "id": "restriccion_prestamos_s32",
      "aspecto_regulado": "Préstamos de enlace SERVIU (Subtítulo 32)",
      "glosa_id": "prestamos_subtitulo_32",
      "ubicacion": "Glosa 06 (Ley 2025 vs Ley 2026)",
      "condicion_endurecida": "En 2026 se eliminaron dos facultades de financiamiento: se retiró a las «Municipalidades del país» como receptoras de préstamos y se suprimió la letra a) «Para adquirir el terreno».",
      "evidencia_textual": "Ley 2025 (Glosa 06): incluía «a Municipalidades del país» y «a) Para adquirir el terreno». Ley 2026 (Glosa 06): elimina ambas menciones y restringe los préstamos a construcción, obras DS 236 y vivienda en arriendo DS 52.",
      "anios_comparar_sugeridos": [
        2025,
        2026
      ]
    },
    {
      "id": "restriccion_transferencias_privados",
      "aspecto_regulado": "Transferencias a instituciones privadas / fundaciones (Subt. 24 y 33)",
      "glosa_id": "transferencias_privados_art23",
      "ubicacion": "Articulado General · Artículo 23 (Ley 2023 vs Ley 2024–2026)",
      "condicion_endurecida": "Amplió el concurso público obligatorio y el bloqueo de nuevas transferencias por incumplimiento desde solo transferencias corrientes hacia «transferencias corrientes y de capital», acotando la asignación directa a causales taxativas con resolución fundada.",
      "evidencia_textual": "Ley 2023 (Art. 23): «correspondientes a transferencias corrientes a instituciones privadas» → Ley 2024–2026 (Art. 23): «provenientes de transferencias corrientes y de capital [...] será el resultado de un concurso público abierto y transparente».",
      "anios_comparar_sugeridos": [
        2023,
        2025
      ]
    }
  ]
}
