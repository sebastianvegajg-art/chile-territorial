"""Extractor reproducible de población oficial INE (vía API REST BDE) e indicadores per cápita.

Cubre:
- Las 17 series anuales oficiales INE verificadas en ``SearchSeries(ANNUAL)``:
  ``CL`` (``F049.POB.STO.INE1.01.A``) y las 16 regiones ``01``..``16``
  (``F049.POB{XX}.STO.INE.AT.A``), para ``2013``–``2030``.
- Resguardo inmutable de insumos originales y ``manifiesto.json`` con hashes
  SHA-256 en ``data/raw/ine-poblacion-<timestamp>/``.
- Reproducción bit-a-bit sin red ni credenciales mediante
  ``--reproducir --insumos <dir>``.
- Publicación normalizada en ``data/published/poblacion-ine-regiones.json``.
- Cálculo exacto con ``Decimal`` de 34 dígitos significativos de PIB per cápita
  nacional y regional, índice ``Chile = 100``, ranking regional y
  σ-convergencia (coeficiente de variación entre las 16 regiones).
- Importador validado de tablas CSV oficiales del INE para las 346 comunas,
  distinguiendo explícitamente 346 comunas vs 345 administraciones municipales
  y bloqueando cualquier imputación de PIB a nivel comunal.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import sys
import unicodedata

_RAIZ_REPO = Path(__file__).resolve().parents[2]
if str(_RAIZ_REPO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_REPO))

from pipelines.economia.bde_api import (  # noqa: E402
    BdeApiError,
    Credenciales,
    ENDPOINT,
    MAX_BYTES,
    NOMBRES_TERRITORIOS,
    REGIONES,
    TERRITORIOS,
    _cargar_json_bde,
    _parsear_fecha_corte,
    _parsear_fecha_observacion,
    contiene_credencial,
    descargar,
    formatear_decimal,
    parsear_catalogo_anual,
    resolver_credenciales,
)


PRECISION_DECIMAL = 34
CONTEXTO_DECIMAL = Context(prec=PRECISION_DECIMAL, rounding=ROUND_HALF_EVEN)
CERO = Decimal("0")
CIEN = Decimal("100")
MILLON = Decimal("1000000")

FUENTE_POBLACION = "INE vía BCCh-BDE"
UNIDAD_POBLACION = "personas"
UNIDAD_PIB = "millones CLP"
UNIDAD_PIB_PER_CAPITA = "CLP por persona"

DESDE_PREDETERMINADO = date(2013, 1, 1)
HASTA_PREDETERMINADO = date(2030, 12, 31)

TOTAL_COMUNAS_CHILE = 346
TOTAL_MUNICIPALIDADES_CHILE = 345
CUT_CABO_DE_HORNOS = "12201"
CUT_ANTARTICA = "12202"

ADVERTENCIA_ESCALA_PIB = (
    "Las cifras de PIB son de escala nacional y regional; "
    "nunca deben atribuirse ni imputarse a las 346 comunas."
)

NOTA_COMUNA_VS_MUNICIPIO = (
    "Chile cuenta con 346 comunas (CUT de 5 dígitos) y 345 municipalidades: "
    "la comuna de Antártica (CUT 12202) carece de municipalidad propia y es "
    "administrada por la Ilustre Municipalidad de Cabo de Hornos (CUT 12201), "
    "conformando la agrupación comunal Cabo de Hornos y Antártica."
)

# Mapeo exacto verificado desde el catálogo oficial BDE/INE (SearchSeries ANNUAL).
SERIES_POBLACION_INE: dict[str, str] = {
    "CL": "F049.POB.STO.INE1.01.A",
    "01": "F049.POBTA.STO.INE.AT.A",
    "02": "F049.POBAN.STO.INE.AT.A",
    "03": "F049.POBAT.STO.INE.AT.A",
    "04": "F049.POBCO.STO.INE.AT.A",
    "05": "F049.POBVA.STO.INE.AT.A",
    "06": "F049.POBLI.STO.INE.AT.A",
    "07": "F049.POBML.STO.INE.AT.A",
    "08": "F049.POBBI.STO.INE.AT.A",
    "09": "F049.POBAR.STO.INE.AT.A",
    "10": "F049.POBLL.STO.INE.AT.A",
    "11": "F049.POBAI.STO.INE.AT.A",
    "12": "F049.POBMA.STO.INE.AT.A",
    "13": "F049.POBRM.STO.INE.AT.A",
    "14": "F049.POBLR.STO.INE.AT.A",
    "15": "F049.POBAP.STO.INE.AT.A",
    "16": "F049.POBNB.STO.INE.AT.A",
}

_ESTADOS_FALTANTES_BDE = frozenset({"ND", "SD", "NA", "N/A"})
_ESTADOS_DISPONIBLES = frozenset({"informado", "preliminar"})
_ESTADOS_AUSENTES = frozenset({"faltante", "suprimido", "no_aplicable", "error"})
_CLASES_VALIDAS = frozenset({"oficial", "estimacion", "proyeccion", "prueba"})
_VALORES_VACIOS_CSV = frozenset({"", "-", "--", "n/a", "na", "nd", "s/i", "sd", "null", "none"})

_PATRON_DECIMAL_ESTRICTO = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?$")
_PATRON_MILES_PUNTO = re.compile(r"^[1-9]\d{0,2}(?:\.\d{3})+$")
_PATRON_MILES_COMA = re.compile(r"^[1-9]\d{0,2}(?:,\d{3}){2,}$")
_PATRON_DEC_CL = re.compile(r"^\d{1,3}(?:\.\d{3})+,\d+$")
_PATRON_DEC_US = re.compile(r"^\d{1,3}(?:,\d{3})+\.\d+$")
_PATRON_COMA_DEC = re.compile(r"^\d+,\d+$")
_PATRON_COLUMNA_ANIO = re.compile(r"^(?:poblacion_|pob_|habitantes_|personas_|anio_|ano_)?(19\d{2}|20\d{2}|2100)$")
_PATRON_CUT_5 = re.compile(r"^\d{5}$")

_ALIAS_COLUMNAS_COMUNAL: dict[str, str] = {
    "cut": "cut",
    "codigo_comuna": "cut",
    "cod_comuna": "cut",
    "codigo_cut": "cut",
    "cut_comuna": "cut",
    "id_comuna": "cut",
    "comuna_codigo": "cut",
    "codigo": "cut",
    "comuna": "comuna",
    "nombre_comuna": "comuna",
    "glosa_comuna": "comuna",
    "nom_comuna": "comuna",
    "region": "region",
    "codigo_region": "region",
    "cod_region": "region",
    "cut_region": "region",
    "nombre_region": "nombre_region",
    "glosa_region": "nombre_region",
    "anio": "anio",
    "ano": "anio",
    "year": "anio",
    "periodo": "anio",
    "ejercicio": "anio",
    "poblacion": "poblacion",
    "poblacion_total": "poblacion",
    "total_poblacion": "poblacion",
    "habitantes": "poblacion",
    "personas": "poblacion",
    "valor": "poblacion",
    "pob_total": "poblacion",
    "clase": "clase",
    "tipo_dato": "clase",
    "tipo": "clase",
    "corte": "corte",
    "fuente": "fuente",
}

_CLASES_COMUNAL_CANONICAS: dict[str, str] = {
    "censo": "oficial",
    "censal": "oficial",
    "oficial": "oficial",
    "estimacion": "estimacion",
    "estimado": "estimacion",
    "proyeccion": "proyeccion",
    "proyectado": "proyeccion",
    "prueba": "prueba",
}


class InePoblacionError(Exception):
    """Error seguro del extractor o validador de población INE (sin revelar secretos)."""


@dataclass(frozen=True)
class SeriePoblacionCatalogo:
    """Metadatos validados en ``SearchSeries`` de una serie de población INE."""

    territorio: str
    codigo: str
    titulo_es: str
    titulo_en: str | None
    frecuencia: str
    primera_observacion: str | None
    ultima_observacion: str | None
    actualizada_en: str | None
    creada_en: str | None


def _normalizar_texto(texto: str) -> str:
    sin_tildes = "".join(
        ch for ch in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(ch)
    )
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


def _normalizar_cabecera(nombre: str) -> str:
    texto = unicodedata.normalize("NFKD", str(nombre).lstrip("\ufeff"))
    sin_tildes = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return re.sub(r"[^a-zA-Z0-9]+", "_", sin_tildes.strip().lower()).strip("_")


def _formatear_decimal_34(valor: Decimal) -> str:
    with localcontext(CONTEXTO_DECIMAL):
        return formatear_decimal(valor)


def _verificar_unidad_personas(codigo: str, *titulos: str | None) -> str:
    """Verifica explícitamente que la serie INE esté expresada en número de personas."""
    for titulo in titulos:
        if not titulo:
            continue
        norm = _normalizar_texto(titulo)
        if "miles de personas" in norm or "thousands of" in norm:
            raise InePoblacionError(
                f"{codigo}: unidad incompatible en metadatos BDE (se esperaba 'número de personas', "
                "no miles de personas)."
            )
        if "numero de personas" in norm or "number of people" in norm or "personas" in norm:
            return UNIDAD_POBLACION
    raise InePoblacionError(
        f"{codigo}: no se pudo verificar la unidad 'número de personas' en los metadatos BDE."
    )


def descubrir_series_poblacion(catalogo: Mapping[str, dict]) -> dict[str, SeriePoblacionCatalogo]:
    """Valida la presencia de las 17 series exactas INE en ``SearchSeries(ANNUAL)``."""
    descubiertas: dict[str, SeriePoblacionCatalogo] = {}
    faltantes: list[str] = []

    for territorio in TERRITORIOS:
        codigo = SERIES_POBLACION_INE[territorio]
        fila = catalogo.get(codigo)
        if fila is None:
            faltantes.append(f"{territorio}:{codigo}")
            continue
        titulo_es = str(fila.get("spanishTitle", "")).strip()
        if not titulo_es:
            raise InePoblacionError(f"{codigo}: título ausente en catálogo BDE.")
        titulo_en_raw = fila.get("englishTitle")
        titulo_en = titulo_en_raw.strip() if isinstance(titulo_en_raw, str) and titulo_en_raw.strip() else None
        frecuencia = str(fila.get("frequencyCode", "")).strip()
        if frecuencia != "ANNUAL":
            raise InePoblacionError(f"{codigo}: frecuencia inesperada ({frecuencia!r}); se requiere ANNUAL.")
        _verificar_unidad_personas(codigo, titulo_es, titulo_en)
        descubiertas[territorio] = SeriePoblacionCatalogo(
            territorio=territorio,
            codigo=codigo,
            titulo_es=titulo_es,
            titulo_en=titulo_en,
            frecuencia=frecuencia,
            primera_observacion=fila.get("firstObservation") if isinstance(fila.get("firstObservation"), str) else None,
            ultima_observacion=fila.get("lastObservation") if isinstance(fila.get("lastObservation"), str) else None,
            actualizada_en=fila.get("updatedAt") if isinstance(fila.get("updatedAt"), str) else None,
            creada_en=fila.get("createdAt") if isinstance(fila.get("createdAt"), str) else None,
        )

    if faltantes:
        raise InePoblacionError(
            f"SearchSeries: faltan {len(faltantes)} de las 17 series oficiales INE ({', '.join(faltantes)})."
        )
    return descubiertas


def _parsear_observaciones_poblacion(
    payload: dict,
    serie: SeriePoblacionCatalogo,
    desde: date,
    hasta: date,
) -> dict[int, dict]:
    bloque = payload.get("Series")
    if not isinstance(bloque, dict) or bloque.get("seriesId") != serie.codigo:
        raise InePoblacionError(f"{serie.codigo}: identidad de serie incorrecta en GetSeries.")
    filas = bloque.get("Obs")
    if not isinstance(filas, list) or not filas:
        raise InePoblacionError(f"{serie.codigo}: observaciones vacías o inválidas.")

    descrip_es = bloque.get("descripEsp") if isinstance(bloque.get("descripEsp"), str) else None
    _verificar_unidad_personas(serie.codigo, serie.titulo_es, descrip_es, serie.titulo_en)

    por_anio: dict[int, dict] = {}
    numericas = 0
    for fila in filas:
        if not isinstance(fila, dict):
            raise InePoblacionError(f"{serie.codigo}: observación mal formada.")
        try:
            fecha_str = fila["indexDateString"]
            fecha = _parsear_fecha_observacion(fecha_str)
            estado_bde = fila["statusCode"]
            valor_crudo = fila["value"]
        except (KeyError, TypeError, ValueError):
            raise InePoblacionError(f"{serie.codigo}: observación mal formada.") from None

        if not desde <= fecha <= hasta:
            raise InePoblacionError(f"{serie.codigo}: período fuera del rango solicitado ({fecha.isoformat()}).")
        if fecha.year in por_anio:
            raise InePoblacionError(f"{serie.codigo}: año repetido ({fecha.year}).")
        if not isinstance(estado_bde, str) or not estado_bde.strip():
            raise InePoblacionError(f"{serie.codigo}: statusCode inválido.")

        estado_limpio = estado_bde.strip()
        if estado_limpio == "OK":
            if valor_crudo is None:
                raise InePoblacionError(f"{serie.codigo}: observación OK sin valor numérico.")
            with localcontext(CONTEXTO_DECIMAL):
                try:
                    valor_decimal = Decimal(str(valor_crudo).strip())
                except InvalidOperation:
                    raise InePoblacionError(f"{serie.codigo}: observación OK con valor no numérico.") from None
                if not valor_decimal.is_finite():
                    raise InePoblacionError(f"{serie.codigo}: observación OK con valor no finito.")
                if valor_decimal < CERO:
                    raise InePoblacionError(f"{serie.codigo}: población negativa inválida ({valor_crudo}).")
                valor_str = formatear_decimal(valor_decimal)
            numericas += 1
            por_anio[fecha.year] = {
                "fecha_origen": fecha_str,
                "valor_crudo": str(valor_crudo),
                "status_bde": estado_limpio,
                "valor": valor_str,
                "estado": "informado",
                "motivo": None,
            }
        elif estado_limpio.upper() in _ESTADOS_FALTANTES_BDE:
            por_anio[fecha.year] = {
                "fecha_origen": fecha_str,
                "valor_crudo": None if valor_crudo is None else str(valor_crudo),
                "status_bde": estado_limpio,
                "valor": None,
                "estado": "faltante",
                "motivo": f"Observación no disponible en BDE (statusCode={estado_limpio}).",
            }
        else:
            raise InePoblacionError(f"{serie.codigo}: statusCode BDE no reconocido ({estado_limpio}).")

    if numericas == 0:
        raise InePoblacionError(f"{serie.codigo}: ninguna observación numérica finita.")
    return por_anio


def _clasificar_observacion_poblacion(
    anio: int,
    corte: str | None,
    extraido_en: str,
    estado_publicacion: str,
    estado_obs: str,
) -> str:
    if estado_obs != "informado":
        return "no_disponible"
    if estado_publicacion == "prueba":
        return "prueba"
    anio_referencia_corte = int(corte[:4]) if corte else int(extraido_en[:4])
    return "proyeccion" if anio > anio_referencia_corte else "estimacion"


def normalizar_poblacion_ine(
    catalogo_bytes: bytes,
    series_bytes: Mapping[str, bytes],
    extraido_en: str,
    desde: date = DESDE_PREDETERMINADO,
    hasta: date = HASTA_PREDETERMINADO,
    estado_publicacion: str = "aprobada",
) -> dict:
    """Normaliza catálogo BDE y las 17 series INE a ``poblacion-ine-regiones.json``."""
    if estado_publicacion not in {"aprobada", "prueba"}:
        raise InePoblacionError("estado_publicacion debe ser 'aprobada' o 'prueba'.")
    if desde > hasta:
        raise InePoblacionError("El inicio del período debe preceder al final.")

    try:
        payload_catalogo = _cargar_json_bde(catalogo_bytes, parse_float=str)
    except (ValueError, UnicodeError):
        raise InePoblacionError("Catálogo anual JSON inválido.") from None

    try:
        catalogo = parsear_catalogo_anual(payload_catalogo)
    except BdeApiError as error:
        raise InePoblacionError(str(error)) from None

    series_poblacion = descubrir_series_poblacion(catalogo)

    faltan_bytes = [
        serie.codigo for serie in series_poblacion.values() if serie.codigo not in series_bytes
    ]
    if faltan_bytes:
        raise InePoblacionError(
            f"Faltan insumos GetSeries de población para: {', '.join(sorted(faltan_bytes))}."
        )

    hash_catalogo = sha256(catalogo_bytes).hexdigest()
    hashes_series = {
        serie.codigo: sha256(series_bytes[serie.codigo]).hexdigest()
        for serie in series_poblacion.values()
    }
    cadena_huella = hash_catalogo + "".join(
        hashes_series[series_poblacion[territorio].codigo] for territorio in TERRITORIOS
    )
    huella = sha256(cadena_huella.encode("utf-8")).hexdigest()[:16]
    publicacion_id = f"ine-poblacion-bde-{extraido_en[:10]}-{huella}"

    artefactos: list[dict] = [
        {
            "id": "bde-api-catalogo-anual",
            "fuente": FUENTE_POBLACION,
            "url": ENDPOINT,
            "sha256": hash_catalogo,
            "corte": None,
            "extraido_en": extraido_en,
        }
    ]

    series_meta: list[dict] = []
    datos_por_territorio: dict[str, tuple[SeriePoblacionCatalogo, str, str | None, dict[int, dict]]] = {}
    anios_observados: set[int] = set()

    for territorio in TERRITORIOS:
        serie = series_poblacion[territorio]
        raw_serie = series_bytes[serie.codigo]
        try:
            payload_serie = _cargar_json_bde(raw_serie, parse_float=str)
        except (ValueError, UnicodeError):
            raise InePoblacionError(f"{serie.codigo}: cuerpo JSON de GetSeries inválido.") from None

        por_anio = _parsear_observaciones_poblacion(payload_serie, serie, desde, hasta)
        anios_observados.update(por_anio.keys())
        corte_serie = _parsear_fecha_corte(serie.actualizada_en)
        artefacto_id = f"bde-api-{serie.codigo}"
        artefactos.append({
            "id": artefacto_id,
            "fuente": FUENTE_POBLACION,
            "url": ENDPOINT,
            "sha256": hashes_series[serie.codigo],
            "corte": corte_serie,
            "extraido_en": extraido_en,
        })
        series_meta.append({
            "territorio": territorio,
            "nombre_territorio": NOMBRES_TERRITORIOS[territorio],
            "serie_bde": serie.codigo,
            "titulo_es": serie.titulo_es,
            "titulo_en": serie.titulo_en,
            "unidad": UNIDAD_POBLACION,
            "frecuencia": serie.frecuencia,
            "corte": corte_serie,
            "primera_observacion": serie.primera_observacion,
            "ultima_observacion": serie.ultima_observacion,
        })
        datos_por_territorio[territorio] = (serie, artefacto_id, corte_serie, por_anio)

    anios = tuple(range(desde.year, hasta.year + 1))
    observaciones: list[dict] = []
    procedencias: list[dict] = []
    valores_por_clave: dict[tuple[str, int], Decimal] = {}

    for territorio in TERRITORIOS:
        serie, artefacto_id, corte_serie, por_anio = datos_por_territorio[territorio]
        for anio in anios:
            obs_id = f"{publicacion_id}.{territorio}.{anio}.poblacion"
            dato = por_anio.get(anio)
            if dato is None:
                estado_obs = "faltante"
                valor_obs = None
                clase_obs = "no_disponible"
                selector = f"GetSeries · {serie.codigo} · {anio} · sin fila"
                motivo = f"Año {anio} ausente en la serie BDE {serie.codigo}."
            else:
                estado_obs = dato["estado"]
                valor_obs = dato["valor"]
                clase_obs = _clasificar_observacion_poblacion(
                    anio, corte_serie, extraido_en, estado_publicacion, estado_obs
                )
                selector = (
                    f"GetSeries · {serie.codigo} · {dato['fecha_origen']} · "
                    f"{dato['valor_crudo']} ({UNIDAD_POBLACION}) · statusCode={dato['status_bde']}"
                )
                motivo = dato["motivo"]
                if valor_obs is not None:
                    valores_por_clave[(territorio, anio)] = Decimal(valor_obs)

            observaciones.append({
                "id": obs_id,
                "territorio": territorio,
                "nombre_territorio": NOMBRES_TERRITORIOS[territorio],
                "anio": anio,
                "metrica": "poblacion",
                "valor": valor_obs,
                "unidad": UNIDAD_POBLACION,
                "estado": estado_obs,
                "clase": clase_obs,
                "corte": corte_serie,
                "publicacion": publicacion_id,
            })
            procedencias.append({
                "observacion": obs_id,
                "publicacion": publicacion_id,
                "serie_bde": serie.codigo,
                "artefacto": artefacto_id,
                "selector": selector,
                "formula_version": None,
                "insumos": [],
                "motivo": motivo,
            })

    corte_cl = datos_por_territorio["CL"][2]
    cortes_reg = sorted({datos_por_territorio[reg][2] for reg in REGIONES if datos_por_territorio[reg][2]})
    nota_cortes = (
        f"La serie nacional CL tiene corte {corte_cl} y las 16 series regionales tienen corte(s) "
        f"{', '.join(cortes_reg) if cortes_reg else 'no informado'}. "
        "Cuando las vigencias censales/proyecciones difieren entre la serie nacional y las regionales, "
        "la suma de las 16 regiones puede diferir del total nacional CL; se reporta la conciliación explícita."
    )

    conciliacion: list[dict] = []
    with localcontext(CONTEXTO_DECIMAL):
        for anio in anios:
            pob_cl = valores_por_clave.get(("CL", anio))
            pobs_reg = [valores_por_clave[(r, anio)] for r in REGIONES if (r, anio) in valores_por_clave]
            regiones_faltantes = [r for r in REGIONES if (r, anio) not in valores_por_clave]
            if pob_cl is not None and len(pobs_reg) == len(REGIONES):
                suma_reg = sum(pobs_reg, CERO)
                diff = pob_cl - suma_reg
                diff_pct = (diff * CIEN / pob_cl) if pob_cl > CERO else None
                conciliacion.append({
                    "anio": anio,
                    "poblacion_nacional_cl": _formatear_decimal_34(pob_cl),
                    "suma_16_regiones": _formatear_decimal_34(suma_reg),
                    "diferencia_cl_menos_regiones": _formatear_decimal_34(diff),
                    "diferencia_porcentual": _formatear_decimal_34(diff_pct) if diff_pct is not None else None,
                    "estado": "conciliado" if diff == CERO else "diferencia_corte_vintage",
                    "regiones_faltantes": [],
                })
            else:
                conciliacion.append({
                    "anio": anio,
                    "poblacion_nacional_cl": _formatear_decimal_34(pob_cl) if pob_cl is not None else None,
                    "suma_16_regiones": _formatear_decimal_34(sum(pobs_reg, CERO)) if pobs_reg else None,
                    "diferencia_cl_menos_regiones": None,
                    "diferencia_porcentual": None,
                    "estado": "incompleto",
                    "regiones_faltantes": regiones_faltantes,
                })

    return {
        "publicacion": {
            "id": publicacion_id,
            "version_esquema": "ine-poblacion-regiones-v1",
            "fecha": extraido_en,
            "estado": estado_publicacion,
            "fuente": FUENTE_POBLACION,
            "endpoint": ENDPOINT,
            "unidad": UNIDAD_POBLACION,
            "rango_anios": {"desde": desde.year, "hasta": hasta.year},
            "cobertura": {
                "territorios": len(TERRITORIOS),
                "series_esperadas": len(SERIES_POBLACION_INE),
                "esperadas": len(observaciones),
                "disponibles": sum(obs["valor"] is not None for obs in observaciones),
            },
            "cortes_por_escala": {
                "nacional_CL": corte_cl,
                "regional_01_16": cortes_reg[0] if len(cortes_reg) == 1 else cortes_reg,
                "nota_cortes": nota_cortes,
            },
            "advertencia_escala_territorial": ADVERTENCIA_ESCALA_PIB,
            "cambios": [
                f"Población oficial INE {desde.year}–{hasta.year} para Chile y 16 regiones (17 series verificadas vía API REST BDE).",
                "Normalización exacta con Decimal(34) en unidad 'personas' distinguiendo estimaciones y proyecciones según fecha de corte.",
                nota_cortes,
            ],
        },
        "series": series_meta,
        "artefactos": artefactos,
        "observaciones": observaciones,
        "procedencias": procedencias,
        "conciliacion_nacional_regional": conciliacion,
    }


def _escribir_salida_protegida(ruta: Path, contenido: bytes, credenciales: Credenciales | None = None) -> None:
    if credenciales is not None and contiene_credencial(contenido, credenciales):
        raise InePoblacionError("Se bloqueó la escritura: se detectó una credencial en el contenido de salida.")
    if ruta.exists():
        if ruta.read_bytes() != contenido:
            raise InePoblacionError(
                f"La salida {ruta} ya pertenece a otro lote. Indica otra ruta o reproduce el lote original."
            )
        return
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("xb") as archivo:
        archivo.write(contenido)


def _verificar_manifiesto_raw(insumos_dir: Path) -> tuple[dict, bytes, dict[str, bytes]]:
    ruta_manifiesto = insumos_dir / "manifiesto.json"
    if not ruta_manifiesto.is_file():
        raise InePoblacionError(f"No se encontró manifiesto.json en {insumos_dir}.")
    try:
        manifiesto = json.loads(ruta_manifiesto.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise InePoblacionError("No se pudo leer manifiesto.json de insumos.") from None

    if not isinstance(manifiesto, dict) or not isinstance(manifiesto.get("artefactos"), list):
        raise InePoblacionError("Estructura inválida en manifiesto.json.")

    catalogo_bytes: bytes | None = None
    series_bytes: dict[str, bytes] = {}
    raiz_insumos = insumos_dir.resolve()

    for entrada in manifiesto["artefactos"]:
        if not isinstance(entrada, dict):
            raise InePoblacionError("Entrada inválida en manifiesto.json.")
        relativo = entrada.get("archivo")
        esperado = entrada.get("sha256")
        if not isinstance(relativo, str) or not isinstance(esperado, str):
            raise InePoblacionError("Metadatos incompletos en manifiesto.json.")
        ruta_archivo = (insumos_dir / relativo).resolve()
        if raiz_insumos not in ruta_archivo.parents:
            raise InePoblacionError("Ruta de artefacto fuera del directorio de insumos.")
        if not ruta_archivo.is_file():
            raise InePoblacionError(f"Falta archivo de insumo declarado en manifiesto: {relativo}.")
        crudo = ruta_archivo.read_bytes()
        if sha256(crudo).hexdigest() != esperado:
            raise InePoblacionError(f"Integridad SHA-256 fallida para {relativo}.")
        if entrada.get("id") == "bde-api-catalogo-anual":
            catalogo_bytes = crudo
        elif isinstance(entrada.get("serie_bde"), str):
            series_bytes[entrada["serie_bde"]] = crudo

    if catalogo_bytes is None:
        raise InePoblacionError("El manifiesto no incluye el catálogo anual.")
    return manifiesto, catalogo_bytes, series_bytes


def ejecutar_extraccion(
    credenciales: Credenciales,
    insumos_dir: Path,
    desde: date = DESDE_PREDETERMINADO,
    hasta: date = HASTA_PREDETERMINADO,
    salida_poblacion: Path = Path("data/published/poblacion-ine-regiones.json"),
    estado_publicacion: str = "aprobada",
) -> dict:
    """Ejecuta la extracción autenticada de las 17 series INE, archiva raw y publica JSON."""
    if desde > hasta:
        raise InePoblacionError("El inicio del período debe preceder al final.")
    if insumos_dir.exists():
        raise InePoblacionError(f"El directorio de insumos ya existe: {insumos_dir}.")

    extraido_en = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        catalogo_bytes, payload_catalogo = descargar(credenciales, "SearchSeries", frequency="ANNUAL")
        catalogo = parsear_catalogo_anual(payload_catalogo)
    except BdeApiError as error:
        raise InePoblacionError(str(error)) from None

    series_poblacion = descubrir_series_poblacion(catalogo)

    series_bytes: dict[str, bytes] = {}
    artefactos_raw: list[dict] = [
        {
            "id": "bde-api-catalogo-anual",
            "archivo": "catalogo-anual.json",
            "sha256": sha256(catalogo_bytes).hexdigest(),
            "bytes": len(catalogo_bytes),
            "territorio": None,
            "serie_bde": None,
            "corte": None,
        }
    ]

    for territorio in TERRITORIOS:
        serie = series_poblacion[territorio]
        try:
            raw_serie, _payload_serie = descargar(
                credenciales,
                "GetSeries",
                timeseries=serie.codigo,
                firstdate=desde.isoformat(),
                lastdate=hasta.isoformat(),
            )
        except BdeApiError as error:
            raise InePoblacionError(str(error)) from None
        series_bytes[serie.codigo] = raw_serie
        artefactos_raw.append({
            "id": f"bde-api-{serie.codigo}",
            "archivo": f"series/{serie.codigo}.json",
            "sha256": sha256(raw_serie).hexdigest(),
            "bytes": len(raw_serie),
            "territorio": territorio,
            "serie_bde": serie.codigo,
            "corte": _parsear_fecha_corte(serie.actualizada_en),
        })

    lote_poblacion = normalizar_poblacion_ine(
        catalogo_bytes,
        series_bytes,
        extraido_en,
        desde=desde,
        hasta=hasta,
        estado_publicacion=estado_publicacion,
    )

    manifiesto = {
        "version_esquema": "ine-poblacion-raw-v1",
        "fuente": ENDPOINT,
        "extraido_en": extraido_en,
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "estado_publicacion": estado_publicacion,
        "series_esperadas": len(SERIES_POBLACION_INE),
        "series_catalogo_anual": len(catalogo),
        "artefactos": artefactos_raw,
    }
    manifiesto_bytes = (json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    pob_bytes = (json.dumps(lote_poblacion, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    if contiene_credencial(manifiesto_bytes, credenciales) or contiene_credencial(pob_bytes, credenciales):
        raise InePoblacionError("Se bloqueó la escritura: credencial detectada en artefacto de salida.")
    if salida_poblacion.exists() and salida_poblacion.read_bytes() != pob_bytes:
        raise InePoblacionError(
            f"La salida {salida_poblacion} ya pertenece a otro lote. Indica otra ruta."
        )

    insumos_dir.parent.mkdir(parents=True, exist_ok=True)
    insumos_dir.mkdir(mode=0o700, exist_ok=False)
    (insumos_dir / "catalogo-anual.json").write_bytes(catalogo_bytes)
    (insumos_dir / "series").mkdir(parents=True, exist_ok=True)
    for codigo, crudo in series_bytes.items():
        (insumos_dir / "series" / f"{codigo}.json").write_bytes(crudo)
    (insumos_dir / "manifiesto.json").write_bytes(manifiesto_bytes)

    _escribir_salida_protegida(salida_poblacion, pob_bytes, credenciales)

    return {
        "insumos": str(insumos_dir),
        "salida": str(salida_poblacion),
        "publicacion": lote_poblacion["publicacion"],
    }


def reproducir_desde_raw(
    insumos_dir: Path,
    salida_poblacion: Path = Path("data/published/poblacion-ine-regiones.json"),
) -> dict:
    """Reconstruye ``poblacion-ine-regiones.json`` bit-a-bit desde insumos raw sin red."""
    manifiesto, catalogo_bytes, series_bytes = _verificar_manifiesto_raw(insumos_dir)
    extraido_en = manifiesto["extraido_en"]
    desde = date.fromisoformat(manifiesto["desde"])
    hasta = date.fromisoformat(manifiesto["hasta"])
    estado_publicacion = manifiesto.get("estado_publicacion", "aprobada")

    lote_poblacion = normalizar_poblacion_ine(
        catalogo_bytes,
        series_bytes,
        extraido_en,
        desde=desde,
        hasta=hasta,
        estado_publicacion=estado_publicacion,
    )
    pob_bytes = (json.dumps(lote_poblacion, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _escribir_salida_protegida(salida_poblacion, pob_bytes)

    return {
        "insumos": str(insumos_dir),
        "salida": str(salida_poblacion),
        "publicacion": lote_poblacion["publicacion"],
    }


def _validar_decimal_str(valor: object, contexto_msg: str) -> Decimal:
    if not isinstance(valor, str) or not _PATRON_DECIMAL_ESTRICTO.fullmatch(valor.strip()):
        raise InePoblacionError(f"Valor decimal inválido en {contexto_msg}.")
    dec = Decimal(valor.strip())
    if not dec.is_finite():
        raise InePoblacionError(f"Valor decimal no finito en {contexto_msg}.")
    return dec


def _calcular_ranking_regional(valores: Mapping[str, Decimal]) -> tuple[dict[str, int], list[dict]]:
    """Ordena regiones de mayor a menor; los empates comparten posición."""
    candidatas = [(valores[reg], reg) for reg in REGIONES if reg in valores]
    candidatas.sort(key=lambda item: item[1])
    candidatas.sort(key=lambda item: item[0], reverse=True)

    posiciones: dict[str, int] = {}
    tabla: list[dict] = []
    valor_anterior: Decimal | None = None
    posicion = 0
    for orden, (val_dec, reg) in enumerate(candidatas, start=1):
        if val_dec != valor_anterior:
            posicion = orden
        posiciones[reg] = posicion
        tabla.append({
            "posicion": posicion,
            "territorio": reg,
            "nombre_territorio": NOMBRES_TERRITORIOS[reg],
            "valor_clp": _formatear_decimal_34(val_dec),
        })
        valor_anterior = val_dec
    return posiciones, tabla


def _calcular_sigma_convergencia_anual(
    valores_por_region: Mapping[str, Decimal],
) -> dict:
    """Calcula media, desviación estándar poblacional y CV (σ-convergencia) entre 16 regiones."""
    faltantes = [reg for reg in REGIONES if reg not in valores_por_region]
    if faltantes:
        return {
            "estado": "faltante",
            "motivo": (
                f"σ-convergencia requiere las 16 regiones completas; faltan: {', '.join(faltantes)}."
            ),
            "n_regiones": len(REGIONES) - len(faltantes),
            "regiones_faltantes": faltantes,
            "media_regional_clp": None,
            "desviacion_estandar_clp": None,
            "coeficiente_variacion": None,
            "coeficiente_variacion_pct": None,
            "min_regional_clp": None,
            "max_regional_clp": None,
            "brecha_max_min": None,
        }

    with localcontext(CONTEXTO_DECIMAL):
        serie = [valores_por_region[reg] for reg in REGIONES]
        n = Decimal(len(serie))
        media = sum(serie, CERO) / n
        if media <= CERO:
            return {
                "estado": "faltante",
                "motivo": "Media regional no positiva; el coeficiente de variación no está definido.",
                "n_regiones": len(serie),
                "regiones_faltantes": [],
                "media_regional_clp": _formatear_decimal_34(media),
                "desviacion_estandar_clp": None,
                "coeficiente_variacion": None,
                "coeficiente_variacion_pct": None,
                "min_regional_clp": _formatear_decimal_34(min(serie)),
                "max_regional_clp": _formatear_decimal_34(max(serie)),
                "brecha_max_min": None,
            }
        varianza = sum(((x - media) ** 2 for x in serie), CERO) / n
        desviacion = varianza.sqrt()
        cv = desviacion / media
        cv_pct = cv * CIEN
        minimo = min(serie)
        maximo = max(serie)
        brecha = (maximo / minimo) if minimo > CERO else None

    return {
        "estado": "informado",
        "motivo": None,
        "n_regiones": len(serie),
        "regiones_faltantes": [],
        "media_regional_clp": _formatear_decimal_34(media),
        "desviacion_estandar_clp": _formatear_decimal_34(desviacion),
        "coeficiente_variacion": _formatear_decimal_34(cv),
        "coeficiente_variacion_pct": _formatear_decimal_34(cv_pct),
        "min_regional_clp": _formatear_decimal_34(minimo),
        "max_regional_clp": _formatear_decimal_34(maximo),
        "brecha_max_min": _formatear_decimal_34(brecha) if brecha is not None else None,
    }


def calcular_pib_per_capita_nacional_y_regional(
    lote_pib: dict,
    lote_poblacion: dict,
) -> dict:
    """Combina PIB nacional/regional (``millones CLP``) y población INE (``personas``) con ``Decimal(34)``.

    Fórmula exacta: ``pib_per_capita_clp = pib_millones * 1_000_000 / personas``.
    Prohíbe estrictamente imputar o atribuir PIB a las 346 comunas.
    """
    if not isinstance(lote_pib, Mapping) or not isinstance(lote_pib.get("observaciones"), list):
        raise InePoblacionError("lote_pib inválido: se requiere un diccionario con 'observaciones'.")
    if not isinstance(lote_poblacion, Mapping) or not isinstance(lote_poblacion.get("observaciones"), list):
        raise InePoblacionError("lote_poblacion inválido: se requiere un diccionario con 'observaciones'.")

    pub_pib = lote_pib.get("publicacion") if isinstance(lote_pib.get("publicacion"), Mapping) else {}
    pub_pob = lote_poblacion.get("publicacion") if isinstance(lote_poblacion.get("publicacion"), Mapping) else {}
    pub_pib_id = pub_pib.get("id")
    pub_pob_id = pub_pob.get("id")

    niveles_pib: dict[tuple[str, str, int], dict] = {}
    anios_ref_real: set[int] = set()
    anios_pib: set[int] = set()

    for obs in lote_pib["observaciones"]:
        if not isinstance(obs, Mapping):
            raise InePoblacionError("Observación de PIB mal formada.")
        territorio = obs.get("territorio")
        if not isinstance(territorio, str):
            raise InePoblacionError("Observación de PIB sin territorio válido.")
        if territorio not in TERRITORIOS:
            if _PATRON_CUT_5.fullmatch(territorio.strip()):
                raise InePoblacionError(
                    f"Territorio comunal detectado en lote_pib ({territorio}). {ADVERTENCIA_ESCALA_PIB}"
                )
            raise InePoblacionError(
                f"Territorio no permitido en lote_pib ({territorio!r}); solo se admiten CL y regiones 01..16."
            )

        if obs.get("metrica") != "nivel":
            continue
        valoracion = obs.get("valoracion")
        if valoracion not in {"real", "nominal"}:
            continue
        anio = obs.get("anio")
        if type(anio) is not int or anio < 2013:
            continue
        if obs.get("unidad") != UNIDAD_PIB:
            raise InePoblacionError(
                f"Unidad incompatible en lote_pib para {territorio}/{anio}: se requiere '{UNIDAD_PIB}'."
            )
        if valoracion == "real" and isinstance(obs.get("anio_referencia"), int):
            anios_ref_real.add(obs["anio_referencia"])

        clave = (valoracion, territorio, anio)
        if clave in niveles_pib:
            raise InePoblacionError(f"Nivel de PIB duplicado para {valoracion}/{territorio}/{anio}.")
        niveles_pib[clave] = dict(obs)
        anios_pib.add(anio)

    if not anios_pib:
        raise InePoblacionError("lote_pib no contiene niveles de PIB desde 2013 en adelante.")
    if len(anios_ref_real) > 1:
        raise InePoblacionError(
            f"lote_pib mezcla múltiples años de referencia reales ({sorted(anios_ref_real)})."
        )

    poblacion_idx: dict[tuple[str, int], dict] = {}
    for obs in lote_poblacion["observaciones"]:
        if not isinstance(obs, Mapping):
            raise InePoblacionError("Observación de población mal formada.")
        if obs.get("metrica") != "poblacion":
            continue
        territorio = obs.get("territorio")
        if not isinstance(territorio, str):
            raise InePoblacionError("Observación de población sin territorio válido.")
        if territorio not in TERRITORIOS:
            if _PATRON_CUT_5.fullmatch(territorio.strip()):
                raise InePoblacionError(
                    f"No se puede cruzar PIB con población comunal ({territorio}). {ADVERTENCIA_ESCALA_PIB}"
                )
            raise InePoblacionError(f"Territorio no permitido en lote_poblacion ({territorio!r}).")
        anio = obs.get("anio")
        if type(anio) is not int:
            raise InePoblacionError(f"Año inválido en lote_poblacion para {territorio}.")
        if obs.get("unidad") != UNIDAD_POBLACION:
            raise InePoblacionError(
                f"Unidad incompatible en lote_poblacion para {territorio}/{anio}: se requiere '{UNIDAD_POBLACION}'."
            )
        clave = (territorio, anio)
        if clave in poblacion_idx:
            raise InePoblacionError(f"Población duplicada para {territorio}/{anio}.")
        poblacion_idx[clave] = dict(obs)

    anios = sorted(anios_pib)
    anio_referencia_real = next(iter(anios_ref_real)) if anios_ref_real else None

    series_planas: list[dict] = []
    por_anio: dict[str, dict] = {}
    sigma_lista: list[dict] = []

    def evaluar_per_capita(
        pib_obs: dict | None,
        pob_obs: dict | None,
        etiqueta: str,
    ) -> tuple[Decimal | None, str | None, str, str | None]:
        if pib_obs is None:
            return None, None, "faltante", f"Falta nivel de PIB {etiqueta} para el territorio y año."
        estado_pib = pib_obs.get("estado")
        if estado_pib not in _ESTADOS_DISPONIBLES:
            estado_res = estado_pib if estado_pib in _ESTADOS_AUSENTES else "error"
            return None, None, estado_res, f"PIB {etiqueta} no disponible (estado={estado_pib})."

        if pob_obs is None:
            return None, None, "faltante", "Falta población oficial INE para el territorio y año."
        estado_pob = pob_obs.get("estado")
        if estado_pob not in _ESTADOS_DISPONIBLES:
            estado_res = estado_pob if estado_pob in _ESTADOS_AUSENTES else "error"
            return None, None, estado_res, f"Población no disponible (estado={estado_pob})."

        clase_pib = pib_obs.get("clase")
        clase_pob = pob_obs.get("clase")
        if clase_pib not in _CLASES_VALIDAS or clase_pob not in _CLASES_VALIDAS:
            return None, None, "error", "Clase de evidencia inválida en PIB o población."
        if ("prueba" in {clase_pib, clase_pob}) and clase_pib != clase_pob:
            return None, None, "error", "No se permite mezclar datos de clase 'prueba' con datos oficiales."

        pib_dec = _validar_decimal_str(pib_obs.get("valor"), f"PIB {etiqueta}")
        pob_dec = _validar_decimal_str(pob_obs.get("valor"), "población")
        if pob_dec <= CERO:
            return None, None, "faltante", "Denominador de población cero o no positivo."

        with localcontext(CONTEXTO_DECIMAL):
            pc_dec = pib_dec * MILLON / pob_dec
            pc_str = _formatear_decimal_34(pc_dec)
        estado_final = "preliminar" if "preliminar" in {estado_pib, estado_pob} else "informado"
        return pc_dec, pc_str, estado_final, None

    for anio in anios:
        pc_real_dec_anio: dict[str, Decimal] = {}
        pc_nom_dec_anio: dict[str, Decimal] = {}
        registros_anio: dict[str, dict] = {}

        for territorio in TERRITORIOS:
            pob_obs = poblacion_idx.get((territorio, anio))
            pib_real_obs = niveles_pib.get(("real", territorio, anio))
            pib_nom_obs = niveles_pib.get(("nominal", territorio, anio))

            pc_real_dec, pc_real_str, estado_real, motivo_real = evaluar_per_capita(
                pib_real_obs, pob_obs, "real"
            )
            pc_nom_dec, pc_nom_str, estado_nom, motivo_nom = evaluar_per_capita(
                pib_nom_obs, pob_obs, "nominal"
            )

            if pc_real_dec is not None:
                pc_real_dec_anio[territorio] = pc_real_dec
            if pc_nom_dec is not None:
                pc_nom_dec_anio[territorio] = pc_nom_dec

            insumos = [
                obs_id
                for obs_id in (
                    pib_real_obs.get("id") if pib_real_obs else None,
                    pib_nom_obs.get("id") if pib_nom_obs else None,
                    pob_obs.get("id") if pob_obs else None,
                )
                if isinstance(obs_id, str) and obs_id
            ]

            registros_anio[territorio] = {
                "anio": anio,
                "territorio": territorio,
                "nombre_territorio": NOMBRES_TERRITORIOS[territorio],
                "poblacion": pob_obs.get("valor") if (pob_obs and pob_obs.get("estado") in _ESTADOS_DISPONIBLES) else None,
                "poblacion_clase": pob_obs.get("clase") if pob_obs else "no_disponible",
                "pib_real_millones": (
                    pib_real_obs.get("valor")
                    if (pib_real_obs and pib_real_obs.get("estado") in _ESTADOS_DISPONIBLES)
                    else None
                ),
                "pib_nominal_millones": (
                    pib_nom_obs.get("valor")
                    if (pib_nom_obs and pib_nom_obs.get("estado") in _ESTADOS_DISPONIBLES)
                    else None
                ),
                "pib_real_per_capita_clp": pc_real_str,
                "pib_nominal_per_capita_clp": pc_nom_str,
                "ratio_vs_chile_real": None,
                "ratio_vs_chile_nominal": None,
                "ranking_regional_real": None,
                "ranking_regional_nominal": None,
                "estado_real": estado_real,
                "estado_nominal": estado_nom,
                "motivo_real": motivo_real,
                "motivo_nominal": motivo_nom,
                "insumos": insumos,
            }

        pos_real, ranking_real_tabla = _calcular_ranking_regional(pc_real_dec_anio)
        pos_nom, ranking_nom_tabla = _calcular_ranking_regional(pc_nom_dec_anio)

        pc_cl_real = pc_real_dec_anio.get("CL")
        pc_cl_nom = pc_nom_dec_anio.get("CL")

        with localcontext(CONTEXTO_DECIMAL):
            for territorio in TERRITORIOS:
                fila = registros_anio[territorio]
                if territorio in pc_real_dec_anio and pc_cl_real is not None and pc_cl_real > CERO:
                    if territorio == "CL":
                        fila["ratio_vs_chile_real"] = "100"
                    else:
                        fila["ratio_vs_chile_real"] = _formatear_decimal_34(
                            pc_real_dec_anio[territorio] * CIEN / pc_cl_real
                        )
                if territorio in pc_nom_dec_anio and pc_cl_nom is not None and pc_cl_nom > CERO:
                    if territorio == "CL":
                        fila["ratio_vs_chile_nominal"] = "100"
                    else:
                        fila["ratio_vs_chile_nominal"] = _formatear_decimal_34(
                            pc_nom_dec_anio[territorio] * CIEN / pc_cl_nom
                        )
                if territorio != "CL":
                    fila["ranking_regional_real"] = pos_real.get(territorio)
                    fila["ranking_regional_nominal"] = pos_nom.get(territorio)
                series_planas.append(fila)

        sigma_real = _calcular_sigma_convergencia_anual(
            {reg: pc_real_dec_anio[reg] for reg in REGIONES if reg in pc_real_dec_anio}
        )
        sigma_nom = _calcular_sigma_convergencia_anual(
            {reg: pc_nom_dec_anio[reg] for reg in REGIONES if reg in pc_nom_dec_anio}
        )
        bloque_sigma = {
            "anio": anio,
            "regiones_esperadas": len(REGIONES),
            "formula_version": "sigma-convergencia-cv-poblacional-v1",
            "n_regiones": sigma_real["n_regiones"],
            "regiones_faltantes": sigma_real["regiones_faltantes"],
            "estado": sigma_real["estado"],
            "motivo": sigma_real["motivo"],
            "media_regional_real_clp": sigma_real["media_regional_clp"],
            "desviacion_estandar_real_clp": sigma_real["desviacion_estandar_clp"],
            "coeficiente_variacion_real": sigma_real["coeficiente_variacion"],
            "coeficiente_variacion_real_pct": sigma_real["coeficiente_variacion_pct"],
            "min_regional_real_clp": sigma_real["min_regional_clp"],
            "max_regional_real_clp": sigma_real["max_regional_clp"],
            "brecha_max_min_real": sigma_real["brecha_max_min"],
            "estado_nominal": sigma_nom["estado"],
            "media_regional_nominal_clp": sigma_nom["media_regional_clp"],
            "desviacion_estandar_nominal_clp": sigma_nom["desviacion_estandar_clp"],
            "coeficiente_variacion_nominal": sigma_nom["coeficiente_variacion"],
            "coeficiente_variacion_nominal_pct": sigma_nom["coeficiente_variacion_pct"],
        }
        sigma_lista.append(bloque_sigma)
        por_anio[str(anio)] = {
            "territorios": registros_anio,
            "ranking_regional_real": ranking_real_tabla,
            "ranking_regional_nominal": ranking_nom_tabla,
            "sigma_convergencia": bloque_sigma,
        }

    sigmas_validos = [s for s in sigma_lista if s["coeficiente_variacion_real"] is not None]
    if len(sigmas_validos) >= 2:
        primero = sigmas_validos[0]
        ultimo = sigmas_validos[-1]
        with localcontext(CONTEXTO_DECIMAL):
            cv_ini = Decimal(primero["coeficiente_variacion_real"])
            cv_fin = Decimal(ultimo["coeficiente_variacion_real"])
            delta_cv = cv_fin - cv_ini
            delta_pp = (cv_fin - cv_ini) * CIEN
        if delta_cv < CERO:
            tendencia = "convergencia"
        elif delta_cv > CERO:
            tendencia = "divergencia"
        else:
            tendencia = "estable"
        resumen_sigma = {
            "anio_inicial": primero["anio"],
            "anio_final": ultimo["anio"],
            "coeficiente_variacion_real_inicial": primero["coeficiente_variacion_real"],
            "coeficiente_variacion_real_final": ultimo["coeficiente_variacion_real"],
            "delta_coeficiente_variacion_real": _formatear_decimal_34(delta_cv),
            "delta_puntos_porcentuales": _formatear_decimal_34(delta_pp),
            "tendencia_descriptiva": tendencia,
            "nota_inferencia": (
                "La σ-convergencia mide descriptivamente la dispersión del PIB real per cápita "
                "entre las 16 regiones (CV = σ_poblacional / media); no implica causalidad por sí sola."
            ),
        }
    else:
        resumen_sigma = {
            "anio_inicial": sigmas_validos[0]["anio"] if sigmas_validos else None,
            "anio_final": sigmas_validos[-1]["anio"] if sigmas_validos else None,
            "coeficiente_variacion_real_inicial": (
                sigmas_validos[0]["coeficiente_variacion_real"] if sigmas_validos else None
            ),
            "coeficiente_variacion_real_final": (
                sigmas_validos[-1]["coeficiente_variacion_real"] if sigmas_validos else None
            ),
            "delta_coeficiente_variacion_real": None,
            "delta_puntos_porcentuales": None,
            "tendencia_descriptiva": "insuficiente",
            "nota_inferencia": "Se requieren al menos dos años completos (16 regiones) para comparar evolución de σ-convergencia.",
        }

    return {
        "metadatos": {
            "version_esquema": "pib-per-capita-nacional-regional-v1",
            "formula_version": "pib-per-capita-decimal34-v1",
            "precision_decimal": PRECISION_DECIMAL,
            "unidad_pib": UNIDAD_PIB,
            "unidad_poblacion": UNIDAD_POBLACION,
            "unidad_pib_per_capita": UNIDAD_PIB_PER_CAPITA,
            "anio_referencia_real": anio_referencia_real,
            "publicacion_pib": pub_pib_id,
            "publicacion_poblacion": pub_pob_id,
            "anios": anios,
            "territorios": list(TERRITORIOS),
            "escala_territorial": "nacional_y_regional",
            "imputacion_pib_comunal_prohibida": True,
            "advertencia_escala_territorial": ADVERTENCIA_ESCALA_PIB,
        },
        "advertencia_escala_territorial": ADVERTENCIA_ESCALA_PIB,
        "series": series_planas,
        "por_anio": por_anio,
        "sigma_convergencia": sigma_lista,
        "resumen_sigma_convergencia": resumen_sigma,
    }


def _decodificar_csv(contenido: bytes) -> str:
    for codificacion in ("utf-8-sig", "cp1252", "iso-8859-1"):
        try:
            return contenido.decode(codificacion)
        except UnicodeDecodeError:
            continue
    raise InePoblacionError("No se pudo decodificar el archivo CSV de población comunal.")


def _detectar_delimitador(linea_cabecera: str) -> str:
    candidatos = (";", ",", "\t")
    mejor = ","
    max_cols = 0
    for delim in candidatos:
        cols = len(next(csv.reader([linea_cabecera], delimiter=delim)))
        if cols > max_cols:
            max_cols = cols
            mejor = delim
    if max_cols < 2:
        raise InePoblacionError("No se pudo detectar un delimitador CSV válido (coma, punto y coma o tabulador).")
    return mejor


def _normalizar_cut(valor: object, linea_num: int) -> str:
    texto = re.sub(r"[\s.]+", "", str(valor or "").strip())
    if not texto.isdigit():
        raise InePoblacionError(f"Línea {linea_num}: código CUT comunal inválido ({valor!r}).")
    if len(texto) == 4:
        texto = f"0{texto}"
    if len(texto) != 5:
        raise InePoblacionError(
            f"Línea {linea_num}: código CUT debe tener 5 dígitos (o 4 sin cero inicial); se recibió {valor!r}."
        )
    region = texto[:2]
    if region not in REGIONES:
        raise InePoblacionError(
            f"Línea {linea_num}: prefijo regional de CUT inválido ({region!r} en {texto}); "
            "debe pertenecer a las regiones 01..16."
        )
    if texto[2] == "0" or texto[3:] == "00":
        raise InePoblacionError(f"Línea {linea_num}: estructura provincial/comunal de CUT inválida ({texto}).")
    return texto


def _parsear_poblacion_csv(valor_raw: object, linea_num: int, columna: str) -> tuple[str | None, str, str | None]:
    texto = str(valor_raw or "").strip()
    if texto.lower() in _VALORES_VACIOS_CSV:
        return None, "faltante", f"Valor faltante o no informado en columna '{columna}' (línea {linea_num})."

    limpio = texto.replace(" ", "").replace("\u00a0", "")
    if limpio.startswith("-"):
        raise InePoblacionError(
            f"Línea {linea_num}: población negativa no permitida en '{columna}' ({valor_raw!r})."
        )

    if _PATRON_MILES_PUNTO.fullmatch(limpio):
        normalizado = limpio.replace(".", "")
    elif _PATRON_MILES_COMA.fullmatch(limpio):
        normalizado = limpio.replace(",", "")
    elif _PATRON_DEC_CL.fullmatch(limpio):
        normalizado = limpio.replace(".", "").replace(",", ".")
    elif _PATRON_DEC_US.fullmatch(limpio):
        normalizado = limpio.replace(",", "")
    elif _PATRON_COMA_DEC.fullmatch(limpio):
        normalizado = limpio.replace(",", ".")
    elif _PATRON_DECIMAL_ESTRICTO.fullmatch(limpio):
        normalizado = limpio
    else:
        raise InePoblacionError(
            f"Línea {linea_num}: valor numérico inválido en '{columna}' ({valor_raw!r})."
        )

    with localcontext(CONTEXTO_DECIMAL):
        try:
            dec = Decimal(normalizado)
        except InvalidOperation:
            raise InePoblacionError(
                f"Línea {linea_num}: no se pudo convertir a Decimal en '{columna}' ({valor_raw!r})."
            ) from None
        if not dec.is_finite() or dec < CERO:
            raise InePoblacionError(
                f"Línea {linea_num}: población fuera de dominio en '{columna}' ({valor_raw!r})."
            )
        return _formatear_decimal_34(dec), "informado", None


def _info_administracion_municipal(cut: str, nombre_comuna: str) -> dict:
    if cut == CUT_ANTARTICA:
        return {
            "tiene_municipalidad_propia": False,
            "cut_municipalidad_administradora": CUT_CABO_DE_HORNOS,
            "administracion_municipal": (
                "Ilustre Municipalidad de Cabo de Hornos "
                "(agrupación comunal Cabo de Hornos y Antártica; comuna sin municipalidad propia)"
            ),
        }
    if cut == CUT_CABO_DE_HORNOS:
        return {
            "tiene_municipalidad_propia": True,
            "cut_municipalidad_administradora": CUT_CABO_DE_HORNOS,
            "administracion_municipal": (
                "Ilustre Municipalidad de Cabo de Hornos "
                "(administra las comunas de Cabo de Hornos 12201 y Antártica 12202)"
            ),
        }
    return {
        "tiene_municipalidad_propia": True,
        "cut_municipalidad_administradora": cut,
        "administracion_municipal": f"Municipalidad de {nombre_comuna}",
    }


def importar_poblacion_comunal_ine(contenido: bytes, nombre_archivo: str) -> dict:
    """Valida e importa una tabla CSV oficial INE de población comunal (hasta 346 comunas).

    Soporta formato largo (``cut, comuna, anio, poblacion``) y formato ancho
    (``cut, comuna, 2013, 2014, ...``), respeta la distinción entre 346 comunas
    y 345 administraciones municipales, no inventa cifras faltantes y bloquea
    columnas que imputen PIB comunal.
    """
    if not isinstance(contenido, (bytes, bytearray)) or not bytes(contenido).strip():
        raise InePoblacionError("El archivo CSV de población comunal está vacío.")
    raw_bytes = bytes(contenido)
    if len(raw_bytes) > MAX_BYTES:
        raise InePoblacionError("El archivo CSV de población comunal supera el tamaño máximo permitido.")
    if not isinstance(nombre_archivo, str) or not nombre_archivo.strip():
        raise InePoblacionError("Debe indicar un nombre de archivo válido.")

    texto = _decodificar_csv(raw_bytes)
    lineas_no_vacias = [linea for linea in texto.splitlines() if linea.strip()]
    if len(lineas_no_vacias) < 2:
        raise InePoblacionError("El CSV comunal debe contener cabecera y al menos una fila de datos.")

    delimitador = _detectar_delimitador(lineas_no_vacias[0])
    lector = csv.reader(io.StringIO(texto), delimiter=delimitador)
    cabecera_raw = next(lector, None)
    if not cabecera_raw:
        raise InePoblacionError("Cabecera CSV ausente.")

    cabeceras_norm = [_normalizar_cabecera(col) for col in cabecera_raw]
    for col_norm in cabeceras_norm:
        if "pib" in col_norm or "producto_interno_bruto" in col_norm:
            raise InePoblacionError(
                f"Columna prohibida detectada ('{col_norm}'). {ADVERTENCIA_ESCALA_PIB}"
            )

    mapa_cols: dict[str, int] = {}
    columnas_anio: list[tuple[int, int, str]] = []
    for idx, col_norm in enumerate(cabeceras_norm):
        if col_norm in _ALIAS_COLUMNAS_COMUNAL and _ALIAS_COLUMNAS_COMUNAL[col_norm] not in mapa_cols:
            mapa_cols[_ALIAS_COLUMNAS_COMUNAL[col_norm]] = idx
            continue
        match_anio = _PATRON_COLUMNA_ANIO.fullmatch(col_norm)
        if match_anio is not None:
            anio_col = int(match_anio.group(1))
            columnas_anio.append((anio_col, idx, cabecera_raw[idx].strip()))

    if "cut" not in mapa_cols or "comuna" not in mapa_cols:
        raise InePoblacionError(
            "El CSV comunal debe incluir columnas identificadoras de CUT ('cut'/'codigo_comuna') "
            "y nombre de comuna ('comuna'/'nombre_comuna')."
        )

    es_formato_largo = "anio" in mapa_cols and "poblacion" in mapa_cols
    es_formato_ancho = bool(columnas_anio) and not es_formato_largo
    if not es_formato_largo and not es_formato_ancho:
        raise InePoblacionError(
            "Estructura CSV no reconocida: proporcione formato largo ('anio' y 'poblacion') "
            "o formato ancho con columnas anuales (ej. 2013, 2014, ..., 2030)."
        )

    if es_formato_ancho:
        anios_vistos = [anio for anio, _, _ in columnas_anio]
        if len(set(anios_vistos)) != len(anios_vistos):
            raise InePoblacionError("El CSV comunal en formato ancho contiene años duplicados en la cabecera.")

    observaciones: list[dict] = []
    claves_vistas: set[tuple[str, int]] = set()
    comunas_info: dict[str, dict] = {}
    anios_set: set[int] = set()
    totales_regionales: dict[tuple[str, int], Decimal] = {}

    for linea_num, fila in enumerate(lector, start=2):
        if not any(celda.strip() for celda in fila):
            continue
        if len(fila) < len(cabeceras_norm):
            fila = list(fila) + [""] * (len(cabeceras_norm) - len(fila))

        cut = _normalizar_cut(fila[mapa_cols["cut"]], linea_num)
        nombre_comuna = fila[mapa_cols["comuna"]].strip()
        if not nombre_comuna:
            raise InePoblacionError(f"Línea {linea_num}: nombre de comuna vacío para CUT {cut}.")

        region = cut[:2]
        if "region" in mapa_cols:
            reg_raw = fila[mapa_cols["region"]].strip()
            if reg_raw:
                reg_digits = re.sub(r"\D+", "", reg_raw)
                if reg_digits:
                    reg_norm = f"{int(reg_digits):02d}"
                    if reg_norm != region:
                        raise InePoblacionError(
                            f"Línea {linea_num}: región informada ({reg_raw!r}) no coincide con prefijo CUT {cut} (región {region})."
                        )

        clase_fila = "oficial"
        if "clase" in mapa_cols:
            clase_raw = _normalizar_texto(fila[mapa_cols["clase"]])
            if clase_raw:
                if clase_raw not in _CLASES_COMUNAL_CANONICAS:
                    raise InePoblacionError(
                        f"Línea {linea_num}: clase de dato no reconocida ({fila[mapa_cols['clase']]!r})."
                    )
                clase_fila = _CLASES_COMUNAL_CANONICAS[clase_raw]

        corte_fila = fila[mapa_cols["corte"]].strip() if "corte" in mapa_cols and fila[mapa_cols["corte"]].strip() else None

        if cut not in comunas_info:
            admin = _info_administracion_municipal(cut, nombre_comuna)
            comunas_info[cut] = {
                "cut": cut,
                "comuna": nombre_comuna,
                "region": region,
                "nombre_region": NOMBRES_TERRITORIOS[region],
                **admin,
            }
            if len(comunas_info) > TOTAL_COMUNAS_CHILE:
                raise InePoblacionError(
                    f"El CSV contiene más de {TOTAL_COMUNAS_CHILE} códigos CUT distintos; verifique duplicados o códigos inválidos."
                )

        admin_comuna = comunas_info[cut]

        if es_formato_largo:
            anio_raw = fila[mapa_cols["anio"]].strip()
            if not anio_raw.isdigit():
                raise InePoblacionError(f"Línea {linea_num}: año inválido ({anio_raw!r}).")
            anio = int(anio_raw)
            if not (1990 <= anio <= 2100):
                raise InePoblacionError(f"Línea {linea_num}: año fuera de rango permitido ({anio}).")
            pares_anio = [(anio, fila[mapa_cols["poblacion"]], "poblacion")]
        else:
            pares_anio = [(anio_col, fila[idx], nombre_col) for anio_col, idx, nombre_col in columnas_anio]

        for anio, valor_raw, nombre_col in pares_anio:
            clave = (cut, anio)
            if clave in claves_vistas:
                raise InePoblacionError(
                    f"Línea {linea_num}: observación duplicada para CUT {cut} y año {anio}."
                )
            claves_vistas.add(clave)
            anios_set.add(anio)

            valor_str, estado_obs, motivo = _parsear_poblacion_csv(valor_raw, linea_num, nombre_col)
            if valor_str is not None:
                with localcontext(CONTEXTO_DECIMAL):
                    totales_regionales[(region, anio)] = (
                        totales_regionales.get((region, anio), CERO) + Decimal(valor_str)
                    )

            observaciones.append({
                "cut": cut,
                "comuna": admin_comuna["comuna"],
                "region": region,
                "nombre_region": NOMBRES_TERRITORIOS[region],
                "anio": anio,
                "metrica": "poblacion",
                "valor": valor_str,
                "unidad": UNIDAD_POBLACION,
                "estado": estado_obs,
                "clase": clase_fila if estado_obs == "informado" else "no_disponible",
                "corte": corte_fila,
                "motivo": motivo,
                "escala": "comunal",
                "tiene_municipalidad_propia": admin_comuna["tiene_municipalidad_propia"],
                "cut_municipalidad_administradora": admin_comuna["cut_municipalidad_administradora"],
            })

    if not observaciones:
        raise InePoblacionError("No se encontraron observaciones válidas en el CSV comunal.")

    observaciones.sort(key=lambda r: (r["anio"], r["cut"]))
    comunas_ordenadas = [comunas_info[cut] for cut in sorted(comunas_info)]
    municipalidades_distintas = sorted({c["cut_municipalidad_administradora"] for c in comunas_ordenadas})
    anios_ordenados = sorted(anios_set)

    totales_reg_salida: list[dict] = []
    for anio in anios_ordenados:
        for reg in REGIONES:
            if (reg, anio) in totales_regionales:
                comunas_reg = [c for c in comunas_ordenadas if c["region"] == reg]
                totales_reg_salida.append({
                    "anio": anio,
                    "region": reg,
                    "nombre_region": NOMBRES_TERRITORIOS[reg],
                    "comunas_presentes": len(comunas_reg),
                    "poblacion_sumada_comunas": _formatear_decimal_34(totales_regionales[(reg, anio)]),
                })

    return {
        "archivo": {
            "nombre": nombre_archivo.strip(),
            "sha256": sha256(raw_bytes).hexdigest(),
            "bytes": len(raw_bytes),
            "formato_detectado": "largo" if es_formato_largo else "ancho",
            "delimitador": delimitador,
        },
        "cobertura": {
            "comunas_importadas": len(comunas_ordenadas),
            "total_comunas_oficiales": TOTAL_COMUNAS_CHILE,
            "comunas_faltantes_vs_346": TOTAL_COMUNAS_CHILE - len(comunas_ordenadas),
            "cobertura_completa_346": len(comunas_ordenadas) == TOTAL_COMUNAS_CHILE,
            "municipalidades_representadas": len(municipalidades_distintas),
            "total_municipalidades_oficiales": TOTAL_MUNICIPALIDADES_CHILE,
            "incluye_antartica_12202": CUT_ANTARTICA in comunas_info,
            "incluye_cabo_de_hornos_12201": CUT_CABO_DE_HORNOS in comunas_info,
            "anios": anios_ordenados,
            "observaciones_esperadas": len(observaciones),
            "observaciones_disponibles": sum(o["valor"] is not None for o in observaciones),
            "observaciones_faltantes": sum(o["valor"] is None for o in observaciones),
        },
        "distincion_comuna_municipio": {
            "total_comunas_chile": TOTAL_COMUNAS_CHILE,
            "total_municipalidades_chile": TOTAL_MUNICIPALIDADES_CHILE,
            "cut_antartica": CUT_ANTARTICA,
            "cut_municipalidad_administradora_antartica": CUT_CABO_DE_HORNOS,
            "nota": NOTA_COMUNA_VS_MUNICIPIO,
        },
        "escala_territorial": "comunal",
        "imputacion_pib_comunal_prohibida": True,
        "advertencia_escala_territorial": ADVERTENCIA_ESCALA_PIB,
        "comunas": comunas_ordenadas,
        "observaciones": observaciones,
        "totales_regionales_sumados_desde_comunas": totales_reg_salida,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extracción oficial reproducible de población INE (17 series BDE, 2013–2030) "
            "y cálculo exacto de PIB per cápita nacional/regional."
        )
    )
    parser.add_argument(
        "--env",
        type=Path,
        default=None,
        help="Ruta opcional a archivo .env local fuera de Git.",
    )
    parser.add_argument(
        "--desde",
        type=date.fromisoformat,
        default=DESDE_PREDETERMINADO,
        help="Fecha inicial ISO para GetSeries (predeterminado: 2013-01-01).",
    )
    parser.add_argument(
        "--hasta",
        type=date.fromisoformat,
        default=HASTA_PREDETERMINADO,
        help="Fecha final ISO para GetSeries (predeterminado: 2030-12-31).",
    )
    parser.add_argument(
        "--insumos",
        type=Path,
        default=None,
        help="Directorio de insumos raw (en --reproducir es obligatorio).",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=Path("data/published/poblacion-ine-regiones.json"),
        help="Ruta del lote publicado de población (predeterminado: data/published/poblacion-ine-regiones.json).",
    )
    parser.add_argument(
        "--estado",
        choices=("aprobada", "prueba"),
        default="aprobada",
        help="Estado del lote publicado.",
    )
    parser.add_argument(
        "--reproducir",
        action="store_true",
        help="Reconstruye la salida bit-a-bit desde --insumos sin red ni credenciales.",
    )
    parser.add_argument(
        "--pib-entrada",
        type=Path,
        default=None,
        help="Opcional: ruta a pib-bde-api.json para emitir además PIB per cápita y σ-convergencia.",
    )
    parser.add_argument(
        "--salida-per-capita",
        type=Path,
        default=Path("data/published/pib-per-capita-nacional-regional.json"),
        help="Ruta de salida opcional para PIB per cápita cuando se entrega --pib-entrada.",
    )
    args = parser.parse_args(argv)

    try:
        if args.reproducir:
            if args.insumos is None:
                parser.exit(2, "En modo --reproducir debe indicar --insumos <directorio-raw>.\n")
            resumen = reproducir_desde_raw(args.insumos, salida_poblacion=args.salida)
        else:
            env_path = args.env
            if env_path is None and not any(
                os.environ.get(var, "").strip()
                for var in ("BCCH_API_TOKEN", "BCCH_API_USER", "BCCH_API_PASS")
            ):
                candidato_env = Path(".env")
                if candidato_env.is_file():
                    env_path = candidato_env
            credenciales = resolver_credenciales(os.environ, env_path=env_path)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            insumos_dir = args.insumos or (_RAIZ_REPO / "data" / "raw" / f"ine-poblacion-{stamp}")
            resumen = ejecutar_extraccion(
                credenciales,
                insumos_dir=insumos_dir,
                desde=args.desde,
                hasta=args.hasta,
                salida_poblacion=args.salida,
                estado_publicacion=args.estado,
            )

        if args.pib_entrada is not None:
            lote_pib = json.loads(args.pib_entrada.read_text(encoding="utf-8"))
            lote_pob = json.loads(args.salida.read_text(encoding="utf-8"))
            resultado_pc = calcular_pib_per_capita_nacional_y_regional(lote_pib, lote_pob)
            pc_bytes = (json.dumps(resultado_pc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            _escribir_salida_protegida(args.salida_per_capita, pc_bytes)
            print("per-capita:", args.salida_per_capita, f"anios={len(resultado_pc['metadatos']['anios'])}")
    except (InePoblacionError, BdeApiError) as error:
        parser.exit(1, f"{error}\n")
    except OSError:
        parser.exit(1, "No se pudo leer o escribir la evidencia local de población INE.\n")

    print(resumen["publicacion"]["id"], resumen["publicacion"]["cobertura"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
