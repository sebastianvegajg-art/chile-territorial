"""Valida e importa un corte aprobado desde sus archivos originales."""

import argparse
from hashlib import file_digest
import json
import os
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import psycopg
from psycopg.types.json import Jsonb


ESQUEMA = Path(__file__).resolve().parents[2] / "contracts/pib-datos.schema.json"


def validar_lote(ruta, originales):
    lote = json.loads(ruta.read_text(encoding="utf-8"))
    esquema = json.loads(ESQUEMA.read_text(encoding="utf-8"))
    validador = Draft202012Validator(esquema, format_checker=FormatChecker())
    error = next(validador.iter_errors(lote), None)
    if error:
        campo = ".".join(map(str, error.absolute_path)) or "raíz"
        raise ValueError(f"El lote incumple el contrato en {campo}.")

    if lote["publicacion"]["estado"] != "aprobada":
        raise ValueError("El cargador de publicaciones admite únicamente cortes aprobados.")

    declarados = {artefacto["id"]: artefacto["sha256"] for artefacto in lote["artefactos"]}
    if not declarados or len(declarados) != len(lote["artefactos"]):
        raise ValueError("El lote debe identificar cada artefacto original una sola vez.")

    if originales.keys() != declarados.keys():
        raise ValueError("Los identificadores de los archivos originales deben coincidir con el lote.")

    for identificador, ruta_original in originales.items():
        with ruta_original.open("rb") as archivo:
            huella = file_digest(archivo, "sha256").hexdigest()
        if huella != declarados[identificador]:
            raise ValueError(f"La huella del artefacto {identificador} no coincide con el lote.")

    return lote


def cargar_lote(lote, url):
    with psycopg.connect(url, connect_timeout=4) as conexion:
        conexion.execute("SET LOCAL ROLE ct_pib_ingest")
        return conexion.execute("SELECT pib.cargar_lote(%s)", (Jsonb(lote),)).fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lote", type=Path)
    parser.add_argument("--artefacto", action="append", required=True, metavar="ID=ARCHIVO")
    parser.add_argument("--validar", action="store_true", help="Verifica contrato y huellas sin conectar a PostgreSQL.")
    argumentos = parser.parse_args()
    originales = {}
    for entrada in argumentos.artefacto:
        identificador, separador, ruta = entrada.partition("=")
        if not separador or not identificador or not ruta or identificador in originales:
            parser.error("Cada --artefacto debe usar ID=ARCHIVO y un identificador único.")
        originales[identificador] = Path(ruta)

    try:
        lote = validar_lote(argumentos.lote, originales)
    except (OSError, UnicodeError, json.JSONDecodeError):
        parser.exit(2, "No se pudo leer el lote, el contrato o un archivo original.\n")
    except ValueError as error:
        parser.exit(2, f"{error}\n")

    if argumentos.validar:
        print("Contrato y huellas validados.")
        return

    url = os.getenv("DATABASE_URL")
    if not url:
        parser.exit(2, "Configura DATABASE_URL con la conexión de ingesta.\n")
    try:
        incorporado = cargar_lote(lote, url)
    except psycopg.Error as error:
        codigo = error.sqlstate or "sin código SQL"
        parser.exit(1, f"PostgreSQL rechazó la carga o la conexión ({codigo}).\n")
    print("Corte incorporado." if incorporado else "El corte idéntico ya estaba incorporado.")


if __name__ == "__main__":
    main()
