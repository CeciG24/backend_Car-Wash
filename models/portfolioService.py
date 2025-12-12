from . import db
from datetime import datetime

class PortfolioService(db.Model):
    __tablename__ = 'portfolio_services'
    id = db.Column(db.Integer, primary_key=True)
    car_model = db.Column(db.String(100))
    service_id = db.Column(db.Integer, db.ForeignKey('services.id_service'), nullable=False)
    video_url = db.Column(db.String(200))
    description = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    service = db.relationship("Services", back_populates="portfolio_services")

    def __repr__(self):
        return f'<Portfolio {self.id}>'
