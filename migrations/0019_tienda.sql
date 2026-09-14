-- 0019_tienda.sql — "Monedas + tienda".
--
-- Las compras del perfil (avatares y temas desbloqueados con monedas). Las monedas
-- NO se guardan: son una vista (respuestas correctas − SUM(price) de las compras).
--
-- El código también la crea lazy (CREATE TABLE IF NOT EXISTS) para bases existentes;
-- este archivo la deja para instalaciones nuevas (initdb).

CREATE TABLE IF NOT EXISTS purchases (
    id          SERIAL PRIMARY KEY,
    profile_id  INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    item_type   TEXT NOT NULL,          -- 'avatar' | 'theme'
    item_code   TEXT NOT NULL,
    price       INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (profile_id, item_type, item_code)
);
