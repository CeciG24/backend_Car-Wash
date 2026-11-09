import re
from datetime import timezone
from flask import Blueprint, current_app, jsonify, request
from flask_mail import Message
from pytz import timezone as named_timezone
from werkzeug.exceptions import BadRequest, Conflict
from extensions import mail
from models import db
from models.appointment import AppointmentExtra, Appointments, AppointmentPrice, AppointmentVehicle, statusEnum
from models.services import Services, VehiculoEnum
from validation import payload, text, date_value, existing, enum_value, integer

appointments_bp = Blueprint("appointments", __name__, url_prefix="/appointments")
MEXICO_CITY = named_timezone("America/Mexico_City")
EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+"
)


class AppointmentSlotTaken(Conflict):
    description = "Este horario acaba de ocuparse. Elige otro horario para tu cita."


@appointments_bp.errorhandler(AppointmentSlotTaken)
def slot_taken(error):
    db.session.rollback()
    return jsonify(error=error.description, code="appointment_slot_taken"), 409


def lock_calendar():
    # The upsert holds a write lock until the appointment transaction ends.
    db.session.execute(db.text(
        "INSERT INTO appointment_write_lock (id) VALUES (1) "
        "ON CONFLICT (id) DO UPDATE SET id = excluded.id"
    ))


def slot_start(date):
    return date.replace(second=0, microsecond=0)


def ensure_slot_available(start):
    occupied = db.session.query(Appointments.id_appointment).filter(
        Appointments.status != statusEnum.CANCELED,
        Appointments.scheduled_date >= start,
        Appointments.scheduled_date <= start.replace(second=59, microsecond=999999),
    ).first()
    if occupied:
        raise AppointmentSlotTaken()


def add_extras(item, values):
    if not isinstance(values, list):
        raise BadRequest("Los extras deben enviarse como una lista")
    ids = {integer(value, "ids_extras", 1, 2_147_483_647) for value in values}
    if len(ids) != len(values):
        raise BadRequest("Cada extra puede seleccionarse una sola vez")
    if not ids:
        return
    extras = Services.query.filter(Services.id_service.in_(ids), Services.es_extra.is_(True)).all()
    if len(extras) != len(ids):
        raise BadRequest("Uno de los extras seleccionados ya no está disponible")
    if any(extra.vehiculo and extra.vehiculo != item.vehicle for extra in extras):
        raise BadRequest("Uno de los extras no está disponible para este vehículo")
    item.extras = [AppointmentExtra(service=extra, amount=extra.price) for extra in extras]


def apply_data(item, data, creating=False):
    for key, attr in (("name", "name"), ("numero_whatsapp", "num_whatsapp"), ("direccion", "direccion")):
        if creating or key in data:
            setattr(item, attr, text(data, key))
    if creating or "scheduled_date" in data:
        item.scheduled_date = date_value(data.get("scheduled_date"), future=True)
    if creating or "id_service" in data:
        service = existing(Services, data.get("id_service"))
        if creating or service.id_service != item.id_service:
            if service.es_extra:
                raise BadRequest("Selecciona un servicio principal para la cita")
            if not creating and item.extras and service.vehiculo and service.vehiculo != item.vehicle:
                raise BadRequest("El servicio principal no es compatible con el vehículo de esta cita")
            item.pricing = AppointmentPrice(amount=service.price)
        item.service = service
        if creating and "vehiculo" in data:
            vehicle = enum_value(VehiculoEnum, data["vehiculo"], "vehiculo")
            if service.vehiculo and service.vehiculo != vehicle:
                raise BadRequest("El servicio no está disponible para el tipo de vehículo seleccionado")
            item.vehicle_selection = AppointmentVehicle(vehicle=vehicle)
    if not creating and "status" in data:
        item.status = enum_value(statusEnum, data["status"], "status")


def send_confirmation(item, email):
    if not current_app.config.get("MAIL_DEFAULT_SENDER"):
        return False
    date = item.scheduled_date.replace(tzinfo=timezone.utc).astimezone(MEXICO_CITY)
    vehicle_line = f"Vehículo: {item.vehicle.value}\n" if item.vehicle else ""
    extras_line = "Extras: " + ", ".join(extra.service.name for extra in item.extras) + "\n" if item.extras else ""
    message = Message(
        subject="LS 1713 | Recibimos tu solicitud de cita",
        recipients=[email],
        body=(f"Recibimos tu solicitud de cita con LS 1713.\n\n"
              f"Folio: {item.id_appointment}\n"
              f"Servicio: {item.service.name}\n"
              f"{extras_line}"
              f"{vehicle_line}"
              f"Fecha solicitada: {date:%d/%m/%Y %H:%M} (hora de Ciudad de México)\n\n"
              "Tu solicitud quedó pendiente en nuestra agenda."),
    )
    try:
        mail.send(message)
    except Exception as error:
        current_app.logger.warning("Falló el correo de la cita %s (%s)", item.id_appointment, type(error).__name__)
        return False
    return True


@appointments_bp.route("", methods=["POST"])
def post_appointment():
    data = payload()
    email = text(data, "email", 254) if "email" in data else None
    if email and not EMAIL_PATTERN.fullmatch(email):
        raise BadRequest("Ingresa un correo electrónico válido")
    item = Appointments()
    with db.session.no_autoflush:
        apply_data(item, data, True)
        add_extras(item, data.get("ids_extras", []))
        item.status = statusEnum.PENDING
        lock_calendar()
        ensure_slot_available(slot_start(item.scheduled_date))
    db.session.add(item)
    db.session.commit()
    result = {"message": "Cita creada exitosamente", "id_appointment": item.id_appointment}
    if email:
        result["confirmation_email_sent"] = send_confirmation(item, email)
    return jsonify(result), 201

@appointments_bp.route("", methods=["GET"])
def get_appointments():
    return jsonify([item.to_dict() for item in Appointments.query.order_by(Appointments.scheduled_date).all()])

@appointments_bp.route("/<int:identifier>", methods=["GET", "PUT", "DELETE"])
def appointment(identifier):
    if request.method in ("PUT", "DELETE"):
        lock_calendar()
    item = existing(Appointments, identifier)
    if request.method in ("GET", "HEAD"):
        return jsonify(item.to_dict())
    if request.method == "PUT":
        previous_slot = slot_start(item.scheduled_date) if item.status != statusEnum.CANCELED else None
        with db.session.no_autoflush:
            apply_data(item, payload())
            if item.status != statusEnum.CANCELED:
                new_slot = slot_start(item.scheduled_date)
                if new_slot != previous_slot:
                    ensure_slot_available(new_slot)
    else:
        db.session.delete(item)
    db.session.commit()
    return jsonify(message="Cita actualizada" if request.method == "PUT" else "Cita eliminada")

