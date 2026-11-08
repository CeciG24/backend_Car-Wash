ALTER TABLE public.services
  ADD COLUMN IF NOT EXISTS categoria varchar(60),
  ADD COLUMN IF NOT EXISTS duracion_minutos integer
    CONSTRAINT services_duration_positive CHECK (duracion_minutos > 0),
  ALTER COLUMN tipo DROP NOT NULL;

UPDATE public.services
SET categoria = CASE upper(btrim(name))
  WHEN 'DETALLADO DE INTERIORES' THEN 'Detallado de interiores'
  WHEN 'DETALLADO EXTERIOR' THEN 'Detallado exterior'
END
WHERE categoria IS NULL
  AND upper(btrim(name)) IN ('DETALLADO DE INTERIORES', 'DETALLADO EXTERIOR');
