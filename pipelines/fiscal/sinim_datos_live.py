"""Extractor oficial en vivo y reproducible de variables presupuestarias SINIM (2018–2025).

Fuente oficial verificada:
    ``https://datos.sinim.gov.cl/datos_municipales.php``
    (endpoints AJAX públicos: ``obtener_municipios.php``, ``obtener_cabecera.php``,
    ``obtener_valores.php``, sin necesidad de credenciales).

Cobertura:
    - Las 10 comunas de la Región de Aysén (región SINIM ``129``, CUT ``11101``–``11402``).
    - Años ``2018`` a ``2025`` (periodos SINIM ``19`` a ``26``).
    - Variables presupuestarias y de gestión en ``M$`` (miles CLP -> ``millones CLP``
      con ``Decimal(34)``): Presupuesto Inicial (``4211``), Presupuesto Vigente (``4213``),
      Gasto Total Devengado (``1093``), Gastos Corrientes oficiales (``894``), Inversión
      Municipal oficial (``1103``), Personal Subt. 21 (``3975``: Planta ``1305``, Contrata
      ``1306``, Honorarios ``4421``, Programas Comunitarios ``3964``), Bienes y Servicios
      Subt. 22 (``3770``), Transferencias Corrientes Subt. 24 (``1229``), Gasto en Área de
      Gestión Interna (``4162``) vs Servicios Comunitarios (``4163``) y Programas Sociales
      (``4165``), e Ingresos Percibidos (``1110``), FCM (``880``) e IPP (``879``).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Context, Decimal, ROUND_HALF_UP, localcontext
from hashlib import sha256
import http.cookiejar
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence
import urllib.parse
import urllib.request

try:
    from pipelines.fiscal.sinim_ficha_live import (
        URL_FICHA_PLANTILLA,
        _formatear_cl,
        _formatear_decimal,
        parsear_monto_sinim_miles,
    )
    from pipelines.fiscal.sinim_importer import COMUNAS_AYSEN
except ImportError:  # pragma: no cover
    from sinim_ficha_live import (
        URL_FICHA_PLANTILLA,
        _formatear_cl,
        _formatear_decimal,
        parsear_monto_sinim_miles,
    )
    from sinim_importer import COMUNAS_AYSEN

ESQUEMA_SINIM_HISTORICO = "sinim-aysen-historico-v1"
REGION_SINIM_AYSEN = "129"
URL_SINIM_BASE = "https://datos.sinim.gov.cl"
URL_SINIM_DATOS = f"{URL_SINIM_BASE}/datos_municipales.php"

PERIODOS_SINIM_POR_ANIO: dict[int, int] = {
    2018: 19,
    2019: 20,
    2020: 21,
    2021: 22,
    2022: 23,
    2023: 24,
    2024: 25,
    2025: 26,
}
ANIO_POR_PERIODO_SINIM: dict[int, int] = {v: k for k, v in PERIODOS_SINIM_POR_ANIO.items()}

# Variables oficiales verificadas en datos.sinim.gov.cl (todas en M$ = miles CLP)
VARIABLES_SINIM: dict[str, tuple[int, str, str]] = {
    "presupuesto_inicial": (4211, "BPIGM", "Presupuesto Inicial Gastos Municipales"),
    "presupuesto_vigente": (4213, "BPVGM", "Presupuesto Vigente Gastos Municipales"),
    "gasto_total_devengado": (1093, "IADM11", "Gastos Municipales (Gasto Total Devengado)"),
    "gastos_corrientes": (894, "IADM51", "Gastos Corrientes"),
    "inversion_municipal": (1103, "IADM22", "Inversión Municipal"),
    "gasto_personal_sub21": (3975, "IADM61", "Gastos en Personal Municipal (Subtítulo 21)"),
    "personal_planta": (1305, "IADM78", "Gasto Personal Planta (215.21.01)"),
    "personal_contrata": (1306, "IADM79", "Gasto Personal a Contrata (215.21.02)"),
    "personal_honorarios": (4421, "IADM80", "Gasto Personal a Honorarios (215.21.03)"),
    "personal_programas_comunitarios": (3964, "IADM111", "Gasto Personal Programas Comunitarios (215.21.04.004)"),
    "gasto_bienes_servicios_sub22": (3770, "IADM85", "Gastos en Bienes y Servicios de Consumo (Subtítulo 22)"),
    "transferencias_corrientes_sub24": (1229, "IADM60", "Transferencias Corrientes (Subtítulo 24)"),
    "area_gestion_interna": (4162, "BGMAGINT", "Gastos Municipales Área de Gestión: Interna"),
    "area_servicios_comunitarios": (4163, "BGMASCOM", "Gastos Municipales Área de Gestión: Servicios Comunitarios"),
    "area_programas_sociales": (4165, "BGMAPSOC", "Gastos Municipales Área de Gestión: Programas Sociales"),
    "area_actividades_municipales": (4164, "BGMAAMUN", "Gastos Municipales Área de Gestión: Actividades Municipales"),
    "ingresos_percibidos": (1110, "IADM01", "Ingresos Municipales (Ingreso Total Percibido)"),
    "ingresos_fcm": (880, "IADM40", "Ingresos por Fondo Común Municipal"),
    "ingresos_propios_permanentes": (879, "IADM41", "Ingresos Propios Permanentes (IPP)"),
}
CAMPO_POR_ID_DATO: dict[int, str] = {v[0]: k for k, v in VARIABLES_SINIM.items()}

SUBAREAS_SINIM: tuple[str, ...] = ("517", "22", "169", "170", "21")

CONTEXTO_DECIMAL = Context(prec=34)
CERO = Decimal("0")
CIEN = Decimal("100")
MIL = Decimal("1000")

_RAIZ_REPO = Path(__file__).resolve().parents[2]
_RAW_ROOT_DEFECTO = _RAIZ_REPO / "data" / "raw"
_SALIDA_DEFECTO = _RAIZ_REPO / "data" / "published" / "sinim-aysen-historico.json"


def _encode_jquery(obj: Any, prefix: str = "") -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}[{k}]" if prefix else str(k)
            pairs.extend(_encode_jquery(v, key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, (dict, list)):
                pairs.extend(_encode_jquery(v, f"{prefix}[{i}]"))
            else:
                pairs.append((f"{prefix}[]", "" if v is None else str(v)))
    else:
        pairs.append((prefix, "" if obj is None else str(obj)))
    return pairs


class ClienteSinimHttp:
    """Cliente HTTP con sesión PHP oficial para ``datos.sinim.gov.cl``."""

    def __init__(self, timeout: int = 35) -> None:
        self._timeout = timeout
        self._cj = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self._cj))
        self._opener.addheaders = [
            ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ChileTerritorial/1.0"),
            ("Referer", URL_SINIM_DATOS),
        ]
        self._iniciado = False

    def iniciar_sesion(self) -> None:
        if not self._iniciado:
            with self._opener.open(URL_SINIM_DATOS, timeout=self._timeout) as resp:
                resp.read()
            self._iniciado = True

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.iniciar_sesion()
        pairs = _encode_jquery(payload)
        encoded = urllib.parse.urlencode(pairs).encode("utf-8")
        req = urllib.request.Request(
            f"{URL_SINIM_BASE}{path}",
            data=encoded,
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": URL_SINIM_DATOS,
            },
        )
        with self._opener.open(req, timeout=self._timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)


def _a_millones(valor_miles: Decimal | None) -> Decimal | None:
    if valor_miles is None:
        return None
    with localcontext(CONTEXTO_DECIMAL):
        return valor_miles / MIL


def _ratio_pct(num: Decimal | None, den: Decimal | None) -> Decimal | None:
    if num is None or den is None or den <= CERO:
        return None
    with localcontext(CONTEXTO_DECIMAL):
        return ((CIEN * num) / den).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def construir_registro_comuna_anio(
    cut: str,
    anio: int,
    valores_miles: Mapping[str, Decimal | None],
) -> dict[str, Any]:
    """Construye el registro presupuestario completo de una comuna y año con ``Decimal(34)``."""
    municipio = COMUNAS_AYSEN[cut]
    mm = {k: _a_millones(v) for k, v in valores_miles.items()}

    inicial = mm.get("presupuesto_inicial")
    vigente = mm.get("presupuesto_vigente")
    devengado = mm.get("gasto_total_devengado")
    corriente_oficial = mm.get("gastos_corrientes")
    inversion_oficial = mm.get("inversion_municipal")
    sub21 = mm.get("gasto_personal_sub21")
    planta = mm.get("personal_planta")
    contrata = mm.get("personal_contrata")
    honorarios = mm.get("personal_honorarios")
    prog_com = mm.get("personal_programas_comunitarios")
    sub22 = mm.get("gasto_bienes_servicios_sub22")
    sub24 = mm.get("transferencias_corrientes_sub24")
    gestion_interna = mm.get("area_gestion_interna")
    serv_comunitarios = mm.get("area_servicios_comunitarios")
    prog_sociales = mm.get("area_programas_sociales")
    act_municipales = mm.get("area_actividades_municipales")
    ingresos = mm.get("ingresos_percibidos")
    fcm = mm.get("ingresos_fcm")
    ipp = mm.get("ingresos_propios_permanentes")

    # Usar Gastos Corrientes oficial SINIM (IADM51); si no existe en un año, caer a Subt. 21+22+24
    es_corriente_oficial = corriente_oficial is not None
    gasto_corriente = corriente_oficial
    if gasto_corriente is None and any(x is not None for x in (sub21, sub22, sub24)):
        with localcontext(CONTEXTO_DECIMAL):
            gasto_corriente = (sub21 or CERO) + (sub22 or CERO) + (sub24 or CERO)

    tasa_ejec_pct = _ratio_pct(devengado, vigente)
    corriente_pct = _ratio_pct(gasto_corriente, devengado)
    inversion_pct = _ratio_pct(inversion_oficial, devengado)
    dep_fcm_pct = _ratio_pct(fcm, ingresos)

    # Costo administrativo interno: preferir Área de Gestión Interna oficial (BGMAGINT)
    if gestion_interna is not None:
        admin_monto = gestion_interna
        admin_pct = _ratio_pct(gestion_interna, devengado)
        nota_admin = (
            "Gasto oficial del Área de Gestión Interna (SINIM BGMAGINT), que separa el "
            "funcionamiento interno municipal de Servicios Comunitarios (BGMASCOM), Programas "
            "Sociales (BGMAPSOC) y Actividades Municipales (BGMAAMUN)."
        )
    elif planta is not None and contrata is not None and honorarios is not None:
        with localcontext(CONTEXTO_DECIMAL):
            admin_monto = planta + contrata + honorarios
        admin_pct = _ratio_pct(admin_monto, devengado)
        nota_admin = (
            "Suma de personal de planta (215.21.01), contrata (215.21.02) y honorarios (215.21.03), "
            "separada de personal en programas comunitarios (215.21.04.004)."
        )
    else:
        admin_monto = None
        admin_pct = None
        nota_admin = "Sin dato de Área de Gestión Interna disponible para este año en SINIM."

    base_calculo = (
        "Porcentajes calculados sobre el Gasto Total Devengado BEP SINIM (IADM11). "
        + (
            "Gasto corriente corresponde a la variable oficial SINIM IADM51 (Gastos Corrientes) "
            "e Inversión corresponde a IADM22 (Inversión Municipal)."
            if es_corriente_oficial
            else "Gasto corriente observable corresponde a Subt. 21 + Subt. 22 + Subt. 24."
        )
    )

    frase_radial: str | None = None
    if corriente_pct is not None and devengado is not None:
        parte_inv = (
            f" y ${_formatear_cl(inversion_pct, 1)} a inversión municipal"
            if inversion_pct is not None
            else ""
        )
        frase_radial = (
            f"De cada $100 ejecutados por la Municipalidad de {municipio} en {anio}, "
            f"${_formatear_cl(corriente_pct, 1)} correspondieron a gasto corriente{parte_inv} "
            f"(base: ${_formatear_cl(devengado, 1)} millones devengados según SINIM BEP {anio})."
        )

    def fmt_opt(v: Decimal | None) -> str | None:
        return _formatear_decimal(v) if v is not None else None

    return {
        "cut": cut,
        "municipio": municipio,
        "es_piloto_destacado": cut == "11201",
        "anio": anio,
        "etapa_contable": "inicial_vigente_devengado",
        "unidad_origen": "miles CLP (M$)",
        "unidad_salida": "millones CLP",
        "moneda": "CLP",
        "presupuesto_inicial_millones": fmt_opt(inicial),
        "presupuesto_vigente_millones": fmt_opt(vigente),
        "gasto_total_devengado_millones": fmt_opt(devengado),
        "tasa_ejecucion_pct": fmt_opt(tasa_ejec_pct),
        "gasto_corriente_observable_millones": fmt_opt(gasto_corriente),
        "porcentaje_gasto_corriente_pct": fmt_opt(corriente_pct),
        "gasto_inversion_millones": fmt_opt(inversion_oficial),
        "inversion_pct": fmt_opt(inversion_pct),
        "gasto_personal_sub21_millones": fmt_opt(sub21),
        "personal_planta_millones": fmt_opt(planta),
        "personal_contrata_millones": fmt_opt(contrata),
        "personal_honorarios_millones": fmt_opt(honorarios),
        "personal_programas_comunitarios_millones": fmt_opt(prog_com),
        "gasto_bienes_servicios_sub22_millones": fmt_opt(sub22),
        "transferencias_corrientes_sub24_millones": fmt_opt(sub24),
        "area_gestion_interna_millones": fmt_opt(gestion_interna),
        "area_servicios_comunitarios_millones": fmt_opt(serv_comunitarios),
        "area_programas_sociales_millones": fmt_opt(prog_sociales),
        "area_actividades_municipales_millones": fmt_opt(act_municipales),
        "costo_admin_interno_millones": fmt_opt(admin_monto),
        "costo_admin_interno_pct": fmt_opt(admin_pct),
        "nota_costo_administracion": nota_admin,
        "ingresos_percibidos_millones": fmt_opt(ingresos),
        "ingresos_fcm_millones": fmt_opt(fcm),
        "ingresos_propios_permanentes_millones": fmt_opt(ipp),
        "dependencia_fcm_pct": fmt_opt(dep_fcm_pct),
        "base_calculo_gasto_corriente": base_calculo,
        "frase_radial": frase_radial,
        "url_respaldo": URL_FICHA_PLANTILLA.format(cut=cut),
        "url_datos_municipales": URL_SINIM_DATOS,
    }


def parsear_respuestas_sinim(
    municipios_payload: Mapping[str, Any],
    valores_por_pagina: Sequence[Mapping[str, Any]],
    anios: Sequence[int],
) -> dict[str, Any]:
    """Convierte las respuestas crudas archivadas de SINIM en el corte publicado histórico."""
    id_a_cut: dict[str, str] = {}
    for m in municipios_payload.get("textos") or []:
        cut = str(m.get("idLegal") or "").strip()
        id_mun = str(m.get("id_municipio") or "").strip()
        if cut in COMUNAS_AYSEN and id_mun:
            id_a_cut[id_mun] = cut

    # Matriz [anio][cut][campo] -> Decimal (miles CLP)
    matriz: dict[int, dict[str, dict[str, Decimal | None]]] = {
        anio: {cut: {} for cut in COMUNAS_AYSEN} for anio in anios
    }

    patron_col = re.compile(r"^col-(\d+)-(\d+)$")
    for pagina in valores_por_pagina:
        for item in pagina.get("textos") or []:
            id_mun = str(item.get("municipio") or "").strip()
            cut = id_a_cut.get(id_mun)
            if not cut:
                continue
            m_col = patron_col.match(str(item.get("col") or "").strip())
            if not m_col:
                continue
            id_per = int(m_col.group(1))
            id_dato = int(m_col.group(2))
            anio = ANIO_POR_PERIODO_SINIM.get(id_per)
            campo = CAMPO_POR_ID_DATO.get(id_dato)
            if anio not in matriz or campo is None:
                continue
            matriz[anio][cut][campo] = parsear_monto_sinim_miles(item.get("valor"))

    por_anio: dict[str, dict[str, Any]] = {}
    for anio in sorted(anios):
        comunas_anio: dict[str, dict[str, Any]] = {}
        for cut in sorted(COMUNAS_AYSEN):
            comunas_anio[cut] = construir_registro_comuna_anio(cut, anio, matriz[anio][cut])
        por_anio[str(anio)] = comunas_anio

    ultimo_anio = max(anios)
    comunas_recientes = [por_anio[str(ultimo_anio)][cut] for cut in sorted(COMUNAS_AYSEN)]

    return {
        "esquema": ESQUEMA_SINIM_HISTORICO,
        "region_codigo": "11",
        "region_nombre": "Aysén del General Carlos Ibáñez del Campo",
        "anios": sorted(anios),
        "ultimo_anio": ultimo_anio,
        "piloto_aysen": por_anio[str(ultimo_anio)]["11201"],
        "comunas": comunas_recientes,
        "por_anio": por_anio,
        "variables_consultadas": [
            {"campo": k, "id_dato": v[0], "codigo_sinim": v[1], "nombre": v[2], "unidad_origen": "M$"}
            for k, v in VARIABLES_SINIM.items()
        ],
    }


def extraer_sinim_historico_live(
    *,
    anios: Sequence[int] = tuple(sorted(PERIODOS_SINIM_POR_ANIO.keys())),
    raw_root: Path = _RAW_ROOT_DEFECTO,
    salida_path: Path = _SALIDA_DEFECTO,
    cliente: ClienteSinimHttp | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Descarga en vivo las 19 variables SINIM (2018–2025) para las 10 comunas de Aysén."""
    cli = cliente or ClienteSinimHttp()
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dir_insumos = raw_root / f"sinim-datos-{ts}"
    dir_insumos.mkdir(parents=True, exist_ok=True)

    anios_ordenados = sorted(int(a) for a in anios if int(a) in PERIODOS_SINIM_POR_ANIO)
    periodos_ids = [str(PERIODOS_SINIM_POR_ANIO[a]) for a in sorted(anios_ordenados, reverse=True)]
    variables_ids = [str(v[0]) for v in VARIABLES_SINIM.values()]

    muns_payload = cli.post_json(
        "/datos_municipales/obtener_municipios.php",
        {
            "region": [REGION_SINIM_AYSEN],
            "municipio": ["T"],
            "limit": 20,
            "campo": "id_legal",
            "orden": "ASC",
            "pagina": 1,
        },
    )

    cab_payload = cli.post_json(
        "/datos_municipales/obtener_cabecera.php",
        {
            "area": ["1"],
            "subarea": list(SUBAREAS_SINIM),
            "variables": variables_ids,
            "periodos": periodos_ids,
            "region": [REGION_SINIM_AYSEN],
            "municipio": ["T"],
        },
    )

    paginas = cab_payload.get("paginas") or {}
    total_paginas = len(paginas)
    valores_paginas: list[dict[str, Any]] = []
    for num_pag in range(1, total_paginas + 1):
        val_pag = cli.post_json(
            "/datos_municipales/obtener_valores.php",
            {
                "variables": paginas,
                "municipios": muns_payload.get("textos") or [],
                "pagina": num_pag,
                "corrmon": 0,
            },
        )
        valores_paginas.append(val_pag)

    # Archivar insumos crudos con SHA-256
    archivos_manifest: list[dict[str, Any]] = []
    for nombre, obj in [
        ("municipios.json", muns_payload),
        ("cabecera.json", cab_payload),
        *[(f"valores-pagina-{i + 1}.json", p) for i, p in enumerate(valores_paginas)],
    ]:
        data_bytes = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        ruta = dir_insumos / nombre
        ruta.write_bytes(data_bytes)
        archivos_manifest.append(
            {"archivo": nombre, "bytes": len(data_bytes), "sha256": sha256(data_bytes).hexdigest()}
        )

    manifiesto = {
        "esquema": ESQUEMA_SINIM_HISTORICO,
        "extraido_en": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "anios": anios_ordenados,
        "region_sinim": REGION_SINIM_AYSEN,
        "total_paginas": total_paginas,
        "archivos": archivos_manifest,
    }
    (dir_insumos / "manifiesto.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    publicado = parsear_respuestas_sinim(muns_payload, valores_paginas, anios_ordenados)
    publicado["fuente_trazabilidad"] = {
        "institucion": "SUBDERE · Sistema Nacional de Información Municipal (SINIM)",
        "url_oficial": URL_SINIM_DATOS,
        "modo": "en_vivo",
        "extraido_en": manifiesto["extraido_en"],
        "directorio_insumos": str(dir_insumos),
        "total_paginas": total_paginas,
        "archivos_sha256": {a["archivo"]: a["sha256"] for a in archivos_manifest},
    }

    salida_path.parent.mkdir(parents=True, exist_ok=True)
    salida_path.write_text(json.dumps(publicado, ensure_ascii=False, indent=2), encoding="utf-8")
    return publicado


def reproducir_sinim_historico(
    dir_insumos: Path,
    *,
    salida_path: Path | None = _SALIDA_DEFECTO,
) -> dict[str, Any]:
    """Reproduce bit-a-bit el corte SINIM histórico sin tocar la red validando SHA-256."""
    manifiesto = json.loads((dir_insumos / "manifiesto.json").read_text(encoding="utf-8"))
    for entry in manifiesto["archivos"]:
        ruta = dir_insumos / entry["archivo"]
        real_hash = sha256(ruta.read_bytes()).hexdigest()
        if real_hash != entry["sha256"]:
            raise RuntimeError(f"Integridad SHA-256 alterada en {ruta.name}.")

    muns_payload = json.loads((dir_insumos / "municipios.json").read_text(encoding="utf-8"))
    total_paginas = int(manifiesto["total_paginas"])
    valores_paginas = [
        json.loads((dir_insumos / f"valores-pagina-{i + 1}.json").read_text(encoding="utf-8"))
        for i in range(total_paginas)
    ]
    publicado = parsear_respuestas_sinim(muns_payload, valores_paginas, manifiesto["anios"])
    publicado["fuente_trazabilidad"] = {
        "institucion": "SUBDERE · Sistema Nacional de Información Municipal (SINIM)",
        "url_oficial": URL_SINIM_DATOS,
        "modo": "reproducido_sin_red",
        "integridad_sha256_verificada": True,
        "extraido_en": manifiesto["extraido_en"],
        "directorio_insumos": str(dir_insumos),
        "total_paginas": total_paginas,
        "archivos_sha256": {a["archivo"]: a["sha256"] for a in manifiesto["archivos"]},
    }
    if salida_path is not None:
        salida_path.parent.mkdir(parents=True, exist_ok=True)
        salida_path.write_text(json.dumps(publicado, ensure_ascii=False, indent=2), encoding="utf-8")
    return publicado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extractor oficial histórico SINIM (2018–2025) para Aysén.")
    parser.add_argument("--reproducir", action="store_true", help="Reproduce desde insumos archivados sin red.")
    parser.add_argument("--insumos", type=Path, help="Directorio de insumos para --reproducir.")
    parser.add_argument("--salida", type=Path, default=_SALIDA_DEFECTO, help="Ruta JSON de salida.")
    args = parser.parse_args(argv)

    if args.reproducir:
        if not args.insumos:
            parser.error("--insumos es obligatorio con --reproducir.")
        pub = reproducir_sinim_historico(args.insumos, salida_path=args.salida)
    else:
        pub = extraer_sinim_historico_live(salida_path=args.salida)

    p = pub["piloto_aysen"]
    print(
        f"SINIM histórico OK | anios={pub['anios'][0]}..{pub['anios'][-1]} ({len(pub['anios'])} años × 10 comunas) | "
        f"Aysén {p['anio']}: Ini={p['presupuesto_inicial_millones']} Vig={p['presupuesto_vigente_millones']} "
        f"Dev={p['gasto_total_devengado_millones']} Corr={p['porcentaje_gasto_corriente_pct']}% "
        f"Inv={p['inversion_pct']}% GestInt={p['costo_admin_interno_pct']}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
