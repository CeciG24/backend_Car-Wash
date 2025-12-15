from .services import services_bp
from .appointments import appointments_bp
from .reviews import reviews_bp
from .portfolio import portfolio_bp
from .contacts import contacts_bp
from .auth import users_bp

__all__ = ['services_bp', 'appointments_bp', 'reviews_bp', 'portfolio_bp', 'contacts_bp', 'users_bp']