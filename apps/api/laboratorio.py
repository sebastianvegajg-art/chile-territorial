"""Laboratorio de Investigación de Solo Lectura (Sección 10 · Fase 2).

Motor 100% determinista, estrictamente de solo lectura y sin dependencias de
servicios de IA de pago. Ejecuta el protocolo metodológico de 10 pasos sobre
los cortes oficiales disponibles en ``data/published/`` y ``data/raw/``, sin
alterar datos oficiales ni inventar cifras faltantes.
"""

from __future__ import annotations

from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
import json
import math
import os
from pathlib import Path
import re
from typing import Any, Mapping
import unicodedata

from .lote_oficial import TERRITORIOS_OFICIALES

RAIZ_REPO = Path(__file__).resolve().parents[2]

RUTA_PIB_API_DEFECTO = RAIZ_REPO / "data" / "published" / "pib-bde-api.json"
RUTA_PIB_PUBLICO_DEFECTO = RAIZ_REPO / "data" / "published" / "pib-bde-publico.json"
RUTA_SECTORIAL_DEFECTO = RAIZ_REPO / "data" / "published" / "pib-sectorial-16-regiones.json"
RUTA_SECTORIAL_AYSEN_RAW = RAIZ_REPO / "data" / "raw" / "bcch-aysen-sectorial-live.json"
RUTA_POBLACION_DEFECTO = RAIZ_REPO / "data" / "published" / "poblacion-ine-regiones.json"
RUTA_DIPRES_AYSEN_DEFECTO = RAIZ_REPO / "data" / "raw" / "dipres-aysen-2025.json"
RUTA_SINIM_DEFECTO = RAIZ_REPO / "data" / "published" / "sinim-aysen-importado.json"
RUTA_CRUCES_DEFECTO = RAIZ_REPO / "pipelines" / "fiscal" / "cruces-investigacion.json"

_CONTEXTO_DECIMAL = Context(prec=34, rounding=ROUND_HALF_EVEN)
_CERO = Decimal("0")
_CIEN = Decimal("100")
_MILLON = Decimal("1000000")

_CATALOGO_TERRITORIOS: dict[str, tuple[str, str]] = {
    codigo: (nombre, nivel) for codigo, nombre, nivel in TERRITORIOS_OFICIALES
}
_CODIGO_VALIDO = re.compile(r"^(CL|0[1-9]|1[0-6])$")

EJES_TEMATICOS: tuple[str, ...] = (
    "crecimiento_y_pib",
    "estructura_y_especializacion",
    "per_capita_y_convergencia",
    "dependencia_estatal",
    "finanzas_y_billeteras",
    "panorama_integral",
)

_PALABRAS_CLAVE_POR_EJE: dict[str, tuple[tuple[str, int], ...]] = {
    "dependencia_estatal": (
        ("dependencia estatal", 6),
        ("dependencia del estado", 6),
        ("dependiente del estado", 6),
        ("peso del estado", 5),
        ("administracion publica", 4),
        ("empleo publico", 4),
        ("sector publico", 3),
        ("estatal", 3),
        ("dependencia", 4),
        ("dependiente", 4),
        ("dependientes", 4),
        ("estado", 2),
    ),
    "finanzas_y_billeteras": (
        ("billeteras", 5),
        ("billetera", 5),
        ("dipres", 5),
        ("sinim", 5),
        ("presupuesto", 4),
        ("presupuestario", 4),
        ("presupuestaria", 4),
        ("gore", 4),
        ("fndr", 4),
        ("gasto publico", 4),
        ("inversion publica", 4),
        ("municipal", 3),
        ("comunas", 3),
        ("comunal", 3),
        ("devengo", 3),
        ("devengado", 3),
        ("ejecucion", 3),
        ("fiscal", 3),
        ("finanzas", 3),
        ("transferencias", 2),
        ("subtitulo", 3),
    ),
    "per_capita_y_convergencia": (
        ("per capita", 5),
        ("percapita", 5),
        ("sigma", 5),
        ("convergencia", 5),
        ("divergencia", 4),
        ("poblacion", 4),
        ("habitante", 4),
        ("habitantes", 4),
        ("demografia", 4),
        ("demografico", 4),
        ("ine", 3),
        ("brecha regional", 4),
    ),
    "estructura_y_especializacion": (
        ("estructura productiva", 5),
        ("especializacion", 5),
        ("sectorial", 4),
        ("sectores", 4),
        ("actividades", 4),
        ("actividad", 3),
        ("hhi", 5),
        ("concentracion", 4),
        ("diversificacion", 4),
        ("krugman", 5),
        ("cociente", 4),
        ("pesca", 4),
        ("acuicultura", 4),
        ("mineria", 4),
        ("industria", 3),
        ("comercio", 3),
        ("matriz productiva", 5),
        ("estructura", 3),
    ),
    "crecimiento_y_pib": (
        ("crecimiento", 4),
        ("crecio", 4),
        ("crece", 4),
        ("pib", 3),
        ("producto interno", 4),
        ("participacion nacional", 4),
        ("participacion", 3),
        ("recesion", 4),
        ("contraccion", 4),
        ("expansion", 3),
        ("evolucion", 2),
        ("economia", 2),
    ),
    "panorama_integral": (
        ("panorama", 5),
        ("integral", 5),
        ("diagnostico", 4),
        ("resumen general", 4),
        ("vision general", 4),
    ),
}

_DESCRIPCION_EJES: dict[str, str] = {
    "crecimiento_y_pib": "Crecimiento real, trayectoria de PIB y participación en el total nacional",
    "estructura_y_especializacion": "Estructura productiva, especialización sectorial y concentración (HHI)",
    "per_capita_y_convergencia": "Demografía oficial INE, PIB per cápita y σ-convergencia territorial",
    "dependencia_estatal": "Matriz de dependencia estatal (CCNN Administración Pública, gasto presupuestario y empleo público)",
    "finanzas_y_billeteras": "Finanzas públicas territoriales, tres billeteras (sectorial, regional, municipal) y ejecución presupuestaria",
    "panorama_integral": "Diagnóstico territorial multidimensional (PIB, estructura, demografía y finanzas públicas)",
}


def _normalizar_texto(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(ch for ch in descompuesto if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


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


def _formatear_decimal(valor: Decimal | None, decimales: int | None = None) -> str | None:
    if valor is None or not valor.is_finite():
        return None
    with localcontext(_CONTEXTO_DECIMAL):
        if decimales is not None:
            cuanto = Decimal("1").scaleb(-decimales)
            valor = valor.quantize(cuanto, rounding=ROUND_HALF_EVEN)
        if valor == _CERO:
            return "0" if decimales is None else format(_CERO.quantize(Decimal("1").scaleb(-decimales)), "f")
        texto = format(valor, "f")
        if decimales is None and "." in texto:
            texto = texto.rstrip("0").rstrip(".")
        return "0" if texto in {"", "-0"} else texto


def _ruta_relativa_segura(ruta: Path | None) -> str | None:
    if ruta is None:
        return None
    try:
        return ruta.resolve().relative_to(RAIZ_REPO.resolve()).as_posix()
    except ValueError:
        return ruta.name


def _leer_json_seguro(ruta: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    if ruta is None or not ruta.is_file():
        return None, None
    try:
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"No se pudo leer el archivo JSON '{ruta.name}': {exc}"
    if not isinstance(contenido, dict):
        return None, f"El archivo '{ruta.name}' no contiene un objeto JSON válido."
    return contenido, None


def _clasificar_pregunta(pregunta: str) -> tuple[str, list[str]]:
    normalizada = _normalizar_texto(pregunta)
    puntajes: dict[str, int] = {eje: 0 for eje in EJES_TEMATICOS}
    detectadas: dict[str, list[str]] = {eje: [] for eje in EJES_TEMATICOS}

    for eje, terminos in _PALABRAS_CLAVE_POR_EJE.items():
        for termino, peso in terminos:
            patron = r"(?<!\w)" + re.escape(termino) + r"(?!\w)"
            if re.search(patron, normalizada):
                puntajes[eje] += peso
                detectadas[eje].append(termino)

    if puntajes["panorama_integral"] >= 4:
        eje_elegido = "panorama_integral"
    else:
        especificos = [eje for eje in EJES_TEMATICOS if eje != "panorama_integral"]
        ordenados = sorted(especificos, key=lambda eje: (-puntajes[eje], especificos.index(eje)))
        mejor = ordenados[0]
        segundo = ordenados[1]
        if puntajes[mejor] == 0:
            eje_elegido = "panorama_integral"
        elif puntajes[mejor] == puntajes[segundo] and puntajes[mejor] >= 3:
            # Empate fuerte entre dos ejes distintos -> visión integral salvo que uno sea dependencia_estatal
            if "dependencia_estatal" in {mejor, segundo} and puntajes["dependencia_estatal"] >= 4:
                eje_elegido = "dependencia_estatal"
            else:
                eje_elegido = "panorama_integral"
        else:
            eje_elegido = mejor

    palabras = sorted({kw for lista in detectadas.values() for kw in lista})
    return eje_elegido, palabras


def _resolver_rutas(
    *,
    ruta_pib: Path | None,
    ruta_sectorial: Path | None,
    ruta_poblacion: Path | None,
    ruta_dipres: Path | None,
    ruta_sinim: Path | None,
) -> dict[str, tuple[Path, bool]]:
    """Resuelve rutas oficiales en modo solo lectura indicando si fueron explícitas."""
    if ruta_pib is not None:
        pib_path, pib_exp = Path(ruta_pib), True
    else:
        env_pib = (os.getenv("CT_LOTE_OFICIAL") or "").strip()
        if env_pib:
            pib_path = Path(env_pib)
        elif RUTA_PIB_API_DEFECTO.is_file():
            pib_path = RUTA_PIB_API_DEFECTO
        else:
            pib_path = RUTA_PIB_PUBLICO_DEFECTO
        pib_exp = False

    if ruta_sectorial is not None:
        sec_path, sec_exp = Path(ruta_sectorial), True
    else:
        env_sec = (os.getenv("CT_SECTORIAL_PATH") or "").strip()
        sec_path = Path(env_sec) if env_sec else RUTA_SECTORIAL_DEFECTO
        sec_exp = False

    if ruta_poblacion is not None:
        pob_path, pob_exp = Path(ruta_poblacion), True
    else:
        env_pob = (os.getenv("CT_POBLACION_PATH") or "").strip()
        pob_path = Path(env_pob) if env_pob else RUTA_POBLACION_DEFECTO
        pob_exp = False

    if ruta_dipres is not None:
        dip_path, dip_exp = Path(ruta_dipres), True
    else:
        env_dip = (os.getenv("CT_DIPRES_PATH") or "").strip()
        dip_path = Path(env_dip) if env_dip else RUTA_DIPRES_AYSEN_DEFECTO
        dip_exp = False

    if ruta_sinim is not None:
        sin_path, sin_exp = Path(ruta_sinim), True
    else:
        env_sin = (os.getenv("CT_SINIM_PATH") or "").strip()
        sin_path = Path(env_sin) if env_sin else RUTA_SINIM_DEFECTO
        sin_exp = False

    return {
        "pib": (pib_path, pib_exp),
        "sectorial": (sec_path, sec_exp),
        "poblacion": (pob_path, pob_exp),
        "dipres": (dip_path, dip_exp),
        "sinim": (sin_path, sin_exp),
    }


def _analizar_pib(datos_pib: dict[str, Any] | None, territorio: str) -> dict[str, Any]:
    if not datos_pib or not isinstance(datos_pib.get("observaciones"), list):
        return {
            "disponible": False,
            "estado": "pendiente",
            "motivo": "No se encontró un corte oficial de PIB válido en disco.",
            "registros_leidos": 0,
        }

    pub = datos_pib.get("publicacion") if isinstance(datos_pib.get("publicacion"), dict) else {}
    observaciones = datos_pib["observaciones"]

    niveles_nominal: dict[tuple[str, int], Decimal] = {}
    niveles_real: dict[tuple[str, int], Decimal] = {}
    crecimientos: dict[tuple[str, int], Decimal] = {}
    participaciones: dict[tuple[str, int], Decimal] = {}
    registros_relevantes = 0

    for fila in observaciones:
        if not isinstance(fila, Mapping):
            continue
        terr = fila.get("territorio")
        anio = fila.get("anio")
        metrica = fila.get("metrica")
        val = fila.get("valoracion")
        num = _a_decimal(fila.get("valor"))
        if not isinstance(terr, str) or type(anio) is not int:
            continue
        if terr in {territorio, "CL"}:
            registros_relevantes += 1
        if num is None:
            continue
        if metrica == "nivel" and val == "nominal":
            niveles_nominal[(terr, anio)] = num
        elif metrica == "nivel" and val == "real":
            niveles_real[(terr, anio)] = num
        elif metrica == "crecimiento" and val == "real":
            crecimientos[(terr, anio)] = num
        elif metrica == "participacion" and val == "nominal":
            participaciones[(terr, anio)] = num

    anios_terr = sorted(
        {anio for (terr, anio) in niveles_real if terr == territorio}
        | {anio for (terr, anio) in niveles_nominal if terr == territorio}
    )
    if not anios_terr:
        return {
            "disponible": False,
            "estado": "pendiente",
            "motivo": f"El corte de PIB no contiene niveles para el territorio '{territorio}'.",
            "registros_leidos": registros_relevantes,
        }

    anio_inicio = anios_terr[0]
    anio_ultimo = anios_terr[-1]

    pib_nom_ult = niveles_nominal.get((territorio, anio_ultimo))
    pib_real_ult = niveles_real.get((territorio, anio_ultimo))
    pib_real_ini = niveles_real.get((territorio, anio_inicio))
    cl_nom_ult = niveles_nominal.get(("CL", anio_ultimo))
    cl_real_ult = niveles_real.get(("CL", anio_ultimo))
    cl_real_ini = niveles_real.get(("CL", anio_inicio))

    crec_ult = crecimientos.get((territorio, anio_ultimo))
    if crec_ult is None and pib_real_ult is not None:
        prev = niveles_real.get((territorio, anio_ultimo - 1))
        if prev is not None and prev != _CERO:
            with localcontext(_CONTEXTO_DECIMAL):
                crec_ult = _CIEN * (pib_real_ult / prev - Decimal("1"))

    crec_cl_ult = crecimientos.get(("CL", anio_ultimo))
    if crec_cl_ult is None and cl_real_ult is not None:
        prev_cl = niveles_real.get(("CL", anio_ultimo - 1))
        if prev_cl is not None and prev_cl != _CERO:
            with localcontext(_CONTEXTO_DECIMAL):
                crec_cl_ult = _CIEN * (cl_real_ult / prev_cl - Decimal("1"))

    crec_acum_terr = None
    if pib_real_ult is not None and pib_real_ini is not None and pib_real_ini != _CERO:
        with localcontext(_CONTEXTO_DECIMAL):
            crec_acum_terr = _CIEN * (pib_real_ult / pib_real_ini - Decimal("1"))

    crec_acum_cl = None
    if cl_real_ult is not None and cl_real_ini is not None and cl_real_ini != _CERO:
        with localcontext(_CONTEXTO_DECIMAL):
            crec_acum_cl = _CIEN * (cl_real_ult / cl_real_ini - Decimal("1"))

    part_ult = None
    if territorio != "CL":
        part_ult = participaciones.get((territorio, anio_ultimo))
        if part_ult is None and pib_nom_ult is not None and cl_nom_ult is not None and cl_nom_ult != _CERO:
            with localcontext(_CONTEXTO_DECIMAL):
                part_ult = _CIEN * (pib_nom_ult / cl_nom_ult)

    serie_crecimientos = [
        crecimientos[(territorio, a)]
        for a in anios_terr
        if (territorio, a) in crecimientos
    ]
    prom_crec = None
    if serie_crecimientos:
        with localcontext(_CONTEXTO_DECIMAL):
            prom_crec = sum(serie_crecimientos, _CERO) / Decimal(len(serie_crecimientos))

    anios_positivos = sum(1 for v in serie_crecimientos if v > _CERO)
    anios_negativos = sum(1 for v in serie_crecimientos if v < _CERO)

    ranking_nom = None
    ranking_crec = None
    if territorio != "CL":
        regiones_nom = sorted(
            [
                (cod, niveles_nominal[(cod, anio_ultimo)])
                for cod in (f"{n:02d}" for n in range(1, 17))
                if (cod, anio_ultimo) in niveles_nominal
            ],
            key=lambda item: (-item[1], item[0]),
        )
        for idx, (cod, _) in enumerate(regiones_nom, start=1):
            if cod == territorio:
                ranking_nom = {"posicion": idx, "total_regiones": len(regiones_nom)}
                break

        regiones_crec = sorted(
            [
                (cod, crecimientos[(cod, anio_ultimo)])
                for cod in (f"{n:02d}" for n in range(1, 17))
                if (cod, anio_ultimo) in crecimientos
            ],
            key=lambda item: (-item[1], item[0]),
        )
        for idx, (cod, _) in enumerate(regiones_crec, start=1):
            if cod == territorio:
                ranking_crec = {"posicion": idx, "total_regiones": len(regiones_crec)}
                break

    return {
        "disponible": True,
        "estado": "disponible",
        "corte_id": pub.get("id"),
        "fecha_corte": pub.get("fecha"),
        "fuente": pub.get("fuente", "BCCh-BDE"),
        "periodo": [anio_inicio, anio_ultimo],
        "ultimo_anio": anio_ultimo,
        "unidad": "millones CLP",
        "anio_referencia_real": 2018,
        "pib_nominal_ultimo_millones": _formatear_decimal(pib_nom_ult, 2),
        "pib_real_ultimo_millones": _formatear_decimal(pib_real_ult, 2),
        "pib_nominal_chile_ultimo_millones": _formatear_decimal(cl_nom_ult, 2),
        "pib_real_chile_ultimo_millones": _formatear_decimal(cl_real_ult, 2),
        "participacion_nacional_pct": _formatear_decimal(part_ult, 2),
        "crecimiento_real_ultimo_anio_pct": _formatear_decimal(crec_ult, 2),
        "crecimiento_real_chile_ultimo_anio_pct": _formatear_decimal(crec_cl_ult, 2),
        "crecimiento_real_acumulado_pct": _formatear_decimal(crec_acum_terr, 2),
        "crecimiento_real_acumulado_chile_pct": _formatear_decimal(crec_acum_cl, 2),
        "promedio_crecimiento_real_anual_pct": _formatear_decimal(prom_crec, 2),
        "anios_crecimiento_observados": len(serie_crecimientos),
        "anios_positivos": anios_positivos,
        "anios_negativos": anios_negativos,
        "ranking_pib_nominal_ultimo_anio": ranking_nom,
        "ranking_crecimiento_ultimo_anio": ranking_crec,
        "registros_leidos": registros_relevantes,
        "_niveles_nominal_raw": niveles_nominal,
        "_niveles_real_raw": niveles_real,
    }


def _extraer_sectorial_desde_16_regiones(
    datos: dict[str, Any],
    territorio: str,
    archivo_label: str,
) -> dict[str, Any] | None:
    """Extrae métricas sectoriales para un territorio desde pib-sectorial-16-regiones.json."""
    anio: int | None = None
    registro_region: dict[str, Any] | None = None

    # Esquema canónico de pipelines/economia/bde_sectorial.py: datos["por_anio"][str(anio)]["regiones"][territorio]
    por_anio = datos.get("por_anio")
    if isinstance(por_anio, Mapping) and por_anio:
        anios_ordenados = sorted(
            (int(k) for k in por_anio.keys() if str(k).isdigit()),
            reverse=True,
        )
        for cand in anios_ordenados:
            bloque = por_anio.get(str(cand))
            if not isinstance(bloque, Mapping):
                continue
            regs = bloque.get("regiones")
            if isinstance(regs, Mapping) and territorio in regs and isinstance(regs[territorio], Mapping):
                anio = cand
                registro_region = dict(regs[territorio])
                break

    # Esquema alternativo plano: datos["regiones"]
    if registro_region is None:
        regiones = datos.get("regiones")
        if isinstance(regiones, Mapping) and territorio in regiones and isinstance(regiones[territorio], Mapping):
            registro_region = dict(regiones[territorio])
        elif isinstance(regiones, list):
            for item in regiones:
                if isinstance(item, Mapping) and (
                    item.get("territorio") == territorio or item.get("codigo") == territorio
                ):
                    registro_region = dict(item)
                    break

    if registro_region is None:
        return None

    if anio is None:
        anio = registro_region.get("ultimo_anio") or registro_region.get("anio") or datos.get("ultimo_anio")
    actividades_raw = registro_region.get("actividades") or []
    actividades: list[dict[str, Any]] = []
    admin_pub: dict[str, Any] | None = None

    for act in actividades_raw:
        if not isinstance(act, Mapping):
            continue
        nombre = str(act.get("nombre") or act.get("actividad") or act.get("actividad_id") or act.get("codigo_actividad") or "")
        part = _a_decimal(
            act.get("participacion_nominal_pct")
            or act.get("participacion_pib_pct")
            or act.get("participacion_actividades_pct")
            or act.get("participacion_pct")
        )
        val_mm = _a_decimal(
            act.get("nominal_millones")
            if act.get("nominal_millones") is not None
            else (act.get("valor_millones") if act.get("valor_millones") is not None else act.get("valor"))
        )
        cod = str(act.get("actividad_id") or act.get("codigo_actividad") or act.get("codigo") or "")
        fila = {
            "codigo_actividad": cod,
            "nombre": nombre,
            "valor_millones": _formatear_decimal(val_mm, 2),
            "participacion_pct": _formatear_decimal(part, 2),
            "cociente_localizacion": _formatear_decimal(
                _a_decimal(act.get("lq_especializacion") or act.get("lq") or act.get("cociente_localizacion")), 2
            ),
            "serie_bde": act.get("serie_bde_nominal") or act.get("serie_bde"),
            "_part_num": part if part is not None else Decimal("-1"),
        }
        actividades.append(fila)
        norm_nom = _normalizar_texto(nombre)
        if act.get("es_administracion_publica") or "administracion publica" in norm_nom or cod.startswith("12"):
            admin_pub = fila

    actividades.sort(key=lambda item: (-item["_part_num"], item["nombre"]))
    top_actividades = [
        {k: v for k, v in item.items() if not k.startswith("_")}
        for item in actividades[:5]
    ]

    hhi_raw = registro_region.get("hhi")
    if isinstance(hhi_raw, Mapping):
        hhi_val = _a_decimal(hhi_raw.get("valor"))
    else:
        hhi_val = _a_decimal(hhi_raw)

    if hhi_val is None and actividades:
        partes_validas = [item["_part_num"] for item in actividades if item["_part_num"] >= _CERO]
        if partes_validas:
            with localcontext(_CONTEXTO_DECIMAL):
                hhi_val = sum((p * p for p in partes_validas), _CERO)

    krugman_raw = registro_region.get("indice_krugman")
    if krugman_raw is None:
        krugman_raw = registro_region.get("krugman")
    krugman_val = _a_decimal(
        krugman_raw.get("valor") if isinstance(krugman_raw, Mapping) else krugman_raw
    )
    div_val = _a_decimal(registro_region.get("diversificacion"))

    pub = datos.get("publicacion") if isinstance(datos.get("publicacion"), Mapping) else {}
    traza = datos.get("fuente_trazabilidad") if isinstance(datos.get("fuente_trazabilidad"), Mapping) else {}
    return {
        "disponible": True,
        "estado": "disponible",
        "fuente_archivo": archivo_label,
        "corte_id": pub.get("id") or traza.get("corte_id") or datos.get("id") or "pib-sectorial-16-regiones",
        "fecha_corte": pub.get("fecha") or traza.get("extraido_en") or traza.get("actualizado_en") or datos.get("extraido_en"),
        "anio": anio,
        "hhi": _formatear_decimal(hhi_val, 2),
        "diversificacion": _formatear_decimal(div_val, 4),
        "krugman": _formatear_decimal(krugman_val, 4),
        "actividades_contabilizadas": len(actividades),
        "actividad_principal": top_actividades[0] if top_actividades else None,
        "administracion_publica": (
            {k: v for k, v in admin_pub.items() if not k.startswith("_")} if admin_pub else None
        ),
        "top_actividades": top_actividades,
        "registros_leidos": len(actividades),
    }


def _extraer_sectorial_aysen_live(datos: dict[str, Any], archivo_label: str) -> dict[str, Any]:
    resumen = datos.get("resumen_pib") if isinstance(datos.get("resumen_pib"), Mapping) else {}
    traza = datos.get("fuente_trazabilidad") if isinstance(datos.get("fuente_trazabilidad"), Mapping) else {}
    hhi_obj = resumen.get("concentracion_hhi") if isinstance(resumen.get("concentracion_hhi"), Mapping) else {}
    hhi_val = _a_decimal(hhi_obj.get("valor"))

    actividades_raw = datos.get("actividades") if isinstance(datos.get("actividades"), list) else []
    actividades: list[dict[str, Any]] = []
    admin_pub: dict[str, Any] | None = None

    for act in actividades_raw:
        if not isinstance(act, Mapping):
            continue
        part = _a_decimal(act.get("participacion_pib_pct") or act.get("participacion_actividades_pct"))
        val_mm = _a_decimal(act.get("valor_millones"))
        fila = {
            "codigo_actividad": str(act.get("codigo_actividad") or ""),
            "nombre": str(act.get("nombre") or ""),
            "valor_millones": _formatear_decimal(val_mm, 2),
            "participacion_pct": _formatear_decimal(part, 2),
            "serie_bde": act.get("serie_bde"),
            "_part_num": part if part is not None else Decimal("-1"),
        }
        actividades.append(fila)
        if act.get("es_administracion_publica") or fila["codigo_actividad"] == "12":
            admin_pub = fila

    actividades.sort(key=lambda item: (-item["_part_num"], item["nombre"]))
    top_actividades = [
        {k: v for k, v in item.items() if not k.startswith("_")}
        for item in actividades[:5]
    ]

    return {
        "disponible": True,
        "estado": "disponible",
        "fuente_archivo": archivo_label,
        "corte_id": f"bcch-aysen-sectorial-{traza.get('actualizado_en') or 'live'}",
        "fecha_corte": traza.get("extraido_en") or traza.get("actualizado_en"),
        "anio": datos.get("ultimo_anio") or resumen.get("anio"),
        "hhi": _formatear_decimal(hhi_val, 2),
        "krugman": None,
        "actividades_contabilizadas": len(actividades),
        "actividad_principal": top_actividades[0] if top_actividades else None,
        "administracion_publica": (
            {k: v for k, v in admin_pub.items() if not k.startswith("_")} if admin_pub else None
        ),
        "top_actividades": top_actividades,
        "registros_leidos": len(actividades),
    }


def _extraer_mapa_poblacion(datos_pob: dict[str, Any]) -> dict[tuple[str, int], Decimal]:
    """Extrae un mapa {(territorio, anio): habitantes} desde formatos estándar INE."""
    mapa: dict[tuple[str, int], Decimal] = {}

    # Formato 1: observaciones = [{"territorio": "11", "anio": 2025, "poblacion"|"valor": ...}]
    obs = datos_pob.get("observaciones")
    if isinstance(obs, list):
        for fila in obs:
            if not isinstance(fila, Mapping):
                continue
            terr = fila.get("territorio") or fila.get("codigo")
            anio = fila.get("anio")
            val = _a_decimal(
                fila.get("poblacion")
                if fila.get("poblacion") is not None
                else fila.get("valor")
            )
            if isinstance(terr, str) and type(anio) is int and val is not None and val > _CERO:
                mapa[(terr, anio)] = val

    # Formato 2: territorios / regiones / series como dict {cod: {serie_anual|anios|datos|observaciones}} o lista
    for contenedor_key in ("territorios", "regiones", "series"):
        cont = datos_pob.get(contenedor_key)
        if isinstance(cont, Mapping):
            for cod, bloque in cont.items():
                if not isinstance(cod, str) or not _CODIGO_VALIDO.fullmatch(cod):
                    continue
                if isinstance(bloque, Mapping):
                    # { "2013": 100000, ... } o { "anios": {"2013": ...} } o { "serie_anual": [...] }
                    for subkey in ("anios", "por_anio", "datos"):
                        sub = bloque.get(subkey)
                        if isinstance(sub, Mapping):
                            for k_anio, v_pob in sub.items():
                                if str(k_anio).isdigit():
                                    val = _a_decimal(v_pob)
                                    if val is not None and val > _CERO:
                                        mapa[(cod, int(k_anio))] = val
                    for subkey in ("serie_anual", "observaciones", "serie"):
                        sub = bloque.get(subkey)
                        if isinstance(sub, list):
                            for item in sub:
                                if not isinstance(item, Mapping):
                                    continue
                                anio = item.get("anio")
                                val = _a_decimal(
                                    item.get("poblacion")
                                    if item.get("poblacion") is not None
                                    else item.get("valor")
                                )
                                if type(anio) is int and val is not None and val > _CERO:
                                    mapa[(cod, anio)] = val
                    for k_anio, v_pob in bloque.items():
                        if str(k_anio).isdigit():
                            val = _a_decimal(v_pob)
                            if val is not None and val > _CERO:
                                mapa[(cod, int(k_anio))] = val
        elif isinstance(cont, list):
            for bloque in cont:
                if not isinstance(bloque, Mapping):
                    continue
                cod = bloque.get("territorio") or bloque.get("codigo")
                if not isinstance(cod, str) or not _CODIGO_VALIDO.fullmatch(cod):
                    continue
                for subkey in ("serie_anual", "observaciones", "serie"):
                    sub = bloque.get(subkey)
                    if isinstance(sub, list):
                        for item in sub:
                            if not isinstance(item, Mapping):
                                continue
                            anio = item.get("anio")
                            val = _a_decimal(
                                item.get("poblacion")
                                if item.get("poblacion") is not None
                                else item.get("valor")
                            )
                            if type(anio) is int and val is not None and val > _CERO:
                                mapa[(cod, anio)] = val

    return mapa


def _analizar_demografia(
    datos_pob: dict[str, Any] | None,
    pib_info: dict[str, Any],
    territorio: str,
) -> dict[str, Any]:
    if datos_pob is None:
        return {
            "disponible": False,
            "estado": "pendiente",
            "motivo": (
                "Archivo oficial de población INE aún no publicado en "
                "data/published/poblacion-ine-regiones.json."
            ),
            "registros_leidos": 0,
        }

    mapa_pob = _extraer_mapa_poblacion(datos_pob)
    if not mapa_pob:
        return {
            "disponible": False,
            "estado": "pendiente",
            "motivo": "El archivo de población INE no contiene observaciones poblacionales válidas.",
            "registros_leidos": 0,
        }

    anios_terr = sorted(anio for (cod, anio) in mapa_pob if cod == territorio)
    if not anios_terr:
        return {
            "disponible": False,
            "estado": "pendiente",
            "motivo": f"El archivo de población INE no contiene registros para el territorio '{territorio}'.",
            "registros_leidos": len(mapa_pob),
        }

    niveles_nom: dict[tuple[str, int], Decimal] = pib_info.get("_niveles_nominal_raw") or {}
    niveles_real: dict[tuple[str, int], Decimal] = pib_info.get("_niveles_real_raw") or {}

    anios_cruce = sorted(
        a for a in anios_terr if (territorio, a) in niveles_real or (territorio, a) in niveles_nom
    )
    anio_ref = anios_cruce[-1] if anios_cruce else anios_terr[-1]
    pob_ultimo = mapa_pob.get((territorio, anio_ref))

    pc_nom_terr = None
    pc_real_terr = None
    pc_nom_cl = None
    pc_real_cl = None
    ratio_pc_real_vs_chile = None

    with localcontext(_CONTEXTO_DECIMAL):
        if pob_ultimo and pob_ultimo > _CERO:
            if (territorio, anio_ref) in niveles_nom:
                pc_nom_terr = (niveles_nom[(territorio, anio_ref)] * _MILLON) / pob_ultimo
            if (territorio, anio_ref) in niveles_real:
                pc_real_terr = (niveles_real[(territorio, anio_ref)] * _MILLON) / pob_ultimo

        pob_cl = mapa_pob.get(("CL", anio_ref))
        if pob_cl and pob_cl > _CERO:
            if ("CL", anio_ref) in niveles_nom:
                pc_nom_cl = (niveles_nom[("CL", anio_ref)] * _MILLON) / pob_cl
            if ("CL", anio_ref) in niveles_real:
                pc_real_cl = (niveles_real[("CL", anio_ref)] * _MILLON) / pob_cl

        if pc_real_terr is not None and pc_real_cl is not None and pc_real_cl > _CERO:
            ratio_pc_real_vs_chile = _CIEN * (pc_real_terr / pc_real_cl)

    # σ-convergencia (desviación estándar de ln(PIB per cápita real) en las 16 regiones)
    sigma_serie: list[dict[str, Any]] = []
    anios_todos = sorted({a for (_, a) in niveles_real if a >= 2013})
    for a in anios_todos:
        logs: list[float] = []
        for reg in (f"{n:02d}" for n in range(1, 17)):
            pib_r = niveles_real.get((reg, a))
            pob_r = mapa_pob.get((reg, a))
            if pib_r is not None and pob_r is not None and pib_r > _CERO and pob_r > _CERO:
                pc_r = float((pib_r * _MILLON) / pob_r)
                if pc_r > 0:
                    logs.append(math.log(pc_r))
        if len(logs) >= 2:
            media = sum(logs) / len(logs)
            varianza = sum((x - media) ** 2 for x in logs) / len(logs)
            sigma = math.sqrt(varianza)
            sigma_serie.append(
                {
                    "anio": a,
                    "sigma_ln_pib_pc_real": _formatear_decimal(Decimal(str(sigma)), 6),
                    "regiones_incluidas": len(logs),
                }
            )

    pub_pob = datos_pob.get("publicacion") if isinstance(datos_pob.get("publicacion"), Mapping) else {}
    traza = datos_pob.get("fuente_trazabilidad") if isinstance(datos_pob.get("fuente_trazabilidad"), Mapping) else {}
    return {
        "disponible": True,
        "estado": "disponible",
        "corte_id": pub_pob.get("id") or traza.get("corte_id") or datos_pob.get("id") or "poblacion-ine-regiones",
        "fecha_corte": pub_pob.get("fecha") or traza.get("extraido_en") or traza.get("actualizado_en") or datos_pob.get("extraido_en"),
        "periodo_poblacion": [anios_terr[0], anios_terr[-1]],
        "anio_referencia_cruce": anio_ref,
        "poblacion_ultimo_cruce": _formatear_decimal(pob_ultimo, 0),
        "pib_per_capita_nominal_clp": _formatear_decimal(pc_nom_terr, 0),
        "pib_per_capita_real_clp": _formatear_decimal(pc_real_terr, 0),
        "pib_per_capita_nominal_chile_clp": _formatear_decimal(pc_nom_cl, 0),
        "pib_per_capita_real_chile_clp": _formatear_decimal(pc_real_cl, 0),
        "indice_pib_pc_real_vs_chile_100": _formatear_decimal(ratio_pc_real_vs_chile, 2),
        "sigma_convergencia_ultimo": sigma_serie[-1] if sigma_serie else None,
        "sigma_convergencia_inicial": sigma_serie[0] if sigma_serie else None,
        "registros_leidos": len(mapa_pob),
    }


def _analizar_dipres(
    datos_dipres: dict[str, Any] | None,
    pib_info: dict[str, Any],
    territorio: str,
    explicito: bool,
) -> dict[str, Any]:
    if datos_dipres is None:
        return {
            "disponible": False,
            "estado": "pendiente",
            "motivo": (
                "No se encontró corte DIPRES CKAN en disco para el territorio solicitado."
            ),
            "registros_leidos": 0,
        }

    region_archivo = str(datos_dipres.get("region_codigo") or "")
    if not explicito and region_archivo and region_archivo != territorio:
        return {
            "disponible": False,
            "estado": "no_aplica_territorio",
            "motivo": (
                f"El corte fiscal DIPRES disponible corresponde al piloto Región {region_archivo} "
                f"y no cubre aún el territorio '{territorio}'."
            ),
            "registros_leidos": 0,
        }

    anio = datos_dipres.get("anio")
    totales = (
        datos_dipres.get("totales_gobierno_central_aysen")
        if isinstance(datos_dipres.get("totales_gobierno_central_aysen"), Mapping)
        else {}
    )
    gore = datos_dipres.get("gore_aysen") if isinstance(datos_dipres.get("gore_aysen"), Mapping) else {}
    traza = (
        datos_dipres.get("fuente_trazabilidad")
        if isinstance(datos_dipres.get("fuente_trazabilidad"), Mapping)
        else {}
    )

    gasto_directo = _a_decimal(totales.get("total_gasto_directo_millones"))
    gasto_corriente = _a_decimal(totales.get("gasto_corriente_sub_21_26"))
    inversion = _a_decimal(totales.get("inversion_sub_29_31"))
    transf_cap = _a_decimal(totales.get("transferencias_capital_sub_33"))
    otros = _a_decimal(totales.get("otros_gastos"))
    fin_gore = _a_decimal(totales.get("financiamiento_gore_p31") or gore.get("ingresos_financiamiento_p31"))

    niveles_nom: dict[tuple[str, int], Decimal] = pib_info.get("_niveles_nominal_raw") or {}
    pib_nom_anio = niveles_nom.get((territorio, anio)) if type(anio) is int else None
    ratio_gasto_pib = None
    if gasto_directo is not None and pib_nom_anio is not None and pib_nom_anio > _CERO:
        with localcontext(_CONTEXTO_DECIMAL):
            ratio_gasto_pib = _CIEN * (gasto_directo / pib_nom_anio)

    return {
        "disponible": True,
        "estado": "disponible",
        "anio": anio,
        "region_codigo": region_archivo or territorio,
        "etapa_informada": traza.get("etapa_informada", "ejecucion_acumulada"),
        "unidad": traza.get("unidad_salida", "millones CLP"),
        "corte_id": traza.get("resource_id") or traza.get("package_name"),
        "fecha_corte": traza.get("actualizado_en") or traza.get("extraido_en"),
        "total_gasto_directo_millones": _formatear_decimal(gasto_directo, 3),
        "gasto_corriente_sub_21_26_millones": _formatear_decimal(gasto_corriente, 3),
        "inversion_sub_29_31_millones": _formatear_decimal(inversion, 3),
        "transferencias_capital_sub_33_millones": _formatear_decimal(transf_cap, 3),
        "otros_gastos_millones": _formatear_decimal(otros, 3),
        "financiamiento_gore_p31_millones": _formatear_decimal(fin_gore, 3),
        "ratio_gasto_directo_sobre_pib_nominal_pct": _formatear_decimal(ratio_gasto_pib, 2),
        "motivo_brecha_gore": gore.get("motivo_brecha"),
        "registros_leidos": int(traza.get("registros_unicos_procesados") or 0),
    }


def _analizar_sinim(
    datos_sinim: dict[str, Any] | None,
    territorio: str,
    explicito: bool,
) -> dict[str, Any]:
    if datos_sinim is None or datos_sinim.get("valido") is not True:
        return {
            "disponible": False,
            "estado": "pendiente",
            "motivo": (
                "No existe archivo SINIM municipal importado para las 10 comunas de Aysén "
                "(SUBDERE/SINIM requiere importación oficial local)."
            ),
            "registros_leidos": 0,
        }
    if not explicito and territorio != "11":
        return {
            "disponible": False,
            "estado": "no_aplica_territorio",
            "motivo": (
                f"La importación SINIM disponible corresponde a las 10 comunas de Aysén (11) "
                f"y no al territorio '{territorio}'."
            ),
            "registros_leidos": 0,
        }

    resumen = datos_sinim.get("resumen") if isinstance(datos_sinim.get("resumen"), Mapping) else {}
    traza = (
        datos_sinim.get("fuente_trazabilidad")
        if isinstance(datos_sinim.get("fuente_trazabilidad"), Mapping)
        else {}
    )
    comunas = datos_sinim.get("comunas") if isinstance(datos_sinim.get("comunas"), list) else []

    return {
        "disponible": True,
        "estado": "disponible",
        "anio": resumen.get("anio"),
        "comunas_cargadas": resumen.get("comunas_cargadas", len(comunas)),
        "comunas_esperadas": resumen.get("comunas_esperadas", 10),
        "etapa": traza.get("etapa"),
        "unidad": traza.get("unidad_salida", "millones CLP"),
        "total_ingresos_millones": resumen.get("total_ingresos_millones"),
        "total_gasto_devengado_millones": resumen.get("total_gasto_devengado_millones"),
        "total_gasto_corriente_millones": resumen.get("total_gasto_corriente_millones"),
        "total_inversion_millones": resumen.get("total_inversion_millones"),
        "corte_id": traza.get("sha256"),
        "fecha_corte": traza.get("actualizado_en"),
        "registros_leidos": len(comunas),
    }


def _construir_hipotesis_y_metodo(eje: str, nombre_territorio: str, codigo_territorio: str) -> dict[str, Any]:
    formulas_base = [
        {
            "nombre": "Crecimiento anual real",
            "version": "pib-crecimiento-v1",
            "formula": "100 * (PIB_real[t] / PIB_real[t-1] - 1)",
            "unidad": "%",
        },
        {
            "nombre": "Crecimiento real acumulado",
            "version": "pib-crecimiento-acumulado-v1",
            "formula": "100 * (PIB_real[t_fin] / PIB_real[t_inicio] - 1)",
            "unidad": "%",
        },
        {
            "nombre": "Participación nominal regional",
            "version": "pib-participacion-v1",
            "formula": "100 * PIB_nominal_regional[t] / PIB_nominal_nacional[t]",
            "unidad": "%",
        },
    ]

    if eje == "crecimiento_y_pib":
        hipotesis = (
            f"El crecimiento real del PIB de {nombre_territorio} ({codigo_territorio}) presenta una "
            "trayectoria diferenciada respecto del promedio nacional en el período oficial 2013–2025, "
            "verificable mediante variaciones anuales y acumuladas del mismo corte."
        )
        criterio = (
            "Comparar la tasa de crecimiento real anual del último año y la expansión acumulada "
            f"de {nombre_territorio} frente al total nacional (CL) usando el mismo año de referencia (2018)."
        )
        formulas = formulas_base
    elif eje == "estructura_y_especializacion":
        hipotesis = (
            f"La estructura productiva nominal de {nombre_territorio} ({codigo_territorio}) muestra "
            "concentración en pocas actividades principales (HHI elevado), lo que explica mayor volatilidad "
            "interanual frente al agregado nacional."
        )
        criterio = (
            "Calcular participaciones nominales por actividad, índice HHI (escala 0–10.000) y peso "
            "de la actividad principal sobre el PIB regional a precios corrientes."
        )
        formulas = [
            *formulas_base[:1],
            {
                "nombre": "Participación sectorial nominal",
                "version": "estructura-participacion-v1",
                "formula": "100 * VA_nominal_actividad / PIB_nominal_territorio",
                "unidad": "%",
            },
            {
                "nombre": "Índice de concentración Herfindahl-Hirschman (HHI)",
                "version": "estructura-hhi-v1",
                "formula": "SUM(participacion_sectorial_pct_i^2)",
                "unidad": "puntos (0-10000)",
            },
        ]
    elif eje == "per_capita_y_convergencia":
        hipotesis = (
            f"El PIB per cápita real de {nombre_territorio} ({codigo_territorio}) diverge del promedio "
            "nacional y la dispersión interregional (σ-convergencia) cambia de forma verificable en 2013–2025."
        )
        criterio = (
            "Cruzar el PIB oficial (nominal y real) con proyecciones oficiales de población INE por "
            "región y estimar la desviación estándar de ln(PIB per cápita real) entre las 16 regiones."
        )
        formulas = [
            *formulas_base[:2],
            {
                "nombre": "PIB per cápita",
                "version": "pib-per-capita-v1",
                "formula": "(PIB_millones_CLP * 1_000_000) / poblacion_INE",
                "unidad": "CLP por habitante",
            },
            {
                "nombre": "σ-convergencia interregional",
                "version": "sigma-convergencia-v1",
                "formula": "std(ln(PIB_per_capita_real_r)) para r en 01..16",
                "unidad": "desviación logarítmica",
            },
        ]
    elif eje == "dependencia_estatal":
        hipotesis = (
            f"La presencia económica del Estado en {nombre_territorio} ({codigo_territorio}) exige "
            "medirse en tres planos no intercambiables: actividad CCNN Administración Pública, "
            "gasto presupuestario localizado y empleo público."
        )
        criterio = (
            "Contrastar separadamente el peso de Administración Pública en PIB nominal (BCCh CCNN), "
            "la razón descriptiva gasto público identificado/PIB nominal (DIPRES/SINIM) y el estado "
            "de cobertura del empleo público (ENE/INE), sin sumar ni confundir perímetros."
        )
        formulas = [
            {
                "nombre": "Peso CCNN Administración Pública",
                "version": "estructura-participacion-v1",
                "formula": "100 * VA_nominal_Administracion_Publica / PIB_nominal_territorio",
                "unidad": "%",
            },
            {
                "nombre": "Intensidad descriptiva de gasto público identificado",
                "version": "gasto-publico-pib-descriptivo-v1",
                "formula": "100 * gasto_publico_identificado_CLP / PIB_nominal_territorio_CLP",
                "unidad": "% (descriptivo, perímetro parcial)",
            },
        ]
    elif eje == "finanzas_y_billeteras":
        hipotesis = (
            f"El gasto público ejecutado en {nombre_territorio} ({codigo_territorio}) se distribuye "
            "entre billetera sectorial, regional (GORE/FNDR) y municipal (SINIM), con brechas de "
            "regionalización que impiden sumar vistas brutas sin conciliación documental."
        )
        criterio = (
            "Desagregar ejecución por billetera, etapa contable y subtítulos presupuestarios (21–26, "
            "29–31, 33 y Partida 31), manteniendo separadas las transferencias internas no conciliadas."
        )
        formulas = [
            {
                "nombre": "Intensidad descriptiva de gasto público identificado",
                "version": "gasto-publico-pib-descriptivo-v1",
                "formula": "100 * gasto_publico_identificado_CLP / PIB_nominal_territorio_CLP",
                "unidad": "%",
            },
            {
                "nombre": "Identidad de consolidación bruto a neto",
                "version": "fiscal-consolidacion-v1",
                "formula": "consolidado_neto == suma(billeteras_brutas) - transferencias_internas_conciliadas",
                "unidad": "millones CLP",
            },
        ]
    else:
        hipotesis = (
            f"El desempeño territorial de {nombre_territorio} ({codigo_territorio}) combina dinámica "
            "macroeconómica real, especialización sectorial, perfil demográfico y presencia fiscal que "
            "deben evaluarse simultáneamente y sin atribución causal directa."
        )
        criterio = (
            "Integrar indicadores oficiales verificados de PIB, estructura productiva, población/per cápita "
            "y finanzas públicas, declarando explícitamente qué dimensiones están completas y cuáles pendientes."
        )
        formulas = [
            *formulas_base,
            {
                "nombre": "Índice HHI sectorial",
                "version": "estructura-hhi-v1",
                "formula": "SUM(participacion_sectorial_pct_i^2)",
                "unidad": "puntos (0-10000)",
            },
            {
                "nombre": "Intensidad descriptiva de gasto público identificado",
                "version": "gasto-publico-pib-descriptivo-v1",
                "formula": "100 * gasto_publico_identificado_CLP / PIB_nominal_territorio_CLP",
                "unidad": "%",
            },
        ]

    return {
        "hipotesis_central": hipotesis,
        "criterio_contraste": criterio,
        "formulas_aplicadas": formulas,
        "principio_causalidad": (
            "Los indicadores calculados son estrictamente descriptivos. Una correlación o razón elevada "
            "no demuestra causalidad sin un diseño de identificación contrafactual y análisis de sensibilidad."
        ),
    }


def _construir_tabla_evidencia(
    territorio: str,
    nombre_territorio: str,
    pib_info: dict[str, Any],
    sec_info: dict[str, Any],
    dem_info: dict[str, Any],
    dipres_info: dict[str, Any],
    sinim_info: dict[str, Any],
) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []

    if pib_info.get("disponible"):
        ult = str(pib_info["ultimo_anio"])
        periodo = f"{pib_info['periodo'][0]}–{pib_info['periodo'][1]}"
        corte = pib_info.get("corte_id") or "BCCh-BDE"
        filas.append(
            {
                "dimension": "Macroeconomía (PIB)",
                "indicador": "PIB nominal anual",
                "territorio": f"{territorio} · {nombre_territorio}",
                "periodo": ult,
                "valor": pib_info["pib_nominal_ultimo_millones"],
                "unidad": "millones CLP",
                "estado": "oficial",
                "fuente": f"BCCh BDE ({corte})",
                "nota": "Precios corrientes",
            }
        )
        filas.append(
            {
                "dimension": "Macroeconomía (PIB)",
                "indicador": "PIB real anual (volúmenes encadenados base 2018)",
                "territorio": f"{territorio} · {nombre_territorio}",
                "periodo": ult,
                "valor": pib_info["pib_real_ultimo_millones"],
                "unidad": "millones CLP (base 2018)",
                "estado": "oficial",
                "fuente": f"BCCh BDE ({corte})",
                "nota": "No aditivo entre regiones fuera de 2018",
            }
        )
        filas.append(
            {
                "dimension": "Macroeconomía (PIB)",
                "indicador": "Crecimiento real anual",
                "territorio": f"{territorio} · {nombre_territorio}",
                "periodo": ult,
                "valor": pib_info["crecimiento_real_ultimo_anio_pct"],
                "unidad": "%",
                "estado": "oficial",
                "fuente": f"BCCh BDE ({corte})",
                "nota": f"Referencia Chile ({ult}): {pib_info['crecimiento_real_chile_ultimo_anio_pct']}%",
            }
        )
        filas.append(
            {
                "dimension": "Macroeconomía (PIB)",
                "indicador": "Crecimiento real acumulado",
                "territorio": f"{territorio} · {nombre_territorio}",
                "periodo": periodo,
                "valor": pib_info["crecimiento_real_acumulado_pct"],
                "unidad": "%",
                "estado": "oficial",
                "fuente": f"BCCh BDE ({corte})",
                "nota": f"Referencia Chile ({periodo}): {pib_info['crecimiento_real_acumulado_chile_pct']}%",
            }
        )
        if territorio != "CL":
            filas.append(
                {
                    "dimension": "Macroeconomía (PIB)",
                    "indicador": "Participación en el PIB nominal de Chile",
                    "territorio": f"{territorio} · {nombre_territorio}",
                    "periodo": ult,
                    "valor": pib_info["participacion_nacional_pct"],
                    "unidad": "%",
                    "estado": "oficial",
                    "fuente": f"BCCh BDE ({corte})",
                    "nota": "Precios corrientes del mismo corte",
                }
            )
    else:
        filas.append(
            {
                "dimension": "Macroeconomía (PIB)",
                "indicador": "PIB anual oficial",
                "territorio": f"{territorio} · {nombre_territorio}",
                "periodo": "2013–2025",
                "valor": None,
                "unidad": "millones CLP",
                "estado": "pendiente",
                "fuente": "BCCh BDE",
                "nota": pib_info.get("motivo", "Corte PIB pendiente"),
            }
        )

    if sec_info.get("disponible"):
        anio_sec = str(sec_info.get("anio") or "")
        fuente_sec = f"BCCh CCNN ({sec_info.get('fuente_archivo')})"
        if sec_info.get("hhi") is not None:
            filas.append(
                {
                    "dimension": "Estructura productiva",
                    "indicador": "Concentración sectorial (HHI)",
                    "territorio": f"{territorio} · {nombre_territorio}",
                    "periodo": anio_sec,
                    "valor": sec_info["hhi"],
                    "unidad": "puntos (0-10000)",
                    "estado": "oficial",
                    "fuente": fuente_sec,
                    "nota": f"{sec_info.get('actividades_contabilizadas')} actividades nominales",
                }
            )
        act_prin = sec_info.get("actividad_principal")
        if isinstance(act_prin, Mapping):
            filas.append(
                {
                    "dimension": "Estructura productiva",
                    "indicador": f"Actividad principal: {act_prin.get('nombre')}",
                    "territorio": f"{territorio} · {nombre_territorio}",
                    "periodo": anio_sec,
                    "valor": act_prin.get("participacion_pct"),
                    "unidad": "% del PIB nominal",
                    "estado": "oficial",
                    "fuente": fuente_sec,
                    "nota": f"Valor nominal: {act_prin.get('valor_millones')} millones CLP",
                }
            )
        adm = sec_info.get("administracion_publica")
        if isinstance(adm, Mapping):
            filas.append(
                {
                    "dimension": "Dependencia estatal · Plano (a) CCNN",
                    "indicador": "Actividad Administración Pública (CCNN)",
                    "territorio": f"{territorio} · {nombre_territorio}",
                    "periodo": anio_sec,
                    "valor": adm.get("participacion_pct"),
                    "unidad": "% del PIB nominal",
                    "estado": "oficial",
                    "fuente": fuente_sec,
                    "nota": f"Valor agregado nominal: {adm.get('valor_millones')} millones CLP (no equivale a gasto presupuestario)",
                }
            )
    else:
        filas.append(
            {
                "dimension": "Estructura productiva",
                "indicador": "Desglose sectorial y HHI",
                "territorio": f"{territorio} · {nombre_territorio}",
                "periodo": "2013–2025",
                "valor": None,
                "unidad": "% / puntos HHI",
                "estado": "pendiente",
                "fuente": "BCCh BDE (pib-sectorial-16-regiones.json)",
                "nota": sec_info.get("motivo", "Corte sectorial pendiente"),
            }
        )

    if dem_info.get("disponible"):
        anio_dem = str(dem_info.get("anio_referencia_cruce") or "")
        filas.append(
            {
                "dimension": "Demografía y per cápita",
                "indicador": "Población oficial INE",
                "territorio": f"{territorio} · {nombre_territorio}",
                "periodo": anio_dem,
                "valor": dem_info.get("poblacion_ultimo_cruce"),
                "unidad": "habitantes",
                "estado": "oficial",
                "fuente": "INE / BCCh BDE",
                "nota": f"Cobertura poblacional: {dem_info['periodo_poblacion'][0]}–{dem_info['periodo_poblacion'][1]}",
            }
        )
        filas.append(
            {
                "dimension": "Demografía y per cápita",
                "indicador": "PIB per cápita real",
                "territorio": f"{territorio} · {nombre_territorio}",
                "periodo": anio_dem,
                "valor": dem_info.get("pib_per_capita_real_clp"),
                "unidad": "CLP base 2018 / hab",
                "estado": "oficial",
                "fuente": "Cruce BCCh PIB + INE población",
                "nota": f"Índice vs Chile=100: {dem_info.get('indice_pib_pc_real_vs_chile_100')}",
            }
        )
        if dem_info.get("sigma_convergencia_ultimo"):
            sig = dem_info["sigma_convergencia_ultimo"]
            filas.append(
                {
                    "dimension": "Demografía y per cápita",
                    "indicador": "σ-convergencia (dispersión interregional)",
                    "territorio": "16 regiones de Chile",
                    "periodo": str(sig["anio"]),
                    "valor": sig["sigma_ln_pib_pc_real"],
                    "unidad": "std(ln PIB pc real)",
                    "estado": "oficial",
                    "fuente": "Cruce BCCh PIB + INE población",
                    "nota": f"Calculado sobre {sig['regiones_incluidas']} regiones",
                }
            )
    else:
        filas.append(
            {
                "dimension": "Demografía y per cápita",
                "indicador": "Población INE, PIB per cápita y σ-convergencia",
                "territorio": f"{territorio} · {nombre_territorio}",
                "periodo": "2013–2030",
                "valor": None,
                "unidad": "habitantes / CLP por hab",
                "estado": "pendiente",
                "fuente": "INE (poblacion-ine-regiones.json)",
                "nota": dem_info.get("motivo", "Corte demográfico pendiente"),
            }
        )

    if dipres_info.get("disponible"):
        anio_dip = str(dipres_info.get("anio") or "")
        filas.append(
            {
                "dimension": "Dependencia estatal · Plano (b) Presupuestario",
                "indicador": "Gasto directo Gobierno Central identificado (DIPRES CKAN)",
                "territorio": f"{territorio} · {nombre_territorio}",
                "periodo": anio_dip,
                "valor": dipres_info.get("total_gasto_directo_millones"),
                "unidad": "millones CLP",
                "estado": "oficial",
                "fuente": f"DIPRES CKAN ({dipres_info.get('corte_id')})",
                "nota": (
                    f"Etapa: {dipres_info.get('etapa_informada')}; "
                    f"ratio descriptivo sobre PIB nominal: {dipres_info.get('ratio_gasto_directo_sobre_pib_nominal_pct')}%"
                ),
            }
        )
        filas.append(
            {
                "dimension": "Finanzas públicas · Billetera regional",
                "indicador": "Financiamiento GORE Partida 31",
                "territorio": f"{territorio} · {nombre_territorio}",
                "periodo": anio_dip,
                "valor": dipres_info.get("financiamiento_gore_p31_millones"),
                "unidad": "millones CLP",
                "estado": "oficial",
                "fuente": f"DIPRES CKAN ({dipres_info.get('corte_id')})",
                "nota": "Transferencias de financiamiento registradas separadamente para evitar doble conteo",
            }
        )
    else:
        filas.append(
            {
                "dimension": "Dependencia estatal · Plano (b) Presupuestario",
                "indicador": "Ejecución presupuestaria DIPRES",
                "territorio": f"{territorio} · {nombre_territorio}",
                "periodo": "2025",
                "valor": None,
                "unidad": "millones CLP",
                "estado": dipres_info.get("estado", "pendiente"),
                "fuente": "DIPRES · datos.gob.cl",
                "nota": dipres_info.get("motivo", "Corte DIPRES pendiente"),
            }
        )

    if sinim_info.get("disponible"):
        filas.append(
            {
                "dimension": "Finanzas públicas · Billetera municipal",
                "indicador": "Gasto total devengado municipal (SINIM)",
                "territorio": f"{territorio} · {nombre_territorio}",
                "periodo": str(sinim_info.get("anio") or ""),
                "valor": sinim_info.get("total_gasto_devengado_millones"),
                "unidad": "millones CLP",
                "estado": "oficial",
                "fuente": "SINIM · SUBDERE (importación local)",
                "nota": (
                    f"{sinim_info.get('comunas_cargadas')}/{sinim_info.get('comunas_esperadas')} comunas; "
                    "vista bruta municipal (no sumar sin conciliar transferencias internas)"
                ),
            }
        )
    else:
        filas.append(
            {
                "dimension": "Finanzas públicas · Billetera municipal",
                "indicador": "Gasto municipal devengado (SINIM)",
                "territorio": f"{territorio} · {nombre_territorio}",
                "periodo": "Pendiente",
                "valor": None,
                "unidad": "millones CLP",
                "estado": sinim_info.get("estado", "pendiente"),
                "fuente": "SINIM · SUBDERE",
                "nota": sinim_info.get("motivo", "Importación SINIM pendiente"),
            }
        )

    filas.append(
        {
            "dimension": "Dependencia estatal · Plano (c) Laboral",
            "indicador": "Empleo público sobre ocupación total",
            "territorio": f"{territorio} · {nombre_territorio}",
            "periodo": "Pendiente",
            "valor": None,
            "unidad": "% de ocupados",
            "estado": "pendiente",
            "fuente": "INE (ENE · microdatos / dominios oficiales)",
            "nota": "Pendiente de integración de microdatos ENE INE y clasificador empleo público/privado",
        }
    )

    return filas


def _construir_hipotesis_alternativas(
    territorio: str,
    nombre_territorio: str,
    pib_info: dict[str, Any],
    sec_info: dict[str, Any],
    dem_info: dict[str, Any],
    dipres_info: dict[str, Any],
) -> dict[str, list[str]]:
    favorable: list[str] = []
    contraria: list[str] = []
    alternativas: list[str] = [
        (
            "Efecto base y tamaño económico: territorios con baja participación en el PIB nacional "
            "registran variaciones porcentuales más pronunciadas ante shocks sectoriales o proyectos puntuales."
        ),
        (
            "Geografía de ejecución vs. sede administrativa: imputar gasto público o ventas según domicilio "
            "institucional puede distorsionar la intensidad fiscal o productiva observada en un territorio."
        ),
        (
            "Ciclos de precios y productividad sectorial: en economías especializadas en recursos naturales "
            "o acuicultura, las oscilaciones nominales reflejan tanto precios internacionales como volúmenes."
        ),
    ]

    if pib_info.get("disponible"):
        ult = pib_info["ultimo_anio"]
        crec_t = _a_decimal(pib_info.get("crecimiento_real_ultimo_anio_pct"))
        crec_c = _a_decimal(pib_info.get("crecimiento_real_chile_ultimo_anio_pct"))
        acum_t = _a_decimal(pib_info.get("crecimiento_real_acumulado_pct"))
        acum_c = _a_decimal(pib_info.get("crecimiento_real_acumulado_chile_pct"))
        if crec_t is not None and crec_c is not None:
            if territorio != "CL" and crec_t > crec_c:
                favorable.append(
                    f"En {ult}, {nombre_territorio} registró un crecimiento real de {pib_info['crecimiento_real_ultimo_anio_pct']}%, "
                    f"superior al promedio nacional ({pib_info['crecimiento_real_chile_ultimo_anio_pct']}%)."
                )
            elif territorio != "CL":
                contraria.append(
                    f"En {ult}, {nombre_territorio} creció {pib_info['crecimiento_real_ultimo_anio_pct']}% en términos reales, "
                    f"por debajo o igual al promedio de Chile ({pib_info['crecimiento_real_chile_ultimo_anio_pct']}%)."
                )
            else:
                favorable.append(
                    f"En {ult}, Chile registró un crecimiento real del PIB de {pib_info['crecimiento_real_ultimo_anio_pct']}%."
                )
        if acum_t is not None and acum_c is not None and territorio != "CL":
            favorable.append(
                f"Entre {pib_info['periodo'][0]} y {ult}, la variación real acumulada de {nombre_territorio} "
                f"fue {pib_info['crecimiento_real_acumulado_pct']}% frente a {pib_info['crecimiento_real_acumulado_chile_pct']}% en Chile."
            )
        if pib_info.get("anios_negativos", 0) > 0:
            contraria.append(
                f"La serie {pib_info['periodo'][0]}–{ult} presenta {pib_info['anios_negativos']} año(s) "
                "de contracción real, lo que impide extrapolar el desempeño del último ejercicio como tendencia estable."
            )

    if sec_info.get("disponible"):
        act = sec_info.get("actividad_principal")
        if isinstance(act, Mapping) and act.get("participacion_pct") is not None:
            favorable.append(
                f"La estructura nominal se concentra en '{act['nombre']}' ({act['participacion_pct']}% del PIB) "
                f"con un índice HHI de {sec_info.get('hhi')} puntos."
            )
        adm = sec_info.get("administracion_publica")
        if isinstance(adm, Mapping) and adm.get("participacion_pct") is not None:
            favorable.append(
                f"La actividad CCNN 'Administración pública' representa {adm['participacion_pct']}% del PIB nominal "
                f"({adm.get('valor_millones')} millones CLP)."
            )
            contraria.append(
                "El valor agregado de Administración Pública en Cuentas Nacionales no equivale al gasto "
                "presupuestario total ni incluye empleo público fuera de esa rama; interpretarlo como dependencia "
                "global sobrestima o subestima el rol fiscal según el perímetro."
            )
    else:
        contraria.append(
            "La ausencia del corte sectorial completo de 16 regiones limita la comparación directa de "
            "especialización relativa (cociente de localización e índice de Krugman) con el resto del país."
        )

    if dipres_info.get("disponible"):
        if dipres_info.get("ratio_gasto_directo_sobre_pib_nominal_pct") is not None:
            favorable.append(
                f"El gasto directo identificado del Gobierno Central en DIPRES CKAN ({dipres_info['anio']}) "
                f"equivale descriptivamente a {dipres_info['ratio_gasto_directo_sobre_pib_nominal_pct']}% del PIB nominal regional."
            )
        contraria.append(
            "La ejecución DIPRES CKAN excluye partidas nacionales no regionalizadas y aún no consolida "
            "documentalmente transferencias internas hacia GORE y municipalidades (SINIM)."
        )

    if dem_info.get("disponible"):
        favorable.append(
            f"Con población oficial INE ({dem_info.get('poblacion_ultimo_cruce')} hab.), el PIB per cápita real "
            f"alcanzó {dem_info.get('pib_per_capita_real_clp')} CLP (base 2018)."
        )
    else:
        contraria.append(
            "Sin el corte oficial de población INE publicado en disco, no es posible ajustar niveles "
            "agregados por tamaño demográfico ni verificar σ-convergencia."
        )

    if not favorable:
        favorable.append(
            "Existen cortes oficiales en modo solo lectura disponibles para auditoría, pero la cobertura "
            "temática para el territorio consultado requiere completar fuentes pendientes."
        )
    if not contraria:
        contraria.append(
            "La evidencia disponible es descriptiva y carece de un contrafactual que permita atribución causal."
        )

    return {
        "evidencia_favorable": favorable,
        "evidencia_contraria": contraria,
        "explicaciones_alternativas_no_causales": alternativas,
    }


def _construir_interpretacion(
    eje: str,
    territorio: str,
    nombre_territorio: str,
    pib_info: dict[str, Any],
    sec_info: dict[str, Any],
    dem_info: dict[str, Any],
    dipres_info: dict[str, Any],
    limitaciones_pendientes: list[str],
) -> dict[str, str]:
    partes: list[str] = []

    if pib_info.get("disponible"):
        ult = pib_info["ultimo_anio"]
        texto_pib = (
            f"Con base en el corte oficial BCCh-BDE ({pib_info.get('corte_id')}), {nombre_territorio} "
            f"({territorio}) registró en {ult} un PIB nominal de {pib_info['pib_nominal_ultimo_millones']} millones CLP, "
            f"un PIB real de {pib_info['pib_real_ultimo_millones']} millones CLP (base 2018) y una variación real "
            f"anual de {pib_info['crecimiento_real_ultimo_anio_pct']}%"
        )
        if territorio != "CL" and pib_info.get("participacion_nacional_pct") is not None:
            texto_pib += (
                f", equivalentes al {pib_info['participacion_nacional_pct']}% del PIB nominal de Chile."
            )
        else:
            texto_pib += "."
        partes.append(texto_pib)
    else:
        partes.append(
            f"No se dispuso de un corte oficial de PIB legible para {nombre_territorio} ({territorio})."
        )

    if sec_info.get("disponible"):
        act = sec_info.get("actividad_principal")
        adm = sec_info.get("administracion_publica")
        texto_sec = f"En el plano sectorial ({sec_info.get('anio')}), el índice HHI alcanza {sec_info.get('hhi')} puntos"
        if isinstance(act, Mapping):
            texto_sec += f", con '{act.get('nombre')}' como actividad principal ({act.get('participacion_pct')}% del PIB nominal)"
        if isinstance(adm, Mapping):
            texto_sec += f" y 'Administración pública' (CCNN) en {adm.get('participacion_pct')}%"
        texto_sec += "."
        partes.append(texto_sec)

    if dem_info.get("disponible"):
        partes.append(
            f"Al cruzar con población oficial INE ({dem_info.get('anio_referencia_cruce')}), el PIB per cápita "
            f"real se sitúa en {dem_info.get('pib_per_capita_real_clp')} CLP (base 2018) "
            f"(índice {dem_info.get('indice_pib_pc_real_vs_chile_100')} respecto de Chile=100)."
        )

    if dipres_info.get("disponible"):
        partes.append(
            f"En el plano presupuestario (DIPRES CKAN {dipres_info.get('anio')}), el gasto directo del Gobierno "
            f"Central identificado suma {dipres_info.get('total_gasto_directo_millones')} millones CLP "
            f"({dipres_info.get('ratio_gasto_directo_sobre_pib_nominal_pct')}% descriptivo sobre PIB nominal), "
            f"adicional al registro separado de financiamiento GORE Partida 31 "
            f"({dipres_info.get('financiamiento_gore_p31_millones')} millones CLP)."
        )

    if limitaciones_pendientes:
        partes.append(
            f"Para responder íntegramente el eje '{_DESCRIPCION_EJES[eje]}', persisten {len(limitaciones_pendientes)} "
            "brecha(s) de fuentes pendientes declaradas en las limitaciones, por lo que toda conclusión "
            "debe tratarse como evidencia parcial y revisable."
        )

    if not pib_info.get("disponible"):
        nivel_certeza = "insuficiente_pendiente_fuentes"
    elif limitaciones_pendientes:
        nivel_certeza = "parcial_con_brechas"
    else:
        nivel_certeza = "descriptiva_verificada"

    return {
        "sintesis": " ".join(partes),
        "nivel_certeza": nivel_certeza,
        "advertencia_no_causalidad": (
            "Síntesis neutral de alcance estrictamente descriptivo. No implica causalidad ni valoración "
            "política; las decisiones de política pública requieren análisis contrafactual y cobertura completa."
        ),
    }


def _construir_dossier_markdown(resultado: Mapping[str, Any]) -> str:
    pf = resultado["pregunta_formulada"]
    hm = resultado["hipotesis_y_metodo"]
    ha = resultado["hipotesis_alternativas"]
    interp = resultado["interpretacion"]
    terr = pf["territorio"]

    lineas: list[str] = [
        f"# Dossier de Investigación · {terr['nombre']} ({terr['codigo']})",
        "",
        f"- **Pregunta formulada:** {pf['texto_original']}",
        f"- **Eje temático:** `{pf['eje_tematico']}` ({_DESCRIPCION_EJES[pf['eje_tematico']]})",
        f"- **Territorio:** {terr['nombre']} (`{terr['codigo']}`, nivel `{terr['nivel']}`)",
        "- **Modo de ejecución:** Solo lectura, 100% determinista, sin IA de pago y sin alteración de cortes oficiales.",
        "",
        "## 1. Pregunta y alcance",
        "",
        pf["texto_original"],
        "",
        "## 2. Variables y fuentes oficiales consultadas",
        "",
        "| Fuente | Institución | Estado | Corte / ID | Cobertura |",
        "|---|---|---|---|---|",
    ]
    for src in resultado["variables_y_fuentes"]:
        lineas.append(
            f"| `{src['codigo']}` | {src['institucion']} | `{src['estado']}` | "
            f"{src.get('corte_id') or 'pendiente'} | {src.get('cobertura') or 'n/d'} |"
        )

    lineas.extend(
        [
            "",
            "## 3. Hipótesis central y método",
            "",
            f"- **Hipótesis falsable:** {hm['hipotesis_central']}",
            f"- **Criterio de contraste:** {hm['criterio_contraste']}",
            f"- **Principio de causalidad:** {hm['principio_causalidad']}",
            "",
            "### Fórmulas aplicadas",
            "",
        ]
    )
    for f in hm["formulas_aplicadas"]:
        lineas.append(f"- **{f['nombre']}** (`{f['version']}`): `{f['formula']}` [{f['unidad']}]")

    lineas.extend(
        [
            "",
            "## 4. Consultas verificadas (solo lectura)",
            "",
        ]
    )
    for q in resultado["consultas_verificadas"]:
        lineas.append(
            f"- **{q['id']}** (`{q['estado']}`, modo `{q['modo']}`): `{q['ruta_o_endpoint']}` "
            f"— registros leídos: `{q['registros_leidos']}` (corte: `{q.get('corte_id') or 'pendiente'}`)"
        )

    lineas.extend(
        [
            "",
            "## 5. Tabla de evidencia reproducible",
            "",
            "| Dimensión | Indicador | Territorio | Período | Valor | Unidad | Estado | Fuente |",
            "|---|---|---|---|---:|---|---|---|",
        ]
    )
    for row in resultado["tabla_evidencia"]:
        val_str = row["valor"] if row["valor"] is not None else "pendiente"
        lineas.append(
            f"| {row['dimension']} | {row['indicador']} | {row['territorio']} | {row['periodo']} | "
            f"{val_str} | {row['unidad']} | `{row['estado']}` | {row['fuente']} |"
        )

    lineas.extend(
        [
            "",
            "## 6. Hipótesis alternativas y contraste de evidencia",
            "",
            "### Evidencia favorable",
            "",
        ]
    )
    for item in ha["evidencia_favorable"]:
        lineas.append(f"- {item}")

    lineas.extend(["", "### Evidencia contraria y matices", ""])
    for item in ha["evidencia_contraria"]:
        lineas.append(f"- {item}")

    lineas.extend(["", "### Explicaciones alternativas no causales", ""])
    for item in ha["explicaciones_alternativas_no_causales"]:
        lineas.append(f"- {item}")

    lineas.extend(
        [
            "",
            "## 7. Interpretación neutral",
            "",
            interp["sintesis"],
            "",
            f"> **Advertencia metodológica:** {interp['advertencia_no_causalidad']}",
            "",
            "## 8. Limitaciones y fuentes pendientes",
            "",
        ]
    )
    for lim in resultado["limitaciones"]:
        lineas.append(f"- {lim}")

    lineas.extend(
        [
            "",
            "## 9. Citas y trazabilidad",
            "",
            "- Banco Central de Chile (BCCh) — Base de Datos Estadísticos (BDE SI3), Cuentas Nacionales base 2018.",
            "- Instituto Nacional de Estadísticas (INE) — Proyecciones poblacionales y Encuesta Nacional de Empleo (ENE).",
            "- Dirección de Presupuestos (DIPRES · Ministerio de Hacienda) — Ejecución Presupuestaria vía `datos.gob.cl` CKAN.",
            "- Subsecretaría de Desarrollo Regional y Administrativo (SUBDERE) — Sistema Nacional de Información Municipal (SINIM).",
            "",
        ]
    )
    return "\n".join(lineas)


def ejecutar_investigacion(
    pregunta: str,
    territorio: str = "11",
    *,
    ruta_pib: Path | None = None,
    ruta_sectorial: Path | None = None,
    ruta_poblacion: Path | None = None,
    ruta_dipres: Path | None = None,
    ruta_sinim: Path | None = None,
) -> dict[str, Any]:
    """Ejecuta el protocolo metodológico de 10 pasos en modo estrictamente solo lectura."""
    pregunta_limpia = (pregunta or "").strip()
    if len(pregunta_limpia) < 5 or len(pregunta_limpia) > 600:
        raise ValueError("La pregunta debe contener entre 5 y 600 caracteres.")

    codigo_terr = (territorio or "").strip().upper()
    if not _CODIGO_VALIDO.fullmatch(codigo_terr):
        raise ValueError(
            "El código territorial debe ser 'CL' o una región oficial entre '01' y '16'."
        )
    nombre_terr, nivel_terr = _CATALOGO_TERRITORIOS[codigo_terr]

    eje_tematico, palabras_clave = _clasificar_pregunta(pregunta_limpia)
    rutas = _resolver_rutas(
        ruta_pib=ruta_pib,
        ruta_sectorial=ruta_sectorial,
        ruta_poblacion=ruta_poblacion,
        ruta_dipres=ruta_dipres,
        ruta_sinim=ruta_sinim,
    )

    # Lecturas estrictamente de solo lectura
    pib_path, _ = rutas["pib"]
    sec_path, sec_explicito = rutas["sectorial"]
    pob_path, _ = rutas["poblacion"]
    dip_path, dip_explicito = rutas["dipres"]
    sin_path, sin_explicito = rutas["sinim"]

    datos_pib, err_pib = _leer_json_seguro(pib_path)
    datos_sec_16, err_sec_16 = _leer_json_seguro(sec_path)
    datos_pob, err_pob = _leer_json_seguro(pob_path)
    datos_dipres, err_dipres = _leer_json_seguro(dip_path)
    datos_sinim, err_sinim = _leer_json_seguro(sin_path)

    pib_info = _analizar_pib(datos_pib, codigo_terr)
    if err_pib:
        pib_info["motivo"] = err_pib

    # Sectorial: prioriza corte 16 regiones; si no fue pasado explícitamente y es Aysén, lee corte live oficial en disco
    sec_info: dict[str, Any]
    uso_sec_aysen_live = False
    sec_16_disponible = datos_sec_16 is not None
    if datos_sec_16 is not None:
        extraido_16 = _extraer_sectorial_desde_16_regiones(
            datos_sec_16, codigo_terr, _ruta_relativa_segura(sec_path) or sec_path.name
        )
        if extraido_16 is not None:
            sec_info = extraido_16
        else:
            sec_info = {
                "disponible": False,
                "estado": "pendiente",
                "motivo": f"El corte sectorial no contiene desglose para el territorio '{codigo_terr}'.",
                "registros_leidos": 0,
            }
    elif not sec_explicito and codigo_terr == "11" and RUTA_SECTORIAL_AYSEN_RAW.is_file():
        datos_aysen_live, _ = _leer_json_seguro(RUTA_SECTORIAL_AYSEN_RAW)
        if datos_aysen_live is not None:
            sec_info = _extraer_sectorial_aysen_live(
                datos_aysen_live, _ruta_relativa_segura(RUTA_SECTORIAL_AYSEN_RAW) or RUTA_SECTORIAL_AYSEN_RAW.name
            )
            uso_sec_aysen_live = True
        else:
            sec_info = {
                "disponible": False,
                "estado": "pendiente",
                "motivo": "No se encontró corte sectorial oficial legible en disco.",
                "registros_leidos": 0,
            }
    else:
        sec_info = {
            "disponible": False,
            "estado": "pendiente",
            "motivo": err_sec_16
            or "Corte sectorial de 16 regiones pendiente de extracción (data/published/pib-sectorial-16-regiones.json).",
            "registros_leidos": 0,
        }

    dem_info = _analizar_demografia(datos_pob, pib_info, codigo_terr)
    if err_pob:
        dem_info["motivo"] = err_pob

    dipres_info = _analizar_dipres(datos_dipres, pib_info, codigo_terr, dip_explicito)
    if err_dipres:
        dipres_info["motivo"] = err_dipres

    sinim_info = _analizar_sinim(datos_sinim, codigo_terr, sin_explicito)
    if err_sinim:
        sinim_info["motivo"] = err_sinim

    # 1. pregunta_formulada
    pregunta_formulada = {
        "texto_original": pregunta_limpia,
        "texto_normalizado": _normalizar_texto(pregunta_limpia),
        "territorio": {
            "codigo": codigo_terr,
            "nombre": nombre_terr,
            "nivel": nivel_terr,
        },
        "eje_tematico": eje_tematico,
        "descripcion_eje": _DESCRIPCION_EJES[eje_tematico],
        "palabras_clave_detectadas": palabras_clave,
        "modo_ejecucion": "solo_lectura_determinista",
    }

    # 2. variables_y_fuentes
    variables_y_fuentes = [
        {
            "codigo": "pib_oficial_bcch",
            "institucion": "Banco Central de Chile (BDE SI3)",
            "estado": pib_info["estado"],
            "archivo": _ruta_relativa_segura(pib_path),
            "corte_id": pib_info.get("corte_id"),
            "fecha_corte": pib_info.get("fecha_corte"),
            "cobertura": (
                f"{pib_info['periodo'][0]}–{pib_info['periodo'][1]}"
                if pib_info.get("disponible")
                else "pendiente"
            ),
            "variables": [
                "pib_nominal_millones",
                "pib_real_millones",
                "crecimiento_real_anual_pct",
                "participacion_nacional_pct",
            ],
        },
        {
            "codigo": "sectorial_16_regiones_bcch",
            "institucion": "Banco Central de Chile (BDE SI3 · CCNN 2018)",
            "estado": "disponible" if sec_16_disponible else "pendiente",
            "archivo": _ruta_relativa_segura(sec_path),
            "corte_id": sec_info.get("corte_id") if sec_16_disponible else None,
            "fecha_corte": sec_info.get("fecha_corte") if sec_16_disponible else None,
            "cobertura": f"16 regiones ({sec_info.get('anio')})" if sec_16_disponible else "pendiente",
            "variables": ["va_nominal_actividad", "participacion_sectorial_pct", "hhi", "lq", "krugman"],
        },
    ]
    if uso_sec_aysen_live:
        variables_y_fuentes.append(
            {
                "codigo": "sectorial_aysen_bcch_live",
                "institucion": "Banco Central de Chile (BDE SI3 · Corte Aysén)",
                "estado": "disponible",
                "archivo": _ruta_relativa_segura(RUTA_SECTORIAL_AYSEN_RAW),
                "corte_id": sec_info.get("corte_id"),
                "fecha_corte": sec_info.get("fecha_corte"),
                "cobertura": f"Región 11 ({sec_info.get('anio')})",
                "variables": [
                    "13_actividades_nominales_aysen",
                    "administracion_publica_ccnn",
                    "pesca_ccnn",
                    "hhi_aysen",
                ],
            }
        )
    variables_y_fuentes.extend(
        [
            {
                "codigo": "poblacion_ine",
                "institucion": "Instituto Nacional de Estadísticas (INE) / BCCh BDE",
                "estado": dem_info["estado"],
                "archivo": _ruta_relativa_segura(pob_path),
                "corte_id": dem_info.get("corte_id"),
                "fecha_corte": dem_info.get("fecha_corte"),
                "cobertura": (
                    f"{dem_info['periodo_poblacion'][0]}–{dem_info['periodo_poblacion'][1]}"
                    if dem_info.get("disponible")
                    else "pendiente"
                ),
                "variables": ["poblacion_regional", "pib_per_capita_real", "pib_per_capita_nominal", "sigma_convergencia"],
            },
            {
                "codigo": "fiscal_dipres_ckan",
                "institucion": "DIPRES · Ministerio de Hacienda (datos.gob.cl CKAN)",
                "estado": dipres_info["estado"],
                "archivo": _ruta_relativa_segura(dip_path),
                "corte_id": dipres_info.get("corte_id"),
                "fecha_corte": dipres_info.get("fecha_corte"),
                "cobertura": f"Región {dipres_info.get('region_codigo')} ({dipres_info.get('anio')})"
                if dipres_info.get("disponible")
                else dipres_info["estado"],
                "variables": [
                    "gasto_corriente_sub_21_26",
                    "inversion_sub_29_31",
                    "transferencias_capital_sub_33",
                    "financiamiento_gore_p31",
                ],
            },
            {
                "codigo": "fiscal_sinim_municipal",
                "institucion": "SUBDERE · SINIM (importación oficial local)",
                "estado": sinim_info["estado"],
                "archivo": _ruta_relativa_segura(sin_path),
                "corte_id": sinim_info.get("corte_id"),
                "fecha_corte": sinim_info.get("fecha_corte"),
                "cobertura": f"{sinim_info.get('comunas_cargadas')}/10 comunas ({sinim_info.get('anio')})"
                if sinim_info.get("disponible")
                else sinim_info["estado"],
                "variables": ["ingresos_municipales", "gasto_total_devengado_municipal", "inversion_municipal"],
            },
            {
                "codigo": "empleo_publico_ine",
                "institucion": "INE · Encuesta Nacional de Empleo (ENE)",
                "estado": "pendiente",
                "archivo": None,
                "corte_id": None,
                "fecha_corte": None,
                "cobertura": "pendiente",
                "variables": ["ocupados_sector_publico", "ocupados_totales"],
            },
        ]
    )

    # 3. hipotesis_y_metodo
    hipotesis_y_metodo = _construir_hipotesis_y_metodo(eje_tematico, nombre_terr, codigo_terr)

    # 4. consultas_verificadas
    consultas_verificadas = [
        {
            "id": "Q1",
            "fuente": "pib_oficial_bcch",
            "modo": "solo_lectura",
            "ruta_o_endpoint": "GET /api/v1/pib",
            "filtros": {"territorio": codigo_terr, "referencia": "CL"},
            "estado": "verificada" if pib_info.get("disponible") else "pendiente",
            "registros_leidos": pib_info.get("registros_leidos", 0),
            "corte_id": pib_info.get("corte_id"),
        },
        {
            "id": "Q2",
            "fuente": "sectorial_aysen_bcch_live" if uso_sec_aysen_live else "sectorial_16_regiones_bcch",
            "modo": "solo_lectura",
            "ruta_o_endpoint": (
                "GET /api/v1/territorial/aysen/estructura"
                if uso_sec_aysen_live
                else "GET /api/v1/sectorial/regiones"
            ),
            "filtros": {"territorio": codigo_terr},
            "estado": "verificada" if sec_info.get("disponible") else "pendiente",
            "registros_leidos": sec_info.get("registros_leidos", 0),
            "corte_id": sec_info.get("corte_id"),
        },
        {
            "id": "Q3",
            "fuente": "poblacion_ine",
            "modo": "solo_lectura",
            "ruta_o_endpoint": "GET /api/v1/demografia/poblacion",
            "filtros": {"territorio": codigo_terr},
            "estado": "verificada" if dem_info.get("disponible") else "pendiente",
            "registros_leidos": dem_info.get("registros_leidos", 0),
            "corte_id": dem_info.get("corte_id"),
        },
        {
            "id": "Q4",
            "fuente": "fiscal_dipres_ckan",
            "modo": "solo_lectura",
            "ruta_o_endpoint": "GET /api/v1/fiscal/dipres",
            "filtros": {"territorio": codigo_terr},
            "estado": (
                "verificada"
                if dipres_info.get("disponible")
                else ("no_aplicable" if dipres_info.get("estado") == "no_aplica_territorio" else "pendiente")
            ),
            "registros_leidos": dipres_info.get("registros_leidos", 0),
            "corte_id": dipres_info.get("corte_id"),
        },
        {
            "id": "Q5",
            "fuente": "fiscal_sinim_municipal",
            "modo": "solo_lectura",
            "ruta_o_endpoint": "GET /api/v1/fiscal/sinim",
            "filtros": {"territorio": codigo_terr},
            "estado": (
                "verificada"
                if sinim_info.get("disponible")
                else ("no_aplicable" if sinim_info.get("estado") == "no_aplica_territorio" else "pendiente")
            ),
            "registros_leidos": sinim_info.get("registros_leidos", 0),
            "corte_id": sinim_info.get("corte_id"),
        },
    ]

    # Limpia claves internas antes de exponer resultados_reproducibles
    pib_publico = {k: v for k, v in pib_info.items() if not k.startswith("_")}

    dependencia_estatal_matriz = {
        "actividad_economica_administracion_publica": (
            {
                "disponible": True,
                "estado": "disponible",
                "fuente": "BCCh CCNN",
                "anio": sec_info.get("anio"),
                "participacion_pib_pct": sec_info["administracion_publica"].get("participacion_pct"),
                "valor_millones_clp": sec_info["administracion_publica"].get("valor_millones"),
                "nota": "Valor agregado de la rama Administración Pública en Cuentas Nacionales; no es gasto fiscal total.",
            }
            if sec_info.get("disponible") and isinstance(sec_info.get("administracion_publica"), Mapping)
            else {
                "disponible": False,
                "estado": "pendiente",
                "fuente": "BCCh CCNN",
                "motivo": sec_info.get("motivo", "Corte sectorial pendiente para el territorio."),
            }
        ),
        "gasto_publico_presupuestario": (
            {
                "disponible": True,
                "estado": "disponible",
                "fuente": "DIPRES CKAN" + (" + SINIM" if sinim_info.get("disponible") else " (SINIM pendiente)"),
                "anio": dipres_info.get("anio"),
                "gasto_directo_gobierno_central_millones": dipres_info.get("total_gasto_directo_millones"),
                "financiamiento_gore_p31_millones": dipres_info.get("financiamiento_gore_p31_millones"),
                "ratio_descriptivo_sobre_pib_nominal_pct": dipres_info.get("ratio_gasto_directo_sobre_pib_nominal_pct"),
                "sinim_gasto_devengado_millones": (
                    sinim_info.get("total_gasto_devengado_millones") if sinim_info.get("disponible") else None
                ),
                "nota": "Perímetro presupuestario distinto del valor agregado CCNN; vistas brutas no consolidadas.",
            }
            if dipres_info.get("disponible")
            else {
                "disponible": False,
                "estado": dipres_info.get("estado", "pendiente"),
                "fuente": "DIPRES CKAN / SINIM",
                "motivo": dipres_info.get("motivo"),
            }
        ),
        "empleo_publico": {
            "disponible": False,
            "estado": "pendiente",
            "fuente": "INE (ENE · microdatos / dominios oficiales)",
            "motivo": (
                "Pendiente de integración de microdatos ENE/INE y clasificador oficial de "
                "empleo público vs privado con dominios representativos."
            ),
        },
    }

    # 5. resultados_reproducibles
    resultados_reproducibles = {
        "pib": pib_publico,
        "estructura_sectorial": sec_info,
        "demografia_y_per_capita": dem_info,
        "finanzas_publicas": {
            "dipres": dipres_info,
            "sinim": sinim_info,
        },
        "dependencia_estatal_matriz": dependencia_estatal_matriz,
    }

    # 6. tabla_evidencia
    tabla_evidencia = _construir_tabla_evidencia(
        codigo_terr, nombre_terr, pib_publico, sec_info, dem_info, dipres_info, sinim_info
    )

    # 7. hipotesis_alternativas
    hipotesis_alternativas = _construir_hipotesis_alternativas(
        codigo_terr, nombre_terr, pib_publico, sec_info, dem_info, dipres_info
    )

    # 9. limitaciones (calculadas antes de interpretación para reportar brechas exactas)
    limitaciones_pendientes: list[str] = []
    if not pib_publico.get("disponible"):
        limitaciones_pendientes.append(
            f"Fuente pendiente: PIB oficial BCCh ({pib_publico.get('motivo')})."
        )
    if not sec_16_disponible:
        limitaciones_pendientes.append(
            "Fuente pendiente: corte sectorial completo de 16 regiones (`data/published/pib-sectorial-16-regiones.json`) aún no publicado en disco."
        )
    if not dem_info.get("disponible"):
        limitaciones_pendientes.append(
            "Fuente pendiente: proyecciones poblacionales oficiales INE (`data/published/poblacion-ine-regiones.json`) aún no publicadas en disco."
        )
    if not dipres_info.get("disponible"):
        limitaciones_pendientes.append(
            f"Fuente pendiente/parcial DIPRES: {dipres_info.get('motivo')}"
        )
    if not sinim_info.get("disponible"):
        limitaciones_pendientes.append(
            f"Fuente pendiente SINIM municipal: {sinim_info.get('motivo')}"
        )
    limitaciones_pendientes.append(
        "Fuente pendiente: empleo público oficial (ENE/microdatos INE) aún no integrado; no se infiere desde CCNN ni desde presupuesto."
    )

    limitaciones = [
        (
            "No aditividad de volúmenes encadenados: los niveles de PIB real (referencia 2018) no "
            "suman exactamente el total nacional fuera del año de referencia; utilice siempre el agregado oficial."
        ),
        (
            "Redondeo y precisión: los cálculos internos emplean aritmética exacta Decimal (34 dígitos) "
            "y los resultados visibles se presentan redondeados a 2 decimales (o 0 en habitantes/CLP per cápita)."
        ),
        (
            "Perímetro fiscal y anti-doble contabilización: la actividad CCNN Administración Pública, "
            "el gasto presupuestario DIPRES/GORE y el gasto municipal SINIM miden conceptos distintos y no "
            "deben sumarse sin conciliación documental de transferencias internas."
        ),
        *limitaciones_pendientes,
    ]

    # 8. interpretacion
    interpretacion = _construir_interpretacion(
        eje_tematico,
        codigo_terr,
        nombre_terr,
        pib_publico,
        sec_info,
        dem_info,
        dipres_info,
        limitaciones_pendientes,
    )

    resultado: dict[str, Any] = {
        "pregunta_formulada": pregunta_formulada,
        "variables_y_fuentes": variables_y_fuentes,
        "hipotesis_y_metodo": hipotesis_y_metodo,
        "consultas_verificadas": consultas_verificadas,
        "resultados_reproducibles": resultados_reproducibles,
        "tabla_evidencia": tabla_evidencia,
        "hipotesis_alternativas": hipotesis_alternativas,
        "interpretacion": interpretacion,
        "limitaciones": limitaciones,
        "dossier_markdown": "",
    }
    # 10. dossier_markdown
    resultado["dossier_markdown"] = _construir_dossier_markdown(resultado)
    return resultado
