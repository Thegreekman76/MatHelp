-- 0023_referral.sql — referral entre familias (Lote E5).
--
-- Cada familia tiene un `referral_code` (Uuid, único) para armar su link de
-- invitación `/r/<code>`. Cuando una familia nueva se registra habiendo entrado
-- por ese link, se guarda `referred_by` = id de la familia que la invitó.
--
-- Idempotente. El código también las crea lazy (ALTER ... ADD COLUMN IF NOT
-- EXISTS, ver referral.fitz::ensure_referral_cols) para la base ya existente.

ALTER TABLE families ADD COLUMN IF NOT EXISTS referral_code TEXT;
ALTER TABLE families ADD COLUMN IF NOT EXISTS referred_by   BIGINT REFERENCES families(id) ON DELETE SET NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_families_referral_code ON families(referral_code) WHERE referral_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_families_referred_by ON families(referred_by);
