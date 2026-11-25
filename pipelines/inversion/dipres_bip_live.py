"""Extractor oficial y reproducible de Iniciativas de Inversión BIP (DIPRES Subt. 31, Aysén 2021–2026).

Fuente oficial verificada (datos.gob.cl · Dirección de Presupuestos — DIPRES):
    Paquetes CKAN ``ejecucion-presupuestaria-de-iniciativas-de-inversion-acumulado-<anio>``
    (cortes Total en moneda Pesos / Miles de Pesos CLP, años 2021 a 2026).

Garantías metodológicas:
- Filtra estrictamente ``Región Destino == 11`` (Región de Aysén del General Carlos
  Ibáñez del Campo) y moneda CLP (``Miles de Pesos`` -> ``millones CLP`` dividiendo por
  1.000 con ``Decimal(34)``, sin ``float``).
- Agrupa por ``(anio, codigo_bip, partida, capitulo)`` para evitar duplicación de filas
  de un mismo proyecto en un mismo servicio y año.
- Construye la trayectoria plurianual oficial de cada Código BIP entre 2021 y 2026:
  * Si un Código BIP ya registró monto identificado o devengado en algún año anterior
    (2021..anio-1), se clasifica como ``"arrastre"`` con respaldo verificable.
  * Si aparece por primera vez en ``anio >= 2022``, se clasifica como ``"nuevo"``.
  * En ``anio == 2021`` (primer año de la serie) no se infiere arrastre (``"sin_dato"``).
- Respeta estrictamente la separación de etapas contables: DIPRES Subt. 31 informa
  ``Monto Identificado`` (marco/compromiso presupuestario) y ``Monto Devengado``
  (ejecución presupuestaria), NO fecha de firma de contrato ni pagos de caja. Por ello
  ``fecha_contratacion`` queda en ``None`` para no contaminar la Pregunta 1 (contratos
  firmados antes de la administración vigente).
- Nunca inventa comunas: si ``Nombre Comuna Destino`` dice ``Sin Registro``, las comunas
  quedan vacías y se informa explícitamente alcance regional / sin comuna registrada.
- Archiva los CSV oficiales crudos + ``manifiesto.json`` con SHA-256 en
  ``data/raw/dipres-bip-<timestamp>/`` y soporta ``--reproducir --insumos <dir>`` sin red.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from hashlib import sha256
import io
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence
import unicodedata
from urllib.parse import urlencode
from urllib.request import Request, urlopen

URL_CKAN_BASE = "https://datos.gob.cl/api/3/action"
URL_DATASET_BASE = "https://datos.gob.cl/dataset"
URL_BIP_CONSULTA = "https://bip.ministeriodesarrollosocial.gob.cl/bip2-consulta/app/parent-flow?opcion=1"
USER_AGENT = "ChileTerritorial/1.0 (+https://datos.gob.cl)"
ESQUEMA_DIPRES_BIP = "dipres-bip-aysen-v1"

ANIOS_DEFECTO: tuple[int, ...] = (2021, 2022, 2023, 2024, 2025, 2026)

CONTEXTO_DECIMAL = Context(prec=34)
CERO = Decimal("0")
CIEN = Decimal("100")
MIL = Decimal("1000")

_RAIZ_REPO = Path(__file__).resolve().parents[2]
_RAW_ROOT_DEFECTO = _RAIZ_REPO / "data" / "raw"
_SALIDA_DEFECTO = _RAIZ_REPO / "data" / "published" / "proyectos-bip-aysen.json"

_MESES_ORDEN: dict[str, int] = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

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

_COMUNAS_CANONICAS: dict[str, str] = {
    "coyhaique": "Coyhaique",
    "coihaique": "Coyhaique",
    "lago verde": "Lago Verde",
    "aysen": "Aysén",
    "aisen": "Aysén",
    "puerto aysen": "Aysén",
    "cisnes": "Cisnes",
    "guaitecas": "Guaitecas",
    "cochrane": "Cochrane",
    "ohiggins": "O'Higgins",
    "o'higgins": "O'Higgins",
    "o higgins": "O'Higgins",
    "tortel": "Tortel",
    "chile chico": "Chile Chico",
    "rio ibanez": "Río Ibáñez",
}

_INSTITUCIONES_CANONICAS: dict[tuple[str, str], tuple[str, str]] = {
    ("05", "71"): ("Gobierno Regional de Aysén (FNDR)", "regional"),
    ("31", "01"): ("Gobierno Regional de Aysén (FNDR)", "regional"),
    ("12", "02"): ("MOP — Dirección General de Obras Públicas (BIP)", "sectorial"),
    ("18", "31"): ("SERVIU Región de Aysén (MINVU)", "sectorial"),
    ("16", "40"): ("Servicio de Salud Aysén", "sectorial"),
    ("09", "34"): ("SLEP Aysén (Educación Pública)", "sectorial"),
    ("03", "03"): ("Poder Judicial (CAPJ)", "sectorial"),
    ("10", "01"): ("Ministerio de Justicia y Derechos Humanos", "sectorial"),
    ("19", "01"): ("Ministerio de Transportes y Telecomunicaciones", "sectorial"),
    ("13", "01"): ("Ministerio de Agricultura", "sectorial"),
    ("26", "02"): ("Instituto Nacional de Deportes (IND)", "sectorial"),
    ("29", "03"): ("Servicio Nacional del Patrimonio Cultural", "sectorial"),
}


def _norm(texto: object) -> str:
    if texto is None:
        return ""
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s).strip().lower()


def _fmt_dec(valor: Decimal, decimales: int = 3) -> str:
    with localcontext(CONTEXTO_DECIMAL):
        q = Decimal("1").scaleb(-decimales)
        r = valor.quantize(q, rounding=ROUND_HALF_UP)
        txt = format(r, "f")
        return "0.000" if txt in {"-0.000", "-0"} else txt


def _fmt_cl(valor: Decimal, decimales: int = 1) -> str:
    with localcontext(CONTEXTO_DECIMAL):
        q = Decimal("1").scaleb(-decimales)
        r = valor.quantize(q, rounding=ROUND_HALF_UP)
        neg = r < CERO
        cuerpo = format(abs(r), "f")
        if "." in cuerpo:
            ent, frac = cuerpo.split(".", 1)
        else:
            ent, frac = cuerpo, ""
        ent_fmt = f"{int(ent):,}".replace(",", ".")
        pref = "-" if neg else ""
        return f"{pref}{ent_fmt},{frac}" if decimales > 0 and frac else f"{pref}{ent_fmt}"


def parsear_monto_miles_clp(valor: object) -> Decimal | None:
    if valor is None:
        return None
    txt = str(valor).strip().replace("\xa0", "").replace(" ", "").replace("$", "")
    if not txt or txt.lower() in {"-", "--", "n/a", "null", "none", "sin registro"}:
        return None
    if "." in txt and "," in txt:
        if txt.rfind(",") > txt.rfind("."):
            txt = txt.replace(".", "").replace(",", ".")
        else:
            txt = txt.replace(",", "")
    elif "." in txt:
        partes = txt.split(".")
        if len(partes) > 2 or (len(partes) == 2 and len(partes[1]) == 3):
            txt = "".join(partes)
    elif "," in txt:
        partes = txt.split(",")
        if len(partes) == 2 and len(partes[1]) <= 2:
            txt = txt.replace(",", ".")
        else:
            txt = "".join(partes)
    try:
        d = Decimal(txt)
    except InvalidOperation:
        return None
    return d if d.is_finite() else None


def _valor_col(fila: Mapping[str, Any], *candidatas: str) -> str:
    for c in candidatas:
        if c in fila and fila[c] is not None:
            return str(fila[c]).strip()
    mapa = {_norm(k): v for k, v in fila.items()}
    for c in candidatas:
        nc = _norm(c)
        if nc in mapa and mapa[nc] is not None:
            return str(mapa[nc]).strip()
    return ""


def _normalizar_comuna(raw: str) -> str | None:
    n = _norm(raw)
    if not n or "sin registro" in n or n in {"0", "00", "regional", "intercomunal", "todas"}:
        return None
    n = re.sub(r"^(comuna de|puerto)\s+", "", n).strip()
    return _COMUNAS_CANONICAS.get(n)


def _normalizar_institucion(partida: str, capitulo: str, nombre_capitulo: str, nombre_partida: str) -> tuple[str, str]:
    p = partida.zfill(2) if partida.isdigit() else partida
    c = capitulo.zfill(2) if capitulo.isdigit() else capitulo
    if (p, c) in _INSTITUCIONES_CANONICAS:
        return _INSTITUCIONES_CANONICAS[(p, c)]
    norm_cap = _norm(nombre_capitulo)
    if "gobierno regional" in norm_cap and ("aysen" in norm_cap or "aisen" in norm_cap):
        return "Gobierno Regional de Aysén (FNDR)", "regional"
    if "serviu" in norm_cap:
        return "SERVIU Región de Aysén (MINVU)", "sectorial"
    if "salud aysen" in norm_cap:
        return "Servicio de Salud Aysén", "sectorial"
    if "educacion aysen" in norm_cap:
        return "SLEP Aysén (Educación Pública)", "sectorial"
    if "obras publicas" in norm_cap:
        return "MOP — Dirección General de Obras Públicas (BIP)", "sectorial"
    etiqueta = nombre_capitulo.strip() or nombre_partida.strip() or f"Partida {p} Cap. {c}"
    return etiqueta.title() if etiqueta.isupper() else etiqueta, "sectorial"


def _detectar_mes_recurso(nombre_recurso: str) -> int:
    n = _norm(nombre_recurso)
    for mes_txt, mes_num in _MESES_ORDEN.items():
        if mes_txt in n:
            return mes_num
    return 0


def _http_get_bytes(url: str, timeout: int = 45) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _http_get_json(url: str, timeout: int = 30) -> dict[str, Any]:
    raw = _http_get_bytes(url, timeout=timeout)
    return json.loads(raw.decode("utf-8", errors="replace"))


def descubrir_recursos_dipres_bip(
    anios: Sequence[int] = ANIOS_DEFECTO,
    http_get_json: Callable[[str, int], dict[str, Any]] = _http_get_json,
) -> dict[int, dict[str, Any]]:
    """Descubre el recurso CSV de mayor mes en pesos CLP por cada año disponible en DIPRES CKAN."""
    url = f"{URL_CKAN_BASE}/package_search?" + urlencode(
        {
            "q": "iniciativas de inversion",
            "fq": "organization:direccion_de_presupuestos",
            "rows": 40,
        }
    )
    payload = http_get_json(url, 30)
    resultados = (payload.get("result") or {}).get("results") or []

    candidatos_por_anio: dict[int, list[tuple[tuple[int, int, str], dict[str, Any]]]] = {}
    for paq in resultados:
        if not isinstance(paq, dict):
            continue
        nombre = str(paq.get("name") or "")
        titulo = str(paq.get("title") or "")
        norm_txt = _norm(f"{nombre} {titulo}")
        if "iniciativas de inversion" not in norm_txt:
            continue
        if "fet" in norm_txt or "incendio" in norm_txt or "covid" in norm_txt or "ley regular" in norm_txt:
            continue
        m_anio = re.search(r"\b(20\d{2})\b", norm_txt)
        if not m_anio:
            continue
        anio = int(m_anio.group(1))
        if anio not in anios:
            continue

        pesos = []
        for rec in paq.get("resources") or []:
            if not isinstance(rec, dict):
                continue
            rname = str(rec.get("name") or "")
            rnorm = _norm(rname)
            rurl = str(rec.get("url") or "").strip()
            if not rurl or "diccionario" in rnorm or "dolar" in rnorm or "usd" in rnorm:
                continue
            if "peso" not in rnorm and "clp" not in rnorm:
                continue
            mes = _detectar_mes_recurso(rname)
            pesos.append((mes, rec))
        if not pesos:
            continue
        pesos.sort(key=lambda x: x[0], reverse=True)
        mejor_mes, mejor_rec = pesos[0]
        es_total = int("total" in norm_txt)
        mod = str(paq.get("metadata_modified") or "")
        candidatos_por_anio.setdefault(anio, []).append(
            (
                (es_total, mejor_mes, mod),
                {
                    "anio": anio,
                    "mes_corte": mejor_mes or 12,
                    "package_name": nombre,
                    "package_title": titulo,
                    "url_dataset": f"{URL_DATASET_BASE}/{nombre}",
                    "resource_id": mejor_rec.get("id"),
                    "resource_name": mejor_rec.get("name"),
                    "resource_url": mejor_rec.get("url"),
                    "actualizado_en": mod,
                },
            )
        )

    seleccionados: dict[int, dict[str, Any]] = {}
    for anio, lista in sorted(candidatos_por_anio.items()):
        lista.sort(key=lambda x: x[0], reverse=True)
        seleccionados[anio] = lista[0][1]
    return seleccionados


def _decodificar_csv(raw: bytes) -> list[dict[str, str]]:
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
    reader = csv.DictReader(io.StringIO(texto), delimiter=delim)
    return [{str(k).strip(): (v or "").strip() for k, v in row.items() if k is not None} for row in reader]


def _administracion_por_anio(anio: int) -> str:
    if anio >= 2026:
        return "Administración 2026–2030"
    if anio >= 2022:
        return "Administración 2022–2026"
    if anio >= 2018:
        return "Administración 2018–2022"
    return "Administración 2014–2018"


def parsear_iniciativas_dipres_aysen(
    csv_por_anio: Mapping[int, bytes],
    meta_por_anio: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    """Normaliza los CSV oficiales DIPRES Subt. 31 para Aysén (Región 11) con trayectoria plurianual."""
    # Paso 1: agregar por (anio, codigo_bip, partida, capitulo)
    agregados: dict[tuple[int, str, str, str], dict[str, Any]] = {}
    historial_bip: dict[str, dict[int, dict[str, Decimal]]] = {}

    for anio in sorted(csv_por_anio.keys()):
        filas = _decodificar_csv(csv_por_anio[anio])
        meta = meta_por_anio.get(anio) or {}
        mes_corte = int(meta.get("mes_corte") or 12)

        for fila in filas:
            reg = _valor_col(fila, "Región Destino", "Region Destino", "Código Región", "Codigo Region")
            nom_reg = _norm(_valor_col(fila, "Nombre Región Destino", "Nombre Region Destino"))
            if reg != "11" and "aysen" not in nom_reg and "aisen" not in nom_reg:
                continue
            moneda = _norm(_valor_col(fila, "Moneda"))
            if moneda and any(tok in moneda for tok in ("dolar", "usd", "us$")):
                continue

            codigo_bip = _valor_col(fila, "Código BIP", "Codigo BIP", "BIP")
            nombre_proy = _valor_col(fila, "Nombre Proyecto", "Nombre Iniciativa")
            if not codigo_bip and not nombre_proy:
                continue
            bip_clave = codigo_bip or f"SINBIP-{sha256(nombre_proy.encode('utf-8')).hexdigest()[:8]}"

            partida = _valor_col(fila, "Partida").zfill(2)
            capitulo = _valor_col(fila, "Capítulo", "Capitulo").zfill(2)
            nom_part = _valor_col(fila, "Nombre Partida")
            nom_cap = _valor_col(fila, "Nombre Capítulo", "Nombre Capitulo")
            nom_prog = _valor_col(fila, "Nombre Programa")
            comuna_raw = _valor_col(fila, "Nombre Comuna Destino", "Comuna Destino")
            comuna_norm = _normalizar_comuna(comuna_raw)

            ident_miles = parsear_monto_miles_clp(
                _valor_col(
                    fila,
                    "Suma de Monto Identificado Ley de Pptos.",
                    "Monto Identificado Ley de Pptos.",
                    "Monto Identificado",
                )
            )
            dev_miles = parsear_monto_miles_clp(
                _valor_col(
                    fila,
                    "Suma de Monto Devengado Ley de Pptos.",
                    "Monto Devengado Ley de Pptos.",
                    "Monto Devengado",
                )
            )

            clave = (anio, bip_clave, partida, capitulo)
            inst_nombre, billetera = _normalizar_institucion(partida, capitulo, nom_cap, nom_part)
            if clave not in agregados:
                agregados[clave] = {
                    "anio": anio,
                    "mes_corte": mes_corte,
                    "codigo_bip": codigo_bip or None,
                    "bip_clave": bip_clave,
                    "nombre_proyecto": nombre_proy or f"Iniciativa BIP {codigo_bip}",
                    "partida": partida,
                    "capitulo": capitulo,
                    "nombre_partida": nom_part,
                    "nombre_capitulo": nom_cap,
                    "nombre_programa": nom_prog,
                    "institucion": inst_nombre,
                    "billetera": billetera,
                    "comunas": set(),
                    "identificado_miles": CERO,
                    "devengado_miles": CERO,
                    "tiene_ident": False,
                    "tiene_dev": False,
                    "url_dataset": meta.get("url_dataset") or URL_DATASET_BASE,
                    "package_name": meta.get("package_name"),
                    "resource_name": meta.get("resource_name"),
                }
            rec = agregados[clave]
            if comuna_norm:
                rec["comunas"].add(comuna_norm)
            if ident_miles is not None:
                rec["identificado_miles"] += ident_miles
                rec["tiene_ident"] = True
            if dev_miles is not None:
                rec["devengado_miles"] += dev_miles
                rec["tiene_dev"] = True

            # Acumular historial global por Código BIP (independiente de cambio de capítulo)
            if codigo_bip:
                h_anio = historial_bip.setdefault(codigo_bip, {}).setdefault(
                    anio, {"identificado_miles": CERO, "devengado_miles": CERO}
                )
                if ident_miles is not None:
                    h_anio["identificado_miles"] += ident_miles
                if dev_miles is not None:
                    h_anio["devengado_miles"] += dev_miles

    anios_disponibles = sorted(csv_por_anio.keys())
    primer_anio_serie = anios_disponibles[0] if anios_disponibles else 2021

    # Paso 2: emitir tarjetas normalizadas compatibles con el contrato de /api/v1/aysen/proyectos
    por_anio: dict[str, list[dict[str, Any]]] = {str(a): [] for a in anios_disponibles}
    indice_bip_global: dict[str, dict[str, Any]] = {}

    with localcontext(CONTEXTO_DECIMAL):
        for codigo_bip, anios_map in historial_bip.items():
            anios_ord = sorted(anios_map.keys())
            total_dev_hist = sum((v["devengado_miles"] for v in anios_map.values()), CERO) / MIL
            indice_bip_global[codigo_bip] = {
                "primer_anio_observado": anios_ord[0],
                "ultimo_anio_observado": anios_ord[-1],
                "anios_activos": anios_ord,
                "devengado_acumulado_2021_2026_millones": _fmt_dec(total_dev_hist, 3),
                "por_anio": {
                    str(yr): {
                        "identificado_millones": _fmt_dec(vals["identificado_miles"] / MIL, 3),
                        "devengado_millones": _fmt_dec(vals["devengado_miles"] / MIL, 3),
                    }
                    for yr, vals in sorted(anios_map.items())
                },
            }

        for (anio, bip_clave, partida, capitulo), rec in sorted(
            agregados.items(),
            key=lambda kv: (kv[0][0], -kv[1]["identificado_miles"], kv[0][1]),
        ):
            ident_mm = (rec["identificado_miles"] / MIL) if rec["tiene_ident"] else None
            dev_mm = (rec["devengado_miles"] / MIL) if rec["tiene_dev"] else None
            codigo_bip = rec["codigo_bip"]
            comunas = sorted(rec["comunas"])
            mes_corte = rec["mes_corte"]
            mes_nombre = _MESES_NOMBRE.get(mes_corte, str(mes_corte))

            # Determinar arrastre plurianual documentado desde historial oficial DIPRES
            anios_previos: list[int] = []
            dev_prev_miles = CERO
            if codigo_bip and codigo_bip in historial_bip:
                for yr_prev, vals_prev in sorted(historial_bip[codigo_bip].items()):
                    if yr_prev < anio and (
                        vals_prev["identificado_miles"] > CERO or vals_prev["devengado_miles"] > CERO
                    ):
                        anios_previos.append(yr_prev)
                        dev_prev_miles += vals_prev["devengado_miles"]

            dev_prev_mm = dev_prev_miles / MIL
            dev_acum_mm = (dev_prev_miles + (rec["devengado_miles"] if rec["tiene_dev"] else CERO)) / MIL

            motivos_insuf: list[str] = []
            if ident_mm is None or ident_mm <= CERO:
                if dev_mm is None or dev_mm <= CERO:
                    motivos_insuf.append("Sin monto identificado ni devengado positivo en el ejercicio.")

            if anio == primer_anio_serie:
                nuevo_o_arrastre = "sin_dato"
                motivos_insuf.append(
                    f"Primer año disponible de la serie DIPRES Subt. 31 ({primer_anio_serie}); "
                    "no se infiere arrastre sin corte oficial del ejercicio previo."
                )
            elif not codigo_bip:
                nuevo_o_arrastre = "sin_dato"
                motivos_insuf.append("Sin Código BIP informado para verificar continuidad plurianual.")
            elif anios_previos:
                nuevo_o_arrastre = "arrastre"
            else:
                nuevo_o_arrastre = "nuevo"

            calidad = "insuficiente" if motivos_insuf else "documentado"
            primer_anio_bip = anios_previos[0] if anios_previos else anio
            admin_primer_anio = _administracion_por_anio(primer_anio_bip)
            admin_actual = _administracion_por_anio(anio)

            comuna_txt = ", ".join(comunas) if comunas else "Región de Aysén (alcance regional / sin comuna registrada)"
            ident_cl = _fmt_cl(ident_mm, 1) if ident_mm is not None else "sin dato"
            dev_cl = _fmt_cl(dev_mm, 1) if dev_mm is not None else "sin dato"
            cond_arr = (
                f"es proyecto de arrastre (registrado en DIPRES desde {primer_anio_bip})"
                if nuevo_o_arrastre == "arrastre"
                else (
                    f"aparece por primera vez en DIPRES Subt. 31 en {anio}"
                    if nuevo_o_arrastre == "nuevo"
                    else "no permite determinar arrastre en este corte"
                )
            )
            frase_radial = (
                f"Iniciativa BIP {codigo_bip or 'sin código'} de {rec['institucion']} en {comuna_txt}: "
                f"{cond_arr}; en {anio} (corte a {mes_nombre}) registra ${ident_cl} millones identificados "
                f"y ${dev_cl} millones devengados según DIPRES Subtítulo 31."
            )

            linea_tiempo = [
                {
                    "hito": "aprobacion_financiamiento",
                    "titulo": "Aprobación / Registro BIP en Ley de Presupuestos",
                    "fecha": f"{primer_anio_bip}-01-01",
                    "institucion_responsable": f"MDSF (BIP {codigo_bip}) · {rec['institucion']}" if codigo_bip else rec["institucion"],
                    "administracion_vigente": admin_primer_anio,
                    "documento_respaldo": f"DIPRES Subt. 31 · Primer registro en serie {primer_anio_bip}" + (f" (BIP {codigo_bip})" if codigo_bip else ""),
                    "url_respaldo": URL_BIP_CONSULTA,
                    "estado": "verificado",
                },
                {
                    "hito": "contratacion",
                    "titulo": "Contratación",
                    "fecha": None,
                    "institucion_responsable": rec["institucion"],
                    "administracion_vigente": None,
                    "documento_respaldo": "Sin dato de fecha de contrato en DIPRES Subt. 31 (requiere cruce con Mercado Público / unidad técnica)",
                    "url_respaldo": rec["url_dataset"],
                    "estado": "sin_dato",
                },
                {
                    "hito": "pagos",
                    "titulo": f"Devengo presupuestario {anio} (a {mes_nombre})",
                    "fecha": f"{anio}-{mes_corte:02d}-01",
                    "institucion_responsable": rec["institucion"],
                    "administracion_vigente": admin_actual,
                    "documento_respaldo": f"{rec['resource_name'] or 'DIPRES Iniciativas de Inversión'} · Devengado ${dev_cl} MM (Identificado ${ident_cl} MM)",
                    "url_respaldo": rec["url_dataset"],
                    "estado": "verificado" if (dev_mm is not None and dev_mm > CERO) else "identificado_sin_devengo",
                },
                {
                    "hito": "entrada_funcionamiento",
                    "titulo": "Entrada en funcionamiento",
                    "fecha": None,
                    "institucion_responsable": rec["institucion"],
                    "administracion_vigente": None,
                    "documento_respaldo": "Sin dato de puesta en marcha en el archivo presupuestario DIPRES Subt. 31",
                    "url_respaldo": URL_BIP_CONSULTA,
                    "estado": "sin_dato",
                },
            ]

            item = {
                "id_contrato": f"BIP-{anio}-{partida}{capitulo}-{bip_clave}",
                "origen_fuente": "dipres_subt31_bip",
                "billetera": rec["billetera"],
                "codigo_bip": codigo_bip,
                "nombre_proyecto": rec["nombre_proyecto"],
                "nombre_contrato": rec["nombre_proyecto"],
                "institucion": rec["institucion"],
                "partida": partida,
                "capitulo": capitulo,
                "comunas": comunas,
                "anio_ejercicio": anio,
                "mes_corte": mes_corte,
                "etapa_contable": "identificado_y_devengado_subt31",
                "nuevo_o_arrastre": nuevo_o_arrastre,
                "calidad_informacion": calidad,
                "motivos_insuficiencia": motivos_insuf,
                # Montos en millones CLP (etapas estrictamente separadas)
                "costo_total_contrato_millones": _fmt_dec(dev_acum_mm, 3) if dev_acum_mm > CERO else (_fmt_dec(ident_mm, 3) if ident_mm is not None else None),
                "etiqueta_costo_total": "Devengado acumulado DIPRES (2021–año)" if dev_acum_mm > CERO else "Monto identificado del año (DIPRES)",
                "compromiso_anio_millones": _fmt_dec(ident_mm, 3) if ident_mm is not None else None,
                "pagado_anio_millones": _fmt_dec(dev_mm, 3) if dev_mm is not None else None,
                "pagado_anios_anteriores_millones": _fmt_dec(dev_prev_mm, 3) if dev_prev_mm > CERO else "0.000",
                "saldo_pendiente_millones": (
                    _fmt_dec(ident_mm - dev_mm, 3)
                    if (ident_mm is not None and dev_mm is not None and ident_mm >= dev_mm)
                    else None
                ),
                # Sin inventar fecha contractual (protege Pregunta 1)
                "fecha_contratacion": None,
                "administracion_contratacion": None,
                "firmado_antes_administracion_actual": None,
                "primer_anio_bip_observado": primer_anio_bip,
                "anios_previos_bip": anios_previos,
                "frase_radial": frase_radial,
                "linea_tiempo": linea_tiempo,
                "enlaces_oficiales": {
                    "dipres_iniciativas_ckan": rec["url_dataset"],
                    "bip_mdsf_consulta": URL_BIP_CONSULTA,
                },
            }
            por_anio[str(anio)].append(item)

    resumen_anios = {}
    for anio_str, lista in por_anio.items():
        with localcontext(CONTEXTO_DECIMAL):
            tot_id = sum((Decimal(p["compromiso_anio_millones"]) for p in lista if p["compromiso_anio_millones"]), CERO)
            tot_dev = sum((Decimal(p["pagado_anio_millones"]) for p in lista if p["pagado_anio_millones"]), CERO)
        resumen_anios[anio_str] = {
            "total_iniciativas": len(lista),
            "documentadas": sum(1 for p in lista if p["calidad_informacion"] == "documentado"),
            "arrastre": sum(1 for p in lista if p["nuevo_o_arrastre"] == "arrastre"),
            "nuevas": sum(1 for p in lista if p["nuevo_o_arrastre"] == "nuevo"),
            "insuficientes": sum(1 for p in lista if p["calidad_informacion"] == "insuficiente"),
            "identificado_total_millones": _fmt_dec(tot_id, 3),
            "devengado_total_millones": _fmt_dec(tot_dev, 3),
            "mes_corte": (meta_por_anio.get(int(anio_str)) or {}).get("mes_corte", 12),
        }

    return {
        "esquema": ESQUEMA_DIPRES_BIP,
        "region_codigo": "11",
        "region_nombre": "Aysén del General Carlos Ibáñez del Campo",
        "anios": anios_disponibles,
        "ultimo_anio": max(anios_disponibles) if anios_disponibles else None,
        "resumen_por_anio": resumen_anios,
        "por_anio": por_anio,
        "indice_bip_historico": indice_bip_global,
    }


def extraer_dipres_bip_live(
    *,
    anios: Sequence[int] = ANIOS_DEFECTO,
    raw_root: Path = _RAW_ROOT_DEFECTO,
    salida_path: Path = _SALIDA_DEFECTO,
    http_get_json: Callable[[str, int], dict[str, Any]] = _http_get_json,
    http_get_bytes: Callable[[str, int], bytes] = _http_get_bytes,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Descarga en vivo los CSV oficiales de DIPRES Subt. 31 (2021–2026), archiva con SHA-256 y publica."""
    recursos = descubrir_recursos_dipres_bip(anios=anios, http_get_json=http_get_json)
    if not recursos:
        raise RuntimeError("No se encontraron recursos DIPRES de Iniciativas de Inversión en datos.gob.cl.")

    ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dir_insumos = raw_root / f"dipres-bip-{ts}"
    dir_insumos.mkdir(parents=True, exist_ok=True)

    csv_por_anio: dict[int, bytes] = {}
    archivos_manifest: list[dict[str, Any]] = []
    for anio, meta in sorted(recursos.items()):
        raw = http_get_bytes(meta["resource_url"], 60)
        nombre_arch = f"dipres-iniciativas-{anio}.csv"
        (dir_insumos / nombre_arch).write_bytes(raw)
        csv_por_anio[anio] = raw
        archivos_manifest.append(
            {
                "anio": anio,
                "archivo": nombre_arch,
                "bytes": len(raw),
                "sha256": sha256(raw).hexdigest(),
                "meta": meta,
            }
        )

    extraido_en = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifiesto = {
        "esquema": ESQUEMA_DIPRES_BIP,
        "extraido_en": extraido_en,
        "anios": sorted(csv_por_anio.keys()),
        "archivos": archivos_manifest,
    }
    (dir_insumos / "manifiesto.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    publicado = parsear_iniciativas_dipres_aysen(csv_por_anio, recursos)
    publicado["fuente_trazabilidad"] = {
        "institucion": "Dirección de Presupuestos (DIPRES) · Iniciativas de Inversión Subtítulo 31 (BIP)",
        "url_oficial": "https://datos.gob.cl/organization/direccion_de_presupuestos",
        "url_bip_consulta": URL_BIP_CONSULTA,
        "modo": "en_vivo",
        "extraido_en": extraido_en,
        "directorio_insumos": str(dir_insumos),
        "archivos_sha256": {a["archivo"]: a["sha256"] for a in archivos_manifest},
    }

    salida_path.parent.mkdir(parents=True, exist_ok=True)
    salida_path.write_text(json.dumps(publicado, ensure_ascii=False, indent=2), encoding="utf-8")
    return publicado


def reproducir_dipres_bip(
    dir_insumos: Path,
    *,
    salida_path: Path | None = _SALIDA_DEFECTO,
) -> dict[str, Any]:
    """Reproduce bit-a-bit el corte DIPRES BIP sin red validando SHA-256."""
    manifiesto = json.loads((dir_insumos / "manifiesto.json").read_text(encoding="utf-8"))
    csv_por_anio: dict[int, bytes] = {}
    meta_por_anio: dict[int, dict[str, Any]] = {}

    for entry in manifiesto["archivos"]:
        ruta = dir_insumos / entry["archivo"]
        raw = ruta.read_bytes()
        if sha256(raw).hexdigest() != entry["sha256"]:
            raise RuntimeError(f"Integridad SHA-256 alterada en {ruta.name}.")
        anio = int(entry["anio"])
        csv_por_anio[anio] = raw
        meta_por_anio[anio] = entry["meta"]

    publicado = parsear_iniciativas_dipres_aysen(csv_por_anio, meta_por_anio)
    publicado["fuente_trazabilidad"] = {
        "institucion": "Dirección de Presupuestos (DIPRES) · Iniciativas de Inversión Subtítulo 31 (BIP)",
        "url_oficial": "https://datos.gob.cl/organization/direccion_de_presupuestos",
        "url_bip_consulta": URL_BIP_CONSULTA,
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
    parser = argparse.ArgumentParser(description="Extractor oficial DIPRES Iniciativas BIP Aysén (2021–2026).")
    parser.add_argument("--reproducir", action="store_true")
    parser.add_argument("--insumos", type=Path)
    parser.add_argument("--salida", type=Path, default=_SALIDA_DEFECTO)
    args = parser.parse_args(argv)

    if args.reproducir:
        if not args.insumos:
            parser.error("--insumos es obligatorio con --reproducir.")
        pub = reproducir_dipres_bip(args.insumos, salida_path=args.salida)
    else:
        pub = extraer_dipres_bip_live(salida_path=args.salida)

    for yr, r in sorted(pub["resumen_por_anio"].items()):
        print(
            f"DIPRES BIP {yr} (mes={r['mes_corte']}): total={r['total_iniciativas']} "
            f"arr={r['arrastre']} nuev={r['nuevas']} ins={r['insuficientes']} | "
            f"Ident=${r['identificado_total_millones']} MM | Dev=${r['devengado_total_millones']} MM"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
