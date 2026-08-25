-- 0006_records.sql — récord de mejor racha POR JUEGO (por perfil).
--
-- Una fila por (perfil, juego) con la mayor racha (aciertos seguidos) lograda
-- alguna vez en ese juego. Se lee al abrir la partida (para saber si esta ronda
-- rompe el récord) y se actualiza al cerrar con GREATEST (sólo sube, race-safe).
-- Idempotente (CREATE TABLE IF NOT EXISTS), corre en el initdb tras 0001..0005.

CREATE TABLE IF NOT EXISTS profile_game_stats (
    id          BIGSERIAL   PRIMARY KEY,
    profile_id  BIGINT      NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    game_code   TEXT        NOT NULL,
    best_streak INTEGER     NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (profile_id, game_code)
);

CREATE INDEX IF NOT EXISTS idx_pgs_profile ON profile_game_stats(profile_id);
