"""API de lectura de Chile Territorial."""
import csv
import io
import json
import os
import re
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Path as PathParameter, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import demo
from .aysen_piloto import router as aysen_piloto_router
from .conectores import router as conectores_router
from .fase2 import router as fase2_router
from .lote_oficial import LoteOficial

PREFIJO = "/api/v1"
ID = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
CODIGO = re.compile(r"^(CL|0[1-9]|1[0-6])$")
CAMPOS = ("id", "territorio", "anio", "metrica", "valoracion", "valor", "unidad",
          "anio_referencia", "estado", "clase", "publicacion")


class Repositorio:
    def __init__(self, demo_activa=False, lote_oficial=None):
        self.demo = bool(demo_activa)
        self.lote = None if self.demo or lote_oficial is None else LoteOficial.desde_archivo(lote_oficial)

    @staticmethod
    def consulta(sql, valores=()):
        url = os.getenv("DATABASE_URL")
        if not url:
            raise HTTPException(503, "Configura la conexión de lectura de PostgreSQL.")
        import psycopg
        from psycopg.rows import dict_row

        try:
            with psycopg.connect(url, row_factory=dict_row, connect_timeout=4) as connection:
                return connection.execute(sql, valores).fetchall()
        except psycopg.Error:
            raise HTTPException(503, "La publicación de datos no está disponible temporalmente.") from None

    def territorios(self):
        if self.demo:
            return demo.territorios()
        if self.lote is not None:
            return self.lote.territorios()
        return self.consulta("SELECT * FROM pib.api_territorio ORDER BY codigo")

    def publicaciones(self):
        if self.demo:
            return [demo.PUBLICACION]
        if self.lote is not None:
            return self.lote.publicaciones()
        return self.consulta(
            "SELECT * FROM pib.api_publicacion WHERE estado = 'aprobada' ORDER BY fecha DESC, id DESC"
        )

    def observaciones(self, cut, codes, start, end, metric, valuation):
        if self.demo:
            return sorted(
                (row for row in demo.FILAS if row["territorio"] in codes and start <= row["anio"] <= end
                 and row["metrica"] == metric and row["valoracion"] == valuation),
                key=lambda row: (row["anio"], row["territorio"]),
            )
        if self.lote is not None:
            return self.lote.observaciones(cut, codes, start, end, metric, valuation)
        rows = self.consulta(
            """SELECT o.* FROM pib.api_observacion o
               JOIN pib.api_publicacion p ON p.id = o.publicacion AND p.estado = 'aprobada'
               WHERE o.publicacion = %s AND o.territorio = ANY(%s) AND o.anio BETWEEN %s AND %s
                 AND o.metrica = %s AND o.valoracion = %s ORDER BY o.anio, o.territorio""",
            (cut, codes, start, end, metric, valuation),
        )
        return [{field: row[field] for field in CAMPOS} for row in rows]

    def procedencia(self, key):
        if self.demo:
            return demo.FUENTES.get(key)
        if self.lote is not None:
            return self.lote.procedencia(key)
        rows = self.consulta(
            """SELECT x.* FROM pib.api_procedencia x
               JOIN pib.api_publicacion p ON p.id = x.publicacion AND p.estado = 'aprobada'
               WHERE x.observacion = %s""", (key,),
        )
        return next(iter(rows), None)


def crear_app(demo_activa=False, lote_oficial=None):
    raiz_repo = Path(__file__).resolve().parents[2]
    if not demo_activa and lote_oficial is None and not os.getenv("DATABASE_URL"):
        env_lote = (os.getenv("CT_LOTE_OFICIAL") or "").strip()
        if env_lote:
            lote_oficial = env_lote
        elif os.getenv("CT_AUTODETECTAR_LOTE") == "1":
            for cand in (
                raiz_repo / "data" / "published" / "pib-bde-api.json",
                raiz_repo / "data" / "published" / "pib-bde-publico.json",
            ):
                if cand.exists():
                    lote_oficial = str(cand)
                    break
    app = FastAPI(title="Chile Territorial · PIB")
    cors_env = (os.getenv("CT_CORS_ORIGINS") or "").strip()
    if cors_env:
        origenes = [o.strip().rstrip("/") for o in cors_env.split(",") if o.strip()]
        if origenes:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=origenes,
                allow_credentials=False,
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=["Content-Type", "Accept"],
            )
    repo = Repositorio(demo_activa=demo_activa, lote_oficial=lote_oficial)
    contrato = raiz_repo / "contracts/openapi.json"
    app.openapi = lambda: json.loads(contrato.read_text(encoding="utf-8"))

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        pub_dir = raiz_repo / "data" / "published"
        raw_dir = raiz_repo / "data" / "raw"
        return {
            "estado": "ok",
            "servicio": "chile-territorial-api",
            "modo": "demo" if repo.demo else ("lote_oficial" if repo.lote is not None else "postgres"),
            "datos_publicados": {
                "pib_api": (pub_dir / "pib-bde-api.json").exists(),
                "pib_publico": (pub_dir / "pib-bde-publico.json").exists(),
                "sectorial_416": (pub_dir / "pib-sectorial-16-regiones.json").exists(),
                "poblacion_ine": (pub_dir / "poblacion-ine-regiones.json").exists(),
                "sinim_aysen": (pub_dir / "sinim-aysen-oficial.json").exists(),
                "proyectos_mop": (pub_dir / "proyectos-mop-aysen.json").exists(),
                "dipres_2025": (raw_dir / "dipres-piloto-2025.json").exists(),
                "dipres_2026": (raw_dir / "dipres-piloto-2026.json").exists(),
            },
        }

    @app.exception_handler(HTTPException)
    async def error(_: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={
            "codigo": {404: "no_encontrado", 422: "filtros_invalidos", 503: "datos_no_disponibles"}.get(
                exc.status_code, "error"
            ), "mensaje": exc.detail,
        })

    @app.exception_handler(RequestValidationError)
    async def validacion(request: Request, _: RequestValidationError):
        return await error(request, HTTPException(422, "Revisa los parámetros de la consulta."))

    @app.get(PREFIJO + "/territorios")
    def territorios():
        return repo.territorios()

    @app.get(PREFIJO + "/publicaciones")
    def publicaciones():
        return repo.publicaciones()

    def consultar(codes, start, end, valuation, metric, publication):
        if start > end or end - start >= 100:
            raise HTTPException(422, "El intervalo debe estar ordenado y abarcar hasta 100 años.")
        if (metric == "crecimiento" and valuation != "real") or (
            metric == "participacion" and valuation != "nominal"
        ):
            raise HTTPException(422, "La métrica no corresponde a la valoración seleccionada.")
        if codes is None:
            codes = [f"{n:02}" for n in range(1, 17)]
            if metric != "participacion":
                codes.append("CL")
        if (len(set(codes)) != len(codes) or any(not CODIGO.fullmatch(code) for code in codes)
                or (metric == "participacion" and "CL" in codes)):
            raise HTTPException(422, "Revisa los códigos territoriales para la métrica seleccionada.")
        cut = next((p["id"] for p in repo.publicaciones() if not publication or p["id"] == publication), None)
        if cut is None:
            raise HTTPException(404, "No se encontró la publicación solicitada.")
        return cut, repo.observaciones(cut, codes, start, end, metric, valuation)

    Anio = Annotated[int, Query(ge=2013, le=9999)]
    Valoracion = Literal["real", "nominal"]
    Metrica = Literal["nivel", "crecimiento", "participacion"]
    Codigos = Annotated[list[str] | None, Query(min_length=1, max_length=17)]
    Publicacion = Annotated[str | None, Query(pattern=ID)]

    @app.get(PREFIJO + "/pib")
    def pib(response: Response, anio_desde: Anio, anio_hasta: Anio, valoracion: Valoracion,
            metrica: Metrica = "nivel", territorios: Codigos = None, publicacion: Publicacion = None,
            pagina: Annotated[int, Query(ge=1)] = 1, limite: Annotated[int, Query(ge=1, le=500)] = 100):
        cut, rows = consultar(territorios, anio_desde, anio_hasta, valoracion, metrica, publicacion)
        offset = (pagina - 1) * limite
        response.headers["X-Publicacion"] = cut
        return dict(publicacion=cut, pagina=pagina, limite=limite, total=len(rows),
                    datos=rows[offset:offset + limite])

    @app.get(PREFIJO + "/pib.csv")
    def pib_csv(anio_desde: Anio, anio_hasta: Anio, valoracion: Valoracion,
                metrica: Metrica = "nivel", territorios: Codigos = None, publicacion: Publicacion = None):
        cut, rows = consultar(territorios, anio_desde, anio_hasta, valoracion, metrica, publicacion)
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=CAMPOS)
        writer.writeheader()
        writer.writerows(rows)
        return Response(buffer.getvalue(), media_type="text/csv",
                        headers={"X-Publicacion": cut, "Content-Disposition": 'attachment; filename="pib.csv"'})

    @app.get(PREFIJO + "/observaciones/{id}/procedencia")
    def procedencia(id: Annotated[str, PathParameter(pattern=ID)]):
        value = repo.procedencia(id)
        if value is None:
            raise HTTPException(404, "No se encontró la observación solicitada.")
        return value

    app.include_router(conectores_router)
    app.include_router(fase2_router)
    app.include_router(aysen_piloto_router)

    return app


app = crear_app(demo_activa=os.getenv("CT_MODO") == "demo")
