"""Prepara los cortes oficiales de datos para el despliegue del backend FastAPI.

Uso recomendado en el build o arranque de producción (Render / Railway / Docker):
    python infra/preparar-datos-oficiales.py --solo-faltantes

Reglas de integridad y seguridad:
- Las credenciales del Banco Central (BCCH_API_TOKEN o BCCH_API_USER/BCCH_API_PASS)
  se leen estrictamente desde variables de entorno del servidor; nunca se imprimen.
- Si una fuente externa falla temporalmente, informa la brecha sin tumbar el resto
  de los cortes oficiales ni inventar cifras.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

RAIZ = Path(__file__).resolve().parents[1]
PUB = RAIZ / "data" / "published"
RAW = RAIZ / "data" / "raw"


def _tiene_credenciales_bcch() -> bool:
    return bool(
        (os.getenv("BCCH_API_TOKEN") or "").strip()
        or ((os.getenv("BCCH_API_USER") or "").strip() and (os.getenv("BCCH_API_PASS") or "").strip())
    )


def _correr_modulo(modulo: str, args: list[str], descripcion: str) -> bool:
    print(f"[datos-oficiales] Ejecutando: {descripcion}...", flush=True)
    cmd = [sys.executable, "-m", modulo, *args]
    res = subprocess.run(cmd, cwd=str(RAIZ), check=False)
    if res.returncode == 0:
        print(f"[datos-oficiales] OK: {descripcion}", flush=True)
        return True
    print(f"[datos-oficiales] AVISO (código {res.returncode}): no se pudo actualizar {descripcion}", flush=True)
    return False


def _preparar_dipres_piloto(solo_faltantes: bool) -> bool:
    sys.path.insert(0, str(RAIZ))
    try:
        from pipelines.fiscal.dipres_ckan import obtener_presupuestos_piloto_live
    except Exception as exc:
        print(f"[datos-oficiales] AVISO: no se pudo importar dipres_ckan: {exc}", flush=True)
        return False

    ok_todos = True
    for anio in (2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018):
        destino = RAW / f"dipres-piloto-{anio}.json"
        if solo_faltantes and destino.exists():
            print(f"[datos-oficiales] Conservando corte existente: {destino.name}", flush=True)
            continue
        try:
            print(f"[datos-oficiales] Descargando DIPRES CKAN piloto {anio}...", flush=True)
            obtener_presupuestos_piloto_live(anio=anio, refresh=not solo_faltantes)
            print(f"[datos-oficiales] OK: DIPRES piloto {anio}", flush=True)
        except Exception as exc:
            print(f"[datos-oficiales] AVISO: DIPRES piloto {anio} no disponible ahora ({exc})", flush=True)
            ok_todos = False
    return ok_todos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepara cortes oficiales para despliegue de Chile Territorial.")
    parser.add_argument(
        "--solo-faltantes",
        action="store_true",
        help="No vuelve a descargar archivos que ya existen en data/published o data/raw.",
    )
    parser.add_argument(
        "--estricto",
        action="store_true",
        help="Devuelve código de salida 1 si alguna fuente oficial no pudo actualizarse.",
    )
    args = parser.parse_args(argv)

    PUB.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)

    fallos: list[str] = []
    con_token = _tiene_credenciales_bcch()

    # 1. PIB Nacional y 16 Regiones (API oficial BCCh si hay credenciales; si no, cuadros públicos BDE)
    if con_token:
        if not (args.solo_faltantes and (PUB / "pib-bde-api.json").exists()):
            if not _correr_modulo("pipelines.economia.bde_api", ["--completo"], "PIB oficial BCCh API (34 series)"):
                fallos.append("pib_bcch_api")
        if not (args.solo_faltantes and (PUB / "pib-sectorial-16-regiones.json").exists()):
            if not _correr_modulo("pipelines.economia.bde_sectorial", [], "PIB sectorial 16 regiones (416 series)"):
                fallos.append("pib_sectorial")
        if not (args.solo_faltantes and (PUB / "poblacion-ine-regiones.json").exists()):
            if not _correr_modulo("pipelines.demografia.ine_poblacion", [], "Población INE 16 regiones + Chile (17 series)"):
                fallos.append("poblacion_ine")
    else:
        print(
            "[datos-oficiales] Sin BCCH_API_TOKEN en el entorno: usando cuadros públicos BDE para PIB "
            "(agrega BCCH_API_TOKEN en Render/Railway para habilitar 416 series sectoriales e INE).",
            flush=True,
        )
        if not (args.solo_faltantes and (PUB / "pib-bde-publico.json").exists()):
            if not _correr_modulo("pipelines.economia.bde_publico", [], "PIB oficial BDE público"):
                fallos.append("pib_bde_publico")

    # 2. SINIM 10 comunas de Aysén (histórico 2018–2025 + ficha comunal)
    if not (args.solo_faltantes and (PUB / "sinim-aysen-historico.json").exists()):
        if not _correr_modulo("pipelines.fiscal.sinim_datos_live", [], "SINIM histórico 2018–2025 (10 comunas Aysén)"):
            fallos.append("sinim_aysen_historico")
    if not (args.solo_faltantes and (PUB / "sinim-aysen-oficial.json").exists()):
        if not _correr_modulo("pipelines.fiscal.sinim_ficha_live", [], "SINIM fichas comunales (10 comunas Aysén)"):
            fallos.append("sinim_aysen")

    # 3. MOP DGOP + DIPRES Subt. 31 BIP proyectos en Aysén (2021–2026)
    if not (args.solo_faltantes and (PUB / "proyectos-mop-aysen.json").exists()):
        if not _correr_modulo("pipelines.inversion.mop_proyectos", [], "MOP DGOP contratos de obras Aysén"):
            fallos.append("mop_aysen")
    if not (args.solo_faltantes and (PUB / "proyectos-bip-aysen.json").exists()):
        if not _correr_modulo("pipelines.inversion.dipres_bip_live", [], "DIPRES Subt. 31 iniciativas BIP Aysén (2021–2026)"):
            fallos.append("dipres_bip_aysen")

    # 4. Mercado laboral INE ENE (BCCh SI3) + SII Estadísticas de Empresas (2013–2025)
    if con_token and not (args.solo_faltantes and (PUB / "mercado-laboral-sii-ine.json").exists()):
        if not _correr_modulo("pipelines.laboral.mercado_laboral_live", [], "Mercado laboral INE ENE + SII Empresas"):
            fallos.append("mercado_laboral_sii_ine")

    # 5. DIPRES CKAN piloto (2018–2026)
    if not _preparar_dipres_piloto(solo_faltantes=args.solo_faltantes):
        fallos.append("dipres_piloto")

    if fallos:
        print(f"[datos-oficiales] Completado con avisos en: {', '.join(fallos)}", flush=True)
        return 1 if args.estricto else 0

    print("[datos-oficiales] Todos los cortes oficiales quedaron listos.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
