-- MVP de PIB anual. La ejecución transaccional y el registro son responsabilidad
-- de infra/pib-db.sh. El esquema es deliberadamente independiente del piloto fiscal.
CREATE SCHEMA pib;
REVOKE ALL ON SCHEMA pib FROM PUBLIC;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ct_pib_reader') THEN
        CREATE ROLE ct_pib_reader NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ct_pib_ingest') THEN
        CREATE ROLE ct_pib_ingest NOLOGIN;
    END IF;
END
$$;

CREATE TABLE pib.configuracion (
    unico boolean PRIMARY KEY DEFAULT true CHECK (unico),
    modo text NOT NULL CHECK (modo IN ('prueba', 'aprobada'))
);

CREATE TABLE pib.territorio (
    codigo text PRIMARY KEY CHECK (codigo ~ '^(CL|0[1-9]|1[0-6])$'),
    nombre text NOT NULL CHECK (nombre <> ''),
    nivel text NOT NULL CHECK (nivel = CASE WHEN codigo = 'CL' THEN 'nacional' ELSE 'regional' END),
    vigente_desde date,
    vigente_hasta date,
    CHECK (vigente_desde IS NULL OR vigente_hasta IS NULL OR vigente_desde <= vigente_hasta)
);

INSERT INTO pib.territorio (codigo, nombre, nivel, vigente_desde) VALUES
    ('CL', 'Chile', 'nacional', NULL),
    ('01', 'Tarapacá', 'regional', NULL),
    ('02', 'Antofagasta', 'regional', NULL),
    ('03', 'Atacama', 'regional', NULL),
    ('04', 'Coquimbo', 'regional', NULL),
    ('05', 'Valparaíso', 'regional', NULL),
    ('06', 'Libertador General Bernardo O’Higgins', 'regional', NULL),
    ('07', 'Maule', 'regional', NULL),
    ('08', 'Biobío', 'regional', NULL),
    ('09', 'La Araucanía', 'regional', NULL),
    ('10', 'Los Lagos', 'regional', NULL),
    ('11', 'Aysén del General Carlos Ibáñez del Campo', 'regional', NULL),
    ('12', 'Magallanes y de la Antártica Chilena', 'regional', NULL),
    ('13', 'Metropolitana de Santiago', 'regional', NULL),
    ('14', 'Los Ríos', 'regional', NULL),
    ('15', 'Arica y Parinacota', 'regional', NULL),
    ('16', 'Ñuble', 'regional', NULL);

CREATE TABLE pib.publicacion (
    id text PRIMARY KEY CHECK (id ~ '^[A-Za-z0-9][A-Za-z0-9._-]*$'),
    fecha timestamptz NOT NULL,
    estado text NOT NULL CHECK (estado IN ('prueba', 'aprobada')),
    fuente text NOT NULL CHECK (fuente ~ '^[A-Za-z0-9][A-Za-z0-9._-]*$'),
    cobertura jsonb NOT NULL CHECK (
        jsonb_typeof(cobertura) = 'object'
        AND jsonb_typeof(cobertura->'esperadas') IS NOT DISTINCT FROM 'number'
        AND jsonb_typeof(cobertura->'disponibles') IS NOT DISTINCT FROM 'number'
        AND (cobertura->>'disponibles')::integer BETWEEN 0 AND (cobertura->>'esperadas')::integer
    ),
    cambios jsonb NOT NULL CHECK (jsonb_typeof(cambios) = 'array'),
    huella bytea NOT NULL
);
CREATE INDEX pib_publicacion_corte ON pib.publicacion (estado, fecha DESC, id DESC);

CREATE TABLE pib.artefacto (
    publicacion text REFERENCES pib.publicacion (id),
    id text CHECK (id ~ '^[A-Za-z0-9][A-Za-z0-9._-]*$'),
    fuente text NOT NULL CHECK (fuente ~ '^[A-Za-z0-9][A-Za-z0-9._-]*$'),
    url text NOT NULL CHECK (url ~ '^https://[^?#]+$' AND url !~ '^https://[^/]+@'),
    sha256 text NOT NULL CHECK (sha256 ~ '^[a-f0-9]{64}$'),
    corte date,
    extraido_en timestamptz NOT NULL,
    PRIMARY KEY (publicacion, id)
);

CREATE TABLE pib.observacion (
    id text PRIMARY KEY CHECK (id ~ '^[A-Za-z0-9][A-Za-z0-9._-]*$'),
    territorio text NOT NULL REFERENCES pib.territorio (codigo),
    anio integer NOT NULL CHECK (anio BETWEEN 2012 AND 9999),
    metrica text NOT NULL CHECK (metrica IN ('nivel', 'crecimiento', 'participacion')),
    valoracion text NOT NULL CHECK (valoracion IN ('real', 'nominal')),
    valor numeric CHECK (valor::text ~ '^-?[0-9]+(\.[0-9]+)?$'),
    unidad text NOT NULL CHECK (unidad <> ''),
    anio_referencia integer CHECK (anio_referencia BETWEEN 2013 AND 9999),
    estado text NOT NULL CHECK (estado IN ('informado', 'preliminar', 'faltante', 'suprimido', 'no_aplicable', 'error')),
    clase text NOT NULL CHECK (clase IN ('oficial', 'estimacion', 'prueba', 'no_disponible')),
    publicacion text NOT NULL REFERENCES pib.publicacion (id),
    UNIQUE (publicacion, id),
    UNIQUE (publicacion, metrica, valoracion, anio, territorio),
    CHECK ((estado IN ('informado', 'preliminar')) = (valor IS NOT NULL)),
    CHECK ((clase = 'no_disponible') = (valor IS NULL)),
    CHECK (valoracion <> 'nominal' OR anio_referencia IS NULL),
    CHECK (anio <> 2012 OR (metrica = 'nivel' AND valoracion = 'real')),
    CHECK (metrica <> 'crecimiento' OR (valoracion = 'real' AND unidad = '%')),
    CHECK (metrica <> 'participacion' OR (valoracion = 'nominal' AND unidad = '%' AND territorio <> 'CL')),
    CHECK (metrica <> 'nivel' OR (unidad = 'millones CLP' AND
        (valoracion <> 'real' OR valor IS NULL OR anio_referencia IS NOT NULL)))
);

CREATE TABLE pib.procedencia (
    observacion text PRIMARY KEY,
    publicacion text NOT NULL,
    serie_bde text,
    artefacto text,
    selector text,
    formula_version text,
    insumos jsonb NOT NULL CHECK (jsonb_typeof(insumos) = 'array'),
    motivo text,
    FOREIGN KEY (publicacion, observacion) REFERENCES pib.observacion (publicacion, id),
    FOREIGN KEY (publicacion, artefacto) REFERENCES pib.artefacto (publicacion, id)
);

CREATE VIEW pib.api_territorio AS
    SELECT codigo, nombre, nivel, vigente_desde, vigente_hasta FROM pib.territorio;

CREATE VIEW pib.api_publicacion AS
    SELECT id, fecha, estado, fuente, cobertura, cambios
    FROM pib.publicacion
    WHERE estado = (SELECT modo FROM pib.configuracion);

CREATE VIEW pib.api_observacion AS
    SELECT o.id, o.territorio, o.anio, o.metrica, o.valoracion, o.valor::text AS valor,
           o.unidad, o.anio_referencia, o.estado, o.clase, o.publicacion
    FROM pib.observacion AS o
    JOIN pib.api_publicacion AS p ON p.id = o.publicacion
    WHERE o.anio >= 2013;

CREATE VIEW pib.api_procedencia AS
    SELECT l.observacion, l.publicacion, l.serie_bde, l.artefacto, l.selector,
           l.formula_version, l.insumos, l.motivo
    FROM pib.procedencia AS l
    JOIN pib.api_publicacion AS p ON p.id = l.publicacion;

CREATE FUNCTION pib.cargar_lote(lote jsonb) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog
AS $$
DECLARE
    corte_id text := lote #>> '{publicacion,id}';
    corte_estado text := lote #>> '{publicacion,estado}';
    huella_nueva bytea := sha256(convert_to(lote::text, 'UTF8'));
    huella_anterior bytea;
    modo text;
BEGIN
    IF corte_id IS NULL OR corte_estado IS NULL OR
       jsonb_typeof(lote->'artefactos') IS DISTINCT FROM 'array' OR
       jsonb_typeof(lote->'observaciones') IS DISTINCT FROM 'array' OR
       jsonb_typeof(lote->'procedencias') IS DISTINCT FROM 'array' THEN
        RAISE EXCEPTION 'Estructura de lote inválida';
    END IF;

    SELECT configuracion.modo INTO STRICT modo FROM pib.configuracion;
    IF corte_estado <> modo THEN
        RAISE EXCEPTION 'El estado del corte es incompatible con el modo de la base';
    END IF;

    PERFORM pg_advisory_xact_lock(hashtextextended(corte_id, 34581));
    SELECT huella INTO huella_anterior FROM pib.publicacion WHERE id = corte_id;
    IF huella_anterior IS NOT NULL THEN
        IF huella_anterior = huella_nueva THEN
            RETURN false;
        END IF;
        RAISE EXCEPTION 'El identificador de publicación ya corresponde a otro lote';
    END IF;

    INSERT INTO pib.publicacion (id, fecha, estado, fuente, cobertura, cambios, huella)
    SELECT id, fecha, estado, fuente, cobertura, cambios, huella_nueva
    FROM jsonb_to_record(lote->'publicacion')
        AS p(id text, fecha timestamptz, estado text, fuente text, cobertura jsonb, cambios jsonb);

    INSERT INTO pib.artefacto (publicacion, id, fuente, url, sha256, corte, extraido_en)
    SELECT corte_id, id, fuente, url, sha256, corte, extraido_en
    FROM jsonb_to_recordset(lote->'artefactos')
        AS a(id text, fuente text, url text, sha256 text, corte date, extraido_en timestamptz);

    INSERT INTO pib.observacion (id, territorio, anio, metrica, valoracion, valor,
        unidad, anio_referencia, estado, clase, publicacion)
    SELECT id, territorio, anio, metrica, valoracion, valor,
        unidad, anio_referencia, estado, clase, publicacion
    FROM jsonb_to_recordset(lote->'observaciones')
        AS o(id text, territorio text, anio integer, metrica text, valoracion text, valor numeric,
            unidad text, anio_referencia integer, estado text, clase text, publicacion text)
    WHERE publicacion = corte_id;
    IF EXISTS (
        SELECT FROM jsonb_array_elements(lote->'observaciones') AS o
        WHERE o->>'publicacion' IS DISTINCT FROM corte_id
    ) THEN
        RAISE EXCEPTION 'Una observación referencia otro corte';
    END IF;

    INSERT INTO pib.procedencia (observacion, publicacion, serie_bde, artefacto,
        selector, formula_version, insumos, motivo)
    SELECT observacion, publicacion, serie_bde, artefacto, selector, formula_version, insumos, motivo
    FROM jsonb_to_recordset(lote->'procedencias')
        AS l(observacion text, publicacion text, serie_bde text, artefacto text,
            selector text, formula_version text, insumos jsonb, motivo text)
    WHERE publicacion = corte_id;
    IF EXISTS (
        SELECT FROM jsonb_array_elements(lote->'procedencias') AS l
        WHERE l->>'publicacion' IS DISTINCT FROM corte_id
    ) THEN
        RAISE EXCEPTION 'Una procedencia referencia otro corte';
    END IF;

    IF EXISTS (
        SELECT FROM pib.observacion AS o
        LEFT JOIN pib.procedencia AS l ON l.observacion = o.id
        WHERE o.publicacion = corte_id AND (
            l.observacion IS NULL
            OR (o.valor IS NULL AND nullif(btrim(l.motivo), '') IS NULL)
            OR (o.clase = 'oficial' AND o.metrica = 'nivel' AND
                (nullif(btrim(l.serie_bde), '') IS NULL OR l.artefacto IS NULL OR nullif(btrim(l.selector), '') IS NULL))
            OR (o.clase = 'oficial' AND o.metrica <> 'nivel' AND
                (nullif(btrim(l.formula_version), '') IS NULL OR jsonb_array_length(l.insumos) = 0))
            OR (modo = 'aprobada' AND (o.clase IN ('prueba', 'estimacion') OR o.estado = 'error'))
            OR (modo = 'prueba' AND o.clase NOT IN ('prueba', 'no_disponible'))
        )
    ) THEN
        RAISE EXCEPTION 'Procedencia, estado o clase de evidencia incompatibles';
    END IF;

    IF EXISTS (
        SELECT FROM pib.procedencia AS l
        CROSS JOIN LATERAL jsonb_array_elements_text(l.insumos) AS i(id)
        LEFT JOIN pib.observacion AS o ON o.id = i.id AND o.publicacion = l.publicacion
        WHERE l.publicacion = corte_id AND (o.id IS NULL OR o.id = l.observacion)
    ) THEN
        RAISE EXCEPTION 'Un insumo de procedencia es inválido';
    END IF;

    IF (SELECT count(*) FROM pib.observacion WHERE publicacion = corte_id AND anio >= 2013)
           > (lote #>> '{publicacion,cobertura,esperadas}')::integer
       OR (SELECT count(*) FROM pib.observacion WHERE publicacion = corte_id AND anio >= 2013 AND valor IS NOT NULL)
           <> (lote #>> '{publicacion,cobertura,disponibles}')::integer THEN
        RAISE EXCEPTION 'Conteos de cobertura incompatibles';
    END IF;
    RETURN true;
END
$$;

REVOKE ALL ON FUNCTION pib.cargar_lote(jsonb) FROM PUBLIC;
GRANT USAGE ON SCHEMA pib TO ct_pib_reader, ct_pib_ingest;
GRANT SELECT ON pib.api_territorio, pib.api_publicacion, pib.api_observacion, pib.api_procedencia TO ct_pib_reader;
GRANT EXECUTE ON FUNCTION pib.cargar_lote(jsonb) TO ct_pib_ingest;
