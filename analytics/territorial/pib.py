"""Indicadores anuales a partir de niveles normalizados del PIB."""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext

Observacion = Mapping[str, object]

CRECIMIENTO_VERSION = "pib-crecimiento-v1"
PARTICIPACION_VERSION = "pib-participacion-v1"
ACUMULADO_VERSION = "pib-crecimiento-acumulado-v1"
INDICE_VERSION = "pib-indice-historico-v1"
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


def crecimiento_acumulado(
    real_actual: Observacion | None, real_base: Observacion | None
) -> Resultado:
    """Calcula la variación real respecto de un año base de análisis explícito."""
    return _calcular(real_actual, real_base, ACUMULADO_VERSION)


def indice_historico(
    real_actual: Observacion | None, real_base: Observacion | None
) -> Resultado:
    """Expresa un nivel real en relación con otro del mismo territorio, con base 100."""
    return _calcular(real_actual, real_base, INDICE_VERSION)


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

    es_real = version != PARTICIPACION_VERSION
    valoracion = "real" if es_real else "nominal"
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
    if es_real:
        if territorio != denominador.get("territorio"):
            return ausente("Los niveles reales requieren el mismo territorio.")
        if version == CRECIMIENTO_VERSION and anio != anio_base + 1:
            return ausente("El crecimiento anual requiere años consecutivos.")
        if anio < anio_base:
            return ausente("El año base de análisis debe ser igual o anterior al año consultado.")
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
        if version in (CRECIMIENTO_VERSION, ACUMULADO_VERSION):
            resultado = (dividendo - divisor) * 100 / divisor
        else:
            resultado = dividendo * 100 / divisor
    estado = "preliminar" if any(
        fila.get("estado") == "preliminar" for fila in (numerador, denominador)
    ) else "informado"
    clase = "estimacion" if "estimacion" in clases else clase_numerador
    return Resultado(format(resultado, "f") if resultado else "0", None, version, insumos, estado, clase)



@dataclass(frozen=True)
class PosicionRegional:
    posicion: int
    territorio: str
    observacion_id: str
    valor: str


def ranking_regional(filas: Iterable[Observacion]) -> tuple[PosicionRegional, ...]:
    """Ordena observaciones regionales comparables; los empates comparten posición."""
    dimensiones = (
        "publicacion", "anio", "metrica", "valoracion", "unidad", "anio_referencia",
        "anio_base", "clase",
    )
    referencial = None
    territorios = set()
    candidatas = []
    for fila in filas:
        territorio = fila.get("territorio")
        if territorio == "CL":
            continue
        if not isinstance(territorio, str) or not _REGION.fullmatch(territorio):
            raise ValueError("El ranking requiere códigos regionales válidos.")
        if territorio in territorios:
            raise ValueError(f"Hay observaciones duplicadas para la región {territorio}.")
        territorios.add(territorio)

        estado = fila.get("estado")
        if estado in _ESTADOS_AUSENTES:
            continue
        if estado not in _ESTADOS_DISPONIBLES:
            raise ValueError(f"Estado inválido para la región {territorio}.")
        identificador = fila.get("id")
        valor = fila.get("valor")
        if not isinstance(identificador, str) or not identificador:
            raise ValueError(f"Falta el identificador de la observación para la región {territorio}.")
        if not isinstance(valor, str) or not _DECIMAL.fullmatch(valor):
            raise ValueError(f"Valor decimal inválido para la región {territorio}.")
        firma = tuple(fila.get(dimension) for dimension in dimensiones)
        publicacion, anio, metrica, valoracion, unidad, referencia, base, clase = firma
        reales = {"nivel", "crecimiento", "crecimiento_acumulado", "indice_historico"}
        nominales = {"nivel", "participacion"}
        if (
            not isinstance(publicacion, str) or not publicacion
            or type(anio) is not int
            or clase not in _CLASES
            or not isinstance(unidad, str) or not unidad
            or (valoracion == "real" and (metrica not in reales or type(referencia) is not int))
            or (valoracion == "nominal" and (metrica not in nominales or referencia is not None))
            or valoracion not in {"real", "nominal"}
            or (metrica in {"crecimiento_acumulado", "indice_historico"}
                and (type(base) is not int or base > anio))
        ):
            raise ValueError(f"Dimensiones inválidas para la región {territorio}.")
        if referencial is None:
            referencial = firma
        if firma != referencial:
            raise ValueError("El ranking requiere observaciones comparables en todas sus dimensiones.")
        candidatas.append((Decimal(valor), territorio, identificador, valor))

    candidatas.sort(key=lambda candidata: candidata[1])
    candidatas.sort(key=lambda candidata: candidata[0], reverse=True)

    resultado = []
    valor_anterior = None
    posicion = 0
    for orden, (valor_decimal, territorio, identificador, valor) in enumerate(candidatas, start=1):
        if valor_decimal != valor_anterior:
            posicion = orden
        resultado.append(PosicionRegional(posicion, territorio, identificador, valor))
        valor_anterior = valor_decimal
    return tuple(resultado)
