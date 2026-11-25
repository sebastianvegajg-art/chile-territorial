"""Extractor oficial y reproducible de Mercado Laboral (INE ENE vía BCCh SI3)
y Tejido Empresarial / Empleo Dependiente y Masa Salarial Formal (SII 2013–2025).

Fuentes oficiales verificadas:
1. Instituto Nacional de Estadísticas (INE · Encuesta Nacional de Empleo ENE) vía
   API REST oficial del Banco Central de Chile (BDE SI3):
   - Ocupados regionales y nacional (`F049.OCU.PMT.INE9.*.M`, miles de personas, 2010–2026)
   - Tasa de desocupación regional y nacional (`F049.DES.TAS.INE9.*.M`, %, 2010–2026)
   - Ocupación nacional en Administración Pública y Defensa (`F049.OCU.PMT.INE4.39B.M`)
2. Servicio de Impuestos Internos (SII · Estadísticas de Empresas 2005–2025):
   - `https://www.sii.cl/sobre_el_sii/empresas/PUB_REG.xlsb` (16 regiones, totales sin supresión)
   - `https://www.sii.cl/sobre_el_sii/empresas/PUB_REG_RUBR.xlsb` (16 regiones × rubro económico,
     incluyendo Rubro `O - Administración pública y defensa`)
   - `https://www.sii.cl/sobre_el_sii/empresas/PUB_COMU.xlsb` (comunas de Aysén: empresas, ventas UF,
     trabajadores dependientes ponderados, masa salarial en UF y honorarios)

Garantías metodológicas (`AGENTS.md`):
- Aritmética exacta con `Decimal(34)` (sin `float` en ratios, promedios ni productividad).
- Manejo estricto del secreto estadístico SII (`"*"` -> `None`, nunca `0`).
- El denominador regional SII proviene siempre del total oficial sin supresión de `PUB_REG.xlsb`.
- Separación explícita entre empleo residente (INE ENE, encuesta de hogares) y empleo formal
  dependiente por domicilio tributario / casa matriz del empleador (SII).
- Archivo inmutable de respuestas crudas + `manifiesto.json` SHA-256 y reproducción
  `--reproducir --insumos <dir>` bit-a-bit sin red.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable, Mapping, Sequence
import unicodedata
from urllib.request import Request, urlopen

_RAIZ_REPO = Path(__file__).resolve().parents[2]
if str(_RAIZ_REPO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_REPO))

ESQUEMA_LABORAL = "mercado-laboral-sii-ine-v1"
USER_AGENT = "ChileTerritorial/1.0 (+https://www.sii.cl)"
ANIO_MIN = 2013
ANIO_MAX = 2026

CONTEXTO_DECIMAL = Context(prec=34)
CERO = Decimal("0")
CIEN = Decimal("100")
MIL = Decimal("1000")
MILLON = Decimal("1000000")

_RAW_ROOT_DEFECTO = _RAIZ_REPO / "data" / "raw"
_SALIDA_DEFECTO = _RAIZ_REPO / "data" / "published" / "mercado-laboral-sii-ine.json"
_PIB_API_DEFECTO = _RAIZ_REPO / "data" / "published" / "pib-bde-api.json"
_PIB_PUB_DEFECTO = _RAIZ_REPO / "data" / "published" / "pib-bde-publico.json"

URL_SII_BASE = "https://www.sii.cl/sobre_el_sii/empresas"
URL_SII_PORTAL = "https://www.sii.cl/sobre_el_sii/estadisticas_de_empresas.html"
URL_BCCH_SIETE = "https://si3.bcentral.cl/Siete"

ARCHIVOS_SII: dict[str, str] = {
    "pub_reg": f"{URL_SII_BASE}/PUB_REG.xlsb",
    "pub_reg_rubr": f"{URL_SII_BASE}/PUB_REG_RUBR.xlsb",
    "pub_comu": f"{URL_SII_BASE}/PUB_COMU.xlsb",
}

# Mapeo oficial de códigos territoriales Chile Territorial -> sufijo INE9 en BCCh SI3
SERIES_ENE_POR_TERRITORIO: dict[str, tuple[str, str, str]] = {
    "CL": ("Chile", "F049.OCU.PMT.INE9.01.M", "F049.DES.TAS.INE9.10.M"),
    "15": ("Arica y Parinacota", "F049.OCU.PMT.INE9.25.M", "F049.DES.TAS.INE9.25.M"),
    "01": ("Tarapacá", "F049.OCU.PMT.INE9.11.M", "F049.DES.TAS.INE9.11.M"),
    "02": ("Antofagasta", "F049.OCU.PMT.INE9.12.M", "F049.DES.TAS.INE9.12.M"),
    "03": ("Atacama", "F049.OCU.PMT.INE9.13.M", "F049.DES.TAS.INE9.13.M"),
    "04": ("Coquimbo", "F049.OCU.PMT.INE9.14.M", "F049.DES.TAS.INE9.14.M"),
    "05": ("Valparaíso", "F049.OCU.PMT.INE9.15.M", "F049.DES.TAS.INE9.15.M"),
    "13": ("Metropolitana de Santiago", "F049.OCU.PMT.INE9.23.M", "F049.DES.TAS.INE9.23.M"),
    "06": ("Libertador General Bernardo O'Higgins", "F049.OCU.PMT.INE9.16.M", "F049.DES.TAS.INE9.16.M"),
    "07": ("Maule", "F049.OCU.PMT.INE9.17.M", "F049.DES.TAS.INE9.17.M"),
    "16": ("Ñuble", "F049.OCU.PMT.INE9.26.M", "F049.DES.TAS.INE9.26.M"),
    "08": ("Biobío", "F049.OCU.PMT.INE9.18N.M", "F049.DES.TAS.INE9.18N.M"),
    "09": ("La Araucanía", "F049.OCU.PMT.INE9.19.M", "F049.DES.TAS.INE9.19.M"),
    "14": ("Los Ríos", "F049.OCU.PMT.INE9.24.M", "F049.DES.TAS.INE9.24.M"),
    "10": ("Los Lagos", "F049.OCU.PMT.INE9.20.M", "F049.DES.TAS.INE9.20.M"),
    "11": ("Aysén del General Carlos Ibáñez del Campo", "F049.OCU.PMT.INE9.21.M", "F049.DES.TAS.INE9.21.M"),
    "12": ("Magallanes y de la Antártica Chilena", "F049.OCU.PMT.INE9.22.M", "F049.DES.TAS.INE9.22.M"),
}

SERIE_ENE_ADM_PUB_CL = "F049.OCU.PMT.INE4.39B.M"

_COMUNAS_AYSEN_POR_NORM: dict[str, tuple[str, str]] = {
    "coyhaique": ("11101", "Coyhaique"),
    "coihaique": ("11101", "Coyhaique"),
    "lago verde": ("11102", "Lago Verde"),
    "aysen": ("11201", "Aysén"),
    "aisen": ("11201", "Aysén"),
    "cisnes": ("11202", "Cisnes"),
    "guaitecas": ("11203", "Guaitecas"),
    "cochrane": ("11301", "Cochrane"),
    "ohiggins": ("11302", "O'Higgins"),
    "o'higgins": ("11302", "O'Higgins"),
    "tortel": ("11303", "Tortel"),
    "chile chico": ("11401", "Chile Chico"),
    "rio ibanez": ("11402", "Río Ibáñez"),
}


def _norm(texto: object) -> str:
    if texto is None:
        return ""
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s).strip().lower()


def _a_decimal(valor: object) -> Decimal | None:
    if valor is None or isinstance(valor, bool):
        return None
    txt = str(valor).strip()
    if not txt or txt in {"*", "-", "--", "NaN", "nan", "None", "null", "s/i"}:
        return None
    try:
        d = Decimal(txt)
    except InvalidOperation:
        return None
    return d if d.is_finite() else None


def _fmt(valor: Decimal | None, decimales: int = 2) -> str | None:
    if valor is None or not valor.is_finite():
        return None
    with localcontext(CONTEXTO_DECIMAL):
        q = Decimal("1").scaleb(-decimales)
        r = valor.quantize(q, rounding=ROUND_HALF_UP)
        txt = format(r, "f")
        return txt.lstrip("-") if txt in {"-0", "-0.0", "-0.00", "-0.000"} else txt


def _ratio_pct(num: Decimal | None, den: Decimal | None) -> Decimal | None:
    if num is None or den is None or den <= CERO:
        return None
    with localcontext(CONTEXTO_DECIMAL):
        return ((CIEN * num) / den).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _mapear_region_sii(nombre_region: str) -> str | None:
    n = _norm(nombre_region)
    if not n or "sin informacion" in n:
        return None
    if "arica" in n:
        return "15"
    if "tarapaca" in n:
        return "01"
    if "antofagasta" in n:
        return "02"
    if "atacama" in n:
        return "03"
    if "coquimbo" in n:
        return "04"
    if "valparaiso" in n:
        return "05"
    if "metropolitana" in n:
        return "13"
    if "ohiggins" in n or "o'higgins" in n or "libertador" in n:
        return "06"
    if "maule" in n:
        return "07"
    if "nuble" in n:
        return "16"
    if "biobio" in n or "bio bio" in n or "bio-bio" in n:
        return "08"
    if "araucania" in n:
        return "09"
    if "los rios" in n:
        return "14"
    if "los lagos" in n:
        return "10"
    if "aysen" in n or "aisen" in n:
        return "11"
    if "magallanes" in n:
        return "12"
    return None


def _leer_filas_xlsb(raw_bytes: bytes) -> tuple[list[str], list[list[Any]]]:
    """Lee la hoja 'Datos' de un archivo oficial SII `.xlsb` retornando (headers, rows)."""
    from pyxlsb import open_workbook  # type: ignore

    headers: list[str] = []
    filas: list[list[Any]] = []
    with open_workbook(io.BytesIO(raw_bytes)) as wb:
        hoja = "Datos" if "Datos" in wb.sheets else wb.sheets[0]
        with wb.get_sheet(hoja) as sh:
            for row in sh.rows():
                vals = [c.v for c in row]
                if not headers:
                    if vals and vals[0] is not None and "comercial" in _norm(vals[0]):
                        headers = [str(v or "").strip() for v in vals]
                    continue
                if not vals or vals[0] is None:
                    continue
                filas.append(vals)
    return headers, filas


def parsear_sii_xlsb(
    pub_reg_bytes: bytes,
    pub_reg_rubr_bytes: bytes,
    pub_comu_bytes: bytes,
    *,
    anio_min: int = ANIO_MIN,
) -> dict[str, Any]:
    """Parsea los tres archivos oficiales SII con `Decimal(34)` y manejo estricto de `*`."""
    # 1. PUB_REG: totales regionales sin supresión por rubro
    _, filas_reg = _leer_filas_xlsb(pub_reg_bytes)
    sii_regiones: dict[str, dict[str, dict[str, Any]]] = {}
    anios_sii: set[int] = set()

    for vals in filas_reg:
        yr_dec = _a_decimal(vals[0])
        if yr_dec is None:
            continue
        yr = int(yr_dec)
        if yr < anio_min:
            continue
        cod = _mapear_region_sii(str(vals[1] or ""))
        if cod is None:
            continue
        anios_sii.add(yr)
        emp = _a_decimal(vals[2] if len(vals) > 2 else None)
        ventas = _a_decimal(vals[3] if len(vals) > 3 else None)
        trab_inf = _a_decimal(vals[4] if len(vals) > 4 else None)
        renta = _a_decimal(vals[5] if len(vals) > 5 else None)
        trab_pond = _a_decimal(vals[6] if len(vals) > 6 else None)
        hon_trab = _a_decimal(vals[13] if len(vals) > 13 else None)
        hon_uf = _a_decimal(vals[14] if len(vals) > 14 else None)

        sii_regiones.setdefault(str(yr), {})[cod] = {
            "territorio": cod,
            "nombre": SERIES_ENE_POR_TERRITORIO[cod][0],
            "empresas": int(emp) if emp is not None else None,
            "ventas_uf": _fmt(ventas, 2),
            "trabajadores_dependientes_informados": int(trab_inf) if trab_inf is not None else None,
            "trabajadores_ponderados": _fmt(trab_pond, 2),
            "renta_neta_uf": _fmt(renta, 2),
            "honorarios_trabajadores": int(hon_trab) if hon_trab is not None else None,
            "honorarios_uf": _fmt(hon_uf, 2),
            # Campos que se completan desde PUB_REG_RUBR (Rubro O y P)
            "rubro_o_adm_publica": None,
            "rubro_p_ensenanza": None,
            "participacion_rubro_o_trabajadores_pct": None,
            "participacion_rubro_o_masa_salarial_pct": None,
            "top_rubros_aysen": [] if cod == "11" else None,
        }

    # 2. PUB_REG_RUBR: Rubro O (Administración pública y defensa) + Rubro P + detalle Aysén
    _, filas_rubr = _leer_filas_xlsb(pub_reg_rubr_bytes)
    rubros_aysen_por_anio: dict[str, list[dict[str, Any]]] = {}

    for vals in filas_rubr:
        yr_dec = _a_decimal(vals[0])
        if yr_dec is None:
            continue
        yr = int(yr_dec)
        if yr < anio_min:
            continue
        cod = _mapear_region_sii(str(vals[1] or ""))
        if cod is None or str(yr) not in sii_regiones or cod not in sii_regiones[str(yr)]:
            continue
        rubro = str(vals[2] or "").strip()
        rubro_norm = _norm(rubro)
        emp = _a_decimal(vals[3] if len(vals) > 3 else None)
        ventas = _a_decimal(vals[4] if len(vals) > 4 else None)
        trab_inf = _a_decimal(vals[5] if len(vals) > 5 else None)
        renta = _a_decimal(vals[6] if len(vals) > 6 else None)
        trab_pond = _a_decimal(vals[7] if len(vals) > 7 else None)

        reg_obj = sii_regiones[str(yr)][cod]
        tot_tp = _a_decimal(reg_obj["trabajadores_ponderados"])
        tot_rn = _a_decimal(reg_obj["renta_neta_uf"])

        bloque_rubro = {
            "rubro": rubro,
            "empresas": int(emp) if emp is not None else None,
            "ventas_uf": _fmt(ventas, 2),
            "trabajadores_dependientes_informados": int(trab_inf) if trab_inf is not None else None,
            "trabajadores_ponderados": _fmt(trab_pond, 2),
            "renta_neta_uf": _fmt(renta, 2),
            "secreto_estadistico_renta": renta is None and (trab_pond is not None and trab_pond > CERO),
            "participacion_trabajadores_pct": _fmt(_ratio_pct(trab_pond, tot_tp), 2),
            "participacion_masa_salarial_pct": _fmt(_ratio_pct(renta, tot_rn), 2),
        }

        if rubro_norm.startswith("o -") or "administracion publica y defensa" in rubro_norm:
            reg_obj["rubro_o_adm_publica"] = bloque_rubro
            reg_obj["participacion_rubro_o_trabajadores_pct"] = bloque_rubro["participacion_trabajadores_pct"]
            reg_obj["participacion_rubro_o_masa_salarial_pct"] = bloque_rubro["participacion_masa_salarial_pct"]
        elif rubro_norm.startswith("p -") or rubro_norm == "p - ensenanza":
            reg_obj["rubro_p_ensenanza"] = bloque_rubro

        if cod == "11":
            rubros_aysen_por_anio.setdefault(str(yr), []).append(bloque_rubro)

    for yr_str, lista_r in rubros_aysen_por_anio.items():
        lista_r.sort(
            key=lambda x: -(_a_decimal(x["trabajadores_ponderados"]) or CERO)
        )
        if yr_str in sii_regiones and "11" in sii_regiones[yr_str]:
            sii_regiones[yr_str]["11"]["top_rubros_aysen"] = lista_r[:10]

    # 3. PUB_COMU: Las 10 comunas de la Región de Aysén
    _, filas_comu = _leer_filas_xlsb(pub_comu_bytes)
    comunas_aysen: dict[str, dict[str, dict[str, Any]]] = {}

    for vals in filas_comu:
        yr_dec = _a_decimal(vals[0])
        if yr_dec is None:
            continue
        yr = int(yr_dec)
        if yr < anio_min:
            continue
        reg_cod = _mapear_region_sii(str(vals[3] or "") if len(vals) > 3 else "")
        if reg_cod != "11":
            continue
        com_norm = _norm(vals[1] if len(vals) > 1 else "")
        match = _COMUNAS_AYSEN_POR_NORM.get(com_norm)
        if not match:
            continue
        cut, nombre_com = match
        emp = _a_decimal(vals[4] if len(vals) > 4 else None)
        ventas = _a_decimal(vals[5] if len(vals) > 5 else None)
        trab_inf = _a_decimal(vals[6] if len(vals) > 6 else None)
        renta = _a_decimal(vals[7] if len(vals) > 7 else None)
        trab_pond = _a_decimal(vals[8] if len(vals) > 8 else None)
        hon_trab = _a_decimal(vals[15] if len(vals) > 15 else None)
        hon_uf = _a_decimal(vals[16] if len(vals) > 16 else None)

        comunas_aysen.setdefault(str(yr), {})[cut] = {
            "cut": cut,
            "comuna": nombre_com,
            "anio": yr,
            "empresas": int(emp) if emp is not None else None,
            "ventas_uf": _fmt(ventas, 2),
            "trabajadores_dependientes_informados": int(trab_inf) if trab_inf is not None else None,
            "trabajadores_ponderados": _fmt(trab_pond, 2),
            "renta_neta_uf": _fmt(renta, 2),
            "honorarios_trabajadores": int(hon_trab) if hon_trab is not None else None,
            "honorarios_uf": _fmt(hon_uf, 2),
            "secreto_estadistico_ventas": ventas is None and (emp is not None and emp > CERO),
        }

    return {
        "anios": sorted(anios_sii),
        "ultimo_anio": max(anios_sii) if anios_sii else None,
        "regiones_por_anio": sii_regiones,
        "comunas_aysen_por_anio": comunas_aysen,
    }


def _promediar_mensual_a_anual(
    observaciones: Sequence[Mapping[str, Any]],
    *,
    anio_min: int = ANIO_MIN,
) -> dict[int, tuple[Decimal, int]]:
    """Promedia observaciones mensuales (fecha DD-MM-YYYY o YYYY-MM-DD) por año con `Decimal(34)`."""
    por_anio: dict[int, list[Decimal]] = {}
    for obs in observaciones:
        fecha = str(obs.get("fecha") or obs.get("indexDateString") or "").strip()
        val = _a_decimal(obs.get("valor") if "valor" in obs else obs.get("value"))
        if val is None or not fecha:
            continue
        m_iso = re.match(r"^(\d{4})-\d{2}-\d{2}", fecha)
        m_cl = re.match(r"^\d{2}-\d{2}-(\d{4})$", fecha)
        if m_iso:
            yr = int(m_iso.group(1))
        elif m_cl:
            yr = int(m_cl.group(1))
        else:
            continue
        if yr < anio_min:
            continue
        por_anio.setdefault(yr, []).append(val)

    salida: dict[int, tuple[Decimal, int]] = {}
    with localcontext(CONTEXTO_DECIMAL):
        for yr, vals in sorted(por_anio.items()):
            if vals:
                salida[yr] = (sum(vals, CERO) / Decimal(len(vals)), len(vals))
    return salida


def construir_lote_laboral(
    *,
    series_bcch: Mapping[str, Sequence[Mapping[str, Any]]],
    sii_reg_bytes: bytes,
    sii_reg_rubr_bytes: bytes,
    sii_comu_bytes: bytes,
    lote_pib: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Combina INE ENE (BCCh SI3), PIB real (productividad laboral) y SII en el corte publicado."""
    sii = parsear_sii_xlsb(sii_reg_bytes, sii_reg_rubr_bytes, sii_comu_bytes)

    # Índice PIB real por (territorio, anio) en millones CLP encadenados
    pib_real_idx: dict[tuple[str, int], Decimal] = {}
    if isinstance(lote_pib, Mapping) and isinstance(lote_pib.get("observaciones"), list):
        for fila in lote_pib["observaciones"]:
            if (
                isinstance(fila, Mapping)
                and fila.get("metrica") == "nivel"
                and fila.get("valoracion") == "real"
                and type(fila.get("anio")) is int
            ):
                val = _a_decimal(fila.get("valor"))
                if val is not None:
                    pib_real_idx[(str(fila["territorio"]), int(fila["anio"]))] = val

    # Promedios anuales INE ENE por territorio
    ene_por_anio: dict[str, dict[str, dict[str, Any]]] = {}
    anios_ene: set[int] = set()

    adm_pub_cl_anual = _promediar_mensual_a_anual(series_bcch.get(SERIE_ENE_ADM_PUB_CL) or [])

    for cod, (nombre, sid_ocu, sid_des) in SERIES_ENE_POR_TERRITORIO.items():
        ocu_anual = _promediar_mensual_a_anual(series_bcch.get(sid_ocu) or [])
        des_anual = _promediar_mensual_a_anual(series_bcch.get(sid_des) or [])
        for yr in sorted(set(ocu_anual.keys()) | set(des_anual.keys())):
            anios_ene.add(yr)
            ocu_miles, meses_ocu = ocu_anual.get(yr, (None, 0))
            des_pct, meses_des = des_anual.get(yr, (None, 0))
            meses = max(meses_ocu, meses_des)

            # Productividad laboral real = (PIB real millones CLP * 1.000.000) / (ocupados_miles * 1.000)
            prod_clp: Decimal | None = None
            pib_real_mm = pib_real_idx.get((cod, yr))
            if pib_real_mm is not None and ocu_miles is not None and ocu_miles > CERO and meses == 12:
                with localcontext(CONTEXTO_DECIMAL):
                    prod_clp = (pib_real_mm * MIL) / ocu_miles

            adm_cl_miles = adm_pub_cl_anual[yr][0] if (cod == "CL" and yr in adm_pub_cl_anual) else None
            adm_cl_pct = _ratio_pct(adm_cl_miles, ocu_miles) if (adm_cl_miles is not None and ocu_miles is not None) else None

            ene_por_anio.setdefault(str(yr), {})[cod] = {
                "territorio": cod,
                "nombre": nombre,
                "anio": yr,
                "meses_promediados": meses,
                "es_anio_en_curso": meses < 12,
                "ocupados_miles": _fmt(ocu_miles, 3),
                "ocupados_personas": _fmt(ocu_miles * MIL, 0) if ocu_miles is not None else None,
                "tasa_desocupacion_pct": _fmt(des_pct, 2),
                "pib_real_millones": _fmt(pib_real_mm, 2) if pib_real_mm is not None else None,
                "productividad_laboral_real_clp": _fmt(prod_clp, 0),
                "serie_ocupados": sid_ocu,
                "serie_desocupacion": sid_des,
                **(
                    {
                        "ocupados_adm_publica_miles": _fmt(adm_cl_miles, 3),
                        "participacion_adm_publica_ene_nacional_pct": _fmt(adm_cl_pct, 2),
                        "serie_adm_publica": SERIE_ENE_ADM_PUB_CL,
                    }
                    if cod == "CL" and adm_cl_miles is not None
                    else {}
                ),
            }

    # Calcular ranking de productividad laboral real por año (solo 16 regiones)
    for yr_str, mapa_terr in ene_por_anio.items():
        regiones_prod = [
            (cod, _a_decimal(obj["productividad_laboral_real_clp"]))
            for cod, obj in mapa_terr.items()
            if cod != "CL" and obj["productividad_laboral_real_clp"] is not None
        ]
        regiones_prod.sort(key=lambda x: -(x[1] or CERO))
        for idx, (cod, _) in enumerate(regiones_prod, start=1):
            mapa_terr[cod]["ranking_productividad_regional"] = idx

    ultimo_anio_ene_cerrado = max(
        (yr for yr in anios_ene if any(v["meses_promediados"] == 12 for v in ene_por_anio[str(yr)].values())),
        default=max(anios_ene) if anios_ene else None,
    )
    ultimo_anio_sii = sii["ultimo_anio"]

    return {
        "esquema": ESQUEMA_LABORAL,
        "anios_ene": sorted(anios_ene),
        "ultimo_anio_ene_cerrado": ultimo_anio_ene_cerrado,
        "anios_sii": sii["anios"],
        "ultimo_anio_sii": ultimo_anio_sii,
        "ine_ene_por_anio": ene_por_anio,
        "sii_regiones_por_anio": sii["regiones_por_anio"],
        "sii_comunas_aysen_por_anio": sii["comunas_aysen_por_anio"],
        "nota_metodologica_separacion": (
            "Las estadísticas de empleo INE ENE (encuesta de hogares por residencia del trabajador) y "
            "los registros tributarios SII (trabajadores dependientes informados y masa salarial en UF por "
            "domicilio tributario / casa matriz del empleador) miden universos distintos y no deben "
            "sumarse ni compararse como fracciones de un mismo denominador. En SII, las celdas con secreto "
            "estadístico ('*') se preservan como no disponibles (null)."
        ),
    }


def _http_get_bytes(url: str, timeout: int = 45) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def extraer_mercado_laboral_live(
    *,
    raw_root: Path = _RAW_ROOT_DEFECTO,
    salida_path: Path = _SALIDA_DEFECTO,
    env_path: Path | None = None,
    http_get_bytes: Callable[[str, int], bytes] = _http_get_bytes,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Descarga en vivo 35 series INE ENE vía BCCh SI3 + 3 archivos oficiales SII XLSB."""
    from pipelines.economia import bcch_live

    env_file = env_path or (_RAIZ_REPO / ".env")
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dir_insumos = raw_root / f"laboral-sii-ine-{ts}"
    dir_insumos.mkdir(parents=True, exist_ok=True)

    # 1. Descargar las 35 series INE ENE desde BCCh SI3
    series_ids = [SERIE_ENE_ADM_PUB_CL]
    for _, sid_ocu, sid_des in SERIES_ENE_POR_TERRITORIO.values():
        series_ids.extend([sid_ocu, sid_des])

    series_bcch: dict[str, list[dict[str, Any]]] = {}
    for sid in series_ids:
        resp = bcch_live.obtener_serie_live(
            sid,
            firstdate=f"{ANIO_MIN}-01-01",
            env_path=env_file if env_file.is_file() else None,
        )
        serie_obj = resp.get("serie") if isinstance(resp.get("serie"), Mapping) else resp
        series_bcch[sid] = list(serie_obj.get("observaciones") or [])

    # 2. Descargar los 3 archivos oficiales SII XLSB
    sii_bytes: dict[str, bytes] = {}
    for clave, url in ARCHIVOS_SII.items():
        sii_bytes[clave] = http_get_bytes(url, 60)

    # 3. Archivar insumos inmutables + SHA-256
    archivos_manifest: list[dict[str, Any]] = []
    bcch_bytes = json.dumps(series_bcch, ensure_ascii=False, indent=2).encode("utf-8")
    (dir_insumos / "bcch-ine-ene-series.json").write_bytes(bcch_bytes)
    archivos_manifest.append(
        {"archivo": "bcch-ine-ene-series.json", "bytes": len(bcch_bytes), "sha256": sha256(bcch_bytes).hexdigest()}
    )
    for clave, raw in sii_bytes.items():
        nombre = f"sii-{clave}.xlsb"
        (dir_insumos / nombre).write_bytes(raw)
        archivos_manifest.append(
            {"archivo": nombre, "bytes": len(raw), "sha256": sha256(raw).hexdigest(), "url": ARCHIVOS_SII[clave]}
        )

    extraido_en = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifiesto = {
        "esquema": ESQUEMA_LABORAL,
        "extraido_en": extraido_en,
        "total_series_bcch": len(series_ids),
        "archivos": archivos_manifest,
    }
    (dir_insumos / "manifiesto.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ruta_pib = _PIB_API_DEFECTO if _PIB_API_DEFECTO.is_file() else _PIB_PUB_DEFECTO
    lote_pib = json.loads(ruta_pib.read_text(encoding="utf-8")) if ruta_pib.is_file() else None

    publicado = construir_lote_laboral(
        series_bcch=series_bcch,
        sii_reg_bytes=sii_bytes["pub_reg"],
        sii_reg_rubr_bytes=sii_bytes["pub_reg_rubr"],
        sii_comu_bytes=sii_bytes["pub_comu"],
        lote_pib=lote_pib,
    )
    publicado["fuente_trazabilidad"] = {
        "instituciones": [
            "Instituto Nacional de Estadísticas (INE · Encuesta Nacional de Empleo ENE) vía BCCh SI3",
            "Servicio de Impuestos Internos (SII · Estadísticas de Empresas 2005–2025)",
        ],
        "enlaces_oficiales": {
            "sii_estadisticas_empresas": URL_SII_PORTAL,
            "bcch_siete": URL_BCCH_SIETE,
        },
        "modo": "en_vivo",
        "extraido_en": extraido_en,
        "directorio_insumos": str(dir_insumos),
        "archivos_sha256": {a["archivo"]: a["sha256"] for a in archivos_manifest},
    }

    salida_path.parent.mkdir(parents=True, exist_ok=True)
    salida_path.write_text(json.dumps(publicado, ensure_ascii=False, indent=2), encoding="utf-8")
    return publicado


def reproducir_mercado_laboral(
    dir_insumos: Path,
    *,
    salida_path: Path | None = _SALIDA_DEFECTO,
    lote_pib_path: Path | None = None,
) -> dict[str, Any]:
    """Reproduce bit-a-bit el corte laboral INE+SII sin red validando SHA-256."""
    manifiesto = json.loads((dir_insumos / "manifiesto.json").read_text(encoding="utf-8"))
    for entry in manifiesto["archivos"]:
        ruta = dir_insumos / entry["archivo"]
        if sha256(ruta.read_bytes()).hexdigest() != entry["sha256"]:
            raise RuntimeError(f"Integridad SHA-256 alterada en {ruta.name}.")

    series_bcch = json.loads((dir_insumos / "bcch-ine-ene-series.json").read_text(encoding="utf-8"))
    sii_reg = (dir_insumos / "sii-pub_reg.xlsb").read_bytes()
    sii_rubr = (dir_insumos / "sii-pub_reg_rubr.xlsb").read_bytes()
    sii_comu = (dir_insumos / "sii-pub_comu.xlsb").read_bytes()

    ruta_pib = lote_pib_path or (_PIB_API_DEFECTO if _PIB_API_DEFECTO.is_file() else _PIB_PUB_DEFECTO)
    lote_pib = json.loads(ruta_pib.read_text(encoding="utf-8")) if ruta_pib.is_file() else None

    publicado = construir_lote_laboral(
        series_bcch=series_bcch,
        sii_reg_bytes=sii_reg,
        sii_reg_rubr_bytes=sii_rubr,
        sii_comu_bytes=sii_comu,
        lote_pib=lote_pib,
    )
    publicado["fuente_trazabilidad"] = {
        "instituciones": [
            "Instituto Nacional de Estadísticas (INE · Encuesta Nacional de Empleo ENE) vía BCCh SI3",
            "Servicio de Impuestos Internos (SII · Estadísticas de Empresas 2005–2025)",
        ],
        "enlaces_oficiales": {
            "sii_estadisticas_empresas": URL_SII_PORTAL,
            "bcch_siete": URL_BCCH_SIETE,
        },
        "modo": "reproducido_sin_red",
        "integridad_sha256_verificada": True,
        "extraido_en": manifiesto["extraido_en"],
        "directorio_insumos": str(dir_insumos),
        "archivos_sha256": {a["archivo"]: a["sha256"] for a in manifiesto["archivos"]},
    }
    if salida_path is not None:
        salida_path.parent.mkdir(parents=True, exist_ok=True)
        salida_path.write_text(json.dumps(publicado, ensure_ascii=False, indent=2), encoding="utf-8")
    return publicado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extractor oficial INE ENE (BCCh SI3) + SII Empresas (2013–2026).")
    parser.add_argument("--reproducir", action="store_true")
    parser.add_argument("--insumos", type=Path)
    parser.add_argument("--salida", type=Path, default=_SALIDA_DEFECTO)
    args = parser.parse_args(argv)

    if args.reproducir:
        if not args.insumos:
            parser.error("--insumos es obligatorio con --reproducir.")
        pub = reproducir_mercado_laboral(args.insumos, salida_path=args.salida)
    else:
        pub = extraer_mercado_laboral_live(salida_path=args.salida)

    yr_ene = str(pub["ultimo_anio_ene_cerrado"])
    yr_sii = str(pub["ultimo_anio_sii"])
    ene_ay = pub["ine_ene_por_anio"][yr_ene]["11"]
    sii_ay = pub["sii_regiones_por_anio"][yr_sii]["11"]
    n_com = len(pub["sii_comunas_aysen_por_anio"].get(yr_sii, {}))
    print(
        f"LABORAL OK | INE ENE {yr_ene} Aysén: ocu={ene_ay['ocupados_miles']}k desoc={ene_ay['tasa_desocupacion_pct']}% "
        f"prod=${ene_ay['productividad_laboral_real_clp']} CLP/ocu (#{ene_ay.get('ranking_productividad_regional')}) | "
        f"SII {yr_sii} Aysén: emp={sii_ay['empresas']} trab_p={sii_ay['trabajadores_ponderados']} "
        f"rubro_O_trab={sii_ay['participacion_rubro_o_trabajadores_pct']}% rubro_O_masa={sii_ay['participacion_rubro_o_masa_salarial_pct']}% | "
        f"comunas_aysen={n_com}/10"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
