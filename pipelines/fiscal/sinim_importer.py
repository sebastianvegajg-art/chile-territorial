"""Importador oficial local de archivos SINIM (CSV/JSON) para las 10 comunas de Aysén.

Valida estrictamente esquema, códigos CUT de la Región de Aysén (Región 11),
rango de ejercicios (2013–2030), unicidad por ``(cut, anio)``, aritmética
exacta ``Decimal`` (>= 0, formato chileno o estándar) y normalización exacta a
``millones CLP``. Nunca persiste archivos inválidos ni inventa cifras.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from decimal import Context, Decimal, InvalidOperation, localcontext
from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path
import re
from typing import Any, Mapping
import unicodedata

PRECISION_DECIMAL = 34
CONTEXTO_DECIMAL = Context(prec=PRECISION_DECIMAL)
CERO = Decimal("0")
UNO = Decimal("1")
MIL = Decimal("1000")
MILLON = Decimal("1000000")

ANIO_MINIMO = 2013
ANIO_MAXIMO = 2030

COMUNAS_AYSEN: dict[str, str] = {
    "11101": "Coyhaique",
    "11102": "Lago Verde",
    "11201": "Aysén",
    "11202": "Cisnes",
    "11203": "Guaitecas",
    "11301": "Cochrane",
    "11302": "O’Higgins",
    "11303": "Tortel",
    "11401": "Chile Chico",
    "11402": "Río Ibáñez",
}

COLUMNAS_PLANTILLA: tuple[str, ...] = (
    "cut",
    "municipio",
    "anio",
    "unidad",
    "etapa",
    "ingresos_totales",
    "gasto_total_devengado",
    "gasto_corriente",
    "gasto_inversion",
    "fuente_archivo",
)

_ALIAS_COLUMNAS: dict[str, str] = {
    # cut
    "cut": "cut",
    "codigo_comuna": "cut",
    "cod_comuna": "cut",
    "codigo": "cut",
    "codigo_cut": "cut",
    "codigo_municipio": "cut",
    "cod_municipio": "cut",
    "id_comuna": "cut",
    # municipio
    "municipio": "municipio",
    "comuna": "municipio",
    "nombre_comuna": "municipio",
    "nombre_municipio": "municipio",
    "municipalidad": "municipio",
    # anio
    "anio": "anio",
    "ano": "anio",
    "ejercicio": "anio",
    "periodo": "anio",
    "year": "anio",
    # unidad
    "unidad": "unidad",
    "unidad_monetaria": "unidad",
    "escala": "unidad",
    # etapa
    "etapa": "etapa",
    "etapa_contable": "etapa",
    "base_contable": "etapa",
    # ingresos_totales
    "ingresos_totales": "ingresos_totales",
    "ingresos_municipales": "ingresos_totales",
    "ingreso_total": "ingresos_totales",
    "ingresos_devengados": "ingresos_totales",
    "ingresos_percibidos": "ingresos_totales",
    # gasto_total_devengado
    "gasto_total_devengado": "gasto_total_devengado",
    "gastos_totales": "gasto_total_devengado",
    "gasto_devengado": "gasto_total_devengado",
    "gastos_municipales": "gasto_total_devengado",
    "gasto_total": "gasto_total_devengado",
    "gastos_total_devengado": "gasto_total_devengado",
    # gasto_corriente
    "gasto_corriente": "gasto_corriente",
    "gastos_corrientes": "gasto_corriente",
    "gasto_corriente_devengado": "gasto_corriente",
    # gasto_inversion
    "gasto_inversion": "gasto_inversion",
    "gastos_inversion": "gasto_inversion",
    "inversion": "gasto_inversion",
    "inversion_municipal": "gasto_inversion",
    "gasto_capital": "gasto_inversion",
    "gasto_de_capital": "gasto_inversion",
    # fuente_archivo
    "fuente_archivo": "fuente_archivo",
    "fuente": "fuente_archivo",
    "archivo_origen": "fuente_archivo",
}

_UNIDADES_DIVISOR: dict[str, tuple[str, Decimal]] = {
    "miles clp": ("miles CLP", MIL),
    "m$": ("miles CLP", MIL),
    "miles $": ("miles CLP", MIL),
    "miles de pesos": ("miles CLP", MIL),
    "miles_clp": ("miles CLP", MIL),
    "m clp": ("miles CLP", MIL),
    "clp": ("CLP", MILLON),
    "$": ("CLP", MILLON),
    "pesos": ("CLP", MILLON),
    "pesos clp": ("CLP", MILLON),
    "millones clp": ("millones CLP", UNO),
    "mm$": ("millones CLP", UNO),
    "millones $": ("millones CLP", UNO),
    "millones de pesos": ("millones CLP", UNO),
    "millones_clp": ("millones CLP", UNO),
    "mm clp": ("millones CLP", UNO),
}

_ETAPAS_CANONICAS: dict[str, str] = {
    "inicial": "inicial",
    "vigente": "vigente",
    "compromiso": "compromiso",
    "devengo": "devengo",
    "devengado": "devengo",
    "pago": "pago",
    "pagado": "pago",
    "ejecutado": "ejecutado",
    "ejecucion": "ejecutado",
}

_PATRON_MILES_PUNTO = re.compile(r"^[1-9]\d{0,2}(?:\.\d{3})+$")
_PATRON_MILES_COMA = re.compile(r"^[1-9]\d{0,2}(?:,\d{3}){2,}$")
_PATRON_DEC_CL = re.compile(r"^\d{1,3}(?:\.\d{3})+,\d+$")
_PATRON_DEC_US = re.compile(r"^\d{1,3}(?:,\d{3})+\.\d+$")
_PATRON_NUMERO_SIMPLE = re.compile(r"^\d+(?:\.\d+)?$")
_VALORES_OPCIONALES_VACIOS = frozenset({"", "-", "--", "n/a", "na", "nd", "s/i", "sd", "null", "none"})


def _normalizar_cabecera(nombre: str) -> str:
    """Normaliza una cabecera CSV/JSON a identificador ASCII minúscula con guion bajo."""
    texto = unicodedata.normalize("NFKD", str(nombre).lstrip("\ufeff"))
    sin_tildes = "".join(ch for ch in texto if not unicodedata.combining(ch))
    limpio = re.sub(r"[^a-zA-Z0-9]+", "_", sin_tildes.strip().lower()).strip("_")
    return limpio


def _normalizar_texto_clave(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", valor)
    sin_tildes = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


def _formatear_decimal(valor: Decimal) -> str:
    with localcontext(CONTEXTO_DECIMAL):
        if valor == CERO:
            return "0"
        texto = format(valor.normalize(), "f")
        if "." in texto:
            texto = texto.rstrip("0").rstrip(".")
        return "0" if texto in {"", "-0"} else texto


def plantilla_sinim_csv() -> str:
    """Genera una plantilla CSV oficial SINIM solo con cabeceras estándar (sin cifras inventadas)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNAS_PLANTILLA)
    return buffer.getvalue()


def _decodificar_texto(contenido: bytes) -> str:
    """Decodifica UTF-8-SIG o ISO-8859-1/Windows-1252."""
    try:
        return contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            return contenido.decode("cp1252")
        except UnicodeDecodeError:
            return contenido.decode("iso-8859-1")


def _detectar_delimitador_csv(texto: str) -> str:
    """Detecta delimitador ',' o ';' analizando la cabecera."""
    primera_linea = ""
    for linea in texto.splitlines():
        if linea.strip():
            primera_linea = linea
            break
    cuenta_punto_coma = primera_linea.count(";")
    cuenta_coma = primera_linea.count(",")
    return ";" if cuenta_punto_coma > cuenta_coma else ","


def _normalizar_fila_aliases(fila: Mapping[str, Any]) -> dict[str, Any]:
    """Mapea alias de columnas SINIM hacia nombres canónicos."""
    normalizada: dict[str, Any] = {}
    for clave, valor in fila.items():
        if clave is None:
            continue
        clave_norm = _normalizar_cabecera(str(clave))
        canonica = _ALIAS_COLUMNAS.get(clave_norm)
        if canonica is not None:
            # Si ya existe valor no vacío en la clave canónica, no sobreescribir con vacío.
            if canonica not in normalizada or (
                normalizada[canonica] in (None, "") and valor not in (None, "")
            ):
                normalizada[canonica] = valor
    return normalizada


def _parsear_anio(raw: Any) -> int | None:
    if raw is None or isinstance(raw, bool) or isinstance(raw, float):
        return None
    if isinstance(raw, int):
        return raw if ANIO_MINIMO <= raw <= ANIO_MAXIMO else None
    texto = str(raw).strip()
    if not re.fullmatch(r"\d{4}", texto):
        return None
    anio = int(texto)
    return anio if ANIO_MINIMO <= anio <= ANIO_MAXIMO else None


def _parsear_unidad(raw: Any) -> tuple[str, Decimal] | None:
    if raw is None or str(raw).strip() == "":
        return ("miles CLP", MIL)
    clave = _normalizar_texto_clave(str(raw))
    return _UNIDADES_DIVISOR.get(clave)


def _parsear_etapa(raw: Any) -> str | None:
    if raw is None or str(raw).strip() == "":
        return "devengo"
    clave = _normalizar_texto_clave(str(raw))
    return _ETAPAS_CANONICAS.get(clave)


def _parsear_monto_sinim(raw: Any, *, obligatorio: bool) -> tuple[Decimal | None, str | None]:
    """Parsea montos SINIM a ``Decimal`` finito >= 0.

    Retorna ``(valor_decimal_o_none, mensaje_error_o_none)``.
    """
    if raw is None:
        if obligatorio:
            return None, "monto obligatorio faltante"
        return None, None
    if isinstance(raw, bool):
        return None, f"tipo booleano inválido ({raw!r})"
    if isinstance(raw, Decimal):
        if not raw.is_finite():
            return None, f"monto no finito ({raw!r})"
        if raw < CERO:
            return None, f"monto negativo no permitido ({raw})"
        return raw, None
    if isinstance(raw, int):
        valor = Decimal(raw)
        if valor < CERO:
            return None, f"monto negativo no permitido ({raw})"
        return valor, None
    if isinstance(raw, float):
        if not math.isfinite(raw):
            return None, f"monto no finito ({raw!r})"
        valor = Decimal(str(raw))
        if valor < CERO:
            return None, f"monto negativo no permitido ({raw})"
        return valor, None

    texto = str(raw).replace("\xa0", " ").replace("\u2009", " ").strip()
    if texto.lower() in _VALORES_OPCIONALES_VACIOS:
        if obligatorio:
            return None, f"monto obligatorio vacío o ausente ({raw!r})"
        return None, None

    # Limpieza opcional de prefijos monetarios
    texto = re.sub(r"^(?:mm?\$|clp|\$)\s*", "", texto, flags=re.IGNORECASE).strip()
    texto = re.sub(r"\s+", "", texto)

    if texto.startswith("-") or (texto.startswith("(") and texto.endswith(")")):
        return None, f"monto negativo no permitido ({raw!r})"
    if texto.startswith("+"):
        texto = texto[1:]

    tiene_punto = "." in texto
    tiene_coma = "," in texto
    normalizado: str | None = None

    if tiene_punto and tiene_coma:
        if _PATRON_DEC_CL.match(texto):
            normalizado = texto.replace(".", "").replace(",", ".")
        elif _PATRON_DEC_US.match(texto):
            normalizado = texto.replace(",", "")
        else:
            return None, f"formato numérico ambiguo o inválido ({raw!r})"
    elif tiene_punto:
        if _PATRON_MILES_PUNTO.match(texto):
            normalizado = texto.replace(".", "")
        elif _PATRON_NUMERO_SIMPLE.match(texto):
            normalizado = texto
        else:
            return None, f"formato numérico con puntos inválido ({raw!r})"
    elif tiene_coma:
        if _PATRON_MILES_COMA.match(texto):
            normalizado = texto.replace(",", "")
        elif texto.count(",") == 1 and re.fullmatch(r"\d+,\d+", texto):
            normalizado = texto.replace(",", ".")
        else:
            return None, f"formato numérico con comas inválido ({raw!r})"
    else:
        if re.fullmatch(r"\d+", texto):
            normalizado = texto
        else:
            return None, f"valor numérico inválido ({raw!r})"

    with localcontext(CONTEXTO_DECIMAL):
        try:
            valor = Decimal(normalizado)
        except InvalidOperation:
            return None, f"valor numérico inválido ({raw!r})"

    if not valor.is_finite():
        return None, f"monto no finito ({raw!r})"
    if valor < CERO:
        return None, f"monto negativo no permitido ({raw!r})"
    return valor, None


def _extraer_filas_brutas(
    texto: str,
    nombre_archivo: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Extrae filas como diccionarios desde CSV (',' o ';') o JSON."""
    errores: list[str] = []
    texto_strip = texto.strip()
    if not texto_strip:
        return [], ["El archivo está vacío."]

    es_json = nombre_archivo.lower().endswith(".json") or texto_strip.startswith(("{", "["))
    if es_json:
        try:
            data = json.loads(texto_strip)
        except json.JSONDecodeError as exc:
            return [], [f"JSON inválido en '{nombre_archivo}': {exc.msg} (línea {exc.lineno})."]
        if isinstance(data, list):
            registros = data
        elif isinstance(data, dict) and isinstance(data.get("registros"), list):
            registros = data["registros"]
        else:
            return [], [
                "Estructura JSON no soportada: se espera una lista de objetos o {'registros': [...]}."
            ]
        filas: list[dict[str, Any]] = []
        for idx, item in enumerate(registros, start=1):
            if not isinstance(item, Mapping):
                errores.append(f"Registro {idx}: se esperaba un objeto JSON por comuna.")
                continue
            filas.append(dict(item))
        return filas, errores

    delimitador = _detectar_delimitador_csv(texto)
    reader = csv.DictReader(io.StringIO(texto), delimiter=delimitador)
    if not reader.fieldnames:
        return [], ["El archivo CSV no contiene fila de cabeceras."]

    filas_csv: list[dict[str, Any]] = []
    for fila in reader:
        # Ignorar filas completamente vacías
        if all((v is None or str(v).strip() == "") for k, v in fila.items() if k is not None):
            continue
        filas_csv.append(dict(fila))
    return filas_csv, errores


def _respuesta_invalida(
    errores: list[str],
    nombre_archivo: str,
    huella_sha256: str,
    actualizado_en: str,
) -> dict[str, Any]:
    return {
        "valido": False,
        "errores": errores,
        "resumen": None,
        "comunas": [],
        "fuente_trazabilidad": {
            "institucion": "SINIM · SUBDERE (importación oficial local)",
            "archivo": nombre_archivo,
            "sha256": huella_sha256,
            "actualizado_en": actualizado_en,
            "etapa": None,
            "unidad_salida": "millones CLP",
            "moneda": "CLP",
        },
    }


def importar_sinim_bytes(contenido: bytes, nombre_archivo: str) -> dict[str, Any]:
    """Importa y valida un archivo oficial SINIM (CSV o JSON) para comunas de Aysén.

    Retorna un diccionario con ``valido: bool``, ``errores``, ``resumen``,
    ``comunas`` y ``fuente_trazabilidad`` (con SHA-256 del insumo original).
    """
    if not isinstance(contenido, (bytes, bytearray)):
        raise TypeError("contenido debe ser bytes.")
    raw_bytes = bytes(contenido)
    huella_sha256 = sha256(raw_bytes).hexdigest()
    actualizado_en = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )

    if not raw_bytes.strip():
        return _respuesta_invalida(
            ["El archivo importado está vacío."],
            nombre_archivo,
            huella_sha256,
            actualizado_en,
        )

    texto = _decodificar_texto(raw_bytes)
    filas_brutas, errores = _extraer_filas_brutas(texto, nombre_archivo)
    if errores:
        return _respuesta_invalida(errores, nombre_archivo, huella_sha256, actualizado_en)
    if not filas_brutas:
        return _respuesta_invalida(
            ["El archivo no contiene registros de comunas."],
            nombre_archivo,
            huella_sha256,
            actualizado_en,
        )

    comunas_procesadas: list[dict[str, Any]] = []
    claves_vistas: set[tuple[str, int]] = set()
    anios_vistos: set[int] = set()
    etapas_vistas: set[str] = set()

    total_ingresos_mm = CERO
    total_gasto_dev_mm = CERO
    total_gasto_corr_mm = CERO
    total_inversion_mm = CERO
    con_gasto_corriente = 0
    con_inversion = 0

    with localcontext(CONTEXTO_DECIMAL):
        for idx, fila_raw in enumerate(filas_brutas, start=1):
            fila = _normalizar_fila_aliases(fila_raw)

            # 1. Validar CUT en Región 11 (Aysén)
            cut_raw = fila.get("cut")
            cut = "" if cut_raw is None else str(cut_raw).strip()
            if cut not in COMUNAS_AYSEN:
                errores.append(
                    f"Fila {idx}: CUT '{cut}' no pertenece a las 10 comunas oficiales "
                    "de la Región de Aysén (Región 11)."
                )

            # 2. Validar año 2013..2030
            anio = _parsear_anio(fila.get("anio"))
            if anio is None:
                errores.append(
                    f"Fila {idx}: año inválido '{fila.get('anio')}' "
                    f"(se requiere entero entre {ANIO_MINIMO} y {ANIO_MAXIMO})."
                )

            # 3. Unicidad por (cut, anio)
            if cut in COMUNAS_AYSEN and anio is not None:
                clave = (cut, anio)
                if clave in claves_vistas:
                    errores.append(
                        f"Fila {idx}: CUT '{cut}' ({COMUNAS_AYSEN[cut]}) duplicado "
                        f"para el ejercicio {anio}."
                    )
                else:
                    claves_vistas.add(clave)
                anios_vistos.add(anio)

            # 4. Unidad monetaria
            unidad_info = _parsear_unidad(fila.get("unidad"))
            if unidad_info is None:
                errores.append(
                    f"Fila {idx}: unidad monetaria no reconocida '{fila.get('unidad')}' "
                    "(válidas: 'miles CLP'/'M$', 'CLP'/'$', 'millones CLP')."
                )

            # 5. Etapa contable
            etapa = _parsear_etapa(fila.get("etapa"))
            if etapa is None:
                errores.append(
                    f"Fila {idx}: etapa contable no reconocida '{fila.get('etapa')}'."
                )
            else:
                etapas_vistas.add(etapa)

            # 6. Montos Decimal finitos >= 0
            ingresos_raw, err_ing = _parsear_monto_sinim(
                fila.get("ingresos_totales"), obligatorio=True
            )
            if err_ing:
                errores.append(f"Fila {idx} (ingresos_totales): {err_ing}.")

            gasto_dev_raw, err_gasto = _parsear_monto_sinim(
                fila.get("gasto_total_devengado"), obligatorio=True
            )
            if err_gasto:
                errores.append(f"Fila {idx} (gasto_total_devengado): {err_gasto}.")

            gasto_corr_raw, err_corr = _parsear_monto_sinim(
                fila.get("gasto_corriente"), obligatorio=False
            )
            if err_corr:
                errores.append(f"Fila {idx} (gasto_corriente): {err_corr}.")

            gasto_inv_raw, err_inv = _parsear_monto_sinim(
                fila.get("gasto_inversion"), obligatorio=False
            )
            if err_inv:
                errores.append(f"Fila {idx} (gasto_inversion): {err_inv}.")

            if (
                cut not in COMUNAS_AYSEN
                or anio is None
                or unidad_info is None
                or etapa is None
                or ingresos_raw is None
                or gasto_dev_raw is None
                or err_corr is not None
                or err_inv is not None
            ):
                continue

            unidad_canonica, divisor = unidad_info
            ingresos_mm = ingresos_raw / divisor
            gasto_dev_mm = gasto_dev_raw / divisor
            gasto_corr_mm = (gasto_corr_raw / divisor) if gasto_corr_raw is not None else None
            gasto_inv_mm = (gasto_inv_raw / divisor) if gasto_inv_raw is not None else None

            total_ingresos_mm += ingresos_mm
            total_gasto_dev_mm += gasto_dev_mm
            if gasto_corr_mm is not None:
                total_gasto_corr_mm += gasto_corr_mm
                con_gasto_corriente += 1
            if gasto_inv_mm is not None:
                total_inversion_mm += gasto_inv_mm
                con_inversion += 1

            municipio_informado = str(fila.get("municipio") or "").strip() or COMUNAS_AYSEN[cut]
            fuente_fila = str(fila.get("fuente_archivo") or "").strip() or nombre_archivo

            comunas_procesadas.append(
                {
                    "cut": cut,
                    "municipio": COMUNAS_AYSEN[cut],
                    "municipio_informado": municipio_informado,
                    "anio": anio,
                    "unidad_origen": unidad_canonica,
                    "etapa": etapa,
                    "ingresos_totales_millones": _formatear_decimal(ingresos_mm),
                    "gasto_total_devengado_millones": _formatear_decimal(gasto_dev_mm),
                    "gasto_corriente_millones": (
                        _formatear_decimal(gasto_corr_mm) if gasto_corr_mm is not None else None
                    ),
                    "gasto_inversion_millones": (
                        _formatear_decimal(gasto_inv_mm) if gasto_inv_mm is not None else None
                    ),
                    "fuente_archivo": fuente_fila,
                }
            )

    if len(anios_vistos) > 1:
        errores.append(
            "No se permite mezclar distintos ejercicios fiscales en una misma importación: "
            f"{sorted(anios_vistos)}."
        )
    if len(etapas_vistas) > 1:
        errores.append(
            "No se permite mezclar etapas contables incompatibles en una misma importación: "
            f"{sorted(etapas_vistas)}."
        )

    if errores:
        return _respuesta_invalida(errores, nombre_archivo, huella_sha256, actualizado_en)

    comunas_procesadas.sort(key=lambda item: item["cut"])
    cuts_cargados = {item["cut"] for item in comunas_procesadas}
    comunas_faltantes = [
        {"cut": cut, "municipio": COMUNAS_AYSEN[cut]}
        for cut in sorted(COMUNAS_AYSEN)
        if cut not in cuts_cargados
    ]
    anio_unico = next(iter(anios_vistos))
    etapa_unica = next(iter(etapas_vistas))

    return {
        "valido": True,
        "errores": [],
        "resumen": {
            "anio": anio_unico,
            "comunas_cargadas": len(comunas_procesadas),
            "comunas_esperadas": len(COMUNAS_AYSEN),
            "comunas_faltantes": comunas_faltantes,
            "total_ingresos_millones": _formatear_decimal(total_ingresos_mm),
            "total_gasto_devengado_millones": _formatear_decimal(total_gasto_dev_mm),
            "total_gasto_corriente_millones": (
                _formatear_decimal(total_gasto_corr_mm) if con_gasto_corriente > 0 else None
            ),
            "total_inversion_millones": (
                _formatear_decimal(total_inversion_mm) if con_inversion > 0 else None
            ),
        },
        "comunas": comunas_procesadas,
        "fuente_trazabilidad": {
            "institucion": "SINIM · SUBDERE (importación oficial local)",
            "archivo": nombre_archivo,
            "sha256": huella_sha256,
            "actualizado_en": actualizado_en,
            "etapa": etapa_unica,
            "unidad_salida": "millones CLP",
            "moneda": "CLP",
        },
    }


def guardar_importacion_sinim(resultado: dict[str, Any], ruta: Path) -> Path:
    """Persiste de forma atómica una importación SINIM válida en formato JSON."""
    if not isinstance(resultado, dict) or resultado.get("valido") is not True:
        raise ValueError(
            "No se permite guardar una importación SINIM inválida o con errores de validación."
        )
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(destino.suffix + ".tmp")
    temporal.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporal, destino)
    return destino


def cargar_importacion_sinim(ruta: Path) -> dict[str, Any] | None:
    """Carga una importación SINIM persistida en JSON; retorna ``None`` si no existe."""
    origen = Path(ruta)
    if not origen.exists():
        return None
    try:
        datos = json.loads(origen.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Archivo de importación SINIM corrupto: {origen}") from exc
    if not isinstance(datos, dict) or datos.get("valido") is not True:
        raise ValueError(f"El archivo '{origen}' no contiene una importación SINIM válida.")
    return datos
