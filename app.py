from flask import Flask
from flask_cors import CORS
from flask_mail import Mail
from models import db
from config import Config

mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Inicializar extensiones
    db.init_app(app)
    CORS(app)
    mail.init_app(app)  # Inicializar Flask-Mail
    
    # Registrar blueprints
    from routes.services import services_bp
    from routes.appointments import appointments_bp
    from routes.reviews import reviews_bp
    from routes.portfolio import portfolio_bp
    from routes.contacts import contacts_bp
    from routes.auth import users_bp
    
    app.register_blueprint(services_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(users_bp)

    app.register_blueprint(contacts_bp)
    
    # Crear tablas
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
