from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models import db


class Rol(db.Model):
    """Representa los roles del sistema: ADMIN, BODEGUERO, VENDEDOR."""

    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    descripcion = db.Column(db.Text, nullable=True)

    # Relación: un rol tiene muchos usuarios
    usuarios = db.relationship('Usuario', backref='rol', lazy=True)

    def __repr__(self):
        return f'<Rol {self.nombre}>'


class Usuario(UserMixin, db.Model):
    """Representa a los empleados que acceden al sistema."""

    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombres = db.Column(db.String(150), nullable=False)
    cedula = db.Column(db.String(20), nullable=False, unique=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)

    # True mientras el usuario no haya cambiado su contraseña temporal
    password_temporal = db.Column(db.Boolean, default=True, nullable=False)

    # True en el primer acceso, obliga a completar preguntas de seguridad
    primer_login = db.Column(db.Boolean, default=True, nullable=False)

    # False si el administrador desactiva la cuenta
    activo = db.Column(db.Boolean, default=True, nullable=False)

    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    ventas = db.relationship('Venta', backref='vendedor', lazy=True)
    movimientos = db.relationship('MovimientoInventario', backref='usuario', lazy=True)
    respuestas_seguridad = db.relationship('RespuestaSeguridad', backref='usuario', lazy=True)

    def set_password(self, password):
        """Genera el hash seguro de la contraseña usando Werkzeug."""
        self.password_hash = generate_password_hash(password)

    def verificar_password(self, password):
        """Compara la contraseña ingresada contra el hash almacenado."""
        return check_password_hash(self.password_hash, password)

    def es_admin(self):
        """Retorna True si el usuario tiene rol ADMIN."""
        return self.rol.nombre == 'ADMIN'

    def es_bodeguero(self):
        """Retorna True si el usuario tiene rol BODEGUERO."""
        return self.rol.nombre == 'BODEGUERO'

    def es_vendedor(self):
        """Retorna True si el usuario tiene rol VENDEDOR."""
        return self.rol.nombre == 'VENDEDOR'

    def __repr__(self):
        return f'<Usuario {self.username}>'


class PreguntaSeguridad(db.Model):
    """Contiene las preguntas disponibles para recuperación de contraseña."""

    __tablename__ = 'preguntas_seguridad'

    id = db.Column(db.Integer, primary_key=True)
    pregunta = db.Column(db.String(200), nullable=False)

    # Relación con respuestas
    respuestas = db.relationship('RespuestaSeguridad', backref='pregunta', lazy=True)

    def __repr__(self):
        return f'<PreguntaSeguridad {self.id}>'


class RespuestaSeguridad(db.Model):
    """Guarda las respuestas de seguridad seleccionadas por cada usuario (hash)."""

    __tablename__ = 'respuestas_seguridad'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    pregunta_id = db.Column(db.Integer, db.ForeignKey('preguntas_seguridad.id'), nullable=False)

    # La respuesta se almacena cifrada, nunca en texto plano
    respuesta_hash = db.Column(db.String(256), nullable=False)

    def set_respuesta(self, respuesta):
        """Cifra la respuesta antes de almacenarla."""
        self.respuesta_hash = generate_password_hash(respuesta.lower().strip())

    def verificar_respuesta(self, respuesta):
        """Verifica si la respuesta ingresada coincide con el hash almacenado."""
        return check_password_hash(self.respuesta_hash, respuesta.lower().strip())

    def __repr__(self):
        return f'<RespuestaSeguridad usuario={self.usuario_id} pregunta={self.pregunta_id}>'