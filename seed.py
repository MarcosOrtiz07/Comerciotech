from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import random
import sys

# ==================================================
# MongoDB AWS EC2
# ==================================================

# Establecemos los datos de ubicación del servidor en la nube donde corre nuestra base de datos
HOST = "100.54.142.187"
PORT = 27017

USER = "Admin"
PASSWORD = quote_plus("Admin2005")

# Armamos la cadena de conexión con las credenciales necesarias para acceder de forma segura
MONGO_URI = (
    f"mongodb://{USER}:{PASSWORD}@{HOST}:{PORT}/"
    "admin?authSource=admin"
)

try:
    # Intentamos conectar con el servidor dándole unos segundos de tolerancia antes de desistir
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000
    )

    # Lanzamos un pulso de prueba para confirmar que el servidor realmente nos está escuchando
    client.admin.command("ping")
    print("✅ Conectado correctamente a MongoDB EC2")

except Exception as e:
    # Si el servidor no responde, mostramos el motivo del fallo y detenemos el proceso de inmediato
    print(f"❌ Error de conexión: {e}")
    sys.exit()

# Nos posicionamos sobre el espacio de trabajo asignado a ComercioTech
db = client["comerciotech"]

# Mapeamos las distintas colecciones con las que vamos a interactuar en esta carga inicial
users_collection = db["users"]
clientes_collection = db["clientes"]
productos_collection = db["productos"]
pedidos_collection = db["pedidos"]

# ==================================================
# Limpiar BD
# ==================================================

# Vaciamos por completo las colecciones para evitar duplicados y empezar con un entorno limpio
users_collection.delete_many({})
clientes_collection.delete_many({})
productos_collection.delete_many({})
pedidos_collection.delete_many({})

print("🗑️ Base limpiada")

# ==================================================
# Usuario administrador
# ==================================================

# Registramos la cuenta principal del administrador del sistema usando una contraseña encriptada
users_collection.insert_one({
    "email": "admin@comerciotech.cl",
    "password": generate_password_hash("Admin2005!"),
    "rol": "admin"
})

print("✅ Usuario administrador creado")

# ==================================================
# Clientes
# ==================================================

# Listados de nombres y apellidos comunes que usaremos para combinar y simular clientes reales
nombres = [
    "Carlos","Maria","Jose","Ana","Luis","Sofia","Miguel","Elena","Jorge","Laura",
    "Pedro","Rosa","Diego","Carmen","Angel","Patricia","David","Fernanda","Ramon","Martha"
]

apellidos = [
    "Garcia","Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Perez","Sanchez",
    "Ramirez","Torres","Flores","Rivera","Gomez","Diaz","Reyes","Cruz","Morales","Ortiz",
    "Jimenez","Vazquez"
]

clientes = []

# Generamos un grupo de veinticinco clientes de forma aleatoria para poblar el sistema
for _ in range(25):

    nombre = random.choice(nombres)
    apellido = random.choice(apellidos)

    # Armamos la ficha técnica del cliente simulando correos, teléfonos y fechas de registro pasadas
    cliente = {
        "nombre": nombre,
        "apellido": apellido,
        "email": f"{nombre.lower()}.{apellido.lower()}{random.randint(1,99)}@email.com",
        "telefono": f"+52 55{random.randint(10000000,99999999)}",
        "direccion": f"Calle {random.choice(['Principal','Juarez','Hidalgo','Morelos','Allende'])} #{random.randint(1,999)}",
        "fecha_registro": datetime.now() - timedelta(days=random.randint(1,365))
    }

    # Guardamos el registro en la base de datos y recuperamos el identificador único que le asignó MongoDB
    resultado = clientes_collection.insert_one(cliente)
    cliente["_id"] = resultado.inserted_id

    # Conservamos el cliente en una lista interna para usarlo más adelante al armar las compras
    clientes.append(cliente)

print(f"✅ {len(clientes)} clientes creados")

# ==================================================
# Productos
# ==================================================

# Catálogo base con los artículos tecnológicos y de hogar que maneja la tienda ComercioTech
productos_info = [
    ("Laptop Pro X1","Computacion"),
    ("Mouse Inalambrico","Computacion"),
    ("Teclado Mecanico RGB","Computacion"),
    ("Monitor 27 4K","Computacion"),
    ("Audifonos Bluetooth","Audio"),
    ("Parlante Portatil","Audio"),
    ("Microfono USB","Audio"),
    ("iPhone 15","Celulares"),
    ("Samsung Galaxy S24","Celulares"),
    ("Cargador Rapido","Celulares"),
    ("Funda Protectora","Accesorios"),
    ("Hub USB-C","Accesorios"),
    ("Webcam HD","Electronica"),
    ("Smart TV 55","Electronica"),
    ("Router WiFi 6","Electronica"),
    ("Bocina Inteligente","Electronica"),
    ("Laptop Gamer","Computacion"),
    ("Tablet 10","Computacion"),
    ("SSD 1TB","Computacion"),
    ("Memoria USB","Accesorios"),
    ("Reloj Deportivo","Deportes"),
    ("Banda Fitness","Deportes"),
    ("Bicicleta Montana","Deportes"),
    ("Lego Constructor","Juguetes"),
    ("Dron con Camara","Juguetes"),
    ("Licuadora","Hogar"),
    ("Cafetera","Hogar"),
    ("Aspiradora Robot","Hogar"),
    ("Silla Ergonomica","Computacion"),
    ("Escritorio","Hogar")
]

productos = []

# Procesamos cada artículo del catálogo para estructurar su inventario y costos
for nombre,categoria in productos_info:

    producto = {
        "nombre": nombre,
        "categoria": categoria,
        "descripcion": f"{nombre} de alta calidad.",
        "precio": round(random.uniform(50,25000),2),
        "stock": random.randint(0,50),
        "activo": True
    }

    # Dejamos un pequeño margen al azar para simular artículos que se quedaron sin existencias o están descontinuados
    if random.random() < 0.1:
        producto["activo"] = False
        producto["stock"] = 0

    # Insertamos el producto en las estanterías digitales de la base de datos
    resultado = productos_collection.insert_one(producto)

    # Registramos su identificador único para poder ligarlo correctamente a los carritos de compra
    producto["_id"] = resultado.inserted_id

    productos.append(producto)

print(f"✅ {len(productos)} productos creados")

# ==================================================
# Pedidos
# ==================================================

# Los diferentes estados lógicos por los que pasa una compra dentro de ComercioTech
estados = [
    "Pendiente",
    "Procesando",
    "Enviado",
    "Entregado",
    "Cancelado"
]

pedidos = 0

# Simulamos cuarenta transacciones comerciales para generar historial en el panel de control
for _ in range(40):

    # Elegimos al azar a un cliente de nuestra lista para asignarle la compra
    cliente = random.choice(clientes)

    detalle = []
    total = 0

    # Seleccionamos un puñado de artículos diferentes para llenar el carrito de este pedido
    seleccion = random.sample(productos, random.randint(1,5))

    for producto in seleccion:

        cantidad = random.randint(1,3)

        subtotal = cantidad * producto["precio"]

        # Agregamos el desglose de este artículo al carrito de compras final
        detalle.append({
            "producto_id": producto["_id"],
            "nombre": producto["nombre"],
            "cantidad": cantidad,
            "precio": producto["precio"]
        })

        total += subtotal

    # Distribuimos los pedidos a lo largo de los últimos seis meses para tener datos históricos realistas
    dias = random.randint(0,180)

    fecha = datetime.now() - timedelta(days=dias)

    # Estructuramos la orden de compra con los montos definitivos, fechas y su estado logístico
    pedido = {
        "cliente_id": cliente["_id"],
        "fecha": fecha,
        "estado": random.choice(estados),
        "total": round(total,2),
        "detalle": detalle
    }

    # Archivamos el pedido formalmente dentro de la base de datos
    pedidos_collection.insert_one(pedido)

    pedidos += 1

print(f"✅ {pedidos} pedidos creados")

# Desplegamos un reporte final en la terminal confirmando que las credenciales de prueba ya están listas para usarse
print()
print("===================================")
print(" BASE COMERCIOTECH LISTA ")
print("===================================")
print()
print("Login:")
print("Email: admin@comerciotech.cl")
print("Password: Admin2005!")
print()
