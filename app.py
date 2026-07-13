from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import timedelta, datetime
import re

# Conectamos con el motor de la base de datos de MongoDB y nos traemos las colecciones clave de ComercioTech
from db import db, users_collection, clientes_collection, productos_collection, pedidos_collection, movimientos_collection
# Estas funciones actúan como guardias de seguridad para asegurar que nadie entre a rutas sin permiso o sin el rol adecuado
from decorators import login_required, admin_required, worker_required

app = Flask(__name__)
# Esta clave secreta protege las sesiones de nuestros usuarios para que nadie pueda falsificarlas
app.secret_key = "ComercioTech2024SecretKey!"
# Si un trabajador deja su sesión abierta, el sistema la dará por terminada automáticamente en veinticuatro horas
app.permanent_session_lifetime = timedelta(days=1)

# Expresiones regulares para asegurarnos de que los correos tengan una estructura lógica y las contraseñas cumplan con un mínimo de seguridad
EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PASSWORD_RE = re.compile(r'^(?=.*[A-Z])(?=.*[!@#$%^&*(),.?":{}|<>]).{8,}$')

# Dividimos el sistema en módulos independientes para que el código sea fácil de mantener y no tener un archivo monstruoso
from routes.clientes import clientes_bp
from routes.productos import productos_bp
from routes.pedidos import pedidos_bp
from routes.reportes import reportes_bp
from routes.usuarios import usuarios_bp
from routes.worker import worker_bp

app.register_blueprint(clientes_bp)
app.register_blueprint(productos_bp)
app.register_blueprint(pedidos_bp)
app.register_blueprint(reportes_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(worker_bp)


@app.context_processor
def inject_now():
    # Una utilidad global para poder usar la fecha actual directamente en cualquier diseño visual del sistema
    return {"now": datetime.now()}


@app.context_processor
def inject_roles():
    # Esto nos facilita la vida en las pantallas para decidir si mostramos u ocultamos menús según el rango del empleado
    return {"is_admin": session.get("rol") == "admin",
            "is_worker": session.get("rol") == "trabajador"}


@app.errorhandler(404)
def not_found(e):
    # Si un usuario se pierde o escribe mal una dirección, lo recibimos con una pantalla de error amigable
    return render_template("404.html"), 404


@app.route("/")
def index():
    # El punto de partida de ComercioTech. Si ya te conocemos, te mandamos directo a trabajar; si no, directo al login.
    if "user" in session:
        if session.get("rol") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("worker.dashboard"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    # Aquí procesamos el formulario cuando un miembro del equipo intenta ingresar al sistema
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    # Validamos el correo antes de ir a desgastar recursos haciendo consultas en la base de datos
    if not EMAIL_RE.match(email):
        flash("Correo electronico invalido", "danger")
        return redirect(url_for("index"))

    # Buscamos las credenciales del empleado y comparamos las contraseñas usando algoritmos seguros de encriptación
    user = users_collection.find_one({"email": email})
    if user and check_password_hash(user["password"], password):
        # Almacenamos la información esencial en la sesión del navegador para recordar quién está operando el sistema
        session.permanent = True
        session["user"] = user["email"]
        session["rol"] = user.get("rol", "trabajador")
        session["user_id"] = str(user["_id"])
        flash("Inicio de sesion exitoso", "success")
        # Mandamos a cada quien a su área correspondiente de la tienda
        if session["rol"] == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("worker.dashboard"))

    flash("Credenciales invalidas", "danger")
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    # Esta sección permite dar de alta a nuevos integrantes dentro del equipo de ComercioTech
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        errors = []
        # Evaluamos detalladamente que se cumplan todas las normativas de seguridad de la empresa
        if not EMAIL_RE.match(email):
            errors.append("Correo electronico invalido")
        if not PASSWORD_RE.match(password):
            errors.append("Minimo 8 caracteres, una mayuscula y un simbolo especial")
        if password != confirm:
            errors.append("Las contrasenas no coinciden")
        if users_collection.find_one({"email": email}):
            errors.append("El email ya esta registrado")

        # Si detectamos problemas, acumulamos todos los mensajes de error para avisarle al usuario de un solo golpe
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("register.html")

        # Si todo marcha a la perfección, guardamos al nuevo colaborador con permisos iniciales de trabajador estándar
        users_collection.insert_one({
            "email": email,
            "password": generate_password_hash(password), # Guardamos la contraseña encriptada para proteger su privacidad
            "rol": "trabajador",
            "created_at": datetime.now()
        })
        flash("Registro exitoso. Inicia sesion.", "success")
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    # Esta es la central de inteligencia donde el administrador monitorea la salud financiera e inventarios de ComercioTech
    
    # Recolectamos el volumen total de registros que tenemos archivados hasta el momento
    total_clientes = clientes_collection.count_documents({})
    total_productos = productos_collection.count_documents({})
    total_pedidos = pedidos_collection.count_documents({})
    total_usuarios = users_collection.count_documents({})

    # Hacemos un cálculo matemático directo en MongoDB para obtener la suma histórica de los ingresos sin contar cancelaciones
    ventas_total = list(pedidos_collection.aggregate([
        {"$match": {"estado": {"$ne": "Cancelado"}}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}}
    ]))
    ventas_total = ventas_total[0]["total"] if ventas_total else 0

    # Analizamos el rendimiento comercial actual y filtramos el stock para detectar alertas de reabastecimiento urgente
    hoy = datetime.now()
    inicio_mes = datetime(hoy.year, hoy.month, 1)
    clientes_mes = clientes_collection.count_documents({"fecha_registro": {"$gte": inicio_mes}})
    stock_bajo = productos_collection.count_documents({"stock": {"$lt": 10, "$gt": 0}}) # Alerta cuando queden unidades críticas de algún artículo
    sin_stock = productos_collection.count_documents({"stock": 0})
    pendientes = pedidos_collection.count_documents({"estado": "Pendiente"})

    # Obtenemos el registro de las últimas compras e investigamos quién fue el cliente cruzando las colecciones de la base de datos
    ultimos_pedidos = list(pedidos_collection.find().sort("fecha", -1).limit(10))
    for p in ultimos_pedidos:
        p["_id_str"] = str(p["_id"]) # Convertimos el identificador nativo de MongoDB a texto plano para que el navegador lo entienda
        c = clientes_collection.find_one({"_id": p["cliente_id"]})
        p["cliente_nombre"] = f"{c['nombre']} {c['apellido']}" if c else "Eliminado"

    # Listamos a los compradores de reciente incorporación a nuestra base de datos
    ultimos_clientes = list(clientes_collection.find().sort("fecha_registro", -1).limit(10))
    for c in ultimos_clientes:
        c["_id_str"] = str(c["_id"])

    # Agrupamos las ventas por mes e ingresos acumulados para poder proyectar el gráfico de crecimiento de la empresa
    ventas_mes = list(pedidos_collection.aggregate([
        {"$match": {"estado": {"$ne": "Cancelado"}}},
        {"$group": {
            "_id": {"anio": {"$year": "$fecha"}, "mes": {"$month": "$fecha"}},
            "total": {"$sum": "$total"}, "cantidad": {"$sum": 1}
        }},
        {"$sort": {"_id.anio": 1, "_id.mes": 1}},
        {"$limit": 12}
    ]))

    # Mapeamos los números del calendario a sus nombres en texto para que los gráficos del panel sean fáciles de interpretar
    meses_n = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
               5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
               9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
    chart_labels = [f"{meses_n[v['_id']['mes']]} {v['_id']['anio']}" for v in ventas_mes]
    chart_data = [v["total"] for v in ventas_mes]

    # Desglosamos todos los carritos de compra guardados para armar una lista con los diez artículos más exitosos en ventas
    prod_categoria = list(pedidos_collection.aggregate([
        {"$match": {"estado": {"$ne": "Cancelado"}}},
        {"$unwind": "$detalle"}, # Desempaquetamos los artículos de los pedidos para analizarlos individualmente
        {"$group": {"_id": "$detalle.nombre", "total": {"$sum": {"$multiply": ["$detalle.cantidad", "$detalle.precio"]}}}},
        {"$sort": {"total": -1}},
        {"$limit": 10}
    ]))

    # Buscamos los productos con menos stock en estantería para advertir al encargado de compras
    stock_data = list(productos_collection.find({"activo": True}).sort("stock", 1).limit(10))
    stock_labels = [p["nombre"] for p in stock_data]
    stock_values = [p["stock"] for p in stock_data]

    # Contabilizamos la cantidad total de pedidos que se encuentran retenidos o procesados según su estado de entrega
    ped_estado = list(pedidos_collection.aggregate([
        {"$group": {"_id": "$estado", "total": {"$sum": 1}}}
    ]))
    estado_labels = [e["_id"] for e in ped_estado]
    estado_values = [e["total"] for e in ped_estado]

    # Preparamos lotes rápidos de información sobre artículos en peligro de desabastecimiento total
    productos_sin_stock = list(productos_collection.find({"stock": 0}).limit(10))
    productos_stock_bajo = list(productos_collection.find({"stock": {"$lt": 10, "$gt": 0}}).limit(10))

    # Obtenemos la bitácora reciente de movimientos del almacén para vigilar las entradas y salidas de mercancía
    ultimos_movimientos = list(movimientos_collection.find().sort("fecha", -1).limit(10))
    for m in ultimos_movimientos:
        m["_id_str"] = str(m["_id"])
        if isinstance(m.get("fecha"), datetime):
            m["fecha_str"] = m["fecha"].strftime("%d/%m/%Y %H:%M")

    # Calculamos la concentración total del inventario dividida por cada categoría comercial de la tienda
    stock_por_categoria = list(productos_collection.aggregate([
        {"$group": {"_id": "$categoria", "total_stock": {"$sum": "$stock"}, "count": {"$sum": 1}}},
        {"$sort": {"total_stock": -1}}
    ]))
    cat_labels = [c["_id"] for c in stock_por_categoria]
    cat_stock_values = [c["total_stock"] for c in stock_por_categoria]

    # Enviamos todo este compendio de métricas ya procesadas hacia la interfaz de usuario
    return render_template("dashboard/index.html",
                           email=session["user"],
                           total_clientes=total_clientes,
                           total_productos=total_productos,
                           total_pedidos=total_pedidos,
                           total_usuarios=total_usuarios,
                           ventas_total=ventas_total,
                           clientes_mes=clientes_mes,
                           stock_bajo=stock_bajo,
                           sin_stock=sin_stock,
                           pendientes=pendientes,
                           ultimos_pedidos=ultimos_pedidos,
                           ultimos_clientes=ultimos_clientes,
                           ultimos_movimientos=ultimos_movimientos,
                           chart_labels=chart_labels,
                           chart_data=chart_data,
                           prod_categoria=prod_categoria,
                           stock_labels=stock_labels,
                           stock_values=stock_values,
                           estado_labels=estado_labels,
                           estado_values=estado_values,
                           cat_labels=cat_labels,
                           cat_stock_values=cat_stock_values,
                           productos_sin_stock=productos_sin_stock,
                           productos_stock_bajo=productos_stock_bajo)


@app.route("/buscar")
@login_required
def buscar_global():
    # Este es el motor de búsqueda en tiempo real de la tienda. Rastrea información de manera asíncrona mientras escribes.
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2: # Frenamos la consulta si el texto es muy corto para no saturar las lecturas de la base de datos
        return jsonify([])

    # Configuramos la búsqueda para que sea completamente indiferente a si escriben con mayúsculas o minúsculas
    regex = re.compile(re.escape(q), re.IGNORECASE)
    resultados = []

    if session.get("rol") == "admin":
        # Buscamos coincidencias de texto dentro del registro de nuestros clientes habituales
        for c in clientes_collection.find({"$or": [{"nombre": regex}, {"apellido": regex}, {"email": regex}]}).limit(5):
            resultados.append({
                "tipo": "Cliente", "nombre": f"{c['nombre']} {c['apellido']}",
                "email": c.get("email", ""), "url": url_for("clientes.listar", q=q)
            })

        # Buscamos coincidencias de texto dentro del catálogo general de mercancías de la tienda
        for p in productos_collection.find({"$or": [{"nombre": regex}, {"categoria": regex}]}).limit(5):
            resultados.append({
                "tipo": "Producto", "nombre": p["nombre"],
                "precio": f"${p['precio']:.2f}", "stock": p["stock"],
                "url": url_for("productos.listar", q=q)
            })

        # Buscamos órdenes de compra rastreando si contienen el nombre de algún artículo dentro de su lista interna de productos
        for p in pedidos_collection.find({"detalle.nombre": regex}).limit(5):
            c = clientes_collection.find_one({"_id": p["cliente_id"]})
            cn = f"{c['nombre']} {c['apellido']}" if c else "Eliminado"
            resultados.append({
                "tipo": "Pedido", "nombre": f"Pedido #{str(p['_id'])[-6:]}", # Recortamos el código largo de MongoDB para mostrar un folio elegante
                "cliente": cn, "total": f"${p['total']:.2f}",
                "url": url_for("pedidos.listar", q=q)
            })

        # Buscamos cuentas de trabajadores registradas en la plataforma que coincidan con el correo solicitado
        for u in users_collection.find({"email": regex}).limit(3):
            resultados.append({
                "tipo": "Usuario", "nombre": u["email"],
                "email": u.get("rol", ""),
                "url": url_for("usuarios.listar")
            })
    else:
        # Si quien busca es un operario normal de la tienda, limitamos su acceso para que únicamente encuentre información sobre existencias del almacén
        for p in productos_collection.find({"$or": [{"nombre": regex}, {"categoria": regex}]}).limit(5):
            resultados.append({
                "tipo": "Producto", "nombre": p["nombre"],
                "precio": f"${p['precio']:.2f}", "stock": p["stock"],
                "url": url_for("worker.productos", q=q)
            })

    return jsonify(resultados)


@app.route("/logout")
def logout():
    # Destruimos por completo los datos almacenados en memoria del navegador para cerrar la sesión de forma limpia y segura
    session.clear()
    flash("Sesion cerrada", "info")
    return redirect(url_for("index"))


if __name__ == "__main__":
    # Ponemos en marcha la aplicación web asignándole el puerto estándar de comunicación local
    app.run(debug=True, host="0.0.0.0", port=5000)
