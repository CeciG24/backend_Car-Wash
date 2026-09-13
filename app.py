from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError
from models import db
from config import Config
from extensions import mail

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    app.url_map.strict_slashes = False
    db.init_app(app)
    CORS(app, origins=app.config["CORS_ORIGINS"])
    mail.init_app(app)
    from routes.services import services_bp
    from routes.appointments import appointments_bp
    from routes.reviews import reviews_bp
    from routes.portfolio import portfolio_bp
    from routes.contacts import contacts_bp
    from routes.auth import users_bp, register_commands
    from routes.charts import charts_bp
    for blueprint in (services_bp, appointments_bp, reviews_bp, portfolio_bp, contacts_bp, users_bp, charts_bp):
        app.register_blueprint(blueprint)
    from security import protect_routes
    app.before_request(protect_routes)
    register_commands(app)

    @app.errorhandler(HTTPException)
    def http_error(error):
        db.session.rollback()
        return jsonify(error=error.description), error.code

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        db.session.rollback()
        return jsonify(error="El registro está duplicado o tiene relaciones que impiden esta operación"), 409

    @app.errorhandler(Exception)
    def server_error(error):
        db.session.rollback()
        app.logger.exception("Error de servidor")
        return jsonify(error="No se pudo completar la operación"), 500

    with app.app_context():
        db.create_all()
    return app

if __name__ == "__main__":
    create_app().run()

