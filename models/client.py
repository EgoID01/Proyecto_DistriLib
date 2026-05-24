from datetime import datetime
from models import db


class Cliente(db.Model):
    """Representa a un comprador registrado en el sistema."""

    __tablename__ = 'clientes'

    id = db.Column(db.Integer, primary_key=True)

    # Cédula o RUC único, es el identificador principal del cliente
    cedula_ruc = db.Column(db.String(20), nullable=False, unique=True)

    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200), nullable=True)
    telefono = db.Column(db.String(20), nullable=True)
    correo = db.Column(db.String(100), nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relación: un cliente puede tener muchas ventas
    ventas = db.relationship('Venta', backref='cliente', lazy=True)

    def nombre_completo(self):
        """Retorna el nombre completo del cliente."""
        return f"{self.nombres} {self.apellidos}"

    def __repr__(self):
        return f'<Cliente {self.cedula_ruc} - {self.nombre_completo()}>'