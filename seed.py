from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import random
import sys

# ==================================================
# MongoDB AWS EC2
# ==================================================

HOST = "100.54.142.187"
PORT = 27017

USER = "Admin"
PASSWORD = quote_plus("Admin2005")

MONGO_URI = (
    f"mongodb://{USER}:{PASSWORD}@{HOST}:{PORT}/"
    "admin?authSource=admin"
)

try:
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000
    )

    client.admin.command("ping")
    print("✅ Conectado correctamente a MongoDB EC2")

except Exception as e:
    print(f"❌ Error de conexión: {e}")
    sys.exit()

db = client["comerciotech"]

users_collection = db["users"]
clientes_collection = db["clientes"]
productos_collection = db["productos"]
pedidos_collection = db["pedidos"]

# ==================================================
# Limpiar BD
# ==================================================

users_collection.delete_many({})
clientes_collection.delete_many({})
productos_collection.delete_many({})
pedidos_collection.delete_many({})

print("🗑️ Base limpiada")

# ==================================================
# Usuario administrador
# ==================================================

users_collection.insert_one({
    "email": "admin@comerciotech.cl",
    "password": generate_password_hash("Admin2005!"),
    "rol": "admin"
})

print("✅ Usuario administrador creado")

# ==================================================
# Clientes
# ==================================================

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

for _ in range(25):

    nombre = random.choice(nombres)
    apellido = random.choice(apellidos)

    cliente = {
        "nombre": nombre,
        "apellido": apellido,
        "email": f"{nombre.lower()}.{apellido.lower()}{random.randint(1,99)}@email.com",
        "telefono": f"+52 55{random.randint(10000000,99999999)}",
        "direccion": f"Calle {random.choice(['Principal','Juarez','Hidalgo','Morelos','Allende'])} #{random.randint(1,999)}",
        "fecha_registro": datetime.now() - timedelta(days=random.randint(1,365))
    }

    resultado = clientes_collection.insert_one(cliente)
    cliente["_id"] = resultado.inserted_id

    clientes.append(cliente)

print(f"✅ {len(clientes)} clientes creados")

# ==================================================
# Productos
# ==================================================

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

for nombre,categoria in productos_info:

    producto = {
        "nombre": nombre,
        "categoria": categoria,
        "descripcion": f"{nombre} de alta calidad.",
        "precio": round(random.uniform(50,25000),2),
        "stock": random.randint(0,50),
        "activo": True
    }

    if random.random() < 0.1:
        producto["activo"] = False
        producto["stock"] = 0

    resultado = productos_collection.insert_one(producto)

    producto["_id"] = resultado.inserted_id

    productos.append(producto)

print(f"✅ {len(productos)} productos creados")

# ==================================================
# Pedidos
# ==================================================

estados = [
    "Pendiente",
    "Procesando",
    "Enviado",
    "Entregado",
    "Cancelado"
]

pedidos = 0

for _ in range(40):

    cliente = random.choice(clientes)

    detalle = []
    total = 0

    seleccion = random.sample(productos, random.randint(1,5))

    for producto in seleccion:

        cantidad = random.randint(1,3)

        subtotal = cantidad * producto["precio"]

        detalle.append({
            "producto_id": producto["_id"],
            "nombre": producto["nombre"],
            "cantidad": cantidad,
            "precio": producto["precio"]
        })

        total += subtotal

    dias = random.randint(0,180)

    fecha = datetime.now() - timedelta(days=dias)

    pedido = {
        "cliente_id": cliente["_id"],
        "fecha": fecha,
        "estado": random.choice(estados),
        "total": round(total,2),
        "detalle": detalle
    }

    pedidos_collection.insert_one(pedido)

    pedidos += 1

print(f"✅ {pedidos} pedidos creados")

print()
print("===================================")
print(" BASE COMERCIOTECH LISTA ")
print("===================================")
print()
print("Login:")
print("Email: admin@comerciotech.cl")
print("Password: Admin2005!")
print()