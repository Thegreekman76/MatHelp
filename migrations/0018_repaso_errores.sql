-- 0018_repaso_errores.sql — "Repasá tus errores".
--
-- Marca qué prompts (ejercicios fallados) ya repasó el chico, sin insertar un
-- attempt falso (no ensucia la precisión del panel del padre). La cola de repaso
-- son los prompts cuyo último intento fue un error y que no se repasaron desde
-- entonces (resolved_at > el created_at del error).
--
-- El código también la crea lazy (CREATE TABLE IF NOT EXISTS) para las bases ya
-- existentes; este archivo la deja para instalaciones nuevas (initdb).

CREATE TABLE IF NOT EXISTS review_resolved (
    id          SERIAL PRIMARY KEY,
    profile_id  INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    prompt      TEXT NOT NULL,
    resolved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (profile_id, prompt)
);
