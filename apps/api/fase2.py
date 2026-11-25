"""Rutas Fase 2 de Chile Territorial: sectorial 16 regiones, demografía INE,
resumen de 4 cruces analíticos + Matriz de Dependencia Estatal y Laboratorio
de Investigación de Solo Lectura.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
import importlib
import json
import os
from pathlib import Path
import sys
from typing import Annotated, Any, Mapping

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .laboratorio import (
    RAIZ_REPO,
    RUTA_CRUCES_DEFECTO,
    RUTA_DIPRES_AYSEN_DEFECTO,
    RUTA_PIB_API_DEFECTO,
    RUTA_PIB_PUBLICO_DEFECTO,
    RUTA_POBLACION_DEFECTO,
    RUTA_SECTORIAL_AYSEN_RAW,
    RUTA_SECTORIAL_DEFECTO,
    RUTA_SINIM_DEFECTO,
    ejecutar_investigacion,
)

PREFIJO = "/api/v1"
PATRON_TERRITORIO = r"^(CL|0[1-9]|1[0-6])$"
_CONTEXTO_DECIMAL = Context(prec=34, rounding=ROUND_HALF_EVEN)
_CERO = Decimal("0")
_CIEN = Decimal("100")

router = APIRouter(prefix=PREFIJO)


class SolicitudLaboratorio(BaseModel):
    pregunta: str = Field(..., min_length=5, max_length=600)
    territorio: str = Field(default="11", pattern=PATRON_TERRITORIO)


def _asegurar_raiz_en_path() -> None:
    raiz = str(RAIZ_REPO)
    if raiz not in sys.path:
        sys.path.insert(0, raiz)


def _cargar_ine_poblacion():
    _asegurar_raiz_en_path()
    return importlib.import_module("pipelines.demografia.ine_poblacion")


def _error_json(status_code: int, codigo: str, mensaje: str, **extra) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"codigo": codigo, "mensaje": mensaje, **extra},
    )


def _ruta_sectorial() -> Path:
    personalizada = (os.getenv("CT_SECTORIAL_PATH") or "").strip()
    return Path(personalizada) if personalizada else RUTA_SECTORIAL_DEFECTO


def _ruta_poblacion() -> Path:
    personalizada = (os.getenv("CT_POBLACION_PATH") or "").strip()
    return Path(personalizada) if personalizada else RUTA_POBLACION_DEFECTO


def _ruta_pib_oficial() -> Path:
    personalizada = (os.getenv("CT_LOTE_OFICIAL") or "").strip()
    if personalizada:
        return Path(personalizada)
    if RUTA_PIB_API_DEFECTO.is_file():
        return RUTA_PIB_API_DEFECTO
    return RUTA_PIB_PUBLICO_DEFECTO


def _ruta_dipres() -> Path:
    personalizada = (os.getenv("CT_DIPRES_PATH") or "").strip()
    return Path(personalizada) if personalizada else RUTA_DIPRES_AYSEN_DEFECTO


def _ruta_sinim() -> Path:
    personalizada = (os.getenv("CT_SINIM_PATH") or "").strip()
    return Path(personalizada) if personalizada else RUTA_SINIM_DEFECTO


def _leer_json(ruta: Path) -> dict[str, Any]:
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(contenido, dict):
        raise ValueError(f"El archivo '{ruta.name}' no contiene un objeto JSON válido.")
    return contenido


def _leer_json_opcional(ruta: Path) -> dict[str, Any] | None:
    if not ruta.is_file():
        return None
    try:
        return _leer_json(ruta)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return None


def _a_decimal(valor: object) -> Decimal | None:
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, Decimal):
        return valor if valor.is_finite() else None
    texto = str(valor).strip()
    if not texto:
        return None
    try:
        numero = Decimal(texto)
    except InvalidOperation:
        return None
    return numero if numero.is_finite() else None


def _fmt(valor: Decimal | None, decimales: int = 2) -> str | None:
    if valor is None or not valor.is_finite():
        return None
    with localcontext(_CONTEXTO_DECIMAL):
        cuanto = Decimal("1").scaleb(-decimales)
        redondeado = valor.quantize(cuanto, rounding=ROUND_HALF_EVEN)
        return format(redondeado, "f")


def _ratio_pct(numerador: Decimal | None, denominador: Decimal | None) -> str | None:
    if numerador is None or denominador is None or denominador <= _CERO:
        return None
    with localcontext(_CONTEXTO_DECIMAL):
        return _fmt(_CIEN * (numerador / denominador), 2)


def _filtrar_sectorial(
    datos: dict[str, Any],
    *,
    anio: int | None,
    territorio: str | None,
) -> dict[str, Any]:
    """Aplica filtros opcionales de año y territorio sobre el corte sectorial sin mutar datos."""
    copia = deepcopy(datos)

    if isinstance(copia.get("por_anio"), Mapping):
        por_anio_original: dict[str, Any] = copia["por_anio"]
        if anio is not None:
            clave_anio = str(anio)
            por_anio_filtrado = (
                {clave_anio: por_anio_original[clave_anio]}
                if clave_anio in por_anio_original
                else {}
            )
        else:
            por_anio_filtrado = por_anio_original

        if territorio is not None:
            nuevo_por_anio: dict[str, Any] = {}
            for k_anio, bloque in por_anio_filtrado.items():
                if not isinstance(bloque, Mapping):
                    continue
                bloque_nuevo = dict(bloque)
                regiones = bloque.get("regiones")
                if isinstance(regiones, Mapping):
                    bloque_nuevo["regiones"] = (
                        {territorio: regiones[territorio]} if territorio in regiones else {}
                    )
                for rank_key in ("ranking_hhi", "ranking_krugman"):
                    ranking = bloque.get(rank_key)
                    if isinstance(ranking, list):
                        bloque_nuevo[rank_key] = [
                            item
                            for item in ranking
                            if isinstance(item, Mapping) and item.get("territorio") == territorio
                        ]
                nuevo_por_anio[k_anio] = bloque_nuevo
            por_anio_filtrado = nuevo_por_anio

        copia["por_anio"] = por_anio_filtrado

    elif isinstance(copia.get("regiones"), Mapping):
        if territorio is not None:
            regiones = copia["regiones"]
            copia["regiones"] = (
                {territorio: regiones[territorio]} if territorio in regiones else {}
            )
    elif isinstance(copia.get("regiones"), list):
        if territorio is not None:
            copia["regiones"] = [
                item
                for item in copia["regiones"]
                if isinstance(item, Mapping)
                and (item.get("territorio") == territorio or item.get("codigo") == territorio)
            ]

    traza = copia.get("fuente_trazabilidad")
    traza_dict = dict(traza) if isinstance(traza, Mapping) else {
        "institucion": "Banco Central de Chile (BDE SI3)",
    }
    traza_dict["solo_lectura"] = True
    traza_dict["filtros_aplicados"] = {"anio": anio, "territorio": territorio}
    copia["fuente_trazabilidad"] = traza_dict

    return {
        "disponible": True,
        "filtros": {"anio": anio, "territorio": territorio},
        **{k: v for k, v in copia.items() if k != "disponible"},
    }


@router.get("/sectorial/regiones")
def sectorial_regiones(
    anio: Annotated[int | None, Query(ge=2013, le=2030)] = None,
    territorio: Annotated[str | None, Query(pattern=PATRON_TERRITORIO)] = None,
):
    ruta = _ruta_sectorial()
    if not ruta.is_file():
        return {
            "disponible": False,
            "motivo": (
                "El corte sectorial oficial de las 16 regiones aún no se ha extraído en "
                "data/published/pib-sectorial-16-regiones.json."
            ),
            "filtros": {"anio": anio, "territorio": territorio},
            "fuente_trazabilidad": {
                "institucion": "Banco Central de Chile (BDE SI3)",
                "estado": "pendiente_extraccion",
                "archivo_esperado": "data/published/pib-sectorial-16-regiones.json",
                "catalogo_sectorial_disponible": bool(
                    (RAIZ_REPO / "data" / "published" / "catalogo-sectorial-bde.json").is_file()
                ),
            },
        }
    try:
        datos = _leer_json(ruta)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        return _error_json(
            500,
            "error_sectorial",
            f"No se pudo leer el corte sectorial de 16 regiones: {exc}",
        )
    return _filtrar_sectorial(datos, anio=anio, territorio=territorio)


@router.get("/demografia/poblacion")
def demografia_poblacion(
    anio: Annotated[int | None, Query(ge=2013, le=2030)] = None,
    territorio: Annotated[str | None, Query(pattern=PATRON_TERRITORIO)] = None,
):
    ruta_pob = _ruta_poblacion()
    if not ruta_pob.is_file():
        return {
            "disponible": False,
            "motivo": (
                "El corte oficial de población INE aún no se ha publicado en "
                "data/published/poblacion-ine-regiones.json."
            ),
            "filtros": {"anio": anio, "territorio": territorio},
            "fuente_trazabilidad": {
                "institucion": "Instituto Nacional de Estadísticas (INE) vía BCCh-BDE",
                "estado": "pendiente_extraccion",
                "archivo_esperado": "data/published/poblacion-ine-regiones.json",
            },
        }

    try:
        lote_poblacion = _leer_json(ruta_pob)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        return _error_json(
            500,
            "error_demografia",
            f"No se pudo leer el corte oficial de población INE: {exc}",
        )

    ruta_pib = _ruta_pib_oficial()
    lote_pib = _leer_json_opcional(ruta_pib)

    obs_pob = lote_poblacion.get("observaciones") if isinstance(lote_poblacion.get("observaciones"), list) else []
    obs_pob_filtradas = [
        fila
        for fila in obs_pob
        if isinstance(fila, Mapping)
        and (anio is None or fila.get("anio") == anio)
        and (territorio is None or fila.get("territorio") == territorio)
    ]
    anios_pob = sorted({fila["anio"] for fila in obs_pob if isinstance(fila, Mapping) and type(fila.get("anio")) is int})

    cruce: dict[str, Any] | None = None
    motivo_cruce: str | None = None
    if lote_pib is None:
        motivo_cruce = (
            "No se encontró el corte oficial de PIB (CT_LOTE_OFICIAL o data/published/pib-bde-api.json) "
            "para calcular PIB per cápita y σ-convergencia."
        )
    else:
        try:
            ine_mod = _cargar_ine_poblacion()
            cruce = ine_mod.calcular_pib_per_capita_nacional_y_regional(lote_pib, lote_poblacion)
        except Exception as exc:
            return _error_json(
                500,
                "error_demografia",
                f"No se pudo cruzar población INE con el corte oficial de PIB: {exc}",
            )

    pib_per_capita_salida: dict[str, Any] | None = None
    sigma_salida: list[dict[str, Any]] = []
    resumen_sigma_salida: dict[str, Any] | None = None
    advertencia_escala: str | None = (
        "Las cifras de PIB son de escala nacional y regional; nunca deben atribuirse ni imputarse a las 346 comunas."
    )

    if cruce is not None:
        series_cruce = cruce.get("series") or []
        if anio is not None or territorio is not None:
            series_cruce = [
                fila
                for fila in series_cruce
                if (anio is None or fila.get("anio") == anio)
                and (territorio is None or fila.get("territorio") == territorio)
            ]

        por_anio_cruce = deepcopy(cruce.get("por_anio") or {})
        if anio is not None:
            k_anio = str(anio)
            por_anio_cruce = {k_anio: por_anio_cruce[k_anio]} if k_anio in por_anio_cruce else {}
        if territorio is not None:
            for k_anio, bloque in list(por_anio_cruce.items()):
                if isinstance(bloque, Mapping) and isinstance(bloque.get("territorios"), Mapping):
                    bloque_mod = dict(bloque)
                    bloque_mod["territorios"] = (
                        {territorio: bloque["territorios"][territorio]}
                        if territorio in bloque["territorios"]
                        else {}
                    )
                    por_anio_cruce[k_anio] = bloque_mod

        sigma_salida = cruce.get("sigma_convergencia") or []
        if anio is not None:
            sigma_salida = [s for s in sigma_salida if s.get("anio") == anio]

        resumen_sigma_salida = cruce.get("resumen_sigma_convergencia")
        advertencia_escala = cruce.get("advertencia_escala_territorial") or advertencia_escala
        pib_per_capita_salida = {
            "metadatos": cruce.get("metadatos"),
            "series": series_cruce,
            "por_anio": por_anio_cruce,
        }

    pub_pob = lote_poblacion.get("publicacion") if isinstance(lote_poblacion.get("publicacion"), Mapping) else {}
    pub_pib = lote_pib.get("publicacion") if isinstance(lote_pib, Mapping) and isinstance(lote_pib.get("publicacion"), Mapping) else {}

    return {
        "disponible": True,
        "filtros": {"anio": anio, "territorio": territorio},
        "poblacion": {
            "publicacion": pub_pob,
            "anios": anios_pob,
            "unidad": "personas",
            "total_observaciones": len(obs_pob_filtradas),
            "observaciones": obs_pob_filtradas,
        },
        "pib_per_capita": pib_per_capita_salida,
        "sigma_convergencia": sigma_salida,
        "resumen_sigma_convergencia": resumen_sigma_salida,
        "motivo_cruce_pib": motivo_cruce,
        "advertencia_escala_territorial": advertencia_escala,
        "fuente_trazabilidad": {
            "institucion": "Instituto Nacional de Estadísticas (INE) vía BCCh-BDE + BCCh Cuentas Nacionales",
            "corte_poblacion": pub_pob.get("id"),
            "fecha_poblacion": pub_pob.get("fecha"),
            "corte_pib": pub_pib.get("id"),
            "fecha_pib": pub_pib.get("fecha"),
            "imputacion_pib_comunal_prohibida": True,
            "solo_lectura": True,
        },
    }


def _obtener_pib_nominal_anio(lote_pib: dict[str, Any] | None, territorio: str, anio: int) -> Decimal | None:
    if not lote_pib or not isinstance(lote_pib.get("observaciones"), list):
        return None
    for fila in lote_pib["observaciones"]:
        if (
            isinstance(fila, Mapping)
            and fila.get("territorio") == territorio
            and fila.get("anio") == anio
            and fila.get("metrica") == "nivel"
            and fila.get("valoracion") == "nominal"
        ):
            return _a_decimal(fila.get("valor"))
    return None


@router.get("/cruces/resumen")
def cruces_resumen():
    definicion = _leer_json_opcional(RUTA_CRUCES_DEFECTO) or {}
    cruces_base = definicion.get("cruces") if isinstance(definicion.get("cruces"), list) else []

    lote_pib = _leer_json_opcional(_ruta_pib_oficial())
    sectorial_16 = _leer_json_opcional(_ruta_sectorial())
    sectorial_aysen = _leer_json_opcional(RUTA_SECTORIAL_AYSEN_RAW)
    poblacion_ine = _leer_json_opcional(_ruta_poblacion())
    dipres_aysen = _leer_json_opcional(_ruta_dipres())
    sinim_aysen = _leer_json_opcional(_ruta_sinim())
    sinim_valido = isinstance(sinim_aysen, Mapping) and sinim_aysen.get("valido") is True

    # Datos reales de Aysén 2025 para métricas auditables
    anio_fiscal = dipres_aysen.get("anio") if isinstance(dipres_aysen, Mapping) else 2025
    anio_ref = anio_fiscal if type(anio_fiscal) is int else 2025
    pib_aysen_nom = _obtener_pib_nominal_anio(lote_pib, "11", anio_ref)

    totales_gc = (
        dipres_aysen.get("totales_gobierno_central_aysen")
        if isinstance(dipres_aysen, Mapping) and isinstance(dipres_aysen.get("totales_gobierno_central_aysen"), Mapping)
        else {}
    )
    gore_aysen = (
        dipres_aysen.get("gore_aysen")
        if isinstance(dipres_aysen, Mapping) and isinstance(dipres_aysen.get("gore_aysen"), Mapping)
        else {}
    )
    traza_dipres = (
        dipres_aysen.get("fuente_trazabilidad")
        if isinstance(dipres_aysen, Mapping) and isinstance(dipres_aysen.get("fuente_trazabilidad"), Mapping)
        else {}
    )

    gasto_directo_gc = _a_decimal(totales_gc.get("total_gasto_directo_millones"))
    gasto_corriente_gc = _a_decimal(totales_gc.get("gasto_corriente_sub_21_26"))
    inversion_gc = _a_decimal(totales_gc.get("inversion_sub_29_31"))
    transf_cap_gc = _a_decimal(totales_gc.get("transferencias_capital_sub_33"))
    fin_gore_p31 = _a_decimal(totales_gc.get("financiamiento_gore_p31") or gore_aysen.get("ingresos_financiamiento_p31"))

    # Plano (a) Actividad Económica Administración Pública (BCCh CCNN)
    adm_pub_info: dict[str, Any] = {
        "disponible": False,
        "estado": "pendiente",
        "concepto": "Valor agregado de la actividad económica Administración Pública en Cuentas Nacionales (BCCh CCNN)",
        "motivo": "No se encontró corte sectorial BCCh disponible en disco.",
    }
    if isinstance(sectorial_aysen, Mapping):
        res_pib = sectorial_aysen.get("resumen_pib") if isinstance(sectorial_aysen.get("resumen_pib"), Mapping) else {}
        sec_clave = res_pib.get("sectores_clave") if isinstance(res_pib.get("sectores_clave"), Mapping) else {}
        adm = sec_clave.get("administracion_publica") if isinstance(sec_clave.get("administracion_publica"), Mapping) else None
        traza_sec = (
            sectorial_aysen.get("fuente_trazabilidad")
            if isinstance(sectorial_aysen.get("fuente_trazabilidad"), Mapping)
            else {}
        )
        if adm is not None:
            adm_pub_info = {
                "disponible": True,
                "estado": "disponible",
                "concepto": "Valor agregado de la actividad económica Administración Pública en Cuentas Nacionales (BCCh CCNN)",
                "territorio": "11",
                "territorio_nombre": "Aysén del General Carlos Ibáñez del Campo",
                "anio": sectorial_aysen.get("ultimo_anio") or res_pib.get("anio"),
                "serie_bde": adm.get("serie_bde"),
                "valor_millones_clp": _fmt(_a_decimal(adm.get("valor_millones")), 2),
                "participacion_pib_nominal_pct": _fmt(_a_decimal(adm.get("participacion_pib_pct")), 2),
                "cobertura_16_regiones_disponible": sectorial_16 is not None,
                "fecha_actualizacion": traza_sec.get("actualizado_en"),
                "advertencia": (
                    "Mide únicamente el valor agregado de la rama Administración Pública en CCNN; "
                    "no equivale al gasto presupuestario total ni al empleo público."
                ),
            }

    # Plano (b) Gasto Público Presupuestario (DIPRES CKAN + SINIM)
    sinim_resumen = sinim_aysen.get("resumen") if sinim_valido and isinstance(sinim_aysen.get("resumen"), Mapping) else None
    gasto_presupuestario_info: dict[str, Any] = {
        "disponible": dipres_aysen is not None,
        "estado": "parcial_sin_consolidar" if dipres_aysen is not None else "pendiente",
        "concepto": "Ejecución presupuestaria del sector público (DIPRES CKAN Gobierno Central/GORE + SINIM municipal)",
        "territorio": "11",
        "territorio_nombre": "Aysén del General Carlos Ibáñez del Campo",
        "anio": anio_ref if dipres_aysen is not None else None,
        "etapa_informada": traza_dipres.get("etapa_informada") if dipres_aysen is not None else None,
        "gasto_directo_gobierno_central_millones": _fmt(gasto_directo_gc, 3),
        "gasto_corriente_sub_21_26_millones": _fmt(gasto_corriente_gc, 3),
        "inversion_sub_29_31_millones": _fmt(inversion_gc, 3),
        "transferencias_capital_sub_33_millones": _fmt(transf_cap_gc, 3),
        "financiamiento_gore_p31_millones": _fmt(fin_gore_p31, 3),
        "pib_nominal_referencia_millones": _fmt(pib_aysen_nom, 2),
        "ratio_gasto_directo_sobre_pib_nominal_pct": _ratio_pct(gasto_directo_gc, pib_aysen_nom),
        "sinim_municipal": (
            {
                "cargado": True,
                "anio": sinim_resumen.get("anio"),
                "comunas_cargadas": sinim_resumen.get("comunas_cargadas"),
                "total_gasto_devengado_millones": sinim_resumen.get("total_gasto_devengado_millones"),
            }
            if sinim_resumen is not None
            else {
                "cargado": False,
                "estado": "pendiente_importacion",
                "motivo": "Importación SINIM de las 10 comunas de Aysén pendiente.",
            }
        ),
        "resource_id_dipres": traza_dipres.get("resource_id"),
        "advertencia": (
            "Vistas brutas por billetera; no sumar Gobierno Central, Partida 31 GORE y SINIM municipal "
            "sin conciliación documental de transferencias internas. Excluye partidas nacionales sin asignación territorial."
        ),
    }

    # Plano (c) Empleo Público (INE ENE/microdatos — pendiente)
    empleo_publico_info: dict[str, Any] = {
        "disponible": False,
        "estado": "pendiente",
        "concepto": "Participación del empleo público en la ocupación total regional",
        "fuente_esperada": "INE · Encuesta Nacional de Empleo (ENE) / microdatos y dominios oficiales",
        "motivo": (
            "Pendiente de integración de microdatos/dominios representativos ENE del INE y clasificador "
            "oficial de empleo público vs privado; nunca se infiere desde CCNN ni desde presupuesto."
        ),
    }

    # Estado auditable de los 4 cruces analíticos
    metricas_por_cruce: dict[str, dict[str, Any]] = {
        "gasto_publico_pib": {
            "estado_operativo": "parcial_piloto_aysen" if (dipres_aysen and pib_aysen_nom) else "pendiente",
            "cobertura_actual": "Piloto Aysén (11) · Gobierno Central CKAN + PIB nominal BCCh; consolidación 3 billeteras pendiente",
            "metricas_disponibles": {
                "territorio": "11",
                "anio": anio_ref,
                "gasto_directo_gc_millones": _fmt(gasto_directo_gc, 3),
                "financiamiento_gore_p31_millones": _fmt(fin_gore_p31, 3),
                "pib_nominal_millones": _fmt(pib_aysen_nom, 2),
                "ratio_descriptivo_gc_sobre_pib_pct": _ratio_pct(gasto_directo_gc, pib_aysen_nom),
                "sinim_cargado": sinim_valido,
            },
        },
        "inversion_publica_pib": {
            "estado_operativo": "parcial_piloto_aysen" if (dipres_aysen and pib_aysen_nom) else "pendiente",
            "cobertura_actual": "Piloto Aysén (11) · Subtítulos 29–31 y 33 CKAN; enlace BIP/MOP/ChileIndica/SINIM pendiente",
            "metricas_disponibles": {
                "territorio": "11",
                "anio": anio_ref,
                "inversion_sub_29_31_millones": _fmt(inversion_gc, 3),
                "transferencias_capital_sub_33_millones": _fmt(transf_cap_gc, 3),
                "pib_nominal_millones": _fmt(pib_aysen_nom, 2),
                "ratio_inversion_directa_sobre_pib_pct": _ratio_pct(inversion_gc, pib_aysen_nom),
                "ratio_transf_capital_sobre_pib_pct": _ratio_pct(transf_cap_gc, pib_aysen_nom),
            },
        },
        "programas_beneficiarios_cobertura": {
            "estado_operativo": "parcial_denominador_ine" if poblacion_ine is not None else "pendiente_fuentes",
            "cobertura_actual": (
                "Denominador poblacional INE disponible; padrones deduplicados de beneficiarios y gasto atribuible por programa pendientes"
                if poblacion_ine is not None
                else "Pendiente de integración de población INE, padrones deduplicados de beneficiarios y ejecución por programa"
            ),
            "metricas_disponibles": {
                "poblacion_ine_disponible": poblacion_ine is not None,
                "padrones_beneficiarios_unicos": False,
            },
        },
        "costo_administrativo_eficiencia": {
            "estado_operativo": "parcial_piloto_aysen" if dipres_aysen is not None else "pendiente",
            "cobertura_actual": "Piloto Aysén (11) · Gasto corriente 21–26 CKAN disponible; base de reparto de costos compartidos y desglose GORE pendientes",
            "metricas_disponibles": {
                "territorio": "11",
                "anio": anio_ref,
                "gasto_corriente_sub_21_26_millones": _fmt(gasto_corriente_gc, 3),
                "inversion_sub_29_31_millones": _fmt(inversion_gc, 3),
                "ratio_gore_corriente_sobre_inversion_pct": gore_aysen.get("ratio_corriente_sobre_inversion_pct"),
                "motivo_brecha_gore": gore_aysen.get("motivo_brecha"),
            },
        },
    }

    cruces_auditables: list[dict[str, Any]] = []
    for cruce in cruces_base:
        if not isinstance(cruce, Mapping):
            continue
        cid = str(cruce.get("id") or "")
        estado_real = metricas_por_cruce.get(
            cid,
            {
                "estado_operativo": "pendiente",
                "cobertura_actual": "Sin métricas cargadas.",
                "metricas_disponibles": {},
            },
        )
        cruces_auditables.append(
            {
                "id": cid,
                "nombre": cruce.get("nombre"),
                "pregunta_investigacion": cruce.get("pregunta_investigacion"),
                "formula": cruce.get("formula"),
                "etapas_contables_validas": cruce.get("etapas_contables_validas", []),
                "billeteras": (cruce.get("perimetro") or {}).get("billeteras", []),
                "brechas_cobertura_vigentes": cruce.get("brechas_cobertura_vigentes", []),
                "criterio_no_atribucion_causal": cruce.get("criterio_no_atribucion_causal"),
                **estado_real,
            }
        )

    pub_pib = lote_pib.get("publicacion") if isinstance(lote_pib, Mapping) and isinstance(lote_pib.get("publicacion"), Mapping) else {}
    return {
        "version_definicion": definicion.get("version"),
        "fecha_revision": definicion.get("fecha_revision"),
        "territorio_piloto": definicion.get("territorio_piloto"),
        "total_cruces": len(cruces_auditables),
        "cruces": cruces_auditables,
        "matriz_dependencia_estatal": {
            "regla_separacion": (
                "La presencia del Estado se audita en tres planos independientes y no sumables: "
                "(a) actividad económica Administración Pública (BCCh CCNN), "
                "(b) gasto público presupuestario (DIPRES CKAN / SINIM) y "
                "(c) empleo público (INE ENE)."
            ),
            "actividad_economica_administracion_publica": adm_pub_info,
            "gasto_publico_presupuestario": gasto_presupuestario_info,
            "empleo_publico": empleo_publico_info,
        },
        "fuente_trazabilidad": {
            "definicion_cruces": "pipelines/fiscal/cruces-investigacion.json",
            "corte_pib": pub_pib.get("id"),
            "sectorial_16_regiones_disponible": sectorial_16 is not None,
            "sectorial_aysen_disponible": sectorial_aysen is not None,
            "poblacion_ine_disponible": poblacion_ine is not None,
            "dipres_aysen_disponible": dipres_aysen is not None,
            "sinim_aysen_cargado": sinim_valido,
            "solo_lectura": True,
        },
    }


@router.post("/laboratorio/consultar")
def laboratorio_consultar(payload: SolicitudLaboratorio):
    pregunta_limpia = payload.pregunta.strip()
    if len(pregunta_limpia) < 5 or len(pregunta_limpia) > 600:
        return _error_json(
            422,
            "filtros_invalidos",
            "La pregunta debe contener entre 5 y 600 caracteres válidos.",
        )
    try:
        return ejecutar_investigacion(
            pregunta=pregunta_limpia,
            territorio=payload.territorio,
        )
    except ValueError as exc:
        return _error_json(422, "filtros_invalidos", str(exc))
