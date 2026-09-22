-- 0022_rate_limits.sql — rate limiting de login/registro (Lote D2).
--
-- Cada intento POST a /login o /registro inserta una fila (ip, endpoint, ts).
-- El middleware cuenta las filas de la misma (ip, endpoint) en la ventana
-- reciente; si supera el límite, corta con 429. Se usa NOW() de Postgres para
-- la ventana (no depende de un reloj del lado de Fitz). Fail-open: si la DB
-- falla, el middleware deja pasar (no bloquea a todos por un error de infra).
--
-- Idempotente. El código también la crea lazy (CREATE TABLE IF NOT EXISTS, ver
-- ratelimit.fitz::ensure_rate_table) para la base de producción que ya existe.

CREATE TABLE IF NOT EXISTS rate_limits (
    id        BIGSERIAL   PRIMARY KEY,
    ip        TEXT        NOT NULL,
    endpoint  TEXT        NOT NULL,
    ts        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rate_ip_ep_ts ON rate_limits(ip, endpoint, ts);
