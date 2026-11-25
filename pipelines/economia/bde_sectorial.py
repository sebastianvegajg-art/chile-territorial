"""Extractor oficial de las 416 series sectoriales regionales del BCCh (BDE).

Descubre desde ``SearchSeries(frequency=ANNUAL)`` las 416 series sectoriales de
Cuentas Nacionales referencia 2018 (16 regiones × 13 actividades canónicas ×
2 valoraciones: real y nominal), respetando literalmente los códigos del
catálogo (incluyendo sufijos ``.21.Z`` como los de Tarapacá), las descarga con
concurrencia cortés acotada (``ThreadPoolExecutor(max_workers=4)``), archiva
todos los JSON originales con manifiesto SHA-256 en ``data/raw/bde-sectorial-*/``
y publica ``data/published/pib-sectorial-16-regiones.json``.

Todos los indicadores estructurales (participaciones sectoriales nominales,
Cociente de Localización LQ, HHI 0–10.000, diversificación ``1 - HHI/10000``,
Índice de Krugman 0–1 y crecimiento real interanual) se calculan con
``Decimal`` reutilizando ``analytics.territorial.estructura`` y
``analytics.territorial.pib``.

Soporta ``--reproducir --insumos <dir>`` para reconstruir el JSON publicado
bit-a-bit sin red ni credenciales. Nunca expone credenciales en logs, errores,
manifiestos ni salidas.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

_RAIZ_REPO = Path(__file__).resolve().parents[2]
if str(_RAIZ_REPO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_REPO))

from analytics.territorial.estructura import (  # noqa: E402
    ESPECIALIZACION_VERSION,
    HHI_VERSION,
    KRUGMAN_VERSION,
    PARTICIPACION_SECTORIAL_VERSION,
    concentracion_hhi,
    especializacion,
    indice_krugman,
    participacion_sectorial,
)
from analytics.territorial.pib import (  # noqa: E402
    CRECIMIENTO_VERSION,
    crecimiento,
)
from pipelines.economia.bde_api import (  # noqa: E402
    ANIO_REFERENCIA_REAL,
    ENDPOINT,
    FUENTE,
    NOMBRES_TERRITORIOS,
    REGIONES,
    UNIDAD_NIVEL,
    VALORACIONES,
    BdeApiError,
    Credenciales,
    SerieCatalogo,
    _ESTADOS_FALTANTES_BDE,
    _cargar_json_bde,
    _factor_a_millones,
    _normalizar_texto,
    _parsear_fecha_corte,
    _parsear_fecha_observacion,
    contiene_credencial,
    descargar,
    descubrir_series_sectoriales,
    formatear_decimal,
    parsear_catalogo_anual,
    resolver_credenciales,
    sanear_mensaje,
)

INSTITUCION_BCCH = "Banco Central de Chile (BDE SI3 REST API)"
SERIES_TOTALES_ESPERADAS = 416
CLASIFICACION_SECTORIAL = "CCNN2018-13-actividades"
PERIMETRO_REGIONALIZADO = "vab_regionalizado_16_regiones"
MAX_WORKERS_DEFAULT = 4
MAX_WORKERS_LIMITE = 8
TIMEOUT_DEFAULT = 30

_CONTEXTO_DECIMAL = Context(prec=34, rounding=ROUND_HALF_EVEN)

ACTIVIDADES_CANONICAS: tuple[dict[str, str], ...] = (
    {"id": "agropecuario_silvicola", "nombre": "Agropecuario-silvícola"},
    {"id": "pesca", "nombre": "Pesca"},
    {"id": "mineria", "nombre": "Minería"},
    {"id": "industria_manufacturera", "nombre": "Industria manufacturera"},
    {"id": "electricidad_gas_agua", "nombre": "Electricidad, gas y agua"},
    {"id": "construccion", "nombre": "Construcción"},
    {"id": "comercio", "nombre": "Comercio"},
    {"id": "restaurantes_y_hoteles", "nombre": "Restaurantes y hoteles"},
    {"id": "transportes_y_comunicaciones", "nombre": "Transportes y comunicaciones"},
    {"id": "servicios_financieros_y_empresariales", "nombre": "Servicios financieros y empresariales"},
    {"id": "propiedad_de_vivienda", "nombre": "Propiedad de vivienda"},
    {"id": "servicios_personales", "nombre": "Servicios personales"},
    {"id": "administracion_publica", "nombre": "Administración pública"},
)

_ORDEN_ACTIVIDAD: dict[str, int] = {
    act["id"]: indice for indice, act in enumerate(ACTIVIDADES_CANONICAS)
}
_NOMBRE_ACTIVIDAD: dict[str, str] = {
    act["id"]: act["nombre"] for act in ACTIVIDADES_CANONICAS
}

# Mapeo por nombre canónico normalizado (incluyendo variantes oficiales del BCCh
# entre valoración real y nominal, ej. "Propiedad de vivienda" vs "Servicios de vivienda").
_ALIAS_ACTIVIDAD_CANONICA: dict[str, str] = {
    "agropecuario-silvicola": "agropecuario_silvicola",
    "agropecuario silvicola": "agropecuario_silvicola",
    "pesca": "pesca",
    "mineria": "mineria",
    "industria manufacturera": "industria_manufacturera",
    "electricidad gas y agua": "electricidad_gas_agua",
    "electricidad gas agua y gestion de desechos": "electricidad_gas_agua",
    "construccion": "construccion",
    "comercio": "comercio",
    "restaurantes y hoteles": "restaurantes_y_hoteles",
    "transportes y comunicaciones": "transportes_y_comunicaciones",
    "transporte informacion y comunicaciones": "transportes_y_comunicaciones",
    "servicios financieros y empresariales": "servicios_financieros_y_empresariales",
    "propiedad de vivienda": "propiedad_de_vivienda",
    "servicios de vivienda": "propiedad_de_vivienda",
    "servicios de vivienda e inmobiliarios": "propiedad_de_vivienda",
    "servicios personales": "servicios_personales",
    "administracion publica": "administracion_publica",
}

_PATRON_CORTE_METADATA_TITULO = re.compile(
    r",\s*(?:regi[oó]n\b|precios\s+corrientes\b|volumen\s+a\s+precios\b|base\s+2018\b|referencia\s+2018\b|series\s+empalmadas\b)",
    flags=re.IGNORECASE,
)


def _limpiar_texto_actividad(titulo_es: str) -> str:
    """Extrae y normaliza el nombre de actividad económica desde ``spanishTitle``."""
    sin_unidad = re.sub(r"\([^()]*\)\s*$", "", titulo_es).strip()
    # Formato estándar BCCh: "PIB <Actividad>, Región de ..., precios corrientes..."
    segmento = _PATRON_CORTE_METADATA_TITULO.split(sin_unidad, maxsplit=1)[0].strip()
    sin_prefijo = re.sub(
        r"^(?:producto\s+interno\s+bruto|pib)\s*[:,.\-]?\s*",
        "",
        segmento,
        flags=re.IGNORECASE,
    ).strip()

    # Formato alternativo posible: "PIB regional <Nombre>, <Actividad>, ..."
    norm_preliminar = _normalizar_texto(sin_prefijo)
    if norm_preliminar.startswith("regional "):
        partes = [p.strip() for p in sin_unidad.split(",") if p.strip()]
        if len(partes) >= 2:
            cola = ", ".join(partes[1:])
            sin_prefijo = _PATRON_CORTE_METADATA_TITULO.split(cola, maxsplit=1)[0].strip()

    norm = _normalizar_texto(sin_prefijo)
    norm = re.sub(r"[,;]+", " ", norm)
    norm = re.sub(r"\s+", " ", norm).strip()
    return norm


def resolver_actividad_canonica(serie: SerieCatalogo) -> str:
    """Resuelve el ``actividad_id`` canónico a partir del título normalizado de la serie."""
    clave_normalizada = _limpiar_texto_actividad(serie.titulo_es)
    actividad_id = _ALIAS_ACTIVIDAD_CANONICA.get(clave_normalizada)
    if actividad_id is None:
        # Errata verificada en el catálogo oficial BDE para Los Ríos nominal
        # (F035.PIB.FLU.N.CLP.2018.COM.Z.Z.14.0.A: "PIB Comercio, restaurantes y hotele, ..."),
        # mientras RH.Z.Z.14.0.A cubre "Restaurantes y hoteles".
        codigo_base = (serie.actividad_codigo or "").split(".", 1)[0].upper()
        if codigo_base == "COM" and clave_normalizada.startswith("comercio"):
            actividad_id = "comercio"
    if actividad_id is None:
        raise BdeApiError(
            f"SearchSeries: no se pudo mapear la actividad canónica para {serie.codigo} "
            f"(texto normalizado: {clave_normalizada!r})."
        )
    return actividad_id


def mapear_series_sectoriales(
    catalogo: dict[str, dict[str, Any]],
) -> tuple[dict[tuple[str, str, str], SerieCatalogo], list[tuple[str, SerieCatalogo]]]:
    """Descubre y valida las 416 series sectoriales regionales agrupadas por actividad canónica.

    Conserva literalmente los códigos de serie del catálogo (incluidos los
    sufijos ``.21.Z`` de Tarapacá y ``02.04.Z`` / ``09.21.Z``).
    """
    descubiertas = descubrir_series_sectoriales(catalogo)
    mapa: dict[tuple[str, str, str], SerieCatalogo] = {}

    for serie in descubiertas:
        actividad_id = resolver_actividad_canonica(serie)
        clave = (serie.territorio, actividad_id, serie.valoracion)
        if clave in mapa:
            raise BdeApiError(
                f"SearchSeries: serie sectorial duplicada para región {serie.territorio}, "
                f"actividad {actividad_id} ({serie.valoracion}): "
                f"{mapa[clave].codigo} y {serie.codigo}."
            )
        mapa[clave] = serie

    esperadas = {
        (region, act["id"], valoracion)
        for region in REGIONES
        for act in ACTIVIDADES_CANONICAS
        for valoracion in VALORACIONES
    }
    faltantes = sorted(esperadas.difference(mapa))
    if faltantes:
        muestra = ", ".join(f"{r}/{a}/{v}" for r, a, v in faltantes[:10])
        sufijo = "..." if len(faltantes) > 10 else ""
        raise BdeApiError(
            f"SearchSeries: faltan {len(faltantes)} de las {SERIES_TOTALES_ESPERADAS} "
            f"series sectoriales regionales ({muestra}{sufijo})."
        )

    ordenadas: list[tuple[str, SerieCatalogo]] = [
        (act["id"], mapa[(region, act["id"], valoracion)])
        for region in REGIONES
        for act in ACTIVIDADES_CANONICAS
        for valoracion in VALORACIONES
    ]
    return mapa, ordenadas


def _formatear_resultado_decimal(valor: str | None) -> str | None:
    if valor is None:
        return None
    return formatear_decimal(Decimal(valor))


def _parsear_observaciones_sectorial(
    payload: dict[str, Any],
    serie: SerieCatalogo,
    desde: date,
    hasta: date,
) -> tuple[dict[int, dict[str, Any]], Decimal, str]:
    bloque = payload.get("Series")
    if not isinstance(bloque, dict) or str(bloque.get("seriesId", "")).strip() != serie.codigo:
        raise BdeApiError(f"{serie.codigo}: identidad de serie incorrecta en GetSeries.")
    filas = bloque.get("Obs")
    if not isinstance(filas, list) or not filas:
        raise BdeApiError(f"{serie.codigo}: observaciones vacías o inválidas.")

    descrip_es = bloque.get("descripEsp") if isinstance(bloque.get("descripEsp"), str) else None
    factor, unidad_origen = _factor_a_millones(
        serie.titulo_es,
        descrip_es,
        serie.titulo_en,
        codigo=serie.codigo,
    )

    por_anio: dict[int, dict[str, Any]] = {}
    for fila in filas:
        if not isinstance(fila, dict):
            raise BdeApiError(f"{serie.codigo}: observación mal formada.")
        try:
            fecha_str = fila["indexDateString"]
            fecha = _parsear_fecha_observacion(fecha_str)
            estado_bde = fila["statusCode"]
            valor_crudo = fila.get("value")
        except (KeyError, TypeError, ValueError):
            raise BdeApiError(f"{serie.codigo}: observación mal formada.") from None

        if not desde <= fecha <= hasta:
            raise BdeApiError(f"{serie.codigo}: período fuera del rango solicitado.")
        if fecha.year in por_anio:
            raise BdeApiError(f"{serie.codigo}: año repetido ({fecha.year}).")
        if not isinstance(estado_bde, str) or not estado_bde.strip():
            raise BdeApiError(f"{serie.codigo}: statusCode inválido.")

        estado_limpio = estado_bde.strip()
        if estado_limpio == "OK":
            if valor_crudo is None:
                raise BdeApiError(f"{serie.codigo}: observación OK sin valor numérico.")
            try:
                valor_dec = Decimal(str(valor_crudo).strip())
            except InvalidOperation:
                raise BdeApiError(f"{serie.codigo}: observación OK con valor no numérico.") from None
            if not valor_dec.is_finite():
                raise BdeApiError(f"{serie.codigo}: observación OK con valor no finito.")
            valor_millones_dec = valor_dec * factor
            por_anio[fecha.year] = {
                "fecha_origen": fecha_str,
                "valor_decimal": valor_millones_dec,
                "valor": formatear_decimal(valor_millones_dec),
                "estado": "informado",
                "clase": "oficial",
                "status_bde": estado_limpio,
            }
        elif estado_limpio.upper() in _ESTADOS_FALTANTES_BDE:
            por_anio[fecha.year] = {
                "fecha_origen": fecha_str,
                "valor_decimal": None,
                "valor": None,
                "estado": "faltante",
                "clase": "no_disponible",
                "status_bde": estado_limpio,
            }
        else:
            raise BdeApiError(f"{serie.codigo}: statusCode BDE no reconocido ({estado_limpio}).")

    return por_anio, factor, unidad_origen


def _construir_obs_nominal_estructura(
    *,
    publicacion_id: str,
    territorio: str,
    anio: int,
    actividad: str,
    valor: str | None,
    estado: str,
    clase: str,
) -> dict[str, Any]:
    return {
        "id": f"{publicacion_id}.{territorio}.{anio}.va.{actividad}",
        "publicacion": publicacion_id,
        "territorio": territorio,
        "anio": anio,
        "metrica": "valor_agregado",
        "valoracion": "nominal",
        "valor": valor,
        "unidad": UNIDAD_NIVEL,
        "anio_referencia": None,
        "actividad": actividad,
        "clasificacion": CLASIFICACION_SECTORIAL,
        "perimetro": PERIMETRO_REGIONALIZADO,
        "estado": estado,
        "clase": clase,
    }


def _construir_obs_real_crecimiento(
    *,
    publicacion_id: str,
    territorio: str,
    anio: int,
    actividad_id: str,
    dato: dict[str, Any] | None,
) -> dict[str, Any]:
    estado = dato["estado"] if dato is not None else "faltante"
    clase = dato["clase"] if dato is not None else "no_disponible"
    valor = dato["valor"] if dato is not None else None
    return {
        "id": f"{publicacion_id}.{territorio}.{anio}.nivel.real.{actividad_id}",
        "publicacion": publicacion_id,
        "territorio": territorio,
        "anio": anio,
        "metrica": "nivel",
        "valoracion": "real",
        "valor": valor,
        "unidad": UNIDAD_NIVEL,
        "anio_referencia": ANIO_REFERENCIA_REAL,
        "estado": estado,
        "clase": clase,
    }


def _construir_ranking(
    filas: list[tuple[Decimal, str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Ordena descendentemente por valor decimal; empates comparten posición."""
    ordenadas = sorted(filas, key=lambda item: item[1])
    ordenadas.sort(key=lambda item: item[0], reverse=True)

    ranking: list[dict[str, Any]] = []
    valor_anterior: Decimal | None = None
    posicion = 0
    for idx, (valor_dec, _territorio, datos) in enumerate(ordenadas, start=1):
        if valor_dec != valor_anterior:
            posicion = idx
        ranking.append({"posicion": posicion, **datos})
        valor_anterior = valor_dec
    return ranking


def normalizar_sectorial_16_regiones(
    catalogo_bytes: bytes,
    series_bytes: dict[str, bytes],
    extraido_en: str,
    desde: date,
    hasta: date,
    estado_publicacion: str = "aprobada",
) -> dict[str, Any]:
    """Normaliza el catálogo anual y las 416 respuestas ``GetSeries`` al corte publicado."""
    if estado_publicacion not in {"aprobada", "prueba"}:
        raise BdeApiError("estado_publicacion debe ser 'aprobada' o 'prueba'.")
    if desde > hasta:
        raise BdeApiError("El inicio del período debe preceder al final.")
    if desde.year < 2013:
        raise BdeApiError("La extracción sectorial regional requiere --desde >= 2013-01-01.")

    try:
        payload_catalogo = _cargar_json_bde(catalogo_bytes, parse_float=str)
    except (ValueError, UnicodeError):
        raise BdeApiError("Catálogo anual JSON inválido.") from None

    catalogo = parsear_catalogo_anual(payload_catalogo)
    mapa_series, series_ordenadas = mapear_series_sectoriales(catalogo)

    faltan_bytes = [
        serie.codigo for _act_id, serie in series_ordenadas if serie.codigo not in series_bytes
    ]
    if faltan_bytes:
        muestra = ", ".join(faltan_bytes[:5])
        sufijo = "..." if len(faltan_bytes) > 5 else ""
        raise BdeApiError(
            f"Faltan {len(faltan_bytes)} insumos GetSeries sectoriales ({muestra}{sufijo})."
        )

    sha_catalogo = sha256(catalogo_bytes).hexdigest()
    hashes_series = {
        serie.codigo: sha256(series_bytes[serie.codigo]).hexdigest()
        for _act_id, serie in series_ordenadas
    }
    sha_codigos = sha256(
        "\n".join(sorted(serie.codigo for _act_id, serie in series_ordenadas)).encode("utf-8")
    ).hexdigest()
    cadena_huella = sha_catalogo + "".join(
        hashes_series[serie.codigo] for _act_id, serie in series_ordenadas
    )
    huella = sha256(cadena_huella.encode("utf-8")).hexdigest()[:16]
    publicacion_id = f"bcch-bde-sectorial-{extraido_en[:10]}-{huella}"

    datos_parseados: dict[tuple[str, str, str], dict[int, dict[str, Any]]] = {}
    anios_disponibles: set[int] = set()
    cortes_detectados: list[str] = []

    for act_id, serie in series_ordenadas:
        raw_serie = series_bytes[serie.codigo]
        try:
            payload_serie = _cargar_json_bde(raw_serie, parse_float=str)
        except (ValueError, UnicodeError):
            raise BdeApiError(f"{serie.codigo}: cuerpo JSON de GetSeries inválido.") from None

        por_anio, _factor, _unidad_origen = _parsear_observaciones_sectorial(
            payload_serie, serie, desde, hasta
        )
        datos_parseados[(serie.territorio, act_id, serie.valoracion)] = por_anio
        anios_disponibles.update(anio for anio in por_anio if desde.year <= anio <= hasta.year)
        corte = _parsear_fecha_corte(serie.actualizada_en)
        if corte is not None:
            cortes_detectados.append(corte)

    if not anios_disponibles:
        raise BdeApiError("Las series sectoriales no contienen observaciones en el período solicitado.")

    anio_inicio = max(2013, desde.year)
    anio_fin = max(anios_disponibles)
    anios = list(range(anio_inicio, anio_fin + 1))

    # Observaciones reales preconstruidas para calcular crecimiento real interanual exacto.
    obs_reales: dict[tuple[str, str, int], dict[str, Any]] = {}
    for region in REGIONES:
        for act in ACTIVIDADES_CANONICAS:
            act_id = act["id"]
            mapa_real = datos_parseados[(region, act_id, "real")]
            for anio in anios:
                obs_reales[(region, act_id, anio)] = _construir_obs_real_crecimiento(
                    publicacion_id=publicacion_id,
                    territorio=region,
                    anio=anio,
                    actividad_id=act_id,
                    dato=mapa_real.get(anio),
                )

    por_anio_salida: dict[str, Any] = {}
    for anio in anios:
        # 1) Observaciones nominales por región y actividad
        obs_reg_por_region: dict[str, list[dict[str, Any]]] = {}
        obs_reg_mapa: dict[tuple[str, str], dict[str, Any]] = {}
        obs_reg_total: dict[str, dict[str, Any]] = {}
        totales_reg_str: dict[str, str | None] = {}

        for region in REGIONES:
            lista_reg: list[dict[str, Any]] = []
            suma_reg = Decimal("0")
            completa_reg = True
            for act in ACTIVIDADES_CANONICAS:
                act_id = act["id"]
                dato_nom = datos_parseados[(region, act_id, "nominal")].get(anio)
                valor_nom = dato_nom["valor"] if dato_nom is not None else None
                estado_nom = dato_nom["estado"] if dato_nom is not None else "faltante"
                clase_nom = dato_nom["clase"] if dato_nom is not None else "no_disponible"

                obs_act = _construir_obs_nominal_estructura(
                    publicacion_id=publicacion_id,
                    territorio=region,
                    anio=anio,
                    actividad=act_id,
                    valor=valor_nom,
                    estado=estado_nom,
                    clase=clase_nom,
                )
                lista_reg.append(obs_act)
                obs_reg_mapa[(region, act_id)] = obs_act

                if dato_nom is not None and dato_nom["valor_decimal"] is not None:
                    suma_reg += dato_nom["valor_decimal"]
                else:
                    completa_reg = False

            obs_reg_por_region[region] = lista_reg
            total_reg_val = formatear_decimal(suma_reg) if completa_reg else None
            totales_reg_str[region] = total_reg_val
            obs_reg_total[region] = _construir_obs_nominal_estructura(
                publicacion_id=publicacion_id,
                territorio=region,
                anio=anio,
                actividad="total",
                valor=total_reg_val,
                estado="informado" if completa_reg else "faltante",
                clase="oficial" if completa_reg else "no_disponible",
            )

        # 2) Total regionalizado por actividad canónica (suma exacta de las 16 regiones)
        total_regionalizado_por_act: dict[str, str | None] = {}
        obs_nac_actividades: list[dict[str, Any]] = []
        obs_nac_mapa: dict[str, dict[str, Any]] = {}
        suma_nacional_reg = Decimal("0")
        nacional_completo = True

        for act in ACTIVIDADES_CANONICAS:
            act_id = act["id"]
            suma_act = Decimal("0")
            completa_act = True
            for region in REGIONES:
                dato_nom = datos_parseados[(region, act_id, "nominal")].get(anio)
                if dato_nom is not None and dato_nom["valor_decimal"] is not None:
                    suma_act += dato_nom["valor_decimal"]
                else:
                    completa_act = False

            val_act_nac = formatear_decimal(suma_act) if completa_act else None
            total_regionalizado_por_act[act_id] = val_act_nac
            if completa_act:
                suma_nacional_reg += suma_act
            else:
                nacional_completo = False

            obs_nac_act = _construir_obs_nominal_estructura(
                publicacion_id=publicacion_id,
                territorio="CL",
                anio=anio,
                actividad=act_id,
                valor=val_act_nac,
                estado="informado" if completa_act else "faltante",
                clase="oficial" if completa_act else "no_disponible",
            )
            obs_nac_actividades.append(obs_nac_act)
            obs_nac_mapa[act_id] = obs_nac_act

        total_nacional_reg_val = formatear_decimal(suma_nacional_reg) if nacional_completo else None
        obs_nac_total = _construir_obs_nominal_estructura(
            publicacion_id=publicacion_id,
            territorio="CL",
            anio=anio,
            actividad="total",
            valor=total_nacional_reg_val,
            estado="informado" if nacional_completo else "faltante",
            clase="oficial" if nacional_completo else "no_disponible",
        )

        # 3) Indicadores estructurales por región
        regiones_salida: dict[str, Any] = {}
        candidatas_hhi: list[tuple[Decimal, str, dict[str, Any]]] = []
        candidatas_krugman: list[tuple[Decimal, str, dict[str, Any]]] = []

        for region in REGIONES:
            res_hhi = concentracion_hhi(obs_reg_por_region[region])
            hhi_str = _formatear_resultado_decimal(res_hhi.valor)
            if res_hhi.valor is not None:
                with localcontext(_CONTEXTO_DECIMAL):
                    div_dec = Decimal("1") - (Decimal(res_hhi.valor) / Decimal("10000"))
                diversificacion_str: str | None = formatear_decimal(div_dec)
            else:
                diversificacion_str = None

            res_krugman = indice_krugman(obs_reg_por_region[region], obs_nac_actividades)
            krugman_str = _formatear_resultado_decimal(res_krugman.valor)

            actividades_reg: list[dict[str, Any]] = []
            mejor_nominal: tuple[Decimal, int, dict[str, Any]] | None = None
            mejor_lq: tuple[Decimal, int, dict[str, Any]] | None = None

            for idx_act, act in enumerate(ACTIVIDADES_CANONICAS):
                act_id = act["id"]
                nombre_act = act["nombre"]
                serie_nom = mapa_series[(region, act_id, "nominal")]
                serie_real = mapa_series[(region, act_id, "real")]

                dato_nom = datos_parseados[(region, act_id, "nominal")].get(anio)
                dato_real = datos_parseados[(region, act_id, "real")].get(anio)

                nom_str = dato_nom["valor"] if dato_nom is not None else None
                real_str = dato_real["valor"] if dato_real is not None else None

                res_part = participacion_sectorial(obs_reg_mapa[(region, act_id)], obs_reg_total[region])
                part_str = _formatear_resultado_decimal(res_part.valor)

                if anio == 2013:
                    crec_str: str | None = None
                else:
                    res_crec = crecimiento(
                        obs_reales[(region, act_id, anio)],
                        obs_reales.get((region, act_id, anio - 1)),
                    )
                    crec_str = _formatear_resultado_decimal(res_crec.valor)

                res_lq = especializacion(
                    obs_reg_mapa[(region, act_id)],
                    obs_reg_total[region],
                    obs_nac_mapa[act_id],
                    obs_nac_total,
                )
                lq_str = _formatear_resultado_decimal(res_lq.valor)

                fila_act = {
                    "actividad_id": act_id,
                    "nombre": nombre_act,
                    "serie_bde_nominal": serie_nom.codigo,
                    "serie_bde_real": serie_real.codigo,
                    "nominal_millones": nom_str,
                    "real_millones": real_str,
                    "participacion_nominal_pct": part_str,
                    "crecimiento_real_pct": crec_str,
                    "lq_especializacion": lq_str,
                }
                actividades_reg.append(fila_act)

                if nom_str is not None:
                    nom_dec = Decimal(nom_str)
                    if mejor_nominal is None or nom_dec > mejor_nominal[0]:
                        mejor_nominal = (
                            nom_dec,
                            idx_act,
                            {
                                "actividad_id": act_id,
                                "nombre": nombre_act,
                                "nominal_millones": nom_str,
                                "participacion_nominal_pct": part_str,
                            },
                        )

                if lq_str is not None:
                    lq_dec = Decimal(lq_str)
                    if mejor_lq is None or lq_dec > mejor_lq[0]:
                        mejor_lq = (
                            lq_dec,
                            idx_act,
                            {
                                "actividad_id": act_id,
                                "nombre": nombre_act,
                                "lq_especializacion": lq_str,
                                "participacion_nominal_pct": part_str,
                            },
                        )

            nombre_reg = NOMBRES_TERRITORIOS[region]
            regiones_salida[region] = {
                "nombre": nombre_reg,
                "total_vab_nominal_millones": totales_reg_str[region],
                "hhi": hhi_str,
                "diversificacion": diversificacion_str,
                "indice_krugman": krugman_str,
                "sector_principal": mejor_nominal[2] if mejor_nominal is not None else None,
                "sector_mas_especializado_lq": mejor_lq[2] if mejor_lq is not None else None,
                "actividades": actividades_reg,
            }

            if hhi_str is not None and diversificacion_str is not None:
                candidatas_hhi.append((
                    Decimal(hhi_str),
                    region,
                    {
                        "territorio": region,
                        "nombre": nombre_reg,
                        "hhi": hhi_str,
                        "diversificacion": diversificacion_str,
                    },
                ))
            if krugman_str is not None:
                candidatas_krugman.append((
                    Decimal(krugman_str),
                    region,
                    {
                        "territorio": region,
                        "nombre": nombre_reg,
                        "indice_krugman": krugman_str,
                    },
                ))

        por_anio_salida[str(anio)] = {
            "total_regionalizado_actividades_nominal": {
                "unidad": UNIDAD_NIVEL,
                "perimetro": PERIMETRO_REGIONALIZADO,
                "nota": (
                    "Suma de las 16 regiones por actividad canónica a precios corrientes "
                    "(millones CLP). Excluye explícitamente partidas extrarregionales e impuestos "
                    "sobre los productos para conservar igual perímetro en LQ e índice de Krugman."
                ),
                "total_millones": total_nacional_reg_val,
                "por_actividad": total_regionalizado_por_act,
            },
            "regiones": regiones_salida,
            "ranking_hhi": _construir_ranking(candidatas_hhi),
            "ranking_krugman": _construir_ranking(candidatas_krugman),
        }

    actualizado_en = max(cortes_detectados) if cortes_detectados else None
    notas = [
        (
            f"Cobertura verificada de {SERIES_TOTALES_ESPERADAS} series sectoriales regionales "
            f"(16 regiones × 13 actividades CCNN2018 × 2 valoraciones) descubiertas literalmente "
            f"en SearchSeries(ANNUAL), preservando códigos especiales como sufijos .21.Z en Tarapacá."
        ),
        (
            "Conversión exacta con Decimal a millones CLP preservando la precisión completa "
            "entregada por GetSeries."
        ),
        (
            "Los indicadores estructurales (participación nominal, LQ, HHI, diversificación e "
            "índice de Krugman) se calculan exclusivamente en valoración nominal (precios corrientes), "
            "respetando la no aditividad de volúmenes reales encadenados."
        ),
        (
            "El denominador nacional de LQ y Krugman corresponde a total_regionalizado_actividades_nominal "
            "(suma de las 16 regiones por actividad), excluyendo partidas extrarregionales para mantener "
            "igual perímetro contable entre región y referencia nacional."
        ),
        (
            "El crecimiento real sectorial interanual es nulo en 2013 por inicio de la serie sectorial "
            "en 2013 y en cualquier observación sin año actual o previo informado."
        ),
    ]

    return {
        "publicacion": {
            "id": publicacion_id,
            "fecha": extraido_en,
            "estado": estado_publicacion,
            "fuente": FUENTE,
            "series_totales": SERIES_TOTALES_ESPERADAS,
            "anios": anios,
            "notas": notas,
        },
        "actividades_canonicas": [dict(act) for act in ACTIVIDADES_CANONICAS],
        "por_anio": por_anio_salida,
        "fuente_trazabilidad": {
            "institucion": INSTITUCION_BCCH,
            "endpoint": ENDPOINT,
            "funciones": ["SearchSeries", "GetSeries"],
            "series_verificadas": SERIES_TOTALES_ESPERADAS,
            "regiones": len(REGIONES),
            "actividades_por_region": len(ACTIVIDADES_CANONICAS),
            "valoraciones": len(VALORACIONES),
            "actualizado_en": actualizado_en,
            "extraido_en": extraido_en,
            "catalogo_anual_sha256": sha_catalogo,
            "codigos_sectoriales_sha256": sha_codigos,
            "formulas": {
                "participacion_sectorial": PARTICIPACION_SECTORIAL_VERSION,
                "especializacion_lq": ESPECIALIZACION_VERSION,
                "concentracion_hhi": HHI_VERSION,
                "indice_krugman": KRUGMAN_VERSION,
                "crecimiento_real": CRECIMIENTO_VERSION,
                "diversificacion": "1 - HHI/10000",
            },
        },
    }


def descargar_series_sectoriales(
    credenciales: Credenciales,
    series_ordenadas: list[tuple[str, SerieCatalogo]],
    desde: date,
    hasta: date,
    *,
    max_workers: int = MAX_WORKERS_DEFAULT,
    timeout: int = TIMEOUT_DEFAULT,
) -> dict[str, bytes]:
    """Descarga las 416 series con concurrencia cortés acotada y sin fugas de credenciales."""
    if isinstance(max_workers, bool) or not isinstance(max_workers, int) or not (1 <= max_workers <= MAX_WORKERS_LIMITE):
        raise BdeApiError(f"max_workers debe ser un entero entre 1 y {MAX_WORKERS_LIMITE}.")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not (1 <= timeout <= 120):
        raise BdeApiError("timeout debe ser un entero entre 1 y 120 segundos.")

    firstdate = desde.isoformat()
    lastdate = hasta.isoformat()
    resultados: dict[str, bytes] = {}
    errores: list[str] = []

    def _descargar_una(serie: SerieCatalogo) -> tuple[str, bytes]:
        raw_bytes, _payload = descargar(
            credenciales,
            "GetSeries",
            timeout=timeout,
            timeseries=serie.codigo,
            firstdate=firstdate,
            lastdate=lastdate,
        )
        return serie.codigo, raw_bytes

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futuros = {
            pool.submit(_descargar_una, serie): serie.codigo
            for _act_id, serie in series_ordenadas
        }
        for futuro in as_completed(futuros):
            codigo = futuros[futuro]
            try:
                cod_ok, raw = futuro.result()
                resultados[cod_ok] = raw
            except BdeApiError as error:
                errores.append(f"{codigo}: {sanear_mensaje(str(error), credenciales)}")
            except Exception:
                errores.append(f"{codigo}: error inesperado durante descarga.")

    if errores:
        errores.sort()
        muestra = "; ".join(errores[:5])
        sufijo = f" (y {len(errores) - 5} más)" if len(errores) > 5 else ""
        raise BdeApiError(
            f"Falló la descarga de {len(errores)} de {len(series_ordenadas)} series sectoriales: {muestra}{sufijo}."
        )

    return {serie.codigo: resultados[serie.codigo] for _act_id, serie in series_ordenadas}


def _escribir_salida_protegida(
    ruta: Path,
    contenido: bytes,
    credenciales: Credenciales | None = None,
    *,
    sobrescribir: bool = False,
) -> None:
    if credenciales is not None and contiene_credencial(contenido, credenciales):
        raise BdeApiError("Se bloqueó la escritura: se detectó una credencial en el contenido de salida.")
    if ruta.exists():
        if ruta.read_bytes() == contenido:
            return
        if not sobrescribir:
            raise BdeApiError(
                f"La salida {ruta} ya pertenece a otro lote. Indica otra ruta o usa --sobrescribir."
            )
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)


def _verificar_manifiesto_sectorial(insumos_dir: Path) -> tuple[dict[str, Any], bytes, dict[str, bytes]]:
    ruta_manifiesto = insumos_dir / "manifiesto.json"
    if not ruta_manifiesto.is_file():
        raise BdeApiError(f"No se encontró manifiesto.json en {insumos_dir}.")
    try:
        manifiesto = json.loads(ruta_manifiesto.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise BdeApiError("No se pudo leer manifiesto.json de insumos sectoriales.") from None

    if not isinstance(manifiesto, dict) or not isinstance(manifiesto.get("artefactos"), list):
        raise BdeApiError("Estructura inválida en manifiesto.json.")

    raiz_resuelta = insumos_dir.resolve()
    catalogo_bytes: bytes | None = None
    series_bytes: dict[str, bytes] = {}

    for entrada in manifiesto["artefactos"]:
        if not isinstance(entrada, dict):
            raise BdeApiError("Entrada inválida en manifiesto.json.")
        relativo = entrada.get("archivo")
        esperado = entrada.get("sha256")
        if not isinstance(relativo, str) or not isinstance(esperado, str):
            raise BdeApiError("Metadatos incompletos en manifiesto.json.")
        ruta_archivo = (insumos_dir / relativo).resolve()
        if raiz_resuelta not in ruta_archivo.parents:
            raise BdeApiError("Ruta de artefacto fuera del directorio de insumos.")
        if not ruta_archivo.is_file():
            raise BdeApiError(f"Falta archivo de insumo declarado en manifiesto: {relativo}.")
        crudo = ruta_archivo.read_bytes()
        if sha256(crudo).hexdigest() != esperado:
            raise BdeApiError(f"Integridad SHA-256 fallida para {relativo}.")
        if entrada.get("id") == "bde-sectorial-catalogo-anual":
            catalogo_bytes = crudo
        elif isinstance(entrada.get("serie_bde"), str):
            series_bytes[entrada["serie_bde"]] = crudo

    if catalogo_bytes is None:
        raise BdeApiError("El manifiesto no incluye catalogo-anual.json.")
    return manifiesto, catalogo_bytes, series_bytes


def ejecutar_extraccion_sectorial(
    credenciales: Credenciales,
    insumos_dir: Path,
    salida: Path,
    desde: date,
    hasta: date,
    *,
    max_workers: int = MAX_WORKERS_DEFAULT,
    timeout: int = TIMEOUT_DEFAULT,
    estado_publicacion: str = "aprobada",
    sobrescribir: bool = False,
) -> dict[str, Any]:
    """Ejecuta la extracción completa de las 416 series, archiva raw y publica JSON."""
    if desde > hasta:
        raise BdeApiError("El inicio del período debe preceder al final.")
    if desde.year < 2013:
        raise BdeApiError("La extracción sectorial requiere --desde >= 2013-01-01.")
    if insumos_dir.exists():
        raise BdeApiError(f"El directorio de insumos ya existe: {insumos_dir}.")

    extraido_en = datetime.now(timezone.utc).isoformat(timespec="seconds")
    catalogo_bytes, payload_catalogo = descargar(
        credenciales,
        "SearchSeries",
        timeout=timeout,
        frequency="ANNUAL",
    )
    catalogo = parsear_catalogo_anual(payload_catalogo)
    _mapa_series, series_ordenadas = mapear_series_sectoriales(catalogo)

    series_bytes = descargar_series_sectoriales(
        credenciales,
        series_ordenadas,
        desde,
        hasta,
        max_workers=max_workers,
        timeout=timeout,
    )

    lote = normalizar_sectorial_16_regiones(
        catalogo_bytes,
        series_bytes,
        extraido_en,
        desde,
        hasta,
        estado_publicacion=estado_publicacion,
    )

    artefactos_raw: list[dict[str, Any]] = [
        {
            "id": "bde-sectorial-catalogo-anual",
            "archivo": "catalogo-anual.json",
            "sha256": sha256(catalogo_bytes).hexdigest(),
            "bytes": len(catalogo_bytes),
            "serie_bde": None,
            "territorio": None,
            "actividad_id": None,
            "valoracion": None,
            "corte": None,
        }
    ]
    for act_id, serie in series_ordenadas:
        raw_serie = series_bytes[serie.codigo]
        artefactos_raw.append({
            "id": f"bde-sectorial-{serie.codigo}",
            "archivo": f"series/{serie.codigo}.json",
            "sha256": sha256(raw_serie).hexdigest(),
            "bytes": len(raw_serie),
            "serie_bde": serie.codigo,
            "territorio": serie.territorio,
            "actividad_id": act_id,
            "valoracion": serie.valoracion,
            "corte": _parsear_fecha_corte(serie.actualizada_en),
        })

    manifiesto = {
        "version_esquema": "bde-sectorial-raw-v1",
        "fuente": ENDPOINT,
        "extraido_en": extraido_en,
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "estado_publicacion": estado_publicacion,
        "series_catalogo_anual": len(catalogo),
        "series_sectoriales_total": len(series_ordenadas),
        "artefactos": artefactos_raw,
    }

    manifiesto_bytes = (json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    salida_bytes = (json.dumps(lote, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    if contiene_credencial(manifiesto_bytes, credenciales):
        raise BdeApiError("Se bloqueó la escritura: credencial detectada en el manifiesto.")
    if contiene_credencial(salida_bytes, credenciales):
        raise BdeApiError("Se bloqueó la escritura: credencial detectada en la salida publicada.")
    if salida.exists() and not sobrescribir and salida.read_bytes() != salida_bytes:
        raise BdeApiError(
            f"La salida {salida} ya pertenece a otro lote. Indica otra ruta o usa --sobrescribir."
        )

    insumos_dir.parent.mkdir(parents=True, exist_ok=True)
    insumos_dir.mkdir(mode=0o700, exist_ok=False)
    (insumos_dir / "catalogo-anual.json").write_bytes(catalogo_bytes)
    series_dir = insumos_dir / "series"
    series_dir.mkdir(parents=True, exist_ok=True)
    for _act_id, serie in series_ordenadas:
        (series_dir / f"{serie.codigo}.json").write_bytes(series_bytes[serie.codigo])
    (insumos_dir / "manifiesto.json").write_bytes(manifiesto_bytes)

    _escribir_salida_protegida(salida, salida_bytes, credenciales, sobrescribir=sobrescribir)

    return {
        "insumos": str(insumos_dir),
        "salida": str(salida),
        "publicacion": lote["publicacion"],
        "fuente_trazabilidad": lote["fuente_trazabilidad"],
    }


def reproducir_sectorial_desde_raw(
    insumos_dir: Path,
    salida: Path,
    *,
    sobrescribir: bool = False,
) -> dict[str, Any]:
    """Reconstruye ``pib-sectorial-16-regiones.json`` bit-a-bit sin red ni credenciales."""
    manifiesto, catalogo_bytes, series_bytes = _verificar_manifiesto_sectorial(insumos_dir)
    extraido_en = manifiesto["extraido_en"]
    desde = date.fromisoformat(manifiesto["desde"])
    hasta = date.fromisoformat(manifiesto["hasta"])
    estado_publicacion = manifiesto.get("estado_publicacion", "aprobada")

    lote = normalizar_sectorial_16_regiones(
        catalogo_bytes,
        series_bytes,
        extraido_en,
        desde,
        hasta,
        estado_publicacion=estado_publicacion,
    )
    salida_bytes = (json.dumps(lote, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _escribir_salida_protegida(salida, salida_bytes, sobrescribir=sobrescribir)

    return {
        "insumos": str(insumos_dir),
        "salida": str(salida),
        "publicacion": lote["publicacion"],
        "fuente_trazabilidad": lote["fuente_trazabilidad"],
    }


def _parsear_fecha_o_anio(texto: str, *, es_fin: bool) -> date:
    limpio = texto.strip()
    if re.fullmatch(r"\d{4}", limpio):
        anio = int(limpio)
        return date(anio, 12, 31) if es_fin else date(anio, 1, 1)
    try:
        return date.fromisoformat(limpio)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Valor inválido {texto!r}: indique año YYYY o fecha ISO YYYY-MM-DD."
        ) from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extracción oficial de las 416 series sectoriales regionales (16 regiones × 13 actividades × 2 valoraciones) desde BCCh BDE."
    )
    parser.add_argument(
        "--env",
        type=Path,
        default=None,
        help="Ruta a archivo .env local fuera de Git (opcional; por defecto lee variables de entorno).",
    )
    parser.add_argument(
        "--desde",
        type=lambda v: _parsear_fecha_o_anio(v, es_fin=False),
        default=date(2013, 1, 1),
        help="Año o fecha inicial ISO para GetSeries (predeterminado: 2013-01-01).",
    )
    parser.add_argument(
        "--hasta",
        type=lambda v: _parsear_fecha_o_anio(v, es_fin=True),
        default=date(2025, 12, 31),
        help="Año o fecha final ISO para GetSeries (predeterminado: 2025-12-31).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=MAX_WORKERS_DEFAULT,
        help=f"Concurrencia cortés máxima para GetSeries (1..{MAX_WORKERS_LIMITE}, predeterminado: {MAX_WORKERS_DEFAULT}).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT_DEFAULT,
        help=f"Timeout HTTP por consulta en segundos (predeterminado: {TIMEOUT_DEFAULT}).",
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
        default=Path("data/published/pib-sectorial-16-regiones.json"),
        help="Ruta del archivo JSON publicado (predeterminado: data/published/pib-sectorial-16-regiones.json).",
    )
    parser.add_argument(
        "--estado",
        choices=("aprobada", "prueba"),
        default="aprobada",
        help="Estado del corte publicado.",
    )
    parser.add_argument(
        "--sobrescribir",
        action="store_true",
        help="Permite sobrescribir --salida si ya contiene otro corte previo.",
    )
    parser.add_argument(
        "--reproducir",
        action="store_true",
        help="Reconstruye --salida bit-a-bit desde --insumos sin red ni credenciales.",
    )
    args = parser.parse_args(argv)

    try:
        if args.reproducir:
            if args.insumos is None:
                parser.exit(2, "En modo --reproducir debe indicar --insumos <directorio-raw>.\n")
            resumen = reproducir_sectorial_desde_raw(
                args.insumos,
                args.salida,
                sobrescribir=args.sobrescribir,
            )
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
            insumos_dir = args.insumos or (_RAIZ_REPO / "data" / "raw" / f"bde-sectorial-{stamp}")
            resumen = ejecutar_extraccion_sectorial(
                credenciales,
                insumos_dir=insumos_dir,
                salida=args.salida,
                desde=args.desde,
                hasta=args.hasta,
                max_workers=args.workers,
                timeout=args.timeout,
                estado_publicacion=args.estado,
                sobrescribir=args.sobrescribir,
            )
    except BdeApiError as error:
        parser.exit(1, f"{error}\n")
    except OSError:
        parser.exit(1, "No se pudo leer o escribir la evidencia local sectorial de BDE.\n")

    pub = resumen["publicacion"]
    traza = resumen["fuente_trazabilidad"]
    print(
        pub["id"],
        f"series={pub['series_totales']}",
        f"anios={pub['anios'][0]}-{pub['anios'][-1]}",
        f"catalogo_sha256={traza['catalogo_anual_sha256'][:12]}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
