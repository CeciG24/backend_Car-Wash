"""Local-only disposable demonstration server. Never uses DATABASE_URL."""
from datetime import datetime, timedelta, timezone
import bcrypt
from app import create_app
from models import db
from models.user import User
from models.services import Services, TipoEnum, VehiculoEnum
from models.appointment import Appointments, statusEnum
from models.material import Material

if __name__ == "__main__":
    app = create_app({
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "preview-only-disposable-secret",
        "ADMIN_EMAILS": {"demo@example.test"},
        "CORS_ORIGINS": ["http://127.0.0.1:5175", "http://localhost:5175"],
        "MAIL_SUPPRESS_SEND": True, "CONTACT_EMAIL": None
    })
    with app.app_context():
        db.session.add(User(nombre="Demo", email="demo@example.test",
                            contraseña_hash=bcrypt.hashpw(b"Demo-preview-123", bcrypt.gensalt()).decode()))
        service = Services(name="Lavado premium (demo)", price=350, tipo=TipoEnum.PREMIUM, vehiculo=VehiculoEnum.AUTO)
        db.session.add(service)
        db.session.flush()
        db.session.add(Appointments(name="Cliente de demostración", num_whatsapp="0000000000", direccion="Dirección de prueba",
                                    scheduled_date=datetime.now(timezone.utc).replace(tzinfo=None)+timedelta(days=1),
                                    status=statusEnum.PENDING, id_service=service.id_service))
        db.session.add(Material(name="Producto de demostración", purpose="Ejemplo para revisar inventario", category="Químico",
                                unit="ml", quantity=150, minimum=200, notes="Dato de demostración",
                                dilutions=[], active=True))
        db.session.commit()
    app.run(host="127.0.0.1", port=5002, debug=False)

