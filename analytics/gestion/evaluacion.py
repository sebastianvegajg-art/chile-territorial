"""Motores auditables de evaluación de programas y eficiencia administrativa (Cruces 3 y 4)."""

import re
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext

INTENSIDAD_BENEFICIARIO_VERSION = "gestion-intensidad-beneficiario-v1"
COBERTURA_PROGRAMA_VERSION = "gestion-cobertura-programa-v1"
EFICIENCIA_ADMINISTRATIVA_VERSION = "gestion-eficiencia-administrativa-v1"

_DECIMAL = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")
_CONTEXTO = Context(prec=34, rounding=ROUND_HALF_EVEN)

_ADVERTENCIA_INTENSIDAD = (
    "El monto por beneficiario no permite inferir por sí solo eficiencia, clientelismo ni impacto causal."
)
_ADVERTENCIA_COBERTURA = (
    "La cobertura depende de la deduplicación de beneficiarios únicos y de la definición, "
    "fuente y vigencia del padrón de población elegible; no permite inferir por sí sola "
    "focalización ni impacto causal."
)
_ADVERTENCIA_EFICIENCIA = (
    "Indicador descriptivo de gestión administrativa: las comparaciones entre períodos o "
    "instituciones exigen ajustes por inflación (moneda constante comparable) y control por "
    "cambios de funciones, perímetro institucional, base de reparto de costos compartidos, "
    "calidad, plazos y resultados."
)


def _parsear_decimal_estricto(valor: object) -> Decimal | None:
    """Convierte str decimal estricto, Decimal finito o int (excluyendo bool y float) a Decimal."""
    if isinstance(valor, bool) or isinstance(valor, float) or valor is None:
        return None
    if isinstance(valor, Decimal):
        return valor if valor.is_finite() else None
    if isinstance(valor, int):
        return Decimal(valor)
    if isinstance(valor, str) and _DECIMAL.fullmatch(valor):
        return Decimal(valor)
    return None


def _es_entero_exacto(valor: Decimal) -> bool:
    return valor == valor.to_integral_value()


def _formatear_decimal(valor: Decimal) -> str:
    if not valor:
        return "0"
    return format(valor.normalize(_CONTEXTO), "f")


def intensidad_beneficiario(
    gasto_devengado_clp: int | str | Decimal | None,
    beneficiarios_unicos: int | str | Decimal | None,
    *,
    meses_programa: int | str | Decimal = 12,
    dias_programa: int | str | Decimal = 365,
) -> dict[str, object]:
    """Calcula la intensidad de gasto devengado por beneficiario único (total, mensual y diario)."""

    def ausente(motivo: str, estado: str = "faltante") -> dict[str, object]:
        return {
            "valor": None,
            "monto_por_beneficiario_clp": None,
            "equivalente_mensual_clp": None,
            "equivalente_diario_clp": None,
            "unidad": "CLP por beneficiario",
            "formula_version": INTENSIDAD_BENEFICIARIO_VERSION,
            "estado": estado,
            "clase": "no_disponible",
            "motivo": motivo,
            "insumos": {
                "gasto_devengado_clp": None if gasto_devengado_clp is None else str(gasto_devengado_clp),
                "beneficiarios_unicos": None if beneficiarios_unicos is None else str(beneficiarios_unicos),
                "meses_programa": None if meses_programa is None else str(meses_programa),
                "dias_programa": None if dias_programa is None else str(dias_programa),
            },
            "advertencia_metodologica": _ADVERTENCIA_INTENSIDAD,
        }

    if gasto_devengado_clp is None or beneficiarios_unicos is None:
        return ausente("Falta el gasto devengado o el número de beneficiarios únicos.", estado="faltante")

    gasto = _parsear_decimal_estricto(gasto_devengado_clp)
    beneficiarios = _parsear_decimal_estricto(beneficiarios_unicos)
    meses = _parsear_decimal_estricto(meses_programa)
    dias = _parsear_decimal_estricto(dias_programa)

    if gasto is None or beneficiarios is None:
        return ausente(
            "El gasto devengado y los beneficiarios únicos deben ser enteros, Decimal o cadenas decimales válidas (no float).",
            estado="error",
        )
    if meses is None or dias is None:
        return ausente(
            "Los parámetros de duración del programa (meses y días) deben ser valores decimales válidos (no float).",
            estado="error",
        )

    if gasto < 0:
        return ausente("El gasto devengado no puede ser negativo.", estado="error")
    if beneficiarios == 0:
        return ausente("El número de beneficiarios únicos (denominador) es cero.", estado="faltante")
    if beneficiarios < 0:
        return ausente("El número de beneficiarios únicos debe ser estrictamente positivo.", estado="error")
    if not _es_entero_exacto(beneficiarios):
        return ausente("El número de beneficiarios únicos debe ser un entero exacto.", estado="error")
    if meses <= 0 or dias <= 0:
        return ausente("La duración del programa en meses y días debe ser estrictamente positiva.", estado="error")

    with localcontext(_CONTEXTO):
        monto_total = gasto / beneficiarios
        equivalente_mensual = gasto / (beneficiarios * meses)
        equivalente_diario = gasto / (beneficiarios * dias)

    monto_str = _formatear_decimal(monto_total)
    return {
        "valor": monto_str,
        "monto_por_beneficiario_clp": monto_str,
        "equivalente_mensual_clp": _formatear_decimal(equivalente_mensual),
        "equivalente_diario_clp": _formatear_decimal(equivalente_diario),
        "unidad": "CLP por beneficiario",
        "formula_version": INTENSIDAD_BENEFICIARIO_VERSION,
        "estado": "informado",
        "clase": "descriptivo",
        "motivo": None,
        "insumos": {
            "gasto_devengado_clp": _formatear_decimal(gasto),
            "beneficiarios_unicos": _formatear_decimal(beneficiarios),
            "meses_programa": _formatear_decimal(meses),
            "dias_programa": _formatear_decimal(dias),
        },
        "advertencia_metodologica": _ADVERTENCIA_INTENSIDAD,
    }


def cobertura_programa(
    beneficiarios_unicos: int | str | Decimal | None,
    poblacion_elegible: int | str | Decimal | None,
) -> dict[str, object]:
    """Calcula la cobertura porcentual `100 * beneficiarios_unicos / poblacion_elegible`.

    Marca explícitamente revisión cuando el resultado supera 100% (posible duplicidad o
    descalce del padrón de población elegible).
    """

    def ausente(motivo: str, estado: str = "faltante") -> dict[str, object]:
        return {
            "valor": None,
            "cobertura_pct": None,
            "unidad": "porcentaje",
            "requiere_revision": False,
            "motivo_revision": None,
            "formula_version": COBERTURA_PROGRAMA_VERSION,
            "estado": estado,
            "clase": "no_disponible",
            "motivo": motivo,
            "insumos": {
                "beneficiarios_unicos": None if beneficiarios_unicos is None else str(beneficiarios_unicos),
                "poblacion_elegible": None if poblacion_elegible is None else str(poblacion_elegible),
            },
            "advertencia_metodologica": _ADVERTENCIA_COBERTURA,
        }

    if beneficiarios_unicos is None or poblacion_elegible is None:
        return ausente("Falta el número de beneficiarios únicos o la población elegible.", estado="faltante")

    beneficiarios = _parsear_decimal_estricto(beneficiarios_unicos)
    elegible = _parsear_decimal_estricto(poblacion_elegible)

    if beneficiarios is None or elegible is None:
        return ausente(
            "Beneficiarios únicos y población elegible deben ser enteros, Decimal o cadenas decimales válidas (no float).",
            estado="error",
        )
    if beneficiarios < 0:
        return ausente("Los beneficiarios únicos no pueden ser negativos.", estado="error")
    if not _es_entero_exacto(beneficiarios):
        return ausente("Los beneficiarios únicos deben ser un entero exacto.", estado="error")
    if elegible == 0:
        return ausente("La población elegible (denominador) es cero.", estado="faltante")
    if elegible < 0:
        return ausente("La población elegible (denominador) debe ser estrictamente positiva.", estado="error")

    with localcontext(_CONTEXTO):
        cobertura = (Decimal(100) * beneficiarios) / elegible

    supera_100 = cobertura > Decimal(100)
    motivo_revision = (
        "La cobertura supera 100%: revisar posible duplicidad de beneficiarios, "
        "descalce temporal o definición incompatible del padrón de población elegible."
        if supera_100
        else None
    )
    cobertura_str = _formatear_decimal(cobertura)

    return {
        "valor": cobertura_str,
        "cobertura_pct": cobertura_str,
        "unidad": "porcentaje",
        "requiere_revision": supera_100,
        "motivo_revision": motivo_revision,
        "formula_version": COBERTURA_PROGRAMA_VERSION,
        "estado": "requiere_revision" if supera_100 else "informado",
        "clase": "descriptivo",
        "motivo": motivo_revision,
        "insumos": {
            "beneficiarios_unicos": _formatear_decimal(beneficiarios),
            "poblacion_elegible": _formatear_decimal(elegible),
        },
        "advertencia_metodologica": _ADVERTENCIA_COBERTURA,
    }


def eficiencia_administrativa(
    costo_administrativo_clp: int | str | Decimal | None,
    inversion_ejecutada_clp: int | str | Decimal | None,
    *,
    unidades_resultado: int | str | Decimal | None = None,
    misma_moneda_y_periodo: bool = True,
) -> dict[str, object]:
    """Calcula razones descriptivas de eficiencia administrativa (Cruce 4).

    Calcula `costo_admin_por_peso_invertido`, `porcentaje_sobre_inversion` y, cuando
    `unidades_resultado > 0`, `costo_por_resultado`. Exige `misma_moneda_y_periodo=True`.
    """

    def ausente(motivo: str, estado: str = "faltante") -> dict[str, object]:
        return {
            "valor": None,
            "costo_admin_por_peso_invertido": None,
            "porcentaje_sobre_inversion": None,
            "costo_por_resultado": None,
            "motivo_costo_por_resultado": None,
            "unidad": "CLP por CLP invertido",
            "formula_version": EFICIENCIA_ADMINISTRATIVA_VERSION,
            "estado": estado,
            "clase": "no_disponible",
            "motivo": motivo,
            "insumos": {
                "costo_administrativo_clp": (
                    None if costo_administrativo_clp is None else str(costo_administrativo_clp)
                ),
                "inversion_ejecutada_clp": (
                    None if inversion_ejecutada_clp is None else str(inversion_ejecutada_clp)
                ),
                "unidades_resultado": None if unidades_resultado is None else str(unidades_resultado),
                "misma_moneda_y_periodo": misma_moneda_y_periodo,
            },
            "advertencia_metodologica": _ADVERTENCIA_EFICIENCIA,
        }

    if misma_moneda_y_periodo is not True:
        return ausente(
            "Comparabilidad insuficiente: se exige misma_moneda_y_periodo=True (moneda constante y período equivalente) para calcular eficiencia administrativa.",
            estado="faltante",
        )

    if costo_administrativo_clp is None or inversion_ejecutada_clp is None:
        return ausente("Falta el costo administrativo o la inversión ejecutada.", estado="faltante")

    costo_admin = _parsear_decimal_estricto(costo_administrativo_clp)
    inversion = _parsear_decimal_estricto(inversion_ejecutada_clp)

    if costo_admin is None or inversion is None:
        return ausente(
            "El costo administrativo y la inversión ejecutada deben ser enteros, Decimal o cadenas decimales válidas (no float).",
            estado="error",
        )
    if costo_admin < 0:
        return ausente("El costo administrativo no puede ser negativo.", estado="error")
    if inversion == 0:
        return ausente("La inversión ejecutada (denominador) es cero.", estado="faltante")
    if inversion < 0:
        return ausente("La inversión ejecutada (denominador) debe ser estrictamente positiva.", estado="error")

    unidades_dec: Decimal | None = None
    motivo_resultado: str | None = None
    if unidades_resultado is not None:
        unidades_dec = _parsear_decimal_estricto(unidades_resultado)
        if unidades_dec is None:
            return ausente(
                "Las unidades de resultado deben ser un entero, Decimal o cadena decimal válida (no float).",
                estado="error",
            )
        if unidades_dec < 0:
            return ausente("Las unidades de resultado no pueden ser negativas.", estado="error")
        if unidades_dec == 0:
            motivo_resultado = "Unidades de resultado es cero; costo_por_resultado queda sin cálculo."

    with localcontext(_CONTEXTO):
        ratio = costo_admin / inversion
        porcentaje = (Decimal(100) * costo_admin) / inversion
        costo_resultado_str = (
            _formatear_decimal(costo_admin / unidades_dec)
            if unidades_dec is not None and unidades_dec > 0
            else None
        )

    ratio_str = _formatear_decimal(ratio)
    return {
        "valor": ratio_str,
        "costo_admin_por_peso_invertido": ratio_str,
        "porcentaje_sobre_inversion": _formatear_decimal(porcentaje),
        "costo_por_resultado": costo_resultado_str,
        "motivo_costo_por_resultado": motivo_resultado,
        "unidad": "CLP por CLP invertido",
        "formula_version": EFICIENCIA_ADMINISTRATIVA_VERSION,
        "estado": "informado",
        "clase": "descriptivo",
        "motivo": None,
        "insumos": {
            "costo_administrativo_clp": _formatear_decimal(costo_admin),
            "inversion_ejecutada_clp": _formatear_decimal(inversion),
            "unidades_resultado": None if unidades_dec is None else _formatear_decimal(unidades_dec),
            "misma_moneda_y_periodo": True,
        },
        "advertencia_metodologica": _ADVERTENCIA_EFICIENCIA,
    }
