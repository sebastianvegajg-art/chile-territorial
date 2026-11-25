"""Conector oficial y auditoría territorial de proyectos MOP (Región de Aysén).

Consulta el servicio ArcGIS REST público de la Dirección General de Obras
Públicas (DGOP / Ministerio de Obras Públicas):
`https://rest-sit.mop.gob.cl/arcgis/rest/services/DGOP/VISOR_OBRA_MOP/MapServer`

Capas consultadas para Región de Aysén (`REG_CODIGO=11`):
- Capa 0: Puntos de Contratos
- Capa 1: Líneas de Contratos (donde residen los tramos de la Dirección de Vialidad)
- Capa 2: Contratos Línea-Punto

Garantías metodológicas:
- Deduplicación estricta por `COD_CONTRATO` conservando el registro con mayor
  completitud de montos y fechas (evitando multiplicar montos cuando un contrato
  tiene múltiples tramos o geometrías entre capas 0, 1 y 2).
- Conversión exacta desde `miles CLP` (unidad origen MOP) a `millones CLP`
  dividiendo por `1000` mediante `Decimal` con precisión 34 (sin `float`).
- Separación explícita de etapas contables (presupuestado, contrato plurianual,
  compromiso anual `MONTO_AGNO_ACT`, pagado del año, pagado años anteriores y
  saldo pendiente) sin mezclar etapas incompatibles.
- Cálculo separado de las dos preguntas ciudadanas clave:
  1) Pagos del año correspondientes a contratos firmados antes del cambio de
     administración presidencial (`fecha_contratacion < fecha_cambio_admin`).
  2) Arrastre presupuestario del ejercicio (`MONTO_AGNO_ACT` de proyectos con
     marca oficial `NUEVOARRASTRE = "A"` sobre el total documentado).
- Aislamiento explícito de proyectos con información insuficiente para que no
  contaminen los porcentajes ni los indicadores agregados.
- Archivo inmutable de respuestas JSON crudas + `manifiesto.json` con SHA-256
  y soporte `--reproducir --insumos <dir>` bit-a-bit sin red.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_ARCGIS_MOP = (
    "https://rest-sit.mop.gob.cl/arcgis/rest/services/DGOP/VISOR_OBRA_MOP/MapServer"
)
CAPAS_MOP: tuple[tuple[int, str], ...] = (
    (0, "Puntos de Contratos"),
    (1, "Líneas de Contratos"),
    (2, "Contratos Línea-Punto"),
)
REGION_AYSEN_CODIGO = 11
REGION_AYSEN_NOMBRE = "Aysén del General Carlos Ibáñez del Campo"
VERSION_ESQUEMA_RAW = "mop-aysen-raw-v1"
VERSION_ESQUEMA_PUBLICADO = "mop-aysen-proyectos-v1"
USER_AGENT = "ChileTerritorial/1.0 (+https://rest-sit.mop.gob.cl)"
TIMEOUT_DEFAULT = 30
MAX_PAGINAS_POR_CAPA = 100

PRECISION_DECIMAL = 34
CONTEXTO_DECIMAL = Context(prec=PRECISION_DECIMAL)
CERO = Decimal("0")
CIEN = Decimal("100")
MIL = Decimal("1000")

_RAIZ_REPO = Path(__file__).resolve().parents[2]
_SALIDA_DEFAULT = Path("data/published/proyectos-mop-aysen.json")

_COMUNAS_AYSEN_CANONICAS: dict[str, str] = {
    "coyhaique": "Coyhaique",
    "coihaique": "Coyhaique",
    "lago verde": "Lago Verde",
    "aysen": "Aysén",
    "aisen": "Aysén",
    "puerto aysen": "Aysén",
    "cisnes": "Cisnes",
    "guaitecas": "Guaitecas",
    "cochrane": "Cochrane",
    "o'higgins": "O'Higgins",
    "ohiggins": "O'Higgins",
    "o higgins": "O'Higgins",
    "tortel": "Tortel",
    "chile chico": "Chile Chico",
    "rio ibanez": "Río Ibáñez",
    "rio ibanes": "Río Ibáñez",
}

_ORDEN_COMUNAS_AYSEN: tuple[str, ...] = (
    "Coyhaique",
    "Lago Verde",
    "Aysén",
    "Cisnes",
    "Guaitecas",
    "Cochrane",
    "O'Higgins",
    "Tortel",
    "Chile Chico",
    "Río Ibáñez",
)

_VALORES_VACIOS = frozenset(
    {"", "-", "--", "---", "–", "—", "n/a", "na", "nd", "s/i", "sd", "null", "none"}
)


class MopProyectosError(RuntimeError):
    """Error controlado en extracción, verificación o normalización MOP."""


def _sha256_bytes(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def _limpiar_texto(valor: object) -> str | None:
    if valor is None:
        return None
    texto = re.sub(r"\s+", " ", str(valor)).strip()
    if not texto or texto.lower() in _VALORES_VACIOS:
        return None
    return texto


def _normalizar_clave_texto(valor: object) -> str:
    if valor is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(valor))
    sin_tildes = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


def formatear_decimal(valor: Decimal) -> str:
    """Formatea un Decimal exacto sin notación científica ni '-0'."""
    with localcontext(CONTEXTO_DECIMAL):
        if valor == CERO:
            return "0"
        normalizado = valor.normalize()
        texto = format(normalizado, "f")
        if "." in texto:
            texto = texto.rstrip("0").rstrip(".")
        return "0" if texto in {"", "-0"} else texto


def formatear_porcentaje(numerador: Decimal, denominador: Decimal) -> str | None:
    """Calcula `100 * numerador / denominador` con `Decimal(34)` a 2 decimales."""
    if denominador == CERO:
        return None
    with localcontext(CONTEXTO_DECIMAL):
        pct = (numerador * CIEN) / denominador
        redondeado = pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return format(redondeado, "f")


def formatear_millones_clp_ciudadano(valor: Decimal) -> str:
    """Formatea un monto en millones CLP al estilo chileno (ej. `$1.361,0 millones`)."""
    with localcontext(CONTEXTO_DECIMAL):
        redondeado = valor.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        negativo = redondeado < CERO
        absoluto = -redondeado if negativo else redondeado
        entero_str, decimal_str = format(absoluto, "f").split(".")
        entero_miles = f"{int(entero_str):,}".replace(",", ".")
        signo = "-" if negativo else ""
        return f"{signo}${entero_miles},{decimal_str} millones"


def formatear_porcentaje_ciudadano(porcentaje_str: str) -> str:
    """Formatea porcentaje como texto ciudadano en español (coma decimal, 1 decimal)."""
    with localcontext(CONTEXTO_DECIMAL):
        val = Decimal(porcentaje_str).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return format(val, "f").replace(".", ",") + "%"


def parsear_decimal_mop(valor: object) -> Decimal | None:
    """Convierte un valor numérico proveniente del servicio MOP a `Decimal(34)` sin float."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, Decimal):
        return valor if valor.is_finite() else None
    if isinstance(valor, int):
        return Decimal(valor)
    if isinstance(valor, float):
        if not math.isfinite(valor):
            return None
        return Decimal(str(valor))
    texto = str(valor).strip()
    if not texto or texto.lower() in _VALORES_VACIOS:
        return None
    texto = texto.replace(" ", "")
    if "," in texto and "." not in texto:
        texto = texto.replace(",", ".")
    try:
        with localcontext(CONTEXTO_DECIMAL):
            dec = Decimal(texto)
    except InvalidOperation:
        return None
    return dec if dec.is_finite() else None


def miles_a_millones_clp(valor: object) -> Decimal | None:
    """Convierte `miles CLP` a `millones CLP` dividiendo exactamente por `1000`."""
    dec = parsear_decimal_mop(valor)
    if dec is None:
        return None
    with localcontext(CONTEXTO_DECIMAL):
        return dec / MIL


def parsear_fecha_mop(valor: object) -> str | None:
    """Convierte fecha MOP `DDMMYYYY` a ISO `YYYY-MM-DD`, o `None` si es vacía o inválida."""
    if valor is None or isinstance(valor, bool):
        return None
    texto = str(valor).strip()
    if not texto or texto.lower() in _VALORES_VACIOS:
        return None
    if not re.fullmatch(r"\d{8}", texto):
        return None
    if texto in {"00000000", "99999999"}:
        return None
    dia = int(texto[0:2])
    mes = int(texto[2:4])
    anio = int(texto[4:8])
    if anio < 1950 or anio > 2100:
        return None
    try:
        fecha = date(anio, mes, dia)
    except ValueError:
        return None
    return fecha.isoformat()


def _parsear_epoch_ms_a_fecha_iso(valor: object) -> str | None:
    """Convierte timestamp ArcGIS en milisegundos epoch a fecha ISO `YYYY-MM-DD` (UTC)."""
    dec = parsear_decimal_mop(valor)
    if dec is None or dec <= CERO:
        return None
    try:
        segundos = int(dec // MIL)
        return datetime.fromtimestamp(segundos, tz=timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _fecha_iso_a_ciudadana(fecha_iso: str) -> str:
    """Convierte `YYYY-MM-DD` a `DD-MM-YYYY` para lectura ciudadana."""
    anio, mes, dia = fecha_iso.split("-")
    return f"{dia}-{mes}-{anio}"


def clasificar_administracion(fecha_iso: str | None) -> str | None:
    """Clasifica la administración presidencial vigente en Chile para una fecha ISO."""
    if not fecha_iso:
        return None
    texto = fecha_iso.strip()
    try:
        fecha = date.fromisoformat(texto)
    except ValueError:
        return None

    if fecha < date(2014, 3, 11):
        return "Administración anterior a 2014"
    if fecha <= date(2018, 3, 10):
        return "Administración 2014–2018"
    if fecha <= date(2022, 3, 10):
        return "Administración 2018–2022"
    if fecha <= date(2026, 3, 10):
        return "Administración 2022–2026"
    return "Administración 2026–2030"


def fecha_cambio_administracion_para_anio(anio_corte: int) -> str:
    """Devuelve la fecha ISO de inicio de la administración vigente en el año de corte."""
    if anio_corte >= 2026:
        return "2026-03-11"
    if anio_corte >= 2022:
        return "2022-03-11"
    if anio_corte >= 2018:
        return "2018-03-11"
    if anio_corte >= 2014:
        return "2014-03-11"
    return "2010-03-11"


def normalizar_comunas(valor: object) -> list[str]:
    """Normaliza `COMUNAS` a una lista ordenada sin duplicados de nombres limpios."""
    texto = _limpiar_texto(valor)
    if not texto:
        return []
    partes = re.split(r"[,;/]+", texto)
    resultado: list[str] = []
    vistos: set[str] = set()
    for parte in partes:
        limpio = re.sub(r"\s+", " ", parte).strip()
        if not limpio:
            continue
        clave = _normalizar_clave_texto(limpio)
        canonica = _COMUNAS_AYSEN_CANONICAS.get(clave)
        if canonica is None:
            canonica = limpio.title()
        if canonica not in vistos:
            vistos.add(canonica)
            resultado.append(canonica)
    return resultado


def _normalizar_nuevo_arrastre(valor: object) -> str:
    texto = _limpiar_texto(valor)
    if not texto:
        return "sin_dato"
    marca = texto.upper()
    if marca == "A":
        return "arrastre"
    if marca == "N":
        return "nuevo"
    return "sin_dato"


def _normalizar_url(valor: object) -> str | None:
    texto = _limpiar_texto(valor)
    if not texto:
        return None
    if texto.startswith(("http://", "https://")):
        return texto
    return None


def _normalizar_id_contrato(attrs: Mapping[str, Any]) -> str | None:
    for campo in ("COD_CONTRATO", "CODCONTRATO"):
        val = attrs.get(campo)
        if val is None or isinstance(val, bool):
            continue
        if isinstance(val, int):
            return str(val)
        if isinstance(val, Decimal):
            if val == val.to_integral_value():
                return str(int(val))
            return formatear_decimal(val)
        texto = _limpiar_texto(val)
        if texto:
            return texto
    return None


def _puntaje_completitud(attrs: Mapping[str, Any], capa_id: int) -> tuple[int, int, int, int, int]:
    """Evalúa completitud de montos y fechas para elegir el mejor registro en deduplicación."""
    montos_no_nulos = 0
    for campo in (
        "MONTO_PRESUPUESTADO",
        "MONTO_CONTRATO",
        "MONTO_AGNO_ACT",
        "PAGADO",
        "PAGADO_AGNO_ANT",
        "SALDO",
    ):
        dec = parsear_decimal_mop(attrs.get(campo))
        if dec is not None:
            montos_no_nulos += 1

    montos_positivos = 0
    for campo in ("MONTO_CONTRATO", "MONTO_AGNO_ACT", "PAGADO", "MONTO_PRESUPUESTADO"):
        dec = parsear_decimal_mop(attrs.get(campo))
        if dec is not None and dec > CERO:
            montos_positivos += 1

    fechas_y_marcas = 0
    if parsear_fecha_mop(attrs.get("FECHA_INICIO")) is not None:
        fechas_y_marcas += 2
    if parsear_fecha_mop(attrs.get("FECHA_TERMINO")) is not None:
        fechas_y_marcas += 1
    if _normalizar_nuevo_arrastre(attrs.get("NUEVOARRASTRE")) in {"arrastre", "nuevo"}:
        fechas_y_marcas += 2

    metadatos_extra = 0
    for campo in (
        "CODIGOBIP",
        "NOM_PROYECTO",
        "NOM_CONTRATO",
        "SERV_NOMBRE",
        "COMUNAS",
        "ESTADO_1",
        "CONTRATISTA",
        "LINK_FICHA_PROY",
        "LINK_FICHA_CTTO",
        "LINK_MERCADO_PUB",
    ):
        if _limpiar_texto(attrs.get(campo)) is not None:
            metadatos_extra += 1
    if parsear_decimal_mop(attrs.get("AVANCE_FISICO")) is not None:
        metadatos_extra += 1

    editado = parsear_decimal_mop(attrs.get("last_edited_date"))
    editado_int = int(editado) if editado is not None else 0

    # Prioridad: montos presentes + fechas/marcas + montos positivos + metadatos + recencia.
    # Desempate determinista por menor número de capa.
    return (
        montos_no_nulos + fechas_y_marcas,
        montos_positivos,
        metadatos_extra,
        editado_int,
        -capa_id,
    )


def deduplicar_registros_mop(
    registros_por_capa: Sequence[tuple[int, Sequence[Mapping[str, Any]]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Deduplica features de capas 0/1/2 por `COD_CONTRATO` conservando el más completo."""
    ganadores: dict[str, tuple[tuple[int, int, int, int, int], int, dict[str, Any]]] = {}
    capas_por_contrato: dict[str, set[int]] = {}
    conteo_por_contrato: dict[str, int] = {}
    sin_id: list[tuple[int, dict[str, Any]]] = []
    total_filas_crudas = 0
    conteo_por_capa: dict[str, int] = {}

    for capa_id, features in registros_por_capa:
        conteo_por_capa[str(capa_id)] = conteo_por_capa.get(str(capa_id), 0) + len(features)
        for item in features:
            total_filas_crudas += 1
            attrs = item.get("attributes") if isinstance(item, Mapping) and "attributes" in item else item
            if not isinstance(attrs, Mapping):
                continue
            attrs_dict = dict(attrs)
            id_contrato = _normalizar_id_contrato(attrs_dict)
            if id_contrato is None:
                sin_id.append((capa_id, attrs_dict))
                continue

            capas_por_contrato.setdefault(id_contrato, set()).add(capa_id)
            conteo_por_contrato[id_contrato] = conteo_por_contrato.get(id_contrato, 0) + 1
            puntaje = _puntaje_completitud(attrs_dict, capa_id)
            previo = ganadores.get(id_contrato)
            if previo is None or puntaje > previo[0]:
                ganadores[id_contrato] = (puntaje, capa_id, attrs_dict)

    deduplicados: list[dict[str, Any]] = []

    def _clave_orden(id_c: str) -> tuple[int, int | str]:
        return (0, int(id_c)) if id_c.isdigit() else (1, id_c)

    for id_contrato in sorted(ganadores.keys(), key=_clave_orden):
        _, capa_ganadora, attrs_dict = ganadores[id_contrato]
        deduplicados.append(
            {
                "id_contrato": id_contrato,
                "capa_ganadora": capa_ganadora,
                "capas_origen": sorted(capas_por_contrato[id_contrato]),
                "registros_geograficos_origen": conteo_por_contrato[id_contrato],
                "attributes": attrs_dict,
            }
        )

    for idx, (capa_id, attrs_dict) in enumerate(sin_id, start=1):
        deduplicados.append(
            {
                "id_contrato": None,
                "id_sin_contrato": f"sin_cod_contrato_{capa_id}_{idx}",
                "capa_ganadora": capa_id,
                "capas_origen": [capa_id],
                "registros_geograficos_origen": 1,
                "attributes": attrs_dict,
            }
        )

    estadisticas = {
        "total_registros_crudos": total_filas_crudas,
        "registros_crudos_por_capa": conteo_por_capa,
        "contratos_unicos": len(ganadores),
        "registros_sin_cod_contrato": len(sin_id),
        "duplicados_eliminados": total_filas_crudas - len(deduplicados),
    }
    return deduplicados, estadisticas


def _nombre_institucion_radial(institucion: str | None) -> str:
    if not institucion:
        return "un servicio del MOP sin identificar"
    limpio = institucion.strip()
    articulo = "la " if limpio.lower().startswith(("dirección", "direccion", "subdirección", "subdireccion", "secretaría", "secretaria")) else ""
    sufijo = "" if "mop" in limpio.lower() or "obras públicas" in limpio.lower() else " del MOP"
    return f"{articulo}{limpio}{sufijo}"


def _lugar_radial(comunas: Sequence[str]) -> str:
    if not comunas:
        return "la Región de Aysén"
    if len(comunas) == 1:
        return comunas[0]
    if len(comunas) == 2:
        return f"{comunas[0]} y {comunas[1]}"
    return ", ".join(comunas[:-1]) + f" y {comunas[-1]}"


def construir_frase_radial_proyecto(
    *,
    institucion: str | None,
    comunas: Sequence[str],
    estado: str | None,
    fecha_contratacion: str | None,
    administracion_contratacion: str | None,
    costo_total_presupuestado: Decimal | None,
    costo_total_contrato: Decimal | None,
    pagado_anio: Decimal | None,
    anio_corte: int,
    calidad_informacion: str,
) -> str:
    """Construye una frase ciudadana de una sola oración explicando contratación, gestión y pagos."""
    lugar = _lugar_radial(comunas)
    entidad = _nombre_institucion_radial(institucion)
    estado_norm = _normalizar_clave_texto(estado)

    if pagado_anio is None:
        tramo_pago = f"sin información verificable de pagos durante {anio_corte}"
    elif pagado_anio > CERO:
        tramo_pago = (
            f"durante {anio_corte} registra pagos por "
            f"{formatear_millones_clp_ciudadano(pagado_anio)}"
        )
    else:
        tramo_pago = f"durante {anio_corte} aún no registra pagos"

    if calidad_informacion != "documentado":
        return (
            f"Esta iniciativa en {lugar} a cargo de {entidad} cuenta con información "
            f"oficial insuficiente para verificar su fecha o condición de arrastre y "
            f"{tramo_pago}."
        )

    if "licitacion" in estado_norm or "adjudicacion" in estado_norm:
        etiqueta_estado = "en licitación" if "licitacion" in estado_norm else "en adjudicación"
        if costo_total_contrato is not None and costo_total_contrato > CERO:
            tramo_monto = (
                f"un monto contractual de "
                f"{formatear_millones_clp_ciudadano(costo_total_contrato)}"
            )
        elif costo_total_presupuestado is not None:
            tramo_monto = (
                f"un monto presupuestado de "
                f"{formatear_millones_clp_ciudadano(costo_total_presupuestado)}"
            )
        else:
            tramo_monto = "monto referencial no informado"

        if fecha_contratacion and administracion_contratacion:
            tramo_fecha = (
                f"inicio programado el {_fecha_iso_a_ciudadana(fecha_contratacion)} "
                f"({administracion_contratacion})"
            )
        else:
            tramo_fecha = "sin fecha oficial de inicio"
        return (
            f"Esta obra en {lugar} se encuentra {etiqueta_estado} a cargo de {entidad} "
            f"con {tramo_monto}, {tramo_fecha} y {tramo_pago}."
        )

    if fecha_contratacion and administracion_contratacion:
        tramo_contrato_fecha = (
            f"fue contratada por {entidad} el {_fecha_iso_a_ciudadana(fecha_contratacion)} "
            f"({administracion_contratacion})"
        )
    else:
        tramo_contrato_fecha = (
            f"figura a cargo de {entidad} sin fecha oficial de contratación registrada"
        )

    if costo_total_contrato is not None and costo_total_contrato > CERO:
        tramo_monto = (
            f"tiene un monto contractual de "
            f"{formatear_millones_clp_ciudadano(costo_total_contrato)}"
        )
    elif costo_total_presupuestado is not None:
        tramo_monto = (
            f"tiene un monto presupuestado de "
            f"{formatear_millones_clp_ciudadano(costo_total_presupuestado)}"
        )
    else:
        tramo_monto = "no informa monto contractual"

    return f"Esta obra en {lugar} {tramo_contrato_fecha}, {tramo_monto} y {tramo_pago}."


def _construir_linea_tiempo(
    *,
    institucion: str | None,
    codigo_bip: str | None,
    estado: str | None,
    contratista: str | None,
    avance_fisico_pct: str | None,
    fecha_contratacion: str | None,
    administracion_contratacion: str | None,
    fecha_termino_programada: str | None,
    administracion_termino: str | None,
    fecha_corte_registro: str | None,
    costo_total_presupuestado: Decimal | None,
    costo_total_contrato: Decimal | None,
    compromiso_anio: Decimal | None,
    pagado_anio: Decimal | None,
    pagado_anios_anteriores: Decimal | None,
    saldo_pendiente: Decimal | None,
    enlaces: Mapping[str, str | None],
    anio_corte: int,
) -> list[dict[str, Any]]:
    """Construye los 4 hitos ordenados del ciclo de obra sin inventar fechas."""
    url_proy = enlaces.get("ficha_proyecto_sipro")
    url_ctto = enlaces.get("ficha_contrato_sipro")
    url_mp = enlaces.get("mercado_publico")
    url_arcgis = enlaces.get("servicio_arcgis")

    # 1. Aprobación de financiamiento (el visor MOP no entrega fecha RS/BIP -> fecha=None)
    partes_aprob = []
    if codigo_bip:
        partes_aprob.append(f"Código BIP {codigo_bip}")
    if costo_total_presupuestado is not None:
        partes_aprob.append(
            f"monto presupuestado oficial de {formatear_millones_clp_ciudadano(costo_total_presupuestado)}"
        )
    partes_aprob.append(
        "la fecha de aprobación BIP/RS no viene publicada en la capa ArcGIS del MOP"
    )
    hito_aprobacion = {
        "hito": "aprobacion_financiamiento",
        "titulo": "Aprobación de financiamiento",
        "fecha": None,
        "institucion": institucion,
        "administracion": None,
        "detalle": "; ".join(partes_aprob) + ".",
        "documento_respaldo_label": (
            "Ficha de proyecto SIPRO MOP" if url_proy else "Servicio ArcGIS Visor Obras MOP"
        ),
        "documento_respaldo_url": url_proy or url_arcgis,
    }

    # 2. Contratación
    partes_ctto = []
    if estado:
        partes_ctto.append(f"Estado oficial: {estado}")
    if contratista:
        partes_ctto.append(f"contratista: {contratista}")
    if costo_total_contrato is not None:
        partes_ctto.append(
            f"monto contractual de {formatear_millones_clp_ciudadano(costo_total_contrato)}"
        )
    elif costo_total_presupuestado is not None:
        partes_ctto.append(
            f"sin monto contractual adjudicado (monto presupuestado: {formatear_millones_clp_ciudadano(costo_total_presupuestado)})"
        )
    if fecha_contratacion is None:
        partes_ctto.append("fecha de inicio de contrato no informada en el registro")
    hito_contratacion = {
        "hito": "contratacion",
        "titulo": "Contratación",
        "fecha": fecha_contratacion,
        "institucion": institucion,
        "administracion": administracion_contratacion,
        "detalle": "; ".join(partes_ctto) + "." if partes_ctto else "Sin antecedentes contractuales.",
        "documento_respaldo_label": (
            "Licitación en Mercado Público"
            if url_mp
            else ("Ficha de contrato SIPRO MOP" if url_ctto else "Servicio ArcGIS Visor Obras MOP")
        ),
        "documento_respaldo_url": url_mp or url_ctto or url_arcgis,
    }

    # 3. Pagos
    hay_pagos = (pagado_anio is not None and pagado_anio > CERO) or (
        pagado_anios_anteriores is not None and pagado_anios_anteriores > CERO
    )
    fecha_pago_hito = fecha_corte_registro if hay_pagos else None
    partes_pagos = []
    if pagado_anio is not None:
        partes_pagos.append(
            f"pagado en {anio_corte}: {formatear_millones_clp_ciudadano(pagado_anio)}"
        )
    if pagado_anios_anteriores is not None:
        partes_pagos.append(
            f"pagado en años anteriores: {formatear_millones_clp_ciudadano(pagado_anios_anteriores)}"
        )
    if compromiso_anio is not None:
        partes_pagos.append(
            f"compromiso presupuestario {anio_corte}: {formatear_millones_clp_ciudadano(compromiso_anio)}"
        )
    if saldo_pendiente is not None:
        partes_pagos.append(
            f"saldo pendiente del contrato: {formatear_millones_clp_ciudadano(saldo_pendiente)}"
        )
    if fecha_pago_hito:
        partes_pagos.append(
            f"cifra acumulada al corte oficial del visor MOP ({fecha_pago_hito})"
        )
    else:
        partes_pagos.append("sin pagos acumulados registrados al corte oficial")
    hito_pagos = {
        "hito": "pagos",
        "titulo": "Pagos y avance presupuestario",
        "fecha": fecha_pago_hito,
        "institucion": institucion,
        "administracion": clasificar_administracion(fecha_pago_hito),
        "detalle": "; ".join(partes_pagos) + ".",
        "documento_respaldo_label": (
            "Ficha de contrato SIPRO MOP" if url_ctto else "Servicio ArcGIS Visor Obras MOP"
        ),
        "documento_respaldo_url": url_ctto or url_arcgis,
    }

    # 4. Entrada en funcionamiento / término programado
    estado_norm = _normalizar_clave_texto(estado)
    partes_termino = []
    if estado_norm == "terminado":
        partes_termino.append("Obra informada como Terminada en el Visor MOP")
    elif fecha_termino_programada is not None:
        partes_termino.append("Fecha de término contractual programada (no acredita recepción definitiva)")
    else:
        partes_termino.append("Sin fecha de término informada")
    if avance_fisico_pct is not None:
        partes_termino.append(f"avance físico informado: {avance_fisico_pct}%")
    hito_funcionamiento = {
        "hito": "entrada_en_funcionamiento",
        "titulo": "Término programado / entrada en funcionamiento",
        "fecha": fecha_termino_programada,
        "institucion": institucion,
        "administracion": administracion_termino,
        "detalle": "; ".join(partes_termino) + ".",
        "documento_respaldo_label": (
            "Ficha de contrato SIPRO MOP" if url_ctto else "Servicio ArcGIS Visor Obras MOP"
        ),
        "documento_respaldo_url": url_ctto or url_arcgis,
    }

    return [hito_aprobacion, hito_contratacion, hito_pagos, hito_funcionamiento]


def normalizar_proyecto_mop(
    registro: Mapping[str, Any],
    *,
    anio_corte: int = 2026,
    fecha_cambio_admin: str | None = None,
    base_arcgis: str = BASE_ARCGIS_MOP,
) -> dict[str, Any]:
    """Normaliza un registro deduplicado MOP al esquema publicado exacto."""
    fecha_corte_admin = fecha_cambio_admin or fecha_cambio_administracion_para_anio(anio_corte)
    attrs = registro.get("attributes") if "attributes" in registro else registro
    if not isinstance(attrs, Mapping):
        raise MopProyectosError("Registro MOP inválido: se esperaba un diccionario de atributos.")

    id_contrato = registro.get("id_contrato")
    if id_contrato is None:
        id_contrato = _normalizar_id_contrato(attrs)

    capa_ganadora = registro.get("capa_ganadora")
    capas_origen = list(registro.get("capas_origen", []))
    registros_geograficos = int(registro.get("registros_geograficos_origen", 1))

    codigo_bip = _limpiar_texto(attrs.get("CODIGOBIP"))
    nombre_proyecto = _limpiar_texto(attrs.get("NOM_PROYECTO"))
    nombre_contrato = _limpiar_texto(attrs.get("NOM_CONTRATO"))
    institucion = _limpiar_texto(attrs.get("SERV_NOMBRE"))
    es_piloto_vialidad = bool(institucion and "vialidad" in institucion.lower())
    comunas = normalizar_comunas(attrs.get("COMUNAS"))
    estado = _limpiar_texto(attrs.get("ESTADO_1"))
    nuevo_o_arrastre = _normalizar_nuevo_arrastre(attrs.get("NUEVOARRASTRE"))
    contratista = _limpiar_texto(attrs.get("CONTRATISTA"))

    avance_dec = parsear_decimal_mop(attrs.get("AVANCE_FISICO"))
    avance_fisico_pct = formatear_decimal(avance_dec) if avance_dec is not None else None

    presup_mill = miles_a_millones_clp(attrs.get("MONTO_PRESUPUESTADO"))
    contrato_raw_mill = miles_a_millones_clp(attrs.get("MONTO_CONTRATO"))
    contrato_mill = (
        contrato_raw_mill
        if contrato_raw_mill is not None and contrato_raw_mill > CERO
        else None
    )
    compromiso_mill = miles_a_millones_clp(attrs.get("MONTO_AGNO_ACT"))
    pagado_mill = miles_a_millones_clp(attrs.get("PAGADO"))
    pagado_ant_mill = miles_a_millones_clp(attrs.get("PAGADO_AGNO_ANT"))
    saldo_mill = miles_a_millones_clp(attrs.get("SALDO"))

    fecha_contratacion = parsear_fecha_mop(attrs.get("FECHA_INICIO"))
    administracion_contratacion = clasificar_administracion(fecha_contratacion)
    firmado_antes: bool | None = (
        fecha_contratacion < fecha_corte_admin if fecha_contratacion is not None else None
    )

    fecha_termino = parsear_fecha_mop(attrs.get("FECHA_TERMINO"))
    administracion_termino = clasificar_administracion(fecha_termino)
    fecha_corte_registro = _parsear_epoch_ms_a_fecha_iso(attrs.get("last_edited_date"))

    motivos_insuficiencia: list[str] = []
    if not id_contrato:
        motivos_insuficiencia.append("falta_cod_contrato")
    if not institucion:
        motivos_insuficiencia.append("falta_serv_nombre")
    if fecha_contratacion is None and nuevo_o_arrastre == "sin_dato":
        motivos_insuficiencia.append("falta_fecha_contratacion_y_nuevo_arrastre")
    if compromiso_mill is None:
        motivos_insuficiencia.append("falta_monto_compromiso_anio")
    if pagado_mill is None:
        motivos_insuficiencia.append("falta_monto_pagado_anio")
    if presup_mill is None and contrato_mill is None:
        motivos_insuficiencia.append("falta_monto_presupuestado_y_contractual")

    calidad_informacion = "documentado" if not motivos_insuficiencia else "insuficiente"

    servicio_url = (
        f"{base_arcgis}/{capa_ganadora}" if capa_ganadora is not None else base_arcgis
    )
    enlaces_oficiales = {
        "ficha_proyecto_sipro": _normalizar_url(attrs.get("LINK_FICHA_PROY")),
        "ficha_contrato_sipro": _normalizar_url(attrs.get("LINK_FICHA_CTTO")),
        "mercado_publico": _normalizar_url(attrs.get("LINK_MERCADO_PUB")),
        "servicio_arcgis": servicio_url,
    }

    linea_tiempo = _construir_linea_tiempo(
        institucion=institucion,
        codigo_bip=codigo_bip,
        estado=estado,
        contratista=contratista,
        avance_fisico_pct=avance_fisico_pct,
        fecha_contratacion=fecha_contratacion,
        administracion_contratacion=administracion_contratacion,
        fecha_termino_programada=fecha_termino,
        administracion_termino=administracion_termino,
        fecha_corte_registro=fecha_corte_registro,
        costo_total_presupuestado=presup_mill,
        costo_total_contrato=contrato_mill,
        compromiso_anio=compromiso_mill,
        pagado_anio=pagado_mill,
        pagado_anios_anteriores=pagado_ant_mill,
        saldo_pendiente=saldo_mill,
        enlaces=enlaces_oficiales,
        anio_corte=anio_corte,
    )

    frase_radial = construir_frase_radial_proyecto(
        institucion=institucion,
        comunas=comunas,
        estado=estado,
        fecha_contratacion=fecha_contratacion,
        administracion_contratacion=administracion_contratacion,
        costo_total_presupuestado=presup_mill,
        costo_total_contrato=contrato_mill,
        pagado_anio=pagado_mill,
        anio_corte=anio_corte,
        calidad_informacion=calidad_informacion,
    )

    return {
        "id_contrato": id_contrato,
        "codigo_bip": codigo_bip,
        "nombre_proyecto": nombre_proyecto,
        "nombre_contrato": nombre_contrato,
        "institucion": institucion,
        "es_piloto_vialidad": es_piloto_vialidad,
        "comunas": comunas,
        "comunas_normalizadas": comunas,
        "es_multicomunal": len(comunas) > 1,
        "estado": estado,
        "nuevo_o_arrastre": nuevo_o_arrastre,
        "contratista": contratista,
        "avance_fisico_pct": avance_fisico_pct,
        "calidad_informacion": calidad_informacion,
        "motivos_insuficiencia": motivos_insuficiencia,
        "unidad_montos": "millones CLP",
        "costo_total_presupuestado_millones": (
            formatear_decimal(presup_mill) if presup_mill is not None else None
        ),
        "costo_total_contrato_millones": (
            formatear_decimal(contrato_mill) if contrato_mill is not None else None
        ),
        "compromiso_anio_millones": (
            formatear_decimal(compromiso_mill) if compromiso_mill is not None else None
        ),
        "pagado_anio_millones": (
            formatear_decimal(pagado_mill) if pagado_mill is not None else None
        ),
        "pagado_anios_anteriores_millones": (
            formatear_decimal(pagado_ant_mill) if pagado_ant_mill is not None else None
        ),
        "saldo_pendiente_millones": (
            formatear_decimal(saldo_mill) if saldo_mill is not None else None
        ),
        "fecha_contratacion": fecha_contratacion,
        "administracion_contratacion": administracion_contratacion,
        "firmado_antes_administracion_actual": firmado_antes,
        "fecha_termino_programada": fecha_termino,
        "administracion_termino": administracion_termino,
        "fecha_corte_visor": fecha_corte_registro,
        "capas_origen": capas_origen,
        "registros_geograficos_origen": registros_geograficos,
        "linea_tiempo": linea_tiempo,
        "enlaces_oficiales": enlaces_oficiales,
        "frase_radial": frase_radial,
    }


def _dec_opcional(valor: object) -> Decimal | None:
    if valor is None:
        return None
    return parsear_decimal_mop(valor)


def calcular_resumen_proyectos(
    proyectos: Sequence[Mapping[str, Any]],
    anio_corte: int = 2026,
    *,
    fecha_cambio_admin: str | None = None,
    etiqueta_ambito: str = "la cartera evaluada",
) -> dict[str, Any]:
    """Calcula por separado las dos preguntas clave y aísla proyectos insuficientes.

    Reutilizable ante cualquier filtro por comuna, institución o subconjunto.
    """
    fecha_corte_admin = fecha_cambio_admin or fecha_cambio_administracion_para_anio(anio_corte)

    documentados: list[Mapping[str, Any]] = []
    insuficientes: list[Mapping[str, Any]] = []
    for p in proyectos:
        if p.get("calidad_informacion") == "documentado":
            documentados.append(p)
        else:
            insuficientes.append(p)

    # Totales documentados (etapas siempre separadas, nunca sumadas entre sí)
    total_presup = CERO
    total_contrato = CERO
    total_compromiso_doc = CERO
    total_pagado_doc = CERO
    total_pagado_ant_doc = CERO
    total_saldo_doc = CERO

    # Pregunta 1: Pagos del año de contratos firmados antes del cambio de administración
    pagado_anteriores = CERO
    pagado_actual = CERO
    pagado_sin_fecha = CERO
    contratos_antes = 0
    contratos_antes_con_pagos = 0
    contratos_actual = 0
    contratos_actual_con_pagos = 0
    contratos_sin_fecha = 0

    # Pregunta 2: Arrastre presupuestario del ejercicio (compromiso anual MONTO_AGNO_ACT)
    compromiso_arrastre = CERO
    compromiso_nuevo = CERO
    compromiso_sin_marca = CERO
    contratos_arrastre = 0
    contratos_nuevos = 0
    contratos_sin_marca = 0

    with localcontext(CONTEXTO_DECIMAL):
        for p in documentados:
            presup = _dec_opcional(p.get("costo_total_presupuestado_millones"))
            ctto = _dec_opcional(p.get("costo_total_contrato_millones"))
            comp = _dec_opcional(p.get("compromiso_anio_millones"))
            pag = _dec_opcional(p.get("pagado_anio_millones"))
            pag_ant = _dec_opcional(p.get("pagado_anios_anteriores_millones"))
            saldo = _dec_opcional(p.get("saldo_pendiente_millones"))

            if presup is not None:
                total_presup += presup
            if ctto is not None:
                total_contrato += ctto
            if comp is not None:
                total_compromiso_doc += comp
            if pag is not None:
                total_pagado_doc += pag
            if pag_ant is not None:
                total_pagado_ant_doc += pag_ant
            if saldo is not None:
                total_saldo_doc += saldo

            # Evaluación Pregunta 1
            fecha_c = p.get("fecha_contratacion")
            if isinstance(fecha_c, str) and fecha_c:
                es_anterior = fecha_c < fecha_corte_admin
                if es_anterior:
                    contratos_antes += 1
                    if pag is not None:
                        pagado_anteriores += pag
                        if pag > CERO:
                            contratos_antes_con_pagos += 1
                else:
                    contratos_actual += 1
                    if pag is not None:
                        pagado_actual += pag
                        if pag > CERO:
                            contratos_actual_con_pagos += 1
            else:
                contratos_sin_fecha += 1
                if pag is not None:
                    pagado_sin_fecha += pag

            # Evaluación Pregunta 2
            marca = p.get("nuevo_o_arrastre")
            if marca == "arrastre":
                contratos_arrastre += 1
                if comp is not None:
                    compromiso_arrastre += comp
            elif marca == "nuevo":
                contratos_nuevos += 1
                if comp is not None:
                    compromiso_nuevo += comp
            else:
                contratos_sin_marca += 1
                if comp is not None:
                    compromiso_sin_marca += comp

        denom_pagos = pagado_anteriores + pagado_actual
        pct_pagos_anteriores = formatear_porcentaje(pagado_anteriores, denom_pagos)

        denom_arrastre = compromiso_arrastre + compromiso_nuevo
        pct_arrastre = formatear_porcentaje(compromiso_arrastre, denom_arrastre)

        # Aislamiento de información insuficiente
        insuf_compromiso = CERO
        insuf_pagado = CERO
        insuf_presup = CERO
        insuf_ids: list[str | None] = []
        for p in insuficientes:
            insuf_ids.append(p.get("id_contrato"))
            c_val = _dec_opcional(p.get("compromiso_anio_millones"))
            p_val = _dec_opcional(p.get("pagado_anio_millones"))
            pr_val = _dec_opcional(p.get("costo_total_presupuestado_millones"))
            if c_val is not None:
                insuf_compromiso += c_val
            if p_val is not None:
                insuf_pagado += p_val
            if pr_val is not None:
                insuf_presup += pr_val

    if pct_pagos_anteriores is not None:
        frase_pagos = (
            f"En {etiqueta_ambito}, de los {formatear_millones_clp_ciudadano(denom_pagos)} "
            f"pagados en {anio_corte} con fecha contractual verificada, "
            f"{formatear_millones_clp_ciudadano(pagado_anteriores)} "
            f"({formatear_porcentaje_ciudadano(pct_pagos_anteriores)}) corresponden a "
            f"{contratos_antes} contratos firmados antes del "
            f"{_fecha_iso_a_ciudadana(fecha_corte_admin)}."
        )
    else:
        frase_pagos = (
            f"En {etiqueta_ambito} no se registran pagos documentados con fecha "
            f"contractual verificada durante {anio_corte}."
        )

    if pct_arrastre is not None:
        frase_arrastre = (
            f"En {etiqueta_ambito}, del presupuesto comprometido en {anio_corte} "
            f"({formatear_millones_clp_ciudadano(denom_arrastre)} documentados), "
            f"{formatear_millones_clp_ciudadano(compromiso_arrastre)} "
            f"({formatear_porcentaje_ciudadano(pct_arrastre)}) corresponden a arrastre "
            f"comprometido de años anteriores en {contratos_arrastre} contratos."
        )
    else:
        frase_arrastre = (
            f"En {etiqueta_ambito} no existe presupuesto anual documentado con "
            f"clasificación oficial de arrastre para {anio_corte}."
        )

    return {
        "anio_corte": anio_corte,
        "fecha_cambio_administracion": fecha_corte_admin,
        "unidad": "millones CLP",
        "total_proyectos": len(proyectos),
        "proyectos_documentados": len(documentados),
        "proyectos_insuficientes": len(insuficientes),
        "totales_documentados_millones": {
            "costo_total_presupuestado_millones": formatear_decimal(total_presup),
            "costo_total_contrato_millones": formatear_decimal(total_contrato),
            "compromiso_anio_millones": formatear_decimal(total_compromiso_doc),
            "pagado_anio_millones": formatear_decimal(total_pagado_doc),
            "pagado_anios_anteriores_millones": formatear_decimal(total_pagado_ant_doc),
            "saldo_pendiente_millones": formatear_decimal(total_saldo_doc),
        },
        "pagos_contratos_administraciones_anteriores": {
            "pregunta": (
                "De lo pagado este año, ¿cuánto corresponde a contratos firmados "
                "antes de que asumiera esta administración?"
            ),
            "fecha_cambio_administracion": fecha_corte_admin,
            "monto_millones": formatear_decimal(pagado_anteriores),
            "total_pagado_anio_documentado_millones": formatear_decimal(denom_pagos),
            "porcentaje": pct_pagos_anteriores,
            "cantidad_contratos": contratos_antes,
            "cantidad_contratos_con_pagos": contratos_antes_con_pagos,
            "total_contratos_evaluados": contratos_antes + contratos_actual,
            "contratos_administracion_actual": {
                "cantidad_contratos": contratos_actual,
                "cantidad_contratos_con_pagos": contratos_actual_con_pagos,
                "monto_millones": formatear_decimal(pagado_actual),
            },
            "sin_fecha_contratacion_excluidos": {
                "cantidad_contratos": contratos_sin_fecha,
                "monto_millones": formatear_decimal(pagado_sin_fecha),
            },
            "frase_radial": frase_pagos,
        },
        "arrastre_presupuesto_inversion": {
            "pregunta": (
                "Del presupuesto de inversión de este año, ¿cuánto ya estaba "
                "comprometido por proyectos de años anteriores?"
            ),
            "monto_millones": formatear_decimal(compromiso_arrastre),
            "total_compromiso_anio_documentado_millones": formatear_decimal(denom_arrastre),
            "porcentaje": pct_arrastre,
            "cantidad_contratos": contratos_arrastre,
            "total_contratos_evaluados": contratos_arrastre + contratos_nuevos,
            "contratos_nuevos": {
                "cantidad_contratos": contratos_nuevos,
                "monto_millones": formatear_decimal(compromiso_nuevo),
            },
            "sin_clasificacion_arrastre_excluidos": {
                "cantidad_contratos": contratos_sin_marca,
                "monto_millones": formatear_decimal(compromiso_sin_marca),
            },
            "frase_radial": frase_arrastre,
        },
        "informacion_insuficiente": {
            "cantidad_contratos": len(insuficientes),
            "compromiso_anio_millones": formatear_decimal(insuf_compromiso),
            "pagado_anio_millones": formatear_decimal(insuf_pagado),
            "costo_total_presupuestado_millones": formatear_decimal(insuf_presup),
            "ids_contratos": insuf_ids,
            "nota": (
                "Contratos sin fecha de contratación ni marca oficial de arrastre, o "
                "sin montos clave verificables. Se informan por separado y no se "
                "incluyen en los denominadores de arrastre ni de pagos por administración."
            ),
        },
    }


def _consultar_url_bytes(url: str, *, timeout: int = TIMEOUT_DEFAULT) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except HTTPError as err:
        raise MopProyectosError(f"Error HTTP {err.code} al consultar MOP ArcGIS: {url}") from err
    except URLError as err:
        raise MopProyectosError(f"Error de red al consultar MOP ArcGIS: {err.reason}") from err


def consultar_capa_arcgis(
    capa_id: int,
    *,
    region_codigo: int = REGION_AYSEN_CODIGO,
    base_arcgis: str = BASE_ARCGIS_MOP,
    timeout: int = TIMEOUT_DEFAULT,
    fetcher: Callable[[str], bytes] | None = None,
) -> list[dict[str, Any]]:
    """Consulta una capa ArcGIS REST del MOP soportando paginación si `exceededTransferLimit`."""
    obtener = fetcher or (lambda u: _consultar_url_bytes(u, timeout=timeout))
    paginas: list[dict[str, Any]] = []
    offset = 0
    pagina_num = 1

    while pagina_num <= MAX_PAGINAS_POR_CAPA:
        params: dict[str, Any] = {
            "where": f"REG_CODIGO={region_codigo}",
            "outFields": "*",
            "returnGeometry": "false",
            "f": "json",
        }
        if offset > 0:
            params["resultOffset"] = offset
        url = f"{base_arcgis}/{capa_id}/query?{urlencode(params)}"
        cuerpo_bytes = obtener(url)
        try:
            datos = json.loads(cuerpo_bytes.decode("utf-8"), parse_float=Decimal)
        except (UnicodeDecodeError, json.JSONDecodeError) as err:
            raise MopProyectosError(
                f"Respuesta JSON inválida en capa {capa_id} página {pagina_num}."
            ) from err

        if isinstance(datos, dict) and "error" in datos:
            raise MopProyectosError(
                f"Error ArcGIS en capa {capa_id}: {datos['error']}"
            )
        if not isinstance(datos, dict) or not isinstance(datos.get("features"), list):
            raise MopProyectosError(
                f"Esquema ArcGIS inesperado en capa {capa_id} página {pagina_num}."
            )

        features = datos["features"]
        paginas.append(
            {
                "capa": capa_id,
                "pagina": pagina_num,
                "url": url,
                "bytes_crudos": cuerpo_bytes,
                "registros": len(features),
                "exceeded_transfer_limit": bool(datos.get("exceededTransferLimit")),
            }
        )

        if not datos.get("exceededTransferLimit") or len(features) == 0:
            break
        offset += len(features)
        pagina_num += 1
    else:
        raise MopProyectosError(
            f"Se excedió el máximo de {MAX_PAGINAS_POR_CAPA} páginas en capa {capa_id}."
        )

    return paginas


def construir_lote_publicado(
    paginas_por_capa: Sequence[tuple[int, Sequence[bytes]]],
    *,
    extraido_en: str,
    anio_corte: int = 2026,
    fecha_cambio_admin: str | None = None,
    region_codigo: int = REGION_AYSEN_CODIGO,
    base_arcgis: str = BASE_ARCGIS_MOP,
    artefactos_trazabilidad: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Transforma respuestas JSON crudas (bytes) de capas 0/1/2 en el lote publicado."""
    fecha_corte_admin = fecha_cambio_admin or fecha_cambio_administracion_para_anio(anio_corte)

    registros_por_capa: list[tuple[int, list[Mapping[str, Any]]]] = []
    fechas_edicion: list[str] = []

    for capa_id, lista_bytes in paginas_por_capa:
        features_capa: list[Mapping[str, Any]] = []
        for raw_bytes in lista_bytes:
            datos = json.loads(raw_bytes.decode("utf-8"), parse_float=Decimal)
            if not isinstance(datos, dict) or not isinstance(datos.get("features"), list):
                raise MopProyectosError(
                    f"Contenido JSON crudo inválido para capa {capa_id}."
                )
            for feat in datos["features"]:
                if isinstance(feat, Mapping):
                    features_capa.append(feat)
                    attrs = feat.get("attributes") if "attributes" in feat else feat
                    if isinstance(attrs, Mapping):
                        f_ed = _parsear_epoch_ms_a_fecha_iso(attrs.get("last_edited_date"))
                        if f_ed:
                            fechas_edicion.append(f_ed)
        registros_por_capa.append((capa_id, features_capa))

    deduplicados, stats_dedup = deduplicar_registros_mop(registros_por_capa)
    proyectos = [
        normalizar_proyecto_mop(
            reg,
            anio_corte=anio_corte,
            fecha_cambio_admin=fecha_corte_admin,
            base_arcgis=base_arcgis,
        )
        for reg in deduplicados
    ]

    proyectos_vialidad = [p for p in proyectos if p["es_piloto_vialidad"]]

    resumen_total = calcular_resumen_proyectos(
        proyectos,
        anio_corte=anio_corte,
        fecha_cambio_admin=fecha_corte_admin,
        etiqueta_ambito="el total de obras MOP en Aysén",
    )
    resumen_vialidad = calcular_resumen_proyectos(
        proyectos_vialidad,
        anio_corte=anio_corte,
        fecha_cambio_admin=fecha_corte_admin,
        etiqueta_ambito="el piloto Dirección de Vialidad del MOP en Aysén",
    )

    instituciones = sorted({p["institucion"] for p in proyectos if p["institucion"]})
    por_institucion: dict[str, Any] = {}
    for inst in instituciones:
        sub = [p for p in proyectos if p["institucion"] == inst]
        por_institucion[inst] = calcular_resumen_proyectos(
            sub,
            anio_corte=anio_corte,
            fecha_cambio_admin=fecha_corte_admin,
            etiqueta_ambito=f"{inst} en Aysén",
        )

    comunas_presentes = [
        c for c in _ORDEN_COMUNAS_AYSEN if any(c in p["comunas"] for p in proyectos)
    ]
    for p in proyectos:
        for c in p["comunas"]:
            if c not in comunas_presentes:
                comunas_presentes.append(c)

    por_comuna: dict[str, Any] = {}
    for comuna in comunas_presentes:
        sub = [p for p in proyectos if comuna in p["comunas"]]
        por_comuna[comuna] = calcular_resumen_proyectos(
            sub,
            anio_corte=anio_corte,
            fecha_cambio_admin=fecha_corte_admin,
            etiqueta_ambito=f"las obras MOP en {comuna}",
        )

    corte_oficial_visor = max(fechas_edicion) if fechas_edicion else None

    return {
        "version_esquema": VERSION_ESQUEMA_PUBLICADO,
        "publicacion": {
            "id": f"mop-aysen-{anio_corte}",
            "region_codigo": region_codigo,
            "region_nombre": REGION_AYSEN_NOMBRE,
            "anio_corte": anio_corte,
            "fecha_cambio_administracion": fecha_corte_admin,
            "corte_oficial_visor": corte_oficial_visor,
            "extraido_en": extraido_en,
            "unidad_origen": "miles CLP",
            "unidad_publicada": "millones CLP",
            "notas_metodologicas": [
                (
                    "Los montos provienen del servicio ArcGIS REST oficial DGOP/VISOR_OBRA_MOP "
                    "expresados originalmente en miles CLP y convertidos a millones CLP mediante "
                    "división exacta por 1000 con Decimal(34)."
                ),
                (
                    "Deduplicación estricta por COD_CONTRATO entre capas 0 (Puntos), 1 (Líneas) "
                    "y 2 (Línea-Punto), conservando el registro de mayor completitud de montos y fechas."
                ),
                (
                    "Se separan estrictamente las etapas contables (presupuestado, contrato plurianual, "
                    "compromiso anual MONTO_AGNO_ACT, pagado del año, pagado años anteriores y saldo) "
                    "y nunca se suman etapas incompatibles."
                ),
                (
                    "La pregunta sobre pagos de contratos firmados antes de la administración actual "
                    "se calcula exclusivamente con fecha_contratacion < fecha_cambio_administracion, "
                    "mientras el arrastre presupuestario se calcula exclusivamente con el compromiso "
                    "anual (MONTO_AGNO_ACT) de proyectos clasificados como 'arrastre' (NUEVOARRASTRE='A')."
                ),
                (
                    "Los proyectos con información insuficiente se informan en bloque separado y no "
                    "contaminan los denominadores de porcentaje."
                ),
                (
                    "En el desglose por_comuna los proyectos multicomunales aparecen en cada comuna "
                    "cubierta, por lo que los subtotales comunales no deben sumarse entre sí para "
                    "reconstruir el total regional."
                ),
            ],
        },
        "deduplicacion": stats_dedup,
        "resumen_arrastre_y_pagos": {
            "total_mop_aysen": resumen_total,
            "piloto_direccion_vialidad": resumen_vialidad,
            "por_institucion": por_institucion,
            "por_comuna": por_comuna,
        },
        "proyectos": proyectos,
        "fuente_trazabilidad": {
            "institucion": "Ministerio de Obras Públicas (MOP) — Dirección General de Obras Públicas (DGOP)",
            "servicio_arcgis": base_arcgis,
            "filtro_where": f"REG_CODIGO={region_codigo}",
            "capas": [{"id": cid, "nombre": nombre} for cid, nombre in CAPAS_MOP],
            "corte_oficial_visor": corte_oficial_visor,
            "extraido_en": extraido_en,
            "artefactos_raw": list(artefactos_trazabilidad or []),
        },
    }


def _escribir_json_canonico(ruta: Path, payload: Mapping[str, Any]) -> bytes:
    contenido = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)
    return contenido


def ejecutar_extraccion_mop(
    *,
    insumos_dir: Path,
    salida: Path,
    anio_corte: int = 2026,
    fecha_cambio_admin: str | None = None,
    region_codigo: int = REGION_AYSEN_CODIGO,
    base_arcgis: str = BASE_ARCGIS_MOP,
    timeout: int = TIMEOUT_DEFAULT,
    extraido_en: str | None = None,
    fetcher: Callable[[str], bytes] | None = None,
) -> dict[str, Any]:
    """Extrae capas 0/1/2 desde MOP ArcGIS, archiva JSON crudos + manifiesto SHA-256 y publica."""
    timestamp_iso = extraido_en or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    fecha_corte_admin = fecha_cambio_admin or fecha_cambio_administracion_para_anio(anio_corte)
    insumos_dir.mkdir(parents=True, exist_ok=True)

    artefactos: list[dict[str, Any]] = []
    paginas_por_capa: list[tuple[int, list[bytes]]] = []

    for capa_id, capa_nombre in CAPAS_MOP:
        paginas = consultar_capa_arcgis(
            capa_id,
            region_codigo=region_codigo,
            base_arcgis=base_arcgis,
            timeout=timeout,
            fetcher=fetcher,
        )
        lista_bytes: list[bytes] = []
        for pag in paginas:
            raw_bytes: bytes = pag["bytes_crudos"]
            lista_bytes.append(raw_bytes)
            nombre_archivo = (
                f"capa-{capa_id}.json"
                if len(paginas) == 1
                else f"capa-{capa_id}-pagina-{pag['pagina']}.json"
            )
            ruta_raw = insumos_dir / nombre_archivo
            ruta_raw.write_bytes(raw_bytes)
            artefactos.append(
                {
                    "capa": capa_id,
                    "nombre_capa": capa_nombre,
                    "pagina": pag["pagina"],
                    "archivo": nombre_archivo,
                    "sha256": _sha256_bytes(raw_bytes),
                    "bytes": len(raw_bytes),
                    "registros": pag["registros"],
                    "exceeded_transfer_limit": pag["exceeded_transfer_limit"],
                    "url": pag["url"],
                }
            )
        paginas_por_capa.append((capa_id, lista_bytes))

    manifiesto = {
        "version_esquema": VERSION_ESQUEMA_RAW,
        "fuente": base_arcgis,
        "region_codigo": region_codigo,
        "anio_corte": anio_corte,
        "fecha_cambio_administracion": fecha_corte_admin,
        "extraido_en": timestamp_iso,
        "artefactos": artefactos,
    }
    _escribir_json_canonico(insumos_dir / "manifiesto.json", manifiesto)

    lote = construir_lote_publicado(
        paginas_por_capa,
        extraido_en=timestamp_iso,
        anio_corte=anio_corte,
        fecha_cambio_admin=fecha_corte_admin,
        region_codigo=region_codigo,
        base_arcgis=base_arcgis,
        artefactos_trazabilidad=artefactos,
    )
    salida_bytes = _escribir_json_canonico(salida, lote)

    return {
        "insumos": str(insumos_dir),
        "salida": str(salida),
        "salida_sha256": _sha256_bytes(salida_bytes),
        "publicacion": lote["publicacion"],
        "deduplicacion": lote["deduplicacion"],
        "resumen_arrastre_y_pagos": lote["resumen_arrastre_y_pagos"],
    }


def verificar_manifiesto_raw(insumos_dir: Path) -> tuple[dict[str, Any], list[tuple[int, list[bytes]]]]:
    """Verifica `manifiesto.json` y el SHA-256 de cada artefacto raw sin acceso a red."""
    ruta_manifiesto = insumos_dir / "manifiesto.json"
    if not ruta_manifiesto.is_file():
        raise MopProyectosError(f"No existe manifiesto.json en {insumos_dir}.")

    try:
        manifiesto = json.loads(ruta_manifiesto.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise MopProyectosError(f"No se pudo leer manifiesto.json: {err}") from err

    if manifiesto.get("version_esquema") != VERSION_ESQUEMA_RAW:
        raise MopProyectosError(
            f"Versión de manifiesto no soportada: {manifiesto.get('version_esquema')!r}."
        )

    artefactos = manifiesto.get("artefactos")
    if not isinstance(artefactos, list) or not artefactos:
        raise MopProyectosError("El manifiesto no contiene artefactos válidos.")

    por_capa: dict[int, list[tuple[int, bytes]]] = {}
    for art in artefactos:
        nombre = art.get("archivo")
        sha_esperado = art.get("sha256")
        capa_id = art.get("capa")
        pagina = int(art.get("pagina", 1))
        if not isinstance(nombre, str) or not isinstance(sha_esperado, str) or not isinstance(capa_id, int):
            raise MopProyectosError("Artefacto malformado en manifiesto.json.")

        ruta_archivo = (insumos_dir / nombre).resolve()
        try:
            ruta_archivo.relative_to(insumos_dir.resolve())
        except ValueError as err:
            raise MopProyectosError(f"Ruta de artefacto fuera del directorio raw: {nombre}") from err
        if not ruta_archivo.is_file():
            raise MopProyectosError(f"Falta el archivo raw declarado en manifiesto: {nombre}")

        raw_bytes = ruta_archivo.read_bytes()
        sha_real = _sha256_bytes(raw_bytes)
        if sha_real != sha_esperado:
            raise MopProyectosError(
                f"SHA-256 inválido para {nombre}: esperado {sha_esperado}, observado {sha_real}."
            )
        por_capa.setdefault(capa_id, []).append((pagina, raw_bytes))

    paginas_ordenadas: list[tuple[int, list[bytes]]] = []
    for capa_id in sorted(por_capa.keys()):
        paginas = [b for _, b in sorted(por_capa[capa_id], key=lambda item: item[0])]
        paginas_ordenadas.append((capa_id, paginas))

    return manifiesto, paginas_ordenadas


def reproducir_desde_raw(insumos_dir: Path, salida: Path) -> dict[str, Any]:
    """Reconstruye `proyectos-mop-aysen.json` bit-a-bit desde un directorio raw verificado."""
    manifiesto, paginas_por_capa = verificar_manifiesto_raw(insumos_dir)
    lote = construir_lote_publicado(
        paginas_por_capa,
        extraido_en=manifiesto["extraido_en"],
        anio_corte=int(manifiesto["anio_corte"]),
        fecha_cambio_admin=manifiesto.get("fecha_cambio_administracion"),
        region_codigo=int(manifiesto.get("region_codigo", REGION_AYSEN_CODIGO)),
        base_arcgis=manifiesto.get("fuente", BASE_ARCGIS_MOP),
        artefactos_trazabilidad=manifiesto["artefactos"],
    )
    salida_bytes = _escribir_json_canonico(salida, lote)
    return {
        "insumos": str(insumos_dir),
        "salida": str(salida),
        "salida_sha256": _sha256_bytes(salida_bytes),
        "publicacion": lote["publicacion"],
        "deduplicacion": lote["deduplicacion"],
        "resumen_arrastre_y_pagos": lote["resumen_arrastre_y_pagos"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extracción y auditoría oficial de proyectos MOP en la Región de Aysén "
            "(piloto Dirección de Vialidad y obras MOP)."
        )
    )
    parser.add_argument(
        "--reproducir",
        action="store_true",
        help="Reconstruye --salida bit-a-bit desde --insumos verificando SHA-256 sin red.",
    )
    parser.add_argument(
        "--insumos",
        type=Path,
        default=None,
        help="Directorio raw (obligatorio con --reproducir; por defecto data/raw/mop-aysen-<timestamp>).",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=_SALIDA_DEFAULT,
        help=f"Ruta de publicación JSON (predeterminado: {_SALIDA_DEFAULT}).",
    )
    parser.add_argument(
        "--anio-corte",
        type=int,
        default=2026,
        help="Año de corte presupuestario para el cálculo de arrastre y pagos (predeterminado: 2026).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT_DEFAULT,
        help=f"Timeout HTTP en segundos (predeterminado: {TIMEOUT_DEFAULT}).",
    )
    args = parser.parse_args(argv)

    try:
        if args.reproducir:
            if args.insumos is None:
                parser.exit(2, "En modo --reproducir debe indicar --insumos <directorio-raw>.\n")
            resumen = reproducir_desde_raw(args.insumos, args.salida)
        else:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            insumos_dir = args.insumos or (_RAIZ_REPO / "data" / "raw" / f"mop-aysen-{stamp}")
            resumen = ejecutar_extraccion_mop(
                insumos_dir=insumos_dir,
                salida=args.salida,
                anio_corte=args.anio_corte,
                timeout=args.timeout,
            )
    except MopProyectosError as err:
        parser.exit(1, f"{err}\n")

    dedup = resumen["deduplicacion"]
    tot = resumen["resumen_arrastre_y_pagos"]["total_mop_aysen"]
    vial = resumen["resumen_arrastre_y_pagos"]["piloto_direccion_vialidad"]
    print(
        f"MOP Aysén | crudos={dedup['total_registros_crudos']} "
        f"unicos={dedup['contratos_unicos']} "
        f"vialidad={vial['total_proyectos']} "
        f"pagos_ant_pct={tot['pagos_contratos_administraciones_anteriores']['porcentaje']} "
        f"arrastre_pct={tot['arrastre_presupuesto_inversion']['porcentaje']} "
        f"sha256={resumen['salida_sha256'][:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
