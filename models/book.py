from datetime import datetime
from models import db


class Libro(db.Model):
    """Representa un libro en el inventario de la librería."""

    __tablename__ = 'libros'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(150), nullable=False)
    editorial = db.Column(db.String(100), nullable=False)
    anio_publicacion = db.Column(db.Integer, nullable=False)
    isbn = db.Column(db.String(20), nullable=False, unique=True)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # False cuando el libro es eliminado lógicamente (no se borra físicamente)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # Relaciones
    detalles_venta = db.relationship('DetalleVenta', backref='libro', lazy=True)
    movimientos = db.relationship('MovimientoInventario', backref='libro', lazy=True)


    def reducir_stock(self, cantidad):
        """
        Reduce el stock del libro en la cantidad indicada.
        Lanza un error si no hay suficiente stock disponible.
        Deshabilita el libro automáticamente si el stock llega a 0.
        """
        if cantidad > self.stock:
            raise ValueError(
                f"Stock insuficiente. Disponible: {self.stock}, solicitado: {cantidad}"
            )
        self.stock -= cantidad
        if self.stock == 0:
            self.activo = False

    def aumentar_stock(self, cantidad):
        """
        Aumenta el stock del libro en la cantidad indicada.
        Reactiva el libro automáticamente si estaba deshabilitado por stock 0.
        """
        if cantidad <= 0:
            raise ValueError("La cantidad a agregar debe ser mayor a cero.")
        self.stock += cantidad
        if not self.activo:
            self.activo = True

    def tiene_stock(self, cantidad=1):
        """Retorna True si hay suficiente stock para la cantidad solicitada."""
        return self.stock >= cantidad

    def nivel_alerta(self):
        """
        Retorna el tipo de alerta según el stock actual.
        Retorna 'ALERTA_ROJA' si stock <= 2,
        'ALERTA_AMARILLA' si stock entre 3 y 5,
        o None si no hay alerta.
        """
        if self.stock <= 2:
            return 'ALERTA_ROJA'
        elif self.stock <= 5:
            return 'ALERTA_AMARILLA'
        return None

    def __repr__(self):
        return f'<Libro {self.nombre} | Stock: {self.stock}>'


class MovimientoInventario(db.Model):
    """
    Registra cada cambio en el stock de un libro.
    Permite auditoría y trazabilidad completa del inventario.
    """

    __tablename__ = 'movimientos_inventario'

    id = db.Column(db.Integer, primary_key=True)
    libro_id = db.Column(db.Integer, db.ForeignKey('libros.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)

    # Tipos: ENTRADA, VENTA, ANULACION, AJUSTE
    tipo_movimiento = db.Column(db.String(20), nullable=False)

    cantidad = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.Text, nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Movimiento {self.tipo_movimiento} | Libro: {self.libro_id} | Cant: {self.cantidad}>'