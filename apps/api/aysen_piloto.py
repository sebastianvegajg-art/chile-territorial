"""Endpoints del Piloto Aysén (4 pestañas):
- GET /api/v1/aysen/resumen
- GET /api/v1/aysen/economia
- GET /api/v1/aysen/presupuestos
- GET /api/v1/aysen/proyectos

Reglas metodológicas y de integridad aplicadas estrictamente:
- Aritmética exacta con ``Decimal`` (sin ``float`` en agregaciones, aportes ni ratios).
- Nunca inventar cifras: cuando falta un dato oficial para el año o corte pedido,
  devuelve ``valor: None`` y ``disponible: False`` con motivo explícito.
- Respeto estricto a la no aditividad de volúmenes reales encadenados en PIB.
- Separación explícita de territorios (Chile Nacional vs Región de Aysén vs Comuna)
  y consolidación anti-duplicación vía ``pipelines.fiscal.conciliacion.consolidar_billeteras``.
- Separación estricta de las dos preguntas de proyectos MOP (pagos de contratos anteriores
  vs arrastre presupuestario) y aislamiento de proyectos con información insuficiente.
"""

from __future__ import annotations

from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
import importlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Annotated, Any, Mapping, Sequence
import unicodedata

from fastapi import APIRouter, HTTPException, Query

RAIZ_REPO = Path(__file__).resolve().parents[2]
RUTA_PIB_API_DEFECTO = RAIZ_REPO / "data" / "published" / "pib-bde-api.json"
RUTA_PIB_PUBLICO_DEFECTO = RAIZ_REPO / "data" / "published" / "pib-bde-publico.json"
RUTA_SECTORIAL_DEFECTO = RAIZ_REPO / "data" / "published" / "pib-sectorial-16-regiones.json"
RUTA_PROYECTOS_MOP_DEFECTO = RAIZ_REPO / "data" / "published" / "proyectos-mop-aysen.json"
RUTA_SINIM_OFICIAL_DEFECTO = RAIZ_REPO / "data" / "published" / "sinim-aysen-oficial.json"
RUTA_SINIM_IMPORTADO_DEFECTO = RAIZ_REPO / "data" / "published" / "sinim-aysen-importado.json"

PREFIJO = "/api/v1/aysen"
ANIOS_DISPONIBLES: tuple[int, ...] = tuple(range(2013, 2027))

_CONTEXTO_DECIMAL = Context(prec=34, rounding=ROUND_HALF_EVEN)
_CERO = Decimal("0")
_CIEN = Decimal("100")
_MIL = Decimal("1000")
_MILLON = Decimal("1000000")

URL_BCCH_SIETE = "https://si3.bcentral.cl/Siete"
URL_BCCH_CCNN = "https://www.bcentral.cl/web/banco-central/areas/estadisticas/cuentas-nacionales"
URL_DIPRES_CKAN = "https://datos.gob.cl/organization/dipres"
URL_DIPRES_PA = "https://presupuestoabierto.gob.cl/"
URL_MOP_DGOP = "https://www.mop.gob.cl/acerca-del-mop/direccion-general-de-obras-publicas/"
URL_SINIM_FICHA_BASE = "https://datos.sinim.gov.cl/impresion_ficha_comunal.php?municipio="

_MESES_NOMBRE: dict[int, str] = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}

COMUNAS_AYSEN_LISTA: tuple[dict[str, str], ...] = (
    {"cut": "11101", "nombre": "Coyhaique"},
    {"cut": "11102", "nombre": "Lago Verde"},
    {"cut": "11201", "nombre": "Aysén"},
    {"cut": "11202", "nombre": "Cisnes"},
    {"cut": "11203", "nombre": "Guaitecas"},
    {"cut": "11301", "nombre": "Cochrane"},
    {"cut": "11302", "nombre": "O’Higgins"},
    {"cut": "11303", "nombre": "Tortel"},
    {"cut": "11401", "nombre": "Chile Chico"},
    {"cut": "11402", "nombre": "Río Ibáñez"},
)

COMUNAS_AYSEN_POR_CUT: dict[str, str] = {
    item["cut"]: item["nombre"] for item in COMUNAS_AYSEN_LISTA
}

router = APIRouter(prefix=PREFIJO, tags=["Piloto Aysén"])


# ---------------------------------------------------------------------------
# Utilidades generales (texto, rutas, Decimal, formateo ciudadano)
# ---------------------------------------------------------------------------


def _asegurar_raiz_en_path() -> None:
    raiz = str(RAIZ_REPO)
    if raiz not in sys.path:
        sys.path.insert(0, raiz)


def _normalizar_texto(valor: object) -> str:
    if valor is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(valor))
    sin_tildes = "".join(ch for ch in texto if not unicodedata.combining(ch))
    sin_apostrofe = sin_tildes.replace("’", "'").replace("'", "")
    return re.sub(r"\s+", " ", sin_apostrofe).strip().lower()


def _a_decimal(valor: object) -> Decimal | None:
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, Decimal):
        return valor if valor.is_finite() else None
    if isinstance(valor, int):
        return Decimal(valor)
    if isinstance(valor, float):
        return None
    texto = str(valor).strip()
    if not texto or texto.lower() in {"none", "null", "n/a", "na", "nd", "-", "--", "s/i"}:
        return None
    texto = texto.replace("\xa0", "").replace(" ", "")
    # Soporta formato chileno simple 1.234.567,89 o estándar 1234567.89
    if "." in texto and "," in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto and texto.count(",") == 1:
        texto = texto.replace(",", ".")
    try:
        num = Decimal(texto)
    except InvalidOperation:
        return None
    return num if num.is_finite() else None


def _a_decimal_flexible(valor: object) -> Decimal | None:
    """Acepta también float proveniente de archivos JSON externos convirtiendo vía str."""
    if isinstance(valor, float):
        import math

        if not math.isfinite(valor):
            return None
        return _a_decimal(str(valor))
    return _a_decimal(valor)


def _fmt(valor: Decimal | None, decimales: int = 2) -> str | None:
    if valor is None or not valor.is_finite():
        return None
    with localcontext(_CONTEXTO_DECIMAL):
        cuanto = Decimal("1").scaleb(-decimales)
        redondeado = valor.quantize(cuanto, rounding=ROUND_HALF_EVEN)
        texto = format(redondeado, "f")
        if texto in {"-0", "-0.0", "-0.00", "-0.000"}:
            return texto.lstrip("-")
        return texto


def _fmt_es(valor: Decimal | None, decimales: int = 1) -> str:
    """Formatea un Decimal en estilo legible en español (ej. 1.234,5)."""
    if valor is None or not valor.is_finite():
        return "sin dato"
    texto = _fmt(valor, decimales)
    if texto is None:
        return "sin dato"
    negativo = texto.startswith("-")
    cuerpo = texto[1:] if negativo else texto
    if "." in cuerpo:
        entero, frac = cuerpo.split(".", 1)
    else:
        entero, frac = cuerpo, ""
    entero_con_puntos = f"{int(entero):,}".replace(",", ".")
    signo = "-" if negativo else ""
    if decimales > 0 and frac:
        return f"{signo}{entero_con_puntos},{frac}"
    return f"{signo}{entero_con_puntos}"


def _ratio_pct(numerador: Decimal | None, denominador: Decimal | None) -> Decimal | None:
    if numerador is None or denominador is None or denominador <= _CERO:
        return None
    with localcontext(_CONTEXTO_DECIMAL):
        return (_CIEN * numerador) / denominador


def _ruta_pib_oficial() -> Path:
    personalizada = (os.getenv("CT_LOTE_OFICIAL") or "").strip()
    if personalizada:
        return Path(personalizada)
    if RUTA_PIB_API_DEFECTO.is_file():
        return RUTA_PIB_API_DEFECTO
    return RUTA_PIB_PUBLICO_DEFECTO


def _ruta_sectorial() -> Path:
    personalizada = (os.getenv("CT_SECTORIAL_PATH") or "").strip()
    return Path(personalizada) if personalizada else RUTA_SECTORIAL_DEFECTO


def _ruta_proyectos_mop() -> Path:
    personalizada = (os.getenv("CT_PROYECTOS_MOP_PATH") or "").strip()
    return Path(personalizada) if personalizada else RUTA_PROYECTOS_MOP_DEFECTO


def _ruta_sinim_oficial() -> Path:
    personalizada = (os.getenv("CT_SINIM_OFICIAL_PATH") or "").strip()
    return Path(personalizada) if personalizada else RUTA_SINIM_OFICIAL_DEFECTO


def _ruta_sinim_importado() -> Path:
    personalizada = (os.getenv("CT_SINIM_PATH") or "").strip()
    return Path(personalizada) if personalizada else RUTA_SINIM_IMPORTADO_DEFECTO


def _leer_json_opcional(ruta: Path) -> dict[str, Any] | None:
    if not ruta.is_file():
        return None
    try:
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return None
    return contenido if isinstance(contenido, dict) else None


def _url_ficha_sinim(cut: str, registro: Mapping[str, Any] | None = None) -> str:
    if isinstance(registro, Mapping):
        for clave in ("url_ficha_oficial", "url_ficha_sinim", "ficha_url", "url_fuente"):
            val = registro.get(clave)
            if isinstance(val, str) and val.strip().startswith("http"):
                return val.strip()
        municipio_id = registro.get("municipio_id") or registro.get("id_municipio")
        if municipio_id is not None and str(municipio_id).strip():
            return f"{URL_SINIM_FICHA_BASE}{str(municipio_id).strip()}"
    return f"{URL_SINIM_FICHA_BASE}{cut}"


def _catalogo_comunas_aysen(sinim_oficial: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    mapa_reg = _indexar_comunas_sinim(sinim_oficial, anio=None) if sinim_oficial else {}
    resultado: list[dict[str, Any]] = []
    for item in COMUNAS_AYSEN_LISTA:
        cut = item["cut"]
        reg = mapa_reg.get(cut)
        resultado.append(
            {
                "cut": cut,
                "nombre": item["nombre"],
                "url_ficha_sinim": _url_ficha_sinim(cut, reg),
            }
        )
    return resultado


def _resolver_comuna_aysen(
    comuna_raw: str | None,
    *,
    obligatoria: bool = False,
) -> dict[str, str] | None:
    texto = (comuna_raw or "").strip()
    if not texto:
        if obligatoria:
            return {"cut": "11201", "nombre": COMUNAS_AYSEN_POR_CUT["11201"]}
        return None
    if texto in COMUNAS_AYSEN_POR_CUT:
        return {"cut": texto, "nombre": COMUNAS_AYSEN_POR_CUT[texto]}
    norm = _normalizar_texto(texto)
    # Permite nombres con o sin prefijo "municipalidad de" / "comuna de" / "puerto"
    norm_limpio = re.sub(r"^(municipalidad de|comuna de|puerto)\s+", "", norm).strip()
    for item in COMUNAS_AYSEN_LISTA:
        nombre_norm = _normalizar_texto(item["nombre"])
        if norm == nombre_norm or norm_limpio == nombre_norm:
            return {"cut": item["cut"], "nombre": item["nombre"]}
        if item["cut"] == "11201" and norm_limpio in {"aisen", "aysen"}:
            return {"cut": item["cut"], "nombre": item["nombre"]}
    raise HTTPException(
        422,
        f"La comuna '{texto}' no corresponde a ninguna de las 10 comunas oficiales de la Región de Aysén.",
    )


def _cargar_modulo_opcional(nombre_modulo: str):
    _asegurar_raiz_en_path()
    try:
        return importlib.import_module(nombre_modulo)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Adaptador DIPRES (live piloto con fallback limpio a caché o sin dato)
# ---------------------------------------------------------------------------


def _normalizar_mes_corte(datos: Mapping[str, Any]) -> int | None:
    traza = datos.get("fuente_trazabilidad") if isinstance(datos.get("fuente_trazabilidad"), Mapping) else {}
    for candidato in (datos.get("mes_corte"), traza.get("mes_corte")):
        if isinstance(candidato, int) and not isinstance(candidato, bool) and 1 <= candidato <= 12:
            return candidato
    dipres_mod = _cargar_modulo_opcional("pipelines.fiscal.dipres_ckan")
    if dipres_mod is not None and hasattr(dipres_mod, "detectar_mes_corte"):
        return dipres_mod.detectar_mes_corte(
            columna_ejecucion=traza.get("columna_ejecucion"),
            package_title=traza.get("package_title"),
            package_name=traza.get("package_name"),
        )
    return None


def _obtener_datos_dipres_piloto(anio: int) -> tuple[dict[str, Any] | None, str | None]:
    """Obtiene el corte DIPRES piloto para ``anio`` priorizando caché local y sin colgar la API."""
    # 1. Override explícito de entorno para pruebas o corte local específico
    ruta_override = (os.getenv("CT_DIPRES_PATH") or "").strip()
    if ruta_override:
        ruta_path = Path(ruta_override)
        datos_override = _leer_json_opcional(ruta_path)
        if datos_override is not None:
            anio_override = datos_override.get("anio")
            if anio_override is None or anio_override == anio:
                return datos_override, "archivo_configurado"

    # 2. Caché local oficial en data/raw/ (piloto primero, luego aysen) — determinista y rápido
    for nombre_archivo in (f"dipres-piloto-{anio}.json", f"dipres-aysen-{anio}.json"):
        ruta_cache = RAIZ_REPO / "data" / "raw" / nombre_archivo
        datos_cache = _leer_json_opcional(ruta_cache)
        if datos_cache is not None:
            return datos_cache, "cache_local"

    # 3. Consulta en vivo solo si está habilitada explícitamente (evita latencia/bloqueo en años sin corte)
    if os.getenv("CT_DIPRES_LIVE_ON_MISS") == "1":
        dipres_mod = _cargar_modulo_opcional("pipelines.fiscal.dipres_ckan")
        if dipres_mod is not None and callable(getattr(dipres_mod, "obtener_presupuestos_piloto_live", None)):
            try:
                datos_piloto = dipres_mod.obtener_presupuestos_piloto_live(anio)
                if isinstance(datos_piloto, dict):
                    return datos_piloto, "dipres_piloto_live"
            except Exception:
                pass

    # 4. Sin red ni caché disponible -> degradación limpia sin inventar datos
    return None, None


def _buscar_entidad_dipres(
    datos_dipres: Mapping[str, Any] | None,
    *claves: str,
) -> Mapping[str, Any] | None:
    if not isinstance(datos_dipres, Mapping):
        return None
    entidades = datos_dipres.get("entidades")
    if isinstance(entidades, Mapping):
        for clave in claves:
            cand = entidades.get(clave)
            if isinstance(cand, Mapping):
                return cand
    for clave in claves:
        cand = datos_dipres.get(clave)
        if isinstance(cand, Mapping):
            return cand
    return None


def _extraer_monto_dict(
    bloque: Mapping[str, Any] | None,
    *claves: str,
) -> Decimal | None:
    if not isinstance(bloque, Mapping):
        return None
    for clave in claves:
        if clave in bloque and bloque[clave] is not None:
            val = _a_decimal_flexible(bloque[clave])
            if val is not None:
                return val
    return None


def _extraer_bloque_gore(datos_dipres: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(datos_dipres, Mapping):
        return {
            "nombre": "Gobierno Regional de Aysén",
            "billetera": "regional",
            "territorio": "Región de Aysén",
            "territorio_codigo": "11",
            "disponible": False,
            "etapa_contable": None,
            "mes_corte": None,
            "inicial_millones": None,
            "vigente_millones": None,
            "ejecutado_millones": None,
            "gasto_corriente_millones": None,
            "inversion_millones": None,
            "transferencias_capital_millones": None,
            "financiamiento_p31_millones": None,
            "proporcion_gasto_corriente_pct": None,
            "tasa_ejecucion_pct": None,
            "motivo_brecha": "Sin dato disponible de DIPRES para el ejercicio solicitado.",
            "url_fuente": URL_DIPRES_CKAN,
        }

    gore = _buscar_entidad_dipres(datos_dipres, "gore_aysen") or {}
    traza = datos_dipres.get("fuente_trazabilidad") if isinstance(datos_dipres.get("fuente_trazabilidad"), Mapping) else {}
    mes_corte = _normalizar_mes_corte(datos_dipres)

    inicial = _extraer_monto_dict(gore, "inicial_millones", "presupuesto_inicial_millones", "inicial")
    vigente = _extraer_monto_dict(gore, "vigente_millones", "presupuesto_vigente_millones", "vigente")
    ejecutado = _extraer_monto_dict(
        gore,
        "ejecutado_millones",
        "total_gasto_directo_millones",
        "ejecucion_millones",
    )
    corriente = _extraer_monto_dict(gore, "gasto_corriente_millones", "gasto_corriente_sub_21_26")
    inversion = _extraer_monto_dict(gore, "inversion_millones", "inversion_sub_29_31")
    trans_cap = _extraer_monto_dict(gore, "transferencias_capital_millones", "transferencias_capital_sub_33")
    inv_y_cap = _extraer_monto_dict(gore, "inversion_y_capital_millones")
    if inv_y_cap is not None and inversion is None and trans_cap is None:
        # Verificar si desglose_partidas trae Subt. 33 vs Subt. 29-31
        for part in gore.get("desglose_partidas") or []:
            if isinstance(part, Mapping):
                cod = str(part.get("codigo") or "")
                if cod == "33":
                    trans_cap = _extraer_monto_dict(part, "ejecutado_millones")
                elif "29" in cod or "31" in cod:
                    inversion = _extraer_monto_dict(part, "ejecutado_millones")
        if inversion is None and trans_cap is None:
            inversion = inv_y_cap
    fin_p31 = _extraer_monto_dict(
        gore,
        "ingresos_financiamiento_p31",
        "financiamiento_p31_millones",
        "ingresos_financiamiento_excluidos_millones",
    )

    disponible = any(v is not None for v in (inicial, vigente, ejecutado, corriente, inversion, trans_cap, inv_y_cap, fin_p31))
    prop_corriente = _extraer_monto_dict(gore, "gasto_corriente_pct", "proporcion_gasto_corriente_pct")
    if prop_corriente is None and corriente is not None and ejecutado is not None and ejecutado > _CERO:
        prop_corriente = _ratio_pct(corriente, ejecutado)
    inv_total = inv_y_cap if inv_y_cap is not None else (
        ((inversion or _CERO) + (trans_cap or _CERO)) if (inversion is not None or trans_cap is not None) else None
    )
    prop_inversion = _extraer_monto_dict(gore, "inversion_y_capital_pct", "inversion_pct")
    if prop_inversion is None and inv_total is not None and ejecutado is not None and ejecutado > _CERO:
        prop_inversion = _ratio_pct(inv_total, ejecutado)
    tasa_ejec = _extraer_monto_dict(gore, "tasa_ejecucion_pct")
    if tasa_ejec is None and ejecutado is not None and vigente is not None and vigente > _CERO:
        tasa_ejec = _ratio_pct(ejecutado, vigente)

    url_fuente = (
        gore.get("url_respaldo")
        or gore.get("url_fuente")
        or (f"https://datos.gob.cl/dataset/{traza.get('package_name')}" if traza.get("package_name") else None)
        or URL_DIPRES_CKAN
    )

    return {
        "nombre": gore.get("nombre") or "Gobierno Regional de Aysén",
        "billetera": "regional",
        "territorio": gore.get("territorio_etiqueta") or "Región de Aysén",
        "territorio_codigo": "11",
        "disponible": disponible,
        "etapa_contable": gore.get("etapa_contable") or traza.get("etapa_informada") or "ejecucion_acumulada",
        "mes_corte": mes_corte,
        "inicial_millones": _fmt(inicial, 3),
        "vigente_millones": _fmt(vigente, 3),
        "ejecutado_millones": _fmt(ejecutado, 3),
        "gasto_corriente_millones": _fmt(corriente, 3),
        "inversion_millones": _fmt(inversion, 3),
        "transferencias_capital_millones": _fmt(trans_cap, 3),
        "inversion_y_capital_millones": _fmt(inv_total, 3),
        "inversion_pct": _fmt(prop_inversion, 2),
        "financiamiento_p31_millones": _fmt(fin_p31, 3),
        "proporcion_gasto_corriente_pct": _fmt(prop_corriente, 2),
        "tasa_ejecucion_pct": _fmt(tasa_ejec, 2),
        "base_calculo": gore.get("base_calculo_porcentaje"),
        "frase_radial": gore.get("frase_radial"),
        "desglose_partidas": list(gore.get("desglose_partidas") or []),
        "costo_administrar": gore.get("costo_administrar"),
        "comparacion_mismo_mes_anterior": gore.get("comparacion_mismo_mes_anterior"),
        "motivo_brecha": gore.get("motivo_brecha") or gore.get("motivo_inicial_vigente"),
        "url_fuente": url_fuente,
    }


def _extraer_bloque_gobierno_central_nacional(
    datos_dipres: Mapping[str, Any] | None,
) -> dict[str, Any]:
    traza = (
        datos_dipres.get("fuente_trazabilidad")
        if isinstance(datos_dipres, Mapping) and isinstance(datos_dipres.get("fuente_trazabilidad"), Mapping)
        else {}
    )
    mes_corte = _normalizar_mes_corte(datos_dipres) if isinstance(datos_dipres, Mapping) else None
    gc = _buscar_entidad_dipres(datos_dipres, "gobierno_central_nacional", "gobierno_central", "nivel_nacional")

    if gc is None:
        return {
            "nombre": "Gobierno Central Total",
            "territorio": "Chile — Nivel Nacional",
            "territorio_codigo": "CL",
            "disponible": False,
            "mes_corte": mes_corte,
            "inicial_millones": None,
            "vigente_millones": None,
            "ejecutado_millones": None,
            "tasa_ejecucion_pct": None,
            "gasto_corriente_millones": None,
            "inversion_millones": None,
            "proporcion_gasto_corriente_pct": None,
            "inversion_pct": None,
            "desglose_partidas": [],
            "costo_administrar": None,
            "nota": (
                "Sin dato nacional de Gobierno Central en el corte DIPRES en caché. "
                "Referencia nacional: nunca se suma en la consolidación regional de Aysén."
            ),
            "url_fuente": URL_DIPRES_CKAN,
        }

    inicial = _extraer_monto_dict(gc, "inicial_millones", "presupuesto_inicial_millones", "inicial")
    vigente = _extraer_monto_dict(gc, "vigente_millones", "presupuesto_vigente_millones", "vigente")
    ejecutado = _extraer_monto_dict(gc, "ejecutado_millones", "ejecucion_millones", "total_gasto_millones", "ejecutado")
    corriente = _extraer_monto_dict(gc, "gasto_corriente_millones", "gasto_corriente_sub_21_26", "gasto_corriente")
    inversion = _extraer_monto_dict(gc, "inversion_y_capital_millones", "inversion_millones", "inversion_sub_29_31", "inversion")

    prop_corriente = _extraer_monto_dict(gc, "proporcion_gasto_corriente_pct", "gasto_corriente_pct")
    if prop_corriente is None and corriente is not None and ejecutado is not None and ejecutado > _CERO:
        prop_corriente = _ratio_pct(corriente, ejecutado)

    prop_inversion = _extraer_monto_dict(gc, "inversion_y_capital_pct", "inversion_pct")
    if prop_inversion is None and inversion is not None and ejecutado is not None and ejecutado > _CERO:
        prop_inversion = _ratio_pct(inversion, ejecutado)

    tasa_ejec = _extraer_monto_dict(gc, "tasa_ejecucion_pct")
    if tasa_ejec is None and ejecutado is not None and vigente is not None and vigente > _CERO:
        tasa_ejec = _ratio_pct(ejecutado, vigente)

    disponible = any(v is not None for v in (inicial, vigente, ejecutado, corriente, inversion))
    url_fuente = (
        gc.get("url_respaldo")
        or gc.get("url_fuente")
        or (f"https://datos.gob.cl/dataset/{traza.get('package_name')}" if traza.get("package_name") else None)
        or URL_DIPRES_CKAN
    )

    return {
        "nombre": gc.get("nombre") or "Gobierno Central Total",
        "territorio": gc.get("territorio_etiqueta") or "Chile — Nivel Nacional",
        "territorio_codigo": "CL",
        "disponible": disponible,
        "mes_corte": gc.get("mes_corte") or mes_corte,
        "inicial_millones": _fmt(inicial, 3),
        "vigente_millones": _fmt(vigente, 3),
        "ejecutado_millones": _fmt(ejecutado, 3),
        "tasa_ejecucion_pct": _fmt(tasa_ejec, 2),
        "gasto_corriente_millones": _fmt(corriente, 3),
        "inversion_millones": _fmt(inversion, 3),
        "proporcion_gasto_corriente_pct": _fmt(prop_corriente, 2),
        "inversion_pct": _fmt(prop_inversion, 2),
        "base_calculo": gc.get("base_calculo_porcentaje"),
        "frase_radial": gc.get("frase_radial"),
        "desglose_partidas": list(gc.get("desglose_partidas") or []),
        "costo_administrar": gc.get("costo_administrar"),
        "comparacion_mismo_mes_anterior": gc.get("comparacion_mismo_mes_anterior"),
        "nota": gc.get("nota_cobertura") or (
            "Territorio: Chile — Nivel Nacional. Se presenta como referencia de escala país y "
            "no se suma dentro de la consolidación territorial de Aysén."
        ),
        "url_fuente": url_fuente,
    }


def _extraer_bloque_vialidad_dipres(datos_dipres: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(datos_dipres, Mapping):
        return {
            "disponible": False,
            "territorio": "Chile — Nivel Nacional (DIPRES)",
            "inicial_millones": None,
            "vigente_millones": None,
            "ejecutado_millones": None,
            "tasa_ejecucion_pct": None,
            "gasto_corriente_millones": None,
            "inversion_millones": None,
            "proporcion_gasto_corriente_pct": None,
            "inversion_pct": None,
            "desglose_partidas": [],
            "costo_administrar": None,
            "nota": "Sin dato DIPRES nacional para la Dirección de Vialidad del MOP en el corte consultado.",
        }

    vialidad = _buscar_entidad_dipres(
        datos_dipres,
        "vialidad_mop_nacional",
        "vialidad_mop",
        "direccion_vialidad",
        "piloto_vialidad_mop",
        "vialidad",
    )
    if vialidad is None and isinstance(datos_dipres.get("servicios_nacionales"), Mapping):
        cand = datos_dipres["servicios_nacionales"].get("vialidad_mop") or datos_dipres["servicios_nacionales"].get("direccion_vialidad")
        if isinstance(cand, Mapping):
            vialidad = cand
    if vialidad is None and isinstance(datos_dipres.get("servicios_publicos_aysen"), list):
        for srv in datos_dipres["servicios_publicos_aysen"]:
            if isinstance(srv, Mapping) and "vialidad" in _normalizar_texto(srv.get("nombre_capitulo")):
                vialidad = srv
                break

    if vialidad is None:
        return {
            "disponible": False,
            "territorio": "Chile — Nivel Nacional (DIPRES)",
            "inicial_millones": None,
            "vigente_millones": None,
            "ejecutado_millones": None,
            "tasa_ejecucion_pct": None,
            "gasto_corriente_millones": None,
            "inversion_millones": None,
            "proporcion_gasto_corriente_pct": None,
            "inversion_pct": None,
            "desglose_partidas": [],
            "costo_administrar": None,
            "nota": (
                "El corte CKAN de Gobierno Central en caché no incluye el capítulo nacional de "
                "Dirección de Vialidad (Partida 12, Capítulo 02); los contratos territorializados en Aysén "
                "se auditan desde MOP DGOP."
            ),
        }

    inicial = _extraer_monto_dict(vialidad, "inicial_millones", "presupuesto_inicial_millones", "inicial")
    vigente = _extraer_monto_dict(vialidad, "vigente_millones", "vigente_gasto_millones", "presupuesto_vigente_millones", "vigente")
    ejecutado = _extraer_monto_dict(vialidad, "ejecutado_millones", "total_gasto_millones", "ejecucion_millones", "ejecutado")
    corriente = _extraer_monto_dict(vialidad, "gasto_corriente_millones", "gasto_corriente_sub_21_26")
    inversion = _extraer_monto_dict(vialidad, "inversion_y_capital_millones", "inversion_millones", "inversion_sub_29_31")
    prop_corriente = _extraer_monto_dict(vialidad, "gasto_corriente_pct", "proporcion_gasto_corriente_pct")
    if prop_corriente is None and corriente is not None and ejecutado is not None and ejecutado > _CERO:
        prop_corriente = _ratio_pct(corriente, ejecutado)
    prop_inversion = _extraer_monto_dict(vialidad, "inversion_y_capital_pct", "inversion_pct")
    if prop_inversion is None and inversion is not None and ejecutado is not None and ejecutado > _CERO:
        prop_inversion = _ratio_pct(inversion, ejecutado)
    tasa_ejec = _extraer_monto_dict(vialidad, "tasa_ejecucion_pct")
    if tasa_ejec is None and ejecutado is not None and vigente is not None and vigente > _CERO:
        tasa_ejec = _ratio_pct(ejecutado, vigente)

    disponible = any(v is not None for v in (inicial, vigente, ejecutado, corriente, inversion))
    return {
        "disponible": disponible,
        "nombre": vialidad.get("nombre") or "Dirección de Vialidad — MOP (Partida 12, Capítulo 02)",
        "territorio": vialidad.get("territorio_etiqueta") or vialidad.get("territorio") or "Chile — Nivel Nacional (DIPRES)",
        "inicial_millones": _fmt(inicial, 3),
        "vigente_millones": _fmt(vigente, 3),
        "ejecutado_millones": _fmt(ejecutado, 3),
        "tasa_ejecucion_pct": _fmt(tasa_ejec, 2),
        "gasto_corriente_millones": _fmt(corriente, 3),
        "inversion_millones": _fmt(inversion, 3),
        "proporcion_gasto_corriente_pct": _fmt(prop_corriente, 2),
        "inversion_pct": _fmt(prop_inversion, 2),
        "base_calculo": vialidad.get("base_calculo_porcentaje"),
        "frase_radial": vialidad.get("frase_radial"),
        "desglose_partidas": list(vialidad.get("desglose_partidas") or []),
        "costo_administrar": vialidad.get("costo_administrar"),
        "comparacion_mismo_mes_anterior": vialidad.get("comparacion_mismo_mes_anterior"),
        "url_fuente": vialidad.get("url_respaldo") or URL_DIPRES_CKAN,
        "nota": vialidad.get("nota_cobertura") or vialidad.get("nota")
        or (
            "Presupuesto nacional de la Dirección de Vialidad del MOP en DIPRES; para obras "
            "territorializadas en la Región de Aysén véanse los contratos MOP DGOP."
        ),
    }


def _extraer_servicios_identificables_aysen(
    datos_dipres: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], Decimal | None]:
    if not isinstance(datos_dipres, Mapping):
        return [], None
    lista_raw = datos_dipres.get("servicios_publicos_aysen")
    if not isinstance(lista_raw, list):
        # Soporte para esquema dipres-piloto-presupuestario-v1 (entidades.servicios_regionales_aysen)
        srv_reg = _buscar_entidad_dipres(datos_dipres, "servicios_regionales_aysen")
        if isinstance(srv_reg, Mapping):
            tot = _extraer_monto_dict(srv_reg, "ejecutado_millones", "total_gasto_millones")
            corr = _extraer_monto_dict(srv_reg, "gasto_corriente_millones") or _CERO
            inv = _extraer_monto_dict(srv_reg, "inversion_y_capital_millones", "inversion_millones") or _CERO
            if tot is not None:
                return (
                    [
                        {
                            "partida": "Varios",
                            "nombre_partida": "Ministerios y Servicios Públicos en Aysén",
                            "capitulo": "Aysén",
                            "nombre": str(srv_reg.get("nombre") or "Servicios Públicos del Gobierno Central en Aysén"),
                            "territorio": str(srv_reg.get("territorio_etiqueta") or "Región de Aysén"),
                            "destacado_aysen": True,
                            "inicial_millones": _fmt(_extraer_monto_dict(srv_reg, "inicial_millones"), 3),
                            "vigente_millones": _fmt(_extraer_monto_dict(srv_reg, "vigente_millones"), 3),
                            "gasto_corriente_millones": _fmt(corr, 3),
                            "inversion_millones": _fmt(inv, 3),
                            "transferencias_capital_millones": None,
                            "total_gasto_millones": _fmt(tot, 3),
                            "tasa_ejecucion_pct": _fmt(_extraer_monto_dict(srv_reg, "tasa_ejecucion_pct"), 2),
                            "gasto_corriente_pct": _fmt(_extraer_monto_dict(srv_reg, "gasto_corriente_pct"), 2),
                            "inversion_pct": _fmt(_extraer_monto_dict(srv_reg, "inversion_y_capital_pct"), 2),
                            "base_calculo": srv_reg.get("base_calculo_porcentaje"),
                            "frase_radial": srv_reg.get("frase_radial"),
                            "desglose_partidas": list(srv_reg.get("desglose_partidas") or []),
                            "costo_administrar": srv_reg.get("costo_administrar"),
                            "url_fuente": srv_reg.get("url_respaldo") or URL_DIPRES_CKAN,
                        }
                    ],
                    tot,
                )
        return [], None

    servicios: list[dict[str, Any]] = []
    total = _CERO
    with localcontext(_CONTEXTO_DECIMAL):
        for srv in lista_raw:
            if not isinstance(srv, Mapping):
                continue
            nombre = str(srv.get("nombre_capitulo") or srv.get("nombre") or "").strip()
            corr = _extraer_monto_dict(srv, "gasto_corriente_sub_21_26", "gasto_corriente_millones") or _CERO
            inv = _extraer_monto_dict(srv, "inversion_sub_29_31", "inversion_millones") or _CERO
            tcap = _extraer_monto_dict(srv, "transferencias_capital_sub_33", "transferencias_capital_millones") or _CERO
            tot = _extraer_monto_dict(srv, "total_gasto_millones", "ejecutado_millones")
            if tot is None:
                tot = corr + inv + tcap
            total += tot
            norm_nombre = _normalizar_texto(nombre)
            destacado = (
                "servicio de salud" in norm_nombre
                or "educacion publica" in norm_nombre
                or "slep" in norm_nombre
                or "delegacion presidencial" in norm_nombre
            )
            servicios.append(
                {
                    "partida": srv.get("partida"),
                    "nombre_partida": srv.get("nombre_partida"),
                    "capitulo": srv.get("capitulo"),
                    "nombre": nombre,
                    "territorio": "Región de Aysén",
                    "destacado_aysen": destacado,
                    "gasto_corriente_millones": _fmt(corr, 3),
                    "inversion_millones": _fmt(inv, 3),
                    "transferencias_capital_millones": _fmt(tcap, 3),
                    "total_gasto_millones": _fmt(tot, 3),
                    "vigente_millones": _fmt(
                        _extraer_monto_dict(srv, "vigente_gasto_millones", "vigente_millones"),
                        3,
                    ),
                }
            )
    return servicios, (total if servicios else None)


# ---------------------------------------------------------------------------
# Adaptador SINIM (oficial + reconocimiento limpio de corte importado por usuario)
# ---------------------------------------------------------------------------


def _divisor_unidad_a_millones(unidad: object) -> Decimal:
    norm = _normalizar_texto(unidad)
    if norm in {"miles clp", "m$", "miles $", "miles de pesos", "miles_clp", "m clp"}:
        return _MIL
    if norm in {"clp", "$", "pesos", "pesos clp"}:
        return _MILLON
    return Decimal("1")


def _indexar_comunas_sinim(
    datos_sinim: Mapping[str, Any] | None,
    *,
    anio: int | None,
) -> dict[str, dict[str, Any]]:
    """Indexa registros municipales por CUT desde múltiples esquemas SINIM posibles."""
    if not isinstance(datos_sinim, Mapping):
        return {}

    bloque_anio: Any = None
    por_anio = datos_sinim.get("por_anio")
    if isinstance(por_anio, Mapping):
        if anio is not None and str(anio) in por_anio:
            bloque_anio = por_anio[str(anio)]
        elif anio is None and por_anio:
            ultimo = sorted(por_anio.keys())[-1]
            bloque_anio = por_anio[ultimo]

    comunas_raw: Any = None
    if isinstance(bloque_anio, Mapping):
        comunas_raw = bloque_anio.get("comunas") or bloque_anio.get("municipalidades") or bloque_anio
    elif isinstance(bloque_anio, list):
        comunas_raw = bloque_anio
    else:
        comunas_raw = datos_sinim.get("comunas") or datos_sinim.get("municipalidades")

    anio_global = datos_sinim.get("anio")
    if anio_global is None and isinstance(datos_sinim.get("resumen"), Mapping):
        anio_global = datos_sinim["resumen"].get("anio")

    indice: dict[str, dict[str, Any]] = {}
    if isinstance(comunas_raw, Mapping):
        for cut, item in comunas_raw.items():
            if str(cut) not in COMUNAS_AYSEN_POR_CUT or not isinstance(item, Mapping):
                continue
            item_anio = item.get("anio") if item.get("anio") is not None else anio_global
            if anio is not None and isinstance(item_anio, int) and item_anio != anio and bloque_anio is None:
                continue
            copia = dict(item)
            copia.setdefault("cut", str(cut))
            if item_anio is not None:
                copia.setdefault("anio", item_anio)
            indice[str(cut)] = copia
    elif isinstance(comunas_raw, list):
        for item in comunas_raw:
            if not isinstance(item, Mapping):
                continue
            cut = str(item.get("cut") or item.get("codigo_comuna") or "").strip()
            if cut not in COMUNAS_AYSEN_POR_CUT:
                continue
            item_anio = item.get("anio") if item.get("anio") is not None else anio_global
            if anio is not None and isinstance(item_anio, int) and item_anio != anio and bloque_anio is None:
                continue
            copia = dict(item)
            copia["cut"] = cut
            if item_anio is not None:
                copia.setdefault("anio", item_anio)
            indice[cut] = copia

    return indice


def _obtener_monto_sinim_millones(
    registro: Mapping[str, Any],
    claves_millones: Sequence[str],
    claves_genericas: Sequence[str] = (),
    divisor_defecto: Decimal = Decimal("1"),
) -> Decimal | None:
    for clave in claves_millones:
        if clave in registro and registro[clave] is not None:
            val = _a_decimal_flexible(registro[clave])
            if val is not None:
                return val
    for clave in claves_genericas:
        if clave in registro and registro[clave] is not None:
            val = _a_decimal_flexible(registro[clave])
            if val is not None:
                with localcontext(_CONTEXTO_DECIMAL):
                    return val / divisor_defecto
    return None


def _construir_billetera_municipal(
    cut: str,
    anio: int,
    sinim_oficial: Mapping[str, Any] | None,
    sinim_importado: Mapping[str, Any] | None,
) -> dict[str, Any]:
    nombre_comuna = COMUNAS_AYSEN_POR_CUT[cut]
    indice_oficial = _indexar_comunas_sinim(sinim_oficial, anio=anio)
    indice_importado = (
        _indexar_comunas_sinim(sinim_importado, anio=anio)
        if isinstance(sinim_importado, Mapping) and sinim_importado.get("valido") is True
        else {}
    )

    registro = indice_oficial.get(cut)
    fuente_datos = "sinim_oficial"
    if registro is None and cut in indice_importado:
        registro = indice_importado[cut]
        fuente_datos = "sinim_importado_usuario"

    # Info sobre corte SINIM adicional importado por el usuario (si existe para cualquier año)
    info_importado_usuario: dict[str, Any] = {"cargado": False}
    if isinstance(sinim_importado, Mapping) and sinim_importado.get("valido") is True:
        res_imp = sinim_importado.get("resumen") if isinstance(sinim_importado.get("resumen"), Mapping) else {}
        traza_imp = sinim_importado.get("fuente_trazabilidad") if isinstance(sinim_importado.get("fuente_trazabilidad"), Mapping) else {}
        reg_imp_cualq = _indexar_comunas_sinim(sinim_importado, anio=None).get(cut)
        info_importado_usuario = {
            "cargado": True,
            "anio": res_imp.get("anio"),
            "archivo": traza_imp.get("archivo"),
            "comunas_cargadas": res_imp.get("comunas_cargadas"),
            "comuna_actual_presente": reg_imp_cualq is not None,
            "gasto_devengado_comuna_millones": (
                reg_imp_cualq.get("gasto_total_devengado_millones") if reg_imp_cualq else None
            ),
        }

    url_ficha = _url_ficha_sinim(cut, registro)
    anios_disponibles_oficial: list[int] = []
    if isinstance(sinim_oficial, Mapping):
        if isinstance(sinim_oficial.get("por_anio"), Mapping):
            anios_disponibles_oficial = sorted(
                int(k) for k in sinim_oficial["por_anio"].keys() if str(k).isdigit()
            )
        elif isinstance(sinim_oficial.get("anio"), int):
            anios_disponibles_oficial = [sinim_oficial["anio"]]
        elif isinstance(sinim_oficial.get("resumen"), Mapping) and isinstance(sinim_oficial["resumen"].get("anio"), int):
            anios_disponibles_oficial = [sinim_oficial["resumen"]["anio"]]

    comunas_disponibles = [
        {
            "cut": item["cut"],
            "nombre": item["nombre"],
            "disponible_anio": (item["cut"] in indice_oficial) or (item["cut"] in indice_importado),
            "url_ficha_sinim": _url_ficha_sinim(item["cut"], indice_oficial.get(item["cut"])),
        }
        for item in COMUNAS_AYSEN_LISTA
    ]

    if registro is None:
        motivo = (
            f"Sin dato municipal oficial SINIM para la Municipalidad de {nombre_comuna} ({cut}) en {anio}."
        )
        if anios_disponibles_oficial:
            motivo += f" Años con corte oficial SINIM disponible: {', '.join(str(a) for a in anios_disponibles_oficial)}."
        return {
            "nombre": f"Municipalidad de {nombre_comuna}",
            "billetera": "municipal",
            "cut": cut,
            "territorio": f"Comuna de {nombre_comuna}",
            "disponible": False,
            "fuente_datos": "sin_dato",
            "anio_datos": None,
            "etapa_contable": None,
            "inicial_millones": None,
            "vigente_millones": None,
            "nota_inicial_vigente": (
                "SINIM/BEP reporta gasto devengado efectivo; no publica Ley Inicial ni Presupuesto Vigente."
            ),
            "devengado_bep_millones": None,
            "ingresos_totales_millones": None,
            "gasto_corriente_observable_millones": None,
            "gasto_corriente_observable_pct": None,
            "base_calculo_gasto_corriente": None,
            "frase_radial": None,
            "desglose_subt_21": {
                "total_millones": None,
                "planta_millones": None,
                "contrata_millones": None,
                "honorarios_millones": None,
                "programas_millones": None,
            },
            "subt_22_bienes_servicios_millones": None,
            "gasto_inversion_millones": None,
            "costo_administracion_interna": {
                "disponible": False,
                "monto_millones": None,
                "porcentaje_sobre_devengado": None,
                "descripcion": "Sin dato disponible para el año seleccionado.",
            },
            "url_ficha_oficial": url_ficha,
            "corte_sinim_importado_usuario": info_importado_usuario,
            "comunas_disponibles": comunas_disponibles,
            "motivo_no_disponible": motivo,
        }

    divisor = _divisor_unidad_a_millones(
        registro.get("unidad") or registro.get("unidad_montos") or "millones CLP"
    )
    inicial = _obtener_monto_sinim_millones(
        registro,
        ("inicial_millones", "presupuesto_inicial_millones"),
        ("inicial", "presupuesto_inicial"),
        divisor,
    )
    vigente = _obtener_monto_sinim_millones(
        registro,
        ("vigente_millones", "presupuesto_vigente_millones"),
        ("vigente", "presupuesto_vigente"),
        divisor,
    )
    devengado = _obtener_monto_sinim_millones(
        registro,
        (
            "devengado_bep_millones",
            "gasto_total_devengado_millones",
            "gasto_devengado_millones",
            "ejecutado_millones",
        ),
        ("devengado_bep", "gasto_total_devengado", "gasto_devengado"),
        divisor,
    )
    ingresos = _obtener_monto_sinim_millones(
        registro,
        ("ingresos_totales_millones", "ingresos_percibidos_millones", "ingresos_devengados_millones"),
        ("ingresos_totales", "ingresos_percibidos", "ingresos_devengados"),
        divisor,
    )
    gasto_inv = _obtener_monto_sinim_millones(
        registro,
        ("gasto_inversion_millones", "inversion_millones"),
        ("gasto_inversion", "inversion"),
        divisor,
    )

    # Desglose Subtítulo 21 (Personal) y Subtítulo 22 (Bienes y servicios de consumo)
    bloque_s21 = (
        registro.get("desglose_subt_21")
        or registro.get("subtitulo_21")
        or registro.get("personal_subt_21")
        or {}
    )
    if not isinstance(bloque_s21, Mapping):
        bloque_s21 = {}

    planta = _obtener_monto_sinim_millones(
        bloque_s21,
        ("planta_millones", "personal_planta_millones"),
        ("planta", "personal_planta"),
        divisor,
    ) or _obtener_monto_sinim_millones(
        registro,
        ("subt_21_planta_millones", "planta_millones", "personal_planta_millones"),
        ("subt_21_planta", "personal_planta"),
        divisor,
    )
    contrata = _obtener_monto_sinim_millones(
        bloque_s21,
        ("contrata_millones", "personal_contrata_millones"),
        ("contrata", "personal_contrata"),
        divisor,
    ) or _obtener_monto_sinim_millones(
        registro,
        ("subt_21_contrata_millones", "contrata_millones", "personal_contrata_millones"),
        ("subt_21_contrata", "personal_contrata"),
        divisor,
    )
    honorarios = _obtener_monto_sinim_millones(
        bloque_s21,
        ("honorarios_millones", "personal_honorarios_millones"),
        ("honorarios", "personal_honorarios"),
        divisor,
    ) or _obtener_monto_sinim_millones(
        registro,
        ("subt_21_honorarios_millones", "honorarios_millones", "personal_honorarios_millones"),
        ("subt_21_honorarios", "personal_honorarios"),
        divisor,
    )
    programas = _obtener_monto_sinim_millones(
        bloque_s21,
        ("programas_millones", "honorarios_programas_millones", "personal_programas_millones", "personal_programas_comunitarios_millones"),
        ("programas", "honorarios_programas", "personal_programas_comunitarios"),
        divisor,
    ) or _obtener_monto_sinim_millones(
        registro,
        ("personal_programas_comunitarios_millones", "subt_21_programas_millones", "programas_millones", "honorarios_programas_millones"),
        ("subt_21_programas", "honorarios_programas"),
        divisor,
    )

    subt_21_total = _obtener_monto_sinim_millones(
        bloque_s21,
        ("total_millones", "subt_21_total_millones"),
        ("total",),
        divisor,
    ) or _obtener_monto_sinim_millones(
        registro,
        ("gasto_personal_sub21_millones", "subt_21_millones", "subtitulo_21_millones", "gasto_personal_millones"),
        ("subt_21", "subtitulo_21", "gasto_personal"),
        divisor,
    )
    partes_s21 = [v for v in (planta, contrata, honorarios, programas) if v is not None]
    if subt_21_total is None and partes_s21:
        with localcontext(_CONTEXTO_DECIMAL):
            subt_21_total = sum(partes_s21, _CERO)

    subt_22 = _obtener_monto_sinim_millones(
        registro,
        (
            "gasto_bienes_servicios_sub22_millones",
            "subt_22_bienes_servicios_millones",
            "subt_22_millones",
            "subtitulo_22_millones",
            "bienes_y_servicios_millones",
        ),
        ("subt_22_bienes_servicios", "subt_22", "subtitulo_22", "bienes_y_servicios"),
        divisor,
    )

    gasto_corriente = _obtener_monto_sinim_millones(
        registro,
        ("gasto_corriente_observable_millones", "gasto_corriente_millones"),
        ("gasto_corriente_observable", "gasto_corriente"),
        divisor,
    )
    if gasto_corriente is None and (subt_21_total is not None or subt_22 is not None):
        with localcontext(_CONTEXTO_DECIMAL):
            gasto_corriente = (subt_21_total or _CERO) + (subt_22 or _CERO)

    gasto_corriente_pct = _a_decimal_flexible(
        registro.get("porcentaje_gasto_corriente_pct")
        or registro.get("gasto_corriente_observable_pct")
        or registro.get("gasto_corriente_pct")
    )
    if gasto_corriente_pct is None and gasto_corriente is not None and devengado is not None and devengado > _CERO:
        gasto_corriente_pct = _ratio_pct(gasto_corriente, devengado)

    base_calculo = registro.get("base_calculo_gasto_corriente") or (
        "Gasto corriente observable (Subt. 21 Personal + Subt. 22 Bienes y Servicios de Consumo"
        + (" y otros corrientes informados en SINIM" if registro.get("gasto_corriente_observable_millones") or registro.get("gasto_corriente_millones") else "")
        + ") dividido por el Gasto Total Devengado BEP del mismo ejercicio."
    )

    # Costo de administración interna (si viene en SINIM o derivable)
    admin_raw = registro.get("costo_administracion_interna")
    if isinstance(admin_raw, Mapping):
        admin_monto = _obtener_monto_sinim_millones(
            admin_raw,
            ("monto_millones", "valor_millones"),
            ("monto", "valor"),
            divisor,
        )
        admin_pct = _a_decimal_flexible(
            admin_raw.get("porcentaje_sobre_devengado") or admin_raw.get("porcentaje")
        )
        if admin_pct is None and admin_monto is not None and devengado is not None and devengado > _CERO:
            admin_pct = _ratio_pct(admin_monto, devengado)
        admin_desc = admin_raw.get("descripcion") or "Gasto en gestión interna municipal informado en SINIM."
    else:
        admin_monto = _obtener_monto_sinim_millones(
            registro,
            ("costo_admin_interno_millones", "costo_administracion_interna_millones", "gasto_gestion_interna_millones"),
            ("costo_admin_interno", "costo_administracion_interna", "gasto_gestion_interna"),
            divisor,
        )
        admin_pct = _a_decimal_flexible(
            registro.get("costo_admin_interno_pct")
            or registro.get("costo_administracion_interna_pct")
            or registro.get("gasto_gestion_interna_pct")
        )
        if admin_pct is None and admin_monto is not None and devengado is not None and devengado > _CERO:
            admin_pct = _ratio_pct(admin_monto, devengado)
        admin_desc = registro.get("nota_costo_administracion") or (
            "Personal de gestión administrativa (Planta + Contrata + Honorarios), separado de programas comunitarios."
            if admin_monto is not None or admin_pct is not None
            else "Dato de gestión interna no desglosado en el corte SINIM disponible."
        )

    anio_registro = registro.get("anio") if isinstance(registro.get("anio"), int) else anio
    frase_radial: str | None = registro.get("frase_radial") if isinstance(registro.get("frase_radial"), str) else None
    if not frase_radial and gasto_corriente_pct is not None:
        frase_radial = (
            f"De cada $100 ejecutados por la Municipalidad de {nombre_comuna} en {anio_registro}, "
            f"${_fmt_es(gasto_corriente_pct, 1)} correspondieron a gasto corriente observable "
            f"(personal y operación básica, sobre devengado BEP)."
        )

    return {
        "nombre": f"Municipalidad de {nombre_comuna}",
        "billetera": "municipal",
        "cut": cut,
        "territorio": f"Comuna de {nombre_comuna}",
        "disponible": True,
        "fuente_datos": fuente_datos,
        "anio_datos": anio_registro,
        "etapa_contable": registro.get("etapa") or "devengado_bep",
        "inicial_millones": _fmt(inicial, 3),
        "vigente_millones": _fmt(vigente, 3),
        "nota_inicial_vigente": (
            None
            if (inicial is not None and vigente is not None)
            else "SINIM/BEP informa ejecución devengada real; no publica Ley Inicial ni Presupuesto Vigente."
        ),
        "devengado_bep_millones": _fmt(devengado, 3),
        "ingresos_totales_millones": _fmt(ingresos, 3),
        "gasto_corriente_observable_millones": _fmt(gasto_corriente, 3),
        "gasto_corriente_observable_pct": _fmt(gasto_corriente_pct, 2),
        "base_calculo_gasto_corriente": base_calculo,
        "frase_radial": frase_radial,
        "desglose_subt_21": {
            "total_millones": _fmt(subt_21_total, 3),
            "planta_millones": _fmt(planta, 3),
            "contrata_millones": _fmt(contrata, 3),
            "honorarios_millones": _fmt(honorarios, 3),
            "programas_millones": _fmt(programas, 3),
        },
        "subt_22_bienes_servicios_millones": _fmt(subt_22, 3),
        "gasto_inversion_millones": _fmt(gasto_inv, 3),
        "costo_administracion_interna": {
            "disponible": admin_monto is not None or admin_pct is not None,
            "monto_millones": _fmt(admin_monto, 3),
            "porcentaje_sobre_devengado": _fmt(admin_pct, 2),
            "descripcion": admin_desc,
        },
        "url_ficha_oficial": url_ficha,
        "corte_sinim_importado_usuario": info_importado_usuario,
        "comunas_disponibles": comunas_disponibles,
        "motivo_no_disponible": None,
    }


# ---------------------------------------------------------------------------
# Motor de Proyectos MOP (2 preguntas separadas + clasificación documental)
# ---------------------------------------------------------------------------


def _fecha_cambio_administracion(anio: int, metadatos: Mapping[str, Any] | None = None) -> str:
    if isinstance(metadatos, Mapping):
        pub = metadatos.get("publicacion") if isinstance(metadatos.get("publicacion"), Mapping) else {}
        f = metadatos.get("fecha_cambio_administracion") or pub.get("fecha_cambio_administracion")
        if isinstance(f, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", f.strip()):
            return f.strip()
    if anio >= 2026:
        return "2026-03-11"
    if anio >= 2022:
        return "2022-03-11"
    if anio >= 2018:
        return "2018-03-11"
    return "2014-03-11"


def _extraer_anio_de_fecha(valor: object) -> int | None:
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, int) and 1990 <= valor <= 2100:
        return valor
    texto = str(valor).strip()
    m = re.search(r"(19\d{2}|20\d{2})", texto)
    return int(m.group(1)) if m else None


def _extraer_fecha_iso(valor: object) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    m_iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})", texto)
    if m_iso:
        return f"{m_iso.group(1)}-{m_iso.group(2)}-{m_iso.group(3)}"
    m_dmy = re.match(r"^(\d{2})[/-](\d{2})[/-](\d{4})", texto)
    if m_dmy:
        return f"{m_dmy.group(3)}-{m_dmy.group(2)}-{m_dmy.group(1)}"
    return None


def _lista_comunas_proyecto(proy: Mapping[str, Any]) -> list[str]:
    bruto = proy.get("comunas")
    if isinstance(bruto, list):
        return [str(c).strip() for c in bruto if c is not None and str(c).strip()]
    if isinstance(bruto, str) and bruto.strip():
        return [p.strip() for p in re.split(r"[,;/]+", bruto) if p.strip()]
    unica = proy.get("comuna")
    if isinstance(unica, str) and unica.strip():
        return [p.strip() for p in re.split(r"[,;/]+", unica) if p.strip()]
    return []


def _es_proyecto_informacion_insuficiente(proy: Mapping[str, Any]) -> bool:
    if proy.get("informacion_insuficiente") is True:
        return True
    estado_doc = _normalizar_texto(
        proy.get("calidad_informacion")
        or proy.get("clasificacion_documental")
        or proy.get("estado_documental")
        or proy.get("calidad_dato")
    )
    if "insuficiente" in estado_doc or "incompleto" in estado_doc or "sin_fecha" in estado_doc:
        return True
    if proy.get("motivo_insuficiencia") or (
        isinstance(proy.get("motivos_insuficiencia"), list) and len(proy["motivos_insuficiencia"]) > 0
    ):
        return True

    # Verifica disponibilidad mínima de fecha/origen de contrato y al menos un monto presupuestario/pago
    tiene_fecha_o_flag = any(
        proy.get(k) is not None and str(proy.get(k)).strip() != ""
        for k in (
            "fecha_contratacion",
            "fecha_contrato",
            "fecha_adjudicacion",
            "fecha_inicio",
            "anio_contrato",
            "anio_inicio",
            "firmado_antes_administracion_actual",
            "es_contrato_anterior",
            "es_arrastre",
            "nuevo_o_arrastre",
        )
    )
    tiene_monto = any(
        _a_decimal_flexible(proy.get(k)) is not None
        for k in (
            "pagado_anio_millones",
            "monto_pagado_anio_millones",
            "ejecutado_anio_millones",
            "compromiso_anio_millones",
            "presupuesto_anio_millones",
            "monto_presupuesto_anio_millones",
            "arrastre_millones",
            "monto_arrastre_millones",
            "monto_vigente_millones",
            "costo_total_contrato_millones",
            "monto_contrato_millones",
        )
    )
    return not (tiene_fecha_o_flag and tiene_monto)


def _cargar_calcular_resumen_proyectos_externo():
    for nombre_mod in (
        "pipelines.inversion.mop_proyectos",
        "pipelines.inversion.proyectos_mop",
        "pipelines.inversion.mop_dgop",
        "pipelines.inversion",
    ):
        mod = _cargar_modulo_opcional(nombre_mod)
        if mod is not None and callable(getattr(mod, "calcular_resumen_proyectos", None)):
            return getattr(mod, "calcular_resumen_proyectos")
    return None


def calcular_resumen_proyectos(
    proyectos: Sequence[Mapping[str, Any]],
    *,
    anio: int = 2026,
    fecha_cambio_administracion: str | None = None,
) -> dict[str, Any]:
    """Calcula con ``Decimal`` las dos preguntas separadas sobre un conjunto de proyectos MOP.

    Pregunta 1 (``pagos_contratos_anteriores``):
      De lo pagado este año, ¿cuánto corresponde a contratos firmados antes de que asumiera esta administración?
    Pregunta 2 (``arrastre_presupuesto``):
      Del presupuesto de inversión de este año, ¿cuánto ya estaba comprometido por proyectos de años anteriores?
    """
    fecha_corte_admin = fecha_cambio_administracion or _fecha_cambio_administracion(anio)

    pagado_total = _CERO
    pagado_anteriores = _CERO
    pagado_nuevos = _CERO
    contratos_con_pago = 0
    contratos_anteriores_con_pago = 0
    excluidos_pregunta_1 = 0

    presupuesto_total_anio = _CERO
    arrastre_comprometido = _CERO
    proyectos_con_presupuesto = 0
    proyectos_arrastre = 0
    excluidos_pregunta_2 = 0

    with localcontext(_CONTEXTO_DECIMAL):
        for proy in proyectos:
            if not isinstance(proy, Mapping):
                continue
            if _es_proyecto_informacion_insuficiente(proy):
                excluidos_pregunta_1 += 1
                excluidos_pregunta_2 += 1
                continue

            fecha_firma = _extraer_fecha_iso(
                proy.get("fecha_contratacion")
                or proy.get("fecha_contrato")
                or proy.get("fecha_adjudicacion")
                or proy.get("fecha_inicio")
            )
            anio_inicio = _extraer_anio_de_fecha(
                proy.get("anio_contrato")
                or proy.get("anio_inicio")
                or fecha_firma
            )

            # Pregunta 1: Pagos del año en contratos anteriores a esta administración
            pagado = _extraer_monto_dict(
                proy,
                "pagado_anio_millones",
                "monto_pagado_anio_millones",
                "ejecutado_anio_millones",
                "pagos_anio_millones",
            )
            es_anterior_admin: bool | None = None
            for flag in (
                "firmado_antes_administracion_actual",
                "es_contrato_anterior",
                "contrato_administracion_anterior",
                "anterior_a_administracion",
            ):
                if isinstance(proy.get(flag), bool):
                    es_anterior_admin = proy[flag]
                    break
            if es_anterior_admin is None and fecha_firma is not None:
                es_anterior_admin = fecha_firma < fecha_corte_admin
            elif es_anterior_admin is None and anio_inicio is not None:
                anio_corte_admin = int(fecha_corte_admin[:4])
                if anio_inicio < anio_corte_admin:
                    es_anterior_admin = True
                elif anio_inicio > anio_corte_admin:
                    es_anterior_admin = False

            if pagado is not None and es_anterior_admin is not None:
                contratos_con_pago += 1
                pagado_total += pagado
                if es_anterior_admin:
                    pagado_anteriores += pagado
                    contratos_anteriores_con_pago += 1
                else:
                    pagado_nuevos += pagado
            else:
                excluidos_pregunta_1 += 1

            # Pregunta 2: Arrastre comprometido del presupuesto de inversión del año
            presup_anio = _extraer_monto_dict(
                proy,
                "compromiso_anio_millones",
                "presupuesto_anio_millones",
                "monto_presupuesto_anio_millones",
                "inversion_anio_millones",
                "asignacion_anio_millones",
            )
            arrastre_explicito = _extraer_monto_dict(
                proy,
                "arrastre_millones",
                "monto_arrastre_millones",
                "compromiso_arrastre_millones",
            )
            es_arrastre: bool | None = None
            if isinstance(proy.get("es_arrastre"), bool):
                es_arrastre = proy["es_arrastre"]
            elif isinstance(proy.get("nuevo_o_arrastre"), str):
                noa = _normalizar_texto(proy["nuevo_o_arrastre"])
                if noa == "arrastre":
                    es_arrastre = True
                elif noa == "nuevo":
                    es_arrastre = False
            elif anio_inicio is not None:
                es_arrastre = anio_inicio < anio

            if presup_anio is not None and (arrastre_explicito is not None or es_arrastre is not None):
                proyectos_con_presupuesto += 1
                presupuesto_total_anio += presup_anio
                monto_arr = (
                    arrastre_explicito
                    if arrastre_explicito is not None
                    else (presup_anio if es_arrastre else _CERO)
                )
                arrastre_comprometido += monto_arr
                if monto_arr > _CERO:
                    proyectos_arrastre += 1
            else:
                excluidos_pregunta_2 += 1

        pct_pagos_anteriores = _ratio_pct(pagado_anteriores, pagado_total) if pagado_total > _CERO else None
        pct_arrastre = _ratio_pct(arrastre_comprometido, presupuesto_total_anio) if presupuesto_total_anio > _CERO else None

    frase_p1 = (
        f"En {anio}, el {_fmt_es(pct_pagos_anteriores, 1)}% de lo pagado en obras documentadas "
        f"({_fmt_es(pagado_anteriores, 1)} de {_fmt_es(pagado_total, 1)} millones CLP) corresponde a "
        f"contratos firmados antes del {fecha_corte_admin}."
        if pct_pagos_anteriores is not None
        else f"Sin dato suficiente para calcular la proporción de pagos de contratos anteriores en {anio}."
    )
    frase_p2 = (
        f"Del presupuesto de inversión {anio} en obras documentadas ({_fmt_es(presupuesto_total_anio, 1)} millones CLP), "
        f"el {_fmt_es(pct_arrastre, 1)}% ({_fmt_es(arrastre_comprometido, 1)} millones CLP) ya estaba comprometido "
        f"por arrastre de años anteriores."
        if pct_arrastre is not None
        else f"Sin dato suficiente para calcular el arrastre presupuestario de inversión en {anio}."
    )

    return {
        "pagos_contratos_anteriores": {
            "pregunta": (
                "De lo pagado este año, ¿cuánto corresponde a contratos firmados antes de que asumiera esta administración?"
            ),
            "disponible": pct_pagos_anteriores is not None,
            "fecha_corte_administracion": fecha_corte_admin,
            "porcentaje": _fmt(pct_pagos_anteriores, 2),
            "unidad": "%",
            "monto_pagado_total_millones": _fmt(pagado_total, 3) if contratos_con_pago > 0 else None,
            "monto_pagado_contratos_anteriores_millones": _fmt(pagado_anteriores, 3) if contratos_con_pago > 0 else None,
            "monto_pagado_contratos_nuevos_millones": _fmt(pagado_nuevos, 3) if contratos_con_pago > 0 else None,
            "contratos_evaluados": contratos_con_pago,
            "contratos_anteriores": contratos_anteriores_con_pago,
            "proyectos_excluidos_sin_dato": excluidos_pregunta_1,
            "frase_ciudadana": frase_p1,
        },
        "arrastre_presupuesto": {
            "pregunta": (
                "Del presupuesto de inversión de este año, ¿cuánto ya estaba comprometido por proyectos de años anteriores?"
            ),
            "disponible": pct_arrastre is not None,
            "porcentaje": _fmt(pct_arrastre, 2),
            "unidad": "%",
            "presupuesto_inversion_anio_millones": _fmt(presupuesto_total_anio, 3) if proyectos_con_presupuesto > 0 else None,
            "monto_arrastre_comprometido_millones": _fmt(arrastre_comprometido, 3) if proyectos_con_presupuesto > 0 else None,
            "proyectos_evaluados": proyectos_con_presupuesto,
            "proyectos_en_arrastre": proyectos_arrastre,
            "proyectos_excluidos_sin_dato": excluidos_pregunta_2,
            "frase_ciudadana": frase_p2,
        },
    }


def _invocar_resumen_proyectos(
    proyectos: Sequence[Mapping[str, Any]],
    *,
    anio: int,
    fecha_cambio_administracion: str,
) -> dict[str, Any]:
    """Usa ``calcular_resumen_proyectos`` del pipeline si existe y devuelve el esquema esperado."""
    fn_ext = _cargar_calcular_resumen_proyectos_externo()
    if fn_ext is not None:
        try:
            res_ext = fn_ext(
                list(proyectos),
                anio=anio,
                fecha_cambio_administracion=fecha_cambio_administracion,
            )
            if (
                isinstance(res_ext, Mapping)
                and "pagos_contratos_anteriores" in res_ext
                and "arrastre_presupuesto" in res_ext
            ):
                return dict(res_ext)
        except TypeError:
            try:
                res_ext = fn_ext(list(proyectos))
                if (
                    isinstance(res_ext, Mapping)
                    and "pagos_contratos_anteriores" in res_ext
                    and "arrastre_presupuesto" in res_ext
                ):
                    return dict(res_ext)
            except Exception:
                pass
        except Exception:
            pass
    return calcular_resumen_proyectos(
        proyectos,
        anio=anio,
        fecha_cambio_administracion=fecha_cambio_administracion,
    )


def _cargar_proyectos_mop_normalizados() -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    datos = _leer_json_opcional(_ruta_proyectos_mop())
    if datos is None:
        return None, []

    lista: list[dict[str, Any]] = []
    if isinstance(datos.get("proyectos"), list):
        lista.extend(dict(p) for p in datos["proyectos"] if isinstance(p, Mapping))
    else:
        for clave_lista, marcar_insuf in (
            ("proyectos_documentados", False),
            ("proyectos_informacion_insuficiente", True),
            ("contratos", False),
        ):
            bloque = datos.get(clave_lista)
            if isinstance(bloque, list):
                for item in bloque:
                    if isinstance(item, Mapping):
                        copia = dict(item)
                        if marcar_insuf:
                            copia["informacion_insuficiente"] = True
                        lista.append(copia)
    return datos, lista


def _proyecto_vigente_en_anio(proy: Mapping[str, Any], anio: int, anio_corte_archivo: int | None) -> bool | None:
    anios_activos = proy.get("anios_activos")
    if isinstance(anios_activos, list) and anios_activos:
        return anio in anios_activos
    if isinstance(proy.get("anio"), int):
        return proy["anio"] == anio
    if isinstance(proy.get("anio_presupuestario"), int):
        return proy["anio_presupuestario"] == anio

    anio_ini = _extraer_anio_de_fecha(
        proy.get("anio_inicio")
        or proy.get("anio_contrato")
        or proy.get("fecha_contratacion")
        or proy.get("fecha_inicio")
        or proy.get("fecha_contrato")
        or proy.get("fecha_adjudicacion")
    )
    anio_fin = _extraer_anio_de_fecha(
        proy.get("anio_termino")
        or proy.get("fecha_termino_programada")
        or proy.get("fecha_termino")
        or proy.get("fecha_termino_vigente")
        or proy.get("fecha_termino_contractual")
    )
    # Si el corte corresponde al año consultado y el contrato tiene compromiso o pago del año, está vigente en ese corte
    if anio_corte_archivo is not None and anio == anio_corte_archivo:
        comp_a = _a_decimal_flexible(proy.get("compromiso_anio_millones"))
        pag_a = _a_decimal_flexible(proy.get("pagado_anio_millones"))
        if (comp_a is not None and comp_a > _CERO) or (pag_a is not None and pag_a > _CERO):
            return True
    if anio_ini is not None and anio_fin is not None:
        return anio_ini <= anio <= anio_fin
    if anio_ini is not None:
        if anio < anio_ini:
            return False
        if anio_corte_archivo is not None and anio == anio_corte_archivo:
            return True
        return anio >= anio_ini
    if anio_corte_archivo is not None:
        return anio == anio_corte_archivo
    return None


def _filtrar_proyectos_mop(
    proyectos: Sequence[Mapping[str, Any]],
    *,
    anio: int,
    anio_corte_archivo: int | None,
    comuna: str = "",
    institucion: str = "",
    q: str = "",
) -> tuple[list[dict[str, Any]], str]:
    comuna_filtro_norm = ""
    comuna_nombre_filtro = ""
    if comuna.strip():
        comuna_obj = _resolver_comuna_aysen(comuna, obligatoria=False)
        assert comuna_obj is not None
        comuna_filtro_norm = _normalizar_texto(comuna_obj["nombre"])
        comuna_nombre_filtro = comuna_obj["nombre"]

    inst_norm = _normalizar_texto(institucion)
    q_norm = _normalizar_texto(q)

    base_filtrada: list[dict[str, Any]] = []
    for proy in proyectos:
        # Filtro institución
        if inst_norm:
            inst_proy = _normalizar_texto(
                proy.get("institucion") or proy.get("direccion") or proy.get("servicio")
            )
            if inst_norm not in inst_proy:
                continue

        # Filtro comuna
        if comuna_filtro_norm:
            comunas_proy = [_normalizar_texto(c) for c in _lista_comunas_proyecto(proy)]
            comunas_proy_limpias = [
                re.sub(r"^(comuna de|puerto)\s+", "", c).strip() for c in comunas_proy
            ]
            coincide_comuna = any(
                comuna_filtro_norm == c
                or comuna_filtro_norm in c
                or (comuna_filtro_norm == "aysen" and ("aisen" in c or "aysen" in c))
                for c in comunas_proy_limpias
            )
            if not coincide_comuna:
                continue

        # Filtro texto libre q (sin tildes)
        if q_norm:
            campos_busqueda = " ".join(
                str(proy.get(k) or "")
                for k in (
                    "nombre",
                    "nombre_proyecto",
                    "nombre_contrato",
                    "nombre_obra",
                    "obra",
                    "proyecto",
                    "codigo_bip",
                    "bip",
                    "codigo_safi",
                    "safi",
                    "id_contrato",
                    "codigo_contrato",
                    "contrato",
                    "contratista",
                    "empresa_contratista",
                    "institucion",
                    "direccion",
                    "servicio",
                )
            ) + " " + " ".join(_lista_comunas_proyecto(proy))
            if q_norm not in _normalizar_texto(campos_busqueda):
                continue

        copia = dict(proy)
        copia["vigente_en_anio"] = _proyecto_vigente_en_anio(proy, anio, anio_corte_archivo)
        base_filtrada.append(copia)

    # Filtro por año: si hay proyectos vigentes en el año solicitado, filtra a los vigentes;
    # si el corte MOP es de otro año (p.ej. corte 2026) y se consulta otro año sin histórico,
    # mantiene los registros marcando explícitamente vigente_en_anio y declarando cobertura_anio.
    vigentes = [p for p in base_filtrada if p.get("vigente_en_anio") is True]
    if vigentes:
        cobertura = (
            f"Contratos vigentes o con ejecución documentada en {anio}"
            + (f" para la comuna de {comuna_nombre_filtro}" if comuna_nombre_filtro else " en la Región de Aysén")
            + "."
        )
        return vigentes, cobertura

    if anio_corte_archivo is not None and anio != anio_corte_archivo and base_filtrada:
        cobertura = (
            f"El corte MOP DGOP disponible corresponde al ejercicio {anio_corte_archivo}; "
            f"se muestran los contratos del corte con su indicador de vigencia para {anio}."
        )
        return base_filtrada, cobertura

    return base_filtrada, f"Corte de contratos MOP DGOP consultado para {anio}."


# ---------------------------------------------------------------------------
# Helpers PIB (economia y tarjeta resumen)
# ---------------------------------------------------------------------------


def _cargar_indice_pib() -> tuple[dict[str, Any] | None, dict[tuple[str, int, str, str], Decimal], list[int]]:
    lote = _leer_json_opcional(_ruta_pib_oficial())
    if lote is None or not isinstance(lote.get("observaciones"), list):
        return None, {}, []
    indice: dict[tuple[str, int, str, str], Decimal] = {}
    anios: set[int] = set()
    for fila in lote["observaciones"]:
        if not isinstance(fila, Mapping):
            continue
        terr = fila.get("territorio")
        anio = fila.get("anio")
        metrica = fila.get("metrica")
        val = fila.get("valoracion")
        num = _a_decimal_flexible(fila.get("valor"))
        if isinstance(terr, str) and type(anio) is int and isinstance(metrica, str) and isinstance(val, str):
            anios.add(anio)
            if num is not None:
                indice[(terr, anio, metrica, val)] = num
    return lote, indice, sorted(anios)


# ---------------------------------------------------------------------------
# ENDPOINT 1: GET /api/v1/aysen/resumen
# ---------------------------------------------------------------------------


def _anio_corte_mop(datos_mop: Mapping[str, Any] | None) -> int | None:
    if not isinstance(datos_mop, Mapping):
        return None
    pub = datos_mop.get("publicacion") if isinstance(datos_mop.get("publicacion"), Mapping) else {}
    for cand in (datos_mop.get("anio_corte"), pub.get("anio_corte"), datos_mop.get("anio")):
        if isinstance(cand, int) and not isinstance(cand, bool):
            return cand
    return None


@router.get("/resumen")
def aysen_resumen(
    anio: Annotated[int, Query(ge=2013, le=2030)] = 2025,
    comuna: str = "",
):
    comuna_sel = _resolver_comuna_aysen(comuna, obligatoria=False)
    lote_pib, indice_pib, anios_pib = _cargar_indice_pib()
    ultimo_anio_pib = anios_pib[-1] if anios_pib else None

    datos_dipres, origen_dipres = _obtener_datos_dipres_piloto(anio)
    datos_dipres_prev, _ = _obtener_datos_dipres_piloto(anio - 1) if anio > 2013 else (None, None)
    datos_mop, lista_mop = _cargar_proyectos_mop_normalizados()
    sinim_oficial = _leer_json_opcional(_ruta_sinim_oficial())

    mes_corte_vigente = _normalizar_mes_corte(datos_dipres) if datos_dipres is not None else None
    es_anio_en_curso = anio >= 2026 or (mes_corte_vigente is not None and mes_corte_vigente < 12)

    # --- Tarjeta 1: Economía (PIB real Aysén vs Chile) ---
    crec_aysen = indice_pib.get(("11", anio, "crecimiento", "real"))
    crec_chile = indice_pib.get(("CL", anio, "crecimiento", "real"))
    if crec_aysen is not None:
        dif_pp = (crec_aysen - crec_chile) if crec_chile is not None else None
        signo_dif = "+" if (dif_pp is not None and dif_pp >= _CERO) else ""
        if crec_chile is not None and dif_pp is not None:
            frase_eco = (
                f"En {anio}, la economía de Aysén creció {_fmt_es(crec_aysen, 1)}% en términos reales, "
                f"frente a {_fmt_es(crec_chile, 1)}% de Chile ({signo_dif}{_fmt_es(dif_pp, 1)} puntos porcentuales)."
            )
        else:
            frase_eco = f"En {anio}, la economía de Aysén varió {_fmt_es(crec_aysen, 1)}% en términos reales."
        cobertura_eco = "Región de Aysén vs Chile (BCCh Cuentas Nacionales; el PIB oficial no se calcula a escala comunal)."
        tarjeta_economia: dict[str, Any] = {
            "id": "economia",
            "titulo": "Crecimiento económico de Aysén vs Chile",
            "disponible": True,
            "valor": _fmt(crec_aysen, 2),
            "valor_chile": _fmt(crec_chile, 2),
            "diferencia_pp": _fmt(dif_pp, 2),
            "unidad": "%",
            "periodo": f"{anio} (cierre anual oficial)",
            "cobertura": cobertura_eco,
            "frase_ciudadana": frase_eco,
            "pestana_destino": "economia",
            "fuente": "Banco Central de Chile (BDE)",
            "url_fuente": URL_BCCH_SIETE,
            "ultimo_anio_disponible": ultimo_anio_pib,
            "motivo_no_disponible": None,
        }
    else:
        motivo_eco = (
            f"Sin cierre anual oficial de PIB para {anio} en el Banco Central de Chile."
            + (f" Último cierre oficial disponible: {ultimo_anio_pib}." if ultimo_anio_pib else "")
        )
        tarjeta_economia = {
            "id": "economia",
            "titulo": "Crecimiento económico de Aysén vs Chile",
            "disponible": False,
            "valor": None,
            "valor_chile": None,
            "diferencia_pp": None,
            "unidad": "%",
            "periodo": f"{anio} (sin cierre anual publicado)",
            "cobertura": "Región de Aysén vs Chile (BCCh Cuentas Nacionales)",
            "frase_ciudadana": motivo_eco,
            "pestana_destino": "economia",
            "fuente": "Banco Central de Chile (BDE)",
            "url_fuente": URL_BCCH_SIETE,
            "ultimo_anio_disponible": ultimo_anio_pib,
            "motivo_no_disponible": motivo_eco,
        }

    # --- Tarjeta 2: Inversión / capital ejecutada observable (GORE Aysén + Vialidad MOP) ---
    gore_bloque = _extraer_bloque_gore(datos_dipres)
    gore_inv_val = _a_decimal(gore_bloque.get("inversion_millones")) or _CERO
    gore_tcap_val = _a_decimal(gore_bloque.get("transferencias_capital_millones")) or _CERO
    gore_cap_total = (gore_inv_val + gore_tcap_val) if gore_bloque["disponible"] else None

    # Contratos Vialidad MOP en Aysén (para el año y comuna si aplica)
    anio_corte_mop = _anio_corte_mop(datos_mop)
    mop_vialidad_pagado: Decimal | None = None
    if lista_mop:
        proys_vialidad, _ = _filtrar_proyectos_mop(
            lista_mop,
            anio=anio,
            anio_corte_archivo=anio_corte_mop,
            comuna=comuna_sel["nombre"] if comuna_sel else "",
            institucion="vialidad",
        )
        if anio_corte_mop is None or anio == anio_corte_mop:
            pagos_v = [
                _extraer_monto_dict(p, "pagado_anio_millones", "monto_pagado_anio_millones", "ejecutado_anio_millones")
                for p in proys_vialidad
                if not _es_proyecto_informacion_insuficiente(p)
            ]
            pagos_v_validos = [v for v in pagos_v if v is not None]
            if pagos_v_validos:
                with localcontext(_CONTEXTO_DECIMAL):
                    mop_vialidad_pagado = sum(pagos_v_validos, _CERO)

    instituciones_inv: list[str] = []
    inversion_observable: Decimal | None = None
    with localcontext(_CONTEXTO_DECIMAL):
        if gore_cap_total is not None and gore_cap_total > _CERO:
            instituciones_inv.append("Gobierno Regional de Aysén (Subt. 29–31 y 33 / DIPRES)")
            inversion_observable = (inversion_observable or _CERO) + gore_cap_total
        if mop_vialidad_pagado is not None and mop_vialidad_pagado > _CERO:
            instituciones_inv.append("Dirección de Vialidad MOP — obras territorializadas en Aysén (DGOP)")
            inversion_observable = (inversion_observable or _CERO) + mop_vialidad_pagado

    # Comparación contra mismo período del año anterior (solo si mes de corte coincide o viene calculada)
    comparacion_inv: dict[str, Any] = {
        "disponible": False,
        "mes_corte_actual": mes_corte_vigente,
        "anio_anterior": anio - 1,
        "mes_corte_anterior": None,
        "valor_anio_anterior_millones": None,
        "variacion_pct": None,
        "nota": "Sin corte comparable del mismo período del año anterior.",
    }
    if isinstance(gore_bloque.get("comparacion_mismo_mes_anterior"), Mapping) and gore_bloque["comparacion_mismo_mes_anterior"].get("disponible"):
        comp_src = gore_bloque["comparacion_mismo_mes_anterior"]
        val_ant = _extraer_monto_dict(comp_src, "ejecutado_mismo_mes_anterior_millones", "inversion_anio_anterior_millones")
        var_pct = _a_decimal_flexible(comp_src.get("variacion_nominal_pct") or comp_src.get("variacion_pct"))
        comparacion_inv = {
            "disponible": var_pct is not None or val_ant is not None,
            "mes_corte_actual": comp_src.get("mes_corte") or mes_corte_vigente,
            "anio_anterior": comp_src.get("anio_anterior") or (anio - 1),
            "mes_corte_anterior": comp_src.get("mes_corte") or mes_corte_vigente,
            "etiqueta": comp_src.get("etiqueta"),
            "valor_anio_anterior_millones": _fmt(val_ant, 3),
            "variacion_pct": _fmt(var_pct, 2),
            "nota": comp_src.get("nota") or "Comparación interanual acumulada al mismo mes de corte.",
        }
    elif isinstance(datos_dipres, Mapping) and isinstance(datos_dipres.get("comparacion_mismo_mes"), Mapping):
        comp_src = datos_dipres["comparacion_mismo_mes"]
        val_ant = _extraer_monto_dict(comp_src, "inversion_anio_anterior_millones", "valor_anio_anterior_millones")
        var_pct = _a_decimal_flexible(comp_src.get("variacion_inversion_pct") or comp_src.get("variacion_pct"))
        comparacion_inv = {
            "disponible": var_pct is not None or val_ant is not None,
            "mes_corte_actual": comp_src.get("mes_corte") or mes_corte_vigente,
            "anio_anterior": comp_src.get("anio_anterior") or (anio - 1),
            "mes_corte_anterior": comp_src.get("mes_corte_anterior") or comp_src.get("mes_corte") or mes_corte_vigente,
            "valor_anio_anterior_millones": _fmt(val_ant, 3),
            "variacion_pct": _fmt(var_pct, 2),
            "nota": comp_src.get("nota") or "Comparación interanual acumulada al mismo mes de corte.",
        }
    elif datos_dipres_prev is not None and gore_cap_total is not None:
        mes_prev = _normalizar_mes_corte(datos_dipres_prev)
        gore_prev = _extraer_bloque_gore(datos_dipres_prev)
        if mes_corte_vigente is not None and mes_prev == mes_corte_vigente and gore_prev["disponible"]:
            prev_cap = (_a_decimal(gore_prev.get("inversion_millones")) or _CERO) + (
                _a_decimal(gore_prev.get("transferencias_capital_millones")) or _CERO
            )
            var_pct = _ratio_pct(gore_cap_total - prev_cap, prev_cap) if prev_cap > _CERO else None
            comparacion_inv = {
                "disponible": var_pct is not None,
                "mes_corte_actual": mes_corte_vigente,
                "anio_anterior": anio - 1,
                "mes_corte_anterior": mes_prev,
                "valor_anio_anterior_millones": _fmt(prev_cap, 3),
                "variacion_pct": _fmt(var_pct, 2),
                "nota": (
                    f"Comparación interanual de capital GORE Aysén acumulada a {_MESES_NOMBRE.get(mes_corte_vigente, str(mes_corte_vigente))} "
                    f"({anio} vs {anio - 1})."
                ),
            }
        elif mes_corte_vigente is not None and mes_prev is not None and mes_prev != mes_corte_vigente:
            comparacion_inv["mes_corte_anterior"] = mes_prev
            comparacion_inv["nota"] = (
                f"El corte {anio} llega a {_MESES_NOMBRE.get(mes_corte_vigente, str(mes_corte_vigente))} "
                f"(mes {mes_corte_vigente}) mientras {anio - 1} corresponde a {_MESES_NOMBRE.get(mes_prev, str(mes_prev))} "
                f"(mes {mes_prev}); no se comparan períodos desiguales."
            )

    if inversion_observable is not None:
        nombre_mes = _MESES_NOMBRE.get(mes_corte_vigente, "") if mes_corte_vigente else ""
        periodo_inv = (
            f"{anio} (acumulado a {nombre_mes}, mes {mes_corte_vigente})"
            if (es_anio_en_curso and mes_corte_vigente and mes_corte_vigente < 12)
            else f"{anio} (cierre anual)"
        )
        cobertura_inv = " + ".join(instituciones_inv)
        frase_inv = (
            f"En {periodo_inv}, la inversión y transferencias de capital observables en Aysén suman "
            f"${_fmt_es(inversion_observable, 1)} millones CLP ({cobertura_inv})."
        )
        tarjeta_inversion: dict[str, Any] = {
            "id": "inversion",
            "titulo": "Inversión y capital ejecutado observable",
            "disponible": True,
            "valor": _fmt(inversion_observable, 3),
            "unidad": "millones CLP",
            "periodo": periodo_inv,
            "mes_corte": mes_corte_vigente,
            "es_anio_en_curso": es_anio_en_curso,
            "instituciones_cubiertas": instituciones_inv,
            "cobertura": cobertura_inv,
            "comparacion_mismo_periodo_anterior": comparacion_inv,
            "frase_ciudadana": frase_inv,
            "pestana_destino": "presupuestos",
            "fuente": "DIPRES · MOP DGOP",
            "url_fuente": gore_bloque.get("url_fuente") or URL_DIPRES_CKAN,
            "motivo_no_disponible": None,
        }
    else:
        motivo_inv = f"Sin dato oficial de ejecución de inversión/capital DIPRES o MOP para {anio}."
        tarjeta_inversion = {
            "id": "inversion",
            "titulo": "Inversión y capital ejecutado observable",
            "disponible": False,
            "valor": None,
            "unidad": "millones CLP",
            "periodo": f"{anio} (sin dato disponible)",
            "mes_corte": mes_corte_vigente,
            "es_anio_en_curso": es_anio_en_curso,
            "instituciones_cubiertas": [],
            "cobertura": "Sin instituciones con ejecución documentada para el año seleccionado.",
            "comparacion_mismo_periodo_anterior": comparacion_inv,
            "frase_ciudadana": motivo_inv,
            "pestana_destino": "presupuestos",
            "fuente": "DIPRES · MOP DGOP",
            "url_fuente": URL_DIPRES_CKAN,
            "motivo_no_disponible": motivo_inv,
        }

    # --- Tarjeta 3: Arrastre presupuestario de contratos MOP ---
    tarjeta_arrastre: dict[str, Any]
    if lista_mop:
        proys_filtrados, cobertura_mop = _filtrar_proyectos_mop(
            lista_mop,
            anio=anio,
            anio_corte_archivo=anio_corte_mop,
            comuna=comuna_sel["nombre"] if comuna_sel else "",
        )
        fecha_cambio = _fecha_cambio_administracion(anio, datos_mop)
        resumen_proys = _invocar_resumen_proyectos(
            proys_filtrados,
            anio=anio,
            fecha_cambio_administracion=fecha_cambio,
        )
        arr = resumen_proys["arrastre_presupuesto"]
        corte_coincide = anio_corte_mop is None or anio == anio_corte_mop
        if arr.get("disponible") and corte_coincide:
            url_mop = (
                (datos_mop.get("fuente_trazabilidad") or {}).get("url_fuente")
                if isinstance(datos_mop, Mapping) and isinstance(datos_mop.get("fuente_trazabilidad"), Mapping)
                else None
            ) or URL_MOP_DGOP
            tarjeta_arrastre = {
                "id": "arrastre",
                "titulo": "Arrastre comprometido en inversión MOP",
                "disponible": True,
                "valor": arr.get("porcentaje"),
                "unidad": "%",
                "periodo": f"{anio} (contratos documentados MOP)",
                "cobertura": cobertura_mop,
                "monto_arrastre_millones": arr.get("monto_arrastre_comprometido_millones"),
                "presupuesto_inversion_millones": arr.get("presupuesto_inversion_anio_millones"),
                "frase_ciudadana": arr.get("frase_ciudadana"),
                "pestana_destino": "proyectos",
                "fuente": "MOP · Dirección General de Obras Públicas (DGOP)",
                "url_fuente": url_mop,
                "motivo_no_disponible": None,
            }
        else:
            motivo_arr = (
                f"Sin dato de arrastre presupuestario MOP documentado para {anio}."
                + (f" Corte MOP disponible: {anio_corte_mop}." if anio_corte_mop else "")
            )
            tarjeta_arrastre = {
                "id": "arrastre",
                "titulo": "Arrastre comprometido en inversión MOP",
                "disponible": False,
                "valor": None,
                "unidad": "%",
                "periodo": f"{anio} (sin dato disponible)",
                "cobertura": cobertura_mop,
                "monto_arrastre_millones": None,
                "presupuesto_inversion_millones": None,
                "frase_ciudadana": motivo_arr,
                "pestana_destino": "proyectos",
                "fuente": "MOP · Dirección General de Obras Públicas (DGOP)",
                "url_fuente": URL_MOP_DGOP,
                "motivo_no_disponible": motivo_arr,
            }
    else:
        motivo_arr = (
            "El archivo oficial de proyectos MOP en Aysén (data/published/proyectos-mop-aysen.json) "
            "aún no está disponible."
        )
        tarjeta_arrastre = {
            "id": "arrastre",
            "titulo": "Arrastre comprometido en inversión MOP",
            "disponible": False,
            "valor": None,
            "unidad": "%",
            "periodo": f"{anio} (pendiente corte MOP DGOP)",
            "cobertura": "Región de Aysén · Obras MOP DGOP",
            "monto_arrastre_millones": None,
            "presupuesto_inversion_millones": None,
            "frase_ciudadana": motivo_arr,
            "pestana_destino": "proyectos",
            "fuente": "MOP · Dirección General de Obras Públicas (DGOP)",
            "url_fuente": URL_MOP_DGOP,
            "motivo_no_disponible": motivo_arr,
        }

    pub_pib = lote_pib.get("publicacion") if isinstance(lote_pib, Mapping) and isinstance(lote_pib.get("publicacion"), Mapping) else {}
    return {
        "territorio": {
            "region_codigo": "11",
            "region_nombre": "Aysén del General Carlos Ibáñez del Campo",
            "comuna_seleccionada": comuna_sel,
        },
        "anio_seleccionado": anio,
        "anios_disponibles": list(ANIOS_DISPONIBLES),
        "mes_corte_vigente": mes_corte_vigente if es_anio_en_curso else None,
        "comunas_aysen": _catalogo_comunas_aysen(sinim_oficial),
        "tarjetas": {
            "economia": tarjeta_economia,
            "inversion": tarjeta_inversion,
            "arrastre": tarjeta_arrastre,
        },
        "fuente_trazabilidad": {
            "pib_publicacion_id": pub_pib.get("id"),
            "pib_ultimo_anio": ultimo_anio_pib,
            "dipres_origen": origen_dipres or "no_disponible",
            "mop_disponible": bool(lista_mop),
            "sinim_oficial_disponible": sinim_oficial is not None,
            "enlaces_oficiales": {
                "bcch": URL_BCCH_SIETE,
                "dipres": URL_DIPRES_CKAN,
                "mop_dgop": URL_MOP_DGOP,
                "sinim": "https://datos.sinim.gov.cl/",
            },
        },
    }


# ---------------------------------------------------------------------------
# ENDPOINT 2: GET /api/v1/aysen/economia
# ---------------------------------------------------------------------------


@router.get("/economia")
def aysen_economia(
    anio: Annotated[int, Query(ge=2013, le=2030)] = 2025,
):
    lote_pib, indice_pib, anios_pib = _cargar_indice_pib()
    sectorial = _leer_json_opcional(_ruta_sectorial())
    ultimo_anio_pib = anios_pib[-1] if anios_pib else None

    # Serie 2013-2025 de crecimiento real Aysén y Chile
    serie_crecimiento: list[dict[str, Any]] = []
    serie_participacion: list[dict[str, Any]] = []
    for yr in anios_pib:
        c_aysen = indice_pib.get(("11", yr, "crecimiento", "real"))
        c_chile = indice_pib.get(("CL", yr, "crecimiento", "real"))
        dif = (c_aysen - c_chile) if (c_aysen is not None and c_chile is not None) else None
        serie_crecimiento.append(
            {
                "anio": yr,
                "crecimiento_aysen_pct": _fmt(c_aysen, 2),
                "crecimiento_chile_pct": _fmt(c_chile, 2),
                "diferencia_pp": _fmt(dif, 2),
            }
        )

        part = indice_pib.get(("11", yr, "participacion", "nominal"))
        nom_aysen = indice_pib.get(("11", yr, "nivel", "nominal"))
        nom_chile = indice_pib.get(("CL", yr, "nivel", "nominal"))
        serie_participacion.append(
            {
                "anio": yr,
                "participacion_aysen_pct": _fmt(part, 2),
                "pib_nominal_aysen_millones": _fmt(nom_aysen, 2),
                "pib_nominal_chile_millones": _fmt(nom_chile, 2),
            }
        )

    por_anio_sec = sectorial.get("por_anio") if isinstance(sectorial, Mapping) and isinstance(sectorial.get("por_anio"), Mapping) else {}
    datos_anio_disponibles = (anio in anios_pib) or (str(anio) in por_anio_sec)

    aviso_sin_cierre: str | None = None
    if not datos_anio_disponibles:
        aviso_sin_cierre = (
            f"Aún no existe cierre anual oficial del PIB regional para {anio} en el Banco Central de Chile. "
            + (
                f"El último año anual publicado es {ultimo_anio_pib}; no se proyectan ni inventan cifras para {anio}."
                if ultimo_anio_pib is not None
                else "No se inventan cifras para años sin publicación oficial."
            )
        )

    # Extraer actividades del año seleccionado (13 actividades) y del año previo (t-1) para aporte_estimado_pp
    actividades_salida: list[dict[str, Any]] = []
    resumen_estructural: dict[str, Any] = {
        "crecimiento_real_aysen_pct": _fmt(indice_pib.get(("11", anio, "crecimiento", "real")), 2),
        "crecimiento_real_chile_pct": _fmt(indice_pib.get(("CL", anio, "crecimiento", "real")), 2),
        "participacion_nominal_aysen_pct": _fmt(indice_pib.get(("11", anio, "participacion", "nominal")), 2),
        "pib_nominal_aysen_millones": _fmt(indice_pib.get(("11", anio, "nivel", "nominal")), 2),
        "pib_real_aysen_millones": _fmt(indice_pib.get(("11", anio, "nivel", "real")), 2),
        "hhi": None,
        "diversificacion": None,
        "indice_krugman": None,
    }

    if datos_anio_disponibles and str(anio) in por_anio_sec:
        bloque_anio = por_anio_sec[str(anio)]
        reg_aysen = (
            (bloque_anio.get("regiones") or {}).get("11")
            if isinstance(bloque_anio, Mapping) and isinstance(bloque_anio.get("regiones"), Mapping)
            else None
        )
        bloque_prev = por_anio_sec.get(str(anio - 1))
        reg_aysen_prev = (
            (bloque_prev.get("regiones") or {}).get("11")
            if isinstance(bloque_prev, Mapping) and isinstance(bloque_prev.get("regiones"), Mapping)
            else None
        )
        pesos_prev: dict[str, Decimal] = {}
        if isinstance(reg_aysen_prev, Mapping) and isinstance(reg_aysen_prev.get("actividades"), list):
            for act_prev in reg_aysen_prev["actividades"]:
                if isinstance(act_prev, Mapping) and act_prev.get("actividad_id"):
                    p_val = _a_decimal_flexible(act_prev.get("participacion_nominal_pct"))
                    if p_val is not None:
                        pesos_prev[str(act_prev["actividad_id"])] = p_val

        if isinstance(reg_aysen, Mapping):
            resumen_estructural["hhi"] = _fmt(_a_decimal_flexible(reg_aysen.get("hhi")), 2)
            resumen_estructural["diversificacion"] = _fmt(_a_decimal_flexible(reg_aysen.get("diversificacion")), 4)
            resumen_estructural["indice_krugman"] = _fmt(_a_decimal_flexible(reg_aysen.get("indice_krugman")), 4)
            acts_raw = reg_aysen.get("actividades") if isinstance(reg_aysen.get("actividades"), list) else []
            with localcontext(_CONTEXTO_DECIMAL):
                for act in acts_raw:
                    if not isinstance(act, Mapping):
                        continue
                    act_id = str(act.get("actividad_id") or "")
                    peso_nom = _a_decimal_flexible(act.get("participacion_nominal_pct"))
                    val_nom = _a_decimal_flexible(act.get("nominal_millones"))
                    val_real = _a_decimal_flexible(act.get("real_millones"))
                    crec_real = _a_decimal_flexible(act.get("crecimiento_real_pct"))
                    lq = _a_decimal_flexible(act.get("lq_especializacion"))
                    peso_prev = pesos_prev.get(act_id)

                    aporte_est: Decimal | None = None
                    if peso_prev is not None and crec_real is not None:
                        aporte_est = (peso_prev * crec_real) / _CIEN

                    actividades_salida.append(
                        {
                            "actividad_id": act_id,
                            "nombre": act.get("nombre"),
                            "participacion_nominal_pct": _fmt(peso_nom, 2),
                            "nominal_millones": _fmt(val_nom, 2),
                            "real_millones": _fmt(val_real, 2),
                            "crecimiento_real_pct": _fmt(crec_real, 2),
                            "lq_especializacion": _fmt(lq, 2),
                            "participacion_nominal_anio_previo_pct": _fmt(peso_prev, 2),
                            "aporte_estimado_pp": _fmt(aporte_est, 2),
                            "es_aproximacion_aporte": aporte_est is not None,
                            "nota_aporte_estimado": (
                                "Aproximación por peso nominal del año previo debido a no aditividad de volúmenes encadenados."
                                if aporte_est is not None
                                else "Sin año previo o sin crecimiento real disponible para estimar aporte."
                            ),
                            "serie_bde_real": act.get("serie_bde_real"),
                            "serie_bde_nominal": act.get("serie_bde_nominal"),
                        }
                    )

    # Ordenamientos solicitados
    sectores_crecieron = sorted(
        [
            a
            for a in actividades_salida
            if a["crecimiento_real_pct"] is not None and Decimal(a["crecimiento_real_pct"]) > _CERO
        ],
        key=lambda item: Decimal(item["crecimiento_real_pct"]),
        reverse=True,
    )
    sectores_cayeron = sorted(
        [
            a
            for a in actividades_salida
            if a["crecimiento_real_pct"] is not None and Decimal(a["crecimiento_real_pct"]) < _CERO
        ],
        key=lambda item: Decimal(item["crecimiento_real_pct"]),
    )
    top_aportantes = sorted(
        [a for a in actividades_salida if a["aporte_estimado_pp"] is not None],
        key=lambda item: Decimal(item["aporte_estimado_pp"]),
        reverse=True,
    )

    # Frase pedagógica distinguiendo tamaño vs aporte al crecimiento del año
    frase_tamano_vs_aporte: str | None = None
    if actividades_salida and top_aportantes:
        por_tamano = sorted(
            [a for a in actividades_salida if a["participacion_nominal_pct"] is not None],
            key=lambda item: Decimal(item["participacion_nominal_pct"]),
            reverse=True,
        )
        mayor_tamano = por_tamano[0] if por_tamano else None
        segundo_tamano = por_tamano[1] if len(por_tamano) > 1 else None
        mayor_aporte = top_aportantes[0]
        # Buscar una actividad grande que no sea el principal motor o Administración pública si existe
        contraste = next(
            (a for a in por_tamano if a["actividad_id"] == "administracion_publica" and a["actividad_id"] != mayor_aporte["actividad_id"]),
            segundo_tamano if (segundo_tamano and segundo_tamano["actividad_id"] != mayor_aporte["actividad_id"]) else None,
        )
        if mayor_tamano and contraste and contraste.get("aporte_estimado_pp") is not None:
            ap_motor = Decimal(mayor_aporte["aporte_estimado_pp"])
            sig_m = "+" if ap_motor >= _CERO else ""
            ap_con = Decimal(contraste["aporte_estimado_pp"])
            sig_c = "+" if ap_con >= _CERO else ""
            frase_tamano_vs_aporte = (
                f"En {anio}, {mayor_aporte['nombre']} explica el mayor aporte estimado al crecimiento "
                f"({sig_m}{_fmt_es(ap_motor, 2)} pp aprox., con un peso nominal de "
                f"{_fmt_es(Decimal(mayor_aporte['participacion_nominal_pct']), 2)}% y variación real de "
                f"{_fmt_es(Decimal(mayor_aporte['crecimiento_real_pct']), 2)}%). En contraste, "
                f"{contraste['nombre']} representa el {_fmt_es(Decimal(contraste['participacion_nominal_pct']), 2)}% "
                f"del tamaño de la economía regional, pero su aporte estimado al crecimiento del año fue "
                f"{sig_c}{_fmt_es(ap_con, 2)} pp aprox. (variación real de "
                f"{_fmt_es(Decimal(contraste['crecimiento_real_pct']), 2)}%). "
                "El tamaño de una actividad no equivale a cuánto explica el crecimiento de un año."
            )
        elif mayor_aporte:
            ap_motor = Decimal(mayor_aporte["aporte_estimado_pp"])
            sig_m = "+" if ap_motor >= _CERO else ""
            frase_tamano_vs_aporte = (
                f"En {anio}, {mayor_aporte['nombre']} registró el mayor aporte estimado al crecimiento "
                f"({sig_m}{_fmt_es(ap_motor, 2)} pp aprox.) con un peso nominal de "
                f"{_fmt_es(Decimal(mayor_aporte['participacion_nominal_pct']), 2)}%. "
                "El tamaño estructural de una actividad no determina por sí solo su aporte al crecimiento anual."
            )
    elif not datos_anio_disponibles:
        frase_tamano_vs_aporte = aviso_sin_cierre

    pub_pib = lote_pib.get("publicacion") if isinstance(lote_pib, Mapping) and isinstance(lote_pib.get("publicacion"), Mapping) else {}
    pub_sec = sectorial.get("publicacion") if isinstance(sectorial, Mapping) and isinstance(sectorial.get("publicacion"), Mapping) else {}

    return {
        "territorio": {
            "region_codigo": "11",
            "region_nombre": "Aysén del General Carlos Ibáñez del Campo",
        },
        "anio_seleccionado": anio,
        "ultimo_anio_pib": ultimo_anio_pib,
        "datos_anio_disponibles": datos_anio_disponibles,
        "aviso_sin_cierre_anual": aviso_sin_cierre,
        "anios_pib_disponibles": anios_pib,
        "resumen_anio": resumen_estructural,
        "serie_crecimiento": serie_crecimiento,
        "serie_participacion": serie_participacion,
        "actividades": actividades_salida,
        "total_actividades": len(actividades_salida),
        "nota_metodologica_aporte": (
            "El campo aporte_estimado_pp es una aproximación calculada como "
            "(participación nominal del año previo × crecimiento real del año / 100), "
            "debido a la no aditividad de los volúmenes reales encadenados de Cuentas Nacionales."
        ),
        "sectores_crecieron": sectores_crecieron,
        "sectores_cayeron": sectores_cayeron,
        "top_aportantes": top_aportantes,
        "frase_tamano_vs_aporte": frase_tamano_vs_aporte,
        "fuente_trazabilidad": {
            "institucion": "Banco Central de Chile (BDE SI3 · Cuentas Nacionales)",
            "publicacion_pib_id": pub_pib.get("id"),
            "publicacion_pib_fecha": pub_pib.get("fecha"),
            "publicacion_sectorial_id": pub_sec.get("id"),
            "publicacion_sectorial_fecha": pub_sec.get("fecha"),
            "enlaces_oficiales": {
                "bde_siete": URL_BCCH_SIETE,
                "cuentas_nacionales": URL_BCCH_CCNN,
            },
            "regla_no_aditividad_volumenes_encadenados": True,
        },
    }


# ---------------------------------------------------------------------------
# ENDPOINT 3: GET /api/v1/aysen/presupuestos
# ---------------------------------------------------------------------------


def _ejecutar_consolidacion_aysen(
    *,
    anio: int,
    gore_bloque: Mapping[str, Any],
    servicios_aysen: Sequence[Mapping[str, Any]],
    municipal_bloque: Mapping[str, Any],
    datos_dipres: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Ejecuta consolidación anti-duplicación con ``pipelines.fiscal.conciliacion.consolidar_billeteras``."""
    conc_mod = _cargar_modulo_opcional("pipelines.fiscal.conciliacion")
    if conc_mod is None:
        return {
            "disponible": False,
            "motivo": "Módulo de conciliación fiscal no disponible.",
        }

    movimientos: list[dict[str, Any]] = []
    transferencias_conciliadas: list[dict[str, Any]] = []
    instituciones_cubiertas: list[str] = []
    instituciones_excluidas: list[dict[str, str]] = [
        {
            "institucion": "Gobierno Central Total (Chile — Nivel Nacional)",
            "motivo": "Escala nacional; no corresponde sumarlo dentro del presupuesto regional de Aysén.",
        },
        {
            "institucion": "Dirección de Vialidad MOP — Presupuesto Nacional DIPRES",
            "motivo": "El capítulo DIPRES es de alcance nacional sin desglose territorial regional; para Aysén se muestran sus contratos MOP DGOP por separado.",
        },
    ]

    # 1. Billetera Regional: GORE Aysén (separando gasto propio de transferencias de capital Subt. 33)
    if gore_bloque.get("disponible"):
        gore_ejec = _a_decimal(gore_bloque.get("ejecutado_millones"))
        gore_tcap = _a_decimal(gore_bloque.get("transferencias_capital_millones")) or _CERO
        if gore_ejec is not None and gore_ejec > _CERO:
            instituciones_cubiertas.append("Gobierno Regional de Aysén (billetera regional)")
            with localcontext(_CONTEXTO_DECIMAL):
                gore_propio = gore_ejec - gore_tcap if gore_ejec >= gore_tcap else gore_ejec
            if gore_propio > _CERO:
                movimientos.append(
                    {
                        "id_movimiento": f"gore-aysen-propio-{anio}",
                        "billetera": "regional",
                        "monto": gore_propio,
                        "etapa": "devengo",
                        "territorio": "11",
                        "es_transferencia_interna": False,
                        "ejecutor": "Gobierno Regional de Aysén",
                        "ejercicio": anio,
                    }
                )
            if gore_tcap > _CERO and gore_ejec >= gore_tcap:
                movimientos.append(
                    {
                        "id_movimiento": f"gore-aysen-subt33-{anio}",
                        "billetera": "regional",
                        "monto": gore_tcap,
                        "etapa": "devengo",
                        "territorio": "11",
                        "es_transferencia_interna": True,
                        "financiador": "Gobierno Regional de Aysén",
                        "ejecutor": "Gobierno Regional de Aysén (Subt. 33)",
                        "ejercicio": anio,
                    }
                )

    # 2. Billetera Sectorial: Servicios públicos identificables en Aysén (ej. Salud Aysén, SLEP Aysén, DPR)
    for idx, srv in enumerate(servicios_aysen):
        monto_srv = _a_decimal(srv.get("total_gasto_millones"))
        if monto_srv is None or monto_srv <= _CERO:
            continue
        nombre_srv = str(srv.get("nombre") or f"Servicio {idx + 1}")
        instituciones_cubiertas.append(f"{nombre_srv} (billetera sectorial en Aysén)")
        norm_srv = _normalizar_texto(nombre_srv)
        # Detectar transferencias explícitas de SUBDERE a GORE para marcarlas como transferencia interna
        es_traspaso_gore = "desarrollo regional" in norm_srv or "transferencias a gobiernos regionales" in norm_srv
        movimientos.append(
            {
                "id_movimiento": f"srv-aysen-{idx + 1}-{anio}",
                "billetera": "sectorial",
                "monto": monto_srv,
                "etapa": "devengo",
                "territorio": "11",
                "es_transferencia_interna": es_traspaso_gore,
                "ejecutor": nombre_srv,
                "ejercicio": anio,
            }
        )

    # 3. Billetera Municipal: Municipalidad seleccionada (ej. 11201 Aysén)
    if municipal_bloque.get("disponible"):
        monto_mun = _a_decimal(municipal_bloque.get("devengado_bep_millones"))
        if monto_mun is not None and monto_mun > _CERO:
            cut = str(municipal_bloque.get("cut") or "11201")
            nombre_mun = str(municipal_bloque.get("nombre") or f"Municipalidad {cut}")
            instituciones_cubiertas.append(f"{nombre_mun} (billetera municipal · CUT {cut})")
            movimientos.append(
                {
                    "id_movimiento": f"mun-{cut}-{anio}",
                    "billetera": "municipal",
                    "monto": monto_mun,
                    "etapa": "devengo",
                    "territorio": cut,
                    "es_transferencia_interna": False,
                    "ejecutor": nombre_mun,
                    "ejercicio": anio,
                }
            )

    # 4. Transferencias internas documentadas con id_documento verificable (si el corte DIPRES las trae)
    if isinstance(datos_dipres, Mapping) and isinstance(datos_dipres.get("transferencias_conciliadas"), list):
        ids_existentes = {m["id_movimiento"] for m in movimientos}
        for t in datos_dipres["transferencias_conciliadas"]:
            if not isinstance(t, Mapping):
                continue
            em = str(t.get("id_movimiento_emisor") or "").strip()
            rec = str(t.get("id_movimiento_receptor") or "").strip()
            doc = str(t.get("id_documento") or "").strip()
            monto_t = _a_decimal_flexible(t.get("monto_conciliado"))
            if em in ids_existentes and doc and monto_t is not None and monto_t > _CERO:
                transferencias_conciliadas.append(
                    {
                        "id_conciliacion": str(t.get("id_conciliacion") or f"conc-{len(transferencias_conciliadas) + 1}"),
                        "id_documento": doc,
                        "id_movimiento_emisor": em,
                        "id_movimiento_receptor": rec if rec in ids_existentes else None,
                        "monto_conciliado": monto_t,
                    }
                )

    if not movimientos:
        return {
            "disponible": False,
            "etapa": "devengo",
            "instituciones_cubiertas": [],
            "instituciones_excluidas_con_motivo": instituciones_excluidas,
            "totales_brutos_por_billetera": {"sectorial": "0.000", "regional": "0.000", "municipal": "0.000"},
            "total_bruto_millones": None,
            "total_transferencias_eliminadas_millones": None,
            "consolidado_neto_millones": None,
            "conservacion_aritmetica_ok": True,
            "transferencias_eliminadas": [],
            "transferencias_pendientes_conciliacion": [],
            "total_pendiente_conciliacion_millones": "0.000",
            "advertencia_metodologica": "No existen movimientos presupuestarios disponibles en el año seleccionado para consolidar.",
        }

    resultado = conc_mod.consolidar_billeteras(movimientos, transferencias_conciliadas)

    transferencias_eliminadas_out = [
        {
            "id_conciliacion": t.id_conciliacion,
            "id_documento": t.id_documento,
            "billetera_emisor": t.billetera_emisor,
            "billetera_receptor": t.billetera_receptor,
            "monto_eliminado_millones": _fmt(t.monto_eliminado, 3),
        }
        for t in resultado.transferencias_aplicadas
    ]
    pendientes_out = [
        {
            "id_movimiento": r.id_movimiento,
            "billetera": r.billetera,
            "territorio": r.territorio,
            "monto_pendiente_millones": _fmt(r.monto_pendiente, 3),
            "motivo": r.motivo,
            "id_documento": r.id_documento,
        }
        for r in resultado.residuales_pendientes
    ]

    return {
        "disponible": True,
        "etapa": resultado.etapa,
        "instituciones_cubiertas": instituciones_cubiertas,
        "instituciones_excluidas_con_motivo": instituciones_excluidas,
        "totales_brutos_por_billetera": {
            k: _fmt(v, 3) for k, v in resultado.totales_brutos_por_billetera.items()
        },
        "total_bruto_millones": _fmt(resultado.total_bruto, 3),
        "total_transferencias_eliminadas_millones": _fmt(resultado.total_transferencias_eliminadas, 3),
        "consolidado_neto_millones": _fmt(resultado.consolidado_neto, 3),
        "conservacion_aritmetica_ok": bool(resultado.conservacion_aritmetica_ok),
        "transferencias_eliminadas": transferencias_eliminadas_out,
        "transferencias_pendientes_conciliacion": pendientes_out,
        "total_pendiente_conciliacion_millones": _fmt(resultado.total_residuales_pendientes, 3),
        "advertencia_metodologica": (
            f"Este total consolidado cubre exactamente {len(instituciones_cubiertas)} institución(es) con datos "
            f"territorializados en Aysén ({', '.join(instituciones_cubiertas[:4])}"
            + ("..." if len(instituciones_cubiertas) > 4 else "")
            + "). Las transferencias internas con respaldo documental se descuentan una sola vez y aquellas "
            "sin contraparte documental emparejada (por ejemplo Subtítulo 33 GORE o transferencias SUBDERE) "
            "quedan informadas explícitamente como pendientes de conciliación documental."
        ),
    }


@router.get("/presupuestos")
def aysen_presupuestos(
    anio: Annotated[int, Query(ge=2013, le=2030)] = 2025,
    comuna: str = "11201",
):
    comuna_sel = _resolver_comuna_aysen(comuna, obligatoria=True)
    assert comuna_sel is not None
    cut = comuna_sel["cut"]

    datos_dipres, origen_dipres = _obtener_datos_dipres_piloto(anio)
    datos_dipres_prev, _ = _obtener_datos_dipres_piloto(anio - 1) if anio > 2013 else (None, None)
    datos_mop, lista_mop = _cargar_proyectos_mop_normalizados()
    sinim_oficial = _leer_json_opcional(_ruta_sinim_oficial())
    sinim_importado = _leer_json_opcional(_ruta_sinim_importado())

    mes_corte = _normalizar_mes_corte(datos_dipres) if datos_dipres is not None else None
    es_cierre_anual = mes_corte == 12

    # 1. Billetera Regional: GORE Aysén
    gore_bloque = _extraer_bloque_gore(datos_dipres)

    # 2. Billetera Sectorial: Servicios Nacionales en Aysén (Piloto Vialidad MOP + Salud/SLEP Aysén)
    vialidad_dipres = _extraer_bloque_vialidad_dipres(datos_dipres)
    servicios_aysen, total_servicios_aysen = _extraer_servicios_identificables_aysen(datos_dipres)

    anio_corte_mop = _anio_corte_mop(datos_mop)
    vialidad_contratos: dict[str, Any] = {
        "disponible": False,
        "territorio": "Región de Aysén (contratos MOP DGOP)",
        "total_proyectos": 0,
        "presupuesto_anio_aysen_millones": None,
        "pagado_anio_aysen_millones": None,
        "arrastre_aysen_millones": None,
        "porcentaje_arrastre": None,
        "url_fuente": URL_MOP_DGOP,
    }
    if lista_mop:
        proys_v, _ = _filtrar_proyectos_mop(
            lista_mop,
            anio=anio,
            anio_corte_archivo=anio_corte_mop,
            institucion="vialidad",
        )
        if proys_v:
            res_v = _invocar_resumen_proyectos(
                proys_v,
                anio=anio,
                fecha_cambio_administracion=_fecha_cambio_administracion(anio, datos_mop),
            )
            url_mop = (
                (datos_mop.get("fuente_trazabilidad") or {}).get("url_fuente")
                if isinstance(datos_mop, Mapping) and isinstance(datos_mop.get("fuente_trazabilidad"), Mapping)
                else None
            ) or URL_MOP_DGOP
            vialidad_contratos = {
                "disponible": True,
                "territorio": "Región de Aysén (contratos MOP DGOP)",
                "total_proyectos": len(proys_v),
                "presupuesto_anio_aysen_millones": res_v["arrastre_presupuesto"]["presupuesto_inversion_anio_millones"],
                "pagado_anio_aysen_millones": res_v["pagos_contratos_anteriores"]["monto_pagado_total_millones"],
                "arrastre_aysen_millones": res_v["arrastre_presupuesto"]["monto_arrastre_comprometido_millones"],
                "porcentaje_arrastre": res_v["arrastre_presupuesto"]["porcentaje"],
                "url_fuente": url_mop,
            }

    servicios_nacionales_bloque = {
        "nombre": "Servicios Nacionales en Aysén (Piloto Dirección de Vialidad MOP y servicios regionales)",
        "billetera": "sectorial",
        "territorio": "Región de Aysén (contratos y servicios territorializados) + marco nacional DIPRES",
        "disponible": bool(vialidad_dipres["disponible"] or vialidad_contratos["disponible"] or servicios_aysen),
        "piloto_vialidad_mop": {
            "nombre": "Dirección de Vialidad — MOP",
            "dipres_nacional": vialidad_dipres,
            "contratos_territorializados_aysen": vialidad_contratos,
        },
        "servicios_identificables_aysen": servicios_aysen,
        "total_servicios_identificables_millones": _fmt(total_servicios_aysen, 3),
        "url_fuente": gore_bloque.get("url_fuente") or URL_DIPRES_CKAN,
    }

    # 3. Billetera Municipal: Municipalidad seleccionada (defecto 11201 Aysén)
    municipal_bloque = _construir_billetera_municipal(cut, anio, sinim_oficial, sinim_importado)

    # 4. Gobierno Central Nacional (Chile — Nivel Nacional)
    gc_nacional = _extraer_bloque_gobierno_central_nacional(datos_dipres)

    # 5. Consolidación anti-duplicación con pipelines.fiscal.conciliacion.consolidar_billeteras
    consolidacion = _ejecutar_consolidacion_aysen(
        anio=anio,
        gore_bloque=gore_bloque,
        servicios_aysen=servicios_aysen,
        municipal_bloque=municipal_bloque,
        datos_dipres=datos_dipres,
    )

    # 6. Comparación contra el mismo mes del año anterior si el año está en curso (mes_corte < 12)
    comparacion_mismo_mes: dict[str, Any]
    if mes_corte is not None and mes_corte < 12:
        if isinstance(gore_bloque.get("comparacion_mismo_mes_anterior"), Mapping) and gore_bloque["comparacion_mismo_mes_anterior"].get("disponible"):
            comp_src = gore_bloque["comparacion_mismo_mes_anterior"]
            comparacion_mismo_mes = {
                "aplica": True,
                "disponible": True,
                "mes_corte": mes_corte,
                "mes_corte_nombre": _MESES_NOMBRE.get(mes_corte),
                "anio_actual": anio,
                "anio_anterior": comp_src.get("anio_anterior") or (anio - 1),
                "etiqueta": comp_src.get("etiqueta"),
                "gore_aysen_actual_millones": gore_bloque.get("ejecutado_millones"),
                "gore_aysen_anterior_millones": comp_src.get("ejecutado_mismo_mes_anterior_millones"),
                "variacion_gore_pct": comp_src.get("variacion_nominal_pct"),
                "nota": comp_src.get("nota") or f"Comparación homogénea acumulada a {_MESES_NOMBRE.get(mes_corte)} ({anio} vs {anio - 1}).",
            }
        elif isinstance(datos_dipres, Mapping) and isinstance(datos_dipres.get("comparacion_mismo_mes"), Mapping):
            comp_src = datos_dipres["comparacion_mismo_mes"]
            comparacion_mismo_mes = {
                "aplica": True,
                "disponible": True,
                "mes_corte": mes_corte,
                "mes_corte_nombre": _MESES_NOMBRE.get(mes_corte),
                "anio_actual": anio,
                "anio_anterior": anio - 1,
                **dict(comp_src),
            }
        else:
            mes_prev = _normalizar_mes_corte(datos_dipres_prev) if datos_dipres_prev is not None else None
            if mes_prev == mes_corte and datos_dipres_prev is not None:
                gore_prev = _extraer_bloque_gore(datos_dipres_prev)
                actual_gore = _a_decimal(gore_bloque.get("ejecutado_millones"))
                prev_gore = _a_decimal(gore_prev.get("ejecutado_millones"))
                var_gore = (
                    _ratio_pct(actual_gore - prev_gore, prev_gore)
                    if (actual_gore is not None and prev_gore is not None and prev_gore > _CERO)
                    else None
                )
                comparacion_mismo_mes = {
                    "aplica": True,
                    "disponible": var_gore is not None,
                    "mes_corte": mes_corte,
                    "mes_corte_nombre": _MESES_NOMBRE.get(mes_corte),
                    "anio_actual": anio,
                    "anio_anterior": anio - 1,
                    "gore_aysen_actual_millones": _fmt(actual_gore, 3),
                    "gore_aysen_anterior_millones": _fmt(prev_gore, 3),
                    "variacion_gore_pct": _fmt(var_gore, 2),
                    "nota": f"Comparación homogénea acumulada a {_MESES_NOMBRE.get(mes_corte)} ({anio} vs {anio - 1}).",
                }
            else:
                comparacion_mismo_mes = {
                    "aplica": True,
                    "disponible": False,
                    "mes_corte": mes_corte,
                    "mes_corte_nombre": _MESES_NOMBRE.get(mes_corte),
                    "anio_actual": anio,
                    "anio_anterior": anio - 1,
                    "mes_corte_anterior_disponible": mes_prev,
                    "nota": (
                        f"El ejercicio {anio} está en curso (corte a {_MESES_NOMBRE.get(mes_corte)}, mes {mes_corte}), "
                        f"mientras el corte disponible de {anio - 1} corresponde al mes {mes_prev or 'desconocido'}. "
                        "No se comparan acumulados de distinto número de meses."
                    ),
                }
    else:
        comparacion_mismo_mes = {
            "aplica": False,
            "disponible": False,
            "mes_corte": mes_corte,
            "mes_corte_nombre": _MESES_NOMBRE.get(mes_corte) if mes_corte else None,
            "anio_actual": anio,
            "anio_anterior": anio - 1,
            "nota": (
                "Cierre anual completo (diciembre, 12 meses); no requiere ajuste por mes de corte en curso."
                if es_cierre_anual
                else "Sin mes de corte informado en el corte DIPRES."
            ),
        }

    return {
        "anio_seleccionado": anio,
        "anios_disponibles": list(ANIOS_DISPONIBLES),
        "mes_corte": mes_corte,
        "es_cierre_anual": es_cierre_anual,
        "comuna_seleccionada": comuna_sel,
        "comunas_aysen": _catalogo_comunas_aysen(sinim_oficial),
        "billeteras": {
            "gore_aysen": gore_bloque,
            "servicios_nacionales_aysen": servicios_nacionales_bloque,
            "municipal": municipal_bloque,
        },
        "gobierno_central_nacional": gc_nacional,
        "consolidacion": consolidacion,
        "comparacion_mismo_mes": comparacion_mismo_mes,
        "fuente_trazabilidad": {
            "dipres_origen": origen_dipres or "no_disponible",
            "sinim_oficial_disponible": sinim_oficial is not None,
            "sinim_importado_usuario_cargado": bool(
                isinstance(sinim_importado, Mapping) and sinim_importado.get("valido") is True
            ),
            "mop_disponible": bool(lista_mop),
            "enlaces_oficiales": {
                "dipres_ckan": URL_DIPRES_CKAN,
                "presupuesto_abierto": URL_DIPRES_PA,
                "sinim_ficha_comunal": municipal_bloque["url_ficha_oficial"],
                "mop_dgop": URL_MOP_DGOP,
            },
        },
    }


# ---------------------------------------------------------------------------
# ENDPOINT 4: GET /api/v1/aysen/proyectos
# ---------------------------------------------------------------------------


@router.get("/proyectos")
def aysen_proyectos(
    anio: Annotated[int, Query(ge=2013, le=2030)] = 2026,
    comuna: str = "",
    institucion: str = "",
    q: Annotated[str, Query(max_length=200)] = "",
):
    comuna_sel = _resolver_comuna_aysen(comuna, obligatoria=False)
    datos_mop, lista_mop = _cargar_proyectos_mop_normalizados()

    if datos_mop is None:
        vacio_resumen = calcular_resumen_proyectos([], anio=anio)
        return {
            "disponible": False,
            "motivo": (
                "El corte oficial de proyectos MOP en Aysén (data/published/proyectos-mop-aysen.json) "
                "aún no se ha publicado."
            ),
            "anio_seleccionado": anio,
            "filtros_aplicados": {
                "anio": anio,
                "comuna": comuna_sel,
                "institucion": institucion.strip() or None,
                "q": q.strip() or None,
            },
            "cobertura_anio": "Sin corte MOP DGOP disponible.",
            "pagos_contratos_anteriores": vacio_resumen["pagos_contratos_anteriores"],
            "arrastre_presupuesto": vacio_resumen["arrastre_presupuesto"],
            "total_proyectos_filtrados": 0,
            "total_documentados": 0,
            "total_informacion_insuficiente": 0,
            "proyectos_documentados": [],
            "proyectos_informacion_insuficiente": [],
            "instituciones_disponibles": [],
            "comunas_disponibles": [c["nombre"] for c in COMUNAS_AYSEN_LISTA],
            "fuente_trazabilidad": {
                "institucion": "Ministerio de Obras Públicas (MOP · DGOP)",
                "estado": "pendiente_publicacion",
                "archivo_esperado": "data/published/proyectos-mop-aysen.json",
                "url_fuente": URL_MOP_DGOP,
            },
        }

    # Catálogos globales del archivo para filtros del frontend
    instituciones_set = sorted(
        {
            str(p.get("institucion") or p.get("direccion") or p.get("servicio")).strip()
            for p in lista_mop
            if (p.get("institucion") or p.get("direccion") or p.get("servicio"))
        }
    )
    comunas_set = sorted(
        {c for p in lista_mop for c in _lista_comunas_proyecto(p)}
    )

    anio_corte_archivo = _anio_corte_mop(datos_mop)

    filtrados, cobertura_anio = _filtrar_proyectos_mop(
        lista_mop,
        anio=anio,
        anio_corte_archivo=anio_corte_archivo,
        comuna=comuna_sel["nombre"] if comuna_sel else "",
        institucion=institucion,
        q=q,
    )

    proyectos_documentados: list[dict[str, Any]] = []
    proyectos_insuficientes: list[dict[str, Any]] = []
    for proy in filtrados:
        if _es_proyecto_informacion_insuficiente(proy):
            copia = dict(proy)
            copia.setdefault(
                "motivo_insuficiencia",
                "Falta fecha verificable de contrato/adjudicación o monto presupuestario/pago del ejercicio.",
            )
            proyectos_insuficientes.append(copia)
        else:
            proyectos_documentados.append(proy)

    fecha_cambio = _fecha_cambio_administracion(anio, datos_mop)
    resumen = _invocar_resumen_proyectos(
        filtrados,
        anio=anio,
        fecha_cambio_administracion=fecha_cambio,
    )

    traza_archivo = (
        dict(datos_mop["fuente_trazabilidad"])
        if isinstance(datos_mop.get("fuente_trazabilidad"), Mapping)
        else {}
    )
    traza_archivo.setdefault("institucion", "Ministerio de Obras Públicas (MOP · DGOP)")
    traza_archivo.setdefault("url_fuente", URL_MOP_DGOP)
    traza_archivo["anio_corte_archivo"] = anio_corte_archivo
    traza_archivo["solo_lectura"] = True

    return {
        "disponible": True,
        "anio_seleccionado": anio,
        "anio_corte_archivo": anio_corte_archivo,
        "filtros_aplicados": {
            "anio": anio,
            "comuna": comuna_sel,
            "institucion": institucion.strip() or None,
            "q": q.strip() or None,
        },
        "cobertura_anio": cobertura_anio,
        "pagos_contratos_anteriores": resumen["pagos_contratos_anteriores"],
        "arrastre_presupuesto": resumen["arrastre_presupuesto"],
        "total_proyectos_filtrados": len(filtrados),
        "total_documentados": len(proyectos_documentados),
        "total_informacion_insuficiente": len(proyectos_insuficientes),
        "proyectos_documentados": proyectos_documentados,
        "proyectos_informacion_insuficiente": proyectos_insuficientes,
        "instituciones_disponibles": instituciones_set,
        "comunas_disponibles": comunas_set or [c["nombre"] for c in COMUNAS_AYSEN_LISTA],
        "fuente_trazabilidad": traza_archivo,
    }
