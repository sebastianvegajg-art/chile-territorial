"""Verificar el catálogo anual y las cuatro series de referencia de la BDE."""

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import os
from pathlib import Path
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import quote, quote_plus, urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


ENDPOINT = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
MAX_BYTES = 20 * 1024 * 1024
REFERENCE = (
    "F032.PIB.FLU.R.CLP.HIST18.Z.Z.0.A",
    "F032.PIB.FLU.N.CLP.HIST18.Z.Z.0.A",
    "F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.A",
    "F035.PIB.FLU.N.CLP.2018.Z.Z.Z.11.0.A",
)


class VerificationError(Exception):
    """Error apto para mostrar sin revelar URL autenticada ni cuerpo."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def download(token, function, **params):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    query = urlencode({"token": token, "function": function, **params})
    request = Request(f"{ENDPOINT}?{query}", headers={"Accept": "application/json"})
    for attempt in range(3):
        try:
            with opener.open(request, timeout=30) as response:
                body = response.read(MAX_BYTES + 1)
            break
        except HTTPError as error:
            failure = VerificationError(f"{function}: HTTP {error.code}.")
            transient = error.code in (429, 500, 502, 503, 504)
            error.close()
            if not transient or attempt == 2:
                raise failure from None
        except (URLError, OSError):
            if attempt == 2:
                raise VerificationError(f"{function}: error de conexión.") from None
        sleep(2 ** (attempt + 1))
    if len(body) > MAX_BYTES:
        raise VerificationError(f"{function}: respuesta supera el tamaño permitido.")
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError):
        raise VerificationError(f"{function}: respuesta JSON inválida.") from None
    response_text = json.dumps(payload, ensure_ascii=False)
    for representation in {token, quote(token, safe=""), quote_plus(token)}:
        if representation.encode() in body or representation in response_text:
            raise VerificationError(f"{function}: respuesta con credencial reflejada.")
    if not isinstance(payload, dict) or payload.get("Codigo") != 0:
        raise VerificationError(f"{function}: la BDE rechazó la consulta.")
    return body, payload


def annual_catalog(payload):
    rows = payload.get("SeriesInfos")
    if not isinstance(rows, list) or not rows:
        raise VerificationError("SearchSeries: catálogo anual vacío o inválido.")
    entries = {}
    for row in rows:
        if not isinstance(row, dict):
            raise VerificationError("SearchSeries: fila de catálogo inválida.")
        code = row.get("seriesId")
        if not isinstance(code, str) or not code or code in entries:
            raise VerificationError("SearchSeries: código ausente o duplicado.")
        if row.get("frequencyCode") != "ANNUAL" or not row.get("spanishTitle"):
            raise VerificationError("SearchSeries: metadatos anuales incompletos.")
        entries[code] = row
    missing = set(REFERENCE).difference(entries)
    if missing:
        raise VerificationError(f"Referencias ausentes del catálogo: {', '.join(sorted(missing))}.")
    return entries


def summarize_series(payload, code, first, last):
    series = payload.get("Series")
    if not isinstance(series, dict) or series.get("seriesId") != code:
        raise VerificationError(f"{code}: identidad de serie incorrecta.")
    rows = series.get("Obs")
    if not isinstance(rows, list) or not rows:
        raise VerificationError(f"{code}: observaciones vacías o inválidas.")
    years = set()
    numeric = 0
    statuses = {}
    for row in rows:
        try:
            observed = datetime.strptime(row["indexDateString"], "%d-%m-%Y").date()
            status = row["statusCode"]
            raw_value = row["value"]
        except (KeyError, TypeError, ValueError):
            raise VerificationError(f"{code}: observación mal formada.") from None
        if not first <= observed <= last or observed.year in years:
            raise VerificationError(f"{code}: período fuera de rango o año repetido.")
        if not isinstance(status, str) or not status:
            raise VerificationError(f"{code}: estado de observación inválido.")
        years.add(observed.year)
        statuses[status] = statuses.get(status, 0) + 1
        try:
            finite_value = Decimal(str(raw_value)).is_finite()
        except InvalidOperation:
            finite_value = False
        numeric += int(finite_value)
        if status == "OK" and not finite_value:
            raise VerificationError(f"{code}: observación OK sin valor numérico finito.")
    if not numeric:
        raise VerificationError(f"{code}: ninguna observación numérica finita.")
    return {
        "serie_bde": code,
        "observaciones": len(rows),
        "valores_numericos": numeric,
        "anios_presentes": sorted(years),
        "anios_sin_fila": sorted(set(range(first.year, last.year + 1)).difference(years)),
        "estados": statuses,
    }


def run(token, output, first, last):
    if first > last:
        raise VerificationError("El inicio del período debe preceder al final.")
    output.mkdir(mode=0o700)
    manifest = {
        "fuente": ENDPOINT,
        "extraido_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "desde": first.isoformat(),
        "hasta": last.isoformat(),
        "artefactos": [],
        "referencias": [],
    }

    def save(name, body):
        path = output / name
        path.write_bytes(body)
        manifest["artefactos"].append({"archivo": name, "sha256": sha256(body).hexdigest()})

    body, payload = download(token, "SearchSeries", frequency="ANNUAL")
    catalog = annual_catalog(payload)
    manifest["series_catalogo_anual"] = len(catalog)
    save("catalogo-anual.json", body)
    for code in REFERENCE:
        body, payload = download(
            token, "GetSeries", timeseries=code, firstdate=first.isoformat(), lastdate=last.isoformat()
        )
        summary = summarize_series(payload, code, first, last)
        summary["titulo_catalogo"] = catalog[code]["spanishTitle"]
        summary["frecuencia_catalogo"] = catalog[code]["frequencyCode"]
        summary["fecha_actualizacion_catalogo"] = catalog[code].get("updatedAt")
        name = f"{code}.json"
        save(name, body)
        manifest["referencias"].append({"archivo": name, **summary})
    (output / "manifiesto.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desde", type=date.fromisoformat, default=date(2013, 1, 1))
    parser.add_argument("--hasta", type=date.fromisoformat, default=date(2025, 12, 31))
    args = parser.parse_args()
    token = os.environ.get("BCCH_API_TOKEN", "").strip()
    if not token:
        parser.exit(2, "Verificación BDE pendiente: configure BCCH_API_TOKEN en el entorno.\n")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = Path(__file__).resolve().parents[2] / "data" / "raw" / f"bde-e01-{stamp}"
    try:
        run(token, output, args.desde, args.hasta)
    except VerificationError as error:
        parser.exit(1, f"{error}\n")
    except OSError:
        parser.exit(1, "No se pudo guardar la evidencia local de BDE.\n")
    print(f"Cuatro referencias verificadas. Evidencia local: {output.relative_to(output.parents[2])}.")


if __name__ == "__main__":
    main()
