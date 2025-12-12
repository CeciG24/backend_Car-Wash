from . import db
import enum

class TipoEnum(enum.Enum):
    EXPRESS="Express"
    BASICO="Basico"
    PREMIUM="Premium"
    SUPREME="Supreme"
    EXTRA="Extra"

class VehiculoEnum(enum.Enum):
    MOTO="Moto"
    AUTO="Auto"
    SUV="SUV"
    SUV_G="SUV Grande"
    PICKUP="Pickup"
    PICKUP_G="Pickup grande"

class Services(db.Model):
    __tablename__ = 'services'
    
    id_service = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name=db.Column(db.String(100), nullable=False)
    price=db.Column(db.Integer, nullable=False)
    tipo=db.Column(db.Enum(TipoEnum, name="tipo_enum"),nullable=False)
    vehiculo=db.Column(db.Enum(VehiculoEnum, name="vehiculo_enum"),nullable=True)

    descriptions = db.relationship("ServiceDescription", back_populates="service", cascade="all, delete-orphan")
    appointments = db.relationship("Appointments", back_populates="service")
    portfolio_services = db.relationship("PortfolioService", back_populates="service")

    def __repr__(self):
        return f'<Service {self.id_service}>'