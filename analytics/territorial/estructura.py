"""Indicadores de estructura productiva, concentración y especialización económica."""

import re
from collections.abc import Iterable, Mapping, Sequence
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext

from analytics.territorial.pib import Observacion, Resultado

PARTICIPACION_SECTORIAL_VERSION = "estructura-participacion-v1"
ESPECIALIZACION_VERSION = "estructura-especializacion-v1"
HHI_VERSION = "estructura-hhi-v1"
KRUGMAN_VERSION = "estructura-krugman-v1"

_DECIMAL = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")
_REGION = re.compile(r"0[1-9]|1[0-6]")
_TERRITORIO = re.compile(r"CL|0[1-9]|1[0-6]")
_ESTADOS_DISPONIBLES = {"informado", "preliminar"}
_ESTADOS_AUSENTES = {"faltante", "suprimido", "no_aplicable", "error"}
_PRIORIDAD_AUSENTES = ("error", "suprimido", "no_aplicable", "faltante")
_CLASES = {"oficial", "estimacion", "prueba"}
_METRICAS_NIVEL = {"nivel", "valor_agregado"}
_METRICAS_PARTICIPACION = {"participacion_sectorial", "participacion"}
_UNIDADES_PARTICIPACION = {"porcentaje", "%"}
_TOLERANCIA_SUMA_PARTICIPACIONES = Decimal("0.0001")
_CONTEXTO = Context(prec=34, rounding=ROUND_HALF_EVEN)


def _extraer_insumos(filas: Sequence[Observacion | None]) -> tuple[str, ...]:
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
) -> Resultado:
    return Resultado(None, motivo, version, insumos, estado, "no_disponible")


def _actividad_valida(fila: Observacion) -> str | None:
    actividad = fila.get("actividad")
    if not isinstance(actividad, str):
        return None
    limpia = actividad.strip()
    if not limpia or limpia.lower() == "total":
        return None
    return limpia


def _es_total_valido(fila: Observacion) -> bool:
    actividad = fila.get("actividad")
    if actividad is None:
        return True
    if not isinstance(actividad, str):
        return False
    limpia = actividad.strip()
    return limpia == "" or limpia.lower() == "total"


def _validar_nominal_y_procedencia(
    filas: Sequence[Observacion],
    *,
    permitir_participaciones: bool = False,
) -> tuple[str, str] | None:
    """Valida publicación, valoración nominal, métrica, unidad, año y perímetro común.

    Retorna (estado, motivo) si hay incumplimiento, o None si todo es válido.
    """
    for fila in filas:
        identificador = fila.get("id")
        publicacion = fila.get("publicacion")
        if not isinstance(identificador, str) or not identificador or not isinstance(publicacion, str) or not publicacion:
            return ("faltante", "Las observaciones carecen de identificadores de procedencia.")

    publicaciones = {fila["publicacion"] for fila in filas}
    if len(publicaciones) != 1:
        return ("faltante", "Las observaciones pertenecen a publicaciones diferentes.")

    valoraciones = {fila.get("valoracion") for fila in filas}
    if "real" in valoraciones:
        return (
            "faltante",
            "Los indicadores de estructura requieren valoración nominal; los volúmenes reales encadenados no son aditivos.",
        )
    if valoraciones != {"nominal"}:
        return ("faltante", "La valoración de las observaciones es incompatible; se requiere valoración nominal.")

    if any(fila.get("anio_referencia") is not None for fila in filas):
        return ("faltante", "Los niveles nominales carecen de año de referencia.")

    metricas = {fila.get("metrica") for fila in filas}
    if len(metricas) != 1:
        return ("faltante", "Las observaciones mezclan métricas incompatibles.")
    metrica = next(iter(metricas))

    unidades = {fila.get("unidad") for fila in filas}
    if metrica in _METRICAS_NIVEL:
        if unidades != {"millones CLP"}:
            return ("faltante", "Las unidades difieren o no están normalizadas a millones de CLP.")
    elif permitir_participaciones and metrica in _METRICAS_PARTICIPACION:
        if len(unidades) != 1 or not (unidades <= _UNIDADES_PARTICIPACION):
            return ("faltante", "Las participaciones sectoriales requieren unidad porcentual homogénea.")
    else:
        return ("faltante", "La métrica de las observaciones es incompatible.")

    anios = [fila.get("anio") for fila in filas]
    if any(type(anio) is not int for anio in anios):
        return ("faltante", "El período anual de las observaciones es inválido.")
    if len(set(anios)) != 1:
        return ("faltante", "Las observaciones pertenecen a años diferentes.")

    perimetros = {fila.get("perimetro") for fila in filas}
    if len(perimetros) != 1:
        return ("faltante", "Las observaciones pertenecen a perímetros de valor agregado diferentes.")

    return None


def _validar_estados(
    filas_etiquetadas: Sequence[tuple[Observacion, str]],
    *,
    reportar_cobertura: bool = False,
    unidad_conteo: str = "actividades",
) -> tuple[str, str] | None:
    """Verifica disponibilidad de estados; conserva causa y cobertura en ausencias."""
    for fila, etiqueta in filas_etiquetadas:
        estado = fila.get("estado")
        if estado not in _ESTADOS_DISPONIBLES and estado not in _ESTADOS_AUSENTES:
            return ("error", f"El estado de {etiqueta} es inválido.")

    ausentes = [
        (etiqueta, fila["estado"])
        for fila, etiqueta in filas_etiquetadas
        if fila.get("estado") in _ESTADOS_AUSENTES
    ]
    if not ausentes:
        return None

    estados_presentes = {estado for _, estado in ausentes}
    estado_final = next(estado for estado in _PRIORIDAD_AUSENTES if estado in estados_presentes)
    if reportar_cobertura:
        total = len(filas_etiquetadas)
        disponibles = total - len(ausentes)
        detalle = ", ".join(f"{etiqueta} ({estado})" for etiqueta, estado in ausentes)
        return (
            estado_final,
            f"Cobertura sectorial incompleta ({disponibles} de {total} {unidad_conteo} disponibles): {detalle}.",
        )
    detalle = ", ".join(f"{etiqueta} tiene estado {estado}" for etiqueta, estado in ausentes)
    return (estado_final, f"Insumo no disponible: {detalle}.")


def _validar_clases(filas: Sequence[Observacion]) -> tuple[str | None, str | None]:
    """Valida compatibilidad de clases de evidencia. Retorna (clase_final, motivo_error)."""
    clases = {fila.get("clase") for fila in filas}
    if not clases <= _CLASES or ("prueba" in clases and len(clases) > 1):
        return (None, "Las clases de evidencia son incompatibles.")
    if "estimacion" in clases:
        return ("estimacion", None)
    return (next(iter(clases)), None)


def _estado_disponible_final(filas: Sequence[Observacion]) -> str:
    return "preliminar" if any(fila.get("estado") == "preliminar" for fila in filas) else "informado"


def _parsear_decimal(fila: Observacion) -> Decimal | None:
    valor = fila.get("valor")
    if not isinstance(valor, str) or not _DECIMAL.fullmatch(valor):
        return None
    return Decimal(valor)


def _formatear_decimal(valor: Decimal) -> str:
    return format(valor, "f") if valor else "0"


def participacion_sectorial(
    va_actividad: Observacion | None,
    va_total: Observacion | None,
) -> Resultado:
    """Calcula la participación porcentual de una actividad en el VA regional o nacional."""
    version = PARTICIPACION_SECTORIAL_VERSION
    insumos = _extraer_insumos((va_actividad, va_total))

    if va_actividad is None or va_total is None:
        return _ausente(version, insumos, "Falta una observación de valor agregado requerida para el cálculo.")

    filas = (va_actividad, va_total)
    falla = _validar_nominal_y_procedencia(filas)
    if falla is not None:
        return _ausente(version, insumos, falla[1], falla[0])

    territorio_act = va_actividad.get("territorio")
    territorio_tot = va_total.get("territorio")
    if (
        not isinstance(territorio_act, str)
        or not _TERRITORIO.fullmatch(territorio_act)
        or territorio_act != territorio_tot
    ):
        return _ausente(
            version,
            insumos,
            "La participación sectorial requiere el mismo territorio válido (región CUT o CL).",
        )

    actividad = _actividad_valida(va_actividad)
    if actividad is None:
        return _ausente(version, insumos, "La observación sectorial carece de un identificador de actividad válido.")
    if not _es_total_valido(va_total):
        return _ausente(version, insumos, "El denominador debe corresponder al valor agregado total del territorio.")

    clasificacion = va_actividad.get("clasificacion")
    if not isinstance(clasificacion, str) or not clasificacion.strip():
        return _ausente(version, insumos, "Falta la clasificación sectorial de la actividad.")
    clasificacion_tot = va_total.get("clasificacion")
    if clasificacion_tot is not None and clasificacion_tot != clasificacion:
        return _ausente(version, insumos, "La actividad y el total pertenecen a clasificaciones diferentes.")

    falla_estado = _validar_estados(((va_actividad, "va_actividad"), (va_total, "va_total")))
    if falla_estado is not None:
        return _ausente(version, insumos, falla_estado[1], falla_estado[0])

    clase, motivo_clase = _validar_clases(filas)
    if clase is None:
        return _ausente(version, insumos, motivo_clase or "Las clases de evidencia son incompatibles.")

    valor_act = _parsear_decimal(va_actividad)
    valor_tot = _parsear_decimal(va_total)
    if valor_act is None or valor_tot is None:
        return _ausente(version, insumos, "Alguna observación carece de un valor decimal válido.", "error")

    if valor_tot == 0:
        return _ausente(version, insumos, "El denominador (valor agregado total) es cero.")
    if valor_tot < 0:
        return _ausente(version, insumos, "El denominador (valor agregado total) debe ser positivo.")

    with localcontext(_CONTEXTO):
        resultado = valor_act * Decimal(100) / valor_tot

    return Resultado(
        _formatear_decimal(resultado),
        None,
        version,
        insumos,
        _estado_disponible_final(filas),
        clase,
    )


def especializacion(
    va_reg_act: Observacion | None,
    va_reg_total: Observacion | None,
    va_nac_act: Observacion | None,
    va_nac_total: Observacion | None,
) -> Resultado:
    """Calcula el Coeficiente de Localización (LQ) de una actividad regional frente a Chile."""
    version = ESPECIALIZACION_VERSION
    entradas = (va_reg_act, va_reg_total, va_nac_act, va_nac_total)
    insumos = _extraer_insumos(entradas)

    if any(fila is None for fila in entradas):
        return _ausente(version, insumos, "Falta una observación de valor agregado requerida para calcular el LQ.")

    filas = (va_reg_act, va_reg_total, va_nac_act, va_nac_total)
    falla = _validar_nominal_y_procedencia(filas)
    if falla is not None:
        return _ausente(version, insumos, falla[1], falla[0])

    territorio_reg = va_reg_act.get("territorio")
    if (
        not isinstance(territorio_reg, str)
        or not _REGION.fullmatch(territorio_reg)
        or va_reg_total.get("territorio") != territorio_reg
    ):
        return _ausente(
            version,
            insumos,
            "La especialización requiere dos observaciones regionales válidas de la misma región.",
        )
    if va_nac_act.get("territorio") != "CL" or va_nac_total.get("territorio") != "CL":
        return _ausente(
            version,
            insumos,
            "La especialización requiere observaciones nacionales (CL) como referencia.",
        )

    actividad_reg = _actividad_valida(va_reg_act)
    actividad_nac = _actividad_valida(va_nac_act)
    if actividad_reg is None or actividad_nac is None:
        return _ausente(version, insumos, "Las observaciones sectoriales requieren un identificador de actividad válido.")
    if actividad_reg != actividad_nac:
        return _ausente(version, insumos, "La actividad regional y la actividad nacional no coinciden.")
    if not _es_total_valido(va_reg_total) or not _es_total_valido(va_nac_total):
        return _ausente(version, insumos, "Los totales regional y nacional no deben corresponder a una actividad parcial.")

    clasificacion_reg = va_reg_act.get("clasificacion")
    clasificacion_nac = va_nac_act.get("clasificacion")
    if (
        not isinstance(clasificacion_reg, str)
        or not clasificacion_reg.strip()
        or clasificacion_reg != clasificacion_nac
    ):
        return _ausente(version, insumos, "La especialización exige la misma clasificación sectorial.")
    clas_tot_reg = va_reg_total.get("clasificacion")
    clas_tot_nac = va_nac_total.get("clasificacion")
    if clas_tot_reg != clas_tot_nac or (clas_tot_reg is not None and clas_tot_reg != clasificacion_reg):
        return _ausente(version, insumos, "Los totales pertenecen a una clasificación incompatible con la actividad.")

    falla_estado = _validar_estados(
        (
            (va_reg_act, "va_reg_act"),
            (va_reg_total, "va_reg_total"),
            (va_nac_act, "va_nac_act"),
            (va_nac_total, "va_nac_total"),
        )
    )
    if falla_estado is not None:
        return _ausente(version, insumos, falla_estado[1], falla_estado[0])

    clase, motivo_clase = _validar_clases(filas)
    if clase is None:
        return _ausente(version, insumos, motivo_clase or "Las clases de evidencia son incompatibles.")

    valores = tuple(_parsear_decimal(fila) for fila in filas)
    if any(valor is None for valor in valores):
        return _ausente(version, insumos, "Alguna observación carece de un valor decimal válido.", "error")

    reg_act, reg_tot, nac_act, nac_tot = valores
    if reg_tot == 0 or nac_tot == 0 or nac_act == 0:
        return _ausente(
            version,
            insumos,
            "Un denominador requerido para el coeficiente de localización es cero.",
        )
    if reg_tot < 0 or nac_tot < 0 or nac_act < 0:
        return _ausente(
            version,
            insumos,
            "Los denominadores del coeficiente de localización deben ser positivos.",
        )
    if reg_act < 0:
        return _ausente(
            version,
            insumos,
            "El valor agregado regional de la actividad no puede ser negativo para el coeficiente de localización.",
        )

    with localcontext(_CONTEXTO):
        resultado = (reg_act * nac_tot) / (reg_tot * nac_act)

    return Resultado(
        _formatear_decimal(resultado),
        None,
        version,
        insumos,
        _estado_disponible_final(filas),
        clase,
    )


def concentracion_hhi(
    participaciones_o_niveles_sectoriales: Iterable[Observacion] | None,
) -> Resultado:
    """Calcula el Índice de Herfindahl-Hirschman (HHI) en escala estándar 0 a 10.000.

    Acepta niveles nominales sectoriales (`millones CLP`) o participaciones sectoriales
    porcentuales (`0..100`) de un mismo territorio, año, publicación y clasificación.
    """
    version = HHI_VERSION
    if participaciones_o_niveles_sectoriales is None:
        return _ausente(version, (), "No se proporcionaron observaciones sectoriales para calcular el HHI.")

    entradas = tuple(participaciones_o_niveles_sectoriales)
    insumos = _extraer_insumos(entradas)
    if not entradas:
        return _ausente(version, insumos, "No se proporcionaron observaciones sectoriales para calcular el HHI.")
    if any(not isinstance(fila, Mapping) for fila in entradas):
        return _ausente(version, insumos, "Se recibió una observación sectorial vacía o inválida.", "error")

    falla = _validar_nominal_y_procedencia(entradas, permitir_participaciones=True)
    if falla is not None:
        return _ausente(version, insumos, falla[1], falla[0])

    territorios = {fila.get("territorio") for fila in entradas}
    territorio = next(iter(territorios))
    if len(territorios) != 1 or not isinstance(territorio, str) or not _TERRITORIO.fullmatch(territorio):
        return _ausente(version, insumos, "El HHI requiere observaciones sectoriales de un único territorio válido.")

    clasificaciones = {fila.get("clasificacion") for fila in entradas}
    clasificacion = next(iter(clasificaciones))
    if len(clasificaciones) != 1 or not isinstance(clasificacion, str) or not clasificacion.strip():
        return _ausente(version, insumos, "El HHI requiere una clasificación sectorial común y explícita.")

    actividades_vistas: set[str] = set()
    filas_etiquetadas: list[tuple[Observacion, str]] = []
    for fila in entradas:
        actividad = _actividad_valida(fila)
        if actividad is None:
            return _ausente(
                version,
                insumos,
                "Cada componente sectorial del HHI requiere una actividad válida distinta del total.",
                "error",
            )
        if actividad in actividades_vistas:
            return _ausente(
                version,
                insumos,
                f"Actividad duplicada en la estructura sectorial: {actividad}.",
                "error",
            )
        actividades_vistas.add(actividad)
        filas_etiquetadas.append((fila, actividad))

    falla_estado = _validar_estados(filas_etiquetadas, reportar_cobertura=True)
    if falla_estado is not None:
        return _ausente(version, insumos, falla_estado[1], falla_estado[0])

    clase, motivo_clase = _validar_clases(entradas)
    if clase is None:
        return _ausente(version, insumos, motivo_clase or "Las clases de evidencia son incompatibles.")

    valores: list[Decimal] = []
    for fila in entradas:
        valor = _parsear_decimal(fila)
        if valor is None:
            return _ausente(version, insumos, "Alguna observación carece de un valor decimal válido.", "error")
        if valor < 0:
            return _ausente(
                version,
                insumos,
                "El índice HHI requiere valores sectoriales no negativos.",
            )
        valores.append(valor)

    metrica = entradas[0]["metrica"]
    with localcontext(_CONTEXTO):
        if metrica in _METRICAS_NIVEL:
            total = sum(valores, Decimal(0))
            if total == 0:
                return _ausente(version, insumos, "El denominador (suma sectorial de valor agregado) es cero.")
            suma_cuadrados = sum((valor * valor for valor in valores), Decimal(0))
            resultado = Decimal(10000) * suma_cuadrados / (total * total)
        else:
            suma_participaciones = sum(valores, Decimal(0))
            if suma_participaciones == 0:
                return _ausente(version, insumos, "La suma de participaciones sectoriales es cero.")
            if abs(suma_participaciones - Decimal(100)) > _TOLERANCIA_SUMA_PARTICIPACIONES:
                return _ausente(
                    version,
                    insumos,
                    f"Las participaciones sectoriales no concilian con 100% (suma: {_formatear_decimal(suma_participaciones)}%).",
                )
            resultado = sum((valor * valor for valor in valores), Decimal(0))

    return Resultado(
        _formatear_decimal(resultado),
        None,
        version,
        insumos,
        _estado_disponible_final(entradas),
        clase,
    )


def indice_krugman(
    niveles_regionales: Iterable[Observacion] | None,
    niveles_nacionales: Iterable[Observacion] | None,
) -> Resultado:
    """Calcula el Índice de Especialización de Krugman `0.5 * sum(|s_ir - s_in|)` en `[0, 1]`."""
    version = KRUGMAN_VERSION
    if niveles_regionales is None or niveles_nacionales is None:
        parciales = tuple(niveles_regionales or ()) + tuple(niveles_nacionales or ())
        return _ausente(
            version,
            _extraer_insumos(parciales),
            "Se requieren niveles sectoriales regionales y nacionales para calcular el índice de Krugman.",
        )

    regionales = tuple(niveles_regionales)
    nacionales = tuple(niveles_nacionales)
    todas = regionales + nacionales
    insumos = _extraer_insumos(todas)

    if not regionales or not nacionales:
        return _ausente(
            version,
            insumos,
            "Se requieren observaciones sectoriales regionales y nacionales no vacías.",
        )
    if any(not isinstance(fila, Mapping) for fila in todas):
        return _ausente(version, insumos, "Se recibió una observación sectorial vacía o inválida.", "error")

    falla = _validar_nominal_y_procedencia(todas)
    if falla is not None:
        return _ausente(version, insumos, falla[1], falla[0])

    territorios_reg = {fila.get("territorio") for fila in regionales}
    territorio_reg = next(iter(territorios_reg))
    if len(territorios_reg) != 1 or not isinstance(territorio_reg, str) or not _REGION.fullmatch(territorio_reg):
        return _ausente(
            version,
            insumos,
            "El índice de Krugman requiere niveles sectoriales de una única región CUT válida.",
        )

    territorios_nac = {fila.get("territorio") for fila in nacionales}
    if territorios_nac != {"CL"}:
        return _ausente(
            version,
            insumos,
            "El índice de Krugman requiere niveles sectoriales nacionales (CL) como referencia.",
        )

    clasificaciones = {fila.get("clasificacion") for fila in todas}
    clasificacion = next(iter(clasificaciones))
    if len(clasificaciones) != 1 or not isinstance(clasificacion, str) or not clasificacion.strip():
        return _ausente(
            version,
            insumos,
            "El índice de Krugman exige la misma clasificación sectorial en la región y en el país.",
        )

    mapa_reg: dict[str, Observacion] = {}
    etiquetadas: list[tuple[Observacion, str]] = []
    for fila in regionales:
        actividad = _actividad_valida(fila)
        if actividad is None:
            return _ausente(
                version,
                insumos,
                "Cada observación sectorial regional requiere una actividad válida distinta del total.",
                "error",
            )
        if actividad in mapa_reg:
            return _ausente(
                version,
                insumos,
                f"Actividad duplicada en la estructura regional: {actividad}.",
                "error",
            )
        mapa_reg[actividad] = fila
        etiquetadas.append((fila, f"regional:{actividad}"))

    mapa_nac: dict[str, Observacion] = {}
    for fila in nacionales:
        actividad = _actividad_valida(fila)
        if actividad is None:
            return _ausente(
                version,
                insumos,
                "Cada observación sectorial nacional requiere una actividad válida distinta del total.",
                "error",
            )
        if actividad in mapa_nac:
            return _ausente(
                version,
                insumos,
                f"Actividad duplicada en la estructura nacional: {actividad}.",
                "error",
            )
        mapa_nac[actividad] = fila
        etiquetadas.append((fila, f"nacional:{actividad}"))

    if set(mapa_reg) != set(mapa_nac):
        solo_reg = sorted(set(mapa_reg) - set(mapa_nac))
        solo_nac = sorted(set(mapa_nac) - set(mapa_reg))
        partes = []
        if solo_reg:
            partes.append(f"solo regionales: {', '.join(solo_reg)}")
        if solo_nac:
            partes.append(f"solo nacionales: {', '.join(solo_nac)}")
        return _ausente(
            version,
            insumos,
            f"Los conjuntos de actividades regional y nacional no coinciden ({'; '.join(partes)}).",
        )

    falla_estado = _validar_estados(
        etiquetadas,
        reportar_cobertura=True,
        unidad_conteo="observaciones sectoriales",
    )
    if falla_estado is not None:
        return _ausente(version, insumos, falla_estado[1], falla_estado[0])

    clase, motivo_clase = _validar_clases(todas)
    if clase is None:
        return _ausente(version, insumos, motivo_clase or "Las clases de evidencia son incompatibles.")

    valores_reg: dict[str, Decimal] = {}
    valores_nac: dict[str, Decimal] = {}
    for actividad in sorted(mapa_reg):
        v_reg = _parsear_decimal(mapa_reg[actividad])
        v_nac = _parsear_decimal(mapa_nac[actividad])
        if v_reg is None or v_nac is None:
            return _ausente(version, insumos, "Alguna observación carece de un valor decimal válido.", "error")
        if v_reg < 0 or v_nac < 0:
            return _ausente(
                version,
                insumos,
                "El índice de Krugman requiere valores sectoriales no negativos.",
            )
        valores_reg[actividad] = v_reg
        valores_nac[actividad] = v_nac

    with localcontext(_CONTEXTO):
        total_reg = sum(valores_reg.values(), Decimal(0))
        total_nac = sum(valores_nac.values(), Decimal(0))
        if total_reg == 0 or total_nac == 0:
            return _ausente(
                version,
                insumos,
                "El denominador (suma sectorial regional o nacional) es cero.",
            )
        suma_diferencias = sum(
            (abs(valores_reg[act] * total_nac - valores_nac[act] * total_reg) for act in sorted(valores_reg)),
            Decimal(0),
        )
        resultado = suma_diferencias / (Decimal(2) * total_reg * total_nac)

    return Resultado(
        _formatear_decimal(resultado),
        None,
        version,
        insumos,
        _estado_disponible_final(todas),
        clase,
    )
