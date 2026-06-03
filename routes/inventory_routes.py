from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db
from models.book import Libro, MovimientoInventario
from utils.decorators import verificar_rol, solo_admin
from utils.helpers import redirigir_segun_estado

inventario_bp = Blueprint('inventario', __name__, url_prefix='/inventario')


@inventario_bp.route('/')
@login_required
def listar_libros():
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente
    q = request.args.get('q', '').strip()
    query = Libro.query
    if q:
        like = f'%{q}%'
        query = query.filter(
            db.or_(
                Libro.nombre.ilike(like),
                Libro.autor.ilike(like),
                Libro.editorial.ilike(like),
                Libro.isbn.ilike(like),
            )
        )
    libros = query.order_by(Libro.nombre.asc()).all()
    return render_template('inventario/lista.html', libros=libros, q=q)


@inventario_bp.route('/crear', methods=['GET', 'POST'])
@login_required
@verificar_rol('ADMIN', 'BODEGUERO')
def crear_libro():
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        autor = request.form.get('autor', '').strip()
        editorial = request.form.get('editorial', '').strip()
        anio = request.form.get('anio_publicacion', '').strip()
        isbn = request.form.get('isbn', '').strip()
        precio = request.form.get('precio', '').strip()
        stock_inicial = request.form.get('stock', '0').strip()

        if not all([nombre, autor, editorial, anio, isbn, precio]):
            flash('Todos los campos son obligatorios excepto el stock inicial.', 'warning')
            return render_template('inventario/crear.html')

        try:
            anio = int(anio)
            precio = float(precio)
            stock_inicial = int(stock_inicial)
        except ValueError:
            flash('Año, precio y stock deben ser valores numéricos válidos.', 'warning')
            return render_template('inventario/crear.html')

        if precio <= 0:
            flash('El precio debe ser mayor a cero.', 'warning')
            return render_template('inventario/crear.html')

        if stock_inicial < 0:
            flash('El stock inicial no puede ser negativo.', 'warning')
            return render_template('inventario/crear.html')

        if Libro.query.filter_by(isbn=isbn).first():
            flash(f'Ya existe un libro con el ISBN "{isbn}".', 'danger')
            return render_template('inventario/crear.html')

        try:
            nuevo = Libro(
                nombre=nombre,
                autor=autor,
                editorial=editorial,
                anio_publicacion=anio,
                isbn=isbn,
                precio=precio,
                stock=stock_inicial,
                activo=(stock_inicial > 0),
            )
            db.session.add(nuevo)
            db.session.flush()

            if stock_inicial > 0:
                movimiento = MovimientoInventario(
                    libro_id=nuevo.id,
                    usuario_id=current_user.id,
                    tipo_movimiento='ENTRADA',
                    cantidad=stock_inicial,
                    motivo='Stock inicial al registrar el libro',
                )
                db.session.add(movimiento)

            db.session.commit()
            flash(f'Libro "{nombre}" registrado correctamente.', 'success')
            return redirect(url_for('inventario.listar_libros'))
        except Exception:
            db.session.rollback()
            flash('Error al registrar el libro. Intenta de nuevo.', 'danger')
            return render_template('inventario/crear.html')

    return render_template('inventario/crear.html')


@inventario_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@verificar_rol('ADMIN', 'BODEGUERO')
def editar_libro(id):
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    libro = Libro.query.get_or_404(id)

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        autor = request.form.get('autor', '').strip()
        editorial = request.form.get('editorial', '').strip()
        anio = request.form.get('anio_publicacion', '').strip()
        isbn = request.form.get('isbn', '').strip()
        precio = request.form.get('precio', '').strip()

        if not all([nombre, autor, editorial, anio, isbn, precio]):
            flash('Todos los campos son obligatorios.', 'warning')
            return render_template('inventario/editar.html', libro=libro)

        try:
            anio = int(anio)
            precio = float(precio)
        except ValueError:
            flash('Año y precio deben ser valores numéricos válidos.', 'warning')
            return render_template('inventario/editar.html', libro=libro)

        if precio <= 0:
            flash('El precio debe ser mayor a cero.', 'warning')
            return render_template('inventario/editar.html', libro=libro)

        duplicado = Libro.query.filter(Libro.isbn == isbn, Libro.id != id).first()
        if duplicado:
            flash(f'El ISBN "{isbn}" ya está en uso por otro libro.', 'danger')
            return render_template('inventario/editar.html', libro=libro)

        try:
            libro.nombre = nombre
            libro.autor = autor
            libro.editorial = editorial
            libro.anio_publicacion = anio
            libro.isbn = isbn
            libro.precio = precio
            db.session.commit()
            flash(f'Libro "{nombre}" actualizado correctamente.', 'success')
            return redirect(url_for('inventario.listar_libros'))
        except Exception:
            db.session.rollback()
            flash('Error al actualizar el libro. Intenta de nuevo.', 'danger')
            return render_template('inventario/editar.html', libro=libro)

    return render_template('inventario/editar.html', libro=libro)


@inventario_bp.route('/<int:id>/ajustar-stock', methods=['GET', 'POST'])
@login_required
@verificar_rol('ADMIN', 'BODEGUERO')
def ajustar_stock(id):
    pendiente = redirigir_segun_estado()
    if pendiente:
        return pendiente

    libro = Libro.query.get_or_404(id)

    if request.method == 'POST':
        tipo = request.form.get('tipo_movimiento', '').strip()
        cantidad_str = request.form.get('cantidad', '').strip()
        motivo = request.form.get('motivo', '').strip()

        if tipo not in ('ENTRADA', 'AJUSTE'):
            flash('Tipo de movimiento no válido.', 'warning')
            return render_template('inventario/ajustar_stock.html', libro=libro)

        try:
            cantidad = int(cantidad_str)
        except ValueError:
            flash('La cantidad debe ser un número entero.', 'warning')
            return render_template('inventario/ajustar_stock.html', libro=libro)

        if tipo == 'ENTRADA' and cantidad <= 0:
            flash('La cantidad de entrada debe ser mayor a cero.', 'warning')
            return render_template('inventario/ajustar_stock.html', libro=libro)

        if tipo == 'AJUSTE' and not motivo:
            flash('El motivo es obligatorio para ajustes manuales.', 'warning')
            return render_template('inventario/ajustar_stock.html', libro=libro)

        try:
            if tipo == 'ENTRADA':
                libro.aumentar_stock(cantidad)
            else:
                if cantidad >= 0:
                    libro.aumentar_stock(cantidad)
                else:
                    libro.reducir_stock(abs(cantidad))

            movimiento = MovimientoInventario(
                libro_id=libro.id,
                usuario_id=current_user.id,
                tipo_movimiento=tipo,
                cantidad=cantidad,
                motivo=motivo or None,
            )
            db.session.add(movimiento)
            db.session.commit()
            flash(f'Stock de "{libro.nombre}" ajustado correctamente. Stock actual: {libro.stock}.', 'success')
            return redirect(url_for('inventario.listar_libros'))
        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'danger')
            return render_template('inventario/ajustar_stock.html', libro=libro)
        except Exception:
            db.session.rollback()
            flash('Error al ajustar el stock. Intenta de nuevo.', 'danger')
            return render_template('inventario/ajustar_stock.html', libro=libro)

    return render_template('inventario/ajustar_stock.html', libro=libro)


@inventario_bp.route('/<int:id>/toggle-activo', methods=['POST'])
@login_required
@solo_admin
def toggle_activo(id):
    libro = Libro.query.get_or_404(id)
    libro.activo = not libro.activo
    db.session.commit()
    estado = 'activado' if libro.activo else 'desactivado'
    flash(f'Libro "{libro.nombre}" {estado} manualmente.', 'success')
    return redirect(url_for('inventario.listar_libros'))


@inventario_bp.route('/<int:id>/eliminar', methods=['POST'])
@login_required
@solo_admin
def eliminar_libro(id):
    libro = Libro.query.get_or_404(id)

    if libro.detalles_venta:
        flash(
            f'No se puede eliminar "{libro.nombre}": tiene movimientos registrados. '
            f'Desactívalo en su lugar para retirarlo del sistema.',
            'danger'
        )
        return redirect(url_for('inventario.listar_libros'))

    nombre = libro.nombre
    try:
        # Eliminar movimientos huérfanos antes de borrar el libro
        for mov in libro.movimientos:
            db.session.delete(mov)
        db.session.delete(libro)
        db.session.commit()
        flash(f'Libro "{nombre}" eliminado permanentemente.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error al eliminar el libro. Intenta de nuevo.', 'danger')

    return redirect(url_for('inventario.listar_libros'))
