import csv
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=os.getenv('CT_CHROMIUM'))
    page = browser.new_page(viewport={'width': 1280, 'height': 900}, accept_downloads=True)
    errors = []
    page.on('pageerror', lambda exception: errors.append(str(exception)))
    response = page.goto(os.getenv('CT_WEB_URL', 'http://127.0.0.1:5173/'))
    assert response and response.ok
    expect(page.get_by_role('heading', name='Comparador de PIB')).to_be_visible()
    expect(page.get_by_text('Datos sintéticos', exact=True)).to_be_visible()
    expect(page.get_by_role('checkbox', name='Aysén', exact=True)).to_be_checked()
    expect(page.get_by_role('checkbox', name='Incluir referencia de Chile')).to_be_checked()
    page.get_by_role('button', name='Seleccionar todas').click()
    expect(page.get_by_role('list', name='PIB real por región en 2025').get_by_role('listitem')).to_have_count(17)
    page.get_by_role('button', name='Tabla y procedencia').click()
    expect(page.get_by_role('row')).to_have_count(18)
    page.get_by_role('button', name='Ver procedencia de Aysén').click()
    expect(page.get_by_role('dialog')).to_contain_text('prueba-local')
    page.keyboard.press('Escape')
    expect(page.get_by_role('dialog')).not_to_be_visible()
    with page.expect_download() as item:
        page.get_by_role('button', name='Descargar CSV').click()
    download = item.value
    assert download.suggested_filename == 'pib-prueba-local-2025.csv'
    with Path(download.path()).open(encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 17
    assert all(row['publicacion'] == 'prueba-local' for row in rows)
    page.get_by_label('Indicador').select_option('participacion')
    expect(page.get_by_role('checkbox', name='Incluir referencia de Chile')).to_be_disabled()
    expect(page.get_by_role('row')).to_have_count(17)
    page.get_by_label('Origen de los datos').select_option('official')
    expect(page.get_by_text('Aún no hay publicaciones oficiales disponibles.', exact=False)).to_be_visible()
    expect(page.get_by_text('Datos sintéticos', exact=True)).not_to_be_visible()
    page.get_by_label('Origen de los datos').select_option('demo')
    page.get_by_role('link', name='Metodología', exact=True).click()
    expect(page.get_by_role('heading', name='Metodología')).to_be_visible()
    page.get_by_role('link', name='Volver al comparador').click()
    expect(page.get_by_role('heading', name='Comparador de PIB')).to_be_visible()
    page.set_viewport_size({'width': 360, 'height': 800})
    expect(page.get_by_role('table')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth === window.innerWidth')
    assert not errors, errors
    browser.close()
    print('Chromium: 16 regiones + Chile, participación, procedencia, CSV fijo, modo oficial aislado, navegación y móvil sin desplazamiento global.')
