import bcrypt
import click
from flask import Blueprint, jsonify, current_app, g
from werkzeug.exceptions import BadRequest, Conflict, Unauthorized, Forbidden
from models import db
from models.user import User
from security import serializer, is_admin
from validation import payload, text

users_bp = Blueprint("auth", __name__)

def create_user(data):
    name = text(data, "nombre")
    email = text(data, "email").lower()
    password = text(data, "contraseña", 72)
    if "@" not in email or len(password) < 8 or len(password.encode("utf-8")) > 72:
        raise BadRequest("Correo inválido o contraseña menor de 8 caracteres / mayor de 72 bytes")
    if User.query.filter_by(email=email).first():
        raise Conflict("El correo ya está registrado")
    user = User(nombre=name, email=email,
                contraseña_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode())
    db.session.add(user)
    db.session.commit()
    return user

@users_bp.route("/register", methods=["POST"])
def register():
    create_user(payload())
    return jsonify(message="Usuario registrado exitosamente"), 201

@users_bp.route("/login", methods=["POST"])
def login():
    data = payload()
    email = text(data, "email").lower()
    password = text(data, "contraseña", 72)
    if len(password.encode()) > 72:
        raise Unauthorized("Credenciales incorrectas")
    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.checkpw(password.encode(), user.contraseña_hash.encode()):
        raise Unauthorized("Credenciales incorrectas")
    if not is_admin(user):
        raise Forbidden("Esta cuenta no tiene acceso administrativo")
    token = serializer().dumps({"user_id": user.id_usuario})
    return jsonify(token=token, expires_in=current_app.config["AUTH_TOKEN_MAX_AGE"])

@users_bp.route("/user/me", methods=["GET"])
def me():
    return jsonify(id_usuario=g.user.id_usuario, nombre=g.user.nombre,
                   email=g.user.email, rol="admin")

def register_commands(app):
    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--nombre", prompt=True)
    @click.password_option()
    def create_admin(email, nombre, password):
        if email.lower() not in app.config["ADMIN_EMAILS"]:
            raise click.ClickException("Agrega primero este correo a ADMIN_EMAILS")
        create_user({"email": email, "nombre": nombre, "contraseña": password})
        click.echo("Administrador creado.")

