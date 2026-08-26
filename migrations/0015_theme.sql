-- 0015_theme.sql — F9 pulido: tema de color por perfil.
--
-- Suma la columna `theme` a profiles (default 'default'). Idempotente.

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS theme TEXT NOT NULL DEFAULT 'default';
