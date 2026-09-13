from flask import Blueprint, jsonify, request
from models.appointment import Appointments, statusEnum
from models.services import Services


charts_bp = Blueprint('charts', __name__, url_prefix='/charts')

@charts_bp.route('/appointments-status', methods=['GET'])
def get_appointments_status():
    try:
        status_counts = {
            'Pending': 0,
            'Completed': 0,
            'Canceled': 0
        }

        appointments = Appointments.query.all()
        for appointment in appointments:
            status_counts[appointment.status.value] += 1

        return jsonify(status_counts), 200
    except Exception as e:
        raise
    
@charts_bp.route('/services-popularity', methods=['GET'])
def get_services_popularity():
    try:
        service_counts = {}

        appointments = Appointments.query.all()
        for appointment in appointments:
            service_name = appointment.service.name if appointment.service else 'Unknown'
            if service_name in service_counts:
                service_counts[service_name] += 1
            else:
                service_counts[service_name] = 1

        return jsonify(service_counts), 200
    except Exception as e:
        raise
    
@charts_bp.route('/appointments-by-month', methods=['GET'])
def get_appointments_by_month():
    try:
        month_counts = {}

        appointments = Appointments.query.all()
        for appointment in appointments:
            month = appointment.scheduled_date.strftime('%Y-%m')
            if month in month_counts:
                month_counts[month] += 1
            else:
                month_counts[month] = 1

        return jsonify(month_counts), 200
    except Exception as e:
        raise
    
@charts_bp.route('/top-services', methods=['GET'])
def get_top_services():
    try:
        service_counts = {}

        appointments = Appointments.query.all()
        for appointment in appointments:
            service_name = appointment.service.name if appointment.service else 'Unknown'
            if service_name in service_counts:
                service_counts[service_name] += 1
            else:
                service_counts[service_name] = 1

        # Sort services by count and get top 5
        sorted_services = sorted(service_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_services = {service: count for service, count in sorted_services}

        return jsonify(top_services), 200
    except Exception as e:
        raise
    
@charts_bp.route('/monthly-revenue', methods=['GET'])
def get_monthly_revenue(): 
    try:
        monthly_revenue = {}

        appointments = Appointments.query.filter_by(status=statusEnum.COMPLETED).all()
        for appointment in appointments:
            month = appointment.scheduled_date.strftime('%Y-%m')
            service_price = appointment.service.price if appointment.service else 0
            if month in monthly_revenue:
                monthly_revenue[month] += service_price
            else:
                monthly_revenue[month] = service_price

        return jsonify(monthly_revenue), 200
    except Exception as e:
        raise

@charts_bp.route('/pending-appointments', methods=['GET'])
def get_pending_appointments():
    try:
        appointments = Appointments.query.filter_by(status=statusEnum.PENDING).all()
        return jsonify([appointment.to_dict() for appointment in appointments]), 200
    except Exception as e:
        raise
