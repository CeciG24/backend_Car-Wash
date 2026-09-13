from flask import Blueprint, jsonify, request
from werkzeug.exceptions import Conflict
from models import db
from models.services import Services, VehiculoEnum, TipoEnum
from models.serviceDescription import ServiceDescription
from validation import payload, text, integer, enum_value, existing

services_bp = Blueprint("services", __name__, url_prefix="/services")

def serialize(item):
    return {"id_servicio": item.id_service, "nombre": item.name, "precio": item.price,
            "tipo": item.tipo.value, "vehiculo": item.vehiculo.value if item.vehiculo else None}

def description_json(item):
    return {"id_description": item.id_description, "id_servicio": item.service_id,
            "descripcion": item.description, "order": item.order}

def apply_data(item, data, creating=False):
    if creating or "name" in data:
        item.name = text(data, "name")
    if creating or "price" in data:
        item.price = integer(data.get("price"), "price")
    if creating or "tipo" in data:
        item.tipo = enum_value(TipoEnum, data.get("tipo"), "tipo")
    if "vehiculo" in data:
        item.vehiculo = enum_value(VehiculoEnum, data["vehiculo"], "vehiculo") if data["vehiculo"] else None

@services_bp.route("", methods=["GET", "POST"])
def services():
    if request.method == "GET":
        return jsonify(Servicios=[serialize(item) for item in Services.query.order_by(Services.id_service).all()])
    item = Services()
    apply_data(item, payload(), True)
    db.session.add(item)
    db.session.commit()
    return jsonify(message="Servicio creado", id_service=item.id_service, service=serialize(item)), 201

@services_bp.route("/<int:identifier>", methods=["GET", "PUT", "DELETE"])
def service(identifier):
    item = existing(Services, identifier)
    if request.method == "GET":
        return jsonify(Servicio=serialize(item))
    if request.method == "PUT":
        apply_data(item, payload())
    else:
        if item.appointments or item.portfolio_services:
            raise Conflict("El servicio está asociado a citas o videos; no puede eliminarse")
        db.session.delete(item)
    db.session.commit()
    return jsonify(message="Servicio actualizado" if request.method == "PUT" else "Servicio eliminado")

@services_bp.route("/descriptions", methods=["GET", "POST"])
def descriptions():
    if request.method == "GET":
        rows = ServiceDescription.query.order_by(ServiceDescription.service_id, ServiceDescription.order).all()
        return jsonify(Descripciones=[description_json(item) for item in rows])
    data = payload()
    item = ServiceDescription(service_id=existing(Services, data.get("service_id")).id_service,
                              description=text(data, "description", 10000),
                              order=integer(data.get("order", 0), "order"))
    db.session.add(item)
    db.session.commit()
    return jsonify(message="Descripción creada", id_description=item.id_description), 201

# GET uses a service ID for compatibility. PUT/DELETE use a description ID.
@services_bp.route("/descriptions/<int:identifier>", methods=["GET", "PUT", "DELETE"])
def description(identifier):
    if request.method == "GET":
        existing(Services, identifier)
        rows = ServiceDescription.query.filter_by(service_id=identifier).order_by(ServiceDescription.order, ServiceDescription.id_description).all()
        return jsonify(Descripcion={"id_servicio": identifier, "descripcion": "\n".join(row.description for row in rows)},
                       Descripciones=[description_json(row) for row in rows])
    item = existing(ServiceDescription, identifier)
    if request.method == "PUT":
        data = payload()
        if "description" in data:
            item.description = text(data, "description", 10000)
        if "order" in data:
            item.order = integer(data["order"], "order")
    else:
        db.session.delete(item)
    db.session.commit()
    return jsonify(message="Descripción actualizada" if request.method == "PUT" else "Descripción eliminada")

