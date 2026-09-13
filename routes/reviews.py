from flask import Blueprint, jsonify, request
from models import db
from models.review import Review
from validation import payload, text, integer, existing

reviews_bp = Blueprint("reviews", __name__, url_prefix="/reviews")

def apply_data(item, data, creating=False):
    for field, size in (("nombre_cliente", 100), ("comentario", 10000)):
        if creating or field in data:
            setattr(item, field, text(data, field, size))
    if creating or "calificacion" in data:
        item.calificacion = integer(data.get("calificacion", 5), "calificacion", 1, 5)

@reviews_bp.route("", methods=["GET", "POST"])
def reviews():
    if request.method == "GET":
        return jsonify({"Reseñas": [item.to_json() for item in Review.query.order_by(Review.fecha.desc()).all()]})
    item = Review()
    apply_data(item, payload(), True)
    db.session.add(item)
    db.session.commit()
    return jsonify(message="Reseña creada exitosamente"), 201

@reviews_bp.route("/<int:identifier>", methods=["PUT", "DELETE"])
def review(identifier):
    item = existing(Review, identifier)
    if request.method == "PUT":
        apply_data(item, payload())
    else:
        db.session.delete(item)
    db.session.commit()
    return jsonify(message="Reseña actualizada" if request.method == "PUT" else "Reseña eliminada")

