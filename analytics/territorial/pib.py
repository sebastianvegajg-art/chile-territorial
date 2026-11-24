"""Indicadores anuales a partir de niveles normalizados del PIB."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext

Observacion = Mapping[str, object]

CRECIMIENTO_VERSION = "pib-crecimiento-v1"
PARTICIPACION_VERSION = "pib-participacion-v1"
_DECIMAL = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")
_REGION = re.compile(r"0[1-9]|1[0-6]")
_ESTADOS_DISPONIBLES = {"informado", "preliminar"}
_ESTADOS_AUSENTES = {"faltante", "suprimido", "no_aplicable", "error"}
_CLASES = {"oficial", "estimacion", "prueba"}
_CONTEXTO = Context(prec=34, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True)
class Resultado:
    valor: str | None
    motivo: str | None
    formula_version: str
    insumos: tuple[str, ...]
    estado: str
    clase: str


def crecimiento(real_actual: Observacion | None, real_previo: Observacion | None) -> Resultado:
    """Calcula la variación porcentual real para años consecutivos de un territorio."""
    return _calcular(real_actual, real_previo, CRECIMIENTO_VERSION)


def participacion(
    nominal_regional: Observacion | None, nominal_nacional: Observacion | None
) -> Resultado:
    """Calcula la proporción porcentual de una región respecto de Chile."""
    return _calcular(nominal_regional, nominal_nacional, PARTICIPACION_VERSION)


def _calcular(
    numerador: Observacion | None, denominador: Observacion | None, version: str
) -> Resultado:
    insumos = tuple(
        fila["id"]
        for fila in (numerador, denominador)
        if fila is not None and isinstance(fila.get("id"), str) and fila["id"]
    )

    def ausente(motivo: str, estado: str = "faltante") -> Resultado:
        return Resultado(None, motivo, version, insumos, estado, "no_disponible")

    if numerador is None or denominador is None:
        return ausente("Falta un nivel de PIB requerido para el cálculo.")
    if len(insumos) != 2 or not numerador.get("publicacion"):
        return ausente("Los niveles carecen de identificadores de procedencia.")
    if numerador["publicacion"] != denominador.get("publicacion"):
        return ausente("Los niveles pertenecen a publicaciones diferentes.")

    es_crecimiento = version == CRECIMIENTO_VERSION
    valoracion = "real" if es_crecimiento else "nominal"
    for fila in (numerador, denominador):
        if fila.get("metrica") != "nivel" or fila.get("valoracion") != valoracion:
            return ausente("La métrica o valoración del nivel es incompatible.")
    if numerador.get("unidad") != "millones CLP" or numerador["unidad"] != denominador.get("unidad"):
        return ausente("Las unidades difieren o no están normalizadas a millones de CLP.")

    anio = numerador.get("anio")
    anio_base = denominador.get("anio")
    if type(anio) is not int or type(anio_base) is not int:
        return ausente("El período anual de los niveles es inválido.")
    territorio = numerador.get("territorio")
    if not isinstance(territorio, str):
        return ausente("El territorio del numerador es inválido.")
    if es_crecimiento:
        if anio != anio_base + 1 or territorio != denominador.get("territorio"):
            return ausente("El crecimiento requiere años consecutivos del mismo territorio.")
        referencia = numerador.get("anio_referencia")
        if type(referencia) is not int or referencia != denominador.get("anio_referencia"):
            return ausente("Los niveles reales requieren el mismo año de referencia.")
    else:
        if anio != anio_base or not _REGION.fullmatch(territorio) or denominador.get("territorio") != "CL":
            return ausente("La participación requiere una región y el total nacional del mismo año.")
        if any(fila.get("anio_referencia") is not None for fila in (numerador, denominador)):
            return ausente("Los niveles nominales carecen de año de referencia.")

    for fila, rol in ((numerador, "numerador"), (denominador, "denominador")):
        estado = fila.get("estado")
        if estado not in _ESTADOS_DISPONIBLES:
            if estado in _ESTADOS_AUSENTES:
                return ausente(f"El {rol} tiene estado {estado}.", estado)
            return ausente(f"El estado del {rol} es inválido.", "error")

    clase_numerador = numerador.get("clase")
    clase_denominador = denominador.get("clase")
    clases = {clase_numerador, clase_denominador}
    if not clases <= _CLASES or ("prueba" in clases and len(clases) > 1):
        return ausente("Las clases de evidencia son incompatibles.")

    valor_numerador = numerador.get("valor")
    valor_denominador = denominador.get("valor")
    if not all(isinstance(valor, str) and _DECIMAL.fullmatch(valor)
               for valor in (valor_numerador, valor_denominador)):
        return ausente("Algún nivel carece de un valor decimal válido.", "error")
    divisor = Decimal(valor_denominador)
    if not divisor:
        return ausente("El denominador es cero.")

    with localcontext(_CONTEXTO):
        dividendo = Decimal(valor_numerador)
        if es_crecimiento:
            resultado = (dividendo - divisor) * 100 / divisor
        else:
            resultado = dividendo * 100 / divisor
    estado = "preliminar" if any(
        fila.get("estado") == "preliminar" for fila in (numerador, denominador)
    ) else "informado"
    clase = "estimacion" if "estimacion" in clases else clase_numerador
    return Resultado(format(resultado, "f") if resultado else "0", None, version, insumos, estado, clase)
