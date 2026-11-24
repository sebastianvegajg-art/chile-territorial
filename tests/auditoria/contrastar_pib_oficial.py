"""Contrasta un lote PIB con copias independientes de ambos cuadros y con la API opcional."""

import argparse
import csv
from decimal import Decimal, localcontext
from hashlib import sha256
import io
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from bs4 import BeautifulSoup
from jsonschema import Draft202012Validator


REGIONES = ("15", "01", "02", "03", "04", "05", "13", "06", "07", "16", "08", "09", "14", "10", "11", "12")
VARIACIONES_2025 = dict(zip(
    (*REGIONES, "CL"),
    map(Decimal, ("5.3", "-8.3", "1.6", "15.3", "2.5", "3.0", "2.8", "-0.7", "1.4",
                  "2.5", "0.8", "2.6", "2.6", "5.3", "8.5", "4.4", "2.5")),
    strict=True,
))


def celdas(ruta):
    tabla = BeautifulSoup(ruta.read_bytes(), "html.parser").select_one("table#grilla")
    anios = [int(c.get_text(strip=True)) for c in tabla.select("tr")[0].select("th,td")[2:]]
    assert anios == list(range(2013, anios[-1] + 1)), (ruta, anios)
    series = tabla.select("tr input[data-serie]")
    assert len(series) == 19
    series_objetivo = series[:16] + series[-1:]
    resultado = {}
    for territorio, serie in zip((*REGIONES, "CL"), series_objetivo, strict=True):
        if territorio == "CL":
            assert serie["data-serie"].startswith("F032.")
        else:
            assert serie["data-serie"].split(".")[-3] == territorio
        assert serie["data-decimales"] == "0"
        valores = serie.find_parent("tr").select("td")[2:]
        for anio, celda in zip(anios, valores, strict=True):
            valor = Decimal(celda.get_text(strip=True).replace(".", "")) * 1000
            resultado[(territorio, anio)] = (serie["data-serie"], valor)
    return resultado


def auditar_lote(lote, fuente, originales):
    ruta = Path(__file__).resolve().parents[2] / "contracts/pib-datos.schema.json"
    esquema = json.loads(ruta.read_text(encoding="utf-8"))
    Draft202012Validator(esquema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(lote)
    publicacion = lote["publicacion"]
    corte = publicacion["id"]
    assert publicacion["estado"] == "aprobada"
    observaciones = lote["observaciones"]
    claves = {(fila["metrica"], fila["valoracion"], fila["territorio"], fila["anio"]): fila
              for fila in observaciones}
    ids = {fila["id"] for fila in observaciones}
    procedencias = {fila["observacion"]: fila for fila in lote["procedencias"]}
    assert len(claves) == len(ids) == len(procedencias) == len(observaciones) == len(lote["procedencias"])
    assert set(procedencias) == ids
    assert all(fila["publicacion"] == corte for fila in observaciones + lote["procedencias"])
    assert all(fila["clase"] in {"oficial", "no_disponible"} for fila in observaciones)
    assert publicacion["cobertura"] == {
        "esperadas": len(observaciones),
        "disponibles": sum(fila["valor"] is not None for fila in observaciones),
    }

    for tipo in ("real", "nominal"):
        archivo = f"{tipo}.html"
        esperado = celdas(fuente / archivo)
        filas = {(territorio, anio): fila
                 for (metrica, valoracion, territorio, anio), fila in claves.items()
                 if metrica == "nivel" and tipo == valoracion and anio >= 2013}
        assert set(filas) == set(esperado)
        artefacto = next(fila for fila in lote["artefactos"] if fila["id"].endswith(f"-{tipo}"))
        assert sha256((originales / archivo).read_bytes()).hexdigest() == artefacto["sha256"]
        assert celdas(originales / archivo) == esperado
        for clave, (serie, valor) in esperado.items():
            fila = filas[clave]
            origen = procedencias[fila["id"]]
            assert Decimal(fila["valor"]) == valor, (clave, tipo)
            assert fila["unidad"] == "millones CLP"
            assert fila["anio_referencia"] == (2018 if tipo == "real" else None)
            assert (origen["serie_bde"], origen["artefacto"]) == (serie, artefacto["id"])
            assert str(clave[1]) in origen["selector"]
        print(f"{tipo}: {len(filas)} valores, unidades, códigos y huella de los insumos conformes")

    contrastes = {}
    for (metrica, tipo, territorio, anio), fila in claves.items():
        if metrica == "nivel":
            continue
        origen = procedencias[fila["id"]]
        actual = claves["nivel", tipo, territorio, anio]
        if metrica == "crecimiento" and anio == 2013:
            assert (fila["valor"], fila["estado"]) == (None, "faltante")
            assert origen["motivo"]
            continue
        base = (claves["nivel", tipo, territorio, anio - 1] if metrica == "crecimiento"
                else claves["nivel", tipo, "CL", anio])
        assert set(origen["insumos"]) == {actual["id"], base["id"]}
        assert origen["formula_version"].startswith(f"pib-{metrica}-")
        with localcontext() as contexto:
            contexto.prec = 55
            razon = Decimal(actual["valor"]) / Decimal(base["valor"])
            ajustada = (razon - (metrica == "crecimiento")) * 100
            assert abs(Decimal(fila["valor"]) - ajustada) < Decimal("1e-28")
        if metrica == "crecimiento" and anio == 2025:
            contraste = VARIACIONES_2025[territorio]
            assert abs(ajustada - contraste) < Decimal("0.15")
            contrastes[territorio] = (ajustada.quantize(Decimal("0.01")), contraste)
    print(f"cálculos y linaje: {sum(fila['metrica'] != 'nivel' for fila in observaciones)} filas")
    print(f"contraste independiente de variación 2025 (calculada, publicada): {contrastes}")


def auditar_api(lote, api):
    corte = lote["publicacion"]["id"]

    def consultar(ruta, **filtros):
        with urlopen(f"{api.rstrip('/')}/{ruta}?{urlencode(filtros)}", timeout=10) as respuesta:
            cuerpo = respuesta.read().decode("utf-8")
            if ruta.startswith("pib"):
                assert respuesta.headers["X-Publicacion"] == corte
            return json.loads(cuerpo) if respuesta.headers.get_content_type() == "application/json" else cuerpo

    assert lote["publicacion"] in consultar("publicaciones")
    assert len(consultar("territorios")) == 17
    for metrica, tipo in (("nivel", "real"), ("nivel", "nominal"),
                          ("crecimiento", "real"), ("participacion", "nominal")):
        esperado = sorted(
            (fila for fila in lote["observaciones"]
             if fila["metrica"] == metrica and fila["valoracion"] == tipo and fila["anio"] >= 2013),
            key=lambda fila: (fila["anio"], fila["territorio"]),
        )
        filtros = dict(publicacion=corte, metrica=metrica, valoracion=tipo, anio_desde=2013,
                       anio_hasta=max(fila["anio"] for fila in esperado))
        verificadas = []
        for pagina in range(1, (len(esperado) - 1) // 100 + 2):
            respuesta = consultar("pib", pagina=pagina, limite=100, **filtros)
            assert respuesta["total"] == len(esperado)
            assert respuesta["publicacion"] == corte
            verificadas.extend(respuesta["datos"])
        assert verificadas == esperado
        exportadas = list(csv.DictReader(io.StringIO(consultar("pib.csv", **filtros))))
        assert exportadas == [
            {clave: "" if valor is None else str(valor) for clave, valor in fila.items()}
            for fila in esperado
        ]
        muestras = [fila for fila in esperado if fila["territorio"] == "11" and fila["anio"] in (2013, 2025)]
        for fila in muestras:
            origen = consultar(f"observaciones/{fila['id']}/procedencia")
            esperado_origen = next(valor for valor in lote["procedencias"] if valor["observacion"] == fila["id"])
            assert all(origen[clave] == esperado_origen[clave] for clave in ("serie_bde", "insumos", "formula_version"))
        print(f"PostgreSQL → API → CSV: {metrica} {tipo}, {len(esperado)} filas idénticas")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lote", type=Path)
    parser.add_argument("fuente", type=Path, help="Directorio con descargas independientes real.html y nominal.html")
    parser.add_argument("originales", type=Path, help="Directorio con originales de la ingesta")
    parser.add_argument("--api", help="URL base local, incluido /api/v1")
    args = parser.parse_args()
    lote = json.loads(args.lote.read_text(encoding="utf-8"))
    auditar_lote(lote, args.fuente, args.originales)
    if args.api:
        auditar_api(lote, args.api)


if __name__ == "__main__":
    main()
