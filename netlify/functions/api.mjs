import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const funcDir = dirname(fileURLToPath(import.meta.url));

let cachedSnapshot = null;
function getSnapshot() {
  if (!cachedSnapshot) {
    const candidates = [
      join(process.cwd(), "netlify", "functions", "data", "snapshot-oficial.json"),
      join(funcDir, "data", "snapshot-oficial.json"),
      "/var/task/netlify/functions/data/snapshot-oficial.json",
    ];
    const found = candidates.find((p) => existsSync(p));
    if (!found) {
      throw new Error(`No se encontró snapshot-oficial.json en: ${candidates.join(", ")}`);
    }
    cachedSnapshot = JSON.parse(readFileSync(found, "utf-8"));
  }
  return cachedSnapshot;
}

const COMUNAS_CUT = {
  "11101": "Coyhaique",
  "11102": "Lago Verde",
  "11201": "Aysén",
  "11202": "Cisnes",
  "11203": "Guaitecas",
  "11301": "Cochrane",
  "11302": "O’Higgins",
  "11303": "Tortel",
  "11401": "Chile Chico",
  "11402": "Río Ibáñez",
};

function normText(v) {
  return String(v ?? "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[’']/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

function resolveComunaCut(raw) {
  const s = String(raw ?? "").trim();
  if (!s) return "";
  if (COMUNAS_CUT[s]) return s;
  const n = normText(s).replace(/^(municipalidad de|comuna de|puerto)\s+/, "");
  for (const [cut, nombre] of Object.entries(COMUNAS_CUT)) {
    const nn = normText(nombre);
    if (n === nn || (cut === "11201" && (n === "aisen" || n === "aysen"))) return cut;
  }
  return null;
}

function toNum(v) {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function fmtCL(val, dec = 1) {
  return Number(val).toLocaleString("es-CL", {
    minimumFractionDigits: dec,
    maximumFractionDigits: dec,
  });
}

function jsonResponse(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "public, max-age=300",
      ...extraHeaders,
    },
  });
}

function errorResponse(status, codigo, mensaje) {
  return jsonResponse({ codigo, mensaje }, status, { "Cache-Control": "no-store" });
}

function filterProjects(base, url) {
  const anio = Number(url.searchParams.get("anio") || "2026");
  const comunaRaw = (url.searchParams.get("comuna") || "").trim();
  const institucion = (url.searchParams.get("institucion") || "").trim();
  const q = (url.searchParams.get("q") || "").trim();

  const cut = resolveComunaCut(comunaRaw);
  if (comunaRaw && cut === null) {
    return errorResponse(422, "filtros_invalidos", `La comuna '${comunaRaw}' no pertenece a la Región de Aysén.`);
  }
  const comunaNombre = cut ? COMUNAS_CUT[cut] : "";
  const comunaNorm = normText(comunaNombre);
  const instNorm = normText(institucion);
  const qNorm = normText(q);

  const filterList = (list) =>
    (list || []).filter((p) => {
      if (instNorm && !normText(p.institucion || "").includes(instNorm)) return false;
      if (comunaNorm) {
        const comunas = Array.isArray(p.comunas) ? p.comunas : [];
        const ok = comunas.some((c) => {
          const cn = normText(c).replace(/^(comuna de|puerto)\s+/, "");
          return cn === comunaNorm || cn.includes(comunaNorm) || (comunaNorm === "aysen" && (cn.includes("aisen") || cn.includes("aysen")));
        });
        if (!ok) return false;
      }
      if (qNorm) {
        const hay = normText(
          [
            p.nombre_proyecto,
            p.nombre_contrato,
            p.codigo_bip,
            p.id_contrato,
            p.contratista,
            p.institucion,
            ...(Array.isArray(p.comunas) ? p.comunas : []),
          ].join(" ")
        );
        if (!hay.includes(qNorm)) return false;
      }
      return true;
    });

  const doc = filterList(base.proyectos_documentados);
  const insuf = filterList(base.proyectos_informacion_insuficiente);
  const fechaCorte = anio >= 2026 ? "2026-03-11" : anio >= 2022 ? "2022-03-11" : "2018-03-11";

  let pagadoTotal = 0;
  let pagadoAnt = 0;
  let pagadoNuevo = 0;
  let contratosConPago = 0;
  let contratosAnt = 0;

  let presTotal = 0;
  let arrastreTotal = 0;
  let proysPres = 0;
  let proysArr = 0;

  for (const p of doc) {
    const pag = toNum(p.pagado_anio_millones);
    const fechaFirma = typeof p.fecha_contratacion === "string" ? p.fecha_contratacion : null;
    const esAnt = typeof p.firmado_antes_administracion_actual === "boolean" && anio >= 2026
      ? p.firmado_antes_administracion_actual
      : fechaFirma ? fechaFirma < fechaCorte : null;

    if (pag !== null && esAnt !== null) {
      contratosConPago += 1;
      pagadoTotal += pag;
      if (esAnt) {
        pagadoAnt += pag;
        contratosAnt += 1;
      } else {
        pagadoNuevo += pag;
      }
    }

    const comp = toNum(p.compromiso_anio_millones);
    const noa = normText(p.nuevo_o_arrastre);
    if (comp !== null && (noa === "arrastre" || noa === "nuevo")) {
      proysPres += 1;
      presTotal += comp;
      if (noa === "arrastre") {
        arrastreTotal += comp;
        proysArr += 1;
      }
    }
  }

  const pctP1 = pagadoTotal > 0 ? Number(((pagadoAnt / pagadoTotal) * 100).toFixed(2)) : null;
  const pctP2 = presTotal > 0 ? Number(((arrastreTotal / presTotal) * 100).toFixed(2)) : null;

  return jsonResponse({
    ...base,
    anio_seleccionado: anio,
    filtros_aplicados: {
      anio,
      comuna: cut ? { cut, nombre: comunaNombre } : null,
      institucion: institucion || null,
      q: q || null,
    },
    cobertura_anio:
      anio === base.anio_corte_archivo
        ? `Contratos documentados en ${anio}${comunaNombre ? ` para la comuna de ${comunaNombre}` : " en la Región de Aysén"}.`
        : `El corte MOP DGOP publicado corresponde al ejercicio ${base.anio_corte_archivo}; se muestran los contratos del corte oficial.`,
    pagos_contratos_anteriores: {
      pregunta: "De lo pagado este año, ¿cuánto corresponde a contratos firmados antes de que asumiera esta administración?",
      disponible: pctP1 !== null,
      fecha_corte_administracion: fechaCorte,
      porcentaje: pctP1 !== null ? pctP1.toFixed(2) : null,
      unidad: "%",
      monto_pagado_total_millones: contratosConPago > 0 ? pagadoTotal.toFixed(3) : null,
      monto_pagado_contratos_anteriores_millones: contratosConPago > 0 ? pagadoAnt.toFixed(3) : null,
      monto_pagado_contratos_nuevos_millones: contratosConPago > 0 ? pagadoNuevo.toFixed(3) : null,
      contratos_evaluados: contratosConPago,
      contratos_anteriores: contratosAnt,
      proyectos_excluidos_sin_dato: insuf.length,
      frase_ciudadana:
        pctP1 !== null
          ? `En ${anio}, el ${fmtCL(pctP1, 1)}% de lo pagado en obras documentadas (${fmtCL(pagadoAnt, 1)} de ${fmtCL(pagadoTotal, 1)} millones CLP) corresponde a contratos firmados antes del ${fechaCorte}.`
          : `Sin dato suficiente para calcular la proporción de pagos de contratos anteriores en ${anio}.`,
    },
    arrastre_presupuesto: {
      pregunta: "Del presupuesto de inversión de este año, ¿cuánto ya estaba comprometido por proyectos de años anteriores?",
      disponible: pctP2 !== null,
      porcentaje: pctP2 !== null ? pctP2.toFixed(2) : null,
      unidad: "%",
      presupuesto_inversion_anio_millones: proysPres > 0 ? presTotal.toFixed(3) : null,
      monto_arrastre_comprometido_millones: proysPres > 0 ? arrastreTotal.toFixed(3) : null,
      proyectos_evaluados: proysPres,
      proyectos_en_arrastre: proysArr,
      proyectos_excluidos_sin_dato: insuf.length,
      frase_ciudadana:
        pctP2 !== null
          ? `Del presupuesto de inversión ${anio} en obras documentadas (${fmtCL(presTotal, 1)} millones CLP), el ${fmtCL(pctP2, 1)}% (${fmtCL(arrastreTotal, 1)} millones CLP) ya estaba comprometido por arrastre de años anteriores.`
          : `Sin dato suficiente para calcular el arrastre presupuestario de inversión en ${anio}.`,
    },
    total_proyectos_filtrados: doc.length + insuf.length,
    total_documentados: doc.length,
    total_informacion_insuficiente: insuf.length,
    proyectos_documentados: doc,
    proyectos_informacion_insuficiente: insuf,
  });
}

function handlePibQuery(snap, url, asCsv = false) {
  const anioDesde = Number(url.searchParams.get("anio_desde") || "2013");
  const anioHasta = Number(url.searchParams.get("anio_hasta") || "2025");
  const valoracion = url.searchParams.get("valoracion") || "real";
  const metrica = url.searchParams.get("metrica") || "nivel";
  const pagina = Math.max(1, Number(url.searchParams.get("pagina") || "1"));
  const limite = Math.min(500, Math.max(1, Number(url.searchParams.get("limite") || "100")));
  const pubId = snap.publicaciones[0].id;
  const reqPub = url.searchParams.get("publicacion");
  if (reqPub && reqPub !== pubId) {
    return errorResponse(404, "no_encontrado", "No se encontró la publicación solicitada.");
  }

  let territorios = url.searchParams.getAll("territorios");
  if (territorios.length === 0) {
    territorios = snap.territorios.map((t) => t.codigo).filter((c) => metrica !== "participacion" || c !== "CL");
  }
  const setTerr = new Set(territorios);

  const rows = snap.observaciones
    .filter(
      (r) =>
        setTerr.has(r.territorio) &&
        r.anio >= anioDesde &&
        r.anio <= anioHasta &&
        r.metrica === metrica &&
        r.valoracion === valoracion
    )
    .sort((a, b) => a.anio - b.anio || a.territorio.localeCompare(b.territorio));

  if (asCsv) {
    const fields = [
      "id", "territorio", "anio", "metrica", "valoracion", "valor",
      "unidad", "anio_referencia", "estado", "clase", "publicacion",
    ];
    const lines = [
      fields.join(","),
      ...rows.map((r) =>
        fields
          .map((f) => {
            const val = String(r[f] ?? "");
            return /[,"\r\n]/.test(val) ? `"${val.replaceAll('"', '""')}"` : val;
          })
          .join(",")
      ),
    ];
    return new Response(lines.join("\r\n"), {
      status: 200,
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "X-Publicacion": pubId,
        "Content-Disposition": 'attachment; filename="pib.csv"',
      },
    });
  }

  const offset = (pagina - 1) * limite;
  return jsonResponse(
    {
      publicacion: pubId,
      pagina,
      limite,
      total: rows.length,
      datos: rows.slice(offset, offset + limite),
    },
    200,
    { "X-Publicacion": pubId }
  );
}

export default async (req) => {
  const url = new URL(req.url);
  const path = url.pathname;

  // Modo híbrido Opción 1: si se configura BACKEND_API_URL en Netlify, redirige en vivo al backend FastAPI (Render/Railway)
  const upstream = (globalThis.Netlify?.env?.get("BACKEND_API_URL") || process.env.BACKEND_API_URL || "")
    .trim()
    .replace(/\/+$/, "");
  if (upstream) {
    const target = `${upstream}${path}${url.search}`;
    const init = {
      method: req.method,
      headers: { Accept: req.headers.get("accept") || "application/json" },
    };
    if (req.method !== "GET" && req.method !== "HEAD") {
      init.body = await req.arrayBuffer();
      const ct = req.headers.get("content-type");
      if (ct) init.headers["Content-Type"] = ct;
    }
    const resp = await fetch(target, init);
    return new Response(resp.body, { status: resp.status, headers: resp.headers });
  }

  const snap = getSnapshot();

  if (path === "/healthz") {
    return jsonResponse({
      estado: "ok",
      servicio: "chile-territorial-netlify-api",
      modo: "snapshot_oficial_verificado",
      publicacion_pib: snap.generado_desde,
    });
  }

  if (path === "/api/v1/territorios") return jsonResponse(snap.territorios);
  if (path === "/api/v1/publicaciones") return jsonResponse(snap.publicaciones);
  if (path === "/api/v1/pib") return handlePibQuery(snap, url, false);
  if (path === "/api/v1/pib.csv") return handlePibQuery(snap, url, true);

  const procMatch = path.match(/^\/api\/v1\/observaciones\/([^/]+)\/procedencia$/);
  if (procMatch) {
    const id = decodeURIComponent(procMatch[1]);
    const entry = snap.procedencias[id];
    if (!entry) return errorResponse(404, "no_encontrado", "No se encontró la observación solicitada.");
    return jsonResponse(entry);
  }

  // Piloto Aysén (4 pestañas)
  if (path === "/api/v1/aysen/resumen") {
    const anio = Number(url.searchParams.get("anio") || "2025");
    const comunaRaw = (url.searchParams.get("comuna") || "").trim();
    const cut = resolveComunaCut(comunaRaw);
    if (comunaRaw && cut === null) {
      return errorResponse(422, "filtros_invalidos", `La comuna '${comunaRaw}' no corresponde a Aysén.`);
    }
    const data = snap.aysen_resumen[`${anio}:${cut}`] || snap.aysen_resumen[`${anio}:`];
    if (!data) return errorResponse(404, "no_encontrado", `Sin corte disponible para el año ${anio}.`);
    return jsonResponse(data);
  }

  if (path === "/api/v1/aysen/economia") {
    const anio = Number(url.searchParams.get("anio") || "2025");
    const data = snap.aysen_economia[String(anio)];
    if (!data) return errorResponse(404, "no_encontrado", `Sin corte económico disponible para el año ${anio}.`);
    return jsonResponse(data);
  }

  if (path === "/api/v1/aysen/presupuestos") {
    const anio = Number(url.searchParams.get("anio") || "2025");
    const comunaRaw = (url.searchParams.get("comuna") || "11201").trim();
    const cut = resolveComunaCut(comunaRaw);
    if (cut === null) {
      return errorResponse(422, "filtros_invalidos", `La comuna '${comunaRaw}' no corresponde a Aysén.`);
    }
    const data = snap.aysen_presupuestos[`${anio}:${cut || "11201"}`] || snap.aysen_presupuestos[`${anio}:11201`];
    if (!data) return errorResponse(404, "no_encontrado", `Sin corte presupuestario disponible para ${anio}.`);
    return jsonResponse(data);
  }

  if (path === "/api/v1/aysen/proyectos") {
    return filterProjects(snap.aysen_proyectos_base, url);
  }

  // Fase 2: Estructura 16 regiones, Demografía INE + PIB per cápita y Cruces
  if (path === "/api/v1/sectorial/regiones") {
    const anio = String(url.searchParams.get("anio") || "2025");
    const data = snap.sectorial_regiones[anio] || snap.sectorial_regiones["2025"];
    return jsonResponse(data);
  }

  if (path === "/api/v1/demografia/poblacion") {
    const anio = String(url.searchParams.get("anio") || "2025");
    const data = snap.demografia_poblacion[anio] || snap.demografia_poblacion["2025"];
    return jsonResponse(data);
  }

  if (path === "/api/v1/cruces/resumen") {
    const anio = String(url.searchParams.get("anio") || "2025");
    const data = snap.cruces_resumen[anio] || snap.cruces_resumen["2025"];
    return jsonResponse(data);
  }

  if (path === "/api/v1/fiscal/sinim/plantilla.csv") {
    const header = "cut,comuna,anio,ingresos_totales_millones,gasto_total_devengado_millones,gasto_personal_sub21_millones,gasto_bienes_servicios_sub22_millones";
    const rows = Object.entries(COMUNAS_CUT).map(([cut, nombre]) => `${cut},${nombre},2025,,,,`);
    return new Response([header, ...rows].join("\r\n"), {
      status: 200,
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": 'attachment; filename="plantilla_sinim_aysen.csv"',
      },
    });
  }

  if (path === "/api/v1/laboratorio/consultar" && req.method === "POST") {
    const body = await req.json().catch(() => ({}));
    const pregunta = String(body?.pregunta || "Análisis territorial de la Región de Aysén");
    const eco25 = snap.aysen_economia["2025"];
    const dem25 = snap.demografia_poblacion["2025"];
    const pres25 = snap.aysen_presupuestos["2025:11201"];
    const aysenDem = (dem25?.regiones || []).find((r) => r.codigo === "11") || {};
    return jsonResponse({
      pregunta_formulada: pregunta,
      variables_y_fuentes: [
        "PIB real y sectorial de Aysén 2013–2025 (Banco Central de Chile · BDE SI3)",
        "Población oficial y PIB per cápita 2025 (INE + BCCh)",
        "Ejecución presupuestaria GORE Aysén, Gobierno Central y SINIM 2018–2026 (DIPRES CKAN + SUBDERE 19 variables)",
        "Contratos de obras MOP DGOP en Aysén 2026 (78 contratos únicos, 43 de Vialidad)",
      ],
      hipotesis_y_metodo:
        "Evaluación determinista en modo solo lectura sobre los cortes oficiales publicados (Decimal(34), sin interpolación ni imputación de PIB regional a comunas).",
      consultas_verificadas: [
        "GET /api/v1/aysen/economia?anio=2025",
        "GET /api/v1/demografia/poblacion?anio=2025",
        "GET /api/v1/aysen/presupuestos?anio=2025&comuna=11201",
        "GET /api/v1/aysen/proyectos?anio=2026&institucion=Vialidad",
      ],
      resultados_reproducibles: {
        crecimiento_real_aysen_2025_pct: eco25?.resumen_anio?.crecimiento_real_aysen_pct ?? null,
        participacion_aysen_chile_2025_pct: eco25?.resumen_anio?.participacion_nominal_aysen_pct ?? null,
        pib_per_capita_real_aysen_2025_clp: aysenDem.pib_per_capita_real_clp ?? null,
        gore_aysen_ejecutado_2025_millones: pres25?.billeteras?.gore_aysen?.ejecutado_millones ?? null,
        muni_aysen_corriente_2025_pct: pres25?.billeteras?.municipal?.gasto_corriente_observable_pct ?? null,
      },
      tabla_evidencia: [
        { indicador: "Crecimiento PIB real Aysén 2025", valor: `${eco25?.resumen_anio?.crecimiento_real_aysen_pct ?? "—"}%`, fuente: "BCCh BDE" },
        { indicador: "Participación PIB nominal Aysén 2025", valor: `${eco25?.resumen_anio?.participacion_nominal_aysen_pct ?? "—"}%`, fuente: "BCCh BDE" },
        { indicador: "GORE Aysén ejecutado 2025", valor: `$${pres25?.billeteras?.gore_aysen?.ejecutado_millones ?? "—"} MM`, fuente: "DIPRES CKAN" },
        { indicador: "Municipalidad de Aysén gasto corriente observable 2025", valor: `${pres25?.billeteras?.municipal?.gasto_corriente_observable_pct ?? "—"}%`, fuente: "SINIM BEP" },
      ],
      hipotesis_alternativas: [
        "La alta participación de Pesca/Acuicultura explica fuertes oscilaciones anuales del crecimiento regional que no reflejan necesariamente la estructura laboral permanente.",
        "Los indicadores municipales 2018–2025 integran Presupuesto Inicial, Vigente, Devengado, Gasto Corriente (IADM51), Inversión Municipal (IADM22), Subt. 24 y Área de Gestión Interna (BGMAGINT) desde SINIM.",
      ],
      interpretacion:
        eco25?.frase_tamano_vs_aporte ||
        "La evidencia oficial confirma la coexistencia de una economía exportadora concentrada con alta relevancia estructural de la Administración Pública y el gasto fiscal regional.",
      limitaciones: [
        "En esta instancia pública de solo lectura el laboratorio opera sobre cortes oficiales verificados; para consultas en vivo arbitrarias a la API SI3 del BCCh conecta BACKEND_API_URL hacia Render/Railway.",
      ],
      dossier_markdown: `# Dossier de Evidencia · Chile Territorial\n\n**Pregunta:** ${pregunta}\n\n- **Crecimiento real PIB Aysén 2025:** ${eco25?.resumen_anio?.crecimiento_real_aysen_pct ?? "—"}% (BCCh)\n- **Participación PIB nacional 2025:** ${eco25?.resumen_anio?.participacion_nominal_aysen_pct ?? "—"}% (BCCh)\n- **GORE Aysén ejecutado 2025:** $${pres25?.billeteras?.gore_aysen?.ejecutado_millones ?? "—"} MM (DIPRES)\n- **Municipalidad de Aysén gasto corriente observable 2025:** ${pres25?.billeteras?.municipal?.gasto_corriente_observable_pct ?? "—"}% (SINIM BEP)\n`,
    });
  }

  return errorResponse(
    404,
    "no_encontrado",
    `Ruta '${path}' no disponible en el corte público de solo lectura. Para consultas en vivo adicionales configura BACKEND_API_URL en Netlify.`
  );
};

export const config = {
  path: ["/api/v1/*", "/healthz"],
};
