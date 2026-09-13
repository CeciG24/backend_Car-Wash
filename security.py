from flask import current_app, request, g
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.exceptions import Unauthorized, Forbidden, ServiceUnavailable
from models import db
from models.user import User

def serializer():
    secret = current_app.config.get("SECRET_KEY")
    if not secret or secret == "dev-secret-key":
        raise ServiceUnavailable("Configura SECRET_KEY para habilitar la autenticación")
    return URLSafeTimedSerializer(secret, salt="ls1713-auth-v1")

def is_admin(user):
    return user.email.lower() in current_app.config["ADMIN_EMAILS"]

def require_admin():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise Unauthorized("Inicia sesión para continuar")
    try:
        data = serializer().loads(header[7:], max_age=current_app.config["AUTH_TOKEN_MAX_AGE"])
        user = db.session.get(User, int(data["user_id"]))
    except (BadSignature, SignatureExpired, ValueError, TypeError, KeyError):
        raise Unauthorized("Sesión inválida o expirada")
    if user is None:
        raise Unauthorized("Sesión inválida")
    if not is_admin(user):
        raise Forbidden("Se requieren permisos de administrador")
    g.user = user

def protect_routes():
    if request.method == "OPTIONS" or request.endpoint is None:
        return
    private = request.blueprint in ("charts", "materials")
    private |= request.blueprint == "appointments" and request.method != "POST"
    private |= request.blueprint in ("services", "portfolio") and request.method not in ("GET", "HEAD")
    private |= request.blueprint == "reviews" and request.method not in ("GET", "HEAD", "POST")
    private |= request.endpoint in ("auth.register", "auth.me")
    if private:
        require_admin()


