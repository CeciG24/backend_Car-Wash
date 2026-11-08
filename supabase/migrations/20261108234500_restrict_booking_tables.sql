ALTER TABLE public.appointment_vehicles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.appointment_write_lock ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.appointment_vehicles, public.appointment_write_lock
  FROM PUBLIC, anon, authenticated;
