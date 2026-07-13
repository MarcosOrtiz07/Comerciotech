from pymongo import MongoClient
from urllib.parse import quote_plus
import os

# Configuramos las variables para ubicar y autenticar el servidor de la base de datos de manera flexible
HOST = os.getenv("MONGO_HOST", "32.198.32.165")
PORT = int(os.getenv("MONGO_PORT", "27017"))
USER = os.getenv("MONGO_USER", "appUser")
# Formateamos los caracteres especiales de la contraseña para evitar rupturas en la estructura de la ruta de conexión
PASSWORD = quote_plus(os.getenv("MONGO_PASS", "App2025@"))

# Definimos las rutas de acceso hacia los servidores tanto en la nube de producción como en entornos locales de prueba
MONGO_URI = "mongodb://Admin:Admin2005@32.198.32.165:27017/admin?authSource=admin"
MONGO_URI_LOCAL = os.getenv("MONGO_URI", "mongodb://localhost:27017")

try:
    # Intentamos levantar el puente de comunicación con el servidor remoto dándole un límite de espera prudente para no congelar la app
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # Enviamos una señal rápida de ida y vuelta para verificar que el servidor realmente esté despierto y respondiendo
    client.admin.command("ping")
    print(f"✅ Conectado a MongoDB AWS ({HOST})")

except Exception as e:
    # Si la comunicación falla atajamos el error para reportarlo inmediatamente y frenamos la ejecución por seguridad
    print("❌ Error conectando a AWS:")
    print(e)
    raise

# Apuntamos directamente hacia el espacio de ComercioTech en el servidor para empezar a operar
db = client["comerciotech"]
# Mapeamos los cajones organizadores lógicos donde guardaremos cada tipo de información del negocio
users_collection = db["users"]
clientes_collection = db["clientes"]
productos_collection = db["productos"]
pedidos_collection = db["pedidos"]

def ensure_indexes():
    # Estructuramos caminos rápidos de búsqueda dentro de las colecciones para que las consultas no se vuelvan lentas con el tiempo
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

# Activamos el cajón destinado a registrar la bitácora de inventario e historial de mercancía
movimientos_collection = db["movimientos"]

# Ejecutamos de forma automática el mantenimiento y verificación de las rutas rápidas de búsqueda al arrancar el script
ensure_indexes()
