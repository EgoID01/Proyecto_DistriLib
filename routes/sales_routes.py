from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user
from models import db
from models.book import Libro, MovimientoInventario
from models.client import Cliente
from models.sale import Venta, DetalleVenta
from utils.decorators import verificar_rol
from utils.helpers import redirigir_segun_estado

ventas_bp = Blueprint('ventas', __name__, url_prefix='/ventas')

SESSION_LIBROS  = 'venta_libros'
SESSION_CLIENTE = 'venta_cliente'


# ── Paso 1: Selección de libros ──────────────────────────────────────────────

@ventas_bp.route('/nueva/paso-1', methods=['GET', 'POST'])
@login_required
@verificar_rol('ADMIN', 'VENDEDOR')
def paso1_libros():
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    libros = Libro.query.filter(Libro.activo == True, Libro.stock > 0).order_by(Libro.nombre.asc()).all()

    # Cantidades previas si el usuario vuelve desde paso 2
    cantidades_previas = {}
    for item in session.get(SESSION_LIBROS, []):
        cantidades_previas[item['libro_id']] = item['cantidad']

    if request.method == 'POST':
        seleccionados = []
        for libro in libros:
            try:
                cantidad = int(request.form.get(f'cantidad_{libro.id}', 0))
            except ValueError:
                cantidad = 0
            if cantidad > 0:
                if cantidad > libro.stock:
                    flash(f'Stock insuficiente para "{libro.nombre}". Disponible: {libro.stock}.', 'danger')
                    return render_template('ventas/paso1_libros.html',
                                           libros=libros, cantidades_previas=cantidades_previas)
                seleccionados.append({
                    'libro_id':  libro.id,
                    'nombre':    libro.nombre,
                    'autor':     libro.autor,
                    'isbn':      libro.isbn,
                    'precio':    float(libro.precio),
                    'stock':     libro.stock,
                    'cantidad':  cantidad,
                    'subtotal':  float(libro.precio) * cantidad,
                })

        if not seleccionados:
            flash('Debes seleccionar al menos un libro.', 'warning')
            return render_template('ventas/paso1_libros.html',
                                   libros=libros, cantidades_previas=cantidades_previas)

        session[SESSION_LIBROS] = seleccionados
        return redirect(url_for('ventas.paso2_cliente'))

    return render_template('ventas/paso1_libros.html',
                           libros=libros, cantidades_previas=cantidades_previas)


# ── Paso 2: Información del cliente ─────────────────────────────────────────

@ventas_bp.route('/nueva/paso-2', methods=['GET', 'POST'])
@login_required
@verificar_rol('ADMIN', 'VENDEDOR')
def paso2_cliente():
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    if not session.get(SESSION_LIBROS):
        flash('Primero selecciona los libros a vender.', 'warning')
        return redirect(url_for('ventas.paso1_libros'))

    cliente_previo = session.get(SESSION_CLIENTE, {})

    if request.method == 'POST':
        cedula_ruc  = request.form.get('cedula_ruc', '').strip()
        nombres     = request.form.get('nombres', '').strip()
        apellidos   = request.form.get('apellidos', '').strip()
        direccion   = request.form.get('direccion', '').strip()
        telefono    = request.form.get('telefono', '').strip()
        correo      = request.form.get('correo', '').strip()

        if not all([cedula_ruc, nombres, apellidos]):
            flash('Cédula/RUC, nombres y apellidos son obligatorios.', 'warning')
            return render_template('ventas/paso2_cliente.html', cliente=cliente_previo)

        if not cedula_ruc.isdigit() or len(cedula_ruc) not in (10, 13):
            flash('La cédula debe tener exactamente 10 dígitos o el RUC 13 dígitos.', 'danger')
            return render_template('ventas/paso2_cliente.html', cliente=cliente_previo)

        cliente_existente = Cliente.query.filter_by(cedula_ruc=cedula_ruc).first()

        session[SESSION_CLIENTE] = {
            'cedula_ruc': cedula_ruc,
            'nombres':    nombres,
            'apellidos':  apellidos,
            'direccion':  direccion,
            'telefono':   telefono,
            'correo':     correo,
            'es_nuevo':   cliente_existente is None,
            'cliente_id': cliente_existente.id if cliente_existente else None,
        }
        return redirect(url_for('ventas.paso3_confirmar'))

    return render_template('ventas/paso2_cliente.html', cliente=cliente_previo)


# ── Paso 3: Confirmación ─────────────────────────────────────────────────────

@ventas_bp.route('/nueva/paso-3')
@login_required
@verificar_rol('ADMIN', 'VENDEDOR')
def paso3_confirmar():
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    libros_sesion  = session.get(SESSION_LIBROS)
    cliente_sesion = session.get(SESSION_CLIENTE)

    if not libros_sesion:
        return redirect(url_for('ventas.paso1_libros'))
    if not cliente_sesion:
        return redirect(url_for('ventas.paso2_cliente'))

    subtotal = sum(item['subtotal'] for item in libros_sesion)

    return render_template('ventas/paso3_confirmar.html',
                           libros=libros_sesion,
                           cliente=cliente_sesion,
                           subtotal=subtotal,
                           iva=0,
                           total=subtotal)


# ── Confirmar venta ──────────────────────────────────────────────────────────

@ventas_bp.route('/nueva/confirmar', methods=['POST'])
@login_required
@verificar_rol('ADMIN', 'VENDEDOR')
def confirmar_venta():
    libros_sesion  = session.get(SESSION_LIBROS)
    cliente_sesion = session.get(SESSION_CLIENTE)

    if not libros_sesion or not cliente_sesion:
        flash('Sesión de venta expirada. Inicia de nuevo.', 'warning')
        return redirect(url_for('ventas.paso1_libros'))

    try:
        # Crear o reusar cliente
        if cliente_sesion['es_nuevo']:
            cliente = Cliente(
                cedula_ruc=cliente_sesion['cedula_ruc'],
                nombres=cliente_sesion['nombres'],
                apellidos=cliente_sesion['apellidos'],
                direccion=cliente_sesion.get('direccion') or None,
                telefono=cliente_sesion.get('telefono') or None,
                correo=cliente_sesion.get('correo') or None,
            )
            db.session.add(cliente)
            db.session.flush()
        else:
            cliente = Cliente.query.get(cliente_sesion['cliente_id'])

        # Crear venta
        venta = Venta(
            cliente_id=cliente.id,
            usuario_id=current_user.id,
            subtotal=0,
            iva=0,
            total=0,
        )
        db.session.add(venta)
        db.session.flush()

        # Procesar cada libro
        for item in libros_sesion:
            libro = Libro.query.get(item['libro_id'])
            if not libro or not libro.activo:
                raise ValueError(f'El libro "{item["nombre"]}" ya no está disponible.')
            if libro.stock < item['cantidad']:
                raise ValueError(
                    f'Stock insuficiente para "{libro.nombre}". '
                    f'Disponible: {libro.stock}, solicitado: {item["cantidad"]}.'
                )

            # Detalle de venta
            detalle = DetalleVenta(
                venta_id=venta.id,
                libro_id=libro.id,
                cantidad=item['cantidad'],
                precio_unitario=Decimal(str(item['precio'])),
                subtotal=Decimal(str(item['subtotal'])),
            )
            db.session.add(detalle)

            # Reducir stock (auto-desactiva si llega a 0)
            libro.reducir_stock(item['cantidad'])

            # Movimiento de inventario
            movimiento = MovimientoInventario(
                libro_id=libro.id,
                usuario_id=current_user.id,
                tipo_movimiento='VENTA',
                cantidad=item['cantidad'],
                motivo=f'Venta #{venta.id}',
            )
            db.session.add(movimiento)

        # Calcular totales
        venta.calcular_total()
        db.session.commit()

        # Limpiar sesión de venta
        session.pop(SESSION_LIBROS, None)
        session.pop(SESSION_CLIENTE, None)

        flash(f'Venta #{venta.id} registrada correctamente. Total: $ {venta.total:.2f}', 'success')
        return redirect(url_for('auth.dashboard'))

    except ValueError as e:
        db.session.rollback()
        flash(str(e), 'danger')
        return redirect(url_for('ventas.paso3_confirmar'))
    except Exception:
        db.session.rollback()
        flash('Error al procesar la venta. Intenta de nuevo.', 'danger')
        return redirect(url_for('ventas.paso3_confirmar'))


# ── Buscar cliente por cédula (AJAX) ─────────────────────────────────────────

@ventas_bp.route('/buscar-cliente')
@login_required
def buscar_cliente():
    cedula = request.args.get('cedula', '').strip()
    if not cedula:
        return jsonify({'encontrado': False})

    cliente = Cliente.query.filter_by(cedula_ruc=cedula).first()
    if not cliente:
        return jsonify({'encontrado': False})

    return jsonify({
        'encontrado': True,
        'cliente_id': cliente.id,
        'nombres':    cliente.nombres,
        'apellidos':  cliente.apellidos,
        'direccion':  cliente.direccion or '',
        'telefono':   cliente.telefono or '',
        'correo':     cliente.correo or '',
    })


# ── Cancelar flujo de nueva venta ────────────────────────────────────────────

@ventas_bp.route('/cancelar', methods=['POST'])
@login_required
def cancelar_venta():
    session.pop(SESSION_LIBROS, None)
    session.pop(SESSION_CLIENTE, None)
    flash('Venta cancelada.', 'info')
    return redirect(url_for('auth.dashboard'))


# ── Ventas del día ───────────────────────────────────────────────────────────

@ventas_bp.route('/hoy')
@login_required
@verificar_rol('ADMIN', 'VENDEDOR')
def ventas_hoy():
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    from datetime import date
    from sqlalchemy import func as sqlfunc
    hoy = date.today()
    ventas = Venta.query.filter(
        sqlfunc.date(Venta.fecha_venta) == hoy
    ).order_by(Venta.fecha_venta.desc()).all()
    total = sum(float(v.total) for v in ventas if v.esta_activa())
    return render_template('ventas/hoy.html', ventas=ventas, total=total, fecha=hoy)


# ── Consultar ventas ──────────────────────────────────────────────────────────

@ventas_bp.route('/consultar')
@login_required
@verificar_rol('ADMIN', 'VENDEDOR')
def consultar_ventas():
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    cedula_busqueda = request.args.get('cedula', '').strip()
    fecha_desde     = request.args.get('fecha_desde', '').strip()
    fecha_hasta     = request.args.get('fecha_hasta', '').strip()

    query = Venta.query.join(Cliente)

    if cedula_busqueda:
        query = query.filter(Cliente.cedula_ruc.ilike(f'%{cedula_busqueda}%'))
    if fecha_desde:
        query = query.filter(Venta.fecha_venta >= fecha_desde)
    if fecha_hasta:
        query = query.filter(Venta.fecha_venta <= fecha_hasta + ' 23:59:59')

    ventas = query.order_by(Venta.fecha_venta.desc()).all()

    return render_template('ventas/consultar.html',
                           ventas=ventas,
                           cedula_busqueda=cedula_busqueda,
                           fecha_desde=fecha_desde,
                           fecha_hasta=fecha_hasta)


# ── Detalle de venta ──────────────────────────────────────────────────────────

@ventas_bp.route('/<int:id>/detalle')
@login_required
@verificar_rol('ADMIN', 'VENDEDOR')
def detalle_venta(id):
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    venta = Venta.query.get_or_404(id)
    return render_template('ventas/detalle.html', venta=venta)


# ── Anular venta ──────────────────────────────────────────────────────────────

@ventas_bp.route('/<int:id>/anular', methods=['POST'])
@login_required
@verificar_rol('ADMIN', 'VENDEDOR')
def anular_venta(id):
    venta = Venta.query.get_or_404(id)

    if not venta.esta_activa():
        flash('Esta venta ya está anulada.', 'warning')
        return redirect(url_for('ventas.consultar_ventas'))

    try:
        venta.anular()

        for detalle in venta.detalles:
            libro = Libro.query.get(detalle.libro_id)
            if libro:
                libro.aumentar_stock(detalle.cantidad)
                movimiento = MovimientoInventario(
                    libro_id=libro.id,
                    usuario_id=current_user.id,
                    tipo_movimiento='ANULACION',
                    cantidad=detalle.cantidad,
                    motivo=f'Anulación de venta #{venta.id}',
                )
                db.session.add(movimiento)

        db.session.commit()
        flash(f'Venta #{venta.id} anulada correctamente. Stock restaurado.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error al anular la venta. Intenta de nuevo.', 'danger')

    return redirect(url_for('ventas.consultar_ventas'))
