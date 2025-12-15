from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app(config_class='config'):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Inicializar extensiones
    db.init_app(app)
    
    return app

# Importar todos los modelos para que SQLAlchemy los registre
from models.user import User
from models.services import Services
from models.serviceDescription import ServiceDescription
from models.appointment import Appointments
from models.review import Review
from models.portfolioService import PortfolioService

__all__ = ['db', 'User', 'Services', 'ServiceDescription', 'Appointments', 'Review', 'PortfolioService']