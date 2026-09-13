from flask import Blueprint, jsonify
from models import db
from models.appointment import Appointments, statusEnum
from models.services import Services
from validation import payload, text, date_value, existing, enum_value

appointments_bp = Blueprint("appointments", __name__, url_prefix="/appointments")

def apply_data(item, data, creating=False):
    for key, attr in (("name", "name"), ("numero_whatsapp", "num_whatsapp"), ("direccion", "direccion")):
        if creating or key in data:
            setattr(item, attr, text(data, key))
    if creating or "scheduled_date" in data:
        item.scheduled_date = date_value(data.get("scheduled_date"), future=True)
    if creating or "id_service" in data:
        item.id_service = existing(Services, data.get("id_service")).id_service
    if not creating and "status" in data:
        item.status = enum_value(statusEnum, data["status"], "status")

@appointments_bp.route("", methods=["POST"])
def post_appointment():
    item = Appointments()
    apply_data(item, payload(), True)
    item.status = statusEnum.PENDING
    db.session.add(item)
    db.session.commit()
    return jsonify(message="Cita creada exitosamente", id_appointment=item.id_appointment), 201

@appointments_bp.route("", methods=["GET"])
def get_appointments():
    return jsonify([item.to_dict() for item in Appointments.query.order_by(Appointments.scheduled_date).all()])

@appointments_bp.route("/<int:identifier>", methods=["GET", "PUT", "DELETE"])
def appointment(identifier):
    from flask import request
    item = existing(Appointments, identifier)
    if request.method == "GET":
        return jsonify(item.to_dict())
    if request.method == "PUT":
        apply_data(item, payload())
    else:
        db.session.delete(item)
    db.session.commit()
    return jsonify(message="Cita actualizada" if request.method == "PUT" else "Cita eliminada")

