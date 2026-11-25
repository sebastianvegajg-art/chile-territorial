"""Conector oficial en vivo para DIPRES (datos.gob.cl CKAN API) y Presupuesto Abierto.

Consulta la ejecución presupuestaria del Gobierno Central y el financiamiento
del Gobierno Regional de Aysén (Región 11) directamente desde el catálogo CKAN
oficial de `datos.gob.cl`, preservando:
- Separación estricta entre ingresos/financiamiento (subtítulos 01–15) y gasto
  directo (gasto corriente 21–26, inversión 29–31, transferencias de capital 33).
- Aritmética exacta con ``Decimal`` (sin ``float`` en agregaciones ni ratios),
  convirtiendo desde ``miles CLP`` a ``millones CLP`` dividiendo por ``1000``.
- Deduplicación estricta por ``_id`` entre consultas CKAN y exclusión de filas
  de subtotales/totales o en moneda distinta a CLP.
- Brechas explícitas (``ratio_corriente_sobre_inversion_pct = None`` con
  ``motivo_brecha``) cuando el recurso CKAN no contiene ambos componentes,
  sin inventar cifras.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import json
import math
import os
from pathlib import Path
import re
import time
from typing import Any, Callable, Mapping, Sequence
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CKAN_BASE = "https://datos.gob.cl/api/3/action"
PRESUPUESTO_ABIERTO_BASE = "https://api.presupuestoabierto.gob.cl"

PRECISION_DECIMAL = 34
CONTEXTO_DECIMAL = Context(prec=PRECISION_DECIMAL)
CERO = Decimal("0")
MIL = Decimal("1000")
CIEN = Decimal("100")

CACHE_TTL_SEGUNDOS = 12 * 3600
TIMEOUT_CKAN_SEGUNDOS = 25
TIMEOUT_PRESUPUESTO_ABIERTO_SEGUNDOS = 10
USER_AGENT = "ChileTerritorial/1.0 (+https://datos.gob.cl)"
LIMITE_PAGINA_CKAN = 1000
MAX_REGISTROS_POR_CONSULTA = 10000

_RAIZ_REPO = Path(__file__).resolve().parents[2]

_SUBTITULOS_GASTO_CORRIENTE = frozenset({"21", "22", "23", "24", "25", "26"})
_SUBTITULOS_INVERSION = frozenset({"29", "30", "31"})
_SUBTITULOS_TRANSFERENCIAS_CAPITAL = frozenset({"33"})
_SUBTITULOS_INGRESOS_FINANCIAMIENTO = frozenset(f"{n:02d}" for n in range(1, 16))

_MESES_ORDEN: tuple[tuple[str, int], ...] = (
    ("diciembre", 12),
    ("noviembre", 11),
    ("octubre", 10),
    ("septiembre", 9),
    ("agosto", 8),
    ("julio", 7),
    ("junio", 6),
    ("mayo", 5),
    ("abril", 4),
    ("marzo", 3),
    ("febrero", 2),
    ("enero", 1),
)
_MESES_VARIANTES_ORDEN: tuple[tuple[str, int], ...] = (
    ("setiembre", 9),
    ("dic", 12),
    ("nov", 11),
    ("oct", 10),
    ("sept", 9),
    ("sep", 9),
    ("ago", 8),
    ("jul", 7),
    ("jun", 6),
    ("may", 5),
    ("abr", 4),
    ("mar", 3),
    ("feb", 2),
    ("ene", 1),
)
_MESES_NOMBRE_POR_NUMERO: dict[int, str] = {num: nombre for nombre, num in _MESES_ORDEN}

ESTADO_ACTUALIZACION_VIVO = "actualizado_en_vivo"
ESTADO_ACTUALIZACION_CACHE = "cache_vigente"
ESTADO_ACTUALIZACION_RESPALDO = "respaldo_ultimo_corte_aprobado"

_PATRON_MILES_PUNTO = re.compile(r"^[1-9]\d{0,2}(?:\.\d{3})+$")
_PATRON_MILES_COMA = re.compile(r"^[1-9]\d{0,2}(?:,\d{3}){2,}$")
_PATRON_ENTERO_CON_DECIMALES_CL = re.compile(r"^\d{1,3}(?:\.\d{3})+,\d+$")
_PATRON_ENTERO_CON_DECIMALES_US = re.compile(r"^\d{1,3}(?:,\d{3})+\.\d+$")
_VALORES_VACIOS = frozenset(
    {"", "-", "--", "---", "–", "—", "n/a", "na", "nd", "s/i", "sd", "null", "none"}
)


class DipresCkanError(RuntimeError):
    """Error controlado al consultar o interpretar recursos CKAN de DIPRES."""


def _normalizar_texto(valor: object) -> str:
    """Devuelve texto en minúsculas sin tildes y con espacios colapsados."""
    if valor is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(valor))
    sin_tildes = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


def _contiene_aysen(valor: object) -> bool:
    """Detecta referencias explícitas a Aysén (con o sin tilde / grafía histórica)."""
    norm = _normalizar_texto(valor)
    return "ays" in norm or "aisen" in norm


def _formatear_decimal(valor: Decimal) -> str:
    """Convierte un Decimal exacto a cadena sin notación científica ni '-0'."""
    with localcontext(CONTEXTO_DECIMAL):
        if valor == CERO:
            return "0"
        normalizado = valor.normalize()
        texto = format(normalizado, "f")
        if "." in texto:
            texto = texto.rstrip("0").rstrip(".")
        return "0" if texto in {"", "-0"} else texto


def _a_millones_clp(miles_clp: Decimal) -> Decimal:
    """Convierte miles CLP a millones CLP con división decimal exacta por 1000."""
    with localcontext(CONTEXTO_DECIMAL):
        return miles_clp / MIL


def _extraer_codigo_subtitulo(subtitulo: object) -> str:
    """Extrae el código de subtítulo de dos dígitos (ej. '5' -> '05', '21' -> '21')."""
    if subtitulo is None:
        return ""
    texto = str(subtitulo).strip()
    if not texto:
        return ""
    coincidencia = re.search(r"\d+", texto)
    if not coincidencia:
        return ""
    numero = int(coincidencia.group(0))
    return f"{numero:02d}"


def clasificar_subtitulo(subtitulo: str) -> str:
    """Clasifica un subtítulo presupuestario DIPRES en su categoría fiscal canónica.

    Reglas:
    - Subtítulos 21, 22, 23, 24, 25, 26 -> ``"gasto_corriente"``
    - Subtítulos 29, 30, 31 -> ``"inversion"``
    - Subtítulo 33 -> ``"transferencias_capital"``
    - Subtítulos 01..15 -> ``"ingresos_financiamiento"`` (NUNCA sumar como gasto)
    - Otros -> ``"otros_gastos"``
    """
    codigo = _extraer_codigo_subtitulo(subtitulo)
    if codigo in _SUBTITULOS_GASTO_CORRIENTE:
        return "gasto_corriente"
    if codigo in _SUBTITULOS_INVERSION:
        return "inversion"
    if codigo in _SUBTITULOS_TRANSFERENCIAS_CAPITAL:
        return "transferencias_capital"
    if codigo in _SUBTITULOS_INGRESOS_FINANCIAMIENTO:
        return "ingresos_financiamiento"
    return "otros_gastos"


def parsear_monto_dipres(raw: object) -> Decimal | None:
    """Parsea montos chilenos de DIPRES CKAN a ``Decimal`` exacto (sin float).

    Soporta:
    - Separadores de miles con punto (ej. ``"7.011.531"`` -> ``Decimal("7011531")``).
    - Decimales con coma o punto (ej. ``"1.234,56"``, ``"123,45"``, ``"123.45"``).
    - Negativos con signo ``-`` o paréntesis contables ``(1.250)``.
    - Valores vacíos, guiones ``"-"`` o etiquetas faltantes -> ``None``.
    """
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, Decimal):
        return raw if raw.is_finite() else None
    if isinstance(raw, int):
        return Decimal(raw)
    if isinstance(raw, float):
        if not math.isfinite(raw):
            return None
        return Decimal(str(raw))

    texto = str(raw).strip()
    if not texto:
        return None

    # Limpieza de símbolos monetarios y espacios no separables.
    texto = texto.replace("\xa0", " ").replace("\u2009", " ").strip()
    if texto.lower() in _VALORES_VACIOS:
        return None

    negativo = False
    if texto.startswith("(") and texto.endswith(")"):
        negativo = True
        texto = texto[1:-1].strip()

    texto = re.sub(r"^(?:mm?\$|clp|us\$|\$)\s*", "", texto, flags=re.IGNORECASE).strip()
    texto = re.sub(r"\s*(?:clp|m\$|mm\$)$", "", texto, flags=re.IGNORECASE).strip()
    if texto.lower() in _VALORES_VACIOS:
        return None

    if texto.startswith("-"):
        negativo = not negativo
        texto = texto[1:].strip()
    elif texto.startswith("+"):
        texto = texto[1:].strip()

    # Eliminar espacios internos usados como separador de miles.
    texto = re.sub(r"\s+", "", texto)
    if not texto or texto.lower() in _VALORES_VACIOS:
        return None

    normalizado: str
    tiene_punto = "." in texto
    tiene_coma = "," in texto

    if tiene_punto and tiene_coma:
        if _PATRON_ENTERO_CON_DECIMALES_CL.match(texto) or texto.rfind(",") > texto.rfind("."):
            normalizado = texto.replace(".", "").replace(",", ".")
        elif _PATRON_ENTERO_CON_DECIMALES_US.match(texto) or texto.rfind(".") > texto.rfind(","):
            normalizado = texto.replace(",", "")
        else:
            return None
    elif tiene_punto:
        if _PATRON_MILES_PUNTO.match(texto):
            normalizado = texto.replace(".", "")
        elif texto.count(".") > 1:
            # Múltiples puntos solo son válidos si forman grupos de miles.
            return None
        else:
            normalizado = texto
    elif tiene_coma:
        if _PATRON_MILES_COMA.match(texto):
            normalizado = texto.replace(",", "")
        elif texto.count(",") == 1:
            normalizado = texto.replace(",", ".")
        else:
            return None
    else:
        normalizado = texto

    if negativo:
        normalizado = f"-{normalizado}"

    with localcontext(CONTEXTO_DECIMAL):
        try:
            resultado = Decimal(normalizado)
        except InvalidOperation:
            return None
    if not resultado.is_finite():
        return None
    return resultado


def _http_get_json(url: str, timeout: int = TIMEOUT_CKAN_SEGUNDOS) -> dict[str, Any]:
    """Ejecuta una solicitud HTTP GET y decodifica JSON."""
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            cuerpo = resp.read().decode("utf-8")
    except HTTPError as exc:
        raise DipresCkanError(f"Error HTTP {exc.code} al consultar CKAN: {url}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise DipresCkanError(f"Error de red al consultar CKAN ({type(exc).__name__}): {url}") from exc
    try:
        data = json.loads(cuerpo)
    except json.JSONDecodeError as exc:
        raise DipresCkanError(f"Respuesta JSON inválida desde CKAN: {url}") from exc
    if not isinstance(data, dict):
        raise DipresCkanError(f"Respuesta inesperada de CKAN (se esperaba objeto JSON): {url}")
    return data


def _consultar_presupuesto_abierto(
    timeout: int = TIMEOUT_PRESUPUESTO_ABIERTO_SEGUNDOS,
) -> dict[str, Any]:
    """Verifica disponibilidad del endpoint oficial ``/about-data`` sin tumbar el flujo."""
    url = f"{PRESUPUESTO_ABIERTO_BASE}/about-data"
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            resp.read(2048)
        disponible = isinstance(status, int) and 200 <= status < 300
        return {
            "url": url,
            "disponible": disponible,
            "http_status": status,
            "nota": (
                "Endpoint oficial Presupuesto Abierto disponible (descargas mensualizadas tras cierre contable)."
                if disponible
                else f"Presupuesto Abierto respondió HTTP {status}."
            ),
        }
    except HTTPError as exc:
        return {
            "url": url,
            "disponible": False,
            "http_status": exc.code,
            "nota": f"Presupuesto Abierto devolvió HTTP {exc.code}.",
        }
    except (URLError, TimeoutError, OSError) as exc:
        return {
            "url": url,
            "disponible": False,
            "http_status": None,
            "nota": f"No se pudo conectar a Presupuesto Abierto ({type(exc).__name__}).",
        }


def _ckan_action(
    accion: str,
    params: Mapping[str, Any],
    http_get_json: Callable[[str, int], dict[str, Any]],
) -> dict[str, Any]:
    """Invoca una acción CKAN v3 validando ``success == True``."""
    query = urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{CKAN_BASE}/{accion}?{query}" if query else f"{CKAN_BASE}/{accion}"
    respuesta = http_get_json(url, TIMEOUT_CKAN_SEGUNDOS)
    if not respuesta.get("success"):
        error = respuesta.get("error")
        raise DipresCkanError(f"CKAN devolvió success=False en '{accion}': {error}")
    resultado = respuesta.get("result")
    if not isinstance(resultado, dict):
        raise DipresCkanError(f"Campo 'result' inválido en respuesta CKAN de '{accion}'.")
    return resultado


def _seleccionar_recurso_ejecucion(paquete: Mapping[str, Any]) -> dict[str, Any] | None:
    """Selecciona el mejor recurso con ``datastore_active == True`` (Programa > Capítulo)."""
    recursos = paquete.get("resources")
    if not isinstance(recursos, list):
        return None
    activos = [r for r in recursos if isinstance(r, dict) and r.get("datastore_active") is True]
    if not activos:
        return None

    for r in activos:
        texto = _normalizar_texto(f"{r.get('name', '')} {r.get('description', '')}")
        if "a nivel programa" in texto or "nivel programa" in texto:
            return r
    for r in activos:
        texto = _normalizar_texto(f"{r.get('name', '')} {r.get('description', '')}")
        if "a nivel capitulo" in texto or "nivel capitulo" in texto:
            return r
    return None


def _paquete_corresponde_anio(paquete: Mapping[str, Any], anio: int) -> bool:
    texto = _normalizar_texto(
        f"{paquete.get('title', '')} {paquete.get('name', '')} {paquete.get('notes', '')}"
    )
    return str(anio) in texto


def _buscar_paquete_ejecucion(
    anio: int,
    http_get_json: Callable[[str, int], dict[str, Any]],
    anio_actual: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Busca el paquete y recurso de ejecución presupuestaria para ``anio``."""
    consultas: list[dict[str, Any]] = []
    if anio < anio_actual and anio != 2026:
        # Primero por relevancia para localizar el cierre de diciembre del año exacto
        consultas.append(
            {
                "q": f"ejecucion presupuestaria a diciembre de {anio} gobierno central total",
                "rows": 15,
            }
        )
    consultas.append(
        {
            "q": f"ejecucion presupuestaria {anio} gobierno central total",
            "rows": 20,
            "sort": "metadata_modified desc",
        }
    )
    consultas.append(
        {
            "q": f"ejecucion presupuestaria {anio} gobierno central",
            "rows": 25,
        }
    )

    for consulta in consultas:
        resultado = _ckan_action("package_search", consulta, http_get_json)
        paquetes = resultado.get("results") or []
        candidatos: list[tuple[tuple[int, int, int, str], dict[str, Any], dict[str, Any]]] = []
        for paq in paquetes:
            if not isinstance(paq, dict):
                continue
            if not _paquete_corresponde_anio(paq, anio):
                continue
            recurso = _seleccionar_recurso_ejecucion(paq)
            if recurso is None:
                continue
            texto_paq = _normalizar_texto(f"{paq.get('title', '')} {paq.get('name', '')}")
            if "ejecucion" not in texto_paq:
                continue
            es_total = int("total" in texto_paq and "fet" not in texto_paq and "incendio" not in texto_paq)
            es_diciembre = int("diciembre" in texto_paq)
            es_ley_regular = int("ley regular" in texto_paq and "fet" not in texto_paq)
            modificado = str(paq.get("metadata_modified") or "")
            clave_orden = (es_total, es_diciembre if anio < anio_actual else es_ley_regular, es_ley_regular, modificado)
            candidatos.append((clave_orden, paq, recurso))
        if candidatos:
            candidatos.sort(key=lambda item: item[0], reverse=True)
            _, paq_sel, rec_sel = candidatos[0]
            return paq_sel, rec_sel

    raise DipresCkanError(
        f"No se encontró un paquete CKAN de ejecución presupuestaria {anio} del Gobierno Central "
        "con recurso activo en Datastore ('A nivel Programa' o 'A nivel Capítulo')."
    )


def _buscar_ley_presupuestos(
    anio: int,
    http_get_json: Callable[[str, int], dict[str, Any]],
) -> dict[str, Any]:
    """Busca el paquete de Ley de Presupuestos inicial y vigente para ``anio``."""
    try:
        resultado = _ckan_action(
            "package_search",
            {
                "q": f"ley de presupuestos inicial y vigente {anio}",
                "rows": 10,
                "sort": "metadata_modified desc",
            },
            http_get_json,
        )
        paquetes = [
            p
            for p in (resultado.get("results") or [])
            if isinstance(p, dict) and _paquete_corresponde_anio(p, anio)
        ]
    except DipresCkanError as exc:
        return {
            "encontrado": False,
            "anio": anio,
            "package_name": None,
            "package_title": None,
            "actualizado_en": None,
            "tiene_datastore_active": False,
            "tiene_csv_disponible": False,
            "recursos": [],
            "nota": f"No fue posible consultar paquete de Ley de Presupuestos: {exc}",
        }

    if not paquetes:
        return {
            "encontrado": False,
            "anio": anio,
            "package_name": None,
            "package_title": None,
            "actualizado_en": None,
            "tiene_datastore_active": False,
            "tiene_csv_disponible": False,
            "recursos": [],
            "nota": f"Sin paquete 'ley de presupuestos inicial y vigente' publicado para {anio}.",
        }

    paquetes.sort(key=lambda p: str(p.get("metadata_modified") or ""), reverse=True)
    elegido = paquetes[0]
    recursos_raw = [r for r in (elegido.get("resources") or []) if isinstance(r, dict)]
    tiene_datastore = any(r.get("datastore_active") is True for r in recursos_raw)
    tiene_csv = any(
        _normalizar_texto(r.get("format", "")) == "csv"
        or str(r.get("url") or "").lower().endswith(".csv")
        for r in recursos_raw
    )
    resumen_recursos = [
        {
            "id": r.get("id"),
            "name": r.get("name"),
            "format": r.get("format"),
            "datastore_active": bool(r.get("datastore_active")),
            "url": r.get("url"),
        }
        for r in recursos_raw
    ]
    return {
        "encontrado": True,
        "anio": anio,
        "package_name": elegido.get("name"),
        "package_title": elegido.get("title"),
        "actualizado_en": elegido.get("metadata_modified"),
        "tiene_datastore_active": tiene_datastore,
        "tiene_csv_disponible": tiene_csv,
        "recursos": resumen_recursos,
        "nota": None,
    }


def _datastore_search_paginado(
    resource_id: str,
    http_get_json: Callable[[str, int], dict[str, Any]],
    *,
    filters: Mapping[str, Any] | None = None,
    q: str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Consulta ``datastore_search`` con paginación segura."""
    registros: list[dict[str, Any]] = []
    campos: list[str] = []
    offset = 0

    while offset < MAX_REGISTROS_POR_CONSULTA:
        params: dict[str, Any] = {
            "resource_id": resource_id,
            "limit": LIMITE_PAGINA_CKAN,
            "offset": offset,
        }
        if filters is not None:
            params["filters"] = json.dumps(filters, ensure_ascii=False)
        if q is not None:
            params["q"] = q

        res = _ckan_action("datastore_search", params, http_get_json)
        if not campos and isinstance(res.get("fields"), list):
            campos = [
                str(f.get("id"))
                for f in res["fields"]
                if isinstance(f, dict) and f.get("id")
            ]

        lote = [r for r in (res.get("records") or []) if isinstance(r, dict)]
        registros.extend(lote)
        total = res.get("total")
        if not lote or len(lote) < LIMITE_PAGINA_CKAN:
            break
        if isinstance(total, int) and len(registros) >= total:
            break
        offset += len(lote)

    return registros, campos


def _buscar_columna(
    columnas: Sequence[str],
    candidatas_exactas: Sequence[str],
) -> str | None:
    """Encuentra el nombre real de una columna comparando sin tildes ni mayúsculas."""
    mapa = {_normalizar_texto(col): col for col in columnas}
    for cand in candidatas_exactas:
        norm = _normalizar_texto(cand)
        if norm in mapa:
            return mapa[norm]
    return None


def detectar_columnas_montos(columnas: Sequence[str]) -> tuple[str | None, str | None, str | None]:
    """Detecta dinámicamente columnas de ejecución acumulada, vigente e inicial."""
    col_ejecucion: str | None = None
    mejor_puntaje = -1

    for idx, col in enumerate(columnas):
        norm = _normalizar_texto(col)
        if "%" in norm or "porcentaje" in norm or "tasa" in norm or "variacion" in norm:
            continue
        if "ejecucion" in norm or "ejecutad" in norm or "deveng" in norm:
            puntaje = 10
            if "ejecucion a " in norm or "acumulad" in norm:
                puntaje += 20
            for mes, orden in _MESES_ORDEN:
                if mes in norm:
                    puntaje += 50 + orden
                    break
            # En empate, prefiere la columna más a la derecha (suele ser acumulado).
            if puntaje > mejor_puntaje or (puntaje == mejor_puntaje and idx > 0):
                mejor_puntaje = puntaje
                col_ejecucion = col

    col_vigente: str | None = None
    for col in columnas:
        norm = _normalizar_texto(col)
        if "%" in norm or "porcentaje" in norm or "variacion" in norm:
            continue
        if "vigente" in norm:
            col_vigente = col
            break

    col_inicial: str | None = None
    for col in columnas:
        norm = _normalizar_texto(col)
        if "%" in norm or "porcentaje" in norm or "variacion" in norm:
            continue
        if "inicial" in norm:
            col_inicial = col
            break

    return col_ejecucion, col_vigente, col_inicial


def _valor_campo(
    fila: Mapping[str, Any],
    *nombres: str,
) -> str:
    """Obtiene el texto de un campo aceptando variantes de acentuación/mayúsculas."""
    for nombre in nombres:
        if nombre in fila and fila[nombre] is not None:
            return str(fila[nombre]).strip()
    mapa_norm = {_normalizar_texto(k): v for k, v in fila.items()}
    for nombre in nombres:
        norm = _normalizar_texto(nombre)
        if norm in mapa_norm and mapa_norm[norm] is not None:
            return str(mapa_norm[norm]).strip()
    return ""


def _es_moneda_no_clp(fila: Mapping[str, Any]) -> bool:
    """Identifica filas en moneda extranjera (USD/dólares) para no mezclar con CLP."""
    moneda = _normalizar_texto(_valor_campo(fila, "Moneda", "Tipo Moneda"))
    if not moneda:
        return False
    return any(tok in moneda for tok in ("dolar", "usd", "us$", "extranjer"))


def _es_fila_total_o_sin_subtitulo(fila: Mapping[str, Any]) -> bool:
    """Evita sumar filas de resumen/total junto con filas de detalle por subtítulo."""
    subtitulo = _valor_campo(fila, "Subtitulo", "Subtítulo", "Codigo Subtitulo")
    if not subtitulo:
        return True
    norm_sub = _normalizar_texto(subtitulo)
    if "total" in norm_sub:
        return True
    if not _extraer_codigo_subtitulo(subtitulo):
        return True
    for campo in ("Nombre Subtitulo", "Nombre Subtítulo", "Nombre Programa", "Nombre Capitulo"):
        val = _normalizar_texto(_valor_campo(fila, campo))
        if val.startswith("total "):
            return True
    return False


def _clave_dedup_registro(fila: Mapping[str, Any]) -> str:
    """Genera una clave única estable por ``_id`` o contenido normalizado."""
    if "_id" in fila and fila["_id"] is not None and str(fila["_id"]).strip() != "":
        return f"id:{fila['_id']}"
    pares = sorted((str(k), "" if v is None else str(v)) for k, v in fila.items())
    return "row:" + json.dumps(pares, ensure_ascii=False)


def _es_fila_gore_aysen(fila: Mapping[str, Any]) -> bool:
    """Determina si una fila corresponde al Gobierno Regional de Aysén (Partida 31)."""
    partida = _extraer_codigo_subtitulo(_valor_campo(fila, "Partida", "Codigo Partida"))
    campos_ref = (
        _valor_campo(fila, "Nombre Programa"),
        _valor_campo(fila, "Nombre Capitulo", "Nombre Capítulo"),
        _valor_campo(fila, "Nombre Asignacion", "Nombre Asignación"),
    )
    tiene_aysen = any(_contiene_aysen(c) for c in campos_ref)
    if not tiene_aysen:
        return False
    if partida == "31":
        return True
    return any("gobierno regional" in _normalizar_texto(c) for c in campos_ref)


def _es_fila_partida05_aysen(fila: Mapping[str, Any]) -> bool:
    """Determina si una fila de Partida 05 refiere explícitamente a Aysén / DPR Aysén."""
    campos_ref = (
        _valor_campo(fila, "Nombre Programa"),
        _valor_campo(fila, "Nombre Capitulo", "Nombre Capítulo"),
        _valor_campo(fila, "Nombre Asignacion", "Nombre Asignación"),
        _valor_campo(fila, "Nombre Item", "Nombre Ítem"),
    )
    return any(_contiene_aysen(c) for c in campos_ref)


def _eliminar_padres_con_hijos(filas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Si un grupo (Partida, Capítulo, Programa, Subtítulo) trae fila resumen e ítems, evita doble conteo."""
    grupos: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for fila in filas:
        clave = (
            _extraer_codigo_subtitulo(_valor_campo(fila, "Partida", "Codigo Partida")),
            _valor_campo(fila, "Capitulo", "Capítulo", "Codigo Capitulo"),
            _valor_campo(fila, "Programa", "Codigo Programa"),
            _extraer_codigo_subtitulo(_valor_campo(fila, "Subtitulo", "Subtítulo", "Codigo Subtitulo")),
        )
        grupos.setdefault(clave, []).append(fila)

    filtradas: list[dict[str, Any]] = []
    for grupo in grupos.values():
        resumenes = [
            f
            for f in grupo
            if not _valor_campo(f, "Item", "Ítem")
            and not _valor_campo(f, "Asignacion", "Asignación")
        ]
        hojas = [
            f
            for f in grupo
            if _valor_campo(f, "Item", "Ítem")
            or _valor_campo(f, "Asignacion", "Asignación")
        ]
        if resumenes and hojas:
            # Conservar únicamente las filas a nivel subtítulo para evitar duplicar con ítems/asignaciones.
            filtradas.extend(resumenes)
        else:
            filtradas.extend(grupo)
    return filtradas


def agregar_registros_aysen(
    registros_p31: Sequence[Mapping[str, Any]],
    registros_p05: Sequence[Mapping[str, Any]],
    registros_q_aysen: Sequence[Mapping[str, Any]],
    campos: Sequence[str] = (),
) -> dict[str, Any]:
    """Agrupa registros DIPRES CKAN de Aysén con aritmética exacta ``Decimal``.

    Separa estrictamente:
    - ``gore_aysen`` (Partida 31 / Gobierno Regional de Aysén)
    - ``servicios_publicos_aysen`` (servicios ejecutores en Aysén y Partida 05 Aysén)
    - ``totales_gobierno_central_aysen`` (gasto directo separado de financiamiento P31
      y excluyendo siempre subtítulos de ingresos/financiamiento 01–15 del gasto).
    """
    dedup: dict[str, dict[str, Any]] = {}

    for fila in registros_p31:
        if _es_fila_gore_aysen(fila):
            dedup[_clave_dedup_registro(fila)] = dict(fila)

    for fila in registros_p05:
        if _es_fila_partida05_aysen(fila):
            dedup[_clave_dedup_registro(fila)] = dict(fila)

    for fila in registros_q_aysen:
        dedup[_clave_dedup_registro(fila)] = dict(fila)

    todas_las_columnas: list[str] = list(campos)
    vistos_cols = set(todas_las_columnas)
    for fila in dedup.values():
        for k in fila.keys():
            if k not in vistos_cols:
                vistos_cols.add(k)
                todas_las_columnas.append(k)

    col_ejecucion, col_vigente, col_inicial = detectar_columnas_montos(todas_las_columnas)

    filas_validas: list[dict[str, Any]] = []
    no_clp_excluidos = 0
    for fila in dedup.values():
        if _es_moneda_no_clp(fila):
            no_clp_excluidos += 1
            continue
        if _es_fila_total_o_sin_subtitulo(fila):
            continue
        filas_validas.append(fila)

    filas_validas = _eliminar_padres_con_hijos(filas_validas)

    # Acumuladores GORE Aysén (en miles CLP para exactitud antes de dividir por 1000)
    gore_corriente_miles = CERO
    gore_inversion_miles = CERO
    gore_trans_cap_miles = CERO
    gore_ingresos_p31_miles = CERO
    gore_otros_miles = CERO
    gore_partidas: list[dict[str, Any]] = []

    # Acumuladores Servicios Públicos Aysén agrupados por (partida, capitulo, nombre_capitulo)
    servicios_map: dict[tuple[str, str, str], dict[str, Any]] = {}

    # Ingresos de servicios públicos excluidos del gasto
    ingresos_servicios_miles = CERO

    with localcontext(CONTEXTO_DECIMAL):
        for fila in filas_validas:
            monto_miles = parsear_monto_dipres(fila.get(col_ejecucion)) if col_ejecucion else None
            if monto_miles is None:
                continue
            vigente_miles = parsear_monto_dipres(fila.get(col_vigente)) if col_vigente else None
            inicial_miles = parsear_monto_dipres(fila.get(col_inicial)) if col_inicial else None

            partida = _extraer_codigo_subtitulo(_valor_campo(fila, "Partida", "Codigo Partida"))
            nombre_partida = _valor_campo(fila, "Nombre Partida")
            capitulo = _valor_campo(fila, "Capitulo", "Capítulo", "Codigo Capitulo")
            nombre_capitulo = _valor_campo(fila, "Nombre Capitulo", "Nombre Capítulo")
            programa = _valor_campo(fila, "Programa", "Codigo Programa")
            nombre_programa = _valor_campo(fila, "Nombre Programa")
            subtitulo = _extraer_codigo_subtitulo(
                _valor_campo(fila, "Subtitulo", "Subtítulo", "Codigo Subtitulo")
            )
            nombre_subtitulo = _valor_campo(fila, "Nombre Subtitulo", "Nombre Subtítulo")
            item = _valor_campo(fila, "Item", "Ítem")
            asignacion = _valor_campo(fila, "Asignacion", "Asignación")
            nombre_asignacion = _valor_campo(fila, "Nombre Asignacion", "Nombre Asignación")

            categoria = clasificar_subtitulo(subtitulo)
            monto_millones = _a_millones_clp(monto_miles)

            if _es_fila_gore_aysen(fila):
                if categoria == "gasto_corriente":
                    gore_corriente_miles += monto_miles
                elif categoria == "inversion":
                    gore_inversion_miles += monto_miles
                elif categoria == "transferencias_capital":
                    gore_trans_cap_miles += monto_miles
                elif categoria == "ingresos_financiamiento":
                    gore_ingresos_p31_miles += monto_miles
                else:
                    gore_otros_miles += monto_miles

                gore_partidas.append(
                    {
                        "partida": partida,
                        "nombre_partida": nombre_partida,
                        "capitulo": capitulo,
                        "nombre_capitulo": nombre_capitulo,
                        "programa": programa,
                        "nombre_programa": nombre_programa,
                        "subtitulo": subtitulo,
                        "nombre_subtitulo": nombre_subtitulo,
                        "item": item or None,
                        "asignacion": asignacion or None,
                        "nombre_asignacion": nombre_asignacion or None,
                        "categoria": categoria,
                        "ejecucion_miles_clp": _formatear_decimal(monto_miles),
                        "ejecucion_millones_clp": _formatear_decimal(monto_millones),
                        "vigente_miles_clp": (
                            _formatear_decimal(vigente_miles) if vigente_miles is not None else None
                        ),
                        "vigente_millones_clp": (
                            _formatear_decimal(_a_millones_clp(vigente_miles))
                            if vigente_miles is not None
                            else None
                        ),
                        "inicial_millones_clp": (
                            _formatear_decimal(_a_millones_clp(inicial_miles))
                            if inicial_miles is not None
                            else None
                        ),
                    }
                )
            else:
                etiqueta_servicio = nombre_capitulo or nombre_programa or nombre_partida or f"Partida {partida}"
                clave_serv = (partida, capitulo, etiqueta_servicio)
                if clave_serv not in servicios_map:
                    servicios_map[clave_serv] = {
                        "partida": partida,
                        "nombre_partida": nombre_partida,
                        "capitulo": capitulo,
                        "nombre_capitulo": etiqueta_servicio,
                        "programas": set(),
                        "corriente_miles": CERO,
                        "inversion_miles": CERO,
                        "trans_cap_miles": CERO,
                        "otros_miles": CERO,
                        "ingresos_miles": CERO,
                        "vigente_gasto_miles": CERO,
                        "tiene_vigente": False,
                        "registros": 0,
                    }
                srv = servicios_map[clave_serv]
                srv["registros"] += 1
                if nombre_programa:
                    srv["programas"].add(nombre_programa)
                if categoria == "gasto_corriente":
                    srv["corriente_miles"] += monto_miles
                elif categoria == "inversion":
                    srv["inversion_miles"] += monto_miles
                elif categoria == "transferencias_capital":
                    srv["trans_cap_miles"] += monto_miles
                elif categoria == "ingresos_financiamiento":
                    srv["ingresos_miles"] += monto_miles
                    ingresos_servicios_miles += monto_miles
                else:
                    srv["otros_miles"] += monto_miles

                if vigente_miles is not None and categoria != "ingresos_financiamiento":
                    srv["vigente_gasto_miles"] += vigente_miles
                    srv["tiene_vigente"] = True

        # Conversión exacta a millones CLP para GORE Aysén
        gore_corriente_mm = _a_millones_clp(gore_corriente_miles)
        gore_inversion_mm = _a_millones_clp(gore_inversion_miles)
        gore_trans_cap_mm = _a_millones_clp(gore_trans_cap_miles)
        gore_ingresos_p31_mm = _a_millones_clp(gore_ingresos_p31_miles)
        gore_otros_mm = _a_millones_clp(gore_otros_miles)
        gore_gasto_directo_mm = (
            gore_corriente_mm + gore_inversion_mm + gore_trans_cap_mm + gore_otros_mm
        )

        # Ratio gasto corriente / inversión del GORE Aysén (solo si ambos > 0)
        ratio_corriente_inversion: str | None
        motivo_brecha: str | None
        if gore_corriente_miles > CERO and gore_inversion_miles > CERO:
            ratio_dec = ((CIEN * gore_corriente_miles) / gore_inversion_miles).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            ratio_corriente_inversion = _formatear_decimal(ratio_dec)
            motivo_brecha = None
        else:
            ratio_corriente_inversion = None
            if gore_partidas and gore_inversion_miles == CERO and (
                gore_ingresos_p31_miles > CERO or gore_trans_cap_miles > CERO or gore_corriente_miles > CERO
            ):
                motivo_brecha = (
                    "El recurso CKAN DIPRES de Gobierno Central solo registra traspasos de "
                    "financiamiento en Partida 31 (ingresos/transferencias) sin desglose completo "
                    "de ejecución del GORE Aysén en subtítulos 21–26 y 29–31; se omite el ratio "
                    "corriente/inversión para no inventar cifras."
                )
            elif not gore_partidas:
                motivo_brecha = (
                    "No se encontraron filas de ejecución del GORE Aysén en el recurso CKAN DIPRES "
                    "consultado; ratio corriente/inversión no calculable."
                )
            elif gore_corriente_miles <= CERO:
                motivo_brecha = (
                    "Gasto corriente (subtítulos 21–26) del GORE Aysén igual a cero o ausente en "
                    "el recurso CKAN DIPRES; ratio corriente/inversión no calculable."
                )
            else:
                motivo_brecha = (
                    "Inversión directa (subtítulos 29–31) del GORE Aysén igual a cero o ausente en "
                    "el recurso CKAN DIPRES; ratio corriente/inversión no calculable."
                )

        # Consolidación de servicios públicos ejecutores en Aysén
        servicios_lista: list[dict[str, Any]] = []
        serv_corriente_total_miles = CERO
        serv_inversion_total_miles = CERO
        serv_trans_cap_total_miles = CERO
        serv_otros_total_miles = CERO

        for srv in servicios_map.values():
            serv_corriente_total_miles += srv["corriente_miles"]
            serv_inversion_total_miles += srv["inversion_miles"]
            serv_trans_cap_total_miles += srv["trans_cap_miles"]
            serv_otros_total_miles += srv["otros_miles"]

            total_gasto_srv_miles = (
                srv["corriente_miles"]
                + srv["inversion_miles"]
                + srv["trans_cap_miles"]
                + srv["otros_miles"]
            )
            servicios_lista.append(
                {
                    "partida": srv["partida"],
                    "nombre_partida": srv["nombre_partida"],
                    "capitulo": srv["capitulo"],
                    "nombre_capitulo": srv["nombre_capitulo"],
                    "programas": sorted(srv["programas"]),
                    "gasto_corriente_sub_21_26": _formatear_decimal(
                        _a_millones_clp(srv["corriente_miles"])
                    ),
                    "inversion_sub_29_31": _formatear_decimal(
                        _a_millones_clp(srv["inversion_miles"])
                    ),
                    "transferencias_capital_sub_33": _formatear_decimal(
                        _a_millones_clp(srv["trans_cap_miles"])
                    ),
                    "otros_gastos": _formatear_decimal(_a_millones_clp(srv["otros_miles"])),
                    "ingresos_financiamiento_excluidos": _formatear_decimal(
                        _a_millones_clp(srv["ingresos_miles"])
                    ),
                    "total_gasto_millones": _formatear_decimal(
                        _a_millones_clp(total_gasto_srv_miles)
                    ),
                    "vigente_gasto_millones": (
                        _formatear_decimal(_a_millones_clp(srv["vigente_gasto_miles"]))
                        if srv["tiene_vigente"]
                        else None
                    ),
                    "registros": srv["registros"],
                }
            )

        servicios_lista.sort(
            key=lambda item: (
                -Decimal(item["total_gasto_millones"]),
                item["partida"],
                item["capitulo"],
                item["nombre_capitulo"],
            )
        )

        # Totales Gobierno Central Aysén: financiamiento P31 estrictamente separado de gasto directo
        total_corriente_mm = _a_millones_clp(serv_corriente_total_miles + gore_corriente_miles)
        total_inversion_mm = _a_millones_clp(serv_inversion_total_miles + gore_inversion_miles)
        total_trans_cap_mm = _a_millones_clp(serv_trans_cap_total_miles + gore_trans_cap_miles)
        total_otros_mm = _a_millones_clp(serv_otros_total_miles + gore_otros_miles)
        total_gasto_directo_mm = (
            total_corriente_mm + total_inversion_mm + total_trans_cap_mm + total_otros_mm
        )
        ingresos_servicios_mm = _a_millones_clp(ingresos_servicios_miles)

    return {
        "columna_ejecucion": col_ejecucion,
        "columna_vigente": col_vigente,
        "columna_inicial": col_inicial,
        "registros_unicos_procesados": len(filas_validas),
        "registros_no_clp_excluidos": no_clp_excluidos,
        "gore_aysen": {
            "gasto_corriente_sub_21_26": _formatear_decimal(gore_corriente_mm),
            "inversion_sub_29_31": _formatear_decimal(gore_inversion_mm),
            "transferencias_capital_sub_33": _formatear_decimal(gore_trans_cap_mm),
            "otros_gastos": _formatear_decimal(gore_otros_mm),
            "total_gasto_directo_millones": _formatear_decimal(gore_gasto_directo_mm),
            "ingresos_financiamiento_p31": _formatear_decimal(gore_ingresos_p31_mm),
            "ratio_corriente_sobre_inversion_pct": ratio_corriente_inversion,
            "motivo_brecha": motivo_brecha,
            "partidas": gore_partidas,
        },
        "servicios_publicos_aysen": servicios_lista,
        "totales_gobierno_central_aysen": {
            "gasto_corriente_sub_21_26": _formatear_decimal(total_corriente_mm),
            "inversion_sub_29_31": _formatear_decimal(total_inversion_mm),
            "transferencias_capital_sub_33": _formatear_decimal(total_trans_cap_mm),
            "otros_gastos": _formatear_decimal(total_otros_mm),
            "total_gasto_directo_millones": _formatear_decimal(total_gasto_directo_mm),
            "financiamiento_gore_p31": _formatear_decimal(gore_ingresos_p31_mm),
            "ingresos_servicios_excluidos": _formatear_decimal(ingresos_servicios_mm),
        },
    }


def detectar_mes_corte(
    columna_ejecucion: str | None = None,
    package_title: str | None = None,
    package_name: str | None = None,
) -> int | None:
    """Detecta el mes de corte acumulado (1..12) desde columna de ejecución o metadatos.

    Prioriza ``columna_ejecucion`` (campo efectivamente sumado), luego ``package_title``
    y finalmente ``package_name``. Busca primero nombres completos de mes en orden
    descendente (diciembre..enero) para capturar el límite superior de rangos como
    "enero a agosto", y luego variantes/abreviaturas delimitadas.
    """
    for fuente in (columna_ejecucion, package_title, package_name):
        norm = _normalizar_texto(fuente)
        if not norm:
            continue
        for mes, numero in _MESES_ORDEN:
            if re.search(rf"(?<![a-z]){mes}(?![a-z])", norm):
                return numero
        for variante, numero in _MESES_VARIANTES_ORDEN:
            if re.search(rf"(?<![a-z]){variante}(?![a-z])", norm):
                return numero
    return None


def _construir_advertencia_comparabilidad_meses(
    mes_corte: int | None,
    anio: int | None = None,
) -> str | None:
    """Construye advertencia metodológica cuando el corte es menor a 12 meses."""
    if mes_corte == 12:
        return None
    if mes_corte is not None and 1 <= mes_corte < 12:
        nombre_mes = _MESES_NOMBRE_POR_NUMERO[mes_corte]
        prefijo = f"El ejercicio {anio}" if anio is not None else "El ejercicio"
        return (
            f"{prefijo} corresponde a ejecución acumulada al mes {mes_corte} "
            f"({nombre_mes}) y no debe compararse en bruto contra un cierre anual "
            "de 12 meses sin usar meses equivalentes."
        )
    return (
        "No fue posible determinar el mes de corte del ejercicio; no debe compararse "
        "en bruto contra un cierre anual de 12 meses sin verificar meses equivalentes."
    )


def _asegurar_metadatos_corte(contenido: dict[str, Any]) -> dict[str, Any]:
    """Completa metadatos de mes de corte y comparabilidad si faltan en caché previo."""
    traza = contenido.get("fuente_trazabilidad")
    if not isinstance(traza, dict):
        return contenido
    mes_corte = traza.get("mes_corte")
    if not isinstance(mes_corte, int) or isinstance(mes_corte, bool) or not (1 <= mes_corte <= 12):
        mes_corte = detectar_mes_corte(
            columna_ejecucion=traza.get("columna_ejecucion"),
            package_title=traza.get("package_title"),
            package_name=traza.get("package_name"),
        )
        traza["mes_corte"] = mes_corte
    traza["es_cierre_anual"] = mes_corte == 12
    if "advertencia_comparabilidad_meses" not in traza:
        anio_raw = contenido.get("anio")
        anio_val = anio_raw if isinstance(anio_raw, int) and not isinstance(anio_raw, bool) else None
        traza["advertencia_comparabilidad_meses"] = _construir_advertencia_comparabilidad_meses(
            mes_corte, anio_val
        )
    return contenido


def _leer_cache_archivo(cache_path: Path) -> dict[str, Any] | None:
    """Lee y valida la estructura básica de un archivo de caché JSON sin evaluar TTL."""
    if not cache_path.exists():
        return None
    try:
        contenido = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(contenido, dict) or not isinstance(
        contenido.get("fuente_trazabilidad"), dict
    ):
        return None
    return _asegurar_metadatos_corte(contenido)


def _leer_cache_vigente(cache_path: Path, ttl_segundos: int) -> dict[str, Any] | None:
    """Lee el archivo de caché si existe y no ha expirado su TTL."""
    if not cache_path.exists():
        return None
    try:
        edad = time.time() - cache_path.stat().st_mtime
        if edad < 0 or edad > ttl_segundos:
            return None
    except OSError:
        return None
    contenido = _leer_cache_archivo(cache_path)
    if contenido is None:
        return None
    contenido["fuente_trazabilidad"]["desde_cache"] = True
    contenido["fuente_trazabilidad"]["estado_actualizacion"] = ESTADO_ACTUALIZACION_CACHE
    contenido["fuente_trazabilidad"]["advertencia_actualizacion"] = None
    return contenido


def _leer_cache_respaldo(cache_path: Path, error: Exception) -> dict[str, Any] | None:
    """Devuelve el último corte aprobado guardado cuando falla la actualización CKAN."""
    contenido = _leer_cache_archivo(cache_path)
    if contenido is None:
        return None
    traza = contenido["fuente_trazabilidad"]
    traza["desde_cache"] = True
    traza["estado_actualizacion"] = ESTADO_ACTUALIZACION_RESPALDO
    traza["advertencia_actualizacion"] = (
        f"No fue posible actualizar desde DIPRES CKAN ({type(error).__name__}: {error}); "
        "se devuelve el último corte aprobado guardado en caché local."
    )
    return contenido


def _escribir_cache_atomico(cache_path: Path, payload: Mapping[str, Any]) -> None:
    """Escribe caché JSON de forma atómica en UTF-8."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporal = cache_path.with_suffix(cache_path.suffix + ".tmp")
    temporal.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporal, cache_path)


def obtener_ejecucion_aysen_live(
    anio: int = 2025,
    refresh: bool = False,
    cache_path: Path | None = None,
    *,
    http_get_json: Callable[[str, int], dict[str, Any]] | None = None,
    check_presupuesto_abierto: Callable[[int], dict[str, Any]] | None = None,
    ttl_segundos: int = CACHE_TTL_SEGUNDOS,
) -> dict[str, Any]:
    """Obtiene la ejecución presupuestaria en vivo de Aysén desde DIPRES CKAN (`datos.gob.cl`).

    Si falla la consulta externa a CKAN al intentar actualizar y existe un archivo
    de caché previo válido en ``cache_path``, devuelve el último corte aprobado
    guardado marcando ``estado_actualizacion = "respaldo_ultimo_corte_aprobado"``.

    Args:
        anio: Ejercicio fiscal a consultar (por defecto ``2025``).
        refresh: Si ``True``, omite caché local y consulta nuevamente la API CKAN.
        cache_path: Ruta opcional para archivo JSON de caché
            (por defecto ``<repo_root>/data/raw/dipres-aysen-{anio}.json``).
        http_get_json: Inyección opcional para pruebas sin red.
        check_presupuesto_abierto: Inyección opcional para verificar Presupuesto Abierto.
        ttl_segundos: Vigencia del caché en segundos (por defecto 12 horas).
    """
    if not isinstance(anio, int) or isinstance(anio, bool) or not (2010 <= anio <= 2035):
        raise ValueError(f"Año presupuestario inválido: {anio!r}")

    ruta_cache = cache_path or (_RAIZ_REPO / "data" / "raw" / f"dipres-aysen-{anio}.json")
    if not refresh:
        en_cache = _leer_cache_vigente(ruta_cache, ttl_segundos)
        if en_cache is not None:
            return en_cache

    fetcher = http_get_json or _http_get_json
    pa_checker = check_presupuesto_abierto or _consultar_presupuesto_abierto
    ahora_utc = datetime.now(timezone.utc)

    try:
        paquete_ejec, recurso_ejec = _buscar_paquete_ejecucion(anio, fetcher, ahora_utc.year)
        resource_id = str(recurso_ejec["id"])

        # Búsqueda paralela documental de Ley de Presupuestos inicial y vigente
        ley_presupuestos = _buscar_ley_presupuestos(anio, fetcher)

        # (a) Partida 31 (Financiamiento Gobiernos Regionales)
        registros_p31, campos_p31 = _datastore_search_paginado(
            resource_id, fetcher, filters={"Partida": "31"}
        )

        # (b) Partida 05 (Ministerio del Interior / Delegación Presidencial Regional de Aysén)
        try:
            registros_p05, campos_p05 = _datastore_search_paginado(
                resource_id, fetcher, filters={"Partida": "05"}
            )
        except DipresCkanError:
            registros_p05, campos_p05 = [], []
        if not registros_p05:
            try:
                registros_p05, campos_p05_alt = _datastore_search_paginado(
                    resource_id, fetcher, filters={"Partida": "5"}
                )
                if campos_p05_alt and not campos_p05:
                    campos_p05 = campos_p05_alt
            except DipresCkanError:
                registros_p05 = []

        # (c) Búsqueda textual de servicios públicos ejecutores en Aysén
        registros_q_aysen, campos_q = _datastore_search_paginado(
            resource_id, fetcher, q="AYSÉN"
        )
    except (DipresCkanError, HTTPError, URLError, TimeoutError, OSError) as exc:
        respaldo = _leer_cache_respaldo(ruta_cache, exc)
        if respaldo is not None:
            return respaldo
        raise

    campos_combinados: list[str] = []
    for lista_campos in (campos_p31, campos_p05, campos_q):
        for c in lista_campos:
            if c not in campos_combinados:
                campos_combinados.append(c)

    agregado = agregar_registros_aysen(
        registros_p31=registros_p31,
        registros_p05=registros_p05,
        registros_q_aysen=registros_q_aysen,
        campos=campos_combinados,
    )

    presupuesto_abierto = pa_checker(TIMEOUT_PRESUPUESTO_ABIERTO_SEGUNDOS)
    extraido_en = ahora_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    mes_corte = detectar_mes_corte(
        columna_ejecucion=agregado["columna_ejecucion"],
        package_title=paquete_ejec.get("title"),
        package_name=paquete_ejec.get("name"),
    )
    es_cierre_anual = mes_corte == 12
    advertencia_comparabilidad = _construir_advertencia_comparabilidad_meses(mes_corte, anio)

    resultado: dict[str, Any] = {
        "anio": anio,
        "region_codigo": "11",
        "region_nombre": "Aysén del General Carlos Ibáñez del Campo",
        "gore_aysen": agregado["gore_aysen"],
        "servicios_publicos_aysen": agregado["servicios_publicos_aysen"],
        "totales_gobierno_central_aysen": agregado["totales_gobierno_central_aysen"],
        "ley_presupuestos": ley_presupuestos,
        "presupuesto_abierto": presupuesto_abierto,
        "fuente_trazabilidad": {
            "institucion": "DIPRES · Ministerio de Hacienda (datos.gob.cl CKAN)",
            "endpoint_ckan": CKAN_BASE,
            "package_name": paquete_ejec.get("name"),
            "package_title": paquete_ejec.get("title"),
            "resource_id": resource_id,
            "resource_name": recurso_ejec.get("name"),
            "columna_ejecucion": agregado["columna_ejecucion"],
            "columna_vigente": agregado["columna_vigente"],
            "columna_inicial": agregado["columna_inicial"],
            "etapa_informada": "ejecucion_acumulada",
            "mes_corte": mes_corte,
            "es_cierre_anual": es_cierre_anual,
            "advertencia_comparabilidad_meses": advertencia_comparabilidad,
            "actualizado_en": paquete_ejec.get("metadata_modified"),
            "extraido_en": extraido_en,
            "unidad_origen": "miles CLP",
            "unidad_salida": "millones CLP",
            "moneda": "CLP",
            "desde_cache": False,
            "estado_actualizacion": ESTADO_ACTUALIZACION_VIVO,
            "advertencia_actualizacion": None,
            "registros_unicos_procesados": agregado["registros_unicos_procesados"],
            "registros_no_clp_excluidos": agregado["registros_no_clp_excluidos"],
        },
    }

    _escribir_cache_atomico(ruta_cache, resultado)
    return resultado
