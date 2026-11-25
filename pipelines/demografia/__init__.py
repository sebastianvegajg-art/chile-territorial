"""Extractores e indicadores oficiales de demografía y población INE."""

from pipelines.demografia.ine_poblacion import (
    ADVERTENCIA_ESCALA_PIB,
    CONTEXTO_DECIMAL,
    CUT_ANTARTICA,
    CUT_CABO_DE_HORNOS,
    PRECISION_DECIMAL,
    SERIES_POBLACION_INE,
    TOTAL_COMUNAS_CHILE,
    TOTAL_MUNICIPALIDADES_CHILE,
    InePoblacionError,
    calcular_pib_per_capita_nacional_y_regional,
    ejecutar_extraccion,
    importar_poblacion_comunal_ine,
    normalizar_poblacion_ine,
    reproducir_desde_raw,
)

__all__ = [
    "ADVERTENCIA_ESCALA_PIB",
    "CONTEXTO_DECIMAL",
    "CUT_ANTARTICA",
    "CUT_CABO_DE_HORNOS",
    "PRECISION_DECIMAL",
    "SERIES_POBLACION_INE",
    "TOTAL_COMUNAS_CHILE",
    "TOTAL_MUNICIPALIDADES_CHILE",
    "InePoblacionError",
    "calcular_pib_per_capita_nacional_y_regional",
    "ejecutar_extraccion",
    "importar_poblacion_comunal_ine",
    "normalizar_poblacion_ine",
    "reproducir_desde_raw",
]
