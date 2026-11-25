/* Generado desde el documento oficial PDZE Aysén 2026-2035 (Res. Ex. SUBDERE N° 361 / 27.01.2026) */

export interface PdzeEtapa {
  etapa: 'Prefactibilidad' | 'Diseño' | 'Ejecución'
  institucion: string
  monto_subdere_millones: number
  monto_gore_millones: number
  monto_sectorial_millones: number
  monto_total_millones: number
  anio_inicio: number
  anio_termino: number
}

export interface PdzeIniciativa {
  id: string
  codigo_bip: string | null
  nombre: string
  comuna: string
  provincia: string
  instituciones: string[]
  institucion_principal: string
  etapas: PdzeEtapa[]
  monto_subdere_millones: number
  monto_gore_millones: number
  monto_sectorial_millones: number
  monto_total_millones: number
  anio_inicio: number
  anio_termino: number
  pagina_documento: number
}

export interface PdzeProvinciaResumen {
  id: string
  nombre: string
  iniciativas: number
  etapas: number
  pdze_miles: number
  sectorial_miles: number
  gore_miles: number
  subdere_miles: number
  nota?: string
  emblematicas: { nombre: string; monto_miles: number }[]
}

export interface PdzeComunaResumen {
  cut: string
  nombre: string
  provincia: string
  iniciativas: number
  etapas: number
  pdze_miles: number
  habitantes: number
  per_capita_miles: number
}

export interface PdzeDataset {
  esquema: string
  resumen_oficial: {
    titulo: string
    resolucion: string
    acuerdo_core: string
    horizonte: string
    url_oficial: string
    iniciativas_total: number
    etapas_total: number
    etapas_porcentaje: {
      ejecucion: number
      diseno: number
      prefactibilidad: number
    }
    presupuesto_total_miles: number
    financiamiento_miles: {
      sectorial: number
      gore_fndr: number
      subdere_pdze: number
    }
    financiamiento_pct: {
      sectorial: number
      gore_fndr: number
      subdere_pdze: number
    }
    nota_auditoria_documento: string
  }
  provincias: PdzeProvinciaResumen[]
  comunas: PdzeComunaResumen[]
  total_iniciativas_detalladas: number
  total_etapas_detalladas: number
  iniciativas: PdzeIniciativa[]
}

export const PDZE_AYSEN_2026: PdzeDataset = {
  "esquema": "pdze-aysen-2026-2035-v1",
  "resumen_oficial": {
    "titulo": "Plan de Desarrollo de Zonas Extremas (PDZE) · Región de Aysén 2026–2035",
    "resolucion": "Resolución Exenta (SUBDERE) N° 361 / 27.01.2026",
    "acuerdo_core": "Acuerdo CORE N° 6.959 (08.08.2025)",
    "horizonte": "2026–2035",
    "url_oficial": "https://www.goreaysen.cl",
    "iniciativas_total": 169,
    "etapas_total": 266,
    "etapas_porcentaje": {
      "ejecucion": 59,
      "diseno": 36,
      "prefactibilidad": 5
    },
    "presupuesto_total_miles": 1688540177,
    "financiamiento_miles": {
      "sectorial": 1152851791,
      "gore_fndr": 365513982,
      "subdere_pdze": 170174404
    },
    "financiamiento_pct": {
      "sectorial": 68,
      "gore_fndr": 22,
      "subdere_pdze": 10
    },
    "nota_auditoria_documento": "Cifras oficiales extraídas del documento PDZE Aysén 2026–2035 (Res. Ex. SUBDERE N° 361/2026). Nota técnica: en la lámina resumen de la pág. 22 la caja de Provisión SUBDERE repite por error de diagramación el monto FNDR (M$ 365.513.982), aunque el texto oficial señala 68% Sectorial, 22% GORE (FNDR) y 10% Provisión PDZE (M$ 170.174.404 por diferencia sobre M$ 1.688.540.177). En la tabla de O'Higgins el libro publica los totales comunales (3 iniciativas, 5 etapas, M$ 8.977.765) y la obra emblemática Observatorio del Hielo."
  },
  "provincias": [
    {
      "id": "aysen",
      "nombre": "Provincia de Aysén",
      "iniciativas": 71,
      "etapas": 118,
      "pdze_miles": 594684919,
      "sectorial_miles": 329344266,
      "gore_miles": 79843270,
      "subdere_miles": 185497383,
      "emblematicas": [
        {
          "nombre": "Mejoramiento Ruta 7 Norte, sectores Las Pulgas–Puente la Unión y Las Peras–Puente Chucao (12,5 km)",
          "monto_miles": 58274000
        },
        {
          "nombre": "Desarrollo de puente urbano en Puerto Aysén",
          "monto_miles": 34208276
        },
        {
          "nombre": "Reposición Complejo Educacional Melinka",
          "monto_miles": 23323020
        },
        {
          "nombre": "Construcción de infraestructura turística P.N. Queulat",
          "monto_miles": 17245019
        }
      ]
    },
    {
      "id": "coyhaique",
      "nombre": "Provincia de Coyhaique",
      "iniciativas": 44,
      "etapas": 67,
      "pdze_miles": 762096064,
      "sectorial_miles": 591518567,
      "gore_miles": 120607997,
      "subdere_miles": 49969500,
      "emblematicas": [
        {
          "nombre": "Reposición Hospital Regional Coyhaique",
          "monto_miles": 194000000
        },
        {
          "nombre": "Mejoramiento Ruta 7 (Ruta 240–Los Torreones y Coyhaique–Valle Simpson, 43 km)",
          "monto_miles": 67500000
        },
        {
          "nombre": "Construcción Establecimiento Penitenciario Coyhaique",
          "monto_miles": 54560000
        },
        {
          "nombre": "Construcción infraestructura fundacional Universidad de Aysén",
          "monto_miles": 35836759
        }
      ]
    },
    {
      "id": "general_carrera",
      "nombre": "Provincia General Carrera",
      "iniciativas": 37,
      "etapas": 56,
      "pdze_miles": 247380617,
      "sectorial_miles": 177698046,
      "gore_miles": 39512686,
      "subdere_miles": 30169885,
      "emblematicas": [
        {
          "nombre": "Mejoramiento y pavimentación Ruta 7 Sur (63,5 km)",
          "monto_miles": 56263250
        },
        {
          "nombre": "Construcción puente Desagüe Lago General Carrera (Chile Chico)",
          "monto_miles": 45000000
        },
        {
          "nombre": "Construcción Centro de Salud Puerto Río Tranquilo",
          "monto_miles": 11250000
        },
        {
          "nombre": "Construcción Terminal de Buses Puerto Río Tranquilo",
          "monto_miles": 3797087
        }
      ]
    },
    {
      "id": "capitan_prat",
      "nombre": "Provincia Capitán Prat",
      "iniciativas": 17,
      "etapas": 25,
      "pdze_miles": 84378577,
      "sectorial_miles": 54290312,
      "gore_miles": 19895916,
      "subdere_miles": 10192349,
      "nota": "Complementa el Plan de Desarrollo Provincia de los Glaciares 2021–2028 (Acuerdo CORE 5657).",
      "emblematicas": [
        {
          "nombre": "Mejoramiento de caminos varios de la Ruta 7 (23,5 km + 15 km Cochrane–Lago Juncal)",
          "monto_miles": 36000000
        },
        {
          "nombre": "Construcción de Polideportivo Provincial, Cochrane",
          "monto_miles": 7664000
        },
        {
          "nombre": "Reposición Gimnasio Centro Comunitario Caleta Tortel",
          "monto_miles": 3000000
        },
        {
          "nombre": "Centro de Desarrollo Científico, Cultural y Turístico Observatorio del Hielo (O’Higgins)",
          "monto_miles": 2943365
        }
      ]
    }
  ],
  "comunas": [
    {
      "cut": "11202",
      "nombre": "Cisnes",
      "provincia": "Provincia de Aysén",
      "iniciativas": 23,
      "etapas": 36,
      "pdze_miles": 169631131,
      "habitantes": 5137,
      "per_capita_miles": 33021
    },
    {
      "cut": "11201",
      "nombre": "Aysén",
      "provincia": "Provincia de Aysén",
      "iniciativas": 38,
      "etapas": 66,
      "pdze_miles": 354629684,
      "habitantes": 23170,
      "per_capita_miles": 8165
    },
    {
      "cut": "11203",
      "nombre": "Guaitecas",
      "provincia": "Provincia de Aysén",
      "iniciativas": 10,
      "etapas": 16,
      "pdze_miles": 70424104,
      "habitantes": 1598,
      "per_capita_miles": 44070
    },
    {
      "cut": "11101",
      "nombre": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "iniciativas": 36,
      "etapas": 53,
      "pdze_miles": 743552256,
      "habitantes": 57823,
      "per_capita_miles": 12859
    },
    {
      "cut": "11102",
      "nombre": "Lago Verde",
      "provincia": "Provincia de Coyhaique",
      "iniciativas": 8,
      "etapas": 14,
      "pdze_miles": 48488558,
      "habitantes": 779,
      "per_capita_miles": 62245
    },
    {
      "cut": "11401",
      "nombre": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "iniciativas": 15,
      "etapas": 21,
      "pdze_miles": 103825902,
      "habitantes": 4905,
      "per_capita_miles": 21167
    },
    {
      "cut": "11402",
      "nombre": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "iniciativas": 22,
      "etapas": 35,
      "pdze_miles": 143554715,
      "habitantes": 2723,
      "per_capita_miles": 52719
    },
    {
      "cut": "11301",
      "nombre": "Cochrane",
      "provincia": "Provincia Capitán Prat",
      "iniciativas": 8,
      "etapas": 12,
      "pdze_miles": 63576706,
      "habitantes": 3458,
      "per_capita_miles": 18154
    },
    {
      "cut": "11303",
      "nombre": "Tortel",
      "provincia": "Provincia Capitán Prat",
      "iniciativas": 6,
      "etapas": 8,
      "pdze_miles": 12624500,
      "habitantes": 505,
      "per_capita_miles": 24999
    },
    {
      "cut": "11302",
      "nombre": "O’Higgins",
      "provincia": "Provincia Capitán Prat",
      "iniciativas": 3,
      "etapas": 5,
      "pdze_miles": 8977765,
      "habitantes": 647,
      "per_capita_miles": 13876
    }
  ],
  "total_iniciativas_detalladas": 167,
  "total_etapas_detalladas": 262,
  "iniciativas": [
    {
      "id": "pdze-40012598-0",
      "codigo_bip": "40012598-0",
      "nombre": "MEJORAMIENTO RUTA 7 NORTE, SECTOR LAS PULGAS-PUENTE UNIÓN, COMUNA DE CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 13274.0,
          "monto_total_millones": 13274.0,
          "anio_inicio": 2027,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 13274.0,
      "monto_total_millones": 13274.0,
      "anio_inicio": 2027,
      "anio_termino": 2029,
      "pagina_documento": 25,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40012970-0",
      "codigo_bip": "40012970-0",
      "nombre": "MEJORAMIENTO RUTA 7 NORTE, SECTOR PUENTE CHUCAO-PORTEZUELO QUEULAT, COMUNA CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 45000.0,
          "monto_total_millones": 45000.0,
          "anio_inicio": 2027,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 45000.0,
      "monto_total_millones": 45000.0,
      "anio_inicio": 2027,
      "anio_termino": 2030,
      "pagina_documento": 25,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40066337-0",
      "codigo_bip": "40066337-0",
      "nombre": "MEJORAMIENTO CAMINO X-120 SECTOR LA JUNTA - PTO. RAÚL MARÍN B., COMUNA CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1200.0,
          "monto_total_millones": 1200.0,
          "anio_inicio": 2029,
          "anio_termino": 2031
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 10950.0,
          "monto_total_millones": 10950.0,
          "anio_inicio": 2033,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 12150.0,
      "monto_total_millones": 12150.0,
      "anio_inicio": 2029,
      "anio_termino": 2035,
      "pagina_documento": 25,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064103-0",
      "codigo_bip": "40064103-0",
      "nombre": "REPOSICIÓN PASARELA RÍO QUINTO EN CAMINO X-111, COMUNA DE CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 700.0,
          "monto_total_millones": 700.0,
          "anio_inicio": 2030,
          "anio_termino": 2031
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 3000.0,
          "monto_total_millones": 3000.0,
          "anio_inicio": 2033,
          "anio_termino": 2034
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 3700.0,
      "monto_total_millones": 3700.0,
      "anio_inicio": 2030,
      "anio_termino": 2034,
      "pagina_documento": 25,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064109-0",
      "codigo_bip": "40064109-0",
      "nombre": "CONSTRUCCIÓN CAMINO CRUCE PALENA - MELIMOYU - SENO GALA, COMUNA DE CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 2250.0,
          "monto_total_millones": 2250.0,
          "anio_inicio": 2029,
          "anio_termino": 2031
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 8050.0,
          "monto_total_millones": 8050.0,
          "anio_inicio": 2034,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 10300.0,
      "monto_total_millones": 10300.0,
      "anio_inicio": 2029,
      "anio_termino": 2035,
      "pagina_documento": 25,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40066340-0",
      "codigo_bip": "40066340-0",
      "nombre": "CONSTRUCCIÓN CAMINO COSTERO SECTOR PUERTO CISNES - PUNTA DE VITT, COMUNA CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 2250.0,
          "monto_total_millones": 2250.0,
          "anio_inicio": 2032,
          "anio_termino": 2034
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 2250.0,
      "monto_total_millones": 2250.0,
      "anio_inicio": 2032,
      "anio_termino": 2034,
      "pagina_documento": 25,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40020096-0",
      "codigo_bip": "40020096-0",
      "nombre": "MEJORAMIENTO INTEGRAL AERÓDROMO MELIMOYU",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DAP"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DAP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 729.4,
          "monto_total_millones": 729.4,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DAP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 3126.0,
          "monto_total_millones": 3126.0,
          "anio_inicio": 2030,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 3855.4,
      "monto_total_millones": 3855.4,
      "anio_inicio": 2027,
      "anio_termino": 2031,
      "pagina_documento": 25,
      "institucion_principal": "MOP-DAP"
    },
    {
      "id": "pdze-40020094-0",
      "codigo_bip": "40020094-0",
      "nombre": "MEJORAMIENTO INTEGRAL AERÓDROMO PTO. CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DAP"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DAP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 729.4,
          "monto_total_millones": 729.4,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DAP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1948.54,
          "monto_total_millones": 1948.54,
          "anio_inicio": 2029,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 2677.94,
      "monto_total_millones": 2677.94,
      "anio_inicio": 2027,
      "anio_termino": 2031,
      "pagina_documento": 25,
      "institucion_principal": "MOP-DAP"
    },
    {
      "id": "pdze-40072305-0",
      "codigo_bip": "40072305-0",
      "nombre": "DIAGNÓSTICO DEFENSAS FLUVIALES RÍO CISNES, SECTOR AERÓDROMO",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DOH"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOH",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 4000.0,
          "monto_total_millones": 4000.0,
          "anio_inicio": 2027,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4000.0,
      "monto_total_millones": 4000.0,
      "anio_inicio": 2027,
      "anio_termino": 2029,
      "pagina_documento": 25,
      "institucion_principal": "MOP-DOH"
    },
    {
      "id": "pdze-30452524-0",
      "codigo_bip": "30452524-0",
      "nombre": "AMPLIACIÓN RAMPA ISLA TOTO CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 4500.0,
          "monto_total_millones": 4500.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4500.0,
      "monto_total_millones": 4500.0,
      "anio_inicio": 2027,
      "anio_termino": 2028,
      "pagina_documento": 25,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-40019943-0",
      "codigo_bip": "40019943-0",
      "nombre": "MEJORAMIENTO BORDE MARÍTIMO RAÚL MARÍN BALMACEDA, COMUNA CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 600.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 7500.0,
          "monto_total_millones": 7500.0,
          "anio_inicio": 2029,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 8100.0,
      "monto_total_millones": 8100.0,
      "anio_inicio": 2027,
      "anio_termino": 2031,
      "pagina_documento": 25,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-30316123-0",
      "codigo_bip": "30316123-0",
      "nombre": "CONSTRUCCIÓN INFRAESTRUCTURA TURÍSTICA P. N. QUEULAT",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "CONAF"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "CONAF",
          "monto_subdere_millones": 8622.509,
          "monto_gore_millones": 8622.51,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 17245.019,
          "anio_inicio": 2026,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 8622.509,
      "monto_gore_millones": 8622.51,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 17245.019,
      "anio_inicio": 2026,
      "anio_termino": 2030,
      "pagina_documento": 26,
      "institucion_principal": "CONAF"
    },
    {
      "id": "pdze-40064617-0",
      "codigo_bip": "40064617-0",
      "nombre": "CONSTRUCCIÓN CALZADA EN ADOCRETO AVDA. COSTANERA RAÚL MARÍN BALMACEDA, COMUNA DE CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Seremi de Vivienda y Urbanismo"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Seremi de Vivienda y Urbanismo",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 6500.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 6500.0,
          "anio_inicio": 2029,
          "anio_termino": 2032
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 6500.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 6500.0,
      "anio_inicio": 2029,
      "anio_termino": 2032,
      "pagina_documento": 26,
      "institucion_principal": "Seremi de Vivienda y Urbanismo"
    },
    {
      "id": "pdze-40064636-0",
      "codigo_bip": "40064636-0",
      "nombre": "CONSTRUCCIÓN 20 VIVIENDAS TUTELADAS LA JUNTA, COMUNA DE CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Seremi de Vivienda y Urbanismo"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Seremi de Vivienda y Urbanismo",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 2094.15,
          "monto_total_millones": 2094.15,
          "anio_inicio": 2030,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 2094.15,
      "monto_total_millones": 2094.15,
      "anio_inicio": 2030,
      "anio_termino": 2031,
      "pagina_documento": 26,
      "institucion_principal": "Seremi de Vivienda y Urbanismo"
    },
    {
      "id": "pdze-40072349-0",
      "codigo_bip": "40072349-0",
      "nombre": "PLAN DE GESTIÓN DE RESIDUOS, COMUNA DE CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Municipalidad de Cisnes"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Cisnes",
          "monto_subdere_millones": 62.0,
          "monto_gore_millones": 300.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 362.0,
          "anio_inicio": 2030,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 62.0,
      "monto_gore_millones": 300.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 362.0,
      "anio_inicio": 2030,
      "anio_termino": 2030,
      "pagina_documento": 26,
      "institucion_principal": "Municipalidad de Cisnes"
    },
    {
      "id": "pdze-40072270-0",
      "codigo_bip": "40072270-0",
      "nombre": "CONSTRUCCIÓN ALCANTARILLADO Y PLANTA DE TRATAMIENTO DE PUERTO RMB, COMUNA DE CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Municipalidad de Cisnes"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Cisnes",
          "monto_subdere_millones": 2948.5,
          "monto_gore_millones": 3948.5,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 6897.0,
          "anio_inicio": 2029,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 2948.5,
      "monto_gore_millones": 3948.5,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 6897.0,
      "anio_inicio": 2029,
      "anio_termino": 2031,
      "pagina_documento": 26,
      "institucion_principal": "Municipalidad de Cisnes"
    },
    {
      "id": "pdze-40031207-0",
      "codigo_bip": "40031207-0",
      "nombre": "CONSTRUCCIÓN RODOVIARIO DE PUERTO CISNES, COMUNA DE CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Municipalidad de Cisnes"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Cisnes",
          "monto_subdere_millones": 50.767,
          "monto_gore_millones": 500.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 550.767,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Cisnes",
          "monto_subdere_millones": 2500.0,
          "monto_gore_millones": 2500.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 5000.0,
          "anio_inicio": 2027,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 2550.767,
      "monto_gore_millones": 3000.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 5550.767,
      "anio_inicio": 2026,
      "anio_termino": 2029,
      "pagina_documento": 26,
      "institucion_principal": "Municipalidad de Cisnes"
    },
    {
      "id": "pdze-40031208-0",
      "codigo_bip": "40031208-0",
      "nombre": "CONSTRUCCIÓN RODOVIARIO LA JUNTA, COMUNA DE CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Municipalidad de Cisnes"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Cisnes",
          "monto_subdere_millones": 94.355,
          "monto_gore_millones": 100.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 194.355,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Cisnes",
          "monto_subdere_millones": 2500.0,
          "monto_gore_millones": 2500.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 5000.0,
          "anio_inicio": 2027,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 2594.355,
      "monto_gore_millones": 2600.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 5194.355,
      "anio_inicio": 2026,
      "anio_termino": 2029,
      "pagina_documento": 26,
      "institucion_principal": "Municipalidad de Cisnes"
    },
    {
      "id": "pdze-40072123-0",
      "codigo_bip": "40072123-0",
      "nombre": "MEJORAMIENTO ESTADIO PUYUHUAPI, COMUNA DE CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "GORE"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "GORE",
          "monto_subdere_millones": 855.25,
          "monto_gore_millones": 855.25,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 1710.5,
          "anio_inicio": 2026,
          "anio_termino": 2027
        }
      ],
      "monto_subdere_millones": 855.25,
      "monto_gore_millones": 855.25,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 1710.5,
      "anio_inicio": 2026,
      "anio_termino": 2027,
      "pagina_documento": 26,
      "institucion_principal": "GORE"
    },
    {
      "id": "pdze-40072611-0",
      "codigo_bip": "40072611-0",
      "nombre": "CONSTRUCCIÓN ACCESO RECINTO PORTUARIO CISNES, COMUNA DE CISNES",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "GORE"
      ],
      "etapas": [
        {
          "etapa": "Prefactibilidad",
          "institucion": "GORE",
          "monto_subdere_millones": 350.0,
          "monto_gore_millones": 350.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 700.0,
          "anio_inicio": 2028,
          "anio_termino": 2029
        },
        {
          "etapa": "Diseño",
          "institucion": "GORE",
          "monto_subdere_millones": 400.0,
          "monto_gore_millones": 400.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 800.0,
          "anio_inicio": 2031,
          "anio_termino": 2032
        },
        {
          "etapa": "Ejecución",
          "institucion": "GORE",
          "monto_subdere_millones": 650.0,
          "monto_gore_millones": 650.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 1300.0,
          "anio_inicio": 2034,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 1400.0,
      "monto_gore_millones": 1400.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 2800.0,
      "anio_inicio": 2028,
      "anio_termino": 2035,
      "pagina_documento": 26,
      "institucion_principal": "GORE"
    },
    {
      "id": "pdze-40011137-0",
      "codigo_bip": "40011137-0",
      "nombre": "REPOSICIÓN RETÉN RAÚL MARÍN BALMACEDA",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Carabineros"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 170.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 170.0,
          "anio_inicio": 2028,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 4000.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 4000.0,
          "anio_inicio": 2030,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 4170.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 4170.0,
      "anio_inicio": 2028,
      "anio_termino": 2031,
      "pagina_documento": 26,
      "institucion_principal": "Carabineros"
    },
    {
      "id": "pdze-40019759-0",
      "codigo_bip": "40019759-0",
      "nombre": "REPOSICIÓN RETÉN PUYUHUAPI",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Carabineros"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 150.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 150.0,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 3500.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 3500.0,
          "anio_inicio": 2028,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 3650.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 3650.0,
      "anio_inicio": 2026,
      "anio_termino": 2029,
      "pagina_documento": 26,
      "institucion_principal": "Carabineros"
    },
    {
      "id": "pdze-40038446-0",
      "codigo_bip": "40038446-0",
      "nombre": "REPOSICIÓN TENENCIA LA JUNTA",
      "comuna": "Cisnes",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Carabineros"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 150.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 150.0,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 3500.0,
          "monto_total_millones": 3500.0,
          "anio_inicio": 2028,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 150.0,
      "monto_sectorial_millones": 3500.0,
      "monto_total_millones": 3650.0,
      "anio_inicio": 2026,
      "anio_termino": 2029,
      "pagina_documento": 26,
      "institucion_principal": "Carabineros"
    },
    {
      "id": "pdze-40049245-0",
      "codigo_bip": "40049245-0",
      "nombre": "MEJORAMIENTO CONEXIÓN VIAL PUERTO AYSÉN - PUERTO CHACABUCO, COMUNA AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Prefactibilidad",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 898.964,
          "monto_total_millones": 898.964,
          "anio_inicio": 2026,
          "anio_termino": 2027
        },
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1000.0,
          "monto_total_millones": 1000.0,
          "anio_inicio": 2028,
          "anio_termino": 2030
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 25000.0,
          "monto_total_millones": 25000.0,
          "anio_inicio": 2032,
          "anio_termino": 2034
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 26898.964,
      "monto_total_millones": 26898.964,
      "anio_inicio": 2026,
      "anio_termino": 2034,
      "pagina_documento": 28,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064950-0",
      "codigo_bip": "40064950-0",
      "nombre": "MEJORAMIENTO CAMINO X-500 CRUCE RUTA 7 (CRUCE CABEZAS) - VIVIANA - CRUCE RUTA 240 (EL BALSEO), COMUNA AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 700.0,
          "monto_total_millones": 700.0,
          "anio_inicio": 2032,
          "anio_termino": 2033
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 700.0,
      "monto_total_millones": 700.0,
      "anio_inicio": 2032,
      "anio_termino": 2033,
      "pagina_documento": 28,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-30073043-0",
      "codigo_bip": "30073043-0",
      "nombre": "MEJORAMIENTO CAMINO PTO. TRANQUILO - EXPLORADORES, AYSÉN, COMUNAS RÍO IBÁÑEZ Y AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 10.0,
          "monto_total_millones": 10.0,
          "anio_inicio": 2035,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 10.0,
      "monto_total_millones": 10.0,
      "anio_inicio": 2035,
      "anio_termino": 2035,
      "pagina_documento": 28,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064091-0",
      "codigo_bip": "40064091-0",
      "nombre": "REPOSICIÓN PUENTE CIFUENTES, VILLA MAÑIHUALES, COMUNA AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 700.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 700.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 2500.0,
          "monto_total_millones": 2500.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 700.0,
      "monto_sectorial_millones": 2500.0,
      "monto_total_millones": 3200.0,
      "anio_inicio": 2027,
      "anio_termino": 2030,
      "pagina_documento": 28,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40027590-0",
      "codigo_bip": "40027590-0",
      "nombre": "REPOSICIÓN PUENTE GRAN PANGAL RUTA X-544, PUERTO AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 365.694,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 365.694,
          "anio_inicio": 2026,
          "anio_termino": 2027
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 2500.0,
          "monto_total_millones": 2500.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 365.694,
      "monto_sectorial_millones": 2500.0,
      "monto_total_millones": 2865.694,
      "anio_inicio": 2026,
      "anio_termino": 2030,
      "pagina_documento": 28,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064096-0",
      "codigo_bip": "40064096-0",
      "nombre": "REPOSICIÓN PASARELA PANGAL 1 EN CAMINO X-544, COMUNA AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 700.0,
          "monto_total_millones": 700.0,
          "anio_inicio": 2030,
          "anio_termino": 2031
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1200.0,
          "monto_total_millones": 1200.0,
          "anio_inicio": 2032,
          "anio_termino": 2034
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 1900.0,
      "monto_total_millones": 1900.0,
      "anio_inicio": 2030,
      "anio_termino": 2034,
      "pagina_documento": 28,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40019922-0",
      "codigo_bip": "40019922-0",
      "nombre": "REPOSICIÓN PUENTE RÍO LOS PALOS, RUTA X-528, COMUNA DE AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 309.0,
          "monto_total_millones": 309.0,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 15864.0,
          "monto_total_millones": 15864.0,
          "anio_inicio": 2027,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 16173.0,
      "monto_total_millones": 16173.0,
      "anio_inicio": 2026,
      "anio_termino": 2030,
      "pagina_documento": 28,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40063253-0",
      "codigo_bip": "40063253-0",
      "nombre": "CONSTRUCCIÓN PUENTE EL BLANCO, COMUNA DE AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 3151.242,
          "monto_total_millones": 3151.242,
          "anio_inicio": 2026,
          "anio_termino": 2027
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 3151.242,
      "monto_total_millones": 3151.242,
      "anio_inicio": 2026,
      "anio_termino": 2027,
      "pagina_documento": 29,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064102-0",
      "codigo_bip": "40064102-0",
      "nombre": "REPOSICIÓN PASARELA LOS TORREONES 1 EN CAMINO X-572, COMUNA AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 800.0,
          "monto_total_millones": 800.0,
          "anio_inicio": 2031,
          "anio_termino": 2032
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 4000.0,
          "monto_total_millones": 4000.0,
          "anio_inicio": 2034,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4800.0,
      "monto_total_millones": 4800.0,
      "anio_inicio": 2031,
      "anio_termino": 2035,
      "pagina_documento": 29,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064839-0",
      "codigo_bip": "40064839-0",
      "nombre": "REPOSICIÓN PASARELA LOS TORREONES 2 EN CAMINO X-572, COMUNA AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 800.0,
          "monto_total_millones": 800.0,
          "anio_inicio": 2031,
          "anio_termino": 2032
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 4000.0,
          "monto_total_millones": 4000.0,
          "anio_inicio": 2034,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4800.0,
      "monto_total_millones": 4800.0,
      "anio_inicio": 2031,
      "anio_termino": 2035,
      "pagina_documento": 29,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064097-0",
      "codigo_bip": "40064097-0",
      "nombre": "REPOSICIÓN PASARELA CÓNDOR 1 EN CAMINO X-550, COMUNA AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1000.0,
          "monto_total_millones": 1000.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 1000.0,
      "monto_total_millones": 1000.0,
      "anio_inicio": 2027,
      "anio_termino": 2028,
      "pagina_documento": 29,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064098-0",
      "codigo_bip": "40064098-0",
      "nombre": "REPOSICIÓN PASARELA CÓNDOR 2 EN CAMINO X-550, COMUNA AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1000.0,
          "monto_total_millones": 1000.0,
          "anio_inicio": 2028,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 1000.0,
      "monto_total_millones": 1000.0,
      "anio_inicio": 2028,
      "anio_termino": 2029,
      "pagina_documento": 29,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064886-0",
      "codigo_bip": "40064886-0",
      "nombre": "MEJORAMIENTO CAMINOS VARIOS AYSÉN, SEGUNDA ETAPA, COMUNA AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 750.0,
          "monto_total_millones": 750.0,
          "anio_inicio": 2028,
          "anio_termino": 2029
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 30000.0,
          "monto_total_millones": 30000.0,
          "anio_inicio": 2031,
          "anio_termino": 2033
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 30750.0,
      "monto_total_millones": 30750.0,
      "anio_inicio": 2028,
      "anio_termino": 2033,
      "pagina_documento": 29,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40072357-0",
      "codigo_bip": "40072357-0",
      "nombre": "REPOSICIÓN PASARELA EL BALSEO EN CAMINO X-542, COMUNA DE AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 700.0,
          "monto_total_millones": 700.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 2500.0,
          "monto_total_millones": 2500.0,
          "anio_inicio": 2030,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 3200.0,
      "monto_total_millones": 3200.0,
      "anio_inicio": 2027,
      "anio_termino": 2031,
      "pagina_documento": 29,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40072244-0",
      "codigo_bip": "40072244-0",
      "nombre": "CONSTRUCCIÓN DEFENSAS FLUVIALES RÍO SIMPSON SECTOR LOS TORREONES - ESTERO CARACOLES",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DOH"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOH",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 400.0,
          "monto_total_millones": 400.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOH",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 4000.0,
          "monto_total_millones": 4000.0,
          "anio_inicio": 2028,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4400.0,
      "monto_total_millones": 4400.0,
      "anio_inicio": 2027,
      "anio_termino": 2030,
      "pagina_documento": 29,
      "institucion_principal": "MOP-DOH"
    },
    {
      "id": "pdze-40072264-0",
      "codigo_bip": "40072264-0",
      "nombre": "CONSTRUCCIÓN DEFENSAS FLUVIALES RÍO MAÑIHUALES, SECTOR VIVIANA",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DOH"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOH",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 400.0,
          "monto_total_millones": 400.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOH",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 4000.0,
          "monto_total_millones": 4000.0,
          "anio_inicio": 2029,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4400.0,
      "monto_total_millones": 4400.0,
      "anio_inicio": 2029,
      "anio_termino": 2031,
      "pagina_documento": 29,
      "institucion_principal": "MOP-DOH"
    },
    {
      "id": "pdze-40072277-0",
      "codigo_bip": "40072277-0",
      "nombre": "CONSTRUCCIÓN INFRAESTRUCTURA RÍO ÑIREHUAO, SECTOR CEMENTERIO MAÑIHUALES",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DOH"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOH",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 400.0,
          "monto_total_millones": 400.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOH",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 4000.0,
          "monto_total_millones": 4000.0,
          "anio_inicio": 2029,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4400.0,
      "monto_total_millones": 4400.0,
      "anio_inicio": 2029,
      "anio_termino": 2031,
      "pagina_documento": 30,
      "institucion_principal": "MOP-DOH"
    },
    {
      "id": "pdze-30089888-0",
      "codigo_bip": "30089888-0",
      "nombre": "CONSTRUCCIÓN INFRAESTRUCTURA PORTUARIA RÍO AYSÉN, SECTOR PUERTO AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 6386.0,
          "monto_total_millones": 6386.0,
          "anio_inicio": 2027,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 6386.0,
      "monto_total_millones": 6386.0,
      "anio_inicio": 2027,
      "anio_termino": 2029,
      "pagina_documento": 30,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-40010823-0",
      "codigo_bip": "40010823-0",
      "nombre": "REPOSICIÓN Y AMPLIACIÓN MUELLE LA BALSA, AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 350.0,
          "monto_total_millones": 350.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 3000.0,
          "monto_total_millones": 3000.0,
          "anio_inicio": 2029,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 3350.0,
      "monto_total_millones": 3350.0,
      "anio_inicio": 2027,
      "anio_termino": 2031,
      "pagina_documento": 30,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-30481318-0",
      "codigo_bip": "30481318-0",
      "nombre": "AMPLIACIÓN INFRAESTRUCTURA PORTUARIA EXPLORADORES, COMUNA AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 600.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 5000.0,
          "monto_total_millones": 5000.0,
          "anio_inicio": 2031,
          "anio_termino": 2032
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 5600.0,
      "monto_total_millones": 5600.0,
      "anio_inicio": 2029,
      "anio_termino": 2032,
      "pagina_documento": 30,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-40064803-0",
      "codigo_bip": "40064803-0",
      "nombre": "CONSTRUCCIÓN VÍAS DE NAVEGACIÓN RÍO AYSÉN, COMUNA AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Prefactibilidad",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 250.0,
          "monto_total_millones": 250.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 600.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 35000.0,
          "monto_total_millones": 35000.0,
          "anio_inicio": 2031,
          "anio_termino": 2033
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 35850.0,
      "monto_total_millones": 35850.0,
      "anio_inicio": 2027,
      "anio_termino": 2033,
      "pagina_documento": 30,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-40064809-0",
      "codigo_bip": "40064809-0",
      "nombre": "AMPLIACIÓN CALETA DE PESCADORES PUERTO AGUIRRE, COMUNA AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 600.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 3500.0,
          "monto_total_millones": 3500.0,
          "anio_inicio": 2031,
          "anio_termino": 2033
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4100.0,
      "monto_total_millones": 4100.0,
      "anio_inicio": 2029,
      "anio_termino": 2033,
      "pagina_documento": 30,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-40064813-0",
      "codigo_bip": "40064813-0",
      "nombre": "CONSTRUCCIÓN INFRAESTRUCTURA PORTUARIA EN ESTERO COPA, PUERTO AGUIRRE",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Prefactibilidad",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 250.0,
          "monto_total_millones": 250.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        },
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 600.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2031,
          "anio_termino": 2032
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 3000.0,
          "monto_total_millones": 3000.0,
          "anio_inicio": 2033,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 3850.0,
      "monto_total_millones": 3850.0,
      "anio_inicio": 2029,
      "anio_termino": 2035,
      "pagina_documento": 30,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-30175124-0",
      "codigo_bip": "30175124-0",
      "nombre": "CONSTRUCCIÓN DE INFRAESTRUCTURA TURÍSTICA PARA ÁREAS SILVESTRES PROTEGIDAS PRIORITARIAS P.N. LAGUNA SAN RAFAEL",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "CONAF"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "CONAF",
          "monto_subdere_millones": 7795.266,
          "monto_gore_millones": 7795.267,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 15590.533,
          "anio_inicio": 2031,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 7795.266,
      "monto_gore_millones": 7795.267,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 15590.533,
      "anio_inicio": 2031,
      "anio_termino": 2035,
      "pagina_documento": 31,
      "institucion_principal": "CONAF"
    },
    {
      "id": "pdze-40071200-0",
      "codigo_bip": "40071200-0",
      "nombre": "AMPLIACIÓN FRENTE ATRAQUE SITIO 1 - MUELLE PUERTO CHACABUCO",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "EMPORCHA"
      ],
      "etapas": [
        {
          "etapa": "Prefactibilidad",
          "institucion": "EMPORCHA",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 1400.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 1400.0,
          "anio_inicio": 2026,
          "anio_termino": 2030
        },
        {
          "etapa": "Diseño",
          "institucion": "EMPORCHA",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1000.0,
          "monto_total_millones": 1000.0,
          "anio_inicio": 2031,
          "anio_termino": 2031
        },
        {
          "etapa": "Ejecución",
          "institucion": "EMPORCHA",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 32842.0,
          "monto_sectorial_millones": 2210.0,
          "monto_total_millones": 35052.0,
          "anio_inicio": 2032,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 34242.0,
      "monto_sectorial_millones": 3210.0,
      "monto_total_millones": 37452.0,
      "anio_inicio": 2026,
      "anio_termino": 2035,
      "pagina_documento": 31,
      "institucion_principal": "EMPORCHA"
    },
    {
      "id": "pdze-40046006-0",
      "codigo_bip": "40046006-0",
      "nombre": "CONSTRUCCIÓN PUENTE URBANO DE PUERTO AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MTT",
        "GORE"
      ],
      "etapas": [
        {
          "etapa": "Prefactibilidad",
          "institucion": "MTT",
          "monto_subdere_millones": 156.676,
          "monto_gore_millones": 100.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 256.676,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Diseño",
          "institucion": "GORE",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 2567.6,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 2567.6,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "GORE",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 31384.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 31384.0,
          "anio_inicio": 2030,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 156.676,
      "monto_gore_millones": 34051.6,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 34208.276,
      "anio_inicio": 2026,
      "anio_termino": 2035,
      "pagina_documento": 31,
      "institucion_principal": "MTT"
    },
    {
      "id": "pdze-30436139-0",
      "codigo_bip": "30436139-0",
      "nombre": "REPOSICIÓN ESCUELA DIFERENCIAL DESPERTAR, PUERTO AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "SLEP"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "SLEP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 10868.614,
          "monto_sectorial_millones": 1700.032,
          "monto_total_millones": 12568.646,
          "anio_inicio": 2026,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 10868.614,
      "monto_sectorial_millones": 1700.032,
      "monto_total_millones": 12568.646,
      "anio_inicio": 2026,
      "anio_termino": 2028,
      "pagina_documento": 31,
      "institucion_principal": "SLEP"
    },
    {
      "id": "pdze-40062989-0",
      "codigo_bip": "40062989-0",
      "nombre": "CONSTRUCCIÓN 20 VIVIENDAS TUTELADAS PARA ADULTO MAYOR, PUERTO AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Seremi de Vivienda y Urbanismo"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Seremi de Vivienda y Urbanismo",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1821.0,
          "monto_total_millones": 1821.0,
          "anio_inicio": 2026,
          "anio_termino": 2027
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 1821.0,
      "monto_total_millones": 1821.0,
      "anio_inicio": 2026,
      "anio_termino": 2027,
      "pagina_documento": 31,
      "institucion_principal": "Seremi de Vivienda y Urbanismo"
    },
    {
      "id": "pdze-40030988-0",
      "codigo_bip": "40030988-0",
      "nombre": "MEJORAMIENTO CALLE TENIENTE MERINO ORIENTE, PUERTO AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Seremi de Vivienda y Urbanismo"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Seremi de Vivienda y Urbanismo",
          "monto_subdere_millones": 1953.324,
          "monto_gore_millones": 1953.325,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 3906.649,
          "anio_inicio": 2027,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 1953.324,
      "monto_gore_millones": 1953.325,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 3906.649,
      "anio_inicio": 2027,
      "anio_termino": 2029,
      "pagina_documento": 31,
      "institucion_principal": "Seremi de Vivienda y Urbanismo"
    },
    {
      "id": "pdze-40072496-0",
      "codigo_bip": "40072496-0",
      "nombre": "CONSTRUCCIÓN Y EQUIPAMIENTO ELEAM SAN BERNARDO, AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Municipalidad de Puerto Aysén"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Puerto Aysén",
          "monto_subdere_millones": 300.0,
          "monto_gore_millones": 300.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2026,
          "anio_termino": 2027
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Puerto Aysén",
          "monto_subdere_millones": 2700.0,
          "monto_gore_millones": 2700.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 5400.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 3000.0,
      "monto_gore_millones": 3000.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 6000.0,
      "anio_inicio": 2026,
      "anio_termino": 2030,
      "pagina_documento": 31,
      "institucion_principal": "Municipalidad de Puerto Aysén"
    },
    {
      "id": "pdze-40066417-0",
      "codigo_bip": "40066417-0",
      "nombre": "CONSTRUCCIÓN COSTANERA CULTURAL RIBERA SUR, PUERTO AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Municipalidad de Puerto Aysén"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Puerto Aysén",
          "monto_subdere_millones": 1500.0,
          "monto_gore_millones": 1500.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 3000.0,
          "anio_inicio": 2026,
          "anio_termino": 2027
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Puerto Aysén",
          "monto_subdere_millones": 13500.0,
          "monto_gore_millones": 13500.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 27000.0,
          "anio_inicio": 2029,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 15000.0,
      "monto_gore_millones": 15000.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 30000.0,
      "anio_inicio": 2026,
      "anio_termino": 2031,
      "pagina_documento": 32,
      "institucion_principal": "Municipalidad de Puerto Aysén"
    },
    {
      "id": "pdze-40024845-0",
      "codigo_bip": "40024845-0",
      "nombre": "CONSTRUCCIÓN ESPACIO PÚBLICO RECREATIVO RIBERA SUR, PUERTO AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Municipalidad de Puerto Aysén"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Puerto Aysén",
          "monto_subdere_millones": 3850.0,
          "monto_gore_millones": 3850.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 7700.0,
          "anio_inicio": 2028,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 3850.0,
      "monto_gore_millones": 3850.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 7700.0,
      "anio_inicio": 2028,
      "anio_termino": 2029,
      "pagina_documento": 32,
      "institucion_principal": "Municipalidad de Puerto Aysén"
    },
    {
      "id": "pdze-40056464-0",
      "codigo_bip": "40056464-0",
      "nombre": "CONSERVACIÓN INFRAESTRUCTURA POLIDEPORTIVO 21 DE ABRIL, PUERTO AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Municipalidad de Puerto Aysén"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Puerto Aysén",
          "monto_subdere_millones": 1000.0,
          "monto_gore_millones": 6000.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 7000.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 1000.0,
      "monto_gore_millones": 6000.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 7000.0,
      "anio_inicio": 2027,
      "anio_termino": 2028,
      "pagina_documento": 32,
      "institucion_principal": "Municipalidad de Puerto Aysén"
    },
    {
      "id": "pdze-40072557-0",
      "codigo_bip": "40072557-0",
      "nombre": "MERCADO MUNICIPAL DE PUERTO AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Municipalidad de Puerto Aysén"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Puerto Aysén",
          "monto_subdere_millones": 300.0,
          "monto_gore_millones": 300.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2026,
          "anio_termino": 2027
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Puerto Aysén",
          "monto_subdere_millones": 2700.0,
          "monto_gore_millones": 2700.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 5400.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 3000.0,
      "monto_gore_millones": 3000.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 6000.0,
      "anio_inicio": 2026,
      "anio_termino": 2030,
      "pagina_documento": 32,
      "institucion_principal": "Municipalidad de Puerto Aysén"
    },
    {
      "id": "pdze-40025451-0",
      "codigo_bip": "40025451-0",
      "nombre": "CONSTRUCCIÓN TERMINAL DE BUSES DE PUERTO AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Municipalidad de Puerto Aysén"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Puerto Aysén",
          "monto_subdere_millones": 2340.321,
          "monto_gore_millones": 4140.321,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 6480.642,
          "anio_inicio": 2026,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 2340.321,
      "monto_gore_millones": 4140.321,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 6480.642,
      "anio_inicio": 2026,
      "anio_termino": 2028,
      "pagina_documento": 32,
      "institucion_principal": "Municipalidad de Puerto Aysén"
    },
    {
      "id": "pdze-40072131-0",
      "codigo_bip": "40072131-0",
      "nombre": "MEJORAMIENTO ESTADIO PUERTO AGUIRRE, COMUNA DE AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "GORE"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "GORE",
          "monto_subdere_millones": 1037.25,
          "monto_gore_millones": 1037.25,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 2074.5,
          "anio_inicio": 2026,
          "anio_termino": 2027
        }
      ],
      "monto_subdere_millones": 1037.25,
      "monto_gore_millones": 1037.25,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 2074.5,
      "anio_inicio": 2026,
      "anio_termino": 2027,
      "pagina_documento": 32,
      "institucion_principal": "GORE"
    },
    {
      "id": "pdze-30083917-0",
      "codigo_bip": "30083917-0",
      "nombre": "REPOSICIÓN RETÉN DE PUERTO AGUIRRE",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Carabineros"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 2742.538,
          "monto_total_millones": 2742.538,
          "anio_inicio": 2026,
          "anio_termino": 2027
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 2742.538,
      "monto_total_millones": 2742.538,
      "anio_inicio": 2026,
      "anio_termino": 2027,
      "pagina_documento": 32,
      "institucion_principal": "Carabineros"
    },
    {
      "id": "pdze-40035284-0",
      "codigo_bip": "40035284-0",
      "nombre": "RESTAURACIÓN MONUMENTO HISTÓRICO OFICINA DE TIERRAS Y COLONIZACIÓN DE PUERTO AYSÉN",
      "comuna": "Aysén",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Carabineros"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 300.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 300.0,
          "anio_inicio": 2031,
          "anio_termino": 2031
        },
        {
          "etapa": "Ejecución",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 8000.0,
          "monto_total_millones": 8000.0,
          "anio_inicio": 2033,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 300.0,
      "monto_sectorial_millones": 8000.0,
      "monto_total_millones": 8300.0,
      "anio_inicio": 2031,
      "anio_termino": 2035,
      "pagina_documento": 32,
      "institucion_principal": "Carabineros"
    },
    {
      "id": "pdze-40064883-0",
      "codigo_bip": "40064883-0",
      "nombre": "MEJORAMIENTO CAMINO X-100 MELINKA - REPOLLAL BAJO, COMUNA DE GUAITECAS",
      "comuna": "Guaitecas",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 14000.0,
          "monto_total_millones": 14000.0,
          "anio_inicio": 2027,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 14000.0,
      "monto_total_millones": 14000.0,
      "anio_inicio": 2027,
      "anio_termino": 2029,
      "pagina_documento": 34,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-30369677-0",
      "codigo_bip": "30369677-0",
      "nombre": "CONSTRUCCIÓN BORDE COSTERO MELINKA",
      "comuna": "Guaitecas",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Prefactibilidad",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 250.0,
          "monto_total_millones": 250.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        },
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 600.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2031,
          "anio_termino": 2032
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 4000.0,
          "monto_total_millones": 4000.0,
          "anio_inicio": 2033,
          "anio_termino": 2034
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4850.0,
      "monto_total_millones": 4850.0,
      "anio_inicio": 2029,
      "anio_termino": 2034,
      "pagina_documento": 34,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-30400114-0",
      "codigo_bip": "30400114-0",
      "nombre": "REPOSICIÓN COMPLEJO EDUCACIONAL MELINKA",
      "comuna": "Guaitecas",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "SLEP"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "SLEP",
          "monto_subdere_millones": 11661.51,
          "monto_gore_millones": 11661.51,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 23323.02,
          "anio_inicio": 2028,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 11661.51,
      "monto_gore_millones": 11661.51,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 23323.02,
      "anio_inicio": 2028,
      "anio_termino": 2030,
      "pagina_documento": 34,
      "institucion_principal": "SLEP"
    },
    {
      "id": "pdze-40064586-0",
      "codigo_bip": "40064586-0",
      "nombre": "CONSTRUCCIÓN PARQUE URBANO CERRO MIRADOR, MELINKA",
      "comuna": "Guaitecas",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Seremi de Vivienda y Urbanismo"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Seremi de Vivienda y Urbanismo",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 1700.0,
          "monto_sectorial_millones": 2100.0,
          "monto_total_millones": 3800.0,
          "anio_inicio": 2030,
          "anio_termino": 2032
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 1700.0,
      "monto_sectorial_millones": 2100.0,
      "monto_total_millones": 3800.0,
      "anio_inicio": 2030,
      "anio_termino": 2032,
      "pagina_documento": 34,
      "institucion_principal": "Seremi de Vivienda y Urbanismo"
    },
    {
      "id": "pdze-40009560-0",
      "codigo_bip": "40009560-0",
      "nombre": "CONSTRUCCIÓN CENTRO DE SALUD GUAITECAS",
      "comuna": "Guaitecas",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Servicio de Salud Aysén"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Servicio de Salud Aysén",
          "monto_subdere_millones": 125.0,
          "monto_gore_millones": 125.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 250.0,
          "anio_inicio": 2029,
          "anio_termino": 2029
        },
        {
          "etapa": "Ejecución",
          "institucion": "Servicio de Salud Aysén",
          "monto_subdere_millones": 5600.0,
          "monto_gore_millones": 5600.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 11200.0,
          "anio_inicio": 2031,
          "anio_termino": 2033
        }
      ],
      "monto_subdere_millones": 5725.0,
      "monto_gore_millones": 5725.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 11450.0,
      "anio_inicio": 2029,
      "anio_termino": 2033,
      "pagina_documento": 34,
      "institucion_principal": "Servicio de Salud Aysén"
    },
    {
      "id": "pdze-40064949-0",
      "codigo_bip": "40064949-0",
      "nombre": "REPOSICIÓN SISTEMA DE GENERACIÓN ELÉCTRICA, MELINKA Y REPOLLAL",
      "comuna": "Guaitecas",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Municipalidad de Guaitecas"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Guaitecas",
          "monto_subdere_millones": 675.0,
          "monto_gore_millones": 895.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 1570.0,
          "anio_inicio": 2028,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 675.0,
      "monto_gore_millones": 895.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 1570.0,
      "anio_inicio": 2028,
      "anio_termino": 2029,
      "pagina_documento": 34,
      "institucion_principal": "Municipalidad de Guaitecas"
    },
    {
      "id": "pdze-40064985-0",
      "codigo_bip": "40064985-0",
      "nombre": "CONSTRUCCIÓN MERCADO MUNICIPAL MELINKA, COMUNA DE GUAITECAS",
      "comuna": "Guaitecas",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Municipalidad de Guaitecas"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Guaitecas",
          "monto_subdere_millones": 125.0,
          "monto_gore_millones": 125.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 250.0,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Guaitecas",
          "monto_subdere_millones": 775.0,
          "monto_gore_millones": 775.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 1550.0,
          "anio_inicio": 2028,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 900.0,
      "monto_gore_millones": 900.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 1800.0,
      "anio_inicio": 2026,
      "anio_termino": 2028,
      "pagina_documento": 34,
      "institucion_principal": "Municipalidad de Guaitecas"
    },
    {
      "id": "pdze-40072989-0",
      "codigo_bip": "40072989-0",
      "nombre": "CONSTRUCCIÓN PLANTA DE GENERACIÓN ELÉCTRICA FOTOVOLTAICA MELINKA-REPOLLAL",
      "comuna": "Guaitecas",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "GORE"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "GORE",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 240.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 240.0,
          "anio_inicio": 2029,
          "anio_termino": 2029
        },
        {
          "etapa": "Ejecución",
          "institucion": "GORE",
          "monto_subdere_millones": 1857.792,
          "monto_gore_millones": 1857.792,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 3715.584,
          "anio_inicio": 2031,
          "anio_termino": 2032
        }
      ],
      "monto_subdere_millones": 1857.792,
      "monto_gore_millones": 2097.792,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 3955.584,
      "anio_inicio": 2029,
      "anio_termino": 2032,
      "pagina_documento": 34,
      "institucion_principal": "GORE"
    },
    {
      "id": "pdze-40072117-0",
      "codigo_bip": "40072117-0",
      "nombre": "MEJORAMIENTO ESTADIO MUNICIPAL LA CHUCHOCA, MELINKA, COMUNA DE GUAITECAS",
      "comuna": "Guaitecas",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "GORE"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "GORE",
          "monto_subdere_millones": 857.75,
          "monto_gore_millones": 857.75,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 1715.5,
          "anio_inicio": 2026,
          "anio_termino": 2027
        }
      ],
      "monto_subdere_millones": 857.75,
      "monto_gore_millones": 857.75,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 1715.5,
      "anio_inicio": 2026,
      "anio_termino": 2027,
      "pagina_documento": 34,
      "institucion_principal": "GORE"
    },
    {
      "id": "pdze-40074637-0",
      "codigo_bip": "40074637-0",
      "nombre": "REPOSICIÓN RETÉN DE MELINKA",
      "comuna": "Guaitecas",
      "provincia": "Provincia de Aysén",
      "instituciones": [
        "Carabineros"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 160.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 160.0,
          "anio_inicio": 2027,
          "anio_termino": 2027
        },
        {
          "etapa": "Ejecución",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 3800.0,
          "monto_total_millones": 3800.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 160.0,
      "monto_sectorial_millones": 3800.0,
      "monto_total_millones": 3960.0,
      "anio_inicio": 2027,
      "anio_termino": 2030,
      "pagina_documento": 34,
      "institucion_principal": "Carabineros"
    },
    {
      "id": "pdze-40059879-0",
      "codigo_bip": "40059879-0",
      "nombre": "MEJORAMIENTO RUTA 7 SECTOR COYHAIQUE - VALLE SIMPSON, COMUNA COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 717.826,
          "monto_total_millones": 717.826,
          "anio_inicio": 2026,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 22500.0,
          "monto_total_millones": 22500.0,
          "anio_inicio": 2029,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 23217.826,
      "monto_total_millones": 23217.826,
      "anio_inicio": 2026,
      "anio_termino": 2031,
      "pagina_documento": 37,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064088-0",
      "codigo_bip": "40064088-0",
      "nombre": "MEJORAMIENTO RUTA 7, RUTA 240. SECTOR COYHAIQUE - LOS TORREONES, COMUNA COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1500.0,
          "monto_total_millones": 1500.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 45000.0,
          "monto_total_millones": 45000.0,
          "anio_inicio": 2030,
          "anio_termino": 2032
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 46500.0,
      "monto_total_millones": 46500.0,
      "anio_inicio": 2027,
      "anio_termino": 2032,
      "pagina_documento": 37,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064891-0",
      "codigo_bip": "40064891-0",
      "nombre": "REPOSICIÓN PUENTES RUTA 240, COMUNAS COYHAIQUE Y AYSÉN",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 4500.0,
          "monto_total_millones": 4500.0,
          "anio_inicio": 2032,
          "anio_termino": 2034
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4500.0,
      "monto_total_millones": 4500.0,
      "anio_inicio": 2032,
      "anio_termino": 2034,
      "pagina_documento": 37,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064877-0",
      "codigo_bip": "40064877-0",
      "nombre": "MEJORAMIENTO RUTA 243-CH SECTOR DOS LAGUNAS - PASO FRONTERIZO COYHAIQUE ALTO, COMUNA COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 15000.0,
          "monto_total_millones": 15000.0,
          "anio_inicio": 2035,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 15000.0,
      "monto_total_millones": 15000.0,
      "anio_inicio": 2035,
      "anio_termino": 2035,
      "pagina_documento": 37,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40059881-0",
      "codigo_bip": "40059881-0",
      "nombre": "MEJORAMIENTO RUTA 243-CH SECTOR LAS BANDURRIAS (FIN PAV) - DOS LAGUNAS, COMUNA DE COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 44824.761,
          "monto_total_millones": 44824.761,
          "anio_inicio": 2026,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 44824.761,
      "monto_total_millones": 44824.761,
      "anio_inicio": 2026,
      "anio_termino": 2029,
      "pagina_documento": 37,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40059886-0",
      "codigo_bip": "40059886-0",
      "nombre": "CONSTRUCCIÓN NUEVO PUENTE ANTOLÍN SILVA Y ACCESOS EN SECTOR BALMACEDA, COMUNA COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Prefactibilidad",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1041.871,
          "monto_total_millones": 1041.871,
          "anio_inicio": 2026,
          "anio_termino": 2027
        },
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1000.0,
          "monto_total_millones": 1000.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 8400.0,
          "monto_total_millones": 8400.0,
          "anio_inicio": 2032,
          "anio_termino": 2034
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 10441.871,
      "monto_total_millones": 10441.871,
      "anio_inicio": 2026,
      "anio_termino": 2034,
      "pagina_documento": 37,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-30255323-0",
      "codigo_bip": "30255323-0",
      "nombre": "REPOSICIÓN PUENTE PINUER EN CAMINO X-614, COMUNA DE COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 106.598,
          "monto_total_millones": 106.598,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 5064.0,
          "monto_total_millones": 5064.0,
          "anio_inicio": 2027,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 5170.598,
      "monto_total_millones": 5170.598,
      "anio_inicio": 2026,
      "anio_termino": 2030,
      "pagina_documento": 37,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064885-0",
      "codigo_bip": "40064885-0",
      "nombre": "MEJORAMIENTO CAMINOS VARIOS COYHAIQUE SEGUNDA ETAPA, COMUNA COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 750.0,
          "monto_total_millones": 750.0,
          "anio_inicio": 2028,
          "anio_termino": 2029
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 30000.0,
          "monto_total_millones": 30000.0,
          "anio_inicio": 2031,
          "anio_termino": 2033
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 30750.0,
      "monto_total_millones": 30750.0,
      "anio_inicio": 2028,
      "anio_termino": 2033,
      "pagina_documento": 38,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-30403479-0",
      "codigo_bip": "30403479-0",
      "nombre": "MEJORAMIENTO RUTA X-608, CRUCE TTE. VIDAL-LAGO ATRAVESADO, COMUNA DE COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 18988.555,
          "monto_total_millones": 18988.555,
          "anio_inicio": 2026,
          "anio_termino": 2027
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 18988.555,
      "monto_total_millones": 18988.555,
      "anio_inicio": 2026,
      "anio_termino": 2027,
      "pagina_documento": 38,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40069901-0",
      "codigo_bip": "40069901-0",
      "nombre": "SISTEMA DE AYUDAS VISUALES PARA RED PEQUEÑOS AERÓDROMOS",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DAP"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DAP",
          "monto_subdere_millones": 1400.0,
          "monto_gore_millones": 1400.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 2800.0,
          "anio_inicio": 2027,
          "anio_termino": 2027
        }
      ],
      "monto_subdere_millones": 1400.0,
      "monto_gore_millones": 1400.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 2800.0,
      "anio_inicio": 2027,
      "anio_termino": 2027,
      "pagina_documento": 38,
      "institucion_principal": "MOP-DAP"
    },
    {
      "id": "pdze-40722239-0",
      "codigo_bip": "40722239-0",
      "nombre": "CONSTRUCCIÓN DEFENSAS FLUVIALES ESTERO CUATRO VIENTOS",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DOH"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOH",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 400.0,
          "monto_total_millones": 400.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOH",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 3000.0,
          "monto_total_millones": 3000.0,
          "anio_inicio": 2028,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 3400.0,
      "monto_total_millones": 3400.0,
      "anio_inicio": 2027,
      "anio_termino": 2030,
      "pagina_documento": 38,
      "institucion_principal": "MOP-DOH"
    },
    {
      "id": "pdze-40072292-0",
      "codigo_bip": "40072292-0",
      "nombre": "ACTUALIZACIÓN DEL PLAN MAESTRO DE EVACUACIÓN Y DRENAJE DE AGUAS LLUVIAS DE COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DOH"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOH",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 800.0,
          "monto_total_millones": 800.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 800.0,
      "monto_total_millones": 800.0,
      "anio_inicio": 2027,
      "anio_termino": 2028,
      "pagina_documento": 38,
      "institucion_principal": "MOP-DOH"
    },
    {
      "id": "pdze-40072301-0",
      "codigo_bip": "40072301-0",
      "nombre": "CONSTRUCCIÓN DEFENSAS FLUVIALES RÍO SIMPSON SECTOR ENSENADA DEL VALLE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DOH"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOH",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 4000.0,
          "monto_total_millones": 4000.0,
          "anio_inicio": 2027,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4000.0,
      "monto_total_millones": 4000.0,
      "anio_inicio": 2027,
      "anio_termino": 2029,
      "pagina_documento": 38,
      "institucion_principal": "MOP-DOH"
    },
    {
      "id": "pdze-40020229-0",
      "codigo_bip": "40020229-0",
      "nombre": "CONSTRUCCIÓN COLECTORES DE AGUAS LLUVIAS DE COYHAIQUE SECTOR ALTO",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DOH"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOH",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 6000.0,
          "monto_total_millones": 6000.0,
          "anio_inicio": 2027,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 6000.0,
      "monto_total_millones": 6000.0,
      "anio_inicio": 2027,
      "anio_termino": 2030,
      "pagina_documento": 38,
      "institucion_principal": "MOP-DOH"
    },
    {
      "id": "pdze-30064914-0",
      "codigo_bip": "30064914-0",
      "nombre": "MEJORAMIENTO BORDE COSTERO EN LAGO ELIZALDE COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 6052.0,
          "monto_total_millones": 6052.0,
          "anio_inicio": 2027,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 6052.0,
      "monto_total_millones": 6052.0,
      "anio_inicio": 2027,
      "anio_termino": 2029,
      "pagina_documento": 38,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-30132150-0",
      "codigo_bip": "30132150-0",
      "nombre": "HABILITACIÓN INFRAESTRUCTURA PARA EL DESARROLLO TURÍSTICO SUSTENTABLE PARQUE NACIONAL CERRO CASTILLO",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "CONAF"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "CONAF",
          "monto_subdere_millones": 175.0,
          "monto_gore_millones": 175.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 350.0,
          "anio_inicio": 2031,
          "anio_termino": 2031
        },
        {
          "etapa": "Ejecución",
          "institucion": "CONAF",
          "monto_subdere_millones": 2500.0,
          "monto_gore_millones": 2500.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 5000.0,
          "anio_inicio": 2032,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 2675.0,
      "monto_gore_millones": 2675.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 5350.0,
      "anio_inicio": 2031,
      "anio_termino": 2035,
      "pagina_documento": 38,
      "institucion_principal": "CONAF"
    },
    {
      "id": "pdze-40069949-0",
      "codigo_bip": "40069949-0",
      "nombre": "CONSTRUCCIÓN ESTABLECIMIENTO PENITENCIARIO COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "Gendarmería de Chile"
      ],
      "etapas": [
        {
          "etapa": "Prefactibilidad",
          "institucion": "Gendarmería de Chile",
          "monto_subdere_millones": 350.0,
          "monto_gore_millones": 350.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 700.0,
          "anio_inicio": 2026,
          "anio_termino": 2027
        },
        {
          "etapa": "Ejecución",
          "institucion": "Gendarmería de Chile",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 16158.0,
          "monto_sectorial_millones": 37702.0,
          "monto_total_millones": 53860.0,
          "anio_inicio": 2029,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 350.0,
      "monto_gore_millones": 16508.0,
      "monto_sectorial_millones": 37702.0,
      "monto_total_millones": 54560.0,
      "anio_inicio": 2026,
      "anio_termino": 2035,
      "pagina_documento": 39,
      "institucion_principal": "Gendarmería de Chile"
    },
    {
      "id": "pdze-40038912-0",
      "codigo_bip": "40038912-0",
      "nombre": "REPOSICIÓN CENTRO DEPORTIVO POLIFUNCIONAL IND, COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "IND"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "IND",
          "monto_subdere_millones": 9326.267,
          "monto_gore_millones": 9326.268,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 18652.535,
          "anio_inicio": 2026,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 9326.267,
      "monto_gore_millones": 9326.268,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 18652.535,
      "anio_inicio": 2026,
      "anio_termino": 2028,
      "pagina_documento": 39,
      "institucion_principal": "IND"
    },
    {
      "id": "pdze-40024745-0",
      "codigo_bip": "40024745-0",
      "nombre": "CONSTRUCCIÓN PISCINA CENTRO DEPORTIVO COMUNITARIO, COMUNA DE COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "IND"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "IND",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 12000.0,
          "monto_total_millones": 12000.0,
          "anio_inicio": 2026,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 12000.0,
      "monto_total_millones": 12000.0,
      "anio_inicio": 2026,
      "anio_termino": 2028,
      "pagina_documento": 39,
      "institucion_principal": "IND"
    },
    {
      "id": "pdze-40072488-0",
      "codigo_bip": "40072488-0",
      "nombre": "REPOSICIÓN CON RELOCALIZACIÓN Y MEJORAMIENTO DEL LABORATORIO SUELO SILVOAGROPECUARIO REGIONAL",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "Seremi Agricultura"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Seremi Agricultura",
          "monto_subdere_millones": 500.0,
          "monto_gore_millones": 500.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 1000.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 500.0,
      "monto_gore_millones": 500.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 1000.0,
      "anio_inicio": 2027,
      "anio_termino": 2028,
      "pagina_documento": 39,
      "institucion_principal": "Seremi Agricultura"
    },
    {
      "id": "pdze-40070373-0",
      "codigo_bip": "40070373-0",
      "nombre": "DISEÑO CONSTRUCCIÓN TERRAZA DIVISADERO, COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "SERNATUR"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "SERNATUR",
          "monto_subdere_millones": 120.0,
          "monto_gore_millones": 120.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 240.0,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "SERNATUR",
          "monto_subdere_millones": 1200.0,
          "monto_gore_millones": 1200.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 2400.0,
          "anio_inicio": 2028,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 1320.0,
      "monto_gore_millones": 1320.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 2640.0,
      "anio_inicio": 2026,
      "anio_termino": 2029,
      "pagina_documento": 39,
      "institucion_principal": "SERNATUR"
    },
    {
      "id": "pdze-30437131-0",
      "codigo_bip": "30437131-0",
      "nombre": "REPOSICIÓN ESCUELA DIFERENCIAL ESPAÑA, COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "SLEP"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "SLEP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 10432.737,
          "monto_sectorial_millones": 11309.193,
          "monto_total_millones": 21741.93,
          "anio_inicio": 2026,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 10432.737,
      "monto_sectorial_millones": 11309.193,
      "monto_total_millones": 21741.93,
      "anio_inicio": 2026,
      "anio_termino": 2029,
      "pagina_documento": 39,
      "institucion_principal": "SLEP"
    },
    {
      "id": "pdze-30474635-0",
      "codigo_bip": "30474635-0",
      "nombre": "CONSTRUCCIÓN INFRAESTRUCTURA FUNDACIONAL UNIVERSIDAD AYSÉN",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "Universidad de Aysén"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Universidad de Aysén",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 29836.759,
          "monto_sectorial_millones": 6000.0,
          "monto_total_millones": 35836.759,
          "anio_inicio": 2026,
          "anio_termino": 2027
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 29836.759,
      "monto_sectorial_millones": 6000.0,
      "monto_total_millones": 35836.759,
      "anio_inicio": 2026,
      "anio_termino": 2027,
      "pagina_documento": 39,
      "institucion_principal": "Universidad de Aysén"
    },
    {
      "id": "pdze-30462104-0",
      "codigo_bip": "30462104-0",
      "nombre": "REPOSICIÓN CALZADAS Y ACERAS SECTOR PLAZA DE ARMAS, COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "Seremi de Vivienda y Urbanismo"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Seremi de Vivienda y Urbanismo",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 1740.0,
          "monto_sectorial_millones": 4060.0,
          "monto_total_millones": 5800.0,
          "anio_inicio": 2027,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 1740.0,
      "monto_sectorial_millones": 4060.0,
      "monto_total_millones": 5800.0,
      "anio_inicio": 2027,
      "anio_termino": 2029,
      "pagina_documento": 39,
      "institucion_principal": "Seremi de Vivienda y Urbanismo"
    },
    {
      "id": "pdze-40064913-0",
      "codigo_bip": "40064913-0",
      "nombre": "CONSTRUCCIÓN CICLOVÍAS COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "Seremi de Vivienda y Urbanismo"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Seremi de Vivienda y Urbanismo",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 4000.0,
          "monto_sectorial_millones": 4000.0,
          "monto_total_millones": 8000.0,
          "anio_inicio": 2033,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 4000.0,
      "monto_sectorial_millones": 4000.0,
      "monto_total_millones": 8000.0,
      "anio_inicio": 2033,
      "anio_termino": 2035,
      "pagina_documento": 39,
      "institucion_principal": "Seremi de Vivienda y Urbanismo"
    },
    {
      "id": "pdze-40068919-0",
      "codigo_bip": "40068919-0",
      "nombre": "CONSTRUCCIÓN CENTRO DE SALUD BALMACEDA",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "Servicio de Salud Aysén"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Servicio de Salud Aysén",
          "monto_subdere_millones": 125.0,
          "monto_gore_millones": 125.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 250.0,
          "anio_inicio": 2029,
          "anio_termino": 2029
        },
        {
          "etapa": "Ejecución",
          "institucion": "Servicio de Salud Aysén",
          "monto_subdere_millones": 5000.0,
          "monto_gore_millones": 5000.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 10000.0,
          "anio_inicio": 2031,
          "anio_termino": 2032
        }
      ],
      "monto_subdere_millones": 5125.0,
      "monto_gore_millones": 5125.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 10250.0,
      "anio_inicio": 2029,
      "anio_termino": 2032,
      "pagina_documento": 39,
      "institucion_principal": "Servicio de Salud Aysén"
    },
    {
      "id": "pdze-30405923-0",
      "codigo_bip": "30405923-0",
      "nombre": "NORMALIZACIÓN HOSPITAL REGIONAL COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "Servicio de Salud Aysén"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Servicio de Salud Aysén",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 2000.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 2000.0,
          "anio_inicio": 2026,
          "anio_termino": 2027
        },
        {
          "etapa": "Ejecución",
          "institucion": "Servicio de Salud Aysén",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 192000.0,
          "monto_total_millones": 192000.0,
          "anio_inicio": 2029,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 2000.0,
      "monto_sectorial_millones": 192000.0,
      "monto_total_millones": 194000.0,
      "anio_inicio": 2026,
      "anio_termino": 2035,
      "pagina_documento": 39,
      "institucion_principal": "Servicio de Salud Aysén"
    },
    {
      "id": "pdze-40071746-0",
      "codigo_bip": "40071746-0",
      "nombre": "CONSTRUCCIÓN ESTADIO CENTENARIO, COMUNA DE COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "Municipalidad de Coyhaique"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Coyhaique",
          "monto_subdere_millones": 1250.0,
          "monto_gore_millones": 1250.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 2500.0,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Coyhaique",
          "monto_subdere_millones": 12500.0,
          "monto_gore_millones": 12500.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 25000.0,
          "anio_inicio": 2028,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 13750.0,
      "monto_gore_millones": 13750.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 27500.0,
      "anio_inicio": 2026,
      "anio_termino": 2030,
      "pagina_documento": 40,
      "institucion_principal": "Municipalidad de Coyhaique"
    },
    {
      "id": "pdze-40071761-0",
      "codigo_bip": "40071761-0",
      "nombre": "CONSTRUCCIÓN ANFITEATRO MATE ACÚSTICO, COMUNA DE COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "Municipalidad de Coyhaique"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Coyhaique",
          "monto_subdere_millones": 150.0,
          "monto_gore_millones": 150.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 300.0,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Coyhaique",
          "monto_subdere_millones": 2350.0,
          "monto_gore_millones": 2350.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 4700.0,
          "anio_inicio": 2028,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 2500.0,
      "monto_gore_millones": 2500.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 5000.0,
      "anio_inicio": 2026,
      "anio_termino": 2029,
      "pagina_documento": 40,
      "institucion_principal": "Municipalidad de Coyhaique"
    },
    {
      "id": "pdze-40071762-0",
      "codigo_bip": "40071762-0",
      "nombre": "CONSTRUCCIÓN POLIDEPORTIVO, COMUNA DE COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "Municipalidad de Coyhaique"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Coyhaique",
          "monto_subdere_millones": 150.0,
          "monto_gore_millones": 150.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 300.0,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Coyhaique",
          "monto_subdere_millones": 5000.0,
          "monto_gore_millones": 5000.0,
          "monto_sectorial_millones": 10000.0,
          "monto_total_millones": 20000.0,
          "anio_inicio": 2028,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 5150.0,
      "monto_gore_millones": 5150.0,
      "monto_sectorial_millones": 10000.0,
      "monto_total_millones": 20300.0,
      "anio_inicio": 2026,
      "anio_termino": 2030,
      "pagina_documento": 40,
      "institucion_principal": "Municipalidad de Coyhaique"
    },
    {
      "id": "pdze-40072132-0",
      "codigo_bip": "40072132-0",
      "nombre": "MEJORAMIENTO ESTADIO VILLA FREI, COMUNA DE COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "GORE"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "GORE",
          "monto_subdere_millones": 943.75,
          "monto_gore_millones": 943.75,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 1887.5,
          "anio_inicio": 2026,
          "anio_termino": 2027
        }
      ],
      "monto_subdere_millones": 943.75,
      "monto_gore_millones": 943.75,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 1887.5,
      "anio_inicio": 2026,
      "anio_termino": 2027,
      "pagina_documento": 40,
      "institucion_principal": "GORE"
    },
    {
      "id": "pdze-40072858-0",
      "codigo_bip": "40072858-0",
      "nombre": "CONSTRUCCIÓN MERCADO SECTOR LOS MAÑÍOS-COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "GORE"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "GORE",
          "monto_subdere_millones": 1000.0,
          "monto_gore_millones": 3200.5,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 4200.5,
          "anio_inicio": 2029,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 1000.0,
      "monto_gore_millones": 3200.5,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 4200.5,
      "anio_inicio": 2029,
      "anio_termino": 2030,
      "pagina_documento": 40,
      "institucion_principal": "GORE"
    },
    {
      "id": "pdze-40072878-0",
      "codigo_bip": "40072878-0",
      "nombre": "CONSTRUCCIÓN PARQUE Y CENTRO DE CONVENCIONES, COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "GORE"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "GORE",
          "monto_subdere_millones": 1000.0,
          "monto_gore_millones": 4400.5,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 5400.5,
          "anio_inicio": 2030,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 1000.0,
      "monto_gore_millones": 4400.5,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 5400.5,
      "anio_inicio": 2030,
      "anio_termino": 2031,
      "pagina_documento": 40,
      "institucion_principal": "GORE"
    },
    {
      "id": "pdze-40074643-0",
      "codigo_bip": "40074643-0",
      "nombre": "REPOSICIÓN 1ERA COMISARÍA COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "Carabineros"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 300.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 300.0,
          "anio_inicio": 2028,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 8000.0,
          "monto_total_millones": 8000.0,
          "anio_inicio": 2030,
          "anio_termino": 2032
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 300.0,
      "monto_sectorial_millones": 8000.0,
      "monto_total_millones": 8300.0,
      "anio_inicio": 2028,
      "anio_termino": 2032,
      "pagina_documento": 40,
      "institucion_principal": "Carabineros"
    },
    {
      "id": "pdze-40000783-0",
      "codigo_bip": "40000783-0",
      "nombre": "CONSTRUCCIÓN CONEXIÓN PASARELA MIRADOR RÍO SIMPSON CON CALLE FREIRE, COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MINVU"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MINVU",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 2167.373,
          "monto_total_millones": 2167.373,
          "anio_inicio": 2029,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 2167.373,
      "monto_total_millones": 2167.373,
      "anio_inicio": 2029,
      "anio_termino": 2030,
      "pagina_documento": 40,
      "institucion_principal": "MINVU"
    },
    {
      "id": "pdze-30394083-0",
      "codigo_bip": "30394083-0",
      "nombre": "CONSTRUCCIÓN CIRCUNVALACIÓN ORIENTE PONIENTE, COYHAIQUE",
      "comuna": "Coyhaique",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MINVU"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MINVU",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 5174.978,
          "monto_total_millones": 5174.978,
          "anio_inicio": 2026,
          "anio_termino": 2027
        },
        {
          "etapa": "Ejecución",
          "institucion": "MINVU",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 41399.82,
          "monto_total_millones": 41399.82,
          "anio_inicio": 2029,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 46574.798,
      "monto_total_millones": 46574.798,
      "anio_inicio": 2026,
      "anio_termino": 2035,
      "pagina_documento": 40,
      "institucion_principal": "MINVU"
    },
    {
      "id": "pdze-30098551-0",
      "codigo_bip": "30098551-0",
      "nombre": "MEJORAMIENTO CAMINO X-13 LA JUNTA, COMUNA LAGO VERDE",
      "comuna": "Lago Verde",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 840.0,
          "monto_total_millones": 840.0,
          "anio_inicio": 2030,
          "anio_termino": 2032
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 180.0,
          "monto_total_millones": 180.0,
          "anio_inicio": 2034,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 1020.0,
      "monto_total_millones": 1020.0,
      "anio_inicio": 2030,
      "anio_termino": 2035,
      "pagina_documento": 42,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064105-0",
      "codigo_bip": "40064105-0",
      "nombre": "REPOSICIÓN PASARELA FIGUEROA EN CAMINO X-103, COMUNA LAGO VERDE",
      "comuna": "Lago Verde",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 700.0,
          "monto_total_millones": 700.0,
          "anio_inicio": 2030,
          "anio_termino": 2031
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 3000.0,
          "monto_total_millones": 3000.0,
          "anio_inicio": 2033,
          "anio_termino": 2034
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 3700.0,
      "monto_total_millones": 3700.0,
      "anio_inicio": 2030,
      "anio_termino": 2034,
      "pagina_documento": 42,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-30093406-0",
      "codigo_bip": "30093406-0",
      "nombre": "CONSTRUCCIÓN CONEXIÓN VIAL LAGO VERDE - LA TAPERA, COMUNA LAGO VERDE",
      "comuna": "Lago Verde",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 25239.592,
          "monto_total_millones": 25239.592,
          "anio_inicio": 2026,
          "anio_termino": 2034
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 25239.592,
      "monto_total_millones": 25239.592,
      "anio_inicio": 2026,
      "anio_termino": 2034,
      "pagina_documento": 42,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40048172-0",
      "codigo_bip": "40048172-0",
      "nombre": "CONSTRUCCIÓN INFRAESTRUCTURA PORTUARIA EN LAGO VERDE",
      "comuna": "Lago Verde",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 600.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 3500.0,
          "monto_total_millones": 3500.0,
          "anio_inicio": 2031,
          "anio_termino": 2032
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4100.0,
      "monto_total_millones": 4100.0,
      "anio_inicio": 2029,
      "anio_termino": 2032,
      "pagina_documento": 42,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-40006757-0",
      "codigo_bip": "40006757-0",
      "nombre": "CONSTRUCCIÓN RED DE ALCANTARILLADO Y PLANTA DE TRATAMIENTO DE AGUAS SERVIDAS LAGO VERDE",
      "comuna": "Lago Verde",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "Municipalidad de Lago Verde"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Lago Verde",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 200.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 200.0,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Lago Verde",
          "monto_subdere_millones": 2764.895,
          "monto_gore_millones": 2764.895,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 5529.79,
          "anio_inicio": 2028,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 2764.895,
      "monto_gore_millones": 2964.895,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 5729.79,
      "anio_inicio": 2026,
      "anio_termino": 2030,
      "pagina_documento": 42,
      "institucion_principal": "Municipalidad de Lago Verde"
    },
    {
      "id": "pdze-40001550-0",
      "codigo_bip": "40001550-0",
      "nombre": "CONSTRUCCIÓN REDES DE ALCANTARILLADO Y PLANTA DE TRATAMIENTO DE AGUAS SERVIDAS VILLA AMENGUAL",
      "comuna": "Lago Verde",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "Municipalidad de Lago Verde"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Lago Verde",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 200.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 200.0,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Lago Verde",
          "monto_subdere_millones": 1309.338,
          "monto_gore_millones": 1309.338,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 2618.676,
          "anio_inicio": 2028,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 1309.338,
      "monto_gore_millones": 1509.338,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 2818.676,
      "anio_inicio": 2026,
      "anio_termino": 2030,
      "pagina_documento": 42,
      "institucion_principal": "Municipalidad de Lago Verde"
    },
    {
      "id": "pdze-40072126-0",
      "codigo_bip": "40072126-0",
      "nombre": "MEJORAMIENTO ESTADIO VILLA LA TAPERA, COMUNA DE LAGO VERDE",
      "comuna": "Lago Verde",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "GORE"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "GORE",
          "monto_subdere_millones": 855.25,
          "monto_gore_millones": 855.25,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 1710.5,
          "anio_inicio": 2026,
          "anio_termino": 2027
        }
      ],
      "monto_subdere_millones": 855.25,
      "monto_gore_millones": 855.25,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 1710.5,
      "anio_inicio": 2026,
      "anio_termino": 2027,
      "pagina_documento": 42,
      "institucion_principal": "GORE"
    },
    {
      "id": "pdze-40011126-0",
      "codigo_bip": "40011126-0",
      "nombre": "REPOSICIÓN RETÉN RÍO CISNES",
      "comuna": "Lago Verde",
      "provincia": "Provincia de Coyhaique",
      "instituciones": [
        "Carabineros"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 170.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 170.0,
          "anio_inicio": 2028,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 4000.0,
          "monto_total_millones": 4000.0,
          "anio_inicio": 2031,
          "anio_termino": 2032
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 170.0,
      "monto_sectorial_millones": 4000.0,
      "monto_total_millones": 4170.0,
      "anio_inicio": 2028,
      "anio_termino": 2032,
      "pagina_documento": 42,
      "institucion_principal": "Carabineros"
    },
    {
      "id": "pdze-40064947-0",
      "codigo_bip": "40064947-0",
      "nombre": "MEJORAMIENTO RUTA 7 SUR. ACCESO CAPILLA DE MÁRMOL - PTE. LEONES, COMUNA DE CHILE CHICO",
      "comuna": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 800.0,
          "monto_total_millones": 800.0,
          "anio_inicio": 2034,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 800.0,
      "monto_total_millones": 800.0,
      "anio_inicio": 2034,
      "anio_termino": 2035,
      "pagina_documento": 45,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064948-0",
      "codigo_bip": "40064948-0",
      "nombre": "MEJORAMIENTO RUTA 7 SUR. SECTOR PUENTE LEONES - CRUCE MAITÉN, COMUNA DE CHILE CHICO",
      "comuna": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 600.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2035,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 600.0,
      "monto_total_millones": 600.0,
      "anio_inicio": 2035,
      "anio_termino": 2035,
      "pagina_documento": 45,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40048030-0",
      "codigo_bip": "40048030-0",
      "nombre": "CONSTRUCCIÓN PUENTE DESAGÜE LAGO GENERAL CARRERA, COMUNA DE CHILE CHICO",
      "comuna": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 45000.0,
          "monto_total_millones": 45000.0,
          "anio_inicio": 2028,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 45000.0,
      "monto_total_millones": 45000.0,
      "anio_inicio": 2028,
      "anio_termino": 2031,
      "pagina_documento": 45,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40048033-0",
      "codigo_bip": "40048033-0",
      "nombre": "MEJORAMIENTO EN RIPIO RUTA 7 SECTORES RESTRINGIDOS, COMUNA DE CHILE CHICO",
      "comuna": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 5870.0,
          "monto_total_millones": 5870.0,
          "anio_inicio": 2030,
          "anio_termino": 2033
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 5870.0,
      "monto_total_millones": 5870.0,
      "anio_inicio": 2030,
      "anio_termino": 2033,
      "pagina_documento": 45,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064086-0",
      "codigo_bip": "40064086-0",
      "nombre": "MEJORAMIENTO RUTA 7 SUR SECTOR CRUCE MAITÉN - BERTRAND, COMUNA CHILE CHICO",
      "comuna": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 600.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2033,
          "anio_termino": 2034
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 600.0,
      "monto_total_millones": 600.0,
      "anio_inicio": 2033,
      "anio_termino": 2034,
      "pagina_documento": 45,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064087-0",
      "codigo_bip": "40064087-0",
      "nombre": "MEJORAMIENTO RUTA 7 SUR SECTOR BERTRAND - CONFLUENCIA, COMUNAS CHILE CHICO Y COCHRANE",
      "comuna": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 600.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2033,
          "anio_termino": 2034
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 600.0,
      "monto_total_millones": 600.0,
      "anio_inicio": 2033,
      "anio_termino": 2034,
      "pagina_documento": 45,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40053652-0",
      "codigo_bip": "40053652-0",
      "nombre": "MEJORAMIENTO RUTA 265-CH. TRAMO GUADAL - MALLÍN GRANDE, COMUNA CHILE CHICO",
      "comuna": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1500.0,
          "monto_total_millones": 1500.0,
          "anio_inicio": 2031,
          "anio_termino": 2032
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 10050.0,
          "monto_total_millones": 10050.0,
          "anio_inicio": 2034,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 11550.0,
      "monto_total_millones": 11550.0,
      "anio_inicio": 2031,
      "anio_termino": 2035,
      "pagina_documento": 45,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40066333-0",
      "codigo_bip": "40066333-0",
      "nombre": "MEJORAMIENTO RUTA 265-CH. SECTOR PASO LAS LLAVES, COMUNA DE CHILE CHICO",
      "comuna": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Prefactibilidad",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 991.413,
          "monto_total_millones": 991.413,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1500.0,
          "monto_total_millones": 1500.0,
          "anio_inicio": 2030,
          "anio_termino": 2031
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 9456.0,
          "monto_total_millones": 9456.0,
          "anio_inicio": 2033,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 11947.413,
      "monto_total_millones": 11947.413,
      "anio_inicio": 2027,
      "anio_termino": 2035,
      "pagina_documento": 46,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-30120147-0",
      "codigo_bip": "30120147-0",
      "nombre": "CONSTRUCCIÓN INFRAESTRUCTURA CUEVA DE LAS MANOS SECTOR JEINIMENI P.N. PATAGONIA",
      "comuna": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "CONAF"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "CONAF",
          "monto_subdere_millones": 2412.645,
          "monto_gore_millones": 2412.646,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 4825.291,
          "anio_inicio": 2026,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 2412.645,
      "monto_gore_millones": 2412.646,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 4825.291,
      "anio_inicio": 2026,
      "anio_termino": 2028,
      "pagina_documento": 46,
      "institucion_principal": "CONAF"
    },
    {
      "id": "pdze-30102353-0",
      "codigo_bip": "30102353-0",
      "nombre": "CONSTRUCCIÓN RELLENO SANITARIO CHILE CHICO",
      "comuna": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "Municipalidad de Chile Chico"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Chile Chico",
          "monto_subdere_millones": 4059.548,
          "monto_gore_millones": 4059.549,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 8119.097,
          "anio_inicio": 2026,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 4059.548,
      "monto_gore_millones": 4059.549,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 8119.097,
      "anio_inicio": 2026,
      "anio_termino": 2028,
      "pagina_documento": 46,
      "institucion_principal": "Municipalidad de Chile Chico"
    },
    {
      "id": "pdze-40026579-0",
      "codigo_bip": "40026579-0",
      "nombre": "CONSTRUCCIÓN ALCANTARILLADO Y AP MALLÍN GRANDE",
      "comuna": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "Municipalidad de Chile Chico"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Chile Chico",
          "monto_subdere_millones": 2503.254,
          "monto_gore_millones": 2503.255,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 5006.509,
          "anio_inicio": 2029,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 2503.254,
      "monto_gore_millones": 2503.255,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 5006.509,
      "anio_inicio": 2029,
      "anio_termino": 2031,
      "pagina_documento": 46,
      "institucion_principal": "Municipalidad de Chile Chico"
    },
    {
      "id": "pdze-40029854-0",
      "codigo_bip": "40029854-0",
      "nombre": "MEJORAMIENTO ALCANTARILLADO Y TRATAMIENTO AS PUERTO GUADAL",
      "comuna": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "Municipalidad de Chile Chico"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Chile Chico",
          "monto_subdere_millones": 100.0,
          "monto_gore_millones": 100.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 200.0,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Chile Chico",
          "monto_subdere_millones": 1550.201,
          "monto_gore_millones": 1550.201,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 3100.402,
          "anio_inicio": 2028,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 1650.201,
      "monto_gore_millones": 1650.201,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 3300.402,
      "anio_inicio": 2026,
      "anio_termino": 2030,
      "pagina_documento": 46,
      "institucion_principal": "Municipalidad de Chile Chico"
    },
    {
      "id": "pdze-40072140-0",
      "codigo_bip": "40072140-0",
      "nombre": "MEJORAMIENTO ESTADIO PUERTO GUADAL, COMUNA DE CHILE CHICO",
      "comuna": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "GORE"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "GORE",
          "monto_subdere_millones": 1000.0,
          "monto_gore_millones": 1069.5,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 2069.5,
          "anio_inicio": 2028,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 1000.0,
      "monto_gore_millones": 1069.5,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 2069.5,
      "anio_inicio": 2028,
      "anio_termino": 2029,
      "pagina_documento": 46,
      "institucion_principal": "GORE"
    },
    {
      "id": "pdze-40073969-0",
      "codigo_bip": "40073969-0",
      "nombre": "CONSTRUCCIÓN VIVIENDAS TUTELADAS CHILE CHICO",
      "comuna": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "Municipalidad de Chile Chico"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Chile Chico",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 30.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 30.0,
          "anio_inicio": 2026,
          "anio_termino": 2027
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Chile Chico",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 1348.29,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 1348.29,
          "anio_inicio": 2028,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 1378.29,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 1378.29,
      "anio_inicio": 2026,
      "anio_termino": 2029,
      "pagina_documento": 46,
      "institucion_principal": "Municipalidad de Chile Chico"
    },
    {
      "id": "pdze-40072953-0",
      "codigo_bip": "40072953-0",
      "nombre": "REPOSICIÓN ELEAM COMUNA DE CHILE CHICO",
      "comuna": "Chile Chico",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "Municipalidad de Chile Chico"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Chile Chico",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 95.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 95.0,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Chile Chico",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 2064.4,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 2064.4,
          "anio_inicio": 2028,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 2159.4,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 2159.4,
      "anio_inicio": 2026,
      "anio_termino": 2029,
      "pagina_documento": 46,
      "institucion_principal": "Municipalidad de Chile Chico"
    },
    {
      "id": "pdze-40048026-0",
      "codigo_bip": "40048026-0",
      "nombre": "MEJORAMIENTO RUTA 7 SUR, ALCANTARILLA CASCADA - SAN SEBASTIÁN, COMUNA RÍO IBÁÑEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 25480.1,
          "monto_total_millones": 25480.1,
          "anio_inicio": 2029,
          "anio_termino": 2032
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 25480.1,
      "monto_total_millones": 25480.1,
      "anio_inicio": 2029,
      "anio_termino": 2032,
      "pagina_documento": 48,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40048027-0",
      "codigo_bip": "40048027-0",
      "nombre": "MEJORAMIENTO RUTA 7 SUR, SAN SEBASTIÁN - PUENTE LAS OVEJAS, COMUNA DE RÍO IBÁÑEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 25173.15,
          "monto_total_millones": 25173.15,
          "anio_inicio": 2032,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 25173.15,
      "monto_total_millones": 25173.15,
      "anio_inicio": 2032,
      "anio_termino": 2035,
      "pagina_documento": 48,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064084-0",
      "codigo_bip": "40064084-0",
      "nombre": "MEJORAMIENTO RUTA 7 SECTOR PUENTE LAS OVEJAS - PUENTE TRAIHUANCA, COMUNA RÍO IBÁÑEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 50.0,
          "monto_total_millones": 50.0,
          "anio_inicio": 2035,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 50.0,
      "monto_total_millones": 50.0,
      "anio_inicio": 2035,
      "anio_termino": 2035,
      "pagina_documento": 48,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064085-0",
      "codigo_bip": "40064085-0",
      "nombre": "MEJORAMIENTO RUTA 7 SECTOR PUENTE TRAIHUANCA - CRUCE MURTA, COMUNA RÍO IBÁÑEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1200.0,
          "monto_total_millones": 1200.0,
          "anio_inicio": 2030,
          "anio_termino": 2033
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 50.0,
          "monto_total_millones": 50.0,
          "anio_inicio": 2035,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 1250.0,
      "monto_total_millones": 1250.0,
      "anio_inicio": 2030,
      "anio_termino": 2035,
      "pagina_documento": 48,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064107-0",
      "codigo_bip": "40064107-0",
      "nombre": "REPOSICIÓN PASARELA SIN NOMBRE EN CAMINO X-725, COMUNA RÍO IBÁÑEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 800.0,
          "monto_total_millones": 800.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 4000.0,
          "monto_total_millones": 4000.0,
          "anio_inicio": 2030,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4800.0,
      "monto_total_millones": 4800.0,
      "anio_inicio": 2027,
      "anio_termino": 2031,
      "pagina_documento": 48,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064881-0",
      "codigo_bip": "40064881-0",
      "nombre": "CONSTRUCCIÓN CAMINO LEVICÁN - EL AVELLANO, COMUNA RÍO IBÁÑEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Prefactibilidad",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1500.0,
          "monto_total_millones": 1500.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1200.0,
          "monto_total_millones": 1200.0,
          "anio_inicio": 2030,
          "anio_termino": 2031
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 5200.0,
          "monto_total_millones": 5200.0,
          "anio_inicio": 2033,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 7900.0,
      "monto_total_millones": 7900.0,
      "anio_inicio": 2027,
      "anio_termino": 2035,
      "pagina_documento": 48,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40072394-0",
      "codigo_bip": "40072394-0",
      "nombre": "CONSTRUCCIÓN PUENTE ALTO RÍO IBÁÑEZ EN CAMINO X-726, COMUNA DE RÍO IBÁÑEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 800.0,
          "monto_total_millones": 800.0,
          "anio_inicio": 2030,
          "anio_termino": 2031
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 4000.0,
          "monto_total_millones": 4000.0,
          "anio_inicio": 2032,
          "anio_termino": 2034
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4800.0,
      "monto_total_millones": 4800.0,
      "anio_inicio": 2030,
      "anio_termino": 2034,
      "pagina_documento": 48,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40071128-0",
      "codigo_bip": "40071128-0",
      "nombre": "CONSTRUCCIÓN DEFENSAS FLUVIALES RÍO CHIRIFO, ENGAÑO, RESBALÓN Y MURTA",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DOH"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOH",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 5000.0,
          "monto_total_millones": 5000.0,
          "anio_inicio": 2027,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 5000.0,
      "monto_total_millones": 5000.0,
      "anio_inicio": 2027,
      "anio_termino": 2030,
      "pagina_documento": 48,
      "institucion_principal": "MOP-DOH"
    },
    {
      "id": "pdze-40072314-0",
      "codigo_bip": "40072314-0",
      "nombre": "CONSTRUCCIÓN DEFENSAS FLUVIALES RÍO SIN NOMBRE Y RÍO CAJÓN",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DOH"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOH",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 400.0,
          "monto_total_millones": 400.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOH",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 4000.0,
          "monto_total_millones": 4000.0,
          "anio_inicio": 2030,
          "anio_termino": 2032
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4400.0,
      "monto_total_millones": 4400.0,
      "anio_inicio": 2029,
      "anio_termino": 2032,
      "pagina_documento": 48,
      "institucion_principal": "MOP-DOH"
    },
    {
      "id": "pdze-30452523-0",
      "codigo_bip": "30452523-0",
      "nombre": "CONSTRUCCIÓN INFRAESTRUCTURA PORTUARIA EN PUERTO SÁNCHEZ, RÍO IBÁÑEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 600.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 3500.0,
          "monto_total_millones": 3500.0,
          "anio_inicio": 2029,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4100.0,
      "monto_total_millones": 4100.0,
      "anio_inicio": 2027,
      "anio_termino": 2031,
      "pagina_documento": 48,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-30457775-0",
      "codigo_bip": "30457775-0",
      "nombre": "CONSTRUCCIÓN INFRAESTRUCTURA PORTUARIA EN EL AVELLANO, RÍO IBÁÑEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 600.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 4000.0,
          "monto_total_millones": 4000.0,
          "anio_inicio": 2029,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4600.0,
      "monto_total_millones": 4600.0,
      "anio_inicio": 2027,
      "anio_termino": 2031,
      "pagina_documento": 48,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-40037656-0",
      "codigo_bip": "40037656-0",
      "nombre": "CONSTRUCCIÓN INFRAESTRUCTURA MANTENCIONES Y/O REPARACIONES EMBARCACIONES LAGO GENERAL CARRERA",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 600.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2027,
          "anio_termino": 2027
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 5000.0,
          "monto_total_millones": 5000.0,
          "anio_inicio": 2028,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 5600.0,
      "monto_total_millones": 5600.0,
      "anio_inicio": 2027,
      "anio_termino": 2029,
      "pagina_documento": 49,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-30481316-0",
      "codigo_bip": "30481316-0",
      "nombre": "AMPLIACIÓN MUELLE PUERTO TRANQUILO, COMUNA RÍO IBÁÑEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 600.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2029,
          "anio_termino": 2030
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 3500.0,
          "monto_total_millones": 3500.0,
          "anio_inicio": 2031,
          "anio_termino": 2033
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 4100.0,
      "monto_total_millones": 4100.0,
      "anio_inicio": 2029,
      "anio_termino": 2033,
      "pagina_documento": 49,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-40068920-0",
      "codigo_bip": "40068920-0",
      "nombre": "CONSTRUCCIÓN CENTRO DE SALUD PUERTO RÍO TRANQUILO",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "Servicio de Salud Aysén"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Servicio de Salud Aysén",
          "monto_subdere_millones": 625.0,
          "monto_gore_millones": 625.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 1250.0,
          "anio_inicio": 2029,
          "anio_termino": 2029
        },
        {
          "etapa": "Ejecución",
          "institucion": "Servicio de Salud Aysén",
          "monto_subdere_millones": 5000.0,
          "monto_gore_millones": 5000.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 10000.0,
          "anio_inicio": 2031,
          "anio_termino": 2032
        }
      ],
      "monto_subdere_millones": 5625.0,
      "monto_gore_millones": 5625.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 11250.0,
      "anio_inicio": 2029,
      "anio_termino": 2032,
      "pagina_documento": 49,
      "institucion_principal": "Servicio de Salud Aysén"
    },
    {
      "id": "pdze-40021195-0",
      "codigo_bip": "40021195-0",
      "nombre": "CONSTRUCCIÓN PASEO COSTANERA PUERTO RÍO TRANQUILO",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "Municipalidad de Río Ibáñez"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Río Ibáñez",
          "monto_subdere_millones": 5228.613,
          "monto_gore_millones": 5228.613,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 10457.226,
          "anio_inicio": 2026,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 5228.613,
      "monto_gore_millones": 5228.613,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 10457.226,
      "anio_inicio": 2026,
      "anio_termino": 2029,
      "pagina_documento": 49,
      "institucion_principal": "Municipalidad de Río Ibáñez"
    },
    {
      "id": "pdze-20189906-0",
      "codigo_bip": "20189906-0",
      "nombre": "RESTAURACIÓN MONUMENTO NACIONAL BODEGAS PORTUARIAS, PUERTO IBÁÑEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "Municipalidad de Río Ibáñez"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Río Ibáñez",
          "monto_subdere_millones": 1867.929,
          "monto_gore_millones": 1867.93,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 3735.859,
          "anio_inicio": 2026,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 1867.929,
      "monto_gore_millones": 1867.93,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 3735.859,
      "anio_inicio": 2026,
      "anio_termino": 2028,
      "pagina_documento": 49,
      "institucion_principal": "Municipalidad de Río Ibáñez"
    },
    {
      "id": "pdze-40049068-0",
      "codigo_bip": "40049068-0",
      "nombre": "CONSTRUCCIÓN TERMINAL DE BUSES PUERTO RÍO TRANQUILO, COMUNA DE IBÁÑEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "Municipalidad de Río Ibáñez"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Río Ibáñez",
          "monto_subdere_millones": 1898.543,
          "monto_gore_millones": 1898.544,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 3797.087,
          "anio_inicio": 2026,
          "anio_termino": 2027
        }
      ],
      "monto_subdere_millones": 1898.543,
      "monto_gore_millones": 1898.544,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 3797.087,
      "anio_inicio": 2026,
      "anio_termino": 2027,
      "pagina_documento": 49,
      "institucion_principal": "Municipalidad de Río Ibáñez"
    },
    {
      "id": "pdze-40038397-0",
      "codigo_bip": "40038397-0",
      "nombre": "CONSTRUCCIÓN PARADOR DE BUSES DE VILLA CERRO CASTILLO, COMUNA DE RÍO IBÁÑEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "Municipalidad de Río Ibáñez"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Río Ibáñez",
          "monto_subdere_millones": 269.402,
          "monto_gore_millones": 269.402,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 538.804,
          "anio_inicio": 2026,
          "anio_termino": 2027
        }
      ],
      "monto_subdere_millones": 269.402,
      "monto_gore_millones": 269.402,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 538.804,
      "anio_inicio": 2026,
      "anio_termino": 2027,
      "pagina_documento": 49,
      "institucion_principal": "Municipalidad de Río Ibáñez"
    },
    {
      "id": "pdze-40072564-0",
      "codigo_bip": "40072564-0",
      "nombre": "REPOSICIÓN CENTRO DE GESTIÓN DE RESIDUOS SÓLIDOS DE PUERTO IBÁÑEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "Municipalidad de Río Ibáñez"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Río Ibáñez",
          "monto_subdere_millones": 100.0,
          "monto_gore_millones": 205.606,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 305.606,
          "anio_inicio": 2028,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Río Ibáñez",
          "monto_subdere_millones": 1850.0,
          "monto_gore_millones": 1850.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 3700.0,
          "anio_inicio": 2030,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 1950.0,
      "monto_gore_millones": 2055.606,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 4005.606,
      "anio_inicio": 2028,
      "anio_termino": 2031,
      "pagina_documento": 49,
      "institucion_principal": "Municipalidad de Río Ibáñez"
    },
    {
      "id": "pdze-40072134-0",
      "codigo_bip": "40072134-0",
      "nombre": "MEJORAMIENTO ESTADIO PUERTO RÍO TRANQUILO, COMUNA DE RÍO IBÁÑEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "GORE"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "GORE",
          "monto_subdere_millones": 1034.75,
          "monto_gore_millones": 1034.75,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 2069.5,
          "anio_inicio": 2028,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 1034.75,
      "monto_gore_millones": 1034.75,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 2069.5,
      "anio_inicio": 2028,
      "anio_termino": 2029,
      "pagina_documento": 49,
      "institucion_principal": "GORE"
    },
    {
      "id": "pdze-40074566-0",
      "codigo_bip": "40074566-0",
      "nombre": "CONSTRUCCIÓN BORDE COSTERO PUERTO SÁNCHEZ",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "Municipalidad de Río Ibáñez"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Río Ibáñez",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 300.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 300.0,
          "anio_inicio": 2028,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Río Ibáñez",
          "monto_subdere_millones": 670.0,
          "monto_gore_millones": 6000.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 6670.0,
          "anio_inicio": 2029,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 670.0,
      "monto_gore_millones": 6300.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 6970.0,
      "anio_inicio": 2028,
      "anio_termino": 2031,
      "pagina_documento": 49,
      "institucion_principal": "Municipalidad de Río Ibáñez"
    },
    {
      "id": "pdze-40003500-0",
      "codigo_bip": "40003500-0",
      "nombre": "REPOSICIÓN RETÉN DE CARABINEROS RÍO TRANQUILO",
      "comuna": "Río Ibáñez",
      "provincia": "Provincia General Carrera",
      "instituciones": [
        "Carabineros"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Carabineros",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 3477.383,
          "monto_total_millones": 3477.383,
          "anio_inicio": 2026,
          "anio_termino": 2027
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 3477.383,
      "monto_total_millones": 3477.383,
      "anio_inicio": 2026,
      "anio_termino": 2027,
      "pagina_documento": 49,
      "institucion_principal": "Carabineros"
    },
    {
      "id": "pdze-40064090-0",
      "codigo_bip": "40064090-0",
      "nombre": "MEJORAMIENTO RUTA 7 SUR. SECTOR COCHRANE - LAGO JUNCAL, COMUNA DE COCHRANE",
      "comuna": "Cochrane",
      "provincia": "Provincia Capitán Prat",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 500.0,
          "monto_total_millones": 500.0,
          "anio_inicio": 2035,
          "anio_termino": 2035
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 500.0,
      "monto_total_millones": 500.0,
      "anio_inicio": 2035,
      "anio_termino": 2035,
      "pagina_documento": 52,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40064100-0",
      "codigo_bip": "40064100-0",
      "nombre": "REPOSICIÓN PASARELA EL SALTO EN CAMINO X-892, COMUNA COCHRANE",
      "comuna": "Cochrane",
      "provincia": "Provincia Capitán Prat",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 2000.0,
          "monto_total_millones": 2000.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 2000.0,
      "monto_total_millones": 2000.0,
      "anio_inicio": 2027,
      "anio_termino": 2028,
      "pagina_documento": 52,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40059882-0",
      "codigo_bip": "40059882-0",
      "nombre": "REPOSICIÓN PUENTE COLGANTE VARGAS EN CAMINO X-910, COMUNA DE COCHRANE",
      "comuna": "Cochrane",
      "provincia": "Provincia Capitán Prat",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 258.112,
          "monto_total_millones": 258.112,
          "anio_inicio": 2026,
          "anio_termino": 2027
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 258.112,
      "monto_total_millones": 258.112,
      "anio_inicio": 2026,
      "anio_termino": 2027,
      "pagina_documento": 52,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40066750-0",
      "codigo_bip": "40066750-0",
      "nombre": "MEJORAMIENTO CAMINOS VARIOS, COMUNA COCHRANE",
      "comuna": "Cochrane",
      "provincia": "Provincia Capitán Prat",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 1000.0,
          "monto_total_millones": 1000.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 35000.0,
          "monto_total_millones": 35000.0,
          "anio_inicio": 2030,
          "anio_termino": 2032
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 36000.0,
      "monto_total_millones": 36000.0,
      "anio_inicio": 2027,
      "anio_termino": 2032,
      "pagina_documento": 52,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40072925-0",
      "codigo_bip": "40072925-0",
      "nombre": "DISEÑO Y CONSTRUCCIÓN NUEVO REFUGIO/TERMINAL AERÓDROMO COCHRANE",
      "comuna": "Cochrane",
      "provincia": "Provincia Capitán Prat",
      "instituciones": [
        "MOP-DAP"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DAP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 313.4,
          "monto_total_millones": 313.4,
          "anio_inicio": 2028,
          "anio_termino": 2029
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DAP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 10168.8,
          "monto_total_millones": 10168.8,
          "anio_inicio": 2031,
          "anio_termino": 2034
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 10482.2,
      "monto_total_millones": 10482.2,
      "anio_inicio": 2028,
      "anio_termino": 2034,
      "pagina_documento": 52,
      "institucion_principal": "MOP-DAP"
    },
    {
      "id": "pdze-40071815-0",
      "codigo_bip": "40071815-0",
      "nombre": "CONSTRUCCIÓN ESTABLECIMIENTO LARGA ESTADÍA PARA ADULTOS MAYORES COCHRANE",
      "comuna": "Cochrane",
      "provincia": "Provincia Capitán Prat",
      "instituciones": [
        "Municipalidad de Cochrane"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Cochrane",
          "monto_subdere_millones": 150.0,
          "monto_gore_millones": 150.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 300.0,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Cochrane",
          "monto_subdere_millones": 1750.0,
          "monto_gore_millones": 1750.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 3500.0,
          "anio_inicio": 2028,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 1900.0,
      "monto_gore_millones": 1900.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 3800.0,
      "anio_inicio": 2026,
      "anio_termino": 2028,
      "pagina_documento": 52,
      "institucion_principal": "Municipalidad de Cochrane"
    },
    {
      "id": "pdze-40071843-0",
      "codigo_bip": "40071843-0",
      "nombre": "CONSTRUCCIÓN POLIDEPORTIVO PROVINCIAL, COCHRANE",
      "comuna": "Cochrane",
      "provincia": "Provincia Capitán Prat",
      "instituciones": [
        "Municipalidad de Cochrane"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "Municipalidad de Cochrane",
          "monto_subdere_millones": 125.0,
          "monto_gore_millones": 125.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 250.0,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de Cochrane",
          "monto_subdere_millones": 3707.0,
          "monto_gore_millones": 3707.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 7414.0,
          "anio_inicio": 2028,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 3832.0,
      "monto_gore_millones": 3832.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 7664.0,
      "anio_inicio": 2026,
      "anio_termino": 2029,
      "pagina_documento": 52,
      "institucion_principal": "Municipalidad de Cochrane"
    },
    {
      "id": "pdze-40072141-0",
      "codigo_bip": "40072141-0",
      "nombre": "MEJORAMIENTO ESTADIO AONIKENK, COMUNA DE COCHRANE",
      "comuna": "Cochrane",
      "provincia": "Provincia Capitán Prat",
      "instituciones": [
        "GORE"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "GORE",
          "monto_subdere_millones": 1000.0,
          "monto_gore_millones": 1072.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 2072.0,
          "anio_inicio": 2028,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 1000.0,
      "monto_gore_millones": 1072.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 2072.0,
      "anio_inicio": 2028,
      "anio_termino": 2029,
      "pagina_documento": 52,
      "institucion_principal": "GORE"
    },
    {
      "id": "pdze-40072464-0",
      "codigo_bip": "40072464-0",
      "nombre": "CONSTRUCCIÓN CAMINO AERÓDROMO - SECTOR JUNQUILLO, COMUNA DE TORTEL",
      "comuna": "Tortel",
      "provincia": "Provincia Capitán Prat",
      "instituciones": [
        "MOP-DV"
      ],
      "etapas": [
        {
          "etapa": "Prefactibilidad",
          "institucion": "MOP-DV",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 500.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 500.0,
          "anio_inicio": 2031,
          "anio_termino": 2032
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 500.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 500.0,
      "anio_inicio": 2031,
      "anio_termino": 2032,
      "pagina_documento": 54,
      "institucion_principal": "MOP-DV"
    },
    {
      "id": "pdze-40060227-0",
      "codigo_bip": "40060227-0",
      "nombre": "CONSTRUCCIÓN REFUGIO DE PASAJEROS Y CARGA, TORTEL",
      "comuna": "Tortel",
      "provincia": "Provincia Capitán Prat",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 600.0,
          "monto_total_millones": 600.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        },
        {
          "etapa": "Ejecución",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 2500.0,
          "monto_total_millones": 2500.0,
          "anio_inicio": 2029,
          "anio_termino": 2031
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 3100.0,
      "monto_total_millones": 3100.0,
      "anio_inicio": 2027,
      "anio_termino": 2031,
      "pagina_documento": 54,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-40072490-0",
      "codigo_bip": "40072490-0",
      "nombre": "CONSTRUCCIÓN INFRAESTRUCTURA PORTUARIA DE CONECTIVIDAD EN SECTOR BAHÍA CUTE, COMUNA DE TORTEL",
      "comuna": "Tortel",
      "provincia": "Provincia Capitán Prat",
      "instituciones": [
        "MOP-DOP"
      ],
      "etapas": [
        {
          "etapa": "Prefactibilidad",
          "institucion": "MOP-DOP",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 250.0,
          "monto_total_millones": 250.0,
          "anio_inicio": 2033,
          "anio_termino": 2034
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 250.0,
      "monto_total_millones": 250.0,
      "anio_inicio": 2033,
      "anio_termino": 2034,
      "pagina_documento": 54,
      "institucion_principal": "MOP-DOP"
    },
    {
      "id": "pdze-40064587-0",
      "codigo_bip": "40064587-0",
      "nombre": "MEJORAMIENTO PARQUE URBANO CALETA TORTEL",
      "comuna": "Tortel",
      "provincia": "Provincia Capitán Prat",
      "instituciones": [
        "Seremi de Vivienda y Urbanismo"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Seremi de Vivienda y Urbanismo",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 1700.0,
          "monto_sectorial_millones": 1700.0,
          "monto_total_millones": 3400.0,
          "anio_inicio": 2030,
          "anio_termino": 2032
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 1700.0,
      "monto_sectorial_millones": 1700.0,
      "monto_total_millones": 3400.0,
      "anio_inicio": 2030,
      "anio_termino": 2032,
      "pagina_documento": 54,
      "institucion_principal": "Seremi de Vivienda y Urbanismo"
    },
    {
      "id": "pdze-40072145-0",
      "codigo_bip": "40072145-0",
      "nombre": "MEJORAMIENTO ESTADIO CALETA TORTEL, COMUNA DE TORTEL",
      "comuna": "Tortel",
      "provincia": "Provincia Capitán Prat",
      "instituciones": [
        "GORE"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "GORE",
          "monto_subdere_millones": 1000.0,
          "monto_gore_millones": 1074.5,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 2074.5,
          "anio_inicio": 2028,
          "anio_termino": 2029
        }
      ],
      "monto_subdere_millones": 1000.0,
      "monto_gore_millones": 1074.5,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 2074.5,
      "anio_inicio": 2028,
      "anio_termino": 2029,
      "pagina_documento": 54,
      "institucion_principal": "GORE"
    },
    {
      "id": "pdze-40073129-0",
      "codigo_bip": "40073129-0",
      "nombre": "REPOSICIÓN GIMNASIO CENTRO COMUNITARIO CALETA TORTEL",
      "comuna": "Tortel",
      "provincia": "Provincia Capitán Prat",
      "instituciones": [
        "GORE"
      ],
      "etapas": [
        {
          "etapa": "Diseño",
          "institucion": "GORE",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 300.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 300.0,
          "anio_inicio": 2026,
          "anio_termino": 2026
        },
        {
          "etapa": "Ejecución",
          "institucion": "GORE",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 3000.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 3000.0,
          "anio_inicio": 2027,
          "anio_termino": 2028
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 3300.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 3300.0,
      "anio_inicio": 2026,
      "anio_termino": 2028,
      "pagina_documento": 54,
      "institucion_principal": "GORE"
    },
    {
      "id": "pdze-167",
      "codigo_bip": null,
      "nombre": "CONSTRUCCIÓN CENTRO DE DESARROLLO CIENTÍFICO, CULTURAL Y TURÍSTICO OBSERVATORIO DEL HIELO, COMUNA DE O'HIGGINS",
      "comuna": "O’Higgins",
      "provincia": "Provincia Capitán Prat",
      "instituciones": [
        "Municipalidad de O’Higgins"
      ],
      "etapas": [
        {
          "etapa": "Ejecución",
          "institucion": "Municipalidad de O’Higgins",
          "monto_subdere_millones": 0.0,
          "monto_gore_millones": 0.0,
          "monto_sectorial_millones": 0.0,
          "monto_total_millones": 2943.365,
          "anio_inicio": 2026,
          "anio_termino": 2030
        }
      ],
      "monto_subdere_millones": 0.0,
      "monto_gore_millones": 0.0,
      "monto_sectorial_millones": 0.0,
      "monto_total_millones": 2943.365,
      "anio_inicio": 2026,
      "anio_termino": 2030,
      "pagina_documento": 50,
      "institucion_principal": "Municipalidad de O’Higgins"
    }
  ]
}

function normalizeBipCode(raw?: string | null): string {
  if (!raw) return ''
  return raw.replace(/\s+/g, '').toUpperCase()
}

const PDZE_BY_BIP = new Map<string, PdzeIniciativa>()
for (const item of PDZE_AYSEN_2026.iniciativas) {
  if (item.codigo_bip) {
    PDZE_BY_BIP.set(normalizeBipCode(item.codigo_bip), item)
  }
}

export function findPdzeByBip(codigoBip?: string | null): PdzeIniciativa | null {
  const key = normalizeBipCode(codigoBip)
  if (!key) return null
  return PDZE_BY_BIP.get(key) ?? null
}

export function isProyectoPdze(codigoBip?: string | null): boolean {
  return findPdzeByBip(codigoBip) !== null
}
