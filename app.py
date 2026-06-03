import pymysql
from flask import Flask
from flask_login import LoginManager
from config import Config
from models import db

# Importar todos los modelos para que SQLAlchemy los registre antes de crear tablas
from models.user import Usuario, Rol, PreguntaSeguridad, RespuestaSeguridad, ConfiguracionSistema
from models.book import Libro, MovimientoInventario
from models.client import Cliente
from models.sale import Venta, DetalleVenta


def crear_base_de_datos():
    """Crea la base de datos si no existe, antes de que SQLAlchemy intente conectarse."""
    conexion = pymysql.connect(
        host=Config.DB_HOST,
        port=int(Config.DB_PORT),
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
    )
    try:
        with conexion.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conexion.commit()
        print(f"Base de datos '{Config.DB_NAME}' verificada correctamente.")
    finally:
        conexion.close()


def crear_app():
    """Factoría de la aplicación Flask."""

    crear_base_de_datos()

    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar extensiones con la app
    db.init_app(app)

    # Configurar Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Debes iniciar sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def cargar_usuario(usuario_id_token):
        """
        Carga el usuario validando id y session_token.
        El formato almacenado en la cookie es 'id|session_token'.
        Si el token no coincide (base de datos recreada, contraseña cambiada),
        la sesión se invalida y el usuario debe volver a loguearse.
        """
        try:
            partes = usuario_id_token.split('|')
            if len(partes) != 2:
                return None
            usuario_id, token = partes
            usuario = Usuario.query.get(int(usuario_id))
            if usuario and usuario.session_token == token:
                return usuario
            return None
        except Exception:
            return None

    # Registrar Blueprints (rutas organizadas por módulo)
    from routes.auth_routes import auth_bp
    from routes.user_routes import usuarios_bp
    from routes.inventory_routes import inventario_bp
    from routes.sales_routes import ventas_bp
    from routes.reports_routes import reportes_bp
    from routes.client_routes import clientes_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(inventario_bp)
    app.register_blueprint(ventas_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(clientes_bp)

    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
    # Aquí iremos registrando más blueprints en fases siguientes:
    # from routes.inventory_routes import inventory_bp
    # from routes.sales_routes import sales_bp

    # Crear tablas y datos iniciales dentro del contexto de la app
    with app.app_context():
        db.create_all()
        insertar_datos_iniciales()

    return app


def insertar_datos_iniciales():
    """
    Inserta los registros necesarios para que el sistema funcione desde el inicio:
    - Los 3 roles del sistema
    - Las 5 preguntas de seguridad
    - El usuario administrador principal
    """
    # Crear roles si no existen
    roles_iniciales = [
        {'nombre': 'ADMIN', 'descripcion': 'Acceso total al sistema'},
        {'nombre': 'BODEGUERO', 'descripcion': 'Gestión de inventario y stock'},
        {'nombre': 'VENDEDOR', 'descripcion': 'Realización y consulta de ventas'},
    ]
    for datos_rol in roles_iniciales:
        if not Rol.query.filter_by(nombre=datos_rol['nombre']).first():
            nuevo_rol = Rol(**datos_rol)
            db.session.add(nuevo_rol)

    db.session.flush()  # Asegura que los roles tengan ID antes de usarlos

    # Crear preguntas de seguridad si no existen
    preguntas_iniciales = [
        '¿Cuál es el nombre de tu primera mascota?',
        '¿En qué ciudad naciste?',
        '¿Cuál es el nombre de tu escuela primaria?',
        '¿Cuál es tu comida favorita?',
        '¿Cuál es el segundo apellido de tu madre?',
    ]
    for texto in preguntas_iniciales:
        if not PreguntaSeguridad.query.filter_by(pregunta=texto).first():
            nueva_pregunta = PreguntaSeguridad(pregunta=texto)
            db.session.add(nueva_pregunta)

    # Crear el administrador principal si no existe
    if not Usuario.query.filter_by(username='admin').first():
        rol_admin = Rol.query.filter_by(nombre='ADMIN').first()
        admin = Usuario(
            nombres='Administrador Principal',
            cedula='0000000000',
            username='admin',
            rol_id=rol_admin.id,
            password_temporal=True,
            primer_login=True,
            activo=True,
        )
        # La contraseña temporal es 'admin', el sistema obligará a cambiarla
        admin.set_password('admin')
        db.session.add(admin)

    db.session.commit()
    print("Datos iniciales verificados correctamente.")


# Punto de entrada de la aplicación
app = crear_app()

if __name__ == '__main__':
    app.run(debug=True)