#!/usr/bin/env python3
"""
Datos de prueba para DistriLib
Simula 1 año de operación: junio 2025 – mayo 2026

Uso:
    python cargar_datos_prueba.py

Credenciales generadas:
    admin        / 123456    (ADMIN)     – primer_login=True, password_temporal=True
    jdaltamirano / Startend3 (VENDEDOR – Juan Diego Altamirano)
    jamalave     / Startend3 (BODEGUERO – Jennifer Alejandra Malave)
    omite        / Startend3 (VENDEDOR – Oscar Mite)
"""

import sys
import os
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import crear_app
from models import db
from models.user import Usuario, Rol, PreguntaSeguridad, RespuestaSeguridad
from models.book import Libro, MovimientoInventario
from models.client import Cliente
from models.sale import Venta, DetalleVenta

random.seed(42)


def rand_fecha(anio, mes, dia_max=28):
    return datetime(anio, mes, random.randint(1, dia_max),
                    random.randint(8, 18), random.randint(0, 59))



app = crear_app()

with app.app_context():

    # ── Guardia: no correr dos veces ────────────────────────────────
    if Usuario.query.filter_by(username='jdaltamirano').first():
        print("Los datos de prueba ya existen. Nada que hacer.")
        sys.exit(0)

    # ── Roles ya seedeados ───────────────────────────────────────────
    rol_admin     = Rol.query.filter_by(nombre='ADMIN').first()
    rol_vendedor  = Rol.query.filter_by(nombre='VENDEDOR').first()
    rol_bodeguero = Rol.query.filter_by(nombre='BODEGUERO').first()

    # ── Actualizar admin ────────────────────────────────────────────
    admin = Usuario.query.filter_by(username='admin').first()
    admin.nombres           = 'Administrador del Sistema'
    admin.cedula            = '1712345678'
    admin.primer_login      = True
    admin.password_temporal = True
    admin.set_password('123456')

    # ── Preguntas de seguridad ───────────────────────────────────────
    pq_mascota = PreguntaSeguridad.query.filter_by(
        pregunta='¿Cuál es el nombre de tu primera mascota?').first()
    pq_ciudad  = PreguntaSeguridad.query.filter_by(
        pregunta='¿En qué ciudad naciste?').first()
    pq_comida  = PreguntaSeguridad.query.filter_by(
        pregunta='¿Cuál es tu comida favorita?').first()

    def agregar_respuestas(usuario_id, resps):
        for pq, resp in zip([pq_mascota, pq_ciudad, pq_comida], resps):
            r = RespuestaSeguridad(usuario_id=usuario_id, pregunta_id=pq.id)
            r.set_respuesta(resp)
            db.session.add(r)

    resps_demo = ['Coco', 'Guayaquil', 'Encebollado']

    # ── Nuevos usuarios ─────────────────────────────────────────────
    def nuevo_usuario(nombres, cedula, username, rol, fecha):
        u = Usuario(
            nombres=nombres, cedula=cedula, username=username,
            rol_id=rol.id, activo=True,
            primer_login=False, password_temporal=False,
            fecha_creacion=fecha,
        )
        u.set_password('Startend3')
        db.session.add(u)
        db.session.flush()
        return u

    v1 = nuevo_usuario('Juan Diego Altamirano Tobar', '0954236980', 'jdaltamirano',
                       rol_vendedor,  datetime(2025, 6, 1, 9, 0))
    agregar_respuestas(v1.id, resps_demo)

    bo = nuevo_usuario('Jennifer Alejandra Malave',   '0966233090', 'jamalave',
                       rol_bodeguero, datetime(2025, 6, 5, 8, 30))
    agregar_respuestas(bo.id, resps_demo)

    v2 = nuevo_usuario('Oscar Mite',                  '1723456783', 'omite',
                       rol_vendedor,  datetime(2025, 7, 15, 10, 0))
    agregar_respuestas(v2.id, resps_demo)

    db.session.commit()
    print("✔ Usuarios creados.")

    # ── Libros ──────────────────────────────────────────────────────
    libros_raw = [
        # (nombre, autor, editorial, anio, isbn, precio, stock_ini)
        ('Código Civil Ecuatoriano Comentado',      'Fausto Murillo',              'Corporación de Estudios', 2023, '978-9942-04-001-1', 45.00, 40),
        ('Código Penal del Ecuador',                'Gustavo Medina',              'Editorial Universitaria', 2022, '978-9942-04-002-8', 38.00, 35),
        ('Código de Comercio Ecuatoriano',          'Jorge Morales',               'Ediciones Legales',       2023, '978-9942-04-003-5', 42.00, 30),
        ('Derecho Constitucional Ecuatoriano',      'Agustín Grijalva',            'UASB',                    2022, '978-9942-04-004-2', 55.00, 25),
        ('Manual de Derecho Laboral',               'Rodrigo Ávalos',              'Jurídica',                2023, '978-9942-04-005-9', 48.00, 28),
        ('Código Tributario Comentado',             'César Montaño',               'CEP',                     2022, '978-9942-04-006-6', 52.00, 30),
        ('Ley de Compañías Comentada',              'Xavier Andrade',              'Ediciones Legales',       2023, '978-9942-04-007-3', 59.00, 20),
        ('Procedimiento Civil Ecuatoriano',         'Ernesto Salcedo',             'Editorial Universitaria', 2021, '978-9942-04-008-0', 44.00, 22),
        ('Derecho de Familia en Ecuador',           'María Cobo',                  'PUCE',                    2022, '978-9942-04-009-7', 39.00, 25),
        ('Ley Orgánica de Comunicación',            'Farith Simon',                'CEP',                     2021, '978-9942-04-010-3', 35.00, 20),
        ('Cien Años de Soledad',                    'Gabriel García Márquez',      'Debolsillo',              2023, '978-0-06-088328-7', 18.50, 50),
        ('El Alquimista',                           'Paulo Coelho',                'Planeta',                 2022, '978-0-06-231609-7', 15.00, 45),
        ('Don Quijote de la Mancha',                'Miguel de Cervantes',         'Alfaguara',               2023, '978-84-204-4804-2', 22.00, 35),
        ('La Casa de los Espíritus',                'Isabel Allende',              'Plaza & Janés',           2022, '978-84-01-42071-4', 19.50, 40),
        ('Rayuela',                                 'Julio Cortázar',              'Alfaguara',               2022, '978-84-204-8393-7', 21.00, 28),
        ('Pedro Páramo',                            'Juan Rulfo',                  'RM Editorial',            2021, '978-968-23-2141-5', 14.00, 35),
        ('El Túnel',                                'Ernesto Sabato',              'Seix Barral',             2022, '978-84-322-2127-2', 13.50, 30),
        ('Ficciones',                               'Jorge Luis Borges',           'Emecé',                   2023, '978-950-04-0017-1', 16.00, 25),
        ('Contabilidad General',                    'Pedro Zapata Sánchez',        'McGraw-Hill',             2021, '978-607-15-1623-1', 65.00, 20),
        ('Principios de Administración',            'Idalberto Chiavenato',        'McGraw-Hill',             2020, '978-607-15-1616-3', 72.00, 18),
        ('Finanzas Corporativas',                   'Stephen Ross',                'McGraw-Hill',             2019, '978-607-15-1515-9', 89.00, 12),
        ('Fundamentos de Marketing',                'Philip Kotler',               'Pearson',                 2021, '978-607-32-4590-3', 78.00, 15),
        ('Macroeconomía',                           'Paul Samuelson',              'McGraw-Hill',             2020, '978-607-15-1453-4', 68.00, 16),
        ('Introducción a la Filosofía',             'Jacques Maritain',            'Club de Lectores',        2018, '978-9942-04-011-0', 25.00, 22),
        ('Historia del Ecuador',                    'Enrique Ayala Mora',          'UASB',                    2022, '978-9942-04-012-7', 32.00, 30),
        ('Matemáticas Superiores',                  'Erwin Kreyszig',              'Limusa',                  2020, '978-968-18-5190-8', 85.00, 10),
        ('Estadística para Administración',         'Mark Berenson',               'Pearson',                 2018, '978-607-32-4031-1', 75.00, 12),
        ('Investigación de Operaciones',            'Hamdy Taha',                  'Pearson',                 2017, '978-607-32-3804-2', 82.00, 10),
        ('Sistemas de Información Gerencial',       'Kenneth Laudon',              'Pearson',                 2020, '978-607-32-4920-8', 76.00, 14),
        ('Metodología de la Investigación',         'Roberto Hernández Sampieri',  'McGraw-Hill',             2018, '978-607-15-2262-1', 69.00, 18),
        ('Psicología General',                      'Robert Feldman',              'McGraw-Hill',             2017, '978-607-15-0918-9', 58.00, 16),
        ('Biología Molecular',                      'Robert Weaver',               'McGraw-Hill',             2019, '978-607-15-1234-9', 95.00,  8),
        ('El Nombre de la Rosa',                    'Umberto Eco',                 'Debolsillo',              2022, '978-84-9793-764-4', 17.00, 28),
        ('Sapiens: De animales a dioses',           'Yuval Noah Harari',           'Debate',                  2023, '978-84-9992-395-5', 24.00, 38),
        ('El Poder del Ahora',                      'Eckhart Tolle',               'Gaia',                    2022, '978-84-8445-155-0', 16.50, 32),
    ]

    libros = []
    stock  = {}   # libro.id -> stock actual

    for nombre, autor, editorial, anio, isbn, precio, stock_ini in libros_raw:
        l = Libro(
            nombre=nombre, autor=autor, editorial=editorial,
            anio_publicacion=anio, isbn=isbn, precio=precio,
            stock=stock_ini, activo=True,
            fecha_registro=datetime(2025, 5, 15, 10, 0),
        )
        db.session.add(l)
        db.session.flush()
        stock[l.id] = stock_ini
        db.session.add(MovimientoInventario(
            libro_id=l.id, usuario_id=admin.id,
            tipo_movimiento='ENTRADA', cantidad=stock_ini,
            motivo='Stock inicial', fecha=datetime(2025, 5, 20, 10, 0),
        ))
        libros.append(l)

    db.session.commit()
    print(f"✔ {len(libros)} libros creados.")

    # Alias para referencias posteriores
    l_cod_civil  = libros[0];  l_cod_penal = libros[1];  l_cod_com   = libros[2]
    l_der_const  = libros[3];  l_cod_trib  = libros[5];  l_ley_comp  = libros[6]
    l_cien_anos  = libros[10]; l_alquimista= libros[11]; l_allende   = libros[13]
    l_rulfo      = libros[15]; l_contab    = libros[18]; l_admin_lib = libros[19]
    l_hist_ec    = libros[24]; l_sapiens   = libros[33]

    # ── Clientes ────────────────────────────────────────────────────
    clientes_raw = [
        ('1701234561', 'Ana',        'Torres Salinas',    'Av. Amazonas 1234, Quito',          '0991234567', 'ana.torres@gmail.com'),
        ('0901234562', 'Roberto',    'Espinoza Peña',     'Calle Sucre 45, Guayaquil',         '0982345678', 'robertoe@yahoo.com'),
        ('1801234563', 'Verónica',   'Castillo Ramos',    'Bolívar 678, Ambato',               '0973456789', 'verocastle@hotmail.com'),
        ('0301234564', 'Diego',      'Morales Jiménez',   'Colón 234, Cuenca',                 '0964567890', 'dmorales@gmail.com'),
        ('1601234565', 'Patricia',   'Guerrero López',    'Gran Colombia 890, Riobamba',       '0995678901', 'pguerrero@outlook.com'),
        ('2001234566', 'Fernando',   'Acosta Vera',       'Olmedo 112, Ibarra',                '0986789012', 'facosta@gmail.com'),
        ('1301234567', 'Lucía',      'Benítez Cruz',      'Ayacucho 456, Portoviejo',          '0977890123', 'lbenitez@yahoo.com'),
        ('1201234568', 'Miguel',     'Ríos Sandoval',     'Rocafuerte 789, Latacunga',         '0968901234', 'mrios@gmail.com'),
        ('0201234569', 'Sandra',     'Vargas Montoya',    'Pichincha 321, Quevedo',            '0999012345', 'svargas@hotmail.com'),
        ('1501234560', 'Andrés',     'Fuentes Herrera',   'Manabí 654, Manta',                 '0980123456', 'afuentes@gmail.com'),
        ('1701234571', 'Carmen',     'Delgado Tapia',     'Naciones Unidas 987, Quito',        '0971234567', 'cdelgado@outlook.com'),
        ('0901234572', 'Jorge',      'Villacís Ponce',    '9 de Octubre 159, Guayaquil',       '0992345678', 'jvillacis@gmail.com'),
        ('1801234573', 'Daniela',    'Romero Alvarado',   'Cevallos 753, Ambato',              '0983456789', 'dromero@yahoo.com'),
        ('0301234574', 'Pablo',      'Ortega Chiriboga',  'Mariscal Sucre 852, Cuenca',        '0974567890', 'portega@gmail.com'),
        ('1701234575', 'Margarita',  'Segura Naranjo',    'República 963, Quito',              '0995678012', 'msegura@hotmail.com'),
        ('0601234576', 'Hernán',     'Cabrera Flores',    'García Moreno 147, Riobamba',       '0986789123', 'hcabrera@gmail.com'),
        ('1301234577', 'Isabella',   'Palacios Intriago', 'Chile 258, Portoviejo',             '0977890234', 'ipalacios@outlook.com'),
        ('0901234578', 'William',    'Aguirre Briones',   'Luque 369, Guayaquil',              '0968901345', 'waguirre@gmail.com'),
        ('1701234579', 'Sofía',      'Miranda Chávez',    'Iñaquito 741, Quito',               '0999123456', 'smiranda@yahoo.com'),
        ('0401234580', 'Cristian',   'León Rivadeneira',  'Olmedo 852, Tulcán',                '0980234567', 'cleon@gmail.com'),
        ('1701234581', 'Gabriela',   'Suárez Pinto',      'Av. Shyris 1596, Quito',            '0991345678', 'gsuarez@gmail.com'),
        ('0901234582', 'Eduardo',    'Hidalgo Romo',      'Av. Boyacá 1234, Guayaquil',        '0982456789', 'ehidalgo@yahoo.com'),
        ('1701234583', 'Valentina',  'Cruz Paredes',      'Diego de Almagro 567, Quito',       '0973567890', 'vcruz@gmail.com'),
        ('1791234567001', 'Universidad Central del', 'Ecuador',
                                                           'Av. América s/n, Quito',           '0223231523', 'adquisiciones@uce.edu.ec'),
        ('0990123456001', 'Librería Científica',      'S.A.',
                                                           'Av. 9 de Octubre 1120, Guayaquil', '0424560123', 'compras@libreriacientifica.com.ec'),
        ('1790123456001', 'Colegio de Abogados de', 'Pichincha',
                                                           'Av. Patria 456, Quito',            '0223456789', 'secretaria@cab.ec'),
    ]

    clientes = []
    for cedula, nombres, apellidos, dir_, tel, correo in clientes_raw:
        c = Cliente(
            cedula_ruc=cedula, nombres=nombres, apellidos=apellidos,
            direccion=dir_, telefono=tel, correo=correo,
            fecha_registro=datetime(2025, 5, 25, 10, 0),
        )
        db.session.add(c)
        clientes.append(c)

    db.session.flush()
    db.session.commit()
    print(f"✔ {len(clientes)} clientes creados.")

    # ── Ventas ──────────────────────────────────────────────────────
    vendedores  = [admin, v1, v2]
    libros_jur  = libros[:10]
    libros_lit  = libros[10:18]
    libros_adm  = libros[18:23]
    libros_acad = libros[23:]

    # (anio, mes, num_ventas, dia_max)
    calendario = [
        (2025,  6, 15, 30), (2025,  7, 18, 31), (2025,  8, 30, 31),
        (2025,  9, 22, 30), (2025, 10, 19, 31), (2025, 11, 26, 30),
        (2025, 12, 40, 31), (2026,  1, 22, 31), (2026,  2, 18, 28),
        (2026,  3, 24, 31), (2026,  4, 21, 30), (2026,  5, 24, 30),
    ]

    n_ventas = 0
    for anio, mes, num, dia_max in calendario:
        if mes in [8, 9, 2, 3]:
            pool_pref = libros_jur + libros_adm + libros_acad
        elif mes in [12, 1]:
            pool_pref = libros_lit + libros_jur
        else:
            pool_pref = libros

        for _ in range(num):
            fecha    = rand_fecha(anio, mes, dia_max)
            vendedor = random.choice(vendedores)
            cliente  = random.choice(clientes)

            disp = [l for l in pool_pref if stock[l.id] > 0] or \
                   [l for l in libros    if stock[l.id] > 0]
            if not disp:
                continue

            selec    = random.sample(disp, min(random.choices([1, 2, 3], weights=[50, 35, 15])[0], len(disp)))
            detalles = [(l, random.randint(1, min(stock[l.id], 3))) for l in selec]
            subtotal = round(sum(l.precio * q for l, q in detalles), 2)

            venta = Venta(
                cliente_id=cliente.id, usuario_id=vendedor.id,
                subtotal=subtotal, iva=0.0, total=subtotal,
                estado='ACTIVA', fecha_venta=fecha,
            )
            db.session.add(venta)
            db.session.flush()

            for l, qty in detalles:
                sub = round(l.precio * qty, 2)
                db.session.add(DetalleVenta(
                    venta_id=venta.id, libro_id=l.id,
                    cantidad=qty, precio_unitario=l.precio, subtotal=sub,
                ))
                stock[l.id] -= qty
                db.session.add(MovimientoInventario(
                    libro_id=l.id, usuario_id=vendedor.id,
                    tipo_movimiento='VENTA', cantidad=qty,
                    motivo=f'Venta #{venta.id}', fecha=fecha,
                ))
            n_ventas += 1

    db.session.commit()
    print(f"✔ {n_ventas} ventas creadas.")

    # ── Anular ~5% ──────────────────────────────────────────────────
    activas  = Venta.query.filter_by(estado='ACTIVA').all()
    a_anular = random.sample(activas, max(1, len(activas) // 20))

    for v in a_anular:
        v.estado  = 'ANULADA'
        f_anu     = v.fecha_venta + timedelta(hours=random.randint(1, 48))
        for d in DetalleVenta.query.filter_by(venta_id=v.id).all():
            stock[d.libro_id] += d.cantidad
            db.session.add(MovimientoInventario(
                libro_id=d.libro_id, usuario_id=admin.id,
                tipo_movimiento='ANULACION', cantidad=d.cantidad,
                motivo=f'Anulación venta #{v.id}', fecha=f_anu,
            ))

    db.session.commit()
    print(f"✔ {len(a_anular)} ventas anuladas.")

    # ── Reposiciones ────────────────────────────────────────────────
    reposiciones = [
        (datetime(2025,  8,  1,  9,  0), l_cod_civil,   20, 'Reposición agosto – inicio clases'),
        (datetime(2025,  8,  1,  9, 10), l_der_const,   15, 'Reposición agosto'),
        (datetime(2025,  8,  5, 10,  0), l_contab,      10, 'Reposición contabilidad'),
        (datetime(2025,  9, 15, 11,  0), l_cien_anos,   25, 'Reposición literatura'),
        (datetime(2025, 11, 15, 10,  0), l_cod_penal,   20, 'Reposición noviembre'),
        (datetime(2025, 11, 20, 10,  0), l_cod_trib,    15, 'Reposición tributario'),
        (datetime(2025, 12,  1,  9,  0), l_alquimista,  30, 'Stock temporada navidad'),
        (datetime(2025, 12,  1,  9, 15), l_allende,     20, 'Stock temporada navidad'),
        (datetime(2025, 12,  5, 10,  0), l_sapiens,     25, 'Sapiens – alta demanda'),
        (datetime(2026,  1, 10,  9,  0), l_cod_com,     20, 'Reposición enero'),
        (datetime(2026,  2, 15, 10,  0), l_admin_lib,   10, 'Reposición administración'),
        (datetime(2026,  3,  1,  9,  0), l_cod_civil,   15, 'Reposición marzo'),
        (datetime(2026,  4, 10, 11,  0), l_hist_ec,     15, 'Historia del Ecuador – demanda'),
        (datetime(2026,  5,  5, 10,  0), l_ley_comp,    10, 'Reposición mayo'),
    ]

    for fecha, libro, qty, motivo in reposiciones:
        stock[libro.id] += qty
        db.session.add(MovimientoInventario(
            libro_id=libro.id, usuario_id=bo.id,
            tipo_movimiento='ENTRADA', cantidad=qty,
            motivo=motivo, fecha=fecha,
        ))

    # ── Ajustes ─────────────────────────────────────────────────────
    ajustes = [
        (datetime(2025, 10,  5, 16, 0), l_rulfo,    2, 'Ajuste – libros deteriorados'),
        (datetime(2026,  1, 31, 17, 0), libros[22], 1, 'Ajuste inventario físico'),
        (datetime(2026,  3, 20, 15, 0), libros[31], 1, 'Ajuste – libro dañado'),
    ]

    for fecha, libro, qty, motivo in ajustes:
        stock[libro.id] = max(0, stock[libro.id] - qty)
        db.session.add(MovimientoInventario(
            libro_id=libro.id, usuario_id=bo.id,
            tipo_movimiento='AJUSTE', cantidad=qty,
            motivo=motivo, fecha=fecha,
        ))

    # ── Forzar alertas de stock para la demo ─────────────────────
    # Garantiza que el dashboard muestre notificaciones interesantes
    con_stock = [l for l in libros if stock[l.id] > 6]
    if len(con_stock) >= 4:
        rojos    = random.sample(con_stock, 2)
        resto    = [l for l in con_stock if l not in rojos]
        amarillos = random.sample(resto, 2)
        for l in rojos:
            dif = stock[l.id] - 1
            if dif > 0:
                stock[l.id] = 1
                db.session.add(MovimientoInventario(
                    libro_id=l.id, usuario_id=bo.id,
                    tipo_movimiento='AJUSTE', cantidad=dif,
                    motivo='Ajuste cierre período – inventario físico',
                    fecha=datetime(2026, 5, 30, 17, 0),
                ))
        for l in amarillos:
            dif = stock[l.id] - 4
            if dif > 0:
                stock[l.id] = 4
                db.session.add(MovimientoInventario(
                    libro_id=l.id, usuario_id=bo.id,
                    tipo_movimiento='AJUSTE', cantidad=dif,
                    motivo='Ajuste cierre período – inventario físico',
                    fecha=datetime(2026, 5, 30, 17, 0),
                ))

    # ── Sincronizar stock final ──────────────────────────────────────
    for l in libros:
        l.stock  = max(0, stock[l.id])
        l.activo = l.stock > 0

    db.session.commit()

    # ── Resumen ──────────────────────────────────────────────────────
    total_v    = Venta.query.count()
    anuladas_n = Venta.query.filter_by(estado='ANULADA').count()
    print()
    print("=" * 52)
    print("   DATOS DE PRUEBA INSERTADOS CORRECTAMENTE")
    print("=" * 52)
    print(f"   Usuarios    : {Usuario.query.count()}")
    print(f"   Libros      : {Libro.query.count()}")
    print(f"   Clientes    : {Cliente.query.count()}")
    print(f"   Ventas      : {total_v}  ({anuladas_n} anuladas)")
    print(f"   Movimientos : {MovimientoInventario.query.count()}")
    print()
    print("   CREDENCIALES:")
    print("   admin        / 123456    [ADMIN]  – primer login pendiente")
    print("   jdaltamirano / Startend3 [VENDEDOR]")
    print("   jamalave     / Startend3 [BODEGUERO]")
    print("   omite        / Startend3 [VENDEDOR]")
    print("=" * 52)
