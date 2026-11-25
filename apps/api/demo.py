"""Datos artificiales para ejercitar la interfaz local."""
from decimal import Decimal

REGIONES = (
    "Tarapacá", "Antofagasta", "Atacama", "Coquimbo", "Valparaíso", "O’Higgins",
    "Maule", "Biobío", "La Araucanía", "Los Lagos", "Aysén", "Magallanes",
    "Metropolitana", "Los Ríos", "Arica y Parinacota", "Ñuble",
)
CORTE = "prueba-local"


def territorios():
    return [
        dict(codigo=code, nombre=name, nivel="nacional" if code == "CL" else "regional",
             vigente_desde=None, vigente_hasta=None)
        for code, name in [("CL", "Chile"), *((f"{n:02}", name) for n, name in enumerate(REGIONES, 1))]
    ]


def nivel(index, year, nominal):
    if index == 0:
        return sum(nivel(n, year, nominal) for n in range(1, 17))
    return (70000 + ((index * 13) % 17) * 31000) * (
        100 + (year - 2012) * (2 + index % 5 + 3 * nominal)
    )


def generar():
    rows, sources = [], {}
    for year in range(2013, 2026):
        for territory in territorios():
            code = territory["codigo"]
            index = 0 if code == "CL" else int(code)
            for metric, valuation in [
                ("nivel", "real"), ("nivel", "nominal"), ("crecimiento", "real"),
                *([("participacion", "nominal")] if index else []),
            ]:
                value = Decimal(nivel(index, year, valuation == "nominal"))
                if metric == "crecimiento":
                    value = 100 * (value / nivel(index, year - 1, False) - 1)
                if metric == "participacion":
                    value = 100 * value / nivel(0, year, True)
                missing = metric == "crecimiento" and year == 2013
                key = f"{CORTE}-{code}-{year}-{metric}-{valuation}"
                rows.append(dict(
                    id=key, territorio=code, anio=year, metrica=metric, valoracion=valuation,
                    valor=None if missing else format(value.quantize(Decimal("0.01")), "f"),
                    unidad="millones CLP" if metric == "nivel" else "%",
                    anio_referencia=2018 if valuation == "real" else None,
                    estado="faltante" if missing else "informado",
                    clase="no_disponible" if missing else "prueba", publicacion=CORTE,
                ))
                sources[key] = dict(
                    observacion=key, publicacion=CORTE, serie_bde=None, artefacto=None, selector=None,
                    formula_version=None, insumos=[],
                    motivo="Año previo ausente en la demostración." if missing else "Valor sintético. No corresponde a la BDE.",
                )
    return rows, sources


FILAS, FUENTES = generar()
PUBLICACION = dict(
    id=CORTE, fecha="2026-11-24T00:00:00Z", estado="prueba", fuente="fixture-sintetico",
    cobertura=dict(esperadas=len(FILAS), disponibles=sum(row["valor"] is not None for row in FILAS)),
    cambios=[],
)
