-- 0024_daily_reminder.sql — recordatorio diario por email opt-in (Lote E4).
--
-- Cada familia puede activar un recordatorio diario ("¡no te olvides de
-- practicar!"). Default apagado. Un @cron diario emails a las familias que lo
-- activaron y que NO jugaron ese día. (PWA push real no es viable en Fitz puro:
-- web-push necesita VAPID ES256 y el jwt del core solo tiene HS256/384/512.)
--
-- Idempotente. El código también la crea lazy (ALTER ... ADD COLUMN IF NOT
-- EXISTS, ver recordatorio.fitz::ensure_reminder_col) para la base ya existente.

ALTER TABLE families ADD COLUMN IF NOT EXISTS daily_reminder BOOLEAN NOT NULL DEFAULT false;
