ALTER TABLE public.services
  ADD COLUMN IF NOT EXISTS es_extra boolean NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS public.appointment_extras (
  appointment_id integer NOT NULL REFERENCES public.appointments(id_appointment) ON DELETE CASCADE,
  service_id integer NOT NULL REFERENCES public.services(id_service),
  amount integer NOT NULL,
  PRIMARY KEY (appointment_id, service_id)
);

CREATE INDEX IF NOT EXISTS ix_appointment_extras_service_id ON public.appointment_extras (service_id);

ALTER TABLE public.appointment_extras ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.appointment_extras FROM PUBLIC, anon, authenticated;
