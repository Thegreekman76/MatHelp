-- MatHelp — esquema inicial.
--
-- Este archivo lo corre Postgres solo, la primera vez que se crea el volumen
-- (docker-entrypoint-initdb.d). Para volver a correrlo: reset.bat.
--
-- A partir de F1 el esquema pasa a manejarse con `fitz db diff` / `fitz db
-- migrate` contra los @table de src/models.fitz. Esto es el punto de partida.

-- Cuenta de la familia: es la que administra el padre o la madre.
CREATE TABLE IF NOT EXISTS families (
    id            BIGSERIAL PRIMARY KEY,
    email         TEXT        NOT NULL UNIQUE,
    password_hash TEXT        NOT NULL,
    display_name  TEXT        NOT NULL DEFAULT '',
    locale        TEXT        NOT NULL DEFAULT 'es-AR',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Un perfil por hijo/a.
CREATE TABLE IF NOT EXISTS profiles (
    id         BIGSERIAL PRIMARY KEY,
    family_id  BIGINT      NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    name       TEXT        NOT NULL,
    avatar     TEXT        NOT NULL DEFAULT 'mate',
    birth_year INT         NOT NULL DEFAULT 0,   -- la edad se deriva: nunca queda vieja
    grade      INT         NOT NULL DEFAULT 0,
    locale     TEXT        NOT NULL DEFAULT 'es-AR',
    pin        TEXT        NOT NULL DEFAULT '',  -- opcional, para que no se metan entre hermanos
    daily_goal INT         NOT NULL DEFAULT 10,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_profiles_family ON profiles(family_id);

-- Una partida.
CREATE TABLE IF NOT EXISTS sessions (
    id          BIGSERIAL PRIMARY KEY,
    profile_id  BIGINT      NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    mode        TEXT        NOT NULL,
    topic_code  TEXT        NOT NULL DEFAULT '',
    level       INT         NOT NULL DEFAULT 1,
    -- El seed reconstruye la partida entera: con seed + indice no hace falta
    -- guardar cada ejercicio, y el panel del padre puede "rejugarla".
    seed        BIGINT      NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at    TIMESTAMPTZ,
    total       INT         NOT NULL DEFAULT 0,
    correct     INT         NOT NULL DEFAULT 0,
    score       INT         NOT NULL DEFAULT 0,
    duration_ms INT         NOT NULL DEFAULT 0,
    CONSTRAINT sessions_mode_valido CHECK (
        mode IN ('quiz','truefalse','fillgap','numpad','story','kiosco','fracciones','practica','desafio')
    )
);
CREATE INDEX IF NOT EXISTS idx_sessions_profile ON sessions(profile_id, started_at DESC);

-- Una respuesta. Se escribe APENAS ocurre: la memoria del server es cache
-- descartable, esto es la fuente de verdad. Cubre a la vez el leak del store
-- de componentes y la falta de reconnect con replay.
CREATE TABLE IF NOT EXISTS attempts (
    id         BIGSERIAL PRIMARY KEY,
    session_id BIGINT      NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    profile_id BIGINT      NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    skill_code TEXT        NOT NULL,
    idx        INT         NOT NULL DEFAULT 0,
    prompt     TEXT        NOT NULL DEFAULT '',
    expected   TEXT        NOT NULL DEFAULT '',
    given      TEXT        NOT NULL DEFAULT '',
    correct    BOOLEAN     NOT NULL DEFAULT FALSE,
    ms         INT         NOT NULL DEFAULT 0,
    difficulty INT         NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_attempts_skill   ON attempts(profile_id, skill_code, created_at DESC);

-- Dominio por destreza: lo que mueve el motor adaptativo.
CREATE TABLE IF NOT EXISTS mastery (
    id           BIGSERIAL PRIMARY KEY,
    profile_id   BIGINT      NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    skill_code   TEXT        NOT NULL,
    rating       DOUBLE PRECISION NOT NULL DEFAULT 800.0,
    seen         INT         NOT NULL DEFAULT 0,
    hits         INT         NOT NULL DEFAULT 0,
    streak       INT         NOT NULL DEFAULT 0,
    avg_ms       INT         NOT NULL DEFAULT 0,
    last_seen_at TIMESTAMPTZ,
    due_at       TIMESTAMPTZ,                    -- repaso espaciado
    UNIQUE (profile_id, skill_code)
);
CREATE INDEX IF NOT EXISTS idx_mastery_due ON mastery(profile_id, due_at);

-- Medallas. Por dominio real, no por tiempo de pantalla.
CREATE TABLE IF NOT EXISTS awards (
    id         BIGSERIAL PRIMARY KEY,
    profile_id BIGINT      NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    code       TEXT        NOT NULL,
    earned_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (profile_id, code)
);

-- Racha diaria.
CREATE TABLE IF NOT EXISTS streaks (
    id         BIGSERIAL PRIMARY KEY,
    profile_id BIGINT  NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    day        DATE    NOT NULL,
    exercises  INT     NOT NULL DEFAULT 0,
    goal_met   BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (profile_id, day)
);
