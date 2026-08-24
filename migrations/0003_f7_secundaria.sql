-- 0003_f7_secundaria.sql — F7: secundaria (13–17 años).
--
-- Agrega la ORIENTACIÓN del perfil. Solo aplica en el Ciclo Orientado
-- (4°–6° de secundaria = grade 11..13); 'comun' cubre primaria y el Ciclo
-- Básico (1°–3° de secundaria), que es igual para todas las modalidades.
--
-- El `grade` sigue siendo INT sin CHECK: primaria es 1..7 y secundaria 8..13
-- (= 1°..6°), con un helper `grade_a_nivel` del lado del código.
--
-- Idempotente (ADD COLUMN IF NOT EXISTS): corre en el initdb de un contenedor
-- nuevo después del 0001/0002, y a mano sobre una base existente.

ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS modalidad TEXT NOT NULL DEFAULT 'comun';
