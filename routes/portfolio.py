from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from models import db
from models.portfolioService import PortfolioService
from models.services import Services
from validation import payload, text, existing, date_value, video_url

portfolio_bp = Blueprint("portfolio", __name__, url_prefix="/portfolio")

def serialize(item):
    return {"id_servicio": item.id, "service_id": item.service_id,
            "servicio": item.service.name if item.service else None,
            "carro": item.car_model, "url": item.video_url,
            "descripcion": item.description, "fecha": item.date.isoformat() + "Z" if item.date else None}

def apply_data(item, data, creating=False):
    if creating or "car_model" in data:
        item.car_model = text(data, "car_model")
    if creating or "service_id" in data:
        item.service_id = existing(Services, data.get("service_id")).id_service
    if creating or "video_url" in data:
        item.video_url = video_url(data)
    if creating or "description" in data:
        item.description = text(data, "description", 10000, optional=True)
    if "date" in data:
        item.date = date_value(data["date"])
    elif creating:
        item.date = datetime.now(timezone.utc).replace(tzinfo=None)

@portfolio_bp.route("", methods=["GET", "POST"])
def portfolio():
    if request.method == "GET":
        rows = PortfolioService.query.order_by(PortfolioService.date.desc(), PortfolioService.id.desc()).all()
        return jsonify(Servicios=[serialize(item) for item in rows])
    item = PortfolioService()
    apply_data(item, payload(), True)
    db.session.add(item)
    db.session.commit()
    return jsonify(message="Video creado", id=item.id), 201

@portfolio_bp.route("/<int:identifier>", methods=["GET", "PUT", "DELETE"])
def portfolio_item(identifier):
    item = existing(PortfolioService, identifier)
    if request.method == "GET":
        return jsonify(Servicio=serialize(item))
    if request.method == "PUT":
        apply_data(item, payload())
    else:
        db.session.delete(item)
    db.session.commit()
    return jsonify(message="Video actualizado" if request.method == "PUT" else "Video eliminado")

