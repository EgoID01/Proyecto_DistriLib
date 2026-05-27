from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def verificar_rol(*roles_permitidos):
    """
    Decorador que verifica si el usuario actual tiene uno de los roles permitidos.
    
    Uso:
        @verificar_rol('ADMIN')
        @verificar_rol('ADMIN', 'BODEGUERO')
    
    Si el usuario no tiene permisos, redirige al dashboard y muestra un mensaje de error.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Debes iniciar sesión para acceder a esta página.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Verificar si el rol del usuario está en los roles permitidos
            usuario_rol = current_user.rol.nombre if current_user.rol else None
            if usuario_rol not in roles_permitidos:
                flash(f'No tienes permiso para acceder a esta página. Se requiere: {", ".join(roles_permitidos)}', 'danger')
                return redirect(url_for('auth.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def solo_admin(f):
    """Decorador rápido para rutas solo de ADMIN."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.es_admin():
            flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def solo_bodeguero(f):
    """Decorador rápido para rutas solo de BODEGUERO."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.es_bodeguero():
            flash('Acceso denegado. Se requieren permisos de bodeguero.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def solo_vendedor(f):
    """Decorador rápido para rutas solo de VENDEDOR."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.es_vendedor():
            flash('Acceso denegado. Se requieren permisos de vendedor.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated_function
