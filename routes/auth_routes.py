from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db
from models.user import Usuario
from utils.helpers import redirigir_segun_estado

# Definición del Blueprint de autenticación
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Maneja el inicio de sesión.
    - GET: muestra el formulario de login.
    - POST: valida credenciales y redirige según el estado del usuario.
    """
    # Si ya tiene sesión activa, aplicar la máquina de estados
    if current_user.is_authenticated:
        return redirigir_segun_estado() or redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Validación básica de campos vacíos
        if not username or not password:
            flash('Por favor ingresa tu usuario y contraseña.', 'warning')
            return render_template('login.html')

        # Buscar el usuario en la base de datos
        usuario = Usuario.query.filter_by(username=username).first()

        # Verificar existencia, contraseña y estado activo
        if not usuario or not usuario.verificar_password(password):
            flash('Usuario o contraseña incorrectos.', 'danger')
            return render_template('login.html')

        if not usuario.activo:
            flash('Tu cuenta está desactivada. Contacta al administrador.', 'danger')
            return render_template('login.html')

        # Iniciar sesión con Flask-Login
        login_user(usuario)

        # Aplicar la máquina de estados post-login
        if usuario.primer_login:
            flash('Bienvenido. Debes completar tu perfil de seguridad.', 'info')
            return redirect(url_for('auth.cambiar_password_temporal'))

        flash(f'Bienvenido, {usuario.nombres.split()[0]}.', 'success')
        return redirect(url_for('auth.dashboard'))

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Cierra la sesión del usuario actual."""
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/cambiar-password', methods=['GET', 'POST'])
@login_required
def cambiar_password_temporal():
    """
    Fuerza al usuario a cambiar su contraseña temporal en el primer acceso.
    Solo accesible mientras password_temporal sea True.
    """
    # Setup ya completado
    if not current_user.primer_login:
        return redirect(url_for('auth.dashboard'))

    # Contraseña ya cambiada, pasar al siguiente paso
    if not current_user.password_temporal:
        return redirect(url_for('auth.registrar_preguntas'))

    if request.method == 'POST':
        nueva_password = request.form.get('nueva_password', '')
        confirmar_password = request.form.get('confirmar_password', '')

        if len(nueva_password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'warning')
            return render_template('cambiar_password.html')

        if nueva_password != confirmar_password:
            flash('Las contraseñas no coinciden.', 'warning')
            return render_template('cambiar_password.html')

        # Guardar la nueva contraseña cifrada
        current_user.set_password(nueva_password)
        current_user.password_temporal = False
        db.session.commit()

        # Re-autenticar para actualizar la cookie con el nuevo session_token
        # (set_password regenera el token, lo que invalidaría la sesión activa)
        login_user(current_user)

        flash('Contraseña actualizada. Ahora registra tus preguntas de seguridad.', 'success')
        return redirect(url_for('auth.registrar_preguntas'))

    return render_template('cambiar_password.html')


@auth_bp.route('/preguntas-seguridad', methods=['GET', 'POST'])
@login_required
def registrar_preguntas():
    """
    Permite al usuario registrar sus 3 preguntas de seguridad en el primer acceso.
    Solo accesible si primer_login es True y password_temporal es False.
    """
    from models.user import PreguntaSeguridad, RespuestaSeguridad

    # Setup ya completado
    if not current_user.primer_login:
        return redirect(url_for('auth.dashboard'))

    # Contraseña aún sin cambiar, volver al paso anterior
    if current_user.password_temporal:
        return redirect(url_for('auth.cambiar_password_temporal'))

    preguntas = PreguntaSeguridad.query.all()

    if request.method == 'POST':
        preguntas_seleccionadas = [
            request.form.get('pregunta_1'),
            request.form.get('pregunta_2'),
            request.form.get('pregunta_3'),
        ]
        respuestas_ingresadas = [
            request.form.get('respuesta_1', '').strip(),
            request.form.get('respuesta_2', '').strip(),
            request.form.get('respuesta_3', '').strip(),
        ]

        # Validar que se seleccionaron 3 preguntas distintas
        if len(set(preguntas_seleccionadas)) < 3:
            flash('Debes seleccionar 3 preguntas diferentes.', 'warning')
            return render_template('preguntas_seguridad.html', preguntas=preguntas)

        # Validar que todas las respuestas tengan contenido
        if any(r == '' for r in respuestas_ingresadas):
            flash('Debes responder las 3 preguntas de seguridad.', 'warning')
            return render_template('preguntas_seguridad.html', preguntas=preguntas)

        # Guardar las 3 respuestas cifradas
        for pregunta_id, respuesta in zip(preguntas_seleccionadas, respuestas_ingresadas):
            nueva_respuesta = RespuestaSeguridad(
                usuario_id=current_user.id,
                pregunta_id=int(pregunta_id),
            )
            nueva_respuesta.set_respuesta(respuesta)
            db.session.add(nueva_respuesta)

        # Marcar que ya completó el primer login
        current_user.primer_login = False
        db.session.commit()

        flash('Perfil de seguridad completado. ¡Bienvenido al sistema!', 'success')
        return redirect(url_for('auth.dashboard'))

    return render_template('preguntas_seguridad.html', preguntas=preguntas)


@auth_bp.route('/recuperar-password', methods=['GET', 'POST'])
def recuperar_password():
    """
    Paso 1 del flujo de recuperación: verifica identidad con las preguntas de seguridad.
    Si las 3 respuestas son correctas, habilita el acceso a /nueva-password via sesión.
    """
    from models.user import PreguntaSeguridad, RespuestaSeguridad

    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'GET':
        username = request.args.get('username', '').strip()
        if not username:
            flash('Ingresa tu nombre de usuario antes de recuperar la contraseña.', 'warning')
            return redirect(url_for('auth.login'))

        usuario = Usuario.query.filter_by(username=username).first()
        if not usuario or not usuario.activo:
            flash('Usuario no encontrado o inactivo.', 'danger')
            return redirect(url_for('auth.login'))

        respuestas = RespuestaSeguridad.query.filter_by(usuario_id=usuario.id).all()
        if not respuestas:
            flash('Este usuario aún no ha configurado sus preguntas de seguridad.', 'danger')
            return redirect(url_for('auth.login'))

        preguntas = [
            {'id': r.pregunta_id, 'texto': r.pregunta.pregunta}
            for r in respuestas
        ]
        return render_template('recuperar_password.html',
                               username=username, preguntas=preguntas)

    # POST: validar respuestas
    username = request.form.get('username', '').strip()
    usuario = Usuario.query.filter_by(username=username).first()
    if not usuario or not usuario.activo:
        flash('Sesión inválida. Intenta de nuevo.', 'danger')
        return redirect(url_for('auth.login'))

    respuestas_db = RespuestaSeguridad.query.filter_by(usuario_id=usuario.id).all()
    respuestas_map = {r.pregunta_id: r for r in respuestas_db}
    preguntas = [
        {'id': r.pregunta_id, 'texto': r.pregunta.pregunta}
        for r in respuestas_db
    ]

    todas_correctas = True
    for i, r in enumerate(respuestas_db, start=1):
        respuesta_ingresada = request.form.get(f'respuesta_{i}', '').strip()
        if not respuestas_map[r.pregunta_id].verificar_respuesta(respuesta_ingresada):
            todas_correctas = False
            break

    if not todas_correctas:
        flash('Una o más respuestas son incorrectas. Intenta de nuevo.', 'danger')
        return render_template('recuperar_password.html',
                               username=username, preguntas=preguntas)

    from flask import session
    session['reset_uid'] = usuario.id
    return redirect(url_for('auth.nueva_password'))


@auth_bp.route('/nueva-password', methods=['GET', 'POST'])
def nueva_password():
    """
    Paso 2 del flujo de recuperación: permite al usuario establecer una nueva contraseña.
    Solo accesible si /recuperar-password validó correctamente las preguntas de seguridad.
    """
    from flask import session

    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    uid = session.get('reset_uid')
    if not uid:
        flash('Sesión de recuperación inválida. Responde las preguntas de seguridad primero.', 'danger')
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(uid)
    if not usuario:
        session.pop('reset_uid', None)
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nueva = request.form.get('nueva_password', '')
        confirmar = request.form.get('confirmar_password', '')

        if len(nueva) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'warning')
            return render_template('nueva_password.html')

        if nueva != confirmar:
            flash('Las contraseñas no coinciden.', 'warning')
            return render_template('nueva_password.html')

        usuario.set_password(nueva)
        usuario.password_temporal = False
        db.session.commit()

        session.pop('reset_uid', None)
        flash('Contraseña actualizada correctamente. Inicia sesión con tu nueva contraseña.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('nueva_password.html')


@auth_bp.route('/notificaciones-json')
@login_required
def notificaciones_json():
    from flask import jsonify
    from models.book import Libro, MovimientoInventario
    from models.user import ConfiguracionSistema

    config = ConfiguracionSistema.obtener()
    corte = config.notif_limpiadas_en

    mov_query = MovimientoInventario.query
    if corte:
        mov_query = mov_query.filter(MovimientoInventario.fecha > corte)
    movimientos = mov_query.order_by(MovimientoInventario.fecha.desc()).limit(50).all()

    if corte:
        libros_con_mov = (
            db.session.query(MovimientoInventario.libro_id)
            .filter(MovimientoInventario.fecha > corte)
            .subquery()
        )
        libros_roja = Libro.query.filter(Libro.stock >= 1, Libro.stock <= 2, Libro.id.in_(libros_con_mov)).order_by(Libro.stock.asc()).all()
        libros_amarilla = Libro.query.filter(Libro.stock >= 3, Libro.stock <= 5, Libro.id.in_(libros_con_mov)).order_by(Libro.stock.asc()).all()
    else:
        libros_roja = Libro.query.filter(Libro.stock >= 1, Libro.stock <= 2).order_by(Libro.stock.asc()).all()
        libros_amarilla = Libro.query.filter(Libro.stock >= 3, Libro.stock <= 5).order_by(Libro.stock.asc()).all()

    return jsonify({
        'total_alertas': len(libros_roja) + len(libros_amarilla),
        'libros_roja':    [{'nombre': l.nombre, 'stock': l.stock} for l in libros_roja],
        'libros_amarilla': [{'nombre': l.nombre, 'stock': l.stock} for l in libros_amarilla],
        'movimientos': [
            {
                'tipo':     m.tipo_movimiento,
                'libro':    m.libro.nombre,
                'cantidad': m.cantidad,
                'fecha':    m.fecha.strftime('%d/%m %H:%M'),
                'motivo':   m.motivo or '',
            }
            for m in movimientos
        ],
    })


@auth_bp.route('/limpiar-notificaciones', methods=['POST'])
@login_required
def limpiar_notificaciones():
    from utils.decorators import solo_admin
    from models.user import ConfiguracionSistema
    from datetime import datetime
    if not current_user.es_admin():
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('auth.dashboard'))
    config = ConfiguracionSistema.obtener()
    config.notif_limpiadas_en = datetime.now()
    db.session.commit()
    flash('Notificaciones borradas correctamente.', 'success')
    return redirect(url_for('auth.dashboard'))


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Dashboard principal. Redirige al paso de seguridad pendiente
    si el usuario aún no completó el perfil en el primer acceso.
    """
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    from datetime import date
    from sqlalchemy import func as sqlfunc
    from models.book import Libro, MovimientoInventario
    from models.sale import Venta
    from models.user import ConfiguracionSistema

    hoy = date.today()
    total_hoy = db.session.query(sqlfunc.sum(Venta.total)).filter(
        sqlfunc.date(Venta.fecha_venta) == hoy,
        Venta.estado == 'ACTIVA'
    ).scalar() or 0

    config = ConfiguracionSistema.obtener()
    corte = config.notif_limpiadas_en

    mov_query = MovimientoInventario.query
    if corte:
        mov_query = mov_query.filter(MovimientoInventario.fecha > corte)
    movimientos_recientes = mov_query.order_by(MovimientoInventario.fecha.desc()).limit(50).all()

    # Alertas de stock: solo libros con actividad posterior al último borrado
    if corte:
        libros_con_mov_reciente = (
            db.session.query(MovimientoInventario.libro_id)
            .filter(MovimientoInventario.fecha > corte)
            .subquery()
        )
        libros_roja = Libro.query.filter(
            Libro.stock <= 2,
            Libro.id.in_(libros_con_mov_reciente)
        ).order_by(Libro.stock.asc()).all()
        libros_amarilla = Libro.query.filter(
            Libro.stock > 2, Libro.stock <= 5,
            Libro.id.in_(libros_con_mov_reciente)
        ).order_by(Libro.stock.asc()).all()
    else:
        libros_roja = Libro.query.filter(Libro.stock <= 2).order_by(Libro.stock.asc()).all()
        libros_amarilla = Libro.query.filter(Libro.stock > 2, Libro.stock <= 5).order_by(Libro.stock.asc()).all()

    total_alertas = len(libros_roja) + len(libros_amarilla)

    return render_template(
        'dashboard.html',
        libros_roja=libros_roja,
        libros_amarilla=libros_amarilla,
        movimientos_recientes=movimientos_recientes,
        total_alertas=total_alertas,
        total_hoy=total_hoy,
    )