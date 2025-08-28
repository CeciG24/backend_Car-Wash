from datetime import datetime
from . import db
import enum

class TipoEnum(enum.Enum):
    EXPRESS="Express"
    BASICO="Basico"
    PREMIUM="Premium"
    SUPREME="Supreme"
    EXTRA="Extra"

class Services(db.Model):
    __tablename__ = 'Services'
    
    id_service = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name=db.Column(db.String(100), nullable=False)
    price=db.Column(db.Integer, nullable=False)
    tipo=db.Column(db.Enum(TipoEnum),nullable=False)
    def __repr__(self):
        return f'<Service {self.id_eval}>'