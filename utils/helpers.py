from flask import redirect, url_for
from flask_login import current_user


def redirigir_segun_estado():
    """
    Verifica si el usuario completó el perfil de seguridad obligatorio.
    Retorna un redirect al paso pendiente, o None si el acceso está habilitado.
    """
    if current_user.password_temporal:
        return redirect(url_for('auth.cambiar_password_temporal'))
    if current_user.primer_login:
        return redirect(url_for('auth.registrar_preguntas'))
    return None