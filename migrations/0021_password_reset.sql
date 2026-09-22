-- 0021_password_reset.sql — tokens de recuperación de contraseña (Lote B).
--
-- Flujo: el usuario pide recuperar → se crea un token de un solo uso, con
-- vencimiento corto, cuyo HASH (Argon2, no el token en claro) se guarda acá.
-- El link del email lleva `id` (el id de esta fila, no secreto) + `t` (el token
-- en claro, secreto). Al usarse: se busca por id (indexado), se verifica `t`
-- contra token_hash, y se marca used_at. Guardar el hash y no el token evita
-- que un dump de la DB exponga tokens vivos.
--
-- Idempotente. El código también la crea lazy (CREATE TABLE IF NOT EXISTS, ver
-- recuperar.fitz::asegurar_tabla_reset) para la base de producción que ya existe;
-- este archivo la deja para instalaciones nuevas (initdb corre solo en bases nuevas).

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          BIGSERIAL   PRIMARY KEY,
    family_id   BIGINT      NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    token_hash  TEXT        NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prt_family ON password_reset_tokens(family_id);
