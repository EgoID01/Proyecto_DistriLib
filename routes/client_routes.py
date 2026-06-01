from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from models import db
from models.client import Cliente
from utils.decorators import verificar_rol
from utils.helpers import redirigir_segun_estado

clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes')


@clientes_bp.route('/')
@login_required
@verificar_rol('ADMIN', 'VENDEDOR')
def listar_clientes():
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    busqueda = request.args.get('q', '').strip()

    if busqueda:
        clientes = Cliente.query.filter(
            db.or_(
                Cliente.cedula_ruc.ilike(f'%{busqueda}%'),
                Cliente.nombres.ilike(f'%{busqueda}%'),
                Cliente.apellidos.ilike(f'%{busqueda}%'),
            )
        ).order_by(Cliente.nombres.asc()).all()
    else:
        clientes = Cliente.query.order_by(Cliente.nombres.asc()).all()

    return render_template('clientes/lista.html', clientes=clientes, busqueda=busqueda)


@clientes_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@verificar_rol('ADMIN', 'VENDEDOR')
def editar_cliente(id):
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    cliente = Cliente.query.get_or_404(id)

    if request.method == 'POST':
        nombres   = request.form.get('nombres', '').strip()
        apellidos = request.form.get('apellidos', '').strip()
        direccion = request.form.get('direccion', '').strip()
        telefono  = request.form.get('telefono', '').strip()
        correo    = request.form.get('correo', '').strip()

        if not nombres or not apellidos:
            flash('Nombres y apellidos son obligatorios.', 'warning')
            return render_template('clientes/editar.html', cliente=cliente)

        try:
            cliente.nombres   = nombres
            cliente.apellidos = apellidos
            cliente.direccion = direccion or None
            cliente.telefono  = telefono or None
            cliente.correo    = correo or None
            db.session.commit()
            flash(f'Cliente "{cliente.nombre_completo()}" actualizado correctamente.', 'success')
            return redirect(url_for('clientes.listar_clientes'))
        except Exception:
            db.session.rollback()
            flash('Error al actualizar el cliente. Intenta de nuevo.', 'danger')
            return render_template('clientes/editar.html', cliente=cliente)

    return render_template('clientes/editar.html', cliente=cliente)
