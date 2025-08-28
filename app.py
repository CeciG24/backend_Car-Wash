from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from models.appointment import Appointments
from models.services import Services
app = Flask(__name__)

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///carwash.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Crear tablas
with app.app_context():
    db.create_all()

@app.route("/Services")
def get_services():
    servicios = Services.query.all()
    return { "Servicios: ": [s.name for s in servicios] }