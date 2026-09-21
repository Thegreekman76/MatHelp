-- 0020_admin_pin.sql — PIN de adulto a nivel cuenta (separación control ↔ jugador).
--
-- La zona de control familiar (/familia, panel, gestión de perfiles, accesibilidad)
-- se protege con un PIN de la CUENTA, distinto del PIN por-perfil. Se guarda en
-- families.admin_pin ("" = no configurado).
--
-- Idempotente. El código también la crea lazy (ALTER ... ADD COLUMN IF NOT EXISTS,
-- ver familia.fitz::asegurar_admin_pin) para la base de producción que ya existe;
-- este archivo la deja para instalaciones nuevas (initdb corre solo en bases nuevas).

ALTER TABLE families ADD COLUMN IF NOT EXISTS admin_pin TEXT NOT NULL DEFAULT '';
