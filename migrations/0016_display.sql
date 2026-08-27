-- 0016_display.sql — accesibilidad: alto contraste + tamaño de fuente por perfil.
--
-- Suma dos columnas a profiles. Idempotente.
--   contrast:  'normal' | 'alto'
--   font_size: 'chico' | 'normal' | 'grande'

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS contrast TEXT NOT NULL DEFAULT 'normal';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS font_size TEXT NOT NULL DEFAULT 'normal';
