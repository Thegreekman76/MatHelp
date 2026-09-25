-- 0025_maestro.sql — modo MAESTRO: account_type, grupos (grados/aulas), grupo_id.
--
-- Un maestro (families.account_type = 'teacher') arma GRADOS (tabla `grupos`,
-- uno por colegio × turno × grado) y cada alumno es un `profiles` con
-- `grupo_id` → grupos.id. Los perfiles de familia tienen grupo_id NULL.
--
-- account_type distingue el rol de la cuenta: 'individual' / 'family' / 'teacher'.
-- Solo se consulta para "¿es maestro?"; individual vs familia se sigue derivando
-- del PIN de adulto (admin_pin), sin tocar la lógica existente.
--
-- Idempotente. El código también lo crea lazy (ALTER/CREATE ... IF NOT EXISTS)
-- para la base ya existente (ver auth.fitz::asegurar_account_type y
-- maestro.fitz::asegurar_grupos / asegurar_grupo_col).

ALTER TABLE families ADD COLUMN IF NOT EXISTS account_type TEXT NOT NULL DEFAULT 'family';

CREATE TABLE IF NOT EXISTS grupos (
    id         BIGSERIAL PRIMARY KEY,
    owner_id   BIGINT NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    colegio    TEXT NOT NULL DEFAULT '',
    turno      TEXT NOT NULL DEFAULT '',
    nombre     TEXT NOT NULL DEFAULT '',        -- "5°B"
    grade      INT  NOT NULL DEFAULT 1,         -- 1..7 primaria, 8..13 secundaria
    modalidad  TEXT NOT NULL DEFAULT 'comun',
    codigo     TEXT NOT NULL DEFAULT '',        -- código del grado (login del alumno)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_grupos_owner  ON grupos(owner_id);
CREATE INDEX IF NOT EXISTS idx_grupos_codigo ON grupos(codigo);

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS grupo_id BIGINT REFERENCES grupos(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_profiles_grupo ON profiles(grupo_id);
