-- 0012_estimar.sql — F9: juego "Estimación" (redondeo + "¿está cerca?").
--
-- Suma el modo 'estimar' al CHECK de sessions.mode. Idempotente: DROP + ADD del
-- constraint (corre en el initdb de un contenedor nuevo tras 0001..0011, y a mano
-- sobre una base existente).

ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_mode_valido;
ALTER TABLE sessions ADD CONSTRAINT sessions_mode_valido CHECK (
    mode IN ('quiz','truefalse','fillgap','numpad','story','escalera','kiosco','fracciones','practica','desafio','potencias','series','reloj','geo','memoria','enteros','ordenar','estimar')
);
