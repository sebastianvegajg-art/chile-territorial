"""Indicadores territoriales de PIB per cápita, diversificación, convergencia y simulación paramétrica."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext

from analytics.territorial.pib import Observacion, Resultado

PIB_PER_CAPITA_VERSION = "pib-per-capita-v1"
DIVERSIFICACION_VERSION = "estructura-diversificacion-v1"
SIGMA_CONVERGENCIA_VERSION = "territorial-sigma-convergencia-v1"
CRECIMIENTO_REQUERIDO_VERSION = "territorial-crecimiento-requerido-v1"

_DECIMAL = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")
_REGION = re.compile(r"0[1-9]|1[0-6]")
_TERRITORIO = re.compile(r"CL|0[1-9]|1[0-6]")
_COMUNA = re.compile(r"[0-9]{5}")
_TODAS_LAS_REGIONES = tuple(f"{codigo:02d}" for codigo in range(1, 17))
_ESTADOS_DISPONIBLES = {"informado", "preliminar"}
_ESTADOS_AUSENTES = {"faltante", "suprimido", "no_aplicable", "error"}
_PRIORIDAD_AUSENTES = ("error", "suprimido", "no_aplicable", "faltante")
_CLASES = {"oficial", "estimacion", "proyeccion", "prueba"}
_CONTEXTO = Context(prec=34, rounding=ROUND_HALF_EVEN)
_CONTEXTO_ALTA_PREC = Context(prec=54, rounding=ROUND_HALF_EVEN)

_ADVERTENCIA_CRECIMIENTO_REQUERIDO = (
    "Ejercicio aritmético paramétrico de simulación hipotética: expresa únicamente la tasa "
    "compuesta requerida bajo crecimiento nacional constante y no constituye una proyección "
    "económica ni una estimación causal del efecto de inversión o políticas sobre el PIB."
)


@dataclass(frozen=True)
class ResultadoTerritorial(Resultado):
    """Extensión retrocompatible de Resultado con metadatos de valoración, unidad y advertencias."""

    unidad: str | None = None
    valoracion: str | None = None
    anio_referencia: int | None = None
    advertencia: str | None = None


def _extraer_insumos(*filas: Observacion | None) -> tuple[str, ...]:
    return tuple(
        fila["id"]
        for fila in filas
        if isinstance(fila, Mapping) and isinstance(fila.get("id"), str) and fila["id"]
    )


def _ausente(
    version: str,
    insumos: tuple[str, ...],
    motivo: str,
    estado: str = "faltante",
    *,
    unidad: str | None = None,
    valoracion: str | None = None,
    anio_referencia: int | None = None,
    advertencia: str | None = None,
) -> ResultadoTerritorial:
    return ResultadoTerritorial(
        valor=None,
        motivo=motivo,
        formula_version=version,
        insumos=insumos,
        estado=estado,
        clase="no_disponible",
        unidad=unidad,
        valoracion=valoracion,
        anio_referencia=anio_referencia,
        advertencia=advertencia,
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


def _formatear_decimal(valor: Decimal) -> str:
    if not valor:
        return "0"
    return format(valor.normalize(_CONTEXTO), "f")


def _combinar_clases(clases_entrada: tuple[object, ...]) -> tuple[str | None, str | None]:
    clases = set(clases_entrada)
    if not clases <= _CLASES or ("prueba" in clases and len(clases) > 1):
        return (None, "Las clases de evidencia son incompatibles.")
    if "proyeccion" in clases:
        return ("proyeccion", None)
    if "estimacion" in clases:
        return ("estimacion", None)
    return (next(iter(clases)), None)


def _raiz_enesima_alta_prec(valor: Decimal, n: int) -> Decimal:
    """Calcula valor**(1/n) en alta precisión Decimal (sin float) para evitar doble redondeo."""
    with localcontext(_CONTEXTO_ALTA_PREC):
        if n == 1:
            return +valor
        if valor == 1:
            return Decimal(1)
        if n == 2:
            return valor.sqrt()
        n_dec = Decimal(n)
        n_menos_1 = Decimal(n - 1)
        x = (valor.ln() / n_dec).exp()
        for _ in range(10):
            siguiente = (n_menos_1 * x + valor / (x ** (n - 1))) / n_dec
            if siguiente == x:
                break
            x = siguiente
        return x


def pib_per_capita(
    obs_pib: Observacion | None,
    obs_poblacion: Observacion | None,
) -> Resultado:
    """Calcula el PIB per cápita en CLP por habitante para nivel nacional (CL) o regional (01-16).

    Rechaza explícitamente códigos comunales (5 dígitos) para evitar imputar PIB regional a comunas.
    """
    version = PIB_PER_CAPITA_VERSION
    unidad_salida = "CLP por habitante"
    insumos = _extraer_insumos(obs_pib, obs_poblacion)

    if not isinstance(obs_pib, Mapping) or not isinstance(obs_poblacion, Mapping):
        return _ausente(
            version,
            insumos,
            "Se requieren observaciones válidas de PIB y población para calcular el PIB per cápita.",
            unidad=unidad_salida,
        )

    if len(insumos) != 2:
        return _ausente(
            version,
            insumos,
            "Las observaciones de PIB y población carecen de identificadores de procedencia.",
            unidad=unidad_salida,
        )

    pub_pib = obs_pib.get("publicacion")
    if not isinstance(pub_pib, str) or not pub_pib.strip():
        return _ausente(
            version,
            insumos,
            "La observación de PIB carece de identificador de publicación.",
            unidad=unidad_salida,
        )
    pub_pob = obs_poblacion.get("publicacion")
    if pub_pob is not None and (not isinstance(pub_pob, str) or not pub_pob.strip()):
        return _ausente(
            version,
            insumos,
            "La publicación declarada para la observación de población es inválida.",
            unidad=unidad_salida,
        )

    territorio_pib = obs_pib.get("territorio")
    territorio_pob = obs_poblacion.get("territorio")

    if isinstance(territorio_pib, str) and _COMUNA.fullmatch(territorio_pib):
        return _ausente(
            version,
            insumos,
            (
                f"Territorio comunal ({territorio_pib}) rechazado: no se debe imputar "
                "PIB regional a comunas; el PIB per cápita solo aplica a nivel nacional (CL) "
                "o regional (01-16)."
            ),
            estado="no_aplicable",
            unidad=unidad_salida,
        )

    if isinstance(territorio_pob, str) and _COMUNA.fullmatch(territorio_pob):
        return _ausente(
            version,
            insumos,
            (
                f"Territorio comunal ({territorio_pob}) en población rechazado: no se debe "
                "imputar PIB regional a comunas."
            ),
            estado="no_aplicable",
            unidad=unidad_salida,
        )

    if not isinstance(territorio_pib, str) or not _TERRITORIO.fullmatch(territorio_pib):
        return _ausente(
            version,
            insumos,
            "El PIB per cápita requiere territorio nacional (CL) o código regional CUT válido (01-16).",
            unidad=unidad_salida,
        )

    valoracion = obs_pib.get("valoracion")
    if valoracion not in {"real", "nominal"}:
        return _ausente(
            version,
            insumos,
            "La observación de PIB debe declarar valoración 'real' o 'nominal'.",
            unidad=unidad_salida,
        )

    anio_referencia = obs_pib.get("anio_referencia")
    if valoracion == "real" and type(anio_referencia) is not int:
        return _ausente(
            version,
            insumos,
            "El PIB real requiere un año de referencia entero explícito.",
            unidad=unidad_salida,
            valoracion=valoracion,
        )
    if valoracion == "nominal" and anio_referencia is not None:
        return _ausente(
            version,
            insumos,
            "El PIB nominal no debe declarar año de referencia.",
            unidad=unidad_salida,
            valoracion=valoracion,
        )

    if obs_pib.get("metrica") != "nivel":
        return _ausente(
            version,
            insumos,
            "La observación de PIB debe corresponder a metrica='nivel'.",
            unidad=unidad_salida,
            valoracion=valoracion,
            anio_referencia=anio_referencia,
        )

    if obs_pib.get("unidad") != "millones CLP":
        return _ausente(
            version,
            insumos,
            "La observación de PIB debe estar normalizada en unidad='millones CLP'.",
            unidad=unidad_salida,
            valoracion=valoracion,
            anio_referencia=anio_referencia,
        )

    if obs_poblacion.get("unidad") != "personas":
        return _ausente(
            version,
            insumos,
            "La observación de población debe estar expresada en unidad='personas'.",
            unidad=unidad_salida,
            valoracion=valoracion,
            anio_referencia=anio_referencia,
        )

    anio_pib = obs_pib.get("anio")
    anio_pob = obs_poblacion.get("anio")
    if type(anio_pib) is not int or type(anio_pob) is not int:
        return _ausente(
            version,
            insumos,
            "El período anual de PIB o población es inválido.",
            unidad=unidad_salida,
            valoracion=valoracion,
            anio_referencia=anio_referencia,
        )
    if anio_pib != anio_pob:
        return _ausente(
            version,
            insumos,
            "Las observaciones de PIB y población pertenecen a años diferentes.",
            unidad=unidad_salida,
            valoracion=valoracion,
            anio_referencia=anio_referencia,
        )

    if territorio_pob != territorio_pib:
        return _ausente(
            version,
            insumos,
            "Las observaciones de PIB y población pertenecen a territorios diferentes.",
            unidad=unidad_salida,
            valoracion=valoracion,
            anio_referencia=anio_referencia,
        )

    estados_etiquetados = ((obs_pib, "PIB"), (obs_poblacion, "población"))
    for fila, etiqueta in estados_etiquetados:
        estado_fila = fila.get("estado")
        if estado_fila not in _ESTADOS_DISPONIBLES and estado_fila not in _ESTADOS_AUSENTES:
            return _ausente(
                version,
                insumos,
                f"El estado de {etiqueta} es inválido.",
                estado="error",
                unidad=unidad_salida,
                valoracion=valoracion,
                anio_referencia=anio_referencia,
            )

    ausentes = [
        (etiqueta, fila["estado"])
        for fila, etiqueta in estados_etiquetados
        if fila.get("estado") in _ESTADOS_AUSENTES
    ]
    if ausentes:
        estados_presentes = {estado for _, estado in ausentes}
        estado_final = next(estado for estado in _PRIORIDAD_AUSENTES if estado in estados_presentes)
        detalle = ", ".join(f"{etiqueta} tiene estado {estado}" for etiqueta, estado in ausentes)
        return _ausente(
            version,
            insumos,
            f"Insumo no disponible: {detalle}.",
            estado=estado_final,
            unidad=unidad_salida,
            valoracion=valoracion,
            anio_referencia=anio_referencia,
        )

    clase, motivo_clase = _combinar_clases((obs_pib.get("clase"), obs_poblacion.get("clase")))
    if clase is None:
        return _ausente(
            version,
            insumos,
            motivo_clase or "Las clases de evidencia son incompatibles.",
            unidad=unidad_salida,
            valoracion=valoracion,
            anio_referencia=anio_referencia,
        )

    valor_pib = _parsear_decimal_estricto(obs_pib.get("valor"))
    valor_pob = _parsear_decimal_estricto(obs_poblacion.get("valor"))
    if valor_pib is None or valor_pob is None:
        return _ausente(
            version,
            insumos,
            "El PIB o la población carecen de un valor decimal válido (no se admite float).",
            estado="error",
            unidad=unidad_salida,
            valoracion=valoracion,
            anio_referencia=anio_referencia,
        )

    if valor_pib < 0:
        return _ausente(
            version,
            insumos,
            "El nivel de PIB no puede ser negativo.",
            estado="error",
            unidad=unidad_salida,
            valoracion=valoracion,
            anio_referencia=anio_referencia,
        )
    if valor_pob == 0:
        return _ausente(
            version,
            insumos,
            "La población (denominador) es cero.",
            estado="faltante",
            unidad=unidad_salida,
            valoracion=valoracion,
            anio_referencia=anio_referencia,
        )
    if valor_pob < 0:
        return _ausente(
            version,
            insumos,
            "La población (denominador) debe ser estrictamente positiva.",
            estado="error",
            unidad=unidad_salida,
            valoracion=valoracion,
            anio_referencia=anio_referencia,
        )

    with localcontext(_CONTEXTO):
        resultado = (valor_pib * Decimal(1_000_000)) / valor_pob

    estado_final = (
        "preliminar"
        if any(fila.get("estado") == "preliminar" for fila in (obs_pib, obs_poblacion))
        else "informado"
    )
    return ResultadoTerritorial(
        valor=_formatear_decimal(resultado),
        motivo=None,
        formula_version=version,
        insumos=insumos,
        estado=estado_final,
        clase=clase,
        unidad=unidad_salida,
        valoracion=valoracion,
        anio_referencia=anio_referencia,
    )


def diversificacion_economica(
    hhi_resultado: Resultado | Decimal | str | None,
) -> Resultado:
    """Calcula el índice de diversificación económica `1 - (HHI / 10000)` en `[0, 1]`."""
    version = DIVERSIFICACION_VERSION
    unidad_salida = "indice [0, 1]"

    if hhi_resultado is None:
        return _ausente(
            version,
            (),
            "Falta el valor o resultado de HHI requerido para calcular la diversificación económica.",
            estado="faltante",
            unidad=unidad_salida,
        )

    if isinstance(hhi_resultado, Resultado):
        insumos = hhi_resultado.insumos
        estado_in = hhi_resultado.estado
        if estado_in in _ESTADOS_AUSENTES:
            motivo_base = hhi_resultado.motivo or f"el HHI tiene estado {estado_in}"
            return _ausente(
                version,
                insumos,
                f"No se puede calcular diversificación económica porque {motivo_base}",
                estado=estado_in,
                unidad=unidad_salida,
            )
        if estado_in not in _ESTADOS_DISPONIBLES:
            return _ausente(
                version,
                insumos,
                "El resultado de HHI tiene un estado inválido.",
                estado="error",
                unidad=unidad_salida,
            )
        if hhi_resultado.valor is None:
            return _ausente(
                version,
                insumos,
                hhi_resultado.motivo or "El resultado de HHI no contiene valor.",
                estado="faltante",
                unidad=unidad_salida,
            )
        clase = hhi_resultado.clase
        if clase not in _CLASES:
            return _ausente(
                version,
                insumos,
                "El resultado de HHI tiene una clase de evidencia inválida.",
                estado="error",
                unidad=unidad_salida,
            )
        hhi_dec = _parsear_decimal_estricto(hhi_resultado.valor)
        if hhi_dec is None:
            return _ausente(
                version,
                insumos,
                "El valor de HHI no es un decimal válido.",
                estado="error",
                unidad=unidad_salida,
            )
        estado_salida = estado_in
    else:
        insumos = ()
        hhi_dec = _parsear_decimal_estricto(hhi_resultado)
        if hhi_dec is None:
            return _ausente(
                version,
                insumos,
                "El valor de HHI debe ser Resultado, Decimal o cadena decimal válida (no float).",
                estado="error",
                unidad=unidad_salida,
            )
        estado_salida = "informado"
        clase = "estimacion"

    if hhi_dec < 0 or hhi_dec > Decimal(10000):
        return _ausente(
            version,
            insumos,
            "El valor de HHI está fuera del rango válido [0, 10000].",
            estado="error",
            unidad=unidad_salida,
        )

    with localcontext(_CONTEXTO):
        diversificacion = Decimal(1) - (hhi_dec / Decimal(10000))

    return ResultadoTerritorial(
        valor=_formatear_decimal(diversificacion),
        motivo=None,
        formula_version=version,
        insumos=insumos,
        estado=estado_salida,
        clase=clase,
        unidad=unidad_salida,
    )


def sigma_convergencia(
    valores_por_region: Mapping[str, str | Decimal | None] | None,
) -> Resultado:
    """Calcula el coeficiente de variación poblacional (`desv_est / media`) entre regiones.

    Usa exclusivamente aritmética Decimal (`Decimal.sqrt()`) sobre las regiones válidas con
    valor positivo (`>= 2` regiones), advirtiendo si la cobertura es inferior a 16 regiones.
    """
    version = SIGMA_CONVERGENCIA_VERSION
    unidad_salida = "coeficiente_variacion"

    if not isinstance(valores_por_region, Mapping) or not valores_por_region:
        return _ausente(
            version,
            (),
            "Se requiere un mapeo no vacío de valores regionales (01-16) para sigma-convergencia.",
            estado="faltante",
            unidad=unidad_salida,
        )

    validas: dict[str, Decimal] = {}
    ausentes_o_no_positivas: list[str] = []

    for codigo in sorted(valores_por_region):
        if not isinstance(codigo, str) or not _REGION.fullmatch(codigo):
            return _ausente(
                version,
                tuple(sorted(validas)),
                f"Código territorial inválido para sigma-convergencia regional: {codigo!r}. Se exigen códigos CUT regionales 01-16.",
                estado="error",
                unidad=unidad_salida,
            )
        raw = valores_por_region[codigo]
        if raw is None:
            ausentes_o_no_positivas.append(f"{codigo} (faltante)")
            continue
        valor = _parsear_decimal_estricto(raw)
        if valor is None:
            return _ausente(
                version,
                tuple(sorted(validas)),
                f"Valor decimal inválido para la región {codigo} (no se admite float ni formatos no decimales).",
                estado="error",
                unidad=unidad_salida,
            )
        if valor <= 0:
            ausentes_o_no_positivas.append(f"{codigo} (no positivo)")
            continue
        validas[codigo] = valor

    insumos = tuple(sorted(validas))
    if len(validas) < 2:
        return _ausente(
            version,
            insumos,
            f"Se requieren al menos 2 regiones con valor positivo para sigma-convergencia (válidas: {len(validas)}).",
            estado="faltante",
            unidad=unidad_salida,
        )

    no_provistas = [codigo for codigo in _TODAS_LAS_REGIONES if codigo not in valores_por_region]
    faltantes_detalle = [*ausentes_o_no_positivas, *(f"{c} (no provista)" for c in no_provistas)]

    if len(validas) < 16:
        advertencia = (
            f"Cobertura regional incompleta: {len(validas)} de 16 regiones válidas "
            f"(faltan o excluidas: {', '.join(faltantes_detalle)}). "
            "Indicador descriptivo de dispersión territorial; no permite inferencia causal."
        )
    else:
        advertencia = (
            "Cobertura regional completa (16 de 16 regiones). "
            "Indicador descriptivo de dispersión territorial; no permite inferencia causal."
        )

    with localcontext(_CONTEXTO):
        n = Decimal(len(validas))
        valores_ordenados = [validas[codigo] for codigo in insumos]
        media = sum(valores_ordenados, Decimal(0)) / n
        varianza = sum(((v - media) * (v - media) for v in valores_ordenados), Decimal(0)) / n
        desv_est = varianza.sqrt()
        cv = desv_est / media

    return ResultadoTerritorial(
        valor=_formatear_decimal(cv),
        motivo=None,
        formula_version=version,
        insumos=insumos,
        estado="informado",
        clase="estimacion",
        unidad=unidad_salida,
        advertencia=advertencia,
    )


def crecimiento_requerido_participacion(
    pib_regional: str | Decimal,
    pib_nacional: str | Decimal,
    crecimiento_nacional_pct: str | Decimal,
    participacion_objetivo_pct: str | Decimal,
    horizonte_anios: int,
) -> dict[str, object]:
    """Simulación aritmética hipotética (Cruce 2) de crecimiento regional requerido.

    Calcula la tasa anual compuesta regional necesaria para llevar la participación nominal
    regional desde su nivel actual hasta `participacion_objetivo_pct` en `horizonte_anios`
    años bajo un supuesto de crecimiento nacional constante `crecimiento_nacional_pct`.
    """

    def invalido(
        motivo: str,
        estado: str = "error",
        *,
        participacion_actual: str | None = None,
        participacion_objetivo: str | None = None,
        crecimiento_nacional: str | None = None,
        horizonte: int | None = None,
    ) -> dict[str, object]:
        return {
            "formula_version": CRECIMIENTO_REQUERIDO_VERSION,
            "clase": "simulacion_hipotetica",
            "estado": estado,
            "motivo": motivo,
            "tasa_anual_regional_requerida_pct": None,
            "brecha_crecimiento_pp": None,
            "participacion_actual_pct": participacion_actual,
            "participacion_objetivo_pct": participacion_objetivo,
            "crecimiento_nacional_pct": crecimiento_nacional,
            "horizonte_anios": horizonte,
            "insumos": {
                "pib_regional": None if pib_regional is None else str(pib_regional),
                "pib_nacional": None if pib_nacional is None else str(pib_nacional),
                "crecimiento_nacional_pct": (
                    None if crecimiento_nacional_pct is None else str(crecimiento_nacional_pct)
                ),
                "participacion_objetivo_pct": (
                    None if participacion_objetivo_pct is None else str(participacion_objetivo_pct)
                ),
                "horizonte_anios": horizonte_anios,
            },
            "advertencia_metodologica": _ADVERTENCIA_CRECIMIENTO_REQUERIDO,
        }

    if type(horizonte_anios) is not int or horizonte_anios < 1:
        return invalido("El horizonte debe ser un entero estrictamente positivo (>= 1 año).")

    reg = _parsear_decimal_estricto(pib_regional)
    nac = _parsear_decimal_estricto(pib_nacional)
    crec_nac = _parsear_decimal_estricto(crecimiento_nacional_pct)
    part_obj = _parsear_decimal_estricto(participacion_objetivo_pct)

    if any(x is None for x in (reg, nac, crec_nac, part_obj)):
        return invalido(
            "Todos los parámetros numéricos deben ser Decimal o cadena decimal válida (no float).",
            horizonte=horizonte_anios,
        )

    if nac == 0:
        return invalido(
            "El PIB nacional (denominador) es cero.",
            estado="faltante",
            participacion_objetivo=_formatear_decimal(part_obj),
            crecimiento_nacional=_formatear_decimal(crec_nac),
            horizonte=horizonte_anios,
        )
    if reg <= 0 or nac < 0:
        return invalido(
            "El PIB regional y el PIB nacional deben ser estrictamente positivos.",
            participacion_objetivo=_formatear_decimal(part_obj),
            crecimiento_nacional=_formatear_decimal(crec_nac),
            horizonte=horizonte_anios,
        )
    if reg > nac:
        return invalido(
            "El PIB regional nominal no puede superar al PIB nacional nominal.",
            participacion_objetivo=_formatear_decimal(part_obj),
            crecimiento_nacional=_formatear_decimal(crec_nac),
            horizonte=horizonte_anios,
        )

    with localcontext(_CONTEXTO):
        participacion_actual = (reg * Decimal(100)) / nac

    if part_obj <= 0 or part_obj > Decimal(100):
        return invalido(
            "La participación objetivo porcentual debe estar en el intervalo (0, 100].",
            participacion_actual=_formatear_decimal(participacion_actual),
            participacion_objetivo=_formatear_decimal(part_obj),
            crecimiento_nacional=_formatear_decimal(crec_nac),
            horizonte=horizonte_anios,
        )

    if crec_nac <= Decimal(-100):
        return invalido(
            "El crecimiento nacional anual porcentual debe ser estrictamente mayor a -100%.",
            participacion_actual=_formatear_decimal(participacion_actual),
            participacion_objetivo=_formatear_decimal(part_obj),
            crecimiento_nacional=_formatear_decimal(crec_nac),
            horizonte=horizonte_anios,
        )

    with localcontext(_CONTEXTO_ALTA_PREC):
        razon_participacion = (part_obj * nac) / (Decimal(100) * reg)
        factor_crecimiento_relativo = _raiz_enesima_alta_prec(razon_participacion, horizonte_anios)
        factor_nacional = Decimal(1) + (crec_nac / Decimal(100))
        tasa_alta = (factor_nacional * factor_crecimiento_relativo - Decimal(1)) * Decimal(100)
        brecha_alta = tasa_alta - crec_nac

    with localcontext(_CONTEXTO):
        tasa_regional_pct = +tasa_alta
        brecha_pp = +brecha_alta

    return {
        "formula_version": CRECIMIENTO_REQUERIDO_VERSION,
        "clase": "simulacion_hipotetica",
        "estado": "informado",
        "motivo": None,
        "tasa_anual_regional_requerida_pct": _formatear_decimal(tasa_regional_pct),
        "brecha_crecimiento_pp": _formatear_decimal(brecha_pp),
        "participacion_actual_pct": _formatear_decimal(participacion_actual),
        "participacion_objetivo_pct": _formatear_decimal(part_obj),
        "crecimiento_nacional_pct": _formatear_decimal(crec_nac),
        "horizonte_anios": horizonte_anios,
        "insumos": {
            "pib_regional": _formatear_decimal(reg),
            "pib_nacional": _formatear_decimal(nac),
            "crecimiento_nacional_pct": _formatear_decimal(crec_nac),
            "participacion_objetivo_pct": _formatear_decimal(part_obj),
            "horizonte_anios": horizonte_anios,
        },
        "advertencia_metodologica": _ADVERTENCIA_CRECIMIENTO_REQUERIDO,
    }
