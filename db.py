from pymongo import MongoClient
from urllib.parse import quote_plus
import os

HOST = os.getenv("MONGO_HOST", "32.198.32.165")
PORT = int(os.getenv("MONGO_PORT", "27017"))
USER = os.getenv("MONGO_USER", "appUser")
PASSWORD = quote_plus(os.getenv("MONGO_PASS", "App2025@"))

MONGO_URI = "mongodb://Admin:Admin2005@32.198.32.165:27017/admin?authSource=admin"
MONGO_URI_LOCAL = os.getenv("MONGO_URI", "mongodb://localhost:27017")

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    print(f"✅ Conectado a MongoDB AWS ({HOST})")

except Exception as e:
    print("❌ Error conectando a AWS:")
    print(e)
    raise

db = client["comerciotech"]
users_collection = db["users"]
clientes_collection = db["clientes"]
productos_collection = db["productos"]
pedidos_collection = db["pedidos"]

def ensure_indexes():
    clientes_collection.create_index("email", unique=True, sparse=True)
    clientes_collection.create_index([("nombre", 1)])
    clientes_collection.create_index([("apellido", 1)])
    productos_collection.create_index([("nombre", 1)])
    productos_collection.create_index([("categoria", 1)])
    productos_collection.create_index([("precio", 1)])
    productos_collection.create_index([("stock", 1)])
    pedidos_collection.create_index([("cliente_id", 1)])
    pedidos_collection.create_index([("fecha", -1)])
    pedidos_collection.create_index([("estado", 1)])
    pedidos_collection.create_index([("detalle.nombre", 1)])
    users_collection.create_index("email", unique=True)
    users_collection.create_index([("usuario_id", 1)])
    users_collection.create_index([("fecha", -1)])
    print(" Indices creados/verificados")

movimientos_collection = db["movimientos"]

ensure_indexes()
