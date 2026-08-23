-- MatHelp — F5 (panel del padre): histórico de rating por día.
--
-- Este archivo lo corre Postgres solo, sobre un volumen nuevo
-- (docker-entrypoint-initdb.d, después de 0001 por orden alfabético).
-- Para una base ya creada: aplicar a mano (`psql ... -f 0002_...sql`) — es
-- idempotente (IF NOT EXISTS).
--
-- Por qué existe: `mastery` guarda solo el rating ACTUAL por destreza. Para la
-- "evolución del rating" del panel del padre necesitamos una foto por día. Se
-- escribe con un upsert en `actualizar_mastery` (una fila por perfil+destreza+
-- día; ON CONFLICT pisa el rating con el último del día), así al cerrar el día
-- queda el rating final de esa jornada. La evolución es AVG(rating) por día.

CREATE TABLE IF NOT EXISTS mastery_snapshots (
    id         BIGSERIAL PRIMARY KEY,
    profile_id BIGINT           NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    skill_code TEXT             NOT NULL,
    day        DATE             NOT NULL,
    rating     DOUBLE PRECISION NOT NULL,
    UNIQUE (profile_id, skill_code, day)
);
CREATE INDEX IF NOT EXISTS idx_mastery_snap ON mastery_snapshots(profile_id, day);
