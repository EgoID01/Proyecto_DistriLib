import os
from dotenv import load_dotenv

# Carga las variables definidas en el archivo .env
load_dotenv()


class Config:
    """Configuración central de la aplicación DISTRILIB."""

    # Clave secreta para sesiones y protección CSRF
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Construcción de la cadena de conexión a MySQL usando PyMySQL como driver
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_HOST = os.environ.get('DB_HOST')
    DB_PORT = os.environ.get('DB_PORT')
    DB_NAME = os.environ.get('DB_NAME')

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    # Desactiva el rastreo de modificaciones (consume memoria innecesaria)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Protección CSRF activa para todos los formularios
    WTF_CSRF_ENABLED = True