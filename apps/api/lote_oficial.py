"""Lectura estrictamente validada y de solo lectura de un lote oficial local."""

from copy import deepcopy
import json
import os
from pathlib import Path
import re

from jsonschema import Draft202012Validator, FormatChecker


ESQUEMA = Path(__file__).resolve().parents[2] / "contracts/pib-datos.schema.json"
URL_CON_CREDENCIALES = re.compile(r"^https://[^/]+@")
CAMPOS = (
    "id",
    "territorio",
    "anio",
    "metrica",
    "valoracion",
    "valor",
    "unidad",
    "anio_referencia",
    "estado",
    "clase",
    "publicacion",
)
CAMPOS_PUBLICACION = ("id", "fecha", "estado", "fuente", "cobertura", "cambios")
CAMPOS_PROCEDENCIA = (
    "observacion",
    "publicacion",
    "serie_bde",
    "artefacto",
    "selector",
    "formula_version",
    "insumos",
    "motivo",
)

# Catálogo oficial idéntico a db/migrations/001_pib.sql ordenado por código.
TERRITORIOS_OFICIALES = (
    ("01", "Tarapacá", "regional"),
    ("02", "Antofagasta", "regional"),
    ("03", "Atacama", "regional"),
    ("04", "Coquimbo", "regional"),
    ("05", "Valparaíso", "regional"),
    ("06", "Libertador General Bernardo O’Higgins", "regional"),
    ("07", "Maule", "regional"),
    ("08", "Biobío", "regional"),
    ("09", "La Araucanía", "regional"),
    ("10", "Los Lagos", "regional"),
    ("11", "Aysén del General Carlos Ibáñez del Campo", "regional"),
    ("12", "Magallanes y de la Antártica Chilena", "regional"),
    ("13", "Metropolitana de Santiago", "regional"),
    ("14", "Los Ríos", "regional"),
    ("15", "Arica y Parinacota", "regional"),
    ("16", "Ñuble", "regional"),
    ("CL", "Chile", "nacional"),
)

_VALIDADOR = None


def _validador_esquema():
    global _VALIDADOR
    if _VALIDADOR is None:
        esquema = json.loads(ESQUEMA.read_text(encoding="utf-8"))
        _VALIDADOR = Draft202012Validator(esquema, format_checker=FormatChecker())
    return _VALIDADOR


def _texto_vacio(valor):
    return valor is None or not str(valor).strip()


def validar_lote_oficial(lote):
    """Valida contrato JSON Schema e invariantes de publicación oficial aprobada."""
    error = next(_validador_esquema().iter_errors(lote), None)
    if error is not None:
        campo = ".".join(map(str, error.absolute_path)) or "raíz"
        raise ValueError(f"El lote oficial incumple el contrato en {campo}.")

    publicacion = lote["publicacion"]
    corte_id = publicacion["id"]
    if publicacion["estado"] != "aprobada":
        raise ValueError(
            "El modo de lote oficial admite únicamente publicaciones con estado 'aprobada'."
        )

    artefactos_ids = set()
    for artefacto in lote["artefactos"]:
        artefacto_id = artefacto["id"]
        if artefacto_id in artefactos_ids:
            raise ValueError(f"El artefacto '{artefacto_id}' está duplicado en el lote oficial.")
        if URL_CON_CREDENCIALES.match(artefacto["url"]):
            raise ValueError(f"La URL del artefacto '{artefacto_id}' no puede incluir credenciales.")
        artefactos_ids.add(artefacto_id)

    observaciones_por_id = {}
    claves_naturales = set()
    for fila in lote["observaciones"]:
        obs_id = fila["id"]
        if fila["publicacion"] != corte_id:
            raise ValueError(f"La observación '{obs_id}' referencia una publicación distinta al corte.")
        if fila["clase"] in {"prueba", "estimacion"}:
            raise ValueError(
                f"La observación '{obs_id}' tiene clase '{fila['clase']}', prohibida en un corte oficial."
            )
        if fila["estado"] == "error":
            raise ValueError(
                f"La observación '{obs_id}' tiene estado 'error', prohibido en un corte oficial."
            )
        if obs_id in observaciones_por_id:
            raise ValueError(f"Identificador de observación duplicado: '{obs_id}'.")

        clave_natural = (fila["metrica"], fila["valoracion"], fila["anio"], fila["territorio"])
        if clave_natural in claves_naturales:
            raise ValueError(f"Observación duplicada para la clave natural {clave_natural}.")
        claves_naturales.add(clave_natural)

        if fila["metrica"] == "participacion" and fila["territorio"] == "CL":
            raise ValueError(f"La observación '{obs_id}' no puede asignar participación a 'CL'.")
        if fila["metrica"] == "nivel":
            if fila["unidad"] != "millones CLP":
                raise ValueError(f"La observación '{obs_id}' de nivel debe usar unidad 'millones CLP'.")
            if fila["valoracion"] == "real" and fila["valor"] is not None and fila["anio_referencia"] is None:
                raise ValueError(f"La observación '{obs_id}' real requiere anio_referencia.")

        observaciones_por_id[obs_id] = fila

    procedencias_por_obs = {}
    for proc in lote["procedencias"]:
        obs_id = proc["observacion"]
        if proc["publicacion"] != corte_id:
            raise ValueError(f"La procedencia de '{obs_id}' referencia una publicación distinta al corte.")
        if obs_id in procedencias_por_obs:
            raise ValueError(f"Procedencia duplicada para la observación '{obs_id}'.")
        if obs_id not in observaciones_por_id:
            raise ValueError(f"La procedencia de '{obs_id}' referencia una observación inexistente.")
        if proc["artefacto"] is not None and proc["artefacto"] not in artefactos_ids:
            raise ValueError(
                f"La procedencia de '{obs_id}' referencia el artefacto inexistente '{proc['artefacto']}'."
            )
        procedencias_por_obs[obs_id] = proc

    for obs_id, fila in observaciones_por_id.items():
        proc = procedencias_por_obs.get(obs_id)
        if proc is None:
            raise ValueError(f"Falta la procedencia de la observación '{obs_id}'.")
        if fila["valor"] is None and _texto_vacio(proc["motivo"]):
            raise ValueError(f"La observación nula '{obs_id}' requiere un motivo de procedencia.")
        if fila["clase"] == "oficial" and fila["metrica"] == "nivel":
            if _texto_vacio(proc["serie_bde"]) or proc["artefacto"] is None or _texto_vacio(proc["selector"]):
                raise ValueError(
                    f"La observación oficial de nivel '{obs_id}' requiere serie_bde, artefacto y selector."
                )
        if fila["clase"] == "oficial" and fila["metrica"] != "nivel":
            if _texto_vacio(proc["formula_version"]) or not proc["insumos"]:
                raise ValueError(
                    f"La observación derivada oficial '{obs_id}' requiere formula_version e insumos."
                )
        for insumo in proc["insumos"]:
            if insumo == obs_id or insumo not in observaciones_por_id:
                raise ValueError(f"La procedencia de '{obs_id}' declara un insumo inválido: '{insumo}'.")

    cobertura = publicacion["cobertura"]
    esperadas = cobertura["esperadas"]
    disponibles = cobertura["disponibles"]
    if disponibles > esperadas:
        raise ValueError("La cobertura declara más observaciones disponibles que esperadas.")
    publicables = [fila for fila in lote["observaciones"] if fila["anio"] >= 2013]
    disponibles_reales = sum(fila["valor"] is not None for fila in publicables)
    if len(publicables) > esperadas or disponibles_reales != disponibles:
        raise ValueError("Los conteos de cobertura no coinciden con las observaciones desde 2013.")

    return lote


class LoteOficial:
    """Almacén inmutable en memoria para servir un corte oficial validado."""

    def __init__(self, lote):
        validado = validar_lote_oficial(lote)
        self._publicacion = {
            campo: deepcopy(validado["publicacion"][campo]) for campo in CAMPOS_PUBLICACION
        }
        self._observaciones = tuple(
            sorted(
                (
                    {campo: fila[campo] for campo in CAMPOS}
                    for fila in validado["observaciones"]
                    if fila["anio"] >= 2013
                ),
                key=lambda fila: (fila["anio"], fila["territorio"]),
            )
        )
        self._procedencias = {
            proc["observacion"]: {
                campo: deepcopy(proc[campo]) for campo in CAMPOS_PROCEDENCIA
            }
            for proc in validado["procedencias"]
        }

    @classmethod
    def desde_archivo(cls, ruta):
        if isinstance(ruta, os.PathLike):
            texto_ruta = os.fspath(ruta)
        elif isinstance(ruta, str):
            texto_ruta = ruta
        else:
            raise ValueError("La ruta del lote oficial debe ser una cadena o Path.")

        if not str(texto_ruta).strip():
            raise ValueError("La ruta del lote oficial no puede estar vacía.")

        archivo = Path(texto_ruta)
        if not archivo.is_file():
            raise ValueError(f"No se encontró el archivo de lote oficial: {archivo}")

        try:
            lote = json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"No se pudo leer el lote oficial en {archivo}: {exc}") from exc

        return cls(lote)

    def territorios(self):
        return [
            {
                "codigo": codigo,
                "nombre": nombre,
                "nivel": nivel,
                "vigente_desde": None,
                "vigente_hasta": None,
            }
            for codigo, nombre, nivel in TERRITORIOS_OFICIALES
        ]

    def publicaciones(self):
        return [deepcopy(self._publicacion)]

    def observaciones(self, cut, codes, start, end, metric, valuation):
        if cut != self._publicacion["id"]:
            return []
        codigos = set(codes)
        return [
            dict(fila)
            for fila in self._observaciones
            if fila["territorio"] in codigos
            and start <= fila["anio"] <= end
            and fila["metrica"] == metric
            and fila["valoracion"] == valuation
        ]

    def procedencia(self, key):
        valor = self._procedencias.get(key)
        return deepcopy(valor) if valor is not None else None
