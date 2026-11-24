"""Genera un lote de PIB anual a partir de dos cuadros públicos del BCCh."""

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen

from analytics.territorial.pib import crecimiento, participacion

_RAIZ = "https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_CCNN/MN_CCNN76/"
_CUADROS = {
    "real": "CCNN2018_PIB_REGIONAL",
    "nominal": "CCNN2018_PIB_REGIONAL_N/637899740344107786",
}
_TERRITORIOS = ("CL", *(f"{codigo:02}" for codigo in range(1, 17)))
_FUENTE = "BCCh-BDE"
_UNIDAD = "millones CLP"
_NUMERO = re.compile(r"-?(?:[0-9]{1,3}(?:\.[0-9]{3})+|[0-9]+)")


class CuadroBDE(HTMLParser):
    """Lee texto de celdas y atributos de serie sin interpretar JavaScript."""

    def __init__(self, documento):
        super().__init__()
        self.titulo = ""
        self.filas = []
        self._en_tabla = False
        self._fila = None
        self._celda = None
        self.feed(documento)
        self.close()

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "legend" and attrs.get("id") == "lgCuadro":
            self.titulo = attrs["data-descname"]
        if tag == "table" and attrs.get("id") == "grilla":
            self._en_tabla = True
        if not self._en_tabla:
            return
        if tag == "tr":
            self._fila = {"atributos": {}, "celdas": []}
        elif tag in {"td", "th"} and self._fila is not None:
            self._celda = []
        elif tag == "input" and attrs.get("class") == "chkGrid" and self._fila is not None:
            self._fila["atributos"] = attrs

    def handle_data(self, data):
        if self._celda is not None:
            self._celda.append(data)

    def handle_endtag(self, tag):
        if tag == "table" and self._en_tabla:
            self._en_tabla = False
        if not self._en_tabla:
            return
        if tag in {"td", "th"} and self._celda is not None:
            self._fila["celdas"].append("".join(self._celda).strip())
            self._celda = None
        elif tag == "tr" and self._fila is not None:
            self.filas.append(self._fila)
            self._fila = None


def leer_cuadro(raw, valoracion):
    cuadro = CuadroBDE(raw.decode("utf-8-sig"))
    real = valoracion == "real"
    medicion = "volumen a precios del año anterior encadenado" if real else "precios corrientes"
    unidad = "(miles de millones de pesos encadenados)" if real else "(miles de millones de pesos)"
    if not all(t in cuadro.titulo for t in (medicion, unidad, "referencia 2018")) or not cuadro.filas:
        raise ValueError(f"Título o tabla incompatible para {valoracion}")
    _, _, *anios = cuadro.filas[0]["celdas"]
    anios = tuple(int(anio) for anio in anios)
    if not anios or anios[0] != 2013 or anios != tuple(range(2013, anios[-1] + 1)):
        raise ValueError(f"Períodos anuales no consecutivos desde 2013 para {valoracion}")

    marca = "R" if real else "N"
    regional = re.compile(rf"F035\.PIB\.FLU\.{marca}\.CLP\.2018\.Z\.Z\.Z\.(0[1-9]|1[0-6])\.0\.[AT]")
    nacional = re.compile(rf"F032\.PIB\.FLU\.{marca}\.CLP\.EP18\.Z\.Z\.0\.[AT]")
    territorios = {}
    for fila in cuadro.filas[1:]:
        attrs = fila["atributos"]
        codigo = attrs["data-serie"]
        region = regional.fullmatch(codigo)
        if region is None and not nacional.fullmatch(codigo):
            continue
        territorio = region[1] if region is not None else "CL"
        if territorio in territorios or attrs["data-decimales"] != "0" or attrs["data-calc"] != "NONE":
            raise ValueError(f"Serie duplicada o presentación incompatible en {valoracion}: {codigo}")
        _, titulo, *valores = fila["celdas"]
        if len(valores) != len(anios) or not all(_NUMERO.fullmatch(valor) for valor in valores):
            raise ValueError(f"Períodos incompletos o valor irreconocible en {valoracion}: {codigo}")
        territorios[territorio] = (codigo, titulo, valores)
    if territorios.keys() != set(_TERRITORIOS):
        raise ValueError(f"Faltan territorios en cuadro {valoracion}")
    return anios, territorios


def normalizar(originales, extraido):
    hashes = {tipo: hashlib.sha256(raw).hexdigest() for tipo, raw in originales.items()}
    huella = hashlib.sha256("".join(hashes[tipo] for tipo in _CUADROS).encode()).hexdigest()[:16]
    publicacion = f"bcch-bde-publico-{extraido[:10]}-{huella}"
    niveles = {}
    observaciones = []
    procedencias = []
    artefactos = []
    periodos = {}

    def registrar(territorio, anio, metrica, valoracion, valor, estado, clase, **procedencia):
        codigo = f"{publicacion}.{territorio}.{anio}.{metrica}.{valoracion}"
        fila = {
            "id": codigo, "territorio": territorio, "anio": anio,
            "metrica": metrica, "valoracion": valoracion, "valor": valor,
            "unidad": _UNIDAD if metrica == "nivel" else "%",
            "anio_referencia": 2018 if valoracion == "real" else None,
            "estado": estado, "clase": clase, "publicacion": publicacion,
        }
        observaciones.append(fila)
        procedencias.append({
            "observacion": codigo, "publicacion": publicacion,
            "serie_bde": None, "artefacto": None, "selector": None,
            "formula_version": None, "insumos": [], "motivo": None, **procedencia,
        })
        return fila

    for tipo, ruta in _CUADROS.items():
        artefacto = f"bde-pib-anual-{tipo}"
        artefactos.append({
            "id": artefacto, "fuente": _FUENTE, "url": _RAIZ + ruta,
            "sha256": hashes[tipo], "corte": None, "extraido_en": extraido,
        })
        anios, territorios = leer_cuadro(originales[tipo], tipo)
        periodos[tipo] = anios
        for territorio in _TERRITORIOS:
            codigo, titulo, valores = territorios[territorio]
            for anio, publicado in zip(anios, valores, strict=True):
                millones = str(int(publicado.replace(".", "")) * 1000)
                niveles[tipo, territorio, anio] = registrar(
                    territorio, anio, "nivel", tipo, millones, "informado", "oficial",
                    artefacto=artefacto, serie_bde=codigo,
                    selector=f"#grilla · {titulo} · {anio} · {publicado} miles de millones de pesos",
                )

    anios = periodos["real"]
    if anios != periodos["nominal"]:
        raise ValueError("Los períodos de los cuadros real y nominal difieren")

    for territorio in _TERRITORIOS:
        for anio in anios:
            resultado = crecimiento(niveles["real", territorio, anio], niveles.get(("real", territorio, anio - 1)))
            registrar(
                territorio, anio, "crecimiento", "real", resultado.valor, resultado.estado, resultado.clase,
                formula_version=resultado.formula_version, insumos=list(resultado.insumos), motivo=resultado.motivo,
            )
            if territorio != "CL":
                resultado = participacion(niveles["nominal", territorio, anio], niveles["nominal", "CL", anio])
                registrar(
                    territorio, anio, "participacion", "nominal", resultado.valor, resultado.estado, resultado.clase,
                    formula_version=resultado.formula_version, insumos=list(resultado.insumos), motivo=resultado.motivo,
                )

    return {
        "publicacion": {
            "id": publicacion, "fecha": extraido, "estado": "aprobada", "fuente": _FUENTE,
            "cobertura": {
                "esperadas": len(observaciones),
                "disponibles": sum(fila["valor"] is not None for fila in observaciones),
            },
            "cambios": [
                f"PIB anual 2013–{anios[-1]} de Chile y 16 regiones, Banco Central de Chile, BDE.",
                "Cuadros públicos con precisión de miles de millones de pesos; conversión exacta a millones de CLP.",
                "La fecha del corte local corresponde a la extracción. Los cuadros no indican fecha de revisión por celda.",
                "Crecimiento anual de 2013 no disponible por ausencia de niveles comparables de 2012 en estos cuadros.",
            ],
        },
        "artefactos": artefactos, "observaciones": observaciones, "procedencias": procedencias,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--insumos", type=Path, default=Path("data/raw/bde-pib-publico"))
    parser.add_argument("--salida", type=Path, default=Path("data/published/pib-bde-publico.json"))
    parser.add_argument("--reproducir", action="store_true", help="Lee archivos y fecha de extracción conservados")
    args = parser.parse_args()
    manifiesto = args.insumos / "extraccion.json"
    if args.reproducir:
        extraido = json.loads(manifiesto.read_text(encoding="utf-8"))["extraido_en"]
        originales = {tipo: (args.insumos / f"{tipo}.html").read_bytes() for tipo in _CUADROS}
    else:
        originales = {}
        for tipo, ruta in _CUADROS.items():
            with urlopen(_RAIZ + ruta, timeout=30) as response:
                originales[tipo] = response.read()
        extraido = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lote = normalizar(originales, extraido)
    salida = (json.dumps(lote, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.salida.exists() and args.salida.read_bytes() != salida:
        parser.error("La salida ya pertenece a otro lote. Indica otro nombre con --salida.")
    if not args.reproducir:
        args.insumos.mkdir(parents=True, exist_ok=False)
        for tipo, raw in originales.items():
            (args.insumos / f"{tipo}.html").write_bytes(raw)
        manifiesto.write_text(json.dumps({"extraido_en": extraido}) + "\n", encoding="utf-8")
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    if not args.salida.exists():
        with args.salida.open("xb") as archivo:
            archivo.write(salida)
    print(lote["publicacion"]["id"], lote["publicacion"]["cobertura"])


if __name__ == "__main__":
    main()
