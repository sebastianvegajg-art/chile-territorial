"""Comprueba el corte oficial en Chromium, en web y opcionalmente sin conexión."""

import argparse
import csv
from decimal import Decimal, ROUND_HALF_UP
import json
import os
from pathlib import Path
import re

from playwright.sync_api import expect, sync_playwright


def auditar(browser, url, lote, offline):
    contexto = browser.new_context(
        accept_downloads=True, offline=offline, viewport={"width": 1280, "height": 900},
    )
    page = contexto.new_page()
    errores = []
    page.on("pageerror", lambda error: errores.append(str(error)))
    if offline:
        page.set_content(url.read_text(encoding="utf-8"))
    else:
        page.goto(url)
    expect(page.get_by_role("heading", name="Comparador de PIB")).to_be_visible()
    expect(page.get_by_role("img", name=re.compile("PIB real, 2013 a 2025"))).to_be_visible()
    expect(page.get_by_text("Datos sintéticos", exact=True)).to_have_count(0)
    page.keyboard.press("Tab")
    expect(page.get_by_role("link", name="Ir al contenido principal")).to_be_focused()
    page.get_by_role("button", name="Seleccionar todas").click()
    expect(page.get_by_role("list", name="Series del gráfico").get_by_role("listitem")).to_have_count(17)
    page.get_by_role("button", name="Tabla y procedencia").click()
    expect(page.get_by_role("table").get_by_role("row")).to_have_count(222)
    origen = page.get_by_role("button", name="Ver procedencia de Aysén del General Carlos Ibáñez del Campo en 2025")
    origen.click()
    detalle = page.get_by_role("dialog")
    expect(detalle).to_contain_text("F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.T")
    corte = lote["publicacion"]["id"]
    expect(detalle).to_contain_text(corte)
    page.keyboard.press("Escape")
    expect(detalle).not_to_be_visible()
    expect(origen).to_be_focused()

    with page.expect_download() as evento:
        page.get_by_role("button", name="Descargar CSV").click()
    with Path(evento.value.path()).open(encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    esperadas = {x["id"]: x["valor"] for x in lote["observaciones"]
                 if (x["metrica"], x["valoracion"]) == ("nivel", "real")}
    assert len(filas) == len(esperadas) == 221
    assert {x["id"]: x["valor"] for x in filas} == esperadas
    assert {x["publicacion"] for x in filas} == {corte}

    page.get_by_label("Indicador").select_option("crecimiento")
    expect(page.get_by_role("table").get_by_text("Sin dato", exact=True)).to_have_count(17)
    page.get_by_role("button", name="Ranking 2025").click()
    ranking = page.get_by_role("list", name="Crecimiento real por región en 2025").get_by_role("listitem")
    expect(ranking).to_have_count(17)
    expect(ranking.first).to_contain_text("1. Atacama")
    expect(ranking.nth(15)).to_contain_text("16. Tarapacá")

    page.get_by_label("Indicador").select_option("indice")
    page.get_by_role("button", name="Tabla y procedencia").click()
    page.get_by_role("combobox", name="Desde", exact=True).select_option("2018")
    niveles = {(x["territorio"], x["anio"]): Decimal(x["valor"]) for x in lote["observaciones"]
                if (x["metrica"], x["valoracion"]) == ("nivel", "real")}
    with page.expect_download() as evento:
        page.get_by_role("button", name="Descargar CSV").click()
    with Path(evento.value.path()).open(encoding="utf-8") as archivo:
        indices = list(csv.DictReader(archivo))
    assert len(indices) == 136
    for fila in indices:
        territorio, anio = fila["territorio"], int(fila["anio"])
        valor = (100 * niveles[territorio, anio] / niveles[territorio, 2018]).quantize(
            Decimal("0.00000001"), rounding=ROUND_HALF_UP,
        )
        assert Decimal(fila["valor"]) == valor
        assert fila["anio_base"] == "2018" and fila["publicacion"] == corte
        assert Decimal(fila["nivel_real_actual"]) == niveles[territorio, anio]
        assert Decimal(fila["nivel_real_base"]) == niveles[territorio, 2018]

    page.set_viewport_size({"width": 360, "height": 800})
    expect(page.get_by_role("table")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth === window.innerWidth")
    page.get_by_role("link", name="Metodología", exact=True).click()
    expect(page.get_by_role("heading", name="Metodología")).to_be_visible()
    assert not errores, errores
    contexto.close()
    print(f"Chromium {'sin conexión' if offline else 'web'}: 17 series, 221 niveles CSV, 136 índices, procedencia, ranking, teclado y móvil.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lote", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:5173/")
    parser.add_argument("--html", type=Path)
    args = parser.parse_args()
    lote = json.loads(args.lote.read_text(encoding="utf-8"))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.getenv("CT_CHROMIUM"))
        auditar(browser, args.url, lote, offline=False)
        if args.html:
            auditar(browser, args.html, lote, offline=True)
        browser.close()


if __name__ == "__main__":
    main()
