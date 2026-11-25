"""Rutas de conectores en vivo (BCCh, DIPRES) e importación local SINIM."""

from __future__ import annotations

from http.client import HTTPException as HTTPClientError
import importlib
import os
from pathlib import Path
import re
import sys
from typing import Annotated, Literal
from urllib.error import URLError
from urllib.parse import quote, quote_plus

from fastapi import APIRouter, Path as PathParameter, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

PREFIJO = "/api/v1"
RAIZ_REPO = Path(__file__).resolve().parents[2]
RUTA_SINIM_DEFECTO = RAIZ_REPO / "data" / "published" / "sinim-aysen-importado.json"
MAX_SINIM_BYTES = 5 * 1024 * 1024  # 5 MB

SERIE_ID = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
FECHA_ISO = r"^\d{4}-\d{2}-\d{2}$"
_VARS_SENSIBLES = (
    "BCCH_API_TOKEN",
    "VITE_BCENTRAL_TOKEN",
    "NEXT_PUBLIC_BCENTRAL_TOKEN",
    "BCCH_API_USER",
    "BCCH_API_PASS",
)
_PATRON_PARAM_SENSIBLE = re.compile(
    r"(token|user|pass|password|apikey|api_key)=[^&\s\"']+",
    re.IGNORECASE,
)

FrecuenciaBCCh = Literal["ANNUAL", "QUARTERLY", "MONTHLY", "DAILY"]

router = APIRouter(prefix=PREFIJO)


class SolicitudImportacionSinim(BaseModel):
    nombre_archivo: str = Field(..., min_length=1, max_length=255)
    contenido: str


def _asegurar_raiz_en_path() -> None:
    raiz = str(RAIZ_REPO)
    if raiz not in sys.path:
        sys.path.insert(0, raiz)


def _cargar_bcch_live():
    _asegurar_raiz_en_path()
    return importlib.import_module("pipelines.economia.bcch_live")


def _cargar_dipres_ckan():
    _asegurar_raiz_en_path()
    return importlib.import_module("pipelines.fiscal.dipres_ckan")


def _cargar_sinim_importer():
    _asegurar_raiz_en_path()
    return importlib.import_module("pipelines.fiscal.sinim_importer")


def _ruta_sinim() -> Path:
    personalizada = (os.getenv("CT_SINIM_PATH") or "").strip()
    if personalizada:
        return Path(personalizada)
    return RUTA_SINIM_DEFECTO


def _sinim_no_cargado() -> dict:
    return {
        "cargado": False,
        "comunas_esperadas": 10,
        "resumen": None,
        "comunas": [],
        "fuente_trazabilidad": {
            "institucion": "SINIM · SUBDERE (importación oficial local)",
            "estado": "pendiente_importacion",
            "nota": (
                "SUBDERE/SINIM no dispone de API REST pública; importe un archivo "
                "CSV o JSON oficial de las 10 comunas de Aysén."
            ),
        },
    }


def _sanear_mensaje(exc: Exception, respaldo: str) -> str:
    texto = str(exc).strip()
    if not texto:
        return respaldo
    limpio = _PATRON_PARAM_SENSIBLE.sub(r"\1=[REDACTED]", texto)
    for clave in _VARS_SENSIBLES:
        secreto = (os.getenv(clave) or "").strip()
        if not secreto:
            continue
        for forma in {secreto, quote(secreto, safe=""), quote_plus(secreto)}:
            if forma:
                limpio = limpio.replace(forma, "[REDACTED]")
    return limpio or respaldo


def _error_json(status_code: int, codigo: str, mensaje: str, **extra) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"codigo": codigo, "mensaje": mensaje, **extra},
    )


def _manejar_error_bcch(bcch, exc: Exception, respaldo_red: str) -> JSONResponse:
    if isinstance(exc, bcch.FaltaTokenBCChError):
        return _error_json(
            503,
            "falta_token_bcch",
            _sanear_mensaje(
                exc,
                "Configura las credenciales del Banco Central de Chile en el servidor.",
            ),
        )
    return _error_json(
        502,
        "error_bcch",
        _sanear_mensaje(exc, respaldo_red),
    )


@router.get("/bcch/search")
def bcch_buscar_series(
    frequency: FrecuenciaBCCh = "ANNUAL",
    q: str = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    bcch = _cargar_bcch_live()
    try:
        return bcch.buscar_series_live(frequency=frequency, query=q, limit=limit)
    except (
        bcch.FaltaTokenBCChError,
        bcch.BdeApiError,
        URLError,
        HTTPClientError,
        OSError,
        TimeoutError,
    ) as exc:
        return _manejar_error_bcch(
            bcch,
            exc,
            "No se pudo consultar el catálogo del Banco Central de Chile.",
        )


@router.get("/bcch/series/{series_id}")
def bcch_obtener_serie(
    series_id: Annotated[str, PathParameter(min_length=1, max_length=128, pattern=SERIE_ID)],
    firstdate: Annotated[str, Query(pattern=FECHA_ISO)] = "2013-01-01",
    lastdate: Annotated[str | None, Query(pattern=FECHA_ISO)] = None,
):
    if lastdate is not None and firstdate > lastdate:
        return _error_json(
            422,
            "filtros_invalidos",
            "firstdate no puede ser posterior a lastdate.",
        )
    bcch = _cargar_bcch_live()
    try:
        return bcch.obtener_serie_live(
            series_id,
            firstdate=firstdate,
            lastdate=lastdate,
        )
    except (
        bcch.FaltaTokenBCChError,
        bcch.BdeApiError,
        URLError,
        HTTPClientError,
        OSError,
        TimeoutError,
    ) as exc:
        return _manejar_error_bcch(
            bcch,
            exc,
            "No se pudo obtener la serie desde el Banco Central de Chile.",
        )


@router.get("/territorial/aysen/estructura")
def territorial_aysen_estructura(
    anio_desde: Annotated[int, Query(ge=2013, le=2030)] = 2013,
    anio_hasta: Annotated[int | None, Query(ge=2013, le=2030)] = None,
    refresh: bool = False,
):
    if anio_hasta is not None and anio_desde > anio_hasta:
        return _error_json(
            422,
            "filtros_invalidos",
            "anio_desde no puede ser mayor que anio_hasta.",
        )
    bcch = _cargar_bcch_live()
    try:
        return bcch.obtener_estructura_aysen_live(
            anio_desde=anio_desde,
            anio_hasta=anio_hasta,
            refresh=refresh,
        )
    except (
        bcch.FaltaTokenBCChError,
        bcch.BdeApiError,
        URLError,
        HTTPClientError,
        OSError,
        TimeoutError,
    ) as exc:
        return _manejar_error_bcch(
            bcch,
            exc,
            "No se pudo obtener la estructura productiva de Aysén desde el Banco Central de Chile.",
        )


@router.get("/fiscal/dipres")
def fiscal_dipres(
    anio: Annotated[int, Query(ge=2020, le=2030)] = 2025,
    refresh: bool = False,
):
    dipres = _cargar_dipres_ckan()
    try:
        return dipres.obtener_ejecucion_aysen_live(anio=anio, refresh=refresh)
    except Exception as exc:
        return _error_json(
            502,
            "error_dipres",
            _sanear_mensaje(
                exc,
                "No se pudo consultar la ejecución presupuestaria de DIPRES.",
            ),
        )


@router.get("/fiscal/sinim")
def fiscal_sinim():
    sinim = _cargar_sinim_importer()
    try:
        datos = sinim.cargar_importacion_sinim(_ruta_sinim())
    except (OSError, ValueError) as exc:
        return _error_json(
            500,
            "error_sinim",
            _sanear_mensaje(exc, "No se pudo leer la importación SINIM almacenada."),
        )
    if datos is None:
        return _sinim_no_cargado()
    return {"cargado": True, **{k: v for k, v in datos.items() if k != "cargado"}}


@router.post("/fiscal/sinim/importar")
def fiscal_sinim_importar(payload: SolicitudImportacionSinim):
    nombre = Path(payload.nombre_archivo.strip()).name
    if not nombre:
        return _error_json(
            422,
            "esquema_sinim_invalido",
            "El archivo SINIM no cumple el esquema de las 10 comunas de Aysén.",
            errores=["El nombre de archivo no puede estar vacío."],
        )
    contenido_bytes = payload.contenido.encode("utf-8")
    if len(contenido_bytes) > MAX_SINIM_BYTES:
        return _error_json(
            413,
            "archivo_demasiado_grande",
            "El archivo SINIM supera el límite máximo permitido de 5 MB.",
        )
    sinim = _cargar_sinim_importer()
    resultado = sinim.importar_sinim_bytes(contenido_bytes, nombre)
    if not resultado.get("valido"):
        return _error_json(
            422,
            "esquema_sinim_invalido",
            "El archivo SINIM no cumple el esquema de las 10 comunas de Aysén.",
            errores=resultado.get("errores", []),
        )
    ruta = _ruta_sinim()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    sinim.guardar_importacion_sinim(resultado, ruta)
    return {"cargado": True, **{k: v for k, v in resultado.items() if k != "cargado"}}


@router.get("/fiscal/sinim/plantilla.csv")
def fiscal_sinim_plantilla_csv():
    sinim = _cargar_sinim_importer()
    contenido = sinim.plantilla_sinim_csv()
    return Response(
        content=contenido,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="sinim-aysen-plantilla.csv"',
        },
    )
