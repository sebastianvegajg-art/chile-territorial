"""Exporta un snapshot oficial compacto (solo lectura, cero secretos) para la
función serverless de Netlify (`netlify/functions/api.mjs`).

Reutiliza exactamente los mismos motores verificados de FastAPI
(`apps/api/lote_oficial.py`, `apps/api/aysen_piloto.py`, `apps/api/fase2.py`)
sobre los cortes oficiales locales en `data/published/` y `data/raw/`.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from apps.api import aysen_piloto as ap
from apps.api import fase2
from apps.api.lote_oficial import LoteOficial

SALIDA = RAIZ / "netlify" / "functions" / "data" / "snapshot-oficial.json"


def main() -> int:
    lote_path = RAIZ / "data" / "published" / "pib-bde-api.json"
    if not lote_path.exists():
        lote_path = RAIZ / "data" / "published" / "pib-bde-publico.json"
    lote = LoteOficial.desde_archivo(str(lote_path))

    pubs = lote.publicaciones()
    pub_id = pubs[0]["id"]
    territorios = lote.territorios()
    codigos_todos = [t["codigo"] for t in territorios]
    codigos_reg = [t["codigo"] for t in territorios if t["codigo"] != "CL"]

    observaciones = []
    for metrica, valoracion, codes in (
        ("nivel", "real", codigos_todos),
        ("nivel", "nominal", codigos_todos),
        ("crecimiento", "real", codigos_todos),
        ("participacion", "nominal", codigos_reg),
    ):
        observaciones.extend(lote.observaciones(pub_id, codes, 2013, 2026, metrica, valoracion))

    procedencias = {}
    for obs in observaciones:
        pr = lote.procedencia(obs["id"])
        if pr is not None:
            procedencias[obs["id"]] = pr

    # Aysén: Resumen, Economía, Presupuestos y Proyectos
    anios = list(range(2013, 2027))
    comunas_cut = [c["cut"] for c in ap.COMUNAS_AYSEN_LISTA]

    aysen_resumen: dict[str, dict] = {}
    aysen_economia: dict[str, dict] = {}
    aysen_presupuestos: dict[str, dict] = {}

    for yr in anios:
        aysen_economia[str(yr)] = ap.aysen_economia(anio=yr)
        aysen_resumen[f"{yr}:"] = ap.aysen_resumen(anio=yr, comuna="")
        # Para 2018–2026 precalculamos las 10 comunas completas en presupuestos (y 2024–2026 en resumen)
        if yr >= 2018:
            for cut in comunas_cut:
                if yr >= 2022:
                    aysen_resumen[f"{yr}:{cut}"] = ap.aysen_resumen(anio=yr, comuna=cut)
                aysen_presupuestos[f"{yr}:{cut}"] = ap.aysen_presupuestos(anio=yr, comuna=cut)
        else:
            aysen_presupuestos[f"{yr}:11201"] = ap.aysen_presupuestos(anio=yr, comuna="11201")

    aysen_proyectos_por_anio: dict[str, dict] = {}
    for yr in range(2021, 2027):
        aysen_proyectos_por_anio[str(yr)] = ap.aysen_proyectos(anio=yr, comuna="", institucion="", q="")
    aysen_proyectos_2026 = aysen_proyectos_por_anio["2026"]

    # Fase 2: Sectorial 16 regiones, Demografía INE + PIB per cápita y Cruces
    sectorial_por_anio: dict[str, dict] = {}
    demografia_por_anio: dict[str, dict] = {}
    for yr in range(2013, 2026):
        sectorial_por_anio[str(yr)] = fase2.sectorial_regiones(anio=yr)
        demografia_por_anio[str(yr)] = fase2.demografia_poblacion(anio=yr)

    cruces_data = fase2.cruces_resumen()
    cruces_por_anio = {
        "2025": cruces_data,
        "2026": cruces_data,
    }

    snapshot = {
        "generado_desde": pub_id,
        "territorios": territorios,
        "publicaciones": pubs,
        "observaciones": observaciones,
        "procedencias": procedencias,
        "aysen_resumen": aysen_resumen,
        "aysen_economia": aysen_economia,
        "aysen_presupuestos": aysen_presupuestos,
        "aysen_proyectos_base": aysen_proyectos_2026,
        "aysen_proyectos_por_anio": aysen_proyectos_por_anio,
        "sectorial_regiones": sectorial_por_anio,
        "demografia_poblacion": demografia_por_anio,
        "cruces_resumen": cruces_por_anio,
    }

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
    SALIDA.write_text(texto, encoding="utf-8")
    print(f"Snapshot oficial exportado en {SALIDA} ({len(texto):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
