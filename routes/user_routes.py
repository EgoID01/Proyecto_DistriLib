from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db
from models.user import Usuario, Rol
from utils.decorators import solo_admin
from utils.helpers import redirigir_segun_estado

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')


@usuarios_bp.route('/')
@login_required
@solo_admin
def listar_usuarios():
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente
    usuarios = Usuario.query.order_by(Usuario.fecha_creacion.desc()).all()
    return render_template('usuarios/lista.html', usuarios=usuarios)


@usuarios_bp.route('/crear', methods=['GET', 'POST'])
@login_required
@solo_admin
def crear_usuario():
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    roles = Rol.query.all()

    if request.method == 'POST':
        nombres = request.form.get('nombres', '').strip()
        cedula = request.form.get('cedula', '').strip()
        username = request.form.get('username', '').strip()
        rol_id = request.form.get('rol_id', '').strip()
        password = request.form.get('password', '')
        confirmar = request.form.get('confirmar_password', '')

        if not all([nombres, cedula, username, rol_id, password]):
            flash('Todos los campos son obligatorios.', 'warning')
            return render_template('usuarios/crear.html', roles=roles)

        if not cedula.isdigit() or len(cedula) != 10:
            flash('La cédula debe tener exactamente 10 dígitos.', 'danger')
            return render_template('usuarios/crear.html', roles=roles)

        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'warning')
            return render_template('usuarios/crear.html', roles=roles)

        if password != confirmar:
            flash('Las contraseñas no coinciden.', 'warning')
            return render_template('usuarios/crear.html', roles=roles)

        if Usuario.query.filter_by(username=username).first():
            flash(f'El nombre de usuario "{username}" ya está en uso.', 'danger')
            return render_template('usuarios/crear.html', roles=roles)

        if Usuario.query.filter_by(cedula=cedula).first():
            flash('Ya existe un usuario registrado con esa cédula.', 'danger')
            return render_template('usuarios/crear.html', roles=roles)

        try:
            nuevo = Usuario(
                nombres=nombres,
                cedula=cedula,
                username=username,
                rol_id=int(rol_id),
                password_temporal=True,
                primer_login=True,
                activo=True,
            )
            nuevo.set_password(password)
            db.session.add(nuevo)
            db.session.commit()
            flash(f'Usuario "{username}" creado correctamente.', 'success')
            return redirect(url_for('usuarios.listar_usuarios'))
        except Exception:
            db.session.rollback()
            flash('Error al crear el usuario. Intenta de nuevo.', 'danger')
            return render_template('usuarios/crear.html', roles=roles)

    return render_template('usuarios/crear.html', roles=roles)


@usuarios_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@solo_admin
def editar_usuario(id):
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    usuario = Usuario.query.get_or_404(id)
    roles = Rol.query.all()

    if request.method == 'POST':
        nombres  = request.form.get('nombres', '').strip()
        cedula   = request.form.get('cedula', '').strip()
        username = request.form.get('username', '').strip()
        rol_id   = request.form.get('rol_id', '').strip()

        if not all([nombres, cedula, username, rol_id]):
            flash('Todos los campos son obligatorios.', 'warning')
            return render_template('usuarios/editar.html', usuario=usuario, roles=roles)

        if not cedula.isdigit() or len(cedula) != 10:
            flash('La cédula debe tener exactamente 10 dígitos.', 'danger')
            return render_template('usuarios/editar.html', usuario=usuario, roles=roles)

        dup_username = Usuario.query.filter(
            Usuario.username == username, Usuario.id != id
        ).first()
        if dup_username:
            flash(f'El nombre de usuario "{username}" ya está en uso.', 'danger')
            return render_template('usuarios/editar.html', usuario=usuario, roles=roles)

        dup_cedula = Usuario.query.filter(
            Usuario.cedula == cedula, Usuario.id != id
        ).first()
        if dup_cedula:
            flash('Ya existe otro usuario con esa cédula.', 'danger')
            return render_template('usuarios/editar.html', usuario=usuario, roles=roles)

        try:
            usuario.nombres  = nombres
            usuario.cedula   = cedula
            usuario.username = username
            usuario.rol_id   = int(rol_id)
            db.session.commit()
            flash(f'Usuario "{username}" actualizado correctamente.', 'success')
            return redirect(url_for('usuarios.listar_usuarios'))
        except Exception:
            db.session.rollback()
            flash('Error al actualizar el usuario. Intenta de nuevo.', 'danger')
            return render_template('usuarios/editar.html', usuario=usuario, roles=roles)

    return render_template('usuarios/editar.html', usuario=usuario, roles=roles)


@usuarios_bp.route('/<int:id>/toggle-activo', methods=['POST'])
@login_required
@solo_admin
def toggle_activo(id):
    usuario = Usuario.query.get_or_404(id)
    if usuario.username == 'admin':
        flash('No se puede desactivar al administrador principal.', 'danger')
    elif usuario.id == current_user.id:
        flash('No puedes desactivar tu propia cuenta.', 'danger')
    else:
        usuario.activo = not usuario.activo
        db.session.commit()
        estado = 'activado' if usuario.activo else 'desactivado'
        flash(f'Usuario "{usuario.nombres}" {estado} correctamente.', 'success')
    return redirect(url_for('usuarios.listar_usuarios'))