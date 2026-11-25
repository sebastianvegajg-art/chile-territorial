"""Extractor oficial en vivo y reproducible de fichas comunales SINIM para Aysén.

Fuente oficial verificada:
    ``https://datos.sinim.gov.cl/impresion_ficha_comunal.php?municipio={cut}``

Reglas metodológicas:
- Parsea las fichas HTML con ``BeautifulSoup`` y aritmética exacta ``Decimal(34)``
  (sin ``float`` en montos ni porcentajes).
- Unidad de origen BEP SINIM: ``M$`` (miles de pesos) -> divide exactamente por
  ``1000`` para expresar en ``millones CLP``.
- Preserva separación estricta de etapas contables: la ficha BEP solo informa
  gasto total devengado e ingresos percibidos, por lo que
  ``presupuesto_inicial_millones = None`` y ``presupuesto_vigente_millones = None``
  (nunca se inventan cifras).
- Archiva los HTML originales junto con ``manifiesto.json`` (SHA-256) en
  ``data/raw/sinim-fichas-<timestamp>/``, publica
  ``data/published/sinim-aysen-oficial.json`` y permite reproducción exacta sin
  red mediante ``--reproducir --insumos <dir>``.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable, Mapping, Sequence
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

try:
    from pipelines.fiscal.sinim_importer import COMUNAS_AYSEN
except ImportError:  # pragma: no cover - ejecución directa dentro de pipelines/fiscal
    from sinim_importer import COMUNAS_AYSEN

URL_FICHA_PLANTILLA = "https://datos.sinim.gov.cl/impresion_ficha_comunal.php?municipio={cut}"
CUT_PILOTO_AYSEN = "11201"
ESQUEMA_SINIM_OFICIAL = "sinim-fichas-aysen-v1"

PRECISION_DECIMAL = 34
CONTEXTO_DECIMAL = Context(prec=PRECISION_DECIMAL)
CERO = Decimal("0")
CIEN = Decimal("100")
MIL = Decimal("1000")

TIMEOUT_SINIM_SEGUNDOS = 25
USER_AGENT = "ChileTerritorial/1.0 (+https://datos.sinim.gov.cl)"

_RAIZ_REPO = Path(__file__).resolve().parents[2]
_RAW_ROOT_DEFECTO = _RAIZ_REPO / "data" / "raw"
_SALIDA_PUBLICADA_DEFECTO = _RAIZ_REPO / "data" / "published" / "sinim-aysen-oficial.json"

BASE_CALCULO_GASTO_CORRIENTE = (
    "Subt. 21 (Personal) + Subt. 22 (Bienes y Servicios) dividido por Gasto Total "
    "Devengado BEP SINIM (la ficha resumida no desglosa Subt. 24 ni Subt. 31 por separado)."
)
NOTA_COSTO_ADMINISTRACION = (
    "La ficha resumida BEP SINIM separa personal de planta (215.21.01), contrata "
    "(215.21.02) y honorarios (215.21.03) respecto de personal en programas comunitarios "
    "(215.21.04.004), pero no separa gastos generales de operación interna de los "
    "servicios directos a la comunidad."
)
NOTA_ETAPAS_BEP = (
    "La ficha resumida BEP SINIM solo informa devengo (y percibido para ingresos); "
    "no publica presupuesto inicial ni vigente."
)
ATRIBUCION_SINIM = (
    "Sistema Nacional de Información Municipal (SINIM), SUBDERE, Ministerio del Interior. "
    "Reutilización sin fines comerciales con atribución."
)

_PATRON_MILES_PUNTO = re.compile(r"^[1-9]\d{0,2}(?:\.\d{3})+$")
_PATRON_DEC_CL = re.compile(r"^\d{1,3}(?:\.\d{3})+,\d+$")
_PATRON_DEC_US = re.compile(r"^\d{1,3}(?:,\d{3})+\.\d+$")
_VALORES_VACIOS = frozenset(
    {"", "-", "--", "---", "–", "—", "n/a", "na", "nd", "s/i", "si/d", "sd", "null", "none", "sin informacion"}
)


class SinimFichaError(RuntimeError):
    """Error controlado en descarga o parseo de fichas comunales SINIM."""


class SinimIntegridadError(SinimFichaError):
    """Error de integridad SHA-256 o manifiesto al reproducir insumos archivados."""


def _normalizar_texto(valor: object) -> str:
    """Devuelve texto en minúsculas sin tildes y con espacios colapsados."""
    if valor is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(valor))
    sin_tildes = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


def _decodificar_html(contenido: bytes) -> str:
    """Decodifica HTML de SINIM tolerando UTF-8, Windows-1252 e ISO-8859-1."""
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "iso-8859-1"):
        try:
            return contenido.decode(encoding)
        except UnicodeDecodeError:
            continue
    return contenido.decode("utf-8", errors="replace")


def _formatear_decimal(valor: Decimal) -> str:
    """Formatea un Decimal exacto sin notación científica ni '-0'."""
    with localcontext(CONTEXTO_DECIMAL):
        if valor == CERO:
            return "0"
        texto = format(valor.normalize(), "f")
        if "." in texto:
            texto = texto.rstrip("0").rstrip(".")
        return "0" if texto in {"", "-0"} else texto


def _formatear_cl(valor: Decimal, decimales: int = 1) -> str:
    """Formatea un Decimal en estilo chileno (punto miles, coma decimal)."""
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
        if decimales > 0:
            return f"{signo}{entero_fmt},{frac}"
        return f"{signo}{entero_fmt}"


def parsear_monto_sinim_miles(raw: object) -> Decimal | None:
    """Parsea un monto BEP SINIM (en miles CLP / ``M$``) a ``Decimal(34)``.

    Reconoce separador de miles con punto (``13.991.900``), decimales con coma
    (``13.991.900,5``), prefijos monetarios (``$``, ``M$``) y celdas vacías o
    ``S/I`` devolviendo ``None``.
    """
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, Decimal):
        return raw if raw.is_finite() else None
    if isinstance(raw, int):
        return Decimal(raw)

    texto = str(raw).replace("\xa0", " ").replace("\u2009", " ").strip()
    if not texto or _normalizar_texto(texto) in _VALORES_VACIOS:
        return None

    negativo = False
    if texto.startswith("(") and texto.endswith(")"):
        negativo = True
        texto = texto[1:-1].strip()

    texto = re.sub(r"^(?:mm?\$|clp|\$)\s*", "", texto, flags=re.IGNORECASE).strip()
    texto = re.sub(r"\s*(?:m\$|mm\$|clp)$", "", texto, flags=re.IGNORECASE).strip()
    if not texto or _normalizar_texto(texto) in _VALORES_VACIOS:
        return None

    if texto.startswith("-"):
        negativo = not negativo
        texto = texto[1:].strip()
    elif texto.startswith("+"):
        texto = texto[1:].strip()

    texto = re.sub(r"\s+", "", texto)
    if not texto or _normalizar_texto(texto) in _VALORES_VACIOS:
        return None

    tiene_punto = "." in texto
    tiene_coma = "," in texto
    normalizado: str | None = None

    if tiene_punto and tiene_coma:
        if _PATRON_DEC_CL.match(texto) or texto.rfind(",") > texto.rfind("."):
            normalizado = texto.replace(".", "").replace(",", ".")
        elif _PATRON_DEC_US.match(texto) or texto.rfind(".") > texto.rfind(","):
            normalizado = texto.replace(",", "")
        else:
            return None
    elif tiene_punto:
        if _PATRON_MILES_PUNTO.match(texto):
            normalizado = texto.replace(".", "")
        elif texto.count(".") == 1 and re.fullmatch(r"\d+\.\d+", texto):
            normalizado = texto
        else:
            return None
    elif tiene_coma:
        if texto.count(",") == 1 and re.fullmatch(r"\d+,\d+", texto):
            normalizado = texto.replace(",", ".")
        elif re.fullmatch(r"\d{1,3}(?:,\d{3}){2,}", texto):
            normalizado = texto.replace(",", "")
        else:
            return None
    else:
        if re.fullmatch(r"\d+", texto):
            normalizado = texto
        else:
            return None

    if negativo:
        normalizado = f"-{normalizado}"

    with localcontext(CONTEXTO_DECIMAL):
        try:
            valor = Decimal(normalizado)
        except InvalidOperation:
            return None
    return valor if valor.is_finite() else None


def parsear_porcentaje_sinim(raw: object) -> Decimal | None:
    """Parsea un porcentaje de ficha SINIM (ej. ``'64,25%'`` -> ``Decimal('64.25')``)."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, Decimal):
        return raw if raw.is_finite() else None
    if isinstance(raw, int):
        return Decimal(raw)
    texto = str(raw).replace("\xa0", " ").replace("%", "").strip()
    if not texto or _normalizar_texto(texto) in _VALORES_VACIOS:
        return None
    texto = re.sub(r"\s+", "", texto)
    if "," in texto and "." not in texto and texto.count(",") == 1:
        normalizado = texto.replace(",", ".")
    elif "." in texto and "," not in texto and texto.count(".") == 1:
        normalizado = texto
    elif "," in texto and "." in texto:
        return parsear_monto_sinim_miles(texto)
    else:
        normalizado = texto
    with localcontext(CONTEXTO_DECIMAL):
        try:
            valor = Decimal(normalizado)
        except InvalidOperation:
            return None
    return valor if valor.is_finite() else None


def detectar_anio_bep(soup: BeautifulSoup) -> int | None:
    """Detecta el año BEP desde el encabezado de la ficha SINIM.

    Ejemplo esperado: ``Ingresos Municipales (M$) 2025 (Fuente BEP)`` -> ``2025``.
    """
    patrones = (
        re.compile(r"ingresos\s+municipales[^0-9]{0,30}(20\d{2})\s*\(?\s*fuente\s+bep"),
        re.compile(r"gastos\s+municipales[^0-9]{0,30}(20\d{2})\s*\(?\s*fuente\s+bep"),
        re.compile(r"(20\d{2})\s*\(\s*fuente\s+bep\s*\)"),
        re.compile(r"fuente\s+bep[^0-9]{0,20}(20\d{2})"),
    )

    # Priorizar encabezados y celdas de título de tabla
    nodos_prioritarios = soup.find_all(["h1", "h2", "h3", "h4", "th", "caption", "strong", "b", "td"])
    for nodo in nodos_prioritarios:
        texto = _normalizar_texto(nodo.get_text(" ", strip=True))
        if "bep" not in texto:
            continue
        for patron in patrones:
            coincidencia = patron.search(texto)
            if coincidencia:
                return int(coincidencia.group(1))

    texto_completo = _normalizar_texto(soup.get_text(" ", strip=True))
    for patron in patrones:
        coincidencia = patron.search(texto_completo)
        if coincidencia:
            return int(coincidencia.group(1))
    return None


def _extraer_filas_pares(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Extrae pares ``(etiqueta, valor_comunal)`` de las tablas SINIM evitando tablas anidadas.

    Las fichas oficiales de SINIM publican tablas de 4 columnas:
    ``Descripción | Unidad Medida | Comunal | Nacional``.
    Esta función detecta el índice de la columna ``Comunal`` por encabezado (o
    usa la columna comunal por posición) para NUNCA tomar la columna ``Nacional``
    ni confundir valores país con cifras municipales.
    """
    pares: list[tuple[str, str]] = []
    tablas = soup.find_all("table")
    procesadas: set[int] = set()

    for tabla in tablas:
        # Ignorar tablas contenedoras que envuelven otra tabla completa
        if tabla.find("table") is not None:
            continue

        idx_comunal: int | None = None
        idx_nacional: int | None = None
        for tr in tabla.find_all("tr"):
            procesadas.add(id(tr))
            celdas_tags = tr.find_all(["th", "td"], recursive=False)
            if len(celdas_tags) < 2:
                continue
            if any(c.find("table") is not None for c in celdas_tags):
                continue

            textos = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)).strip() for c in celdas_tags]
            es_encabezado = all(c.name == "th" for c in celdas_tags) or any(
                _normalizar_texto(t) in {"comunal", "nacional", "unidad medida", "descripcion"}
                for t in textos
            )
            if es_encabezado:
                for i, t in enumerate(textos):
                    tn = _normalizar_texto(t)
                    if "comunal" in tn or tn in {"comuna", "municipal", "municipio"}:
                        idx_comunal = i
                    elif "nacional" in tn or tn in {"pais", "total pais"}:
                        idx_nacional = i
                continue

            etiqueta = textos[0]
            if not etiqueta:
                continue

            if len(textos) == 2:
                valor = textos[1]
            elif idx_comunal is not None and idx_comunal < len(textos):
                valor = textos[idx_comunal]
            elif idx_nacional is not None and idx_nacional >= 2 and (idx_nacional - 1) < len(textos):
                valor = textos[idx_nacional - 1]
            elif len(textos) >= 4:
                # Estructura estándar SINIM: [Descripción, Unidad, Comunal, Nacional]
                valor = textos[2]
            elif len(textos) == 3:
                # Estructura sin columna Nacional: [Descripción, Unidad, Comunal]
                valor = textos[2]
            else:
                valor = textos[1]

            pares.append((etiqueta, valor))

    # Fallback para filas <tr> sueltas fuera de <table> (fixtures mínimos)
    for tr in soup.find_all("tr"):
        if id(tr) in procesadas:
            continue
        celdas_tags = tr.find_all(["th", "td"], recursive=False)
        if len(celdas_tags) < 2 or any(c.find("table") is not None for c in celdas_tags):
            continue
        textos = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)).strip() for c in celdas_tags]
        if textos[0]:
            pares.append((textos[0], textos[1] if len(textos) == 2 else textos[2]))

    return pares


def _clasificar_fila_sinim(etiqueta: str) -> str | None:
    """Identifica el campo canónico correspondiente a una fila verificada de SINIM."""
    norm = _normalizar_texto(etiqueta)
    if not norm:
        return None

    # Sub-partidas específicas de Subtítulo 21 (evaluar antes que el total Subt. 21)
    if re.search(r"(?<!\d)215\.21\.04\.004(?!\d)", norm):
        return "personal_programas_comunitarios_miles"
    if re.search(r"(?<!\d)215\.21\.01(?!\.\d|\d)", norm):
        return "personal_planta_miles"
    if re.search(r"(?<!\d)215\.21\.02(?!\.\d|\d)", norm):
        return "personal_contrata_miles"
    if re.search(r"(?<!\d)215\.21\.03(?!\.\d|\d)", norm):
        return "personal_honorarios_miles"

    # Ingresos y dependencia FCM
    if "participacion del fondo comun municipal" in norm and "ingreso total" in norm:
        return "dependencia_fcm_pct"
    if "ingreso total percibido" in norm or (
        "ingresos municipales" in norm and "percibido" in norm
    ):
        return "ingresos_percibidos_miles"
    if "ingresos por fondo comun municipal" in norm and "participacion" not in norm:
        return "ingresos_fcm_miles"
    if "ingresos propios permanentes" in norm and "participacion" not in norm:
        return "ingresos_propios_permanentes_miles"

    # Gastos BEP
    if "gastos total devengado" in norm or "gasto total devengado" in norm:
        return "gasto_total_devengado_miles"
    if "gastos en personal municipal" in norm and ("subtitulo 21" in norm or "subt. 21" in norm):
        return "gasto_personal_sub21_miles"
    if "bienes y servicios de consumo" in norm and ("subtitulo 22" in norm or "subt. 22" in norm):
        return "gasto_bienes_servicios_sub22_miles"

    # Traspaso educación municipal a SLEP
    if "realizo traspaso de la educacion municipal" in norm or (
        "traspaso de la educacion municipal" in norm
    ):
        return "traspaso_educacion_slep"

    return None


def _a_millones(valor_miles: Decimal | None) -> Decimal | None:
    if valor_miles is None:
        return None
    with localcontext(CONTEXTO_DECIMAL):
        return valor_miles / MIL


def _construir_frase_radial_comuna(
    municipio: str,
    anio: int | None,
    pct_corriente: Decimal | None,
    gasto_total_mm: Decimal | None,
) -> str | None:
    if pct_corriente is None or gasto_total_mm is None or anio is None:
        return None
    pct_cl = _formatear_cl(pct_corriente, decimales=1)
    base_cl = _formatear_cl(gasto_total_mm, decimales=1)
    return (
        f"De cada $100 ejecutados por la Municipalidad de {municipio} en {anio}, "
        f"${pct_cl} correspondieron a gasto corriente observable en personal y bienes y "
        f"servicios (base: ${base_cl} millones devengados según ficha BEP SINIM {anio})."
    )


def parsear_ficha_sinim_html(
    html_bytes: bytes,
    cut: str,
    *,
    url: str | None = None,
    archivo_html: str | None = None,
) -> dict[str, Any]:
    """Parsea los bytes HTML de una ficha comunal SINIM con ``BeautifulSoup`` y ``Decimal(34)``."""
    cut_limpio = str(cut).strip()
    if cut_limpio not in COMUNAS_AYSEN:
        raise ValueError(
            f"CUT '{cut_limpio}' no pertenece a las 10 comunas oficiales de Aysén (Región 11)."
        )
    if not isinstance(html_bytes, (bytes, bytearray)) or not html_bytes.strip():
        raise SinimFichaError(f"HTML vacío para CUT {cut_limpio}.")

    raw_bytes = bytes(html_bytes)
    huella = sha256(raw_bytes).hexdigest()
    html_texto = _decodificar_html(raw_bytes)
    soup = BeautifulSoup(html_texto, "html.parser")

    municipio = COMUNAS_AYSEN[cut_limpio]
    anio_bep = detectar_anio_bep(soup)

    extraidos_raw: dict[str, str] = {}
    for etiqueta, valor in _extraer_filas_pares(soup):
        campo = _clasificar_fila_sinim(etiqueta)
        if campo is not None and campo not in extraidos_raw:
            extraidos_raw[campo] = valor

    ingresos_percibidos_miles = parsear_monto_sinim_miles(
        extraidos_raw.get("ingresos_percibidos_miles")
    )
    ingresos_fcm_miles = parsear_monto_sinim_miles(extraidos_raw.get("ingresos_fcm_miles"))
    ingresos_ipp_miles = parsear_monto_sinim_miles(
        extraidos_raw.get("ingresos_propios_permanentes_miles")
    )
    dependencia_fcm_pct = parsear_porcentaje_sinim(extraidos_raw.get("dependencia_fcm_pct"))
    gasto_total_miles = parsear_monto_sinim_miles(extraidos_raw.get("gasto_total_devengado_miles"))
    sub21_miles = parsear_monto_sinim_miles(extraidos_raw.get("gasto_personal_sub21_miles"))
    planta_miles = parsear_monto_sinim_miles(extraidos_raw.get("personal_planta_miles"))
    contrata_miles = parsear_monto_sinim_miles(extraidos_raw.get("personal_contrata_miles"))
    honorarios_miles = parsear_monto_sinim_miles(extraidos_raw.get("personal_honorarios_miles"))
    prog_com_miles = parsear_monto_sinim_miles(
        extraidos_raw.get("personal_programas_comunitarios_miles")
    )
    sub22_miles = parsear_monto_sinim_miles(extraidos_raw.get("gasto_bienes_servicios_sub22_miles"))

    traspaso_raw = extraidos_raw.get("traspaso_educacion_slep")
    traspaso_slep = traspaso_raw.strip() if isinstance(traspaso_raw, str) and traspaso_raw.strip() else None

    with localcontext(CONTEXTO_DECIMAL):
        ingresos_percibidos_mm = _a_millones(ingresos_percibidos_miles)
        ingresos_fcm_mm = _a_millones(ingresos_fcm_miles)
        ingresos_ipp_mm = _a_millones(ingresos_ipp_miles)
        gasto_total_mm = _a_millones(gasto_total_miles)
        sub21_mm = _a_millones(sub21_miles)
        planta_mm = _a_millones(planta_miles)
        contrata_mm = _a_millones(contrata_miles)
        honorarios_mm = _a_millones(honorarios_miles)
        prog_com_mm = _a_millones(prog_com_miles)
        sub22_mm = _a_millones(sub22_miles)

        gasto_corriente_obs_mm: Decimal | None = None
        if sub21_mm is not None and sub22_mm is not None:
            gasto_corriente_obs_mm = sub21_mm + sub22_mm

        pct_gasto_corriente_exacto: Decimal | None = None
        pct_gasto_corriente_str: str | None = None
        if (
            gasto_corriente_obs_mm is not None
            and gasto_total_mm is not None
            and gasto_total_mm > CERO
        ):
            pct_gasto_corriente_exacto = (CIEN * gasto_corriente_obs_mm) / gasto_total_mm
            pct_gasto_corriente_str = _formatear_decimal(
                pct_gasto_corriente_exacto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            )

        otros_gastos_mm: Decimal | None = None
        if gasto_total_mm is not None and gasto_corriente_obs_mm is not None:
            otros_gastos_mm = gasto_total_mm - gasto_corriente_obs_mm

        # Costo administrativo interno observable en personal: planta + contrata + honorarios
        # (estrictamente separado de 215.21.04.004 programas comunitarios).
        costo_admin_interno_mm: Decimal | None = None
        if planta_mm is not None and contrata_mm is not None and honorarios_mm is not None:
            costo_admin_interno_mm = planta_mm + contrata_mm + honorarios_mm

        costo_admin_interno_pct_str: str | None = None
        if (
            costo_admin_interno_mm is not None
            and gasto_total_mm is not None
            and gasto_total_mm > CERO
        ):
            pct_admin = ((CIEN * costo_admin_interno_mm) / gasto_total_mm).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            costo_admin_interno_pct_str = _formatear_decimal(pct_admin)

    frase_radial = _construir_frase_radial_comuna(
        municipio=municipio,
        anio=anio_bep,
        pct_corriente=pct_gasto_corriente_exacto,
        gasto_total_mm=gasto_total_mm,
    )

    url_oficial = url or URL_FICHA_PLANTILLA.format(cut=cut_limpio)
    return {
        "cut": cut_limpio,
        "municipio": municipio,
        "es_piloto_destacado": cut_limpio == CUT_PILOTO_AYSEN,
        "anio": anio_bep,
        "etapa_contable": "devengo",
        "unidad_origen": "miles CLP (M$)",
        "unidad_salida": "millones CLP",
        "moneda": "CLP",
        "presupuesto_inicial_millones": None,
        "presupuesto_vigente_millones": None,
        "nota_etapas_presupuestarias": NOTA_ETAPAS_BEP,
        "ingresos_percibidos_millones": (
            _formatear_decimal(ingresos_percibidos_mm) if ingresos_percibidos_mm is not None else None
        ),
        "ingresos_fcm_millones": (
            _formatear_decimal(ingresos_fcm_mm) if ingresos_fcm_mm is not None else None
        ),
        "ingresos_propios_permanentes_millones": (
            _formatear_decimal(ingresos_ipp_mm) if ingresos_ipp_mm is not None else None
        ),
        "dependencia_fcm_pct": (
            _formatear_decimal(dependencia_fcm_pct) if dependencia_fcm_pct is not None else None
        ),
        "gasto_total_devengado_millones": (
            _formatear_decimal(gasto_total_mm) if gasto_total_mm is not None else None
        ),
        "gasto_personal_sub21_millones": (
            _formatear_decimal(sub21_mm) if sub21_mm is not None else None
        ),
        "personal_planta_millones": (
            _formatear_decimal(planta_mm) if planta_mm is not None else None
        ),
        "personal_contrata_millones": (
            _formatear_decimal(contrata_mm) if contrata_mm is not None else None
        ),
        "personal_honorarios_millones": (
            _formatear_decimal(honorarios_mm) if honorarios_mm is not None else None
        ),
        "personal_programas_comunitarios_millones": (
            _formatear_decimal(prog_com_mm) if prog_com_mm is not None else None
        ),
        "gasto_bienes_servicios_sub22_millones": (
            _formatear_decimal(sub22_mm) if sub22_mm is not None else None
        ),
        "traspaso_educacion_slep": traspaso_slep,
        "gasto_corriente_observable_millones": (
            _formatear_decimal(gasto_corriente_obs_mm) if gasto_corriente_obs_mm is not None else None
        ),
        "porcentaje_gasto_corriente_pct": pct_gasto_corriente_str,
        "otros_gastos_no_desglosados_millones": (
            _formatear_decimal(otros_gastos_mm) if otros_gastos_mm is not None else None
        ),
        "base_calculo_gasto_corriente": BASE_CALCULO_GASTO_CORRIENTE,
        "frase_radial": frase_radial,
        "costo_admin_interno_millones": (
            _formatear_decimal(costo_admin_interno_mm) if costo_admin_interno_mm is not None else None
        ),
        "costo_admin_interno_pct": costo_admin_interno_pct_str,
        "nota_costo_administracion": NOTA_COSTO_ADMINISTRACION,
        "url_respaldo": url_oficial,
        "archivo_html": archivo_html,
        "sha256_html": huella,
    }


def _http_get_bytes(url: str, timeout: int = TIMEOUT_SINIM_SEGUNDOS) -> tuple[bytes, int]:
    """Descarga una ficha SINIM devolviendo ``(bytes_crudos, http_status)``."""
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode() or 200
            return resp.read(), int(status)
    except HTTPError as exc:
        raise SinimFichaError(f"Error HTTP {exc.code} al descargar ficha SINIM: {url}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise SinimFichaError(
            f"Error de red al descargar ficha SINIM ({type(exc).__name__}): {url}"
        ) from exc


def _escribir_json_atomico(ruta: Path, payload: Mapping[str, Any]) -> Path:
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(destino.suffix + ".tmp")
    temporal.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporal, destino)
    return destino


def _validar_lista_comunas(comunas: Sequence[str] | None) -> list[str]:
    if comunas is None:
        return sorted(COMUNAS_AYSEN.keys())
    limpias: list[str] = []
    vistas: set[str] = set()
    for raw in comunas:
        cut = str(raw).strip()
        if not cut:
            continue
        if cut not in COMUNAS_AYSEN:
            raise ValueError(
                f"CUT '{cut}' no pertenece a las 10 comunas oficiales de Aysén: "
                f"{sorted(COMUNAS_AYSEN.keys())}"
            )
        if cut not in vistas:
            vistas.add(cut)
            limpias.append(cut)
    if not limpias:
        raise ValueError("Debe especificar al menos un CUT válido de la Región de Aysén.")
    return sorted(limpias)


def _construir_publicacion(
    comunas_parseadas: list[dict[str, Any]],
    errores: list[dict[str, Any]],
    *,
    modo: str,
    directorio_insumos: Path,
    manifiesto_sha256: str,
    extraido_en: str,
    integridad_sha256_verificada: bool,
) -> dict[str, Any]:
    comunas_ordenadas = sorted(comunas_parseadas, key=lambda c: c["cut"])
    cuts_ok = {c["cut"] for c in comunas_ordenadas}
    comunas_faltantes = [
        {"cut": cut, "municipio": COMUNAS_AYSEN[cut]}
        for cut in sorted(COMUNAS_AYSEN)
        if cut not in cuts_ok
    ]

    anios_detectados = sorted({c["anio"] for c in comunas_ordenadas if c.get("anio") is not None})
    anio_resumen = anios_detectados[0] if len(anios_detectados) == 1 else None

    def _sumar_campo(campo: str) -> Decimal | None:
        valores = [Decimal(c[campo]) for c in comunas_ordenadas if c.get(campo) is not None]
        if not valores:
            return None
        with localcontext(CONTEXTO_DECIMAL):
            acum = CERO
            for v in valores:
                acum += v
            return acum

    with localcontext(CONTEXTO_DECIMAL):
        tot_ingresos = _sumar_campo("ingresos_percibidos_millones")
        tot_fcm = _sumar_campo("ingresos_fcm_millones")
        tot_ipp = _sumar_campo("ingresos_propios_permanentes_millones")
        tot_gasto = _sumar_campo("gasto_total_devengado_millones")
        tot_sub21 = _sumar_campo("gasto_personal_sub21_millones")
        tot_sub22 = _sumar_campo("gasto_bienes_servicios_sub22_millones")
        tot_corr = _sumar_campo("gasto_corriente_observable_millones")
        tot_otros = _sumar_campo("otros_gastos_no_desglosados_millones")
        tot_admin = _sumar_campo("costo_admin_interno_millones")
        tot_prog_com = _sumar_campo("personal_programas_comunitarios_millones")

        pct_corr_regional: str | None = None
        if tot_corr is not None and tot_gasto is not None and tot_gasto > CERO:
            pct_corr_regional = _formatear_decimal(
                ((CIEN * tot_corr) / tot_gasto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            )

    piloto_aysen = next((c for c in comunas_ordenadas if c["cut"] == CUT_PILOTO_AYSEN), None)

    return {
        "esquema": ESQUEMA_SINIM_OFICIAL,
        "region_codigo": "11",
        "region_nombre": "Aysén del General Carlos Ibáñez del Campo",
        "piloto_destacado_cut": CUT_PILOTO_AYSEN,
        "piloto_aysen": piloto_aysen,
        "resumen": {
            "anio": anio_resumen,
            "anios_detectados": anios_detectados,
            "comunas_procesadas": len(comunas_ordenadas),
            "comunas_esperadas": len(COMUNAS_AYSEN),
            "comunas_faltantes": comunas_faltantes,
            "presupuesto_inicial_millones": None,
            "presupuesto_vigente_millones": None,
            "total_ingresos_percibidos_millones": (
                _formatear_decimal(tot_ingresos) if tot_ingresos is not None else None
            ),
            "total_ingresos_fcm_millones": (
                _formatear_decimal(tot_fcm) if tot_fcm is not None else None
            ),
            "total_ingresos_propios_permanentes_millones": (
                _formatear_decimal(tot_ipp) if tot_ipp is not None else None
            ),
            "total_gasto_devengado_millones": (
                _formatear_decimal(tot_gasto) if tot_gasto is not None else None
            ),
            "total_personal_sub21_millones": (
                _formatear_decimal(tot_sub21) if tot_sub21 is not None else None
            ),
            "total_bienes_servicios_sub22_millones": (
                _formatear_decimal(tot_sub22) if tot_sub22 is not None else None
            ),
            "total_gasto_corriente_observable_millones": (
                _formatear_decimal(tot_corr) if tot_corr is not None else None
            ),
            "porcentaje_gasto_corriente_regional_pct": pct_corr_regional,
            "total_otros_gastos_no_desglosados_millones": (
                _formatear_decimal(tot_otros) if tot_otros is not None else None
            ),
            "total_costo_admin_interno_millones": (
                _formatear_decimal(tot_admin) if tot_admin is not None else None
            ),
            "total_programas_comunitarios_millones": (
                _formatear_decimal(tot_prog_com) if tot_prog_com is not None else None
            ),
            "base_calculo_gasto_corriente": BASE_CALCULO_GASTO_CORRIENTE,
            "nota_etapas_presupuestarias": NOTA_ETAPAS_BEP,
        },
        "comunas": comunas_ordenadas,
        "errores": errores,
        "fuente_trazabilidad": {
            "institucion": "SINIM · SUBDERE, Ministerio del Interior",
            "atribucion": ATRIBUCION_SINIM,
            "url_plantilla": URL_FICHA_PLANTILLA,
            "modo": modo,
            "directorio_insumos": str(directorio_insumos),
            "manifiesto_sha256": manifiesto_sha256,
            "integridad_sha256_verificada": integridad_sha256_verificada,
            "extraido_en": extraido_en,
            "etapa_contable": "devengo",
            "unidad_origen": "miles CLP (M$)",
            "unidad_salida": "millones CLP",
            "moneda": "CLP",
        },
    }


def extraer_fichas_sinim_live(
    comunas: Sequence[str] | None = None,
    *,
    raw_root: Path | None = None,
    salida_path: Path | None = None,
    http_get_bytes: Callable[[str, int], tuple[bytes, int]] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Descarga, archiva con SHA-256 y publica fichas oficiales SINIM de Aysén."""
    cuts = _validar_lista_comunas(comunas)
    ahora_utc = datetime.now(timezone.utc).replace(microsecond=0)
    ts = timestamp or ahora_utc.strftime("%Y%m%dT%H%M%SZ")
    extraido_en = ahora_utc.isoformat().replace("+00:00", "Z")

    dir_raw = Path(raw_root or _RAW_ROOT_DEFECTO) / f"sinim-fichas-{ts}"
    dir_raw.mkdir(parents=True, exist_ok=True)
    fetcher = http_get_bytes or _http_get_bytes

    entradas_manifiesto: list[dict[str, Any]] = []
    comunas_parseadas: list[dict[str, Any]] = []
    errores: list[dict[str, Any]] = []

    for cut in cuts:
        url = URL_FICHA_PLANTILLA.format(cut=cut)
        nombre_archivo = f"ficha-{cut}.html"
        ruta_html = dir_raw / nombre_archivo
        try:
            html_bytes, status = fetcher(url, TIMEOUT_SINIM_SEGUNDOS)
            if not (200 <= status < 300):
                raise SinimFichaError(f"Estado HTTP inesperado {status} en {url}")
            ruta_html.write_bytes(html_bytes)
            huella = sha256(html_bytes).hexdigest()
            ficha = parsear_ficha_sinim_html(
                html_bytes,
                cut,
                url=url,
                archivo_html=nombre_archivo,
            )
            comunas_parseadas.append(ficha)
            entradas_manifiesto.append(
                {
                    "cut": cut,
                    "municipio": COMUNAS_AYSEN[cut],
                    "archivo": nombre_archivo,
                    "url": url,
                    "http_status": status,
                    "bytes": len(html_bytes),
                    "sha256": huella,
                    "consultado_en": extraido_en,
                    "estado": "ok",
                    "error": None,
                }
            )
        except (SinimFichaError, HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            errores.append(
                {
                    "cut": cut,
                    "municipio": COMUNAS_AYSEN[cut],
                    "url": url,
                    "error": str(exc),
                }
            )
            entradas_manifiesto.append(
                {
                    "cut": cut,
                    "municipio": COMUNAS_AYSEN[cut],
                    "archivo": None,
                    "url": url,
                    "http_status": None,
                    "bytes": 0,
                    "sha256": None,
                    "consultado_en": extraido_en,
                    "estado": "error",
                    "error": str(exc),
                }
            )

    manifiesto = {
        "esquema": "sinim-fichas-manifiesto-v1",
        "generado_en": extraido_en,
        "fuente": ATRIBUCION_SINIM,
        "url_plantilla": URL_FICHA_PLANTILLA,
        "comunas_solicitadas": cuts,
        "archivos": entradas_manifiesto,
    }
    ruta_manifiesto = _escribir_json_atomico(dir_raw / "manifiesto.json", manifiesto)
    manifiesto_sha256 = sha256(ruta_manifiesto.read_bytes()).hexdigest()

    publicacion = _construir_publicacion(
        comunas_parseadas,
        errores,
        modo="en_vivo",
        directorio_insumos=dir_raw,
        manifiesto_sha256=manifiesto_sha256,
        extraido_en=extraido_en,
        integridad_sha256_verificada=True,
    )
    destino = Path(salida_path or _SALIDA_PUBLICADA_DEFECTO)
    _escribir_json_atomico(destino, publicacion)
    return publicacion


def reproducir_fichas_sinim(
    insumos_dir: Path,
    *,
    salida_path: Path | None = None,
    escribir_salida: bool = True,
) -> dict[str, Any]:
    """Reproduce el JSON publicado SIN RED validando SHA-256 contra ``manifiesto.json``."""
    dir_insumos = Path(insumos_dir)
    ruta_manifiesto = dir_insumos / "manifiesto.json"
    if not ruta_manifiesto.exists():
        raise SinimIntegridadError(
            f"No existe manifiesto.json en el directorio de insumos: {dir_insumos}"
        )

    raw_manifiesto = ruta_manifiesto.read_bytes()
    manifiesto_sha256 = sha256(raw_manifiesto).hexdigest()
    try:
        manifiesto = json.loads(raw_manifiesto.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SinimIntegridadError(f"manifiesto.json inválido en {dir_insumos}: {exc}") from exc

    archivos = manifiesto.get("archivos")
    if not isinstance(archivos, list):
        raise SinimIntegridadError("El campo 'archivos' de manifiesto.json debe ser una lista.")

    comunas_parseadas: list[dict[str, Any]] = []
    errores: list[dict[str, Any]] = []

    for entrada in archivos:
        if not isinstance(entrada, Mapping):
            continue
        cut = str(entrada.get("cut") or "").strip()
        estado = entrada.get("estado")
        if estado != "ok":
            errores.append(
                {
                    "cut": cut,
                    "municipio": COMUNAS_AYSEN.get(cut),
                    "url": entrada.get("url"),
                    "error": entrada.get("error") or "descarga_fallida_en_captura_original",
                }
            )
            continue

        nombre_archivo = entrada.get("archivo")
        sha_esperado = entrada.get("sha256")
        if not nombre_archivo or not sha_esperado:
            raise SinimIntegridadError(
                f"Entrada de manifiesto incompleta para CUT '{cut}': faltan archivo o sha256."
            )
        ruta_html = dir_insumos / str(nombre_archivo)
        if not ruta_html.exists():
            raise SinimIntegridadError(
                f"Archivo HTML faltante en insumos para CUT '{cut}': {ruta_html}"
            )
        html_bytes = ruta_html.read_bytes()
        sha_actual = sha256(html_bytes).hexdigest()
        if sha_actual != sha_esperado:
            raise SinimIntegridadError(
                f"Discrepancia SHA-256 en '{ruta_html}' (CUT {cut}): "
                f"esperado={sha_esperado}, actual={sha_actual}."
            )

        ficha = parsear_ficha_sinim_html(
            html_bytes,
            cut,
            url=entrada.get("url"),
            archivo_html=str(nombre_archivo),
        )
        comunas_parseadas.append(ficha)

    extraido_en = str(
        manifiesto.get("generado_en")
        or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    publicacion = _construir_publicacion(
        comunas_parseadas,
        errores,
        modo="reproducido_sin_red",
        directorio_insumos=dir_insumos,
        manifiesto_sha256=manifiesto_sha256,
        extraido_en=extraido_en,
        integridad_sha256_verificada=True,
    )
    if escribir_salida:
        destino = Path(salida_path or _SALIDA_PUBLICADA_DEFECTO)
        _escribir_json_atomico(destino, publicacion)
    return publicacion


def _construir_parser_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pipelines.fiscal.sinim_ficha_live",
        description=(
            "Descarga o reproduce sin red las fichas comunales oficiales BEP SINIM "
            "para las 10 comunas de la Región de Aysén."
        ),
    )
    parser.add_argument(
        "--comunas",
        type=str,
        default=None,
        help="Lista de CUT separados por coma (ej. 11201 para piloto Aysén). Por defecto las 10 comunas.",
    )
    parser.add_argument(
        "--reproducir",
        action="store_true",
        help="Reproduce la publicación sin red desde un directorio de insumos archivados.",
    )
    parser.add_argument(
        "--insumos",
        type=Path,
        default=None,
        help="Directorio de insumos con HTML originales y manifiesto.json (requerido con --reproducir).",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=_RAW_ROOT_DEFECTO,
        help="Directorio raíz donde archivar sinim-fichas-<timestamp>/.",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=_SALIDA_PUBLICADA_DEFECTO,
        help="Ruta del archivo JSON publicado.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _construir_parser_cli()
    args = parser.parse_args(argv)

    if args.reproducir:
        if args.insumos is None:
            parser.error("--reproducir requiere especificar --insumos <dir>.")
        resultado = reproducir_fichas_sinim(args.insumos, salida_path=args.salida)
    else:
        lista_comunas = (
            [c.strip() for c in args.comunas.split(",") if c.strip()]
            if args.comunas
            else None
        )
        resultado = extraer_fichas_sinim_live(
            comunas=lista_comunas,
            raw_root=args.raw_dir,
            salida_path=args.salida,
        )

    resumen = resultado["resumen"]
    print(
        json.dumps(
            {
                "modo": resultado["fuente_trazabilidad"]["modo"],
                "anio": resumen["anio"],
                "comunas_procesadas": resumen["comunas_procesadas"],
                "errores": len(resultado["errores"]),
                "salida": str(args.salida),
                "directorio_insumos": resultado["fuente_trazabilidad"]["directorio_insumos"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
