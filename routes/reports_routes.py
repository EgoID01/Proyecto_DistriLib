import json
from datetime import datetime, date
from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import func, extract
from models import db
from models.book import Libro, MovimientoInventario
from models.client import Cliente
from models.sale import Venta, DetalleVenta
from models.user import Usuario, Rol
from utils.decorators import solo_admin
from utils.helpers import redirigir_segun_estado

reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes')

MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
         'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']


# ── Estadístico de ventas ────────────────────────────────────────────────────

@reportes_bp.route('/estadistico')
@login_required
@solo_admin
def estadistico():
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    # Años con ventas activas registradas
    años_raw = (db.session.query(extract('year', Venta.fecha_venta).label('año'))
                .filter(Venta.estado == 'ACTIVA')
                .distinct()
                .order_by('año')
                .all())
    años_disponibles = [int(r.año) for r in años_raw] or [datetime.now().year]

    try:
        año = int(request.args.get('año', años_disponibles[-1]))
    except (ValueError, TypeError):
        año = años_disponibles[-1]
    if año not in años_disponibles:
        año = años_disponibles[-1]

    # Ventas mensuales del año seleccionado (solo ACTIVA)
    filas_mes = db.session.query(
        extract('month', Venta.fecha_venta).label('mes'),
        func.sum(Venta.total).label('total')
    ).filter(
        extract('year', Venta.fecha_venta) == año,
        Venta.estado == 'ACTIVA'
    ).group_by('mes').order_by('mes').all()

    ventas_por_mes = [0.0] * 12
    for fila in filas_mes:
        ventas_por_mes[int(fila.mes) - 1] = float(fila.total)

    # Top 5 libros más vendidos del año seleccionado (por cantidad, ventas ACTIVA)
    top_libros = db.session.query(
        Libro.nombre,
        func.sum(DetalleVenta.cantidad).label('cantidad_total')
    ).join(DetalleVenta, DetalleVenta.libro_id == Libro.id
    ).join(Venta, Venta.id == DetalleVenta.venta_id
    ).filter(
        Venta.estado == 'ACTIVA',
        extract('year', Venta.fecha_venta) == año,
    ).group_by(Libro.id, Libro.nombre
    ).order_by(func.sum(DetalleVenta.cantidad).desc()
    ).limit(5).all()

    nombres_top    = [r.nombre for r in top_libros]
    cantidades_top = [int(r.cantidad_total) for r in top_libros]
    total_año      = sum(ventas_por_mes)

    return render_template('reportes/estadistico.html',
                           año=año,
                           años_disponibles=años_disponibles,
                           meses=json.dumps(MESES),
                           ventas_por_mes=json.dumps(ventas_por_mes),
                           nombres_top=json.dumps(nombres_top),
                           cantidades_top=json.dumps(cantidades_top),
                           total_año=total_año)


# ── Reportes de ventas ───────────────────────────────────────────────────────

@reportes_bp.route('/ventas')
@login_required
@solo_admin
def reporte_ventas():
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    # Filtros
    fecha_desde  = request.args.get('fecha_desde', '')
    fecha_hasta  = request.args.get('fecha_hasta', '')
    vendedor_id  = request.args.get('vendedor_id', '')
    tab_activa   = request.args.get('tab', 'general')

    vendedores = (Usuario.query
                  .join(Rol, Usuario.rol_id == Rol.id)
                  .filter(Usuario.activo == True, Rol.nombre.in_(['ADMIN', 'VENDEDOR']))
                  .order_by(Usuario.nombres)
                  .all())

    def base_query():
        q = db.session.query(Venta).filter(Venta.estado == 'ACTIVA')
        if fecha_desde:
            q = q.filter(Venta.fecha_venta >= fecha_desde)
        if fecha_hasta:
            q = q.filter(Venta.fecha_venta <= fecha_hasta + ' 23:59:59')
        if vendedor_id:
            q = q.filter(Venta.usuario_id == int(vendedor_id))
        return q

    # General
    ventas_general = base_query().order_by(Venta.fecha_venta.desc()).all()
    total_general  = sum(float(v.total) for v in ventas_general)

    # Por producto
    q_producto = db.session.query(
        Libro.nombre,
        Libro.isbn,
        func.sum(DetalleVenta.cantidad).label('cantidad'),
        func.sum(DetalleVenta.subtotal).label('subtotal')
    ).join(DetalleVenta, DetalleVenta.libro_id == Libro.id
    ).join(Venta, Venta.id == DetalleVenta.venta_id
    ).filter(Venta.estado == 'ACTIVA')

    if fecha_desde:
        q_producto = q_producto.filter(Venta.fecha_venta >= fecha_desde)
    if fecha_hasta:
        q_producto = q_producto.filter(Venta.fecha_venta <= fecha_hasta + ' 23:59:59')
    if vendedor_id:
        q_producto = q_producto.filter(Venta.usuario_id == int(vendedor_id))

    ventas_producto = q_producto.group_by(Libro.id, Libro.nombre, Libro.isbn
                      ).order_by(func.sum(DetalleVenta.subtotal).desc()).all()

    # Por cliente
    q_cliente = db.session.query(
        Cliente.cedula_ruc,
        Cliente.nombres,
        Cliente.apellidos,
        func.count(Venta.id).label('num_ventas'),
        func.sum(Venta.total).label('total')
    ).join(Venta, Venta.cliente_id == Cliente.id
    ).filter(Venta.estado == 'ACTIVA')

    if fecha_desde:
        q_cliente = q_cliente.filter(Venta.fecha_venta >= fecha_desde)
    if fecha_hasta:
        q_cliente = q_cliente.filter(Venta.fecha_venta <= fecha_hasta + ' 23:59:59')
    if vendedor_id:
        q_cliente = q_cliente.filter(Venta.usuario_id == int(vendedor_id))

    ventas_cliente = q_cliente.group_by(Cliente.id, Cliente.cedula_ruc,
                     Cliente.nombres, Cliente.apellidos
                     ).order_by(func.sum(Venta.total).desc()).all()

    # Por vendedor
    q_vendedor = db.session.query(
        Usuario.nombres,
        func.count(Venta.id).label('num_ventas'),
        func.sum(Venta.total).label('total')
    ).join(Venta, Venta.usuario_id == Usuario.id
    ).filter(Venta.estado == 'ACTIVA')

    if fecha_desde:
        q_vendedor = q_vendedor.filter(Venta.fecha_venta >= fecha_desde)
    if fecha_hasta:
        q_vendedor = q_vendedor.filter(Venta.fecha_venta <= fecha_hasta + ' 23:59:59')

    ventas_vendedor = q_vendedor.group_by(Usuario.id, Usuario.nombres
                      ).order_by(func.sum(Venta.total).desc()).all()

    return render_template('reportes/ventas.html',
                           vendedores=vendedores,
                           fecha_desde=fecha_desde,
                           fecha_hasta=fecha_hasta,
                           vendedor_id=vendedor_id,
                           tab_activa=tab_activa,
                           ventas_general=ventas_general,
                           total_general=total_general,
                           ventas_producto=ventas_producto,
                           ventas_cliente=ventas_cliente,
                           ventas_vendedor=ventas_vendedor)


# ── Reportes de inventario ───────────────────────────────────────────────────

@reportes_bp.route('/inventario')
@login_required
@solo_admin
def reporte_inventario():
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    tab_activa = request.args.get('tab', 'general')

    libros_general  = Libro.query.order_by(Libro.nombre.asc()).all()
    libros_criticos = Libro.query.filter(Libro.stock >= 1, Libro.stock <= 2).order_by(Libro.stock.asc()).all()
    libros_bajo     = Libro.query.filter(Libro.stock >= 3, Libro.stock <= 5).order_by(Libro.stock.asc()).all()
    libros_agotados = Libro.query.filter(Libro.stock == 0).order_by(Libro.nombre.asc()).all()

    movimientos = MovimientoInventario.query.order_by(
        MovimientoInventario.fecha.desc()
    ).limit(200).all()

    return render_template('reportes/inventario.html',
                           tab_activa=tab_activa,
                           libros_general=libros_general,
                           libros_criticos=libros_criticos,
                           libros_bajo=libros_bajo,
                           libros_agotados=libros_agotados,
                           movimientos=movimientos)
