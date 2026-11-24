"""Extractor oficial autenticado de la API REST del Banco Central de Chile (BDE).

Soporta:
- Autenticación mediante ``BCCH_API_TOKEN`` o el par ``BCCH_API_USER`` +
  ``BCCH_API_PASS``, desde variables de entorno o un archivo ``.env`` local
  opcional (``--env .env``), sin dependencias externas.
- Descubrimiento desde catálogo (``SearchSeries``, ``frequency=ANNUAL``) de:
  1. Las 34 series anuales de PIB total (Chile + 16 regiones, real y nominal,
     referencia 2018 / ``HIST18``).
  2. El inventario reproducible de series sectoriales regionales (referencia de
     416 series: 16 regiones × 13 actividades × 2 valoraciones).
- Extracción de las 34 series totales con ``GetSeries`` desde ``2012-01-01``
  hasta la fecha actual, normalización exacta con ``Decimal`` al contrato
  ``contracts/pib-datos.schema.json`` (``millones CLP``), resguardo de insumos
  originales con manifiesto SHA-256 en ``data/raw/bde-api-*/`` y publicación en
  ``data/published/pib-bde-api.json``.
- Modo ``--inventario-sectorial`` para emitir ``data/published/catalogo-sectorial-bde.json``.
- Modo ``--reproducir`` para reconstrucción bit-a-bit sin red ni credenciales.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from time import sleep
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import quote, quote_plus, urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

_RAIZ_REPO = Path(__file__).resolve().parents[2]
if str(_RAIZ_REPO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_REPO))

from analytics.territorial.pib import crecimiento, participacion  # noqa: E402


ENDPOINT = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
MAX_BYTES = 50 * 1024 * 1024
FUENTE = "BCCh-BDE"
UNIDAD_NIVEL = "millones CLP"
ANIO_REFERENCIA_REAL = 2018
REFERENCIA_SECTORIAL_TOTAL = 416
REFERENCIA_SECTORIAL_REGIONES = 16
REFERENCIA_SECTORIAL_ACTIVIDADES = 13
REFERENCIA_SECTORIAL_VALORACIONES = 2

TERRITORIOS = ("CL", *(f"{codigo:02d}" for codigo in range(1, 17)))
REGIONES = tuple(f"{codigo:02d}" for codigo in range(1, 17))
VALORACIONES = ("real", "nominal")

NOMBRES_TERRITORIOS = {
    "CL": "Chile",
    "01": "Tarapacá",
    "02": "Antofagasta",
    "03": "Atacama",
    "04": "Coquimbo",
    "05": "Valparaíso",
    "06": "Libertador General Bernardo O'Higgins",
    "07": "Maule",
    "08": "Biobío",
    "09": "La Araucanía",
    "10": "Los Lagos",
    "11": "Aysén del General Carlos Ibáñez del Campo",
    "12": "Magallanes y de la Antártica Chilena",
    "13": "Metropolitana de Santiago",
    "14": "Los Ríos",
    "15": "Arica y Parinacota",
    "16": "Ñuble",
}

_CODIGOS_NACIONALES_CANDIDATOS = {
    "real": (
        "F032.PIB.FLU.R.CLP.HIST18.Z.Z.0.A",
        "F032.PIB.FLU.R.CLP.2018.Z.Z.0.A",
    ),
    "nominal": (
        "F032.PIB.FLU.N.CLP.HIST18.Z.Z.0.A",
        "F032.PIB.FLU.N.CLP.2018.Z.Z.0.A",
    ),
}

_PATRON_REGIONAL_TOTAL = re.compile(
    r"^F035\.PIB\.FLU\.(R|N)\.CLP\.2018\.Z\.Z\.Z\.(0[1-9]|1[0-6])\.0\.A$"
)
_PATRON_REGIONAL_SECTORIAL = re.compile(
    r"^F035\.PIB\.FLU\.(R|N)\.CLP\.2018\.([^.]+)\.([^.]+)\.([^.]+)\.(0[1-9]|1[0-6])\.0\.A$"
)
_ESTADOS_FALTANTES_BDE = frozenset({"ND", "SD", "NA", "N/A"})
_CLAVE_ENV = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class BdeApiError(Exception):
    """Error seguro para mostrar sin revelar credenciales, URLs ni cuerpos."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class Credenciales:
    """Credenciales de consulta BDE con representación siempre redactada."""

    modo: str
    token: str | None = None
    usuario: str | None = None
    clave: str | None = None

    def __post_init__(self) -> None:
        if self.modo == "token":
            if not self.token:
                raise BdeApiError("Credencial BCCH_API_TOKEN vacía.")
        elif self.modo == "user_pass":
            if not self.usuario or not self.clave:
                raise BdeApiError("Se requieren BCCH_API_USER y BCCH_API_PASS.")
        else:
            raise BdeApiError("Modo de autenticación BDE no reconocido.")

    def __repr__(self) -> str:
        return f"Credenciales(modo={self.modo!r})"

    def __str__(self) -> str:
        return self.__repr__()

    def parametros_consulta(self) -> dict[str, str]:
        if self.modo == "token":
            assert self.token is not None
            return {"token": self.token}
        assert self.usuario is not None and self.clave is not None
        return {"user": self.usuario, "pass": self.clave}

    def secretos(self) -> tuple[str, ...]:
        if self.modo == "token":
            assert self.token is not None
            return (self.token,)
        assert self.usuario is not None and self.clave is not None
        return (self.usuario, self.clave)


@dataclass(frozen=True)
class SerieCatalogo:
    """Metadatos normalizados de una serie descubierta en ``SearchSeries``."""

    codigo: str
    territorio: str
    valoracion: str
    titulo_es: str
    titulo_en: str | None
    frecuencia: str
    unidad_titulo: str | None
    primera_observacion: str | None
    ultima_observacion: str | None
    actualizada_en: str | None
    creada_en: str | None
    actividad_codigo: str | None = None


def _normalizar_texto(texto: str) -> str:
    sin_tildes = "".join(
        ch for ch in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(ch)
    )
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


def _extraer_unidad_titulo(titulo: str) -> str | None:
    coincidencias = re.findall(r"\(([^()]+)\)", titulo)
    for candidato in reversed(coincidencias):
        limpio = candidato.strip()
        if limpio:
            return limpio
    return None


def _factor_a_millones(*titulos: str | None) -> tuple[Decimal, str]:
    for titulo in titulos:
        if not titulo:
            continue
        norm = _normalizar_texto(titulo)
        if "miles de millones de pesos" in norm:
            return Decimal("1000"), _extraer_unidad_titulo(titulo) or "miles de millones de pesos"
        if "millones de pesos" in norm:
            return Decimal("1"), _extraer_unidad_titulo(titulo) or "millones de pesos"
    raise BdeApiError(
        "No se pudo verificar la unidad monetaria (miles de millones o millones de pesos) en los metadatos."
    )


def _validar_coherencia_valoracion(codigo: str, valoracion: str, titulo: str) -> None:
    norm = _normalizar_texto(titulo)
    if valoracion == "real" and "precios corrientes" in norm and "encadenad" not in norm:
        raise BdeApiError(f"{codigo}: título inconsistente con valoración real.")
    if valoracion == "nominal" and ("encadenad" in norm or "volumen a precios" in norm):
        raise BdeApiError(f"{codigo}: título inconsistente con valoración nominal.")


def _parsear_fecha_corte(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    texto = raw.strip()
    if not texto:
        return None
    candidatos = (texto, texto[:10])
    for candidato in candidatos:
        for formato in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(candidato, formato).date().isoformat()
            except ValueError:
                continue
    return None


def _parsear_fecha_observacion(raw: object) -> date:
    if not isinstance(raw, str):
        raise ValueError("Fecha no textual")
    texto = raw.strip()
    for formato in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ValueError("Formato de fecha de observación inválido")


def formatear_decimal(valor: Decimal) -> str:
    """Formatea un ``Decimal`` finito sin notación científica y con precisión exacta."""
    if not valor.is_finite():
        raise BdeApiError("Valor decimal no finito.")
    if valor == 0:
        return "0"
    texto = format(valor, "f")
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto


def _representaciones_secretos(credenciales: Credenciales) -> tuple[str, ...]:
    representaciones: set[str] = set()
    for secreto in credenciales.secretos():
        for forma in (secreto, quote(secreto, safe=""), quote_plus(secreto)):
            if forma:
                representaciones.add(forma)
    return tuple(sorted(representaciones, key=len, reverse=True))


def contiene_credencial(contenido: bytes | str, credenciales: Credenciales) -> bool:
    """Retorna ``True`` si algún secreto aparece en el texto o bytes dados."""
    if isinstance(contenido, bytes):
        for rep in _representaciones_secretos(credenciales):
            if rep.encode("utf-8") in contenido:
                return True
        return False
    for rep in _representaciones_secretos(credenciales):
        if rep in contenido:
            return True
    return False


def sanear_mensaje(texto: str, credenciales: Credenciales | None) -> str:
    """Elimina cualquier rastro de secretos o parámetros de consulta en un mensaje."""
    limpio = re.sub(r"(token|user|pass)=[^&\s\"']+", r"\1=[REDACTED]", texto, flags=re.IGNORECASE)
    if credenciales is not None:
        for rep in _representaciones_secretos(credenciales):
            limpio = limpio.replace(rep, "[REDACTED]")
    return limpio


def cargar_archivo_env(ruta: Path) -> dict[str, str]:
    """Lee un archivo ``.env`` simple sin dependencias externas ni ejecución de código."""
    if not ruta.is_file():
        raise BdeApiError(f"No se encontró el archivo de entorno local: {ruta.name}.")
    try:
        lineas = ruta.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        raise BdeApiError("No se pudo leer el archivo de entorno local.") from None

    valores: dict[str, str] = {}
    for numero, linea in enumerate(lineas, start=1):
        cruda = linea.strip()
        if not cruda or cruda.startswith("#"):
            continue
        if cruda.startswith("export ") and "=" in cruda:
            cruda = cruda[len("export ") :].strip()
        if "=" not in cruda:
            raise BdeApiError(f"Formato inválido en archivo .env (línea {numero}).")
        clave, valor = cruda.split("=", 1)
        clave = clave.strip()
        if not _CLAVE_ENV.fullmatch(clave):
            raise BdeApiError(f"Nombre de variable inválido en archivo .env (línea {numero}).")
        valor = valor.strip()
        if valor and valor[0] in {'"', "'"}:
            comilla = valor[0]
            chars: list[str] = []
            idx = 1
            cerrado = False
            while idx < len(valor):
                ch = valor[idx]
                if comilla == '"' and ch == "\\" and idx + 1 < len(valor):
                    siguiente = valor[idx + 1]
                    if siguiente in {'"', "\\"}:
                        chars.append(siguiente)
                        idx += 2
                        continue
                if ch == comilla:
                    cerrado = True
                    idx += 1
                    break
                chars.append(ch)
                idx += 1
            resto = valor[idx:].strip()
            if not cerrado or (resto and not resto.startswith("#")):
                raise BdeApiError(f"Comillas inválidas en archivo .env (línea {numero}).")
            valor = "".join(chars)
        else:
            # Permite comentarios inline precedidos por espacio: KEY=val # comentario
            partes = re.split(r"\s+#", valor, maxsplit=1)
            valor = partes[0].strip()
        valores[clave] = valor
    return valores


def resolver_credenciales(
    environ: dict[str, str] | os._Environ[str] | None = None,
    env_path: Path | None = None,
) -> Credenciales:
    """Resuelve ``BCCH_API_TOKEN`` o ``BCCH_API_USER`` + ``BCCH_API_PASS``.

    Las variables del entorno del proceso tienen precedencia sobre ``env_path``
    cuando ambas están presentes y no vacías.
    """
    combinado: dict[str, str] = {}
    if env_path is not None:
        combinado.update(cargar_archivo_env(env_path))
    fuente_env = os.environ if environ is None else environ
    for clave in ("BCCH_API_TOKEN", "BCCH_API_USER", "BCCH_API_PASS"):
        valor = str(fuente_env.get(clave, "")).strip()
        if valor:
            combinado[clave] = valor

    token = combinado.get("BCCH_API_TOKEN", "").strip()
    usuario = combinado.get("BCCH_API_USER", "").strip()
    clave = combinado.get("BCCH_API_PASS", "").strip()

    if token:
        return Credenciales(modo="token", token=token)
    if usuario or clave:
        if not usuario or not clave:
            raise BdeApiError(
                "Autenticación incompleta: configure tanto BCCH_API_USER como BCCH_API_PASS."
            )
        return Credenciales(modo="user_pass", usuario=usuario, clave=clave)
    raise BdeApiError(
        "Faltan credenciales BDE: configure BCCH_API_TOKEN o BCCH_API_USER + BCCH_API_PASS "
        "(en el entorno o mediante --env .env)."
    )


def descargar(
    credenciales: Credenciales,
    funcion: str,
    timeout: int = 30,
    **params: str,
) -> tuple[bytes, dict]:
    """Ejecuta una consulta autenticada de solo lectura en la API REST BDE."""
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    consulta = urlencode({**credenciales.parametros_consulta(), "function": funcion, **params})
    peticion = Request(f"{ENDPOINT}?{consulta}", headers={"Accept": "application/json"})

    body: bytes | None = None
    for intento in range(3):
        try:
            with opener.open(peticion, timeout=timeout) as respuesta:
                body = respuesta.read(MAX_BYTES + 1)
            break
        except HTTPError as error:
            codigo_http = error.code
            error.close()
            transitorio = codigo_http in (429, 500, 502, 503, 504)
            if not transitorio or intento == 2:
                raise BdeApiError(f"{funcion}: HTTP {codigo_http}.") from None
        except (URLError, OSError):
            if intento == 2:
                raise BdeApiError(f"{funcion}: error de conexión.") from None
        sleep(2 ** (intento + 1))

    assert body is not None
    if len(body) > MAX_BYTES:
        raise BdeApiError(f"{funcion}: respuesta supera el tamaño permitido.")
    try:
        payload = json.loads(body.decode("utf-8"), parse_float=str)
    except (ValueError, UnicodeError):
        raise BdeApiError(f"{funcion}: respuesta JSON inválida.") from None

    texto_serializado = json.dumps(payload, ensure_ascii=False)
    if contiene_credencial(body, credenciales) or contiene_credencial(texto_serializado, credenciales):
        raise BdeApiError(f"{funcion}: respuesta con credencial reflejada.")

    if not isinstance(payload, dict) or payload.get("Codigo") != 0:
        codigo_bde = payload.get("Codigo") if isinstance(payload, dict) else "desconocido"
        raise BdeApiError(f"{funcion}: la BDE rechazó la consulta (Codigo={codigo_bde}).")
    return body, payload


def parsear_catalogo_anual(payload: dict) -> dict[str, dict]:
    """Valida e indexa las entradas anuales de ``SearchSeries`` por ``seriesId``."""
    filas = payload.get("SeriesInfos")
    if not isinstance(filas, list) or not filas:
        raise BdeApiError("SearchSeries: catálogo anual vacío o inválido.")
    entradas: dict[str, dict] = {}
    for fila in filas:
        if not isinstance(fila, dict):
            raise BdeApiError("SearchSeries: fila de catálogo inválida.")
        codigo = fila.get("seriesId")
        if not isinstance(codigo, str) or not codigo.strip() or codigo in entradas:
            raise BdeApiError("SearchSeries: código ausente o duplicado.")
        if fila.get("frequencyCode") != "ANNUAL":
            raise BdeApiError(f"SearchSeries: frecuencia no anual para {codigo}.")
        titulo = fila.get("spanishTitle")
        if not isinstance(titulo, str) or not titulo.strip():
            raise BdeApiError(f"SearchSeries: título ausente para {codigo}.")
        entradas[codigo] = fila
    return entradas


def _construir_serie_catalogo(
    fila: dict,
    territorio: str,
    valoracion: str,
    actividad_codigo: str | None = None,
) -> SerieCatalogo:
    titulo_es = str(fila["spanishTitle"]).strip()
    titulo_en = fila.get("englishTitle")
    if isinstance(titulo_en, str):
        titulo_en = titulo_en.strip() or None
    else:
        titulo_en = None
    return SerieCatalogo(
        codigo=str(fila["seriesId"]).strip(),
        territorio=territorio,
        valoracion=valoracion,
        titulo_es=titulo_es,
        titulo_en=titulo_en,
        frecuencia=str(fila["frequencyCode"]).strip(),
        unidad_titulo=_extraer_unidad_titulo(titulo_es),
        primera_observacion=fila.get("firstObservation") if isinstance(fila.get("firstObservation"), str) else None,
        ultima_observacion=fila.get("lastObservation") if isinstance(fila.get("lastObservation"), str) else None,
        actualizada_en=fila.get("updatedAt") if isinstance(fila.get("updatedAt"), str) else None,
        creada_en=fila.get("createdAt") if isinstance(fila.get("createdAt"), str) else None,
        actividad_codigo=actividad_codigo,
    )


def descubrir_series_totales(catalogo: dict[str, dict]) -> dict[tuple[str, str], SerieCatalogo]:
    """Descubre y valida las 34 series anuales de PIB total desde el catálogo.

    Retorna un diccionario indexado por ``(territorio, valoracion)`` para
    ``CL`` y las 16 regiones (``01``..``16``) en valoraciones ``real`` y
    ``nominal``.
    """
    descubiertas: dict[tuple[str, str], SerieCatalogo] = {}

    for valoracion in VALORACIONES:
        elegida: dict | None = None
        for candidato in _CODIGOS_NACIONALES_CANDIDATOS[valoracion]:
            if candidato in catalogo:
                elegida = catalogo[candidato]
                break
        if elegida is not None:
            serie = _construir_serie_catalogo(elegida, "CL", valoracion)
            _validar_coherencia_valoracion(serie.codigo, valoracion, serie.titulo_es)
            descubiertas[("CL", valoracion)] = serie

    for codigo, fila in catalogo.items():
        coincidencia = _PATRON_REGIONAL_TOTAL.fullmatch(codigo)
        if coincidencia is None:
            continue
        marca, region = coincidencia.groups()
        valoracion = "real" if marca == "R" else "nominal"
        clave = (region, valoracion)
        if clave in descubiertas:
            raise BdeApiError(
                f"SearchSeries: serie de PIB total duplicada para región {region} ({valoracion})."
            )
        serie = _construir_serie_catalogo(fila, region, valoracion)
        _validar_coherencia_valoracion(serie.codigo, valoracion, serie.titulo_es)
        descubiertas[clave] = serie

    esperadas = {(territorio, valoracion) for territorio in TERRITORIOS for valoracion in VALORACIONES}
    faltantes = sorted(esperadas.difference(descubiertas))
    if faltantes:
        detalle = ", ".join(f"{territorio}/{valoracion}" for territorio, valoracion in faltantes)
        raise BdeApiError(
            f"SearchSeries: faltan {len(faltantes)} de las 34 series anuales de PIB total ({detalle})."
        )
    return {
        (territorio, valoracion): descubiertas[(territorio, valoracion)]
        for territorio in TERRITORIOS
        for valoracion in VALORACIONES
    }


def descubrir_series_sectoriales(catalogo: dict[str, dict]) -> list[SerieCatalogo]:
    """Descubre desde el catálogo todas las series sectoriales regionales ref. 2018.

    No inventa ni deriva códigos por patrón fuera del catálogo: solo inventaría
    las entradas efectivamente presentes en ``SearchSeries``.
    """
    sectoriales: list[SerieCatalogo] = []
    for codigo, fila in catalogo.items():
        coincidencia = _PATRON_REGIONAL_SECTORIAL.fullmatch(codigo)
        if coincidencia is None:
            continue
        marca, act, sub1, sub2, region = coincidencia.groups()
        if (act, sub1, sub2) == ("Z", "Z", "Z"):
            continue
        actividad = act if (sub1 == "Z" and sub2 == "Z") else f"{act}.{sub1}.{sub2}"
        valoracion = "real" if marca == "R" else "nominal"
        serie = _construir_serie_catalogo(fila, region, valoracion, actividad_codigo=actividad)
        _validar_coherencia_valoracion(serie.codigo, valoracion, serie.titulo_es)
        sectoriales.append(serie)

    sectoriales.sort(key=lambda s: (s.territorio, s.actividad_codigo or "", s.valoracion, s.codigo))
    return sectoriales


def _comparar_con_referencia(
    series_actuales: list[dict],
    referencia_bytes: bytes,
    nombre_referencia: str,
) -> dict:
    try:
        datos_ref = json.loads(referencia_bytes.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise BdeApiError("Archivo de referencia sectorial JSON inválido.") from None

    if isinstance(datos_ref, dict) and isinstance(datos_ref.get("series"), list):
        filas_ref = datos_ref["series"]
    elif isinstance(datos_ref, list):
        filas_ref = datos_ref
    else:
        raise BdeApiError("El archivo de referencia sectorial debe contener una lista en 'series'.")

    por_codigo_ref: dict[str, dict] = {}
    for fila in filas_ref:
        if isinstance(fila, str) and fila.strip():
            codigo = fila.strip()
            por_codigo_ref[codigo] = {"serie_bde": codigo}
        elif isinstance(fila, dict) and isinstance(fila.get("serie_bde") or fila.get("seriesId"), str):
            codigo = str(fila.get("serie_bde") or fila.get("seriesId")).strip()
            por_codigo_ref[codigo] = fila
        else:
            raise BdeApiError("Entrada inválida en archivo de referencia sectorial.")

    por_codigo_actual = {fila["serie_bde"]: fila for fila in series_actuales}
    codigos_ref = set(por_codigo_ref)
    codigos_actual = set(por_codigo_actual)

    altas = sorted(codigos_actual.difference(codigos_ref))
    bajas = sorted(codigos_ref.difference(codigos_actual))

    campos_auditoria = (
        "territorio",
        "actividad_codigo",
        "valoracion",
        "frecuencia",
        "unidad",
        "anio_referencia",
        "titulo_es",
    )
    cambios_metadatos: list[dict] = []
    for codigo in sorted(codigos_actual.intersection(codigos_ref)):
        ref = por_codigo_ref[codigo]
        act = por_codigo_actual[codigo]
        diferencias = {}
        for campo in campos_auditoria:
            if campo in ref and ref[campo] != act.get(campo):
                diferencias[campo] = {"anterior": ref[campo], "actual": act.get(campo)}
        if diferencias:
            cambios_metadatos.append({"serie_bde": codigo, "cambios": diferencias})

    return {
        "estado": "comparado",
        "archivo_referencia": nombre_referencia,
        "sha256_referencia": sha256(referencia_bytes).hexdigest(),
        "total_referencia": len(por_codigo_ref),
        "total_actual": len(por_codigo_actual),
        "altas": altas,
        "bajas": bajas,
        "cambios_metadatos": cambios_metadatos,
    }


def construir_inventario_sectorial(
    catalogo_bytes: bytes,
    extraido_en: str,
    referencia_sectorial_bytes: bytes | None = None,
    nombre_referencia: str | None = None,
) -> dict:
    """Construye el manifiesto reproducible del inventario sectorial regional."""
    try:
        payload = json.loads(catalogo_bytes.decode("utf-8"), parse_float=str)
    except (ValueError, UnicodeError):
        raise BdeApiError("Catálogo anual JSON inválido.") from None
    catalogo = parsear_catalogo_anual(payload)
    sectoriales = descubrir_series_sectoriales(catalogo)

    registros = [
        {
            "serie_bde": s.codigo,
            "territorio": s.territorio,
            "nombre_territorio": NOMBRES_TERRITORIOS[s.territorio],
            "actividad_codigo": s.actividad_codigo,
            "valoracion": s.valoracion,
            "anio_referencia": ANIO_REFERENCIA_REAL if s.valoracion == "real" else None,
            "frecuencia": s.frecuencia,
            "unidad": s.unidad_titulo,
            "titulo_es": s.titulo_es,
            "titulo_en": s.titulo_en,
            "primera_observacion": s.primera_observacion,
            "ultima_observacion": s.ultima_observacion,
            "actualizada_en": s.actualizada_en,
            "corte": _parsear_fecha_corte(s.actualizada_en),
        }
        for s in sectoriales
    ]

    sha_catalogo = sha256(catalogo_bytes).hexdigest()
    sha_codigos = sha256(
        "\n".join(sorted(r["serie_bde"] for r in registros)).encode("utf-8")
    ).hexdigest()
    sha_inventario = sha256(
        json.dumps(registros, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    actividades_globales = sorted({r["actividad_codigo"] for r in registros if r["actividad_codigo"]})
    por_region: dict[str, dict] = {}
    anomalias: list[dict] = []

    for region in REGIONES:
        de_region = [r for r in registros if r["territorio"] == region]
        acts_real = sorted({r["actividad_codigo"] for r in de_region if r["valoracion"] == "real"})
        acts_nom = sorted({r["actividad_codigo"] for r in de_region if r["valoracion"] == "nominal"})
        esperadas_region = REFERENCIA_SECTORIAL_ACTIVIDADES * REFERENCIA_SECTORIAL_VALORACIONES
        por_region[region] = {
            "nombre": NOMBRES_TERRITORIOS[region],
            "total": len(de_region),
            "esperadas_referencia": esperadas_region,
            "diferencia": len(de_region) - esperadas_region,
            "real": len(acts_real),
            "nominal": len(acts_nom),
            "actividades_real": acts_real,
            "actividades_nominal": acts_nom,
            "actividades_solo_real": sorted(set(acts_real).difference(acts_nom)),
            "actividades_solo_nominal": sorted(set(acts_nom).difference(acts_real)),
        }
        if len(acts_real) != REFERENCIA_SECTORIAL_ACTIVIDADES or len(acts_nom) != REFERENCIA_SECTORIAL_ACTIVIDADES:
            anomalias.append({
                "tipo": "cobertura_region",
                "territorio": region,
                "real": len(acts_real),
                "nominal": len(acts_nom),
                "esperadas_por_valoracion": REFERENCIA_SECTORIAL_ACTIVIDADES,
            })

    por_actividad: dict[str, dict] = {}
    for act in actividades_globales:
        de_act = [r for r in registros if r["actividad_codigo"] == act]
        regs_real = sorted({r["territorio"] for r in de_act if r["valoracion"] == "real"})
        regs_nom = sorted({r["territorio"] for r in de_act if r["valoracion"] == "nominal"})
        titulos_muestra = sorted({r["titulo_es"] for r in de_act})[:3]
        por_actividad[act] = {
            "total": len(de_act),
            "regiones_real": len(regs_real),
            "regiones_nominal": len(regs_nom),
            "regiones_faltantes_real": sorted(set(REGIONES).difference(regs_real)),
            "regiones_faltantes_nominal": sorted(set(REGIONES).difference(regs_nom)),
            "titulos_muestra": titulos_muestra,
        }
        if len(regs_real) != REFERENCIA_SECTORIAL_REGIONES or len(regs_nom) != REFERENCIA_SECTORIAL_REGIONES:
            anomalias.append({
                "tipo": "cobertura_actividad",
                "actividad_codigo": act,
                "regiones_real": len(regs_real),
                "regiones_nominal": len(regs_nom),
                "esperadas_regiones": REFERENCIA_SECTORIAL_REGIONES,
            })

    total_real = sum(1 for r in registros if r["valoracion"] == "real")
    total_nominal = sum(1 for r in registros if r["valoracion"] == "nominal")
    esperadas_por_val = REFERENCIA_SECTORIAL_REGIONES * REFERENCIA_SECTORIAL_ACTIVIDADES

    if referencia_sectorial_bytes is not None:
        comparacion = _comparar_con_referencia(
            registros,
            referencia_sectorial_bytes,
            nombre_referencia or "referencia-sectorial.json",
        )
    else:
        comparacion = {
            "estado": "pendiente_inventario_original",
            "motivo": (
                "No se recibió el archivo con los 416 identificadores originales de la prueba Excel. "
                "Este inventario fechado y con hash sirve como corte reproducible base."
            ),
            "archivo_referencia": None,
            "sha256_referencia": None,
            "total_referencia": REFERENCIA_SECTORIAL_TOTAL,
            "total_actual": len(registros),
            "altas": [],
            "bajas": [],
            "cambios_metadatos": [],
        }

    huella = sha256(f"{sha_catalogo}{sha_codigos}".encode("utf-8")).hexdigest()[:16]
    return {
        "inventario": {
            "id": f"bcch-bde-sectorial-{extraido_en[:10]}-{huella}",
            "version_esquema": "bde-catalogo-sectorial-v1",
            "fuente": FUENTE,
            "endpoint": ENDPOINT,
            "extraido_en": extraido_en,
            "series_catalogo_anual": len(catalogo),
            "hashes": {
                "catalogo_anual_sha256": sha_catalogo,
                "codigos_sectoriales_sha256": sha_codigos,
                "inventario_normalizado_sha256": sha_inventario,
            },
        },
        "referencia_prueba_excel": {
            "total_esperado": REFERENCIA_SECTORIAL_TOTAL,
            "regiones_esperadas": REFERENCIA_SECTORIAL_REGIONES,
            "actividades_por_region_esperadas": REFERENCIA_SECTORIAL_ACTIVIDADES,
            "valoraciones_esperadas": REFERENCIA_SECTORIAL_VALORACIONES,
            "encontradas": len(registros),
            "diferencia_total": len(registros) - REFERENCIA_SECTORIAL_TOTAL,
            "actividades_distintas_encontradas": len(actividades_globales),
            "coincide_total_416": len(registros) == REFERENCIA_SECTORIAL_TOTAL and not anomalias,
        },
        "comparacion_identificadores": comparacion,
        "cobertura": {
            "por_valoracion": {
                "real": {
                    "encontradas": total_real,
                    "esperadas_referencia": esperadas_por_val,
                    "diferencia": total_real - esperadas_por_val,
                },
                "nominal": {
                    "encontradas": total_nominal,
                    "esperadas_referencia": esperadas_por_val,
                    "diferencia": total_nominal - esperadas_por_val,
                },
            },
            "por_region": por_region,
            "por_actividad": por_actividad,
            "anomalias": anomalias,
        },
        "series": registros,
    }


def _parsear_observaciones_serie(
    payload: dict,
    serie: SerieCatalogo,
    desde: date,
    hasta: date,
) -> tuple[dict[int, dict], Decimal, str]:
    bloque = payload.get("Series")
    if not isinstance(bloque, dict) or bloque.get("seriesId") != serie.codigo:
        raise BdeApiError(f"{serie.codigo}: identidad de serie incorrecta en GetSeries.")
    filas = bloque.get("Obs")
    if not isinstance(filas, list) or not filas:
        raise BdeApiError(f"{serie.codigo}: observaciones vacías o inválidas.")

    descrip_es = bloque.get("descripEsp") if isinstance(bloque.get("descripEsp"), str) else None
    factor, unidad_origen = _factor_a_millones(serie.titulo_es, descrip_es)

    por_anio: dict[int, dict] = {}
    numericas = 0
    for fila in filas:
        if not isinstance(fila, dict):
            raise BdeApiError(f"{serie.codigo}: observación mal formada.")
        try:
            fecha_str = fila["indexDateString"]
            fecha = _parsear_fecha_observacion(fecha_str)
            estado_bde = fila["statusCode"]
            valor_crudo = fila["value"]
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
                valor_decimal = Decimal(str(valor_crudo).strip())
            except InvalidOperation:
                raise BdeApiError(f"{serie.codigo}: observación OK con valor no numérico.") from None
            if not valor_decimal.is_finite():
                raise BdeApiError(f"{serie.codigo}: observación OK con valor no finito.")
            valor_millones = formatear_decimal(valor_decimal * factor)
            numericas += 1
            por_anio[fecha.year] = {
                "fecha_origen": fecha_str,
                "valor_crudo": str(valor_crudo),
                "status_bde": estado_limpio,
                "valor": valor_millones,
                "estado": "informado",
                "clase": "oficial",
                "motivo": None,
            }
        elif estado_limpio.upper() in _ESTADOS_FALTANTES_BDE:
            por_anio[fecha.year] = {
                "fecha_origen": fecha_str,
                "valor_crudo": None if valor_crudo is None else str(valor_crudo),
                "status_bde": estado_limpio,
                "valor": None,
                "estado": "faltante",
                "clase": "no_disponible",
                "motivo": f"Observación no disponible en BDE (statusCode={estado_limpio}).",
            }
        else:
            raise BdeApiError(f"{serie.codigo}: statusCode BDE no reconocido ({estado_limpio}).")

    if numericas == 0:
        raise BdeApiError(f"{serie.codigo}: ninguna observación numérica finita.")
    return por_anio, factor, unidad_origen


def normalizar_pib_total(
    catalogo_bytes: bytes,
    series_bytes: dict[str, bytes],
    extraido_en: str,
    desde: date,
    hasta: date,
    estado_publicacion: str = "aprobada",
) -> dict:
    """Normaliza catálogo y 34 respuestas ``GetSeries`` al contrato ``pib-datos.schema.json``."""
    if estado_publicacion not in {"aprobada", "prueba"}:
        raise BdeApiError("estado_publicacion debe ser 'aprobada' o 'prueba'.")
    if desde > hasta:
        raise BdeApiError("El inicio del período debe preceder al final.")
    if desde.year < 2012:
        raise BdeApiError("El contrato PIB admite períodos desde 2012 en adelante (--desde >= 2012-01-01).")

    try:
        payload_catalogo = json.loads(catalogo_bytes.decode("utf-8"), parse_float=str)
    except (ValueError, UnicodeError):
        raise BdeApiError("Catálogo anual JSON inválido.") from None
    catalogo = parsear_catalogo_anual(payload_catalogo)
    series_totales = descubrir_series_totales(catalogo)

    faltan_bytes = [
        serie.codigo for serie in series_totales.values() if serie.codigo not in series_bytes
    ]
    if faltan_bytes:
        raise BdeApiError(f"Faltan insumos GetSeries para: {', '.join(sorted(faltan_bytes))}.")

    hash_catalogo = sha256(catalogo_bytes).hexdigest()
    hashes_series = {
        serie.codigo: sha256(series_bytes[serie.codigo]).hexdigest()
        for serie in series_totales.values()
    }
    cadena_huella = hash_catalogo + "".join(
        hashes_series[series_totales[(territorio, valoracion)].codigo]
        for territorio in TERRITORIOS
        for valoracion in VALORACIONES
    )
    huella = sha256(cadena_huella.encode("utf-8")).hexdigest()[:16]
    publicacion_id = f"bcch-bde-api-{extraido_en[:10]}-{huella}"

    artefactos: list[dict] = [
        {
            "id": "bde-api-catalogo-anual",
            "fuente": FUENTE,
            "url": ENDPOINT,
            "sha256": hash_catalogo,
            "corte": None,
            "extraido_en": extraido_en,
        }
    ]

    datos_series: dict[tuple[str, str], tuple[SerieCatalogo, str, dict[int, dict], str]] = {}
    anios_publicables: set[int] = set()
    cortes_detectados: list[str] = []

    for valoracion in VALORACIONES:
        for territorio in TERRITORIOS:
            serie = series_totales[(territorio, valoracion)]
            raw_serie = series_bytes[serie.codigo]
            try:
                payload_serie = json.loads(raw_serie.decode("utf-8"), parse_float=str)
            except (ValueError, UnicodeError):
                raise BdeApiError(f"{serie.codigo}: cuerpo JSON de GetSeries inválido.") from None
            por_anio, _factor, unidad_origen = _parsear_observaciones_serie(
                payload_serie, serie, desde, hasta
            )
            anios_publicables.update(anio for anio in por_anio if anio >= 2013)
            corte_serie = _parsear_fecha_corte(serie.actualizada_en)
            if corte_serie is not None:
                cortes_detectados.append(corte_serie)
            artefacto_id = f"bde-api-{serie.codigo}"
            artefactos.append({
                "id": artefacto_id,
                "fuente": FUENTE,
                "url": ENDPOINT,
                "sha256": hashes_series[serie.codigo],
                "corte": corte_serie,
                "extraido_en": extraido_en,
            })
            datos_series[(territorio, valoracion)] = (serie, artefacto_id, por_anio, unidad_origen)

    if not anios_publicables:
        raise BdeApiError("Las series extraídas no contienen observaciones desde 2013 en adelante.")

    anio_inicio = max(2013, desde.year)
    anio_fin = max(anios_publicables)
    anios = tuple(range(anio_inicio, anio_fin + 1))

    niveles: dict[tuple[str, str, int], dict] = {}
    observaciones: list[dict] = []
    procedencias: list[dict] = []

    def registrar(
        territorio: str,
        anio: int,
        metrica: str,
        valoracion: str,
        valor: str | None,
        estado: str,
        clase: str,
        **procedencia: object,
    ) -> dict:
        obs_id = f"{publicacion_id}.{territorio}.{anio}.{metrica}.{valoracion}"
        fila = {
            "id": obs_id,
            "territorio": territorio,
            "anio": anio,
            "metrica": metrica,
            "valoracion": valoracion,
            "valor": valor,
            "unidad": UNIDAD_NIVEL if metrica == "nivel" else "%",
            "anio_referencia": ANIO_REFERENCIA_REAL if valoracion == "real" else None,
            "estado": estado,
            "clase": clase,
            "publicacion": publicacion_id,
        }
        observaciones.append(fila)
        procedencias.append({
            "observacion": obs_id,
            "publicacion": publicacion_id,
            "serie_bde": None,
            "artefacto": None,
            "selector": None,
            "formula_version": None,
            "insumos": [],
            "motivo": None,
            **procedencia,
        })
        return fila

    territorios_con_2012 = 0
    for valoracion in VALORACIONES:
        for territorio in TERRITORIOS:
            serie, artefacto_id, por_anio, unidad_origen = datos_series[(territorio, valoracion)]
            # El contrato permite 2012 exclusivamente para nivel real (insumo de crecimiento 2013).
            if valoracion == "real" and desde.year <= 2012 and 2012 in por_anio:
                dato_2012 = por_anio[2012]
                if dato_2012["estado"] in {"informado", "preliminar"}:
                    territorios_con_2012 += 1
                niveles["real", territorio, 2012] = registrar(
                    territorio,
                    2012,
                    "nivel",
                    "real",
                    dato_2012["valor"],
                    dato_2012["estado"],
                    dato_2012["clase"],
                    artefacto=artefacto_id,
                    serie_bde=serie.codigo,
                    selector=(
                        f"GetSeries · {serie.codigo} · {dato_2012['fecha_origen']} · "
                        f"{dato_2012['valor_crudo']} ({unidad_origen}) · statusCode={dato_2012['status_bde']}"
                    ),
                    motivo=dato_2012["motivo"],
                )

            for anio in anios:
                dato = por_anio.get(anio)
                if dato is None:
                    niveles[valoracion, territorio, anio] = registrar(
                        territorio,
                        anio,
                        "nivel",
                        valoracion,
                        None,
                        "faltante",
                        "no_disponible",
                        artefacto=artefacto_id,
                        serie_bde=serie.codigo,
                        selector=f"GetSeries · {serie.codigo} · {anio} · sin fila",
                        motivo=f"Año {anio} ausente en la serie BDE {serie.codigo}.",
                    )
                else:
                    niveles[valoracion, territorio, anio] = registrar(
                        territorio,
                        anio,
                        "nivel",
                        valoracion,
                        dato["valor"],
                        dato["estado"],
                        dato["clase"],
                        artefacto=artefacto_id,
                        serie_bde=serie.codigo,
                        selector=(
                            f"GetSeries · {serie.codigo} · {dato['fecha_origen']} · "
                            f"{dato['valor_crudo']} ({unidad_origen}) · statusCode={dato['status_bde']}"
                        ),
                        motivo=dato["motivo"],
                    )

    for territorio in TERRITORIOS:
        for anio in anios:
            res_crec = crecimiento(
                niveles["real", territorio, anio],
                niveles.get(("real", territorio, anio - 1)),
            )
            registrar(
                territorio,
                anio,
                "crecimiento",
                "real",
                res_crec.valor,
                res_crec.estado,
                res_crec.clase,
                formula_version=res_crec.formula_version,
                insumos=list(res_crec.insumos),
                motivo=res_crec.motivo,
            )
            if territorio != "CL":
                res_part = participacion(
                    niveles["nominal", territorio, anio],
                    niveles["nominal", "CL", anio],
                )
                registrar(
                    territorio,
                    anio,
                    "participacion",
                    "nominal",
                    res_part.valor,
                    res_part.estado,
                    res_part.clase,
                    formula_version=res_part.formula_version,
                    insumos=list(res_part.insumos),
                    motivo=res_part.motivo,
                )

    nota_2012 = (
        f"Crecimiento real de 2013 calculado para {territorios_con_2012} de 17 territorios "
        f"con nivel real 2012 informado en la API BDE."
        if territorios_con_2012 > 0
        else "Crecimiento real de 2013 marcado como faltante por ausencia de niveles reales 2012 en la API BDE."
    )
    cambios = [
        f"PIB anual {anio_inicio}–{anio_fin} de Chile y 16 regiones vía API REST oficial BDE (34 series descubiertas en SearchSeries).",
        "Conversión exacta con Decimal a millones CLP preservando toda la precisión decimal entregada por GetSeries.",
        nota_2012,
    ]
    if cortes_detectados:
        cambios.append(f"Última fecha de actualización reportada por catálogo BDE: {max(cortes_detectados)}.")

    return {
        "publicacion": {
            "id": publicacion_id,
            "fecha": extraido_en,
            "estado": estado_publicacion,
            "fuente": FUENTE,
            "cobertura": {
                "esperadas": len(observaciones),
                "disponibles": sum(fila["valor"] is not None for fila in observaciones),
            },
            "cambios": cambios,
        },
        "artefactos": artefactos,
        "observaciones": observaciones,
        "procedencias": procedencias,
    }


def _escribir_salida_protegida(ruta: Path, contenido: bytes, credenciales: Credenciales | None = None) -> None:
    if credenciales is not None and contiene_credencial(contenido, credenciales):
        raise BdeApiError("Se bloqueó la escritura: se detectó una credencial en el contenido de salida.")
    if ruta.exists():
        if ruta.read_bytes() != contenido:
            raise BdeApiError(
                f"La salida {ruta} ya pertenece a otro lote. Indica otra ruta o reproduce el lote original."
            )
        return
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("xb") as archivo:
        archivo.write(contenido)


def _verificar_manifiesto_raw(insumos_dir: Path) -> tuple[dict, bytes, dict[str, bytes]]:
    ruta_manifiesto = insumos_dir / "manifiesto.json"
    if not ruta_manifiesto.is_file():
        raise BdeApiError(f"No se encontró manifiesto.json en {insumos_dir}.")
    try:
        manifiesto = json.loads(ruta_manifiesto.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise BdeApiError("No se pudo leer manifiesto.json de insumos.") from None

    if not isinstance(manifiesto, dict) or not isinstance(manifiesto.get("artefactos"), list):
        raise BdeApiError("Estructura inválida en manifiesto.json.")

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
        if insumos_dir.resolve() not in ruta_archivo.parents:
            raise BdeApiError("Ruta de artefacto fuera del directorio de insumos.")
        if not ruta_archivo.is_file():
            raise BdeApiError(f"Falta archivo de insumo declarado en manifiesto: {relativo}.")
        crudo = ruta_archivo.read_bytes()
        if sha256(crudo).hexdigest() != esperado:
            raise BdeApiError(f"Integridad SHA-256 fallida para {relativo}.")
        if entrada.get("id") == "bde-api-catalogo-anual":
            catalogo_bytes = crudo
        elif isinstance(entrada.get("serie_bde"), str):
            series_bytes[entrada["serie_bde"]] = crudo

    if catalogo_bytes is None:
        raise BdeApiError("El manifiesto no incluye el catálogo anual.")
    return manifiesto, catalogo_bytes, series_bytes


def ejecutar_extraccion(
    credenciales: Credenciales,
    insumos_dir: Path,
    desde: date,
    hasta: date,
    salida_pib: Path | None = None,
    salida_sectorial: Path | None = None,
    referencia_sectorial: Path | None = None,
    estado_publicacion: str = "aprobada",
) -> dict:
    """Ejecuta la extracción autenticada completa, archiva raw y escribe salidas."""
    if salida_pib is None and salida_sectorial is None:
        raise BdeApiError("Debe solicitarse al menos una salida (PIB total o inventario sectorial).")
    if salida_pib is not None and desde.year < 2012:
        raise BdeApiError("Para el lote PIB total, --desde debe ser >= 2012-01-01.")
    if desde > hasta:
        raise BdeApiError("El inicio del período debe preceder al final.")
    if insumos_dir.exists():
        raise BdeApiError(f"El directorio de insumos ya existe: {insumos_dir}.")

    extraido_en = datetime.now(timezone.utc).isoformat(timespec="seconds")
    catalogo_bytes, payload_catalogo = descargar(credenciales, "SearchSeries", frequency="ANNUAL")
    catalogo = parsear_catalogo_anual(payload_catalogo)

    series_bytes: dict[str, bytes] = {}
    artefactos_raw: list[dict] = [
        {
            "id": "bde-api-catalogo-anual",
            "archivo": "catalogo-anual.json",
            "sha256": sha256(catalogo_bytes).hexdigest(),
            "bytes": len(catalogo_bytes),
            "serie_bde": None,
            "corte": None,
        }
    ]

    lote_pib: dict | None = None
    if salida_pib is not None:
        series_totales = descubrir_series_totales(catalogo)
        for valoracion in VALORACIONES:
            for territorio in TERRITORIOS:
                serie = series_totales[(territorio, valoracion)]
                raw_serie, _payload_serie = descargar(
                    credenciales,
                    "GetSeries",
                    timeseries=serie.codigo,
                    firstdate=desde.isoformat(),
                    lastdate=hasta.isoformat(),
                )
                series_bytes[serie.codigo] = raw_serie
                artefactos_raw.append({
                    "id": f"bde-api-{serie.codigo}",
                    "archivo": f"series/{serie.codigo}.json",
                    "sha256": sha256(raw_serie).hexdigest(),
                    "bytes": len(raw_serie),
                    "serie_bde": serie.codigo,
                    "corte": _parsear_fecha_corte(serie.actualizada_en),
                })
        lote_pib = normalizar_pib_total(
            catalogo_bytes,
            series_bytes,
            extraido_en,
            desde,
            hasta,
            estado_publicacion=estado_publicacion,
        )

    inventario_sectorial: dict | None = None
    if salida_sectorial is not None:
        ref_bytes = referencia_sectorial.read_bytes() if referencia_sectorial is not None else None
        inventario_sectorial = construir_inventario_sectorial(
            catalogo_bytes,
            extraido_en,
            referencia_sectorial_bytes=ref_bytes,
            nombre_referencia=referencia_sectorial.name if referencia_sectorial is not None else None,
        )

    modo = (
        "completo"
        if (salida_pib is not None and salida_sectorial is not None)
        else ("pib-total" if salida_pib is not None else "inventario-sectorial")
    )
    manifiesto = {
        "version_esquema": "bde-api-raw-v1",
        "modo": modo,
        "fuente": ENDPOINT,
        "extraido_en": extraido_en,
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "estado_publicacion": estado_publicacion,
        "series_catalogo_anual": len(catalogo),
        "artefactos": artefactos_raw,
    }
    manifiesto_bytes = (json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if contiene_credencial(manifiesto_bytes, credenciales):
        raise BdeApiError("Se bloqueó la escritura: credencial detectada en el manifiesto.")

    # Pre-serializar y validar salidas antes de escribir archivos raw.
    pib_bytes = (
        (json.dumps(lote_pib, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if lote_pib is not None
        else None
    )
    sec_bytes = (
        (json.dumps(inventario_sectorial, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if inventario_sectorial is not None
        else None
    )
    for salida_ruta, contenido in ((salida_pib, pib_bytes), (salida_sectorial, sec_bytes)):
        if salida_ruta is not None and contenido is not None:
            if contiene_credencial(contenido, credenciales):
                raise BdeApiError("Se bloqueó la escritura: credencial detectada en salida.")
            if salida_ruta.exists() and salida_ruta.read_bytes() != contenido:
                raise BdeApiError(
                    f"La salida {salida_ruta} ya pertenece a otro lote. Indica otra ruta."
                )

    insumos_dir.parent.mkdir(parents=True, exist_ok=True)
    insumos_dir.mkdir(mode=0o700, exist_ok=False)
    (insumos_dir / "catalogo-anual.json").write_bytes(catalogo_bytes)
    if series_bytes:
        (insumos_dir / "series").mkdir(parents=True, exist_ok=True)
        for codigo, crudo in series_bytes.items():
            (insumos_dir / "series" / f"{codigo}.json").write_bytes(crudo)
    (insumos_dir / "manifiesto.json").write_bytes(manifiesto_bytes)

    if salida_pib is not None and pib_bytes is not None:
        _escribir_salida_protegida(salida_pib, pib_bytes, credenciales)
    if salida_sectorial is not None and sec_bytes is not None:
        _escribir_salida_protegida(salida_sectorial, sec_bytes, credenciales)

    return {
        "insumos": str(insumos_dir),
        "pib": lote_pib["publicacion"] if lote_pib is not None else None,
        "sectorial": inventario_sectorial["inventario"] if inventario_sectorial is not None else None,
    }


def reproducir_desde_raw(
    insumos_dir: Path,
    salida_pib: Path | None = None,
    salida_sectorial: Path | None = None,
    referencia_sectorial: Path | None = None,
) -> dict:
    """Reconstruye salidas bit-a-bit desde un directorio ``data/raw/bde-api-*/`` sin red."""
    if salida_pib is None and salida_sectorial is None:
        raise BdeApiError("Debe solicitarse al menos una salida al reproducir.")
    manifiesto, catalogo_bytes, series_bytes = _verificar_manifiesto_raw(insumos_dir)
    extraido_en = manifiesto["extraido_en"]
    desde = date.fromisoformat(manifiesto["desde"])
    hasta = date.fromisoformat(manifiesto["hasta"])
    estado_publicacion = manifiesto.get("estado_publicacion", "aprobada")

    resultado: dict = {"insumos": str(insumos_dir), "pib": None, "sectorial": None}

    if salida_pib is not None:
        lote_pib = normalizar_pib_total(
            catalogo_bytes,
            series_bytes,
            extraido_en,
            desde,
            hasta,
            estado_publicacion=estado_publicacion,
        )
        pib_bytes = (json.dumps(lote_pib, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        _escribir_salida_protegida(salida_pib, pib_bytes)
        resultado["pib"] = lote_pib["publicacion"]

    if salida_sectorial is not None:
        ref_bytes = referencia_sectorial.read_bytes() if referencia_sectorial is not None else None
        inventario = construir_inventario_sectorial(
            catalogo_bytes,
            extraido_en,
            referencia_sectorial_bytes=ref_bytes,
            nombre_referencia=referencia_sectorial.name if referencia_sectorial is not None else None,
        )
        sec_bytes = (json.dumps(inventario, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        _escribir_salida_protegida(salida_sectorial, sec_bytes)
        resultado["sectorial"] = inventario["inventario"]

    return resultado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extracción oficial autenticada de PIB total (34 series) e inventario sectorial BDE."
    )
    parser.add_argument(
        "--env",
        type=Path,
        default=None,
        help="Ruta a archivo .env local fuera de Git (opcional; por defecto lee variables de entorno).",
    )
    parser.add_argument(
        "--desde",
        type=date.fromisoformat,
        default=date(2012, 1, 1),
        help="Fecha inicial ISO para GetSeries (predeterminado: 2012-01-01).",
    )
    parser.add_argument(
        "--hasta",
        type=date.fromisoformat,
        default=date.today(),
        help="Fecha final ISO para GetSeries (predeterminado: hoy).",
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
        default=Path("data/published/pib-bde-api.json"),
        help="Ruta del lote normalizado PIB total (predeterminado: data/published/pib-bde-api.json).",
    )
    parser.add_argument(
        "--inventario-sectorial",
        action="store_true",
        help="Genera el manifiesto del inventario sectorial regional (416 de referencia).",
    )
    parser.add_argument(
        "--completo",
        action="store_true",
        help="Ejecuta tanto la extracción de las 34 series totales como el inventario sectorial.",
    )
    parser.add_argument(
        "--salida-sectorial",
        type=Path,
        default=Path("data/published/catalogo-sectorial-bde.json"),
        help="Ruta del manifiesto sectorial (predeterminado: data/published/catalogo-sectorial-bde.json).",
    )
    parser.add_argument(
        "--referencia-sectorial",
        type=Path,
        default=None,
        help="Archivo JSON previo o con los 416 identificadores oficiales para reportar altas/bajas.",
    )
    parser.add_argument(
        "--estado",
        choices=("aprobada", "prueba"),
        default="aprobada",
        help="Estado del lote publicado según contrato pib-datos.schema.json.",
    )
    parser.add_argument(
        "--reproducir",
        action="store_true",
        help="Reconstruye las salidas bit-a-bit desde --insumos sin red ni credenciales.",
    )
    args = parser.parse_args(argv)

    pedir_pib = args.completo or not args.inventario_sectorial
    pedir_sectorial = args.completo or args.inventario_sectorial
    salida_pib = args.salida if pedir_pib else None
    salida_sectorial = args.salida_sectorial if pedir_sectorial else None

    try:
        if args.reproducir:
            if args.insumos is None:
                parser.exit(2, "En modo --reproducir debe indicar --insumos <directorio-raw>.\n")
            resumen = reproducir_desde_raw(
                args.insumos,
                salida_pib=salida_pib,
                salida_sectorial=salida_sectorial,
                referencia_sectorial=args.referencia_sectorial,
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
            prefijo = "bde-api-sectorial" if (pedir_sectorial and not pedir_pib) else "bde-api"
            insumos_dir = args.insumos or (_RAIZ_REPO / "data" / "raw" / f"{prefijo}-{stamp}")
            resumen = ejecutar_extraccion(
                credenciales,
                insumos_dir=insumos_dir,
                desde=args.desde,
                hasta=args.hasta,
                salida_pib=salida_pib,
                salida_sectorial=salida_sectorial,
                referencia_sectorial=args.referencia_sectorial,
                estado_publicacion=args.estado,
            )
    except BdeApiError as error:
        parser.exit(1, f"{error}\n")
    except OSError:
        parser.exit(1, "No se pudo leer o escribir la evidencia local de BDE.\n")

    if resumen["pib"] is not None:
        print(resumen["pib"]["id"], resumen["pib"]["cobertura"])
    if resumen["sectorial"] is not None:
        print(resumen["sectorial"]["id"], f"sha256={resumen['sectorial']['hashes']['codigos_sectoriales_sha256'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
