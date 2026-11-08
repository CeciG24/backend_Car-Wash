# Backend LS 1713

## Ejecución local

Activa el entorno virtual e instala requirements.txt. Configura las variables de
.env.example en tu .env existente (no sobrescribas tu DATABASE_URL ni credenciales).

Ejecuta: python app.py
La API escucha por defecto en http://127.0.0.1:5000.

El frontend público usa VITE_API_URL; consulta frontend/.env.example.
Las rutas aceptan barra final o su ausencia.

## Acceso administrativo

El modelo actual de usuarios no tiene roles. Para esta etapa los administradores
se autorizan mediante ADMIN_EMAILS, una lista explícita de correos en el servidor.
No se modifica el esquema ni se otorgan privilegios a todos los usuarios existentes.

1. Configura SECRET_KEY con un valor aleatorio largo, por ejemplo generado con:
   python -c "import secrets; print(secrets.token_urlsafe(48))"
2. Agrega el correo del propietario a ADMIN_EMAILS.
3. Si la cuenta no existe, ejecuta flask --app app create-admin.
   El comando solicita la contraseña sin mostrarla; no la pases por argumentos.
4. POST /login con email y contraseña devuelve token y expires_in.
5. Envía Authorization: Bearer TOKEN en las peticiones administrativas.
6. GET /user/me permite comprobar la sesión.

Los tokens son opacos firmados con ItsDangerous (dependencia de Flask), duran
24 horas y se validan contra el usuario y la lista de administradores en cada
solicitud. No son JWT: el código anterior usaba una biblioteca jwt incompatible.
Las sesiones antiguas requieren iniciar sesión de nuevo. No decodifiques tokens
en el cliente. Cerrar sesión elimina el token del cliente; no hay revocación
individual del token en el servidor. Quitar un correo de ADMIN_EMAILS y reiniciar
el proceso retira su acceso; rotar SECRET_KEY invalida todas las sesiones.

POST /register está protegido. La primera cuenta se crea desde el comando local.
El panel administrativo está implementado en frontend-adminpanel. Consulta su
README para ejecución, publicación y configuración del origen en CORS_ORIGINS.

## Contratos principales

- GET /services: { Servicios: [{ id_servicio, nombre, precio, tipo, vehiculo,
  categoria, duracion_minutos }] }
- GET /services/:id: { Servicio: {...} }
- POST /services: name y price (entero no negativo). vehiculo, tipo (paquete de
  lavado), categoria y duracion_minutos son opcionales. La duración, si se
  captura, se expresa como un entero positivo en minutos.
- PUT y DELETE /services/:id: privados. No se puede eliminar un servicio asociado
  a citas o videos.
- GET /services/descriptions/:id: el id es del servicio; devuelve Descripcion
  (texto unido y ordenado) y Descripciones (registros con id_description).
- POST /services/descriptions: service_id, description, order opcional.
- PUT y DELETE /services/descriptions/:id: el id es de la descripción.
- POST /appointments: público; name, numero_whatsapp, direccion,
  scheduled_date (ISO 8601 con zona horaria), id_service. Admite vehiculo y
  email para el formulario público. Los servicios sin tipo de vehículo están
  disponibles para todos los tipos.
  Si recibe email, usa la configuración MAIL del servidor para enviar el folio
  de la solicitud. confirmation_email_sent indica si se pudo enviar. La cita
  se guarda como pendiente aunque falle el correo.
  La agenda tiene un cupo por fecha y hora de inicio, con precisión de minuto.
  Si el cupo ya se ocupó, devuelve 409 con code `appointment_slot_taken`.
  Cancelar, eliminar o mover la cita libera el horario si queda libre de otras
  citas anteriores. La regla también aplica al reprogramar o reactivar una cita.
- GET /appointments, GET/PUT/DELETE /appointments/:id: privados.
  PUT permite editar datos y status: Pending, Completed, Canceled.
- GET /portfolio: público; { Servicios: [{ id_servicio, service_id, carro,
  servicio, url, descripcion, fecha }] }. id_servicio es el ID del video.
- POST /portfolio: privado; car_model, service_id, video_url,
  description opcional y date opcional (ISO 8601 con zona horaria).
- GET /portfolio/:id público; PUT/DELETE privados.
- GET y POST /reviews: públicos. POST usa nombre_cliente, comentario y
  calificacion (entero de 1 a 5). PUT/DELETE /reviews/:id son privados.
- POST /contacts: nombre, numero, detalles. Requiere correo configurado.
- GET /charts/*: privado.
- GET/POST /materials y GET/PUT/DELETE /materials/:id: privados.
  Campos: name, purpose, category (Químico/Herramienta/Consumible), unit
  (ml/L/g/kg/piezas), quantity inicial, minimum, notes, active y dilutions.
  Cada dilución contiene use, product, water e instructions (partes producto:agua).
- GET/POST /materials/:id/movements: privados. POST recibe kind
  (entrada/salida), quantity positiva y note. Devuelve el material actualizado.
  Las existencias admiten tres decimales y se actualizan atómicamente para evitar
  saldos negativos. La cantidad no se modifica desde PUT /materials/:id.
  Un material con movimientos se desactiva: no puede eliminarse ni cambiar de unidad.

Los errores se devuelven como { error: "mensaje" }; las validaciones usan 400,
las sesiones 401/403, registros ausentes 404 y conflictos 409.
Las fechas nuevas se normalizan a UTC. Los datos históricos sin zona horaria
se consideran UTC; si se almacenaron con hora local, necesitan revisión antes
de convertirlos. No se han modificado registros históricos.

Al iniciar, create_all crea las tablas nuevas. La agenda usa
appointment_write_lock para que la comprobación de cupo y el guardado se
realicen en la misma transacción, incluso con varias instancias del servidor.

Para una base de Supabase existente, aplica la migración SQL en
supabase/migrations antes de desplegar la API de servicios. La migración deja
la duración pendiente de captura y clasifica por nombre los servicios de
detallado de interiores y exterior.

## Pruebas

python -m unittest discover -s tests -v

Las pruebas usan SQLite desechable y suprimen los correos.

