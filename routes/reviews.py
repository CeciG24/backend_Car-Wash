from flask import Blueprint, jsonify, request
from models import db
from models.review import Review

reviews_bp = Blueprint('reviews', __name__, url_prefix='/reviews')

#CRUD Reseñas

#Obtener todas las reseñas
@reviews_bp.route("/", methods=['GET'])
def get_reviews():
    try:
        reviews = Review.query.all()
        return jsonify({
            "Reseñas": [r.to_json() for r in reviews]
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener reseñas: {str(e)}"}), 500 

#Crear una nueva reseña
@reviews_bp.route("/", methods=['POST'])
def post_review():
    try:
        data = request.get_json()
        nombre_cliente = data.get("nombre_cliente")
        comentario = data.get("comentario")
        calificacion = data.get("calificacion", 5)

        if not all([nombre_cliente, comentario]):
            return jsonify({"error": "Faltan campos"}), 400

        nueva_reseña = Review(
            nombre_cliente=nombre_cliente,
            comentario=comentario,
            calificacion=calificacion
        )

        db.session.add(nueva_reseña)
        db.session.commit()

        return jsonify({"message": "Reseña creada exitosamente"}), 201
    except Exception as e:
        return jsonify({"error": f"Error al crear reseña: {str(e)}"}), 500
    
#Eliminar una reseña por ID
@reviews_bp.route("/<int:review_id>", methods=['DELETE'])
def delete_review(review_id):
    try:
        reseña = Review.query.get(review_id)
        if not reseña:
            return jsonify({"error": "Reseña no encontrada"}), 404

        db.session.delete(reseña)
        db.session.commit()

        return jsonify({"message": "Reseña eliminada exitosamente"}), 200
    except Exception as e:
        return jsonify({"error": f"Error al eliminar reseña: {str(e)}"}), 500
    
#Actualizar una reseña por ID
@reviews_bp.route("/<int:review_id>", methods=['PUT']) 
def update_review(review_id):
    try:
        data = request.get_json()
        reseña = Review.query.get(review_id)
        if not reseña:
            return jsonify({"error": "Reseña no encontrada"}), 404

        reseña.nombre_cliente = data.get("nombre_cliente", reseña.nombre_cliente)
        reseña.comentario = data.get("comentario", reseña.comentario)
        reseña.calificacion = data.get("calificacion", reseña.calificacion)

        db.session.commit()

        return jsonify({"message": "Reseña actualizada exitosamente"}), 200
    except Exception as e:
        return jsonify({"error": f"Error al actualizar reseña: {str(e)}"}), 500