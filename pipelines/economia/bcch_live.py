"""Conector en vivo y cacheable hacia la API REST del Banco Central de Chile (BDE SI3).

Provee consultas autenticadas de solo lectura para:
- Búsqueda dinámica de series por frecuencia (``SearchSeries``) con caché en
  memoria de 15 minutos.
- Descarga de observaciones exactas de una serie (``GetSeries``) preservando
  valores decimales como texto (sin ``float``) y ``statusCode``.
- Extracción en vivo de la estructura productiva real de la Región de Aysén
  (4 series de PIB total + 13 actividades nominales + hasta 3 series trimestrales),
  normalizada con ``Decimal`` y calculada con ``analytics.territorial.pib`` y
  ``analytics.territorial.estructura``, con caché en disco de 24 horas.

Nunca utiliza cifras mockeadas ni expone credenciales en logs, errores, caché o
respuestas.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import sys
import threading
import time
from typing import Any

_RAIZ_REPO = Path(__file__).resolve().parents[2]
if str(_RAIZ_REPO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_REPO))

from analytics.territorial.estructura import (  # noqa: E402
    HHI_VERSION,
    PARTICIPACION_SECTORIAL_VERSION,
    concentracion_hhi,
    participacion_sectorial,
)
from analytics.territorial.pib import (  # noqa: E402
    crecimiento,
    participacion,
)
from pipelines.economia.bde_api import (  # noqa: E402
    ANIO_REFERENCIA_REAL,
    ENDPOINT,
    NOMBRES_TERRITORIOS,
    UNIDAD_NIVEL,
    BdeApiError,
    Credenciales,
    SerieCatalogo,
    _ESTADOS_FALTANTES_BDE,
    _factor_a_millones,
    _normalizar_texto,
    _parsear_fecha_corte,
    _parsear_fecha_observacion,
    cargar_archivo_env,
    contiene_credencial,
    descargar,
    descubrir_series_sectoriales,
    descubrir_series_totales,
    formatear_decimal,
    parsear_catalogo_anual,
    sanear_mensaje,
)

INSTITUCION_BCCH = "Banco Central de Chile (BDE SI3 REST API)"
FRECUENCIAS_VALIDAS = frozenset({"ANNUAL", "QUARTERLY", "MONTHLY", "DAILY"})
_CACHE_CATALOGO_TTL_SEGUNDOS = 15 * 60
_CACHE_ESTRUCTURA_TTL = timedelta(hours=24)
_CACHE_ESTRUCTURA_DEFAULT = _RAIZ_REPO / "data" / "raw" / "bcch-aysen-sectorial-live.json"
_PATRON_AYSEN_TRIMESTRAL = re.compile(r"^F035\.PIB\.FLU\.R\.CLP\.2018\.(.+)\.11\.0\.T$")
_CLASIFICACION_SECTORIAL = "CCNN2018-13-actividades"

_CACHE_LOCK = threading.Lock()
# frecuencia -> (monotonic_ts, extraido_en_iso, payload_dict)
_CACHE_CATALOGO: dict[str, tuple[float, str, dict[str, Any]]] = {}


class FaltaTokenBCChError(BdeApiError):
    """Error seguro cuando no hay token ni credenciales BCCh configuradas."""


def limpiar_cache_memoria() -> None:
    """Limpia el caché en memoria de ``SearchSeries``."""
    with _CACHE_LOCK:
        _CACHE_CATALOGO.clear()


def obtener_credenciales_bcch(env_path: Path | None = None) -> Credenciales:
    """Resuelve credenciales BCCh desde entorno del proceso y luego ``.env``.

    Acepta exclusivamente credenciales privadas del servidor:
    ``BCCH_API_TOKEN`` o el par ``BCCH_API_USER`` + ``BCCH_API_PASS``.
    """
    token_env = os.environ.get("BCCH_API_TOKEN", "").strip()
    if token_env:
        return Credenciales(modo="token", token=token_env)

    usuario_env = os.environ.get("BCCH_API_USER", "").strip()
    clave_env = os.environ.get("BCCH_API_PASS", "").strip()
    if usuario_env and clave_env:
        return Credenciales(modo="user_pass", usuario=usuario_env, clave=clave_env)

    archivo_valores: dict[str, str] = {}
    ruta_env = env_path if env_path is not None else (_RAIZ_REPO / ".env")
    if ruta_env.is_file():
        archivo_valores = cargar_archivo_env(ruta_env)

    token_archivo = archivo_valores.get("BCCH_API_TOKEN", "").strip()
    if token_archivo:
        return Credenciales(modo="token", token=token_archivo)

    usuario = usuario_env or archivo_valores.get("BCCH_API_USER", "").strip()
    clave = clave_env or archivo_valores.get("BCCH_API_PASS", "").strip()
    if usuario and clave:
        return Credenciales(modo="user_pass", usuario=usuario, clave=clave)
    if usuario or clave:
        raise FaltaTokenBCChError(
            "Autenticación incompleta: configure tanto BCCH_API_USER como BCCH_API_PASS."
        )

    raise FaltaTokenBCChError(
        "Falta configurar BCCH_API_TOKEN o BCCH_API_USER + BCCH_API_PASS en el entorno o en .env local del servidor."
    )


def _obtener_catalogo_cached(
    credenciales: Credenciales,
    frequency: str,
    *,
    force_refresh: bool = False,
) -> tuple[dict[str, Any], str, bool]:
    """Consulta ``SearchSeries`` usando caché en memoria con TTL de 15 minutos."""
    ahora_mono = time.monotonic()
    if not force_refresh:
        with _CACHE_LOCK:
            entrada = _CACHE_CATALOGO.get(frequency)
            if entrada is not None:
                ts_guardado, extraido_en, payload_guardado = entrada
                if (ahora_mono - ts_guardado) < _CACHE_CATALOGO_TTL_SEGUNDOS:
                    return payload_guardado, extraido_en, True

    extraido_en = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _raw, payload = descargar(credenciales, "SearchSeries", frequency=frequency)
    if not isinstance(payload, dict) or not isinstance(payload.get("SeriesInfos"), list):
        raise BdeApiError(f"SearchSeries ({frequency}): estructura de catálogo inválida.")

    with _CACHE_LOCK:
        _CACHE_CATALOGO[frequency] = (time.monotonic(), extraido_en, payload)
    return payload, extraido_en, False


def _fecha_actualizacion_catalogo(filas: list[dict[str, Any]]) -> str | None:
    fechas: list[str] = []
    for fila in filas:
        corte = _parsear_fecha_corte(fila.get("updatedAt"))
        if corte is not None:
            fechas.append(corte)
    return max(fechas) if fechas else None


def buscar_series_live(
    frequency: str = "ANNUAL",
    query: str = "",
    limit: int = 50,
    env_path: Path | None = None,
) -> dict[str, Any]:
    """Busca series en vivo en el catálogo BDE (``SearchSeries``) con caché de 15 min."""
    if not isinstance(frequency, str):
        raise BdeApiError("La frecuencia debe ser una cadena de texto.")
    freq = frequency.strip().upper()
    if freq not in FRECUENCIAS_VALIDAS:
        raise BdeApiError(
            f"Frecuencia no soportada: {frequency!r}. Use una de: {', '.join(sorted(FRECUENCIAS_VALIDAS))}."
        )
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
        raise BdeApiError("El parámetro limit debe ser un entero mayor o igual a 0.")

    credenciales = obtener_credenciales_bcch(env_path=env_path)
    payload, extraido_en, desde_cache = _obtener_catalogo_cached(credenciales, freq)
    filas_crudas = payload.get("SeriesInfos")
    if not isinstance(filas_crudas, list):
        raise BdeApiError(f"SearchSeries ({freq}): listado SeriesInfos inválido.")

    tokens_query = _normalizar_texto(query or "").split()
    coincidencias: list[dict[str, Any]] = []
    for fila in filas_crudas:
        if not isinstance(fila, dict):
            continue
        series_id = fila.get("seriesId")
        spanish_title = fila.get("spanishTitle")
        if not isinstance(series_id, str) or not series_id.strip():
            continue
        if not isinstance(spanish_title, str):
            spanish_title = ""
        series_id_limpio = series_id.strip()
        titulo_limpio = spanish_title.strip()

        if tokens_query:
            texto_buscable = f"{_normalizar_texto(series_id_limpio)} {_normalizar_texto(titulo_limpio)}"
            if not all(token in texto_buscable for token in tokens_query):
                continue

        coincidencias.append({
            "seriesId": series_id_limpio,
            "spanishTitle": titulo_limpio,
            "frequencyCode": str(fila.get("frequencyCode") or freq).strip(),
            "firstObservation": (
                fila.get("firstObservation") if isinstance(fila.get("firstObservation"), str) else None
            ),
            "lastObservation": (
                fila.get("lastObservation") if isinstance(fila.get("lastObservation"), str) else None
            ),
            "updatedAt": fila.get("updatedAt") if isinstance(fila.get("updatedAt"), str) else None,
        })

    actualizado_en = _fecha_actualizacion_catalogo(coincidencias) or _fecha_actualizacion_catalogo(
        [f for f in filas_crudas if isinstance(f, dict)]
    )

    return {
        "fuente_trazabilidad": {
            "institucion": INSTITUCION_BCCH,
            "endpoint": ENDPOINT,
            "funcion": "SearchSeries",
            "frecuencia": freq,
            "actualizado_en": actualizado_en,
            "extraido_en": extraido_en,
            "desde_cache": desde_cache,
        },
        "total": len(coincidencias),
        "series": coincidencias[:limit],
    }


def _parsear_valor_decimal_exacto(series_id: str, valor_crudo: Any, estado_bde: str) -> str | None:
    estado_limpio = estado_bde.strip()
    if estado_limpio == "OK":
        if valor_crudo is None:
            raise BdeApiError(f"{series_id}: observación OK sin valor numérico.")
        try:
            valor_dec = Decimal(str(valor_crudo).strip())
        except InvalidOperation:
            raise BdeApiError(f"{series_id}: observación OK con valor no numérico.") from None
        if not valor_dec.is_finite():
            raise BdeApiError(f"{series_id}: observación OK con valor no finito.")
        return formatear_decimal(valor_dec)

    if estado_limpio.upper() in _ESTADOS_FALTANTES_BDE or valor_crudo is None:
        return None

    texto = str(valor_crudo).strip()
    if not texto or texto.lower() == "nan":
        return None
    try:
        valor_dec = Decimal(texto)
    except InvalidOperation:
        return None
    return formatear_decimal(valor_dec) if valor_dec.is_finite() else None


def obtener_serie_live(
    series_id: str,
    firstdate: str = "2013-01-01",
    lastdate: str | None = None,
    env_path: Path | None = None,
) -> dict[str, Any]:
    """Descarga una serie exacta desde BDE (``GetSeries``) sin conversión a ``float``."""
    if not isinstance(series_id, str) or not series_id.strip():
        raise BdeApiError("Debe especificar un series_id válido.")
    codigo = series_id.strip()
    fecha_hasta = lastdate.strip() if isinstance(lastdate, str) and lastdate.strip() else date.today().isoformat()
    fecha_desde = firstdate.strip() if isinstance(firstdate, str) and firstdate.strip() else "2013-01-01"

    try:
        d_desde = date.fromisoformat(fecha_desde)
        d_hasta = date.fromisoformat(fecha_hasta)
    except ValueError:
        raise BdeApiError("Las fechas firstdate y lastdate deben estar en formato ISO YYYY-MM-DD.") from None
    if d_desde > d_hasta:
        raise BdeApiError("firstdate no puede ser posterior a lastdate.")

    credenciales = obtener_credenciales_bcch(env_path=env_path)
    extraido_en = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _raw, payload = descargar(
        credenciales,
        "GetSeries",
        timeseries=codigo,
        firstdate=fecha_desde,
        lastdate=fecha_hasta,
    )

    bloque = payload.get("Series")
    if not isinstance(bloque, dict) or str(bloque.get("seriesId", "")).strip() != codigo:
        raise BdeApiError(f"{codigo}: identidad de serie incorrecta en GetSeries.")
    filas_obs = bloque.get("Obs")
    if not isinstance(filas_obs, list):
        raise BdeApiError(f"{codigo}: observaciones inválidas en GetSeries.")

    descrip_esp = bloque.get("descripEsp")
    descrip_esp_str = descrip_esp.strip() if isinstance(descrip_esp, str) else ""

    observaciones: list[dict[str, Any]] = []
    for fila in filas_obs:
        if not isinstance(fila, dict):
            raise BdeApiError(f"{codigo}: observación mal formada.")
        try:
            fecha_obs = _parsear_fecha_observacion(fila["indexDateString"])
            estado_raw = fila["statusCode"]
            valor_raw = fila.get("value")
        except (KeyError, TypeError, ValueError):
            raise BdeApiError(f"{codigo}: observación mal formada.") from None
        if not isinstance(estado_raw, str) or not estado_raw.strip():
            raise BdeApiError(f"{codigo}: statusCode inválido.")

        estado_limpio = estado_raw.strip()
        valor_str = _parsear_valor_decimal_exacto(codigo, valor_raw, estado_limpio)
        observaciones.append({
            "fecha": fecha_obs.isoformat(),
            "anio": fecha_obs.year,
            "valor": valor_str,
            "estado": estado_limpio,
        })

    observaciones.sort(key=lambda item: item["fecha"])
    actualizado_en = _parsear_fecha_corte(bloque.get("updatedAt"))
    if actualizado_en is None and observaciones:
        actualizado_en = observaciones[-1]["fecha"]

    return {
        "fuente_trazabilidad": {
            "institucion": INSTITUCION_BCCH,
            "endpoint": ENDPOINT,
            "funcion": "GetSeries",
            "series_consultadas": [codigo],
            "actualizado_en": actualizado_en,
            "extraido_en": extraido_en,
        },
        "serie": {
            "seriesId": codigo,
            "descripEsp": descrip_esp_str,
            "observaciones": observaciones,
        },
    }


def _extraer_nombre_actividad(titulo_es: str) -> str:
    """Extrae el nombre legible de la actividad económica desde el título BDE."""
    sin_unidad = re.sub(r"\([^()]*\)\s*$", "", titulo_es).strip()
    partes = [parte.strip() for parte in sin_unidad.split(",") if parte.strip()]
    utiles: list[str] = []
    for parte in partes:
        limpia = re.sub(
            r"^(?:producto\s+interno\s+bruto|pib)\s*[:,.\-]?\s*",
            "",
            parte,
            flags=re.IGNORECASE,
        ).strip()
        if not limpia:
            continue
        norm = _normalizar_texto(limpia)
        if (
            "aysen" in norm
            or norm.startswith("region de")
            or norm.startswith("region del")
            or "precios corrientes" in norm
            or "volumen a precios" in norm
            or "encadenad" in norm
            or "referencia 2018" in norm
            or "base 2018" in norm
            or "miles de millones" in norm
            or "millones de pesos" in norm
        ):
            continue
        utiles.append(limpia)
    return ", ".join(utiles) if utiles else titulo_es.strip()


def _es_administracion_publica(codigo_actividad: str | None, titulo_es: str) -> bool:
    if codigo_actividad == "12":
        return True
    return "administracion publica" in _normalizar_texto(titulo_es)


def _es_pesca(codigo_actividad: str | None, titulo_es: str) -> bool:
    if codigo_actividad == "02.04.Z":
        return True
    return "pesca" in _normalizar_texto(titulo_es)


def _parsear_serie_anual_a_millones(
    payload: dict[str, Any],
    serie: SerieCatalogo,
) -> tuple[dict[int, dict[str, Any]], Decimal, str, str]:
    """Parsea ``GetSeries`` anual y normaliza exactamente a ``millones CLP`` con ``Decimal``."""
    bloque = payload.get("Series")
    if not isinstance(bloque, dict) or str(bloque.get("seriesId", "")).strip() != serie.codigo:
        raise BdeApiError(f"{serie.codigo}: identidad de serie incorrecta en GetSeries.")
    filas = bloque.get("Obs")
    if not isinstance(filas, list) or not filas:
        raise BdeApiError(f"{serie.codigo}: observaciones anuales vacías o inválidas.")

    descrip_es = bloque.get("descripEsp") if isinstance(bloque.get("descripEsp"), str) else ""
    factor, unidad_origen = _factor_a_millones(
        serie.titulo_es,
        descrip_es or None,
        serie.titulo_en,
        codigo=serie.codigo,
    )

    por_anio: dict[int, dict[str, Any]] = {}
    for fila in filas:
        if not isinstance(fila, dict):
            raise BdeApiError(f"{serie.codigo}: observación mal formada.")
        try:
            fecha_obs = _parsear_fecha_observacion(fila["indexDateString"])
            estado_raw = fila["statusCode"]
            valor_raw = fila.get("value")
        except (KeyError, TypeError, ValueError):
            raise BdeApiError(f"{serie.codigo}: observación mal formada.") from None
        if not isinstance(estado_raw, str) or not estado_raw.strip():
            raise BdeApiError(f"{serie.codigo}: statusCode inválido.")

        estado_limpio = estado_raw.strip()
        if estado_limpio == "OK":
            if valor_raw is None:
                raise BdeApiError(f"{serie.codigo}: observación OK sin valor numérico.")
            try:
                valor_dec = Decimal(str(valor_raw).strip())
            except InvalidOperation:
                raise BdeApiError(f"{serie.codigo}: observación OK con valor no numérico.") from None
            if not valor_dec.is_finite():
                raise BdeApiError(f"{serie.codigo}: observación OK con valor no finito.")
            valor_millones_dec = valor_dec * factor
            por_anio[fecha_obs.year] = {
                "fecha": fecha_obs.isoformat(),
                "valor_origen": formatear_decimal(valor_dec),
                "valor_decimal": valor_millones_dec,
                "valor_millones": formatear_decimal(valor_millones_dec),
                "estado": "informado",
                "estado_bde": estado_limpio,
                "clase": "oficial",
            }
        elif estado_limpio.upper() in _ESTADOS_FALTANTES_BDE:
            por_anio[fecha_obs.year] = {
                "fecha": fecha_obs.isoformat(),
                "valor_origen": None,
                "valor_decimal": None,
                "valor_millones": None,
                "estado": "faltante",
                "estado_bde": estado_limpio,
                "clase": "no_disponible",
            }
        else:
            raise BdeApiError(f"{serie.codigo}: statusCode BDE no reconocido ({estado_limpio}).")

    return por_anio, factor, unidad_origen, descrip_es.strip()


def _construir_obs_pib(
    publicacion_id: str,
    territorio: str,
    anio: int,
    valoracion: str,
    dato: dict[str, Any] | None,
) -> dict[str, Any]:
    estado = dato["estado"] if dato is not None else "faltante"
    clase = dato["clase"] if dato is not None else "no_disponible"
    valor = dato["valor_millones"] if dato is not None else None
    return {
        "id": f"{publicacion_id}.{territorio}.{anio}.nivel.{valoracion}",
        "publicacion": publicacion_id,
        "territorio": territorio,
        "anio": anio,
        "metrica": "nivel",
        "valoracion": valoracion,
        "valor": valor,
        "unidad": UNIDAD_NIVEL,
        "anio_referencia": ANIO_REFERENCIA_REAL if valoracion == "real" else None,
        "estado": estado,
        "clase": clase,
    }


def _construir_obs_estructura(
    publicacion_id: str,
    anio: int,
    actividad: str,
    valor: str | None,
    estado: str,
    clase: str,
    perimetro: str,
) -> dict[str, Any]:
    return {
        "id": f"{publicacion_id}.11.{anio}.va.{perimetro}.{actividad}",
        "publicacion": publicacion_id,
        "territorio": "11",
        "anio": anio,
        "metrica": "valor_agregado",
        "valoracion": "nominal",
        "valor": valor,
        "unidad": UNIDAD_NIVEL,
        "anio_referencia": None,
        "actividad": actividad,
        "clasificacion": _CLASIFICACION_SECTORIAL,
        "perimetro": perimetro,
        "estado": estado,
        "clase": clase,
    }


def _prioridad_serie_trimestral(segmento: str, series_id: str) -> tuple[int, str]:
    tokens = {tok.upper() for tok in segmento.split(".") if tok}
    if tokens == {"Z"}:
        return (0, series_id)
    if "PB" in tokens:
        return (1, series_id)
    if "SERV" in tokens:
        return (2, series_id)
    if "COM" in tokens:
        return (3, series_id)
    return (4, series_id)


def _categoria_trimestral(segmento: str) -> str:
    tokens = [tok.upper() for tok in segmento.split(".") if tok]
    if set(tokens) == {"Z"}:
        return "TOTAL"
    for clave in ("PB", "SERV", "COM"):
        if clave in tokens:
            return clave
    return segmento


def _seleccionar_series_trimestrales_aysen(
    payload_trimestral: dict[str, Any],
    max_series: int = 3,
) -> list[tuple[dict[str, Any], str]]:
    filas = payload_trimestral.get("SeriesInfos")
    if not isinstance(filas, list):
        return []
    candidatas: list[tuple[tuple[int, str], dict[str, Any], str]] = []
    vistos: set[str] = set()
    for fila in filas:
        if not isinstance(fila, dict):
            continue
        codigo = fila.get("seriesId")
        if not isinstance(codigo, str) or not codigo.strip():
            continue
        codigo_limpio = codigo.strip()
        if codigo_limpio in vistos:
            continue
        coincidencia = _PATRON_AYSEN_TRIMESTRAL.fullmatch(codigo_limpio)
        if coincidencia is None:
            continue
        vistos.add(codigo_limpio)
        segmento = coincidencia.group(1)
        candidatas.append((_prioridad_serie_trimestral(segmento, codigo_limpio), fila, segmento))

    candidatas.sort(key=lambda item: item[0])
    return [(fila, segmento) for _prio, fila, segmento in candidatas[:max_series]]


def _parsear_serie_trimestral(
    payload: dict[str, Any],
    fila_catalogo: dict[str, Any],
    segmento: str,
) -> dict[str, Any]:
    codigo = str(fila_catalogo["seriesId"]).strip()
    titulo_es = str(fila_catalogo.get("spanishTitle") or "").strip()
    titulo_en = fila_catalogo.get("englishTitle") if isinstance(fila_catalogo.get("englishTitle"), str) else None
    bloque = payload.get("Series")
    if not isinstance(bloque, dict) or str(bloque.get("seriesId", "")).strip() != codigo:
        raise BdeApiError(f"{codigo}: identidad de serie trimestral incorrecta en GetSeries.")
    filas_obs = bloque.get("Obs")
    if not isinstance(filas_obs, list):
        raise BdeApiError(f"{codigo}: observaciones trimestrales inválidas en GetSeries.")

    descrip_esp = bloque.get("descripEsp") if isinstance(bloque.get("descripEsp"), str) else ""
    try:
        factor, unidad_origen = _factor_a_millones(titulo_es, descrip_esp or None, titulo_en, codigo=codigo)
    except BdeApiError:
        factor, unidad_origen = None, None

    observaciones: list[dict[str, Any]] = []
    for fila in filas_obs:
        if not isinstance(fila, dict):
            raise BdeApiError(f"{codigo}: observación trimestral mal formada.")
        try:
            fecha_obs = _parsear_fecha_observacion(fila["indexDateString"])
            estado_raw = fila["statusCode"]
            valor_raw = fila.get("value")
        except (KeyError, TypeError, ValueError):
            raise BdeApiError(f"{codigo}: observación trimestral mal formada.") from None
        if not isinstance(estado_raw, str) or not estado_raw.strip():
            raise BdeApiError(f"{codigo}: statusCode trimestral inválido.")

        estado_limpio = estado_raw.strip()
        valor_str = _parsear_valor_decimal_exacto(codigo, valor_raw, estado_limpio)
        valor_millones = (
            formatear_decimal(Decimal(valor_str) * factor)
            if valor_str is not None and factor is not None
            else None
        )
        trimestre = (fecha_obs.month - 1) // 3 + 1
        observaciones.append({
            "fecha": fecha_obs.isoformat(),
            "anio": fecha_obs.year,
            "trimestre": trimestre,
            "periodo": f"{fecha_obs.year}-T{trimestre}",
            "valor": valor_str,
            "valor_millones": valor_millones,
            "estado": estado_limpio,
        })

    observaciones.sort(key=lambda item: item["fecha"])
    return {
        "seriesId": codigo,
        "spanishTitle": titulo_es,
        "descripEsp": descrip_esp.strip(),
        "categoria": _categoria_trimestral(segmento),
        "unidad_origen": unidad_origen,
        "updatedAt": fila_catalogo.get("updatedAt") if isinstance(fila_catalogo.get("updatedAt"), str) else None,
        "observaciones": observaciones,
    }


def _leer_cache_estructura_archivo(
    ruta_cache: Path,
    anio_desde: int,
    anio_hasta: int,
    *,
    exigir_vigencia: bool = True,
) -> dict[str, Any] | None:
    if not ruta_cache.is_file():
        return None
    try:
        datos = json.loads(ruta_cache.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return None
    if not isinstance(datos, dict):
        return None

    rango = datos.get("rango_solicitado")
    traza = datos.get("fuente_trazabilidad")
    if (
        not isinstance(rango, dict)
        or not isinstance(traza, dict)
        or not isinstance(datos.get("resumen_pib"), dict)
        or not isinstance(datos.get("actividades"), list)
        or not isinstance(datos.get("ultimo_anio"), int)
    ):
        return None
    if rango.get("anio_desde") != anio_desde or rango.get("anio_hasta") != anio_hasta:
        return None

    if exigir_vigencia:
        ahora = datetime.now(timezone.utc)
        extraido_str = traza.get("extraido_en")
        dt_cache: datetime | None = None
        if isinstance(extraido_str, str) and extraido_str.strip():
            try:
                dt_cache = datetime.fromisoformat(extraido_str.replace("Z", "+00:00"))
                if dt_cache.tzinfo is None:
                    dt_cache = dt_cache.replace(tzinfo=timezone.utc)
            except ValueError:
                dt_cache = None
        if dt_cache is None:
            try:
                dt_cache = datetime.fromtimestamp(ruta_cache.stat().st_mtime, tz=timezone.utc)
            except OSError:
                return None

        if (ahora - dt_cache) >= _CACHE_ESTRUCTURA_TTL or (ahora - dt_cache) < timedelta(seconds=-60):
            return None

    resultado = deepcopy(datos)
    resultado["fuente_trazabilidad"]["desde_cache"] = True
    return resultado


def _leer_cache_estructura_vigente(
    ruta_cache: Path,
    anio_desde: int,
    anio_hasta: int,
) -> dict[str, Any] | None:
    return _leer_cache_estructura_archivo(
        ruta_cache,
        anio_desde,
        anio_hasta,
        exigir_vigencia=True,
    )


def _guardar_cache_estructura(
    ruta_cache: Path,
    payload: dict[str, Any],
    credenciales: Credenciales,
) -> None:
    raw = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if contiene_credencial(raw, credenciales):
        raise BdeApiError("Se bloqueó el caché: se detectó una credencial en el contenido.")
    try:
        ruta_cache.parent.mkdir(parents=True, exist_ok=True)
        ruta_cache.write_bytes(raw)
    except OSError:
        # En entornos donde data/raw no es escribible, continúa sin fallar.
        return


def obtener_estructura_aysen_live(
    anio_desde: int = 2013,
    anio_hasta: int | None = None,
    refresh: bool = False,
    env_path: Path | None = None,
    cache_path: Path | None = None,
) -> dict[str, Any]:
    """Extrae en vivo (con caché 24h) la estructura productiva real de la Región de Aysén."""
    anio_hasta_efectivo = anio_hasta if anio_hasta is not None else date.today().year
    if isinstance(anio_desde, bool) or not isinstance(anio_desde, int):
        raise BdeApiError("anio_desde debe ser un año entero.")
    if isinstance(anio_hasta_efectivo, bool) or not isinstance(anio_hasta_efectivo, int):
        raise BdeApiError("anio_hasta debe ser un año entero.")
    if anio_desde > anio_hasta_efectivo:
        raise BdeApiError("anio_desde no puede ser posterior a anio_hasta.")

    ruta_cache = cache_path if cache_path is not None else _CACHE_ESTRUCTURA_DEFAULT
    if not refresh:
        desde_disco = _leer_cache_estructura_vigente(ruta_cache, anio_desde, anio_hasta_efectivo)
        if desde_disco is not None:
            return desde_disco

    credenciales: Credenciales | None = None
    try:
        credenciales = obtener_credenciales_bcch(env_path=env_path)
        resultado = _descargar_estructura_aysen_live(
            credenciales=credenciales,
            anio_desde=anio_desde,
            anio_hasta_efectivo=anio_hasta_efectivo,
            refresh=refresh,
        )
    except (BdeApiError, OSError) as error:
        respaldo = _leer_cache_estructura_archivo(
            ruta_cache,
            anio_desde,
            anio_hasta_efectivo,
            exigir_vigencia=False,
        )
        if respaldo is not None:
            detalle = sanear_mensaje(str(error), credenciales).strip() or "falla en consulta viva BCCh"
            respaldo["fuente_trazabilidad"]["desde_cache"] = True
            respaldo["fuente_trazabilidad"]["estado_actualizacion"] = "respaldo_ultimo_corte_aprobado"
            respaldo["fuente_trazabilidad"]["advertencia_actualizacion"] = (
                f"No se pudo refrescar desde BCCh ({detalle}); se sirve el último corte aprobado en caché."
            )
            return respaldo
        raise

    _guardar_cache_estructura(ruta_cache, resultado, credenciales)
    return resultado


def _descargar_estructura_aysen_live(
    *,
    credenciales: Credenciales,
    anio_desde: int,
    anio_hasta_efectivo: int,
    refresh: bool,
) -> dict[str, Any]:
    extraido_en = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # 1) Catálogo anual -> 4 series totales + 13 series sectoriales nominales de Aysén
    payload_anual, _extraido_cat, _cat_cache = _obtener_catalogo_cached(
        credenciales,
        "ANNUAL",
        force_refresh=refresh,
    )
    catalogo_anual = parsear_catalogo_anual(payload_anual)
    series_totales_mapa = descubrir_series_totales(catalogo_anual)

    claves_totales = (
        ("CL", "real"),
        ("CL", "nominal"),
        ("11", "real"),
        ("11", "nominal"),
    )
    series_totales_4: dict[tuple[str, str], SerieCatalogo] = {
        clave: series_totales_mapa[clave] for clave in claves_totales
    }

    todas_sectoriales = descubrir_series_sectoriales(catalogo_anual)
    series_sectoriales_aysen = [
        serie
        for serie in todas_sectoriales
        if serie.territorio == "11" and serie.valoracion == "nominal"
    ]
    if not series_sectoriales_aysen:
        raise BdeApiError(
            "SearchSeries: no se encontraron series sectoriales nominales para Aysén (región 11)."
        )

    firstdate_anual = f"{anio_desde}-01-01"
    lastdate_anual = f"{anio_hasta_efectivo}-12-31"

    datos_totales: dict[tuple[str, str], dict[int, dict[str, Any]]] = {}
    series_anuales_consultadas: list[str] = []
    fechas_actualizacion: list[str] = []

    for clave in claves_totales:
        serie = series_totales_4[clave]
        _raw, payload_serie = descargar(
            credenciales,
            "GetSeries",
            timeseries=serie.codigo,
            firstdate=firstdate_anual,
            lastdate=lastdate_anual,
        )
        por_anio, _factor, _unidad, _desc = _parsear_serie_anual_a_millones(payload_serie, serie)
        datos_totales[clave] = por_anio
        series_anuales_consultadas.append(serie.codigo)
        corte = _parsear_fecha_corte(serie.actualizada_en)
        if corte is not None:
            fechas_actualizacion.append(corte)

    datos_actividades: list[tuple[SerieCatalogo, dict[int, dict[str, Any]], str]] = []
    for serie in series_sectoriales_aysen:
        _raw, payload_serie = descargar(
            credenciales,
            "GetSeries",
            timeseries=serie.codigo,
            firstdate=firstdate_anual,
            lastdate=lastdate_anual,
        )
        por_anio, _factor, unidad_origen, _desc = _parsear_serie_anual_a_millones(payload_serie, serie)
        datos_actividades.append((serie, por_anio, unidad_origen))
        series_anuales_consultadas.append(serie.codigo)
        corte = _parsear_fecha_corte(serie.actualizada_en)
        if corte is not None:
            fechas_actualizacion.append(corte)

    # 2) Determinar ultimo_anio disponible con cobertura consistente
    anios_aysen_nom = {
        anio for anio, d in datos_totales[("11", "nominal")].items() if d["estado"] == "informado"
    }
    anios_cl_nom = {
        anio for anio, d in datos_totales[("CL", "nominal")].items() if d["estado"] == "informado"
    }
    anios_totales_nom = anios_aysen_nom & anios_cl_nom
    if not anios_totales_nom:
        raise BdeApiError(
            "No existen años comunes con datos nominales informados para Aysén y Chile."
        )

    anios_con_todas_actividades = set(anios_totales_nom)
    for _serie, por_anio, _unidad in datos_actividades:
        anios_con_todas_actividades &= {
            anio for anio, d in por_anio.items() if d["estado"] == "informado"
        }

    if anios_con_todas_actividades:
        ultimo_anio = max(anios_con_todas_actividades)
    else:
        anios_con_alguna_actividad = {
            anio
            for anio in anios_totales_nom
            if any(
                por_anio.get(anio, {}).get("estado") == "informado"
                for _s, por_anio, _u in datos_actividades
            )
        }
        if not anios_con_alguna_actividad:
            raise BdeApiError(
                "No existen años comunes con datos sectoriales nominales informados para Aysén."
            )
        ultimo_anio = max(anios_con_alguna_actividad)

    publicacion_id = f"bcch-aysen-live-{extraido_en[:10]}"

    # 3) Indicadores de PIB (analytics.territorial.pib)
    anios_rango = sorted(
        {
            anio
            for mapa in datos_totales.values()
            for anio in mapa
            if anio_desde <= anio <= anio_hasta_efectivo
        }
    )

    obs_totales: dict[tuple[str, str, int], dict[str, Any]] = {}
    for territorio, valoracion in claves_totales:
        mapa = datos_totales[(territorio, valoracion)]
        for anio in anios_rango:
            obs_totales[(territorio, valoracion, anio)] = _construir_obs_pib(
                publicacion_id, territorio, anio, valoracion, mapa.get(anio)
            )

    res_part_nacional = participacion(
        obs_totales.get(("11", "nominal", ultimo_anio)),
        obs_totales.get(("CL", "nominal", ultimo_anio)),
    )
    res_crec_aysen = crecimiento(
        obs_totales.get(("11", "real", ultimo_anio)),
        obs_totales.get(("11", "real", ultimo_anio - 1)),
    )
    res_crec_chile = crecimiento(
        obs_totales.get(("CL", "real", ultimo_anio)),
        obs_totales.get(("CL", "real", ultimo_anio - 1)),
    )

    serie_anual_pib: list[dict[str, Any]] = []
    for anio in anios_rango:
        p_nac = participacion(
            obs_totales.get(("11", "nominal", anio)),
            obs_totales.get(("CL", "nominal", anio)),
        )
        c_ay = crecimiento(
            obs_totales.get(("11", "real", anio)),
            obs_totales.get(("11", "real", anio - 1)),
        )
        c_cl = crecimiento(
            obs_totales.get(("CL", "real", anio)),
            obs_totales.get(("CL", "real", anio - 1)),
        )
        serie_anual_pib.append({
            "anio": anio,
            "aysen_nominal_millones": obs_totales[("11", "nominal", anio)]["valor"],
            "aysen_real_millones": obs_totales[("11", "real", anio)]["valor"],
            "chile_nominal_millones": obs_totales[("CL", "nominal", anio)]["valor"],
            "chile_real_millones": obs_totales[("CL", "real", anio)]["valor"],
            "participacion_aysen_en_chile_pct": p_nac.valor,
            "crecimiento_real_aysen_pct": c_ay.valor,
            "crecimiento_real_chile_pct": c_cl.valor,
        })

    # 4) Estructura productiva de Aysén (analytics.territorial.estructura)
    dato_aysen_nom = datos_totales[("11", "nominal")][ultimo_anio]
    aysen_nom_decimal: Decimal = dato_aysen_nom["valor_decimal"]
    dato_aysen_real = datos_totales[("11", "real")].get(ultimo_anio)
    dato_cl_nom = datos_totales[("CL", "nominal")][ultimo_anio]
    dato_cl_real = datos_totales[("CL", "real")].get(ultimo_anio)

    suma_actividades_decimal = Decimal("0")
    for _serie, por_anio, _unidad in datos_actividades:
        dato_act = por_anio.get(ultimo_anio)
        if dato_act is not None and dato_act["valor_decimal"] is not None:
            suma_actividades_decimal += dato_act["valor_decimal"]

    diferencia_impuestos_decimal = aysen_nom_decimal - suma_actividades_decimal

    obs_total_vab = _construir_obs_estructura(
        publicacion_id,
        ultimo_anio,
        "total",
        formatear_decimal(suma_actividades_decimal),
        "informado",
        "oficial",
        perimetro="vab_actividades_aysen",
    )
    obs_total_pib = _construir_obs_estructura(
        publicacion_id,
        ultimo_anio,
        "total",
        dato_aysen_nom["valor_millones"],
        dato_aysen_nom["estado"],
        dato_aysen_nom["clase"],
        perimetro="pib_regional_aysen",
    )

    obs_actividades_vab: list[dict[str, Any]] = []
    actividades_lista: list[dict[str, Any]] = []
    sector_admin_pub: dict[str, Any] | None = None
    sector_pesca: dict[str, Any] | None = None

    for serie, por_anio, unidad_origen in datos_actividades:
        codigo_act = serie.actividad_codigo or serie.codigo
        dato_act = por_anio.get(ultimo_anio)
        valor_act_str = dato_act["valor_millones"] if dato_act is not None else None
        estado_act = dato_act["estado"] if dato_act is not None else "faltante"
        clase_act = dato_act["clase"] if dato_act is not None else "no_disponible"

        obs_act_vab = _construir_obs_estructura(
            publicacion_id,
            ultimo_anio,
            codigo_act,
            valor_act_str,
            estado_act,
            clase_act,
            perimetro="vab_actividades_aysen",
        )
        obs_act_pib = _construir_obs_estructura(
            publicacion_id,
            ultimo_anio,
            codigo_act,
            valor_act_str,
            estado_act,
            clase_act,
            perimetro="pib_regional_aysen",
        )
        obs_actividades_vab.append(obs_act_vab)

        res_part_vab = participacion_sectorial(obs_act_vab, obs_total_vab)
        res_part_pib = participacion_sectorial(obs_act_pib, obs_total_pib)

        es_admin_pub = _es_administracion_publica(serie.actividad_codigo, serie.titulo_es)
        es_pesca_flag = _es_pesca(serie.actividad_codigo, serie.titulo_es)
        nombre_actividad = _extraer_nombre_actividad(serie.titulo_es)

        historico_act = [
            {
                "anio": anio,
                "valor_millones": por_anio[anio]["valor_millones"],
                "estado": por_anio[anio]["estado"],
            }
            for anio in sorted(por_anio)
            if anio_desde <= anio <= anio_hasta_efectivo
        ]

        registro_act = {
            "codigo_actividad": codigo_act,
            "serie_bde": serie.codigo,
            "nombre": nombre_actividad,
            "titulo_es": serie.titulo_es,
            "valor_millones": valor_act_str,
            "valor_origen": dato_act["valor_origen"] if dato_act is not None else None,
            "unidad": UNIDAD_NIVEL,
            "unidad_origen": unidad_origen,
            "participacion_actividades_pct": res_part_vab.valor,
            "participacion_pib_pct": res_part_pib.valor,
            "estado": estado_act,
            "es_administracion_publica": es_admin_pub,
            "es_pesca": es_pesca_flag,
            "serie_anual": historico_act,
        }
        actividades_lista.append(registro_act)

        resumen_clave = {
            "codigo_actividad": codigo_act,
            "serie_bde": serie.codigo,
            "nombre": nombre_actividad,
            "titulo_es": serie.titulo_es,
            "valor_millones": valor_act_str,
            "participacion_actividades_pct": res_part_vab.valor,
            "participacion_pib_pct": res_part_pib.valor,
            "estado": estado_act,
        }
        if es_admin_pub and sector_admin_pub is None:
            sector_admin_pub = resumen_clave
        if es_pesca_flag and sector_pesca is None:
            sector_pesca = resumen_clave

    res_hhi = concentracion_hhi(obs_actividades_vab)

    # Orden descendente numérico por valor_millones (faltantes al final)
    actividades_lista.sort(
        key=lambda item: (
            item["valor_millones"] is None,
            -(Decimal(item["valor_millones"]) if item["valor_millones"] is not None else Decimal("0")),
            item["codigo_actividad"],
        )
    )

    # 5) Catálogo trimestral -> hasta 3 series clave de Aysén de los últimos 3 años
    trim_anio_fin = anio_hasta_efectivo
    trim_anio_inicio = max(anio_desde, trim_anio_fin - 2)
    trim_desde = f"{trim_anio_inicio}-01-01"
    trim_hasta = f"{trim_anio_fin}-12-31"

    payload_trimestral, _extraido_trim, _trim_cache = _obtener_catalogo_cached(
        credenciales,
        "QUARTERLY",
        force_refresh=refresh,
    )
    seleccion_trimestral = _seleccionar_series_trimestrales_aysen(payload_trimestral, max_series=3)

    series_trimestrales: list[dict[str, Any]] = []
    series_trimestrales_consultadas: list[str] = []
    for fila_cat, segmento in seleccion_trimestral:
        codigo_trim = str(fila_cat["seriesId"]).strip()
        _raw_t, payload_t = descargar(
            credenciales,
            "GetSeries",
            timeseries=codigo_trim,
            firstdate=trim_desde,
            lastdate=trim_hasta,
        )
        series_trimestrales.append(_parsear_serie_trimestral(payload_t, fila_cat, segmento))
        series_trimestrales_consultadas.append(codigo_trim)
        corte_t = _parsear_fecha_corte(fila_cat.get("updatedAt"))
        if corte_t is not None:
            fechas_actualizacion.append(corte_t)

    actualizado_en = max(fechas_actualizacion) if fechas_actualizacion else None
    todas_consultadas = series_anuales_consultadas + series_trimestrales_consultadas

    resultado: dict[str, Any] = {
        "territorio": {
            "codigo": "11",
            "nombre": NOMBRES_TERRITORIOS["11"],
            "referencia_nacional": "CL",
        },
        "ultimo_anio": ultimo_anio,
        "rango_solicitado": {
            "anio_desde": anio_desde,
            "anio_hasta": anio_hasta_efectivo,
        },
        "resumen_pib": {
            "anio": ultimo_anio,
            "unidad": UNIDAD_NIVEL,
            "anio_referencia_real": ANIO_REFERENCIA_REAL,
            "aysen_nominal_millones": dato_aysen_nom["valor_millones"],
            "aysen_real_millones": dato_aysen_real["valor_millones"] if dato_aysen_real else None,
            "chile_nominal_millones": dato_cl_nom["valor_millones"],
            "chile_real_millones": dato_cl_real["valor_millones"] if dato_cl_real else None,
            "participacion_aysen_en_chile_pct": res_part_nacional.valor,
            "crecimiento_real_aysen_pct": res_crec_aysen.valor,
            "crecimiento_real_chile_pct": res_crec_chile.valor,
            "suma_actividades_nominal_millones": formatear_decimal(suma_actividades_decimal),
            "diferencia_impuestos_productos_millones": formatear_decimal(diferencia_impuestos_decimal),
            "diferencia_impuestos_productos_nota": (
                "Diferencia contable entre el PIB regional a precios de mercado y la suma del "
                "Valor Agregado Bruto (VAB) de las actividades económicas, explicada por impuestos "
                "sobre los productos (IVA y derechos de importación) netos de subvenciones en "
                "Cuentas Nacionales (CCNN) del Banco Central de Chile."
            ),
            "concentracion_hhi": {
                "valor": res_hhi.valor,
                "escala": "0-10000",
                "formula_version": res_hhi.formula_version,
                "estado": res_hhi.estado,
                "motivo": res_hhi.motivo,
            },
            "sectores_clave": {
                "administracion_publica": sector_admin_pub,
                "pesca": sector_pesca,
            },
            "formulas": {
                "participacion_nacional": res_part_nacional.formula_version,
                "crecimiento_real_aysen": res_crec_aysen.formula_version,
                "crecimiento_real_chile": res_crec_chile.formula_version,
                "participacion_sectorial": PARTICIPACION_SECTORIAL_VERSION,
                "concentracion_hhi": HHI_VERSION,
            },
            "serie_anual": serie_anual_pib,
        },
        "actividades": actividades_lista,
        "trimestral": {
            "disponible": bool(series_trimestrales),
            "rango": {
                "desde": trim_desde,
                "hasta": trim_hasta,
            },
            "series": series_trimestrales,
        },
        "fuente_trazabilidad": {
            "institucion": INSTITUCION_BCCH,
            "endpoint": ENDPOINT,
            "funciones": ["SearchSeries", "GetSeries"],
            "series_consultadas": todas_consultadas,
            "series_anuales_consultadas": series_anuales_consultadas,
            "series_trimestrales_consultadas": series_trimestrales_consultadas,
            "actualizado_en": actualizado_en,
            "extraido_en": extraido_en,
            "desde_cache": False,
        },
    }

    return resultado
