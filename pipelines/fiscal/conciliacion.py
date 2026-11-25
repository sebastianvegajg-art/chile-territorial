"""Motor puro de cálculo presupuestario y consolidación territorial.

Implementa las reglas de `docs/METHODOLOGY.md` (secciones «Presupuesto y
disponibilidad» y «Consolidación territorial») usando aritmética `Decimal`
de precisión 34 sin dependencias externas.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Context, Decimal, InvalidOperation, localcontext
from typing import Any, Iterable, Mapping, Optional, Union

PRECISION_DECIMAL = 34
CONTEXTO_DECIMAL = Context(prec=PRECISION_DECIMAL)

BILLETERAS_VALIDAS = ("sectorial", "regional", "municipal")
ETAPAS_CONTABLES_VALIDAS = ("inicial", "vigente", "compromiso", "devengo", "pago")
COBERTURAS_TERRITORIALES_VALIDAS = ("localizado", "multirregional", "sin_asignacion")

CERO = Decimal("0")
CIEN = Decimal("100")

ESQUEMA_CRUCE1_DISPONIBILIDAD = "fiscal-cruce1-disponibilidad-v1"
ADVERTENCIA_CAJA_DISPONIBILIDAD = (
    "La disponibilidad presupuestaria no equivale a disponibilidad efectiva "
    "de caja ni acredita liquidez de tesorería."
)

NumeroEntrada = Union[Decimal, int, str, None]


def _a_decimal(valor: NumeroEntrada, nombre_campo: str) -> Optional[Decimal]:
    """Convierte un valor exacto a Decimal con precisión 34.

    Rechaza `float` y `bool` para evitar errores de representación binaria
    en cálculos contables.
    """
    if valor is None:
        return None
    if isinstance(valor, bool) or isinstance(valor, float):
        raise TypeError(
            f"El campo '{nombre_campo}' no admite valores float ni bool; "
            "use Decimal, str o int."
        )
    if not isinstance(valor, (Decimal, int, str)):
        raise TypeError(
            f"Tipo no soportado para '{nombre_campo}': {type(valor).__name__}"
        )
    with localcontext(CONTEXTO_DECIMAL):
        try:
            resultado = Decimal(valor) if not isinstance(valor, Decimal) else +valor
        except InvalidOperation as exc:
            raise ValueError(
                f"Valor numérico inválido en '{nombre_campo}': {valor!r}"
            ) from exc
    if not resultado.is_finite():
        raise ValueError(
            f"El campo '{nombre_campo}' debe ser finito; se recibió {valor!r}"
        )
    return resultado


def clasificar_cobertura_territorial(territorio: Optional[str]) -> str:
    """Clasifica un código o etiqueta territorial en una cobertura canónica."""
    if territorio is None:
        return "sin_asignacion"
    normalizado = str(territorio).strip().lower()
    normalizado_sin_tilde = (
        normalizado.replace("ó", "o")
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ú", "u")
    )
    if normalizado_sin_tilde in {
        "",
        "sin_asignacion",
        "sin_asignar",
        "no_asignado",
        "sin asignacion",
        "sin asignar",
    }:
        return "sin_asignacion"
    if normalizado_sin_tilde in {"multirregional", "multicomunal"}:
        return "multirregional"
    return "localizado"


@dataclass(frozen=True)
class ResultadoCalculo:
    """Resultado auditable de un indicador presupuestario."""

    valor: Optional[Decimal]
    estado: str
    motivo: Optional[str] = None
    requiere_revision: bool = False


@dataclass(frozen=True)
class MovimientoFiscal:
    """Registro contable de una billetera en una etapa y territorio."""

    id_movimiento: str
    billetera: str
    monto: Decimal
    etapa: str
    territorio: Optional[str]
    es_transferencia_interna: bool = False
    id_documento: Optional[str] = None
    financiador: Optional[str] = None
    receptor: Optional[str] = None
    ejecutor: Optional[str] = None
    proyecto: Optional[str] = None
    ejercicio: Optional[int] = None
    corte: Optional[str] = None


@dataclass(frozen=True)
class TransferenciaConciliada:
    """Par de transferencia interna conciliada por identificador documental."""

    id_conciliacion: str
    id_documento: str
    id_movimiento_emisor: str
    id_movimiento_receptor: Optional[str]
    monto_conciliado: Decimal


@dataclass(frozen=True)
class TransferenciaAplicada:
    """Eliminación efectivamente aplicada en la consolidación bruto-a-neto."""

    id_conciliacion: str
    id_documento: str
    id_movimiento_emisor: str
    id_movimiento_receptor: str
    billetera_emisor: str
    billetera_receptor: str
    monto_eliminado: Decimal


@dataclass(frozen=True)
class ResidualPendiente:
    """Monto de transferencia sin contraparte completa que permanece sin eliminar."""

    id_movimiento: str
    billetera: str
    territorio: Optional[str]
    cobertura_territorial: str
    monto_total_movimiento: Decimal
    monto_conciliado: Decimal
    monto_pendiente: Decimal
    motivo: str
    id_documento: Optional[str] = None


@dataclass(frozen=True)
class ResultadoConsolidacion:
    """Vista completa bruto-a-neto, residuales y cobertura territorial."""

    etapa: Optional[str]
    totales_brutos_por_billetera: Mapping[str, Decimal]
    total_bruto: Decimal
    total_transferencias_eliminadas: Decimal
    consolidado_neto: Decimal
    conservacion_aritmetica_ok: bool
    transferencias_aplicadas: tuple[TransferenciaAplicada, ...]
    residuales_pendientes: tuple[ResidualPendiente, ...]
    total_residuales_pendientes: Decimal
    bruto_por_cobertura: Mapping[str, Decimal]
    neto_por_cobertura: Mapping[str, Decimal]
    porcentaje_cobertura_neta: Mapping[str, Optional[Decimal]]


def saldo_por_devengar(
    vigente: NumeroEntrada,
    devengo: NumeroEntrada,
) -> ResultadoCalculo:
    """Calcula vigente menos devengo imputado al mismo corte y perímetro.

    Conserva el signo negativo si existe y marca la observación para revisión.
    """
    vigente_dec = _a_decimal(vigente, "vigente")
    devengo_dec = _a_decimal(devengo, "devengo")
    if vigente_dec is None or devengo_dec is None:
        return ResultadoCalculo(
            valor=None,
            estado="no_calculable",
            motivo="vigente_o_devengo_faltante",
            requiere_revision=False,
        )
    with localcontext(CONTEXTO_DECIMAL):
        saldo = vigente_dec - devengo_dec
    if saldo < CERO:
        return ResultadoCalculo(
            valor=saldo,
            estado="requiere_revision",
            motivo="saldo_por_devengar_negativo_revisar",
            requiere_revision=True,
        )
    return ResultadoCalculo(
        valor=saldo,
        estado="calculado",
        motivo=None,
        requiere_revision=False,
    )


def saldo_no_comprometido(
    vigente: NumeroEntrada,
    devengo: NumeroEntrada,
    compromiso_pendiente: NumeroEntrada,
    *,
    compromisos_completos: bool = True,
) -> ResultadoCalculo:
    """Calcula el saldo presupuestario no comprometido.

    Fórmula: ``vigente - devengo - compromiso_pendiente``.
    Cuando faltan compromisos completos o `compromiso_pendiente` es ``None``,
    retorna ``valor=None`` con motivo explícito sin estimar disponibilidad.
    Conserva el signo si el saldo resulta negativo para revisión.
    """
    if not compromisos_completos or compromiso_pendiente is None:
        return ResultadoCalculo(
            valor=None,
            estado="no_calculable",
            motivo="compromisos_incompletos_o_no_disponibles",
            requiere_revision=False,
        )
    vigente_dec = _a_decimal(vigente, "vigente")
    devengo_dec = _a_decimal(devengo, "devengo")
    compromiso_dec = _a_decimal(compromiso_pendiente, "compromiso_pendiente")
    if vigente_dec is None or devengo_dec is None:
        return ResultadoCalculo(
            valor=None,
            estado="no_calculable",
            motivo="vigente_o_devengo_faltante",
            requiere_revision=False,
        )
    assert compromiso_dec is not None
    if compromiso_dec < CERO:
        raise ValueError(
            "compromiso_pendiente no puede ser negativo; debe excluir "
            "porciones devengadas y anuladas."
        )
    with localcontext(CONTEXTO_DECIMAL):
        saldo = vigente_dec - devengo_dec - compromiso_dec
    if saldo < CERO:
        return ResultadoCalculo(
            valor=saldo,
            estado="requiere_revision",
            motivo="saldo_no_comprometido_negativo_revisar",
            requiere_revision=True,
        )
    return ResultadoCalculo(
        valor=saldo,
        estado="calculado",
        motivo=None,
        requiere_revision=False,
    )


def tasa_ejecucion(
    devengo: NumeroEntrada,
    vigente: NumeroEntrada,
) -> ResultadoCalculo:
    """Calcula ``100 * devengo / vigente`` al mismo corte y perímetro.

    Un denominador cero, negativo o faltante produce valor faltante con causa.
    """
    devengo_dec = _a_decimal(devengo, "devengo")
    vigente_dec = _a_decimal(vigente, "vigente")
    if devengo_dec is None or vigente_dec is None:
        return ResultadoCalculo(
            valor=None,
            estado="no_calculable",
            motivo="devengo_o_vigente_faltante",
            requiere_revision=False,
        )
    if vigente_dec == CERO:
        return ResultadoCalculo(
            valor=None,
            estado="no_calculable",
            motivo="denominador_cero_vigente",
            requiere_revision=False,
        )
    if vigente_dec < CERO:
        return ResultadoCalculo(
            valor=None,
            estado="no_calculable",
            motivo="denominador_negativo_invalido",
            requiere_revision=False,
        )
    with localcontext(CONTEXTO_DECIMAL):
        tasa = (CIEN * devengo_dec) / vigente_dec
    if devengo_dec < CERO:
        return ResultadoCalculo(
            valor=tasa,
            estado="requiere_revision",
            motivo="devengo_negativo_revisar",
            requiere_revision=True,
        )
    if tasa > CIEN:
        return ResultadoCalculo(
            valor=tasa,
            estado="requiere_revision",
            motivo="ejecucion_superior_al_vigente_revisar",
            requiere_revision=True,
        )
    return ResultadoCalculo(
        valor=tasa,
        estado="calculado",
        motivo=None,
        requiere_revision=False,
    )


def analizar_disponibilidad_presupuestaria(
    presupuesto_inicial: NumeroEntrada,
    presupuesto_vigente: NumeroEntrada,
    arrastre_ejercicios_anteriores: NumeroEntrada = None,
    compromisos_plurianuales_ejercicio: NumeroEntrada = None,
    nuevos_compromisos: NumeroEntrada = None,
    devengo_acumulado: NumeroEntrada = None,
    pagos_acumulados: NumeroEntrada = None,
    *,
    compromiso_pendiente_devengar: NumeroEntrada = None,
    compromisos_completos: bool = True,
) -> dict[str, Any]:
    """Cruce 1: Presupuesto nominal vs disponibilidad efectiva y arrastre.

    Separa estrictamente las etapas contables (inicial, vigente, compromiso,
    devengo y pago) usando aritmética exacta ``Decimal`` (precisión 34), sin
    aceptar ``float`` ni estimar compromisos faltantes.

    Reglas principales:
    - ``saldo_por_devengar = presupuesto_vigente - devengo_acumulado``.
    - ``compromiso_total_ejercicio = arrastre + plurianuales + nuevos_compromisos``
      únicamente cuando los tres componentes están informados.
    - ``margen_no_comprometido``:
      * Si se entrega ``compromiso_pendiente_devengar`` explícito (y
        ``compromisos_completos=True``), calcula
        ``vigente - devengo - compromiso_pendiente_devengar``.
      * En su defecto, si ``compromiso_total_ejercicio`` está completo (y
        ``compromisos_completos=True``), deriva
        ``vigente - max(devengo, compromiso_total_ejercicio)`` (equivalente a
        ``vigente - devengo - max(0, compromiso_total_ejercicio - devengo)``).
      * Si faltan compromisos o ``compromisos_completos=False``, retorna
        ``None`` con motivo explícito sin inventar holgura.
    - ``porcentaje_arrastre_sobre_vigente = 100 * arrastre / vigente``.
    - ``desfase_devengo_pago = devengo_acumulado - pagos_acumulados`` cuando
      ambos están informados.
    - ``tasa_ejecucion_pct = 100 * devengo_acumulado / presupuesto_vigente``.
    """
    inicial_dec = _a_decimal(presupuesto_inicial, "presupuesto_inicial")
    vigente_dec = _a_decimal(presupuesto_vigente, "presupuesto_vigente")
    arrastre_dec = _a_decimal(
        arrastre_ejercicios_anteriores, "arrastre_ejercicios_anteriores"
    )
    plurianuales_dec = _a_decimal(
        compromisos_plurianuales_ejercicio, "compromisos_plurianuales_ejercicio"
    )
    nuevos_dec = _a_decimal(nuevos_compromisos, "nuevos_compromisos")
    devengo_dec = _a_decimal(devengo_acumulado, "devengo_acumulado")
    pagos_dec = _a_decimal(pagos_acumulados, "pagos_acumulados")
    comp_pend_explicito_dec = _a_decimal(
        compromiso_pendiente_devengar, "compromiso_pendiente_devengar"
    )

    for nombre_comp, valor_comp in (
        ("arrastre_ejercicios_anteriores", arrastre_dec),
        ("compromisos_plurianuales_ejercicio", plurianuales_dec),
        ("nuevos_compromisos", nuevos_dec),
        ("compromiso_pendiente_devengar", comp_pend_explicito_dec),
    ):
        if valor_comp is not None and valor_comp < CERO:
            raise ValueError(
                f"El campo '{nombre_comp}' no puede ser negativo; se recibió {valor_comp}."
            )

    motivos_no_calculable: dict[str, str] = {}
    alertas_revision: list[str] = []

    res_saldo_devengar = saldo_por_devengar(vigente_dec, devengo_dec)
    if res_saldo_devengar.valor is None and res_saldo_devengar.motivo:
        motivos_no_calculable["saldo_por_devengar"] = res_saldo_devengar.motivo
    if res_saldo_devengar.requiere_revision and res_saldo_devengar.motivo:
        alertas_revision.append(res_saldo_devengar.motivo)

    res_tasa = tasa_ejecucion(devengo_dec, vigente_dec)
    if res_tasa.valor is None and res_tasa.motivo:
        motivos_no_calculable["tasa_ejecucion_pct"] = res_tasa.motivo
    if res_tasa.requiere_revision and res_tasa.motivo:
        alertas_revision.append(res_tasa.motivo)

    with localcontext(CONTEXTO_DECIMAL):
        # Variación presupuestaria (vigente - inicial)
        variacion_vigente_inicial: Optional[Decimal] = None
        if inicial_dec is not None and vigente_dec is not None:
            variacion_vigente_inicial = vigente_dec - inicial_dec
        else:
            motivos_no_calculable["variacion_vigente_sobre_inicial"] = (
                "inicial_o_vigente_faltante"
            )

        # Compromiso total del ejercicio (exige los tres componentes)
        faltantes_comp = [
            nombre
            for nombre, val in (
                ("arrastre_ejercicios_anteriores", arrastre_dec),
                ("compromisos_plurianuales_ejercicio", plurianuales_dec),
                ("nuevos_compromisos", nuevos_dec),
            )
            if val is None
        ]
        compromiso_total: Optional[Decimal] = None
        if not faltantes_comp:
            assert (
                arrastre_dec is not None
                and plurianuales_dec is not None
                and nuevos_dec is not None
            )
            compromiso_total = arrastre_dec + plurianuales_dec + nuevos_dec
        else:
            motivos_no_calculable["compromiso_total_ejercicio"] = (
                "componentes_compromiso_faltantes:" + ",".join(faltantes_comp)
            )

        # Margen presupuestario no comprometido
        margen_no_comprometido: Optional[Decimal] = None
        compromiso_pendiente_aplicado: Optional[Decimal] = None
        metodo_margen: Optional[str] = None
        motivo_margen: Optional[str] = None

        if not compromisos_completos:
            motivo_margen = "compromisos_incompletos_o_no_disponibles"
            motivos_no_calculable["margen_no_comprometido"] = motivo_margen
        elif comp_pend_explicito_dec is not None:
            res_margen = saldo_no_comprometido(
                vigente_dec,
                devengo_dec,
                comp_pend_explicito_dec,
                compromisos_completos=True,
            )
            margen_no_comprometido = res_margen.valor
            if margen_no_comprometido is not None:
                compromiso_pendiente_aplicado = comp_pend_explicito_dec
                metodo_margen = "vigente_menos_devengo_menos_compromiso_pendiente"
                if res_margen.requiere_revision and res_margen.motivo:
                    alertas_revision.append(res_margen.motivo)
            else:
                motivo_margen = res_margen.motivo
                if motivo_margen:
                    motivos_no_calculable["margen_no_comprometido"] = motivo_margen
        elif compromiso_total is not None:
            if vigente_dec is None or devengo_dec is None:
                motivo_margen = "vigente_o_devengo_faltante"
                motivos_no_calculable["margen_no_comprometido"] = motivo_margen
            else:
                compromiso_o_devengo = (
                    devengo_dec
                    if devengo_dec >= compromiso_total
                    else compromiso_total
                )
                margen_no_comprometido = vigente_dec - compromiso_o_devengo
                compromiso_pendiente_aplicado = (
                    compromiso_total - devengo_dec
                    if compromiso_total > devengo_dec
                    else CERO
                )
                metodo_margen = "vigente_menos_max_devengo_o_compromiso_total"
                if devengo_dec > compromiso_total:
                    alertas_revision.append("devengo_supera_compromiso_total_revisar")
                if margen_no_comprometido < CERO:
                    alertas_revision.append("margen_no_comprometido_negativo_revisar")
        else:
            motivo_margen = (
                "compromisos_incompletos_o_no_disponibles:"
                + ",".join(faltantes_comp)
            )
            motivos_no_calculable["margen_no_comprometido"] = motivo_margen

        # Porcentaje de arrastre sobre presupuesto vigente
        pct_arrastre: Optional[Decimal] = None
        if arrastre_dec is None or vigente_dec is None:
            motivos_no_calculable["porcentaje_arrastre_sobre_vigente"] = (
                "arrastre_o_vigente_faltante"
            )
        elif vigente_dec == CERO:
            motivos_no_calculable["porcentaje_arrastre_sobre_vigente"] = (
                "denominador_cero_vigente"
            )
        elif vigente_dec < CERO:
            motivos_no_calculable["porcentaje_arrastre_sobre_vigente"] = (
                "denominador_negativo_invalido"
            )
        else:
            pct_arrastre = (CIEN * arrastre_dec) / vigente_dec
            if pct_arrastre > CIEN:
                alertas_revision.append("arrastre_superior_al_vigente_revisar")

        # Desfase entre devengo acumulado y pagos acumulados (deuda flotante del ejercicio)
        desfase_devengo_pago: Optional[Decimal] = None
        if devengo_dec is not None and pagos_dec is not None:
            desfase_devengo_pago = devengo_dec - pagos_dec
            if desfase_devengo_pago < CERO:
                alertas_revision.append("pagos_superiores_a_devengo_revisar")
        else:
            motivos_no_calculable["desfase_devengo_pago"] = (
                "pagos_o_devengo_faltante"
            )

    return {
        "esquema": ESQUEMA_CRUCE1_DISPONIBILIDAD,
        "etapas_separadas": True,
        "entradas": {
            "presupuesto_inicial": inicial_dec,
            "presupuesto_vigente": vigente_dec,
            "arrastre_ejercicios_anteriores": arrastre_dec,
            "compromisos_plurianuales_ejercicio": plurianuales_dec,
            "nuevos_compromisos": nuevos_dec,
            "compromiso_pendiente_devengar": comp_pend_explicito_dec,
            "devengo_acumulado": devengo_dec,
            "pagos_acumulados": pagos_dec,
        },
        "variacion_vigente_sobre_inicial": variacion_vigente_inicial,
        "saldo_por_devengar": res_saldo_devengar.valor,
        "compromiso_total_ejercicio": compromiso_total,
        "compromiso_pendiente_aplicado": compromiso_pendiente_aplicado,
        "margen_no_comprometido": margen_no_comprometido,
        "metodo_margen_no_comprometido": metodo_margen,
        "motivo_margen_no_comprometido": motivo_margen,
        "porcentaje_arrastre_sobre_vigente": pct_arrastre,
        "desfase_devengo_pago": desfase_devengo_pago,
        "tasa_ejecucion_pct": res_tasa.valor,
        "requiere_revision": bool(alertas_revision),
        "alertas_revision": alertas_revision,
        "motivos_no_calculable": motivos_no_calculable,
        "advertencia_caja": ADVERTENCIA_CAJA_DISPONIBILIDAD,
    }


def _normalizar_movimiento(
    item: Union[MovimientoFiscal, Mapping[str, Any]],
) -> MovimientoFiscal:
    if isinstance(item, MovimientoFiscal):
        monto = _a_decimal(item.monto, "monto")
        mov = MovimientoFiscal(
            id_movimiento=str(item.id_movimiento).strip(),
            billetera=str(item.billetera).strip().lower(),
            monto=monto if monto is not None else CERO,
            etapa=str(item.etapa).strip().lower(),
            territorio=item.territorio,
            es_transferencia_interna=bool(item.es_transferencia_interna),
            id_documento=(
                str(item.id_documento).strip()
                if item.id_documento is not None and str(item.id_documento).strip()
                else None
            ),
            financiador=item.financiador,
            receptor=item.receptor,
            ejecutor=item.ejecutor,
            proyecto=item.proyecto,
            ejercicio=item.ejercicio,
            corte=item.corte,
        )
    elif isinstance(item, Mapping):
        if "monto" not in item or item["monto"] is None:
            raise ValueError("Todo movimiento debe informar un monto no nulo.")
        monto = _a_decimal(item["monto"], "monto")
        assert monto is not None
        raw_doc = item.get("id_documento")
        mov = MovimientoFiscal(
            id_movimiento=str(item["id_movimiento"]).strip(),
            billetera=str(item["billetera"]).strip().lower(),
            monto=monto,
            etapa=str(item["etapa"]).strip().lower(),
            territorio=item.get("territorio"),
            es_transferencia_interna=bool(item.get("es_transferencia_interna", False)),
            id_documento=(
                str(raw_doc).strip()
                if raw_doc is not None and str(raw_doc).strip()
                else None
            ),
            financiador=item.get("financiador"),
            receptor=item.get("receptor"),
            ejecutor=item.get("ejecutor"),
            proyecto=item.get("proyecto"),
            ejercicio=item.get("ejercicio"),
            corte=item.get("corte"),
        )
    else:
        raise TypeError(
            "Cada movimiento debe ser MovimientoFiscal o Mapping."
        )

    if not mov.id_movimiento:
        raise ValueError("id_movimiento no puede estar vacío.")
    if mov.billetera not in BILLETERAS_VALIDAS:
        raise ValueError(
            f"Billetera inválida '{mov.billetera}'; válidas: {BILLETERAS_VALIDAS}"
        )
    if mov.etapa not in ETAPAS_CONTABLES_VALIDAS:
        raise ValueError(
            f"Etapa contable inválida '{mov.etapa}'; válidas: {ETAPAS_CONTABLES_VALIDAS}"
        )
    if mov.monto < CERO:
        raise ValueError(
            f"El monto del movimiento '{mov.id_movimiento}' no puede ser negativo."
        )
    return mov


def _normalizar_transferencia(
    item: Union[TransferenciaConciliada, Mapping[str, Any]],
) -> TransferenciaConciliada:
    if isinstance(item, TransferenciaConciliada):
        id_conciliacion = str(item.id_conciliacion).strip()
        id_documento = "" if item.id_documento is None else str(item.id_documento).strip()
        id_emisor = str(item.id_movimiento_emisor).strip()
        id_receptor = (
            str(item.id_movimiento_receptor).strip()
            if item.id_movimiento_receptor is not None
            and str(item.id_movimiento_receptor).strip()
            else None
        )
        monto = _a_decimal(item.monto_conciliado, "monto_conciliado")
    elif isinstance(item, Mapping):
        id_conciliacion = str(item.get("id_conciliacion", "")).strip()
        raw_doc = item.get("id_documento")
        id_documento = "" if raw_doc is None else str(raw_doc).strip()
        id_emisor = str(item.get("id_movimiento_emisor", "")).strip()
        raw_rec = item.get("id_movimiento_receptor")
        id_receptor = (
            str(raw_rec).strip()
            if raw_rec is not None and str(raw_rec).strip()
            else None
        )
        monto = _a_decimal(item.get("monto_conciliado"), "monto_conciliado")
    else:
        raise TypeError(
            "Cada transferencia conciliada debe ser TransferenciaConciliada o Mapping."
        )

    if not id_conciliacion:
        raise ValueError("id_conciliacion no puede estar vacío.")
    if not id_documento:
        raise ValueError(
            f"La transferencia '{id_conciliacion}' carece de id_documento; "
            "no se permite conciliar sin respaldo documental verificable."
        )
    if not id_emisor:
        raise ValueError(
            f"La transferencia '{id_conciliacion}' requiere id_movimiento_emisor."
        )
    if monto is None or monto <= CERO:
        raise ValueError(
            f"La transferencia '{id_conciliacion}' debe tener monto_conciliado > 0."
        )
    return TransferenciaConciliada(
        id_conciliacion=id_conciliacion,
        id_documento=id_documento,
        id_movimiento_emisor=id_emisor,
        id_movimiento_receptor=id_receptor,
        monto_conciliado=monto,
    )


def consolidar_billeteras(
    movimientos: Iterable[Union[MovimientoFiscal, Mapping[str, Any]]],
    transferencias_conciliadas: Iterable[
        Union[TransferenciaConciliada, Mapping[str, Any]]
    ] = (),
) -> ResultadoConsolidacion:
    """Consolida las tres billeteras (sectorial, regional, municipal) de bruto a neto.

    Reglas aplicadas:
    - Todos los movimientos deben pertenecer a una única etapa contable.
    - Las transferencias internas se eliminan únicamente si están respaldadas
      por un par explícito con ``id_documento`` verificable y contraparte
      presente dentro del perímetro consolidado.
    - En la vista consolidada neta se elimina el monto conciliado del emisor
      y se conserva el gasto final del receptor/ejecutor.
    - Transferencias con contraparte parcial o ausente conservan su remanente
      sin eliminar y se reportan explícitamente en ``residuales_pendientes``.
    - Garantiza conservación aritmética exacta:
      ``sum(brutos) - total_transferencias_eliminadas == consolidado_neto``
      y ``sum(neto_por_cobertura) == consolidado_neto``.
    """
    lista_movs = [_normalizar_movimiento(m) for m in movimientos]
    lista_trans = [_normalizar_transferencia(t) for t in transferencias_conciliadas]

    movimientos_por_id: dict[str, MovimientoFiscal] = {}
    etapas_encontradas: set[str] = set()

    totales_brutos: dict[str, Decimal] = {b: CERO for b in BILLETERAS_VALIDAS}
    bruto_por_cobertura: dict[str, Decimal] = {
        c: CERO for c in COBERTURAS_TERRITORIALES_VALIDAS
    }
    cobertura_por_mov: dict[str, str] = {}

    with localcontext(CONTEXTO_DECIMAL):
        for mov in lista_movs:
            if mov.id_movimiento in movimientos_por_id:
                raise ValueError(
                    f"id_movimiento duplicado en consolidación: '{mov.id_movimiento}'"
                )
            movimientos_por_id[mov.id_movimiento] = mov
            etapas_encontradas.add(mov.etapa)
            totales_brutos[mov.billetera] += mov.monto
            cobertura = clasificar_cobertura_territorial(mov.territorio)
            cobertura_por_mov[mov.id_movimiento] = cobertura
            bruto_por_cobertura[cobertura] += mov.monto

        if len(etapas_encontradas) > 1:
            raise ValueError(
                "No se permite mezclar etapas contables incompatibles en una "
                f"misma consolidación: {sorted(etapas_encontradas)}"
            )
        etapa_unica = next(iter(etapas_encontradas), None)

        neto_por_cobertura = dict(bruto_por_cobertura)
        conciliado_emisor: dict[str, Decimal] = {}
        conciliado_receptor: dict[str, Decimal] = {}
        ids_conciliacion_vistos: set[str] = set()
        transferencias_aplicadas: list[TransferenciaAplicada] = []
        emisores_con_contraparte_ausente: dict[str, str] = {}

        total_eliminadas = CERO

        for trans in lista_trans:
            if trans.id_conciliacion in ids_conciliacion_vistos:
                raise ValueError(
                    f"id_conciliacion duplicado: '{trans.id_conciliacion}'"
                )
            ids_conciliacion_vistos.add(trans.id_conciliacion)

            if trans.id_movimiento_emisor not in movimientos_por_id:
                raise ValueError(
                    f"El emisor '{trans.id_movimiento_emisor}' de la conciliación "
                    f"'{trans.id_conciliacion}' no existe en los movimientos."
                )
            emisor = movimientos_por_id[trans.id_movimiento_emisor]

            if (
                emisor.id_documento is not None
                and emisor.id_documento != trans.id_documento
            ):
                raise ValueError(
                    f"Discrepancia documental en emisor '{emisor.id_movimiento}': "
                    f"movimiento='{emisor.id_documento}' vs conciliación='{trans.id_documento}'."
                )

            if (
                trans.id_movimiento_receptor is None
                or trans.id_movimiento_receptor not in movimientos_por_id
            ):
                # Contraparte ausente en el perímetro: no se elimina y queda pendiente.
                emisores_con_contraparte_ausente[emisor.id_movimiento] = (
                    trans.id_documento
                )
                continue

            receptor = movimientos_por_id[trans.id_movimiento_receptor]
            if emisor.id_movimiento == receptor.id_movimiento:
                raise ValueError(
                    f"La conciliación '{trans.id_conciliacion}' no puede referenciar "
                    "el mismo movimiento como emisor y receptor."
                )
            if (
                receptor.id_documento is not None
                and receptor.id_documento != trans.id_documento
            ):
                raise ValueError(
                    f"Discrepancia documental en receptor '{receptor.id_movimiento}': "
                    f"movimiento='{receptor.id_documento}' vs conciliación='{trans.id_documento}'."
                )

            acum_emisor = conciliado_emisor.get(emisor.id_movimiento, CERO) + trans.monto_conciliado
            if acum_emisor > emisor.monto:
                raise ValueError(
                    f"El monto conciliado acumulado ({acum_emisor}) excede el monto "
                    f"del emisor '{emisor.id_movimiento}' ({emisor.monto})."
                )
            acum_receptor = conciliado_receptor.get(receptor.id_movimiento, CERO) + trans.monto_conciliado
            if acum_receptor > receptor.monto:
                raise ValueError(
                    f"El monto conciliado acumulado ({acum_receptor}) excede el monto "
                    f"del receptor '{receptor.id_movimiento}' ({receptor.monto})."
                )

            conciliado_emisor[emisor.id_movimiento] = acum_emisor
            conciliado_receptor[receptor.id_movimiento] = acum_receptor
            total_eliminadas += trans.monto_conciliado
            neto_por_cobertura[cobertura_por_mov[emisor.id_movimiento]] -= (
                trans.monto_conciliado
            )
            transferencias_aplicadas.append(
                TransferenciaAplicada(
                    id_conciliacion=trans.id_conciliacion,
                    id_documento=trans.id_documento,
                    id_movimiento_emisor=emisor.id_movimiento,
                    id_movimiento_receptor=receptor.id_movimiento,
                    billetera_emisor=emisor.billetera,
                    billetera_receptor=receptor.billetera,
                    monto_eliminado=trans.monto_conciliado,
                )
            )

        residuales: list[ResidualPendiente] = []
        total_residuales = CERO

        for mov in lista_movs:
            conciliado = conciliado_emisor.get(mov.id_movimiento, CERO)
            if conciliado > CERO and conciliado < mov.monto:
                pendiente = mov.monto - conciliado
                total_residuales += pendiente
                residuales.append(
                    ResidualPendiente(
                        id_movimiento=mov.id_movimiento,
                        billetera=mov.billetera,
                        territorio=mov.territorio,
                        cobertura_territorial=cobertura_por_mov[mov.id_movimiento],
                        monto_total_movimiento=mov.monto,
                        monto_conciliado=conciliado,
                        monto_pendiente=pendiente,
                        motivo="conciliacion_parcial",
                        id_documento=mov.id_documento,
                    )
                )
            elif conciliado == CERO and (
                mov.es_transferencia_interna
                or mov.id_movimiento in emisores_con_contraparte_ausente
            ):
                pendiente = mov.monto
                total_residuales += pendiente
                doc_ref = mov.id_documento or emisores_con_contraparte_ausente.get(
                    mov.id_movimiento
                )
                residuales.append(
                    ResidualPendiente(
                        id_movimiento=mov.id_movimiento,
                        billetera=mov.billetera,
                        territorio=mov.territorio,
                        cobertura_territorial=cobertura_por_mov[mov.id_movimiento],
                        monto_total_movimiento=mov.monto,
                        monto_conciliado=CERO,
                        monto_pendiente=pendiente,
                        motivo="contraparte_ausente",
                        id_documento=doc_ref,
                    )
                )

        total_bruto = sum(totales_brutos.values(), CERO)
        consolidado_neto = total_bruto - total_eliminadas

        suma_bruto_cobertura = sum(bruto_por_cobertura.values(), CERO)
        suma_neto_cobertura = sum(neto_por_cobertura.values(), CERO)
        conservacion_ok = (
            (total_bruto - total_eliminadas == consolidado_neto)
            and (suma_bruto_cobertura == total_bruto)
            and (suma_neto_cobertura == consolidado_neto)
        )

        porcentaje_cobertura: dict[str, Optional[Decimal]] = {}
        for cob in COBERTURAS_TERRITORIALES_VALIDAS:
            if consolidado_neto > CERO:
                porcentaje_cobertura[cob] = (
                    CIEN * neto_por_cobertura[cob]
                ) / consolidado_neto
            else:
                porcentaje_cobertura[cob] = None

    return ResultadoConsolidacion(
        etapa=etapa_unica,
        totales_brutos_por_billetera=totales_brutos,
        total_bruto=total_bruto,
        total_transferencias_eliminadas=total_eliminadas,
        consolidado_neto=consolidado_neto,
        conservacion_aritmetica_ok=conservacion_ok,
        transferencias_aplicadas=tuple(transferencias_aplicadas),
        residuales_pendientes=tuple(residuales),
        total_residuales_pendientes=total_residuales,
        bruto_por_cobertura=bruto_por_cobertura,
        neto_por_cobertura=neto_por_cobertura,
        porcentaje_cobertura_neta=porcentaje_cobertura,
    )
