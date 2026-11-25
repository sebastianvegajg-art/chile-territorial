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
DATASET_PUBLICO_BASE = "https://datos.gob.cl/dataset"
PRESUPUESTO_ABIERTO_BASE = "https://api.presupuestoabierto.gob.cl"
ESQUEMA_PILOTO_PRESUPUESTARIO = "dipres-piloto-presupuestario-v1"

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
    """Identifica filas en moneda distinta a pesos chilenos (ej. USD/dólares) para no mezclar con CLP."""
    moneda = _normalizar_texto(_valor_campo(fila, "Moneda", "Tipo Moneda"))
    if not moneda:
        return False
    if any(tok in moneda for tok in ("dolar", "usd", "us$", "extranjer", "euro", "uf")):
        return True
    if any(tok in moneda for tok in ("peso", "clp", "nacional")):
        return False
    # Cualquier otra etiqueta monetaria explícita distinta de pesos se excluye por seguridad.
    return True


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
    """Determina si una fila corresponde al Gobierno Regional de Aysén (Partida 31 o ex Partida 05)."""
    partida = _extraer_codigo_subtitulo(_valor_campo(fila, "Partida", "Codigo Partida"))
    campos_ref = (
        _valor_campo(fila, "Nombre Programa"),
        _valor_campo(fila, "Nombre Capitulo", "Nombre Capítulo"),
        _valor_campo(fila, "Nombre Asignacion", "Nombre Asignación"),
        _valor_campo(
            fila,
            "Nombre Sub-Asignacion",
            "Nombre Sub-Asignación",
            "Nombre Subasignacion",
            "Nombre Subasignación",
        ),
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
        _valor_campo(
            fila,
            "Nombre Sub-Asignacion",
            "Nombre Sub-Asignación",
            "Nombre Subasignacion",
            "Nombre Subasignación",
        ),
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
        if edad < -5 or edad > ttl_segundos:
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


# ---------------------------------------------------------------------------
# Piloto Presupuestario completo (Inicial / Vigente / Ejecutado + Nacional +
# Vialidad MOP + Comparación mismo mes del año anterior)
# ---------------------------------------------------------------------------

_DESGLOSE_PARTIDAS_ORDEN: tuple[tuple[str, str, str], ...] = (
    ("21", "Personal (Subt. 21)", "gasto_corriente"),
    ("22", "Bienes y servicios de consumo (Subt. 22)", "gasto_corriente"),
    ("23", "Prestaciones de seguridad social (Subt. 23)", "gasto_corriente"),
    ("24", "Transferencias corrientes (Subt. 24)", "gasto_corriente"),
    ("25", "Íntegros al Fisco (Subt. 25)", "gasto_corriente"),
    ("26", "Otros gastos corrientes (Subt. 26)", "gasto_corriente"),
    ("29-31", "Inversión física (Subt. 29–31)", "inversion_y_capital"),
    ("33", "Transferencias de capital (Subt. 33)", "inversion_y_capital"),
    ("otros", "Otros gastos y servicio de la deuda (Subt. 27, 28, 32, 34–35)", "otros_gastos"),
)

_BASE_CALCULO_PORCENTAJE_PILOTO = (
    "Porcentajes calculados sobre el gasto total ejecutado en pesos chilenos (CLP), "
    "excluyendo estrictamente subtítulos de ingresos/financiamiento (01–15) y filas en "
    "moneda extranjera (USD/dólares). Gasto corriente = Subt. 21–26; Inversión y capital "
    "= Inversión física (Subt. 29–31) + Transferencias de capital (Subt. 33)."
)


def _url_dataset_publico(package_name: str | None) -> str | None:
    if not package_name or not str(package_name).strip():
        return None
    return f"{DATASET_PUBLICO_BASE}/{str(package_name).strip()}"


def _formatear_cl(valor: Decimal, decimales: int = 1) -> str:
    """Formatea un Decimal en notación chilena (punto de miles, coma decimal)."""
    with localcontext(CONTEXTO_DECIMAL):
        cuanto = Decimal("1") if decimales <= 0 else Decimal("1").scaleb(-decimales)
        redondeado = valor.quantize(cuanto, rounding=ROUND_HALF_UP)
        signo = "-" if redondeado < CERO else ""
        abs_val = abs(redondeado)
        texto = f"{abs_val:.{decimales}f}"
        if "." in texto:
            entero, frac = texto.split(".", 1)
        else:
            entero, frac = texto, ""
        grupos: list[str] = []
        while len(entero) > 3:
            grupos.append(entero[-3:])
            entero = entero[:-3]
        grupos.append(entero)
        entero_fmt = ".".join(reversed(grupos))
        return f"{signo}{entero_fmt},{frac}" if decimales > 0 else f"{signo}{entero_fmt}"


def _seleccionar_recurso_nivel_nacional(paquete: Mapping[str, Any]) -> dict[str, Any] | None:
    """Selecciona el recurso ``A nivel Nacional`` con ``datastore_active == True``."""
    recursos = paquete.get("resources")
    if not isinstance(recursos, list):
        return None
    for r in recursos:
        if not isinstance(r, dict) or r.get("datastore_active") is not True:
            continue
        texto = _normalizar_texto(f"{r.get('name', '')} {r.get('description', '')}")
        if "a nivel nacional" in texto or "nivel nacional" in texto:
            return r
    return None


def _es_fila_vialidad_mop(fila: Mapping[str, Any]) -> bool:
    """Detecta filas de Dirección de Vialidad MOP (Partida 12, Capítulo 02)."""
    partida = _extraer_codigo_subtitulo(_valor_campo(fila, "Partida", "Codigo Partida"))
    if partida != "12":
        return False
    capitulo = _extraer_codigo_subtitulo(
        _valor_campo(fila, "Capitulo", "Capítulo", "Codigo Capitulo")
    )
    if capitulo == "02":
        return True
    campos_ref = (
        _valor_campo(fila, "Nombre Capitulo", "Nombre Capítulo"),
        _valor_campo(fila, "Nombre Programa"),
    )
    return any("vialidad" in _normalizar_texto(c) for c in campos_ref)


def _filtrar_filas_vialidad_mop(filas: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Filtra filas de Dirección de Vialidad MOP (12-02) sin mezclar otros servicios MOP."""
    candidatas = [dict(f) for f in filas if _es_fila_vialidad_mop(f)]
    if not candidatas:
        return []
    con_vialidad = [
        f
        for f in candidatas
        if "vialidad"
        in _normalizar_texto(
            f"{_valor_campo(f, 'Nombre Capitulo', 'Nombre Capítulo')} "
            f"{_valor_campo(f, 'Nombre Programa')}"
        )
    ]
    return con_vialidad if con_vialidad else candidatas


def _detectar_columnas_ley(columnas: Sequence[str]) -> tuple[str | None, str | None]:
    """Detecta columnas ``Monto Ley Inicial`` y ``Monto Ley Vigente...`` en recursos de Ley."""
    col_inicial: str | None = None
    mejor_ini = -1
    col_vigente: str | None = None
    mejor_vig = -1

    for idx, col in enumerate(columnas):
        norm = _normalizar_texto(col)
        if "%" in norm or "porcentaje" in norm or "tasa" in norm or "variacion" in norm:
            continue
        if "inicial" in norm:
            puntaje = 10
            if "monto" in norm:
                puntaje += 10
            if "ley" in norm:
                puntaje += 10
            if puntaje > mejor_ini:
                mejor_ini = puntaje
                col_inicial = col
        if "vigente" in norm:
            puntaje = 10
            if "monto" in norm:
                puntaje += 10
            if "ley" in norm:
                puntaje += 10
            for mes, orden in _MESES_ORDEN:
                if mes in norm:
                    puntaje += 50 + orden
                    break
            if puntaje > mejor_vig or (puntaje == mejor_vig and idx > 0):
                mejor_vig = puntaje
                col_vigente = col

    return col_inicial, col_vigente


def _buscar_paquete_ley_piloto(
    anio: int,
    mes_corte: int | None,
    http_get_json: Callable[[str, int], dict[str, Any]],
) -> dict[str, Any]:
    """Busca el paquete de Ley de Presupuestos Inicial y Vigente para ``anio`` y ``mes_corte``."""
    consultas: list[dict[str, Any]] = []
    nombre_mes = _MESES_NOMBRE_POR_NUMERO.get(mes_corte) if mes_corte else None
    if nombre_mes:
        consultas.append(
            {
                "q": f"ley de presupuestos inicial y vigente a {nombre_mes} de {anio} gobierno central total",
                "rows": 15,
            }
        )
    consultas.append(
        {
            "q": f"ley de presupuestos inicial y vigente {anio} gobierno central total",
            "rows": 20,
        }
    )
    consultas.append(
        {
            "q": f"ley de presupuestos inicial y vigente {anio}",
            "rows": 25,
        }
    )

    candidatos: list[tuple[tuple[int, int, int, int, str], dict[str, Any]]] = []
    vistos: set[str] = set()
    ultimo_error: str | None = None

    for consulta in consultas:
        try:
            resultado = _ckan_action("package_search", consulta, http_get_json)
        except DipresCkanError as exc:
            ultimo_error = str(exc)
            continue
        for paq in resultado.get("results") or []:
            if not isinstance(paq, dict):
                continue
            clave_paq = str(paq.get("name") or paq.get("id") or "")
            if clave_paq and clave_paq in vistos:
                continue
            if clave_paq:
                vistos.add(clave_paq)
            if not _paquete_corresponde_anio(paq, anio):
                continue
            texto_paq = _normalizar_texto(f"{paq.get('title', '')} {paq.get('name', '')}")
            if "ley" not in texto_paq or "presupuesto" not in texto_paq:
                continue
            es_total = int("total" in texto_paq and "fet" not in texto_paq and "incendio" not in texto_paq)
            mes_paq = detectar_mes_corte(
                package_title=paq.get("title"),
                package_name=paq.get("name"),
            )
            coincide_mes = int(mes_corte is not None and mes_paq == mes_corte)
            es_dic = int(mes_paq == 12)
            recursos = [r for r in (paq.get("resources") or []) if isinstance(r, dict)]
            tiene_ds = int(any(r.get("datastore_active") is True for r in recursos))
            mod = str(paq.get("metadata_modified") or "")
            candidatos.append(((es_total, coincide_mes, tiene_ds, es_dic, mod), paq))
        if candidatos:
            break

    if not candidatos:
        nota = (
            f"No fue posible consultar paquete de Ley de Presupuestos {anio}: {ultimo_error}"
            if ultimo_error
            else f"No se encontró paquete CKAN de Ley de Presupuestos Inicial y Vigente para {anio}."
        )
        return {
            "encontrado": False,
            "anio": anio,
            "package_name": None,
            "package_title": None,
            "url_respaldo": None,
            "actualizado_en": None,
            "tiene_datastore_active": False,
            "recurso_nacional": None,
            "recurso_programa": None,
            "nota": nota,
        }

    candidatos.sort(key=lambda item: item[0], reverse=True)
    elegido = candidatos[0][1]
    recurso_nac = _seleccionar_recurso_nivel_nacional(elegido)
    recurso_prog = _seleccionar_recurso_ejecucion(elegido)
    recursos_raw = [r for r in (elegido.get("resources") or []) if isinstance(r, dict)]
    tiene_ds = any(r.get("datastore_active") is True for r in recursos_raw)
    nota_ds = (
        None
        if tiene_ds
        else (
            f"El paquete CKAN '{elegido.get('title') or elegido.get('name')}' tiene "
            "datastore_active=False; los montos inicial y vigente quedan como no disponibles "
            "sin inventar cifras."
        )
    )
    return {
        "encontrado": True,
        "anio": anio,
        "package_name": elegido.get("name"),
        "package_title": elegido.get("title"),
        "url_respaldo": _url_dataset_publico(elegido.get("name")),
        "actualizado_en": elegido.get("metadata_modified"),
        "tiene_datastore_active": tiene_ds,
        "recurso_nacional": recurso_nac,
        "recurso_programa": recurso_prog,
        "nota": nota_ds,
    }


def _buscar_paquete_ejecucion_mes(
    anio: int,
    mes: int,
    http_get_json: Callable[[str, int], dict[str, Any]],
) -> dict[str, Any] | None:
    """Busca el paquete de ejecución acumulada de un ``anio`` y ``mes`` exactos."""
    nombre_mes = _MESES_NOMBRE_POR_NUMERO.get(mes)
    if not nombre_mes:
        return None
    consultas = (
        {
            "q": f"ejecucion presupuestaria a {nombre_mes} de {anio} gobierno central total",
            "rows": 15,
        },
        {
            "q": f"ejecucion presupuestaria {nombre_mes} {anio} gobierno central",
            "rows": 20,
        },
    )
    for consulta in consultas:
        try:
            resultado = _ckan_action("package_search", consulta, http_get_json)
        except DipresCkanError:
            continue
        candidatos: list[tuple[tuple[int, int, str], dict[str, Any]]] = []
        for paq in resultado.get("results") or []:
            if not isinstance(paq, dict):
                continue
            if not _paquete_corresponde_anio(paq, anio):
                continue
            texto_paq = _normalizar_texto(f"{paq.get('title', '')} {paq.get('name', '')}")
            if "ejecucion" not in texto_paq:
                continue
            mes_paq = detectar_mes_corte(
                package_title=paq.get("title"),
                package_name=paq.get("name"),
            )
            if mes_paq != mes:
                continue
            rec_nac = _seleccionar_recurso_nivel_nacional(paq)
            rec_prog = _seleccionar_recurso_ejecucion(paq)
            if rec_nac is None and rec_prog is None:
                continue
            es_total = int("total" in texto_paq and "fet" not in texto_paq and "incendio" not in texto_paq)
            ambos = int(rec_nac is not None and rec_prog is not None)
            mod = str(paq.get("metadata_modified") or "")
            candidatos.append(((es_total, ambos, mod), paq))
        if candidatos:
            candidatos.sort(key=lambda item: item[0], reverse=True)
            return candidatos[0][1]
    return None


def _cargar_csv_recurso_ckan(
    recurso: Mapping[str, Any] | None,
    timeout: int = TIMEOUT_CKAN_SEGUNDOS,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Descarga y parsea el CSV oficial de un recurso CKAN cuando su Datastore está vacío/inactivo."""
    import csv as _csv
    import io as _io

    if not isinstance(recurso, Mapping):
        return [], []
    url = str(recurso.get("url") or "").strip()
    if not url or not url.lower().startswith(("http://", "https://")):
        return [], []
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv, */*"})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    texto: str | None = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "iso-8859-1"):
        try:
            texto = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if texto is None:
        texto = raw.decode("utf-8", errors="replace")
    primera = texto.splitlines()[0] if texto.splitlines() else ""
    delim = ";" if primera.count(";") >= primera.count(",") else ","
    reader = _csv.DictReader(_io.StringIO(texto), delimiter=delim)
    campos = [str(c).strip() for c in (reader.fieldnames or []) if c]
    filas = [
        {str(k).strip(): v for k, v in row.items() if k is not None}
        for row in reader
    ]
    return filas, campos


def _clasificar_filas_programa_desde_lista(
    filas_todas: Sequence[Mapping[str, Any]],
    campos: Sequence[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Separa filas de GORE Aysén, Vialidad MOP (12-02) y servicios en Aysén desde una lista completa."""
    filas_gore: list[dict[str, Any]] = []
    filas_p12: list[dict[str, Any]] = []
    dedup_serv: dict[str, dict[str, Any]] = {}

    for fila in filas_todas:
        if _es_fila_gore_aysen(fila):
            filas_gore.append(dict(fila))
            continue
        partida = _extraer_codigo_subtitulo(_valor_campo(fila, "Partida", "Codigo Partida"))
        if partida == "12":
            filas_p12.append(dict(fila))
        if _es_fila_partida05_aysen(fila):
            dedup_serv[_clave_dedup_registro(fila)] = dict(fila)

    filas_vialidad = _filtrar_filas_vialidad_mop(filas_p12)
    return filas_gore, filas_vialidad, list(dedup_serv.values()), list(campos)


def _consultar_filas_programa_piloto(
    resource_id: str,
    http_get_json: Callable[[str, int], dict[str, Any]],
    *,
    recurso: Mapping[str, Any] | None = None,
    permitir_csv_directo: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Consulta en un recurso ``A nivel Programa`` las filas de GORE, Vialidad MOP y servicios Aysén."""
    # 1. Partida 31 -> GORE Aysén (2023+)
    try:
        reg_p31, c_p31 = _datastore_search_paginado(
            resource_id, http_get_json, filters={"Partida": "31"}
        )
    except DipresCkanError:
        if permitir_csv_directo and recurso is not None:
            filas_csv, campos_csv = _cargar_csv_recurso_ckan(recurso)
            if filas_csv:
                return _clasificar_filas_programa_desde_lista(filas_csv, campos_csv)
        raise

    filas_gore = [dict(f) for f in reg_p31 if _es_fila_gore_aysen(f)]

    # 2. Partida 12 Capítulo 02 -> Dirección de Vialidad MOP
    reg_p12: list[dict[str, Any]] = []
    c_p12: list[str] = []
    for filtro_vialidad in (
        {"Partida": "12", "Capitulo": "02"},
        {"Partida": "12", "Capitulo": "2"},
        {"Partida": "12"},
    ):
        try:
            reg_p12, c_p12 = _datastore_search_paginado(
                resource_id, http_get_json, filters=filtro_vialidad
            )
        except DipresCkanError:
            reg_p12 = []
        if reg_p12:
            break
    filas_vialidad = _filtrar_filas_vialidad_mop(reg_p12)

    # 3. Partida 05 + búsqueda textual AYSÉN -> Servicios regionales en Aysén (y GORE P05 en 2018-2022)
    reg_p05: list[dict[str, Any]] = []
    c_p05: list[str] = []
    for cod_p05 in ("05", "5"):
        try:
            reg_p05, c_p05 = _datastore_search_paginado(
                resource_id, http_get_json, filters={"Partida": cod_p05}
            )
        except DipresCkanError:
            reg_p05 = []
        if reg_p05:
            break
    try:
        reg_q_aysen, c_q = _datastore_search_paginado(resource_id, http_get_json, q="AYSÉN")
    except DipresCkanError:
        reg_q_aysen, c_q = [], []

    dedup_gore: dict[str, dict[str, Any]] = {_clave_dedup_registro(f): f for f in filas_gore}
    dedup_serv: dict[str, dict[str, Any]] = {}
    for fila in reg_p05:
        if _es_fila_gore_aysen(fila):
            dedup_gore[_clave_dedup_registro(fila)] = dict(fila)
        elif _es_fila_partida05_aysen(fila):
            dedup_serv[_clave_dedup_registro(fila)] = dict(fila)
    for fila in reg_q_aysen:
        if _es_fila_gore_aysen(fila):
            dedup_gore[_clave_dedup_registro(fila)] = dict(fila)
        else:
            dedup_serv[_clave_dedup_registro(fila)] = dict(fila)
    filas_gore = list(dedup_gore.values())
    filas_servicios = list(dedup_serv.values())

    campos: list[str] = []
    for lista in (c_p31, c_p12, c_p05, c_q):
        for c in lista:
            if c not in campos:
                campos.append(c)

    if permitir_csv_directo and recurso is not None and not filas_gore and not filas_vialidad:
        filas_csv, campos_csv = _cargar_csv_recurso_ckan(recurso)
        if filas_csv:
            return _clasificar_filas_programa_desde_lista(filas_csv, campos_csv)

    return filas_gore, filas_vialidad, filas_servicios, campos


def _grupo_partida_subtitulo(codigo_subtitulo: str) -> str | None:
    """Mapea un código de subtítulo de 2 dígitos a su grupo de desglose presupuestario."""
    if codigo_subtitulo in _SUBTITULOS_INGRESOS_FINANCIAMIENTO:
        return None
    if codigo_subtitulo in _SUBTITULOS_GASTO_CORRIENTE:
        return codigo_subtitulo
    if codigo_subtitulo in _SUBTITULOS_INVERSION:
        return "29-31"
    if codigo_subtitulo in _SUBTITULOS_TRANSFERENCIAS_CAPITAL:
        return "33"
    return "otros"


def _preparar_filas_limpias(
    filas: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Deduplica, excluye moneda no-CLP y totales, y elimina doble conteo padre/hijo."""
    dedup: dict[str, dict[str, Any]] = {}
    for fila in filas:
        dedup[_clave_dedup_registro(fila)] = dict(fila)

    limpias: list[dict[str, Any]] = []
    no_clp = 0
    for fila in dedup.values():
        if _es_moneda_no_clp(fila):
            no_clp += 1
            continue
        if _es_fila_total_o_sin_subtitulo(fila):
            continue
        limpias.append(fila)
    return _eliminar_padres_con_hijos(limpias), no_clp


def _recolectar_columnas(
    filas: Sequence[Mapping[str, Any]],
    campos_base: Sequence[str] = (),
) -> list[str]:
    cols = list(campos_base)
    vistos = set(cols)
    for fila in filas:
        for k in fila.keys():
            if k not in vistos:
                vistos.add(k)
                cols.append(k)
    return cols


def _sumar_montos_gasto_por_grupo(
    filas: Sequence[Mapping[str, Any]],
    columna: str | None,
) -> tuple[dict[str, Decimal], Decimal, Decimal, bool]:
    """Suma montos en miles CLP por grupo de partida excluyendo ingresos (01–15).

    Retorna ``(por_grupo_miles, total_gasto_miles, ingresos_miles, tuvo_valores)``.
    """
    por_grupo: dict[str, Decimal] = {cod: CERO for cod, _, _ in _DESGLOSE_PARTIDAS_ORDEN}
    total_gasto = CERO
    ingresos = CERO
    tuvo_valores = False
    if not columna:
        return por_grupo, total_gasto, ingresos, False

    with localcontext(CONTEXTO_DECIMAL):
        for fila in filas:
            monto = parsear_monto_dipres(fila.get(columna))
            if monto is None:
                continue
            tuvo_valores = True
            sub = _extraer_codigo_subtitulo(
                _valor_campo(fila, "Subtitulo", "Subtítulo", "Codigo Subtitulo")
            )
            grupo = _grupo_partida_subtitulo(sub)
            if grupo is None:
                ingresos += monto
            else:
                por_grupo[grupo] += monto
                total_gasto += monto

    return por_grupo, total_gasto, ingresos, tuvo_valores


def _etiqueta_periodo_piloto(anio: int, mes_corte: int | None) -> str:
    if mes_corte == 12:
        return f"Año completo {anio} (enero–diciembre)"
    if mes_corte == 1:
        return f"enero {anio}"
    if mes_corte is not None and 2 <= mes_corte < 12:
        return f"enero–{_MESES_NOMBRE_POR_NUMERO[mes_corte]} {anio}"
    return f"ejercicio {anio}"


def _construir_frase_radial_entidad(
    nombre_corto: str,
    anio: int,
    mes_corte: int | None,
    pct_corriente: Decimal | None,
    pct_inversion_capital: Decimal | None,
    ejecutado_mm: Decimal | None,
) -> str | None:
    if pct_corriente is None or pct_inversion_capital is None or ejecutado_mm is None:
        return None
    if mes_corte == 12:
        periodo_txt = f"en {anio}"
    elif mes_corte == 1:
        periodo_txt = f"en enero de {anio}"
    elif mes_corte is not None and 2 <= mes_corte < 12:
        periodo_txt = f"entre enero y {_MESES_NOMBRE_POR_NUMERO[mes_corte]} de {anio}"
    else:
        periodo_txt = f"en {anio}"

    corr_cl = _formatear_cl(pct_corriente, decimales=1)
    inv_cl = _formatear_cl(pct_inversion_capital, decimales=1)
    base_cl = _formatear_cl(ejecutado_mm, decimales=1)
    return (
        f"De cada $100 ejecutados por {nombre_corto} {periodo_txt}, "
        f"${corr_cl} correspondieron a gasto corriente y ${inv_cl} a inversión y "
        f"transferencias de capital (base: ${base_cl} millones ejecutados según DIPRES CKAN)."
    )


def _construir_costo_administrar(
    entidad_id: str,
    por_grupo_miles: Mapping[str, Decimal],
    total_gasto_miles: Decimal,
) -> dict[str, Any]:
    """Construye el bloque ``costo_administrar`` transparente según perímetro de cada entidad."""
    if total_gasto_miles <= CERO:
        return {
            "disponible": False,
            "monto_millones": None,
            "porcentaje": None,
            "explicacion": "Sin gasto ejecutado positivo en CLP en el corte consultado.",
        }

    with localcontext(CONTEXTO_DECIMAL):
        if entidad_id == "gore_aysen":
            monto_miles = sum(
                (por_grupo_miles.get(cod, CERO) for cod in ("21", "22", "23", "24", "25", "26")),
                CERO,
            )
            explicacion = (
                "Corresponde al gasto corriente de funcionamiento (Subt. 21–26) sobre el total "
                "ejecutado de la Partida 31 para GORE Aysén; el desglose administrativo interno "
                "detallado requiere contraste con los Programas 01 y 02 del propio GORE."
            )
        elif entidad_id == "gobierno_central_nacional":
            monto_miles = por_grupo_miles.get("21", CERO) + por_grupo_miles.get("22", CERO)
            explicacion = (
                "Corresponde a funcionamiento directo (Subt. 21 Personal + Subt. 22 Bienes y "
                "Servicios de Consumo) sobre el total ejecutado nacional; excluye transferencias "
                "corrientes (Subt. 24) y seguridad social (Subt. 23), e incluye dotación "
                "asistencial (salud, educación y orden público), no solo burocracia central."
            )
        elif entidad_id == "vialidad_mop_nacional":
            monto_miles = por_grupo_miles.get("21", CERO) + por_grupo_miles.get("22", CERO)
            explicacion = (
                "Corresponde a funcionamiento directo (Subt. 21 Personal + Subt. 22 Bienes y "
                "Servicios de Consumo) sobre el total ejecutado nacional de la Dirección de "
                "Vialidad MOP frente a su cartera de inversión vial."
            )
        else:
            monto_miles = por_grupo_miles.get("21", CERO) + por_grupo_miles.get("22", CERO)
            explicacion = (
                "Corresponde a funcionamiento directo (Subt. 21 Personal + Subt. 22 Bienes y "
                "Servicios de Consumo) sobre el total ejecutado de los servicios públicos "
                "identificables en Aysén (incluye personal asistencial de salud y otros servicios)."
            )

        monto_mm = _a_millones_clp(monto_miles)
        pct = ((CIEN * monto_miles) / total_gasto_miles).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    return {
        "disponible": True,
        "monto_millones": _formatear_decimal(monto_mm),
        "porcentaje": _formatear_decimal(pct),
        "explicacion": explicacion,
    }


def _construir_comparacion_mismo_mes(
    actual_mm: Decimal | None,
    anterior_mm: Decimal | None,
    anio: int,
    mes_corte: int,
    package_name_anterior: str | None,
) -> dict[str, Any]:
    """Calcula variación nominal interanual comparable en meses equivalentes."""
    nombre_mes = _MESES_NOMBRE_POR_NUMERO[mes_corte]
    anio_ant = anio - 1
    etiqueta = (
        f"enero {anio} vs enero {anio_ant}"
        if mes_corte == 1
        else f"enero–{nombre_mes} {anio} vs enero–{nombre_mes} {anio_ant}"
    )

    if actual_mm is None or anterior_mm is None:
        return {
            "disponible": False,
            "comparable": False,
            "anio_anterior": anio_ant,
            "mes_corte": mes_corte,
            "etiqueta": etiqueta,
            "ejecutado_mismo_mes_anterior_millones": (
                _formatear_decimal(anterior_mm) if anterior_mm is not None else None
            ),
            "diferencia_millones": None,
            "variacion_nominal_pct": None,
            "url_respaldo_anterior": _url_dataset_publico(package_name_anterior),
            "motivo": (
                f"No se encontró ejecución comparable en CKAN para el mismo corte "
                f"({nombre_mes} {anio_ant})."
            ),
        }

    with localcontext(CONTEXTO_DECIMAL):
        diferencia = actual_mm - anterior_mm
        variacion_pct: str | None = None
        if anterior_mm > CERO:
            var_dec = ((CIEN * diferencia) / anterior_mm).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            variacion_pct = _formatear_decimal(var_dec)

    return {
        "disponible": True,
        "comparable": True,
        "anio_anterior": anio_ant,
        "mes_corte": mes_corte,
        "etiqueta": etiqueta,
        "ejecutado_mismo_mes_anterior_millones": _formatear_decimal(anterior_mm),
        "diferencia_millones": _formatear_decimal(diferencia),
        "variacion_nominal_pct": variacion_pct,
        "url_respaldo_anterior": _url_dataset_publico(package_name_anterior),
        "nota": (
            "Variación nominal interanual en meses acumulados equivalentes (pesos corrientes, "
            "no deflactados por IPC)."
        ),
    }


def _construir_entidad_piloto(
    *,
    entidad_id: str,
    nombre: str,
    nombre_radial: str,
    territorio_etiqueta: str,
    filas_ejecucion: Sequence[Mapping[str, Any]],
    campos_ejecucion: Sequence[str],
    filas_ley: Sequence[Mapping[str, Any]] | None,
    campos_ley: Sequence[str],
    anio: int,
    mes_corte: int | None,
    url_respaldo: str | None,
    url_respaldo_ley: str | None,
    motivo_inicial_vigente: str | None,
    nota_cobertura: str | None = None,
) -> tuple[dict[str, Any], Decimal | None, int]:
    """Agrega una entidad del Piloto Presupuestario con aritmética exacta ``Decimal(34)``."""
    filas_ejec_limpias, no_clp_ejec = _preparar_filas_limpias(filas_ejecucion)
    cols_ejec = _recolectar_columnas(filas_ejec_limpias, campos_ejecucion)
    col_ejec, col_vig_en_ejec, col_ini_en_ejec = detectar_columnas_montos(cols_ejec)

    ejec_por_grupo, total_ejec_miles, ingresos_excl_miles, tuvo_ejec = _sumar_montos_gasto_por_grupo(
        filas_ejec_limpias, col_ejec
    )

    # Presupuesto inicial y vigente: prioridad al paquete de Ley con datastore_active=True.
    ini_por_grupo: dict[str, Decimal] = {}
    vig_por_grupo: dict[str, Decimal] = {}
    total_ini_miles: Decimal | None = None
    total_vig_miles: Decimal | None = None
    no_clp_ley = 0
    motivo_iv = motivo_inicial_vigente

    if filas_ley is not None:
        filas_ley_limpias, no_clp_ley = _preparar_filas_limpias(filas_ley)
        cols_ley = _recolectar_columnas(filas_ley_limpias, campos_ley)
        col_ini_ley, col_vig_ley = _detectar_columnas_ley(cols_ley)
        ini_grp, tot_ini, _, tuvo_ini = _sumar_montos_gasto_por_grupo(filas_ley_limpias, col_ini_ley)
        vig_grp, tot_vig, _, tuvo_vig = _sumar_montos_gasto_por_grupo(filas_ley_limpias, col_vig_ley)
        if tuvo_ini:
            ini_por_grupo = ini_grp
            total_ini_miles = tot_ini
        if tuvo_vig:
            vig_por_grupo = vig_grp
            total_vig_miles = tot_vig
        if tuvo_ini or tuvo_vig:
            motivo_iv = None
        elif motivo_iv is None:
            motivo_iv = (
                "El recurso CKAN de Ley de Presupuestos no devolvió filas de gasto CLP "
                "para esta entidad."
            )
    else:
        # Si el propio recurso de ejecución incluyera columnas inicial/vigente con datos reales, usarlas.
        if col_ini_en_ejec:
            ini_grp, tot_ini, _, tuvo_ini = _sumar_montos_gasto_por_grupo(
                filas_ejec_limpias, col_ini_en_ejec
            )
            if tuvo_ini:
                ini_por_grupo = ini_grp
                total_ini_miles = tot_ini
        if col_vig_en_ejec:
            vig_grp, tot_vig, _, tuvo_vig = _sumar_montos_gasto_por_grupo(
                filas_ejec_limpias, col_vig_en_ejec
            )
            if tuvo_vig:
                vig_por_grupo = vig_grp
                total_vig_miles = tot_vig
        if total_ini_miles is not None or total_vig_miles is not None:
            motivo_iv = None

    with localcontext(CONTEXTO_DECIMAL):
        ejecutado_mm: Decimal | None = _a_millones_clp(total_ejec_miles) if tuvo_ejec else None
        inicial_mm: Decimal | None = (
            _a_millones_clp(total_ini_miles) if total_ini_miles is not None else None
        )
        vigente_mm: Decimal | None = (
            _a_millones_clp(total_vig_miles) if total_vig_miles is not None else None
        )

        corriente_miles = sum(
            (ejec_por_grupo[cod] for cod in ("21", "22", "23", "24", "25", "26")),
            CERO,
        )
        inv_cap_miles = ejec_por_grupo["29-31"] + ejec_por_grupo["33"]
        otros_miles = ejec_por_grupo["otros"]

        gasto_corriente_mm = _a_millones_clp(corriente_miles) if tuvo_ejec else None
        inv_cap_mm = _a_millones_clp(inv_cap_miles) if tuvo_ejec else None
        otros_mm = _a_millones_clp(otros_miles) if tuvo_ejec else None
        ingresos_excl_mm = _a_millones_clp(ingresos_excl_miles)

        gasto_corriente_pct_dec: Decimal | None = None
        gasto_corriente_pct_str: str | None = None
        inv_cap_pct_dec: Decimal | None = None
        inv_cap_pct_str: str | None = None
        if tuvo_ejec and total_ejec_miles > CERO:
            gasto_corriente_pct_dec = (CIEN * corriente_miles) / total_ejec_miles
            gasto_corriente_pct_str = _formatear_decimal(
                gasto_corriente_pct_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            )
            inv_cap_pct_dec = (CIEN * inv_cap_miles) / total_ejec_miles
            inv_cap_pct_str = _formatear_decimal(
                inv_cap_pct_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            )

        tasa_ejecucion_pct_str: str | None = None
        saldo_por_devengar_str: str | None = None
        if vigente_mm is not None and ejecutado_mm is not None:
            saldo_por_devengar_str = _formatear_decimal(vigente_mm - ejecutado_mm)
            if vigente_mm > CERO:
                tasa_dec = ((CIEN * ejecutado_mm) / vigente_mm).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                tasa_ejecucion_pct_str = _formatear_decimal(tasa_dec)

        desglose_partidas: list[dict[str, Any]] = []
        for codigo, etiqueta, categoria in _DESGLOSE_PARTIDAS_ORDEN:
            m_ejec = ejec_por_grupo[codigo]
            m_ini = ini_por_grupo.get(codigo) if total_ini_miles is not None else None
            m_vig = vig_por_grupo.get(codigo) if total_vig_miles is not None else None
            if (
                m_ejec == CERO
                and (m_ini is None or m_ini == CERO)
                and (m_vig is None or m_vig == CERO)
            ):
                continue
            pct_partida: str | None = None
            if total_ejec_miles > CERO:
                pct_partida = _formatear_decimal(
                    ((CIEN * m_ejec) / total_ejec_miles).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                )
            desglose_partidas.append(
                {
                    "codigo": codigo,
                    "etiqueta": etiqueta,
                    "categoria": categoria,
                    "inicial_millones": (
                        _formatear_decimal(_a_millones_clp(m_ini)) if m_ini is not None else None
                    ),
                    "vigente_millones": (
                        _formatear_decimal(_a_millones_clp(m_vig)) if m_vig is not None else None
                    ),
                    "ejecutado_millones": _formatear_decimal(_a_millones_clp(m_ejec)),
                    "porcentaje_ejecutado_pct": pct_partida,
                }
            )

    costo_administrar = _construir_costo_administrar(
        entidad_id=entidad_id,
        por_grupo_miles=ejec_por_grupo,
        total_gasto_miles=total_ejec_miles if tuvo_ejec else CERO,
    )
    frase_radial = _construir_frase_radial_entidad(
        nombre_corto=nombre_radial,
        anio=anio,
        mes_corte=mes_corte,
        pct_corriente=gasto_corriente_pct_dec,
        pct_inversion_capital=inv_cap_pct_dec,
        ejecutado_mm=ejecutado_mm,
    )

    entidad_dict: dict[str, Any] = {
        "id": entidad_id,
        "nombre": nombre,
        "territorio_etiqueta": territorio_etiqueta,
        "inicial_millones": _formatear_decimal(inicial_mm) if inicial_mm is not None else None,
        "vigente_millones": _formatear_decimal(vigente_mm) if vigente_mm is not None else None,
        "ejecutado_millones": _formatear_decimal(ejecutado_mm) if ejecutado_mm is not None else None,
        "tasa_ejecucion_pct": tasa_ejecucion_pct_str,
        "saldo_por_devengar_millones": saldo_por_devengar_str,
        "gasto_corriente_millones": (
            _formatear_decimal(gasto_corriente_mm) if gasto_corriente_mm is not None else None
        ),
        "gasto_corriente_pct": gasto_corriente_pct_str,
        "inversion_y_capital_millones": (
            _formatear_decimal(inv_cap_mm) if inv_cap_mm is not None else None
        ),
        "inversion_y_capital_pct": inv_cap_pct_str,
        "otros_gastos_millones": _formatear_decimal(otros_mm) if otros_mm is not None else None,
        "ingresos_financiamiento_excluidos_millones": _formatear_decimal(ingresos_excl_mm),
        "base_calculo_porcentaje": _BASE_CALCULO_PORCENTAJE_PILOTO,
        "frase_radial": frase_radial,
        "desglose_partidas": desglose_partidas,
        "costo_administrar": costo_administrar,
        "comparacion_mismo_mes_anterior": None,
        "url_respaldo": url_respaldo,
        "url_respaldo_ley": url_respaldo_ley,
        "motivo_inicial_vigente": motivo_iv,
        "nota_cobertura": nota_cobertura,
        "registros_no_clp_excluidos": no_clp_ejec + no_clp_ley,
    }
    return entidad_dict, ejecutado_mm, no_clp_ejec + no_clp_ley


def obtener_presupuestos_piloto_live(
    anio: int = 2025,
    refresh: bool = False,
    cache_path: Path | None = None,
    *,
    http_get_json: Callable[[str, int], dict[str, Any]] | None = None,
    ttl_segundos: int = CACHE_TTL_SEGUNDOS,
) -> dict[str, Any]:
    """Obtiene el Piloto Presupuestario completo desde DIPRES CKAN (`datos.gob.cl`).

    Cubre cuatro entidades con etapas separadas (Inicial, Vigente, Ejecutado),
    moneda estrictamente CLP (excluyendo USD/dólares) y comparación interanual
    en meses equivalentes cuando ``mes_corte < 12``:
    - ``gobierno_central_nacional`` (recurso ``A nivel Nacional``)
    - ``gore_aysen`` (Partida 31, recurso ``A nivel Programa``)
    - ``vialidad_mop_nacional`` (Partida 12 Capítulo 02, recurso ``A nivel Programa``)
    - ``servicios_regionales_aysen`` (Partida 05 + búsqueda ``AYSÉN``, ``A nivel Programa``)

    Usa caché local en ``<repo_root>/data/raw/dipres-piloto-{anio}.json`` (TTL 12h)
    y devuelve automáticamente el último corte aprobado ante fallas de red/CKAN.
    """
    if not isinstance(anio, int) or isinstance(anio, bool) or not (2010 <= anio <= 2035):
        raise ValueError(f"Año presupuestario inválido: {anio!r}")

    ruta_cache = cache_path or (_RAIZ_REPO / "data" / "raw" / f"dipres-piloto-{anio}.json")
    if not refresh:
        en_cache = _leer_cache_vigente(ruta_cache, ttl_segundos)
        if en_cache is not None:
            return en_cache

    fetcher = http_get_json or _http_get_json
    ahora_utc = datetime.now(timezone.utc)

    try:
        # 1. Paquete de ejecución del año consultado
        paquete_ejec, recurso_prog = _buscar_paquete_ejecucion(anio, fetcher, ahora_utc.year)
        recurso_nac = _seleccionar_recurso_nivel_nacional(paquete_ejec)
        res_id_prog = str(recurso_prog["id"])
        res_id_nac = str(recurso_nac["id"]) if recurso_nac is not None else None

        # Ejecución A nivel Programa (GORE Aysén, Vialidad MOP 12-02, servicios Aysén)
        es_live = http_get_json is None
        filas_gore, filas_vialidad, filas_serv, campos_prog = _consultar_filas_programa_piloto(
            res_id_prog, fetcher, recurso=recurso_prog, permitir_csv_directo=es_live
        )

        # Ejecución A nivel Nacional (Gobierno Central de Chile)
        if res_id_nac is not None:
            filas_nac, campos_nac = _datastore_search_paginado(res_id_nac, fetcher)
            if es_live and (not filas_nac or campos_nac == ["_id"]):
                filas_nac_csv, campos_nac_csv = _cargar_csv_recurso_ckan(recurso_nac)
                if filas_nac_csv:
                    filas_nac, campos_nac = filas_nac_csv, campos_nac_csv
        else:
            filas_nac, campos_nac = [], []
    except (DipresCkanError, HTTPError, URLError, TimeoutError, OSError) as exc:
        respaldo = _leer_cache_respaldo(ruta_cache, exc)
        if respaldo is not None:
            return respaldo
        raise

    cols_prog_all = _recolectar_columnas(filas_gore + filas_vialidad + filas_serv, campos_prog)
    col_ejec_prog, _, _ = detectar_columnas_montos(cols_prog_all)
    cols_nac_all = _recolectar_columnas(filas_nac, campos_nac)
    col_ejec_nac, _, _ = detectar_columnas_montos(cols_nac_all)

    mes_corte = detectar_mes_corte(
        columna_ejecucion=col_ejec_prog or col_ejec_nac,
        package_title=paquete_ejec.get("title"),
        package_name=paquete_ejec.get("name"),
    )
    es_cierre_anual = mes_corte == 12
    advertencia_comparabilidad = _construir_advertencia_comparabilidad_meses(mes_corte, anio)
    url_ejec = _url_dataset_publico(paquete_ejec.get("name"))

    # 2. Ley de Presupuestos Inicial y Vigente (solo cuando datastore_active == True)
    ley_info = _buscar_paquete_ley_piloto(anio, mes_corte, fetcher)
    ley_nac_filas: list[dict[str, Any]] | None = None
    ley_nac_campos: list[str] = []
    ley_gore_filas: list[dict[str, Any]] | None = None
    ley_vial_filas: list[dict[str, Any]] | None = None
    ley_serv_filas: list[dict[str, Any]] | None = None
    ley_prog_campos: list[str] = []

    if ley_info["encontrado"] and ley_info["tiene_datastore_active"]:
        rec_ley_nac = ley_info["recurso_nacional"]
        if rec_ley_nac is not None and rec_ley_nac.get("id"):
            try:
                ley_nac_filas, ley_nac_campos = _datastore_search_paginado(
                    str(rec_ley_nac["id"]), fetcher
                )
                if es_live and (not ley_nac_filas or ley_nac_campos == ["_id"]):
                    ley_nac_filas, ley_nac_campos = _cargar_csv_recurso_ckan(rec_ley_nac)
            except DipresCkanError:
                ley_nac_filas = None
        rec_ley_prog = ley_info["recurso_programa"]
        if rec_ley_prog is not None and rec_ley_prog.get("id"):
            try:
                (
                    ley_gore_filas,
                    ley_vial_filas,
                    ley_serv_filas,
                    ley_prog_campos,
                ) = _consultar_filas_programa_piloto(
                    str(rec_ley_prog["id"]), fetcher, recurso=rec_ley_prog, permitir_csv_directo=es_live
                )
            except DipresCkanError:
                ley_gore_filas = None
                ley_vial_filas = None
                ley_serv_filas = None
    elif ley_info["encontrado"] and es_live:
        rec_ley_nac = ley_info.get("recurso_nacional")
        rec_ley_prog = ley_info.get("recurso_programa")
        if rec_ley_nac is not None:
            try:
                ley_nac_filas, ley_nac_campos = _cargar_csv_recurso_ckan(rec_ley_nac)
            except Exception:
                ley_nac_filas = None
        if rec_ley_prog is not None:
            try:
                filas_lcsv, campos_lcsv = _cargar_csv_recurso_ckan(rec_ley_prog)
                if filas_lcsv:
                    (
                        ley_gore_filas,
                        ley_vial_filas,
                        ley_serv_filas,
                        ley_prog_campos,
                    ) = _clasificar_filas_programa_desde_lista(filas_lcsv, campos_lcsv)
            except Exception:
                ley_gore_filas = None

    motivo_iv_general = ley_info["nota"]
    url_ley = ley_info["url_respaldo"]

    # Construir las 4 entidades del Piloto Presupuestario
    ent_nac, ejec_nac_mm, no_clp_nac = _construir_entidad_piloto(
        entidad_id="gobierno_central_nacional",
        nombre="Gobierno Central de Chile (Nivel Nacional)",
        nombre_radial="el Gobierno Central de Chile",
        territorio_etiqueta="Chile (Nivel Nacional)",
        filas_ejecucion=filas_nac,
        campos_ejecucion=campos_nac,
        filas_ley=ley_nac_filas,
        campos_ley=ley_nac_campos,
        anio=anio,
        mes_corte=mes_corte,
        url_respaldo=url_ejec,
        url_respaldo_ley=url_ley,
        motivo_inicial_vigente=motivo_iv_general,
        nota_cobertura=(
            "Recurso 'A nivel Nacional' del Gobierno Central Total, filtrado estrictamente "
            "a moneda PESOS/CLP (excluyendo registros en DOLARES)."
            if res_id_nac is not None
            else "El paquete CKAN de ejecución no publicó un recurso 'A nivel Nacional' con datastore_active=True."
        ),
    )

    ent_gore, ejec_gore_mm, no_clp_gore = _construir_entidad_piloto(
        entidad_id="gore_aysen",
        nombre="Gobierno Regional de Aysén (Partida 31)",
        nombre_radial="el Gobierno Regional de Aysén (Partida 31)",
        territorio_etiqueta="Región de Aysén",
        filas_ejecucion=filas_gore,
        campos_ejecucion=campos_prog,
        filas_ley=ley_gore_filas,
        campos_ley=ley_prog_campos,
        anio=anio,
        mes_corte=mes_corte,
        url_respaldo=url_ejec,
        url_respaldo_ley=url_ley,
        motivo_inicial_vigente=motivo_iv_general,
        nota_cobertura=(
            "Partida 31 (Financiamiento Gobiernos Regionales) — Programa GORE Aysén; "
            "separa ingresos/financiamiento (Subt. 01–15) del gasto directo (Subt. 21–33)."
        ),
    )

    ent_vialidad, ejec_vial_mm, no_clp_vial = _construir_entidad_piloto(
        entidad_id="vialidad_mop_nacional",
        nombre="Dirección de Vialidad — MOP (Partida 12, Capítulo 02)",
        nombre_radial="la Dirección de Vialidad del MOP",
        territorio_etiqueta=(
            "Chile (Nacional — Dirección de Vialidad MOP; territorialización regional en pestaña Proyectos)"
        ),
        filas_ejecucion=filas_vialidad,
        campos_ejecucion=campos_prog,
        filas_ley=ley_vial_filas,
        campos_ley=ley_prog_campos,
        anio=anio,
        mes_corte=mes_corte,
        url_respaldo=url_ejec,
        url_respaldo_ley=url_ley,
        motivo_inicial_vigente=motivo_iv_general,
        nota_cobertura=(
            "Partida 12 Capítulo 02 (Dirección de Vialidad MOP) a escala nacional; "
            "la atribución regional por iniciativa se audita en la cartera de proyectos."
        ),
    )

    ent_servicios, ejec_serv_mm, no_clp_serv = _construir_entidad_piloto(
        entidad_id="servicios_regionales_aysen",
        nombre="Servicios Públicos del Gobierno Central en Aysén",
        nombre_radial="los servicios públicos del Gobierno Central en Aysén",
        territorio_etiqueta="Región de Aysén (servicios públicos identificables en CKAN DIPRES)",
        filas_ejecucion=filas_serv,
        campos_ejecucion=campos_prog,
        filas_ley=ley_serv_filas,
        campos_ley=ley_prog_campos,
        anio=anio,
        mes_corte=mes_corte,
        url_respaldo=url_ejec,
        url_respaldo_ley=url_ley,
        motivo_inicial_vigente=motivo_iv_general,
        nota_cobertura=(
            "Agrupa servicios del Gobierno Central identificables explícitamente en Aysén "
            "(Partida 05 Aysén y búsqueda 'AYSÉN', excluyendo Partida 31 GORE para evitar doble conteo)."
        ),
    )

    # 3. Comparación mismo mes del año anterior cuando mes_corte < 12
    comparacion_interanual_meta: dict[str, Any] | None = None
    if mes_corte is not None and 1 <= mes_corte < 12:
        anio_ant = anio - 1
        paq_ant = _buscar_paquete_ejecucion_mes(anio_ant, mes_corte, fetcher)
        pkg_name_ant = paq_ant.get("name") if paq_ant else None
        ant_nac_mm: Decimal | None = None
        ant_gore_mm: Decimal | None = None
        ant_vial_mm: Decimal | None = None
        ant_serv_mm: Decimal | None = None

        if paq_ant is not None:
            rec_ant_nac = _seleccionar_recurso_nivel_nacional(paq_ant)
            if rec_ant_nac is not None and rec_ant_nac.get("id"):
                try:
                    f_ant_nac, c_ant_nac = _datastore_search_paginado(
                        str(rec_ant_nac["id"]), fetcher
                    )
                    f_ant_nac_limp, _ = _preparar_filas_limpias(f_ant_nac)
                    col_ant_nac, _, _ = detectar_columnas_montos(
                        _recolectar_columnas(f_ant_nac_limp, c_ant_nac)
                    )
                    _, tot_ant_nac, _, ok_nac = _sumar_montos_gasto_por_grupo(
                        f_ant_nac_limp, col_ant_nac
                    )
                    if ok_nac:
                        ant_nac_mm = _a_millones_clp(tot_ant_nac)
                except DipresCkanError:
                    ant_nac_mm = None

            rec_ant_prog = _seleccionar_recurso_ejecucion(paq_ant)
            if rec_ant_prog is not None and rec_ant_prog.get("id"):
                try:
                    f_ant_gore, f_ant_vial, f_ant_serv, c_ant_prog = (
                        _consultar_filas_programa_piloto(str(rec_ant_prog["id"]), fetcher)
                    )
                    for filas_ent, destino in (
                        (f_ant_gore, "gore"),
                        (f_ant_vial, "vial"),
                        (f_ant_serv, "serv"),
                    ):
                        f_limp, _ = _preparar_filas_limpias(filas_ent)
                        col_ant, _, _ = detectar_columnas_montos(
                            _recolectar_columnas(f_limp, c_ant_prog)
                        )
                        _, tot_ant, _, ok_ent = _sumar_montos_gasto_por_grupo(f_limp, col_ant)
                        if ok_ent:
                            val_mm = _a_millones_clp(tot_ant)
                            if destino == "gore":
                                ant_gore_mm = val_mm
                            elif destino == "vial":
                                ant_vial_mm = val_mm
                            else:
                                ant_serv_mm = val_mm
                except DipresCkanError:
                    pass

        ent_nac["comparacion_mismo_mes_anterior"] = _construir_comparacion_mismo_mes(
            ejec_nac_mm, ant_nac_mm, anio, mes_corte, pkg_name_ant
        )
        ent_gore["comparacion_mismo_mes_anterior"] = _construir_comparacion_mismo_mes(
            ejec_gore_mm, ant_gore_mm, anio, mes_corte, pkg_name_ant
        )
        ent_vialidad["comparacion_mismo_mes_anterior"] = _construir_comparacion_mismo_mes(
            ejec_vial_mm, ant_vial_mm, anio, mes_corte, pkg_name_ant
        )
        ent_servicios["comparacion_mismo_mes_anterior"] = _construir_comparacion_mismo_mes(
            ejec_serv_mm, ant_serv_mm, anio, mes_corte, pkg_name_ant
        )
        comparacion_interanual_meta = {
            "anio_base": anio_ant,
            "mes_corte": mes_corte,
            "etiqueta": ent_nac["comparacion_mismo_mes_anterior"]["etiqueta"],
            "encontrado": paq_ant is not None,
            "package_name": pkg_name_ant,
            "package_title": paq_ant.get("title") if paq_ant else None,
            "url_respaldo": _url_dataset_publico(pkg_name_ant),
        }

    extraido_en = ahora_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    ley_resumen = {
        "encontrado": ley_info["encontrado"],
        "anio": ley_info["anio"],
        "package_name": ley_info["package_name"],
        "package_title": ley_info["package_title"],
        "url_respaldo": ley_info["url_respaldo"],
        "actualizado_en": ley_info["actualizado_en"],
        "tiene_datastore_active": ley_info["tiene_datastore_active"],
        "nota": ley_info["nota"],
    }

    resultado: dict[str, Any] = {
        "esquema": ESQUEMA_PILOTO_PRESUPUESTARIO,
        "anio": anio,
        "mes_corte": mes_corte,
        "es_cierre_anual": es_cierre_anual,
        "periodo_etiqueta": _etiqueta_periodo_piloto(anio, mes_corte),
        "entidades": {
            "gobierno_central_nacional": ent_nac,
            "gore_aysen": ent_gore,
            "vialidad_mop_nacional": ent_vialidad,
            "servicios_regionales_aysen": ent_servicios,
        },
        "ley_presupuestos": ley_resumen,
        "comparacion_interanual": comparacion_interanual_meta,
        "fuente_trazabilidad": {
            "institucion": "DIPRES · Ministerio de Hacienda (datos.gob.cl CKAN)",
            "endpoint_ckan": CKAN_BASE,
            "package_name": paquete_ejec.get("name"),
            "package_title": paquete_ejec.get("title"),
            "url_respaldo": url_ejec,
            "resource_id_nacional": res_id_nac,
            "resource_id_programa": res_id_prog,
            "columna_ejecucion": col_ejec_prog or col_ejec_nac,
            "columna_ejecucion_nacional": col_ejec_nac,
            "columna_ejecucion_programa": col_ejec_prog,
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
            "registros_no_clp_excluidos": no_clp_nac + no_clp_gore + no_clp_vial + no_clp_serv,
        },
    }

    _escribir_cache_atomico(ruta_cache, resultado)
    return resultado
