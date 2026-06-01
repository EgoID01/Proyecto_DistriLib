from datetime import datetime
from models import db


class Venta(db.Model):
    """
    Representa una transacción de compra completa.
    Las ventas nunca se eliminan físicamente; se marcan como ANULADA.
    """

    __tablename__ = 'ventas'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)

    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    # Los libros están exentos de IVA en Ecuador, este campo siempre será 0
    iva = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    # Estado lógico: ACTIVA o ANULADA
    estado = db.Column(db.String(10), nullable=False, default='ACTIVA')

    fecha_venta = db.Column(db.DateTime, default=datetime.now, nullable=False)

    # Relación: una venta tiene muchos detalles (líneas de productos)
    detalles = db.relationship('DetalleVenta', backref='venta', lazy=True)

    def calcular_total(self):
        """
        Recalcula el subtotal y total sumando todos los detalles.
        Los libros son exentos de IVA (0%), por lo que total = subtotal.
        """
        self.subtotal = sum(detalle.subtotal for detalle in self.detalles)
        self.iva = 0
        self.total = self.subtotal

    def anular(self):
        """
        Marca la venta como ANULADA.
        La restauración del stock se maneja en la ruta, no aquí,
        para poder registrar también el movimiento de inventario.
        """
        self.estado = 'ANULADA'

    def esta_activa(self):
        """Retorna True si la venta está en estado ACTIVA."""
        return self.estado == 'ACTIVA'

    def __repr__(self):
        return f'<Venta #{self.id} | Estado: {self.estado} | Total: {self.total}>'


class DetalleVenta(db.Model):
    """
    Línea de detalle de una venta.
    Resuelve la relación muchos a muchos entre Venta y Libro.
    """

    __tablename__ = 'detalle_venta'

    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('ventas.id'), nullable=False)
    libro_id = db.Column(db.Integer, db.ForeignKey('libros.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)

    # Se guarda el precio al momento de la venta para mantener trazabilidad histórica
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)

    subtotal = db.Column(db.Numeric(10, 2), nullable=False)

    def calcular_subtotal(self):
        """Calcula el subtotal multiplicando precio unitario por cantidad."""
        self.subtotal = self.precio_unitario * self.cantidad

    def __repr__(self):
        return f'<DetalleVenta venta={self.venta_id} libro={self.libro_id} cant={self.cantidad}>'


