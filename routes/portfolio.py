from flask import Blueprint, jsonify, request
from models import db
from models.portfolioService import PortfolioService

portfolio_bp = Blueprint('portfolio', __name__, url_prefix='/portfolio')

#CRUD de servicios del portafolio

# Obtener todos los servicios del portafolio
@portfolio_bp.route("/", methods=['GET'])
def get_portfolioServices():
    try:
        portfolio = PortfolioService.query.all()
        return jsonify({
            "Servicios": [{
                "id_servicio": s.id_service,
                "carro": s.car_model,
                "url": s.video_url,
                "descripcion": s.description,
                "fecha": s.date
            } for s in portfolio]
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error al obtener servicios del portafolio: {str(e)}"}), 500
    
# Crear un nuevo servicio del portafolio
@portfolio_bp.route("/", methods=['POST'])
def create_portfolioService():
    try:
        data = request.get_json()
        new_service = PortfolioService(
            car_model=data['car_model'],
            service_id=data['service_id'],
            video_url=data['video_url'],
            description=data['description'],
            date=data['date']
        )
        db.session.add(new_service)
        db.session.commit()
        return jsonify({"message": "Servicio del portafolio creado exitosamente"}), 201
    except Exception as e:
        return jsonify({"error": f"Error al crear servicio del portafolio: {str(e)}"}), 500
    
# Actualizar un servicio del portafolio existente
@portfolio_bp.route("/<int:id_service>", methods=['PUT'])
def update_portfolioService(id_service):
    try:
        data = request.get_json()
        service = PortfolioService.query.get(id_service)
        if not service:
            return jsonify({"error": "Servicio no encontrado"}), 404

        service.car_model = data.get('car_model', service.car_model)
        service.service_id = data.get('service_id', service.service_id)
        service.video_url = data.get('video_url', service.video_url)
        service.description = data.get('description', service.description)
        service.date = data.get('date', service.date)

        db.session.commit()
        return jsonify({"message": "Servicio del portafolio actualizado exitosamente"}), 200
    except Exception as e:
        return jsonify({"error": f"Error al actualizar servicio del portafolio: {str(e)}"}), 500
    
# Eliminar un servicio del portafolio
@portfolio_bp.route("/<int:id_service>", methods=['DELETE'])
def delete_portfolioService(id_service):
    try:
        service = PortfolioService.query.get(id_service)
        if not service:
            return jsonify({"error": "Servicio no encontrado"}), 404

        db.session.delete(service)
        db.session.commit()
        return jsonify({"message": "Servicio del portafolio eliminado exitosamente"}), 200
    except Exception as e:
        return jsonify({"error": f"Error al eliminar servicio del portafolio: {str(e)}"}), 500